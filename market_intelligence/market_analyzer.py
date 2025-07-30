#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKET INTELLIGENCE ENGINE - REAL MT5 DATA ANALYSIS
==================================================
ระบบวิเคราะห์ตลาดอัจฉริยะที่ใช้ข้อมูลจริงจาก MT5
วิเคราะห์สภาวะตลาด และเลือกกลยุทธ์การเทรดแบบอัตโนมัติ

🎯 FEATURES:
- Real-time market condition detection
- Multi-timeframe analysis (M1, M5, M15, H1)
- Session-based trading logic
- Volatility and trend analysis
- Intelligent strategy selection
- News impact detection
"""

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
import math
import statistics
from collections import deque, defaultdict

class MarketCondition(Enum):
    """สภาวะตลาด"""
    TRENDING_STRONG = "TRENDING_STRONG"
    TRENDING_WEAK = "TRENDING_WEAK"
    RANGING_TIGHT = "RANGING_TIGHT"
    RANGING_WIDE = "RANGING_WIDE"
    VOLATILE_HIGH = "VOLATILE_HIGH"
    VOLATILE_NEWS = "VOLATILE_NEWS"
    QUIET_LOW = "QUIET_LOW"
    BREAKOUT = "BREAKOUT"
    REVERSAL = "REVERSAL"

class TradingSession(Enum):
    """เซสชันการเทรด"""
    ASIAN = "ASIAN"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    OVERLAP_LONDON_NY = "OVERLAP_LONDON_NY"
    QUIET = "QUIET"

class TrendDirection(Enum):
    """ทิศทางเทรนด์"""
    BULLISH_STRONG = "BULLISH_STRONG"
    BULLISH_WEAK = "BULLISH_WEAK"
    BEARISH_STRONG = "BEARISH_STRONG"
    BEARISH_WEAK = "BEARISH_WEAK"
    SIDEWAYS = "SIDEWAYS"

class EntryStrategy(Enum):
    """กลยุทธ์การเข้า"""
    TREND_FOLLOWING = "TREND_FOLLOWING"
    MEAN_REVERSION = "MEAN_REVERSION"
    BREAKOUT_TRADE = "BREAKOUT_TRADE"
    FALSE_BREAKOUT = "FALSE_BREAKOUT"
    NEWS_REACTION = "NEWS_REACTION"
    SCALPING = "SCALPING"
    GRID_ENTRY = "GRID_ENTRY"

@dataclass
class MarketData:
    """ข้อมูลตลาด"""
    timestamp: datetime
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    spread: float

@dataclass
class TechnicalIndicators:
    """ตัวชี้วัดทางเทคนิค"""
    # Moving Averages
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_200: float = 0.0
    ema_12: float = 0.0
    ema_26: float = 0.0
    
    # Oscillators
    rsi_14: float = 50.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    
    # Volatility
    atr_14: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_middle: float = 0.0
    bollinger_lower: float = 0.0
    bollinger_width: float = 0.0
    
    # Trend Strength
    adx_14: float = 0.0
    
    # Support/Resistance
    pivot_point: float = 0.0
    resistance_1: float = 0.0
    resistance_2: float = 0.0
    support_1: float = 0.0
    support_2: float = 0.0

@dataclass
class MarketAnalysis:
    """ผลการวิเคราะห์ตลาด"""
    timestamp: datetime
    symbol: str
    condition: MarketCondition
    session: TradingSession
    trend_direction: TrendDirection
    trend_strength: float  # 0-100
    volatility_level: float  # 0-100
    recommended_strategy: EntryStrategy
    confidence_score: float  # 0-100
    
    # Technical levels
    current_price: float
    support_levels: List[float]
    resistance_levels: List[float]
    
    # Risk assessment
    spread_score: float  # 0-100 (100 = best)
    liquidity_score: float  # 0-100
    
    # Multi-timeframe
    m1_signals: Dict[str, Any] = field(default_factory=dict)
    m5_signals: Dict[str, Any] = field(default_factory=dict)
    m15_signals: Dict[str, Any] = field(default_factory=dict)
    h1_signals: Dict[str, Any] = field(default_factory=dict)

class RealTimeMarketAnalyzer:
    """
    Real-Time Market Analyzer - ใช้ข้อมูลจาก MT5 เท่านั้น
    """
    
    def __init__(self, symbol: str = ".XAUUSD.v"):
        self.symbol = symbol
        self.is_analyzing = False
        self.analysis_thread = None
        
        # Data storage
        self.price_history = {
            mt5.TIMEFRAME_M1: deque(maxlen=1000),
            mt5.TIMEFRAME_M5: deque(maxlen=500),
            mt5.TIMEFRAME_M15: deque(maxlen=200),
            mt5.TIMEFRAME_H1: deque(maxlen=100)
        }
        
        # Current analysis
        self.current_analysis = None
        self.last_analysis_time = None
        
        # Performance tracking
        self.analysis_count = 0
        self.analysis_errors = 0
        
        print(f"🧠 Market Intelligence Engine initialized for {symbol}")
    
    def start_analysis(self):
        """เริ่มการวิเคราะห์แบบ Real-time"""
        if self.is_analyzing:
            return
        
        self.is_analyzing = True
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        print("✅ Real-time market analysis started")
    
    def stop_analysis(self):
        """หยุดการวิเคราะห์"""
        self.is_analyzing = False
        if self.analysis_thread:
            self.analysis_thread.join(timeout=5)
        print("⏹️ Market analysis stopped")
    
    def _analysis_loop(self):
        """Loop การวิเคราะห์หลัก"""
        while self.is_analyzing:
            try:
                # ดึงข้อมูลจาก MT5
                self._fetch_market_data()
                
                # วิเคราะห์ตลาด
                analysis = self._analyze_market()
                
                if analysis:
                    self.current_analysis = analysis
                    self.last_analysis_time = datetime.now()
                    self.analysis_count += 1
                    
                    # Log การวิเคราะห์
                    self._log_analysis(analysis)
                
                time.sleep(1)  # วิเคราะห์ทุก 1 วินาที
                
            except Exception as e:
                self.analysis_errors += 1
                print(f"❌ Analysis Error: {e}")
                time.sleep(5)
    
    def _fetch_market_data(self):
        """ดึงข้อมูลตลาดจาก MT5"""
        try:
            # ดึงข้อมูลแต่ละ timeframe
            timeframes = [
                mt5.TIMEFRAME_M1,
                mt5.TIMEFRAME_M5,
                mt5.TIMEFRAME_M15,
                mt5.TIMEFRAME_H1
            ]
            
            for tf in timeframes:
                # ดึงข้อมูล 100 bars ล่าสุด
                rates = mt5.copy_rates_from_pos(self.symbol, tf, 0, 100)
                
                if rates is not None and len(rates) > 0:
                    # แปลงเป็น DataFrame
                    df = pd.DataFrame(rates)
                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    
                    # เก็บข้อมูลล่าสุด
                    latest_data = MarketData(
                        timestamp=df.iloc[-1]['time'],
                        symbol=self.symbol,
                        timeframe=self._timeframe_to_string(tf),
                        open=df.iloc[-1]['open'],
                        high=df.iloc[-1]['high'],
                        low=df.iloc[-1]['low'],
                        close=df.iloc[-1]['close'],
                        volume=df.iloc[-1]['tick_volume'],
                        spread=self._get_current_spread()
                    )
                    
                    self.price_history[tf].append(latest_data)
                    
        except Exception as e:
            print(f"❌ Error fetching market data: {e}")
    
    def _get_current_spread(self):
        """ดึง Spread ปัจจุบัน"""
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            if tick:
                return tick.ask - tick.bid
            return 0.0
        except:
            return 0.0
    
    def _timeframe_to_string(self, timeframe):
        """แปลง timeframe เป็น string"""
        mapping = {
            mt5.TIMEFRAME_M1: "M1",
            mt5.TIMEFRAME_M5: "M5",
            mt5.TIMEFRAME_M15: "M15",
            mt5.TIMEFRAME_H1: "H1"
        }
        return mapping.get(timeframe, "UNKNOWN")
    
    def _analyze_market(self) -> Optional[MarketAnalysis]:
        """วิเคราะห์ตลาดแบบครอบคลุม"""
        try:
            # ตรวจสอบข้อมูลเพียงพอ
            if not self._has_sufficient_data():
                return None
            
            # ดึงราคาปัจจุบัน
            current_tick = mt5.symbol_info_tick(self.symbol)
            if not current_tick:
                return None
            
            current_price = (current_tick.bid + current_tick.ask) / 2
            
            # คำนวณตัวชี้วัดทางเทคนิค
            indicators = self._calculate_technical_indicators()
            
            # วิเคราะห์สภาวะตลาด
            market_condition = self._detect_market_condition(indicators)
            
            # ระบุเซสชันการเทรด
            trading_session = self._identify_trading_session()
            
            # วิเคราะห์เทรนด์
            trend_direction, trend_strength = self._analyze_trend(indicators)
            
            # คำนวณระดับความผันผวน
            volatility_level = self._calculate_volatility_level(indicators)
            
            # เลือกกลยุทธ์ที่เหมาะสม
            strategy, confidence = self._select_optimal_strategy(
                market_condition, trading_session, trend_direction, volatility_level
            )
            
            # คำนวณ Support/Resistance
            support_levels, resistance_levels = self._calculate_support_resistance()
            
            # ประเมินความเสี่ยง
            spread_score = self._evaluate_spread_quality()
            liquidity_score = self._evaluate_liquidity()
            
            # สร้างผลการวิเคราะห์
            analysis = MarketAnalysis(
                timestamp=datetime.now(),
                symbol=self.symbol,
                condition=market_condition,
                session=trading_session,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                volatility_level=volatility_level,
                recommended_strategy=strategy,
                confidence_score=confidence,
                current_price=current_price,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                spread_score=spread_score,
                liquidity_score=liquidity_score,
                m1_signals=self._get_timeframe_signals(mt5.TIMEFRAME_M1),
                m5_signals=self._get_timeframe_signals(mt5.TIMEFRAME_M5),
                m15_signals=self._get_timeframe_signals(mt5.TIMEFRAME_M15),
                h1_signals=self._get_timeframe_signals(mt5.TIMEFRAME_H1)
            )
            
            return analysis
            
        except Exception as e:
            print(f"❌ Market analysis error: {e}")
            return None
    
    def _has_sufficient_data(self) -> bool:
        """ตรวจสอบว่ามีข้อมูลเพียงพอสำหรับการวิเคราะห์"""
        for tf, data in self.price_history.items():
            if len(data) < 20:  # ต้องมีข้อมูลอย่างน้อย 20 periods
                return False
        return True
    
    def _calculate_technical_indicators(self) -> TechnicalIndicators:
        """คำนวณตัวชี้วัดทางเทคนิค"""
        indicators = TechnicalIndicators()
        
        try:
            # ใช้ข้อมูล M15 เป็นหลัก
            m15_data = list(self.price_history[mt5.TIMEFRAME_M15])
            if len(m15_data) < 50:
                return indicators
            
            # แปลงเป็น arrays
            closes = np.array([d.close for d in m15_data])
            highs = np.array([d.high for d in m15_data])
            lows = np.array([d.low for d in m15_data])
            
            # Moving Averages
            if len(closes) >= 200:
                indicators.sma_200 = np.mean(closes[-200:])
            if len(closes) >= 50:
                indicators.sma_50 = np.mean(closes[-50:])
            if len(closes) >= 20:
                indicators.sma_20 = np.mean(closes[-20:])
            
            # EMA calculation
            indicators.ema_12 = self._calculate_ema(closes, 12)
            indicators.ema_26 = self._calculate_ema(closes, 26)
            
            # RSI calculation
            indicators.rsi_14 = self._calculate_rsi(closes, 14)
            
            # MACD calculation
            macd_line = indicators.ema_12 - indicators.ema_26
            macd_signal = self._calculate_ema(np.array([macd_line]), 9)
            indicators.macd = macd_line
            indicators.macd_signal = macd_signal
            indicators.macd_histogram = macd_line - macd_signal
            
            # ATR calculation
            indicators.atr_14 = self._calculate_atr(highs, lows, closes, 14)
            
            # Bollinger Bands
            sma_20 = indicators.sma_20
            std_20 = np.std(closes[-20:]) if len(closes) >= 20 else 0
            indicators.bollinger_middle = sma_20
            indicators.bollinger_upper = sma_20 + (2 * std_20)
            indicators.bollinger_lower = sma_20 - (2 * std_20)
            indicators.bollinger_width = indicators.bollinger_upper - indicators.bollinger_lower
            
            # ADX calculation (simplified)
            indicators.adx_14 = self._calculate_adx(highs, lows, closes, 14)
            
            # Pivot Points
            yesterday_data = m15_data[-96:]  # 24 hours of M15 data
            if len(yesterday_data) >= 96:
                high_24h = max([d.high for d in yesterday_data])
                low_24h = min([d.low for d in yesterday_data])
                close_24h = yesterday_data[-1].close
                
                indicators.pivot_point = (high_24h + low_24h + close_24h) / 3
                indicators.resistance_1 = (2 * indicators.pivot_point) - low_24h
                indicators.resistance_2 = indicators.pivot_point + (high_24h - low_24h)
                indicators.support_1 = (2 * indicators.pivot_point) - high_24h
                indicators.support_2 = indicators.pivot_point - (high_24h - low_24h)
            
        except Exception as e:
            print(f"❌ Technical indicators calculation error: {e}")
        
        return indicators
    
    def _calculate_ema(self, prices, period):
        """คำนวณ EMA"""
        if len(prices) < period:
            return prices[-1] if len(prices) > 0 else 0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices, period):
        """คำนวณ RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_atr(self, highs, lows, closes, period):
        """คำนวณ ATR"""
        if len(highs) < period + 1:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(highs)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            true_ranges.append(max(tr1, tr2, tr3))
        
        return np.mean(true_ranges[-period:])
    
    def _calculate_adx(self, highs, lows, closes, period):
        """คำนวณ ADX (simplified version)"""
        if len(highs) < period + 1:
            return 0.0
        
        # Simplified ADX calculation
        price_ranges = highs[-period:] - lows[-period:]
        avg_range = np.mean(price_ranges)
        
        # Trend strength based on price movement
        price_change = abs(closes[-1] - closes[-period])
        trend_strength = min((price_change / avg_range) * 20, 100) if avg_range > 0 else 0
        
        return trend_strength
    
    def _detect_market_condition(self, indicators: TechnicalIndicators) -> MarketCondition:
        """ตรวจสอบสภาวะตลาด"""
        try:
            # ตรวจสอบความผันผวน
            atr_threshold_high = indicators.atr_14 * 1.5
            atr_threshold_low = indicators.atr_14 * 0.5
            
            # ตรวจสอบ Bollinger Band Width
            bb_width_ratio = indicators.bollinger_width / indicators.bollinger_middle if indicators.bollinger_middle > 0 else 0
            
            # ตรวจสอบเทรนด์
            adx_strong = indicators.adx_14 > 25
            adx_weak = indicators.adx_14 < 20
            
            # เงื่อนไขการตัดสิน
            current_tick = mt5.symbol_info_tick(self.symbol)
            if not current_tick:
                return MarketCondition.QUIET_LOW
            
            current_price = (current_tick.bid + current_tick.ask) / 2
            spread = current_tick.ask - current_tick.bid
            
            # High Volatility Conditions
            if spread > 1.0 or bb_width_ratio > 0.02:
                return MarketCondition.VOLATILE_HIGH
            
            # News Impact Detection (simplified)
            if self._is_news_time():
                return MarketCondition.VOLATILE_NEWS
            
            # Trending Conditions
            if adx_strong:
                if self._is_strong_trend(indicators):
                    return MarketCondition.TRENDING_STRONG
                else:
                    return MarketCondition.TRENDING_WEAK
            
            # Ranging Conditions
            if adx_weak:
                if bb_width_ratio < 0.005:
                    return MarketCondition.RANGING_TIGHT
                else:
                    return MarketCondition.RANGING_WIDE
            
            # Breakout Detection
            if self._is_breakout_condition(indicators, current_price):
                return MarketCondition.BREAKOUT
            
            # Reversal Detection
            if self._is_reversal_condition(indicators):
                return MarketCondition.REVERSAL
            
            # Default to quiet
            return MarketCondition.QUIET_LOW
            
        except Exception as e:
            print(f"❌ Market condition detection error: {e}")
            return MarketCondition.QUIET_LOW
    
    def _is_news_time(self) -> bool:
        """ตรวจสอบเวลาข่าวสำคัญ"""
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        # Major news times (approximate)
        news_times = [
            (8, 30),   # Tokyo market open
            (15, 30),  # London market open
            (20, 30),  # NY market open
            (22, 30),  # Major US news (EST converted)
        ]
        
        for news_hour, news_minute in news_times:
            if abs(hour - news_hour) <= 1 and abs(minute - news_minute) <= 30:
                return True
        
        return False
    
    def _is_strong_trend(self, indicators: TechnicalIndicators) -> bool:
        """ตรวจสอบเทรนด์แรง"""
        try:
            # Price position relative to moving averages
            current_tick = mt5.symbol_info_tick(self.symbol)
            if not current_tick:
                return False
            
            current_price = (current_tick.bid + current_tick.ask) / 2
            
            # Strong uptrend conditions
            if (current_price > indicators.sma_20 > indicators.sma_50 > indicators.sma_200 and
                indicators.rsi_14 > 50 and
                indicators.macd > indicators.macd_signal):
                return True
            
            # Strong downtrend conditions
            if (current_price < indicators.sma_20 < indicators.sma_50 < indicators.sma_200 and
                indicators.rsi_14 < 50 and
                indicators.macd < indicators.macd_signal):
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Strong trend detection error: {e}")
            return False
    
    def _is_breakout_condition(self, indicators: TechnicalIndicators, current_price: float) -> bool:
        """ตรวจสอบ Breakout"""
        try:
            # Bollinger Band breakout
            if (current_price > indicators.bollinger_upper or 
                current_price < indicators.bollinger_lower):
                return True
            
            # Support/Resistance breakout
            if (current_price > indicators.resistance_1 or 
                current_price < indicators.support_1):
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Breakout detection error: {e}")
            return False
    
    def _is_reversal_condition(self, indicators: TechnicalIndicators) -> bool:
        """ตรวจสอบ Reversal"""
        try:
            # RSI reversal signals
            if indicators.rsi_14 > 70 or indicators.rsi_14 < 30:
                return True
            
            # MACD reversal
            if abs(indicators.macd_histogram) < 0.1:  # MACD convergence
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Reversal detection error: {e}")
            return False
    
    def _identify_trading_session(self) -> TradingSession:
        """ระบุเซสชันการเทรด"""
        now = datetime.now()
        hour = now.hour
        
        # GMT+7 timezone adjustments
        if 3 <= hour < 12:  # Asian session
            return TradingSession.ASIAN
        elif 15 <= hour < 20:  # London session
            return TradingSession.LONDON
        elif 20 <= hour < 24 or 0 <= hour < 3:  # NY session
            return TradingSession.NEW_YORK
        elif 20 <= hour < 24:  # London-NY overlap
            return TradingSession.OVERLAP_LONDON_NY
        else:
            return TradingSession.QUIET
    
    def _analyze_trend(self, indicators: TechnicalIndicators) -> Tuple[TrendDirection, float]:
        """วิเคราะห์เทรนด์และความแรง"""
        try:
            current_tick = mt5.symbol_info_tick(self.symbol)
            if not current_tick:
                return TrendDirection.SIDEWAYS, 0.0
            
            current_price = (current_tick.bid + current_tick.ask) / 2
            
            # Score calculation
            trend_score = 0
            
            # Price vs Moving Averages
            if current_price > indicators.sma_20:
                trend_score += 1
            else:
                trend_score -= 1
            
            if indicators.sma_20 > indicators.sma_50:
                trend_score += 1
            else:
                trend_score -= 1
            
            if indicators.sma_50 > indicators.sma_200:
                trend_score += 1
            else:
                trend_score -= 1
            
            # MACD
            if indicators.macd > indicators.macd_signal:
                trend_score += 1
            else:
                trend_score -= 1
            
            # RSI
            if indicators.rsi_14 > 50:
                trend_score += 1
            else:
                trend_score -= 1
            
            # ADX strength
            strength = min(indicators.adx_14, 100)
            
            # Determine direction and strength
            if trend_score >= 3:
                if strength > 50:
                    return TrendDirection.BULLISH_STRONG, strength
                else:
                    return TrendDirection.BULLISH_WEAK, strength
            elif trend_score <= -3:
                if strength > 50:
                    return TrendDirection.BEARISH_STRONG, strength
                else:
                    return TrendDirection.BEARISH_WEAK, strength
            else:
                return TrendDirection.SIDEWAYS, strength
                
        except Exception as e:
            print(f"❌ Trend analysis error: {e}")
            return TrendDirection.SIDEWAYS, 0.0
    
    def _calculate_volatility_level(self, indicators: TechnicalIndicators) -> float:
        """คำนวณระดับความผันผวน (0-100)"""
        try:
            # ATR-based volatility
            m15_data = list(self.price_history[mt5.TIMEFRAME_M15])
            if len(m15_data) < 50:
                return 50.0
            
            # Calculate average ATR for comparison
            recent_prices = [d.close for d in m15_data[-50:]]
            price_range = max(recent_prices) - min(recent_prices)
            avg_price = statistics.mean(recent_prices)
            
            volatility_ratio = (price_range / avg_price) * 100 if avg_price > 0 else 0
            
            # Bollinger Band width factor
            bb_factor = (indicators.bollinger_width / indicators.bollinger_middle) * 1000 if indicators.bollinger_middle > 0 else 0
            
            # Combine factors
            volatility_score = min((volatility_ratio + bb_factor) * 2, 100)
            
            return volatility_score
            
        except Exception as e:
            print(f"❌ Volatility calculation error: {e}")
            return 50.0
    
    def _select_optimal_strategy(self, condition: MarketCondition, session: TradingSession, 
                               trend: TrendDirection, volatility: float) -> Tuple[EntryStrategy, float]:
        """เลือกกลยุทธ์ที่เหมาะสมที่สุด"""
        try:
            confidence = 50.0  # Base confidence
            
            # Strategy selection based on market condition
            if condition == MarketCondition.TRENDING_STRONG:
                if trend in [TrendDirection.BULLISH_STRONG, TrendDirection.BEARISH_STRONG]:
                    confidence = 85.0
                    return EntryStrategy.TREND_FOLLOWING, confidence
            
            elif condition == MarketCondition.RANGING_TIGHT:
                confidence = 75.0
                return EntryStrategy.MEAN_REVERSION, confidence
            
            elif condition == MarketCondition.RANGING_WIDE:
                confidence = 70.0
                return EntryStrategy.GRID_ENTRY, confidence
            
            elif condition == MarketCondition.VOLATILE_HIGH:
                confidence = 60.0
                return EntryStrategy.SCALPING, confidence
            
            elif condition == MarketCondition.BREAKOUT:
                confidence = 80.0
                return EntryStrategy.BREAKOUT_TRADE, confidence
            
            elif condition == MarketCondition.REVERSAL:
                confidence = 70.0
                return EntryStrategy.FALSE_BREAKOUT, confidence
            
            elif condition == MarketCondition.VOLATILE_NEWS:
                confidence = 65.0
                return EntryStrategy.NEWS_REACTION, confidence
            
            # Session-based adjustments
            if session == TradingSession.ASIAN:
                confidence -= 10  # Lower confidence in Asian session
                return EntryStrategy.MEAN_REVERSION, confidence
            
            elif session == TradingSession.OVERLAP_LONDON_NY:
                confidence += 15  # Higher confidence in overlap
                return EntryStrategy.BREAKOUT_TRADE, confidence
            
            # Default strategy
            return EntryStrategy.SCALPING, max(confidence, 30.0)
            
        except Exception as e:
            print(f"❌ Strategy selection error: {e}")
            return EntryStrategy.SCALPING, 30.0
    
    def _calculate_support_resistance(self) -> Tuple[List[float], List[float]]:
        """คำนวณ Support และ Resistance levels"""
        try:
            support_levels = []
            resistance_levels = []
            
            # ใช้ข้อมูล H1 สำหรับ S/R
            h1_data = list(self.price_history[mt5.TIMEFRAME_H1])
            if len(h1_data) < 20:
                return support_levels, resistance_levels
            
            # หา swing highs และ lows
            highs = [d.high for d in h1_data[-50:]]
            lows = [d.low for d in h1_data[-50:]]
            
            # Find significant levels
            for i in range(2, len(highs) - 2):
                # Resistance levels (swing highs)
                if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                    resistance_levels.append(highs[i])
                
                # Support levels (swing lows)
                if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                    support_levels.append(lows[i])
            
            # Sort and limit to most relevant levels
            support_levels = sorted(list(set(support_levels)), reverse=True)[:3]
            resistance_levels = sorted(list(set(resistance_levels)))[:3]
            
            return support_levels, resistance_levels
            
        except Exception as e:
            print(f"❌ S/R calculation error: {e}")
            return [], []
    
    def _evaluate_spread_quality(self) -> float:
        """ประเมินคุณภาพของ Spread (0-100)"""
        try:
            current_tick = mt5.symbol_info_tick(self.symbol)
            if not current_tick:
                return 0.0
            
            spread = current_tick.ask - current_tick.bid
            
            # Gold spread quality thresholds
            if spread <= 0.3:
                return 100.0  # Excellent
            elif spread <= 0.5:
                return 80.0   # Good
            elif spread <= 0.8:
                return 60.0   # Average
            elif spread <= 1.2:
                return 40.0   # Poor
            else:
                return 20.0   # Very poor
                
        except Exception as e:
            print(f"❌ Spread evaluation error: {e}")
            return 50.0
    
    def _evaluate_liquidity(self) -> float:
        """ประเมินสภาพคล่อง (0-100)"""
        try:
            # Simple liquidity assessment based on session and time
            session = self._identify_trading_session()
            
            session_scores = {
                TradingSession.ASIAN: 60.0,
                TradingSession.LONDON: 90.0,
                TradingSession.NEW_YORK: 95.0,
                TradingSession.OVERLAP_LONDON_NY: 100.0,
                TradingSession.QUIET: 30.0
            }
            
            return session_scores.get(session, 50.0)
            
        except Exception as e:
            print(f"❌ Liquidity evaluation error: {e}")
            return 50.0
    
    def _get_timeframe_signals(self, timeframe) -> Dict[str, Any]:
        """ดึงสัญญาณจาก timeframe ที่กำหนด"""
        try:
            data = list(self.price_history[timeframe])
            if len(data) < 10:
                return {}
            
            recent_data = data[-10:]
            current_price = recent_data[-1].close
            
            # Simple signals
            signals = {
                'trend': 'UP' if recent_data[-1].close > recent_data[-5].close else 'DOWN',
                'momentum': 'STRONG' if abs(float(recent_data[-1].close) - float(recent_data[-3].close)) > float(recent_data[-1].close) * 0.001 else 'WEAK',
                'volume': 'HIGH' if recent_data[-1].volume > statistics.mean([float(d.volume) for d in recent_data]) else 'LOW'
            }
            
            return signals
            
        except Exception as e:
            print(f"❌ Timeframe signals error: {e}")
            return {}
    
    def _log_analysis(self, analysis: MarketAnalysis):
        """Log ผลการวิเคราะห์"""
        try:
            if self.analysis_count % 30 == 0:  # Log every 30 analyses
                print(f"\n🧠 MARKET INTELLIGENCE ANALYSIS #{self.analysis_count}")
                print(f"⏰ Time: {analysis.timestamp.strftime('%H:%M:%S')}")
                print(f"💰 Price: ${analysis.current_price:.2f}")
                print(f"📊 Condition: {analysis.condition.value}")
                print(f"🌐 Session: {analysis.session.value}")
                print(f"📈 Trend: {analysis.trend_direction.value} ({analysis.trend_strength:.1f}%)")
                print(f"⚡ Volatility: {analysis.volatility_level:.1f}%")
                print(f"🎯 Strategy: {analysis.recommended_strategy.value}")
                print(f"🔍 Confidence: {analysis.confidence_score:.1f}%")
                print(f"📊 Spread Quality: {analysis.spread_score:.1f}%")
                print(f"💧 Liquidity: {analysis.liquidity_score:.1f}%")
                print("-" * 60)
                
        except Exception as e:
            print(f"❌ Analysis logging error: {e}")
    
    def get_current_analysis(self) -> Optional[MarketAnalysis]:
        """ดึงผลการวิเคราะห์ปัจจุบัน"""
        return self.current_analysis
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """ดึงสถิติการวิเคราะห์"""
        return {
            'total_analyses': self.analysis_count,
            'total_errors': self.analysis_errors,
            'error_rate': (self.analysis_errors / max(self.analysis_count, 1)) * 100,
            'last_analysis': self.last_analysis_time.strftime('%H:%M:%S') if self.last_analysis_time else 'None',
            'data_points': {tf: len(data) for tf, data in self.price_history.items()}
        }

