#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRADING PARAMETERS - พารามิเตอร์การเทรดหลัก (COMPLETE)
===================================================
กำหนดพารามิเตอร์การเทรดทั้งหมดสำหรับระบบ Intelligent Gold Trading System
ฉบับสมบูรณ์แบบที่รองรับการจัดการพารามิเตอร์ขั้นสูง

🎯 ฟีเจอร์หลัก:
- Multi-strategy parameter management
- Session-based parameter optimization
- Risk management parameters
- Recovery method configurations
- Performance-based parameter tuning
- Real-time parameter adjustment
- Parameter validation และ constraints
- Historical parameter tracking
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
from collections import defaultdict

# ===============================
# ENUMS และ CONSTANTS
# ===============================

class EntryStrategy(Enum):
    """กลยุทธ์การเข้าออร์เดอร์"""
    TREND_FOLLOWING = "TREND_FOLLOWING"        # ตามเทรนด์
    MEAN_REVERSION = "MEAN_REVERSION"          # กลับค่าเฉลี่ย
    BREAKOUT_FALSE = "BREAKOUT_FALSE"          # หลอกเบรค
    NEWS_REACTION = "NEWS_REACTION"            # ปฏิกิริยาข่าว
    SCALPING_ENGINE = "SCALPING_ENGINE"        # สกัลปิ้ง
    GRID_TRADING = "GRID_TRADING"              # เทรด Grid
    ARBITRAGE = "ARBITRAGE"                    # Arbitrage

class RecoveryMethod(Enum):
    """วิธีการ Recovery (แก้ไม้)"""
    MARTINGALE_SMART = "MARTINGALE_SMART"          # Martingale อัจฉริยะ
    GRID_INTELLIGENT = "GRID_INTELLIGENT"          # Grid ยืดหยุ่น
    HEDGING_ADVANCED = "HEDGING_ADVANCED"          # Hedging ขั้นสูง
    AVERAGING_INTELLIGENT = "AVERAGING_INTELLIGENT" # เฉลี่ยราคาอัจฉริยะ
    CORRELATION_RECOVERY = "CORRELATION_RECOVERY"   # Recovery แบบ correlation
    DYNAMIC_HEDGING = "DYNAMIC_HEDGING"            # Hedging แบบไดนามิก
    PYRAMID_RECOVERY = "PYRAMID_RECOVERY"          # Recovery แบบ Pyramid

class PositionSizing(Enum):
    """วิธีการคำนวณขนาดตำแหน่ง"""
    FIXED = "FIXED"                    # ขนาดคงที่
    PERCENTAGE = "PERCENTAGE"          # เปอร์เซ็นต์ของ balance
    VOLATILITY_BASED = "VOLATILITY_BASED"  # ตาม volatility
    KELLY_CRITERION = "KELLY_CRITERION"    # Kelly Criterion
    ADAPTIVE = "ADAPTIVE"              # ปรับตามสถานการณ์
    BALANCE_FRACTION = "BALANCE_FRACTION"  # เศษส่วนของ balance
    EQUITY_CURVE = "EQUITY_CURVE"      # ตาม equity curve

class RiskProfile(Enum):
    """โปรไฟล์ความเสี่ยง"""
    CONSERVATIVE = "CONSERVATIVE"      # อนุรักษ์นิยม
    MODERATE = "MODERATE"             # ปานกลาง
    AGGRESSIVE = "AGGRESSIVE"         # ก้าวร้าว
    HIGH_FREQUENCY = "HIGH_FREQUENCY" # ความถี่สูง (สำหรับ rebate)
    ULTRA_CONSERVATIVE = "ULTRA_CONSERVATIVE"  # อนุรักษ์นิยมมาก
    EXTREME_AGGRESSIVE = "EXTREME_AGGRESSIVE"  # ก้าวร้าวมาก

class MarketCondition(Enum):
    """สภาวะตลาด"""
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    QUIET = "QUIET"
    NEWS_IMPACT = "NEWS_IMPACT"
    WEEKEND = "WEEKEND"

# ===============================
# PARAMETER CLASSES
# ===============================

