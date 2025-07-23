#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PERFORMANCE TRACKER - Performance Analytics Engine
================================================
เครื่องมือวิเคราะห์ประสิทธิภาพการเทรดแบบ Real-time และครอบคลุม
ติดตามทุกแง่มุมของระบบ Trading และ Recovery

Key Features:
- Real-time performance monitoring
- Recovery system effectiveness analysis
- Volume achievement tracking (50-100 lots/วัน)
- Win rate และ Recovery rate calculations
- Strategy performance comparison
- Risk metrics และ drawdown analysis
- Session-based performance analytics

เชื่อมต่อไปยัง:
- position_management/position_tracker.py (ข้อมูล positions)
- intelligent_recovery/recovery_engine.py (ข้อมูล recovery)
- adaptive_entries/signal_generator.py (ข้อมูล signals)
- money_management/position_sizer.py (ข้อมูล sizing)
- mt5_integration/order_executor.py (ข้อมูล orders)
"""

import asyncio
import threading
import time
import statistics
from datetime import datetime, timedelta, date
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
import json
import sqlite3
from collections import defaultdict, deque

# เชื่อมต่อ internal modules
from config.settings import get_system_settings, MarketSession
from config.trading_params import get_trading_parameters, EntryStrategy, RecoveryMethod
from utilities.professional_logger import setup_trading_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class PerformanceMetric(Enum):
    """ประเภทของ Performance Metrics"""
    PROFIT_LOSS = "PROFIT_LOSS"                    # กำไร/ขาดทุน
    WIN_RATE = "WIN_RATE"                          # อัตราชนะ
    RECOVERY_RATE = "RECOVERY_RATE"                # อัตราการ Recovery สำเร็จ
    VOLUME_ACHIEVEMENT = "VOLUME_ACHIEVEMENT"      # การบรรลุเป้าหมาย Volume
    DRAWDOWN = "DRAWDOWN"                          # Drawdown
    SHARPE_RATIO = "SHARPE_RATIO"                  # Sharpe Ratio
    CALMAR_RATIO = "CALMAR_RATIO"                  # Calmar Ratio
    PROFIT_FACTOR = "PROFIT_FACTOR"                # Profit Factor
    AVERAGE_TRADE = "AVERAGE_TRADE"                # เทรดเฉลี่ย
    HOLD_TIME = "HOLD_TIME"                        # เวลาถือ Position

class TimeFrame(Enum):
    """ช่วงเวลาสำหรับการวิเคราะห์"""
    REAL_TIME = "REAL_TIME"        # Real-time
    HOURLY = "HOURLY"              # รายชั่วโมง
    DAILY = "DAILY"                # รายวัน
    WEEKLY = "WEEKLY"              # รายสัปดาห์
    MONTHLY = "MONTHLY"            # รายเดือน
    YEARLY = "YEARLY"              # รายปี

class TradeStatus(Enum):
    """สถานะของเทรด"""
    OPEN = "OPEN"                  # เปิดอยู่
    CLOSED_PROFIT = "CLOSED_PROFIT"  # ปิดกำไร
    CLOSED_LOSS = "CLOSED_LOSS"      # ปิดขาดทุน
    RECOVERED = "RECOVERED"          # Recovery สำเร็จ
    IN_RECOVERY = "IN_RECOVERY"      # อยู่ระหว่าง Recovery

@dataclass
class TradeRecord:
    """
    บันทึกข้อมูลเทรดแต่ละรายการ
    """
    trade_id: str                              # ID เฉพาะของเทรด
    position_id: str                           # Position ID
    symbol: str = "XAUUSD"                     # สัญลักษณ์
    
    # Trade Information
    entry_time: datetime                       # เวลาเปิด
    close_time: Optional[datetime] = None      # เวลาปิด
    direction: str = "BUY"                     # ทิศทาง (BUY/SELL)
    volume: float = 0.1                        # Volume
    
    # Price Information
    entry_price: float = 0.0                   # ราคาเปิด
    close_price: Optional[float] = None        # ราคาปิด
    current_price: float = 0.0                 # ราคาปัจจุบัน
    
    # P&L Information
    realized_pnl: float = 0.0                  # กำไร/ขาดทุนที่ตัดแล้ว
    unrealized_pnl: float = 0.0                # กำไร/ขาดทุนที่ยังไม่ตัด
    commission: float = 0.0                    # ค่าคอมมิชชั่น
    swap: float = 0.0                          # ค่า Swap
    
    # Trade Context
    entry_strategy: EntryStrategy              # กลยุทธ์การเข้า
    signal_quality: float = 0.0                # คุณภาพ Signal (0-100)
    market_session: MarketSession              # Session ที่เทรด
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Recovery Information
    status: TradeStatus = TradeStatus.OPEN
    is_recovery_trade: bool = False            # เป็นเทรด Recovery หรือไม่
    parent_trade_id: Optional[str] = None      # Trade ต้นฉบับที่ต้อง Recover
    recovery_method: Optional[RecoveryMethod] = None  # วิธี Recovery
    recovery_level: int = 0                    # ระดับของ Recovery (0=original, 1=first recovery, etc.)
    
    # Performance Metrics
    hold_duration: timedelta = field(default_factory=timedelta)  # ระยะเวลาถือ
    max_profit: float = 0.0                    # กำไรสูงสุดที่เคยมี
    max_loss: float = 0.0                      # ขาดทุนสูงสุดที่เคยมี
    
    # Additional Information
    notes: str = ""                            # หมายเหตุ
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceSnapshot:
    """
    ภาพรวมประสิทธิภาพ ณ เวลาหนึ่ง
    """
    timestamp: datetime                        # เวลาที่บันทึก
    timeframe: TimeFrame                       # ช่วงเวลา
    
    # Account Metrics
    account_balance: float = 0.0               # ยอดเงินในบัญชี
    account_equity: float = 0.0                # Equity
    free_margin: float = 0.0                   # Margin ที่ใช้ได้
    margin_level: float = 0.0                  # Margin Level %
    
    # Trading Metrics
    total_trades: int = 0                      # จำนวนเทรดทั้งหมด
    winning_trades: int = 0                    # จำนวนเทรดกำไร
    losing_trades: int = 0                     # จำนวนเทรดขาดทุน
    recovered_trades: int = 0                  # จำนวนเทรดที่ Recovery สำเร็จ
    
    # P&L Metrics
    total_profit: float = 0.0                  # กำไรรวม
    total_loss: float = 0.0                    # ขาดทุนรวม
    net_profit: float = 0.0                    # กำไรสุทธิ
    gross_profit: float = 0.0                  # กำไรก่อนหักค่าใช้จ่าย
    gross_loss: float = 0.0                    # ขาดทุนก่อนหักค่าใช้จ่าย
    
    # Volume Metrics
    total_volume: float = 0.0                  # Volume รวม
    daily_volume_target: float = 75.0          # เป้าหมาย Volume ประจำวัน
    volume_achievement_rate: float = 0.0       # อัตราการบรรลุเป้าหมาย Volume (%)
    
    # Key Performance Indicators
    win_rate: float = 0.0                      # อัตราชนะ (%)
    recovery_rate: float = 100.0               # อัตราการ Recovery สำเร็จ (%)
    profit_factor: float = 0.0                 # Profit Factor
    average_win: float = 0.0                   # กำไรเฉลี่ยต่อเทรด
    average_loss: float = 0.0                  # ขาดทุนเฉลี่ยต่อเทรด
    
    # Risk Metrics
    max_drawdown: float = 0.0                  # Drawdown สูงสุด
    current_drawdown: float = 0.0              # Drawdown ปัจจุบัน
    sharpe_ratio: float = 0.0                  # Sharpe Ratio
    calmar_ratio: float = 0.0                  # Calmar Ratio
    
    # Session-based Metrics
    session_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Strategy Performance
    strategy_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Recovery Metrics
    recovery_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)

class PerformanceDatabase:
    """
    จัดการฐานข้อมูลสำหรับเก็บข้อมูล Performance
    """
    
    def __init__(self, db_path: str = "performance.db"):
        self.db_path = db_path
        self.logger = setup_trading_logger()
        self._init_database()
    
    def _init_database(self) -> None:
        """
        เริ่มต้นฐานข้อมูล
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # ตาราง Trade Records
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_records (
                    trade_id TEXT PRIMARY KEY,
                    position_id TEXT,
                    symbol TEXT,
                    entry_time TEXT,
                    close_time TEXT,
                    direction TEXT,
                    volume REAL,
                    entry_price REAL,
                    close_price REAL,
                    realized_pnl REAL,
                    unrealized_pnl REAL,
                    commission REAL,
                    swap REAL,
                    entry_strategy TEXT,
                    signal_quality REAL,
                    market_session TEXT,
                    status TEXT,
                    is_recovery_trade INTEGER,
                    parent_trade_id TEXT,
                    recovery_method TEXT,
                    recovery_level INTEGER,
                    hold_duration_seconds INTEGER,
                    max_profit REAL,
                    max_loss REAL,
                    market_conditions TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # ตาราง Performance Snapshots
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    timeframe TEXT,
                    account_balance REAL,
                    account_equity REAL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    recovered_trades INTEGER,
                    total_profit REAL,
                    total_loss REAL,
                    net_profit REAL,
                    total_volume REAL,
                    win_rate REAL,
                    recovery_rate REAL,
                    profit_factor REAL,
                    max_drawdown REAL,
                    current_drawdown REAL,
                    sharpe_ratio REAL,
                    volume_achievement_rate REAL,
                    session_performance TEXT,
                    strategy_performance TEXT,
                    recovery_performance TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # สร้าง Indexes สำหรับ Performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_entry_time ON trade_records(entry_time)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_status ON trade_records(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_timestamp ON performance_snapshots(timestamp)")
                
                conn.commit()
                
            self.logger.info("✅ เริ่มต้นฐานข้อมูล Performance สำเร็จ")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเริ่มต้นฐานข้อมูล: {e}")
    
    def save_trade_record(self, trade: TradeRecord) -> bool:
        """
        บันทึก Trade Record
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                INSERT OR REPLACE INTO trade_records (
                    trade_id, position_id, symbol, entry_time, close_time, direction, volume,
                    entry_price, close_price, realized_pnl, unrealized_pnl, commission, swap,
                    entry_strategy, signal_quality, market_session, status, is_recovery_trade,
                    parent_trade_id, recovery_method, recovery_level, hold_duration_seconds,
                    max_profit, max_loss, market_conditions, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade.trade_id, trade.position_id, trade.symbol,
                    trade.entry_time.isoformat(),
                    trade.close_time.isoformat() if trade.close_time else None,
                    trade.direction, trade.volume, trade.entry_price, trade.close_price,
                    trade.realized_pnl, trade.unrealized_pnl, trade.commission, trade.swap,
                    trade.entry_strategy.value, trade.signal_quality, trade.market_session.value,
                    trade.status.value, int(trade.is_recovery_trade), trade.parent_trade_id,
                    trade.recovery_method.value if trade.recovery_method else None,
                    trade.recovery_level, int(trade.hold_duration.total_seconds()),
                    trade.max_profit, trade.max_loss,
                    json.dumps(trade.market_conditions), trade.notes
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการบันทึก Trade Record: {e}")
            return False
    
    def save_performance_snapshot(self, snapshot: PerformanceSnapshot) -> bool:
        """
        บันทึก Performance Snapshot
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                INSERT INTO performance_snapshots (
                    timestamp, timeframe, account_balance, account_equity, total_trades,
                    winning_trades, losing_trades, recovered_trades, total_profit, total_loss,
                    net_profit, total_volume, win_rate, recovery_rate, profit_factor,
                    max_drawdown, current_drawdown, sharpe_ratio, volume_achievement_rate,
                    session_performance, strategy_performance, recovery_performance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot.timestamp.isoformat(), snapshot.timeframe.value,
                    snapshot.account_balance, snapshot.account_equity, snapshot.total_trades,
                    snapshot.winning_trades, snapshot.losing_trades, snapshot.recovered_trades,
                    snapshot.total_profit, snapshot.total_loss, snapshot.net_profit,
                    snapshot.total_volume, snapshot.win_rate, snapshot.recovery_rate,
                    snapshot.profit_factor, snapshot.max_drawdown, snapshot.current_drawdown,
                    snapshot.sharpe_ratio, snapshot.volume_achievement_rate,
                    json.dumps(snapshot.session_performance),
                    json.dumps(snapshot.strategy_performance),
                    json.dumps(snapshot.recovery_performance)
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการบันทึก Performance Snapshot: {e}")
            return False
    
    def get_trades_by_period(self, start_time: datetime, end_time: datetime) -> List[TradeRecord]:
        """
        ดึงเทรดในช่วงเวลาที่กำหนด
        """
        try:
            trades = []
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                SELECT * FROM trade_records 
                WHERE entry_time >= ? AND entry_time <= ?
                ORDER BY entry_time
                """, (start_time.isoformat(), end_time.isoformat()))
                
                rows = cursor.fetchall()
                
                # แปลงเป็น TradeRecord objects
                for row in rows:
                    # สร้าง TradeRecord จาก database row
                    # TODO: Implement full conversion
                    pass
                
            return trades
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงเทรด: {e}")
            return []

class RealTimeMetricsCalculator:
    """
    คำนวณ Metrics แบบ Real-time
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Real-time data storage
        self.active_trades: Dict[str, TradeRecord] = {}
        self.recent_trades: deque = deque(maxlen=1000)  # เก็บเทรด 1000 รายการล่าสุด
        self.hourly_snapshots: deque = deque(maxlen=24)  # เก็บ snapshot 24 ชั่วโมงล่าสุด
        
        # Running calculations
        self.running_pnl = 0.0
        self.running_volume = 0.0
        self.daily_high_balance = 0.0
        self.max_drawdown_today = 0.0
        
        self.logger.info("📊 เริ่มต้น Real-time Metrics Calculator")
    
    def add_trade(self, trade: TradeRecord) -> None:
        """
        เพิ่มเทรดใหม่เข้าสู่การติดตาม
        """
        try:
            if trade.status == TradeStatus.OPEN:
                self.active_trades[trade.trade_id] = trade
            else:
                # เทรดปิดแล้ว
                if trade.trade_id in self.active_trades:
                    del self.active_trades[trade.trade_id]
                
                self.recent_trades.append(trade)
                
                # อัพเดท Running calculations
                self.running_pnl += trade.realized_pnl
                self.running_volume += trade.volume
            
            self.logger.debug(f"📈 เพิ่มเทรด: {trade.trade_id} | P&L: {trade.realized_pnl:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเพิ่มเทรด: {e}")
    
    def update_trade(self, trade_id: str, current_price: float, unrealized_pnl: float) -> None:
        """
        อัพเดทข้อมูลเทรดที่เปิดอยู่
        """
        try:
            if trade_id in self.active_trades:
                trade = self.active_trades[trade_id]
                trade.current_price = current_price
                trade.unrealized_pnl = unrealized_pnl
                trade.hold_duration = datetime.now() - trade.entry_time
                
                # อัพเดท Max Profit/Loss
                if unrealized_pnl > trade.max_profit:
                    trade.max_profit = unrealized_pnl
                if unrealized_pnl < trade.max_loss:
                    trade.max_loss = unrealized_pnl
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดทเทรด: {e}")
    
    def calculate_current_metrics(self) -> Dict[str, Any]:
        """
        คำนวณ Metrics ปัจจุบัน
        """
        try:
            # รวบรวมข้อมูลเทรดทั้งหมด
            all_trades = list(self.recent_trades) + list(self.active_trades.values())
            
            if not all_trades:
                return self._get_empty_metrics()
            
            # คำนวณ Basic Metrics
            total_trades = len([t for t in all_trades if t.status != TradeStatus.OPEN])
            winning_trades = len([t for t in all_trades if t.realized_pnl > 0])
            losing_trades = len([t for t in all_trades if t.realized_pnl < 0])
            recovered_trades = len([t for t in all_trades if t.status == TradeStatus.RECOVERED])
            
            # คำนวณ P&L
            total_realized_pnl = sum(t.realized_pnl for t in all_trades)
            total_unrealized_pnl = sum(t.unrealized_pnl for t in self.active_trades.values())
            net_pnl = total_realized_pnl + total_unrealized_pnl
            
            # คำนวณ Volume
            total_volume = sum(t.volume for t in all_trades)
            
            # คำนวณอัตราต่างๆ
            win_rate = (winning_trades / max(total_trades, 1)) * 100
            recovery_rate = 100.0 if losing_trades == 0 else (recovered_trades / max(losing_trades, 1)) * 100
            
            # คำนวณ Profit Factor
            total_profit = sum(t.realized_pnl for t in all_trades if t.realized_pnl > 0)
            total_loss = abs(sum(t.realized_pnl for t in all_trades if t.realized_pnl < 0))
            profit_factor = total_profit / max(total_loss, 1.0)
            
            # คำนวณค่าเฉลี่ย
            profits = [t.realized_pnl for t in all_trades if t.realized_pnl > 0]
            losses = [t.realized_pnl for t in all_trades if t.realized_pnl < 0]
            
            average_win = statistics.mean(profits) if profits else 0.0
            average_loss = statistics.mean(losses) if losses else 0.0
            
            return {
                "timestamp": datetime.now(),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "recovered_trades": recovered_trades,
                "win_rate": round(win_rate, 2),
                "recovery_rate": round(recovery_rate, 2),
                "total_realized_pnl": round(total_realized_pnl, 2),
                "total_unrealized_pnl": round(total_unrealized_pnl, 2),
                "net_pnl": round(net_pnl, 2),
                "total_volume": round(total_volume, 2),
                "profit_factor": round(profit_factor, 2),
                "average_win": round(average_win, 2),
                "average_loss": round(average_loss, 2),
                "active_positions": len(self.active_trades)
            }
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Metrics: {e}")
            return self._get_empty_metrics()
    
    def _get_empty_metrics(self) -> Dict[str, Any]:
        """
        ส่งคืน Empty Metrics
        """
        return {
            "timestamp": datetime.now(),
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "recovered_trades": 0,
            "win_rate": 0.0,
            "recovery_rate": 100.0,
            "total_realized_pnl": 0.0,
            "total_unrealized_pnl": 0.0,
            "net_pnl": 0.0,
            "total_volume": 0.0,
            "profit_factor": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "active_positions": 0
        }

class PerformanceTracker:
    """
    🎯 Main Performance Tracker Class
    
    เครื่องมือหลักสำหรับติดตามและวิเคราะห์ประสิทธิภาพการเทรด
    รองรับการวิเคราะห์แบบ Real-time และครอบคลุม
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Core Components
        self.database = PerformanceDatabase()
        self.metrics_calculator = RealTimeMetricsCalculator()
        
        # External Connections
        self.position_tracker = None        # จะเชื่อมต่อใน start()
        self.recovery_engine = None         # จะเชื่อมต่อใน start()
        self.signal_generator = None        # จะเชื่อมต่อใน start()
        
        # Performance Tracking
        self.current_snapshot = PerformanceSnapshot(
            timestamp=datetime.now(),
            timeframe=TimeFrame.REAL_TIME
        )
        
        # Threading
        self.tracker_active = False
        self.update_thread = None
        self.snapshot_thread = None
        
        # Statistics
        self.total_analysis_runs = 0
        self.last_snapshot_time = datetime.now()
        
        self.logger.info("📊 เริ่มต้น Performance Tracker")
    
    @handle_trading_errors(ErrorCategory.ANALYTICS, ErrorSeverity.MEDIUM)
    async def start_performance_tracker(self) -> None:
        """
        เริ่ม Performance Tracker
        """
        if self.tracker_active:
            self.logger.warning("⚠️ Performance Tracker กำลังทำงานอยู่แล้ว")
            return
        
        self.logger.info("🚀 เริ่มต้น Performance Tracker System")
        
        # เชื่อมต่อ External Components
        try:
            from position_management.position_tracker import PositionTracker
            self.position_tracker = PositionTracker()
        except ImportError:
            self.logger.warning("⚠️ ไม่สามารถเชื่อมต่อ Position Tracker")
        
        try:
            from intelligent_recovery.recovery_engine import get_recovery_engine
            self.recovery_engine = get_recovery_engine()
        except ImportError:
            self.logger.warning("⚠️ ไม่สามารถเชื่อมต่อ Recovery Engine")
        
        try:
            from adaptive_entries.signal_generator import get_signal_generator
            self.signal_generator = get_signal_generator()
        except ImportError:
            self.logger.warning("⚠️ ไม่สามารถเชื่อมต่อ Signal Generator")
        
        # เริ่ม Tracking Threads
        self.tracker_active = True
        self.update_thread = threading.Thread(target=self._performance_update_loop, daemon=True)
        self.snapshot_thread = threading.Thread(target=self._snapshot_creation_loop, daemon=True)
        
        self.update_thread.start()
        self.snapshot_thread.start()
        
        # สร้าง Initial Snapshot
        await self._create_performance_snapshot(TimeFrame.REAL_TIME)
        
        self.logger.info("✅ Performance Tracker System เริ่มทำงานแล้ว")
    
    def record_trade_opened(self, position_id: str, entry_strategy: EntryStrategy,
                          entry_price: float, volume: float, direction: str,
                          signal_quality: float = 0.0, market_session: MarketSession = MarketSession.ASIAN,
                          market_conditions: Dict[str, Any] = None) -> str:
        """
        บันทึกการเปิดเทรดใหม่
        """
        try:
            trade_id = f"TRADE_{position_id}_{int(time.time())}"
            
            trade = TradeRecord(
                trade_id=trade_id,
                position_id=position_id,
                entry_time=datetime.now(),
                direction=direction,
                volume=volume,
                entry_price=entry_price,
                current_price=entry_price,
                entry_strategy=entry_strategy,
                signal_quality=signal_quality,
                market_session=market_session,
                market_conditions=market_conditions or {},
                status=TradeStatus.OPEN
            )
            
            # เพิ่มเข้าระบบติดตาม
            self.metrics_calculator.add_trade(trade)
            
            # บันทึกลงฐานข้อมูล
            self.database.save_trade_record(trade)
            
            self.logger.info(f"📈 บันทึกเทรดใหม่: {trade_id} | {direction} {volume} lots @ {entry_price}")
            
            return trade_id
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการบันทึกเทรดใหม่: {e}")
            return ""
    
    def record_trade_closed(self, trade_id: str, close_price: float, realized_pnl: float,
                          commission: float = 0.0, swap: float = 0.0) -> bool:
        """
        บันทึกการปิดเทรด
        """
        try:
            # ดึงข้อมูลเทรดจาก Active Trades
            if trade_id not in self.metrics_calculator.active_trades:
                self.logger.warning(f"⚠️ ไม่พบเทรด Active: {trade_id}")
                return False
            
            trade = self.metrics_calculator.active_trades[trade_id]
            
            # อัพเดทข้อมูลการปิด
            trade.close_time = datetime.now()
            trade.close_price = close_price
            trade.realized_pnl = realized_pnl
            trade.commission = commission
            trade.swap = swap
            trade.hold_duration = trade.close_time - trade.entry_time
            
            # กำหนดสถานะ
            if realized_pnl > 0:
                trade.status = TradeStatus.CLOSED_PROFIT
            else:
                trade.status = TradeStatus.CLOSED_LOSS
            
            # อัพเดทระบบติดตาม
            self.metrics_calculator.add_trade(trade)  # จะย้ายจาก active ไป recent
            
            # บันทึกลงฐานข้อมูล
            self.database.save_trade_record(trade)
            
            self.logger.info(f"📊 ปิดเทรด: {trade_id} | P&L: {realized_pnl:.2f} | "
                           f"Duration: {trade.hold_duration}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการบันทึกการปิดเทรด: {e}")
            return False
    
    def record_recovery_trade(self, position_id: str, parent_trade_id: str,
                            recovery_method: RecoveryMethod, recovery_level: int,
                            entry_price: float, volume: float, direction: str) -> str:
        """
        บันทึกเทรด Recovery
        """
        try:
            trade_id = f"REC_{parent_trade_id}_{recovery_level}_{int(time.time())}"
            
            trade = TradeRecord(
                trade_id=trade_id,
                position_id=position_id,
                entry_time=datetime.now(),
                direction=direction,
                volume=volume,
                entry_price=entry_price,
                current_price=entry_price,
                entry_strategy=EntryStrategy.MEAN_REVERSION,  # Recovery มักใช้ Mean Reversion
                market_session=MarketSession.ASIAN,  # จะอัพเดทจาก market analyzer
                status=TradeStatus.IN_RECOVERY,
                is_recovery_trade=True,
                parent_trade_id=parent_trade_id,
                recovery_method=recovery_method,
                recovery_level=recovery_level
            )
            
            # เพิ่มเข้าระบบติดตาม
            self.metrics_calculator.add_trade(trade)
            
            # บันทึกลงฐานข้อมูล
            self.database.save_trade_record(trade)
            
            self.logger.info(f"🔄 บันทึกเทรด Recovery: {trade_id} | "
                           f"Method: {recovery_method.value} | Level: {recovery_level}")
            
            return trade_id
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการบันทึกเทรด Recovery: {e}")
            return ""
    
    def record_successful_recovery(self, parent_trade_id: str, recovery_trades: List[str],
                                 final_pnl: float) -> bool:
        """
        บันทึกการ Recovery สำเร็จ
        """
        try:
            # อัพเดทสถานะของ parent trade
            for trade in self.metrics_calculator.recent_trades:
                if trade.trade_id == parent_trade_id:
                    trade.status = TradeStatus.RECOVERED
                    trade.realized_pnl = final_pnl
                    self.database.save_trade_record(trade)
                    break
            
            # อัพเดทสถานะของ recovery trades
            for recovery_trade_id in recovery_trades:
                for trade in self.metrics_calculator.recent_trades:
                    if trade.trade_id == recovery_trade_id:
                        trade.status = TradeStatus.RECOVERED
                        self.database.save_trade_record(trade)
                        break
            
            self.logger.info(f"✅ Recovery สำเร็จ: {parent_trade_id} | Final P&L: {final_pnl:.2f}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการบันทึก Recovery สำเร็จ: {e}")
            return False
    
    def update_position_pnl(self, position_id: str, current_price: float, unrealized_pnl: float) -> None:
        """
        อัพเดท P&L ของ Position ที่เปิดอยู่
        """
        try:
            # หา Trade ID จาก Position ID
            trade_id = None
            for tid, trade in self.metrics_calculator.active_trades.items():
                if trade.position_id == position_id:
                    trade_id = tid
                    break
            
            if trade_id:
                self.metrics_calculator.update_trade(trade_id, current_price, unrealized_pnl)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Position P&L: {e}")
    
    def get_current_performance(self) -> Dict[str, Any]:
        """
        ดึงประสิทธิภาพปัจจุบัน
        """
        try:
            # ดึง Real-time Metrics
            metrics = self.metrics_calculator.calculate_current_metrics()
            
            # เพิ่มข้อมูลเป้าหมาย Volume
            daily_target = (self.settings.daily_volume_target_min + 
                          self.settings.daily_volume_target_max) / 2
            volume_achievement = (metrics['total_volume'] / daily_target) * 100 if daily_target > 0 else 0
            
            # เพิ่ม Recovery Statistics
            recovery_stats = {}
            if self.recovery_engine:
                recovery_stats = self.recovery_engine.get_recovery_statistics()
            
            # เพิ่ม Signal Statistics
            signal_stats = {}
            if self.signal_generator:
                signal_stats = self.signal_generator.get_signal_statistics()
            
            return {
                **metrics,
                "daily_volume_target": daily_target,
                "volume_achievement_rate": round(volume_achievement, 2),
                "recovery_statistics": recovery_stats,
                "signal_statistics": signal_stats,
                "last_update": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงประสิทธิภาพปัจจุบัน: {e}")
            return {"error": str(e)}
    
    def get_session_performance(self, session: MarketSession) -> Dict[str, Any]:
        """
        ดึงประสิทธิภาพตาม Session
        """
        try:
            session_trades = []
            
            # รวบรวมเทรดของ Session นี้
            all_trades = list(self.metrics_calculator.recent_trades) + list(self.metrics_calculator.active_trades.values())
            
            for trade in all_trades:
                if trade.market_session == session:
                    session_trades.append(trade)
            
            if not session_trades:
                return {
                    "session": session.value,
                    "total_trades": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "total_volume": 0.0
                }
            
            # คำนวณสถิติ Session
            total_trades = len(session_trades)
            winning_trades = len([t for t in session_trades if t.realized_pnl > 0])
            total_pnl = sum(t.realized_pnl + t.unrealized_pnl for t in session_trades)
            total_volume = sum(t.volume for t in session_trades)
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            return {
                "session": session.value,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": round(win_rate, 2),
                "total_pnl": round(total_pnl, 2),
                "total_volume": round(total_volume, 2),
                "average_pnl_per_trade": round(total_pnl / total_trades, 2) if total_trades > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงประสิทธิภาพ Session: {e}")
            return {"error": str(e)}
    
    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        ดึงประสิทธิภาพแยกตาม Strategy
        """
        try:
            strategy_stats = {}
            
            # รวบรวมเทรดทั้งหมด
            all_trades = list(self.metrics_calculator.recent_trades) + list(self.metrics_calculator.active_trades.values())
            
            # จัดกลุ่มตาม Strategy
            strategy_groups = defaultdict(list)
            for trade in all_trades:
                strategy_groups[trade.entry_strategy].append(trade)
            
            # คำนวณสถิติแต่ละ Strategy
            for strategy, trades in strategy_groups.items():
                total_trades = len(trades)
                winning_trades = len([t for t in trades if t.realized_pnl > 0])
                total_pnl = sum(t.realized_pnl + t.unrealized_pnl for t in trades)
                total_volume = sum(t.volume for t in trades)
                
                win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
                avg_signal_quality = statistics.mean([t.signal_quality for t in trades]) if trades else 0
                
                strategy_stats[strategy.value] = {
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "win_rate": round(win_rate, 2),
                    "total_pnl": round(total_pnl, 2),
                    "total_volume": round(total_volume, 2),
                    "average_signal_quality": round(avg_signal_quality, 2),
                    "average_pnl_per_trade": round(total_pnl / total_trades, 2) if total_trades > 0 else 0
                }
            
            return strategy_stats
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงประสิทธิภาพ Strategy: {e}")
            return {}
    
    def get_recovery_performance(self) -> Dict[str, Any]:
        """
        ดึงประสิทธิภาพของระบบ Recovery
        """
        try:
            # รวบรวมเทรด Recovery
            recovery_trades = []
            original_trades = []
            
            all_trades = list(self.metrics_calculator.recent_trades) + list(self.metrics_calculator.active_trades.values())
            
            for trade in all_trades:
                if trade.is_recovery_trade:
                    recovery_trades.append(trade)
                elif trade.status in [TradeStatus.CLOSED_LOSS, TradeStatus.RECOVERED]:
                    original_trades.append(trade)
            
            # คำนวณสถิติ Recovery
            total_losing_trades = len([t for t in original_trades if t.status == TradeStatus.CLOSED_LOSS])
            total_recovered_trades = len([t for t in original_trades if t.status == TradeStatus.RECOVERED])
            
            recovery_rate = (total_recovered_trades / max(total_losing_trades + total_recovered_trades, 1)) * 100
            
            # วิเคราะห์ Recovery Methods
            method_stats = defaultdict(lambda: {"count": 0, "success": 0, "total_volume": 0.0})
            
            for trade in recovery_trades:
                if trade.recovery_method:
                    method = trade.recovery_method.value
                    method_stats[method]["count"] += 1
                    method_stats[method]["total_volume"] += trade.volume
                    
                    if trade.status == TradeStatus.RECOVERED:
                        method_stats[method]["success"] += 1
            
            # คำนวณ Success Rate แต่ละ Method
            for method, stats in method_stats.items():
                success_rate = (stats["success"] / max(stats["count"], 1)) * 100
                method_stats[method]["success_rate"] = round(success_rate, 2)
            
            return {
                "total_losing_trades": total_losing_trades,
                "total_recovered_trades": total_recovered_trades,
                "recovery_rate": round(recovery_rate, 2),
                "total_recovery_trades": len(recovery_trades),
                "recovery_methods": dict(method_stats),
                "average_recovery_level": round(
                    statistics.mean([t.recovery_level for t in recovery_trades]) if recovery_trades else 0, 2
                )
            }
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงประสิทธิภาพ Recovery: {e}")
            return {}
    
    async def _create_performance_snapshot(self, timeframe: TimeFrame) -> PerformanceSnapshot:
        """
        สร้าง Performance Snapshot
        """
        try:
            # ดึงข้อมูลปัจจุบัน
            current_metrics = self.metrics_calculator.calculate_current_metrics()
            session_performance = {}
            strategy_performance = self.get_strategy_performance()
            recovery_performance = self.get_recovery_performance()
            
            # สร้าง Snapshot
            snapshot = PerformanceSnapshot(
                timestamp=datetime.now(),
                timeframe=timeframe,
                total_trades=current_metrics["total_trades"],
                winning_trades=current_metrics["winning_trades"],
                losing_trades=current_metrics["losing_trades"],
                recovered_trades=current_metrics["recovered_trades"],
                total_profit=max(0, current_metrics["net_pnl"]),
                total_loss=abs(min(0, current_metrics["net_pnl"])),
                net_profit=current_metrics["net_pnl"],
                total_volume=current_metrics["total_volume"],
                win_rate=current_metrics["win_rate"],
                recovery_rate=current_metrics["recovery_rate"],
                profit_factor=current_metrics["profit_factor"],
                average_win=current_metrics["average_win"],
                average_loss=current_metrics["average_loss"],
                session_performance=session_performance,
                strategy_performance=strategy_performance,
                recovery_performance=recovery_performance
            )
            
            # บันทึกลงฐานข้อมูล
            self.database.save_performance_snapshot(snapshot)
            
            # อัพเดท Current Snapshot
            self.current_snapshot = snapshot
            self.last_snapshot_time = datetime.now()
            
            self.logger.debug(f"📸 สร้าง Performance Snapshot: {timeframe.value}")
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Performance Snapshot: {e}")
            return self.current_snapshot
    
    def _performance_update_loop(self) -> None:
        """
        Loop สำหรับอัพเดท Performance อย่างต่อเนื่อง
        """
        self.logger.info("🔄 เริ่มต้น Performance Update Loop")
        
        while self.tracker_active:
            try:
                # อัพเดท Real-time Data
                if self.position_tracker:
                    positions = self.position_tracker.get_all_positions()
                    
                    for position in positions:
                        self.update_position_pnl(
                            position.get('position_id', ''),
                            position.get('current_price', 0.0),
                            position.get('unrealized_pnl', 0.0)
                        )
                
                # อัพเดททุก 5 วินาที
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Performance Update Loop: {e}")
                time.sleep(10)
    
    def _snapshot_creation_loop(self) -> None:
        """
        Loop สำหรับสร้าง Performance Snapshots
        """
        self.logger.info("📸 เริ่มต้น Snapshot Creation Loop")
        
        while self.tracker_active:
            try:
                current_time = datetime.now()
                
                # สร้าง Hourly Snapshot ทุกชั่วโมง
                if current_time.minute == 0 and current_time.second < 30:
                    asyncio.run(self._create_performance_snapshot(TimeFrame.HOURLY))
                
                # สร้าง Daily Snapshot ทุกวันเที่ยงคืน
                if current_time.hour == 0 and current_time.minute == 0 and current_time.second < 30:
                    asyncio.run(self._create_performance_snapshot(TimeFrame.DAILY))
                
                # รอ 30 วินาที
                time.sleep(30)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Snapshot Creation Loop: {e}")
                time.sleep(60)
    
    def stop_performance_tracker(self) -> None:
        """
        หยุดการทำงานของ Performance Tracker
        """
        self.logger.info("🛑 หยุด Performance Tracker System")
        
        self.tracker_active = False
        
        # รอให้ Threads จบ
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=10)
        
        if self.snapshot_thread and self.snapshot_thread.is_alive():
            self.snapshot_thread.join(timeout=5)
        
        # สร้าง Final Snapshot
        try:
            asyncio.run(self._create_performance_snapshot(TimeFrame.REAL_TIME))
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Final Snapshot: {e}")
        
        self.logger.info("✅ Performance Tracker System หยุดแล้ว")
    
    def get_tracker_statistics(self) -> Dict[str, Any]:
        """
        ดึงสถิติการทำงานของ Performance Tracker
        """
        return {
            "tracker_active": self.tracker_active,
            "total_analysis_runs": self.total_analysis_runs,
            "last_snapshot_time": self.last_snapshot_time.isoformat(),
            "active_trades_count": len(self.metrics_calculator.active_trades),
            "recent_trades_count": len(self.metrics_calculator.recent_trades),
            "database_path": self.database.db_path,
            "current_snapshot_timeframe": self.current_snapshot.timeframe.value
        }

# === GLOBAL PERFORMANCE TRACKER INSTANCE ===
_global_performance_tracker: Optional[PerformanceTracker] = None

def get_performance_tracker() -> PerformanceTracker:
    """
    ดึง PerformanceTracker แบบ Singleton
    """
    global _global_performance_tracker
    if _global_performance_tracker is None:
        _global_performance_tracker = PerformanceTracker()
    return _global_performance_tracker

# === CONVENIENCE FUNCTIONS ===
def record_trade_entry(position_id: str, entry_strategy: EntryStrategy, 
                      entry_price: float, volume: float, direction: str) -> str:
    """
    ฟังก์ชันสะดวกสำหรับบันทึกการเปิดเทรด
    """
    tracker = get_performance_tracker()
    return tracker.record_trade_opened(position_id, entry_strategy, entry_price, volume, direction)

def record_trade_exit(trade_id: str, close_price: float, realized_pnl: float) -> bool:
    """
    ฟังก์ชันสะดวกสำหรับบันทึกการปิดเทรด
    """
    tracker = get_performance_tracker()
    return tracker.record_trade_closed(trade_id, close_price, realized_pnl)

def get_current_stats() -> Dict[str, Any]:
    """
    ฟังก์ชันสะดวกสำหรับดึงสถิติปัจจุบัน
    """
    tracker = get_performance_tracker()
    return tracker.get_current_performance()

def get_recovery_stats() -> Dict[str, Any]:
    """
    ฟังก์ชันสะดวกสำหรับดึงสถิติ Recovery
    """
    tracker = get_performance_tracker()
    return tracker.get_recovery_performance()

async def main():
    """
    ทดสอบการทำงานของ Performance Tracker
    """
    print("🧪 ทดสอบ Performance Tracker")
    
    tracker = get_performance_tracker()
    
    try:
        await tracker.start_performance_tracker()
        
        # สร้างเทรดทดสอบ
        trade_id = tracker.record_trade_opened(
            position_id="TEST_POS_001",
            entry_strategy=EntryStrategy.TREND_FOLLOWING,
            entry_price=2000.0,
            volume=0.1,
            direction="BUY",
            signal_quality=85.0
        )
        
        print(f"✅ สร้างเทรดทดสอบ: {trade_id}")
        
        # รัน 10 วินาที
        await asyncio.sleep(10)
        
        # อัพเดท P&L
        tracker.update_position_pnl("TEST_POS_001", 2010.0, 100.0)
        
        await asyncio.sleep(5)
        
        # ปิดเทรด
        tracker.record_trade_closed(trade_id, 2010.0, 100.0)
        
        # แสดงสถิติ
        current_performance = tracker.get_current_performance()
        print(f"📊 ประสิทธิภาพปัจจุบัน:")
        print(json.dumps(current_performance, indent=2, ensure_ascii=False))
        
        # แสดงสถิติ Strategy
        strategy_performance = tracker.get_strategy_performance()
        print(f"🎯 ประสิทธิภาพ Strategy:")
        print(json.dumps(strategy_performance, indent=2, ensure_ascii=False))
        
        # แสดงสถิติ Recovery
        recovery_performance = tracker.get_recovery_performance()
        print(f"🔄 ประสิทธิภาพ Recovery:")
        print(json.dumps(recovery_performance, indent=2, ensure_ascii=False))
        
    finally:
        tracker.stop_performance_tracker()

if __name__ == "__main__":
    asyncio.run(main())