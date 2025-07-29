#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSITION SIZER - Dynamic Position Sizing Engine
==============================================
เครื่องมือคำนวณ Position Size แบบ Dynamic และ Intelligent
รองรับการคำนวณ Lot Size สำหรับ High-Frequency Trading และ Recovery System

Key Features:
- Dynamic lot size calculation ตาม market conditions
- Recovery-aware position sizing
- High-frequency volume optimization (50-100 lots/วัน)
- Market volatility adaptation
- Capital allocation optimization
- Session-based sizing strategies

เชื่อมต่อไปยัง:
- config/settings.py (การตั้งค่าระบบ)
- config/trading_params.py (พารามิเตอร์การเทรด)
- market_intelligence/market_analyzer.py (วิเคราะห์ตลาด)
- intelligent_recovery/recovery_engine.py (ระบบ Recovery)
- position_management/position_tracker.py (ติดตาม positions)
"""

import math
import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
import json
import asyncio
# เชื่อมต่อ internal modules
from config.settings import get_system_settings, MarketSession
from config.trading_params import get_trading_parameters, EntryStrategy, RecoveryMethod
from utilities.professional_logger import setup_trading_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class SizingStrategy(Enum):
    """กลยุทธ์การคำนวณ Position Size"""
    FIXED_LOT = "FIXED_LOT"                     # Lot size คงที่
    VOLATILITY_BASED = "VOLATILITY_BASED"       # ตาม Volatility
    CAPITAL_PERCENTAGE = "CAPITAL_PERCENTAGE"   # เปอร์เซ็นต์ของเงินทุน
    RECOVERY_ADAPTIVE = "RECOVERY_ADAPTIVE"     # ปรับตาม Recovery status
    VOLUME_TARGET = "VOLUME_TARGET"             # เป้าหมาย Volume
    MARKET_CONDITIONS = "MARKET_CONDITIONS"     # ตามสภาพตลาด
    SESSION_BASED = "SESSION_BASED"             # ตาม Trading session

class RiskLevel(Enum):
    """ระดับความเสี่ยง"""
    VERY_LOW = 1      # 0.5% ของเงินทุน
    LOW = 2           # 1% ของเงินทุน
    MODERATE = 3      # 2% ของเงินทุน
    HIGH = 4          # 3% ของเงินทุน
    VERY_HIGH = 5     # 5% ของเงินทุน

class VolatilityLevel(Enum):
    """ระดับความผันผวน"""
    VERY_LOW = "VERY_LOW"       # ATR < 5 points
    LOW = "LOW"                 # ATR 5-10 points
    MODERATE = "MODERATE"       # ATR 10-20 points
    HIGH = "HIGH"               # ATR 20-30 points
    VERY_HIGH = "VERY_HIGH"     # ATR > 30 points

@dataclass
class SizingParameters:
    """
    พารามิเตอร์สำหรับการคำนวณ Position Size
    """
    # Account Information
    account_balance: float = 10000.0           # ยอดเงินในบัญชี
    account_equity: float = 10000.0            # Equity ปัจจุบัน
    free_margin: float = 10000.0               # Margin ที่ใช้ได้
    
    # Risk Management
    max_risk_per_trade: float = 0.02           # ความเสี่ยงสูงสุดต่อเทรด (2%)
    max_daily_risk: float = 0.10               # ความเสี่ยงสูงสุดต่อวัน (10%)
    current_daily_risk: float = 0.0            # ความเสี่ยงปัจจุบันวันนี้
    
    # Volume Targets
    daily_volume_target: float = 75.0          # เป้าหมาย Volume ต่อวัน (lots)
    current_daily_volume: float = 0.0          # Volume ปัจจุบันวันนี้
    remaining_volume_target: float = 75.0      # Volume ที่เหลือต้องทำ
    
    # Market Conditions
    current_volatility: VolatilityLevel = VolatilityLevel.MODERATE
    atr_value: float = 15.0                    # ATR ปัจจุบัน (points)
    current_session: MarketSession = MarketSession.ASIAN
    
    # Position Information
    total_open_positions: int = 0              # จำนวน positions ที่เปิดอยู่
    recovery_positions: int = 0                # จำนวน positions ที่อยู่ใน recovery
    largest_position_size: float = 0.0         # Position size ที่ใหญ่ที่สุด
    
    # Symbol Specific
    symbol: str = "XAUUSD.v"
    point_value: float = 0.01                  # ค่า 1 point
    tick_size: float = 0.01                    # Tick size
    contract_size: float = 100.0               # Contract size
    margin_required: float = 1000.0            # Margin ที่ต้องใช้ต่อ 1 lot

@dataclass
class SizingResult:
    """
    ผลการคำนวณ Position Size
    """
    recommended_lot_size: float                # Lot size ที่แนะนำ
    max_lot_size: float                        # Lot size สูงสุดที่ได้
    min_lot_size: float                        # Lot size ต่ำสุดที่ได้
    
    # Calculation Details
    sizing_method: SizingStrategy              # วิธีที่ใช้คำนวณ
    risk_amount: float                         # จำนวนเงินที่เสี่ยง
    margin_required: float                     # Margin ที่ต้องใช้
    
    # Quality Metrics
    confidence_score: float                    # ความเชื่อมั่นในการคำนวณ (0-100)
    risk_reward_ratio: float                   # อัตราส่วน Risk:Reward
    
    # Additional Info
    reasoning: str = ""                        # เหตุผลในการเลือก size
    warnings: List[str] = field(default_factory=list)  # คำเตือน
    market_impact: str = "LOW"                 # ผลกระทบต่อตลาด
    
    # Execution Parameters
    suggested_slippage: float = 2.0            # Slippage ที่คาดหวัง (points)
    urgency_level: int = 1                     # ระดับความรีบด่วน (1-5)

class MarketImpactCalculator:
    """
    คำนวณผลกระทบของ Position Size ต่อตลาด
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Market Impact Thresholds (lots)
        self.impact_thresholds = {
            "VERY_LOW": 0.1,      # < 0.1 lots
            "LOW": 0.5,           # 0.1-0.5 lots
            "MODERATE": 2.0,      # 0.5-2.0 lots
            "HIGH": 5.0,          # 2.0-5.0 lots
            "VERY_HIGH": 10.0     # 5.0-10.0 lots
        }
        
        # Session-based liquidity factors
        self.liquidity_factors = {
            MarketSession.ASIAN: 0.7,      # ความเหลวใส 70%
            MarketSession.LONDON: 1.0,     # ความเหลวใส 100%
            MarketSession.NEW_YORK: 1.2,   # ความเหลวใส 120%
            MarketSession.OVERLAP: 1.5     # ความเหลวใส 150%
        }
    
    def calculate_market_impact(self, lot_size: float, session: MarketSession,
                              volatility: VolatilityLevel) -> Tuple[str, float]:
        """
        คำนวณผลกระทบต่อตลาด
        """
        try:
            # ปรับ lot size ตาม liquidity ของ session
            liquidity_factor = self.liquidity_factors.get(session, 1.0)
            adjusted_lot_size = lot_size / liquidity_factor
            
            # ปรับตาม volatility
            volatility_multiplier = {
                VolatilityLevel.VERY_LOW: 1.2,
                VolatilityLevel.LOW: 1.1,
                VolatilityLevel.MODERATE: 1.0,
                VolatilityLevel.HIGH: 0.9,
                VolatilityLevel.VERY_HIGH: 0.8
            }.get(volatility, 1.0)
            
            final_adjusted_size = adjusted_lot_size * volatility_multiplier
            
            # กำหนดระดับผลกระทบ
            if final_adjusted_size < self.impact_thresholds["VERY_LOW"]:
                impact_level = "VERY_LOW"
                impact_score = 0.1
            elif final_adjusted_size < self.impact_thresholds["LOW"]:
                impact_level = "LOW"
                impact_score = 0.3
            elif final_adjusted_size < self.impact_thresholds["MODERATE"]:
                impact_level = "MODERATE"
                impact_score = 0.5
            elif final_adjusted_size < self.impact_thresholds["HIGH"]:
                impact_level = "HIGH"
                impact_score = 0.7
            else:
                impact_level = "VERY_HIGH"
                impact_score = 0.9
            
            return impact_level, impact_score
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Market Impact: {e}")
            return "MODERATE", 0.5