@dataclass
class StrategyParameters:
    """พารามิเตอร์สำหรับกลยุทธ์เฉพาะ"""
    strategy: EntryStrategy
    enabled: bool = True
    weight: float = 1.0                    # น้ำหนักในการเลือกใช้
    confidence_threshold: float = 0.5      # threshold ขั้นต่ำ
    max_signals_per_hour: int = 10         # สัญญาณสูงสุดต่อชั่วโมง
    cooldown_seconds: int = 30             # cooldown ระหว่างสัญญาณ
    
    # Strategy-specific parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Performance tracking
    signals_generated: int = 0
    signals_executed: int = 0
    successful_trades: int = 0
    total_profit: float = 0.0
    last_used: Optional[datetime] = None
    
    def get_success_rate(self) -> float:
        """คำนวณ success rate"""
        if self.signals_executed == 0:
            return 0.0
        return (self.successful_trades / self.signals_executed) * 100
    
    def get_average_profit(self) -> float:
        """คำนวณกำไรเฉลี่ย"""
        if self.successful_trades == 0:
            return 0.0
        return self.total_profit / self.successful_trades
    
    def update_performance(self, profit: float, success: bool):
        """อัพเดทผลงาน"""
        self.signals_executed += 1
        if success:
            self.successful_trades += 1
        self.total_profit += profit
        self.last_used = datetime.now()

@dataclass
class RecoveryParameters:
    """พารามิเตอร์ Recovery"""
    method: RecoveryMethod
    enabled: bool = True
    max_levels: int = 10               # จำนวนระดับสูงสุด
    multiplier: float = 1.5            # ตัวคูณ volume
    step_pips: float = 10.0            # ระยะห่างระหว่างระดับ
    
    # Advanced parameters
    dynamic_multiplier: bool = True     # ปรับ multiplier ตาม market
    correlation_factor: float = 0.8    # ปัจจัย correlation
    time_decay: float = 0.1            # การลดลงตามเวลา
    volatility_adjustment: bool = True  # ปรับตาม volatility
    
    # Risk controls
    max_recovery_amount: float = 1000.0  # จำนวนเงินสูงสุดใน recovery
    recovery_timeout_hours: int = 24    # timeout สำหรับ recovery
    
    # Performance tracking
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    total_recovery_profit: float = 0.0
    average_recovery_time: float = 0.0
    
    def get_recovery_success_rate(self) -> float:
        """คำนวณ success rate ของ recovery"""
        if self.recovery_attempts == 0:
            return 0.0
        return (self.successful_recoveries / self.recovery_attempts) * 100

@dataclass
class PositionSizingParameters:
    """พารามิเตอร์การคำนวณขนาดตำแหน่ง"""
    method: PositionSizing = PositionSizing.ADAPTIVE
    base_volume: float = 0.01              # ขนาดพื้นฐาน
    min_volume: float = 0.01               # ขนาดขั้นต่ำ
    max_volume: float = 10.0               # ขนาดสูงสุด
    volume_step: float = 0.01              # ขั้นการเพิ่ม
    
    # Risk-based sizing
    risk_per_trade_percent: float = 1.0    # % ของ balance ต่อเทรด
    max_risk_per_day_percent: float = 5.0  # % ของ balance ต่อวัน
    
    # Adaptive parameters
    confidence_multiplier: float = 2.0     # คูณด้วย confidence
    volatility_factor: float = 0.5         # ปัจจัย volatility
    session_multiplier: Dict[str, float] = field(default_factory=lambda: {
        "ASIAN": 0.8,
        "LONDON": 1.2,
        "NEW_YORK": 1.5,
        "OVERLAP": 1.8
    })
    
    # Kelly Criterion parameters
    kelly_fraction: float = 0.25           # เศษส่วน Kelly
    kelly_lookback: int = 100              # จำนวนเทรดที่ดูย้อนหลัง
    
    # Equity curve parameters
    equity_smooth_period: int = 20         # period สำหรับ smooth equity
    equity_threshold: float = 0.95         # threshold สำหรับลด size
    
    def calculate_position_size(self, account_balance: float, confidence: float, 
                                volatility: float, session: str = "ASIAN") -> float:
        """คำนวณขนาดตำแหน่ง"""
        base_size = self.base_volume
        
        if self.method == PositionSizing.FIXED:
            return base_size
        
        elif self.method == PositionSizing.PERCENTAGE:
            size = account_balance * (self.risk_per_trade_percent / 100) / 1000  # Assume $1000 per lot
            
        elif self.method == PositionSizing.VOLATILITY_BASED:
            volatility_adj = 1.0 / max(volatility, 0.5)
            size = base_size * volatility_adj
            
        elif self.method == PositionSizing.ADAPTIVE:
            # Combine multiple factors
            confidence_adj = 0.5 + (confidence * self.confidence_multiplier)
            volatility_adj = 1.0 / max(volatility * self.volatility_factor, 0.5)
            session_adj = self.session_multiplier.get(session, 1.0)
            
            size = base_size * confidence_adj * volatility_adj * session_adj
            
        else:
            size = base_size
        
        # Apply limits
        return max(self.min_volume, min(size, self.max_volume))

