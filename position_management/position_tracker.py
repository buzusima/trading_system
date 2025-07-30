#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSITION TRACKER - Real MT5 Position Management System
====================================================
ระบบจัดการตำแหน่งการเทรดแบบครอบคลุม สำหรับ Live Trading
รองรับการติดตาม pairing, correlation, และ portfolio management

🎯 FEATURES:
- Real-time position tracking from MT5
- Intelligent position pairing and correlation
- Portfolio balance management
- Risk exposure calculation
- Profit optimization strategies
- Performance analytics
- Position lifecycle management
"""

import MetaTrader5 as mt5
import threading
import time
import statistics
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import json

class PositionType(Enum):
    """ประเภท Position"""
    BUY = "BUY"
    SELL = "SELL"
    HEDGE = "HEDGE"
    RECOVERY = "RECOVERY"
    GRID = "GRID"

class PositionStatus(Enum):
    """สถานะ Position"""
    OPEN = "OPEN"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    CLOSED = "CLOSED"
    PENDING_CLOSE = "PENDING_CLOSE"
    ERROR = "ERROR"

class PositionGroup(Enum):
    """กลุม Position"""
    STANDALONE = "STANDALONE"
    PAIRED = "PAIRED"
    GRID_SET = "GRID_SET"
    HEDGE_SET = "HEDGE_SET"
    RECOVERY_SET = "RECOVERY_SET"

class RiskLevel(Enum):
    """ระดับความเสี่ยง"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class Position:
    """ข้อมูล Position แบบละเอียด"""
    ticket: int
    symbol: str
    position_type: PositionType
    volume: float
    open_price: float
    current_price: float
    profit: float
    swap: float
    commission: float
    open_time: datetime
    magic_number: int
    comment: str
    
    # Extended tracking
    status: PositionStatus = PositionStatus.OPEN
    group: PositionGroup = PositionGroup.STANDALONE
    group_id: Optional[str] = None
    parent_position: Optional[int] = None
    child_positions: List[int] = field(default_factory=list)
    
    # Risk metrics
    risk_level: RiskLevel = RiskLevel.MEDIUM
    max_profit: float = 0.0
    max_loss: float = 0.0
    drawdown_from_peak: float = 0.0
    
    # Performance tracking
    duration: timedelta = field(default_factory=timedelta)
    pip_movement: float = 0.0
    roi_percent: float = 0.0
    
    # Metadata
    entry_reason: str = ""
    target_profit: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class PositionGroup:
    """กลุม Position ที่เกี่ยวข้องกัน"""
    group_id: str
    group_type: PositionGroup
    positions: List[int] = field(default_factory=list)
    total_volume: float = 0.0
    total_profit: float = 0.0
    net_exposure: float = 0.0
    created_time: datetime = field(default_factory=datetime.now)
    target_profit: float = 0.0
    risk_level: RiskLevel = RiskLevel.MEDIUM

@dataclass
class PortfolioMetrics:
    """ตัวชี้วัดพอร์ตโฟลิโอ"""
    total_positions: int = 0
    total_volume: float = 0.0
    total_profit: float = 0.0
    total_margin: float = 0.0
    free_margin: float = 0.0
    margin_level: float = 0.0
    
    # Exposure metrics
    long_exposure: float = 0.0
    short_exposure: float = 0.0
    net_exposure: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    risk_score: float = 0.0
    
    # Performance metrics
    total_pnl_today: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    last_update: datetime = field(default_factory=datetime.now)