class VolatilityAdjuster:
    """
    ปรับ Position Size ตาม Volatility
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Volatility-based multipliers
        self.volatility_multipliers = {
            VolatilityLevel.VERY_LOW: 1.5,    # เพิ่ม size เมื่อ volatility ต่ำ
            VolatilityLevel.LOW: 1.2,
            VolatilityLevel.MODERATE: 1.0,    # Base multiplier
            VolatilityLevel.HIGH: 0.8,        # ลด size เมื่อ volatility สูง
            VolatilityLevel.VERY_HIGH: 0.6
        }
    
    def adjust_for_volatility(self, base_lot_size: float, volatility: VolatilityLevel,
                            atr_value: float) -> Tuple[float, str]:
        """
        ปรับ Position Size ตาม Volatility
        """
        try:
            # ดึง multiplier ตาม volatility level
            multiplier = self.volatility_multipliers.get(volatility, 1.0)
            
            # ปรับเพิ่มเติมตาม ATR value
            if atr_value > 0:
                # ATR-based adjustment (inverse relationship)
                atr_adjustment = max(0.5, min(2.0, 20.0 / atr_value))
                final_multiplier = multiplier * atr_adjustment
            else:
                final_multiplier = multiplier
            
            adjusted_size = base_lot_size * final_multiplier
            
            # สร้างคำอธิบาย
            reasoning = f"ปรับตาม {volatility.value} volatility (ATR: {atr_value:.1f})"
            if final_multiplier > 1.0:
                reasoning += f" - เพิ่ม size {final_multiplier:.1f}x"
            elif final_multiplier < 1.0:
                reasoning += f" - ลด size {final_multiplier:.1f}x"
            
            return adjusted_size, reasoning
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการปรับตาม Volatility: {e}")
            return base_lot_size, "ไม่สามารถปรับตาม volatility ได้"

class SessionBasedSizer:
    """
    คำนวณ Position Size ตาม Trading Session
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Session-based sizing parameters
        self.session_parameters = {
            MarketSession.ASIAN: {
                "base_multiplier": 0.8,        # Conservative sizing
                "max_lot_per_trade": 1.0,
                "volume_distribution": 0.20     # 20% ของ daily volume
            },
            MarketSession.LONDON: {
                "base_multiplier": 1.2,        # Aggressive sizing
                "max_lot_per_trade": 3.0,
                "volume_distribution": 0.40     # 40% ของ daily volume
            },
            MarketSession.NEW_YORK: {
                "base_multiplier": 1.0,        # Standard sizing
                "max_lot_per_trade": 2.0,
                "volume_distribution": 0.35     # 35% ของ daily volume
            },
            MarketSession.OVERLAP: {
                "base_multiplier": 1.5,        # Maximum sizing
                "max_lot_per_trade": 5.0,
                "volume_distribution": 0.25     # 25% ของ daily volume (overlap period)
            }
        }
    
    def calculate_session_size(self, base_lot_size: float, session: MarketSession,
                             daily_volume_target: float, current_daily_volume: float) -> Tuple[float, str]:
        """
        คำนวณ Position Size ตาม Session
        """
        try:
            session_params = self.session_parameters.get(session, self.session_parameters[MarketSession.ASIAN])
            
            # คำนวณ volume ที่ควรทำใน session นี้
            target_session_volume = daily_volume_target * session_params["volume_distribution"]
            remaining_volume = max(0, target_session_volume - current_daily_volume)
            
            # ปรับ base size ตาม session multiplier
            session_adjusted_size = base_lot_size * session_params["base_multiplier"]
            
            # จำกัดตาม max lot per trade
            max_lot = session_params["max_lot_per_trade"]
            session_adjusted_size = min(session_adjusted_size, max_lot)
            
            # ปรับตาม remaining volume target
            if remaining_volume > 0:
                volume_factor = min(2.0, remaining_volume / target_session_volume)
                session_adjusted_size *= volume_factor
            else:
                session_adjusted_size *= 0.5  # ลดขนาดถ้าทำ volume เกินแล้ว
            
            reasoning = f"{session.value} session - {session_params['base_multiplier']}x multiplier"
            
            return session_adjusted_size, reasoning
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Session Size: {e}")
            return base_lot_size, "ไม่สามารถปรับตาม session ได้"

