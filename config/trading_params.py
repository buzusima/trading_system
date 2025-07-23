#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRADING PARAMETERS - พารามิเตอร์การเทรดดิ้ง
======================================
กำหนดพารามิเตอร์ทั้งหมดสำหรับการเทรด XAUUSD
รวมถึงการตั้งค่าสำหรับ Recovery Strategies ต่างๆ

เชื่อมต่อไปยัง:
- config/settings.py (การตั้งค่าระบบหลัก)
- intelligent_recovery/strategies/* (กลยุทธ์ Recovery)
- adaptive_entries/entry_engines/* (กลยุทธ์การเข้าออร์เดอร์)
- money_management/* (การจัดการเงินทุน)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from enum import Enum

class RecoveryMethod(Enum):
    """วิธีการ Recovery ต่างๆ"""
    MARTINGALE_SMART = "MARTINGALE_SMART"           # Martingale อัจฉริยะ
    GRID_INTELLIGENT = "GRID_INTELLIGENT"           # Grid แบบอัจฉริยะ  
    HEDGING_ADVANCED = "HEDGING_ADVANCED"           # Hedging ขั้นสูง
    AVERAGING_INTELLIGENT = "AVERAGING_INTELLIGENT" # เฉลี่ยราคาอัจฉริยะ
    CORRELATION_RECOVERY = "CORRELATION_RECOVERY"   # Recovery ด้วย Correlation

class EntryStrategy(Enum):
    """กลยุทธ์การเข้าออร์เดอร์"""
    TREND_FOLLOWING = "TREND_FOLLOWING"     # ตาม Trend
    MEAN_REVERSION = "MEAN_REVERSION"       # กลับสู่ค่าเฉลี่ย
    BREAKOUT_FALSE = "BREAKOUT_FALSE"       # False Breakout
    NEWS_REACTION = "NEWS_REACTION"         # ปฏิกิริยาข่าว
    SCALPING_ENGINE = "SCALPING_ENGINE"     # Scalping

@dataclass
class MarketConditionParams:
    """พารามิเตอร์สำหรับสภาพตลาดแต่ละแบบ"""
    
    # Trend Detection Parameters
    adx_period: int = 14
    adx_trending_min: float = 25.0      # ADX > 25 = Trending
    adx_ranging_max: float = 20.0       # ADX < 20 = Ranging
    
    # Moving Average Parameters
    ma_fast_period: int = 10
    ma_slow_period: int = 50
    ma_trend_confirmation: int = 5      # จำนวน candle ที่ต้องยืนยัน trend
    
    # Volatility Parameters
    atr_period: int = 14
    atr_high_multiplier: float = 1.5    # ATR * 1.5 = High Volatility
    atr_low_multiplier: float = 0.8     # ATR * 0.8 = Low Volatility
    
    # Bollinger Bands Parameters
    bb_period: int = 20
    bb_deviation: float = 2.0
    bb_squeeze_threshold: float = 0.1   # ค่าต่ำสุดของ bandwidth

@dataclass
class EntryParams:
    """พารามิเตอร์สำหรับการเข้าออร์เดอร์"""
    
    # === TREND FOLLOWING PARAMETERS ===
    trend_following: Dict = field(default_factory=lambda: {
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "min_trend_strength": 0.7,      # ความแรงของ trend ขั้นต่ำ
        "entry_timeout_minutes": 5,     # หมดเวลารอสัญญาณ
        "max_entries_per_trend": 3      # จำนวนออร์เดอร์สูงสุดต่อ trend
    })
    
    # === MEAN REVERSION PARAMETERS ===
    mean_reversion: Dict = field(default_factory=lambda: {
        "bb_period": 20,
        "bb_deviation": 2.0,
        "rsi_extreme_high": 80,         # RSI สูงมาก
        "rsi_extreme_low": 20,          # RSI ต่ำมาก
        "stoch_period": 14,
        "stoch_overbought": 80,
        "stoch_oversold": 20,
        "mean_distance_threshold": 0.5,  # ระยะห่างจากค่าเฉลี่ย (%)
        "reversion_confirmation": 2      # จำนวน candle ยืนยัน
    })
    
    # === BREAKOUT FALSE PARAMETERS ===
    breakout_false: Dict = field(default_factory=lambda: {
        "support_resistance_period": 50,
        "breakout_min_pips": 10,        # Breakout ขั้นต่ำ (pips)
        "false_breakout_pips": 5,       # กลับเข้า range (pips)
        "volume_confirmation": True,     # ใช้ volume ยืนยัน
        "time_window_minutes": 15,      # หน้าต่างเวลาสำหรับ false breakout
        "max_attempts_per_level": 2     # จำนวนครั้งสูงสุดต่อระดับ
    })
    
    # === NEWS REACTION PARAMETERS ===
    news_reaction: Dict = field(default_factory=lambda: {
        "impact_levels": ["HIGH", "MEDIUM"],  # ระดับผลกระทบข่าว
        "reaction_window_minutes": 30,        # หน้าต่างเวลาหลังข่าว
        "spike_min_pips": 15,                # ความเคลื่อนไหวขั้นต่ำ
        "reversal_confirmation": 3,          # candle ยืนยันการกลับตัว
        "avoid_currencies": ["JPY", "CHF"],  # หลีกเลี่ยงข่าวสกุลเงินนี้
        "pre_news_stop_minutes": 5           # หยุดเทรดก่อนข่าว
    })
    
    # === SCALPING PARAMETERS ===
    scalping: Dict = field(default_factory=lambda: {
        "timeframe": "M1",              # Timeframe หลัก
        "pip_target": 3,                # เป้าหมาย profit (pips)
        "spread_max": 2.0,              # Spread สูงสุด
        "momentum_period": 5,           # ระยะเวลาวัด momentum
        "entry_precision": 0.1,         # ความแม่นยำในการ entry (pips)
        "max_positions_concurrent": 10   # จำนวน position พร้อมกันสูงสุด
    })

@dataclass  
class RecoveryParams:
    """พารามิเตอร์สำหรับระบบ Recovery ต่างๆ"""
    
    # === SMART MARTINGALE RECOVERY ===
    martingale_smart: Dict = field(default_factory=lambda: {
        "initial_multiplier": 2.0,      # ตัวคูณเริ่มต้น
        "max_multiplier": 8.0,          # ตัวคูณสูงสุด
        "adaptive_multiplier": True,     # ปรับตัวคูณตามสภาพตลาด
        "volatility_adjustment": True,   # ปรับตาม volatility
        "max_levels": 10,               # จำนวนระดับสูงสุด
        "level_distance_pips": 50,      # ระยะห่างระหว่างระดับ (pips)
        "profit_factor": 1.2,           # เป้าหมาย profit
        "risk_reduction_factor": 0.8    # ลดความเสี่ยงเมื่อขาดทุนมาก
    })
    
    # === INTELLIGENT GRID RECOVERY ===
    grid_intelligent: Dict = field(default_factory=lambda: {
        "grid_spacing_pips": 30,        # ระยะห่าง Grid (pips)
        "max_grid_levels": 15,          # จำนวนระดับ Grid สูงสุด
        "dynamic_spacing": True,        # ปรับระยะห่างแบบ dynamic
        "trend_bias_factor": 1.5,       # น้ำหนัก trend
        "consolidation_detection": True, # ตรวจจับการ sideways
        "partial_close_enabled": True,  # ปิดบางส่วน
        "breakeven_threshold": 0.5,     # เกณฑ์ breakeven
        "grid_recovery_target": 1.3     # เป้าหมาย recovery
    })
    
    # === ADVANCED HEDGING RECOVERY ===
    hedging_advanced: Dict = field(default_factory=lambda: {
        "hedge_ratio": 1.0,             # อัตราส่วน hedge (1:1)
        "partial_hedge_enabled": True,   # hedge บางส่วน
        "correlation_threshold": 0.7,    # เกณฑ์ correlation
        "hedge_timing_delay": 60,       # หน่วงเวลาก่อน hedge (วินาที)
        "max_hedge_levels": 5,          # จำนวนระดับ hedge สูงสุด
        "profit_taking_aggressive": True, # รับกำไรแบบ aggressive
        "hedge_exit_strategy": "FIFO",  # กลยุทธ์ออกจาก hedge
        "correlation_pairs": ["EURUSD", "GBPUSD", "USDJPY"]  # คู่สกุลเงิน correlation
    })
    
    # === INTELLIGENT AVERAGING RECOVERY ===
    averaging_intelligent: Dict = field(default_factory=lambda: {
        "averaging_distance_pips": 25,     # ระยะห่างสำหรับเฉลี่ย (pips)
        "max_averaging_positions": 12,     # จำนวน position สูงสุด
        "size_progression": "FIBONACCI",   # ลำดับขนาด position
        "trend_weight_factor": 0.7,        # น้ำหนัก trend ในการเฉลี่ย
        "time_based_averaging": True,      # เฉลี่ยตามเวลา
        "volatility_adjustment": True,     # ปรับตาม volatility
        "profit_lock_percentage": 50,      # ล็อคกำไร (%)
        "averaging_timeout_hours": 24      # หมดเวลาการเฉลี่ย
    })
    
    # === CORRELATION RECOVERY ===
    correlation_recovery: Dict = field(default_factory=lambda: {
        "correlation_threshold": 0.8,      # เกณฑ์ correlation
        "correlation_window": 100,         # จำนวน candle คำนวณ correlation
        "hedge_instruments": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF"],
        "recovery_ratio": 0.8,             # อัตราส่วน recovery
        "max_correlation_positions": 8,    # จำนวน position correlation สูงสุด
        "correlation_update_minutes": 5,   # อัพเดท correlation (นาที)
        "exit_correlation_threshold": 0.3, # เกณฑ์ออกจาก correlation
        "profit_sharing_ratio": 0.6        # แบ่งกำไรระหว่าง instruments
    })

@dataclass
class MoneyManagementParams:
    """พารามิเตอร์การจัดการเงินทุน"""
    
    # === POSITION SIZING ===
    base_lot_size: float = 0.01             # ขนาด lot พื้นฐาน
    max_lot_size: float = 10.0              # ขนาด lot สูงสุด
    lot_size_precision: int = 2             # ทศนิยม lot size
    
    # === CAPITAL ALLOCATION ===
    max_capital_risk_percent: float = 95.0   # ใช้เงินทุนสูงสุด (%)
    reserve_capital_percent: float = 5.0     # เงินสำรอง (%)
    recovery_capital_ratio: float = 0.7      # สัดส่วนเงินทุนสำหรับ recovery
    
    # === DYNAMIC LOT SIZING ===
    balance_based_sizing: bool = True        # ปรับขนาดตาม balance
    volatility_based_sizing: bool = True     # ปรับขนาดตาม volatility
    recovery_based_sizing: bool = True       # ปรับขนาดตามสถานะ recovery
    
    # เส้นโค้งการปรับขนาด lot
    sizing_curve: Dict = field(default_factory=lambda: {
        "balance_ranges": {             # ขนาด lot ตาม balance
            1000: 0.01,
            5000: 0.05,
            10000: 0.10,
            50000: 0.50,
            100000: 1.00
        },
        "volatility_multipliers": {     # ตัวคูณตาม volatility
            "LOW": 1.2,
            "NORMAL": 1.0,
            "HIGH": 0.8,
            "EXTREME": 0.6
        }
    })
    
    # === EXPOSURE MANAGEMENT ===
    max_total_exposure: float = 20.0        # exposure สูงสุด (lots)
    max_single_direction: float = 15.0      # exposure ทิศทางเดียวสูงสุด
    exposure_warning_level: float = 12.0    # ระดับแจ้งเตือน exposure
    
    # === MARGIN MANAGEMENT ===
    margin_buffer_percent: float = 20.0     # buffer margin (%)
    margin_warning_level: float = 30.0      # ระดับแจ้งเตือน margin
    auto_reduce_on_margin: bool = True      # ลด position อัตโนมัติเมื่อ margin ต่ำ

@dataclass
class SessionParams:
    """พารามิเตอร์สำหรับแต่ละ session การเทรด"""
    
    # === ASIAN SESSION (22:00-08:00 GMT+7) ===
    asian_session: Dict = field(default_factory=lambda: {
        "preferred_strategies": [EntryStrategy.MEAN_REVERSION, EntryStrategy.SCALPING_ENGINE],
        "recovery_method": RecoveryMethod.AVERAGING_INTELLIGENT,
        "max_positions_per_hour": 20,
        "lot_size_multiplier": 0.8,         # ลดขนาด lot
        "volatility_expectation": "LOW",
        "spread_tolerance": 1.5,            # tolerane spread สูงกว่า
        "news_impact_sensitivity": 0.6      # ความไวต่อข่าวต่ำกว่า
    })
    
    # === LONDON SESSION (15:00-00:00 GMT+7) ===
    london_session: Dict = field(default_factory=lambda: {
        "preferred_strategies": [EntryStrategy.TREND_FOLLOWING, EntryStrategy.BREAKOUT_FALSE],
        "recovery_method": RecoveryMethod.GRID_INTELLIGENT,
        "max_positions_per_hour": 40,
        "lot_size_multiplier": 1.2,         # เพิ่มขนาด lot
        "volatility_expectation": "HIGH",
        "spread_tolerance": 1.0,
        "news_impact_sensitivity": 1.0
    })
    
    # === NEW YORK SESSION (20:30-05:30 GMT+7) ===
    newyork_session: Dict = field(default_factory=lambda: {
        "preferred_strategies": [EntryStrategy.NEWS_REACTION, EntryStrategy.TREND_FOLLOWING],
        "recovery_method": RecoveryMethod.HEDGING_ADVANCED,
        "max_positions_per_hour": 50,       # สูงสุด
        "lot_size_multiplier": 1.0,
        "volatility_expectation": "HIGH",
        "spread_tolerance": 0.8,            # tolerance spread ต่ำสุด
        "news_impact_sensitivity": 1.5      # ความไวต่อข่าวสูงสุด
    })
    
    # === OVERLAP SESSION (20:30-00:00 GMT+7) ===
    overlap_session: Dict = field(default_factory=lambda: {
        "preferred_strategies": [EntryStrategy.BREAKOUT_FALSE, EntryStrategy.SCALPING_ENGINE],
        "recovery_method": RecoveryMethod.MARTINGALE_SMART,
        "max_positions_per_hour": 60,       # สูงสุดในช่วง overlap
        "lot_size_multiplier": 1.5,         # เพิ่มขนาด lot สูงสุด
        "volatility_expectation": "EXTREME",
        "spread_tolerance": 0.5,            # tolerance spread ต่ำสุด
        "news_impact_sensitivity": 2.0      # ความไวต่อข่าวสูงสุด
    })

@dataclass
class PerformanceParams:
    """พารามิเตอร์การวัดประสิทธิภาพ"""
    
    # === VOLUME TARGETS ===
    daily_volume_min: float = 50.0         # Volume ขั้นต่ำต่อวัน (lots)
    daily_volume_target: float = 75.0      # Volume เป้าหมายต่อวัน (lots)
    daily_volume_max: float = 100.0        # Volume สูงสุดต่อวัน (lots)
    
    hourly_volume_distribution: Dict = field(default_factory=lambda: {
        "00-01": 1.0,   "01-02": 0.8,   "02-03": 0.6,   "03-04": 0.4,
        "04-05": 0.6,   "05-06": 0.8,   "06-07": 1.2,   "07-08": 1.0,
        "08-09": 0.8,   "09-10": 0.6,   "10-11": 0.8,   "11-12": 1.0,
        "12-13": 1.2,   "13-14": 1.0,   "14-15": 1.5,   "15-16": 2.0,  # London เริ่ม
        "16-17": 2.5,   "17-18": 2.2,   "18-19": 2.0,   "19-20": 1.8,
        "20-21": 3.5,   "21-22": 4.0,   "22-23": 3.8,   "23-00": 3.2   # Overlap
    })
    
    # === PROFIT TARGETS ===
    daily_profit_target: float = 100.0     # เป้าหมายกำไรต่อวัน (USD)
    weekly_profit_target: float = 500.0    # เป้าหมายกำไรต่อสัปดาห์ (USD)
    monthly_profit_target: float = 2000.0  # เป้าหมายกำไรต่อเดือน (USD)
    
    # === RECOVERY SUCCESS METRICS ===
    recovery_success_target: float = 98.0  # เป้าหมาย recovery success (%)
    max_recovery_time_hours: float = 24.0  # เวลา recovery สูงสุด (ชั่วโมง)
    recovery_efficiency_target: float = 1.2 # ประสิทธิภาพ recovery
    
    # === SYSTEM PERFORMANCE ===
    order_execution_target_ms: int = 100   # เป้าหมายความเร็วส่งออร์เดอร์ (ms)
    system_uptime_target: float = 99.9     # เป้าหมาย uptime (%)
    error_rate_max: float = 0.1            # อัตราข้อผิดพลาดสูงสุด (%)

@dataclass
class TradingParameters:
    """คลาสหลักรวบรวมพารามิเตอร์ทั้งหมด"""
    
    market_conditions: MarketConditionParams = field(default_factory=MarketConditionParams)
    entry_params: EntryParams = field(default_factory=EntryParams)
    recovery_params: RecoveryParams = field(default_factory=RecoveryParams)
    money_management: MoneyManagementParams = field(default_factory=MoneyManagementParams)
    session_params: SessionParams = field(default_factory=SessionParams)
    performance_params: PerformanceParams = field(default_factory=PerformanceParams)
    
    def get_strategy_params(self, strategy: EntryStrategy) -> Dict:
        """ดึงพารามิเตอร์สำหรับกลยุทธ์เฉพาะ"""
        strategy_map = {
            EntryStrategy.TREND_FOLLOWING: self.entry_params.trend_following,
            EntryStrategy.MEAN_REVERSION: self.entry_params.mean_reversion,
            EntryStrategy.BREAKOUT_FALSE: self.entry_params.breakout_false,
            EntryStrategy.NEWS_REACTION: self.entry_params.news_reaction,
            EntryStrategy.SCALPING_ENGINE: self.entry_params.scalping
        }
        return strategy_map.get(strategy, {})
    
    def get_recovery_params(self, method: RecoveryMethod) -> Dict:
        """ดึงพารามิเตอร์สำหรับวิธี Recovery เฉพาะ"""
        recovery_map = {
            RecoveryMethod.MARTINGALE_SMART: self.recovery_params.martingale_smart,
            RecoveryMethod.GRID_INTELLIGENT: self.recovery_params.grid_intelligent,
            RecoveryMethod.HEDGING_ADVANCED: self.recovery_params.hedging_advanced,
            RecoveryMethod.AVERAGING_INTELLIGENT: self.recovery_params.averaging_intelligent,
            RecoveryMethod.CORRELATION_RECOVERY: self.recovery_params.correlation_recovery
        }
        return recovery_map.get(method, {})
    
    def get_session_params(self, session_name: str) -> Dict:
        """ดึงพารามิเตอร์สำหรับ session เฉพาะ"""
        session_map = {
            "ASIAN": self.session_params.asian_session,
            "LONDON": self.session_params.london_session,
            "NEW_YORK": self.session_params.newyork_session, 
            "OVERLAP": self.session_params.overlap_session
        }
        return session_map.get(session_name, {})
    
    def validate_parameters(self) -> List[str]:
        """ตรวจสอบความถูกต้องของพารามิเตอร์"""
        errors = []
        
        # ตรวจสอบ Volume Targets
        if self.performance_params.daily_volume_min > self.performance_params.daily_volume_max:
            errors.append("Daily volume min ต้องน้อยกว่า max")
        
        # ตรวจสอบ Money Management
        if self.money_management.max_capital_risk_percent > 100:
            errors.append("Max capital risk ต้องไม่เกิน 100%")
        
        # ตรวจสอบ Recovery Parameters
        for method, params in [
            ("martingale", self.recovery_params.martingale_smart),
            ("grid", self.recovery_params.grid_intelligent),
            ("hedging", self.recovery_params.hedging_advanced),
            ("averaging", self.recovery_params.averaging_intelligent)
        ]:
            if not params:
                errors.append(f"Recovery parameters สำหรับ {method} ว่างเปล่า")
        
        return errors
    
    def optimize_for_session(self, session_name: str) -> 'TradingParameters':
        """ปรับแต่งพารามิเตอร์สำหรับ session เฉพาะ"""
        # สร้าง copy ของ parameters
        optimized = TradingParameters(
            market_conditions=self.market_conditions,
            entry_params=self.entry_params,
            recovery_params=self.recovery_params,
            money_management=self.money_management,
            session_params=self.session_params,
            performance_params=self.performance_params
        )
        
        # ปรับแต่งตาม session
        session_config = self.get_session_params(session_name)
        if session_config:
            # ปรับ lot size multiplier
            lot_multiplier = session_config.get("lot_size_multiplier", 1.0)
            optimized.money_management.base_lot_size *= lot_multiplier
            
            # ปรับ max positions per hour
            max_positions = session_config.get("max_positions_per_hour", 30)
            # TODO: Apply to relevant parameters
        
        return optimized

# === GLOBAL PARAMETERS INSTANCE ===
_global_trading_params: Optional[TradingParameters] = None

def get_trading_parameters() -> TradingParameters:
    """ดึง Trading Parameters แบบ Singleton"""
    global _global_trading_params
    if _global_trading_params is None:
        _global_trading_params = TradingParameters()
    return _global_trading_params

def update_trading_parameters(new_params: TradingParameters) -> None:
    """อัพเดท Trading Parameters"""
    global _global_trading_params
    _global_trading_params = new_params

def load_parameters_from_file(file_path: str) -> Optional[TradingParameters]:
    """โหลดพารามิเตอร์จากไฟล์"""
    # TODO: Implement file loading
    return None

def save_parameters_to_file(params: TradingParameters, file_path: str) -> bool:
    """บันทึกพารามิเตอร์ลงไฟล์"""
    # TODO: Implement file saving
    return True

# === PARAMETER VALIDATION FUNCTIONS ===

def validate_lot_size(lot_size: float, symbol: str = "XAUUSD") -> bool:
    """ตรวจสอบความถูกต้องของขนาด lot"""
    # ขนาด lot ขั้นต่ำ/สูงสุดสำหรับ XAUUSD
    min_lot = 0.01
    max_lot = 100.0
    step = 0.01
    
    return (min_lot <= lot_size <= max_lot and 
            lot_size % step == 0)

def validate_recovery_levels(levels: int, method: RecoveryMethod) -> bool:
    """ตรวจสอบจำนวนระดับ recovery"""
    max_levels = {
        RecoveryMethod.MARTINGALE_SMART: 10,
        RecoveryMethod.GRID_INTELLIGENT: 15,
        RecoveryMethod.HEDGING_ADVANCED: 5,
        RecoveryMethod.AVERAGING_INTELLIGENT: 12,
        RecoveryMethod.CORRELATION_RECOVERY: 8
    }
    
    return 1 <= levels <= max_levels.get(method, 10)

def calculate_required_margin(lot_size: float, leverage: int = 100) -> float:
    """คำนวณ margin ที่ต้องใช้"""
    # สูตรคำนวณ margin สำหรับ XAUUSD
    # Margin = (Lot Size * Contract Size * Current Price) / Leverage
    
    # ค่าประมาณสำหรับ XAUUSD
    contract_size = 100  # 100 oz per lot
    estimated_price = 2000  # USD per oz (ประมาณ)
    
    margin_required = (lot_size * contract_size * estimated_price) / leverage
    return margin_required