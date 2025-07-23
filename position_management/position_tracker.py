#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSITION TRACKER - ระบบติดตาม Position แบบครบครัน
============================================
ติดตาม จัดการ และวิเคราะห์ positions ทั้งหมดแบบเรียลไทม์
รองรับการจับคู่ positions และคำนวณ portfolio metrics

เชื่อมต่อไปยัง:
- mt5_integration/mt5_connector.py (ดึงข้อมูล positions จาก MT5)
- mt5_integration/order_executor.py (ส่งออร์เดอร์)
- intelligent_recovery/recovery_selector.py (ส่งข้อมูลการขาดทุน)
- position_management/pair_matcher.py (จับคู่ positions)
- analytics_engine/performance_tracker.py (วิเคราะห์ประสิทธิภาพ)
"""

import MetaTrader5 as mt5
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import statistics

try:
    from mt5_integration.mt5_connector import get_mt5_connector, ensure_mt5_connection
    from mt5_integration.order_executor import get_order_executor, OrderResult
    from config.trading_params import get_trading_parameters
    from utilities.professional_logger import setup_trading_logger
    from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity
except ImportError as e:
    print(f"Import Error in position_tracker.py: {e}")

class PositionStatus(Enum):
    """สถานะของ Position"""
    OPEN = "OPEN"               # เปิดอยู่
    CLOSED = "CLOSED"           # ปิดแล้ว
    PARTIALLY_CLOSED = "PARTIALLY_CLOSED"  # ปิดบางส่วน
    RECOVERY_PENDING = "RECOVERY_PENDING"  # รอ Recovery
    PAIRED = "PAIRED"           # จับคู่แล้ว

class PositionType(Enum):
    """ประเภทของ Position"""
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class Position:
    """ข้อมูล Position แบบครบครัน"""
    
    # ข้อมูลพื้นฐาน
    ticket: int                             # MT5 position ticket
    symbol: str                             # Symbol
    position_type: PositionType             # BUY/SELL
    volume: float                           # Volume
    open_price: float                       # ราคาเปิด
    current_price: float = 0.0              # ราคาปัจจุบัน
    
    # เวลา
    open_time: datetime = field(default_factory=datetime.now)
    close_time: Optional[datetime] = None
    
    # การเงิน
    profit: float = 0.0                     # กำไร/ขาดทุนปัจจุบัน
    swap: float = 0.0                       # ค่า swap
    commission: float = 0.0                 # ค่าคอมมิชชั่น
    
    # ข้อมูลเพิ่มเติม
    magic_number: int = 0                   # Magic number
    comment: str = ""                       # Comment
    entry_strategy: str = ""                # กลยุทธ์ที่ใช้เข้า
    recovery_level: int = 0                 # ระดับ Recovery (0=entry แรก)
    
    # สถานะ
    status: PositionStatus = PositionStatus.OPEN
    is_hedged: bool = False                 # มี hedge หรือไม่
    hedge_partner_ticket: Optional[int] = None  # คู่ hedge
    
    # การวิเคราะห์
    unrealized_pnl: float = 0.0             # P&L ที่ยังไม่เกิดขึ้นจริง
    realized_pnl: float = 0.0               # P&L ที่เกิดขึ้นจริงแล้ว
    max_profit: float = 0.0                 # กำไรสูงสุดที่เคยมี
    max_loss: float = 0.0                   # ขาดทุนสูงสุดที่เคยมี
    profit_percentage: float = 0.0          # เปอร์เซ็นต์กำไร
    
    # Tags และ Metadata
    tags: Set[str] = field(default_factory=set)  # Tags สำหรับจัดกลุ่ม
    metadata: Dict[str, Any] = field(default_factory=dict)  # ข้อมูลเพิ่มเติม
    
    def update_current_data(self, current_price: float, profit: float, 
                           swap: float = None, commission: float = None):
        """อัพเดทข้อมูลปัจจุบัน"""
        self.current_price = current_price
        self.profit = profit
        self.unrealized_pnl = profit
        
        if swap is not None:
            self.swap = swap
        if commission is not None:
            self.commission = commission
        
        # คำนวณเปอร์เซ็นต์
        if self.open_price > 0:
            price_diff = self.current_price - self.open_price
            if self.position_type == PositionType.SELL:
                price_diff = -price_diff
            self.profit_percentage = (price_diff / self.open_price) * 100
        
        # อัพเดท max profit/loss
        if profit > self.max_profit:
            self.max_profit = profit
        if profit < self.max_loss:
            self.max_loss = profit
    
    def get_holding_time(self) -> timedelta:
        """ดึงเวลาที่ถือ position"""
        end_time = self.close_time if self.close_time else datetime.now()
        return end_time - self.open_time
    
    def get_holding_minutes(self) -> float:
        """ดึงเวลาที่ถือ position เป็นนาที"""
        return self.get_holding_time().total_seconds() / 60
    
    def is_profitable(self) -> bool:
        """ตรวจสอบว่ากำไรหรือไม่"""
        return self.profit > 0
    
    def is_long_position(self) -> bool:
        """ตรวจสอบว่าเป็น long position หรือไม่"""
        return self.position_type == PositionType.BUY
    
    def add_tag(self, tag: str):
        """เพิ่ม tag"""
        self.tags.add(tag)
    
    def remove_tag(self, tag: str):
        """ลบ tag"""
        self.tags.discard(tag)
    
    def has_tag(self, tag: str) -> bool:
        """ตรวจสอบว่ามี tag หรือไม่"""
        return tag in self.tags

@dataclass
class PortfolioMetrics:
    """เมตริกของ Portfolio"""
    
    # จำนวน Positions
    total_positions: int = 0
    open_positions: int = 0
    buy_positions: int = 0
    sell_positions: int = 0
    
    # Volume
    total_volume: float = 0.0
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    net_volume: float = 0.0                 # buy_volume - sell_volume
    
    # P&L
    total_unrealized_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    total_profit: float = 0.0
    total_loss: float = 0.0
    net_pnl: float = 0.0
    
    # Statistics
    winning_positions: int = 0
    losing_positions: int = 0
    win_rate: float = 0.0
    avg_profit_per_position: float = 0.0
    avg_holding_time_minutes: float = 0.0
    
    # Risk Metrics
    largest_profit: float = 0.0
    largest_loss: float = 0.0
    max_concurrent_positions: int = 0
    current_drawdown: float = 0.0
    
    # Recovery Information
    positions_in_recovery: int = 0
    total_recovery_cost: float = 0.0
    recovery_success_rate: float = 0.0

class PositionTracker:
    """
    ตัวติดตาม Position หลัก
    ติดตาม จัดการ และวิเคราะห์ positions ทั้งหมดแบบเรียลไทม์
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.trading_params = get_trading_parameters()
        
        # เก็บข้อมูล positions
        self.positions: Dict[int, Position] = {}           # ticket -> Position
        self.closed_positions: Dict[int, Position] = {}    # positions ที่ปิดแล้ว
        self.position_groups: Dict[str, List[int]] = {}    # จัดกลุ่มตาม strategy/tag
        
        # Threading
        self.tracker_lock = threading.Lock()
        self.tracking_active = False
        self.tracking_thread: Optional[threading.Thread] = None
        
        # การตั้งค่า
        self.update_interval = 1.0  # วินาที
        self.max_history_size = 1000  # จำนวน positions ที่เก็บในประวัติ
        
        # สถิติ
        self.total_positions_tracked = 0
        self.last_update_time: Optional[datetime] = None
        
        # Callbacks
        self.position_callbacks: List[callable] = []
        self.pnl_callbacks: List[callable] = []
        
        self.logger.info("📍 เริ่มต้น Position Tracker")
    
    def start_tracking(self):
        """เริ่มการติดตาม positions"""
        if self.tracking_active:
            return
        
        self.tracking_active = True
        self.tracking_thread = threading.Thread(
            target=self._tracking_loop,
            daemon=True,
            name="PositionTracker"
        )
        self.tracking_thread.start()
        
        self.logger.info("🚀 เริ่มติดตาม Positions แบบเรียลไทม์")
    
    def stop_tracking(self):
        """หยุดการติดตาม positions"""
        self.tracking_active = False
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=5.0)
        
        self.logger.info("🛑 หยุดติดตาม Positions")
    
    @handle_trading_errors(ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM)
    def _tracking_loop(self):
        """ลูปหลักสำหรับติดตาม positions"""
        
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
                time.sleep(5.0)  # รอนานขึ้นเมื่อเกิดข้อผิดพลาด
    
    def _update_positions_from_mt5(self):
        """อัพเดทข้อมูล positions จาก MT5"""
        
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
                    ticket = mt5_pos.ticket
                    current_tickets.add(ticket)
                    
                    # ดึงราคาปัจจุบัน
                    symbol_info = mt5.symbol_info_tick(mt5_pos.symbol)
                    if symbol_info:
                        if mt5_pos.type == mt5.POSITION_TYPE_BUY:
                            current_price = symbol_info.bid
                        else:
                            current_price = symbol_info.ask
                    else:
                        current_price = mt5_pos.price_open
                    
                    if ticket in self.positions:
                        # อัพเดท position ที่มีอยู่
                        position = self.positions[ticket]
                        position.update_current_data(
                            current_price=current_price,
                            profit=mt5_pos.profit,
                            swap=mt5_pos.swap,
                            commission=mt5_pos.commission
                        )
                    else:
                        # สร้าง position ใหม่
                        position = self._create_position_from_mt5(mt5_pos, current_price)
                        self.positions[ticket] = position
                        self.total_positions_tracked += 1
                        
                        self.logger.info(
                            f"📍 ตรวจพบ Position ใหม่: {ticket} {position.symbol} "
                            f"{position.position_type.value} {position.volume}"
                        )
                
                # ตรวจหา positions ที่ถูกปิด
                closed_tickets = set(self.positions.keys()) - current_tickets
                for ticket in closed_tickets:
                    position = self.positions[ticket]
                    position.status = PositionStatus.CLOSED
                    position.close_time = datetime.now()
                    position.realized_pnl = position.profit
                    
                    # ย้ายไป closed_positions
                    self.closed_positions[ticket] = position
                    del self.positions[ticket]
                    
                    self.logger.info(
                        f"✅ Position ปิด: {ticket} P&L: {position.profit:.2f} "
                        f"Time: {position.get_holding_minutes():.1f}min"
                    )
                    
                    # จำกัดขนาด history
                    if len(self.closed_positions) > self.max_history_size:
                        oldest_ticket = min(self.closed_positions.keys(), 
                                          key=lambda t: self.closed_positions[t].close_time)
                        del self.closed_positions[oldest_ticket]
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท positions จาก MT5: {e}")
    
    def _create_position_from_mt5(self, mt5_pos, current_price: float) -> Position:
        """สร้าง Position จากข้อมูล MT5"""
        
        position_type = PositionType.BUY if mt5_pos.type == mt5.POSITION_TYPE_BUY else PositionType.SELL
        
        position = Position(
            ticket=mt5_pos.ticket,
            symbol=mt5_pos.symbol,
            position_type=position_type,
            volume=mt5_pos.volume,
            open_price=mt5_pos.price_open,
            current_price=current_price,
            open_time=datetime.fromtimestamp(mt5_pos.time),
            profit=mt5_pos.profit,
            swap=mt5_pos.swap,
            commission=mt5_pos.commission,
            magic_number=mt5_pos.magic,
            comment=mt5_pos.comment,
            unrealized_pnl=mt5_pos.profit
        )
        
        # แยกข้อมูลจาก comment ถ้ามี
        self._parse_position_metadata(position)
        
        return position
    
    def _parse_position_metadata(self, position: Position):
        """แยกข้อมูล metadata จาก comment"""
        
        comment = position.comment
        if not comment:
            return
        
        try:
            # ตัวอย่างรูปแบบ comment: "Strategy:TREND_FOLLOWING|Level:2|Tag:RECOVERY"
            parts = comment.split("|")
            for part in parts:
                if ":" in part:
                    key, value = part.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == "strategy":
                        position.entry_strategy = value
                    elif key == "level":
                        try:
                            position.recovery_level = int(value)
                        except ValueError:
                            pass
                    elif key == "tag":
                        position.add_tag(value)
                    else:
                        position.metadata[key] = value
        
        except Exception as e:
            self.logger.debug(f"ไม่สามารถแยก metadata จาก comment: {e}")
    
    def _detect_position_changes(self):
        """ตรวจหาการเปลี่ยนแปลงของ positions"""
        
        with self.tracker_lock:
            for position in self.positions.values():
                # ตรวจหาการขาดทุนที่ต้อง Recovery
                if (position.profit < -100 and  # ขาดทุนเกิน 100
                    position.status == PositionStatus.OPEN and
                    not position.has_tag("RECOVERY_NOTIFIED")):
                    
                    position.add_tag("RECOVERY_NOTIFIED")
                    position.status = PositionStatus.RECOVERY_PENDING
                    
                    self.logger.warning(
                        f"⚠️ Position ต้อง Recovery: {position.ticket} "
                        f"Loss: {position.profit:.2f} Symbol: {position.symbol}"
                    )
    
    def _calculate_portfolio_metrics(self):
        """คำนวณ metrics ของ portfolio"""
        # จะถูกเรียกจาก _tracking_loop แต่ไม่ implement เต็มในที่นี้
        pass
    
    def _notify_callbacks(self):
        """แจ้งเตือน callbacks"""
        try:
            for callback in self.position_callbacks:
                callback(list(self.positions.values()))
        except Exception as e:
            self.logger.warning(f"⚠️ ข้อผิดพลาดใน position callback: {e}")
    
    # === PUBLIC METHODS ===
    
    def get_open_positions(self, symbol: str = None) -> List[Position]:
        """ดึง positions ที่เปิดอยู่"""
        with self.tracker_lock:
            positions = list(self.positions.values())
            if symbol:
                positions = [p for p in positions if p.symbol == symbol]
            return positions
    
    def get_position_by_ticket(self, ticket: int) -> Optional[Position]:
        """ดึง position ตาม ticket"""
        with self.tracker_lock:
            return self.positions.get(ticket)
    
    def get_positions_by_strategy(self, strategy: str) -> List[Position]:
        """ดึง positions ตามกลยุทธ์"""
        with self.tracker_lock:
            return [p for p in self.positions.values() if p.entry_strategy == strategy]
    
    def get_positions_by_tag(self, tag: str) -> List[Position]:
        """ดึง positions ตาม tag"""
        with self.tracker_lock:
            return [p for p in self.positions.values() if p.has_tag(tag)]
    
    def get_losing_positions(self, min_loss: float = 0.0) -> List[Position]:
        """ดึง positions ที่ขาดทุน"""
        with self.tracker_lock:
            return [p for p in self.positions.values() 
                   if p.profit < -abs(min_loss)]
    
    def get_profitable_positions(self, min_profit: float = 0.0) -> List[Position]:
        """ดึง positions ที่กำไร"""
        with self.tracker_lock:
            return [p for p in self.positions.values() 
                   if p.profit > min_profit]
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """ดึงสรุป portfolio"""
        with self.tracker_lock:
            positions = list(self.positions.values())
            
            if not positions:
                return {
                    "total_positions": 0,
                    "total_unrealized_pnl": 0.0,
                    "total_volume": 0.0,
                    "symbols": []
                }
            
            total_pnl = sum(p.profit for p in positions)
            total_volume = sum(p.volume for p in positions)
            buy_positions = [p for p in positions if p.position_type == PositionType.BUY]
            sell_positions = [p for p in positions if p.position_type == PositionType.SELL]
            
            symbols = list(set(p.symbol for p in positions))
            profitable_positions = [p for p in positions if p.profit > 0]
            losing_positions = [p for p in positions if p.profit < 0]
            
            return {
                "total_positions": len(positions),
                "buy_positions": len(buy_positions),
                "sell_positions": len(sell_positions),
                "total_unrealized_pnl": round(total_pnl, 2),
                "total_volume": round(total_volume, 2),
                "buy_volume": round(sum(p.volume for p in buy_positions), 2),
                "sell_volume": round(sum(p.volume for p in sell_positions), 2),
                "net_volume": round(sum(p.volume for p in buy_positions) - sum(p.volume for p in sell_positions), 2),
                "profitable_positions": len(profitable_positions),
                "losing_positions": len(losing_positions),
                "largest_profit": max([p.profit for p in positions] + [0]),
                "largest_loss": min([p.profit for p in positions] + [0]),
                "symbols": symbols,
                "avg_holding_time_minutes": statistics.mean([p.get_holding_minutes() for p in positions]) if positions else 0,
                "positions_needing_recovery": len([p for p in positions if p.status == PositionStatus.RECOVERY_PENDING])
            }
    
    def get_positions_for_recovery(self, min_loss: float = 50.0) -> List[Position]:
        """ดึง positions ที่ต้อง Recovery"""
        losing_positions = self.get_losing_positions(min_loss)
        
        # แปลงเป็น LossPosition format สำหรับ recovery system
        from intelligent_recovery.recovery_selector import LossPosition
        
        loss_positions = []
        for pos in losing_positions:
            loss_pos = LossPosition(
                position_id=str(pos.ticket),
                symbol=pos.symbol,
                entry_price=pos.open_price,
                current_price=pos.current_price,
                volume=pos.volume,
                loss_amount=pos.profit,
                loss_percentage=abs(pos.profit_percentage),
                entry_time=pos.open_time,
                holding_time_minutes=pos.get_holding_minutes(),
                entry_strategy=pos.entry_strategy,
                market_condition_at_entry=pos.metadata.get("market_condition", "UNKNOWN")
            )
            loss_positions.append(loss_pos)
        
        return loss_positions
    
    def update_position_metadata(self, ticket: int, key: str, value: Any):
        """อัพเดท metadata ของ position"""
        with self.tracker_lock:
            position = self.positions.get(ticket)
            if position:
                position.metadata[key] = value
    
    def add_position_tag(self, ticket: int, tag: str):
        """เพิ่ม tag ให้ position"""
        with self.tracker_lock:
            position = self.positions.get(ticket)
            if position:
                position.add_tag(tag)
    
    def remove_position_tag(self, ticket: int, tag: str):
        """ลบ tag จาก position"""
        with self.tracker_lock:
            position = self.positions.get(ticket)
            if position:
                position.remove_tag(tag)
    
    def close_position(self, ticket: int, volume: Optional[float] = None) -> bool:
        """ปิด position"""
        position = self.get_position_by_ticket(ticket)
        if not position:
            return False
        
        order_executor = get_order_executor()
        result = order_executor.close_position(ticket, volume)
        
        success = result.status.value in ["FILLED", "SUCCESS"]
        if success:
            self.logger.info(f"✅ ปิด Position สำเร็จ: {ticket}")
        else:
            self.logger.error(f"❌ ปิด Position ไม่สำเร็จ: {ticket} - {result.error_description}")
        
        return success
    
    def close_all_losing_positions(self, min_loss: float = 0.0) -> List[bool]:
        """ปิด positions ที่ขาดทุนทั้งหมด"""
        losing_positions = self.get_losing_positions(min_loss)
        results = []
        
        for position in losing_positions:
            result = self.close_position(position.ticket)
            results.append(result)
        
        return results
    
    def close_all_profitable_positions(self, min_profit: float = 0.0) -> List[bool]:
        """ปิด positions ที่กำไรทั้งหมด"""
        profitable_positions = self.get_profitable_positions(min_profit)
        results = []
        
        for position in profitable_positions:
            result = self.close_position(position.ticket)
            results.append(result)
        
        return results
    
    def add_position_callback(self, callback: callable):
        """เพิ่ม callback สำหรับการแจ้งเตือนเมื่อ positions เปลี่ยนแปลง"""
        self.position_callbacks.append(callback)
    
    def get_tracking_statistics(self) -> Dict[str, Any]:
        """ดึงสถิติการติดตาม"""
        return {
            "tracking_active": self.tracking_active,
            "total_positions_tracked": self.total_positions_tracked,
            "current_open_positions": len(self.positions),
            "closed_positions_in_history": len(self.closed_positions),
            "last_update": self.last_update_time.isoformat() if self.last_update_time else None,
            "update_interval_seconds": self.update_interval
        }