class RecoveryAwareSizer:
    """
    คำนวณ Position Size โดยคำนึงถึง Recovery System
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Recovery-based multipliers
        self.recovery_multipliers = {
            0: 1.0,      # ไม่มี recovery positions
            1: 0.9,      # มี 1 recovery position
            2: 0.8,      # มี 2 recovery positions
            3: 0.7,      # มี 3 recovery positions
            4: 0.6,      # มี 4 recovery positions
        }
    
    def adjust_for_recovery(self, base_lot_size: float, recovery_positions: int,
                          recovery_method: Optional[RecoveryMethod] = None) -> Tuple[float, str]:
        """
        ปรับ Position Size ตาม Recovery status
        """
        try:
            # ปรับตามจำนวน recovery positions
            recovery_count = min(recovery_positions, 4)  # จำกัดที่ 4
            multiplier = self.recovery_multipliers.get(recovery_count, 0.5)
            
            # ปรับเพิ่มเติมตาม Recovery Method
            if recovery_method == RecoveryMethod.MARTINGALE_SMART:
                # Martingale ต้องการ capital สำรอง
                multiplier *= 0.8
            elif recovery_method == RecoveryMethod.GRID_INTELLIGENT:
                # Grid ต้องการ positions หลายๆ ตัว
                multiplier *= 0.9
            elif recovery_method == RecoveryMethod.HEDGING_ADVANCED:
                # Hedging ต้องการ positions คู่
                multiplier *= 0.85
            
            adjusted_size = base_lot_size * multiplier
            
            reasoning = f"ปรับตาม Recovery: {recovery_positions} positions, multiplier {multiplier:.1f}x"
            
            return adjusted_size, reasoning
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการปรับตาม Recovery: {e}")
            return base_lot_size, "ไม่สามารถปรับตาม recovery ได้"

class PositionSizer:
    """
    🎯 Main Position Sizer Class
    
    เครื่องมือหลักสำหรับคำนวณ Position Size แบบ Dynamic และ Intelligent
    รองรับ High-Frequency Trading และ Recovery System
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Core Components
        self.market_impact_calculator = MarketImpactCalculator()
        self.volatility_adjuster = VolatilityAdjuster()
        self.session_sizer = SessionBasedSizer()
        self.recovery_sizer = RecoveryAwareSizer()
        
        # External Connections
        self.market_analyzer = None      # จะเชื่อมต่อใน start()
        self.position_tracker = None     # จะเชื่อมต่อใน start()
        self.recovery_engine = None      # จะเชื่อมต่อใน start()
        
        # Sizing Parameters
        self.current_parameters = SizingParameters()
        self.default_strategy = SizingStrategy.MARKET_CONDITIONS
        
        # Statistics
        self.sizing_calculations_today = 0
        self.average_lot_size = 0.1
        self.total_volume_allocated = 0.0
        
        # Threading
        self.parameters_lock = threading.Lock()
        self.update_thread = None
        self.parameters_active = False
        
        self.logger.info("💰 เริ่มต้น Position Sizer")
    
    @handle_trading_errors(ErrorCategory.POSITION_SIZING, ErrorSeverity.MEDIUM)
    async def start_position_sizer(self) -> None:
        """
        เริ่มต้น Position Sizer
        """
        self.logger.info("🚀 เริ่มต้น Position Sizer System")
        
        # เชื่อมต่อ External Components
        try:
            from market_intelligence.market_analyzer import MarketAnalyzer
            self.market_analyzer = MarketAnalyzer()
        except ImportError:
            self.logger.warning("⚠️ ไม่สามารถเชื่อมต่อ Market Analyzer")
        
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
        
        # เริ่ม Parameter Update Thread
        self.parameters_active = True
        self.update_thread = threading.Thread(target=self._parameters_update_loop, daemon=True)
        self.update_thread.start()
        
        # อัพเดท Parameters ครั้งแรก
        await self._update_sizing_parameters()
        
        self.logger.info("✅ Position Sizer System เริ่มทำงานแล้ว")
    
    def calculate_position_size(self, entry_strategy: EntryStrategy,
                              market_conditions: Dict[str, Any],
                              recovery_context: Optional[Dict[str, Any]] = None,
                              custom_parameters: Optional[SizingParameters] = None) -> SizingResult:
        """
        คำนวณ Position Size หลัก
        """
        try:
            # ใช้ parameters ที่กำหนดหรือปัจจุบัน
            params = custom_parameters or self.current_parameters
            
            # เลือกกลยุทธ์การคำนวณ
            sizing_strategy = self._select_sizing_strategy(entry_strategy, market_conditions, recovery_context)
            
            # คำนวณ Base Lot Size
            base_lot_size = self._calculate_base_lot_size(params, sizing_strategy)
            
            # ปรับตาม Market Conditions
            market_adjusted_size, market_reasoning = self._adjust_for_market_conditions(
                base_lot_size, market_conditions, params
            )
            
            # ปรับตาม Session
            session_adjusted_size, session_reasoning = self.session_sizer.calculate_session_size(
                market_adjusted_size, params.current_session, 
                params.daily_volume_target, params.current_daily_volume
            )
            
            # ปรับตาม Recovery Context
            recovery_adjusted_size, recovery_reasoning = self._adjust_for_recovery_context(
                session_adjusted_size, recovery_context
            )
            
            # ปรับตาม Volatility
            final_lot_size, volatility_reasoning = self.volatility_adjuster.adjust_for_volatility(
                recovery_adjusted_size, params.current_volatility, params.atr_value
            )
            
            # ตรวจสอบขีดจำกัด
            final_lot_size, limit_warnings = self._apply_limits(final_lot_size, params)
            
            # คำนวณ Market Impact
            market_impact, impact_score = self.market_impact_calculator.calculate_market_impact(
                final_lot_size, params.current_session, params.current_volatility
            )
            
            # สร้างผลลัพธ์
            result = self._create_sizing_result(
                final_lot_size, sizing_strategy, params, market_impact,
                [market_reasoning, session_reasoning, recovery_reasoning, volatility_reasoning],
                limit_warnings
            )
            
            # บันทึกสถิติ
            self._update_sizing_statistics(final_lot_size)
            
            self.logger.debug(f"💰 คำนวณ Position Size: {final_lot_size:.2f} lots | "
                            f"Strategy: {sizing_strategy.value} | "
                            f"Confidence: {result.confidence_score:.1f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Position Size: {e}")
            return self._create_fallback_result()
    
    def _select_sizing_strategy(self, entry_strategy: EntryStrategy,
                              market_conditions: Dict[str, Any],
                              recovery_context: Optional[Dict[str, Any]]) -> SizingStrategy:
        """
        เลือกกลยุทธ์การคำนวณ Position Size
        """
        try:
            # ถ้ามี Recovery Context ให้ใช้ Recovery Adaptive
            if recovery_context and recovery_context.get('recovery_positions', 0) > 0:
                return SizingStrategy.RECOVERY_ADAPTIVE
            
            # ตรวจสอบ Volume Target
            remaining_volume = self.current_parameters.remaining_volume_target
            if remaining_volume > self.current_parameters.daily_volume_target * 0.8:
                return SizingStrategy.VOLUME_TARGET
            
            # ตรวจสอบ Market Conditions
            volatility = market_conditions.get('volatility_level', 'MODERATE')
            if volatility in ['HIGH', 'VERY_HIGH']:
                return SizingStrategy.VOLATILITY_BASED
            
            # ตรวจสอบ Session
            current_hour = datetime.now().hour
            if 20 <= current_hour <= 23 or 0 <= current_hour <= 2:  # Overlap period
                return SizingStrategy.SESSION_BASED
            
            # Default strategy
            return self.default_strategy
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเลือก Sizing Strategy: {e}")
            return SizingStrategy.CAPITAL_PERCENTAGE
    
    def _calculate_base_lot_size(self, params: SizingParameters, strategy: SizingStrategy) -> float:
        """
        คำนวณ Base Lot Size ตามกลยุทธ์
        """
        try:
            if strategy == SizingStrategy.FIXED_LOT:
                return 0.1  # Fixed 0.1 lots
            
            elif strategy == SizingStrategy.CAPITAL_PERCENTAGE:
                # คำนวณจากเปอร์เซ็นต์ของเงินทุน
                risk_amount = params.account_equity * params.max_risk_per_trade
                return max(0.01, min(10.0, risk_amount / 1000.0))  # Assume $1000 per lot risk
            
            elif strategy == SizingStrategy.VOLATILITY_BASED:
                # คำนวณจาก ATR
                if params.atr_value > 0:
                    base_size = 200.0 / params.atr_value  # เป้าหมาย risk $200
                    return max(0.01, min(5.0, base_size))
                return 0.1
            
            elif strategy == SizingStrategy.VOLUME_TARGET:
                # คำนวณจากเป้าหมาย Volume
                hours_remaining = 24 - datetime.now().hour
                if hours_remaining > 0:
                    hourly_target = params.remaining_volume_target / hours_remaining
                    return max(0.01, min(2.0, hourly_target))
                return 0.1
            
            elif strategy == SizingStrategy.SESSION_BASED:
                # คำนวณตาม Session
                session_multipliers = {
                    MarketSession.ASIAN: 0.5,
                    MarketSession.LONDON: 1.0,
                    MarketSession.NEW_YORK: 0.8,
                    MarketSession.OVERLAP: 1.5
                }
                multiplier = session_multipliers.get(params.current_session, 1.0)
                return 0.1 * multiplier
            
            else:  # MARKET_CONDITIONS
                # คำนวณจากสภาพตลาดรวม
                base = 0.1
                
                # ปรับตาม Volatility
                volatility_adj = {
                    VolatilityLevel.VERY_LOW: 1.5,
                    VolatilityLevel.LOW: 1.2,
                    VolatilityLevel.MODERATE: 1.0,
                    VolatilityLevel.HIGH: 0.8,
                    VolatilityLevel.VERY_HIGH: 0.6
                }.get(params.current_volatility, 1.0)
                
                return base * volatility_adj
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Base Lot Size: {e}")
            return 0.1  # Fallback
    
    def _adjust_for_market_conditions(self, base_size: float, market_conditions: Dict[str, Any],
                                    params: SizingParameters) -> Tuple[float, str]:
        """
        ปรับ Position Size ตาม Market Conditions
        """
        try:
            adjusted_size = base_size
            adjustments = []
            
            # ปรับตาม Trend Strength
            trend_strength = market_conditions.get('trend_strength', 'MODERATE')
            if trend_strength == 'STRONG':
                adjusted_size *= 1.2
                adjustments.append("เพิ่ม 20% สำหรับ Strong Trend")
            elif trend_strength == 'WEAK':
                adjusted_size *= 0.8
                adjustments.append("ลด 20% สำหรับ Weak Trend")
            
            # ปรับตาม Market State
            market_state = market_conditions.get('market_state', 'RANGING')
            if market_state == 'TRENDING':
                adjusted_size *= 1.1
                adjustments.append("เพิ่ม 10% สำหรับ Trending Market")
            elif market_state == 'VOLATILE':
                adjusted_size *= 0.9
                adjustments.append("ลด 10% สำหรับ Volatile Market")
            
            # ปรับตาม Support/Resistance
            near_key_level = market_conditions.get('near_key_level', False)
            if near_key_level:
                adjusted_size *= 0.85
                adjustments.append("ลด 15% เนื่องจากใกล้ Key Level")
            
            reasoning = "Market Conditions: " + ", ".join(adjustments) if adjustments else "ไม่มีการปรับแต่ง"
            
            return adjusted_size, reasoning
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการปรับตาม Market Conditions: {e}")
            return base_size, "ไม่สามารถปรับตาม market conditions ได้"
    
    def _adjust_for_recovery_context(self, base_size: float, 
                                   recovery_context: Optional[Dict[str, Any]]) -> Tuple[float, str]:
        """
        ปรับ Position Size ตาม Recovery Context
        """
        try:
            if not recovery_context:
                return base_size, "ไม่มี Recovery Context"
            
            recovery_positions = recovery_context.get('recovery_positions', 0)
            recovery_method = recovery_context.get('recovery_method')
            
            if recovery_positions == 0:
                return base_size, "ไม่มี Recovery Positions"
            
            # ใช้ Recovery Sizer
            adjusted_size, reasoning = self.recovery_sizer.adjust_for_recovery(
                base_size, recovery_positions, recovery_method
            )
            
            return adjusted_size, reasoning
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการปรับตาม Recovery Context: {e}")
            return base_size, "ไม่สามารถปรับตาม recovery context ได้"
    
    def _apply_limits(self, lot_size: float, params: SizingParameters) -> Tuple[float, List[str]]:
        """
        ใช้ขีดจำกัดต่างๆ กับ Position Size
        """
        warnings = []
        original_size = lot_size
        
        try:
            # ขีดจำกัดขั้นต่ำ
            min_lot = 0.01
            if lot_size < min_lot:
                lot_size = min_lot
                warnings.append(f"ปรับเป็น Min Lot Size: {min_lot}")
            
            # ขีดจำกัดสูงสุดตาม Free Margin
            max_lot_by_margin = params.free_margin / params.margin_required
            if lot_size > max_lot_by_margin:
                lot_size = max_lot_by_margin
                warnings.append(f"จำกัดด้วย Free Margin: {max_lot_by_margin:.2f} lots")
            
            # ขีดจำกัดสูงสุดตาม Daily Risk
            remaining_daily_risk = params.max_daily_risk - params.current_daily_risk
            if remaining_daily_risk > 0:
                max_lot_by_risk = (remaining_daily_risk * params.account_equity) / 1000.0
                if lot_size > max_lot_by_risk:
                    lot_size = max_lot_by_risk
                    warnings.append(f"จำกัดด้วย Daily Risk: {max_lot_by_risk:.2f} lots")
            else:
                lot_size = 0.01  # ขั้นต่ำถ้า risk เกิน
                warnings.append("Daily Risk เกินกำหนด - ใช้ขั้นต่ำ")
            
            # ขีดจำกัดสูงสุดสัมบูรณ์
            absolute_max = 10.0  # 10 lots สูงสุด
            if lot_size > absolute_max:
                lot_size = absolute_max
                warnings.append(f"จำกัดด้วยขีดจำกัดสัมบูรณ์: {absolute_max} lots")
            
            # ปัดเศษให้เหมาะสม
            lot_size = round(lot_size, 2)
            
            if lot_size != original_size:
                warnings.insert(0, f"ปรับจาก {original_size:.2f} เป็น {lot_size:.2f} lots")
            
            return lot_size, warnings
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการใช้ขีดจำกัด: {e}")
            return min(original_size, 0.1), ["ข้อผิดพลาดในการตรวจสอบขีดจำกัด"]
    
    def _create_sizing_result(self, lot_size: float, strategy: SizingStrategy,
                            params: SizingParameters, market_impact: str,
                            reasoning_parts: List[str], warnings: List[str]) -> SizingResult:
        """
        สร้าง SizingResult
        """
        try:
            # คำนวณ Risk Amount
            risk_amount = lot_size * 1000.0  # ประมาณ $1000 per lot
            
            # คำนวณ Margin Required
            margin_required = lot_size * params.margin_required
            
            # คำนวณ Confidence Score
            confidence_score = self._calculate_confidence_score(lot_size, params, market_impact)
            
            # คำนวณ Risk-Reward Ratio (ประมาณการ)
            risk_reward_ratio = 2.0  # Default 1:2
            
            # สร้าง Reasoning
            reasoning = " | ".join([r for r in reasoning_parts if r and r != "ไม่มีการปรับแต่ง"])
            
            # คำนวณ Max และ Min Lot Size
            max_lot_size = min(lot_size * 2.0, 5.0)
            min_lot_size = max(lot_size * 0.5, 0.01)
            
            return SizingResult(
                recommended_lot_size=lot_size,
                max_lot_size=max_lot_size,
                min_lot_size=min_lot_size,
                sizing_method=strategy,
                risk_amount=risk_amount,
                margin_required=margin_required,
                confidence_score=confidence_score,
                risk_reward_ratio=risk_reward_ratio,
                reasoning=reasoning,
                warnings=warnings,
                market_impact=market_impact,
                suggested_slippage=2.0,
                urgency_level=1
            )
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง SizingResult: {e}")
            return self._create_fallback_result()
    
    def _calculate_confidence_score(self, lot_size: float, params: SizingParameters,
                                  market_impact: str) -> float:
        """
        คำนวณ Confidence Score
        """
        try:
            score = 50.0  # Base score
            
            # ปรับตาม Market Impact
            impact_scores = {
                "VERY_LOW": 95.0,
                "LOW": 85.0,
                "MODERATE": 70.0,
                "HIGH": 55.0,
                "VERY_HIGH": 30.0
            }
            score = impact_scores.get(market_impact, 50.0)
            
            # ปรับตาม Free Margin
            margin_ratio = params.free_margin / (lot_size * params.margin_required)
            if margin_ratio > 10:
                score += 10
            elif margin_ratio > 5:
                score += 5
            elif margin_ratio < 2:
                score -= 20
            
            # ปรับตาม Daily Risk
            risk_usage = params.current_daily_risk / params.max_daily_risk
            if risk_usage < 0.5:
                score += 10
            elif risk_usage > 0.8:
                score -= 15
            
            # ปรับตาม Volume Target Progress
            volume_progress = params.current_daily_volume / params.daily_volume_target
            if 0.3 <= volume_progress <= 0.7:
                score += 5  # On track
            elif volume_progress > 0.9:
                score -= 10  # May be over-trading
            
            return max(0.0, min(100.0, score))
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Confidence Score: {e}")
            return 50.0
    
    def _create_fallback_result(self) -> SizingResult:
        """
        สร้าง Fallback Result เมื่อเกิดข้อผิดพลาด
        """
        return SizingResult(
            recommended_lot_size=0.1,
            max_lot_size=0.2,
            min_lot_size=0.01,
            sizing_method=SizingStrategy.FIXED_LOT,
            risk_amount=100.0,
            margin_required=100.0,
            confidence_score=30.0,
            risk_reward_ratio=1.0,
            reasoning="Fallback sizing due to calculation error",
            warnings=["ใช้ค่า default เนื่องจากข้อผิดพลาด"],
            market_impact="MODERATE"
        )
    
    def _update_sizing_statistics(self, lot_size: float) -> None:
        """
        อัพเดทสถิติการคำนวณ
        """
        try:
            self.sizing_calculations_today += 1
            self.total_volume_allocated += lot_size
            
            # คำนวณค่าเฉลี่ย
            self.average_lot_size = self.total_volume_allocated / self.sizing_calculations_today
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดทสถิติ: {e}")
    
    async def _update_sizing_parameters(self) -> None:
        """
        อัพเดท Sizing Parameters จาก External Sources
        """
        try:
            with self.parameters_lock:
                # อัพเดท Account Information
                if hasattr(self, 'account_monitor'):
                    account_info = await self.account_monitor.get_account_info()
                    if account_info:
                        self.current_parameters.account_balance = account_info.get('balance', 10000.0)
                        self.current_parameters.account_equity = account_info.get('equity', 10000.0)
                        self.current_parameters.free_margin = account_info.get('free_margin', 10000.0)
                
                # อัพเดท Market Conditions
                if self.market_analyzer:
                    market_state = self.market_analyzer.get_current_market_state()
                    self.current_parameters.atr_value = market_state.get('atr_value', 15.0)
                    self.current_parameters.current_session = self.market_analyzer.get_current_session()
                    
                    # อัพเดท Volatility Level
                    atr = self.current_parameters.atr_value
                    if atr < 5:
                        self.current_parameters.current_volatility = VolatilityLevel.VERY_LOW
                    elif atr < 10:
                        self.current_parameters.current_volatility = VolatilityLevel.LOW
                    elif atr < 20:
                        self.current_parameters.current_volatility = VolatilityLevel.MODERATE
                    elif atr < 30:
                        self.current_parameters.current_volatility = VolatilityLevel.HIGH
                    else:
                        self.current_parameters.current_volatility = VolatilityLevel.VERY_HIGH
                
                # อัพเดท Position Information
                if self.position_tracker:
                    positions = self.position_tracker.get_all_positions()
                    self.current_parameters.total_open_positions = len(positions)
                    
                    if positions:
                        volumes = [p.get('volume', 0.0) for p in positions]
                        self.current_parameters.largest_position_size = max(volumes)
                
                # อัพเดท Recovery Information
                if self.recovery_engine:
                    recovery_stats = self.recovery_engine.get_recovery_statistics()
                    active_recoveries = self.recovery_engine.get_active_recoveries()
                    self.current_parameters.recovery_positions = len(active_recoveries)
                
                # อัพเดท Volume Targets
                self._update_volume_targets()
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Parameters: {e}")
    
    def _update_volume_targets(self) -> None:
        """
        อัพเดทเป้าหมาย Volume
        """
        try:
            # คำนวณเป้าหมาย Volume ประจำวัน
            target_min = self.settings.daily_volume_target_min
            target_max = self.settings.daily_volume_target_max
            self.current_parameters.daily_volume_target = (target_min + target_max) / 2
            
            # คำนวณ Volume ที่เหลือต้องทำ (จำลอง)
            # TODO: เชื่อมต่อกับระบบติดตาม Volume จริง
            hours_passed = datetime.now().hour
            expected_progress = hours_passed / 24.0
            expected_volume = self.current_parameters.daily_volume_target * expected_progress
            
            # สมมติว่าทำได้ 80% ของที่คาดหวัง
            self.current_parameters.current_daily_volume = expected_volume * 0.8
            self.current_parameters.remaining_volume_target = max(0, 
                self.current_parameters.daily_volume_target - self.current_parameters.current_daily_volume
            )
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Volume Targets: {e}")
    
    def _parameters_update_loop(self) -> None:
        """
        Loop สำหรับอัพเดท Parameters อย่างต่อเนื่อง
        """
        self.logger.info("🔄 เริ่มต้น Parameters Update Loop")
        
        while self.parameters_active:
            try:
                # อัพเดททุก 30 วินาที
                asyncio.run(self._update_sizing_parameters())
                time.sleep(30)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Parameters Update Loop: {e}")
                time.sleep(60)
    
    def stop_position_sizer(self) -> None:
        """
        หยุดการทำงานของ Position Sizer
        """
        self.logger.info("🛑 หยุด Position Sizer System")
        
        self.parameters_active = False
        
        # รอให้ Thread จบ
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5)
        
        self.logger.info("✅ Position Sizer System หยุดแล้ว")
    
    def get_sizing_statistics(self) -> Dict[str, Any]:
        """
        ดึงสถิติการทำงานของ Position Sizer
        """
        return {
            "sizing_calculations_today": self.sizing_calculations_today,
            "average_lot_size": round(self.average_lot_size, 3),
            "total_volume_allocated": round(self.total_volume_allocated, 2),
            "current_parameters": {
                "account_equity": self.current_parameters.account_equity,
                "daily_volume_target": self.current_parameters.daily_volume_target,
                "current_daily_volume": self.current_parameters.current_daily_volume,
                "remaining_volume_target": self.current_parameters.remaining_volume_target,
                "current_volatility": self.current_parameters.current_volatility.value,
                "current_session": self.current_parameters.current_session.value,
                "total_open_positions": self.current_parameters.total_open_positions,
                "recovery_positions": self.current_parameters.recovery_positions
            },
            "parameters_active": self.parameters_active
        }
    
    def get_current_parameters(self) -> SizingParameters:
        """
        ดึง Current Sizing Parameters
        """
        with self.parameters_lock:
            return self.current_parameters
    
    def update_parameters(self, new_parameters: SizingParameters) -> bool:
        """
        อัพเดท Sizing Parameters แบบ Manual
        """
        try:
            with self.parameters_lock:
                self.current_parameters = new_parameters
            
            self.logger.info("✅ อัพเดท Sizing Parameters สำเร็จ")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Parameters: {e}")
            return False
    
    def calculate_optimal_size_for_recovery(self, recovery_task_id: str,
                                          recovery_method: RecoveryMethod,
                                          original_loss: float) -> SizingResult:
        """
        คำนวณ Position Size ที่เหมาะสมสำหรับ Recovery
        """
        try:
            # สร้าง Recovery Context
            recovery_context = {
                'recovery_positions': self.current_parameters.recovery_positions + 1,
                'recovery_method': recovery_method,
                'original_loss': original_loss,
                'recovery_task_id': recovery_task_id
            }
            
            # คำนวณ Size สำหรับ Recovery
            market_conditions = {}
            if self.market_analyzer:
                market_conditions = self.market_analyzer.get_current_market_state()
            
            result = self.calculate_position_size(
                EntryStrategy.MEAN_REVERSION,  # Recovery มักใช้ Mean Reversion
                market_conditions,
                recovery_context
            )
            
            # ปรับเพิ่มเติมสำหรับ Recovery
            if recovery_method == RecoveryMethod.MARTINGALE_SMART:
                # Martingale ต้องการขนาดที่เพิ่มขึ้น
                result.recommended_lot_size *= 1.5
            elif recovery_method == RecoveryMethod.GRID_INTELLIGENT:
                # Grid ใช้ขนาดเล็กหลายๆ ตัว
                result.recommended_lot_size *= 0.7
            
            result.reasoning += f" | Recovery for {recovery_method.value}"
            
            self.logger.info(f"💰 คำนวณ Recovery Size: {result.recommended_lot_size:.2f} lots "
                           f"สำหรับ {recovery_method.value}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Recovery Size: {e}")
            return self._create_fallback_result()

