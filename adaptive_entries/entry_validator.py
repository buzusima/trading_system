#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRY VALIDATOR - Signal Validation System
=========================================
ระบบตรวจสอบและกรองสัญญาณการเข้าเทรดแบบอัจฉริยะ
รับผิดชอบการประเมินคุณภาพสัญญาณและความเหมาะสมในการเข้าเทรด

Key Features:
- Multi-criteria signal quality assessment
- Risk-reward ratio evaluation and optimization
- Market condition suitability analysis
- Historical performance validation
- Real-time signal filtering and ranking
- Integration with all entry_engines
- High-frequency signal processing (50-100 lots/day)
- Recovery-focused validation (No Stop Loss requirement)

เชื่อมต่อไปยัง:
- adaptive_entries/signal_generator.py (รับสัญญาณ)
- adaptive_entries/entry_engines/* (ตรวจสอบ engines ทั้งหมด)
- market_intelligence/market_analyzer.py (สภาพตลาด)
- analytics_engine/performance_tracker.py (ประสิทธิภาพในอดีต)
- position_management/position_tracker.py (สถานะ positions)
"""

import asyncio
import threading
import time
import statistics
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from enum import Enum
import json
import numpy as np
from collections import defaultdict, deque

# เชื่อมต่อ internal modules
from config.settings import get_system_settings, MarketSession
from config.trading_params import get_trading_parameters, EntryStrategy, RecoveryMethod
from utilities.professional_logger import setup_trading_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity
    
class ValidationCriteria(Enum):
    """เกณฑ์การตรวจสอบสัญญาณ"""
    SIGNAL_STRENGTH = "signal_strength"              # ความแรงของสัญญาณ
    MARKET_SUITABILITY = "market_suitability"        # ความเหมาะสมกับสภาพตลาด
    RISK_REWARD_RATIO = "risk_reward_ratio"          # อัตราส่วนความเสี่ยงต่อผลตอบแทน
    HISTORICAL_PERFORMANCE = "historical_performance" # ประสิทธิภาพในอดีต
    ENTRY_TIMING = "entry_timing"                    # จังหวะการเข้า
    RECOVERY_POTENTIAL = "recovery_potential"        # ศักยภาพในการ Recovery
    CORRELATION_ANALYSIS = "correlation_analysis"    # การวิเคราะห์ความสัมพันธ์
    VOLUME_SUITABILITY = "volume_suitability"        # ความเหมาะสมกับปริมาณการเทรด

class SignalQuality(Enum):
    """ระดับคุณภาพสัญญาณ"""
    EXCELLENT = "excellent"      # คะแนน 90-100%
    GOOD = "good"               # คะแนน 75-89%
    FAIR = "fair"               # คะแนน 60-74%
    POOR = "poor"               # คะแนน 40-59%
    REJECTED = "rejected"       # คะแนน < 40%

@dataclass
class ValidationResult:
    """ผลการตรวจสอบสัญญาณ"""
    signal_id: str
    is_valid: bool
    overall_score: float
    quality_level: SignalQuality
    
    # คะแนนแต่ละเกณฑ์
    criteria_scores: Dict[ValidationCriteria, float] = field(default_factory=dict)
    
    # เหตุผลและคำแนะนำ
    validation_reasons: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    
    # ข้อมูลเพิ่มเติม
    recommended_volume: float = 0.0
    recommended_recovery_method: Optional[RecoveryMethod] = None
    priority_level: int = 50  # 1-100, สูงกว่า = สำคัญกว่า
    
    # Timing Information
    validation_time: datetime = field(default_factory=datetime.now)
    expiry_time: Optional[datetime] = None

@dataclass
class SignalContext:
    """บริบทของสัญญาณสำหรับการตรวจสอบ"""
    signal_id: str
    entry_strategy: EntryStrategy
    direction: str  # "BUY" หรือ "SELL"
    entry_price: float
    confidence_level: float
    
    # Market Context
    market_session: MarketSession
    market_conditions: Dict[str, Any]
    
    # Technical Context
    timeframe: str
    indicators_data: Dict[str, float]
    
    # System Context
    current_positions: List[Dict[str, Any]]
    account_equity: float
    daily_volume_progress: float

class MarketSuitabilityAnalyzer:
    """
    วิเคราะห์ความเหมาะสมของสัญญาณกับสภาพตลาดปัจจุบัน
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Market State Definitions
        self.trending_conditions = {
            'adx_min': 25.0,
            'ma_alignment': True,
            'momentum_strength': 0.7
        }
        
        self.ranging_conditions = {
            'adx_max': 20.0,
            'bb_squeeze': True,
            'volatility_low': True
        }
        
        self.volatile_conditions = {
            'atr_multiplier': 1.5,
            'bb_width_high': True,
            'price_gaps': True
        }
    
    def analyze_suitability(self, signal_context: SignalContext) -> Tuple[float, List[str]]:
        """
        วิเคราะห์ความเหมาะสมของสัญญาณกับสภาพตลาด
        
        Returns:
            Tuple[float, List[str]]: (คะแนนความเหมาะสม 0-100, เหตุผล)
        """
        try:
            market_conditions = signal_context.market_conditions
            entry_strategy = signal_context.entry_strategy
            
            suitability_score = 0.0
            reasons = []
            
            # วิเคราะห์ตามประเภท Market State
            market_state = market_conditions.get('market_state', 'UNKNOWN')
            
            if market_state == 'TRENDING':
                score, reason_list = self._analyze_trending_suitability(signal_context)
                suitability_score += score * 0.4
                reasons.extend(reason_list)
                
            elif market_state == 'RANGING':
                score, reason_list = self._analyze_ranging_suitability(signal_context)
                suitability_score += score * 0.4
                reasons.extend(reason_list)
                
            elif market_state == 'VOLATILE':
                score, reason_list = self._analyze_volatile_suitability(signal_context)
                suitability_score += score * 0.4
                reasons.extend(reason_list)
            
            # วิเคราะห์ตาม Session
            session_score, session_reasons = self._analyze_session_suitability(signal_context)
            suitability_score += session_score * 0.3
            reasons.extend(session_reasons)
            
            # วิเคราะห์ Volatility Match
            volatility_score, vol_reasons = self._analyze_volatility_match(signal_context)
            suitability_score += volatility_score * 0.3
            reasons.extend(vol_reasons)
            
            return min(100.0, suitability_score), reasons
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์ความเหมาะสม: {e}")
            return 0.0, ["ข้อผิดพลาดในการวิเคราะห์"]
    
    def _analyze_trending_suitability(self, signal_context: SignalContext) -> Tuple[float, List[str]]:
        """วิเคราะห์ความเหมาะสมในตลาด Trending"""
        reasons = []
        score = 0.0
        
        strategy = signal_context.entry_strategy
        market_data = signal_context.market_conditions
        
        # Strategy ที่เหมาะกับ Trending Market
        if strategy in [EntryStrategy.TREND_FOLLOWING, EntryStrategy.BREAKOUT_MOMENTUM]:
            score += 30.0
            reasons.append("✅ Strategy เหมาะสมกับตลาด Trending")
        else:
            score += 10.0
            reasons.append("⚠️ Strategy ไม่เหมาะสมที่สุดกับตลาด Trending")
        
        # ADX Strength
        adx = market_data.get('adx_current', 0)
        if adx > 35:
            score += 25.0
            reasons.append(f"✅ ADX แรงมาก ({adx:.1f})")
        elif adx > 25:
            score += 15.0
            reasons.append(f"✅ ADX ปานกลาง ({adx:.1f})")
        
        # Trend Direction Alignment
        trend_direction = market_data.get('trend_direction', 'NEUTRAL')
        signal_direction = signal_context.direction
        
        if (trend_direction == 'BULLISH' and signal_direction == 'BUY') or \
           (trend_direction == 'BEARISH' and signal_direction == 'SELL'):
            score += 20.0
            reasons.append("✅ ทิศทางสัญญาณสอดคล้องกับเทรนด์")
        else:
            score += 5.0
            reasons.append("⚠️ ทิศทางสัญญาณขัดกับเทรนด์")
        
        return score, reasons
    
    def _analyze_ranging_suitability(self, signal_context: SignalContext) -> Tuple[float, List[str]]:
        """วิเคราะห์ความเหมาะสมในตลาด Ranging"""
        reasons = []
        score = 0.0
        
        strategy = signal_context.entry_strategy
        market_data = signal_context.market_conditions
        
        # Strategy ที่เหมาะกับ Ranging Market
        if strategy in [EntryStrategy.MEAN_REVERSION, EntryStrategy.SCALPING_QUICK]:
            score += 30.0
            reasons.append("✅ Strategy เหมาะสมกับตลาด Ranging")
        else:
            score += 15.0
            reasons.append("⚠️ Strategy ไม่เหมาะสมที่สุดกับตลาด Ranging")
        
        # Support/Resistance Level
        price_position = market_data.get('price_position_in_range', 0.5)
        if price_position <= 0.2 or price_position >= 0.8:
            score += 25.0
            reasons.append("✅ ราคาอยู่ใกล้ขอบ Range")
        else:
            score += 10.0
            reasons.append("⚠️ ราคาอยู่กลาง Range")
        
        # Range Stability
        range_stability = market_data.get('range_stability', 0.0)
        if range_stability > 0.7:
            score += 20.0
            reasons.append("✅ Range มีเสถียรภาพสูง")
        
        return score, reasons
    
    def _analyze_volatile_suitability(self, signal_context: SignalContext) -> Tuple[float, List[str]]:
        """วิเคราะห์ความเหมาะสมในตลาด Volatile"""
        reasons = []
        score = 0.0
        
        strategy = signal_context.entry_strategy
        market_data = signal_context.market_conditions
        
        # Strategy ที่เหมาะกับ Volatile Market
        if strategy in [EntryStrategy.FALSE_BREAKOUT, EntryStrategy.NEWS_REACTION]:
            score += 30.0
            reasons.append("✅ Strategy เหมาะสมกับตลาด Volatile")
        
        # Volatility Level
        atr_ratio = market_data.get('atr_ratio', 1.0)
        if atr_ratio > 1.5:
            score += 25.0
            reasons.append(f"✅ Volatility สูง (ATR Ratio: {atr_ratio:.2f})")
        
        return score, reasons
    
    def _analyze_session_suitability(self, signal_context: SignalContext) -> Tuple[float, List[str]]:
        """วิเคราะห์ความเหมาะสมตาม Session"""
        reasons = []
        score = 0.0
        
        session = signal_context.market_session
        strategy = signal_context.entry_strategy
        
        # Session-Strategy Matching
        session_strategy_map = {
            MarketSession.ASIAN: [EntryStrategy.MEAN_REVERSION, EntryStrategy.SCALPING_QUICK],
            MarketSession.LONDON: [EntryStrategy.TREND_FOLLOWING, EntryStrategy.BREAKOUT_MOMENTUM],
            MarketSession.NEW_YORK: [EntryStrategy.NEWS_REACTION, EntryStrategy.FALSE_BREAKOUT],
            MarketSession.OVERLAP: [EntryStrategy.FALSE_BREAKOUT, EntryStrategy.BREAKOUT_MOMENTUM]
        }
        
        if strategy in session_strategy_map.get(session, []):
            score += 40.0
            reasons.append(f"✅ Strategy เหมาะสมกับ {session.value} Session")
        else:
            score += 20.0
            reasons.append(f"⚠️ Strategy ไม่เหมาะสมที่สุดกับ {session.value} Session")
        
        return score, reasons
    
    def _analyze_volatility_match(self, signal_context: SignalContext) -> Tuple[float, List[str]]:
        """วิเคราะห์ความเหมาะสมของ Volatility"""
        reasons = []
        score = 0.0
        
        current_volatility = signal_context.market_conditions.get('current_volatility', 0.0)
        optimal_volatility = signal_context.market_conditions.get('strategy_optimal_volatility', 0.0)
        
        if optimal_volatility > 0:
            volatility_match = 1.0 - abs(current_volatility - optimal_volatility) / optimal_volatility
            score = max(0, volatility_match * 50.0)
            
            if volatility_match > 0.8:
                reasons.append("✅ Volatility เหมาะสมมาก")
            elif volatility_match > 0.6:
                reasons.append("✅ Volatility เหมาะสม")
            else:
                reasons.append("⚠️ Volatility ไม่เหมาะสม")
        
        return score, reasons

class RiskRewardAnalyzer:
    """
    วิเคราะห์อัตราส่วน Risk-Reward สำหรับสัญญาณ
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.min_acceptable_ratio = 1.5  # อัตราส่วนขั้นต่ำที่ยอมรับได้
        self.preferred_ratio = 2.0       # อัตราส่วนที่ต้องการ
    
    def calculate_risk_reward(self, signal_context: SignalContext) -> Tuple[float, float, List[str]]:
        """
        คำนวณ Risk-Reward Ratio
        
        Returns:
            Tuple[float, float, List[str]]: (Risk-Reward Ratio, Score 0-100, เหตุผล)
        """
        try:
            reasons = []
            
            # คำนวณ Potential Profit (เนื่องจากไม่มี TP ต้องใช้วิธีอื่น)
            potential_profit = self._calculate_potential_profit(signal_context)
            
            # คำนวณ Potential Risk (เนื่องจากไม่มี SL ใช้ Recovery Cost แทน)
            potential_risk = self._calculate_recovery_cost(signal_context)
            
            if potential_risk <= 0:
                return 0.0, 0.0, ["❌ ไม่สามารถคำนวณ Risk ได้"]
            
            # คำนวณ Risk-Reward Ratio
            rr_ratio = potential_profit / potential_risk
            
            # คำนวณคะแนน
            score = self._calculate_rr_score(rr_ratio)
            
            # สร้าง Reasons
            reasons.append(f"📊 Risk-Reward Ratio: {rr_ratio:.2f}")
            reasons.append(f"💰 Potential Profit: {potential_profit:.2f}")
            reasons.append(f"⚠️ Recovery Cost: {potential_risk:.2f}")
            
            if rr_ratio >= self.preferred_ratio:
                reasons.append("✅ Risk-Reward Ratio ดีเลิศ")
            elif rr_ratio >= self.min_acceptable_ratio:
                reasons.append("✅ Risk-Reward Ratio ยอมรับได้")
            else:
                reasons.append("❌ Risk-Reward Ratio ต่ำเกินไป")
            
            return rr_ratio, score, reasons
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Risk-Reward: {e}")
            return 0.0, 0.0, ["ข้อผิดพลาดในการคำนวณ"]
    
    def _calculate_potential_profit(self, signal_context: SignalContext) -> float:
        """คำนวณ Potential Profit จากสัญญาณ"""
        # ใช้ข้อมูลทางเทคนิคเพื่อประมาณ Target
        market_data = signal_context.market_conditions
        
        # ใช้ ATR เป็นฐานในการคำนวณ Target
        atr = market_data.get('atr_current', 0.01)
        
        # Target แตกต่างกันไปตาม Strategy
        strategy = signal_context.entry_strategy
        
        target_multipliers = {
            EntryStrategy.SCALPING_QUICK: 0.5,      # Scalping = Target ใกล้
            EntryStrategy.MEAN_REVERSION: 1.0,      # Mean Reversion = Target ปานกลาง
            EntryStrategy.TREND_FOLLOWING: 2.0,     # Trend Following = Target ไกล
            EntryStrategy.BREAKOUT_MOMENTUM: 1.5,   # Breakout = Target ปานกลาง-ไกล
            EntryStrategy.FALSE_BREAKOUT: 1.0,      # False Breakout = Target ปานกลาง
            EntryStrategy.NEWS_REACTION: 1.5        # News = Target ปานกลาง-ไกล
        }
        
        multiplier = target_multipliers.get(strategy, 1.0)
        target_distance = atr * multiplier
        
        # คำนวณ Profit ต่อ Lot (สำหรับ XAUUSD)
        # 1 pip ของ XAUUSD = $0.01 per 0.01 lot
        profit_per_pip = 1.0  # สำหรับ 0.01 lot
        profit_in_pips = target_distance * 100  # แปลงเป็น pips
        
        potential_profit = profit_in_pips * profit_per_pip
        
        return potential_profit
    
    def _calculate_recovery_cost(self, signal_context: SignalContext) -> float:
        """คำนวณต้นทุนในการ Recovery"""
        # คำนวณต้นทุนเฉลี่ยสำหรับการ Recovery
        market_data = signal_context.market_conditions
        
        # ใช้ ATR และ Market Volatility ในการประมาณต้นทุน Recovery
        atr = market_data.get('atr_current', 0.01)
        volatility = market_data.get('current_volatility', 1.0)
        
        # ต้นทุน Recovery ขึ้นกับ Strategy และ Market Condition
        strategy = signal_context.entry_strategy
        
        recovery_cost_multipliers = {
            EntryStrategy.SCALPING_QUICK: 0.3,      # Scalping = Recovery ง่าย
            EntryStrategy.MEAN_REVERSION: 0.5,      # Mean Reversion = Recovery ปานกลาง
            EntryStrategy.TREND_FOLLOWING: 0.8,     # Trend Following = Recovery ยาก
            EntryStrategy.BREAKOUT_MOMENTUM: 0.7,   # Breakout = Recovery ค่อนข้างยาก
            EntryStrategy.FALSE_BREAKOUT: 0.4,      # False Breakout = Recovery ง่าย
            EntryStrategy.NEWS_REACTION: 0.6        # News = Recovery ปานกลาง
        }
        
        multiplier = recovery_cost_multipliers.get(strategy, 0.5)
        base_cost = atr * multiplier * volatility
        
        # แปลงเป็นค่าใช้จ่ายจริง
        cost_per_pip = 1.0  # สำหรับ 0.01 lot
        cost_in_pips = base_cost * 100
        
        recovery_cost = cost_in_pips * cost_per_pip
        
        return recovery_cost
    
    def _calculate_rr_score(self, rr_ratio: float) -> float:
        """คำนวณคะแนนจาก Risk-Reward Ratio"""
        if rr_ratio >= 3.0:
            return 100.0
        elif rr_ratio >= 2.5:
            return 90.0
        elif rr_ratio >= self.preferred_ratio:
            return 80.0
        elif rr_ratio >= self.min_acceptable_ratio:
            return 60.0
        elif rr_ratio >= 1.0:
            return 40.0
        else:
            return 20.0

class HistoricalPerformanceAnalyzer:
    """
    วิเคราะห์ประสิทธิภาพในอดีตของสัญญาณประเภทเดียวกัน
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.performance_cache = {}
        self.min_sample_size = 10  # จำนวนขั้นต่ำสำหรับการวิเคราะห์
    
    def analyze_historical_performance(self, signal_context: SignalContext) -> Tuple[float, List[str]]:
        """
        วิเคราะห์ประสิทธิภาพในอดีตของสัญญาณ
        
        Returns:
            Tuple[float, List[str]]: (คะแนนประสิทธิภาพ 0-100, เหตุผล)
        """
        try:
            # สร้าง Key สำหรับค้นหาข้อมูลในอดีต
            performance_key = self._create_performance_key(signal_context)
            
            # ดึงข้อมูลประสิทธิภาพในอดีต
            historical_data = self._get_historical_data(performance_key)
            
            if not historical_data or len(historical_data) < self.min_sample_size:
                return 50.0, ["⚠️ ข้อมูลในอดีตไม่เพียงพอสำหรับการวิเคราะห์"]
            
            # วิเคราะห์ประสิทธิภาพ
            performance_score, reasons = self._analyze_performance_data(historical_data)
            
            return performance_score, reasons
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์ประสิทธิภาพในอดีต: {e}")
            return 0.0, ["ข้อผิดพลาดในการวิเคราะห์"]
    
    def _create_performance_key(self, signal_context: SignalContext) -> str:
        """สร้าง Key สำหรับค้นหาข้อมูลในอดีต"""
        strategy = signal_context.entry_strategy.value
        session = signal_context.market_session.value
        market_state = signal_context.market_conditions.get('market_state', 'UNKNOWN')
        
        return f"{strategy}_{session}_{market_state}"
    
    def _get_historical_data(self, performance_key: str) -> List[Dict[str, Any]]:
        """ดึงข้อมูลประสิทธิภาพในอดีต"""
        # จำลองการดึงข้อมูลจากฐานข้อมูล
        # ในการใช้งานจริงจะเชื่อมต่อกับ performance_tracker
        
        try:
            # เชื่อมต่อกับ Performance Tracker
            from analytics_engine.performance_tracker import get_performance_tracker
            performance_tracker = get_performance_tracker()
            
            # ดึงข้อมูลการเทรดในอดีต
            historical_trades = performance_tracker.get_historical_trades(
                strategy_filter=performance_key,
                days_back=30
            )
            
            return historical_trades
            
        except ImportError:
            self.logger.warning("⚠️ ไม่สามารถเชื่อมต่อ Performance Tracker")
            return []
    
    def _analyze_performance_data(self, historical_data: List[Dict[str, Any]]) -> Tuple[float, List[str]]:
        """วิเคราะห์ข้อมูลประสิทธิภาพ"""
        reasons = []
        
        # คำนวณสถิติพื้นฐาน
        total_trades = len(historical_data)
        profitable_trades = sum(1 for trade in historical_data if trade.get('pnl', 0) > 0)
        win_rate = (profitable_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # คำนวณ Average PnL
        pnl_values = [trade.get('pnl', 0) for trade in historical_data]
        avg_pnl = statistics.mean(pnl_values) if pnl_values else 0
        
        # คำนวณ Recovery Rate (สำคัญมากสำหรับระบบนี้)
        recovery_count = sum(1 for trade in historical_data if trade.get('recovered', False))
        recovery_rate = (recovery_count / total_trades) * 100 if total_trades > 0 else 0
        
        # คำนวณคะแนนรวม
        score = 0.0
        
        # Win Rate Score (30%)
        if win_rate >= 70:
            score += 30.0
            reasons.append(f"✅ Win Rate สูง ({win_rate:.1f}%)")
        elif win_rate >= 50:
            score += 20.0
            reasons.append(f"✅ Win Rate ปานกลาง ({win_rate:.1f}%)")
        else:
            score += 10.0
            reasons.append(f"⚠️ Win Rate ต่ำ ({win_rate:.1f}%)")
        
        # Recovery Rate Score (40% - สำคัญที่สุด)
        if recovery_rate >= 95:
            score += 40.0
            reasons.append(f"✅ Recovery Rate ดีเลิศ ({recovery_rate:.1f}%)")
        elif recovery_rate >= 90:
            score += 35.0
            reasons.append(f"✅ Recovery Rate ดี ({recovery_rate:.1f}%)")
        elif recovery_rate >= 80:
            score += 25.0
            reasons.append(f"⚠️ Recovery Rate ปานกลาง ({recovery_rate:.1f}%)")
        else:
            score += 10.0
            reasons.append(f"❌ Recovery Rate ต่ำ ({recovery_rate:.1f}%)")
        
        # Average PnL Score (30%)
        if avg_pnl > 0:
            score += 30.0
            reasons.append(f"✅ Average PnL เป็นบวก ({avg_pnl:.2f})")
        elif avg_pnl >= -10:
            score += 15.0
            reasons.append(f"⚠️ Average PnL เกือบเป็นศูนย์ ({avg_pnl:.2f})")
        else:
            score += 5.0
            reasons.append(f"❌ Average PnL เป็นลบ ({avg_pnl:.2f})")
        
        reasons.append(f"📊 จำนวนเทรดในอดีต: {total_trades}")
        
        return score, reasons

class EntryTimingAnalyzer:
    """
    วิเคราะห์จังหวะเวลาในการเข้าเทรด
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Timing Preferences ตาม Strategy
        self.strategy_timing_preferences = {
            EntryStrategy.SCALPING_QUICK: {
                'optimal_spread': 2.0,      # pips
                'max_spread': 4.0,
                'volume_requirement': 'high',
                'news_avoidance': 5          # นาทีก่อน/หลังข่าว
            },
            EntryStrategy.TREND_FOLLOWING: {
                'optimal_spread': 3.0,
                'max_spread': 6.0,
                'volume_requirement': 'medium',
                'news_avoidance': 10
            },
            EntryStrategy.MEAN_REVERSION: {
                'optimal_spread': 2.5,
                'max_spread': 5.0,
                'volume_requirement': 'low',
                'news_avoidance': 15
            },
            EntryStrategy.BREAKOUT_MOMENTUM: {
                'optimal_spread': 4.0,
                'max_spread': 8.0,
                'volume_requirement': 'high',
                'news_avoidance': 5
            },
            EntryStrategy.FALSE_BREAKOUT: {
                'optimal_spread': 3.5,
                'max_spread': 7.0,
                'volume_requirement': 'medium',
                'news_avoidance': 3
            },
            EntryStrategy.NEWS_REACTION: {
                'optimal_spread': 5.0,
                'max_spread': 10.0,
                'volume_requirement': 'very_high',
                'news_avoidance': 0         # ไม่หลีกเลี่ยงข่าว
            }
        }
    
    def analyze_entry_timing(self, signal_context: SignalContext) -> Tuple[float, List[str]]:
        """วิเคราะห์จังหวะเวลาในการเข้าเทรด"""
        try:
            reasons = []
            timing_score = 0.0
            
            strategy = signal_context.entry_strategy
            timing_prefs = self.strategy_timing_preferences.get(strategy, {})
            
            # 1. วิเคราะห์ Spread (31.25% แทน 25%)
            spread_score, spread_reasons = self._analyze_spread_conditions(signal_context, timing_prefs)
            timing_score += spread_score * 0.3125  # เพิ่มน้ำหนัก
            reasons.extend(spread_reasons)
            
            # 2. วิเคราะห์ Volume (31.25% แทน 25%)
            volume_score, volume_reasons = self._analyze_volume_conditions(signal_context, timing_prefs)
            timing_score += volume_score * 0.3125  # เพิ่มน้ำหนัก
            reasons.extend(volume_reasons)
            
            # 3. ลบ News Analysis ออก
            # news_score, news_reasons = self._analyze_news_timing(signal_context, timing_prefs)
            # timing_score += news_score * 0.20
            # reasons.extend(news_reasons)
            
            # 4. วิเคราะห์ Session (25% แทน 20%)
            session_score, session_reasons = self._analyze_session_timing(signal_context)
            timing_score += session_score * 0.25  # เพิ่มน้ำหนัก
            reasons.extend(session_reasons)
            
            # 5. วิเคราะห์ Technical (12.5% แทน 10%)
            tech_score, tech_reasons = self._analyze_technical_timing(signal_context)
            timing_score += tech_score * 0.125  # เพิ่มน้ำหนัก
            reasons.extend(tech_reasons)
            
            return min(100.0, timing_score), reasons
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์จังหวะเวลา: {e}")
            return 0.0, ["ข้อผิดพลาดในการวิเคราะห์"]
        
    def _analyze_spread_conditions(self, signal_context: SignalContext, 
                                    timing_prefs: Dict[str, Any]) -> Tuple[float, List[str]]:
        """วิเคราะห์สภาพ Spread"""
        reasons = []
        score = 0.0
        
        current_spread = signal_context.market_conditions.get('current_spread', 0.0)
        optimal_spread = timing_prefs.get('optimal_spread', 3.0)
        max_spread = timing_prefs.get('max_spread', 6.0)
        
        if current_spread <= optimal_spread:
            score = 100.0
            reasons.append(f"✅ Spread ดีเยี่ยม ({current_spread:.1f} pips)")
        elif current_spread <= max_spread:
            score = 70.0 - ((current_spread - optimal_spread) / (max_spread - optimal_spread)) * 40.0
            reasons.append(f"✅ Spread ยอมรับได้ ({current_spread:.1f} pips)")
        else:
            score = 20.0
            reasons.append(f"❌ Spread สูงเกินไป ({current_spread:.1f} pips)")
        
        return score, reasons
    
    def _analyze_volume_conditions(self, signal_context: SignalContext,
                                    timing_prefs: Dict[str, Any]) -> Tuple[float, List[str]]:
        """วิเคราะห์สภาพ Volume"""
        reasons = []
        score = 0.0
        
        current_volume = signal_context.market_conditions.get('current_volume', 0.0)
        avg_volume = signal_context.market_conditions.get('average_volume', 1.0)
        required_volume = timing_prefs.get('volume_requirement', 'medium')
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        volume_thresholds = {
            'very_high': 2.0,
            'high': 1.5,
            'medium': 1.0,
            'low': 0.7
        }
        
        required_threshold = volume_thresholds.get(required_volume, 1.0)
        
        if volume_ratio >= required_threshold:
            score = min(100.0, 60.0 + (volume_ratio - required_threshold) * 20.0)
            reasons.append(f"✅ Volume เพียงพอ ({volume_ratio:.2f}x)")
        else:
            score = (volume_ratio / required_threshold) * 60.0
            reasons.append(f"⚠️ Volume ต่ำกว่าที่ต้องการ ({volume_ratio:.2f}x)")
        
        return score, reasons
    
    
    def _analyze_session_timing(self, signal_context: SignalContext) -> Tuple[float, List[str]]:
        """วิเคราะห์จังหวะเวลาตาม Session"""
        reasons = []
        score = 0.0
        
        current_session = signal_context.market_session
        current_time = datetime.now()
        
        # ความเข้มข้นของการเทรดในแต่ละ Session
        session_intensity = {
            MarketSession.ASIAN: 60.0,     # Low-Medium intensity
            MarketSession.LONDON: 90.0,    # High intensity
            MarketSession.NEW_YORK: 95.0,  # Very high intensity
            MarketSession.OVERLAP: 100.0   # Maximum intensity
        }
        
        base_score = session_intensity.get(current_session, 50.0)
        
        # ปรับคะแนนตามเวลาภายใน Session
        hour = current_time.hour
        
        # Asian Session peak hours
        if current_session == MarketSession.ASIAN and hour in [23, 0, 1, 2]:
            score = base_score + 10.0
            reasons.append("✅ ช่วงเวลาที่ดีที่สุดใน Asian Session")
        
        # London Session peak hours
        elif current_session == MarketSession.LONDON and hour in [15, 16, 17, 18]:
            score = base_score + 10.0
            reasons.append("✅ ช่วงเวลาที่ดีที่สุดใน London Session")
        
        # New York Session peak hours
        elif current_session == MarketSession.NEW_YORK and hour in [21, 22, 23, 0]:
            score = base_score + 10.0
            reasons.append("✅ ช่วงเวลาที่ดีที่สุดใน New York Session")
        
        # Overlap period
        elif current_session == MarketSession.OVERLAP:
            score = base_score
            reasons.append("✅ ช่วงเวลา Overlap - โอกาสสูงสุด")
        
        else:
            score = base_score
            reasons.append(f"✅ เวลาปกติของ {current_session.value} Session")
        
        return min(100.0, score), reasons
    
    def _analyze_technical_timing(self, signal_context: SignalContext) -> Tuple[float, List[str]]:
        """วิเคราะห์จังหวะเวลาทางเทคนิค"""
        reasons = []
        score = 0.0
        
        indicators = signal_context.indicators_data
        
        # ตรวจสอบ Momentum Alignment
        momentum_indicators = ['rsi', 'macd', 'stochastic']
        aligned_indicators = 0
        
        for indicator in momentum_indicators:
            if indicator in indicators:
                value = indicators[indicator]
                
                # Bullish alignment check
                if signal_context.direction == 'BUY':
                    if (indicator == 'rsi' and 30 <= value <= 70) or \
                        (indicator == 'macd' and value > 0) or \
                        (indicator == 'stochastic' and value < 80):
                        aligned_indicators += 1
                
                # Bearish alignment check
                elif signal_context.direction == 'SELL':
                    if (indicator == 'rsi' and 30 <= value <= 70) or \
                        (indicator == 'macd' and value < 0) or \
                        (indicator == 'stochastic' and value > 20):
                        aligned_indicators += 1
        
        if aligned_indicators >= 2:
            score = 100.0
            reasons.append("✅ Indicators สนับสนุนทิศทางสัญญาณ")
        elif aligned_indicators >= 1:
            score = 70.0
            reasons.append("✅ Indicators บางตัวสนับสนุนสัญญาณ")
        else:
            score = 40.0
            reasons.append("⚠️ Indicators ไม่สนับสนุนสัญญาณอย่างชัดเจน")
        
        return score, reasons

class RecoveryPotentialAnalyzer:
    """
    วิเคราะห์ศักยภาพในการ Recovery ของสัญญาณ
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Recovery Method Rankings ตาม Market Condition
        self.recovery_rankings = {
            'TRENDING': [
                RecoveryMethod.GRID_INTELLIGENT,
                RecoveryMethod.AVERAGING_INTELLIGENT,
                RecoveryMethod.MARTINGALE_SMART
            ],
            'RANGING': [
                RecoveryMethod.MARTINGALE_SMART,
                RecoveryMethod.AVERAGING_INTELLIGENT,
                RecoveryMethod.GRID_INTELLIGENT
            ],
            'VOLATILE': [
                RecoveryMethod.HEDGING_ADVANCED,
                RecoveryMethod.CORRELATION_RECOVERY,
                RecoveryMethod.AVERAGING_INTELLIGENT
            ]
        }
    
    def analyze_recovery_potential(self, signal_context: SignalContext) -> Tuple[float, RecoveryMethod, List[str]]:
        """
        วิเคราะห์ศักยภาพในการ Recovery
        
        Returns:
            Tuple[float, RecoveryMethod, List[str]]: (คะแนนศักยภาพ, วิธี Recovery ที่แนะนำ, เหตุผล)
        """
        try:
            reasons = []
            
            market_state = signal_context.market_conditions.get('market_state', 'RANGING')
            
            # เลือก Recovery Methods ที่เหมาะสม
            suitable_methods = self.recovery_rankings.get(market_state, self.recovery_rankings['RANGING'])
            recommended_method = suitable_methods[0]
            
            # คำนวณศักยภาพ Recovery
            recovery_score = 0.0
            
            # 1. Market State Compatibility (40%)
            state_score = self._analyze_market_state_compatibility(signal_context, recommended_method)
            recovery_score += state_score * 0.4
            
            # 2. Position Correlation (30%)
            correlation_score = self._analyze_position_correlation(signal_context)
            recovery_score += correlation_score * 0.3
            
            # 3. Account Health (20%)
            account_score = self._analyze_account_health(signal_context)
            recovery_score += account_score * 0.2
            
            # 4. Recovery History (10%)
            history_score = self._analyze_recovery_history(signal_context)
            recovery_score += history_score * 0.1
            
            # สร้าง Reasons
            reasons.append(f"🔧 วิธี Recovery ที่แนะนำ: {recommended_method.value}")
            reasons.append(f"📊 Market State: {market_state}")
            reasons.append(f"⭐ คะแนนศักยภาพ Recovery: {recovery_score:.1f}/100")
            
            if recovery_score >= 80:
                reasons.append("✅ ศักยภาพ Recovery สูงมาก")
            elif recovery_score >= 60:
                reasons.append("✅ ศักยภาพ Recovery ดี")
            elif recovery_score >= 40:
                reasons.append("⚠️ ศักยภาพ Recovery ปานกลาง")
            else:
                reasons.append("❌ ศักยภาพ Recovery ต่ำ")
            
            return recovery_score, recommended_method, reasons
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์ศักยภาพ Recovery: {e}")
            return 0.0, RecoveryMethod.MARTINGALE_SMART, ["ข้อผิดพลาดในการวิเคราะห์"]
    
    def _analyze_market_state_compatibility(self, signal_context: SignalContext, 
                                            recovery_method: RecoveryMethod) -> float:
        """วิเคราะห์ความเข้ากันได้ของ Market State กับ Recovery Method"""
        market_state = signal_context.market_conditions.get('market_state', 'RANGING')
        
        # Compatibility Matrix
        compatibility_scores = {
            ('TRENDING', RecoveryMethod.GRID_INTELLIGENT): 90.0,
            ('TRENDING', RecoveryMethod.AVERAGING_INTELLIGENT): 85.0,
            ('TRENDING', RecoveryMethod.MARTINGALE_SMART): 70.0,
            ('TRENDING', RecoveryMethod.HEDGING_ADVANCED): 60.0,
            ('TRENDING', RecoveryMethod.CORRELATION_RECOVERY): 50.0,
            
            ('RANGING', RecoveryMethod.MARTINGALE_SMART): 95.0,
            ('RANGING', RecoveryMethod.AVERAGING_INTELLIGENT): 90.0,
            ('RANGING', RecoveryMethod.GRID_INTELLIGENT): 80.0,
            ('RANGING', RecoveryMethod.HEDGING_ADVANCED): 65.0,
            ('RANGING', RecoveryMethod.CORRELATION_RECOVERY): 55.0,
            
            ('VOLATILE', RecoveryMethod.HEDGING_ADVANCED): 95.0,
            ('VOLATILE', RecoveryMethod.CORRELATION_RECOVERY): 90.0,
            ('VOLATILE', RecoveryMethod.AVERAGING_INTELLIGENT): 75.0,
            ('VOLATILE', RecoveryMethod.GRID_INTELLIGENT): 60.0,
            ('VOLATILE', RecoveryMethod.MARTINGALE_SMART): 50.0,
        }
        
        return compatibility_scores.get((market_state, recovery_method), 60.0)
    
    def _analyze_position_correlation(self, signal_context: SignalContext) -> float:
        """วิเคราะห์ความสัมพันธ์กับ Positions ปัจจุบัน"""
        current_positions = signal_context.current_positions
        
        if not current_positions:
            return 100.0  # ไม่มี position อื่น = Recovery ง่าย
        
        # ตรวจสอบทิศทางของ positions ปัจจุบัน
        same_direction_count = sum(1 for pos in current_positions 
                                    if pos.get('direction') == signal_context.direction)
        opposite_direction_count = len(current_positions) - same_direction_count
        
        # คำนวณ Correlation Score
        if opposite_direction_count > same_direction_count:
            return 85.0  # มี position ตรงข้าม = Recovery ง่าย (Natural Hedge)
        elif same_direction_count <= 2:
            return 70.0  # position ทิศทางเดียวกันน้อย = Recovery ปานกลาง
        else:
            return 40.0  # position ทิศทางเดียวกันเยอะ = Recovery ยาก
    
    def _analyze_account_health(self, signal_context: SignalContext) -> float:
        """วิเคราะห์สุขภาพของบัญชี"""
        account_equity = signal_context.account_equity
        
        # คำนวณ Equity สำหรับ Recovery
        if account_equity >= 10000:
            return 100.0  # Equity สูง = Recovery ง่าย
        elif account_equity >= 5000:
            return 80.0
        elif account_equity >= 2000:
            return 60.0
        elif account_equity >= 1000:
            return 40.0
        else:
            return 20.0   # Equity ต่ำ = Recovery ยาก
    
    def _analyze_recovery_history(self, signal_context: SignalContext) -> float:
        """วิเคราะห์ประวัติการ Recovery"""
        try:
            # เชื่อมต่อกับ Recovery Engine เพื่อดู Recovery History
            from intelligent_recovery.recovery_engine import get_recovery_engine
            recovery_engine = get_recovery_engine()
            
            recent_recovery_rate = recovery_engine.get_recent_recovery_rate(days=7)
            
            if recent_recovery_rate >= 95:
                return 100.0
            elif recent_recovery_rate >= 90:
                return 85.0
            elif recent_recovery_rate >= 80:
                return 70.0
            else:
                return 50.0
                
        except ImportError:
            return 75.0  # Default score เมื่อไม่สามารถเชื่อมต่อได้

class EntryValidator:
    """
    🎯 Main Entry Validator Class
    
    ระบบตรวจสอบและกรองสัญญาณการเข้าเทรดแบบครอบคลุม
    รวบรวมการวิเคราะห์จากทุก Analyzer เข้าด้วยกัน
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Initialize Analyzers
        self.market_suitability_analyzer = MarketSuitabilityAnalyzer()
        self.risk_reward_analyzer = RiskRewardAnalyzer()
        self.historical_performance_analyzer = HistoricalPerformanceAnalyzer()
        self.entry_timing_analyzer = EntryTimingAnalyzer()
        self.recovery_potential_analyzer = RecoveryPotentialAnalyzer()
        
        # Validation Thresholds
        self.min_overall_score = 60.0        # คะแนนขั้นต่ำสำหรับการผ่าน
        self.excellent_threshold = 90.0      # คะแนนสำหรับ Excellent
        self.good_threshold = 75.0           # คะแนนสำหรับ Good
        self.fair_threshold = 60.0           # คะแนนสำหรับ Fair
        
        # Weights for Different Criteria
        self.criteria_weights = {
            ValidationCriteria.SIGNAL_STRENGTH: 0.15,
            ValidationCriteria.MARKET_SUITABILITY: 0.25,
            ValidationCriteria.RISK_REWARD_RATIO: 0.20,
            ValidationCriteria.HISTORICAL_PERFORMANCE: 0.15,
            ValidationCriteria.ENTRY_TIMING: 0.15,
            ValidationCriteria.RECOVERY_POTENTIAL: 0.10
        }
        
        # Validation Statistics
        self.total_signals_processed = 0
        self.signals_accepted = 0
        self.signals_rejected = 0
        
        # Signal Queue for High-Frequency Processing
        self.signal_queue = deque(maxlen=1000)
        self.processing_active = False
        
        self.logger.info("🎯 เริ่มต้น Entry Validator System")
    
    @handle_trading_errors(ErrorCategory.SIGNAL_PROCESSING, ErrorSeverity.HIGH)
    async def validate_signal(self, signal_context: SignalContext) -> ValidationResult:
        """
        ตรวจสอบสัญญาณการเข้าเทรดแบบครอบคลุม
        
        Args:
            signal_context: บริบทของสัญญาณที่ต้องการตรวจสอบ
            
        Returns:
            ValidationResult: ผลการตรวจสอบพร้อมคะแนนและคำแนะนำ
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"🔍 เริ่มตรวจสอบสัญญาณ: {signal_context.signal_id}")
            
            # Initialize result
            result = ValidationResult(
                signal_id=signal_context.signal_id,
                is_valid=False,
                overall_score=0.0,
                quality_level=SignalQuality.REJECTED
            )
            
            # 1. Market Suitability Analysis
            suitability_score, suitability_reasons = await self._run_async_analysis(
                self.market_suitability_analyzer.analyze_suitability, signal_context
            )
            result.criteria_scores[ValidationCriteria.MARKET_SUITABILITY] = suitability_score
            result.validation_reasons.extend(suitability_reasons)
            
            # 2. Risk-Reward Analysis
            rr_ratio, rr_score, rr_reasons = await self._run_async_analysis(
                self.risk_reward_analyzer.calculate_risk_reward, signal_context
            )
            result.criteria_scores[ValidationCriteria.RISK_REWARD_RATIO] = rr_score
            result.validation_reasons.extend(rr_reasons)
            
            # 3. Historical Performance Analysis
            performance_score, performance_reasons = await self._run_async_analysis(
                self.historical_performance_analyzer.analyze_historical_performance, signal_context
            )
            result.criteria_scores[ValidationCriteria.HISTORICAL_PERFORMANCE] = performance_score
            result.validation_reasons.extend(performance_reasons)
            
            # 4. Entry Timing Analysis
            timing_score, timing_reasons = await self._run_async_analysis(
                self.entry_timing_analyzer.analyze_entry_timing, signal_context
            )
            result.criteria_scores[ValidationCriteria.ENTRY_TIMING] = timing_score
            result.validation_reasons.extend(timing_reasons)
            
            # 5. Recovery Potential Analysis
            recovery_score, recommended_recovery, recovery_reasons = await self._run_async_analysis(
                self.recovery_potential_analyzer.analyze_recovery_potential, signal_context
            )
            result.criteria_scores[ValidationCriteria.RECOVERY_POTENTIAL] = recovery_score
            result.recommended_recovery_method = recommended_recovery
            result.validation_reasons.extend(recovery_reasons)
            
            # 6. Signal Strength (from original signal)
            signal_strength = signal_context.confidence_level * 100
            result.criteria_scores[ValidationCriteria.SIGNAL_STRENGTH] = signal_strength
            
            # Calculate Overall Score
            result.overall_score = self._calculate_overall_score(result.criteria_scores)
            
            # Determine Quality Level and Validity
            result.quality_level = self._determine_quality_level(result.overall_score)
            result.is_valid = result.overall_score >= self.min_overall_score
            
            # Generate Recommendations
            result.recommended_volume = self._calculate_recommended_volume(signal_context, result)
            result.priority_level = self._calculate_priority_level(result)
            result.improvement_suggestions = self._generate_improvement_suggestions(result)
            
            # Set Expiry Time
            result.expiry_time = datetime.now() + timedelta(minutes=15)  # สัญญาณหมดอายุใน 15 นาทีี
            
            # Update Statistics
            self.total_signals_processed += 1
            if result.is_valid:
                self.signals_accepted += 1
            else:
                self.signals_rejected += 1
            
            # Log Result
            processing_time = (time.time() - start_time) * 1000
            self.logger.info(
                f"✅ ตรวจสอบสัญญาณเสร็จสิ้น: {signal_context.signal_id} | "
                f"คะแนน: {result.overall_score:.1f} | "
                f"คุณภาพ: {result.quality_level.value} | "
                f"ผ่าน: {result.is_valid} | "
                f"เวลา: {processing_time:.1f}ms"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจสอบสัญญาณ {signal_context.signal_id}: {e}")
            
            # Return failed result
            return ValidationResult(
                signal_id=signal_context.signal_id,
                is_valid=False,
                overall_score=0.0,
                quality_level=SignalQuality.REJECTED,
                validation_reasons=[f"ข้อผิดพลาดในการตรวจสอบ: {e}"]
            )
    
    async def _run_async_analysis(self, analysis_func: Callable, *args) -> Any:
        """รันการวิเคราะห์แบบ Async"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, analysis_func, *args)
    
    def _calculate_overall_score(self, criteria_scores: Dict[ValidationCriteria, float]) -> float:
        """
        คำนวณคะแนนรวมจากเกณฑ์ต่างๆ
        """
        total_score = 0.0
        total_weight = 0.0
        
        for criteria, score in criteria_scores.items():
            weight = self.criteria_weights.get(criteria, 0.1)
            total_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            return total_score / total_weight
        else:
            return 0.0
    
    def _determine_quality_level(self, overall_score: float) -> SignalQuality:
        """กำหนดระดับคุณภาพของสัญญาณ"""
        if overall_score >= self.excellent_threshold:
            return SignalQuality.EXCELLENT
        elif overall_score >= self.good_threshold:
            return SignalQuality.GOOD
        elif overall_score >= self.fair_threshold:
            return SignalQuality.FAIR
        elif overall_score >= 40.0:
            return SignalQuality.POOR
        else:
            return SignalQuality.REJECTED
    
    def _calculate_recommended_volume(self, signal_context: SignalContext, 
                                    result: ValidationResult) -> float:
        """คำนวณ Volume ที่แนะนำสำหรับสัญญาณ"""
        base_volume = 0.01  # Base volume
        
        # ปรับตามคุณภาพสัญญาณ
        quality_multipliers = {
            SignalQuality.EXCELLENT: 2.0,
            SignalQuality.GOOD: 1.5,
            SignalQuality.FAIR: 1.0,
            SignalQuality.POOR: 0.5,
            SignalQuality.REJECTED: 0.0
        }
        
        volume_multiplier = quality_multipliers.get(result.quality_level, 1.0)
        
        # ปรับตาม Account Equity
        account_equity = signal_context.account_equity
        equity_factor = min(2.0, account_equity / 1000.0)  # Max 2x สำหรับ account > $1000
        
        # ปรับตาม Market Session
        session_multipliers = {
            MarketSession.ASIAN: 0.8,
            MarketSession.LONDON: 1.2,
            MarketSession.NEW_YORK: 1.3,
            MarketSession.OVERLAP: 1.5
        }
        
        session_multiplier = session_multipliers.get(signal_context.market_session, 1.0)
        
        # คำนวณ Volume สุดท้าย
        recommended_volume = base_volume * volume_multiplier * equity_factor * session_multiplier
        
        # จำกัด Volume ตามการตั้งค่า
        max_volume = self.trading_params.max_position_size
        recommended_volume = min(recommended_volume, max_volume)
        
        return round(recommended_volume, 2)
    
    def _calculate_priority_level(self, result: ValidationResult) -> int:
        """คำนวณระดับความสำคัญของสัญญาณ (1-100)"""
        # Base priority จากคะแนนรวม
        base_priority = result.overall_score
        
        # ปรับตาม Recovery Potential
        recovery_score = result.criteria_scores.get(ValidationCriteria.RECOVERY_POTENTIAL, 50.0)
        if recovery_score >= 80:
            base_priority += 10
        elif recovery_score <= 40:
            base_priority -= 10
        
        # ปรับตาม Risk-Reward Ratio
        rr_score = result.criteria_scores.get(ValidationCriteria.RISK_REWARD_RATIO, 50.0)
        if rr_score >= 80:
            base_priority += 5
        elif rr_score <= 40:
            base_priority -= 5
        
        return max(1, min(100, int(base_priority)))
    
    def _generate_improvement_suggestions(self, result: ValidationResult) -> List[str]:
        """สร้างคำแนะนำในการปรับปรุงสัญญาณ"""
        suggestions = []
        
        # ตรวจสอบคะแนนแต่ละเกณฑ์
        for criteria, score in result.criteria_scores.items():
            if score < 50.0:
                if criteria == ValidationCriteria.MARKET_SUITABILITY:
                    suggestions.append("💡 ปรับ Strategy ให้เหมาะสมกับสภาพตลาดปัจจุบัน")
                elif criteria == ValidationCriteria.RISK_REWARD_RATIO:
                    suggestions.append("💡 ปรับ Target หรือ Entry Point เพื่อเพิ่ม Risk-Reward Ratio")
                elif criteria == ValidationCriteria.HISTORICAL_PERFORMANCE:
                    suggestions.append("💡 ปรับพารามิเตอร์ Strategy ตามประสิทธิภาพในอดีต")
                elif criteria == ValidationCriteria.ENTRY_TIMING:
                    suggestions.append("💡 รอจังหวะเวลาที่เหมาะสมกว่าในการเข้าเทรด")
                elif criteria == ValidationCriteria.RECOVERY_POTENTIAL:
                    suggestions.append("💡 พิจารณา Recovery Method ที่เหมาะสมกับสภาพตลาด")
                elif criteria == ValidationCriteria.SIGNAL_STRENGTH:
                    suggestions.append("💡 เพิ่มความแรงของสัญญาณด้วย Indicator เพิ่มเติม")
        
        # คำแนะนำทั่วไป
        if result.overall_score < 60:
            suggestions.append("💡 พิจารณารอสัญญาณที่มีคุณภาพดีกว่า")
        elif result.overall_score < 75:
            suggestions.append("💡 ลดขนาด Position หรือใช้ Recovery Method ที่ปลอดภัยกว่า")
        
        return suggestions[:3]  # จำกัดไม่เกิน 3 คำแนะนำ
    
    def validate_multiple_signals(self, signal_contexts: List[SignalContext]) -> List[ValidationResult]:
        """
        ตรวจสอบสัญญาณหลายๆ อันพร้อมกัน
        """
        self.logger.info(f"🔍 เริ่มตรวจสอบสัญญาณ {len(signal_contexts)} อัน")
        
        async def validate_all():
            tasks = [self.validate_signal(context) for context in signal_contexts]
            return await asyncio.gather(*tasks)
        
        # รัน Async validation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(validate_all())
            return results
        finally:
            loop.close()
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """
        ดึงสถิติการตรวจสอบสัญญาณ
        """
        if self.total_signals_processed == 0:
            acceptance_rate = 0.0
        else:
            acceptance_rate = (self.signals_accepted / self.total_signals_processed) * 100
        
        return {
            'total_processed': self.total_signals_processed,
            'accepted': self.signals_accepted,
            'rejected': self.signals_rejected,
            'acceptance_rate': acceptance_rate,
            'criteria_weights': self.criteria_weights,
            'validation_thresholds': {
                'min_overall_score': self.min_overall_score,
                'excellent_threshold': self.excellent_threshold,
                'good_threshold': self.good_threshold,
                'fair_threshold': self.fair_threshold
            }
        }
    
    def update_validation_parameters(self, new_params: Dict[str, Any]) -> None:
        """
        อัพเดทพารามิเตอร์การตรวจสอบ
        """
        try:
            if 'min_overall_score' in new_params:
                self.min_overall_score = new_params['min_overall_score']
            
            if 'criteria_weights' in new_params:
                self.criteria_weights.update(new_params['criteria_weights'])
            
            if 'quality_thresholds' in new_params:
                thresholds = new_params['quality_thresholds']
                self.excellent_threshold = thresholds.get('excellent', self.excellent_threshold)
                self.good_threshold = thresholds.get('good', self.good_threshold)
                self.fair_threshold = thresholds.get('fair', self.fair_threshold)
            
            self.logger.info("✅ อัพเดทพารามิเตอร์การตรวจสอบสำเร็จ")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดทพารามิเตอร์: {e}")
    
    async def start_continuous_validation(self) -> None:
        """
        เริ่มการตรวจสอบสัญญาณแบบต่อเนื่อง (สำหรับ High-Frequency)
        """
        if self.processing_active:
            self.logger.warning("⚠️ การตรวจสอบต่อเนื่องกำลังทำงานอยู่แล้ว")
            return
        
        self.processing_active = True
        self.logger.info("🚀 เริ่มการตรวจสอบสัญญาณแบบต่อเนื่อง")
        
        try:
            while self.processing_active:
                if self.signal_queue:
                    # ดึงสัญญาณจาก Queue
                    signal_context = self.signal_queue.popleft()
                    
                    # ตรวจสอบสัญญาณ
                    result = await self.validate_signal(signal_context)
                    
                    # ส่งผลไปยัง Signal Generator หรือ Entry System
                    await self._send_validation_result(result)
                
                # รอสักครู่ก่อนตรวจสอบ Queue อีกครั้ง
                await asyncio.sleep(0.1)  # 100ms
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจสอบต่อเนื่อง: {e}")
        finally:
            self.processing_active = False
            self.logger.info("🛑 หยุดการตรวจสอบสัญญาณแบบต่อเนื่อง")
    
    async def _send_validation_result(self, result: ValidationResult) -> None:
        """
        ส่งผลการตรวจสอบไปยังระบบอื่น
        """
        try:
            # เชื่อมต่อกับ Signal Generator
            from adaptive_entries.signal_generator import get_signal_generator
            signal_generator = get_signal_generator()
            
            # ส่งผลการตรวจสอบ
            await signal_generator.receive_validation_result(result)
            
        except ImportError:
            self.logger.warning("⚠️ ไม่สามารถเชื่อมต่อ Signal Generator")
    
    def add_signal_to_queue(self, signal_context: SignalContext) -> None:
        """
        เพิ่มสัญญาณเข้า Queue สำหรับการตรวจสอบ
        """
        self.signal_queue.append(signal_context)
        self.logger.debug(f"📥 เพิ่มสัญญาณเข้า Queue: {signal_context.signal_id}")
    
    def stop_continuous_validation(self) -> None:
        """
        หยุดการตรวจสอบสัญญาณแบบต่อเนื่อง
        """
        self.processing_active = False
        self.logger.info("🛑 สั่งหยุดการตรวจสอบสัญญาณแบบต่อเนื่อง")

# Global Entry Validator Instance
_entry_validator_instance: Optional[EntryValidator] = None

def get_entry_validator() -> EntryValidator:
    """
    ดึง Entry Validator Instance (Singleton Pattern)
    
    Returns:
        EntryValidator: Instance ของ Entry Validator
    """
    global _entry_validator_instance
    
    if _entry_validator_instance is None:
        _entry_validator_instance = EntryValidator()
    
    return _entry_validator_instance

# Utility Functions
def create_signal_context(signal_id: str, entry_strategy: EntryStrategy, direction: str,
                        entry_price: float, confidence_level: float, 
                        market_session: MarketSession = MarketSession.ASIAN,
                        market_conditions: Dict[str, Any] = None,
                        timeframe: str = "M5",
                        indicators_data: Dict[str, float] = None,
                        current_positions: List[Dict[str, Any]] = None,
                        account_equity: float = 1000.0,
                        daily_volume_progress: float = 0.0) -> SignalContext:
    """
    สร้าง SignalContext สำหรับการตรวจสอบ
    
    Utility function สำหรับสร้าง SignalContext ได้ง่ายๆ
    """
    return SignalContext(
        signal_id=signal_id,
        entry_strategy=entry_strategy,
        direction=direction,
        entry_price=entry_price,
        confidence_level=confidence_level,
        market_session=market_session,
        market_conditions=market_conditions or {},
        timeframe=timeframe,
        indicators_data=indicators_data or {},
        current_positions=current_positions or [],
        account_equity=account_equity,
        daily_volume_progress=daily_volume_progress
    )

async def quick_validate_signal(signal_id: str, entry_strategy: EntryStrategy, 
                              direction: str, entry_price: float, 
                              confidence_level: float) -> ValidationResult:
    """
    ตรวจสอบสัญญาณแบบเร็ว (ใช้พารามิเตอร์พื้นฐาน)
    
    Utility function สำหรับการตรวจสอบสัญญาณแบบง่ายๆ
    """
    validator = get_entry_validator()
    
    signal_context = create_signal_context(
        signal_id=signal_id,
        entry_strategy=entry_strategy,
        direction=direction,
        entry_price=entry_price,
        confidence_level=confidence_level
    )
    
    return await validator.validate_signal(signal_context)

if __name__ == "__main__":
    """
    ทดสอบ Entry Validator System
    """
    import asyncio
    
    async def test_entry_validator():
        """ทดสอบการทำงานของ Entry Validator"""
        
        print("🧪 เริ่มทดสอบ Entry Validator System")
        
        # สร้าง Test Signal Context
        test_signal = create_signal_context(
            signal_id="TEST_001",
            entry_strategy=EntryStrategy.TREND_FOLLOWING,
            direction="BUY",
            entry_price=1850.50,
            confidence_level=0.75,
            market_session=MarketSession.LONDON,
            market_conditions={
                'market_state': 'TRENDING',
                'adx_current': 28.5,
                'atr_current': 1.2,
                'current_spread': 2.5,
                'current_volume': 1.3,
                'average_volume': 1.0
            },
            indicators_data={
                'rsi': 55.0,
                'macd': 0.5,
                'stochastic': 45.0
            },
            account_equity=5000.0
        )
        
        # ทดสอบการตรวจสอบ
        validator = get_entry_validator()
        result = await validator.validate_signal(test_signal)
        
        # แสดงผล
        print(f"\n📊 ผลการตรวจสอบ:")
        print(f"   สัญญาณ: {result.signal_id}")
        print(f"   ผ่านการตรวจสอบ: {result.is_valid}")
        print(f"   คะแนนรวม: {result.overall_score:.1f}/100")
        print(f"   ระดับคุณภาพ: {result.quality_level.value}")
        print(f"   Volume แนะนำ: {result.recommended_volume}")
        print(f"   Recovery Method: {result.recommended_recovery_method}")
        print(f"   ระดับความสำคัญ: {result.priority_level}/100")
        
        print(f"\n📋 คะแนนแต่ละเกณฑ์:")
        for criteria, score in result.criteria_scores.items():
            print(f"   {criteria.value}: {score:.1f}/100")
        
        print(f"\n📝 เหตุผล:")
        for reason in result.validation_reasons:
            print(f"   {reason}")
        
        if result.improvement_suggestions:
            print(f"\n💡 คำแนะนำ:")
            for suggestion in result.improvement_suggestions:
                print(f"   {suggestion}")
        
        # ทดสอบสถิติ
        stats = validator.get_validation_statistics()
        print(f"\n📈 สถิติการตรวจสอบ:")
        print(f"   ประมวลผลทั้งหมด: {stats['total_processed']}")
        print(f"   ผ่านการตรวจสอบ: {stats['accepted']}")
        print(f"   ไม่ผ่านการตรวจสอบ: {stats['rejected']}")
        print(f"   อัตราการผ่าน: {stats['acceptance_rate']:.1f}%")
        
        print("\n✅ ทดสอบ Entry Validator เสร็จสิ้น")
    
    # รันการทดสอบ
    asyncio.run(test_entry_validator())