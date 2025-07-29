#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSITION TRACKER - Enhanced Position Tracking System
=================================================
ระบบติดตาม Position ที่ปรับปรุงให้รองรับระบบใหม่
เพิ่ม methods ที่จำเป็นสำหรับ Core Trading System

🔄 การปรับปรุง:
- เพิ่ม get_all_positions() method
- เพิ่ม get_positions_needing_recovery() method
- ปรับ interface ให้ตรงกับ IntelligentTradingSystem
- รองรับ Recovery System integration
- เพิ่ม Real-time position monitoring
- เพิ่ม Compatibility aliases
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

# Internal imports - ปรับให้ตรงกับโครงสร้างเดิม
try:
    from config.settings import get_system_settings
    from config.trading_params import get_trading_parameters
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
        if not mt5.initialize():
            return False
        return True
    
    def get_system_settings():
        return None
    
    def get_trading_parameters():
        return None
    
    class ErrorCategory:
        SYSTEM = "SYSTEM"
        TRADING_LOGIC = "TRADING_LOGIC"
        MARKET_DATA = "MARKET_DATA"
        RECOVERY = "RECOVERY"
    
    class ErrorSeverity:
        LOW = "LOW"
        MEDIUM = "MEDIUM"
        HIGH = "HIGH"
        CRITICAL = "CRITICAL"

@dataclass
class PositionData:
    """ข้อมูล Position ที่ปรับปรุงแล้ว"""
    ticket: str
    symbol: str = "XAUUSD.v"
    type: str = "BUY"  # BUY or SELL
    volume: float = 0.01
    price_open: float = 0.0
    price_current: float = 0.0
    profit: float = 0.0
    swap: float = 0.0
    commission: float = 0.0
    time_open: datetime = field(default_factory=datetime.now)
    comment: str = ""
    
    # Recovery Related
    recovery_group: Optional[str] = None
    recovery_level: int = 0
    is_recovery_position: bool = False
    needs_recovery: bool = False
    
    # Performance Metrics
    unrealized_pnl: float = 0.0
    pips: float = 0.0
    hold_time_minutes: int = 0
    max_profit: float = 0.0
    max_loss: float = 0.0
    
    def __post_init__(self):
        """คำนวณข้อมูลเพิ่มเติมหลังจากสร้าง object"""
        self.unrealized_pnl = self.profit + self.swap + self.commission
        self.pips = self._calculate_pips()
        self.hold_time_minutes = self._calculate_hold_time_minutes()
        self.needs_recovery = self.profit < -5.0  # ขาดทุนเกิน $5
    
    def _calculate_pips(self) -> float:
        """คำนวณ Pips"""
        if self.price_open == 0:
            return 0.0
        
        pip_value = 0.1 if 'JPY' in self.symbol else 0.0001
        if self.type == "BUY":
            return (self.price_current - self.price_open) / pip_value
        else:
            return (self.price_open - self.price_current) / pip_value
    
    def _calculate_hold_time_minutes(self) -> int:
        """คำนวณเวลาที่ถือ Position"""
        if isinstance(self.time_open, datetime):
            duration = datetime.now() - self.time_open
            return int(duration.total_seconds() / 60)
        return 0
    
    @property
    def is_open(self) -> bool:
        """ตรวจสอบว่า Position ยังเปิดอยู่หรือไม่"""
        return True  # สำหรับ Position ที่ Track อยู่ควรจะเปิดอยู่
    
    @property
    def is_profitable(self) -> bool:
        """ตรวจสอบว่ากำไรหรือไม่"""
        return self.unrealized_pnl > 0
    
    @property
    def is_losing(self) -> bool:
        """ตรวจสอบว่าขาดทุนหรือไม่"""
        return self.profit < -0.01
    
    @property
    def age_minutes(self) -> int:
        """อายุของ Position เป็นนาที - alias สำหรับ hold_time_minutes"""
        return self.hold_time_minutes
    
    @property
    def type_str(self) -> str:
        """แปลง type เป็น string"""
        return self.type
    
    @property
    def time_str(self) -> str:
        """แปลงเวลาเป็น string"""
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
        """Alias สำหรับ pips (compatibility)"""
        return self.pips
    
    def to_dict(self) -> Dict[str, Any]:
        """แปลงเป็น Dictionary"""
        return {
            'ticket': self.ticket,
            'symbol': self.symbol,
            'type': self.type,
            'volume': self.volume,
            'price_open': self.price_open,
            'price_current': self.price_current,
            'profit': self.profit,
            'pips': self.pips,
            'status': self.status,
            'is_recovery': self.is_recovery_position,
            'recovery_level': self.recovery_level,
            'hold_time': self.hold_time_minutes
        }

