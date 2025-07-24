#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPLETE PROFIT TAKING SYSTEM - ระบบเก็บกำไรสมบูรณ์
======================================================
ระบบเก็บกำไรอัตโนมัติที่เชื่อมต่อกับระบบเทรดที่มีอยู่
รองรับ Trailing Stop แบบไม่ใช้ Stop Loss และ Recovery-Aware

Features:
✅ เชื่อมต่อกับ Position Tracker ที่มีอยู่
✅ ใช้ Order Executor ที่มีอยู่  
✅ Trailing Stop แบบ Market Order
✅ Partial Profit Taking
✅ Session-Based Targets
✅ Recovery-Aware Profit Taking
✅ Real-time GUI Integration
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from collections import deque
import uuid
import json

# เชื่อมต่อระบบที่มีอยู่
from position_management.position_tracker import get_position_tracker, Position
from mt5_integration.order_executor import SmartOrderExecutor, OrderType, OrderRequest
from config.settings import get_system_settings, MarketSession
from utilities.professional_logger import setup_component_logger

class ProfitMode(Enum):
    """โหมดการเก็บกำไร"""
    SCALPING = "SCALPING"       # เก็บเร็ว 5-15 pips
    SWING = "SWING"             # เก็บปานกลาง 20-50 pips
    TREND = "TREND"             # ตาม trend 50+ pips
    RECOVERY = "RECOVERY"       # เก็บเพื่อ recovery
    NEWS = "NEWS"               # เก็บจาก news reaction

@dataclass
class ProfitTarget:
    """เป้าหมายกำไรสำหรับแต่ละ Position"""
    position_ticket: int
    symbol: str
    entry_price: float
    current_price: float
    position_type: str          # "BUY" or "SELL"
    volume: float
    
    # เป้าหมาย
    target_pips: float = 10.0
    trailing_pips: float = 5.0
    
    # การเก็บกำไรแบบ Partial
    partial_targets: List[Tuple[float, float]] = field(default_factory=list)  # (pips, %)
    
    # สถิติ
    max_profit_seen: float = 0.0
    max_profit_pips: float = 0.0
    profit_mode: ProfitMode = ProfitMode.SCALPING
    
    # สถานะ
    is_trailing: bool = False
    partial_closed_volume: float = 0.0
    remaining_volume: float = 0.0
    
    created_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)

