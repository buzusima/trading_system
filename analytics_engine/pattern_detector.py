#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PATTERN DETECTOR - Pattern Recognition Engine
============================================
ระบบจดจำและวิเคราะห์รูปแบบการเทรดแบบอัจฉริยะ
รองรับการจดจำ Pattern ทั้งทางเทคนิคและพฤติกรรมการเทรด

Key Features:
- Market pattern identification algorithms
- Profitable pattern detection and scoring
- Pattern-based entry signal generation
- Historical pattern performance analysis
- Real-time pattern matching system
- Machine learning ready pattern classification
- High-frequency pattern processing (50-100 lots/day)

เชื่อมต่อไปยัง:
- market_intelligence/market_analyzer.py (ข้อมูล market patterns)
- analytics_engine/trade_analyzer.py (ข้อมูล trade patterns)
- analytics_engine/performance_tracker.py (ข้อมูล performance)
- adaptive_entries/signal_generator.py (สร้าง signals จาก patterns)
- intelligent_recovery/recovery_engine.py (pattern-based recovery)
"""

import asyncio
import threading
import time
import math
import statistics
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from enum import Enum
import json
import sqlite3
from collections import defaultdict, deque, Counter
import random

# เชื่อมต่อ internal modules
from config.settings import get_system_settings, MarketSession
from config.trading_params import get_trading_parameters, EntryStrategy, RecoveryMethod
from utilities.professional_logger import setup_trading_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class PatternType(Enum):
    """ประเภทของ Pattern"""
    # Price Action Patterns
    BREAKOUT = "breakout"                    # การทะลุแนวต้าน/รับ
    FALSE_BREAKOUT = "false_breakout"        # การทะลุเทียม
    REVERSAL = "reversal"                    # การกลับตัว
    CONTINUATION = "continuation"            # การต่อเนื่อง
    CONSOLIDATION = "consolidation"          # การสะสม
    
    # Candlestick Patterns
    DOJI = "doji"                           # โดจิ
    HAMMER = "hammer"                       # ค้อน
    SHOOTING_STAR = "shooting_star"         # ดาวตก
    ENGULFING = "engulfing"                 # การกลืน
    HARAMI = "harami"                       # ฮารามิ
    
    # Trading Behavior Patterns
    SCALPING_BURST = "scalping_burst"       # การ Scalp อย่างรวดเร็ว
    TREND_RIDING = "trend_riding"           # การตาม Trend
    MEAN_REVERSION_CYCLE = "mean_reversion_cycle"  # วงจร Mean Reversion
    NEWS_REACTION_PATTERN = "news_reaction_pattern"  # Pattern หลังข่าว
    SESSION_TRANSITION = "session_transition"  # การเปลี่ยน Session
    
    # Recovery Patterns
    MARTINGALE_SEQUENCE = "martingale_sequence"     # ลำดับ Martingale
    GRID_FORMATION = "grid_formation"               # การจัด Grid
    HEDGE_CORRELATION = "hedge_correlation"         # การ Hedge แบบสัมพันธ์
    
    # System Patterns
    HIGH_FREQUENCY_CLUSTER = "high_frequency_cluster"  # กลุ่มการเทรดถี่
    VOLUME_SPIKE = "volume_spike"                     # การพุ่งของ Volume
    VOLATILITY_EXPANSION = "volatility_expansion"     # การขยายตัวของ Volatility

class PatternConfidence(Enum):
    """ระดับความมั่นใจใน Pattern"""
    VERY_HIGH = 5      # 90-100%
    HIGH = 4           # 80-89%
    MEDIUM = 3         # 60-79%
    LOW = 2            # 40-59%
    VERY_LOW = 1       # 0-39%

class PatternTimeframe(Enum):
    """กรอบเวลาของ Pattern"""
    M1 = "M1"          # 1 นาที
    M5 = "M5"          # 5 นาที
    M15 = "M15"        # 15 นาที
    H1 = "H1"          # 1 ชั่วโมง
    H4 = "H4"          # 4 ชั่วโมง
    D1 = "D1"          # 1 วัน

@dataclass
class PatternData:
    """ข้อมูลของ Pattern"""
    # Basic Information
    pattern_id: str
    pattern_type: PatternType
    timeframe: PatternTimeframe
    
    # Detection Information
    detected_at: datetime = field(default_factory=datetime.now)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Market Data
    price_data: List[Dict[str, Any]] = field(default_factory=list)
    volume_data: List[float] = field(default_factory=list)
    volatility_data: List[float] = field(default_factory=list)
    
    # Pattern Characteristics
    pattern_strength: float = 0.0          # ความแรงของ Pattern (0-100)
    confidence_level: PatternConfidence = PatternConfidence.MEDIUM
    reliability_score: float = 0.0         # คะแนนความน่าเชื่อถือ
    
    # Context Information
    market_session: MarketSession = MarketSession.ASIAN
    market_condition: str = "UNKNOWN"      # TRENDING, RANGING, VOLATILE
    news_context: List[str] = field(default_factory=list)
    
    # Pattern Metrics
    expected_move: float = 0.0             # การเคลื่อนไหวที่คาดหวัง (pips)
    success_probability: float = 0.0       # ความน่าจะเป็นของความสำเร็จ
    risk_level: str = "MEDIUM"             # LOW, MEDIUM, HIGH
    
    # Additional Data
    pattern_parameters: Dict[str, Any] = field(default_factory=dict)
    related_patterns: List[str] = field(default_factory=list)
    invalidation_conditions: List[str] = field(default_factory=list)

@dataclass
class PatternPerformance:
    """ประสิทธิภาพของ Pattern"""
    pattern_type: PatternType
    
    # Performance Metrics
    total_occurrences: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    success_rate: float = 0.0
    
    # Financial Metrics
    total_pips_gained: float = 0.0
    average_pips_per_trade: float = 0.0
    profit_factor: float = 1.0
    max_drawdown: float = 0.0
    
    # Timing Metrics
    average_duration: timedelta = field(default_factory=timedelta)
    fastest_completion: timedelta = field(default_factory=timedelta)
    slowest_completion: timedelta = field(default_factory=timedelta)
    
    # Context Performance
    session_performance: Dict[MarketSession, float] = field(default_factory=dict)
    condition_performance: Dict[str, float] = field(default_factory=dict)
    
    # Recent Performance
    recent_success_rate: float = 0.0       # Success rate ใน 30 วันล่าสุด
    performance_trend: str = "STABLE"      # IMPROVING, STABLE, DECLINING
    
    # Risk Metrics
    average_risk_reward: float = 0.0
    volatility_during_pattern: float = 0.0
    market_impact: float = 0.0

@dataclass
class PatternSignal:
    """สัญญาณจาก Pattern"""
    signal_id: str
    pattern_id: str
    pattern_type: PatternType
    
    # Signal Information
    signal_strength: float = 0.0           # ความแรงของสัญญาณ (0-100)
    direction: str = "NEUTRAL"             # BUY, SELL, NEUTRAL
    entry_price: float = 0.0
    target_prices: List[float] = field(default_factory=list)
    invalidation_price: float = 0.0
    
    # Timing Information
    generated_at: datetime = field(default_factory=datetime.now)
    valid_until: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=1))
    
    # Risk Information
    recommended_volume: float = 0.01
    risk_level: str = "MEDIUM"
    max_risk_pips: float = 20.0
    
    # Context
    market_context: Dict[str, Any] = field(default_factory=dict)
    supporting_patterns: List[str] = field(default_factory=list)
    
    # Confidence
    confidence_score: float = 0.0          # ความมั่นใจในสัญญาณ
    reliability_factors: List[str] = field(default_factory=list)

class PriceActionAnalyzer:
    """
    วิเคราะห์ Price Action Patterns
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Pattern Detection Parameters
        self.breakout_threshold = 0.3       # % สำหรับการทะลุ
        self.false_breakout_pullback = 0.6  # % สำหรับ False Breakout
        self.reversal_strength_min = 0.4    # ความแรงขั้นต่ำสำหรับ Reversal
        self.consolidation_range = 0.2      # % สำหรับ Consolidation
    
    def detect_price_patterns(self, price_data: List[Dict[str, Any]], 
                            timeframe: PatternTimeframe) -> List[PatternData]:
        """
        ตรวจจับ Price Action Patterns
        
        Args:
            price_data: ข้อมูลราคา (OHLCV)
            timeframe: กรอบเวลา
            
        Returns:
            List[PatternData]: รายการ Patterns ที่พบ
        """
        try:
            detected_patterns = []
            
            if len(price_data) < 10:
                return detected_patterns
            
            # ตรวจจับ Breakout Patterns
            breakout_patterns = self._detect_breakout_patterns(price_data, timeframe)
            detected_patterns.extend(breakout_patterns)
            
            # ตรวจจับ False Breakout Patterns
            false_breakout_patterns = self._detect_false_breakout_patterns(price_data, timeframe)
            detected_patterns.extend(false_breakout_patterns)
            
            # ตรวจจับ Reversal Patterns
            reversal_patterns = self._detect_reversal_patterns(price_data, timeframe)
            detected_patterns.extend(reversal_patterns)
            
            # ตรวจจับ Consolidation Patterns
            consolidation_patterns = self._detect_consolidation_patterns(price_data, timeframe)
            detected_patterns.extend(consolidation_patterns)
            
            # ตรวจจับ Continuation Patterns
            continuation_patterns = self._detect_continuation_patterns(price_data, timeframe)
            detected_patterns.extend(continuation_patterns)
            
            self.logger.debug(f"🔍 ตรวจพบ Price Patterns: {len(detected_patterns)} patterns")
            
            return detected_patterns
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ Price Patterns: {e}")
            return []
    
    def _detect_breakout_patterns(self, price_data: List[Dict[str, Any]], 
                                timeframe: PatternTimeframe) -> List[PatternData]:
        """ตรวจจับ Breakout Patterns"""
        patterns = []
        
        try:
            for i in range(10, len(price_data)):
                current_bar = price_data[i]
                previous_bars = price_data[i-10:i]
                
                # หา Support/Resistance Levels
                highs = [bar['high'] for bar in previous_bars]
                lows = [bar['low'] for bar in previous_bars]
                
                resistance_level = max(highs)
                support_level = min(lows)
                
                # ตรวจสอบ Breakout ขึ้น
                if (current_bar['high'] > resistance_level and 
                    current_bar['close'] > resistance_level * (1 + self.breakout_threshold / 100)):
                    
                    pattern = self._create_breakout_pattern(
                        price_data[i-5:i+1], timeframe, "BULLISH", resistance_level
                    )
                    if pattern:
                        patterns.append(pattern)
                
                # ตรวจสอบ Breakout ลง
                elif (current_bar['low'] < support_level and 
                      current_bar['close'] < support_level * (1 - self.breakout_threshold / 100)):
                    
                    pattern = self._create_breakout_pattern(
                        price_data[i-5:i+1], timeframe, "BEARISH", support_level
                    )
                    if pattern:
                        patterns.append(pattern)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ Breakout: {e}")
        
        return patterns
    
    def _detect_false_breakout_patterns(self, price_data: List[Dict[str, Any]], 
                                      timeframe: PatternTimeframe) -> List[PatternData]:
        """ตรวจจับ False Breakout Patterns"""
        patterns = []
        
        try:
            for i in range(15, len(price_data)):
                # หา Breakout ที่เกิดขึ้นก่อนหน้า
                breakout_bar = None
                resistance_level = 0.0
                support_level = 0.0
                
                # ค้นหา Breakout ใน 5 bars ที่ผ่านมา
                for j in range(i-5, i):
                    bar = price_data[j]
                    previous_bars = price_data[max(0, j-10):j]
                    
                    if len(previous_bars) >= 5:
                        highs = [b['high'] for b in previous_bars]
                        lows = [b['low'] for b in previous_bars]
                        resistance = max(highs)
                        support = min(lows)
                        
                        # ตรวจสอบ Breakout ขึ้นที่ล้มเหลว
                        if bar['high'] > resistance and bar['close'] > resistance:
                            # ตรวจสอบการ Pullback
                            current_price = price_data[i]['close']
                            if current_price < resistance * (1 - self.false_breakout_pullback / 100):
                                breakout_bar = j
                                resistance_level = resistance
                                break
                        
                        # ตรวจสอบ Breakout ลงที่ล้มเหลว
                        elif bar['low'] < support and bar['close'] < support:
                            # ตรวจสอบการ Pullback
                            current_price = price_data[i]['close']
                            if current_price > support * (1 + self.false_breakout_pullback / 100):
                                breakout_bar = j
                                support_level = support
                                break
                
                if breakout_bar is not None:
                    direction = "BEARISH" if resistance_level > 0 else "BULLISH"
                    key_level = resistance_level if resistance_level > 0 else support_level
                    
                    pattern = self._create_false_breakout_pattern(
                        price_data[breakout_bar:i+1], timeframe, direction, key_level
                    )
                    if pattern:
                        patterns.append(pattern)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ False Breakout: {e}")
        
        return patterns
    
    def _detect_reversal_patterns(self, price_data: List[Dict[str, Any]], 
                                timeframe: PatternTimeframe) -> List[PatternData]:
        """ตรวจจับ Reversal Patterns"""
        patterns = []
        
        try:
            for i in range(20, len(price_data)):
                current_bar = price_data[i]
                previous_bars = price_data[i-20:i]
                
                # คำนวณ Trend Direction
                trend_direction = self._calculate_trend_direction(previous_bars)
                
                # ตรวจสอบ Bullish Reversal
                if trend_direction == "BEARISH":
                    reversal_strength = self._calculate_bullish_reversal_strength(
                        previous_bars[-5:] + [current_bar]
                    )
                    
                    if reversal_strength >= self.reversal_strength_min:
                        pattern = self._create_reversal_pattern(
                            price_data[i-10:i+1], timeframe, "BULLISH", reversal_strength
                        )
                        if pattern:
                            patterns.append(pattern)
                
                # ตรวจสอบ Bearish Reversal
                elif trend_direction == "BULLISH":
                    reversal_strength = self._calculate_bearish_reversal_strength(
                        previous_bars[-5:] + [current_bar]
                    )
                    
                    if reversal_strength >= self.reversal_strength_min:
                        pattern = self._create_reversal_pattern(
                            price_data[i-10:i+1], timeframe, "BEARISH", reversal_strength
                        )
                        if pattern:
                            patterns.append(pattern)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ Reversal: {e}")
        
        return patterns
    
    def _detect_consolidation_patterns(self, price_data: List[Dict[str, Any]], 
                                     timeframe: PatternTimeframe) -> List[PatternData]:
        """ตรวจจับ Consolidation Patterns"""
        patterns = []
        
        try:
            for i in range(15, len(price_data)):
                consolidation_bars = price_data[i-15:i+1]
                
                # คำนวณ Range
                highs = [bar['high'] for bar in consolidation_bars]
                lows = [bar['low'] for bar in consolidation_bars]
                
                highest = max(highs)
                lowest = min(lows)
                range_size = highest - lowest
                avg_price = (highest + lowest) / 2
                
                # ตรวจสอบว่าเป็น Consolidation หรือไม่
                range_percentage = (range_size / avg_price) * 100
                
                if range_percentage <= self.consolidation_range:
                    # ตรวจสอบว่าราคาอยู่ในช่วง Range
                    prices_in_range = 0
                    for bar in consolidation_bars:
                        if lowest <= bar['close'] <= highest:
                            prices_in_range += 1
                    
                    consolidation_strength = prices_in_range / len(consolidation_bars)
                    
                    if consolidation_strength >= 0.8:  # 80% ของราคาอยู่ใน Range
                        pattern = self._create_consolidation_pattern(
                            consolidation_bars, timeframe, highest, lowest, consolidation_strength
                        )
                        if pattern:
                            patterns.append(pattern)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ Consolidation: {e}")
        
        return patterns
    
    def _detect_continuation_patterns(self, price_data: List[Dict[str, Any]], 
                                    timeframe: PatternTimeframe) -> List[PatternData]:
        """ตรวจจับ Continuation Patterns"""
        patterns = []
        
        try:
            for i in range(20, len(price_data)):
                # แบ่งข้อมูลเป็น 3 ส่วน
                before_bars = price_data[i-20:i-10]  # ก่อน Continuation
                during_bars = price_data[i-10:i]     # ระหว่าง Continuation
                current_bar = price_data[i]           # ปัจจุบัน
                
                # ตรวจสอบ Trend ก่อนหน้า
                before_trend = self._calculate_trend_direction(before_bars)
                
                if before_trend != "NEUTRAL":
                    # ตรวจสอบการ Consolidation ระหว่าง
                    during_volatility = self._calculate_volatility(during_bars)
                    
                    # ตรวจสอบการ Continue Trend
                    if before_trend == "BULLISH":
                        if current_bar['close'] > during_bars[-1]['high']:
                            pattern = self._create_continuation_pattern(
                                price_data[i-15:i+1], timeframe, "BULLISH", during_volatility
                            )
                            if pattern:
                                patterns.append(pattern)
                    
                    elif before_trend == "BEARISH":
                        if current_bar['close'] < during_bars[-1]['low']:
                            pattern = self._create_continuation_pattern(
                                price_data[i-15:i+1], timeframe, "BEARISH", during_volatility
                            )
                            if pattern:
                                patterns.append(pattern)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ Continuation: {e}")
        
        return patterns
    
    def _create_breakout_pattern(self, pattern_data: List[Dict[str, Any]], 
                               timeframe: PatternTimeframe, direction: str, 
                               key_level: float) -> Optional[PatternData]:
        """สร้าง Breakout Pattern"""
        try:
            pattern_id = f"BREAKOUT_{int(time.time())}_{direction}"
            
            # คำนวณ Pattern Strength
            breakout_bar = pattern_data[-1]
            strength = abs(breakout_bar['close'] - key_level) / key_level * 1000  # ในหน่วย pips
            
            # คำนวณ Expected Move
            volatility = self._calculate_volatility(pattern_data)
            expected_move = volatility * 1.5  # คาดหวังการเคลื่อนไหว 1.5 เท่าของ volatility
            
            pattern = PatternData(
                pattern_id=pattern_id,
                pattern_type=PatternType.BREAKOUT,
                timeframe=timeframe,
                start_time=pattern_data[0].get('timestamp'),
                end_time=pattern_data[-1].get('timestamp'),
                price_data=pattern_data,
                pattern_strength=min(100.0, strength * 5),  # Scale to 0-100
                confidence_level=self._determine_confidence_level(strength * 5),
                expected_move=expected_move,
                success_probability=self._calculate_breakout_success_probability(pattern_data, direction),
                pattern_parameters={
                    'direction': direction,
                    'key_level': key_level,
                    'breakout_strength': strength
                }
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Breakout Pattern: {e}")
            return None
    
    def _create_false_breakout_pattern(self, pattern_data: List[Dict[str, Any]], 
                                     timeframe: PatternTimeframe, direction: str, 
                                     key_level: float) -> Optional[PatternData]:
        """สร้าง False Breakout Pattern"""
        try:
            pattern_id = f"FALSE_BREAKOUT_{int(time.time())}_{direction}"
            
            # คำนวณ Pattern Strength จากการ Pullback
            current_price = pattern_data[-1]['close']
            pullback_distance = abs(current_price - key_level) / key_level * 1000
            
            pattern = PatternData(
                pattern_id=pattern_id,
                pattern_type=PatternType.FALSE_BREAKOUT,
                timeframe=timeframe,
                start_time=pattern_data[0].get('timestamp'),
                end_time=pattern_data[-1].get('timestamp'),
                price_data=pattern_data,
                pattern_strength=min(100.0, pullback_distance * 3),
                confidence_level=self._determine_confidence_level(pullback_distance * 3),
                expected_move=self._calculate_volatility(pattern_data) * 2,
                success_probability=self._calculate_false_breakout_success_probability(pattern_data, direction),
                pattern_parameters={
                    'direction': direction,
                    'key_level': key_level,
                    'pullback_distance': pullback_distance
                }
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง False Breakout Pattern: {e}")
            return None
    
    def _create_reversal_pattern(self, pattern_data: List[Dict[str, Any]], 
                               timeframe: PatternTimeframe, direction: str, 
                               strength: float) -> Optional[PatternData]:
        """สร้าง Reversal Pattern"""
        try:
            pattern_id = f"REVERSAL_{int(time.time())}_{direction}"
            
            pattern = PatternData(
                pattern_id=pattern_id,
                pattern_type=PatternType.REVERSAL,
                timeframe=timeframe,
                start_time=pattern_data[0].get('timestamp'),
                end_time=pattern_data[-1].get('timestamp'),
                price_data=pattern_data,
                pattern_strength=strength * 100,
                confidence_level=self._determine_confidence_level(strength * 100),
                expected_move=self._calculate_volatility(pattern_data) * 1.8,
                success_probability=self._calculate_reversal_success_probability(pattern_data, direction),
                pattern_parameters={
                    'direction': direction,
                    'reversal_strength': strength
                }
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Reversal Pattern: {e}")
            return None
    
    def _create_consolidation_pattern(self, pattern_data: List[Dict[str, Any]], 
                                    timeframe: PatternTimeframe, highest: float, 
                                    lowest: float, strength: float) -> Optional[PatternData]:
        """สร้าง Consolidation Pattern"""
        try:
            pattern_id = f"CONSOLIDATION_{int(time.time())}"
            
            range_size = highest - lowest
            avg_price = (highest + lowest) / 2
            
            pattern = PatternData(
                pattern_id=pattern_id,
                pattern_type=PatternType.CONSOLIDATION,
                timeframe=timeframe,
                start_time=pattern_data[0].get('timestamp'),
                end_time=pattern_data[-1].get('timestamp'),
                price_data=pattern_data,
                pattern_strength=strength * 100,
                confidence_level=self._determine_confidence_level(strength * 100),
                expected_move=range_size * 1.2,  # คาดหวังการทะลุออกจาก Range
                success_probability=0.6,  # Consolidation มักจะทะลุในที่สุด
                pattern_parameters={
                    'highest': highest,
                    'lowest': lowest,
                    'range_size': range_size,
                    'avg_price': avg_price
                }
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Consolidation Pattern: {e}")
            return None
    
    def _create_continuation_pattern(self, pattern_data: List[Dict[str, Any]], 
                                   timeframe: PatternTimeframe, direction: str, 
                                   consolidation_volatility: float) -> Optional[PatternData]:
        """สร้าง Continuation Pattern"""
        try:
            pattern_id = f"CONTINUATION_{int(time.time())}_{direction}"
            
            # ความแรงของ Pattern ขึ้นกับการลดลงของ Volatility ระหว่าง Consolidation
            strength = max(0.0, 1.0 - consolidation_volatility) * 100
            
            pattern = PatternData(
                pattern_id=pattern_id,
                pattern_type=PatternType.CONTINUATION,
                timeframe=timeframe,
                start_time=pattern_data[0].get('timestamp'),
                end_time=pattern_data[-1].get('timestamp'),
                price_data=pattern_data,
                pattern_strength=strength,
                confidence_level=self._determine_confidence_level(strength),
                expected_move=self._calculate_volatility(pattern_data) * 2,
                success_probability=0.7,  # Continuation มีโอกาสสำเร็จสูง
                pattern_parameters={
                    'direction': direction,
                    'consolidation_volatility': consolidation_volatility
                }
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Continuation Pattern: {e}")
            return None
        
    def _calculate_trend_direction(self, price_data: List[Dict[str, Any]]) -> str:
        """คำนวณทิศทางของ Trend"""
        if len(price_data) < 3:
            return "NEUTRAL"
        
        try:
            # ใช้ Linear Regression เพื่อหาทิศทาง
            closes = [bar['close'] for bar in price_data]
            x = list(range(len(closes)))
            
            # คำนวณ slope
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(closes)
            sum_xy = sum(x[i] * closes[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            
            # กำหนดทิศทาง
            if slope > 0.1:
                return "BULLISH"
            elif slope < -0.1:
                return "BEARISH"
            else:
                return "NEUTRAL"
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Trend Direction: {e}")
            return "NEUTRAL"
    
    def _calculate_volatility(self, price_data: List[Dict[str, Any]]) -> float:
        """คำนวณ Volatility"""
        if len(price_data) < 2:
            return 0.0
        
        try:
            returns = []
            for i in range(1, len(price_data)):
                prev_close = price_data[i-1]['close']
                curr_close = price_data[i]['close']
                ret = (curr_close - prev_close) / prev_close
                returns.append(ret)
            
            return statistics.stdev(returns) if len(returns) > 1 else 0.0
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Volatility: {e}")
            return 0.0
    
    def _calculate_bullish_reversal_strength(self, price_data: List[Dict[str, Any]]) -> float:
        """คำนวณความแรงของ Bullish Reversal"""
        try:
            if len(price_data) < 3:
                return 0.0
            
            strength = 0.0
            
            # ตรวจสอบ Hammer/Doji patterns
            last_bar = price_data[-1]
            body_size = abs(last_bar['close'] - last_bar['open'])
            total_range = last_bar['high'] - last_bar['low']
            
            if total_range > 0:
                lower_shadow = last_bar['open'] - last_bar['low'] if last_bar['close'] > last_bar['open'] else last_bar['close'] - last_bar['low']
                
                # Hammer pattern
                if lower_shadow > body_size * 2:
                    strength += 0.3
                
                # Small body (Doji-like)
                if body_size / total_range < 0.3:
                    strength += 0.2
            
            # ตรวจสอบ Volume spike
            if len(price_data) >= 5:
                avg_volume = statistics.mean([bar.get('volume', 0) for bar in price_data[:-1]])
                current_volume = last_bar.get('volume', 0)
                
                if current_volume > avg_volume * 1.5:
                    strength += 0.2
            
            # ตรวจสอบ Support level test
            lows = [bar['low'] for bar in price_data[:-1]]
            support_level = min(lows)
            
            if abs(last_bar['low'] - support_level) / support_level < 0.01:  # ใกล้ Support
                strength += 0.3
            
            return min(1.0, strength)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Bullish Reversal Strength: {e}")
            return 0.0
    
    def _calculate_bearish_reversal_strength(self, price_data: List[Dict[str, Any]]) -> float:
        """คำนวณความแรงของ Bearish Reversal"""
        try:
            if len(price_data) < 3:
                return 0.0
            
            strength = 0.0
            
            # ตรวจสอบ Shooting Star/Doji patterns
            last_bar = price_data[-1]
            body_size = abs(last_bar['close'] - last_bar['open'])
            total_range = last_bar['high'] - last_bar['low']
            
            if total_range > 0:
                upper_shadow = last_bar['high'] - last_bar['open'] if last_bar['close'] < last_bar['open'] else last_bar['high'] - last_bar['close']
                
                # Shooting Star pattern
                if upper_shadow > body_size * 2:
                    strength += 0.3
                
                # Small body (Doji-like)
                if body_size / total_range < 0.3:
                    strength += 0.2
            
            # ตรวจสอบ Volume spike
            if len(price_data) >= 5:
                avg_volume = statistics.mean([bar.get('volume', 0) for bar in price_data[:-1]])
                current_volume = last_bar.get('volume', 0)
                
                if current_volume > avg_volume * 1.5:
                    strength += 0.2
            
            # ตรวจสอบ Resistance level test
            highs = [bar['high'] for bar in price_data[:-1]]
            resistance_level = max(highs)
            
            if abs(last_bar['high'] - resistance_level) / resistance_level < 0.01:  # ใกล้ Resistance
                strength += 0.3
            
            return min(1.0, strength)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Bearish Reversal Strength: {e}")
            return 0.0
    
    def _determine_confidence_level(self, strength_score: float) -> PatternConfidence:
        """กำหนดระดับความมั่นใจ"""
        if strength_score >= 90:
            return PatternConfidence.VERY_HIGH
        elif strength_score >= 80:
            return PatternConfidence.HIGH
        elif strength_score >= 60:
            return PatternConfidence.MEDIUM
        elif strength_score >= 40:
            return PatternConfidence.LOW
        else:
            return PatternConfidence.VERY_LOW
    
    def _calculate_breakout_success_probability(self, pattern_data: List[Dict[str, Any]], 
                                                direction: str) -> float:
        """คำนวณความน่าจะเป็นของความสำเร็จ Breakout"""
        try:
            # Base probability
            base_prob = 0.6
            
            # ปรับตาม Volume
            if len(pattern_data) >= 2:
                last_volume = pattern_data[-1].get('volume', 0)
                prev_volume = pattern_data[-2].get('volume', 0)
                
                if last_volume > prev_volume * 1.5:
                    base_prob += 0.1
            
            # ปรับตาม Time of day (สมมติ)
            current_hour = datetime.now().hour
            if 15 <= current_hour <= 18:  # London session
                base_prob += 0.05
            elif 20 <= current_hour <= 23:  # NY session
                base_prob += 0.05
            
            return min(0.9, base_prob)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Breakout Success Probability: {e}")
            return 0.6
    
    def _calculate_false_breakout_success_probability(self, pattern_data: List[Dict[str, Any]], 
                                                    direction: str) -> float:
        """คำนวณความน่าจะเป็นของความสำเร็จ False Breakout"""
        try:
            # False Breakout มีโอกาสสำเร็จสูงกว่า Breakout เล็กน้อย
            base_prob = 0.65
            
            # ปรับตามความแรงของ Pullback
            if len(pattern_data) >= 2:
                breakout_price = pattern_data[0]['close']
                current_price = pattern_data[-1]['close']
                pullback = abs(current_price - breakout_price) / breakout_price
                
                if pullback > 0.005:  # Pullback > 0.5%
                    base_prob += 0.1
            
            return min(0.85, base_prob)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ False Breakout Success Probability: {e}")
            return 0.65
    
    def _calculate_reversal_success_probability(self, pattern_data: List[Dict[str, Any]], 
                                                direction: str) -> float:
        """คำนวณความน่าจะเป็นของความสำเร็จ Reversal"""
        try:
            # Reversal มีความเสี่ยงสูงกว่า
            base_prob = 0.55
            
            # ปรับตาม Support/Resistance strength
            if direction == "BULLISH":
                lows = [bar['low'] for bar in pattern_data[:-1]]
                support_tests = sum(1 for low in lows if abs(low - min(lows)) / min(lows) < 0.01)
                
                if support_tests >= 2:  # Support ถูกทดสอบหลายครั้ง
                    base_prob += 0.15
            
            else:  # BEARISH
                highs = [bar['high'] for bar in pattern_data[:-1]]
                resistance_tests = sum(1 for high in highs if abs(high - max(highs)) / max(highs) < 0.01)
                
                if resistance_tests >= 2:  # Resistance ถูกทดสอบหลายครั้ง
                    base_prob += 0.15
            
            return min(0.8, base_prob)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Reversal Success Probability: {e}")
            return 0.55

class TradingBehaviorAnalyzer:
    """
    วิเคราะห์ Trading Behavior Patterns
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Behavior Pattern Parameters
        self.scalping_max_duration = timedelta(minutes=15)
        self.trend_min_duration = timedelta(hours=1)
        self.news_reaction_window = timedelta(minutes=30)
        self.session_transition_window = timedelta(minutes=60)
    
    def detect_behavior_patterns(self, trade_history: List[Dict[str, Any]],
                                timeframe: PatternTimeframe) -> List[PatternData]:
        """
        ตรวจจับ Trading Behavior Patterns
        
        Args:
            trade_history: ประวัติการเทรด
            timeframe: กรอบเวลา
            
        Returns:
            List[PatternData]: รายการ Behavior Patterns
        """
        try:
            detected_patterns = []
            
            if len(trade_history) < 5:
                return detected_patterns
            
            # ตรวจจับ Scalping Burst Patterns
            scalping_patterns = self._detect_scalping_burst_patterns(trade_history, timeframe)
            detected_patterns.extend(scalping_patterns)
            
            # ตรวจจับ Trend Riding Patterns
            trend_patterns = self._detect_trend_riding_patterns(trade_history, timeframe)
            detected_patterns.extend(trend_patterns)
            
            # ตรวจจับ Mean Reversion Cycle Patterns
            reversion_patterns = self._detect_mean_reversion_patterns(trade_history, timeframe)
            detected_patterns.extend(reversion_patterns)
            
            # ตรวจจับ News Reaction Patterns
            news_patterns = self._detect_news_reaction_patterns(trade_history, timeframe)
            detected_patterns.extend(news_patterns)
            
            # ตรวจจับ Session Transition Patterns
            session_patterns = self._detect_session_transition_patterns(trade_history, timeframe)
            detected_patterns.extend(session_patterns)
            
            # ตรวจจับ High Frequency Cluster Patterns
            hf_patterns = self._detect_high_frequency_patterns(trade_history, timeframe)
            detected_patterns.extend(hf_patterns)
            
            self.logger.debug(f"🔍 ตรวจพบ Behavior Patterns: {len(detected_patterns)} patterns")
            
            return detected_patterns
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ Behavior Patterns: {e}")
            return []
    
    def _detect_scalping_burst_patterns(self, trade_history: List[Dict[str, Any]],
                                        timeframe: PatternTimeframe) -> List[PatternData]:
        """ตรวจจับ Scalping Burst Patterns"""
        patterns = []
        
        try:
            # หาช่วงเวลาที่มีการ Scalp หลายครั้งติดกัน
            scalping_sequences = []
            current_sequence = []
            
            for trade in trade_history:
                trade_duration = trade.get('duration', timedelta(hours=1))
                
                if trade_duration <= self.scalping_max_duration:
                    current_sequence.append(trade)
                else:
                    if len(current_sequence) >= 3:  # ต้องมีอย่างน้อย 3 scalp trades
                        scalping_sequences.append(current_sequence.copy())
                    current_sequence = []
            
            # ตรวจสอบ sequence สุดท้าย
            if len(current_sequence) >= 3:
                scalping_sequences.append(current_sequence)
            
            # สร้าง Pattern สำหรับแต่ละ sequence
            for i, sequence in enumerate(scalping_sequences):
                pattern = self._create_scalping_burst_pattern(sequence, timeframe, i)
                if pattern:
                    patterns.append(pattern)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ Scalping Burst: {e}")
        
        return patterns
    
    def _detect_trend_riding_patterns(self, trade_history: List[Dict[str, Any]],
                                    timeframe: PatternTimeframe) -> List[PatternData]:
        """ตรวจจับ Trend Riding Patterns"""
        patterns = []
        
        try:
            # หาการเทรดที่ถือนานและไปทิศทางเดียวกัน
            trend_sequences = []
            
            for i in range(len(trade_history) - 2):
                # ตรวจสอบ 3 trades ติดกัน
                trades = trade_history[i:i+3]
                
                # ตรวจสอบว่าเป็น Trend Riding หรือไม่
                all_long_duration = all(trade.get('duration', timedelta()) >= self.trend_min_duration 
                                        for trade in trades)
                same_direction = len(set(trade.get('direction', 'UNKNOWN') for trade in trades)) == 1
                profitable = sum(trade.get('pnl', 0) for trade in trades) > 0
                
                if all_long_duration and same_direction and profitable:
                    trend_sequences.append(trades)
            
            # สร้าง Pattern
            for i, sequence in enumerate(trend_sequences):
                pattern = self._create_trend_riding_pattern(sequence, timeframe, i)
                if pattern:
                    patterns.append(pattern)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ Trend Riding: {e}")
        
        return patterns
    
    def _detect_mean_reversion_patterns(self, trade_history: List[Dict[str, Any]],
                                        timeframe: PatternTimeframe) -> List[PatternData]:
        """ตรวจจับ Mean Reversion Cycle Patterns"""
        patterns = []
        
        try:
            # หา Pattern ของการเทรดไปมาในช่วงราคา
            for i in range(len(trade_history) - 3):
                trades = trade_history[i:i+4]
                
                # ตรวจสอบ Mean Reversion cycle
                directions = [trade.get('direction', 'UNKNOWN') for trade in trades]
                
                # ต้องมีการสลับทิศทาง
                direction_changes = sum(1 for j in range(1, len(directions)) 
                                        if directions[j] != directions[j-1])
                
                if direction_changes >= 2:  # มีการสลับทิศทางอย่างน้อย 2 ครั้ง
                    # ตรวจสอบว่าเทรดใน Range เดียวกัน
                    entry_prices = [trade.get('entry_price', 0) for trade in trades]
                    price_range = max(entry_prices) - min(entry_prices)
                    avg_price = sum(entry_prices) / len(entry_prices)
                    
                    if price_range / avg_price < 0.01:  # Range < 1%
                        pattern = self._create_mean_reversion_pattern(trades, timeframe, i)
                        if pattern:
                            patterns.append(pattern)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ Mean Reversion: {e}")
        
        return patterns
    
    def _detect_news_reaction_patterns(self, trade_history: List[Dict[str, Any]],
                                        timeframe: PatternTimeframe) -> List[PatternData]:
        """ตรวจจับ News Reaction Patterns"""
        patterns = []
        
        try:
            # หาการเทรดที่เกิดขึ้นใกล้เวลาข่าว
            news_times = self._get_news_times()  # ดึงเวลาข่าวจากแหล่งอื่น
            
            for news_time in news_times:
                nearby_trades = []
                
                for trade in trade_history:
                    trade_time = trade.get('entry_time', datetime.now())
                    
                    if abs(trade_time - news_time) <= self.news_reaction_window:
                        nearby_trades.append(trade)
                
                if len(nearby_trades) >= 2:  # มีการเทรดอย่างน้อย 2 ครั้งหลังข่าว
                    pattern = self._create_news_reaction_pattern(nearby_trades, timeframe, news_time)
                    if pattern:
                        patterns.append(pattern)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ News Reaction: {e}")
        
        return patterns
    
    def _detect_session_transition_patterns(self, trade_history: List[Dict[str, Any]],
                                            timeframe: PatternTimeframe) -> List[PatternData]:
        """ตรวจจับ Session Transition Patterns"""
        patterns = []
        
        try:
            # Session transition times (GMT+7)
            transitions = [
                (8, "ASIAN_TO_LONDON"),
                (15, "LONDON_OVERLAP"),
                (20, "NY_OVERLAP"),
                (2, "NY_TO_ASIAN")
            ]
            
            for transition_hour, transition_name in transitions:
                transition_trades = []
                
                for trade in trade_history:
                    trade_time = trade.get('entry_time', datetime.now())
                    
                    # ตรวจสอบว่าเทรดใน Window ของ transition หรือไม่
                    if abs(trade_time.hour - transition_hour) <= 1:
                        transition_trades.append(trade)
                
                if len(transition_trades) >= 3:
                    pattern = self._create_session_transition_pattern(
                        transition_trades, timeframe, transition_name
                    )
                    if pattern:
                        patterns.append(pattern)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ Session Transition: {e}")
        
        return patterns
    
    def _detect_high_frequency_patterns(self, trade_history: List[Dict[str, Any]],
                                        timeframe: PatternTimeframe) -> List[PatternData]:
        """ตรวจจับ High Frequency Cluster Patterns"""
        patterns = []
        
        try:
            # หา Cluster ของการเทรดในช่วงเวลาสั้น
            time_window = timedelta(minutes=30)
            clusters = []
            
            for i, trade in enumerate(trade_history):
                trade_time = trade.get('entry_time', datetime.now())
                cluster_trades = [trade]
                
                # หาเทรดอื่นๆ ในช่วงเวลาเดียวกัน
                for j, other_trade in enumerate(trade_history):
                    if i != j:
                        other_time = other_trade.get('entry_time', datetime.now())
                        
                        if abs(trade_time - other_time) <= time_window:
                            cluster_trades.append(other_trade)
                
                if len(cluster_trades) >= 5:  # High frequency = อย่างน้อย 5 trades ใน 30 นาที
                    clusters.append(cluster_trades)
            
            # สร้าง Pattern สำหรับแต่ละ cluster
            unique_clusters = []
            for cluster in clusters:
                # ตรวจสอบว่าไม่ซ้ำกับ cluster ที่มีอยู่แล้ว
                is_duplicate = False
                for existing_cluster in unique_clusters:
                    if len(set(t.get('trade_id', '') for t in cluster) & 
                            set(t.get('trade_id', '') for t in existing_cluster)) > 0:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_clusters.append(cluster)
            
            for i, cluster in enumerate(unique_clusters):
                pattern = self._create_high_frequency_pattern(cluster, timeframe, i)
                if pattern:
                    patterns.append(pattern)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ High Frequency: {e}")
        
        return patterns
    
    def _create_scalping_burst_pattern(self, trades: List[Dict[str, Any]],
                                        timeframe: PatternTimeframe, sequence_id: int) -> Optional[PatternData]:
        """สร้าง Scalping Burst Pattern"""
        try:
            pattern_id = f"SCALPING_BURST_{int(time.time())}_{sequence_id}"
            
            # คำนวณ Performance metrics
            total_pnl = sum(trade.get('pnl', 0) for trade in trades)
            win_rate = sum(1 for trade in trades if trade.get('pnl', 0) > 0) / len(trades)
            avg_duration = sum((trade.get('duration', timedelta()).total_seconds() 
                                for trade in trades), 0) / len(trades) / 60  # นาที
            
            # Pattern strength ขึ้นกับ profitability และ consistency
            strength = (win_rate * 50) + (min(50, total_pnl) if total_pnl > 0 else 0)
            
            pattern = PatternData(
                pattern_id=pattern_id,
                pattern_type=PatternType.SCALPING_BURST,
                timeframe=timeframe,
                start_time=trades[0].get('entry_time'),
                end_time=trades[-1].get('exit_time'),
                pattern_strength=strength,
                confidence_level=self._determine_confidence_level(strength),
                success_probability=win_rate,
                pattern_parameters={
                    'trade_count': len(trades),
                    'total_pnl': total_pnl,
                    'win_rate': win_rate,
                    'avg_duration_minutes': avg_duration
                }
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Scalping Burst Pattern: {e}")
            return None
    
    def _create_trend_riding_pattern(self, trades: List[Dict[str, Any]],
                                    timeframe: PatternTimeframe, sequence_id: int) -> Optional[PatternData]:
        """สร้าง Trend Riding Pattern"""
        try:
            pattern_id = f"TREND_RIDING_{int(time.time())}_{sequence_id}"
            
            total_pnl = sum(trade.get('pnl', 0) for trade in trades)
            direction = trades[0].get('direction', 'UNKNOWN')
            avg_duration = sum((trade.get('duration', timedelta()).total_seconds() 
                                for trade in trades), 0) / len(trades) / 3600  # ชั่วโมง
            
            # Trend riding strength ขึ้นกับความสามารถในการถือ position นาน
            strength = min(100, (avg_duration * 10) + (total_pnl * 0.1 if total_pnl > 0 else 0))
            
            pattern = PatternData(
                pattern_id=pattern_id,
                pattern_type=PatternType.TREND_RIDING,
                timeframe=timeframe,
                start_time=trades[0].get('entry_time'),
                end_time=trades[-1].get('exit_time'),
                pattern_strength=strength,
                confidence_level=self._determine_confidence_level(strength),
                success_probability=0.7 if total_pnl > 0 else 0.3,
                pattern_parameters={
                    'direction': direction,
                    'trade_count': len(trades),
                    'total_pnl': total_pnl,
                    'avg_duration_hours': avg_duration
                }
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Trend Riding Pattern: {e}")
            return None
    
    def _create_mean_reversion_pattern(self, trades: List[Dict[str, Any]],
                                        timeframe: PatternTimeframe, sequence_id: int) -> Optional[PatternData]:
        """สร้าง Mean Reversion Pattern"""
        try:
            pattern_id = f"MEAN_REVERSION_{int(time.time())}_{sequence_id}"
            
            total_pnl = sum(trade.get('pnl', 0) for trade in trades)
            entry_prices = [trade.get('entry_price', 0) for trade in trades]
            price_range = max(entry_prices) - min(entry_prices)
            
            # Mean reversion strength ขึ้นกับความสม่ำเสมอของ range
            range_consistency = 1.0 - (price_range / statistics.mean(entry_prices))
            strength = range_consistency * 80 + (20 if total_pnl > 0 else 0)
            
            pattern = PatternData(
                pattern_id=pattern_id,
                pattern_type=PatternType.MEAN_REVERSION_CYCLE,
                timeframe=timeframe,
                start_time=trades[0].get('entry_time'),
                end_time=trades[-1].get('exit_time'),
                pattern_strength=strength,
                confidence_level=self._determine_confidence_level(strength),
                success_probability=0.6 if total_pnl > 0 else 0.4,
                pattern_parameters={
                    'trade_count': len(trades),
                    'total_pnl': total_pnl,
                    'price_range': price_range,
                    'range_consistency': range_consistency
                }
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Mean Reversion Pattern: {e}")
            return None
    
    def _create_news_reaction_pattern(self, trades: List[Dict[str, Any]],
                                    timeframe: PatternTimeframe, news_time: datetime) -> Optional[PatternData]:
        """สร้าง News Reaction Pattern"""
        try:
            pattern_id = f"NEWS_REACTION_{int(news_time.timestamp())}"
            
            total_pnl = sum(trade.get('pnl', 0) for trade in trades)
            reaction_speed = []
            
            for trade in trades:
                trade_time = trade.get('entry_time', datetime.now())
                speed = abs((trade_time - news_time).total_seconds())
                reaction_speed.append(speed)
            
            avg_reaction_speed = statistics.mean(reaction_speed) if reaction_speed else 300
            
            # News reaction strength ขึ้นกับความเร็วในการ react
            speed_score = max(0, 100 - (avg_reaction_speed / 60 * 10))  # ลดลง 10 คะแนนต่อนาที
            strength = (speed_score * 0.6) + (40 if total_pnl > 0 else 0)
            
            pattern = PatternData(
                pattern_id=pattern_id,
                pattern_type=PatternType.NEWS_REACTION_PATTERN,
                timeframe=timeframe,
                start_time=min(trade.get('entry_time', datetime.now()) for trade in trades),
                end_time=max(trade.get('exit_time', datetime.now()) for trade in trades),
                pattern_strength=strength,
                confidence_level=self._determine_confidence_level(strength),
                success_probability=0.65 if total_pnl > 0 else 0.35,
                pattern_parameters={
                    'news_time': news_time.isoformat(),
                    'trade_count': len(trades),
                    'total_pnl': total_pnl,
                    'avg_reaction_speed_seconds': avg_reaction_speed
                }
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง News Reaction Pattern: {e}")
            return None
        
   
    def _create_session_transition_pattern(self, trades: List[Dict[str, Any]],
                                            timeframe: PatternTimeframe, transition_name: str) -> Optional[PatternData]:
        """สร้าง Session Transition Pattern"""
        try:
            pattern_id = f"SESSION_TRANSITION_{int(time.time())}_{transition_name}"
            
            total_pnl = sum(trade.get('pnl', 0) for trade in trades)
            volumes = [trade.get('volume', 0.01) for trade in trades]
            avg_volume = statistics.mean(volumes)
            
            # Session transition strength ขึ้นกับ volume และ profitability
            volume_score = min(50, avg_volume * 500)  # Scale volume
            profit_score = 50 if total_pnl > 0 else 20
            strength = volume_score + profit_score
            
            pattern = PatternData(
                pattern_id=pattern_id,
                pattern_type=PatternType.SESSION_TRANSITION,
                timeframe=timeframe,
                start_time=min(trade.get('entry_time', datetime.now()) for trade in trades),
                end_time=max(trade.get('exit_time', datetime.now()) for trade in trades),
                pattern_strength=strength,
                confidence_level=self._determine_confidence_level(strength),
                success_probability=0.7 if total_pnl > 0 else 0.4,
                pattern_parameters={
                    'transition_type': transition_name,
                    'trade_count': len(trades),
                    'total_pnl': total_pnl,
                    'avg_volume': avg_volume
                }
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Session Transition Pattern: {e}")
            return None
    
    def _create_high_frequency_pattern(self, trades: List[Dict[str, Any]],
                                        timeframe: PatternTimeframe, cluster_id: int) -> Optional[PatternData]:
        """สร้าง High Frequency Pattern"""
        try:
            pattern_id = f"HIGH_FREQUENCY_{int(time.time())}_{cluster_id}"
            
            total_pnl = sum(trade.get('pnl', 0) for trade in trades)
            trade_count = len(trades)
            
            # คำนวณ frequency (trades per hour)
            time_span = max(trade.get('exit_time', datetime.now()) for trade in trades) - \
                        min(trade.get('entry_time', datetime.now()) for trade in trades)
            hours = max(0.5, time_span.total_seconds() / 3600)  # อย่างน้อย 0.5 ชั่วโมง
            frequency = trade_count / hours
            
            # High frequency strength ขึ้นกับ frequency และ efficiency
            frequency_score = min(80, frequency * 8)  # Max 80 คะแนน
            efficiency_score = 20 if total_pnl > 0 else 0
            strength = frequency_score + efficiency_score
            
            pattern = PatternData(
                pattern_id=pattern_id,
                pattern_type=PatternType.HIGH_FREQUENCY_CLUSTER,
                timeframe=timeframe,
                start_time=min(trade.get('entry_time', datetime.now()) for trade in trades),
                end_time=max(trade.get('exit_time', datetime.now()) for trade in trades),
                pattern_strength=strength,
                confidence_level=self._determine_confidence_level(strength),
                success_probability=0.6 if total_pnl > 0 else 0.4,
                pattern_parameters={
                    'trade_count': trade_count,
                    'total_pnl': total_pnl,
                    'frequency_per_hour': frequency,
                    'time_span_hours': hours
                }
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง High Frequency Pattern: {e}")
            return None
    
    def _get_news_times(self) -> List[datetime]:
        """ดึงเวลาข่าวสำคัญ (Mock data)"""
        # ในระบบจริงจะเชื่อมต่อกับ Economic Calendar
        base_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        return [
            base_time.replace(hour=15, minute=30),  # London session news
            base_time.replace(hour=17, minute=0),   # US session news
            base_time.replace(hour=21, minute=30),  # NY session news
        ]

class PatternPerformanceTracker:
    """
    ติดตามประสิทธิภาพของ Patterns
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.pattern_database = {}  # เก็บข้อมูล Pattern และ Performance
        self.performance_history = defaultdict(list)
    
    def track_pattern_performance(self, pattern: PatternData, 
                                actual_result: Dict[str, Any]) -> PatternPerformance:
        """
        ติดตามประสิทธิภาพของ Pattern
        
        Args:
            pattern: ข้อมูล Pattern
            actual_result: ผลลัพธ์จริงที่เกิดขึ้น
            
        Returns:
            PatternPerformance: ประสิทธิภาพที่อัพเดท
        """
        try:
            pattern_type = pattern.pattern_type
            
            # ดึงหรือสร้าง Performance record
            if pattern_type not in self.pattern_database:
                self.pattern_database[pattern_type] = PatternPerformance(pattern_type=pattern_type)
            
            performance = self.pattern_database[pattern_type]
            
            # อัพเดท Performance
            performance.total_occurrences += 1
            
            pnl = actual_result.get('pnl', 0)
            success = actual_result.get('success', pnl > 0)
            duration = actual_result.get('duration', timedelta())
            
            if success:
                performance.successful_trades += 1
                performance.total_pips_gained += actual_result.get('pips_gained', 0)
            else:
                performance.failed_trades += 1
            
            # คำนวณ Success Rate
            performance.success_rate = (performance.successful_trades / performance.total_occurrences) * 100
            
            # คำนวณ Average Pips
            if performance.successful_trades > 0:
                performance.average_pips_per_trade = performance.total_pips_gained / performance.successful_trades
            
            # อัพเดท Duration metrics
            if duration:
                if not performance.fastest_completion or duration < performance.fastest_completion:
                    performance.fastest_completion = duration
                
                if not performance.slowest_completion or duration > performance.slowest_completion:
                    performance.slowest_completion = duration
                
                # คำนวณ Average Duration
                all_durations = self.performance_history[pattern_type]
                all_durations.append(duration)
                
                if len(all_durations) > 100:  # เก็บแค่ 100 records ล่าสุด
                    all_durations.pop(0)
                
                avg_seconds = statistics.mean([d.total_seconds() for d in all_durations])
                performance.average_duration = timedelta(seconds=avg_seconds)
            
            # อัพเดท Session Performance
            session = actual_result.get('session', MarketSession.ASIAN)
            if session not in performance.session_performance:
                performance.session_performance[session] = 0.0
            
            session_success_rate = performance.session_performance[session]
            session_count = sum(1 for r in self.performance_history[pattern_type] 
                                if r.get('session') == session)
            
            if session_count > 0:
                performance.session_performance[session] = (
                    (session_success_rate * (session_count - 1) + (100 if success else 0)) / session_count
                )
            else:
                performance.session_performance[session] = 100 if success else 0
            
            # คำนวณ Recent Performance (30 วันล่าสุด)
            recent_results = [r for r in self.performance_history[pattern_type][-30:]]
            if recent_results:
                recent_successes = sum(1 for r in recent_results if r.get('success', False))
                performance.recent_success_rate = (recent_successes / len(recent_results)) * 100
            
            # กำหนด Performance Trend
            if len(self.performance_history[pattern_type]) >= 20:
                old_results = self.performance_history[pattern_type][-20:-10]
                new_results = self.performance_history[pattern_type][-10:]
                
                old_rate = sum(1 for r in old_results if r.get('success', False)) / len(old_results)
                new_rate = sum(1 for r in new_results if r.get('success', False)) / len(new_results)
                
                if new_rate > old_rate + 0.1:
                    performance.performance_trend = "IMPROVING"
                elif new_rate < old_rate - 0.1:
                    performance.performance_trend = "DECLINING"
                else:
                    performance.performance_trend = "STABLE"
            
            # เพิ่มผลลัพธ์ลง History
            result_record = {
                'timestamp': datetime.now(),
                'success': success,
                'pnl': pnl,
                'duration': duration,
                'session': session,
                **actual_result
            }
            self.performance_history[pattern_type].append(result_record)
            
            return performance
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการติดตาม Pattern Performance: {e}")
            return PatternPerformance(pattern_type=pattern.pattern_type)
    
    def get_pattern_performance(self, pattern_type: PatternType) -> Optional[PatternPerformance]:
        """ดึงประสิทธิภาพของ Pattern"""
        return self.pattern_database.get(pattern_type)
    
    def get_all_pattern_performances(self) -> Dict[PatternType, PatternPerformance]:
        """ดึงประสิทธิภาพของ Pattern ทั้งหมด"""
        return self.pattern_database.copy()
    
    def get_top_performing_patterns(self, limit: int = 5) -> List[Tuple[PatternType, PatternPerformance]]:
        """ดึง Pattern ที่มีประสิทธิภาพสูงสุด"""
        try:
            patterns = [(pt, perf) for pt, perf in self.pattern_database.items() 
                        if perf.total_occurrences >= 5]  # อย่างน้อย 5 occurrences
            
            # เรียงตาม Success Rate และ Average Pips
            patterns.sort(key=lambda x: (x[1].success_rate, x[1].average_pips_per_trade), reverse=True)
            
            return patterns[:limit]
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึง Top Performing Patterns: {e}")
            return []

class PatternSignalGenerator:
    """
    สร้างสัญญาณการเทรดจาก Patterns
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.signal_history = deque(maxlen=1000)
        self.active_signals = {}
    
    def generate_signal_from_pattern(self, pattern: PatternData, 
                                    market_context: Dict[str, Any],
                                    performance_data: Optional[PatternPerformance] = None) -> Optional[PatternSignal]:
        """
        สร้างสัญญาณจาก Pattern
        
        Args:
            pattern: ข้อมูล Pattern
            market_context: บริบทตลาดปัจจุบัน
            performance_data: ข้อมูลประสิทธิภาพของ Pattern
            
        Returns:
            PatternSignal: สัญญาณที่สร้างจาก Pattern
        """
        try:
            signal_id = f"SIGNAL_{pattern.pattern_id}_{int(time.time())}"
            
            # กำหนดทิศทางสัญญาณ
            direction = self._determine_signal_direction(pattern, market_context)
            
            if direction == "NEUTRAL":
                return None  # ไม่สร้างสัญญาณ
            
            # คำนวณ Entry Price
            entry_price = self._calculate_entry_price(pattern, market_context)
            
            # คำนวณ Target Prices
            target_prices = self._calculate_target_prices(pattern, entry_price, direction)
            
            # คำนวณ Invalidation Price
            invalidation_price = self._calculate_invalidation_price(pattern, entry_price, direction)
            
            # คำนวณ Signal Strength
            signal_strength = self._calculate_signal_strength(pattern, performance_data, market_context)
            
            # คำนวณ Recommended Volume
            recommended_volume = self._calculate_recommended_volume(pattern, signal_strength, market_context)
            
            # คำนวณ Risk Parameters
            max_risk_pips = abs(entry_price - invalidation_price) / 0.1  # Convert to pips
            
            # สร้าง Signal
            signal = PatternSignal(
                signal_id=signal_id,
                pattern_id=pattern.pattern_id,
                pattern_type=pattern.pattern_type,
                signal_strength=signal_strength,
                direction=direction,
                entry_price=entry_price,
                target_prices=target_prices,
                invalidation_price=invalidation_price,
                recommended_volume=recommended_volume,
                risk_level=self._determine_risk_level(pattern, signal_strength),
                max_risk_pips=max_risk_pips,
                market_context=market_context,
                confidence_score=pattern.pattern_strength * (signal_strength / 100),
                reliability_factors=self._generate_reliability_factors(pattern, performance_data)
            )
            
            # เพิ่มเข้า Active Signals
            self.active_signals[signal_id] = signal
            self.signal_history.append(signal)
            
            self.logger.info(f"📡 สร้างสัญญาณจาก Pattern: {signal_id} ({pattern.pattern_type.value})")
            
            return signal
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้างสัญญาณ: {e}")
            return None
    
    def _determine_signal_direction(self, pattern: PatternData, market_context: Dict[str, Any]) -> str:
        """กำหนดทิศทางของสัญญาณ"""
        try:
            pattern_type = pattern.pattern_type
            pattern_params = pattern.pattern_parameters
            
            # กำหนดทิศทางตาม Pattern Type
            if pattern_type == PatternType.BREAKOUT:
                direction = pattern_params.get('direction', 'NEUTRAL')
                return "BUY" if direction == "BULLISH" else "SELL" if direction == "BEARISH" else "NEUTRAL"
            
            elif pattern_type == PatternType.FALSE_BREAKOUT:
                direction = pattern_params.get('direction', 'NEUTRAL')
                # False breakout = ทิศทางตรงข้าม
                return "SELL" if direction == "BULLISH" else "BUY" if direction == "BEARISH" else "NEUTRAL"
            
            elif pattern_type == PatternType.REVERSAL:
                direction = pattern_params.get('direction', 'NEUTRAL')
                return "BUY" if direction == "BULLISH" else "SELL" if direction == "BEARISH" else "NEUTRAL"
            
            elif pattern_type == PatternType.CONSOLIDATION:
                # รอการทะลุออกจาก Range
                current_price = market_context.get('current_price', 0)
                highest = pattern_params.get('highest', current_price)
                lowest = pattern_params.get('lowest', current_price)
                
                if current_price > highest * 1.001:  # ทะลุขึ้น
                    return "BUY"
                elif current_price < lowest * 0.999:  # ทะลุลง
                    return "SELL"
                else:
                    return "NEUTRAL"
            
            elif pattern_type == PatternType.CONTINUATION:
                direction = pattern_params.get('direction', 'NEUTRAL')
                return "BUY" if direction == "BULLISH" else "SELL" if direction == "BEARISH" else "NEUTRAL"
            
            # Trading Behavior Patterns
            elif pattern_type == PatternType.SCALPING_BURST:
                # ตาม Momentum ปัจจุบัน
                momentum = market_context.get('momentum', 0)
                return "BUY" if momentum > 0.1 else "SELL" if momentum < -0.1 else "NEUTRAL"
            
            elif pattern_type == PatternType.TREND_RIDING:
                trend_direction = market_context.get('trend_direction', 'NEUTRAL')
                return "BUY" if trend_direction == "BULLISH" else "SELL" if trend_direction == "BEARISH" else "NEUTRAL"
            
            elif pattern_type == PatternType.MEAN_REVERSION_CYCLE:
                # Mean reversion = ทิศทางตรงข้ามกับการเคลื่อนไหวปัจจุบัน
                momentum = market_context.get('momentum', 0)
                return "SELL" if momentum > 0.2 else "BUY" if momentum < -0.2 else "NEUTRAL"
            
            else:
                return "NEUTRAL"
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการกำหนดทิศทางสัญญาณ: {e}")
            return "NEUTRAL"
    
    def _calculate_entry_price(self, pattern: PatternData, market_context: Dict[str, Any]) -> float:
        """คำนวณราคาเข้า"""
        try:
            current_price = market_context.get('current_price', 0)
            
            if current_price <= 0:
                # ใช้ราคาจาก Pattern
                if pattern.price_data:
                    current_price = pattern.price_data[-1].get('close', 1850.0)
                else:
                    current_price = 1850.0  # Default XAUUSD price
            
            pattern_type = pattern.pattern_type
            
            # ปรับราคาเข้าตาม Pattern Type
            if pattern_type in [PatternType.BREAKOUT, PatternType.CONTINUATION]:
                # เข้าที่ราคาปัจจุบันหรือใกล้เคียง
                return current_price
            
            elif pattern_type == PatternType.FALSE_BREAKOUT:
                # เข้าหลังจาก Pullback
                key_level = pattern.pattern_parameters.get('key_level', current_price)
                return key_level * 0.999 if current_price < key_level else key_level * 1.001
            
            elif pattern_type == PatternType.REVERSAL:
                # เข้าใกล้ Support/Resistance
                return current_price
            
            elif pattern_type == PatternType.CONSOLIDATION:
                # เข้าที่ขอบ Range
                highest = pattern.pattern_parameters.get('highest', current_price)
                lowest = pattern.pattern_parameters.get('lowest', current_price)
                
                if current_price > (highest + lowest) / 2:
                    return highest * 0.999  # เข้า Short ใกล้ Resistance
                else:
                    return lowest * 1.001   # เข้า Long ใกล้ Support
            
            else:
                return current_price
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณราคาเข้า: {e}")
            return market_context.get('current_price', 1850.0)
    
    def _calculate_target_prices(self, pattern: PatternData, entry_price: float, direction: str) -> List[float]:
        """คำนวณราคาเป้าหมาย"""
        try:
            targets = []
            expected_move = pattern.expected_move
            
            if expected_move <= 0:
                expected_move = 20.0  # Default 20 pips
            
            # สร้าง Multiple targets
            if direction == "BUY":
                targets.append(entry_price + (expected_move * 0.1 * 0.5))    # Target 1: 50% ของ expected move
                targets.append(entry_price + (expected_move * 0.1))          # Target 2: 100% ของ expected move
                targets.append(entry_price + (expected_move * 0.1 * 1.5))    # Target 3: 150% ของ expected move
            else:  # SELL
                targets.append(entry_price - (expected_move * 0.1 * 0.5))    # Target 1
                targets.append(entry_price - (expected_move * 0.1))          # Target 2
                targets.append(entry_price - (expected_move * 0.1 * 1.5))    # Target 3
            
            return targets
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณราคาเป้าหมาย: {e}")
            return [entry_price + 10.0 if direction == "BUY" else entry_price - 10.0]
    
    def _calculate_invalidation_price(self, pattern: PatternData, entry_price: float, direction: str) -> float:
        """คำนวณราคา Invalidation"""
        try:
            pattern_type = pattern.pattern_type
            pattern_params = pattern.pattern_parameters
            
            # Default invalidation distance
            default_distance = 20.0  # 20 pips
            
            if pattern_type == PatternType.BREAKOUT:
                # Invalidation = กลับเข้า Range
                key_level = pattern_params.get('key_level', entry_price)
                if direction == "BUY":
                    return key_level * 0.998  # 0.2% ต่ำกว่า breakout level
                else:
                    return key_level * 1.002  # 0.2% สูงกว่า breakout level
            
            elif pattern_type == PatternType.FALSE_BREAKOUT:
                # Invalidation = ทะลุไปทิศทางเดิม
                key_level = pattern_params.get('key_level', entry_price)
                if direction == "BUY":
                    return key_level * 0.997
                else:
                    return key_level * 1.003
            
            elif pattern_type == PatternType.CONSOLIDATION:
                # Invalidation = กลับเข้า Range
                highest = pattern_params.get('highest', entry_price)
                lowest = pattern_params.get('lowest', entry_price)
                
                if direction == "BUY":
                    return (highest + lowest) / 2  # กลางของ Range
                else:
                    return (highest + lowest) / 2
            
            else:
                # Default invalidation
                if direction == "BUY":
                    return entry_price - (default_distance * 0.1)
                else:
                    return entry_price + (default_distance * 0.1)
                    
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณราคา Invalidation: {e}")
            return entry_price - 20.0 if direction == "BUY" else entry_price + 20.0
    
    def _calculate_signal_strength(self, pattern: PatternData, 
                                    performance_data: Optional[PatternPerformance],
                                    market_context: Dict[str, Any]) -> float:
        """คำนวณความแรงของสัญญาณ"""
        try:
            strength = pattern.pattern_strength  # Base strength
            
            # ปรับตาม Performance History
            if performance_data:
                success_rate = performance_data.success_rate
                if success_rate > 70:
                    strength *= 1.2
                elif success_rate > 50:
                    strength *= 1.0
                else:
                    strength *= 0.8
            
            # ปรับตาม Market Context
            volatility = market_context.get('volatility', 1.0)
            if volatility > 1.5:
                strength *= 0.9  # ลดความแรงในช่วง Volatility สูง
            elif volatility < 0.7:
                strength *= 0.8  # ลดความแรงในช่วง Volatility ต่ำ
            
            # ปรับตาม Time of day
            current_hour = datetime.now().hour
            if 15 <= current_hour <= 18:  # London session
                strength *= 1.1
            elif 20 <= current_hour <= 23:  # NY session
                strength *= 1.05
            
            return min(100.0, strength)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Signal Strength: {e}")
            return 50.0
    
    def _calculate_recommended_volume(self, pattern: PatternData, signal_strength: float,
                                    market_context: Dict[str, Any]) -> float:
        """คำนวณ Volume ที่แนะนำ"""
        try:
            base_volume = 0.01
            
            # ปรับตาม Signal Strength
            strength_multiplier = signal_strength / 100.0
            
            # ปรับตาม Pattern Type
            pattern_multipliers = {
                PatternType.BREAKOUT: 1.2,
                PatternType.FALSE_BREAKOUT: 1.0,
                PatternType.REVERSAL: 0.8,
                PatternType.CONSOLIDATION: 0.9,
                PatternType.CONTINUATION: 1.1,
                PatternType.SCALPING_BURST: 0.5,
                PatternType.HIGH_FREQUENCY_CLUSTER: 0.3
            }
            
            pattern_multiplier = pattern_multipliers.get(pattern.pattern_type, 1.0)
            
            # ปรับตาม Market Volatility
            volatility = market_context.get('volatility', 1.0)
            volatility_multiplier = 1.0 / volatility if volatility > 0 else 1.0
            
            # คำนวณ Volume สุดท้าย
            recommended_volume = base_volume * strength_multiplier * pattern_multiplier * volatility_multiplier
            
            # จำกัดขอบเขต
            return max(0.01, min(0.5, recommended_volume))
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Recommended Volume: {e}")
            return 0.01
    
    def _determine_risk_level(self, pattern: PatternData, signal_strength: float) -> str:
        """กำหนดระดับความเสี่ยง"""
        try:
            if signal_strength >= 80 and pattern.confidence_level in [PatternConfidence.VERY_HIGH, PatternConfidence.HIGH]:
                return "LOW"
            elif signal_strength >= 60:
                return "MEDIUM"
            else:
                return "HIGH"
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการกำหนดระดับความเสี่ยง: {e}")
            return "MEDIUM"
    
    def _generate_reliability_factors(self, pattern: PatternData, 
                                    performance_data: Optional[PatternPerformance]) -> List[str]:
        """สร้างปัจจัยความน่าเชื่อถือ"""
        factors = []
        
        try:
            # Pattern Strength
            if pattern.pattern_strength >= 80:
                factors.append("✅ Pattern มีความแรงสูง")
            elif pattern.pattern_strength >= 60:
                factors.append("🟡 Pattern มีความแรงปานกลาง")
            else:
                factors.append("🔴 Pattern มีความแรงต่ำ")
           
            # Confidence Level
            if pattern.confidence_level == PatternConfidence.VERY_HIGH:
                factors.append("✅ ความมั่นใจในการตรวจจับสูงมาก")
            elif pattern.confidence_level == PatternConfidence.HIGH:
                factors.append("✅ ความมั่นใจในการตรวจจับสูง")
            
            # Historical Performance
            if performance_data:
                if performance_data.success_rate >= 70:
                    factors.append("✅ ประสิทธิภาพในอดีตสูง")
                elif performance_data.success_rate >= 50:
                    factors.append("🟡 ประสิทธิภาพในอดีตปานกลาง")
                else:
                    factors.append("🔴 ประสิทธิภาพในอดีตต่ำ")
                
                if performance_data.total_occurrences >= 20:
                    factors.append("✅ มีข้อมูลในอดีตเพียงพอ")
                else:
                    factors.append("🟡 ข้อมูลในอดีตจำกัด")
            
            # Success Probability
            if pattern.success_probability >= 0.7:
                factors.append("✅ ความน่าจะเป็นของความสำเร็จสูง")
            elif pattern.success_probability >= 0.5:
                factors.append("🟡 ความน่าจะเป็นของความสำเร็จปานกลาง")
            
            return factors
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Reliability Factors: {e}")
            return ["⚠️ ไม่สามารถประเมินความน่าเชื่อถือได้"]
   
    def get_active_signals(self) -> Dict[str, PatternSignal]:
        """ดึงสัญญาณที่ยังใช้งานได้"""
        active = {}
        current_time = datetime.now()
        
        for signal_id, signal in self.active_signals.items():
            if signal.valid_until > current_time:
                active[signal_id] = signal
            else:
                # ลบสัญญาณที่หมดอายุ
                del self.active_signals[signal_id]
        
        return active
    
    def invalidate_signal(self, signal_id: str) -> bool:
        """ยกเลิกสัญญาณ"""
        if signal_id in self.active_signals:
            del self.active_signals[signal_id]
            return True
        return False

class PatternDetector:
    """
    🎯 Main Pattern Detector Class
    
    ระบบจดจำและวิเคราะห์รูปแบบการเทรดแบบครอบคลุม
    รวบรวมการวิเคราะห์จากทุก Analyzer เข้าด้วยกัน
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Initialize Analyzers
        self.price_action_analyzer = PriceActionAnalyzer()
        self.behavior_analyzer = TradingBehaviorAnalyzer()
        self.performance_tracker = PatternPerformanceTracker()
        self.signal_generator = PatternSignalGenerator()
        
        # Pattern Database
        self.detected_patterns = {}  # เก็บ Patterns ที่ตรวจพบ
        self.pattern_history = deque(maxlen=1000)
        
        # External Connections
        self.market_analyzer = None       # จะเชื่อมต่อใน start()
        self.trade_analyzer = None        # จะเชื่อมต่อใน start()
        
        # Threading
        self.detection_active = False
        self.detection_thread = None
        self.pattern_queue = deque(maxlen=500)
        
        self.logger.info("🔍 เริ่มต้น Pattern Detector")
    
    @handle_trading_errors(ErrorCategory.PATTERN_DETECTION, ErrorSeverity.MEDIUM)
    async def start_pattern_detector(self) -> None:
        """
        เริ่มต้น Pattern Detector
        """
        self.logger.info("🚀 เริ่มต้น Pattern Detector System")
        
        # เชื่อมต่อ External Components
        try:
            from market_intelligence.market_analyzer import MarketAnalyzer
            self.market_analyzer = MarketAnalyzer()
            
            from analytics_engine.trade_analyzer import get_trade_analyzer
            self.trade_analyzer = get_trade_analyzer()
            
            self.logger.info("✅ เชื่อมต่อ External Components สำเร็จ")
            
        except ImportError as e:
            self.logger.warning(f"⚠️ ไม่สามารถเชื่อมต่อบาง Components: {e}")
        
        # เริ่ม Pattern Detection Processing
        await self._start_pattern_detection()
        
        self.logger.info("✅ Pattern Detector พร้อมทำงาน")
    
    async def detect_patterns(self, price_data: List[Dict[str, Any]] = None,
                            trade_history: List[Dict[str, Any]] = None,
                            timeframe: PatternTimeframe = PatternTimeframe.M15) -> List[PatternData]:
        """
        ตรวจจับ Patterns ทั้งหมด
        
        Args:
            price_data: ข้อมูลราคา
            trade_history: ประวัติการเทรด
            timeframe: กรอบเวลา
            
        Returns:
            List[PatternData]: รายการ Patterns ที่พบ
        """
        try:
            self.logger.info(f"🔍 เริ่มตรวจจับ Patterns - Timeframe: {timeframe.value}")
            
            all_patterns = []
            
            # 1. ตรวจจับ Price Action Patterns
            if price_data:
                price_patterns = self.price_action_analyzer.detect_price_patterns(price_data, timeframe)
                all_patterns.extend(price_patterns)
                self.logger.debug(f"   พบ Price Patterns: {len(price_patterns)}")
            
            # 2. ตรวจจับ Trading Behavior Patterns
            if trade_history:
                behavior_patterns = self.behavior_analyzer.detect_behavior_patterns(trade_history, timeframe)
                all_patterns.extend(behavior_patterns)
                self.logger.debug(f"   พบ Behavior Patterns: {len(behavior_patterns)}")
            
            # 3. กรอง Patterns ที่ซ้ำกัน
            unique_patterns = self._filter_duplicate_patterns(all_patterns)
            
            # 4. เพิ่ม Context Information
            contextualized_patterns = await self._add_market_context(unique_patterns)
            
            # 5. คำนวณ Reliability Score
            scored_patterns = self._calculate_reliability_scores(contextualized_patterns)
            
            # 6. บันทึก Patterns
            for pattern in scored_patterns:
                self.detected_patterns[pattern.pattern_id] = pattern
                self.pattern_history.append(pattern)
            
            self.logger.info(f"✅ ตรวจจับ Patterns เสร็จสิ้น - พบทั้งหมด: {len(scored_patterns)}")
            
            return scored_patterns
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ Patterns: {e}")
            return []
    
    async def generate_signals_from_patterns(self, patterns: List[PatternData] = None) -> List[PatternSignal]:
        """
        สร้างสัญญาณจาก Patterns
        
        Args:
            patterns: รายการ Patterns (ถ้าไม่ระบุจะใช้ที่ตรวจพบล่าสุด)
            
        Returns:
            List[PatternSignal]: รายการสัญญาณ
        """
        try:
            if patterns is None:
                # ใช้ Patterns ที่ตรวจพบใน 1 ชั่วโมงล่าสุด
                cutoff_time = datetime.now() - timedelta(hours=1)
                patterns = [p for p in self.pattern_history 
                            if p.detected_at >= cutoff_time]
            
            signals = []
            market_context = await self._get_current_market_context()
            
            for pattern in patterns:
                # ดึงข้อมูลประสิทธิภาพ
                performance_data = self.performance_tracker.get_pattern_performance(pattern.pattern_type)
                
                # สร้างสัญญาณ
                signal = self.signal_generator.generate_signal_from_pattern(
                    pattern, market_context, performance_data
                )
                
                if signal:
                    signals.append(signal)
            
            self.logger.info(f"📡 สร้างสัญญาณจาก Patterns: {len(signals)} สัญญาณ")
            
            return signals
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้างสัญญาณ: {e}")
            return []
    
    def track_pattern_outcome(self, pattern_id: str, actual_result: Dict[str, Any]) -> None:
        """
        ติดตามผลลัพธ์ของ Pattern
        
        Args:
            pattern_id: ID ของ Pattern
            actual_result: ผลลัพธ์จริงที่เกิดขึ้น
        """
        try:
            pattern = self.detected_patterns.get(pattern_id)
            if not pattern:
                self.logger.warning(f"⚠️ ไม่พบ Pattern ID: {pattern_id}")
                return
            
            # ติดตามประสิทธิภาพ
            self.performance_tracker.track_pattern_performance(pattern, actual_result)
            
            self.logger.info(f"📊 บันทึกผลลัพธ์ Pattern: {pattern_id}")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการติดตามผลลัพธ์: {e}")
    
    def get_pattern_performance_summary(self) -> Dict[str, Any]:
        """ดึงสรุปประสิทธิภาพของ Patterns"""
        try:
            all_performances = self.performance_tracker.get_all_pattern_performances()
            top_patterns = self.performance_tracker.get_top_performing_patterns(10)
            
            summary = {
                "total_pattern_types": len(all_performances),
                "total_detections": len(self.pattern_history),
                "active_signals": len(self.signal_generator.get_active_signals()),
                "top_performing_patterns": [
                    {
                        "pattern_type": pattern_type.value,
                        "success_rate": performance.success_rate,
                        "total_occurrences": performance.total_occurrences,
                        "average_pips": performance.average_pips_per_trade
                    }
                    for pattern_type, performance in top_patterns
                ],
                "pattern_distribution": {
                    pattern_type.value: len([p for p in self.pattern_history if p.pattern_type == pattern_type])
                    for pattern_type in PatternType
                }
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงสรุปประสิทธิภาพ: {e}")
            return {}
    
    def _filter_duplicate_patterns(self, patterns: List[PatternData]) -> List[PatternData]:
        """กรอง Patterns ที่ซ้ำกัน"""
        try:
            unique_patterns = []
            seen_combinations = set()
            
            for pattern in patterns:
                # สร้าง signature ของ pattern
                signature = (
                    pattern.pattern_type,
                    pattern.timeframe,
                    round(pattern.pattern_strength, 1),
                    pattern.start_time.replace(second=0, microsecond=0) if pattern.start_time else None
                )
                
                if signature not in seen_combinations:
                    unique_patterns.append(pattern)
                    seen_combinations.add(signature)
            
            return unique_patterns
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการกรอง Duplicate Patterns: {e}")
            return patterns
    
    async def _add_market_context(self, patterns: List[PatternData]) -> List[PatternData]:
        """เพิ่มข้อมูล Market Context ให้กับ Patterns"""
        try:
            market_context = await self._get_current_market_context()
            
            for pattern in patterns:
                pattern.market_session = MarketSession(market_context.get('current_session', 'ASIAN'))
                pattern.market_condition = market_context.get('market_state', 'UNKNOWN')
                
                # เพิ่มข้อมูลข่าว
                if market_context.get('news_impact', 'NONE') != 'NONE':
                    pattern.news_context = [market_context.get('news_impact')]
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเพิ่ม Market Context: {e}")
            return patterns
    
    def _calculate_reliability_scores(self, patterns: List[PatternData]) -> List[PatternData]:
        """คำนวณ Reliability Score ของ Patterns"""
        try:
            for pattern in patterns:
                score = 0.0
                
                # คะแนนจาก Pattern Strength
                score += pattern.pattern_strength * 0.4
                
                # คะแนนจาก Confidence Level
                confidence_scores = {
                    PatternConfidence.VERY_HIGH: 100,
                    PatternConfidence.HIGH: 80,
                    PatternConfidence.MEDIUM: 60,
                    PatternConfidence.LOW: 40,
                    PatternConfidence.VERY_LOW: 20
                }
                score += confidence_scores.get(pattern.confidence_level, 60) * 0.3
                
                # คะแนนจาก Success Probability
                score += pattern.success_probability * 100 * 0.3
                
                pattern.reliability_score = min(100.0, score)
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Reliability Score: {e}")
            return patterns
    
    async def _get_current_market_context(self) -> Dict[str, Any]:
        """ดึงข้อมูล Market Context ปัจจุบัน"""
        try:
            context = {
                'current_price': 1850.0,  # Default
                'current_session': 'LONDON',
                'market_state': 'TRENDING',
                'volatility': 1.2,
                'momentum': 0.1,
                'trend_direction': 'BULLISH',
                'news_impact': 'NONE'
            }
            
            if self.market_analyzer:
                market_data = self.market_analyzer.get_current_market_state()
                context.update(market_data)
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึง Market Context: {e}")
            return {'current_price': 1850.0, 'current_session': 'LONDON'}
    
    async def _start_pattern_detection(self) -> None:
        """เริ่ม Pattern Detection แบบต่อเนื่อง"""
        if self.detection_active:
            return
        
        self.detection_active = True
        self.detection_thread = threading.Thread(target=self._pattern_detection_loop, daemon=True)
        self.detection_thread.start()
        
        self.logger.info("🔄 เริ่ม Pattern Detection แบบต่อเนื่อง")
    
    def _pattern_detection_loop(self) -> None:
        """Pattern Detection Loop"""
        try:
            while self.detection_active:
                if self.pattern_queue:
                    # ดึงข้อมูลจาก Queue
                    detection_task = self.pattern_queue.popleft()
                    
                    # ประมวลผลการตรวจจับ
                    try:
                        result = asyncio.run(self.detect_patterns(
                            detection_task.get('price_data'),
                            detection_task.get('trade_history'),
                            detection_task.get('timeframe', PatternTimeframe.M15)
                        ))
                        
                        # Callback ถ้ามี
                        if detection_task.get('callback'):
                            detection_task['callback'](result)
                            
                    except Exception as e:
                        self.logger.error(f"❌ ข้อผิดพลาดในการประมวลผล Pattern Detection: {e}")
                
                time.sleep(5)  # รอ 5 วินาที
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Pattern Detection Loop: {e}")
        finally:
            self.detection_active = False
    
    def queue_pattern_detection(self, price_data: List[Dict[str, Any]] = None,
                                trade_history: List[Dict[str, Any]] = None,
                                timeframe: PatternTimeframe = PatternTimeframe.M15,
                                callback: Callable = None) -> None:
        """เพิ่มงานเข้า Pattern Detection Queue"""
        detection_task = {
            'price_data': price_data,
            'trade_history': trade_history,
            'timeframe': timeframe,
            'callback': callback,
            'queued_at': datetime.now()
        }
        
        self.pattern_queue.append(detection_task)
        self.logger.debug(f"📥 เพิ่มงานเข้า Pattern Detection Queue")
    
    def stop_pattern_detector(self) -> None:
        """หยุด Pattern Detector"""
        self.detection_active = False
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=5)
        
        self.logger.info("🛑 หยุด Pattern Detector")

# Global Pattern Detector Instance
_global_pattern_detector: Optional[PatternDetector] = None

def get_pattern_detector() -> PatternDetector:
    """
    ดึง Pattern Detector Instance (Singleton Pattern)
    
    Returns:
        PatternDetector: Instance ของ Pattern Detector
    """
    global _global_pattern_detector
    
    if _global_pattern_detector is None:
        _global_pattern_detector = PatternDetector()
    
    return _global_pattern_detector

# Utility Functions
async def quick_pattern_detection(price_data: List[Dict[str, Any]]) -> List[PatternData]:
    """
    ตรวจจับ Pattern แบบเร็ว
    
    Args:
        price_data: ข้อมูลราคา
        
    Returns:
        List[PatternData]: รายการ Patterns
    """
    detector = get_pattern_detector()
    return await detector.detect_patterns(price_data)

def create_mock_price_data(symbol: str = "XAUUSD", bars: int = 50, 
                         start_price: float = 1850.0) -> List[Dict[str, Any]]:
    """
    สร้างข้อมูลราคาจำลองสำหรับทดสอบ
    
    Args:
        symbol: ชื่อ Symbol
        bars: จำนวน Bars
        start_price: ราคาเริ่มต้น
        
    Returns:
        List[Dict]: ข้อมูลราคา OHLCV
    """
    import random
    
    price_data = []
    current_price = start_price
    base_time = datetime.now() - timedelta(minutes=bars * 5)
    
    for i in range(bars):
        # สร้างการเคลื่อนไหวแบบสุ่ม
        change_percent = random.uniform(-0.002, 0.002)  # ±0.2%
        price_change = current_price * change_percent
        
        open_price = current_price
        close_price = current_price + price_change
        
        high_price = max(open_price, close_price) + random.uniform(0, abs(price_change))
        low_price = min(open_price, close_price) - random.uniform(0, abs(price_change))
        
        volume = random.uniform(100, 1000)
        
        bar_data = {
            'timestamp': base_time + timedelta(minutes=i * 5),
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        }
        
        price_data.append(bar_data)
        current_price = close_price
    
    return price_data

if __name__ == "__main__":
    """
    ทดสอบ Pattern Detector System
    """
    import asyncio
    
    async def test_pattern_detector():
        """ทดสอบการทำงานของ Pattern Detector"""
        
        print("🧪 เริ่มทดสอบ Pattern Detector System")
        
        # เริ่มต้น Pattern Detector
        detector = get_pattern_detector()
        await detector.start_pattern_detector()
        
        try:
            # สร้างข้อมูลทดสอบ
            print("\n📊 สร้างข้อมูลทดสอบ...")
            price_data = create_mock_price_data("XAUUSD", 100, 1850.0)
            
            # สร้าง Trade History จำลอง
            trade_history = []
            base_time = datetime.now() - timedelta(hours=2)
            
            for i in range(10):
                trade = {
                    'trade_id': f"TEST_{i:03d}",
                    'entry_time': base_time + timedelta(minutes=i * 10),
                    'exit_time': base_time + timedelta(minutes=i * 10 + 5),
                    'direction': 'BUY' if i % 2 == 0 else 'SELL',
                    'entry_price': 1850.0 + random.uniform(-5, 5),
                    'volume': 0.01,
                    'pnl': random.uniform(-50, 100),
                    'duration': timedelta(minutes=random.randint(5, 30))
                }
                trade_history.append(trade)
            
            # ทดสอบการตรวจจับ Patterns
            print(f"\n🔍 ทดสอบการตรวจจับ Patterns...")
            patterns = await detector.detect_patterns(
                price_data=price_data,
                trade_history=trade_history,
                timeframe=PatternTimeframe.M5
            )
            
            print(f"   ตรวจพบ Patterns: {len(patterns)}")
            
            for pattern in patterns[:5]:  # แสดง 5 อันแรก
                print(f"   - {pattern.pattern_type.value}: Strength {pattern.pattern_strength:.1f}, "
                        f"Confidence {pattern.confidence_level.name}")
            
            # ทดสอบการสร้างสัญญาณ
            print(f"\n📡 ทดสอบการสร้างสัญญาณ...")
            signals = await detector.generate_signals_from_patterns(patterns)
            
            print(f"   สร้างสัญญาณ: {len(signals)}")
            
            for signal in signals[:3]:  # แสดง 3 อันแรก
                print(f"   - Signal {signal.signal_id}: {signal.direction} @ {signal.entry_price:.2f}")
                print(f"     Strength: {signal.signal_strength:.1f}, Targets: {signal.target_prices[:2]}")
            
            # ทดสอบการติดตามประสิทธิภาพ
            print(f"\n📊 ทดสอบการติดตามประสิทธิภาพ...")
            
            # จำลองผลลัพธ์
            for pattern in patterns[:3]:
                result = {
                    'success': random.choice([True, False]),
                    'pnl': random.uniform(-50, 150),
                    'pips_gained': random.uniform(-20, 50),
                    'duration': timedelta(minutes=random.randint(10, 120)),
                    'session': random.choice(list(MarketSession))
                }
                
                detector.track_pattern_outcome(pattern.pattern_id, result)
            
            # แสดงสรุปประสิทธิภาพ
            performance_summary = detector.get_pattern_performance_summary()
            print(f"\n📈 สรุปประสิทธิภาพ Pattern Detector:")
            print(json.dumps(performance_summary, indent=2, ensure_ascii=False, default=str))
            
            # ทดสอบ Queue System
            print(f"\n🔄 ทดสอบ Queue System...")
            
            def detection_callback(result):
                print(f"   📋 Queue Detection Complete: พบ {len(result)} patterns")
            
            # เพิ่มงานเข้า Queue
            detector.queue_pattern_detection(
                price_data=price_data[-50:],  # ข้อมูล 50 bars ล่าสุด
                timeframe=PatternTimeframe.M15,
                callback=detection_callback
            )
            
            # รอให้ประมวลผลเสร็จ
            await asyncio.sleep(3)
            
        finally:
            detector.stop_pattern_detector()
        
        print("\n✅ ทดสอบ Pattern Detector เสร็จสิ้น")
    
    # รันการทดสอบ
    asyncio.run(test_pattern_detector())