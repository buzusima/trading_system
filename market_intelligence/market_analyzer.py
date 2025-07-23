#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REAL-TIME MARKET ANALYSIS ENGINE - เครื่องวิเคราะห์ตลาดแบบเรียลไทม์
===========================================================
วิเคราะห์สภาพตลาด XAUUSD แบบอัตโนมัติและตัดสินใจเลือกกลยุทธ์
รองรับการวิเคราะห์หลายไทม์เฟรมและปรับตัวตามสภาพตลาด

เชื่อมต่อไปยัง:
- mt5_integration/mt5_connector.py (การเชื่อมต่อ MT5)  
- config/trading_params.py (พารามิเตอร์การวิเคราะห์)
- config/session_config.py (การตั้งค่า session)
- utilities/professional_logger.py (logging)
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Imports
try:
    from mt5_integration.mt5_connector import get_mt5_connector, ensure_mt5_connection
    from config.trading_params import get_trading_parameters, RecoveryMethod, EntryStrategy
    from config.session_config import get_session_manager, SessionType
    from utilities.professional_logger import setup_market_logger
    from utilities.error_handler import handle_trading_errors, MarketDataError, ErrorCategory, ErrorSeverity
except ImportError as e:
    print(f"Import Error in market_analyzer.py: {e}")

class MarketCondition(Enum):
    """สภาพตลาดต่างๆ"""
    TRENDING_STRONG = "TRENDING_STRONG"
    TRENDING_WEAK = "TRENDING_WEAK" 
    RANGING_TIGHT = "RANGING_TIGHT"
    RANGING_WIDE = "RANGING_WIDE"
    VOLATILE_HIGH = "VOLATILE_HIGH"
    VOLATILE_LOW = "VOLATILE_LOW"
    NEWS_IMPACT = "NEWS_IMPACT"
    QUIET_HOURS = "QUIET_HOURS"

