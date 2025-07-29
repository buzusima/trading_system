#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSITION TRACKER - Enhanced Position Tracking System (COMPLETE FIXED)
====================================================================
ระบบติดตาม Position ที่ปรับปรุงให้รองรับระบบใหม่
เพิ่ม methods ที่จำเป็นสำหรับ Core Trading System - ครบถ้วนทุก function
"""

import MetaTrader5 as mt5
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import deque, defaultdict

# Internal imports
try:
   from config.settings import get_system_settings
   from config.trading_params import get_trading_parameters, get_current_gold_symbol
   from utilities.professional_logger import setup_component_logger
   from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity
   from mt5_integration.mt5_connector import ensure_mt5_connection
except ImportError as e:
   # Fallback for missing modules
   import logging
   def setup_component_logger(name):
       logger = logging.getLogger(name)
       if not logger.handlers:
           handler = logging.StreamHandler()
           formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
           handler.setFormatter(formatter)
           logger.addHandler(handler)
           logger.setLevel(logging.INFO)
       return logger
   
   def handle_trading_errors(category, severity):
       def decorator(func):
           def wrapper(*args, **kwargs):
               try:
                   return func(*args, **kwargs)
               except Exception as e:
                   logging.error(f"Trading Error in {func.__name__}: {e}")
                   return None
           return wrapper
       return decorator
   
   def ensure_mt5_connection():
       try:
           return mt5.initialize()
       except:
           return False
   
   def get_system_settings():
       return None
   
   def get_trading_parameters():
       return None
   
   def get_current_gold_symbol():
       return "XAUUSD"
   
   class ErrorCategory:
       SYSTEM = "SYSTEM"
       TRADING_LOGIC = "TRADING_LOGIC"
       MARKET_DATA = "MARKET_DATA"
       
   class ErrorSeverity:
       LOW = "LOW"
       MEDIUM = "MEDIUM"
       HIGH = "HIGH"
       CRITICAL = "CRITICAL"

class PositionStatus(Enum):
   """สถานะของ Position"""
   OPEN = "OPEN"
   CLOSED = "CLOSED"
   PARTIAL = "PARTIAL"
   PENDING = "PENDING"

class PositionType(Enum):
   """ประเภทของ Position"""
   BUY = "BUY"
   SELL = "SELL"

@dataclass
class Position:
   """ข้อมูล Position หลัก"""
   ticket: int
   symbol: str
   type: str  # "BUY" or "SELL"
   volume: float
   open_price: float
   current_price: float
   profit: float
   time_open: datetime
   magic: int = 0
   comment: str = ""
   swap: float = 0.0
   commission: float = 0.0
   
   # Recovery attributes
   is_recovery_position: bool = False
   recovery_level: int = 0
   parent_position_id: Optional[str] = None
   
   @property
   def is_profitable(self) -> bool:
       return self.profit > 0.01
   
   @property
   def needs_recovery(self) -> bool:
       return self.profit < -5.0 and not self.is_recovery_position
   
   @property
   def age_minutes(self) -> int:
       if self.time_open:
           return int((datetime.now() - self.time_open).total_seconds() / 60)
       return 0
   
   @property
   def pips(self) -> float:
       """คำนวณ pips"""
       if self.open_price == 0:
           return 0.0
       
       pip_value = 0.1 if 'JPY' in self.symbol else 0.0001
       
       if self.type == "BUY":
           return (self.current_price - self.open_price) / pip_value
       else:
           return (self.open_price - self.current_price) / pip_value
   
   @property
   def hold_time_minutes(self) -> int:
       """เวลาถือครอง (นาที)"""
       return self.age_minutes
   
   @property
   def type_str(self) -> str:
       """ประเภท Position เป็น string"""
       return self.type
   
   @property
   def time_str(self) -> str:
       """เวลาเปิด Position เป็น string"""
       if isinstance(self.time_open, datetime):
           return self.time_open.strftime("%H:%M:%S")
       return "--:--:--"
   
   @property
   def status(self) -> str:
       """สถานะของ Position"""
       if self.needs_recovery:
           return "NEEDS_RECOVERY"
       elif self.is_recovery_position:
           return f"RECOVERY_L{self.recovery_level}"
       elif self.is_profitable:
           return "PROFITABLE"
       else:
           return "NORMAL"
   
   @property
   def pips_profit(self) -> float:
       """Alias สำหรับ pips"""
       return self.pips
   
   def to_dict(self) -> Dict[str, Any]:
       """แปลงเป็น Dictionary"""
       return {
           'ticket': self.ticket,
           'symbol': self.symbol,
           'type': self.type,
           'volume': self.volume,
           'open_price': self.open_price,
           'current_price': self.current_price,
           'profit': self.profit,
           'pips': self.pips,
           'status': self.status,
           'is_recovery': self.is_recovery_position,
           'recovery_level': self.recovery_level,
           'hold_time': self.hold_time_minutes,
           'time_open': self.time_open.isoformat() if self.time_open else None
       }

class EnhancedPositionTracker:
   """Enhanced Position Tracker - รองรับ Core Trading System"""
   
   def __init__(self):
       self.logger = setup_component_logger("EnhancedPositionTracker")
       
       # Configuration
       try:
           self.settings = get_system_settings()
           self.trading_params = get_trading_parameters()
           self.symbol = get_current_gold_symbol()
       except:
           self.settings = None
           self.trading_params = None
           self.symbol = "XAUUSD"
       
       # Position storage
       self.positions: Dict[int, Position] = {}
       self.position_history: deque = deque(maxlen=1000)
       
       # Tracking state
       self.tracking_active = False
       self.tracking_thread: Optional[threading.Thread] = None
       self.stop_event = threading.Event()
       self.last_update_time: Optional[datetime] = None
       
       # Threading
       self.tracker_lock = threading.Lock()
       self.update_interval = 2  # seconds
       
       # Callbacks
       self.position_callbacks: List[Callable] = []
       
       # Statistics
       self.total_positions_tracked = 0
       self.positions_needing_recovery = 0
       
       # Performance metrics
       self.portfolio_metrics = {
           'total_profit': 0.0,
           'total_volume': 0.0,
           'buy_volume': 0.0,
           'sell_volume': 0.0,
           'net_volume': 0.0,
           'position_count': 0,
           'profitable_count': 0,
           'losing_count': 0
       }
       
       self.logger.info(f"✅ Enhanced Position Tracker initialized for {self.symbol}")
   
   @handle_trading_errors(ErrorCategory.TRADING_LOGIC, ErrorSeverity.HIGH)
   def start_tracking(self) -> bool:
       """เริ่มการติดตาม Position"""
       if self.tracking_active:
           self.logger.warning("⚠️ Position tracking already active")
           return True
       
       try:
           if not ensure_mt5_connection():
               self.logger.error("❌ Cannot connect to MT5")
               return False
           
           self.tracking_active = True
           self.stop_event.clear()
           
           # เริ่ม tracking thread
           self.tracking_thread = threading.Thread(
               target=self._tracking_loop,
               name="PositionTrackingThread",
               daemon=True
           )
           self.tracking_thread.start()
           
           self.logger.info("🚀 Position tracking started")
           return True
           
       except Exception as e:
           self.tracking_active = False
           self.logger.error(f"❌ Failed to start position tracking: {e}")
           return False
   
   def stop_tracking(self) -> bool:
       """หยุดการติดตาม Position"""
       try:
           self.stop_event.set()
           self.tracking_active = False
           
           if self.tracking_thread and self.tracking_thread.is_alive():
               self.tracking_thread.join(timeout=5.0)
           
           self.logger.info("⏹️ Position tracking stopped")
           return True
           
       except Exception as e:
           self.logger.error(f"❌ Failed to stop position tracking: {e}")
           return False
   
   def _tracking_loop(self):
       """Loop หลักสำหรับติดตาม Position"""
       self.logger.info("🔄 Position tracking loop started")
       
       while not self.stop_event.is_set():
           try:
               # อัปเดต positions จาก MT5
               self._update_positions_from_mt5()
               
               # ตรวจสอบการเปลี่ยนแปลง
               self._detect_position_changes()
               
               # คำนวณเมทริก
               self._calculate_portfolio_metrics()
               
               # แจ้ง callbacks
               self._notify_position_callbacks()
               
               # อัปเดตเวลา
               self.last_update_time = datetime.now()
               
               time.sleep(self.update_interval)
               
           except Exception as e:
               self.logger.error(f"❌ Error in position tracking loop: {e}")
               time.sleep(5)
   
   @handle_trading_errors(ErrorCategory.MARKET_DATA, ErrorSeverity.MEDIUM)
   def _update_positions_from_mt5(self):
       """อัปเดต Positions จาก MT5"""
       try:
           # ดึง positions จาก MT5
           mt5_positions = mt5.positions_get(symbol=self.symbol)
           
           if mt5_positions is None:
               mt5_positions = []
           
           current_tickets = set()
           
           # อัปเดต/เพิ่ม positions
           for mt5_pos in mt5_positions:
               ticket = mt5_pos.ticket
               current_tickets.add(ticket)
               
               # แปลงจาก MT5 position เป็น Position object
               position = self._convert_mt5_position(mt5_pos)
               
               with self.tracker_lock:
                   if ticket not in self.positions:
                       # Position ใหม่
                       self.positions[ticket] = position
                       self.total_positions_tracked += 1
                       self.logger.info(f"📈 New position: {ticket} {position.type} {position.volume}")
                   else:
                       # อัปเดต position ที่มีอยู่
                       self.positions[ticket] = position
           
           # ลบ positions ที่ปิดไปแล้ว
           with self.tracker_lock:
               closed_tickets = set(self.positions.keys()) - current_tickets
               for ticket in closed_tickets:
                   closed_position = self.positions[ticket]
                   self.position_history.append(closed_position)
                   del self.positions[ticket]
                   self.logger.info(f"📉 Position closed: {ticket} Profit: {closed_position.profit:.2f}")
           
       except Exception as e:
           self.logger.error(f"❌ Failed to update positions from MT5: {e}")
   
   def _convert_mt5_position(self, mt5_pos) -> Position:
       """แปลง MT5 Position เป็น Position object"""
       try:
           pos_type = "BUY" if mt5_pos.type == mt5.POSITION_TYPE_BUY else "SELL"
           
           return Position(
               ticket=mt5_pos.ticket,
               symbol=mt5_pos.symbol,
               type=pos_type,
               volume=mt5_pos.volume,
               open_price=mt5_pos.price_open,
               current_price=mt5_pos.price_current,
               profit=mt5_pos.profit,
               time_open=datetime.fromtimestamp(mt5_pos.time),
               magic=mt5_pos.magic,
               comment=mt5_pos.comment or "",
               swap=mt5_pos.swap,
               commission=getattr(mt5_pos, 'commission', 0.0)
           )
       except Exception as e:
           self.logger.error(f"❌ Failed to convert MT5 position: {e}")
           # Return minimal position
           return Position(
               ticket=getattr(mt5_pos, 'ticket', 0),
               symbol=getattr(mt5_pos, 'symbol', self.symbol),
               type="BUY",
               volume=getattr(mt5_pos, 'volume', 0.0),
               open_price=getattr(mt5_pos, 'price_open', 0.0),
               current_price=getattr(mt5_pos, 'price_current', 0.0),
               profit=getattr(mt5_pos, 'profit', 0.0),
               time_open=datetime.now()
           )
   
   def _detect_position_changes(self):
       """ตรวจสอบการเปลี่ยนแปลงของ Position"""
       try:
           recovery_count = 0
           
           with self.tracker_lock:
               for position in self.positions.values():
                   if position.needs_recovery:
                       recovery_count += 1
           
           self.positions_needing_recovery = recovery_count
           
       except Exception as e:
           self.logger.error(f"❌ Failed to detect position changes: {e}")
   
   def _calculate_portfolio_metrics(self):
       """คำนวณเมทริกของ Portfolio"""
       try:
           with self.tracker_lock:
               positions = list(self.positions.values())
               
               if not positions:
                   # รีเซ็ตเมทริก
                   self.portfolio_metrics = {
                       'total_profit': 0.0,
                       'total_volume': 0.0,
                       'buy_volume': 0.0,
                       'sell_volume': 0.0,
                       'net_volume': 0.0,
                       'position_count': 0,
                       'profitable_count': 0,
                       'losing_count': 0
                   }
                   return
               
               # คำนวณเมทริก
               total_profit = sum(pos.profit for pos in positions)
               total_volume = sum(pos.volume for pos in positions)
               buy_volume = sum(pos.volume for pos in positions if pos.type == "BUY")
               sell_volume = sum(pos.volume for pos in positions if pos.type == "SELL")
               profitable_count = len([pos for pos in positions if pos.is_profitable])
               losing_count = len([pos for pos in positions if not pos.is_profitable])
               
               self.portfolio_metrics = {
                   'total_profit': total_profit,
                   'total_volume': total_volume,
                   'buy_volume': buy_volume,
                   'sell_volume': sell_volume,
                   'net_volume': buy_volume - sell_volume,
                   'position_count': len(positions),
                   'profitable_count': profitable_count,
                   'losing_count': losing_count
               }
               
       except Exception as e:
           self.logger.error(f"❌ Failed to calculate portfolio metrics: {e}")
   
   def _notify_position_callbacks(self):
       """แจ้ง Position Callbacks"""
       if not self.position_callbacks:
           return
       
       try:
           position_data = {
               'positions': self.get_all_positions(),
               'metrics': self.portfolio_metrics.copy(),
               'timestamp': datetime.now(),
               'positions_needing_recovery': self.positions_needing_recovery
           }
           
           for callback in self.position_callbacks:
               try:
                   callback(position_data)
               except Exception as e:
                   self.logger.error(f"❌ Error in position callback: {e}")
                   
       except Exception as e:
           self.logger.error(f"❌ Failed to notify position callbacks: {e}")
   
   # ===== PUBLIC METHODS =====
   
   def get_all_positions(self) -> List[Position]:
       """ดึง Positions ทั้งหมด"""
       with self.tracker_lock:
           return list(self.positions.values())
   
   def get_positions_needing_recovery(self) -> List[Position]:
       """ดึง Positions ที่ต้อง Recovery"""
       with self.tracker_lock:
           return [pos for pos in self.positions.values() if pos.needs_recovery]
   
   def get_position_by_ticket(self, ticket: int) -> Optional[Position]:
       """ดึง Position ตาม Ticket"""
       with self.tracker_lock:
           return self.positions.get(ticket)
   
   def get_positions_by_type(self, position_type: str) -> List[Position]:
       """ดึง Positions ตามประเภท (BUY/SELL)"""
       with self.tracker_lock:
           return [pos for pos in self.positions.values() if pos.type == position_type]
   
   def get_portfolio_summary(self) -> Dict[str, Any]:
       """ดึงสรุป Portfolio"""
       with self.tracker_lock:
           summary = self.portfolio_metrics.copy()
           summary.update({
               'positions_needing_recovery': self.positions_needing_recovery,
               'last_update': self.last_update_time.isoformat() if self.last_update_time else None,
               'tracking_active': self.tracking_active,
               'symbol': self.symbol
           })
           return summary
   
   def get_position_statistics(self) -> Dict[str, Any]:
       """ดึงสถิติ Position"""
       return {
           'total_tracked': self.total_positions_tracked,
           'current_open': len(self.positions),
           'positions_needing_recovery': self.positions_needing_recovery,
           'portfolio_metrics': self.portfolio_metrics.copy()
       }
   
   def add_position_callback(self, callback: Callable):
       """เพิ่ม Callback สำหรับ Position Updates"""
       self.position_callbacks.append(callback)
   
   def remove_position_callback(self, callback: Callable):
       """ลบ Callback"""
       if callback in self.position_callbacks:
           self.position_callbacks.remove(callback)
   
   def force_update(self):
       """บังคับอัปเดต Position ทันที"""
       try:
           self._update_positions_from_mt5()
           self._detect_position_changes()
           self._calculate_portfolio_metrics()
           self.logger.info("🔄 Force updated position data")
       except Exception as e:
           self.logger.error(f"❌ Failed to force update: {e}")
   
   def get_status(self) -> Dict[str, Any]:
       """ดึงสถานะของ Position Tracker"""
       return {
           'active': self.tracking_active,
           'symbol': self.symbol,
           'position_count': len(self.positions),
           'callbacks_count': len(self.position_callbacks),
           'last_update': self.last_update_time
       }

# ===== COMPATIBILITY ALIASES =====

# Legacy class names
PositionData = Position
PositionInfo = Position
TradePosition = Position

class PositionTracker(EnhancedPositionTracker):
   """Legacy PositionTracker class สำหรับ backward compatibility"""
   
   def __init__(self):
       super().__init__()
       self.logger.info("📊 Using Legacy PositionTracker interface")
   
   def get_positions(self) -> List[Position]:
       """Legacy method name"""
       return self.get_all_positions()
   
   def get_position_count(self) -> int:
       """Legacy method"""
       return len(self.positions)
   
   def is_tracking(self) -> bool:
       """Legacy method"""
       return self.tracking_active

# ===== FACTORY FUNCTIONS - ครบถ้วนทุกตัว =====

def get_enhanced_position_tracker() -> EnhancedPositionTracker:
   """Factory function สำหรับสร้าง Enhanced Position Tracker"""
   return EnhancedPositionTracker()

def get_position_tracker() -> EnhancedPositionTracker:
   """Factory function หลัก"""
   return EnhancedPositionTracker()

def create_position_tracker() -> EnhancedPositionTracker:
   """Legacy creation function"""
   return EnhancedPositionTracker()

def get_tracker() -> EnhancedPositionTracker:
   """Legacy function name"""
   return EnhancedPositionTracker()

# ===== GLOBAL INSTANCE =====

_global_position_tracker = None

def get_global_position_tracker() -> EnhancedPositionTracker:
   """ดึง Global Position Tracker"""
   global _global_position_tracker
   if _global_position_tracker is None:
       _global_position_tracker = EnhancedPositionTracker()
   return _global_position_tracker

# ===== UTILITY FUNCTIONS =====

def get_current_positions() -> List[Dict[str, Any]]:
   """ดึงรายการ Position ปัจจุบัน"""
   tracker = get_global_position_tracker()
   positions = tracker.get_all_positions()
   return [pos.to_dict() for pos in positions]

def get_positions_summary() -> Dict[str, Any]:
   """ดึงสรุป Positions"""
   tracker = get_global_position_tracker()
   return tracker.get_portfolio_summary()

def check_positions_needing_recovery() -> List[int]:
   """ตรวจสอบ Positions ที่ต้องการ Recovery"""
   tracker = get_global_position_tracker()
   recovery_positions = tracker.get_positions_needing_recovery()
   return [pos.ticket for pos in recovery_positions]

def start_position_tracking() -> bool:
   """เริ่มการติดตาม Positions"""
   tracker = get_global_position_tracker()
   return tracker.start_tracking()

def stop_position_tracking():
   """หยุดการติดตาม Positions"""
   tracker = get_global_position_tracker()
   tracker.stop_tracking()

# ===== EXPORT LIST - ครบถ้วน =====

__all__ = [
   # Classes
   'Position', 'PositionData', 'PositionInfo', 'TradePosition',
   'EnhancedPositionTracker', 'PositionTracker',
   
   # Factory functions - ครบทุกตัว
   'get_enhanced_position_tracker', 'get_position_tracker', 'get_global_position_tracker',
   'create_position_tracker', 'get_tracker',
   
   # Utility functions
   'get_current_positions', 'get_positions_summary', 'check_positions_needing_recovery',
   'start_position_tracking', 'stop_position_tracking'
]

# ===== TESTING =====

if __name__ == "__main__":
   print("🧪 ทดสอบ Enhanced Position Tracker")
   print("=" * 50)
   
   try:
       # ทดสอบทุก factory functions
       tracker1 = get_enhanced_position_tracker()
       print("✅ get_enhanced_position_tracker() ทำงาน")
       
       tracker2 = get_position_tracker()
       print("✅ get_position_tracker() ทำงาน")
       
       tracker3 = get_global_position_tracker()
       print("✅ get_global_position_tracker() ทำงาน")
       
       tracker4 = create_position_tracker()
       print("✅ create_position_tracker() ทำงาน")
       
       tracker5 = get_tracker()
       print("✅ get_tracker() ทำงาน")
       
       # แสดงสถานะ
       status = tracker1.get_status()
       print(f"📊 Status: {status}")
       
       print("\n🎯 Enhanced Position Tracker พร้อมใช้งาน!")
       print("✅ ทุก Factory Functions ทำงานได้แล้ว")
       
       # ทดสอบ import
       print("\n🔍 ทดสอบ import functions:")
       from position_management.position_tracker import get_enhanced_position_tracker
       print("✅ import get_enhanced_position_tracker สำเร็จ")
       
   except Exception as e:
       print(f"❌ ข้อผิดพลาด: {e}")
       import traceback
       traceback.print_exc()