@dataclass
class TechnicalParameters:
    """พารามิเตอร์ Technical Analysis"""
    
    # Moving Averages
    ma_fast_period: int = 10
    ma_slow_period: int = 20
    ma_signal_period: int = 5
    ma_method: str = "SMA"                 # SMA, EMA, WMA
    
    # RSI Parameters
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    rsi_signal_threshold: float = 5.0      # ระยะห่างจาก extreme levels
    
    # Bollinger Bands
    bb_period: int = 20
    bb_deviation: float = 2.0
    bb_price_source: str = "CLOSE"         # CLOSE, OPEN, HIGH, LOW
    
    # ADX Parameters
    adx_period: int = 14
    adx_trending_threshold: float = 25.0
    adx_ranging_threshold: float = 20.0
    adx_strong_threshold: float = 40.0
    
    # ATR Parameters
    atr_period: int = 14
    atr_multiplier: float = 2.0
    atr_smoothing: str = "RMA"             # SMA, EMA, RMA
    
    # MACD Parameters
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    macd_price_source: str = "CLOSE"
    
    # Stochastic Parameters
    stoch_k_period: int = 14
    stoch_d_period: int = 3
    stoch_smooth: int = 3
    stoch_overbought: float = 80.0
    stoch_oversold: float = 20.0
    
    # Support/Resistance
    sr_lookback: int = 100                 # จำนวน bars ที่ดูย้อนหลัง
    sr_touch_tolerance: float = 0.1        # tolerance ในการแตะ level
    sr_strength_threshold: int = 3         # จำนวนครั้งที่แตะขั้นต่ำ
    
    # Volume Analysis
    volume_sma_period: int = 20
    volume_spike_threshold: float = 2.0    # เท่าของ volume average
    
    # Pattern Recognition
    pattern_recognition_enabled: bool = True
    pattern_lookback: int = 50
    pattern_tolerance: float = 0.05

@dataclass
class SessionParameters:
    """พารามิเตอร์เฉพาะ Session"""
    session_name: str
    
    # Timing
    start_hour: int = 0
    start_minute: int = 0
    end_hour: int = 23
    end_minute: int = 59
    
    # Market characteristics
    expected_volatility: str = "MEDIUM"     # LOW, MEDIUM, HIGH, EXTREME
    typical_spread: float = 2.0
    volume_profile: str = "NORMAL"         # LOW, NORMAL, HIGH
    
    # Strategy preferences
    preferred_strategies: List[EntryStrategy] = field(default_factory=list)
    avoided_strategies: List[EntryStrategy] = field(default_factory=list)
    strategy_weights: Dict[EntryStrategy, float] = field(default_factory=dict)
    
    # Risk adjustments
    max_spread: float = 3.0
    position_sizing_multiplier: float = 1.0
    max_positions: int = 10
    risk_multiplier: float = 1.0
    
    # Recovery settings
    preferred_recovery_method: RecoveryMethod = RecoveryMethod.AVERAGING_INTELLIGENT
    recovery_aggressiveness: float = 1.0
    
    # Performance targets
    target_signals_per_hour: int = 5
    target_success_rate: float = 60.0
    
    # News handling
    news_sensitivity: float = 1.0          # ความไวต่อข่าว
    pre_news_stop_minutes: int = 5         # หยุดก่อนข่าวกี่นาที
    post_news_wait_minutes: int = 5        # รอหลังข่าวกี่นาที

