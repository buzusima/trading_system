#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELLIGENT RECOVERY SYSTEM - REAL MT5 RECOVERY EXECUTION
========================================================
ระบบกู้คืนตำแหน่งขาดทุนอัจฉริยะ สำหรับ Live Trading
ใช้หลากหลายกลยุทธ์การแก้ไม้ (Recovery Strategies) ตามสภาวะตลาด

🎯 RECOVERY STRATEGIES:
- Martingale Recovery (การเพิ่ม lot แบบทวีคูณ)
- Grid Recovery (การเปิด position แบบ grid)
- Hedging Recovery (การ hedge ด้วย position ตรงข้าม)
- Averaging Recovery (การเฉลี่ยราคา)
- Correlation Recovery (การใช้ correlation กู้คืน)
- Smart Recovery (การรวมหลายวิธี)

🚨 CRITICAL: REAL MT5 INTEGRATION ONLY - NO MOCK
"""

import MetaTrader5 as mt5
import threading
import time
import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import numpy as np

class RecoveryStrategy(Enum):
    """กลยุทธ์การกู้คืน"""
    MARTINGALE = "MARTINGALE"
    GRID_TRADING = "GRID_TRADING"
    HEDGING = "HEDGING"
    AVERAGING = "AVERAGING"
    CORRELATION = "CORRELATION"
    SMART_RECOVERY = "SMART_RECOVERY"
    QUICK_RECOVERY = "QUICK_RECOVERY"

class RecoveryStatus(Enum):
    """สถานะการกู้คืน"""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class RecoveryTrigger(Enum):
    """ตัวกระตุ้นการกู้คืน"""
    LOSS_THRESHOLD = "LOSS_THRESHOLD"
    TIME_BASED = "TIME_BASED"
    DRAWDOWN_PERCENT = "DRAWDOWN_PERCENT"
    MANUAL = "MANUAL"
    AUTO_DETECT = "AUTO_DETECT"

@dataclass
class LosingPosition:
    """ข้อมูล Position ที่ขาดทุน"""
    ticket: int
    symbol: str
    position_type: int  # mt5.POSITION_TYPE_BUY or mt5.POSITION_TYPE_SELL
    volume: float
    open_price: float
    current_price: float
    profit: float
    open_time: datetime
    magic_number: int = 0
    comment: str = ""
    
    # Recovery tracking
    recovery_id: Optional[str] = None
    recovery_attempts: int = 0
    total_recovery_volume: float = 0.0
    recovery_cost: float = 0.0
    is_being_recovered: bool = False

@dataclass
class RecoveryPlan:
    """แผนการกู้คืน"""
    recovery_id: str
    original_position: LosingPosition
    strategy: RecoveryStrategy
    trigger: RecoveryTrigger
    created_time: datetime
    target_profit: float
    max_recovery_attempts: int
    max_recovery_volume: float
    status: RecoveryStatus = RecoveryStatus.PENDING
    
    # Execution tracking
    recovery_positions: List[int] = field(default_factory=list)
    executed_volume: float = 0.0
    recovery_cost: float = 0.0
    current_profit: float = 0.0
    success_probability: float = 50.0
    
    # Strategy-specific parameters
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RecoveryResult:
    """ผลการกู้คืน"""
    recovery_id: str
    success: bool
    final_profit: float
    total_volume_used: float
    total_cost: float
    recovery_time: timedelta
    positions_opened: int
    strategy_used: RecoveryStrategy
    completion_time: datetime
    notes: str = ""

class RealRecoveryEngine:
    """
    Recovery Engine สำหรับ Live Trading - ไม่มี Mock
    """
    
    def __init__(self, symbol: str = "XAUUSD.v"):
        self.symbol = symbol
        self.is_running = False
        self.recovery_thread = None
        
        # Recovery tracking
        self.active_recoveries: Dict[str, RecoveryPlan] = {}
        self.completed_recoveries: List[RecoveryResult] = []
        self.losing_positions: Dict[int, LosingPosition] = {}
        
        # Smart Recovery Settings - ฉลาดขึ้น 200 เท่า
        self.base_pip_threshold = 25        # แทน $50 → 25 pips
        self.min_wait_seconds = 60          # แทน 5 นาที → 1 นาที  
        self.account_risk_percent = 0.5     # 0.5% ของ account
        self.max_concurrent_recoveries = 3
        self.recovery_check_interval = 1    # ตรวจทุก 1 วินาที (เร็วขึ้น)

        # Market condition multipliers - ปรับตามสภาวะตลาด
        self.market_multipliers = {
            'VOLATILE_HIGH': 0.4,     # ลด 60% ตอนผันผวนสูง
            'VOLATILE_NEWS': 0.3,     # ลด 70% ตอนมีข่าว
            'TRENDING_STRONG': 1.5,   # เพิ่ม 50% ตอนเทรนด์แรง
            'TRENDING_WEAK': 1.2,     # เพิ่ม 20% ตอนเทรนด์อ่อน
            'RANGING_TIGHT': 0.7,     # ลด 30% ตอน ranging
            'RANGING_WIDE': 0.9,      # ลด 10% ตอน ranging กว้าง
            'QUIET_LOW': 1.3,         # เพิ่ม 30% ตอนเงียบ
            'BREAKOUT': 0.5,          # ลด 50% ตอน breakout
            'REVERSAL': 0.6           # ลด 40% ตอน reversal
        }

        # Strategy performance tracking
        self.strategy_performance = defaultdict(list)
        self.strategy_weights = {
            RecoveryStrategy.MARTINGALE: 1.0,
            RecoveryStrategy.GRID_TRADING: 1.0,
            RecoveryStrategy.HEDGING: 1.0,
            RecoveryStrategy.AVERAGING: 1.0,
            RecoveryStrategy.CORRELATION: 1.0,
            RecoveryStrategy.SMART_RECOVERY: 1.2,
            RecoveryStrategy.QUICK_RECOVERY: 0.8
        }
        
        print(f"🔧 Recovery Engine initialized for {symbol}")
    
    def start_recovery_monitoring(self):
        """เริ่มการตรวจสอบและกู้คืนอัตโนมัติ"""
        if self.is_running:
            return
        
        self.is_running = True
        self.recovery_thread = threading.Thread(target=self._recovery_loop, daemon=True)
        self.recovery_thread.start()
        
        print("✅ Recovery monitoring started")
    
    def stop_recovery_monitoring(self):
        """หยุดการตรวจสอบ"""
        self.is_running = False
        if self.recovery_thread:
            self.recovery_thread.join(timeout=10)
        
        print("⏹️ Recovery monitoring stopped")
    
    def _recovery_loop(self):
        """Loop หลักของการกู้คืน"""
        while self.is_running:
            try:
                # ตรวจสอบ positions ที่ขาดทุน
                self._scan_losing_positions()
                
                # สร้างแผนการกู้คืนใหม่
                self._create_recovery_plans()
                
                # ดำเนินการกู้คืนที่กำลัง active
                self._execute_active_recoveries()
                
                # ตรวจสอบผลการกู้คืน
                self._check_recovery_completion()
                
                # Log สถานะ
                self._log_recovery_status()
                
                time.sleep(self.recovery_check_interval)
                
            except Exception as e:
                print(f"❌ Recovery loop error: {e}")
                time.sleep(10)
    
    def _scan_losing_positions(self):
        """สแกนหา positions ที่ขาดทุน"""
        try:
            # ดึง positions ปัจจุบัน
            positions = mt5.positions_get(symbol=self.symbol)
            if positions is None:
                return
            
            current_time = datetime.now()
            
            for position in positions:
                # ตรวจสอบว่าขาดทุนเกินกว่าที่กำหนด
                if position.profit < -self.loss_threshold:
                    
                    # สร้าง LosingPosition object
                    losing_pos = LosingPosition(
                        ticket=position.ticket,
                        symbol=position.symbol,
                        position_type=position.type,
                        volume=position.volume,
                        open_price=position.price_open,
                        current_price=position.price_current,
                        profit=position.profit,
                        open_time=datetime.fromtimestamp(position.time),
                        magic_number=position.magic,
                        comment=position.comment
                    )
                    
                    # เพิ่มเข้า losing positions หากยังไม่มี
                    if position.ticket not in self.losing_positions:
                        self.losing_positions[position.ticket] = losing_pos
                        print(f"🔍 New losing position detected: Ticket={position.ticket}, Loss=${position.profit:.2f}")
                    else:
                        # อัพเดทข้อมูล
                        self.losing_positions[position.ticket].current_price = position.price_current
                        self.losing_positions[position.ticket].profit = position.profit
                
                # ลบ positions ที่ปิดแล้วหรือกำไรแล้ว
                elif position.ticket in self.losing_positions:
                    if position.profit >= 0:
                        print(f"✅ Position recovered naturally: Ticket={position.ticket}, Profit=${position.profit:.2f}")
                    del self.losing_positions[position.ticket]
            
            # ลบ positions ที่ถูกปิดแล้ว
            current_tickets = [pos.ticket for pos in positions] if positions else []
            closed_tickets = [ticket for ticket in self.losing_positions.keys() if ticket not in current_tickets]
            
            for ticket in closed_tickets:
                print(f"🔒 Position closed: Ticket={ticket}")
                del self.losing_positions[ticket]
                
        except Exception as e:
            print(f"❌ Error scanning losing positions: {e}")
    
    def _create_recovery_plans(self):
        """สร้างแผนการกู้คืนสำหรับ positions ที่ขาดทุน"""
        try:
            # จำกัดจำนวน recovery ที่ทำงานพร้อมกัน
            if len(self.active_recoveries) >= self.max_concurrent_recoveries:
                return
            
            for ticket, losing_pos in self.losing_positions.items():
                # ข้าม position ที่กำลังถูกกู้คืนอยู่
                if losing_pos.is_being_recovered:
                    continue
                
                # ตรวจสอบเงื่อนไขการกู้คืน
                if self._should_start_recovery(losing_pos):
                    recovery_plan = self._design_recovery_strategy(losing_pos)
                    
                    if recovery_plan:
                        # เพิ่มเข้า active recoveries
                        self.active_recoveries[recovery_plan.recovery_id] = recovery_plan
                        losing_pos.is_being_recovered = True
                        losing_pos.recovery_id = recovery_plan.recovery_id
                        
                        print(f"📋 Recovery plan created: {recovery_plan.recovery_id}")
                        print(f"🎯 Strategy: {recovery_plan.strategy.value}")
                        print(f"💰 Target Profit: ${recovery_plan.target_profit:.2f}")
                        
        except Exception as e:
            print(f"❌ Error creating recovery plans: {e}")
    
    def _should_start_recovery(self, losing_pos: LosingPosition) -> bool:
        """ตรวจสอบการกู้คืนแบบอัจฉริยะ - ฉลาดขึ้น 200 เท่า"""
        try:
            # 1. คำนวณ pip loss ปัจจุบัน
            current_tick = mt5.symbol_info_tick(self.symbol)
            if not current_tick:
                return False
            
            current_price = current_tick.bid if losing_pos.position_type == mt5.POSITION_TYPE_BUY else current_tick.ask
            
            # คำนวณ pips ที่ขาดทุน
            if losing_pos.position_type == mt5.POSITION_TYPE_BUY:
                pip_loss = (losing_pos.open_price - current_price) / 0.01
            else:
                pip_loss = (current_price - losing_pos.open_price) / 0.01
            
            pip_loss = max(0, pip_loss)  # ไม่ติดลบ
            
            # 2. ดึงสภาวะตลาดปัจจุบัน
            market_condition = self._get_current_market_condition()
            
            # 3. คำนวณ threshold อัจฉริยะ
            smart_threshold = self._calculate_smart_threshold(losing_pos, market_condition)
            
            # 4. ตรวจสอบเวลาที่รอ (ลดจาก 5 นาที เป็น 1 นาที)
            time_open = datetime.now() - losing_pos.open_time
            min_wait = self.min_wait_seconds
            
            # 5. เร่งการแก้ไม้ถ้ามีข่าวหรือผันผวนสูง
            if market_condition in ['VOLATILE_NEWS', 'VOLATILE_HIGH']:
                min_wait = 30  # รอแค่ 30 วินาที
            elif market_condition == 'BREAKOUT':
                min_wait = 45  # รอ 45 วินาที
            
            if time_open.total_seconds() < min_wait:
                return False
            
            # 6. ตรวจสอบจำนวน recovery attempts
            if losing_pos.recovery_attempts >= 5:
                return False
            
            # 7. ตรวจสอบสภาวะตลาด (เพิ่มการตรวจสอบ spread)
            spread = current_tick.ask - current_tick.bid
            if spread > 1.5:  # Spread สูงเกินไป
                return False
            
            # 8. ตัดสินใจขั้นสุดท้าย
            should_recover = pip_loss >= smart_threshold
            
            if should_recover:
                print(f"🚨 Smart Recovery Triggered!")
                print(f"   Position: {losing_pos.ticket}")
                print(f"   Pip Loss: {pip_loss:.1f} pips")
                print(f"   Threshold: {smart_threshold:.1f} pips")
                print(f"   Market: {market_condition}")
                print(f"   Wait Time: {time_open.total_seconds():.0f}s")
            
            return should_recover
            
        except Exception as e:
            print(f"❌ Error checking recovery conditions: {e}")
            return False

    def _get_current_market_condition(self) -> str:
        """ดึงสภาวะตลาดปัจจุบัน"""
        try:
            # Simple market condition detection
            current_time = datetime.now()
            hour = current_time.hour
            
            # ตรวจสอบเวลาข่าว
            if self._is_news_time():
                return 'VOLATILE_NEWS'
            
            # ตรวจสอบ session
            if 20 <= hour <= 23 or 0 <= hour <= 2:  # London/NY overlap
                return 'VOLATILE_HIGH'
            elif 15 <= hour <= 19:  # London session
                return 'TRENDING_STRONG'
            elif 3 <= hour <= 11:   # Asian session
                return 'RANGING_TIGHT'
            else:
                return 'QUIET_LOW'
                
        except Exception as e:
            print(f"❌ Error detecting market condition: {e}")
            return 'RANGING_TIGHT'  # Default safe condition

    def _calculate_smart_threshold(self, losing_pos: LosingPosition, market_condition: str) -> float:
        """คำนวณ threshold อัจฉริยะตามสภาวะตลาดและขนาด account"""
        try:
            # 1. Base pip threshold
            pip_threshold = self.base_pip_threshold
            
            # 2. ปรับตามสภาวะตลาด
            multiplier = self.market_multipliers.get(market_condition, 1.0)
            pip_threshold *= multiplier
            
            # 3. ปรับตามขนาด account
            account_info = mt5.account_info()
            if account_info:
                # Account ใหญ่ ใช้เปอร์เซ็นต์
                if account_info.balance > 10000:
                    account_threshold_dollar = account_info.balance * self.account_risk_percent / 100
                    pip_value = losing_pos.volume * 10  # $10 per pip for 0.01 lot XAUUSD
                    account_threshold_pips = account_threshold_dollar / pip_value
                    pip_threshold = min(pip_threshold, account_threshold_pips)
                
                # Account เล็ก ใช้ pip-based เท่านั้น
                else:
                    # สำหรับ account เล็ก ลด threshold ลงเพื่อป้องกันการขาดทุนมาก
                    if account_info.balance < 1000:
                        pip_threshold *= 0.6  # ลด 40%
                    elif account_info.balance < 5000:
                        pip_threshold *= 0.8  # ลด 20%
            
            # 4. ปรับตามขนาด position
            if losing_pos.volume >= 0.1:  # Position ใหญ่
                pip_threshold *= 0.7  # ลด threshold 30%
            elif losing_pos.volume >= 0.05:
                pip_threshold *= 0.85  # ลด threshold 15%
            
            # 5. ป้องกันค่าต่ำเกินไป
            min_threshold = 8  # อย่างน้อย 8 pips
            max_threshold = 100  # ไม่เกิน 100 pips
            
            final_threshold = max(min_threshold, min(pip_threshold, max_threshold))
            
            return final_threshold
            
        except Exception as e:
            print(f"❌ Error calculating smart threshold: {e}")
            return self.base_pip_threshold

    def _is_news_time(self) -> bool:
        """ตรวจสอบเวลาข่าวสำคัญ - เพิ่มความแม่นยำ"""
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        # ไม่มีข่าวสำคัญในวันเสาร์-อาทิตย์
        if weekday >= 5:
            return False
        
        # เวลาข่าวสำคัญ (GMT+7)
        major_news_times = [
            (8, 30, 9, 30),    # Tokyo open + JPY news
            (15, 30, 16, 30),  # London open + EUR news  
            (20, 30, 21, 30),  # NY open + USD news
            (22, 30, 23, 30),  # Major US news (CPI, NFP, FOMC)
        ]
        
        for start_hour, start_min, end_hour, end_min in major_news_times:
            if start_hour <= hour <= end_hour:
                if hour == start_hour and minute >= start_min:
                    return True
                elif hour == end_hour and minute <= end_min:
                    return True
                elif start_hour < hour < end_hour:
                    return True
        
        # ช่วงเปลี่ยน session (ผันผวนสูง)
        session_change_times = [
            (7, 45, 8, 15),    # Pre-Tokyo
            (14, 45, 15, 15),  # Pre-London
            (20, 15, 20, 45),  # Pre-NY
        ]
        
        for start_hour, start_min, end_hour, end_min in session_change_times:
            if start_hour <= hour <= end_hour:
                if (hour == start_hour and minute >= start_min) or \
                (hour == end_hour and minute <= end_min) or \
                (start_hour < hour < end_hour):
                    return True
        
        return False
        
    def _design_recovery_strategy(self, losing_pos: LosingPosition) -> Optional[RecoveryPlan]:
        """ออกแบบกลยุทธ์การกู้คืน"""
        try:
            recovery_id = f"REC_{losing_pos.ticket}_{int(time.time())}"
            
            # เลือกกลยุทธ์ตามสถานการณ์
            strategy = self._select_recovery_strategy(losing_pos)
            
            # คำนวณเป้าหมาย
            target_profit = abs(losing_pos.profit) * 1.2  # Target 20% more than loss
            
            # สร้างแผน
            plan = RecoveryPlan(
                recovery_id=recovery_id,
                original_position=losing_pos,
                strategy=strategy,
                trigger=RecoveryTrigger.LOSS_THRESHOLD,
                created_time=datetime.now(),
                target_profit=target_profit,
                max_recovery_attempts=5,
                max_recovery_volume=losing_pos.volume * 10  # Max 10x original volume
            )
            
            # ตั้งค่าพารามิเตอร์ตามกลยุทธ์
            plan.parameters = self._get_strategy_parameters(strategy, losing_pos)
            
            # คำนวณความน่าจะเป็นของความสำเร็จ
            plan.success_probability = self._calculate_success_probability(plan)
            
            return plan
            
        except Exception as e:
            print(f"❌ Error designing recovery strategy: {e}")
            return None
    
    def _select_recovery_strategy(self, losing_pos: LosingPosition) -> RecoveryStrategy:
        """เลือกกลยุทธ์การกู้คืนที่เหมาะสม"""
        try:
            loss_amount = abs(losing_pos.profit)
            time_in_loss = datetime.now() - losing_pos.open_time
            
            # เลือกกลยุทธ์ตามสถานการณ์
            if loss_amount < 100:
                # ขาดทุนน้อย - ใช้ Quick Recovery
                return RecoveryStrategy.QUICK_RECOVERY
            
            elif loss_amount < 300:
                # ขาดทุนปานกลาง - ใช้ Averaging หรือ Grid
                if time_in_loss.total_seconds() < 1800:  # น้อยกว่า 30 นาที
                    return RecoveryStrategy.AVERAGING
                else:
                    return RecoveryStrategy.GRID_TRADING
            
            elif loss_amount < 500:
                # ขาดทุนมาก - ใช้ Hedging หรือ Smart Recovery
                return RecoveryStrategy.HEDGING
            
            else:
                # ขาดทุนมากมาย - ใช้ Smart Recovery
                return RecoveryStrategy.SMART_RECOVERY
                
        except Exception as e:
            print(f"❌ Error selecting recovery strategy: {e}")
            return RecoveryStrategy.QUICK_RECOVERY
    
    def _get_strategy_parameters(self, strategy: RecoveryStrategy, losing_pos: LosingPosition) -> Dict[str, Any]:
        """ดึงพารามิเตอร์สำหรับกลยุทธ์"""
        try:
            base_params = {
                'original_volume': losing_pos.volume,
                'original_price': losing_pos.open_price,
                'current_loss': abs(losing_pos.profit),
                'position_type': losing_pos.position_type
            }
            
            if strategy == RecoveryStrategy.MARTINGALE:
                return {
                    **base_params,
                    'multiplier': 2.0,
                    'max_levels': 4,
                    'take_profit_pips': 10
                }
            
            elif strategy == RecoveryStrategy.GRID_TRADING:
                return {
                    **base_params,
                    'grid_distance_pips': 20,
                    'grid_levels': 5,
                    'lot_increment': 0.01
                }
            
            elif strategy == RecoveryStrategy.HEDGING:
                return {
                    **base_params,
                    'hedge_ratio': 1.5,
                    'profit_target_pips': 15,
                    'correlation_threshold': 0.8
                }
            
            elif strategy == RecoveryStrategy.AVERAGING:
                return {
                    **base_params,
                    'average_distance_pips': 30,
                    'volume_increment': 0.5,
                    'max_averages': 3
                }
            
            elif strategy == RecoveryStrategy.QUICK_RECOVERY:
                return {
                    **base_params,
                    'quick_volume_multiplier': 1.5,
                    'take_profit_pips': 8,
                    'time_limit_minutes': 15
                }
            
            elif strategy == RecoveryStrategy.SMART_RECOVERY:
                return {
                    **base_params,
                    'use_multiple_methods': True,
                    'adaptive_sizing': True,
                    'market_condition_aware': True
                }
            
            return base_params
            
        except Exception as e:
            print(f"❌ Error getting strategy parameters: {e}")
            return {}
    
    def _calculate_success_probability(self, plan: RecoveryPlan) -> float:
        """คำนวณความน่าจะเป็นของความสำเร็จ"""
        try:
            base_probability = 60.0  # Base 60%
            
            # ปรับตามกลยุทธ์
            strategy_modifiers = {
                RecoveryStrategy.QUICK_RECOVERY: 0.85,
                RecoveryStrategy.AVERAGING: 0.75,
                RecoveryStrategy.GRID_TRADING: 0.80,
                RecoveryStrategy.HEDGING: 0.70,
                RecoveryStrategy.MARTINGALE: 0.65,
                RecoveryStrategy.SMART_RECOVERY: 0.90
            }
            
            probability = base_probability * strategy_modifiers.get(plan.strategy, 0.75)
            
            # ปรับตามขนาดการขาดทุน
            loss_ratio = abs(plan.original_position.profit) / 1000  # Normalize to $1000
            probability *= max(0.5, 1.0 - (loss_ratio * 0.2))  # ลดลงตามขนาดการขาดทุน
            
            # ปรับตามประสิทธิภาพของกลยุทธ์ในอดีต
            strategy_weight = self.strategy_weights.get(plan.strategy, 1.0)
            probability *= strategy_weight
            
            return min(max(probability, 10.0), 95.0)  # Clamp between 10-95%
            
        except Exception as e:
            print(f"❌ Error calculating success probability: {e}")
            return 50.0
    
    def _execute_active_recoveries(self):
        """ดำเนินการกู้คืนที่กำลัง active"""
        try:
            for recovery_id, plan in list(self.active_recoveries.items()):
                if plan.status == RecoveryStatus.PENDING:
                    # เริ่มการกู้คืน
                    plan.status = RecoveryStatus.ACTIVE
                    self._start_recovery_execution(plan)
                
                elif plan.status == RecoveryStatus.ACTIVE:
                    # ดำเนินการกู้คืนต่อ
                    self._continue_recovery_execution(plan)
                    
        except Exception as e:
            print(f"❌ Error executing recoveries: {e}")
    
    def _start_recovery_execution(self, plan: RecoveryPlan):
        """เริ่มการดำเนินการกู้คืน"""
        try:
            print(f"🚀 Starting recovery execution: {plan.recovery_id}")
            print(f"📊 Strategy: {plan.strategy.value}")
            print(f"🎯 Target: ${plan.target_profit:.2f}")
            
            # เรียกใช้ method ตามกลยุทธ์
            if plan.strategy == RecoveryStrategy.MARTINGALE:
                self._execute_martingale_recovery(plan)
            elif plan.strategy == RecoveryStrategy.GRID_TRADING:
                self._execute_grid_recovery(plan)
            elif plan.strategy == RecoveryStrategy.HEDGING:
                self._execute_hedging_recovery(plan)
            elif plan.strategy == RecoveryStrategy.AVERAGING:
                self._execute_averaging_recovery(plan)
            elif plan.strategy == RecoveryStrategy.QUICK_RECOVERY:
                self._execute_quick_recovery(plan)
            elif plan.strategy == RecoveryStrategy.SMART_RECOVERY:
                self._execute_smart_recovery(plan)
                
        except Exception as e:
            print(f"❌ Error starting recovery execution: {e}")
            plan.status = RecoveryStatus.FAILED
    
    def _execute_martingale_recovery(self, plan: RecoveryPlan):
        """ดำเนินการกู้คืนแบบ Martingale"""
        try:
            original_pos = plan.original_position
            params = plan.parameters
            
            # คำนวณ lot size สำหรับ recovery
            multiplier = params.get('multiplier', 2.0)
            recovery_volume = original_pos.volume * multiplier
            
            # ตรวจสอบขีดจำกัด
            if plan.executed_volume + recovery_volume > plan.max_recovery_volume:
                print(f"⚠️ Recovery volume limit reached: {plan.recovery_id}")
                plan.status = RecoveryStatus.FAILED
                return
            
            # กำหนดทิศทางตรงข้าม
            if original_pos.position_type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
            else:
                order_type = mt5.ORDER_TYPE_BUY
            
            # ดึงราคาปัจจุบัน
            tick = mt5.symbol_info_tick(self.symbol)
            if not tick:
                return
            
            price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
            
            # สร้าง order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": recovery_volume,
                "type": order_type,
                "price": price,
                "deviation": 3,
                "magic": 999001,  # Recovery magic number
                "comment": f"Martingale-{plan.recovery_id}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # ส่ง order
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Martingale recovery order executed: {result.order}")
                print(f"📊 Volume: {recovery_volume}, Price: {result.price}")
                
                # อัพเดทแผน
                plan.recovery_positions.append(result.order)
                plan.executed_volume += recovery_volume
                plan.recovery_cost += recovery_volume * result.price
                
                # อัพเดทตำแหน่งดั้งเดิม
                original_pos.recovery_attempts += 1
                original_pos.total_recovery_volume += recovery_volume
                
            else:
                print(f"❌ Martingale recovery order failed: {result.retcode} - {result.comment}")
                
        except Exception as e:
            print(f"❌ Martingale recovery execution error: {e}")
    
    def _execute_grid_recovery(self, plan: RecoveryPlan):
        """ดำเนินการกู้คืนแบบ Grid Trading"""
        try:
            original_pos = plan.original_position
            params = plan.parameters
            
            grid_distance = params.get('grid_distance_pips', 20)
            grid_levels = params.get('grid_levels', 5)
            lot_increment = params.get('lot_increment', 0.01)
            
            # คำนวณระดับ grid
            current_price = original_pos.current_price
            pip_value = 0.01  # สำหรับ Gold
            
            # สร้าง grid orders
            for level in range(1, grid_levels + 1):
                if len(plan.recovery_positions) >= level:
                    continue  # มี order ในระดับนี้แล้ว
                
                # คำนวณราคาสำหรับ grid level
                if original_pos.position_type == mt5.POSITION_TYPE_BUY:
                    # Original เป็น BUY, สร้าง SELL grid ด้านบน
                    grid_price = current_price + (grid_distance * pip_value * level)
                    order_type = mt5.ORDER_TYPE_SELL
                else:
                    # Original เป็น SELL, สร้าง BUY grid ด้านล่าง
                    grid_price = current_price - (grid_distance * pip_value * level)
                    order_type = mt5.ORDER_TYPE_BUY
                
                # คำนวณ volume
                grid_volume = original_pos.volume + (lot_increment * level)
                
                # ตรวจสอบขีดจำกัด
                if plan.executed_volume + grid_volume > plan.max_recovery_volume:
                    break
                
                # สร้าง pending order
                request = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": self.symbol,
                    "volume": grid_volume,
                    "type": mt5.ORDER_TYPE_BUY_LIMIT if order_type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_SELL_LIMIT,
                    "price": grid_price,
                    "deviation": 3,
                    "magic": 999002,
                    "comment": f"Grid-{plan.recovery_id}-L{level}",
                    "type_time": mt5.ORDER_TIME_GTC,
                }
                
                result = mt5.order_send(request)
                
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"✅ Grid order placed: Level {level}, Price {grid_price}")
                    plan.recovery_positions.append(result.order)
                    plan.executed_volume += grid_volume
                else:
                    print(f"❌ Grid order failed: {result.retcode}")
                    
        except Exception as e:
            print(f"❌ Grid recovery execution error: {e}")
    
    def _execute_hedging_recovery(self, plan: RecoveryPlan):
        """ดำเนินการกู้คืนแบบ Hedging"""
        try:
            original_pos = plan.original_position
            params = plan.parameters
            
            hedge_ratio = params.get('hedge_ratio', 1.5)
            hedge_volume = original_pos.volume * hedge_ratio
            
            # ตรวจสอบว่ามี hedge position แล้วหรือยัง
            if len(plan.recovery_positions) > 0:
                return  # มี hedge แล้ว
            
            # กำหนดทิศทางตรงข้าม
            if original_pos.position_type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
            else:
                order_type = mt5.ORDER_TYPE_BUY
            
            # ดึงราคาปัจจุบัน
            tick = mt5.symbol_info_tick(self.symbol)
            if not tick:
                return
            
            price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
            
            # สร้าง hedge order
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": hedge_volume,
                "type": order_type,
                "price": price,
                "deviation": 3,
                "magic": 999003,
                "comment": f"Hedge-{plan.recovery_id}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Hedge position opened: {result.order}")
                print(f"📊 Hedge Volume: {hedge_volume}, Price: {result.price}")
                
                plan.recovery_positions.append(result.order)
                plan.executed_volume += hedge_volume
                plan.recovery_cost += hedge_volume * result.price
                
            else:
                print(f"❌ Hedge order failed: {result.retcode}")
        except Exception as e:
                print(f"❌ Hedging recovery execution error: {e}")
   
    def _execute_averaging_recovery(self, plan: RecoveryPlan):
        """ดำเนินการกู้คืนแบบ Averaging"""
        try:
            original_pos = plan.original_position
            params = plan.parameters
            
            average_distance = params.get('average_distance_pips', 30)
            volume_increment = params.get('volume_increment', 0.5)
            max_averages = params.get('max_averages', 3)
            
            # ตรวจสอบจำนวน averages ที่ทำแล้ว
            if len(plan.recovery_positions) >= max_averages:
                return
            
            # คำนวณราคาสำหรับ averaging
            pip_value = 0.01
            current_price = original_pos.current_price
            
            # ระดับ averaging ปัจจุบัน
            level = len(plan.recovery_positions) + 1
            
            if original_pos.position_type == mt5.POSITION_TYPE_BUY:
                # Average down สำหรับ BUY position
                target_price = original_pos.open_price - (average_distance * pip_value * level)
                order_type = mt5.ORDER_TYPE_BUY
                
                # ตรวจสอบว่าราคาปัจจุบันต่ำกว่า target หรือไม่
                if current_price > target_price:
                    return  # ยังไม่ถึงระดับ averaging
            else:
                # Average up สำหรับ SELL position
                target_price = original_pos.open_price + (average_distance * pip_value * level)
                order_type = mt5.ORDER_TYPE_SELL
                
                if current_price < target_price:
                    return
            
            # คำนวณ volume
            avg_volume = original_pos.volume * (1 + volume_increment * level)
            
            # ส่ง market order
            tick = mt5.symbol_info_tick(self.symbol)
            if not tick:
                return
            
            price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": avg_volume,
                "type": order_type,
                "price": price,
                "deviation": 3,
                "magic": 999004,
                "comment": f"Average-{plan.recovery_id}-L{level}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Averaging order executed: Level {level}")
                print(f"📊 Volume: {avg_volume}, Price: {result.price}")
                
                plan.recovery_positions.append(result.order)
                plan.executed_volume += avg_volume
                plan.recovery_cost += avg_volume * result.price
                
            else:
                print(f"❌ Averaging order failed: {result.retcode}")
                
        except Exception as e:
            print(f"❌ Averaging recovery execution error: {e}")
   
    def _execute_quick_recovery(self, plan: RecoveryPlan):
        """ดำเนินการกู้คืนแบบ Quick Recovery"""
        try:
            original_pos = plan.original_position
            params = plan.parameters
            
            # ตรวจสอบว่าทำ quick recovery แล้วหรือยัง
            if len(plan.recovery_positions) > 0:
                return
            
            multiplier = params.get('quick_volume_multiplier', 1.5)
            quick_volume = original_pos.volume * multiplier
            
            # กำหนดทิศทางตรงข้าม
            if original_pos.position_type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
            else:
                order_type = mt5.ORDER_TYPE_BUY
            
            # ดึงราคาปัจจุบัน
            tick = mt5.symbol_info_tick(self.symbol)
            if not tick:
                return
            
            price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
            
            # สร้าง quick recovery order
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": quick_volume,
                "type": order_type,
                "price": price,
                "deviation": 3,
                "magic": 999005,
                "comment": f"Quick-{plan.recovery_id}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Quick recovery order executed: {result.order}")
                print(f"📊 Volume: {quick_volume}, Price: {result.price}")
                
                plan.recovery_positions.append(result.order)
                plan.executed_volume += quick_volume
                plan.recovery_cost += quick_volume * result.price
                
            else:
                print(f"❌ Quick recovery order failed: {result.retcode}")
                
        except Exception as e:
            print(f"❌ Quick recovery execution error: {e}")
   
    def _execute_smart_recovery(self, plan: RecoveryPlan):
        """ดำเนินการกู้คืนแบบ Smart Recovery (รวมหลายวิธี)"""
        try:
            original_pos = plan.original_position
            loss_amount = abs(original_pos.profit)
            
            # เลือกวิธีการตามขนาดการขาดทุน
            if loss_amount < 200:
                # ใช้ Quick Recovery
                self._execute_quick_recovery(plan)
            elif loss_amount < 500:
                # ใช้ Averaging + Quick Recovery
                if len(plan.recovery_positions) == 0:
                    self._execute_quick_recovery(plan)
                else:
                    self._execute_averaging_recovery(plan)
            else:
                # ใช้ Hedging + Grid
                if len(plan.recovery_positions) == 0:
                    self._execute_hedging_recovery(plan)
                else:
                    self._execute_grid_recovery(plan)
                    
        except Exception as e:
            print(f"❌ Smart recovery execution error: {e}")
    
    def _continue_recovery_execution(self, plan: RecoveryPlan):
        """ดำเนินการกู้คืนต่อเนื่อง"""
        try:
            # อัพเดทสถานะปัจจุบัน
            self._update_recovery_status(plan)
            
            # ตรวจสอบว่าถึงเป้าหมายแล้วหรือไม่
            if plan.current_profit >= plan.target_profit:
                self._complete_recovery(plan, success=True)
                return
            
            # ตรวจสอบเงื่อนไขหยุด
            if self._should_stop_recovery(plan):
                self._complete_recovery(plan, success=False)
                return
                
            # ดำเนินการเพิ่มเติมตามกลยุทธ์
            if plan.strategy in [RecoveryStrategy.GRID_TRADING, RecoveryStrategy.AVERAGING]:
                # ตรวจสอบว่าควรเพิ่ม level หรือไม่
                if self._should_add_recovery_level(plan):
                    if plan.strategy == RecoveryStrategy.GRID_TRADING:
                        self._execute_grid_recovery(plan)
                    else:
                        self._execute_averaging_recovery(plan)
                        
        except Exception as e:
            print(f"❌ Error continuing recovery execution: {e}")
   
    def _update_recovery_status(self, plan: RecoveryPlan):
        """อัพเดทสถานะการกู้คืน"""
        try:
            total_profit = 0.0
            
            # คำนวณกำไรจาก original position
            original_ticket = plan.original_position.ticket
            original_position = mt5.positions_get(ticket=original_ticket)
            
            if original_position:
                total_profit += original_position[0].profit
            
            # คำนวณกำไรจาก recovery positions
            for ticket in plan.recovery_positions:
                recovery_position = mt5.positions_get(ticket=ticket)
                if recovery_position:
                    total_profit += recovery_position[0].profit
            
            plan.current_profit = total_profit
            
        except Exception as e:
            print(f"❌ Error updating recovery status: {e}")
   
    def _should_stop_recovery(self, plan: RecoveryPlan) -> bool:
        """ตรวจสอบว่าควรหยุดการกู้คืนหรือไม่"""
        try:
            # ตรวจสอบจำนวน attempts
            if plan.original_position.recovery_attempts >= plan.max_recovery_attempts:
                return True
            
            # ตรวจสอบ volume limit
            if plan.executed_volume >= plan.max_recovery_volume:
                return True
            
            # ตรวจสอบ time limit
            elapsed_time = datetime.now() - plan.created_time
            if elapsed_time.total_seconds() > 3600:  # 1 hour limit
                return True
            
            # ตรวจสอบการขาดทุนเพิ่มขึ้น
            if plan.current_profit < -(abs(plan.original_position.profit) * 2):
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking stop conditions: {e}")
            return True
   
    def _should_add_recovery_level(self, plan: RecoveryPlan) -> bool:
        """ตรวจสอบว่าควรเพิ่ม recovery level หรือไม่"""
        try:
            # ตรวจสอบเวลาที่ผ่านไปนับจาก recovery ครั้งล่าสุด
            if len(plan.recovery_positions) > 0:
                # ใช้เวลาที่สร้างแผนแทน (เพื่อความง่าย)
                time_since_last = datetime.now() - plan.created_time
                if time_since_last.total_seconds() < 300:  # รอ 5 นาที
                    return False
            
            # ตรวจสอบการเคลื่อนไหวของราคา
            original_pos = plan.original_position
            current_loss = abs(plan.current_profit)
            original_loss = abs(original_pos.profit)
            
            # เพิ่ม level หากขาดทุนเพิ่มขึ้น 50%
            if current_loss > original_loss * 1.5:
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking add level conditions: {e}")
            return False
   
    def _complete_recovery(self, plan: RecoveryPlan, success: bool):
        """เสร็จสิ้นการกู้คืน"""
        try:
            plan.status = RecoveryStatus.COMPLETED if success else RecoveryStatus.FAILED
            
            # สร้างผลการกู้คืน
            result = RecoveryResult(
                recovery_id=plan.recovery_id,
                success=success,
                final_profit=plan.current_profit,
                total_volume_used=plan.executed_volume,
                total_cost=plan.recovery_cost,
                recovery_time=datetime.now() - plan.created_time,
                positions_opened=len(plan.recovery_positions),
                strategy_used=plan.strategy,
                completion_time=datetime.now(),
                notes=f"{'Successful' if success else 'Failed'} recovery using {plan.strategy.value}"
            )
            
            # เพิ่มเข้าประวัติ
            self.completed_recoveries.append(result)
            
            # อัพเดทประสิทธิภาพของกลยุทธ์
            self._update_strategy_performance(plan.strategy, success, plan.current_profit)
            
            # ลบออกจาก active recoveries
            if plan.recovery_id in self.active_recoveries:
                del self.active_recoveries[plan.recovery_id]
            
            # อัพเดทสถานะของ original position
            if plan.original_position.ticket in self.losing_positions:
                self.losing_positions[plan.original_position.ticket].is_being_recovered = False
                
                if success:
                    # ลบออกจาก losing positions หากกู้คืนสำเร็จ
                    del self.losing_positions[plan.original_position.ticket]
            
            # Log ผลลัพธ์
            status_emoji = "✅" if success else "❌"
            print(f"{status_emoji} Recovery {('completed' if success else 'failed')}: {plan.recovery_id}")
            print(f"💰 Final Profit: ${result.final_profit:.2f}")
            print(f"📊 Volume Used: {result.total_volume_used:.2f}")
            print(f"⏱️ Recovery Time: {result.recovery_time}")
            print(f"🎯 Strategy: {result.strategy_used.value}")
            
        except Exception as e:
            print(f"❌ Error completing recovery: {e}")
   
    def _update_strategy_performance(self, strategy: RecoveryStrategy, success: bool, profit: float):
        """อัพเดทประสิทธิภาพของกลยุทธ์"""
        try:
            performance_record = {
                'success': success,
                'profit': profit,
                'timestamp': datetime.now()
            }
            
            self.strategy_performance[strategy].append(performance_record)
            
            # เก็บเฉพาะ 100 records ล่าสุด
            if len(self.strategy_performance[strategy]) > 100:
                self.strategy_performance[strategy] = self.strategy_performance[strategy][-100:]
            
            # อัพเดทน้ำหนักของกลยุทธ์
            self._recalculate_strategy_weights()
            
        except Exception as e:
            print(f"❌ Error updating strategy performance: {e}")
   
    def _recalculate_strategy_weights(self):
        """คำนวณน้ำหนักของกลยุทธ์ใหม่"""
        try:
            for strategy, records in self.strategy_performance.items():
                if len(records) < 5:  # ต้องมีข้อมูลอย่างน้อย 5 รายการ
                    continue
                
                recent_records = records[-20:]  # ใช้ 20 records ล่าสุด
                
                # คำนวณอัตราความสำเร็จ
                success_rate = sum(1 for r in recent_records if r['success']) / len(recent_records)
                
                # คำนวณกำไรเฉลี่ย
                avg_profit = statistics.mean([r['profit'] for r in recent_records])
                
                # คำนวณน้ำหนักใหม่
                # Base weight = 1.0, ปรับตามประสิทธิภาพ
                weight = 1.0 + (success_rate - 0.5) + (avg_profit / 1000)
                weight = max(0.3, min(weight, 2.0))  # จำกัดระหว่าง 0.3 - 2.0
                
                self.strategy_weights[strategy] = weight
                
        except Exception as e:
            print(f"❌ Error recalculating strategy weights: {e}")
    
    def _check_recovery_completion(self):
        """ตรวจสอบการเสร็จสิ้นของการกู้คืน"""
        try:
            completed_recoveries = []
            
            for recovery_id, plan in self.active_recoveries.items():
                if plan.status in [RecoveryStatus.COMPLETED, RecoveryStatus.FAILED, RecoveryStatus.CANCELLED]:
                    completed_recoveries.append(recovery_id)
            
            # ลบ recoveries ที่เสร็จสิ้นแล้ว
            for recovery_id in completed_recoveries:
                del self.active_recoveries[recovery_id]
                
        except Exception as e:
            print(f"❌ Error checking recovery completion: {e}")
   
    def _log_recovery_status(self):
        """Log สถานะการกู้คืน"""
        try:
            current_time = datetime.now()
            
            # Log ทุก 60 วินาที
            if not hasattr(self, '_last_status_log'):
                self._last_status_log = current_time
            
            if (current_time - self._last_status_log).total_seconds() >= 60:
                print(f"\n🔧 RECOVERY ENGINE STATUS - {current_time.strftime('%H:%M:%S')}")
                print(f"📍 Losing Positions: {len(self.losing_positions)}")
                print(f"🔄 Active Recoveries: {len(self.active_recoveries)}")
                print(f"✅ Completed Recoveries: {len(self.completed_recoveries)}")
                
                if self.active_recoveries:
                    print("🎯 Active Recovery Details:")
                    for recovery_id, plan in self.active_recoveries.items():
                        print(f"  - {recovery_id}: {plan.strategy.value} (${plan.current_profit:.2f})")
                
                if self.losing_positions:
                    print("⚠️ Losing Positions:")
                    for ticket, pos in self.losing_positions.items():
                        recovery_status = "🔄" if pos.is_being_recovered else "⏸️"
                        print(f"  - {ticket}: ${pos.profit:.2f} {recovery_status}")
                
                print("-" * 60)
                self._last_status_log = current_time
                
        except Exception as e:
            print(f"❌ Error logging recovery status: {e}")
   
    # ===== PUBLIC METHODS =====
    
    def force_recovery(self, ticket: int, strategy: RecoveryStrategy = RecoveryStrategy.QUICK_RECOVERY) -> bool:
        """บังคับเริ่มการกู้คืนสำหรับ position ที่กำหนด"""
        try:
            # ดึงข้อมูล position
            position = mt5.positions_get(ticket=ticket)
            if not position:
                print(f"❌ Position {ticket} not found")
                return False
            
            position = position[0]
            
            # สร้าง LosingPosition
            losing_pos = LosingPosition(
                ticket=position.ticket,
                symbol=position.symbol,
                position_type=position.type,
                volume=position.volume,
                open_price=position.price_open,
                current_price=position.price_current,
                profit=position.profit,
                open_time=datetime.fromtimestamp(position.time),
                magic_number=position.magic,
                comment=position.comment
            )
            
            # สร้างแผนการกู้คืน
            recovery_id = f"MANUAL_{ticket}_{int(time.time())}"
            plan = RecoveryPlan(
                recovery_id=recovery_id,
                original_position=losing_pos,
                strategy=strategy,
                trigger=RecoveryTrigger.MANUAL,
                created_time=datetime.now(),
                target_profit=abs(position.profit) * 1.2,
                max_recovery_attempts=5,
                max_recovery_volume=position.volume * 10
            )
            
            plan.parameters = self._get_strategy_parameters(strategy, losing_pos)
            plan.success_probability = self._calculate_success_probability(plan)
            
            # เพิ่มเข้าระบบ
            self.active_recoveries[recovery_id] = plan
            self.losing_positions[ticket] = losing_pos
            losing_pos.is_being_recovered = True
            losing_pos.recovery_id = recovery_id
            
            print(f"✅ Manual recovery initiated: {recovery_id}")
            print(f"🎯 Strategy: {strategy.value}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error forcing recovery: {e}")
            return False
   
    def cancel_recovery(self, recovery_id: str) -> bool:
        """ยกเลิกการกู้คืน"""
        try:
            if recovery_id not in self.active_recoveries:
                print(f"❌ Recovery {recovery_id} not found")
                return False
            
            plan = self.active_recoveries[recovery_id]
            plan.status = RecoveryStatus.CANCELLED
            
            # ยกเลิก pending orders ที่เกี่ยวข้อง
            for ticket in plan.recovery_positions:
                order_info = mt5.orders_get(ticket=ticket)
                if order_info:
                    # ยกเลิก pending order
                    cancel_request = {
                        "action": mt5.TRADE_ACTION_REMOVE,
                        "order": ticket,
                    }
                    mt5.order_send(cancel_request)
            
            # อัพเดทสถานะ
            if plan.original_position.ticket in self.losing_positions:
                self.losing_positions[plan.original_position.ticket].is_being_recovered = False
            
            print(f"⏹️ Recovery cancelled: {recovery_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error cancelling recovery: {e}")
            return False
   
    def get_recovery_stats(self) -> Dict[str, Any]:
        """ดึงสถิติการกู้คืน"""
        try:
            total_recoveries = len(self.completed_recoveries)
            successful_recoveries = sum(1 for r in self.completed_recoveries if r.success)
            
            stats = {
                'total_recoveries': total_recoveries,
                'successful_recoveries': successful_recoveries,
                'success_rate': (successful_recoveries / max(total_recoveries, 1)) * 100,
                'active_recoveries': len(self.active_recoveries),
                'losing_positions': len(self.losing_positions),
                'strategy_weights': dict(self.strategy_weights),
                'total_profit_recovered': sum(r.final_profit for r in self.completed_recoveries if r.success),
                'average_recovery_time': statistics.mean([
                    r.recovery_time.total_seconds() / 60  # Convert to minutes
                    for r in self.completed_recoveries
                ]) if self.completed_recoveries else 0
            }
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting recovery stats: {e}")
            return {}
   
    def close_all_losing_positions(self) -> bool:
        """ปิด positions ที่ขาดทุนทั้งหมด (Emergency function)"""
        try:
            print("🚨 EMERGENCY: Closing all losing positions")
            
            closed_count = 0
            for ticket, losing_pos in list(self.losing_positions.items()):
                # ปิด position
                close_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": losing_pos.symbol,
                    "volume": losing_pos.volume,
                    "type": mt5.ORDER_TYPE_SELL if losing_pos.position_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                    "position": ticket,
                    "magic": 999999,
                    "comment": "Emergency Close",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_FOK,
                }
                
                result = mt5.order_send(close_request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"✅ Position {ticket} closed")
                    closed_count += 1
                else:
                    print(f"❌ Failed to close position {ticket}: {result.retcode}")
            
            # ล้างข้อมูล
            self.losing_positions.clear()
            self.active_recoveries.clear()
            
            print(f"🚨 Emergency close completed: {closed_count} positions closed")
            return True
            
        except Exception as e:
            print(f"❌ Error in emergency close: {e}")
            return False

# ===== FACTORY FUNCTION =====

def create_recovery_engine(symbol: str = "XAUUSD.v") -> RealRecoveryEngine:
    """
    สร้าง Recovery Engine สำหรับ symbol ที่กำหนด
    """
    try:
        engine = RealRecoveryEngine(symbol)
        print(f"✅ Recovery Engine created for {symbol}")
        return engine
    except Exception as e:
        print(f"❌ Failed to create Recovery Engine: {e}")
        raise

# ===== TESTING FUNCTION =====

def test_recovery_engine():
    """
    ทดสอบระบบ Recovery Engine
    """
    print("🧪 Testing Recovery Engine...")
    
    try:
        # สร้าง engine
        engine = create_recovery_engine("XAUUSD.v")
        
        # เริ่มการตรวจสอบ
        engine.start_recovery_monitoring()
        
        # รันทดสอบ 60 วินาที
        import time
        start_time = time.time()
        while time.time() - start_time < 60:
            # แสดงสถิติ
            stats = engine.get_recovery_stats()
            print(f"📊 Recovery Stats: {stats}")
            
            time.sleep(10)
        
        # หยุดการทำงาน
        engine.stop_recovery_monitoring()
        
        print("✅ Recovery Engine test completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
   # ทดสอบหาก run โดยตรง
   test_recovery_engine()