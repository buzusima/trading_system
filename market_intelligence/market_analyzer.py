#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKET ANALYZER - ระบบวิเคราะห์ตลาดอัจฉริยะ
===========================================
ระบบวิเคราะห์สถานการณ์ตลาดแบบเรียลไทม์สำหรับ XAUUSD
รองรับการตรวจจับเทรนด์, volatility, และสภาวะตลาดต่างๆ

🎯 ฟีเจอร์หลัก:
- ตรวจจับทิศทางเทรนด์ (Trend Direction)
- วิเคราะห์ความผันผวน (Volatility Analysis)
- ระบุสภาวะตลาด (Market Condition)
- การวิเคราะห์หลายไทม์เฟรม (Multi-Timeframe)
- การติดตาม Session Trading
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

# Enums for market analysis
class TrendDirection(Enum):
    """ทิศทางเทรนด์"""
    STRONG_UPTREND = "เทรนด์ขึ้นแรง"
    UPTREND = "เทรนด์ขึ้น"
    SIDEWAYS = "เทรนด์ข้าง"
    DOWNTREND = "เทรนด์ลง"
    STRONG_DOWNTREND = "เทรนด์ลงแรง"
    UNCERTAIN = "ไม่แน่นอน"

class MarketCondition(Enum):
    """สภาวะตลาด"""
    TRENDING = "Trending"
    RANGING = "Ranging"
    VOLATILE = "Volatile"
    QUIET = "Quiet"
    NEWS_IMPACT = "News Impact"
    BREAKOUT = "Breakout"

class TradingSession(Enum):
    """เซสชันการเทรด"""
    ASIAN = "Asian"
    LONDON = "London"
    NEW_YORK = "New York"
    OVERLAP = "Overlap"
    CLOSED = "Market Closed"

class VolatilityLevel(Enum):
    """ระดับความผันผวน"""
    VERY_LOW = "ต่ำมาก"
    LOW = "ต่ำ"
    NORMAL = "ปกติ"
    HIGH = "สูง"
    VERY_HIGH = "สูงมาก"

@dataclass
class MarketData:
    """ข้อมูลตลาดพื้นฐาน"""
    symbol: str = "XAUUSD.v"
    timeframe: str = "M5"
    timestamp: datetime = field(default_factory=datetime.now)
    
    # ข้อมูลราคา
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    
    # ข้อมูล Spread
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0

@dataclass
class TechnicalIndicators:
    """ตัวชี้วัดทางเทคนิค"""
    # Moving Averages
    sma_20: float = 0.0
    sma_50: float = 0.0
    ema_20: float = 0.0
    ema_50: float = 0.0
    
    # Trend Indicators
    adx: float = 0.0
    adx_plus: float = 0.0
    adx_minus: float = 0.0
    
    # Volatility Indicators
    atr: float = 0.0
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    bb_width: float = 0.0
    
    # Momentum Indicators
    rsi: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0

@dataclass
class MarketAnalysis:
    """ผลการวิเคราะห์ตลาด"""
    timestamp: datetime = field(default_factory=datetime.now)
    symbol: str = "XAUUSD.v"
    
    # การวิเคราะห์หลัก
    trend_direction: TrendDirection = TrendDirection.UNCERTAIN
    market_condition: MarketCondition = MarketCondition.RANGING
    trading_session: TradingSession = TradingSession.ASIAN
    volatility_level: VolatilityLevel = VolatilityLevel.NORMAL
    
    # คะแนนความแข็งแกร่ง
    trend_strength: float = 0.0  # 0-100
    volatility_score: float = 0.0  # 0-100
    momentum_score: float = 0.0  # 0-100
    
    # ข้อมูลสำคัญ
    current_price: float = 0.0
    support_level: float = 0.0
    resistance_level: float = 0.0
    
    # แนะนำการเทรด
    trade_recommendation: str = "รอสัญญาณ"
    confidence_level: float = 0.0  # 0-100