class EnhancedPositionTracker:
    """
    📊 Enhanced Position Tracker - ระบบติดตาม Position ที่ปรับปรุงแล้ว
    
    รองรับการทำงานกับ Core Trading System ใหม่
    """
    
    def __init__(self):
        self.logger = setup_component_logger("EnhancedPositionTracker")
        
        # Configuration
        try:
            self.settings = get_system_settings()
            self.trading_params = get_trading_parameters()
        except:
            self.settings = None
            self.trading_params = None
        
        # Position Storage
        self.positions: Dict[str, PositionData] = {}
        self.position_history: List[PositionData] = []
        
        # Tracking State
        self.tracking_active = False
        self.tracking_thread: Optional[threading.Thread] = None
        self.last_update_time: Optional[datetime] = None
        
        # Threading
        self.tracker_lock = threading.Lock()
        self.update_interval = 2  # seconds
        
        # Callbacks
        self.position_callbacks: List[Callable] = []
        self.recovery_callbacks: List[Callable] = []
        
        # Statistics
        self.total_positions_tracked = 0
        self.positions_needing_recovery = 0
        
        self.logger.info("📊 เริ่มต้น Enhanced Position Tracker")
    
    def start_tracking(self) -> bool:
        """🚀 เริ่มการติดตาม positions"""
        if self.tracking_active:
            return True
        
        try:
            if not ensure_mt5_connection():
                self.logger.error("❌ ไม่สามารถเชื่อมต่อ MT5")
                return False
            
            self.tracking_active = True
            self.tracking_thread = threading.Thread(
                target=self._tracking_loop,
                daemon=True,
                name="PositionTracker"
            )
            self.tracking_thread.start()
            
            self.logger.info("🚀 เริ่มติดตาม Positions แบบเรียลไทม์")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเริ่มติดตาม: {e}")
            return False
    
    def stop_tracking(self):
        """🛑 หยุดการติดตาม positions"""
        self.tracking_active = False
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=5.0)
        
        self.logger.info("🛑 หยุดติดตาม Positions")
    
    @handle_trading_errors(ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM)
    def _tracking_loop(self):
        """🔄 ลูปหลักสำหรับติดตาม positions"""
        
        while self.tracking_active:
            try:
                # อัพเดทข้อมูล positions
                self._update_positions_from_mt5()
                
                # ตรวจสอบการเปลี่ยนแปลง
                self._detect_position_changes()
                
                # คำนวณ metrics
                self._calculate_portfolio_metrics()
                
                # เรียก callbacks
                self._notify_callbacks()
                
                # อัพเดทเวลา
                self.last_update_time = datetime.now()
                
                # รอก่อนรอบถัดไป
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน tracking loop: {e}")
                time.sleep(5.0)
    
    def _update_positions_from_mt5(self):
        """📈 อัพเดทข้อมูล positions จาก MT5"""
        
        if not ensure_mt5_connection():
            return
        
        try:
            # ดึง positions ทั้งหมดจาก MT5
            mt5_positions = mt5.positions_get()
            if mt5_positions is None:
                mt5_positions = []
            
            current_tickets = set()
            
            with self.tracker_lock:
                # อัพเดท positions ที่มีอยู่
                for mt5_pos in mt5_positions:
                    ticket = str(mt5_pos.ticket)
                    current_tickets.add(ticket)
                    
                    # ดึงราคาปัจจุบัน
                    symbol_info = mt5.symbol_info_tick(mt5_pos.symbol)
                    current_price = 0.0
                    if symbol_info:
                        if mt5_pos.type == mt5.ORDER_TYPE_BUY:
                            current_price = symbol_info.bid
                        else:
                            current_price = symbol_info.ask
                    
                    # สร้างหรืออัพเดท Position
                    if ticket in self.positions:
                        # อัพเดท position ที่มีอยู่
                        pos = self.positions[ticket]
                        pos.price_current = current_price
                        pos.profit = mt5_pos.profit
                        pos.swap = mt5_pos.swap
                        pos.commission = mt5_pos.commission
                        pos.unrealized_pnl = pos.profit + pos.swap + pos.commission
                        pos.pips = pos._calculate_pips()
                        pos.hold_time_minutes = pos._calculate_hold_time_minutes()
                        pos.needs_recovery = pos.profit < -5.0
                        
                        # อัพเดท max profit/loss
                        if pos.profit > pos.max_profit:
                            pos.max_profit = pos.profit
                        if pos.profit < pos.max_loss:
                            pos.max_loss = pos.profit
                    else:
                        # สร้าง position ใหม่
                        position_data = PositionData(
                            ticket=ticket,
                            symbol=mt5_pos.symbol,
                            type="BUY" if mt5_pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                            volume=mt5_pos.volume,
                            price_open=mt5_pos.price_open,
                            price_current=current_price,
                            profit=mt5_pos.profit,
                            swap=mt5_pos.swap,
                            commission=mt5_pos.commission,
                            time_open=datetime.fromtimestamp(mt5_pos.time),
                            comment=mt5_pos.comment
                        )
                        
                        self.positions[ticket] = position_data
                        self.total_positions_tracked += 1
                        
                        self.logger.info(f"📈 New Position: {ticket} {position_data.type} {position_data.volume}")
                
                # ลบ positions ที่ปิดแล้ว
                closed_tickets = set(self.positions.keys()) - current_tickets
                for ticket in closed_tickets:
                    closed_pos = self.positions.pop(ticket)
                    self.position_history.append(closed_pos)
                    self.logger.info(f"📉 Position Closed: {ticket} P&L: ${closed_pos.profit:.2f}")
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท positions: {e}")
    
    def _detect_position_changes(self):
        """🔍 ตรวจสอบการเปลี่ยนแปลงของ positions"""
        # ตรวจสอบ positions ที่ต้องการ recovery
        recovery_needed = 0
        for position in self.positions.values():
            if position.needs_recovery and not position.is_recovery_position:
                recovery_needed += 1
        
        self.positions_needing_recovery = recovery_needed
    
    def _calculate_portfolio_metrics(self):
        """📊 คำนวณ metrics ของ portfolio"""
        # คำนวณข้อมูลรวม - เพิ่มเติมในอนาคต
        pass
    
    def _notify_callbacks(self):
        """📞 เรียก callbacks"""
        try:
            for callback in self.position_callbacks:
                callback(list(self.positions.values()))
        except Exception as e:
            self.logger.error(f"❌ Callback Error: {e}")
    
    # === PUBLIC METHODS สำหรับ Core Trading System ===
    
    def get_all_positions(self) -> List[PositionData]:
        """📋 ดึง Position ทั้งหมด (สำหรับ Core Trading System)"""
        with self.tracker_lock:
            return list(self.positions.values())
    
    def get_positions_needing_recovery(self) -> List[PositionData]:
        """🔄 ดึง Positions ที่ต้องการ Recovery"""
        with self.tracker_lock:
            return [pos for pos in self.positions.values() 
                   if pos.needs_recovery and not pos.is_recovery_position]
    
    def get_position_by_ticket(self, ticket: str) -> Optional[PositionData]:
        """🎫 ดึง Position ตาม Ticket"""
        with self.tracker_lock:
            return self.positions.get(ticket)
    
    def get_positions_by_symbol(self, symbol: str = "XAUUSD.v") -> List[PositionData]:
        """📊 ดึง Positions ตาม Symbol"""
        with self.tracker_lock:
            return [pos for pos in self.positions.values() if pos.symbol == symbol]
    
    def get_profitable_positions(self) -> List[PositionData]:
        """💰 ดึง Positions ที่กำไร"""
        with self.tracker_lock:
            return [pos for pos in self.positions.values() if pos.is_profitable]
    
    def get_losing_positions(self) -> List[PositionData]:
        """📉 ดึง Positions ที่ขาดทุน"""
        with self.tracker_lock:
            return [pos for pos in self.positions.values() if not pos.is_profitable]
    
    def get_recovery_positions(self) -> List[PositionData]:
        """🔄 ดึง Recovery Positions"""
        with self.tracker_lock:
            return [pos for pos in self.positions.values() if pos.is_recovery_position]
    
    def mark_position_for_recovery(self, ticket: str, recovery_group: str = None) -> bool:
        """🏷️ ทำเครื่องหมาย Position สำหรับ Recovery"""
        with self.tracker_lock:
            if ticket in self.positions:
                position = self.positions[ticket]
                position.recovery_group = recovery_group or f"REC_{ticket}"
                self.logger.info(f"🏷️ Marked for recovery: {ticket}")
                return True
            return False
    
    def add_recovery_position(self, original_ticket: str, recovery_ticket: str, 
                            recovery_level: int = 1) -> bool:
        """➕ เพิ่ม Recovery Position"""
        with self.tracker_lock:
            if recovery_ticket in self.positions:
                recovery_pos = self.positions[recovery_ticket]
                recovery_pos.is_recovery_position = True
                recovery_pos.recovery_level = recovery_level
                
                # เชื่อมโยงกับ original position
                if original_ticket in self.positions:
                    original_pos = self.positions[original_ticket]
                    recovery_pos.recovery_group = original_pos.recovery_group
                
                self.logger.info(f"➕ Added recovery position: {recovery_ticket} Level {recovery_level}")
                return True
            return False
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """📊 ดึงสรุป Portfolio"""
        with self.tracker_lock:
            positions = list(self.positions.values())
            
            if not positions:
                return {
                    'total_positions': 0,
                    'total_profit': 0.0,
                    'total_volume': 0.0,
                    'profitable_positions': 0,
                    'losing_positions': 0,
                    'recovery_positions': 0,
                    'positions_needing_recovery': 0
                }
            
            return {
                'total_positions': len(positions),
                'total_profit': sum(pos.profit for pos in positions),
                'total_volume': sum(pos.volume for pos in positions),
                'profitable_positions': len([p for p in positions if p.is_profitable]),
                'losing_positions': len([p for p in positions if not p.is_profitable]),
                'recovery_positions': len([p for p in positions if p.is_recovery_position]),
                'positions_needing_recovery': len([p for p in positions if p.needs_recovery and not p.is_recovery_position]),
                'avg_profit_per_position': sum(pos.profit for pos in positions) / len(positions),
                'max_profit_position': max(positions, key=lambda p: p.profit).profit if positions else 0,
                'max_loss_position': min(positions, key=lambda p: p.profit).profit if positions else 0,
                'total_pips': sum(pos.pips for pos in positions),
                'last_update': self.last_update_time.isoformat() if self.last_update_time else None
            }
    
    def register_position_callback(self, callback: Callable):
        """📞 ลงทะเบียน Callback สำหรับ Position Updates"""
        self.position_callbacks.append(callback)
    
    def register_recovery_callback(self, callback: Callable):
        """📞 ลงทะเบียน Callback สำหรับ Recovery Events"""
        self.recovery_callbacks.append(callback)
    
    def force_update(self):
        """🔄 บังคับอัพเดทข้อมูล"""
        self._update_positions_from_mt5()
        self._detect_position_changes()
        self._calculate_portfolio_metrics()
        
        self.logger.info("🔄 Force updated position data")
    
    def get_tracking_status(self) -> Dict[str, Any]:
        """📊 ดึงสถานะการติดตาม"""
        return {
            'tracking_active': self.tracking_active,
            'total_positions': len(self.positions),
            'positions_needing_recovery': self.positions_needing_recovery,
            'last_update': self.last_update_time.isoformat() if self.last_update_time else None,
            'total_tracked': self.total_positions_tracked,
            'update_interval': self.update_interval
        }


