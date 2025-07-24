#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIGNAL GENERATOR - Real MT5 Data Entry Signal System
==================================================
ระบบสร้าง Entry Signals จากข้อมูลจริงของ MT5
เชื่อมต่อกับ MetaTrader 5 และวิเคราะห์ XAUUSD แบบเรียลไทม์

Key Features:
- เชื่อมต่อ MT5 API สำหรับข้อมูลจริง
- วิเคราะห์ Technical Indicators แบบเรียลไทม์
- สร้าง Entry Signals ตาม Market Conditions
- รองรับ Multi-Timeframe Analysis
- High-Frequency Signal Generation (50-100 lots/day)
- ไม่ใช้ Mock Data - ข้อมูลจริงเท่านั้น
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import threading
import time
import logging
import queue
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum

# Technical Analysis
try:
    import pandas_ta as ta
    TA_AVAILABLE = True
    print("✅ pandas_ta library available")
except ImportError:
    TA_AVAILABLE = False
    print("⚠️ pandas_ta not available - using manual calculations")
    print("Install with: pip install pandas_ta")

class SignalStrength(Enum):
    """ความแรงของ Signal"""
    VERY_WEAK = 1
    WEAK = 2
    MODERATE = 3
    STRONG = 4
    VERY_STRONG = 5

class SignalDirection(Enum):
    """ทิศทางของ Signal"""
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"

class MarketSession(Enum):
    """Market Session"""
    ASIAN = "ASIAN"
    LONDON = "LONDON"
    NY = "NY"
    OVERLAP = "OVERLAP"

class EntryStrategy(Enum):
    """Entry Strategy Types"""
    TREND_FOLLOWING = "TREND_FOLLOWING"
    MEAN_REVERSION = "MEAN_REVERSION"
    BREAKOUT_FALSE = "BREAKOUT_FALSE"
    NEWS_REACTION = "NEWS_REACTION"
    SCALPING_ENGINE = "SCALPING_ENGINE"

@dataclass
class MarketData:
    """ข้อมูลตลาดจาก MT5"""
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    tick_volume: int

@dataclass
class TechnicalIndicators:
    """Technical Indicators ที่คำนวณได้"""
    rsi: float = 50.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    adx: float = 25.0
    atr: float = 20.0
    bb_upper: float = 0.0
    bb_lower: float = 0.0
    bb_middle: float = 0.0
    ma_fast: float = 0.0
    ma_slow: float = 0.0
    stoch_k: float = 50.0
    stoch_d: float = 50.0

@dataclass
class EntrySignal:
    """Entry Signal จากข้อมูลจริง"""
    signal_id: str
    timestamp: datetime
    source_engine: EntryStrategy
    direction: SignalDirection
    strength: SignalStrength
    confidence: float
    current_price: float
    suggested_volume: float
    technical_indicators: Optional[Any] = None  # Made optional with default
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    signal_quality_score: float = 0.0
    risk_reward_ratio: float = 1.0
    probability_success: float = 0.5
    urgency_level: int = 1
    max_slippage_points: float = 2.0
    session: MarketSession = MarketSession.ASIAN
    market_volatility: str = "MEDIUM"
    additional_info: Dict[str, Any] = field(default_factory=dict)

class MT5DataProvider:
    """Provider สำหรับดึงข้อมูลจาก MT5"""
    
    def __init__(self):
        self.logger = logging.getLogger("MT5DataProvider")
        self.connected = False
        self.symbol = "XAUUSD.v"
        
    def initialize_mt5(self) -> bool:
        """เริ่มต้นการเชื่อมต่อ MT5"""
        try:
            if not mt5.initialize():
                self.logger.error(f"❌ MT5 initialization failed: {mt5.last_error()}")
                return False
            
            self.connected = True
            self.logger.info("✅ MT5 connected successfully")
            
            # ตรวจสอบ symbol
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None:
                self.logger.error(f"❌ Symbol {self.symbol} not found")
                return False
                
            if not symbol_info.visible:
                if not mt5.symbol_select(self.symbol, True):
                    self.logger.error(f"❌ Failed to select symbol {self.symbol}")
                    return False
            
            self.logger.info(f"✅ Symbol {self.symbol} ready")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ MT5 initialization error: {e}")
            return False
    
    def get_current_tick(self) -> Optional[Dict[str, Any]]:
        """ดึงข้อมูล tick ปัจจุบัน"""
        if not self.connected:
            return None
            
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            if tick is None:
                return None
                
            return {
                'time': datetime.fromtimestamp(tick.time),
                'bid': tick.bid,
                'ask': tick.ask,
                'last': tick.last,
                'volume': tick.volume,
                'spread': tick.ask - tick.bid
            }
        except Exception as e:
            self.logger.error(f"❌ Error getting tick: {e}")
            return None
    
    def get_historical_data(self, timeframe: str, count: int = 100) -> Optional[pd.DataFrame]:
        """ดึงข้อมูลประวัติราคา"""
        if not self.connected:
            return None
            
        try:
            # แปลง timeframe string เป็น MT5 constant
            tf_map = {
                'M1': mt5.TIMEFRAME_M1,
                'M5': mt5.TIMEFRAME_M5,
                'M15': mt5.TIMEFRAME_M15,
                'H1': mt5.TIMEFRAME_H1,
                'H4': mt5.TIMEFRAME_H4,
                'D1': mt5.TIMEFRAME_D1
            }
            
            mt5_timeframe = tf_map.get(timeframe, mt5.TIMEFRAME_M15)
            
            # ดึงข้อมูล
            rates = mt5.copy_rates_from_pos(self.symbol, mt5_timeframe, 0, count)
            if rates is None or len(rates) == 0:
                self.logger.warning(f"⚠️ No data for {self.symbol} {timeframe}")
                return None
            
            # แปลงเป็น DataFrame    
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error getting historical data: {e}")
            return None

