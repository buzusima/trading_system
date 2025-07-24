#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIGNAL GENERATOR - Entry Signal Coordination Engine (FIXED)
=========================================================
รวบรวมและประสานงาน Entry Signals จากทุก Entry Engines
แก้ไขให้ทำงานแบบ SYNC และเชื่อมต่อกับระบบอื่นได้

Key Features:
- รวบรวม signals จาก entry engines ทั้งหมด
- ประเมินคุณภาพ signal และความน่าเชื่อถือ
- จัดลำดับความสำคัญของ signals
- ตัดสินใจ final entry signal
- รองรับ High-Frequency Trading (50-100 lots/วัน)
"""

import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
import queue
import json

# เชื่อมต่อ internal modules
from config.settings import get_system_settings, MarketSession
from config.trading_params import get_trading_parameters, EntryStrategy
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

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

class SignalConfidence(Enum):
    """ความเชื่อมั่นของ Signal"""
    LOW = 0.3      # 30% confidence
    MEDIUM = 0.6   # 60% confidence
    HIGH = 0.8     # 80% confidence
    VERY_HIGH = 0.95  # 95% confidence

@dataclass
class EntrySignal:
    """คลาสสำหรับเก็บข้อมูล Entry Signal"""
    signal_id: str
    timestamp: datetime
    source_engine: EntryStrategy
    direction: SignalDirection
    strength: SignalStrength
    confidence: float
    current_price: float
    suggested_volume: float
    technical_indicators: Dict[str, Any] = field(default_factory=dict)
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    signal_quality_score: float = 0.0
    risk_reward_ratio: float = 1.0
    probability_success: float = 0.5
    urgency_level: int = 1
    max_slippage_points: float = 2.0
    session: MarketSession = MarketSession.ASIAN
    market_volatility: str = "MEDIUM"
    additional_info: Dict[str, Any] = field(default_factory=dict)

class SignalAggregator:
    """รวบรวมและประมวลผล Signals จาก Entry Engines ต่างๆ"""
    
    def __init__(self):
        self.logger = setup_component_logger("SignalAggregator")
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Signal Storage
        self.active_signals: List[EntrySignal] = []
        self.signal_history: List[EntrySignal] = []
        self.signal_queue = queue.Queue()
        
        # Entry Engines Connection
        self.entry_engines: Dict[EntryStrategy, Any] = {}
        self.engine_weights: Dict[EntryStrategy, float] = {
            EntryStrategy.TREND_FOLLOWING: 0.25,
            EntryStrategy.MEAN_REVERSION: 0.25,
            EntryStrategy.BREAKOUT_FALSE: 0.20,
            EntryStrategy.NEWS_REACTION: 0.15,
            EntryStrategy.SCALPING_ENGINE: 0.15
        }
        
        # Signal Quality Filters
        self.min_signal_strength = SignalStrength.MODERATE
        self.min_confidence_level = 0.6
        self.min_quality_score = 60.0
        
        self.logger.info("📊 เริ่มต้น Signal Aggregator")
    
    def register_entry_engine(self, strategy: EntryStrategy, engine_instance: Any) -> None:
        """ลงทะเบียน Entry Engine"""
        self.entry_engines[strategy] = engine_instance
        self.logger.info(f"✅ ลงทะเบียน {strategy.value} Engine")
    
    def add_signal(self, signal: EntrySignal) -> bool:
        """เพิ่ม Signal เข้าระบบ"""
        try:
            # ตรวจสอบคุณภาพ Signal
            if not self._validate_signal(signal):
                self.logger.debug(f"📊 Signal ไม่ผ่านการตรวจสอบ: {signal.signal_id}")
                return False
            
            # เพิ่มเข้า Queue
            self.signal_queue.put(signal)
            self.active_signals.append(signal)
            
            self.logger.info(f"📨 เพิ่ม Signal: {signal.signal_id} | "
                           f"Direction: {signal.direction.value} | "
                           f"Strength: {signal.strength.value} | "
                           f"Confidence: {signal.confidence:.2f}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเพิ่ม Signal: {e}")
            return False
    
    def _validate_signal(self, signal: EntrySignal) -> bool:
        """ตรวจสอบคุณภาพ Signal"""
        # ตรวจสอบความแรงของ Signal
        if signal.strength.value < self.min_signal_strength.value:
            return False
        
        # ตรวจสอบความเชื่อมั่น
        if signal.confidence < self.min_confidence_level:
            return False
        
        # ตรวจสอบคะแนนคุณภาพ
        if signal.signal_quality_score < self.min_quality_score:
            return False
        
        return True
    
    def get_next_signal(self) -> Optional[EntrySignal]:
        """ดึง Signal ถัดไป"""
        try:
            return self.signal_queue.get_nowait()
        except queue.Empty:
            return None
    
    def clear_old_signals(self, max_age_minutes: int = 5):
        """ลบ Signals ที่เก่าเกินไป"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(minutes=max_age_minutes)
        
        # กรอง Active Signals
        self.active_signals = [
            signal for signal in self.active_signals 
            if signal.timestamp > cutoff_time
        ]
        
        self.logger.debug(f"🧹 ลบ Signals เก่า | เหลือ: {len(self.active_signals)} signals")