# === COMPATIBILITY CLASSES (สำหรับไฟล์เดิม) ===

class PositionTracker(EnhancedPositionTracker):
    """Legacy PositionTracker class สำหรับ backward compatibility"""
    
    def __init__(self):
        super().__init__()
        self.logger.info("📊 Using Legacy PositionTracker interface")
    
    def get_positions(self) -> List[PositionData]:
        """Legacy method name"""
        return self.get_all_positions()
    
    def get_position_count(self) -> int:
        """Legacy method"""
        return len(self.positions)
    
    def is_tracking(self) -> bool:
        """Legacy method"""
        return self.tracking_active


# === SINGLETON PATTERN ===

_position_tracker_instance = None

def get_position_tracker() -> EnhancedPositionTracker:
    """Get Position Tracker Singleton Instance"""
    global _position_tracker_instance
    if _position_tracker_instance is None:
        _position_tracker_instance = EnhancedPositionTracker()
    return _position_tracker_instance


# === COMPATIBILITY ALIASES ===
# สำหรับ backward compatibility กับไฟล์เดิม

Position = PositionData  # Alias หลักสำหรับ recovery_selector.py และไฟล์อื่นๆ

# Additional aliases
PositionInfo = PositionData
TradePosition = PositionData

# Legacy function aliases
def get_tracker():
    """Legacy function name"""
    return get_position_tracker()