# === HELPER FUNCTIONS ===

def get_current_positions(symbol: str = None) -> List[Position]:
    """ดึง positions ปัจจุบัน"""
    tracker = get_position_tracker()
    return tracker.get_open_positions(symbol)

def get_total_unrealized_pnl() -> float:
    """ดึงกำไร/ขาดทุนรวมที่ยังไม่เกิดขึ้นจริง"""
    tracker = get_position_tracker()
    summary = tracker.get_portfolio_summary()
    return summary["total_unrealized_pnl"]

def get_positions_needing_recovery(min_loss: float = 50.0):
    """ดึง positions ที่ต้อง Recovery"""
    tracker = get_position_tracker()
    return tracker.get_positions_for_recovery(min_loss)

def close_all_positions() -> bool:
    """ปิด positions ทั้งหมด"""
    tracker = get_position_tracker()
    positions = tracker.get_open_positions()
    
    success_count = 0
    for position in positions:
        if tracker.close_position(position.ticket):
            success_count += 1
    
    return success_count == len(positions)

def start_position_tracking():
    """เริ่มการติดตาม positions"""
    tracker = get_position_tracker()
    tracker.start_tracking()

def stop_position_tracking():
    """หยุดการติดตาม positions"""
    tracker = get_position_tracker()
    tracker.stop_tracking()

# === GLOBAL INSTANCE ===
_global_position_tracker: Optional[PositionTracker] = None

def get_position_tracker() -> PositionTracker:
    """ดึง Position Tracker แบบ Singleton"""
    global _global_position_tracker
    if _global_position_tracker is None:
        _global_position_tracker = PositionTracker()
        # เริ่มการติดตามอัตโนมัติ
        _global_position_tracker.start_tracking()
    return _global_position_tracker