# === GLOBAL POSITION SIZER INSTANCE ===
_global_position_sizer: Optional[PositionSizer] = None

def get_position_sizer() -> PositionSizer:
    """
    ดึง PositionSizer แบบ Singleton
    """
    global _global_position_sizer
    if _global_position_sizer is None:
        _global_position_sizer = PositionSizer()
    return _global_position_sizer

# === CONVENIENCE FUNCTIONS ===
def calculate_lot_size(entry_strategy: EntryStrategy,
                      market_conditions: Dict[str, Any],
                      recovery_context: Optional[Dict[str, Any]] = None) -> SizingResult:
    """
    ฟังก์ชันสะดวกสำหรับคำนวณ Lot Size
    """
    sizer = get_position_sizer()
    return sizer.calculate_position_size(entry_strategy, market_conditions, recovery_context)

def get_sizing_stats() -> Dict[str, Any]:
    """
    ฟังก์ชันสะดวกสำหรับดึงสถิติ
    """
    sizer = get_position_sizer()
    return sizer.get_sizing_statistics()

def calculate_recovery_size(recovery_task_id: str, recovery_method: RecoveryMethod,
                          original_loss: float) -> SizingResult:
    """
    ฟังก์ชันสะดวกสำหรับคำนวณ Recovery Size
    """
    sizer = get_position_sizer()
    return sizer.calculate_optimal_size_for_recovery(recovery_task_id, recovery_method, original_loss)