def create_position_tracker():
    """Legacy creation function"""
    return EnhancedPositionTracker()


# === UTILITY FUNCTIONS ===

def get_current_positions() -> List[Dict[str, Any]]:
    """ดึงรายการ Position ปัจจุบัน"""
    tracker = get_position_tracker()
    positions = tracker.get_all_positions()
    
    return [pos.to_dict() for pos in positions]

def get_positions_summary() -> Dict[str, Any]:
    """ดึงสรุป Positions"""
    tracker = get_position_tracker()
    return tracker.get_portfolio_summary()

def check_positions_needing_recovery() -> List[str]:
    """ตรวจสอบ Positions ที่ต้องการ Recovery"""
    tracker = get_position_tracker()
    recovery_positions = tracker.get_positions_needing_recovery()
    return [pos.ticket for pos in recovery_positions]

def start_position_tracking() -> bool:
    """เริ่มการติดตาม Positions"""
    tracker = get_position_tracker()
    return tracker.start_tracking()

def stop_position_tracking():
    """หยุดการติดตาม Positions"""
    tracker = get_position_tracker()
    tracker.stop_tracking()


# === EXPORT LIST ===
__all__ = [
    'PositionData', 'Position', 'PositionInfo', 'TradePosition',  # Classes
    'EnhancedPositionTracker', 'PositionTracker',  # Tracker classes
    'get_position_tracker', 'get_tracker', 'create_position_tracker',  # Factory functions
    'get_current_positions', 'get_positions_summary', 'check_positions_needing_recovery',  # Utility functions
    'start_position_tracking', 'stop_position_tracking'  # Control functions
]