class TrendDirection(Enum):
    """ทิศทางของ trend"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH" 
    SIDEWAYS = "SIDEWAYS"
    UNCERTAIN = "UNCERTAIN"

@dataclass
class MarketAnalysis:
    """ผลการวิเคราะห์ตลาด"""
    timestamp: datetime = field(default_factory=datetime.now)
    symbol: str = "XAUUSD"
    
    # Trend Analysis
    trend_direction: TrendDirection = TrendDirection.UNCERTAIN
    trend_strength: float = 0.0
    adx_value: float = 0.0
    
    # Volatility Analysis  
    atr_value: float = 0.0
    volatility_level: str = "NORMAL"
    bollinger_width: float = 0.0
    
    # Momentum Analysis
    rsi_value: float = 50.0
    macd_value: float = 0.0
    macd_signal: float = 0.0
    stochastic_k: float = 50.0
    stochastic_d: float = 50.0
    
    # Support/Resistance
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    current_price: float = 0.0
    
    # Market Condition
    primary_condition: MarketCondition = MarketCondition.RANGING_TIGHT
    secondary_conditions: List[MarketCondition] = field(default_factory=list)
    
    # Recommendations
    recommended_entry_strategies: List[EntryStrategy] = field(default_factory=list)
    recommended_recovery_method: RecoveryMethod = RecoveryMethod.GRID_INTELLIGENT
    confidence_score: float = 0.0
    
    # Session Context
    current_session: Optional[SessionType] = None
    
    # Multi-timeframe Data
    timeframe_analysis: Dict[str, Dict] = field(default_factory=dict)

class MarketAnalyzer:
    """เครื่องวิเคราะห์ตลาดหลัก"""
    
    def __init__(self):
        self.logger = setup_market_logger()
        self.trading_params = get_trading_parameters()
        self.session_manager = get_session_manager()
        
        # ข้อมูลการวิเคราะห์
        self.current_analysis: Optional[MarketAnalysis] = None
        self.analysis_history: List[MarketAnalysis] = []
        self.symbol = "XAUUSD"
        
        # การตั้งค่า
        self.timeframes = ["M1", "M5", "M15", "H1"]
        self.analysis_interval = 5
        
        # Threading
        self.analysis_lock = threading.Lock()
        self.analysis_thread: Optional[threading.Thread] = None
        self.analysis_active = False
        
        self.logger.info("🌍 เริ่มต้น Market Analyzer")
    
    def start_analysis(self):
        """เริ่มการวิเคราะห์ตลาดแบบเรียลไทม์"""
        if self.analysis_active:
            return
        
        self.analysis_active = True
        self.analysis_thread = threading.Thread(
            target=self._analysis_loop,
            daemon=True,
            name="MarketAnalysisLoop"
        )
        self.analysis_thread.start()
        self.logger.info("🚀 เริ่มการวิเคราะห์ตลาดแบบเรียลไทม์")
    
    def stop_analysis(self):
        """หยุดการวิเคราะห์ตลาด"""
        self.analysis_active = False
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=10.0)
        self.logger.info("🛑 หยุดการวิเคราะห์ตลาด")
    
    @handle_trading_errors(ErrorCategory.MARKET_DATA, ErrorSeverity.MEDIUM)
    def analyze_market(self) -> Optional[MarketAnalysis]:
        """วิเคราะห์ตลาดครบวงจร"""
        
        if not ensure_mt5_connection():
            self.logger.error("❌ ไม่สามารถเชื่อมต่อ MT5 สำหรับการวิเคราะห์")
            return None
        
        with self.analysis_lock:
            try:
                self.logger.debug("🔍 เริ่มวิเคราะห์ตลาด")
                
                # สร้าง MarketAnalysis ใหม่
                analysis = MarketAnalysis()
                
                # ดึงข้อมูลราคาปัจจุบัน
                tick = mt5.symbol_info_tick(self.symbol)
                if not tick:
                    raise MarketDataError(f"ไม่สามารถดึงข้อมูลราคา {self.symbol} ได้")
                
                analysis.current_price = (tick.ask + tick.bid) / 2
                
                # วิเคราะห์แต่ละไทม์เฟรม
                for timeframe in self.timeframes:
                    tf_analysis = self._analyze_timeframe(timeframe)
                    analysis.timeframe_analysis[timeframe] = tf_analysis
                
                # รวมผลการวิเคราะห์
                self._consolidate_analysis(analysis)
                
                # วิเคราะห์ session
                self._analyze_session_context(analysis)
                
                # แนะนำกลยุทธ์
                self._recommend_strategies(analysis)
                
                # คำนวณความมั่นใจ
                analysis.confidence_score = self._calculate_confidence(analysis)
                
                # บันทึกผล
                self.current_analysis = analysis
                self.analysis_history.append(analysis)
                
                # จำกัดประวัติ
                if len(self.analysis_history) > 1000:
                    self.analysis_history = self.analysis_history[-1000:]
                
                self.logger.debug(
                    f"✅ วิเคราะห์สำเร็จ - Condition: {analysis.primary_condition.value} "
                    f"Trend: {analysis.trend_direction.value} Confidence: {analysis.confidence_score:.2f}"
                )
                
                return analysis
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์: {e}")
                return None
    def _analyze_timeframe(self, timeframe: str) -> Dict:
        """วิเคราะห์ไทม์เฟรมเฉพาะ"""
        
        # แปลงไทม์เฟรมเป็นรูปแบบ MT5
        mt5_timeframe = self._convert_timeframe_to_mt5(timeframe)
        
        # ดึงข้อมูลราคา
        rates = mt5.copy_rates_from_pos(self.symbol, mt5_timeframe, 0, 200)
        if rates is None or len(rates) == 0:
            return {"error": f"ไม่สามารถดึงข้อมูล {timeframe} ได้"}
        
        # แปลงเป็น DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        # คำนวณ indicators
        indicators = self._calculate_indicators(df)
        
        # วิเคราะห์ต่างๆ
        trend_analysis = self._analyze_trend(df, indicators)
        volatility_analysis = self._analyze_volatility(df, indicators)
        momentum_analysis = self._analyze_momentum(df, indicators)
        sr_levels = self._find_support_resistance(df)
        
        return {
            "timeframe": timeframe,
            "current_price": df['close'].iloc[-1],
            "indicators": indicators,
            "trend": trend_analysis,
            "volatility": volatility_analysis,
            "momentum": momentum_analysis,
            "support_resistance": sr_levels,
            "candle_count": len(df)
        }
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """คำนวณ indicators ต่างๆ"""
        indicators = {}
        
        try:
            # Moving Averages
            indicators['sma_10'] = df['close'].rolling(window=10).mean().iloc[-1]
            indicators['sma_50'] = df['close'].rolling(window=50).mean().iloc[-1]
            indicators['ema_10'] = df['close'].ewm(span=10).mean().iloc[-1]
            indicators['ema_50'] = df['close'].ewm(span=50).mean().iloc[-1]
            
            # Technical Indicators
            indicators['adx'] = self._calculate_adx(df)
            indicators['atr'] = self._calculate_atr(df)
            indicators['rsi'] = self._calculate_rsi(df)
            
            # MACD
            macd_data = self._calculate_macd(df)
            indicators.update(macd_data)
            
            # Bollinger Bands
            bb_data = self._calculate_bollinger_bands(df)
            indicators.update(bb_data)
            
            # Stochastic
            stoch_data = self._calculate_stochastic(df)
            indicators.update(stoch_data)
            
        except Exception as e:
            self.logger.warning(f"⚠️ ข้อผิดพลาดในการคำนวณ indicators: {e}")
        
        return indicators
    
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
            dm_pos = high.diff()
            dm_neg = low.diff() * -1
            
            dm_pos[(dm_pos < 0) | (dm_pos < dm_neg)] = 0
            dm_neg[(dm_neg < 0) | (dm_neg < dm_pos)] = 0
            
            # Directional Indicators
            atr = tr.rolling(window=period).mean()
            di_pos = (dm_pos.rolling(window=period).mean() / atr) * 100
            di_neg = (dm_neg.rolling(window=period).mean() / atr) * 100
            
            # ADX
            dx = abs(di_pos - di_neg) / (di_pos + di_neg) * 100
            adx = dx.rolling(window=period).mean()
            
            return adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0.0
            
        except Exception:
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
            return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0.0
            
        except Exception:
            return 0.0
    
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
            
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
            
        except Exception:
            return 50.0
    
    def _calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """คำนวณ MACD"""
        try:
            close = df['close']
            
            ema_fast = close.ewm(span=fast).mean()
            ema_slow = close.ewm(span=slow).mean()
            
            macd = ema_fast - ema_slow
            macd_signal = macd.ewm(span=signal).mean()
            macd_histogram = macd - macd_signal
            
            return {
                'macd': macd.iloc[-1] if not pd.isna(macd.iloc[-1]) else 0.0,
                'macd_signal': macd_signal.iloc[-1] if not pd.isna(macd_signal.iloc[-1]) else 0.0,
                'macd_histogram': macd_histogram.iloc[-1] if not pd.isna(macd_histogram.iloc[-1]) else 0.0
            }
            
        except Exception:
            return {'macd': 0.0, 'macd_signal': 0.0, 'macd_histogram': 0.0}
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std: float = 2.0) -> Dict:
        """คำนวณ Bollinger Bands"""
        try:
            close = df['close']
            
            middle = close.rolling(window=period).mean()
            std_dev = close.rolling(window=period).std()
            
            upper = middle + (std_dev * std)
            lower = middle - (std_dev * std)
            width = upper - lower
            
            return {
                'bb_upper': upper.iloc[-1] if not pd.isna(upper.iloc[-1]) else 0.0,
                'bb_middle': middle.iloc[-1] if not pd.isna(middle.iloc[-1]) else 0.0,
                'bb_lower': lower.iloc[-1] if not pd.isna(lower.iloc[-1]) else 0.0,
                'bb_width': width.iloc[-1] if not pd.isna(width.iloc[-1]) else 0.0
            }
            
        except Exception:
            current_price = df['close'].iloc[-1]
            return {
                'bb_upper': current_price * 1.01,
                'bb_middle': current_price,
                'bb_lower': current_price * 0.99,
                'bb_width': current_price * 0.02
            }
    
    def _calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict:
        """คำนวณ Stochastic"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            lowest_low = low.rolling(window=k_period).min()
            highest_high = high.rolling(window=k_period).max()
            
            k_percent = ((close - lowest_low) / (highest_high - lowest_low)) * 100
            d_percent = k_percent.rolling(window=d_period).mean()
            
            return {
                'stoch_k': k_percent.iloc[-1] if not pd.isna(k_percent.iloc[-1]) else 50.0,
                'stoch_d': d_percent.iloc[-1] if not pd.isna(d_percent.iloc[-1]) else 50.0
            }
            
        except Exception:
            return {'stoch_k': 50.0, 'stoch_d': 50.0}
        
    def _analyze_trend(self, df: pd.DataFrame, indicators: Dict) -> Dict:
        """วิเคราะห์ trend"""
        trend_analysis = {
            'direction': TrendDirection.UNCERTAIN,
            'strength': 0.0,
            'adx_value': indicators.get('adx', 0.0)
        }
        
        try:
            current_price = df['close'].iloc[-1]
            sma_10 = indicators.get('sma_10', current_price)
            sma_50 = indicators.get('sma_50', current_price)
            adx = indicators.get('adx', 0.0)
            
            # กำหนดทิศทาง trend
            if current_price > sma_10 > sma_50:
                trend_analysis['direction'] = TrendDirection.BULLISH
            elif current_price < sma_10 < sma_50:
                trend_analysis['direction'] = TrendDirection.BEARISH
            else:
                trend_analysis['direction'] = TrendDirection.SIDEWAYS
            
            # กำหนด strength จาก ADX
            if adx >= 25:
                trend_analysis['strength'] = min(adx / 50, 1.0)
            else:
                trend_analysis['strength'] = adx / 25 * 0.5
                
        except Exception as e:
            self.logger.warning(f"⚠️ ข้อผิดพลาดในการวิเคราะห์ trend: {e}")
        
        return trend_analysis
    
    def _analyze_volatility(self, df: pd.DataFrame, indicators: Dict) -> Dict:
        """วิเคราะห์ volatility"""
        volatility_analysis = {
            'level': 'NORMAL',
            'atr_value': indicators.get('atr', 0.0),
            'bb_width': indicators.get('bb_width', 0.0)
        }
        
        try:
            atr = indicators.get('atr', 0.0)
            
            # คำนวณ ATR เฉลี่ย
            atr_avg = df['close'].rolling(window=50).std().iloc[-1] if len(df) >= 50 else atr
            
            # กำหนดระดับ volatility
            if atr > atr_avg * 2.0:
                volatility_analysis['level'] = 'EXTREME'
            elif atr > atr_avg * 1.5:
                volatility_analysis['level'] = 'HIGH'
            elif atr < atr_avg * 0.8:
                volatility_analysis['level'] = 'LOW'
            else:
                volatility_analysis['level'] = 'NORMAL'
                
        except Exception as e:
            self.logger.warning(f"⚠️ ข้อผิดพลาดในการวิเคราะห์ volatility: {e}")
        
        return volatility_analysis
    
    def _analyze_momentum(self, df: pd.DataFrame, indicators: Dict) -> Dict:
        """วิเคราะห์ momentum"""
        return {
            'rsi': indicators.get('rsi', 50.0),
            'macd': indicators.get('macd', 0.0),
            'macd_signal': indicators.get('macd_signal', 0.0),
            'stoch_k': indicators.get('stoch_k', 50.0),
            'stoch_d': indicators.get('stoch_d', 50.0)
        }
    
    def _find_support_resistance(self, df: pd.DataFrame, lookback: int = 50) -> Dict:
        """หา support และ resistance levels"""
        try:
            high = df['high'].tail(lookback)
            low = df['low'].tail(lookback)
            
            resistance_levels = []
            support_levels = []
            
            # หา pivot points
            for i in range(2, len(high) - 2):
                # Resistance
                if (high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and
                    high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]):
                    resistance_levels.append(high.iloc[i])
                
                # Support
                if (low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and
                    low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]):
                    support_levels.append(low.iloc[i])
            
            current_price = df['close'].iloc[-1]
            
            # กรองและเรียงลำดับ
            resistance_levels = sorted([r for r in resistance_levels if r > current_price])[:3]
            support_levels = sorted([s for s in support_levels if s < current_price], reverse=True)[:3]
            
            return {
                'support_levels': support_levels,
                'resistance_levels': resistance_levels,
                'nearest_support': support_levels[0] if support_levels else current_price * 0.99,
                'nearest_resistance': resistance_levels[0] if resistance_levels else current_price * 1.01
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ ข้อผิดพลาดในการหา S/R: {e}")
            current_price = df['close'].iloc[-1]
            return {
                'support_levels': [current_price * 0.99],
                'resistance_levels': [current_price * 1.01],
                'nearest_support': current_price * 0.99,
                'nearest_resistance': current_price * 1.01
            }
    
    def _consolidate_analysis(self, analysis: MarketAnalysis):
        """รวมผลการวิเคราะห์จากทุกไทม์เฟรม"""
        
        # รวม trend analysis
        trend_votes = {'BULLISH': 0, 'BEARISH': 0, 'SIDEWAYS': 0}
        total_adx = 0
        total_atr = 0
        
        for tf, tf_data in analysis.timeframe_analysis.items():
            if 'trend' in tf_data and tf_data['trend']:
                trend_dir = tf_data['trend']['direction'].value
                trend_votes[trend_dir] = trend_votes.get(trend_dir, 0) + 1
                total_adx += tf_data['trend'].get('adx_value', 0)
            
            if 'volatility' in tf_data and tf_data['volatility']:
                total_atr += tf_data['volatility'].get('atr_value', 0)
        
        # กำหนด trend หลัก
        max_votes = max(trend_votes.values()) if trend_votes.values() else 0
        for direction, votes in trend_votes.items():
            if votes == max_votes:
                analysis.trend_direction = TrendDirection(direction)
                break
        
        # คำนวณค่าเฉลี่ย
        num_timeframes = len(analysis.timeframe_analysis)
        if num_timeframes > 0:
            analysis.adx_value = total_adx / num_timeframes
            analysis.atr_value = total_atr / num_timeframes
            analysis.trend_strength = min(analysis.adx_value / 50, 1.0)
        
        # ใช้ข้อมูลจาก M15 เป็นหลัก
        if 'M15' in analysis.timeframe_analysis:
            m15_data = analysis.timeframe_analysis['M15']
            
            if 'momentum' in m15_data and m15_data['momentum']:
                momentum = m15_data['momentum']
                analysis.rsi_value = momentum.get('rsi', 50.0)
                analysis.macd_value = momentum.get('macd', 0.0)
                analysis.macd_signal = momentum.get('macd_signal', 0.0)
                analysis.stochastic_k = momentum.get('stoch_k', 50.0)
                analysis.stochastic_d = momentum.get('stoch_d', 50.0)
            
            if 'support_resistance' in m15_data and m15_data['support_resistance']:
                sr_data = m15_data['support_resistance']
                analysis.support_levels = sr_data.get('support_levels', [])
                analysis.resistance_levels = sr_data.get('resistance_levels', [])
            
            if 'volatility' in m15_data and m15_data['volatility']:
                analysis.volatility_level = m15_data['volatility'].get('level', 'NORMAL')
        
        # กำหนด market condition
        analysis.primary_condition = self._determine_market_condition(analysis)
    
    def _determine_market_condition(self, analysis: MarketAnalysis) -> MarketCondition:
        """กำหนดสภาพตลาดหลัก"""
        
        # ตรวจสอบ trend
        if analysis.adx_value > 25:
            if analysis.trend_strength > 0.7:
                return MarketCondition.TRENDING_STRONG
            else:
                return MarketCondition.TRENDING_WEAK
        
        # ตรวจสอบ volatility
        if analysis.volatility_level in ['HIGH', 'EXTREME']:
            return MarketCondition.VOLATILE_HIGH
        elif analysis.volatility_level == 'LOW':
            return MarketCondition.VOLATILE_LOW
        
        # ตรวจสอบ ranging
        if analysis.adx_value < 20:
            if analysis.volatility_level in ['HIGH', 'NORMAL']:
                return MarketCondition.RANGING_WIDE
            else:
                return MarketCondition.RANGING_TIGHT
        
        return MarketCondition.RANGING_TIGHT
    
    def _analyze_session_context(self, analysis: MarketAnalysis):
        """วิเคราะห์บริบทของ session"""
        current_session = self.session_manager.get_current_session()
        analysis.current_session = current_session
    
    def _recommend_strategies(self, analysis: MarketAnalysis):
        """แนะนำกลยุทธ์ตามสภาพตลาด"""
        
        condition_strategies = {
            MarketCondition.TRENDING_STRONG: [
                EntryStrategy.TREND_FOLLOWING,
                EntryStrategy.BREAKOUT_FALSE
            ],
            MarketCondition.TRENDING_WEAK: [
                EntryStrategy.TREND_FOLLOWING,
                EntryStrategy.MEAN_REVERSION
            ],
            MarketCondition.RANGING_TIGHT: [
                EntryStrategy.MEAN_REVERSION,
                EntryStrategy.SCALPING_ENGINE
            ],
            MarketCondition.RANGING_WIDE: [
                EntryStrategy.MEAN_REVERSION,
                EntryStrategy.BREAKOUT_FALSE
            ],
            MarketCondition.VOLATILE_HIGH: [
                EntryStrategy.BREAKOUT_FALSE,
                EntryStrategy.NEWS_REACTION
            ]
        }
        
        analysis.recommended_entry_strategies = condition_strategies.get(
            analysis.primary_condition,
            [EntryStrategy.MEAN_REVERSION]
        )
        
        # Recovery method
        if analysis.primary_condition in [MarketCondition.TRENDING_STRONG, MarketCondition.TRENDING_WEAK]:
            analysis.recommended_recovery_method = RecoveryMethod.GRID_INTELLIGENT
        elif analysis.primary_condition in [MarketCondition.RANGING_TIGHT, MarketCondition.RANGING_WIDE]:
            analysis.recommended_recovery_method = RecoveryMethod.AVERAGING_INTELLIGENT
        elif analysis.primary_condition == MarketCondition.VOLATILE_HIGH:
            analysis.recommended_recovery_method = RecoveryMethod.HEDGING_ADVANCED
        else:
            analysis.recommended_recovery_method = RecoveryMethod.MARTINGALE_SMART
    
    def _calculate_confidence(self, analysis: MarketAnalysis) -> float:
        """คำนวณความมั่นใจ"""
        confidence_factors = []
        
        # ADX strength
        if analysis.adx_value > 0:
            confidence_factors.append(min(analysis.adx_value / 50, 1.0))
        
        # RSI clarity
        if analysis.rsi_value != 50.0:
            rsi_clarity = abs(analysis.rsi_value - 50) / 50
            confidence_factors.append(rsi_clarity)
        
        # MACD clarity
        if analysis.macd_value != 0.0 and analysis.macd_signal != 0.0:
            macd_diff = abs(analysis.macd_value - analysis.macd_signal)
            macd_max = max(abs(analysis.macd_value), abs(analysis.macd_signal), 0.001)
            macd_clarity = min(macd_diff / macd_max, 1.0)
            confidence_factors.append(macd_clarity)
        
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
    
    def _convert_timeframe_to_mt5(self, timeframe: str) -> int:
        """แปลงไทม์เฟรมเป็นรูปแบบ MT5"""
        timeframe_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1
        }
        return timeframe_map.get(timeframe, mt5.TIMEFRAME_M15)
    
    def _analysis_loop(self):
        """ลูปการวิเคราะห์แบบเรียลไทม์"""
        while self.analysis_active:
            try:
                analysis = self.analyze_market()
                
                if analysis:
                    self.logger.debug(
                        f"📊 Market: {analysis.primary_condition.value} | "
                        f"Trend: {analysis.trend_direction.value} | "
                        f"ADX: {analysis.adx_value:.1f} | RSI: {analysis.rsi_value:.1f}"
                    )
                
                time.sleep(self.analysis_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Error in analysis loop: {e}")
                time.sleep(10)
    
    def get_current_analysis(self, force_update: bool = False) -> Optional[MarketAnalysis]:
        """ดึงผลการวิเคราะห์ปัจจุบัน"""
        if force_update or self.current_analysis is None:
            return self.analyze_market()
        return self.current_analysis
    
    def get_market_summary(self) -> Dict:
        """ดึงสรุปสภาพตลาด"""
        analysis = self.get_current_analysis()
        if not analysis:
            return {"error": "ไม่มีข้อมูลการวิเคราะห์"}
        
        return {
            "timestamp": analysis.timestamp.isoformat(),
            "current_price": analysis.current_price,
            "market_condition": analysis.primary_condition.value,
            "trend_direction": analysis.trend_direction.value,
            "trend_strength": round(analysis.trend_strength, 3),
            "volatility_level": analysis.volatility_level,
            "adx": round(analysis.adx_value, 2),
            "rsi": round(analysis.rsi_value, 1),
            "atr": round(analysis.atr_value, 5),
            "confidence": round(analysis.confidence_score, 3),
            "recommended_strategies": [s.value for s in analysis.recommended_entry_strategies],
            "recommended_recovery": analysis.recommended_recovery_method.value,
            "current_session": analysis.current_session.value if analysis.current_session else None
        }

# === GLOBAL INSTANCE ===
_global_market_analyzer: Optional[MarketAnalyzer] = None

def get_market_analyzer() -> MarketAnalyzer:
    """ดึง Market Analyzer แบบ Singleton"""
    global _global_market_analyzer
    if _global_market_analyzer is None:
        _global_market_analyzer = MarketAnalyzer()
        _global_market_analyzer.start_analysis()
    return _global_market_analyzer

def get_current_market_condition() -> Optional[MarketCondition]:
    """ดึงสภาพตลาดปัจจุบัน"""
    analyzer = get_market_analyzer()
    analysis = analyzer.get_current_analysis()
    return analysis.primary_condition if analysis else None

def get_trend_direction() -> Optional[TrendDirection]:
    """ดึงทิศทาง trend ปัจจุบัน"""
    analyzer = get_market_analyzer()
    analysis = analyzer.get_current_analysis()
    return analysis.trend_direction if analysis else None

def is_trending_market() -> bool:
    """ตรวจสอบว่าตลาดกำลัง trend หรือไม่"""
    condition = get_current_market_condition()
    return condition in [MarketCondition.TRENDING_STRONG, MarketCondition.TRENDING_WEAK] if condition else False

def get_recommended_strategies() -> List[EntryStrategy]:
    """ดึงกลยุทธ์ที่แนะนำ"""
    analyzer = get_market_analyzer()
    analysis = analyzer.get_current_analysis()
    return analysis.recommended_entry_strategies if analysis else [EntryStrategy.MEAN_REVERSION]