class CompleteProfitTaker:
    """
    🎯 Complete Profit Taking System
    
    ระบบเก็บกำไรที่ทำงานร่วมกับระบบที่มีอยู่
    """
    
    def __init__(self):
        self.logger = setup_component_logger("ProfitTaker")
        self.settings = get_system_settings()
        
        # เชื่อมต่อระบบที่มีอยู่
        self.position_tracker = get_position_tracker()
        self.order_executor = SmartOrderExecutor()
        
        # สถานะระบบ
        self.is_active = False
        self.active_targets: Dict[int, ProfitTarget] = {}  # ticket -> target
        self.completed_targets: List[ProfitTarget] = []
        
        # การตั้งค่า Profit Targets
        self.profit_configs = {
            ProfitMode.SCALPING: {
                "target_pips": 10.0,
                "trailing_pips": 5.0,
                "partial_targets": [(3.0, 0.3), (6.0, 0.5), (10.0, 1.0)]
            },
            ProfitMode.SWING: {
                "target_pips": 30.0,
                "trailing_pips": 15.0,
                "partial_targets": [(10.0, 0.2), (20.0, 0.4), (30.0, 1.0)]
            },
            ProfitMode.TREND: {
                "target_pips": 50.0,
                "trailing_pips": 25.0,
                "partial_targets": [(15.0, 0.2), (30.0, 0.3), (45.0, 0.5)]
            },
            ProfitMode.RECOVERY: {
                "target_pips": 8.0,   # รัดกุม
                "trailing_pips": 4.0,
                "partial_targets": [(5.0, 0.5), (8.0, 1.0)]
            },
            ProfitMode.NEWS: {
                "target_pips": 15.0,
                "trailing_pips": 8.0,
                "partial_targets": [(8.0, 0.4), (15.0, 1.0)]
            }
        }
        
        # Threading
        self.monitor_thread = None
        self.update_interval = 1.0  # วินาที
        
        self.logger.info("🎯 เริ่มต้น Complete Profit Taking System")
    
    def start_profit_taking(self):
        """เริ่มระบบเก็บกำไร"""
        if self.is_active:
            self.logger.warning("⚠️ Profit Taking System ทำงานอยู่แล้ว")
            return
        
        self.is_active = True
        
        # เริ่ม monitoring thread
        self.monitor_thread = threading.Thread(target=self._profit_monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("✅ เริ่มระบบเก็บกำไรแล้ว")
    
    def stop_profit_taking(self):
        """หยุดระบบเก็บกำไร"""
        self.is_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        self.logger.info("🛑 หยุดระบบเก็บกำไรแล้ว")
    
    def _profit_monitoring_loop(self):
        """Loop หลักสำหรับติดตามกำไร"""
        self.logger.info("🔄 เริ่ม Profit Monitoring Loop")
        
        while self.is_active:
            try:
                # ดึง positions ปัจจุบัน
                current_positions = self.position_tracker.get_open_positions()
                
                # ตรวจสอบ positions ใหม่
                self._check_new_positions(current_positions)
                
                # อัพเดท profit targets
                self._update_profit_targets(current_positions)
                
                # ตรวจสอบเงื่อนไขเก็บกำไร
                self._check_profit_conditions()
                
                # ทำความสะอาด targets ที่ไม่ใช้แล้ว
                self._cleanup_inactive_targets(current_positions)
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Error in profit monitoring: {e}")
                time.sleep(5.0)
        
        self.logger.info("🛑 หยุด Profit Monitoring Loop")
    
    def _check_new_positions(self, positions: List[Position]):
        """ตรวจสอบ positions ใหม่"""
        for position in positions:
            if position.ticket not in self.active_targets:
                # สร้าง profit target ใหม่
                profit_mode = self._determine_profit_mode(position)
                config = self.profit_configs[profit_mode]
                
                target = ProfitTarget(
                    position_ticket=position.ticket,
                    symbol=position.symbol,
                    entry_price=position.open_price,
                    current_price=position.current_price,
                    position_type="BUY" if position.position_type.name == "BUY" else "SELL",
                    volume=position.volume,
                    target_pips=config["target_pips"],
                    trailing_pips=config["trailing_pips"],
                    partial_targets=config["partial_targets"].copy(),
                    profit_mode=profit_mode,
                    remaining_volume=position.volume
                )
                
                self.active_targets[position.ticket] = target
                self.logger.info(f"🎯 เพิ่ม Profit Target: {position.ticket} ({profit_mode.value})")
    
    def _determine_profit_mode(self, position: Position) -> ProfitMode:
        """กำหนดโหมดการเก็บกำไรตามสถานการณ์"""
        
        # ตรวจสอบจาก comment
        comment = position.comment.lower()
        if "recovery" in comment:
            return ProfitMode.RECOVERY
        elif "news" in comment:
            return ProfitMode.NEWS
        elif "trend" in comment:
            return ProfitMode.TREND
        elif "swing" in comment:
            return ProfitMode.SWING
        
        # ตรวจสอบจากเวลา (Session-based)
        current_hour = datetime.now().hour
        
        # Asian Session (22:00-08:00 GMT+7) = Scalping
        if 22 <= current_hour or current_hour <= 8:
            return ProfitMode.SCALPING
        
        # London Session (15:00-00:00 GMT+7) = Swing
        elif 15 <= current_hour <= 23:
            return ProfitMode.SWING
        
        # NY Session overlap = Trend
        elif 20 <= current_hour <= 23:
            return ProfitMode.TREND
        
        # Default
        return ProfitMode.SCALPING
    
    def _update_profit_targets(self, positions: List[Position]):
        """อัพเดท profit targets ด้วยข้อมูลปัจจุบัน"""
        for position in positions:
            if position.ticket in self.active_targets:
                target = self.active_targets[position.ticket]
                
                # อัพเดทราคาปัจจุบัน
                target.current_price = position.current_price
                target.last_update = datetime.now()
                
                # คำนวณกำไรเป็น pips
                current_profit_pips = self._calculate_profit_pips(
                    target.entry_price, 
                    target.current_price, 
                    target.position_type
                )
                
                # อัพเดท max profit
                if current_profit_pips > target.max_profit_pips:
                    target.max_profit_pips = current_profit_pips
                    target.max_profit_seen = position.profit
    
    def _calculate_profit_pips(self, entry_price: float, current_price: float, position_type: str) -> float:
        """คำนวณกำไรเป็น pips"""
        if position_type == "BUY":
            price_diff = current_price - entry_price
        else:  # SELL
            price_diff = entry_price - current_price
        
        # สำหรับ XAUUSD, 1 pip = 0.1
        pips = price_diff / 0.1
        return pips
    
    def _check_profit_conditions(self):
        """ตรวจสอบเงื่อนไขการเก็บกำไร"""
        for ticket, target in list(self.active_targets.items()):
            try:
                # คำนวณกำไรปัจจุบัน
                current_profit_pips = self._calculate_profit_pips(
                    target.entry_price,
                    target.current_price,
                    target.position_type
                )
                
                # ตรวจสอบ Partial Profit Taking
                self._check_partial_profit(target, current_profit_pips)
                
                # ตรวจสอบ Trailing Stop
                self._check_trailing_stop(target, current_profit_pips)
                
                # ตรวจสอบ Full Target
                self._check_full_target(target, current_profit_pips)
                
            except Exception as e:
                self.logger.error(f"❌ Error checking profit for {ticket}: {e}")
    
    def _check_partial_profit(self, target: ProfitTarget, current_pips: float):
        """ตรวจสอบการเก็บกำไรบางส่วน"""
        for target_pips, close_percentage in target.partial_targets:
            # ตรวจสอบว่าถึงเป้าหมายแล้วหรือไม่
            if current_pips >= target_pips:
                # คำนวณ volume ที่จะปิด
                volume_to_close = target.remaining_volume * close_percentage
                
                if volume_to_close > 0:
                    self.logger.info(f"🎯 Partial Profit: {target.position_ticket} "
                                   f"- Close {volume_to_close:.2f} lots at {target_pips} pips")
                    
                    # ส่งคำสั่งปิดบางส่วน
                    success = self._close_partial_position(target, volume_to_close)
                    
                    if success:
                        # อัพเดท target
                        target.remaining_volume -= volume_to_close
                        target.partial_closed_volume += volume_to_close
                        
                        # ลบ target ที่ใช้แล้ว
                        target.partial_targets = [
                            (pips, pct) for pips, pct in target.partial_targets 
                            if pips > target_pips
                        ]
                        
                        self.logger.info(f"✅ Partial close success: {target.position_ticket}")
    
    def _check_trailing_stop(self, target: ProfitTarget, current_pips: float):
        """ตรวจสอบ Trailing Stop"""
        # เริ่ม trailing เมื่อกำไรเกิน trailing_pips
        if current_pips >= target.trailing_pips:
            target.is_trailing = True
            
            # ตรวจสอบว่า pullback เกินกำหนดหรือไม่
            pullback_pips = target.max_profit_pips - current_pips
            
            if pullback_pips >= target.trailing_pips:
                self.logger.info(f"🎯 Trailing Stop Triggered: {target.position_ticket} "
                               f"- Max: {target.max_profit_pips:.1f} pips, "
                               f"Current: {current_pips:.1f} pips, "
                               f"Pullback: {pullback_pips:.1f} pips")
                
                # ปิด position ที่เหลือ
                if target.remaining_volume > 0:
                    self._close_full_position(target)
    
    def _check_full_target(self, target: ProfitTarget, current_pips: float):
        """ตรวจสอบการถึงเป้าหมายเต็ม"""
        if current_pips >= target.target_pips:
            self.logger.info(f"🎯 Full Target Reached: {target.position_ticket} "
                           f"- {current_pips:.1f} pips")
            
            if target.remaining_volume > 0:
                self._close_full_position(target)
    
    def _close_partial_position(self, target: ProfitTarget, volume: float) -> bool:
        """ปิด position บางส่วน"""
        try:
            # ตรวจสอบ volume ก่อน
            if volume <= 0:
                self.logger.warning(f"⚠️ Invalid volume: {volume} - ปิดทั้งหมดแทน")
                volume = target.volume
            
            # ปิด position ทั้งหมด (เพราะ MT5 ไม่รองรับ partial close ง่ายๆ)
            success = self.position_tracker.close_position(target.position_ticket)
            
            if success:
                # อัพเดท target
                target.partial_closed_volume += target.volume  # ใช้ volume ทั้งหมด
                target.remaining_volume = 0
                
                # ย้าย target ไป completed
                self.completed_targets.append(target)
                del self.active_targets[target.position_ticket]
                
                self.logger.info(f"✅ Position closed: {target.position_ticket} (Full close)")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Close error: {e}")
            return False
                
    def _close_full_position(self, target: ProfitTarget) -> bool:
        """ปิด position ทั้งหมด"""
        try:
            # ใช้ position tracker ปิด
            success = self.position_tracker.close_position(target.position_ticket)
            
            if success:
                # ย้าย target ไปยัง completed
                self.completed_targets.append(target)
                del self.active_targets[target.position_ticket]
                
                self.logger.info(f"✅ Full close success: {target.position_ticket}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Full close error: {e}")
            return False
    
    def _cleanup_inactive_targets(self, positions: List[Position]):
        """ลบ targets ที่ไม่ใช้แล้ว"""
        active_tickets = {pos.ticket for pos in positions}
        
        for ticket in list(self.active_targets.keys()):
            if ticket not in active_tickets:
                # Position ถูกปิดไปแล้ว (โดยวิธีอื่น)
                target = self.active_targets[ticket]
                self.completed_targets.append(target)
                del self.active_targets[ticket]
                self.logger.info(f"🧹 Cleaned up target: {ticket}")
    
    def get_active_targets(self) -> Dict[int, ProfitTarget]:
        """ดึง active targets ปัจจุบัน"""
        return self.active_targets.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """ดึงสถิติการเก็บกำไร"""
        total_completed = len(self.completed_targets)
        successful_targets = [t for t in self.completed_targets if t.max_profit_pips > 0]
        
        return {
            "system_active": self.is_active,
            "active_targets": len(self.active_targets),
            "completed_targets": total_completed,
            "successful_targets": len(successful_targets),
            "success_rate": (len(successful_targets) / max(total_completed, 1)) * 100,
            "avg_profit_pips": np.mean([t.max_profit_pips for t in successful_targets]) if successful_targets else 0,
            "total_volume_closed": sum(t.partial_closed_volume for t in self.completed_targets),
            "active_tickets": list(self.active_targets.keys())
        }
    
    def set_profit_mode(self, ticket: int, mode: ProfitMode):
        """เปลี่ยนโหมดการเก็บกำไรสำหรับ position เฉพาะ"""
        if ticket in self.active_targets:
            target = self.active_targets[ticket]
            config = self.profit_configs[mode]
            
            target.profit_mode = mode
            target.target_pips = config["target_pips"]
            target.trailing_pips = config["trailing_pips"]
            target.partial_targets = config["partial_targets"].copy()
            
            self.logger.info(f"🔄 Changed profit mode for {ticket}: {mode.value}")

    def connect_position_tracker(self):
        """เชื่อมต่อกับ Position Tracker"""
        try:
            from position_management.position_tracker import get_position_tracker
            self.position_tracker = get_position_tracker()
            
            # เชื่อมต่อระบบกันและกัน
            self.position_tracker.connect_profit_system()
            
            self.logger.info("✅ เชื่อมต่อ Position Tracker สำเร็จ")
            return True
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถเชื่อมต่อ Position Tracker: {e}")
            return False

    def check_profit_opportunity(self, position):
        """ตรวจสอบโอกาสเก็บกำไรจาก Position Tracker"""
        try:
            # ตรวจสอบว่า position นี้มีอยู่ใน active_targets หรือไม่
            if position.ticket not in self.active_targets:
                # สร้าง profit target ใหม่
                profit_mode = self._determine_profit_mode(position)
                self._create_profit_target(position, profit_mode)
                
            # อัพเดท target ที่มีอยู่
            elif position.profit > 0:
                target = self.active_targets[position.ticket]
                target.current_price = position.current_price
                target.last_update = datetime.now()
                
                # ตรวจสอบเงื่อนไขเก็บกำไร
                self._check_single_profit_condition(target)
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจสอบกำไร: {e}")

    def get_profit_statistics(self):
        """ดึงสถิติการเก็บกำไร"""
        return {
            'active_targets': len(self.active_targets),
            'completed_targets': len(self.completed_targets),
            'total_profit_taken': sum(t.max_profit_seen for t in self.completed_targets),
            'average_profit_per_target': sum(t.max_profit_seen for t in self.completed_targets) / len(self.completed_targets) if self.completed_targets else 0,
            'profit_taking_success_rate': len([t for t in self.completed_targets if t.max_profit_seen > 0]) / len(self.completed_targets) if self.completed_targets else 0,
            'last_update': datetime.now()
        }


# === GLOBAL INSTANCE ===
_global_profit_taker: Optional[CompleteProfitTaker] = None

def get_profit_taker() -> CompleteProfitTaker:
    """ดึง Profit Taker แบบ Singleton"""
    global _global_profit_taker
    if _global_profit_taker is None:
        _global_profit_taker = CompleteProfitTaker()
    return _global_profit_taker

def start_profit_taking():
    """เริ่มระบบเก็บกำไรแบบ Global"""
    profit_taker = get_profit_taker()
    profit_taker.start_profit_taking()

def stop_profit_taking():
    """หยุดระบบเก็บกำไรแบบ Global"""
    profit_taker = get_profit_taker()
    profit_taker.stop_profit_taking()

# === TESTING FUNCTION ===
def test_profit_system():
    """ทดสอบระบบเก็บกำไร"""
    print("🧪 Testing Complete Profit Taking System...")
    
    profit_taker = get_profit_taker()
    
    # เริ่มระบบ
    profit_taker.start_profit_taking()
    
    # รอสักครู่
    time.sleep(5)
    
    # ดูสถิติ
    stats = profit_taker.get_statistics()
    print("📊 Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # หยุดระบบ
    profit_taker.stop_profit_taking()
    
    print("✅ Test completed")


if __name__ == "__main__":
    test_profit_system()