# === TESTING FUNCTION ===
def test_position_tracker():
    """ทดสอบ Position Tracker"""
    print("🧪 Testing Enhanced Position Tracker")
    print("=" * 50)
    
    tracker = get_position_tracker()
    
    # Test MT5 connection
    if not ensure_mt5_connection():
        print("❌ Cannot connect to MT5")
        return False
    
    print("✅ MT5 Connected")
    
    # Start tracking
    if tracker.start_tracking():
        print("✅ Position tracking started")
    else:
        print("❌ Failed to start tracking")
        return False
    
    # Wait and check positions
    time.sleep(3)
    
    positions = tracker.get_all_positions()
    print(f"📊 Found {len(positions)} positions")
    
    for pos in positions:
        print(f"   {pos.ticket}: {pos.type} {pos.volume} {pos.symbol} | P&L: ${pos.profit:.2f}")
    
    # Test summary
    summary = tracker.get_portfolio_summary()
    print(f"\n📈 Portfolio Summary:")
    print(f"   Total Positions: {summary['total_positions']}")
    print(f"   Total P&L: ${summary['total_profit']:.2f}")
    print(f"   Positions Needing Recovery: {summary['positions_needing_recovery']}")
    
    # Stop tracking
    tracker.stop_tracking()
    print("🛑 Position tracking stopped")
    
    return True


if __name__ == "__main__":
    test_position_tracker()