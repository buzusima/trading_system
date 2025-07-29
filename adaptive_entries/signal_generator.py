#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIGNAL GENERATOR - Intelligent Signal Generation System
=====================================================
ระบบสร้างสัญญาณการเทรดอัจฉริยะที่ปรับปรุงใหม่
เปลี่ยนจากการสร้างสัญญาณแยกหลายตัว เป็นระบบเดียวที่มีประสิทธิภาพ

🎯 หน้าที่หลัก:
- สร้างสัญญาณการเข้าออร์เดอร์แบบอัตโนมัติ
- เชื่อมต่อกับ Market Analyzer สำหรับการตัดสินใจ
- ปรับความถี่ของสัญญาณตาม Market Condition
- รองรับ High-Frequency Trading (50-100 lots/day)
- เลือก Entry Strategy อัตโนมัติ

✨ ปรับปรุงใหม่:
- รวม Logic ทุก Strategy ในไฟล์เดียว
- เงื่อนไขการสร้างสัญญาณชัดเจน
- ปรับความถี่ตาม Market Session
- เชื่อมต่อ Market Analyzer โดยตรง
"""

import threading
import time
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import random
import numpy as np
import MetaTrader5 as mt5

# Internal imports
from config.settings import get_system_settings
from config.trading_params import get_trading_parameters, EntryStrategy
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity
from market_intelligence.market_analyzer import get_market_analyzer, MarketCondition, SessionType
from mt5_integration.mt5_connector import ensure_mt5_connection

class SignalType(Enum):
   """ประเภทสัญญาณ"""
   BUY = "BUY"
   SELL = "SELL"
   HOLD = "HOLD"

class SignalStrength(Enum):
   """ความแรงของสัญญาณ"""
   WEAK = "WEAK"           # 30-50%
   MODERATE = "MODERATE"   # 50-70%
   STRONG = "STRONG"       # 70-85%
   VERY_STRONG = "VERY_STRONG"  # 85-100%

@dataclass
class TradingSignal:
   """สัญญาณการเทรด"""
   signal_id: str
   timestamp: datetime
   symbol: str = "XAUUSD"
   
   # Signal Properties
   signal_type: SignalType = SignalType.HOLD
   entry_strategy: EntryStrategy = EntryStrategy.SCALPING_ENGINE
   signal_strength: SignalStrength = SignalStrength.WEAK
   
   # Price Information
   current_price: float = 0.0
   entry_price: float = 0.0
   
   # Risk Management
   suggested_volume: float = 0.01
   max_spread: float = 3.0
   
   # Market Context
   market_condition: MarketCondition = MarketCondition.UNKNOWN
   session_type: SessionType = SessionType.QUIET
   confidence_score: float = 0.0
   reasoning: str = ""
   
   # Status
   is_executed: bool = False
   execution_time: Optional[datetime] = None

class IntelligentSignalGenerator:
   """🎯 Intelligent Signal Generator - ระบบสร้างสัญญาณอัจฉริยะ"""
   
   def __init__(self):
       self.logger = setup_component_logger("IntelligentSignalGenerator")
       self.settings = get_system_settings()
       self.trading_params = get_trading_parameters()
       
       # Market Analyzer Connection
       self.market_analyzer = get_market_analyzer()
       
       # Signal Generation State
       self.generation_active = False
       self.trading_started = False  # GUI control flag
       self.generation_thread: Optional[threading.Thread] = None
       
       # Signal Storage
       self.signals_queue = queue.Queue(maxsize=100)
       self.recent_signals: List[TradingSignal] = []
       
       # Timing Control
       self.last_signal_time = 0
       self.signal_cooldown = 15  # Base cooldown in seconds
       
       # Volume Management
       self.daily_volume_generated = 0.0
       self.daily_volume_target = 75.0  # Target lots/day
       
       # Statistics
       self.signals_generated_today = 0
       self.signals_executed_today = 0
       
       self.logger.info("🎯 เริ่มต้น Intelligent Signal Generator")
   
   def start_signal_generation(self) -> bool:
       """🚀 เริ่มการสร้างสัญญาณ"""
       if self.generation_active:
           return True
       
       try:
           if not ensure_mt5_connection():
               self.logger.error("❌ ไม่สามารถเชื่อมต่อ MT5")
               return False
           
           if not self.market_analyzer.analysis_active:
               self.market_analyzer.start_analysis()
           
           self.generation_active = True
           self.generation_thread = threading.Thread(
               target=self._signal_generation_loop,
               daemon=True,
               name="SignalGenerationLoop"
           )
           self.generation_thread.start()
           
           self.logger.info("🚀 เริ่มการสร้างสัญญาณแบบ Real-time")
           return True
           
       except Exception as e:
           self.logger.error(f"❌ ข้อผิดพลาดในการเริ่มสร้างสัญญาณ: {e}")
           return False
   
   def stop_signal_generation(self):
       """🛑 หยุดการสร้างสัญญาณ"""
       self.generation_active = False
       self.trading_started = False
       
       if self.generation_thread and self.generation_thread.is_alive():
           self.generation_thread.join(timeout=10.0)
       
       self.logger.info("🛑 หยุดการสร้างสัญญาณ")
   
   def enable_trading(self):
       """✅ เปิดใช้งานการเทรด"""
       self.trading_started = True
       self.logger.info("✅ เปิดใช้งานการสร้างสัญญาณ")
   
   def disable_trading(self):
       """🛑 ปิดการเทรด"""
       self.trading_started = False
       self.logger.info("🛑 ปิดการสร้างสัญญาณ")
   
   def _signal_generation_loop(self):
       """🔄 Main Signal Generation Loop"""
       while self.generation_active:
           try:
               if not self.trading_started:
                   time.sleep(1)
                   continue
               
               if self._should_generate_signal():
                   signal = self._generate_signal()
                   if signal:
                       self._process_new_signal(signal)
               
               sleep_time = self._calculate_adaptive_sleep()
               time.sleep(sleep_time)
               
           except Exception as e:
               self.logger.error(f"❌ Signal Generation Loop Error: {e}")
               time.sleep(10)
   
   def _should_generate_signal(self) -> bool:
       """🤔 ตรวจสอบว่าควรสร้างสัญญาณหรือไม่"""
       current_time = time.time()
       if current_time - self.last_signal_time < self.signal_cooldown:
           return False
       
       if self.daily_volume_generated >= self.daily_volume_target * 1.2:
           return False
       
       suitable, reason = self.market_analyzer.is_good_time_to_trade()
       return suitable
   
   @handle_trading_errors(ErrorCategory.TRADING_LOGIC, ErrorSeverity.MEDIUM)
   def _generate_signal(self) -> Optional[TradingSignal]:
       """🎯 สร้างสัญญาณการเทรด"""
       try:
           market_analysis = self.market_analyzer.get_current_analysis()
           if not market_analysis:
               return None
           
           current_price = self._get_current_price()
           if current_price <= 0:
               return None
           
           strategy = market_analysis.recommended_entry_strategy
           
           # Generate signal based on strategy
           signal_type, entry_price, reasoning = self._generate_strategy_signal(
               strategy, market_analysis, current_price
           )
           
           if signal_type == SignalType.HOLD:
               return None
           
           signal_strength = self._calculate_signal_strength(market_analysis)
           suggested_volume = self._calculate_suggested_volume(strategy, market_analysis)
           
           signal = TradingSignal(
               signal_id=f"SIG_{int(time.time() * 1000)}",
               timestamp=datetime.now(),
               signal_type=signal_type,
               entry_strategy=strategy,
               signal_strength=signal_strength,
               current_price=current_price,
               entry_price=entry_price,
               suggested_volume=suggested_volume,
               market_condition=market_analysis.primary_condition,
               session_type=market_analysis.current_session,
               confidence_score=market_analysis.confidence_score,
               reasoning=reasoning
           )
           
           return signal
           
       except Exception as e:
           self.logger.error(f"❌ Signal Generation Error: {e}")
           return None
   
   def _generate_strategy_signal(self, strategy: EntryStrategy, market_analysis, 
                               current_price: float) -> Tuple[SignalType, float, str]:
       """🎲 สร้างสัญญาณตาม Strategy"""
       
       metrics = market_analysis.metrics
       
       if strategy == EntryStrategy.SCALPING_ENGINE:
           return self._scalping_signal(metrics, current_price)
       elif strategy == EntryStrategy.TREND_FOLLOWING:
           return self._trend_following_signal(metrics, current_price)
       elif strategy == EntryStrategy.MEAN_REVERSION:
           return self._mean_reversion_signal(metrics, current_price)
       elif strategy == EntryStrategy.BREAKOUT_FALSE:
           return self._breakout_false_signal(metrics, current_price)
       elif strategy == EntryStrategy.NEWS_REACTION:
           return self._news_reaction_signal(metrics, current_price)
       else:
           return SignalType.HOLD, current_price, "Unknown strategy"
   
   def _scalping_signal(self, metrics, current_price: float) -> Tuple[SignalType, float, str]:
       """⚡ Scalping Signal Logic"""
       rsi = metrics.rsi_value
       distance_from_ma = metrics.distance_from_ma
       
       if rsi < 40 and distance_from_ma < -0.1:
           entry_price = current_price + 0.5
           return SignalType.BUY, entry_price, f"Scalping BUY: RSI {rsi:.1f}, below MA"
       elif rsi > 60 and distance_from_ma > 0.1:
           entry_price = current_price - 0.5
           return SignalType.SELL, entry_price, f"Scalping SELL: RSI {rsi:.1f}, above MA"
       
       return SignalType.HOLD, current_price, "No scalping opportunity"
   
   def _trend_following_signal(self, metrics, current_price: float) -> Tuple[SignalType, float, str]:
       """📈 Trend Following Signal Logic"""
       ma_slope = metrics.ma_slope
       adx = metrics.adx_value
       
       if ma_slope > 0.1 and adx > 25:
           entry_price = current_price + 1.0
           return SignalType.BUY, entry_price, f"Trend BUY: Strong uptrend, ADX {adx:.1f}"
       elif ma_slope < -0.1 and adx > 25:
           entry_price = current_price - 1.0
           return SignalType.SELL, entry_price, f"Trend SELL: Strong downtrend, ADX {adx:.1f}"
       
       return SignalType.HOLD, current_price, "No trend signal"
   
   def _mean_reversion_signal(self, metrics, current_price: float) -> Tuple[SignalType, float, str]:
       """🔄 Mean Reversion Signal Logic"""
       distance_from_ma = metrics.distance_from_ma
       rsi = metrics.rsi_value
       
       if distance_from_ma > 0.3 and rsi > 70:
           entry_price = current_price - 0.5
           return SignalType.SELL, entry_price, f"Mean Reversion SELL: {distance_from_ma:.2f}% above MA"
       elif distance_from_ma < -0.3 and rsi < 30:
           entry_price = current_price + 0.5
           return SignalType.BUY, entry_price, f"Mean Reversion BUY: {distance_from_ma:.2f}% below MA"
       
       return SignalType.HOLD, current_price, "No mean reversion opportunity"
   
   def _breakout_false_signal(self, metrics, current_price: float) -> Tuple[SignalType, float, str]:
       """💥 False Breakout Signal Logic"""
       resistance = metrics.resistance_level
       support = metrics.support_level
       atr_normalized = metrics.atr_normalized
       
       if resistance > 0 and abs(current_price - resistance) < 2.0 and atr_normalized > 1.3:
           entry_price = current_price - 1.0
           return SignalType.SELL, entry_price, f"False breakout SELL: Near resistance"
       elif support > 0 and abs(current_price - support) < 2.0 and atr_normalized > 1.3:
           entry_price = current_price + 1.0
           return SignalType.BUY, entry_price, f"False breakout BUY: Near support"
       
       return SignalType.HOLD, current_price, "No false breakout setup"
   
   def _news_reaction_signal(self, metrics, current_price: float) -> Tuple[SignalType, float, str]:
       """📰 News Reaction Signal Logic"""
       atr_normalized = metrics.atr_normalized
       
       if atr_normalized > 2.0:
           if random.random() > 0.5:
               entry_price = current_price + 0.5
               return SignalType.BUY, entry_price, f"News reaction BUY: High volatility"
           else:
               entry_price = current_price - 0.5
               return SignalType.SELL, entry_price, f"News reaction SELL: High volatility"
       
       return SignalType.HOLD, current_price, "No news reaction detected"
   
   def _calculate_signal_strength(self, market_analysis) -> SignalStrength:
       """💪 คำนวณความแรงของสัญญาณ"""
       combined_score = (market_analysis.confidence_score + market_analysis.signal_strength) / 2
       
       if combined_score >= 85:
           return SignalStrength.VERY_STRONG
       elif combined_score >= 70:
           return SignalStrength.STRONG
       elif combined_score >= 50:
           return SignalStrength.MODERATE
       else:
           return SignalStrength.WEAK
   
   def _calculate_suggested_volume(self, strategy: EntryStrategy, market_analysis) -> float:
       """📊 คำนวณขนาด Volume ที่แนะนำ"""
       base_volumes = {
           EntryStrategy.SCALPING_ENGINE: 0.01,
           EntryStrategy.TREND_FOLLOWING: 0.05,
           EntryStrategy.MEAN_REVERSION: 0.03,
           EntryStrategy.BREAKOUT_FALSE: 0.02,
           EntryStrategy.NEWS_REACTION: 0.01
       }
       
       base_volume = base_volumes.get(strategy, 0.01)
       confidence_multiplier = market_analysis.confidence_score / 100
       adjusted_volume = base_volume * confidence_multiplier
       
       return max(0.01, min(0.1, round(adjusted_volume, 2)))
   
   def _get_current_price(self) -> float:
       """💰 ดึงราคาปัจจุบัน"""
       try:
           if not ensure_mt5_connection():
               return 0.0
           
           tick = mt5.symbol_info_tick("XAUUSD")
           if tick:
               return (tick.bid + tick.ask) / 2
           else:
               return 0.0
               
       except Exception as e:
           self.logger.error(f"❌ Get Current Price Error: {e}")
           return 0.0
   
   def _process_new_signal(self, signal: TradingSignal):
       """🔄 ประมวลผลสัญญาณใหม่"""
       try:
           if not self.signals_queue.full():
               self.signals_queue.put(signal)
           
           self.recent_signals.append(signal)
           if len(self.recent_signals) > 50:
               self.recent_signals.pop(0)
           
           self.signals_generated_today += 1
           self.last_signal_time = time.time()
           self.daily_volume_generated += signal.suggested_volume
           
           self.logger.info(
               f"🎯 New Signal: {signal.signal_type.value} {signal.symbol} "
               f"| Strategy: {signal.entry_strategy.value} "
               f"| Volume: {signal.suggested_volume} "
               f"| Price: {signal.entry_price:.2f}"
           )
           
       except Exception as e:
           self.logger.error(f"❌ Process Signal Error: {e}")
   
   def _calculate_adaptive_sleep(self) -> float:
       """⏰ คำนวณเวลารอแบบ Adaptive"""
       market_summary = self.market_analyzer.get_market_summary()
       session = market_summary.get('session', 'QUIET')
       
       session_sleep = {
           'ASIAN': 60,
           'LONDON': 30,
           'NEW_YORK': 20,
           'OVERLAP': 15,
           'QUIET': 120
       }
       
       base_sleep = session_sleep.get(session, 60)
       variation = random.uniform(0.8, 1.2)
       
       return base_sleep * variation
   
   # === PUBLIC METHODS ===
   
   def get_latest_signals(self, count: int = 10) -> List[TradingSignal]:
       """ดึงสัญญาณล่าสุด"""
       return self.recent_signals[-count:] if self.recent_signals else []
   
   def get_pending_signals(self) -> List[TradingSignal]:
       """ดึงสัญญาณที่รอดำเนินการ"""
       pending_signals = []
       try:
           while not self.signals_queue.empty():
               signal = self.signals_queue.get_nowait()
               if not signal.is_executed:
                   pending_signals.append(signal)
       except queue.Empty:
           pass
       
       return pending_signals
   
   def mark_signal_executed(self, signal_id: str) -> bool:
       """ทำเครื่องหมายสัญญาณว่าถูกดำเนินการแล้ว"""
       try:
           for signal in self.recent_signals:
               if signal.signal_id == signal_id:
                   signal.is_executed = True
                   signal.execution_time = datetime.now()
                   self.signals_executed_today += 1
                   
                   self.logger.info(f"✅ Signal executed: {signal_id}")
                   return True
           
           return False
           
       except Exception as e:
           self.logger.error(f"❌ Mark Signal Executed Error: {e}")
           return False
   
   def get_signal_statistics(self) -> Dict[str, Any]:
       """ดึงสถิติสัญญาณ"""
       return {
           'signals_generated_today': self.signals_generated_today,
           'signals_executed_today': self.signals_executed_today,
           'execution_rate': (self.signals_executed_today / max(1, self.signals_generated_today)) * 100,
           'daily_volume_generated': self.daily_volume_generated,
           'daily_volume_target': self.daily_volume_target,
           'volume_progress': (self.daily_volume_generated / self.daily_volume_target) * 100,
           'recent_signals_count': len(self.recent_signals),
           'pending_signals_count': self.signals_queue.qsize(),
           'trading_enabled': self.trading_started,
           'generation_active': self.generation_active
       }


# === SINGLETON PATTERN ===

_signal_generator_instance = None

def get_signal_generator() -> IntelligentSignalGenerator:
   """Get Signal Generator Singleton Instance"""
   global _signal_generator_instance
   if _signal_generator_instance is None:
       _signal_generator_instance = IntelligentSignalGenerator()
   return _signal_generator_instance