#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKET ANALYZER - Intelligent Market Analysis System
=================================================
ระบบวิเคราะห์ตลาดอัจฉริยะที่ปรับปรุงใหม่
เปลี่ยนจากการวิเคราะห์หลายแบบซับซ้อน เป็นระบบเดียวที่มีประสิทธิภาพ

🧠 หน้าที่หลัก:
- วิเคราะห์สภาพตลาดแบบ Real-time
- ตรวจจับ Market Condition อัตโนมัติ
- แนะนำ Entry Strategy และ Recovery Method
- Multi-timeframe Analysis (M1, M5, M15, H1)
- Session-based Analysis (Asian, London, NY)

✨ ปรับปรุงใหม่:
- รวม Logic ทั้งหมดในไฟล์เดียว (ไม่กระจาย)
- เงื่อนไขการวิเคราะห์ชัดเจนและง่าย
- ผลลัพธ์ที่เข้าใจง่าย
- Performance ที่ดีขึ้น
"""

import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import deque, defaultdict
import statistics

# Internal imports
from config.settings import get_system_settings, MarketSession
from config.trading_params import get_trading_parameters, EntryStrategy, RecoveryMethod
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity
from mt5_integration.mt5_connector import ensure_mt5_connection

class MarketCondition(Enum):
    """สภาพตลาดหลัก (ลดความซับซ้อน)"""
    TRENDING_STRONG = "TRENDING_STRONG"     # เทรนด์แรง - ใช้ Trend Following
    TRENDING_WEAK = "TRENDING_WEAK"         # เทรนด์อ่อน - ใช้ Trend + Grid
    RANGING_TIGHT = "RANGING_TIGHT"         # Range แคบ - ใช้ Scalping
    RANGING_WIDE = "RANGING_WIDE"           # Range กว้าง - ใช้ Mean Reversion
    VOLATILE_HIGH = "VOLATILE_HIGH"         # ผันแปรสูง - ใช้ Breakout False
    VOLATILE_NEWS = "VOLATILE_NEWS"         # ข่าวสำคัญ - ใช้ News Reaction
    UNKNOWN = "UNKNOWN"                     # ไม่ทราบ - รอสัญญาณ

class SessionType(Enum):
    """เซสชันการเทรด"""
    ASIAN = "ASIAN"         # 22:00-08:00 GMT+7
    LONDON = "LONDON"       # 15:00-00:00 GMT+7
    NEW_YORK = "NEW_YORK"   # 20:30-05:30 GMT+7
    OVERLAP = "OVERLAP"     # 20:30-00:00 GMT+7 (London + NY)
    QUIET = "QUIET"         # ช่วงเงียบ

@dataclass
class MarketMetrics:
    """ข้อมูล Market Metrics"""
    # Trend Metrics
    adx_value: float = 0.0
    ma_slope: float = 0.0
    trend_strength: float = 0.0
    trend_direction: str = "NEUTRAL"  # UP, DOWN, NEUTRAL
    
    # Volatility Metrics
    atr_value: float = 0.0
    atr_normalized: float = 0.0  # เทียบกับค่าเฉลี่ย 20 วัน
    bollinger_width: float = 0.0
    volatility_level: str = "NORMAL"  # LOW, NORMAL, HIGH, EXTREME
    
    # Price Action Metrics
    current_price: float = 0.0
    support_level: float = 0.0
    resistance_level: float = 0.0
    distance_from_ma: float = 0.0
    rsi_value: float = 50.0
    
    # Market Structure
    market_structure: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    momentum: float = 0.0
    volume_trend: str = "NORMAL"  # LOW, NORMAL, HIGH

@dataclass
class MarketAnalysis:
    """ผลการวิเคราะห์ตลาด"""
    timestamp: datetime = field(default_factory=datetime.now)
    symbol: str = "XAUUSD"
    
    # Market Condition
    primary_condition: MarketCondition = MarketCondition.UNKNOWN
    confidence_score: float = 0.0  # 0-100
    
    # Recommendations
    recommended_entry_strategy: EntryStrategy = EntryStrategy.SCALPING_ENGINE
    recommended_recovery_method: RecoveryMethod = RecoveryMethod.GRID_INTELLIGENT
    
    # Session Info
    current_session: SessionType = SessionType.QUIET
    session_characteristics: str = "Unknown"
    
    # Market Data
    metrics: MarketMetrics = field(default_factory=MarketMetrics)
    
    # Multi-timeframe Data
    timeframe_data: Dict[str, Dict] = field(default_factory=dict)
    
    # Trading Signals
    signal_strength: float = 0.0  # 0-100
    entry_timing: str = "WAIT"  # IMMEDIATE, WAIT, AVOID
    risk_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH

class SmartMarketAnalyzer:
    """
    🧠 Smart Market Analyzer - ระบบวิเคราะห์ตลาดอัจฉริยะ
    
    ระบบวิเคราะห์ที่ปรับปรุงใหม่ให้เรียบง่ายและมีประสิทธิภาพ
    """
    
    def __init__(self):
        self.logger = setup_component_logger("SmartMarketAnalyzer")
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Analysis State
        self.current_analysis: Optional[MarketAnalysis] = None
        self.analysis_history: deque = deque(maxlen=100)
        self.last_analysis_time = 0
        
        # Market Data Cache
        self.price_cache = {}
        self.indicator_cache = {}
        self.cache_expiry = 30  # seconds
        
        # Threading
        self.analysis_active = False
        self.analysis_thread: Optional[threading.Thread] = None
        self.analysis_lock = threading.Lock()
        
        # Configuration
        self.symbol = "XAUUSD"
        self.timeframes = ["M1", "M5", "M15", "H1"]
        self.analysis_interval = 30  # seconds
        
        # Thresholds (เงื่อนไขที่ชัดเจน)
        self.thresholds = {
            # ADX Thresholds
            'adx_trending_strong': 30.0,
            'adx_trending_weak': 20.0,
            'adx_ranging': 15.0,
            
            # ATR Thresholds (normalized)
            'atr_high_volatility': 1.5,
            'atr_normal_volatility': 1.0,
            'atr_low_volatility': 0.7,
            
            # RSI Thresholds
            'rsi_overbought': 70.0,
            'rsi_oversold': 30.0,
            
            # Confidence Thresholds
            'min_confidence': 60.0,
            'high_confidence': 80.0
        }
        
        self.logger.info("🧠 เริ่มต้น Smart Market Analyzer")
    
    def start_analysis(self) -> bool:
        """🚀 เริ่มการวิเคราะห์ตลาด"""
        if self.analysis_active:
            return True
        
        try:
            if not ensure_mt5_connection():
                self.logger.error("❌ ไม่สามารถเชื่อมต่อ MT5")
                return False
            
            self.analysis_active = True
            self.analysis_thread = threading.Thread(
                target=self._analysis_loop,
                daemon=True,
                name="MarketAnalysisLoop"
            )
            self.analysis_thread.start()
            
            self.logger.info("🚀 เริ่มการวิเคราะห์ตลาดแบบ Real-time")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเริ่มวิเคราะห์: {e}")
            return False
    
    def stop_analysis(self):
        """🛑 หยุดการวิเคราะห์ตลาด"""
        self.analysis_active = False
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=10.0)
        self.logger.info("🛑 หยุดการวิเคราะห์ตลาด")
    
    def _analysis_loop(self):
        """📊 Main Analysis Loop"""
        while self.analysis_active:
            try:
                current_time = time.time()
                
                # Check if need to analyze
                if current_time - self.last_analysis_time >= self.analysis_interval:
                    analysis = self.analyze_market_now()
                    if analysis:
                        with self.analysis_lock:
                            self.current_analysis = analysis
                            self.analysis_history.append(analysis)
                        
                        self.last_analysis_time = current_time
                        self.logger.debug(f"📊 Market Analysis: {analysis.primary_condition.value} (Confidence: {analysis.confidence_score:.1f}%)")
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self.logger.error(f"❌ Analysis Loop Error: {e}")
                time.sleep(10)
    
    @handle_trading_errors(ErrorCategory.MARKET_DATA, ErrorSeverity.MEDIUM)
    def analyze_market_now(self) -> Optional[MarketAnalysis]:
        """🎯 วิเคราะห์ตลาดทันที (Main Analysis Function)"""
        
        if not ensure_mt5_connection():
            return None
        
        try:
            # 1. Get Market Data
            market_data = self._get_market_data()
            if not market_data:
                return None
            
            # 2. Calculate Indicators
            indicators = self._calculate_indicators(market_data)
            
            # 3. Detect Market Condition
            condition, confidence = self._detect_market_condition(indicators)
            
            # 4. Get Session Info
            session = self._get_current_session()
            
            # 5. Generate Recommendations
            entry_strategy = self._recommend_entry_strategy(condition, session, indicators)
            recovery_method = self._recommend_recovery_method(condition, session)
            
            # 6. Calculate Signal Strength
            signal_strength, entry_timing = self._calculate_signal_strength(condition, indicators)
            
            # 7. Create Analysis Result
            analysis = MarketAnalysis(
                primary_condition=condition,
                confidence_score=confidence,
                recommended_entry_strategy=entry_strategy,
                recommended_recovery_method=recovery_method,
                current_session=session,
                signal_strength=signal_strength,
                entry_timing=entry_timing,
                metrics=self._create_market_metrics(indicators),
                timeframe_data=market_data
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ Market Analysis Error: {e}")
            return None
    
    def _get_market_data(self) -> Dict[str, pd.DataFrame]:
        """📈 ดึงข้อมูลตลาดทุก Timeframe"""
        market_data = {}
        
        try:
            for tf in self.timeframes:
                # Check cache first
                cache_key = f"{self.symbol}_{tf}"
                if (cache_key in self.price_cache and 
                    time.time() - self.price_cache[cache_key]['timestamp'] < self.cache_expiry):
                    market_data[tf] = self.price_cache[cache_key]['data']
                    continue
                
                # Get fresh data from MT5
                rates = mt5.copy_rates_from_pos(self.symbol, getattr(mt5, f"TIMEFRAME_{tf}"), 0, 100)
                if rates is not None and len(rates) > 0:
                    df = pd.DataFrame(rates)
                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    df.set_index('time', inplace=True)
                    
                    market_data[tf] = df
                    
                    # Cache the data
                    self.price_cache[cache_key] = {
                        'data': df,
                        'timestamp': time.time()
                    }
                else:
                    self.logger.warning(f"⚠️ ไม่สามารถดึงข้อมูล {tf} ได้")
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"❌ Get Market Data Error: {e}")
            return {}
    
    def _calculate_indicators(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """🔢 คำนวณ Technical Indicators"""
        indicators = {}
        
        try:
            # Use H1 data for main indicators
            if 'H1' not in market_data or market_data['H1'].empty:
                return indicators
            
            df = market_data['H1'].copy()
            
            # === TREND INDICATORS ===
            
            # ADX (Average Directional Index)
            indicators['adx'] = self._calculate_adx(df)
            
            # Moving Averages
            df['ma_20'] = df['close'].rolling(window=20).mean()
            df['ma_50'] = df['close'].rolling(window=50).mean()
            indicators['ma_20'] = df['ma_20'].iloc[-1] if not df['ma_20'].empty else 0
            indicators['ma_50'] = df['ma_50'].iloc[-1] if not df['ma_50'].empty else 0
            
            # MA Slope (Trend Direction)
            if len(df['ma_20']) >= 5:
                recent_ma = df['ma_20'].iloc[-5:].values
                indicators['ma_slope'] = np.polyfit(range(5), recent_ma, 1)[0]
            else:
                indicators['ma_slope'] = 0
            
            # === VOLATILITY INDICATORS ===
            
            # ATR (Average True Range)
            indicators['atr'] = self._calculate_atr(df)
            indicators['atr_normalized'] = self._normalize_atr(indicators['atr'], df)
            
            # Bollinger Bands
            bb_upper, bb_lower, bb_width = self._calculate_bollinger_bands(df)
            indicators['bb_width'] = bb_width
            
            # === MOMENTUM INDICATORS ===
            
            # RSI
            indicators['rsi'] = self._calculate_rsi(df)
            
            # === PRICE ACTION ===
            
            current_price = df['close'].iloc[-1]
            indicators['current_price'] = current_price
            indicators['distance_from_ma'] = (current_price - indicators['ma_20']) / indicators['ma_20'] * 100
            
            # Support/Resistance (Simple)
            recent_highs = df['high'].iloc[-20:].rolling(window=5).max()
            recent_lows = df['low'].iloc[-20:].rolling(window=5).min()
            indicators['resistance'] = recent_highs.max()
            indicators['support'] = recent_lows.min()
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"❌ Calculate Indicators Error: {e}")
            return {}
    
    def _detect_market_condition(self, indicators: Dict[str, Any]) -> Tuple[MarketCondition, float]:
        """🎯 ตรวจจับสภาพตลาด (หัวใจหลัก)"""
        
        if not indicators:
            return MarketCondition.UNKNOWN, 0.0
        
        # Get key indicators
        adx = indicators.get('adx', 0)
        atr_norm = indicators.get('atr_normalized', 1.0)
        rsi = indicators.get('rsi', 50)
        ma_slope = indicators.get('ma_slope', 0)
        bb_width = indicators.get('bb_width', 0)
        
        condition_scores = {}
        
        # === TRENDING CONDITIONS ===
        
        # Strong Trend: ADX > 30, clear MA slope, normal/high volatility
        if (adx > self.thresholds['adx_trending_strong'] and 
            abs(ma_slope) > 0.05 and 
            atr_norm >= self.thresholds['atr_normal_volatility']):
            
            score = min(100, adx + abs(ma_slope) * 100 + atr_norm * 10)
            condition_scores[MarketCondition.TRENDING_STRONG] = score
        
        # Weak Trend: ADX 20-30, some MA slope
        elif (self.thresholds['adx_trending_weak'] < adx <= self.thresholds['adx_trending_strong'] and
              abs(ma_slope) > 0.02):
            
            score = adx + abs(ma_slope) * 50 + 20
            condition_scores[MarketCondition.TRENDING_WEAK] = score
        
        # === RANGING CONDITIONS ===
        
        # Tight Range: Low ADX, low volatility, narrow BB
        if (adx < self.thresholds['adx_ranging'] and 
            atr_norm < self.thresholds['atr_low_volatility'] and
            bb_width < 0.001):
            
            score = (20 - adx) + (1.0 - atr_norm) * 30 + 30
            condition_scores[MarketCondition.RANGING_TIGHT] = score
        
        # Wide Range: Low ADX, normal volatility, wide BB
        elif (adx < self.thresholds['adx_trending_weak'] and 
              atr_norm >= self.thresholds['atr_normal_volatility'] and
              bb_width > 0.002):
            
            score = (25 - adx) + atr_norm * 20 + bb_width * 10000
            condition_scores[MarketCondition.RANGING_WIDE] = score
        
        # === VOLATILE CONDITIONS ===
        
        # High Volatility: High ATR, wide BB, extreme RSI
        if (atr_norm > self.thresholds['atr_high_volatility'] and
            (rsi > 80 or rsi < 20)):
            
            score = atr_norm * 30 + abs(rsi - 50) + bb_width * 5000
            condition_scores[MarketCondition.VOLATILE_HIGH] = score
        
        # News Volatility: Extreme ATR spike
        if atr_norm > 2.0:
            score = atr_norm * 40
            condition_scores[MarketCondition.VOLATILE_NEWS] = score
        
        # Select best condition
        if condition_scores:
            best_condition = max(condition_scores, key=condition_scores.get)
            confidence = min(100, condition_scores[best_condition])
            return best_condition, confidence
        else:
            return MarketCondition.UNKNOWN, 0.0
    
    def _recommend_entry_strategy(self, condition: MarketCondition, session: SessionType, 
                                indicators: Dict[str, Any]) -> EntryStrategy:
        """🎯 แนะนำ Entry Strategy"""
        
        # Strategy mapping based on condition and session
        strategy_map = {
            MarketCondition.TRENDING_STRONG: {
                SessionType.LONDON: EntryStrategy.TREND_FOLLOWING,
                SessionType.NEW_YORK: EntryStrategy.TREND_FOLLOWING,
                SessionType.OVERLAP: EntryStrategy.TREND_FOLLOWING,
                SessionType.ASIAN: EntryStrategy.TREND_FOLLOWING,
                SessionType.QUIET: EntryStrategy.SCALPING_ENGINE
            },
            MarketCondition.TRENDING_WEAK: {
                SessionType.LONDON: EntryStrategy.TREND_FOLLOWING,
                SessionType.NEW_YORK: EntryStrategy.MEAN_REVERSION,
                SessionType.OVERLAP: EntryStrategy.TREND_FOLLOWING,
                SessionType.ASIAN: EntryStrategy.SCALPING_ENGINE,
                SessionType.QUIET: EntryStrategy.SCALPING_ENGINE
            },
            MarketCondition.RANGING_TIGHT: {
                SessionType.LONDON: EntryStrategy.SCALPING_ENGINE,
                SessionType.NEW_YORK: EntryStrategy.SCALPING_ENGINE,
                SessionType.OVERLAP: EntryStrategy.MEAN_REVERSION,
                SessionType.ASIAN: EntryStrategy.SCALPING_ENGINE,
                SessionType.QUIET: EntryStrategy.SCALPING_ENGINE
            },
            MarketCondition.RANGING_WIDE: {
                SessionType.LONDON: EntryStrategy.MEAN_REVERSION,
                SessionType.NEW_YORK: EntryStrategy.MEAN_REVERSION,
                SessionType.OVERLAP: EntryStrategy.MEAN_REVERSION,
                SessionType.ASIAN: EntryStrategy.MEAN_REVERSION,
                SessionType.QUIET: EntryStrategy.SCALPING_ENGINE
            },
            MarketCondition.VOLATILE_HIGH: {
                SessionType.LONDON: EntryStrategy.BREAKOUT_FALSE,
                SessionType.NEW_YORK: EntryStrategy.BREAKOUT_FALSE,
                SessionType.OVERLAP: EntryStrategy.BREAKOUT_FALSE,
                SessionType.ASIAN: EntryStrategy.SCALPING_ENGINE,
                SessionType.QUIET: EntryStrategy.SCALPING_ENGINE
            },
            MarketCondition.VOLATILE_NEWS: {
                SessionType.LONDON: EntryStrategy.NEWS_REACTION,
                SessionType.NEW_YORK: EntryStrategy.NEWS_REACTION,
                SessionType.OVERLAP: EntryStrategy.NEWS_REACTION,
                SessionType.ASIAN: EntryStrategy.NEWS_REACTION,
                SessionType.QUIET: EntryStrategy.SCALPING_ENGINE
            }
        }
        
        return strategy_map.get(condition, {}).get(session, EntryStrategy.SCALPING_ENGINE)
    
    def _recommend_recovery_method(self, condition: MarketCondition, session: SessionType) -> RecoveryMethod:
        """🔄 แนะนำ Recovery Method"""
        
        # Recovery method mapping
        recovery_map = {
            MarketCondition.TRENDING_STRONG: RecoveryMethod.GRID_INTELLIGENT,
            MarketCondition.TRENDING_WEAK: RecoveryMethod.AVERAGING_INTELLIGENT,
            MarketCondition.RANGING_TIGHT: RecoveryMethod.MARTINGALE_SMART,
            MarketCondition.RANGING_WIDE: RecoveryMethod.AVERAGING_INTELLIGENT,
            MarketCondition.VOLATILE_HIGH: RecoveryMethod.HEDGING_ADVANCED,
            MarketCondition.VOLATILE_NEWS: RecoveryMethod.HEDGING_ADVANCED
        }
        
        return recovery_map.get(condition, RecoveryMethod.GRID_INTELLIGENT)
    
    def _get_current_session(self) -> SessionType:
        """🕐 ตรวจสอบ Session ปัจจุบัน"""
        now = datetime.now()
        hour = now.hour
        
        # GMT+7 Time
        if 22 <= hour or hour < 8:  # 22:00-08:00
            return SessionType.ASIAN
        elif 15 <= hour < 20:       # 15:00-20:00 (London only)
            return SessionType.LONDON
        elif 20 <= hour < 22:       # 20:00-22:00 (Overlap)
            return SessionType.OVERLAP
        elif 20 <= hour or hour < 5:  # 20:30-05:30 (NY included)
            return SessionType.NEW_YORK
        else:
            return SessionType.QUIET
    
    def _calculate_signal_strength(self, condition: MarketCondition, 
                                 indicators: Dict[str, Any]) -> Tuple[float, str]:
        """📊 คำนวณความแรงของสัญญาณ"""
        
        base_strength = {
            MarketCondition.TRENDING_STRONG: 80,
            MarketCondition.TRENDING_WEAK: 60,
            MarketCondition.RANGING_TIGHT: 70,
            MarketCondition.RANGING_WIDE: 65,
            MarketCondition.VOLATILE_HIGH: 50,
            MarketCondition.VOLATILE_NEWS: 40,
            MarketCondition.UNKNOWN: 20
        }.get(condition, 20)
        
        # Adjust based on indicators
        adx = indicators.get('adx', 0)
        rsi = indicators.get('rsi', 50)
        
        # ADX boost
        if adx > 30:
            base_strength += 10
        elif adx < 15:
            base_strength -= 10
        
        # RSI adjustment
        if 30 < rsi < 70:  # Good range
            base_strength += 5
        elif rsi > 80 or rsi < 20:  # Extreme
            base_strength -= 15
        
        signal_strength = max(0, min(100, base_strength))
        
        # Entry timing
        if signal_strength > 75:
            entry_timing = "IMMEDIATE"
        elif signal_strength > 50:
            entry_timing = "WAIT"
        else:
            entry_timing = "AVOID"
        
        return signal_strength, entry_timing
    
    def _create_market_metrics(self, indicators: Dict[str, Any]) -> MarketMetrics:
        """📈 สร้าง Market Metrics"""
        return MarketMetrics(
            adx_value=indicators.get('adx', 0),
            ma_slope=indicators.get('ma_slope', 0),
            atr_value=indicators.get('atr', 0),
            atr_normalized=indicators.get('atr_normalized', 1.0),
            bollinger_width=indicators.get('bb_width', 0),
            current_price=indicators.get('current_price', 0),
            support_level=indicators.get('support', 0),
            resistance_level=indicators.get('resistance', 0),
            distance_from_ma=indicators.get('distance_from_ma', 0),
            rsi_value=indicators.get('rsi', 50)
        )
    
    # === TECHNICAL INDICATOR CALCULATIONS ===
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """คำนวณ ADX"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            # True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Directional Movement
            dm_plus = np.where((high - high.shift(1)) > (low.shift(1) - low), 
                              np.maximum(high - high.shift(1), 0), 0)
            dm_minus = np.where((low.shift(1) - low) > (high - high.shift(1)), 
                               np.maximum(low.shift(1) - low, 0), 0)
            
            # Smoothed values
            tr_smooth = pd.Series(tr).rolling(window=period).mean()
            dm_plus_smooth = pd.Series(dm_plus).rolling(window=period).mean()
            dm_minus_smooth = pd.Series(dm_minus).rolling(window=period).mean()
            
            # DI values
            di_plus = 100 * dm_plus_smooth / tr_smooth
            di_minus = 100 * dm_minus_smooth / tr_smooth
            
            # ADX
            dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
            adx = dx.rolling(window=period).mean()
            
            return adx.iloc[-1] if not adx.empty else 0.0
            
        except Exception as e:
            self.logger.error(f"❌ ADX Calculation Error: {e}")
            return 0.0
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """คำนวณ ATR"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            atr = tr.rolling(window=period).mean()
            return atr.iloc[-1] if not atr.empty else 0.0
            
        except Exception as e:
            self.logger.error(f"❌ ATR Calculation Error: {e}")
            return 0.0
    
    def _normalize_atr(self, current_atr: float, df: pd.DataFrame, period: int = 20) -> float:
        """Normalize ATR เทียบกับค่าเฉลี่ย"""
        try:
            atr_series = []
            for i in range(len(df) - period, len(df)):
                if i < 14:  # Need minimum data for ATR
                    continue
                subset = df.iloc[max(0, i-13):i+1]
                atr_val = self._calculate_atr(subset)
                if atr_val > 0:
                    atr_series.append(atr_val)
            
            if atr_series:
                avg_atr = np.mean(atr_series)
                return current_atr / avg_atr if avg_atr > 0 else 1.0
            else:
                return 1.0
                
        except Exception as e:
            self.logger.error(f"❌ ATR Normalization Error: {e}")
            return 1.0
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """คำนวณ RSI"""
        try:
            close = df['close']
            delta = close.diff()
            
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1] if not rsi.empty else 50.0
            
        except Exception as e:
            self.logger.error(f"❌ RSI Calculation Error: {e}")
            return 50.0
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, 
                                 std_dev: int = 2) -> Tuple[float, float, float]:
        """คำนวณ Bollinger Bands"""
        try:
            close = df['close']
            sma = close.rolling(window=period).mean()
            std = close.rolling(window=period).std()
            
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            
            # Band width (normalized)
            width = (upper.iloc[-1] - lower.iloc[-1]) / sma.iloc[-1] if not sma.empty else 0
            
            return upper.iloc[-1], lower.iloc[-1], width
            
        except Exception as e:
            self.logger.error(f"❌ Bollinger Bands Calculation Error: {e}")
            return 0.0, 0.0, 0.0
    
    # === PUBLIC METHODS ===
    
    def get_current_analysis(self) -> Optional[MarketAnalysis]:
        """ดึงการวิเคราะห์ปัจจุบัน"""
        with self.analysis_lock:
            return self.current_analysis
    
    def get_analysis_history(self, count: int = 10) -> List[MarketAnalysis]:
        """ดึงประวัติการวิเคราะห์"""
        with self.analysis_lock:
            return list(self.analysis_history)[-count:]
    
    def force_analysis(self) -> Optional[MarketAnalysis]:
        """บังคับให้วิเคราะห์ทันที"""
        return self.analyze_market_now()
    
    def get_market_summary(self) -> Dict[str, Any]:
        """ดึงสรุปสภาพตลาด"""
        analysis = self.get_current_analysis()
        if not analysis:
            return {"status": "No analysis available"}
        
        return {
            "condition": analysis.primary_condition.value,
            "confidence": analysis.confidence_score,
            "entry_strategy": analysis.recommended_entry_strategy.value,
            "recovery_method": analysis.recommended_recovery_method.value,
            "signal_strength": analysis.signal_strength,
            "entry_timing": analysis.entry_timing,
            "session": analysis.current_session.value,
            "timestamp": analysis.timestamp.isoformat(),
            "price": analysis.metrics.current_price,
            "trend": "UP" if analysis.metrics.ma_slope > 0 else "DOWN" if analysis.metrics.ma_slope < 0 else "NEUTRAL",
            "volatility": analysis.metrics.volatility_level
        }
    
    def is_good_time_to_trade(self) -> Tuple[bool, str]:
        """ตรวจสอบว่าเป็นเวลาที่ดีในการเทรดหรือไม่"""
        analysis = self.get_current_analysis()
        if not analysis:
            return False, "No market analysis available"
        
        # Check confidence
        if analysis.confidence_score < self.thresholds['min_confidence']:
            return False, f"Low confidence: {analysis.confidence_score:.1f}%"
        
        # Check entry timing
        if analysis.entry_timing == "AVOID":
            return False, "Market conditions suggest avoiding trades"
        
        # Check signal strength
        if analysis.signal_strength < 50:
            return False, f"Weak signal strength: {analysis.signal_strength:.1f}%"
        
        # Check market condition
        if analysis.primary_condition == MarketCondition.UNKNOWN:
            return False, "Unknown market condition"
        
        return True, f"Good time to trade: {analysis.primary_condition.value}"
    
    def get_recommended_strategy(self) -> Tuple[EntryStrategy, RecoveryMethod, float]:
        """ดึงกลยุทธ์ที่แนะนำ"""
        analysis = self.get_current_analysis()
        if not analysis:
            return EntryStrategy.SCALPING_ENGINE, RecoveryMethod.GRID_INTELLIGENT, 0.0
        
        return (analysis.recommended_entry_strategy, 
                analysis.recommended_recovery_method, 
                analysis.confidence_score)
    
    def get_market_risk_level(self) -> str:
        """ดึงระดับความเสี่ยงของตลาด"""
        analysis = self.get_current_analysis()
        if not analysis:
            return "UNKNOWN"
        
        # Risk based on condition and volatility
        if analysis.primary_condition in [MarketCondition.VOLATILE_HIGH, MarketCondition.VOLATILE_NEWS]:
            return "HIGH"
        elif analysis.primary_condition in [MarketCondition.TRENDING_STRONG, MarketCondition.RANGING_WIDE]:
            return "MEDIUM"
        elif analysis.primary_condition in [MarketCondition.RANGING_TIGHT, MarketCondition.TRENDING_WEAK]:
            return "LOW"
        else:
            return "UNKNOWN"
    
    def should_use_recovery(self) -> Tuple[bool, RecoveryMethod]:
        """ตรวจสอบว่าควรใช้ Recovery หรือไม่"""
        analysis = self.get_current_analysis()
        if not analysis:
            return True, RecoveryMethod.GRID_INTELLIGENT
        
        # Recovery is always recommended (no stop loss system)
        return True, analysis.recommended_recovery_method
    
    def get_session_characteristics(self) -> Dict[str, str]:
        """ดึงลักษณะของ Session ปัจจุบัน"""
        session = self._get_current_session()
        
        characteristics = {
            SessionType.ASIAN: {
                "volatility": "LOW",
                "trend_strength": "WEAK",
                "best_strategy": "SCALPING",
                "characteristics": "Range-bound, low volatility, good for scalping"
            },
            SessionType.LONDON: {
                "volatility": "HIGH",
                "trend_strength": "STRONG",
                "best_strategy": "TREND_FOLLOWING",
                "characteristics": "High volatility, strong trends, breakout opportunities"
            },
            SessionType.NEW_YORK: {
                "volatility": "VERY_HIGH",
                "trend_strength": "STRONG",
                "best_strategy": "NEWS_REACTION",
                "characteristics": "Highest volume, news reactions, strong movements"
            },
            SessionType.OVERLAP: {
                "volatility": "EXTREME",
                "trend_strength": "VERY_STRONG",
                "best_strategy": "BREAKOUT",
                "characteristics": "Maximum volatility, false breakouts, extreme movements"
            },
            SessionType.QUIET: {
                "volatility": "VERY_LOW",
                "trend_strength": "MINIMAL",
                "best_strategy": "AVOID",
                "characteristics": "Very low activity, avoid trading"
            }
        }
        
        return characteristics.get(session, {
            "volatility": "UNKNOWN",
            "trend_strength": "UNKNOWN",
            "best_strategy": "SCALPING",
            "characteristics": "Unknown session characteristics"
        })


# === SINGLETON PATTERN ===

_market_analyzer_instance = None

def get_market_analyzer() -> SmartMarketAnalyzer:
    """Get Market Analyzer Singleton Instance"""
    global _market_analyzer_instance
    if _market_analyzer_instance is None:
        _market_analyzer_instance = SmartMarketAnalyzer()
    return _market_analyzer_instance


# === UTILITY FUNCTIONS ===

def quick_market_check() -> Dict[str, Any]:
    """ตรวจสอบตลาดอย่างรวดเร็ว"""
    analyzer = get_market_analyzer()
    
    # Force immediate analysis
    analysis = analyzer.force_analysis()
    if not analysis:
        return {"status": "error", "message": "Cannot analyze market"}
    
    return {
        "status": "success",
        "condition": analysis.primary_condition.value,
        "confidence": analysis.confidence_score,
        "signal_strength": analysis.signal_strength,
        "entry_timing": analysis.entry_timing,
        "recommended_strategy": analysis.recommended_entry_strategy.value,
        "session": analysis.current_session.value,
        "timestamp": analysis.timestamp.isoformat()
    }

def is_market_suitable_for_entry() -> bool:
    """ตรวจสอบว่าตลาดเหมาะสำหรับการเข้าออร์เดอร์หรือไม่"""
    analyzer = get_market_analyzer()
    suitable, reason = analyzer.is_good_time_to_trade()
    return suitable

def get_current_market_condition() -> str:
    """ดึงสภาพตลาดปัจจุบัน"""
    analyzer = get_market_analyzer()
    analysis = analyzer.get_current_analysis()
    
    if analysis:
        return analysis.primary_condition.value
    else:
        return "UNKNOWN"

def get_recommended_entry_strategy() -> str:
    """ดึงกลยุทธ์การเข้าที่แนะนำ"""
    analyzer = get_market_analyzer()
    strategy, recovery, confidence = analyzer.get_recommended_strategy()
    return strategy.value