class IntelligentStrategySelector:
    """
    ระบบเลือกกลยุทธ์อัจฉริยะ
    ใช้ผลการวิเคราะห์จาก MarketAnalyzer เพื่อเลือกกลยุทธ์ที่เหมาะสม
    """
    
    def __init__(self):
        self.strategy_performance = defaultdict(list)
        self.strategy_weights = {
            EntryStrategy.TREND_FOLLOWING: 1.0,
            EntryStrategy.MEAN_REVERSION: 1.0,
            EntryStrategy.BREAKOUT_TRADE: 1.0,
            EntryStrategy.FALSE_BREAKOUT: 1.0,
            EntryStrategy.NEWS_REACTION: 1.0,
            EntryStrategy.SCALPING: 1.0,
            EntryStrategy.GRID_ENTRY: 1.0
        }
        
        print("🎯 Intelligent Strategy Selector initialized")
    
    def select_strategy(self, analysis: MarketAnalysis) -> Tuple[EntryStrategy, float, Dict[str, Any]]:
        """
        เลือกกลยุทธ์ที่เหมาะสมที่สุดตามการวิเคราะห์
        
        Returns:
            strategy: กลยุทธ์ที่เลือก
            confidence: ความมั่นใจ (0-100)
            parameters: พารามิเตอร์สำหรับกลยุทธ์
        """
        try:
            # Base strategy from market analysis
            base_strategy = analysis.recommended_strategy
            base_confidence = analysis.confidence_score
            
            # Strategy-specific parameters
            parameters = self._get_strategy_parameters(base_strategy, analysis)
            
            # Adjust confidence based on market quality
            adjusted_confidence = self._adjust_confidence(base_confidence, analysis)
            
            # Consider strategy performance history
            performance_weight = self.strategy_weights.get(base_strategy, 1.0)
            final_confidence = min(adjusted_confidence * performance_weight, 100.0)
            
            # Log strategy selection
            self._log_strategy_selection(base_strategy, final_confidence, parameters)
            
            return base_strategy, final_confidence, parameters
            
        except Exception as e:
            print(f"❌ Strategy selection error: {e}")
            return EntryStrategy.SCALPING, 30.0, {}
    
    def _get_strategy_parameters(self, strategy: EntryStrategy, analysis: MarketAnalysis) -> Dict[str, Any]:
        """ดึงพารามิเตอร์สำหรับกลยุทธ์ที่เลือก"""
        try:
            base_params = {
                'symbol': analysis.symbol,
                'current_price': analysis.current_price,
                'spread': analysis.current_price * (100 - analysis.spread_score) / 10000,  # Estimate spread
                'volatility': analysis.volatility_level,
                'trend_strength': analysis.trend_strength,
                'session': analysis.session.value
            }
            
            if strategy == EntryStrategy.TREND_FOLLOWING:
                return {
                    **base_params,
                    'entry_method': 'PULLBACK' if analysis.trend_strength > 70 else 'BREAKOUT',
                    'lot_size': 0.01 if analysis.volatility_level > 60 else 0.02,
                    'take_profit_pips': 15 if analysis.volatility_level > 60 else 10,
                    'max_positions': 3
                }
            
            elif strategy == EntryStrategy.MEAN_REVERSION:
                return {
                    **base_params,
                    'entry_method': 'BOLLINGER_BOUNCE',
                    'lot_size': 0.01,
                    'take_profit_pips': 8,
                    'max_positions': 5,
                    'overbought_threshold': 70,
                    'oversold_threshold': 30
                }
            
            elif strategy == EntryStrategy.BREAKOUT_TRADE:
                return {
                    **base_params,
                    'entry_method': 'RESISTANCE_BREAK',
                    'lot_size': 0.02 if analysis.confidence_score > 80 else 0.01,
                    'take_profit_pips': 20,
                    'max_positions': 2,
                    'breakout_confirmation': True
                }
            
            elif strategy == EntryStrategy.FALSE_BREAKOUT:
                return {
                    **base_params,
                    'entry_method': 'FAKE_BREAKOUT',
                    'lot_size': 0.01,
                    'take_profit_pips': 12,
                    'max_positions': 3,
                    'wait_time_seconds': 60
                }
            
            elif strategy == EntryStrategy.NEWS_REACTION:
                return {
                    **base_params,
                    'entry_method': 'NEWS_REVERSAL',
                    'lot_size': 0.01,  # Conservative during news
                    'take_profit_pips': 15,
                    'max_positions': 2,
                    'quick_exit': True
                }
            
            elif strategy == EntryStrategy.SCALPING:
                return {
                    **base_params,
                    'entry_method': 'QUICK_SCALP',
                    'lot_size': 0.01,
                    'take_profit_pips': 5,
                    'max_positions': 10,
                    'fast_execution': True
                }
            
            elif strategy == EntryStrategy.GRID_ENTRY:
                return {
                    **base_params,
                    'entry_method': 'GRID_LEVELS',
                    'lot_size': 0.01,
                    'grid_distance_pips': 10,
                    'max_grid_levels': 5,
                    'take_profit_pips': 8
                }
            
            return base_params
            
        except Exception as e:
            print(f"❌ Strategy parameters error: {e}")
            return {}
    
    def _adjust_confidence(self, base_confidence: float, analysis: MarketAnalysis) -> float:
        """ปรับความมั่นใจตามคุณภาพตลาด"""
        try:
            adjusted = base_confidence
            
            # Spread quality adjustment
            if analysis.spread_score < 50:
                adjusted *= 0.8  # Reduce confidence for poor spreads
            elif analysis.spread_score > 80:
                adjusted *= 1.1  # Increase confidence for good spreads
            
            # Liquidity adjustment
            if analysis.liquidity_score < 50:
                adjusted *= 0.9
            elif analysis.liquidity_score > 80:
                adjusted *= 1.05
            
            # Volatility adjustment
            if analysis.volatility_level > 80:
                adjusted *= 0.85  # High volatility = lower confidence
            elif analysis.volatility_level < 20:
                adjusted *= 0.9   # Very low volatility = lower confidence
            
            # Session adjustment
            if analysis.session == TradingSession.OVERLAP_LONDON_NY:
                adjusted *= 1.15  # Best trading session
            elif analysis.session == TradingSession.QUIET:
                adjusted *= 0.7   # Quiet session
            
            return min(max(adjusted, 10.0), 100.0)  # Clamp between 10-100
            
        except Exception as e:
            print(f"❌ Confidence adjustment error: {e}")
            return base_confidence
    
    def update_strategy_performance(self, strategy: EntryStrategy, success: bool, profit: float):
        """อัพเดทผลการดำเนินงานของกลยุทธ์"""
        try:
            self.strategy_performance[strategy].append({
                'success': success,
                'profit': profit,
                'timestamp': datetime.now()
            })
            
            # Keep only recent performance (last 100 trades per strategy)
            if len(self.strategy_performance[strategy]) > 100:
                self.strategy_performance[strategy] = self.strategy_performance[strategy][-100:]
            
            # Update strategy weights based on performance
            self._update_strategy_weights()
            
        except Exception as e:
            print(f"❌ Strategy performance update error: {e}")
    
    def _update_strategy_weights(self):
        """อัพเดทน้ำหนักของกลยุทธ์ตามผลการดำเนินงาน"""
        try:
            for strategy, performances in self.strategy_performance.items():
                if len(performances) < 10:  # Need minimum trades
                    continue
                
                recent_performances = performances[-50:]  # Last 50 trades
                
                # Calculate success rate
                success_rate = sum(1 for p in recent_performances if p['success']) / len(recent_performances)
                
                # Calculate average profit
                avg_profit = statistics.mean([p['profit'] for p in recent_performances])
                
                # Calculate new weight
                # Base weight = 1.0, adjust based on performance
                performance_score = (success_rate * 0.7) + (min(avg_profit / 10, 0.3) * 0.3)
                new_weight = 0.5 + (performance_score * 1.0)  # Range: 0.5 - 1.5
                
                self.strategy_weights[strategy] = max(min(new_weight, 1.5), 0.5)
                
        except Exception as e:
            print(f"❌ Strategy weights update error: {e}")
    
    def _log_strategy_selection(self, strategy: EntryStrategy, confidence: float, parameters: Dict[str, Any]):
        """Log การเลือกกลยุทธ์"""
        try:
            print(f"🎯 Strategy Selected: {strategy.value}")
            print(f"🔍 Confidence: {confidence:.1f}%")
            print(f"⚙️ Parameters: {parameters.get('entry_method', 'N/A')}")
            print(f"💰 Lot Size: {parameters.get('lot_size', 0.01)}")
            print(f"🎯 Take Profit: {parameters.get('take_profit_pips', 'N/A')} pips")
            
        except Exception as e:
            print(f"❌ Strategy logging error: {e}")
    
    def get_strategy_stats(self) -> Dict[str, Any]:
        """ดึงสถิติของกลยุทธ์"""
        try:
            stats = {}
            
            for strategy, performances in self.strategy_performance.items():
                if len(performances) > 0:
                    recent = performances[-20:]  # Last 20 trades
                    success_rate = sum(1 for p in recent if p['success']) / len(recent) * 100
                    avg_profit = statistics.mean([p['profit'] for p in recent])
                    
                    stats[strategy.value] = {
                        'total_trades': len(performances),
                        'recent_success_rate': success_rate,
                        'recent_avg_profit': avg_profit,
                        'current_weight': self.strategy_weights.get(strategy, 1.0)
                    }
            
            return stats
            
        except Exception as e:
            print(f"❌ Strategy stats error: {e}")
            return {}