class MarketAnalyzer:
    """ระบบวิเคราะห์ตลาดหลัก"""
    
    def __init__(self, symbol: str = "XAUUSD.v"):
        self.symbol = symbol
        self.current_analysis: Optional[MarketAnalysis] = None
        self.historical_data: Dict[str, pd.DataFrame] = {}
        self.indicators: Dict[str, TechnicalIndicators] = {}
        
        # การตั้งค่า
        self.timeframes = ["M1", "M5", "M15", "H1"]
        self.analysis_period = 100  # จำนวน candle สำหรับวิเคราะห์
        
        # Threading
        self.update_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        print(f"📊 เริ่มต้น Market Analyzer สำหรับ {symbol}")
    
    def get_market_data(self, timeframe: str = "M5", count: int = 100) -> Optional[pd.DataFrame]:
        """ดึงข้อมูลตลาด"""
        try:
            # แปลง timeframe
            mt5_timeframe = self._convert_timeframe(timeframe)
            
            # ดึงข้อมูล
            rates = mt5.copy_rates_from_pos(self.symbol, mt5_timeframe, 0, count)
            
            if rates is None or len(rates) == 0:
                print(f"❌ ไม่สามารถดึงข้อมูล {self.symbol} {timeframe}")
                return None
            
            # แปลงเป็น DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"❌ ข้อผิดพลาดในการดึงข้อมูล: {e}")
            return None
    
    def _convert_timeframe(self, timeframe: str) -> int:
        """แปลง timeframe เป็น MT5 format"""
        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        return timeframe_map.get(timeframe, mt5.TIMEFRAME_M5)
    
    def calculate_indicators(self, df: pd.DataFrame) -> TechnicalIndicators:
        """คำนวณตัวชี้วัดทางเทคนิค"""
        indicators = TechnicalIndicators()
        
        try:
            # Moving Averages
            indicators.sma_20 = df['close'].rolling(20).mean().iloc[-1]
            indicators.sma_50 = df['close'].rolling(50).mean().iloc[-1]
            indicators.ema_20 = df['close'].ewm(span=20).mean().iloc[-1]
            indicators.ema_50 = df['close'].ewm(span=50).mean().iloc[-1]
            
            # ADX (Average Directional Index)
            indicators.adx, indicators.adx_plus, indicators.adx_minus = self._calculate_adx(df)
            
            # ATR (Average True Range)
            indicators.atr = self._calculate_atr(df)
            
            # Bollinger Bands
            bb_data = self._calculate_bollinger_bands(df)
            indicators.bb_upper = bb_data['upper']
            indicators.bb_middle = bb_data['middle']
            indicators.bb_lower = bb_data['lower']
            indicators.bb_width = bb_data['width']
            
            # RSI
            indicators.rsi = self._calculate_rsi(df)
            
            # MACD
            macd_data = self._calculate_macd(df)
            indicators.macd = macd_data['macd']
            indicators.macd_signal = macd_data['signal']
            indicators.macd_histogram = macd_data['histogram']
            
        except Exception as e:
            print(f"⚠️ ข้อผิดพลาดในการคำนวณ indicators: {e}")
        
        return indicators
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> Tuple[float, float, float]:
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
            dm_plus = (high - high.shift(1)).where((high - high.shift(1)) > (low.shift(1) - low), 0)
            dm_minus = (low.shift(1) - low).where((low.shift(1) - low) > (high - high.shift(1)), 0)
            
            # Smooth the values
            tr_smooth = tr.ewm(alpha=1/period).mean()
            dm_plus_smooth = dm_plus.ewm(alpha=1/period).mean()
            dm_minus_smooth = dm_minus.ewm(alpha=1/period).mean()
            
            # Directional Indicators
            di_plus = 100 * dm_plus_smooth / tr_smooth
            di_minus = 100 * dm_minus_smooth / tr_smooth
            
            # ADX
            dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
            adx = dx.ewm(alpha=1/period).mean()
            
            return adx.iloc[-1], di_plus.iloc[-1], di_minus.iloc[-1]
            
        except:
            return 0.0, 0.0, 0.0
    
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
            
            atr = tr.rolling(period).mean()
            return atr.iloc[-1]
            
        except:
            return 0.0
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2) -> Dict[str, float]:
        """คำนวณ Bollinger Bands"""
        try:
            close = df['close']
            sma = close.rolling(period).mean()
            std = close.rolling(period).std()
            
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            width = (upper - lower) / sma * 100
            
            return {
                'upper': upper.iloc[-1],
                'middle': sma.iloc[-1],
                'lower': lower.iloc[-1],
                'width': width.iloc[-1]
            }
            
        except:
            return {'upper': 0.0, 'middle': 0.0, 'lower': 0.0, 'width': 0.0}
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """คำนวณ RSI"""
        try:
            close = df['close']
            delta = close.diff()
            
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(period).mean()
            avg_loss = loss.rolling(period).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1]
            
        except:
            return 50.0
    
    def _calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, float]:
        """คำนวณ MACD"""
        try:
            close = df['close']
            
            ema_fast = close.ewm(span=fast).mean()
            ema_slow = close.ewm(span=slow).mean()
            
            macd = ema_fast - ema_slow
            macd_signal = macd.ewm(span=signal).mean()
            macd_histogram = macd - macd_signal
            
            return {
                'macd': macd.iloc[-1],
                'signal': macd_signal.iloc[-1],
                'histogram': macd_histogram.iloc[-1]
            }
            
        except:
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}
    
    def analyze_trend(self, indicators: TechnicalIndicators, df: pd.DataFrame) -> Tuple[TrendDirection, float]:
        """วิเคราะห์ทิศทางเทรนด์"""
        try:
            current_price = df['close'].iloc[-1]
            trend_score = 0.0
            
            # Moving Average Analysis
            if current_price > indicators.ema_20 > indicators.ema_50:
                trend_score += 30
            elif current_price < indicators.ema_20 < indicators.ema_50:
                trend_score -= 30
            
            # ADX Analysis
            if indicators.adx > 25:
                if indicators.adx_plus > indicators.adx_minus:
                    trend_score += 25
                else:
                    trend_score -= 25
            
            # MACD Analysis
            if indicators.macd > indicators.macd_signal:
                trend_score += 20
            else:
                trend_score -= 20
            
            # Price vs Bollinger Bands
            if current_price > indicators.bb_upper:
                trend_score += 15
            elif current_price < indicators.bb_lower:
                trend_score -= 15
            
            # Determine trend direction
            if trend_score > 60:
                direction = TrendDirection.STRONG_UPTREND
            elif trend_score > 30:
                direction = TrendDirection.UPTREND
            elif trend_score > -30:
                direction = TrendDirection.SIDEWAYS
            elif trend_score > -60:
                direction = TrendDirection.DOWNTREND
            else:
                direction = TrendDirection.STRONG_DOWNTREND
            
            # Trend strength (0-100)
            strength = min(100, abs(trend_score))
            
            return direction, strength
            
        except Exception as e:
            print(f"⚠️ ข้อผิดพลาดในการวิเคราะห์เทรนด์: {e}")
            return TrendDirection.UNCERTAIN, 0.0
    
    def analyze_market_condition(self, indicators: TechnicalIndicators, df: pd.DataFrame) -> MarketCondition:
        """วิเคราะห์สภาวะตลาด"""
        try:
            # Volatility check
            if indicators.atr > df['close'].rolling(20).std().iloc[-1] * 2:
                return MarketCondition.VOLATILE
            
            # ADX for trending/ranging
            if indicators.adx > 25:
                return MarketCondition.TRENDING
            elif indicators.adx < 15:
                return MarketCondition.RANGING
            
            # Bollinger Bands width for volatility
            if indicators.bb_width < 1.0:
                return MarketCondition.QUIET
            elif indicators.bb_width > 3.0:
                return MarketCondition.VOLATILE
            
            # Default
            return MarketCondition.RANGING
            
        except:
            return MarketCondition.RANGING
    
    def get_trading_session(self) -> TradingSession:
        """ระบุ Trading Session ปัจจุบัน"""
        try:
            now = datetime.now()
            hour = now.hour
            
            # GMT+7 timezone
            if 22 <= hour or hour < 8:
                return TradingSession.ASIAN
            elif 15 <= hour < 20:
                return TradingSession.LONDON
            elif 20 <= hour < 24:
                return TradingSession.OVERLAP
            elif 0 <= hour < 5:
                return TradingSession.NEW_YORK
            else:
                return TradingSession.CLOSED
                
        except:
            return TradingSession.ASIAN
    
    def calculate_support_resistance(self, df: pd.DataFrame) -> Tuple[float, float]:
        """คำนวณ Support และ Resistance"""
        try:
            # ใช้ Pivot Points แบบง่าย
            recent_data = df.tail(20)
            
            highs = recent_data['high']
            lows = recent_data['low']
            
            resistance = highs.max()
            support = lows.min()
            
            return support, resistance
            
        except:
            return 0.0, 0.0
    
    def perform_analysis(self) -> MarketAnalysis:
        """ทำการวิเคราะห์ตลาดครบถ้วน"""
        analysis = MarketAnalysis(symbol=self.symbol)
        
        try:
            # ดึงข้อมูลตลาด
            df = self.get_market_data("M5", 100)
            if df is None:
                return analysis
            
            # คำนวณตัวชี้วัด
            indicators = self.calculate_indicators(df)
            self.indicators["M5"] = indicators
            
            # วิเคราะห์เทรนด์
            trend_direction, trend_strength = self.analyze_trend(indicators, df)
            analysis.trend_direction = trend_direction
            analysis.trend_strength = trend_strength
            
            # วิเคราะห์สภาวะตลาด
            analysis.market_condition = self.analyze_market_condition(indicators, df)
            
            # ระบุ Trading Session
            analysis.trading_session = self.get_trading_session()
            
            # ระดับความผันผวน
            if indicators.atr > 2.0:
                analysis.volatility_level = VolatilityLevel.VERY_HIGH
                analysis.volatility_score = 90
            elif indicators.atr > 1.5:
                analysis.volatility_level = VolatilityLevel.HIGH
                analysis.volatility_score = 70
            elif indicators.atr > 0.5:
                analysis.volatility_level = VolatilityLevel.NORMAL
                analysis.volatility_score = 50
            else:
                analysis.volatility_level = VolatilityLevel.LOW
                analysis.volatility_score = 30
            
            # ราคาปัจจุบัน
            analysis.current_price = df['close'].iloc[-1]
            
            # Support/Resistance
            support, resistance = self.calculate_support_resistance(df)
            analysis.support_level = support
            analysis.resistance_level = resistance
            
            # คะแนน Momentum
            if indicators.rsi > 70:
                analysis.momentum_score = 80
            elif indicators.rsi > 50:
                analysis.momentum_score = 60
            elif indicators.rsi > 30:
                analysis.momentum_score = 40
            else:
                analysis.momentum_score = 20
            
            # แนะนำการเทรด
            if trend_strength > 60:
                if trend_direction in [TrendDirection.STRONG_UPTREND, TrendDirection.UPTREND]:
                    analysis.trade_recommendation = "พิจารณา BUY"
                    analysis.confidence_level = trend_strength
                elif trend_direction in [TrendDirection.STRONG_DOWNTREND, TrendDirection.DOWNTREND]:
                    analysis.trade_recommendation = "พิจารณา SELL"
                    analysis.confidence_level = trend_strength
            else:
                analysis.trade_recommendation = "รอสัญญาณชัด"
                analysis.confidence_level = 30
            
            self.current_analysis = analysis
            
        except Exception as e:
            print(f"❌ ข้อผิดพลาดในการวิเคราะห์: {e}")
        
        return analysis
    
    def get_current_analysis(self) -> Optional[MarketAnalysis]:
        """ดึงผลการวิเคราะห์ปัจจุบัน"""
        return self.current_analysis
    
    def start_continuous_analysis(self, interval: int = 30):
        """เริ่มการวิเคราะห์อย่างต่อเนื่อง"""
        self.is_running = True
        
        def analysis_loop():
            while self.is_running:
                try:
                    self.perform_analysis()
                    time.sleep(interval)
                except Exception as e:
                    print(f"❌ ข้อผิดพลาดใน analysis loop: {e}")
                    time.sleep(5)
        
        self.update_thread = threading.Thread(target=analysis_loop, daemon=True)
        self.update_thread.start()
        print(f"🔄 เริ่มการวิเคราะห์อย่างต่อเนื่องทุก {interval} วินาที")
    
    def stop_analysis(self):
        """หยุดการวิเคราะห์"""
        self.is_running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join()
        print("⏹️ หยุดการวิเคราะห์ตลาด")