class RealPositionTracker:
    """
    Real Position Tracker - ติดตาม positions จาก MT5 จริง
    """
    
    def __init__(self, symbol: str = "XAUUSD.v"):
        self.symbol = symbol
        self.is_tracking = False
        self.tracking_thread = None
        
        # Position storage
        self.positions: Dict[int, Position] = {}
        self.position_groups: Dict[str, PositionGroup] = {}
        self.closed_positions: List[Position] = []
        
        # Portfolio tracking
        self.portfolio_metrics = PortfolioMetrics()
        self.portfolio_history: deque = deque(maxlen=1000)
        
        # Performance tracking
        self.tracking_start_time = datetime.now()
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Risk management
        self.max_positions = 20
        self.max_exposure = 1000000  # $1M
        self.position_correlation_threshold = 0.8
        
        # Update intervals
        self.update_interval = 1  # seconds
        self.metrics_update_interval = 10  # seconds
        
        print(f"📊 Position Tracker initialized for {symbol}")
    
    def start_tracking(self):
        """เริ่มการติดตาม positions"""
        if self.is_tracking:
            return
        
        self.is_tracking = True
        self.tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.tracking_thread.start()
        
        print("✅ Position tracking started")
    
    def stop_tracking(self):
        """หยุดการติดตาม"""
        self.is_tracking = False
        if self.tracking_thread:
            self.tracking_thread.join(timeout=10)
        
        print("⏹️ Position tracking stopped")
    
    def _tracking_loop(self):
        """Loop หลักของการติดตาม"""
        last_metrics_update = time.time()
        
        while self.is_tracking:
            try:
                # อัพเดท positions
                self._update_positions()
                
                # อัพเดท groups
                self._update_position_groups()
                
                # อัพเดท portfolio metrics (ทุก 10 วินาที)
                if time.time() - last_metrics_update >= self.metrics_update_interval:
                    self._update_portfolio_metrics()
                    last_metrics_update = time.time()
                
                # ตรวจสอบความเสี่ยง
                self._check_risk_levels()
                
                # Log สถานะ
                self._log_tracking_status()
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                print(f"❌ Position tracking error: {e}")
                time.sleep(5)
    
    def _update_positions(self):
        """อัพเดท positions จาก MT5"""
        try:
            # ดึง positions ปัจจุบันจาก MT5
            mt5_positions = mt5.positions_get(symbol=self.symbol)
            if mt5_positions is None:
                mt5_positions = []
            
            current_tickets = set()
            
            for mt5_pos in mt5_positions:
                ticket = mt5_pos.ticket
                current_tickets.add(ticket)
                
                # แปลง position type
                pos_type = PositionType.BUY if mt5_pos.type == mt5.POSITION_TYPE_BUY else PositionType.SELL
                
                # สร้างหรืออัพเดท position
                if ticket in self.positions:
                    # อัพเดท position ที่มีอยู่
                    position = self.positions[ticket]
                    old_profit = position.profit
                    
                    position.current_price = mt5_pos.price_current
                    position.profit = mt5_pos.profit
                    position.swap = mt5_pos.swap
                    position.commission = mt5_pos.commission
                    position.last_update = datetime.now()
                    position.duration = datetime.now() - position.open_time
                    
                    # อัพเดท performance metrics
                    self._update_position_metrics(position, old_profit)
                    
                else:
                    # สร้าง position ใหม่
                    position = Position(
                        ticket=ticket,
                        symbol=mt5_pos.symbol,
                        position_type=pos_type,
                        volume=mt5_pos.volume,
                        open_price=mt5_pos.price_open,
                        current_price=mt5_pos.price_current,
                        profit=mt5_pos.profit,
                        swap=mt5_pos.swap,
                        commission=mt5_pos.commission,
                        open_time=datetime.fromtimestamp(mt5_pos.time),
                        magic_number=mt5_pos.magic,
                        comment=mt5_pos.comment,
                        entry_reason=self._determine_entry_reason(mt5_pos.comment),
                        last_update=datetime.now()
                    )
                    
                    self.positions[ticket] = position
                    self.total_trades += 1
                    
                    print(f"📈 New position tracked: {ticket} - {pos_type.value} {mt5_pos.volume} {mt5_pos.symbol}")
            
            # ตรวจหา positions ที่ปิดแล้ว
            closed_tickets = set(self.positions.keys()) - current_tickets
            for ticket in closed_tickets:
                closed_position = self.positions[ticket]
                closed_position.status = PositionStatus.CLOSED
                
                # บันทึกสถิติ
                if closed_position.profit > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1
                
                # ย้ายไปที่ closed positions
                self.closed_positions.append(closed_position)
                del self.positions[ticket]
                
                print(f"🔒 Position closed: {ticket} - P&L: ${closed_position.profit:.2f}")
                
        except Exception as e:
            print(f"❌ Error updating positions: {e}")
    
    def _update_position_metrics(self, position: Position, old_profit: float):
        """อัพเดทตัวชี้วัดของ position"""
        try:
            # อัพเดท max profit/loss
            if position.profit > position.max_profit:
                position.max_profit = position.profit
            
            if position.profit < position.max_loss:
                position.max_loss = position.profit
            
            # คำนวณ drawdown จากจุดสูงสุด
            if position.max_profit > 0:
                position.drawdown_from_peak = position.max_profit - position.profit
            
            # คำนวณ pip movement
            pip_value = 0.01 if position.symbol == "XAUUSD.v" else 0.0001
            if position.position_type == PositionType.BUY:
                position.pip_movement = (position.current_price - position.open_price) / pip_value
            else:
                position.pip_movement = (position.open_price - position.current_price) / pip_value
            
            # คำนวณ ROI
            if position.volume > 0:
                investment = position.volume * position.open_price
                position.roi_percent = (position.profit / investment) * 100 if investment > 0 else 0
            
            # ประเมินระดับความเสี่ยง
            position.risk_level = self._assess_position_risk(position)
            
        except Exception as e:
            print(f"❌ Error updating position metrics: {e}")
    
    def _determine_entry_reason(self, comment: str) -> str:
        """กำหนดเหตุผลการเข้า position จาก comment"""
        comment_lower = comment.lower()
        
        if "martingale" in comment_lower:
            return "Martingale Recovery"
        elif "grid" in comment_lower:
            return "Grid Trading"
        elif "hedge" in comment_lower:
            return "Hedging"
        elif "average" in comment_lower:
            return "Averaging"
        elif "quick" in comment_lower:
            return "Quick Recovery"
        elif "trend" in comment_lower:
            return "Trend Following"
        elif "reversal" in comment_lower:
            return "Mean Reversion"
        elif "breakout" in comment_lower:
            return "Breakout"
        elif "news" in comment_lower:
            return "News Trading"
        else:
            return "Manual Entry"
    
    def _assess_position_risk(self, position: Position) -> RiskLevel:
        """ประเมินระดับความเสี่ยงของ position"""
        try:
            risk_score = 0
            
            # ขนาดการขาดทุน
            loss_percent = abs(position.profit) / (position.volume * position.open_price) * 100
            if loss_percent > 10:
                risk_score += 3
            elif loss_percent > 5:
                risk_score += 2
            elif loss_percent > 2:
                risk_score += 1
            
            # ระยะเวลาที่ขาดทุน
            if position.profit < 0:
                hours_in_loss = position.duration.total_seconds() / 3600
                if hours_in_loss > 24:
                    risk_score += 2
                elif hours_in_loss > 12:
                    risk_score += 1
            
            # Drawdown จากจุดสูงสุด
            if position.drawdown_from_peak > position.volume * 100:  # $100 per lot
                risk_score += 2
            elif position.drawdown_from_peak > position.volume * 50:
                risk_score += 1
            
            # Volume size
            if position.volume > 1.0:
                risk_score += 1
            if position.volume > 5.0:
                risk_score += 2
            
            # กำหนดระดับความเสี่ยง
            if risk_score >= 6:
                return RiskLevel.CRITICAL
            elif risk_score >= 4:
                return RiskLevel.HIGH
            elif risk_score >= 2:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.LOW
                
        except Exception as e:
            print(f"❌ Error assessing position risk: {e}")
            return RiskLevel.MEDIUM
    
    def _update_position_groups(self):
        """อัพเดทกลุม positions"""
        try:
            # ตรวจหาและจัดกลุม positions ตาม magic number และ comment
            magic_groups = defaultdict(list)
            
            for ticket, position in self.positions.items():
                # จัดกลุมตาม magic number
                if position.magic_number != 0:
                    magic_groups[position.magic_number].append(ticket)
                
                # จัดกลุมตาม comment pattern
                comment = position.comment.lower()
                if "grid" in comment:
                    position.group = PositionGroup.GRID_SET
                elif "hedge" in comment:
                    position.group = PositionGroup.HEDGE_SET
                elif any(word in comment for word in ["martingale", "recovery", "average"]):
                    position.group = PositionGroup.RECOVERY_SET
                
            # สร้าง/อัพเดท position groups
            for magic_number, tickets in magic_groups.items():
                if len(tickets) > 1:  # มากกว่า 1 position ถึงจะเป็น group
                    group_id = f"MAGIC_{magic_number}"
                    
                    if group_id not in self.position_groups:
                        self.position_groups[group_id] = PositionGroup(
                            group_id=group_id,
                            group_type=PositionGroup.PAIRED,
                            created_time=datetime.now()
                        )
                    
                    group = self.position_groups[group_id]
                    group.positions = tickets
                    
                    # คำนวณ metrics ของกลุม
                    total_volume = sum(self.positions[ticket].volume for ticket in tickets)
                    total_profit = sum(self.positions[ticket].profit for ticket in tickets)
                    
                    # คำนวณ net exposure
                    long_volume = sum(
                        self.positions[ticket].volume 
                        for ticket in tickets 
                        if self.positions[ticket].position_type == PositionType.BUY
                    )
                    short_volume = sum(
                        self.positions[ticket].volume 
                        for ticket in tickets 
                        if self.positions[ticket].position_type == PositionType.SELL
                    )
                    
                    group.total_volume = total_volume
                    group.total_profit = total_profit
                    group.net_exposure = long_volume - short_volume
                    
                    # อัพเดท group_id ใน positions
                    for ticket in tickets:
                        self.positions[ticket].group_id = group_id
                        
        except Exception as e:
            print(f"❌ Error updating position groups: {e}")
    
    def _update_portfolio_metrics(self):
        """อัพเดทตัวชี้วัดพอร์ตโฟลิโอ"""
        try:
            # ดึงข้อมูลบัญชี
            account_info = mt5.account_info()
            if not account_info:
                return
            
            # คำนวณ basic metrics
            self.portfolio_metrics.total_positions = len(self.positions)
            self.portfolio_metrics.total_volume = sum(pos.volume for pos in self.positions.values())
            self.portfolio_metrics.total_profit = sum(pos.profit for pos in self.positions.values())
            self.portfolio_metrics.total_margin = account_info.margin
            self.portfolio_metrics.free_margin = account_info.margin_free
            # คำนวณ margin level ใหม่
            if account_info.margin > 0:
                self.portfolio_metrics.margin_level = (account_info.equity / account_info.margin) * 100
            else:
                self.portfolio_metrics.margin_level = 0.0 if account_info.equity == 0 else 99999.0            
            # คำนวณ exposure
            long_volume = sum(
                pos.volume for pos in self.positions.values() 
                if pos.position_type == PositionType.BUY
            )
            short_volume = sum(
                pos.volume for pos in self.positions.values() 
                if pos.position_type == PositionType.SELL
            )
            
            self.portfolio_metrics.long_exposure = long_volume
            self.portfolio_metrics.short_exposure = short_volume
            self.portfolio_metrics.net_exposure = long_volume - short_volume
            
            # คำนวณ performance metrics
            total_trades = self.winning_trades + self.losing_trades
            if total_trades > 0:
                self.portfolio_metrics.win_rate = (self.winning_trades / total_trades) * 100
            
            # คำนวณ P&L วันนี้
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_positions = [pos for pos in self.positions.values() if pos.open_time >= today_start]
            today_closed = [pos for pos in self.closed_positions if pos.open_time >= today_start]
            
            self.portfolio_metrics.total_pnl_today = (
                sum(pos.profit for pos in today_positions) +
                sum(pos.profit for pos in today_closed)
            )
            
            # คำนวณ drawdown
            self._calculate_drawdown()
            
            # คำนวณ risk score
            self.portfolio_metrics.risk_score = self._calculate_portfolio_risk_score()
            
            # บันทึกประวัติ
            self.portfolio_history.append({
                'timestamp': datetime.now(),
                'equity': account_info.equity,
                'balance': account_info.balance,
                'profit': self.portfolio_metrics.total_profit,
                'positions': self.portfolio_metrics.total_positions,
                'margin_level': self.portfolio_metrics.margin_level
            })
            
            self.portfolio_metrics.last_update = datetime.now()
            
        except Exception as e:
            print(f"❌ Error updating portfolio metrics: {e}")
    
    def _calculate_drawdown(self):
        """คำนวณ drawdown"""
        try:
            if len(self.portfolio_history) < 2:
                return
            
            # หา peak equity
            equity_values = [record['equity'] for record in self.portfolio_history]
            peak_equity = max(equity_values)
            current_equity = equity_values[-1]
            
            # คำนวณ current drawdown
            if peak_equity > 0:
                current_drawdown = ((peak_equity - current_equity) / peak_equity) * 100
                self.portfolio_metrics.current_drawdown = max(current_drawdown, 0)
            
            # คำนวณ max drawdown
            max_dd = 0
            peak = equity_values[0]
            
            for equity in equity_values:
                if equity > peak:
                    peak = equity
                else:
                    drawdown = ((peak - equity) / peak) * 100
                    max_dd = max(max_dd, drawdown)
            
            self.portfolio_metrics.max_drawdown = max_dd
            
        except Exception as e:
            print(f"❌ Error calculating drawdown: {e}")
    
    def _calculate_portfolio_risk_score(self) -> float:
        """คำนวณคะแนนความเสี่ยงของพอร์ตโฟลิโอ"""
        try:
            risk_score = 0.0
            
            # Margin level risk
            if self.portfolio_metrics.margin_level < 100:
                risk_score += 50
            elif self.portfolio_metrics.margin_level < 200:
                risk_score += 30
            elif self.portfolio_metrics.margin_level < 500:
                risk_score += 10
            
            # Position count risk
            if self.portfolio_metrics.total_positions > 15:
                risk_score += 20
            elif self.portfolio_metrics.total_positions > 10:
                risk_score += 10
            
            # Exposure risk
            max_exposure = max(self.portfolio_metrics.long_exposure, self.portfolio_metrics.short_exposure)
            if max_exposure > 10:  # มากกว่า 10 lots
                risk_score += 25
            elif max_exposure > 5:
                risk_score += 15
            
            # Drawdown risk
            if self.portfolio_metrics.current_drawdown > 20:
                risk_score += 30
            elif self.portfolio_metrics.current_drawdown > 10:
                risk_score += 15
            
            # Losing positions risk
            losing_positions = sum(1 for pos in self.positions.values() if pos.profit < 0)
            if losing_positions > 10:
                risk_score += 20
            elif losing_positions > 5:
                risk_score += 10
            
            return min(risk_score, 100.0)  # Cap at 100
            
        except Exception as e:
            print(f"❌ Error calculating portfolio risk score: {e}")
            return 50.0
    
    def _check_risk_levels(self):
        """ตรวจสอบระดับความเสี่ยง"""
        try:
            # ตรวจสอบ positions ที่มีความเสี่ยงสูง
            critical_positions = [
                pos for pos in self.positions.values() 
                if pos.risk_level == RiskLevel.CRITICAL
            ]
            
            if critical_positions:
                print(f"🚨 CRITICAL RISK: {len(critical_positions)} positions need attention")
                for pos in critical_positions:
                    print(f"   Position {pos.ticket}: ${pos.profit:.2f} ({pos.duration})")
            
            # ตรวจสอบ portfolio risk
            if self.portfolio_metrics.risk_score > 80:
                print(f"🚨 HIGH PORTFOLIO RISK: Score {self.portfolio_metrics.risk_score:.1f}")
            elif self.portfolio_metrics.risk_score > 60:
                print(f"⚠️ MEDIUM PORTFOLIO RISK: Score {self.portfolio_metrics.risk_score:.1f}")
            
            # ตรวจสอบ margin level (เฉพาะเมื่อมี positions เปิด)
            if self.portfolio_metrics.total_positions > 0 and self.portfolio_metrics.margin_level < 150:
                print(f"🚨 LOW MARGIN LEVEL: {self.portfolio_metrics.margin_level:.1f}%")

        except Exception as e:
            print(f"❌ Error checking risk levels: {e}")
    
    def _log_tracking_status(self):
        """Log สถานะการติดตาม"""
        try:
            current_time = datetime.now()
            
            # Log ทุก 60 วินาที
            if not hasattr(self, '_last_status_log'):
                self._last_status_log = current_time
            
            if (current_time - self._last_status_log).total_seconds() >= 60:
                print(f"\n📊 POSITION TRACKER STATUS - {current_time.strftime('%H:%M:%S')}")
                print(f"🎯 Active Positions: {len(self.positions)}")
                print(f"💰 Total P&L: ${self.portfolio_metrics.total_profit:.2f}")
                print(f"📦 Total Volume: {self.portfolio_metrics.total_volume:.2f} lots")
                print(f"📈 Win Rate: {self.portfolio_metrics.win_rate:.1f}%")
                print(f"⚖️ Margin Level: {self.portfolio_metrics.margin_level:.1f}%")
                print(f"⚠️ Risk Score: {self.portfolio_metrics.risk_score:.1f}")
                
                if self.positions:
                    print("📋 Active Positions Summary:")
                    for ticket, pos in list(self.positions.items())[:5]:  # Show first 5
                        status_emoji = "🟢" if pos.profit >= 0 else "🔴"
                        print(f"  {status_emoji} {ticket}: {pos.position_type.value} {pos.volume} - ${pos.profit:.2f}")
                    
                    if len(self.positions) > 5:
                        print(f"  ... และอีก {len(self.positions) - 5} positions")
                
                if self.position_groups:
                    print(f"👥 Position Groups: {len(self.position_groups)}")
                    for group_id, group in list(self.position_groups.items())[:3]:
                        print(f"  - {group_id}: {len(group.positions)} positions, P&L: ${group.total_profit:.2f}")
                
                print("-" * 80)
                self._last_status_log = current_time
                
        except Exception as e:
            print(f"❌ Error logging tracking status: {e}")
    
    # ===== PUBLIC METHODS =====
    
    def get_position(self, ticket: int) -> Optional[Position]:
        """ดึงข้อมูล position ตาม ticket"""
        return self.positions.get(ticket)
    
    def get_positions_by_type(self, position_type: PositionType) -> List[Position]:
        """ดึง positions ตามประเภท"""
        return [pos for pos in self.positions.values() if pos.position_type == position_type]
    
    def get_losing_positions(self, min_loss: float = 0) -> List[Position]:
        """ดึง positions ที่ขาดทุน"""
        return [
            pos for pos in self.positions.values() 
            if pos.profit < -min_loss
        ]
    
    def get_profitable_positions(self, min_profit: float = 0) -> List[Position]:
        """ดึง positions ที่กำไร"""
        return [
            pos for pos in self.positions.values() 
            if pos.profit > min_profit
        ]
    
    def get_positions_by_risk(self, risk_level: RiskLevel) -> List[Position]:
        """ดึง positions ตามระดับความเสี่ยง"""
        return [pos for pos in self.positions.values() if pos.risk_level == risk_level]
    
    def get_position_groups(self) -> Dict[str, PositionGroup]:
        """ดึงข้อมูลกลุม positions"""
        return self.position_groups.copy()
    
    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """ดึงตัวชี้วัดพอร์ตโฟลิโอ"""
        return self.portfolio_metrics
    
    def get_tracking_stats(self) -> Dict[str, Any]:
        """ดึงสถิติการติดตาม"""
        runtime = datetime.now() - self.tracking_start_time
        
        return {
            'runtime_hours': runtime.total_seconds() / 3600,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': (self.winning_trades / max(self.total_trades, 1)) * 100,
            'active_positions': len(self.positions),
            'closed_positions': len(self.closed_positions),
            'position_groups': len(self.position_groups),
            'current_profit': self.portfolio_metrics.total_profit,
            'max_drawdown': self.portfolio_metrics.max_drawdown,
            'current_drawdown': self.portfolio_metrics.current_drawdown,
            'risk_score': self.portfolio_metrics.risk_score,
            'margin_level': self.portfolio_metrics.margin_level,
            'total_volume': self.portfolio_metrics.total_volume,
            'net_exposure': self.portfolio_metrics.net_exposure
        }

    def calculate_position_correlation(self, ticket1: int, ticket2: int) -> float:
        """คำนวณ correlation ระหว่าง 2 positions"""
        try:
            pos1 = self.positions.get(ticket1)
            pos2 = self.positions.get(ticket2)
            
            if not pos1 or not pos2:
                return 0.0
            
            # Simple correlation based on profit movement direction
            # ในระบบจริงควรใช้ price movement correlation
            
            if pos1.position_type == pos2.position_type:
                return 0.8  # Same direction = high positive correlation
            else:
                return -0.8  # Opposite direction = high negative correlation
                
        except Exception as e:
            print(f"❌ Error calculating correlation: {e}")
            return 0.0
    
    def find_hedging_opportunities(self) -> List[Tuple[int, int, float]]:
        """หาโอกาสในการ hedge positions"""
        try:
            opportunities = []
            losing_positions = self.get_losing_positions(50)  # Loss > $50
            
            for pos in losing_positions:
                # หา position ที่สามารถ hedge ได้
                for other_ticket, other_pos in self.positions.items():
                    if (other_pos.ticket != pos.ticket and 
                        other_pos.position_type != pos.position_type and
                        other_pos.profit > 0):  # Profitable position
                        
                        # คำนวณ hedge ratio
                        hedge_ratio = abs(pos.profit) / other_pos.profit
                        
                        if 0.5 <= hedge_ratio <= 2.0:  # Reasonable hedge ratio
                            opportunities.append((pos.ticket, other_pos.ticket, hedge_ratio))
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Error finding hedging opportunities: {e}")
            return []
    
    def optimize_position_sizes(self) -> Dict[int, float]:
        """เสนอแนะการปรับขนาด positions"""
        try:
            recommendations = {}
            
            for ticket, pos in self.positions.items():
                current_volume = pos.volume
                suggested_volume = current_volume
                
                # ลดขนาดหาก risk สูง
                if pos.risk_level == RiskLevel.CRITICAL:
                    suggested_volume = current_volume * 0.5
                elif pos.risk_level == RiskLevel.HIGH:
                    suggested_volume = current_volume * 0.7
                
                # เพิ่มขนาดหากกำไรดีและ risk ต่ำ
                elif pos.profit > 100 and pos.risk_level == RiskLevel.LOW:
                    suggested_volume = current_volume * 1.2
                
                # ปรับขนาดตาม portfolio risk
                if self.portfolio_metrics.risk_score > 70:
                    suggested_volume *= 0.8
                
                if suggested_volume != current_volume:
                    recommendations[ticket] = suggested_volume
            
            return recommendations
            
        except Exception as e:
            print(f"❌ Error optimizing position sizes: {e}")
            return {}
    
    def get_position_performance_report(self) -> Dict[str, Any]:
        """สร้างรายงานผลการดำเนินงาน"""
        try:
            report = {
                'summary': {
                    'total_positions': len(self.positions),
                    'profitable_positions': len(self.get_profitable_positions()),
                    'losing_positions': len(self.get_losing_positions()),
                    'total_profit': self.portfolio_metrics.total_profit,
                    'win_rate': self.portfolio_metrics.win_rate
                },
                'risk_analysis': {
                    'low_risk': len(self.get_positions_by_risk(RiskLevel.LOW)),
                    'medium_risk': len(self.get_positions_by_risk(RiskLevel.MEDIUM)),
                    'high_risk': len(self.get_positions_by_risk(RiskLevel.HIGH)),
                    'critical_risk': len(self.get_positions_by_risk(RiskLevel.CRITICAL)),
                    'portfolio_risk_score': self.portfolio_metrics.risk_score
                },
                'exposure_analysis': {
                    'long_exposure': self.portfolio_metrics.long_exposure,
                    'short_exposure': self.portfolio_metrics.short_exposure,
                    'net_exposure': self.portfolio_metrics.net_exposure,
                    'total_volume': self.portfolio_metrics.total_volume
                },
                'performance_metrics': {
                    'max_drawdown': self.portfolio_metrics.max_drawdown,
                    'current_drawdown': self.portfolio_metrics.current_drawdown,
                    'margin_level': self.portfolio_metrics.margin_level,
                    'free_margin': self.portfolio_metrics.free_margin
                },
                'top_performers': [],
                'worst_performers': [],
                'recommendations': {
                    'hedging_opportunities': len(self.find_hedging_opportunities()),
                    'size_optimizations': len(self.optimize_position_sizes()),
                    'risk_warnings': []
                }
            }
            
            # Top และ Worst performers
            sorted_positions = sorted(
                self.positions.values(), 
                key=lambda x: x.profit, 
                reverse=True
            )
            
            report['top_performers'] = [
                {
                    'ticket': pos.ticket,
                    'profit': pos.profit,
                    'roi_percent': pos.roi_percent,
                    'duration_hours': pos.duration.total_seconds() / 3600
                }
                for pos in sorted_positions[:5]
            ]
            
            report['worst_performers'] = [
                {
                    'ticket': pos.ticket,
                    'profit': pos.profit,
                    'roi_percent': pos.roi_percent,
                    'duration_hours': pos.duration.total_seconds() / 3600
                }
                for pos in sorted_positions[-5:]
            ]
            
            # Risk warnings
            if self.portfolio_metrics.risk_score > 70:
                report['recommendations']['risk_warnings'].append("High portfolio risk detected")
            
            if self.portfolio_metrics.margin_level < 200:
                report['recommendations']['risk_warnings'].append("Low margin level warning")
            
            critical_positions = self.get_positions_by_risk(RiskLevel.CRITICAL)
            if critical_positions:
                report['recommendations']['risk_warnings'].append(f"{len(critical_positions)} positions in critical risk")
            
            return report
            
        except Exception as e:
            print(f"❌ Error generating performance report: {e}")
            return {}
    
    def export_positions_to_json(self, filename: Optional[str] = None) -> str:
        """Export ข้อมูล positions เป็น JSON"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"positions_export_{timestamp}.json"
            
            export_data = {
                'export_time': datetime.now().isoformat(),
                'portfolio_metrics': {
                    'total_positions': self.portfolio_metrics.total_positions,
                    'total_profit': self.portfolio_metrics.total_profit,
                    'total_volume': self.portfolio_metrics.total_volume,
                    'margin_level': self.portfolio_metrics.margin_level,
                    'risk_score': self.portfolio_metrics.risk_score,
                    'win_rate': self.portfolio_metrics.win_rate
                },
                'positions': [],
                'position_groups': []
            }
            
            # Export positions
            for ticket, pos in self.positions.items():
                export_data['positions'].append({
                    'ticket': ticket,
                    'symbol': pos.symbol,
                    'type': pos.position_type.value,
                    'volume': pos.volume,
                    'open_price': pos.open_price,
                    'current_price': pos.current_price,
                    'profit': pos.profit,
                    'open_time': pos.open_time.isoformat(),
                    'duration_minutes': pos.duration.total_seconds() / 60,
                    'risk_level': pos.risk_level.value,
                    'entry_reason': pos.entry_reason,
                    'roi_percent': pos.roi_percent
                })
            
            # Export position groups
            for group_id, group in self.position_groups.items():
                export_data['position_groups'].append({
                    'group_id': group_id,
                    'type': group.group_type.value,
                    'positions': group.positions,
                    'total_profit': group.total_profit,
                    'net_exposure': group.net_exposure
                })
            
            # Write to file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Positions exported to {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error exporting positions: {e}")
            return ""
    
    def close_positions_by_criteria(self, criteria: Dict[str, Any]) -> List[int]:
        """ปิด positions ตามเงื่อนไข"""
        try:
            closed_tickets = []
            
            for ticket, pos in list(self.positions.items()):
                should_close = False
                
                # ตรวจสอบเงื่อนไขต่างๆ
                if 'min_profit' in criteria and pos.profit >= criteria['min_profit']:
                    should_close = True
                
                if 'max_loss' in criteria and pos.profit <= -criteria['max_loss']:
                    should_close = True
                
                if 'risk_level' in criteria and pos.risk_level.value in criteria['risk_level']:
                    should_close = True
                
                if 'max_duration_hours' in criteria:
                    duration_hours = pos.duration.total_seconds() / 3600
                    if duration_hours >= criteria['max_duration_hours']:
                        should_close = True
                
                if 'position_type' in criteria and pos.position_type.value in criteria['position_type']:
                    should_close = True
                
                if should_close:
                    # ส่งคำสั่งปิด position
                    success = self._close_position(ticket)
                    if success:
                        closed_tickets.append(ticket)
            
            return closed_tickets
            
        except Exception as e:
            print(f"❌ Error closing positions by criteria: {e}")
            return []
    
    def _close_position(self, ticket: int) -> bool:
        """ปิด position ตาม ticket"""
        try:
            position = self.positions.get(ticket)
            if not position:
                return False
            
            # กำหนดทิศทางการปิด
            if position.position_type == PositionType.BUY:
                order_type = mt5.ORDER_TYPE_SELL
            else:
                order_type = mt5.ORDER_TYPE_BUY
            
            # ดึงราคาปัจจุบัน
            tick = mt5.symbol_info_tick(position.symbol)
            if not tick:
                return False
            
            price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
            
            # สร้างคำสั่งปิด
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 3,
                "magic": 888888,
                "comment": f"Auto Close - {position.comment}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # ส่งคำสั่ง
            result = mt5.order_send(close_request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Position closed: {ticket} - Final P&L: ${position.profit:.2f}")
                return True
            else:
                print(f"❌ Failed to close position {ticket}: {result.retcode}")
                return False
                
        except Exception as e:
            print(f"❌ Error closing position {ticket}: {e}")
            return False
    
    def emergency_close_all(self) -> bool:
        """ปิด positions ทั้งหมด (ฉุกเฉิน)"""
        try:
            print("🚨 EMERGENCY: Closing all positions")
            
            closed_count = 0
            total_positions = len(self.positions)
            
            for ticket in list(self.positions.keys()):
                if self._close_position(ticket):
                    closed_count += 1
                time.sleep(0.1)  # Small delay between closes
            
            print(f"🚨 Emergency close completed: {closed_count}/{total_positions} positions closed")
            return closed_count == total_positions
            
        except Exception as e:
            print(f"❌ Error in emergency close: {e}")
            return False

# ===== FACTORY FUNCTIONS =====

def create_position_tracker(symbol: str = "XAUUSD.v") -> RealPositionTracker:
    """สร้าง Position Tracker"""
    try:
        tracker = RealPositionTracker(symbol)
        print(f"✅ Position Tracker created for {symbol}")
        return tracker
    except Exception as e:
        print(f"❌ Failed to create Position Tracker: {e}")
        raise

def create_and_start_tracking(symbol: str = "XAUUSD.v") -> RealPositionTracker:
    """สร้างและเริ่มการติดตาม positions"""
    try:
        tracker = create_position_tracker(symbol)
        tracker.start_tracking()
        print(f"✅ Position tracking started for {symbol}")
        return tracker
    except Exception as e:
        print(f"❌ Failed to start position tracking: {e}")
        raise

# ===== TESTING FUNCTION =====

def test_position_tracker():
    """ทดสอบ Position Tracker"""
    print("🧪 Testing Position Tracker...")
    
    try:
        # สร้างและเริ่มการติดตาม
        tracker = create_and_start_tracking("XAUUSD.v")
        
        # รันทดสอบ 60 วินาที
        print("⏱️ Running 60-second tracking test...")
        import time
        start_time = time.time()
        
        while time.time() - start_time < 60:
            # แสดงสถิติทุก 10 วินาที
            if int(time.time() - start_time) % 10 == 0:
                stats = tracker.get_tracking_stats()
                metrics = tracker.get_portfolio_metrics()
                
                print(f"\n📊 Current Stats:")
                print(f"  Active Positions: {stats['active_positions']}")
                print(f"  Total P&L: ${stats['current_profit']:.2f}")
                print(f"  Win Rate: {stats['win_rate']:.1f}%")
                print(f"  Risk Score: {stats['risk_score']:.1f}")
                print(f"  Margin Level: {stats['margin_level']:.1f}%")
                
                # แสดง positions
                if tracker.positions:
                    print("  Top Positions:")
                    sorted_positions = sorted(
                        tracker.positions.values(), 
                        key=lambda x: x.profit, 
                        reverse=True
                    )[:3]
                    
                    for pos in sorted_positions:
                        emoji = "🟢" if pos.profit >= 0 else "🔴"
                        print(f"    {emoji} {pos.ticket}: ${pos.profit:.2f}")
            
            time.sleep(1)
        
        # สร้างรายงาน
        print("\n📋 Generating performance report...")
        report = tracker.get_position_performance_report()
        
        print("📈 Performance Summary:")
        print(f"  Total Positions: {report['summary']['total_positions']}")
        print(f"  Profitable: {report['summary']['profitable_positions']}")
        print(f"  Losing: {report['summary']['losing_positions']}")
        print(f"  Total Profit: ${report['summary']['total_profit']:.2f}")
        
        print("⚠️ Risk Analysis:")
        risk_analysis = report['risk_analysis']
        print(f"  Low Risk: {risk_analysis['low_risk']}")
        print(f"  Medium Risk: {risk_analysis['medium_risk']}")
        print(f"  High Risk: {risk_analysis['high_risk']}")
        print(f"  Critical Risk: {risk_analysis['critical_risk']}")
        
        # Export ข้อมูล
        print("\n💾 Exporting data...")
        export_file = tracker.export_positions_to_json()
        if export_file:
            print(f"✅ Data exported to {export_file}")
        
        # หยุดการติดตาม
        tracker.stop_tracking()
        
        print("✅ Position Tracker test completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
   # ทดสอบหาก run โดยตรง
   test_position_tracker()