class TechnicalAnalyzer:
    """วิเคราะห์ Technical Indicators"""
    
    def __init__(self):
        self.logger = logging.getLogger("TechnicalAnalyzer")
    
    def calculate_indicators(self, df: pd.DataFrame) -> TechnicalIndicators:
        """คำนวณ Technical Indicators"""
        try:
            if len(df) < 50:  # ต้องมีข้อมูลเพียงพอ
                return TechnicalIndicators()
            
            # สร้าง copy ของ DataFrame เพื่อไม่ให้กระทบของเดิม
            data = df.copy()
            
            indicators = TechnicalIndicators()
            
            # RSI
            if TA_AVAILABLE:
                data['rsi'] = ta.rsi(data['close'], length=14)
                indicators.rsi = data['rsi'].iloc[-1] if not pd.isna(data['rsi'].iloc[-1]) else 50.0
            else:
                indicators.rsi = self._manual_rsi(data['close'].values)
            
            # MACD
            if TA_AVAILABLE:
                macd_data = ta.macd(data['close'], fast=12, slow=26, signal=9)
                indicators.macd = macd_data['MACD_12_26_9'].iloc[-1] if not pd.isna(macd_data['MACD_12_26_9'].iloc[-1]) else 0.0
                indicators.macd_signal = macd_data['MACDs_12_26_9'].iloc[-1] if not pd.isna(macd_data['MACDs_12_26_9'].iloc[-1]) else 0.0
                indicators.macd_histogram = macd_data['MACDh_12_26_9'].iloc[-1] if not pd.isna(macd_data['MACDh_12_26_9'].iloc[-1]) else 0.0
            else:
                macd_data = self._manual_macd(data['close'].values)
                indicators.macd = macd_data['macd']
                indicators.macd_signal = macd_data['signal']
                indicators.macd_histogram = macd_data['histogram']
            
            # ADX
            if TA_AVAILABLE:
                adx_data = ta.adx(data['high'], data['low'], data['close'], length=14)
                indicators.adx = adx_data['ADX_14'].iloc[-1] if not pd.isna(adx_data['ADX_14'].iloc[-1]) else 25.0
            else:
                indicators.adx = self._manual_adx(data['high'].values, data['low'].values, data['close'].values)
            
            # ATR
            if TA_AVAILABLE:
                data['atr'] = ta.atr(data['high'], data['low'], data['close'], length=14)
                indicators.atr = data['atr'].iloc[-1] if not pd.isna(data['atr'].iloc[-1]) else 20.0
            else:
                indicators.atr = self._manual_atr(data['high'].values, data['low'].values, data['close'].values)
            
            # Bollinger Bands
            if TA_AVAILABLE:
                bb_data = ta.bbands(data['close'], length=20, std=2)
                indicators.bb_upper = bb_data['BBU_20_2.0'].iloc[-1] if not pd.isna(bb_data['BBU_20_2.0'].iloc[-1]) else data['close'].iloc[-1]
                indicators.bb_middle = bb_data['BBM_20_2.0'].iloc[-1] if not pd.isna(bb_data['BBM_20_2.0'].iloc[-1]) else data['close'].iloc[-1]
                indicators.bb_lower = bb_data['BBL_20_2.0'].iloc[-1] if not pd.isna(bb_data['BBL_20_2.0'].iloc[-1]) else data['close'].iloc[-1]
            else:
                bb_data = self._manual_bbands(data['close'].values)
                indicators.bb_upper = bb_data['upper']
                indicators.bb_middle = bb_data['middle']
                indicators.bb_lower = bb_data['lower']
            
            # Moving Averages
            if TA_AVAILABLE:
                data['ema_10'] = ta.ema(data['close'], length=10)
                data['ema_50'] = ta.ema(data['close'], length=50)
                indicators.ma_fast = data['ema_10'].iloc[-1] if not pd.isna(data['ema_10'].iloc[-1]) else data['close'].iloc[-1]
                indicators.ma_slow = data['ema_50'].iloc[-1] if not pd.isna(data['ema_50'].iloc[-1]) else data['close'].iloc[-1]
            else:
                indicators.ma_fast = data['close'].rolling(window=10).mean().iloc[-1]
                indicators.ma_slow = data['close'].rolling(window=50).mean().iloc[-1]
            
            # Stochastic
            if TA_AVAILABLE:
                stoch_data = ta.stoch(data['high'], data['low'], data['close'], k=14, d=3)
                indicators.stoch_k = stoch_data['STOCHk_14_3_3'].iloc[-1] if not pd.isna(stoch_data['STOCHk_14_3_3'].iloc[-1]) else 50.0
                indicators.stoch_d = stoch_data['STOCHd_14_3_3'].iloc[-1] if not pd.isna(stoch_data['STOCHd_14_3_3'].iloc[-1]) else 50.0
            else:
                stoch_data = self._manual_stoch(data['high'].values, data['low'].values, data['close'].values)
                indicators.stoch_k = stoch_data['k']
                indicators.stoch_d = stoch_data['d']
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"❌ Error calculating indicators: {e}")
            return TechnicalIndicators()
    
    def _manual_rsi(self, close: np.ndarray, period: int = 14) -> float:
        """คำนวณ RSI แบบ manual"""
        try:
            deltas = np.diff(close)
            gain = np.where(deltas > 0, deltas, 0)
            loss = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gain[-period:])
            avg_loss = np.mean(loss[-period:])
            
            if avg_loss == 0:
                return 100.0
                
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi)
        except:
            return 50.0
    
    def _manual_macd(self, close: np.ndarray) -> Dict[str, float]:
        """คำนวณ MACD แบบ manual"""
        try:
            exp1 = pd.Series(close).ewm(span=12).mean()
            exp2 = pd.Series(close).ewm(span=26).mean() 
            macd = exp1 - exp2
            signal = macd.ewm(span=9).mean()
            histogram = macd - signal
            
            return {
                'macd': float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0.0,
                'signal': float(signal.iloc[-1]) if not pd.isna(signal.iloc[-1]) else 0.0,
                'histogram': float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else 0.0
            }
        except:
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}
    
    def _manual_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float:
        """คำนวณ ATR แบบ manual"""
        try:
            tr1 = high - low
            tr2 = np.abs(high - np.roll(close, 1))
            tr3 = np.abs(low - np.roll(close, 1))
            
            tr = np.maximum(tr1, np.maximum(tr2, tr3))
            atr = np.mean(tr[-period:])
            return float(atr)
        except:
            return 20.0
    
    def _manual_adx(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float:
        """คำนวณ ADX แบบ manual (simplified)"""
        try:
            # ใช้การคำนวณแบบง่าย
            price_range = high - low
            avg_range = np.mean(price_range[-period:])
            
            # ประมาณ ADX จาก volatility
            volatility = avg_range / np.mean(close[-period:]) * 1000
            adx = min(volatility * 2, 100)  # Scale to 0-100
            return float(adx)
        except:
            return 25.0
    
    def _manual_bbands(self, close: np.ndarray, period: int = 20, std: float = 2.0) -> Dict[str, float]:
        """คำนวณ Bollinger Bands แบบ manual"""
        try:
            middle = np.mean(close[-period:])
            std_dev = np.std(close[-period:])
            
            return {
                'upper': float(middle + (std * std_dev)),
                'middle': float(middle),
                'lower': float(middle - (std * std_dev))
            }
        except:
            return {'upper': 0.0, 'middle': 0.0, 'lower': 0.0}
    
    def _manual_stoch(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> Dict[str, float]:
        """คำนวณ Stochastic แบบ manual"""
        try:
            lowest_low = np.min(low[-period:])
            highest_high = np.max(high[-period:])
            
            if highest_high == lowest_low:
                return {'k': 50.0, 'd': 50.0}
            
            k = 100 * (close[-1] - lowest_low) / (highest_high - lowest_low)
            
            # ใช้ k เป็น d แบบง่าย (ปกติต้องใช้ moving average)
            d = k
            
            return {'k': float(k), 'd': float(d)}
        except:
            return {'k': 50.0, 'd': 50.0}

class SignalAnalyzer:
    """วิเคราะห์และสร้าง Entry Signals"""
    
    def __init__(self):
        self.logger = logging.getLogger("SignalAnalyzer")
    
    def analyze_trend_following(self, indicators: TechnicalIndicators, current_price: float) -> Optional[EntrySignal]:
        """วิเคราะห์ Trend Following Signal - ปรับให้ออก signal ง่ายขึ้น"""
        try:
            # เงื่อนไข Trend Following (ผ่อนปรนให้ออก signal ง่ายขึ้น)
            signal_strength = SignalStrength.MODERATE
            direction = SignalDirection.NEUTRAL
            confidence = 0.6  # เริ่มต้นที่ 60%
            
            # ตรวจสอบ Trend จาก MA (เงื่อนไขง่ายขึ้น)
            ma_trend_strength = abs(indicators.ma_fast - indicators.ma_slow) / indicators.ma_slow * 1000
            
            if indicators.ma_fast > indicators.ma_slow:
                # Uptrend - ลอง BUY (เงื่อนไขผ่อนปรน)
                if indicators.rsi < 75:  # ผ่อนปรนจาก 70 → 75
                    direction = SignalDirection.BUY
                    confidence = 0.65
                    
                    # เพิ่ม confidence ตาม indicators
                    if indicators.macd > indicators.macd_signal:
                        confidence += 0.1
                    if indicators.adx > 20:  # ลดจาก 25 → 20
                        confidence += 0.1
                        signal_strength = SignalStrength.STRONG
                    if ma_trend_strength > 5:  # Trend ชัด
                        confidence += 0.05
            
            elif indicators.ma_fast < indicators.ma_slow:
                # Downtrend - ลอง SELL (เงื่อนไขผ่อนปรน)
                if indicators.rsi > 25:  # ผ่อนปรนจาก 30 → 25
                    direction = SignalDirection.SELL
                    confidence = 0.65
                    
                    # เพิ่ม confidence ตาม indicators
                    if indicators.macd < indicators.macd_signal:
                        confidence += 0.1
                    if indicators.adx > 20:  # ลดจาก 25 → 20
                        confidence += 0.1
                        signal_strength = SignalStrength.STRONG
                    if ma_trend_strength > 5:  # Trend ชัด
                        confidence += 0.05
            
            # ลด threshold การผ่าน (จาก 0.6 → 0.55)
            if direction != SignalDirection.NEUTRAL and confidence >= 0.55:
                signal_id = f"TREND_{datetime.now().strftime('%H%M%S')}"
                
                return EntrySignal(
                    signal_id=signal_id,
                    timestamp=datetime.now(),
                    source_engine=EntryStrategy.TREND_FOLLOWING,
                    direction=direction,
                    strength=signal_strength,
                    confidence=min(confidence, 0.95),  # Cap ที่ 95%
                    current_price=current_price,
                    suggested_volume=0.01,
                    technical_indicators=indicators,
                    signal_quality_score=confidence * 100,
                    risk_reward_ratio=2.0,
                    probability_success=confidence,
                    session=self._get_current_session()
                )
                
        except Exception as e:
            self.logger.error(f"❌ Error analyzing trend following: {e}")
        
        return None
    
    def analyze_mean_reversion(self, indicators: TechnicalIndicators, current_price: float) -> Optional[EntrySignal]:
        """วิเคราะห์ Mean Reversion Signal - ปรับให้ออก signal ง่ายขึ้น"""
        try:
            signal_strength = SignalStrength.MODERATE
            direction = SignalDirection.NEUTRAL
            confidence = 0.6  # เริ่มต้นสูงขึ้น
            
            # เงื่อนไข Mean Reversion (ผ่อนปรนมาก)
            if indicators.rsi > 65:  # ลดจาก 70 → 65 (Overbought)
                direction = SignalDirection.SELL
                confidence = 0.65
                
                if current_price > indicators.bb_middle:  # ไม่ต้องทะลุ upper band
                    confidence += 0.05
                if indicators.stoch_k > 70:  # ลดจาก 80 → 70
                    confidence += 0.05
                    signal_strength = SignalStrength.STRONG
                if indicators.rsi > 75:  # Very overbought
                    confidence += 0.1
            
            elif indicators.rsi < 35:  # เพิ่มจาก 30 → 35 (Oversold)
                direction = SignalDirection.BUY
                confidence = 0.65
                
                if current_price < indicators.bb_middle:  # ไม่ต้องทะลุ lower band
                    confidence += 0.05
                if indicators.stoch_k < 30:  # เพิ่มจาก 20 → 30
                    confidence += 0.05
                    signal_strength = SignalStrength.STRONG
                if indicators.rsi < 25:  # Very oversold
                    confidence += 0.1
            
            # Moderate Mean Reversion (เพิ่ม cases ใหม่)
            elif 55 < indicators.rsi < 65 and indicators.macd_histogram < 0:
                # ราคาเริ่มกลับตัว
                direction = SignalDirection.SELL
                confidence = 0.55
                
            elif 35 < indicators.rsi < 45 and indicators.macd_histogram > 0:
                # ราคาเริ่มกลับตัว
                direction = SignalDirection.BUY
                confidence = 0.55
            
            # ลด threshold (จาก 0.6 → 0.52)
            if direction != SignalDirection.NEUTRAL and confidence >= 0.52:
                signal_id = f"MEAN_{datetime.now().strftime('%H%M%S')}"
                
                return EntrySignal(
                    signal_id=signal_id,
                    timestamp=datetime.now(),
                    source_engine=EntryStrategy.MEAN_REVERSION,
                    direction=direction,
                    strength=signal_strength,
                    confidence=min(confidence, 0.95),
                    current_price=current_price,
                    suggested_volume=0.01,
                    technical_indicators=indicators,
                    signal_quality_score=confidence * 100,
                    risk_reward_ratio=1.5,
                    probability_success=confidence,
                    session=self._get_current_session()
                )
                
        except Exception as e:
            self.logger.error(f"❌ Error analyzing mean reversion: {e}")
        
        return None
    
    def analyze_breakout_signals(self, indicators: TechnicalIndicators, current_price: float) -> Optional[EntrySignal]:
        """วิเคราะห์ Breakout Signals"""
        try:
            signal_strength = SignalStrength.MODERATE
            direction = SignalDirection.NEUTRAL
            confidence = 0.5
            
            # Bollinger Band Breakout
            bb_width = indicators.bb_upper - indicators.bb_lower
            if bb_width > 0:
                bb_position = (current_price - indicators.bb_lower) / bb_width
                
                if bb_position > 1.0:  # ราคาทะลุ Upper Band
                    if indicators.adx > 20 and indicators.atr > 15:  # มี momentum
                        direction = SignalDirection.BUY
                        confidence = 0.7
                        signal_strength = SignalStrength.STRONG
                
                elif bb_position < 0.0:  # ราคาทะลุ Lower Band
                    if indicators.adx > 20 and indicators.atr > 15:  # มี momentum
                        direction = SignalDirection.SELL
                        confidence = 0.7
                        signal_strength = SignalStrength.STRONG
            
            if direction != SignalDirection.NEUTRAL and confidence >= 0.6:
                signal_id = f"BREAK_{datetime.now().strftime('%H%M%S')}"
                
                return EntrySignal(
                    signal_id=signal_id,
                    timestamp=datetime.now(),
                    source_engine=EntryStrategy.BREAKOUT_FALSE,
                    direction=direction,
                    strength=signal_strength,
                    confidence=confidence,
                    current_price=current_price,
                    suggested_volume=0.02,
                    technical_indicators=indicators,  # Pass the full TechnicalIndicators object
                    signal_quality_score=confidence * 100,
                    risk_reward_ratio=2.5,
                    probability_success=confidence,
                    session=self._get_current_session()
                )
                
        except Exception as e:
            self.logger.error(f"❌ Error analyzing breakout: {e}")
        
        return None
    
    def _get_current_session(self) -> MarketSession:
        """ดึง Market Session ปัจจุบัน"""
        current_hour = datetime.now().hour
        
        if 22 <= current_hour or current_hour < 8:
            return MarketSession.ASIAN
        elif 15 <= current_hour < 20:
            return MarketSession.LONDON
        elif 20 <= current_hour < 22:
            return MarketSession.OVERLAP
        else:
            return MarketSession.NY

class SignalGenerator:
    """
    🎯 Real MT5 Data Signal Generator
    
    สร้าง Entry Signals จากข้อมูลจริงของ MT5
    """
    
    def __init__(self):
        # Setup logger
        self.logger = logging.getLogger("SignalGenerator")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Core Components
        self.mt5_provider = MT5DataProvider()
        self.technical_analyzer = TechnicalAnalyzer()
        self.signal_analyzer = SignalAnalyzer()
        
        # System Status
        self.generator_active = False
        self.is_ready = False
        
        # Signal Storage
        self.active_signals: List[EntrySignal] = []
        self.signal_history: List[EntrySignal] = []
        self.signal_queue = queue.Queue()
        
        # Statistics
        self.signals_generated_today = 0
        self.signals_executed_today = 0
        
        # Threading
        self.generator_thread = None
        self.signal_monitor_thread = None
        
        # Timing Control
        self.last_signal_time = datetime.now()
        self.min_signal_interval = timedelta(seconds=10)  # ลดจาก 30 → 10 วินาที
        
        self.logger.info("🎯 Real MT5 Signal Generator initialized")
    
    def start_signal_generation(self) -> None:
        """เริ่มต้นการสร้าง Signals จากข้อมูลจริง"""
        if self.generator_active:
            self.logger.warning("⚠️ Signal Generator กำลังทำงานอยู่แล้ว")
            return
        
        self.logger.info("🚀 Starting Real MT5 Signal Generation System")
        
        # เชื่อมต่อ MT5
        if not self.mt5_provider.initialize_mt5():
            self.logger.error("❌ Cannot connect to MT5 - Signal Generator NOT READY")
            self.is_ready = False
            return
        
        # เริ่มต้นระบบ
        self.generator_active = True
        self.is_ready = True
        
        # เริ่ม Threading
        self.generator_thread = threading.Thread(
            target=self._real_signal_generation_loop,
            daemon=True,
            name="RealSignalGenerationLoop"
        )
        
        self.signal_monitor_thread = threading.Thread(
            target=self._signal_monitor_loop,
            daemon=True,
            name="SignalMonitorLoop"
        )
        
        self.generator_thread.start()
        self.signal_monitor_thread.start()
        
        self.logger.info("✅ Real MT5 Signal Generation System started successfully")
    
    def stop_signal_generation(self) -> None:
        """หยุดการสร้าง Signals"""
        self.logger.info("🛑 Stopping Real Signal Generation System")
        
        self.generator_active = False
        self.is_ready = False
        
        # รอ threads ปิด
        if self.generator_thread and self.generator_thread.is_alive():
            self.generator_thread.join(timeout=5.0)
        
        if self.signal_monitor_thread and self.signal_monitor_thread.is_alive():
            self.signal_monitor_thread.join(timeout=5.0)
        
        # ปิด MT5
        try:
            mt5.shutdown()
        except:
            pass
        
        self.logger.info("✅ Real Signal Generation System stopped")
    
    def _real_signal_generation_loop(self):
        """Loop หลักสำหรับการสร้าง Signals จากข้อมูลจริง"""
        self.logger.info("🔄 Real signal generation loop started")
        
        while self.generator_active:
            try:
                # ตรวจสอบเงื่อนไขการสร้าง Signal
                if self._should_generate_signal():
                    # ดึงข้อมูลจาก MT5
                    current_tick = self.mt5_provider.get_current_tick()
                    if current_tick is None:
                        self.logger.warning("⚠️ No tick data from MT5")
                        time.sleep(5)
                        continue
                    
                    # ดึงข้อมูลประวัติราคา
                    df_m15 = self.mt5_provider.get_historical_data("M15", 100)
                    if df_m15 is None or len(df_m15) < 50:
                        self.logger.warning("⚠️ Insufficient historical data")
                        time.sleep(10)
                        continue
                    
                    # คำนวณ Technical Indicators
                    indicators = self.technical_analyzer.calculate_indicators(df_m15)
                    
                    # วิเคราะห์และสร้าง Signals
                    signals = self._analyze_and_create_signals(indicators, current_tick['ask'])
                    
                    # เพิ่ม Signals ที่ได้
                    for signal in signals:
                        if signal:
                            self._add_real_signal(signal)
                            self.signals_generated_today += 1
                            self.last_signal_time = datetime.now()
                            
                            self.logger.info(f"📨 New Real Signal: {signal.signal_id} | "
                                           f"{signal.direction.value} | "
                                           f"Price: {signal.current_price:.2f} | "
                                           f"Confidence: {signal.confidence:.2f}")
                
                # รอก่อนการตรวจสอบครั้งต่อไป
                time.sleep(15)  # ตรวจสอบทุก 15 วินาที
                
            except Exception as e:
                self.logger.error(f"❌ Error in real signal generation loop: {e}")
                time.sleep(30)  # รอนานขึ้นเมื่อมี error
    
    def _analyze_and_create_signals(self, indicators: TechnicalIndicators, current_price: float) -> List[Optional[EntrySignal]]:
        """วิเคราะห์และสร้าง Signals จาก indicators"""
        signals = []
        
        try:
            # วิเคราะห์ Trend Following
            trend_signal = self.signal_analyzer.analyze_trend_following(indicators, current_price)
            if trend_signal:
                signals.append(trend_signal)
            
            # วิเคราะห์ Mean Reversion  
            mean_signal = self.signal_analyzer.analyze_mean_reversion(indicators, current_price)
            if mean_signal:
                signals.append(mean_signal)
            
            # วิเคราะห์ Breakout
            breakout_signal = self.signal_analyzer.analyze_breakout_signals(indicators, current_price)
            if breakout_signal:
                signals.append(breakout_signal)
            
            # เพิ่ม Scalping Signal (สำหรับ High Frequency) - เสมอ!
            scalping_signal = self._create_scalping_signal(indicators, current_price)
            if scalping_signal:
                signals.append(scalping_signal)
                    
        except Exception as e:
            self.logger.error(f"❌ Error analyzing signals: {e}")
        
        return signals
    
    def _create_scalping_signal(self, indicators: TechnicalIndicators, current_price: float) -> Optional[EntrySignal]:
        """สร้าง Scalping Signal สำหรับ High Frequency - ออก signal ง่ายมาก"""
        try:
            # เงื่อนไข Scalping แบบง่ายมาก (เพื่อ volume)
            direction = SignalDirection.NEUTRAL
            confidence = 0.55  # confidence ต่ำแต่พอใช้
            
            # Strategy 1: MACD Histogram Scalping
            if indicators.macd_histogram > 0:
                if indicators.rsi < 65:  # ไม่ overbought มาก
                    direction = SignalDirection.BUY
                    confidence = 0.58
            elif indicators.macd_histogram < 0:
                if indicators.rsi > 35:  # ไม่ oversold มาก
                    direction = SignalDirection.SELL
                    confidence = 0.58
            
            # Strategy 2: Price vs MA Scalping (ถ้ายังไม่มี signal)
            if direction == SignalDirection.NEUTRAL:
                if current_price > indicators.ma_fast:
                    direction = SignalDirection.BUY
                    confidence = 0.55
                elif current_price < indicators.ma_fast:
                    direction = SignalDirection.SELL
                    confidence = 0.55
            
            # Strategy 3: Stochastic Quick Scalping (ถ้ายังไม่มี signal)
            if direction == SignalDirection.NEUTRAL:
                if indicators.stoch_k < 50 and indicators.stoch_d < 50:
                    direction = SignalDirection.BUY
                    confidence = 0.52
                elif indicators.stoch_k > 50 and indicators.stoch_d > 50:
                    direction = SignalDirection.SELL
                    confidence = 0.52
            
            # Strategy 4: Random Walk Scalping (สุดท้าย - เพื่อให้ได้ volume)
            if direction == SignalDirection.NEUTRAL:
                # ใช้ second ปัจจุบันเป็นตัวกำหนด
                current_second = datetime.now().second
                if current_second % 2 == 0:  # เลขคู่
                    direction = SignalDirection.BUY
                else:  # เลขคี่
                    direction = SignalDirection.SELL
                confidence = 0.51  # confidence ต่ำสุดที่ยอมรับได้
            
            # ส่ง signal เมื่อมี direction (จะมีเสมอ)
            if direction != SignalDirection.NEUTRAL:
                signal_id = f"SCALP_{datetime.now().strftime('%H%M%S')}"
                
                return EntrySignal(
                    signal_id=signal_id,
                    timestamp=datetime.now(),
                    source_engine=EntryStrategy.SCALPING_ENGINE,
                    direction=direction,
                    strength=SignalStrength.MODERATE,
                    confidence=confidence,
                    current_price=current_price,
                    suggested_volume=0.01,
                    technical_indicators=indicators,
                    signal_quality_score=confidence * 100,
                    risk_reward_ratio=1.2,
                    probability_success=confidence,
                    session=self.signal_analyzer._get_current_session(),
                    market_conditions={
                        'volatility': 'MEDIUM' if indicators.atr < 25 else 'HIGH',
                        'trend': 'BULLISH' if indicators.ma_fast > indicators.ma_slow else 'BEARISH',
                        'scalping_type': 'HIGH_FREQUENCY'
                    }
                )
                
        except Exception as e:
            self.logger.error(f"❌ Error creating scalping signal: {e}")
        
        return None
    
    def _should_generate_signal(self) -> bool:
        """ตรวจสอบว่าควรสร้าง Signal หรือไม่"""
        # ตรวจสอบเวลาผ่านมาเพียงพอหรือไม่
        time_since_last = datetime.now() - self.last_signal_time
        if time_since_last < self.min_signal_interval:
            return False
        
        # ตรวจสอบจำนวน signals ที่มีอยู่
        if len(self.active_signals) > 10:  # ไม่เก็บ signals เกิน 10 อัน
            return False
        
        # ตรวจสอบ MT5 connection
        if not self.mt5_provider.connected:
            return False
        
        return True
    
    def _add_real_signal(self, signal: EntrySignal):
        """เพิ่ม Real Signal เข้าระบบ"""
        try:
            # เพิ่มเข้า queue และ list
            self.signal_queue.put(signal)
            self.active_signals.append(signal)
            self.signal_history.append(signal)
            
            # Log signal details
            self.logger.info(f"📨 Real Signal Added: {signal.signal_id}")
            self.logger.info(f"   Direction: {signal.direction.value}")
            self.logger.info(f"   Strategy: {signal.source_engine.value}")
            self.logger.info(f"   Price: {signal.current_price:.2f}")
            self.logger.info(f"   Confidence: {signal.confidence:.2f}")
            if signal.technical_indicators:
                self.logger.info(f"   RSI: {signal.technical_indicators.rsi:.1f}")
                self.logger.info(f"   MACD: {signal.technical_indicators.macd:.4f}")
                self.logger.info(f"   ADX: {signal.technical_indicators.adx:.1f}")
            else:
                self.logger.info(f"   Technical Indicators: Not available")
            
        except Exception as e:
            self.logger.error(f"❌ Error adding real signal: {e}")
    
    def _signal_monitor_loop(self):
        """Loop สำหรับติดตาม Signal stats"""
        self.logger.info("📊 Signal monitor loop started")
        
        while self.generator_active:
            try:
                # อัพเดท statistics
                self._update_statistics()
                
                # ทำความสะอาด signals เก่า
                self._cleanup_old_signals()
                
                # ตรวจสอบ MT5 connection status
                self._check_mt5_connection()
                
                # รอ 60 วินาที
                time.sleep(60)
                
            except Exception as e:
                self.logger.error(f"❌ Error in signal monitor: {e}")
                time.sleep(120)
    
    def _check_mt5_connection(self):
        """ตรวจสอบสถานะการเชื่อมต่อ MT5"""
        try:
            # ทดสอบการเชื่อมต่อด้วยการดึง tick
            tick = self.mt5_provider.get_current_tick()
            if tick is None:
                self.logger.warning("⚠️ MT5 connection issue detected")
                self.mt5_provider.connected = False
                
                # พยายาม reconnect
                if self.mt5_provider.initialize_mt5():
                    self.logger.info("✅ MT5 reconnected successfully")
                else:
                    self.logger.error("❌ MT5 reconnection failed")
                    self.is_ready = False
            else:
                if not self.mt5_provider.connected:
                    self.mt5_provider.connected = True
                    self.is_ready = True
                    self.logger.info("✅ MT5 connection restored")
                    
        except Exception as e:
            self.logger.error(f"❌ Error checking MT5 connection: {e}")
    
    def _update_statistics(self):
        """อัพเดท Statistics"""
        active_count = len(self.active_signals)
        total_generated = self.signals_generated_today
        
        # Log stats ทุก 10 minutes
        if datetime.now().minute % 10 == 0:
            self.logger.info(f"📊 Real Signal Stats:")
            self.logger.info(f"   Active Signals: {active_count}")
            self.logger.info(f"   Generated Today: {total_generated}")
            self.logger.info(f"   MT5 Connected: {self.mt5_provider.connected}")
            self.logger.info(f"   System Ready: {self.is_ready}")
            
            # แสดง latest signal ถ้ามี
            if self.active_signals:
                latest = self.active_signals[-1]
                self.logger.info(f"   Latest Signal: {latest.signal_id} ({latest.direction.value})")
    
    def _cleanup_old_signals(self):
        """ลบ Signals เก่า"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(minutes=15)  # เก็บแค่ 15 นาที
        
        # กรอง active signals
        old_count = len(self.active_signals)
        self.active_signals = [
            signal for signal in self.active_signals 
            if signal.timestamp > cutoff_time
        ]
        new_count = len(self.active_signals)
        
        if old_count != new_count:
            self.logger.debug(f"🧹 Cleaned up {old_count - new_count} old signals")
    
    def get_system_status(self) -> Dict[str, Any]:
        """ดึงสถานะระบบ"""
        current_tick = self.mt5_provider.get_current_tick() if self.mt5_provider.connected else None
        
        return {
            "is_ready": self.is_ready,
            "generator_active": self.generator_active,
            "mt5_connected": self.mt5_provider.connected,
            "active_signals": len(self.active_signals),
            "signals_generated_today": self.signals_generated_today,
            "signals_executed_today": self.signals_executed_today,
            "last_signal_time": self.last_signal_time.isoformat() if self.last_signal_time else None,
            "current_price": current_tick['ask'] if current_tick else 0.0,
            "current_bid": current_tick['bid'] if current_tick else 0.0,
            "current_spread": current_tick['spread'] if current_tick else 0.0,
            "symbol": self.mt5_provider.symbol
        }
    
    def get_latest_signals(self, limit: int = 5) -> List[Dict[str, Any]]:
        """ดึง Signals ล่าสุด"""
        latest_signals = sorted(self.active_signals, 
                              key=lambda x: x.timestamp, 
                              reverse=True)[:limit]
        
        return [
            {
                "signal_id": signal.signal_id,
                "timestamp": signal.timestamp.isoformat(),
                "direction": signal.direction.value,
                "strength": signal.strength.value,
                "confidence": signal.confidence,
                "price": signal.current_price,
                "strategy": signal.source_engine.value,
                "quality_score": signal.signal_quality_score,
                "rsi": signal.technical_indicators.rsi if signal.technical_indicators else 50.0,
                "macd": signal.technical_indicators.macd if signal.technical_indicators else 0.0,
                "adx": signal.technical_indicators.adx if signal.technical_indicators else 25.0,
                "session": signal.session.value
            }
            for signal in latest_signals
        ]
    
    def get_mt5_market_info(self) -> Dict[str, Any]:
        """ดึงข้อมูลตลาดจาก MT5"""
        if not self.mt5_provider.connected:
            return {"error": "MT5 not connected"}
        
        try:
            # ข้อมูล Symbol
            symbol_info = mt5.symbol_info(self.mt5_provider.symbol)
            if symbol_info is None:
                return {"error": "Symbol info not available"}
            
            # ข้อมูล Tick ปัจจุบัน
            current_tick = self.mt5_provider.get_current_tick()
            
            # ข้อมูล Account
            account_info = mt5.account_info()
            
            return {
                "symbol": {
                    "name": symbol_info.name,
                    "digits": symbol_info.digits,
                    "point": symbol_info.point,
                    "spread": symbol_info.spread,
                    "contract_size": symbol_info.trade_contract_size,
                    "min_volume": symbol_info.volume_min,
                    "max_volume": symbol_info.volume_max,
                    "volume_step": symbol_info.volume_step
                },
                "current_price": current_tick if current_tick else {},
                "account": {
                    "login": account_info.login if account_info else 0,
                    "balance": account_info.balance if account_info else 0.0,
                    "equity": account_info.equity if account_info else 0.0,
                    "margin": account_info.margin if account_info else 0.0,
                    "free_margin": account_info.margin_free if account_info else 0.0,
                    "currency": account_info.currency if account_info else "USD",
                    "server": account_info.server if account_info else "Unknown"
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error getting MT5 market info: {e}")
            return {"error": str(e)}
    
    def force_generate_signal(self) -> Dict[str, Any]:
        """บังคับสร้าง Signal (สำหรับการทดสอบ)"""
        try:
            if not self.mt5_provider.connected:
                return {"success": False, "error": "MT5 not connected"}
            
            # ดึงข้อมูลจาก MT5
            current_tick = self.mt5_provider.get_current_tick()
            if current_tick is None:
                return {"success": False, "error": "No tick data"}
            
            df_m15 = self.mt5_provider.get_historical_data("M15", 100)
            if df_m15 is None or len(df_m15) < 50:
                return {"success": False, "error": "Insufficient historical data"}
            
            # คำนวณ indicators
            indicators = self.technical_analyzer.calculate_indicators(df_m15)
            
            # สร้าง signals
            signals = self._analyze_and_create_signals(indicators, current_tick['ask'])
            
            signal_count = 0
            for signal in signals:
                if signal:
                    self._add_real_signal(signal)
                    self.signals_generated_today += 1
                    signal_count += 1
            
            if signal_count > 0:
                return {
                    "success": True, 
                    "signals_generated": signal_count,
                    "price": current_tick['ask']
                }
            else:
                return {
                    "success": False, 
                    "error": "No valid signals generated",
                    "indicators": {
                        "rsi": indicators.rsi,
                        "macd": indicators.macd,
                        "adx": indicators.adx
                    }
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error force generating signal: {e}")
    def get_next_entry_signal(self) -> Optional[EntrySignal]:
        """ดึง Entry Signal ถัดไป (เพื่อ compatibility กับระบบเดิม)"""
        return self.get_next_signal()
    
    def get_next_signal(self) -> Optional[EntrySignal]:
        """ดึง Signal ถัดไป"""
        try:
            return self.signal_queue.get_nowait()
        except queue.Empty:
            return None

# Global instance
_signal_generator_instance = None

def get_signal_generator():
    """ได้ Real Signal Generator instance"""
    global _signal_generator_instance
    if _signal_generator_instance is None:
        _signal_generator_instance = SignalGenerator()
    return _signal_generator_instance

# เพื่อใช้กับระบบอื่น
def setup_component_logger(name: str):
    """Setup logger สำหรับ component"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

# === INSTALLATION CHECK ===
def check_requirements():
    """ตรวจสอบ Requirements"""
    missing = []
    
    try:
        import MetaTrader5
        print("✅ MetaTrader5 library available")
    except ImportError:
        missing.append("MetaTrader5")
    
    try:
        import pandas
        print("✅ pandas available")
    except ImportError:
        missing.append("pandas")
    
    try:
        import numpy
        print("✅ numpy available")
    except ImportError:
        missing.append("numpy")
    
    try:
        import pandas_ta
        print("✅ pandas_ta available")
    except ImportError:
        print("⚠️ pandas_ta not available - will use manual calculations")
        print("   Install with: pip install pandas_ta")
    
    if missing:
        print(f"\n❌ Missing requirements: {', '.join(missing)}")
        print("Install with: pip install MetaTrader5 pandas numpy pandas_ta")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Real MT5 Signal Generator Test")
    print("=" * 50)
    
    # ตรวจสอบ requirements
    if not check_requirements():
        print("❌ Requirements not met!")
        exit(1)
    
    # ทดสอบ Signal Generator
    generator = SignalGenerator()
    
    print("\n🔌 Testing MT5 Connection...")
    if not generator.mt5_provider.initialize_mt5():
        print("❌ Cannot connect to MT5!")
        print("Please make sure:")
        print("1. MetaTrader 5 is running")
        print("2. You are logged into your account")
        print("3. AutoTrading is enabled")
        print("4. XAUUSD symbol is available")
        exit(1)
    
    print("✅ MT5 Connected successfully!")
    
    # แสดงข้อมูลตลาด
    market_info = generator.get_mt5_market_info()
    if "error" not in market_info:
        print(f"\n📊 Market Info:")
        print(f"   Account: {market_info['account']['login']}")
        print(f"   Balance: ${market_info['account']['balance']:,.2f}")
        print(f"   Server: {market_info['account']['server']}")
        
        if market_info['current_price']:
            price = market_info['current_price']
            print(f"   XAUUSD: Bid={price['bid']:.2f}, Ask={price['ask']:.2f}")
    
    # เริ่มต้น Signal Generation
    print(f"\n🚀 Starting Real Signal Generation...")
    generator.start_signal_generation()
    
    if generator.is_ready:
        print("✅ Signal Generator is READY!")
        print("📡 Generating signals from real MT5 data...")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                status = generator.get_system_status()
                print(f"\n📊 Status: Ready={status['is_ready']}, "
                      f"Signals={status['active_signals']}, "
                      f"Price={status['current_price']:.2f}")
                
                # แสดง signals ล่าสุด
                latest = generator.get_latest_signals(3)
                for signal in latest:
                    print(f"   Signal: {signal['signal_id']} | "
                          f"{signal['direction']} | "
                          f"Strategy: {signal['strategy']} | "
                          f"Confidence: {signal['confidence']:.2f}")
                
                # ทดสอบ force generate
                if status['active_signals'] == 0:
                    print("🔄 Attempting to force generate signal...")
                    result = generator.force_generate_signal()
                    if result['success']:
                        print(f"✅ Generated {result['signals_generated']} signals")
                    else:
                        print(f"❌ Force generate failed: {result['error']}")
                
                time.sleep(30)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping Signal Generator...")
            generator.stop_signal_generation()
            print("✅ Stopped successfully")
    
    else:
        print("❌ Signal Generator NOT READY!")
        generator.stop_signal_generation()