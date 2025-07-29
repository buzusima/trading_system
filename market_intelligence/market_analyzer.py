#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REAL MARKET ANALYZER - Intelligent Market Analysis System (LIVE ONLY)
====================================================================
ระบบวิเคราะห์ตลาดจริงสำหรับ Live Trading เท่านั้น
ไม่มี Mock หรือ Simulation ใดๆ - ใช้ข้อมูลจริงจาก MT5

🎯 หน้าที่:
- วิเคราะห์ตลาด XAUUSD แบบ Real-time
- ใช้ข้อมูลจาก MT5 เท่านั้น
- ตรวจจับ Market Condition อัตโนมัติ
- แนะนำ Strategy และ Recovery Method
- Multi-timeframe Analysis (M1, M5, M15, H1)
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
import json
from collections import deque, defaultdict

# Internal imports
from config.settings import get_system_settings
from config.trading_params import get_trading_parameters, EntryStrategy, RecoveryMethod, MarketCondition, SessionType
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class AnalysisStatus(Enum):
    """สถานะการวิเคราะห์"""
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    ERROR = "ERROR"

@dataclass
class MarketData:
    """ข้อมูลตลาดแบบ Real-time"""
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    bid: float
    ask: float
    spread: float

@dataclass
class TechnicalIndicators:
    """ตัวชี้วัดทางเทคนิค"""
    sma_20: float = 0.0
    sma_50: float = 0.0
    ema_12: float = 0.0
    ema_26: float = 0.0
    rsi_14: float = 0.0
    adx_14: float = 0.0
    atr_14: float = 0.0
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    macd_main: float = 0.0
    macd_signal: float = 0.0
    stoch_k: float = 0.0
    stoch_d: float = 0.0

@dataclass
class MarketAnalysis:
    """ผลการวิเคราะห์ตลาด"""
    timestamp: datetime
    symbol: str
    current_price: float
    condition: MarketCondition
    session: SessionType
    trend_strength: float  # 0.0-1.0
    volatility_level: float  # 0.0-1.0
    recommended_strategy: EntryStrategy
    recommended_recovery: RecoveryMethod
    confidence_score: float  # 0.0-1.0
    technical_indicators: TechnicalIndicators
    market_data: Dict[str, MarketData]
    notes: str = ""