def test_market_analyzer():
    """ทดสอบ Market Analyzer"""
    print("🧪 ทดสอบ Market Analyzer...")
    
    if not mt5.initialize():
        print("❌ ไม่สามารถเชื่อมต่อ MT5")
        return
    
    try:
        # สร้าง analyzer
        analyzer = MarketAnalyzer("XAUUSD")
        
        # ทำการวิเคราะห์
        analysis = analyzer.perform_analysis()
        
        # แสดงผล
        print(f"\n📊 ผลการวิเคราะห์ {analysis.symbol}:")
        print(f"⏰ เวลา: {analysis.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"💰 ราคาปัจจุบัน: {analysis.current_price:.2f}")
        print(f"📈 ทิศทางเทรนด์: {analysis.trend_direction.value}")
        print(f"💪 ความแข็งแกร่งเทรนด์: {analysis.trend_strength:.1f}%")
        print(f"🌊 สภาวะตลาد: {analysis.market_condition.value}")
        print(f"⚡ ระดับความผันผวน: {analysis.volatility_level.value}")
        print(f"🕒 เซสชัน: {analysis.trading_session.value}")
        print(f"📋 แนะนำ: {analysis.trade_recommendation}")
        print(f"✅ ความมั่นใจ: {analysis.confidence_level:.1f}%")
        
        if analysis.support_level > 0:
            print(f"🔻 Support: {analysis.support_level:.2f}")
            print(f"🔺 Resistance: {analysis.resistance_level:.2f}")
        
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการทดสอบ: {e}")
    
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    test_market_analyzer()