@dataclass
class TradingParameters:
    """
    คลาสหลักสำหรับพารามิเตอร์การเทรด - ฉบับสมบูรณ์
    รวบรวมพารามิเตอร์การเทรดทั้งหมดอย่างเป็นระบบ
    """
    
    # === BASIC TRADING SETTINGS ===
    symbol: str = "XAUUSD"
    base_volume: float = 0.01               # ขนาดตำแหน่งเริ่มต้น
    min_volume: float = 0.01                # ขนาดขั้นต่ำ
    max_volume: float = 10.0                # ขนาดสูงสุด
    max_spread: float = 3.0                 # Spread สูงสุดที่ยอมรับ (pips)
    
    # === ENTRY PARAMETERS ===
    signal_cooldown: int = 15               # ช่วงเวลาระหว่างสัญญาณ (วินาที)
    min_confidence: float = 0.5             # Confidence ขั้นต่ำสำหรับเข้าออร์เดอร์
    max_daily_entries: int = 200            # จำนวนการเข้าออร์เดอร์สูงสุดต่อวัน
    entry_slippage_tolerance: float = 0.5   # ความคลาดเคลื่อนราคาที่ยอมรับ
    
    # === STRATEGY MANAGEMENT ===
    strategies: Dict[EntryStrategy, StrategyParameters] = field(default_factory=dict)
    strategy_selection_method: str = "WEIGHTED"  # WEIGHTED, PERFORMANCE, ADAPTIVE
    
    # === RECOVERY MANAGEMENT ===
    recovery_methods: Dict[RecoveryMethod, RecoveryParameters] = field(default_factory=dict)
    recovery_selection_method: str = "MARKET_CONDITION"  # MARKET_CONDITION, PERFORMANCE, FIXED
    
    # === POSITION SIZING ===
    position_sizing: PositionSizingParameters = field(default_factory=PositionSizingParameters)
    
    # === TECHNICAL ANALYSIS ===
    technical_params: TechnicalParameters = field(default_factory=TechnicalParameters)
    
    # === SESSION MANAGEMENT ===
    sessions: Dict[str, SessionParameters] = field(default_factory=dict)
    
    # === VOLUME TARGET SETTINGS ===
    volume_targets: Dict[str, float] = field(default_factory=lambda: {
        "daily_minimum": 50.0,              # lots/วัน ขั้นต่ำ
        "daily_target": 75.0,               # lots/วัน เป้าหมาย
        "daily_maximum": 100.0,             # lots/วัน สูงสุด
        "hourly_target": 4.0,               # lots/ชั่วโมง เฉลี่ย
        "rebate_optimization": True         # เปิดการเพิ่มประสิทธิภาพ rebate
    })
    
    # === RISK MANAGEMENT (แบบไม่จำกัด - เน้น Recovery) ===
    risk_management: Dict[str, Any] = field(default_factory=lambda: {
        "use_stop_loss": False,             # ❌ ห้ามใช้ Stop Loss
        "use_take_profit": False,           # ❌ ห้ามใช้ Take Profit แบบดั้งเดิม
        "recovery_mandatory": True,         # ✅ บังคับใช้ Recovery
        "max_drawdown_warning": 30.0,      # เตือนเมื่อ Drawdown > 30%
        "max_positions_total": 100,        # จำนวนตำแหน่งรวมสูงสุด
        "emergency_stop_enabled": True,     # เปิดใช้การหยุดฉุกเฉิน
        "correlation_limit": 0.8,           # จำกัด correlation ระหว่างตำแหน่ง
        "max_daily_loss": 500.0,           # ขาดทุนสูงสุดต่อวัน ($)
        "max_single_loss": 100.0           # ขาดทุนสูงสุดต่อ position ($)
    })
    
    # === PERFORMANCE OPTIMIZATION ===
    performance_settings: Dict[str, Any] = field(default_factory=lambda: {
        "execution_speed": "FAST",          # ความเร็วในการ execute
        "price_improvement": True,          # พยายามปรับปรุงราคา
        "partial_fills": True,              # ยอมรับการ fill บางส่วน
        "requote_handling": "AUTOMATIC",    # จัดการ requote อัตโนมัติ
        "slippage_tolerance": 0.5,          # ความคลาดเคลื่อนที่ยอมรับ
        "latency_threshold": 100,           # threshold ของ latency (ms)
        "retry_attempts": 3,                # จำนวนครั้งที่ลองใหม่
        "timeout_seconds": 30               # timeout ในการ execute
    })
    
    # === ADVANCED FEATURES ===
    advanced_features: Dict[str, Any] = field(default_factory=lambda: {
        "machine_learning_enabled": False,   # เปิดใช้ ML
        "sentiment_analysis": False,         # วิเคราะห์ sentiment
        "news_impact_scoring": True,         # คะแนนผลกระทบข่าว
        "correlation_trading": False,        # เทรดตาม correlation
        "arbitrage_detection": False,        # ตรวจจับ arbitrage
        "market_microstructure": False,     # วิเคราะห์ microstructure
        "order_flow_analysis": False        # วิเคราะห์ order flow
    })
    
    # === METADATA ===
    version: str = "2.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    profile_name: str = "default"
    
    def __post_init__(self):
        """การตั้งค่าเพิ่มเติมหลังจาก initialization"""
        self._validate_parameters()
        self._setup_default_strategies()
        self._setup_default_recovery_methods()
        self._setup_default_sessions()
        self.updated_at = datetime.now()
    
    def _validate_parameters(self):
        """ตรวจสอบความถูกต้องของพารามิเตอร์"""
        # ตรวจสอบ volume
        if self.min_volume > self.max_volume:
            self.min_volume = 0.01
            self.max_volume = 10.0
        
        if self.base_volume < self.min_volume:
            self.base_volume = self.min_volume
        elif self.base_volume > self.max_volume:
            self.base_volume = self.max_volume
        
        # ตรวจสอบ spread
        if self.max_spread <= 0:
            self.max_spread = 3.0
        
        # ตรวจสอบ confidence
        if not 0.0 <= self.min_confidence <= 1.0:
            self.min_confidence = 0.5
        
        # ตรวจสอบ volume targets
        volume_targets = self.volume_targets
        if volume_targets["daily_minimum"] > volume_targets["daily_target"]:
            volume_targets["daily_minimum"] = volume_targets["daily_target"] * 0.7
    
    def _setup_default_strategies(self):
        """ตั้งค่า strategies เริ่มต้น"""
        if not self.strategies:
            default_strategies = {
                EntryStrategy.SCALPING_ENGINE: StrategyParameters(
                    strategy=EntryStrategy.SCALPING_ENGINE,
                    weight=0.4,
                    confidence_threshold=0.6,
                    max_signals_per_hour=20,
                    cooldown_seconds=15,
                    parameters={
                        "bb_touch_threshold": 0.8,
                        "rsi_neutral_range": [45, 55],
                        "max_spread": 2.0
                    }
                ),
                EntryStrategy.TREND_FOLLOWING: StrategyParameters(
                    strategy=EntryStrategy.TREND_FOLLOWING,
                    weight=0.3,
                    confidence_threshold=0.7,
                    max_signals_per_hour=10,
                    cooldown_seconds=30,
                    parameters={
                        "adx_min_strength": 25,
                        "ma_alignment_required": True,
                        "trend_confirmation_bars": 3
                    }
                ),
                EntryStrategy.MEAN_REVERSION: StrategyParameters(
                    strategy=EntryStrategy.MEAN_REVERSION,
                    weight=0.2,
                    confidence_threshold=0.65,
                    max_signals_per_hour=15,
                    cooldown_seconds=20,
                    parameters={
                        "rsi_extreme_threshold": 20,
                        "bb_breakout_reversion": True,
                        "mean_reversion_distance": 0.5
                    }
                ),
                EntryStrategy.BREAKOUT_FALSE: StrategyParameters(
                    strategy=EntryStrategy.BREAKOUT_FALSE,
                    weight=0.07,
                    confidence_threshold=0.75,
                    max_signals_per_hour=5,
                    cooldown_seconds=60,
                    parameters={
                        "volume_confirmation": True,
                        "false_breakout_pips": 5,
                        "reversal_confirmation_time": 300
                    }
                ),
                EntryStrategy.NEWS_REACTION: StrategyParameters(
                    strategy=EntryStrategy.NEWS_REACTION,
                    weight=0.03,
                    confidence_threshold=0.8,
                    max_signals_per_hour=3,
                    cooldown_seconds=120,
                    parameters={
                        "news_impact_threshold": 7,
                        "reaction_delay_seconds": 30,
                        "volatility_spike_required": True
                    }
                )
            }
            self.strategies = default_strategies
    
    def _setup_default_recovery_methods(self):
        """ตั้งค่า recovery methods เริ่มต้น"""
        if not self.recovery_methods:
            default_recovery = {
                RecoveryMethod.MARTINGALE_SMART: RecoveryParameters(
                    method=RecoveryMethod.MARTINGALE_SMART,
                    max_levels=8,
                    multiplier=1.5,
                    step_pips=10.0,
                    dynamic_multiplier=True,
                    volatility_adjustment=True
                ),
                RecoveryMethod.GRID_INTELLIGENT: RecoveryParameters(
                    method=RecoveryMethod.GRID_INTELLIGENT,
                    max_levels=12,
                    multiplier=1.0,
                    step_pips=15.0,
                    dynamic_multiplier=False,
                    correlation_factor=0.6
                ),
                RecoveryMethod.HEDGING_ADVANCED: RecoveryParameters(
                    method=RecoveryMethod.HEDGING_ADVANCED,
                    max_levels=6,
                    multiplier=1.2,
                    step_pips=20.0,
                    correlation_factor=0.9,
                    time_decay=0.05
                ),
                RecoveryMethod.AVERAGING_INTELLIGENT: RecoveryParameters(
                    method=RecoveryMethod.AVERAGING_INTELLIGENT,
                    max_levels=10,
                    multiplier=1.3,
                    step_pips=12.0,
                    dynamic_multiplier=True,
                    volatility_adjustment=True
                )
            }
            self.recovery_methods = default_recovery
    
    def _setup_default_sessions(self):
        """ตั้งค่า sessions เริ่มต้น"""
        if not self.sessions:
            default_sessions = {
                "ASIAN": SessionParameters(
                    session_name="ASIAN",
                    start_hour=22, end_hour=8,
                    expected_volatility="LOW",
                    typical_spread=2.0,
                    preferred_strategies=[EntryStrategy.MEAN_REVERSION, EntryStrategy.SCALPING_ENGINE],
                    max_spread=2.5,
                    position_sizing_multiplier=0.8,
                    max_positions=8,
                    target_signals_per_hour=3
                ),
                "LONDON": SessionParameters(
                    session_name="LONDON",
                    start_hour=15, end_hour=20,
                    expected_volatility="HIGH",
                    typical_spread=2.5,
                    preferred_strategies=[EntryStrategy.TREND_FOLLOWING, EntryStrategy.BREAKOUT_FALSE],
                    max_spread=3.0,
                    position_sizing_multiplier=1.2,
                    max_positions=12,
                    target_signals_per_hour=8
                ),
                "NEW_YORK": SessionParameters(
                    session_name="NEW_YORK",
                    start_hour=20, start_minute=30, end_hour=5, end_minute=30,
                    expected_volatility="VERY_HIGH",
                    typical_spread=3.0,
                    preferred_strategies=[EntryStrategy.NEWS_REACTION, EntryStrategy.TREND_FOLLOWING],
                    max_spread=3.5,
                    position_sizing_multiplier=1.5,
                    max_positions=15,
                    target_signals_per_hour=10
                ),
                "OVERLAP": SessionParameters(
                    session_name="OVERLAP",
                    start_hour=20, start_minute=30, end_hour=0,
                    expected_volatility="EXTREME",
                    typical_spread=3.5,
                    preferred_strategies=[EntryStrategy.BREAKOUT_FALSE, EntryStrategy.NEWS_REACTION],
                    max_spread=4.0,
                    position_sizing_multiplier=1.8,
                    max_positions=20,
                    target_signals_per_hour=12
                )
            }
            self.sessions = default_sessions
    
    def get_strategy_parameters(self, strategy: EntryStrategy) -> Optional[StrategyParameters]:
        """ดึงพารามิเตอร์ของกลยุทธ์"""
        return self.strategies.get(strategy)
    
    def get_recovery_parameters(self, method: RecoveryMethod) -> Optional[RecoveryParameters]:
        """ดึงพารามิเตอร์ของ recovery method"""
        return self.recovery_methods.get(method)
    
    def get_session_parameters(self, session: str) -> Optional[SessionParameters]:
        """ดึงพารามิเตอร์ของ session"""
        return self.sessions.get(session)
    
    def get_optimal_strategy_for_session(self, session: str) -> EntryStrategy:
        """เลือกกลยุทธ์ที่เหมาะสมสำหรับ session"""
        session_params = self.get_session_parameters(session)
        
        if session_params and session_params.preferred_strategies:
            # เลือกจาก preferred strategies ตาม performance
            best_strategy = session_params.preferred_strategies[0]
            best_performance = 0.0
            
            for strategy in session_params.preferred_strategies:
                strategy_params = self.get_strategy_parameters(strategy)
                if strategy_params:
                    performance = strategy_params.get_success_rate()
                    if performance > best_performance:
                        best_performance = performance
                        best_strategy = strategy
            
            return best_strategy
        
        # Default fallback
        return EntryStrategy.SCALPING_ENGINE
    
    def get_optimal_recovery_for_condition(self, market_condition: MarketCondition) -> RecoveryMethod:
        """เลือก recovery method ที่เหมาะสมสำหรับสภาวะตลาด"""
        
        condition_recovery_map = {
            MarketCondition.TRENDING_UP: RecoveryMethod.GRID_INTELLIGENT,
            MarketCondition.TRENDING_DOWN: RecoveryMethod.GRID_INTELLIGENT,
            MarketCondition.RANGING: RecoveryMethod.MARTINGALE_SMART,
            MarketCondition.VOLATILE: RecoveryMethod.HEDGING_ADVANCED,
            MarketCondition.NEWS_IMPACT: RecoveryMethod.CORRELATION_RECOVERY,
            MarketCondition.QUIET: RecoveryMethod.AVERAGING_INTELLIGENT
        }
        
        preferred_method = condition_recovery_map.get(market_condition, RecoveryMethod.AVERAGING_INTELLIGENT)
        
        # ตรวจสอบ performance ของ method นี้
        recovery_params = self.get_recovery_parameters(preferred_method)
        if recovery_params and recovery_params.get_recovery_success_rate() < 50.0:
            # ถ้า performance ต่ำ ให้ใช้ default
            return RecoveryMethod.AVERAGING_INTELLIGENT
        
        return preferred_method
    
    def calculate_position_size(self, confidence: float, session: str = "ASIAN", 
                                account_balance: float = 10000.0, 
                                market_volatility: float = 1.0) -> float:
        """คำนวณขนาดตำแหน่ง"""
        return self.position_sizing.calculate_position_size(
            account_balance, confidence, market_volatility, session
        )
    
    def adjust_parameters_by_performance(self):
        """ปรับพารามิเตอร์ตาม performance"""
        
        # ปรับ strategy weights ตาม performance
        total_weight = 0.0
        for strategy_params in self.strategies.values():
            if strategy_params.enabled:
                success_rate = strategy_params.get_success_rate()
                # ปรับ weight ตาม success rate
                if success_rate > 70:
                    strategy_params.weight *= 1.1  # เพิ่ม weight
                elif success_rate < 40:
                    strategy_params.weight *= 0.9  # ลด weight
                
                total_weight += strategy_params.weight
        
        # Normalize weights
        if total_weight > 0:
            for strategy_params in self.strategies.values():
                strategy_params.weight /= total_weight
        
        # ปรับ recovery parameters ตาม performance
        for recovery_params in self.recovery_methods.values():
            success_rate = recovery_params.get_recovery_success_rate()
            if success_rate < 50 and recovery_params.multiplier > 1.2:
                recovery_params.multiplier *= 0.95  # ลด aggressiveness
            elif success_rate > 80 and recovery_params.multiplier < 2.0:
                recovery_params.multiplier *= 1.05  # เพิ่ม aggressiveness
        
        self.updated_at = datetime.now()
    
    def optimize_for_rebate(self):
        """เพิ่มประสิทธิภาพสำหรับ rebate"""
        
        # เพิ่มความถี่ของการเทรด
        for strategy_params in self.strategies.values():
            if strategy_params.strategy in [EntryStrategy.SCALPING_ENGINE, EntryStrategy.MEAN_REVERSION]:
                strategy_params.max_signals_per_hour = int(strategy_params.max_signals_per_hour * 1.2)
                strategy_params.cooldown_seconds = max(10, int(strategy_params.cooldown_seconds * 0.8))
        
        # เพิ่ม target volume
        self.volume_targets["daily_target"] = min(
            self.volume_targets["daily_maximum"],
            self.volume_targets["daily_target"] * 1.1
        )
        
        # ลด confidence threshold เล็กน้อยเพื่อเพิ่มสัญญาณ
        for strategy_params in self.strategies.values():
            strategy_params.confidence_threshold = max(0.4, strategy_params.confidence_threshold - 0.05)
        
        self.updated_at = datetime.now()
    
    def create_conservative_profile(self) -> 'TradingParameters':
        """สร้าง profile แบบอนุรักษ์นิยม"""
        conservative = copy.deepcopy(self)
        
        # ลด volume targets
        conservative.volume_targets["daily_target"] *= 0.5
        conservative.volume_targets["daily_maximum"] *= 0.6
        
        # เพิ่ม confidence threshold
        for strategy_params in conservative.strategies.values():
            strategy_params.confidence_threshold = min(0.9, strategy_params.confidence_threshold + 0.1)
            strategy_params.max_signals_per_hour = max(1, strategy_params.max_signals_per_hour // 2)
        
        # ลด recovery aggressiveness
        for recovery_params in conservative.recovery_methods.values():
            recovery_params.multiplier = max(1.1, recovery_params.multiplier - 0.2)
            recovery_params.max_levels = max(3, recovery_params.max_levels - 2)
        
        # ลด position sizing
        conservative.position_sizing.risk_per_trade_percent *= 0.5
        conservative.position_sizing.max_volume *= 0.5
        
        conservative.profile_name = "conservative"
        return conservative
    
    def create_aggressive_profile(self) -> 'TradingParameters':
        """สร้าง profile แบบก้าวร้าว"""
        aggressive = copy.deepcopy(self)
        
        # เพิ่ม volume targets
        aggressive.volume_targets["daily_target"] *= 1.5
        aggressive.volume_targets["daily_maximum"] *= 1.3
        
        # ลด confidence threshold
        for strategy_params in aggressive.strategies.values():
            strategy_params.confidence_threshold = max(0.3, strategy_params.confidence_threshold - 0.1)
            strategy_params.max_signals_per_hour = min(50, int(strategy_params.max_signals_per_hour * 1.5))
        
        # เพิ่ม recovery aggressiveness
        for recovery_params in aggressive.recovery_methods.values():
            recovery_params.multiplier = min(3.0, recovery_params.multiplier + 0.3)
            recovery_params.max_levels = min(15, recovery_params.max_levels + 3)
        
        # เพิ่ม position sizing
        aggressive.position_sizing.risk_per_trade_percent *= 1.5
        aggressive.position_sizing.max_volume *= 1.5
        
        aggressive.profile_name = "aggressive"
        return aggressive
    
    def export_parameters(self, filename: Optional[str] = None) -> str:
        """ส่งออกพารามิเตอร์"""
        try:
            if filename is None:
                filename = f"trading_params_{self.profile_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Convert to serializable format
            export_data = self._to_serializable_dict()
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            return filename
            
        except Exception as e:
            print(f"❌ ไม่สามารถส่งออกพารามิเตอร์: {e}")
            return ""
    
    def _to_serializable_dict(self) -> Dict[str, Any]:
        """แปลงเป็น dict ที่ serialize ได้"""
        result = {}
        
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, Enum):
                result[field_name] = field_value.value
            elif isinstance(field_value, datetime):
                result[field_name] = field_value.isoformat()
            elif isinstance(field_value, dict):
                if field_name in ['strategies', 'recovery_methods', 'sessions']:
                    # Handle complex object dictionaries
                    nested_dict = {}
                    for key, obj in field_value.items():
                        if hasattr(obj, '__dict__'):
                            obj_dict = {}
                            for obj_field, obj_value in obj.__dict__.items():
                                if isinstance(obj_value, Enum):
                                    obj_dict[obj_field] = obj_value.value
                                elif isinstance(obj_value, datetime):
                                    obj_dict[obj_field] = obj_value.isoformat() if obj_value else None
                                else:
                                    obj_dict[obj_fiel