class SignalGenerator:
    """
    🎯 Main Signal Generator Class (แก้ไขแล้ว)
    
    ประสานงานการสร้าง Entry Signals และจัดการ High-Frequency Trading
    """
    
    def __init__(self):
        self.logger = setup_component_logger("SignalGenerator")
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Core Components
        self.signal_aggregator = SignalAggregator()
        self.market_analyzer = None  # จะเชื่อมต่อใน start()
        self.strategy_selector = None  # จะเชื่อมต่อใน start()
        
        # Signal Generation Stats
        self.signals_generated_today = 0
        self.signals_executed_today = 0
        self.target_signals_per_hour = self._calculate_target_signals()
        
        # Timing Control
        self.last_signal_time = datetime.now()
        self.min_signal_interval = timedelta(seconds=self.settings.min_entry_interval_seconds)
        
        # Threading
        self.generator_active = False
        self.generator_thread = None
        self.signal_monitor_thread = None
        
        self.logger.info("🎯 เริ่มต้น Signal Generator")
    
    def _calculate_target_signals(self) -> int:
        """คำนวณเป้าหมาย Signals ต่อชั่วโมง"""
        daily_target = (self.settings.daily_volume_target_min + 
                       self.settings.daily_volume_target_max) / 2
        hourly_target = daily_target / 24
        return int(hourly_target * 1.5)  # เผื่อสำหรับ signals ที่ไม่ได้ execute
    
    @handle_trading_errors(ErrorCategory.SIGNAL_GENERATION, ErrorSeverity.MEDIUM)
    def start_signal_generation(self) -> None:
        """เริ่มต้นการสร้าง Signals (แก้ไขเป็น SYNC)"""
        if self.generator_active:
            self.logger.warning("⚠️ Signal Generator กำลังทำงานอยู่แล้ว")
            return
        
        self.logger.info("🚀 เริ่มต้น Signal Generation System")
        
        # เชื่อมต่อ Market Analyzer
        try:
            from market_intelligence.market_analyzer import MarketAnalyzer
            self.market_analyzer = MarketAnalyzer()
            # ไม่ต้อง start_analysis() เพราะจะ start ใน main_window แล้ว
            self.logger.info("✅ เชื่อมต่อ Market Analyzer สำเร็จ")
        except ImportError as e:
            self.logger.error(f"❌ ไม่สามารถเชื่อมต่อ Market Analyzer: {e}")
            # ทำงานต่อได้แม้ไม่มี Market Analyzer
        
        # เชื่อมต่อ Strategy Selector (Optional)
        try:
            from adaptive_entries.strategy_selector import StrategySelector
            self.strategy_selector = StrategySelector()
            self.logger.info("✅ เชื่อมต่อ Strategy Selector สำเร็จ")
        except ImportError as e:
            self.logger.warning(f"⚠️ ไม่สามารถเชื่อมต่อ Strategy Selector: {e}")
            # ทำงานต่อได้แม้ไม่มี Strategy Selector
        
        # เริ่ม Signal Generation Threads
        self.generator_active = True
        
        self.generator_thread = threading.Thread(
            target=self._signal_generation_loop,
            daemon=True,
            name="SignalGenerationLoop"
        )
        
        self.signal_monitor_thread = threading.Thread(
            target=self._signal_monitor_loop,
            daemon=True,
            name="SignalMonitorLoop"
        )
        
        self.generator_thread.start()
        self.signal_monitor_thread.start()
        
        self.logger.info("✅ Signal Generation System เริ่มทำงานแล้ว")
    
    def stop_signal_generation(self) -> None:
        """หยุดการสร้าง Signals"""
        self.generator_active = False
        
        if self.generator_thread and self.generator_thread.is_alive():
            self.generator_thread.join(timeout=5.0)
        
        if self.signal_monitor_thread and self.signal_monitor_thread.is_alive():
            self.signal_monitor_thread.join(timeout=5.0)
        
        self.logger.info("🛑 หยุด Signal Generation System")
    
    def _signal_generation_loop(self) -> None:
        """Main Signal Generation Loop"""
        self.logger.info("🔄 เริ่มต้น Signal Generation Loop")
        
        while self.generator_active:
            try:
                # ตรวจสอบเวลาระหว่างการสร้าง Signal
                current_time = datetime.now()
                time_since_last = current_time - self.last_signal_time
                
                if time_since_last < self.min_signal_interval:
                    time.sleep(1)
                    continue
                
                # สร้าง Signal ใหม่
                signal = self._generate_entry_signal()
                if signal:
                    # เพิ่มเข้าระบบ
                    if self.signal_aggregator.add_signal(signal):
                        self.signals_generated_today += 1
                        self.last_signal_time = current_time
                        
                        self.logger.info(f"🎯 สร้าง Signal สำเร็จ: {signal.signal_id}")
                
                # รอก่อนสร้าง Signal ถัดไป
                time.sleep(5)  # รอ 5 วินาที
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Signal Generation Loop: {e}")
                time.sleep(10)
    
    def _signal_monitor_loop(self) -> None:
        """Monitor Signal Quality และ Cleanup"""
        while self.generator_active:
            try:
                # ลบ Signals เก่า
                self.signal_aggregator.clear_old_signals()
                
                # Log สถิติ
                active_count = len(self.signal_aggregator.active_signals)
                if active_count > 0:
                    self.logger.debug(f"📊 Active Signals: {active_count} | "
                                    f"Generated Today: {self.signals_generated_today}")
                
                time.sleep(30)  # ตรวจสอบทุก 30 วินาที
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Signal Monitor Loop: {e}")
                time.sleep(60)
    
    def _generate_entry_signal(self) -> Optional[EntrySignal]:
        """สร้าง Entry Signal ใหม่"""
        try:
            # ดึงข้อมูลตลาดปัจจุบัน
            market_data = self._get_current_market_data()
            if not market_data:
                return None
            
            # วิเคราะห์สภาพตลาด
            market_condition = self._analyze_market_condition(market_data)
            
            # เลือกกลยุทธ์
            selected_strategy = self._select_entry_strategy(market_condition)
            
            # สร้าง Signal
            signal = EntrySignal(
                signal_id=f"SIG_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{selected_strategy.value[:3]}",
                timestamp=datetime.now(),
                source_engine=selected_strategy,
                direction=self._determine_signal_direction(market_data, market_condition),
                strength=self._calculate_signal_strength(market_data, market_condition),
                confidence=self._calculate_confidence(market_data, market_condition),
                current_price=market_data.get('current_price', 0.0),
                suggested_volume=self._calculate_suggested_volume(),
                technical_indicators=market_data.get('technical_indicators', {}),
                market_conditions=market_condition,
                signal_quality_score=self._calculate_quality_score(market_data, market_condition),
                risk_reward_ratio=2.0,  # Default 1:2
                probability_success=0.65,  # Default 65%
                urgency_level=2,
                session=self._get_current_session()
            )
            
            return signal
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Signal: {e}")
            return None
    
    def _get_current_market_data(self) -> Optional[Dict[str, Any]]:
        """ดึงข้อมูลตลาดปัจจุบัน"""
        try:
            # ดึงข้อมูลจาก MT5
            import MetaTrader5 as mt5
            
            # ดึงราคาปัจจุบัน
            tick = mt5.symbol_info_tick("XAUUSD")
            if not tick:
                return None
            
            # ดึงข้อมูล OHLC
            rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M5, 0, 100)
            if rates is None or len(rates) == 0:
                return None
            
            current_price = (tick.bid + tick.ask) / 2
            
            return {
                'current_price': current_price,
                'bid': tick.bid,
                'ask': tick.ask,
                'spread': (tick.ask - tick.bid) * 10000,
                'rates': rates,
                'technical_indicators': self._calculate_basic_indicators(rates)
            }
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถดึงข้อมูลตลาดได้: {e}")
            return None
    
    def _calculate_basic_indicators(self, rates) -> Dict[str, float]:
        """คำนวณ Technical Indicators พื้นฐาน"""
        try:
            import numpy as np
            
            closes = np.array([r['close'] for r in rates])
            
            # Simple Moving Averages
            sma_20 = np.mean(closes[-20:]) if len(closes) >= 20 else closes[-1]
            sma_50 = np.mean(closes[-50:]) if len(closes) >= 50 else closes[-1]
            
            # ATR approximation
            highs = np.array([r['high'] for r in rates])
            lows = np.array([r['low'] for r in rates])
            atr = np.mean(highs[-14:] - lows[-14:]) if len(rates) >= 14 else 0.0
            
            return {
                'sma_20': sma_20,
                'sma_50': sma_50,
                'atr': atr,
                'current_close': closes[-1]
            }
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถคำนวณ Indicators ได้: {e}")
            return {}
    
    def _analyze_market_condition(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """วิเคราะห์สภาพตลาด"""
        indicators = market_data.get('technical_indicators', {})
        
        # Trend Analysis
        sma_20 = indicators.get('sma_20', 0)
        sma_50 = indicators.get('sma_50', 0)
        current_price = market_data.get('current_price', 0)
        
        if sma_20 > sma_50 and current_price > sma_20:
            trend = "BULLISH"
        elif sma_20 < sma_50 and current_price < sma_20:
            trend = "BEARISH"
        else:
            trend = "SIDEWAYS"
        
        # Volatility Analysis
        atr = indicators.get('atr', 0)
        volatility = "HIGH" if atr > 2.0 else "MEDIUM" if atr > 1.0 else "LOW"
        
        return {
            'trend': trend,
            'volatility': volatility,
            'atr': atr,
            'spread': market_data.get('spread', 0)
        }
    
    def _select_entry_strategy(self, market_condition: Dict[str, Any]) -> EntryStrategy:
        """เลือกกลยุทธ์การเข้าออร์เดอร์"""
        trend = market_condition.get('trend', 'SIDEWAYS')
        volatility = market_condition.get('volatility', 'MEDIUM')
        
        if trend in ['BULLISH', 'BEARISH'] and volatility == 'HIGH':
            return EntryStrategy.TREND_FOLLOWING
        elif trend == 'SIDEWAYS':
            return EntryStrategy.MEAN_REVERSION
        elif volatility == 'HIGH':
            return EntryStrategy.BREAKOUT_FALSE
        else:
            return EntryStrategy.SCALPING_ENGINE
    
    def _determine_signal_direction(self, market_data: Dict[str, Any], 
                                  market_condition: Dict[str, Any]) -> SignalDirection:
        """กำหนดทิศทางของ Signal"""
        trend = market_condition.get('trend', 'SIDEWAYS')
        current_price = market_data.get('current_price', 0)
        indicators = market_data.get('technical_indicators', {})
        sma_20 = indicators.get('sma_20', current_price)
        
        if trend == 'BULLISH' and current_price > sma_20:
            return SignalDirection.BUY
        elif trend == 'BEARISH' and current_price < sma_20:
            return SignalDirection.SELL
        else:
            # Random direction for sideways market
            import random
            return random.choice([SignalDirection.BUY, SignalDirection.SELL])
    
    def _calculate_signal_strength(self, market_data: Dict[str, Any], 
                                 market_condition: Dict[str, Any]) -> SignalStrength:
        """คำนวณความแรงของ Signal"""
        volatility = market_condition.get('volatility', 'MEDIUM')
        spread = market_condition.get('spread', 0)
        
        if volatility == 'HIGH' and spread < 3.0:
            return SignalStrength.STRONG
        elif volatility == 'MEDIUM':
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    def _calculate_confidence(self, market_data: Dict[str, Any], 
                            market_condition: Dict[str, Any]) -> float:
        """คำนวณความเชื่อมั่นของ Signal"""
        base_confidence = 0.6
        
        # ปรับตาม volatility
        volatility = market_condition.get('volatility', 'MEDIUM')
        if volatility == 'HIGH':
            base_confidence += 0.1
        elif volatility == 'LOW':
            base_confidence -= 0.1
        
        # ปรับตาม spread
        spread = market_condition.get('spread', 0)
        if spread < 2.0:
            base_confidence += 0.1
        elif spread > 5.0:
            base_confidence -= 0.1
        
        return max(0.3, min(0.95, base_confidence))
    
    def _calculate_suggested_volume(self) -> float:
        """คำนวณ Volume ที่แนะนำ"""
        # ใช้ volume พื้นฐาน 0.01 lots
        return 0.01
    
    def _calculate_quality_score(self, market_data: Dict[str, Any], 
                               market_condition: Dict[str, Any]) -> float:
        """คำนวณคะแนนคุณภาพของ Signal"""
        base_score = 60.0
        
        # ปรับตามสภาพตลาด
        trend = market_condition.get('trend', 'SIDEWAYS')
        volatility = market_condition.get('volatility', 'MEDIUM')
        
        if trend != 'SIDEWAYS':
            base_score += 10.0
        
        if volatility == 'MEDIUM':
            base_score += 10.0
        elif volatility == 'HIGH':
            base_score += 5.0
        
        return min(100.0, base_score)
    
    def _get_current_session(self) -> MarketSession:
        """ดึง Market Session ปัจจุบัน"""
        current_hour = datetime.now().hour
        
        if 15 <= current_hour < 24 or current_hour == 0:
            return MarketSession.LONDON
        elif 20 <= current_hour or current_hour < 6:
            return MarketSession.NEW_YORK
        elif 20 <= current_hour < 24:
            return MarketSession.OVERLAP
        else:
            return MarketSession.ASIAN
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """ดึงสถิติการทำงานของ Signal Generator"""
        return {
            'signals_generated_today': self.signals_generated_today,
            'signals_executed_today': self.signals_executed_today,
            'target_signals_per_hour': self.target_signals_per_hour,
            'active_signals_count': len(self.signal_aggregator.active_signals),
            'generator_active': self.generator_active,
            'last_signal_time': self.last_signal_time.strftime("%H:%M:%S") if self.last_signal_time else "Never"
        }
    
    def get_next_entry_signal(self) -> Optional[EntrySignal]:
        """ดึง Entry Signal ถัดไป"""
        return self.signal_aggregator.get_next_signal()

# === GLOBAL SIGNAL GENERATOR INSTANCE ===
_global_signal_generator: Optional[SignalGenerator] = None

def get_signal_generator() -> SignalGenerator:
    """ดึง Signal Generator แบบ Singleton"""
    global _global_signal_generator
    if _global_signal_generator is None:
        _global_signal_generator = SignalGenerator()
    return _global_signal_generator