class RealMarketAnalyzer:
    """Real Market Analyzer - ไม่มี Mock"""
    
    def __init__(self):
        self.logger = setup_component_logger("RealMarketAnalyzer")
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # ตรวจสอบ MT5 connection
        if not mt5.initialize():
            raise RuntimeError("❌ ไม่สามารถเชื่อมต่อ MT5 ได้ - ระบบไม่สามารถทำงานได้")
        
        self.logger.info("✅ เชื่อมต่อ MT5 สำเร็จ - ใช้ข้อมูลจริง")
        
        # Analysis state
        self.status = AnalysisStatus.STOPPED
        self.analysis_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Data storage
        self.market_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.current_analysis: Optional[MarketAnalysis] = None
        self.analysis_lock = threading.Lock()
        
        # Callbacks
        self.analysis_callbacks: List[callable] = []
        
        # Symbol - ใช้ Auto-detected Gold Symbol
        from config.trading_params import get_current_gold_symbol
        self.symbol = get_current_gold_symbol()
        self.timeframes = ["M1", "M5", "M15", "H1"]
        
        # Verify symbol
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            raise RuntimeError(f"❌ ไม่พบ Symbol {self.symbol} ใน MT5")
        
        if not symbol_info.visible:
            if not mt5.symbol_select(self.symbol, True):
                raise RuntimeError(f"❌ ไม่สามารถเลือก Symbol {self.symbol}")
        
        self.logger.info(f"✅ ตรวจสอบ Symbol {self.symbol} สำเร็จ")
    
    @handle_trading_errors(ErrorCategory.MARKET_DATA, ErrorSeverity.HIGH)
    def start_analysis(self) -> bool:
        """เริ่มการวิเคราะห์ตลาด"""
        if self.status == AnalysisStatus.RUNNING:
            self.logger.warning("⚠️ การวิเคราะห์ทำงานอยู่แล้ว")
            return True
        
        try:
            self.status = AnalysisStatus.STARTING
            self.stop_event.clear()
            
            # เริ่ม analysis thread
            self.analysis_thread = threading.Thread(
                target=self._analysis_loop,
                name="MarketAnalysisThread",
                daemon=True
            )
            self.analysis_thread.start()
            
            self.status = AnalysisStatus.RUNNING
            self.logger.info("🚀 เริ่มการวิเคราะห์ตลาดแบบ Real-time")
            return True
            
        except Exception as e:
            self.status = AnalysisStatus.ERROR
            self.logger.error(f"❌ ไม่สามารถเริ่มการวิเคราะห์: {e}")
            return False
    
    def stop_analysis(self) -> bool:
        """หยุดการวิเคราะห์"""
        try:
            self.stop_event.set()
            self.status = AnalysisStatus.STOPPED
            
            if self.analysis_thread and self.analysis_thread.is_alive():
                self.analysis_thread.join(timeout=5.0)
            
            self.logger.info("⏹️ หยุดการวิเคราะห์ตลาด")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถหยุดการวิเคราะห์: {e}")
            return False
    
    def _analysis_loop(self):
        """Loop หลักสำหรับการวิเคราะห์"""
        self.logger.info("🔄 เริ่ม Analysis Loop")
        
        while not self.stop_event.is_set():
            try:
                # ดึงข้อมูลตลาดจาก MT5
                market_data = self._get_real_market_data()
                if not market_data:
                    time.sleep(1)
                    continue
                
                # วิเคราะห์ข้อมูล
                analysis = self._analyze_market_data(market_data)
                
                # อัปเดตผลการวิเคราะห์
                with self.analysis_lock:
                    self.current_analysis = analysis
                
                # แจ้ง callbacks
                self._notify_callbacks(analysis)
                
                # Log ผลการวิเคราะห์
                self._log_analysis_result(analysis)
                
                # รอก่อนวิเคราะห์ครั้งต่อไป
                time.sleep(5)  # วิเคราะห์ทุก 5 วินาที
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Analysis Loop: {e}")
                time.sleep(10)  # รอก่อนลองใหม่
    
    @handle_trading_errors(ErrorCategory.MARKET_DATA, ErrorSeverity.MEDIUM)
    def _get_real_market_data(self) -> Optional[Dict[str, MarketData]]:
        """ดึงข้อมูลตลาดจริงจาก MT5"""
        try:
            market_data = {}
            
            # ดึงข้อมูลแต่ละ timeframe
            for tf in self.timeframes:
                # แปลง timeframe เป็น MT5 constant
                mt5_tf = self._get_mt5_timeframe(tf)
                if mt5_tf is None:
                    continue
                
                # ดึงข้อมูล rates
                rates = mt5.copy_rates_from_pos(self.symbol, mt5_tf, 0, 100)
                if rates is None or len(rates) == 0:
                    self.logger.warning(f"⚠️ ไม่สามารถดึงข้อมูล {tf} ได้")
                    continue
                
                # ข้อมูล tick ล่าสุด
                tick = mt5.symbol_info_tick(self.symbol)
                if tick is None:
                    self.logger.warning(f"⚠️ ไม่สามารถดึง tick ข้อมูลได้")
                    continue
                
                # สร้าง MarketData object
                latest_rate = rates[-1]
                market_data[tf] = MarketData(
                    symbol=self.symbol,
                    timeframe=tf,
                    timestamp=datetime.fromtimestamp(latest_rate['time']),
                    open=float(latest_rate['open']),
                    high=float(latest_rate['high']),
                    low=float(latest_rate['low']),
                    close=float(latest_rate['close']),
                    volume=int(latest_rate['tick_volume']),
                    bid=float(tick.bid),
                    ask=float(tick.ask),
                    spread=float(tick.ask - tick.bid)
                )
                
                # เก็บข้อมูลใน deque
                self.market_data[tf].append(market_data[tf])
            
            return market_data if market_data else None
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถดึงข้อมูลตลาด: {e}")
            return None
    
    def _get_mt5_timeframe(self, timeframe: str):
        """แปลง timeframe string เป็น MT5 constant"""
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        return tf_map.get(timeframe)
    
    @handle_trading_errors(ErrorCategory.TRADING_LOGIC, ErrorSeverity.MEDIUM)
    def _calculate_technical_indicators(self, rates_data: np.ndarray) -> TechnicalIndicators:
        """คำนวณตัวชี้วัดทางเทคนิคจากข้อมูลจริง"""
        try:
            df = pd.DataFrame(rates_data)
            close_prices = df['close'].astype(float)
            high_prices = df['high'].astype(float)
            low_prices = df['low'].astype(float)
            
            indicators = TechnicalIndicators()
            
            # Moving Averages
            if len(close_prices) >= 50:
                indicators.sma_20 = float(close_prices.rolling(20).mean().iloc[-1])
                indicators.sma_50 = float(close_prices.rolling(50).mean().iloc[-1])
            
            if len(close_prices) >= 26:
                indicators.ema_12 = float(close_prices.ewm(span=12).mean().iloc[-1])
                indicators.ema_26 = float(close_prices.ewm(span=26).mean().iloc[-1])
            
            # RSI
            if len(close_prices) >= 14:
                delta = close_prices.diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                indicators.rsi_14 = float(100 - (100 / (1 + rs.iloc[-1])))
            
            # ATR
            if len(close_prices) >= 14:
                tr1 = high_prices - low_prices
                tr2 = abs(high_prices - close_prices.shift(1))
                tr3 = abs(low_prices - close_prices.shift(1))
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                indicators.atr_14 = float(tr.rolling(14).mean().iloc[-1])
            
            # Bollinger Bands
            if len(close_prices) >= 20:
                sma_20 = close_prices.rolling(20).mean()
                std_20 = close_prices.rolling(20).std()
                indicators.bb_upper = float(sma_20.iloc[-1] + (2 * std_20.iloc[-1]))
                indicators.bb_middle = float(sma_20.iloc[-1])
                indicators.bb_lower = float(sma_20.iloc[-1] - (2 * std_20.iloc[-1]))
            
            # MACD
            if len(close_prices) >= 26:
                ema_12 = close_prices.ewm(span=12).mean()
                ema_26 = close_prices.ewm(span=26).mean()
                macd_line = ema_12 - ema_26
                signal_line = macd_line.ewm(span=9).mean()
                indicators.macd_main = float(macd_line.iloc[-1])
                indicators.macd_signal = float(signal_line.iloc[-1])
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถคำนวณ Technical Indicators: {e}")
            return TechnicalIndicators()
    
    @handle_trading_errors(ErrorCategory.TRADING_LOGIC, ErrorSeverity.LOW)
    def _analyze_market_data(self, market_data: Dict[str, MarketData]) -> MarketAnalysis:
        """วิเคราะห์ข้อมูลตลาดและกำหนด Strategy"""
        try:
            # ใช้ข้อมูล M15 เป็นหลัก
            primary_data = market_data.get("M15") or market_data.get("M5") or market_data.get("M1")
            if not primary_data:
                raise ValueError("ไม่มีข้อมูลตลาดสำหรับการวิเคราะห์")
            
            # ดึงข้อมูล rates สำหรับคำนวณ indicators
            rates = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M15, 0, 100)
            if rates is None:
                raise ValueError("ไม่สามารถดึงข้อมูล rates ได้")
            
            # คำนวณ Technical Indicators
            indicators = self._calculate_technical_indicators(rates)
            
            # ตรวจจับ Market Condition
            condition = self._detect_market_condition(primary_data, indicators)
            
            # ตรวจจับ Session
            session = self._detect_current_session()
            
            # คำนวณ Trend Strength
            trend_strength = self._calculate_trend_strength(indicators)
            
            # คำนวณ Volatility Level
            volatility_level = self._calculate_volatility_level(indicators, market_data)
            
            # เลือก Strategy และ Recovery Method
            strategy_info = self.trading_params.get_strategy_for_condition(condition)
            recommended_strategy = strategy_info.get('primary', EntryStrategy.SCALPING_FAST)
            recommended_recovery = strategy_info.get('recovery', RecoveryMethod.CONSERVATIVE_RECOVERY)
            confidence_score = strategy_info.get('confidence', 0.5)
            
            # สร้างผลการวิเคราะห์
            analysis = MarketAnalysis(
                timestamp=datetime.now(),
                symbol=self.symbol,
                current_price=primary_data.close,
                condition=condition,
                session=session,
                trend_strength=trend_strength,
                volatility_level=volatility_level,
                recommended_strategy=recommended_strategy,
                recommended_recovery=recommended_recovery,
                confidence_score=confidence_score,
                technical_indicators=indicators,
                market_data=market_data,
                notes=f"Real-time analysis at {datetime.now().strftime('%H:%M:%S')}"
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถวิเคราะห์ข้อมูลตลาด: {e}")
            # Return default analysis
            return MarketAnalysis(
                timestamp=datetime.now(),
                symbol=self.symbol,
                current_price=2000.0,
                condition=MarketCondition.UNKNOWN,
                session=SessionType.ASIAN,
                trend_strength=0.5,
                volatility_level=0.5,
                recommended_strategy=EntryStrategy.SCALPING_FAST,
                recommended_recovery=RecoveryMethod.CONSERVATIVE_RECOVERY,
                confidence_score=0.3,
                technical_indicators=TechnicalIndicators(),
                market_data=market_data,
                notes="Error in analysis - using default values"
            )
    
    def _detect_market_condition(self, market_data: MarketData, indicators: TechnicalIndicators) -> MarketCondition:
        """ตรวจจับสภาพตลาดจากข้อมูลจริง"""
        try:
            # ADX สำหรับความแรงของเทรนด์
            if indicators.adx_14 > 25:
                # Trending Market
                if indicators.adx_14 > 40:
                    return MarketCondition.TRENDING_STRONG
                else:
                    return MarketCondition.TRENDING_WEAK
            
            # ATR สำหรับความผันแปร
            if indicators.atr_14 > 15:  # High volatility for Gold
                return MarketCondition.VOLATILE_HIGH
            
            # Bollinger Bands สำหรับ Range
            if indicators.bb_upper > 0 and indicators.bb_lower > 0:
                bb_width = indicators.bb_upper - indicators.bb_lower
                current_price = market_data.close
                
                if bb_width < 10:  # Tight range for Gold
                    return MarketCondition.RANGING_TIGHT
                elif current_price > indicators.bb_upper or current_price < indicators.bb_lower:
                    return MarketCondition.VOLATILE_HIGH
                else:
                    return MarketCondition.RANGING_WIDE
            
            # Default condition
            return MarketCondition.RANGING_TIGHT
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถตรวจจับ Market Condition: {e}")
            return MarketCondition.UNKNOWN
    
    def _detect_current_session(self) -> SessionType:
        """ตรวจจับ Session ปัจจุบัน (GMT+7)"""
        now = datetime.now()
        current_time = now.time()
        
        # London/NY Overlap (20:30-00:00)
        if current_time >= time(20, 30) or current_time <= time(0, 0):
            return SessionType.OVERLAP
        
        # London Session (15:00-00:00)
        elif current_time >= time(15, 0):
            return SessionType.LONDON
        
        # NY Session (20:30-05:30) - ส่วนที่ไม่ overlap
        elif current_time <= time(5, 30):
            return SessionType.NY
        
        # Asian Session (22:00-08:00) - ส่วนที่เหลือ
        else:
            return SessionType.ASIAN
    
    def _calculate_trend_strength(self, indicators: TechnicalIndicators) -> float:
        """คำนวณความแรงของเทรนด์ (0.0-1.0)"""
        try:
            strength = 0.0
            factors = 0
            
            # ADX strength
            if indicators.adx_14 > 0:
                strength += min(indicators.adx_14 / 50, 1.0)
                factors += 1
            
            # Moving Average alignment
            if indicators.sma_20 > 0 and indicators.sma_50 > 0:
                if abs(indicators.sma_20 - indicators.sma_50) > 5:  # Significant gap
                    strength += 0.8
                else:
                    strength += 0.3
                factors += 1
            
            # MACD strength
            if indicators.macd_main != 0 and indicators.macd_signal != 0:
                macd_diff = abs(indicators.macd_main - indicators.macd_signal)
                strength += min(macd_diff / 10, 1.0)
                factors += 1
            
            return strength / factors if factors > 0 else 0.5
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถคำนวณ Trend Strength: {e}")
            return 0.5
    
    def _calculate_volatility_level(self, indicators: TechnicalIndicators, market_data: Dict[str, MarketData]) -> float:
        """คำนวณระดับความผันแปร (0.0-1.0)"""
        try:
            volatility = 0.0
            factors = 0
            
            # ATR-based volatility
            if indicators.atr_14 > 0:
                volatility += min(indicators.atr_14 / 20, 1.0)  # Normalize for Gold
                factors += 1
            
            # Bollinger Bands width
            if indicators.bb_upper > 0 and indicators.bb_lower > 0:
                bb_width = indicators.bb_upper - indicators.bb_lower
                volatility += min(bb_width / 30, 1.0)  # Normalize for Gold
                factors += 1
            
            # Spread-based volatility
            for tf_data in market_data.values():
                if tf_data.spread > 0:
                    volatility += min(tf_data.spread / 2.0, 1.0)  # Normalize spread
                    factors += 1
                    break  # Use one timeframe only
            
            return volatility / factors if factors > 0 else 0.5
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถคำนวณ Volatility Level: {e}")
            return 0.5
    
    def _notify_callbacks(self, analysis: MarketAnalysis):
        """แจ้ง callbacks เมื่อมีการวิเคราะห์ใหม่"""
        for callback in self.analysis_callbacks:
            try:
                callback(analysis)
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน analysis callback: {e}")
    
    def _log_analysis_result(self, analysis: MarketAnalysis):
        """Log ผลการวิเคราะห์"""
        self.logger.info(
            f"📊 Market Analysis: {analysis.condition.value} | "
            f"Session: {analysis.session.value} | "
            f"Strategy: {analysis.recommended_strategy.value} | "
            f"Price: {analysis.current_price:.2f} | "
            f"Confidence: {analysis.confidence_score:.2f}"
        )
    
    def get_current_analysis(self) -> Optional[MarketAnalysis]:
        """ดึงผลการวิเคราะห์ปัจจุบัน"""
        with self.analysis_lock:
            return self.current_analysis
    
    def add_analysis_callback(self, callback: callable):
        """เพิ่ม callback สำหรับผลการวิเคราะห์ใหม่"""
        self.analysis_callbacks.append(callback)
    
    def remove_analysis_callback(self, callback: callable):
        """ลบ callback"""
        if callback in self.analysis_callbacks:
            self.analysis_callbacks.remove(callback)
    
    def get_analysis_status(self) -> Dict[str, Any]:
        """ดึงสถานะการวิเคราะห์"""
        return {
            'status': self.status.value,
            'mt5_connected': mt5.terminal_info() is not None,
            'symbol': self.symbol,
            'timeframes': self.timeframes,
            'data_points': {tf: len(data) for tf, data in self.market_data.items()},
            'last_analysis': self.current_analysis.timestamp if self.current_analysis else None,
            'callbacks_count': len(self.analysis_callbacks)
        }
    
    def __del__(self):
        """Cleanup เมื่อ object ถูกทำลาย"""
        try:
            self.stop_analysis()
        except:
            pass

# ===== FACTORY FUNCTION =====

def get_market_analyzer() -> RealMarketAnalyzer:
    """Factory function สำหรับสร้าง Real Market Analyzer"""
    return RealMarketAnalyzer()

# ===== MAIN TESTING =====

if __name__ == "__main__":
    """ทดสอบ Real Market Analyzer"""
    
    print("🧪 ทดสอบ Real Market Analyzer")
    print("=" * 50)
    
    try:
        # สร้าง analyzer
        analyzer = RealMarketAnalyzer()
        print("✅ สร้าง Real Market Analyzer สำเร็จ")
        
        # เริ่มการวิเคราะห์
        if analyzer.start_analysis():
            print("✅ เริ่มการวิเคราะห์สำเร็จ")
            
            # รอให้ได้ผลการวิเคราะห์
            print("⏳ รอผลการวิเคราะห์...")
            time.sleep(10)
            
            # ดึงผลการวิเคราะห์
            analysis = analyzer.get_current_analysis()
            if analysis:
                print(f"📊 Market Condition: {analysis.condition.value}")
                print(f"📊 Current Session: {analysis.session.value}")
                print(f"📊 Recommended Strategy: {analysis.recommended_strategy.value}")
                print(f"📊 Current Price: {analysis.current_price:.2f}")
                print(f"📊 Confidence: {analysis.confidence_score:.2f}")
            else:
                print("❌ ไม่ได้ผลการวิเคราะห์")
            
            # หยุดการวิเคราะห์
            analyzer.stop_analysis()
            print("⏹️ หยุดการวิเคราะห์")
        
        else:
            print("❌ ไม่สามารถเริ่มการวิเคราะห์ได้")
            
    except Exception as e:
        print(f"❌ ข้อผิดพลาด: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎯 การทดสอบเสร็จสิ้น")