async def main():
    """
    ทดสอบการทำงานของ Position Sizer
    """
    print("🧪 ทดสอบ Position Sizer")
    
    sizer = get_position_sizer()
    
    try:
        await sizer.start_position_sizer()
        
        # ทดสอบการคำนวณ Position Size
        market_conditions = {
            'market_state': 'TRENDING',
            'trend_strength': 'STRONG',
            'volatility_level': 'MODERATE',
            'atr_value': 15.0,
            'near_key_level': False
        }
        
        result1 = sizer.calculate_position_size(
            EntryStrategy.TREND_FOLLOWING,
            market_conditions
        )
        
        print(f"📊 Position Size 1: {result1.recommended_lot_size:.2f} lots")
        print(f"   Confidence: {result1.confidence_score:.1f}%")
        print(f"   Reasoning: {result1.reasoning}")
        print(f"   Warnings: {result1.warnings}")
        
        # ทดสอบ Recovery Size
        recovery_result = sizer.calculate_optimal_size_for_recovery(
            "REC_TEST_001",
            RecoveryMethod.MARTINGALE_SMART,
            -100.0
        )
        
        print(f"🔄 Recovery Size: {recovery_result.recommended_lot_size:.2f} lots")
        print(f"   Method: {recovery_result.sizing_method.value}")
        
        # แสดงสถิติ
        stats = sizer.get_sizing_statistics()
        print(f"📈 สถิติ Position Sizer:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        
    finally:
        sizer.stop_position_sizer()

if __name__ == "__main__":
    asyncio.run(main())