# ===== FACTORY FUNCTIONS =====

def create_market_analyzer(symbol: str = "XAUUSD.v") -> RealTimeMarketAnalyzer:
    """
    สร้าง Market Analyzer สำหรับ symbol ที่กำหนด
    """
    try:
        analyzer = RealTimeMarketAnalyzer(symbol)
        print(f"✅ Market Analyzer created for {symbol}")
        return analyzer
    except Exception as e:
        print(f"❌ Failed to create Market Analyzer: {e}")
        raise

def create_strategy_selector() -> IntelligentStrategySelector:
    """
    สร้าง Strategy Selector
    """
    try:
        selector = IntelligentStrategySelector()
        print("✅ Strategy Selector created")
        return selector
    except Exception as e:
        print(f"❌ Failed to create Strategy Selector: {e}")
        raise

def get_market_intelligence_system(symbol: str = "XAUUSD.v") -> Tuple[RealTimeMarketAnalyzer, IntelligentStrategySelector]:
    """
    สร้างระบบ Market Intelligence ที่สมบูรณ์
    
    Returns:
        analyzer: Market Analyzer
        selector: Strategy Selector
    """
    try:
        print("🧠 Initializing Market Intelligence System...")
        
        analyzer = create_market_analyzer(symbol)
        selector = create_strategy_selector()
        
        print("✅ Market Intelligence System ready")
        
        return analyzer, selector
        
    except Exception as e:
        print(f"❌ Failed to initialize Market Intelligence System: {e}")
        raise

# ===== MAIN TESTING FUNCTION =====

def test_market_intelligence():
    """
    ทดสอบระบบ Market Intelligence
    """
    print("🧪 Testing Market Intelligence System...")
    
    try:
        # Create system
        analyzer, selector = get_market_intelligence_system()
        
        # Start analysis
        analyzer.start_analysis()
        
        # Run test for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            current_analysis = analyzer.get_current_analysis()
            
            if current_analysis:
                # Get strategy recommendation
                strategy, confidence, params = selector.select_strategy(current_analysis)
                
                print(f"\n📊 Test Result:")
                print(f"Market: {current_analysis.condition.value}")
                print(f"Strategy: {strategy.value}")
                print(f"Confidence: {confidence:.1f}%")
            
            time.sleep(5)
        
        # Stop analysis
        analyzer.stop_analysis()
        
        # Print stats
        print("\n📈 Analysis Stats:")
        stats = analyzer.get_analysis_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        print("✅ Market Intelligence test completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    # Test if running directly
    test_market_intelligence()