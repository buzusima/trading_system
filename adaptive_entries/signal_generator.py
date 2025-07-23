#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIGNAL GENERATOR - Entry Signal Coordination Engine
================================================
รวบรวมและประสานงาน Entry Signals จากทุก Entry Engines
ทำหน้าที่เป็นหัวใจหลักในการตัดสินใจเข้าออร์เดอร์

Key Features:
- รวบรวม signals จาก entry engines ทั้งหมด
- ประเมินคุณภาพ signal และความน่าเชื่อถือ
- จัดลำดับความสำคัญของ signals
- ตัดสินใจ final entry signal
- ปรับความถี่การเข้าออร์เดอร์ตาม market conditions
- รองรับ High-Frequency Trading (50-100 lots/วัน)

เชื่อมต่อไปยัง:
- adaptive_entries/entry_engines/* (รับ signals)
- market_intelligence/market_analyzer.py (วิเคราะห์ตลาด)
- adaptive_entries/strategy_selector.py (เลือกกลยุทธ์)
- mt5_integration/order_executor.py (ส่งออร์เดอร์)
"""

import asyncio
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
from utilities.professional_logger import setup_trading_logger
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
    """
    คลาสสำหรับเก็บข้อมูล Entry Signal
    """
    signal_id: str                              # ID เฉพาะของ Signal
    timestamp: datetime                         # เวลาที่สร้าง Signal
    source_engine: EntryStrategy               # Engine ที่สร้าง Signal
    direction: SignalDirection                 # ทิศทางการเทรด
    strength: SignalStrength                   # ความแรงของ Signal
    confidence: float                          # ความเชื่อมั่น (0.0-1.0)
    
    # Market Data
    current_price: float                       # ราคาปัจจุบัน
    suggested_volume: float                    # Volume ที่แนะนำ
    
    # Technical Analysis Data
    technical_indicators: Dict[str, Any] = field(default_factory=dict)
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Signal Quality Metrics
    signal_quality_score: float = 0.0         # คะแนนคุณภาพ Signal (0-100)
    risk_reward_ratio: float = 1.0             # อัตราส่วน Risk:Reward
    probability_success: float = 0.5           # ความน่าจะเป็นที่จะสำเร็จ
    
    # Execution Parameters
    urgency_level: int = 1                     # ระดับความรีบด่วน (1-5)
    max_slippage_points: float = 2.0           # Slippage สูงสุดที่ยอมรับได้
    
    # Metadata
    session: MarketSession                     # Session ที่เกิด Signal
    market_volatility: str = "MEDIUM"          # ความผันผวนของตลาด
    additional_info: Dict[str, Any] = field(default_factory=dict)

class SignalAggregator:
    """
    รวบรวมและประมวลผล Signals จาก Entry Engines ต่างๆ
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
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
        
        # Threading
        self.processing_active = False
        self.signal_processor_thread = None
        
        self.logger.info("📊 เริ่มต้น Signal Aggregator")
    
    def register_entry_engine(self, strategy: EntryStrategy, engine_instance: Any) -> None:
        """
        ลงทะเบียน Entry Engine
        """
        self.entry_engines[strategy] = engine_instance
        self.logger.info(f"✅ ลงทะเบียน {strategy.value} Engine")
    
    def add_signal(self, signal: EntrySignal) -> bool:
        """
        เพิ่ม Signal เข้าสู่ระบบ
        """
        try:
            # ตรวจสอบคุณภาพ Signal
            if not self._validate_signal_quality(signal):
                self.logger.debug(f"🚫 Signal คุณภาพต่ำ: {signal.signal_id}")
                return False
            
            # คำนวณ Signal Quality Score
            signal.signal_quality_score = self._calculate_quality_score(signal)
            
            # เพิ่มเข้า Queue
            self.signal_queue.put(signal)
            self.logger.debug(f"📈 เพิ่ม Signal: {signal.signal_id} | Score: {signal.signal_quality_score:.1f}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเพิ่ม Signal: {e}")
            return False
    
    def _validate_signal_quality(self, signal: EntrySignal) -> bool:
        """
        ตรวจสอบคุณภาพ Signal ขั้นพื้นฐาน
        """
        # ตรวจสอบความแรง
        if signal.strength.value < self.min_signal_strength.value:
            return False
        
        # ตรวจสอบความเชื่อมั่น
        if signal.confidence < self.min_confidence_level:
            return False
        
        # ตรวจสอบอายุของ Signal (ต้องไม่เก่าเกิน 60 วินาที)
        signal_age = (datetime.now() - signal.timestamp).total_seconds()
        if signal_age > 60:
            return False
        
        return True
    
    def _calculate_quality_score(self, signal: EntrySignal) -> float:
        """
        คำนวณคะแนนคุณภาพของ Signal
        """
        score = 0.0
        
        # Base Score จากความแรง (0-30 คะแนน)
        score += signal.strength.value * 6
        
        # Confidence Score (0-25 คะแนน)
        score += signal.confidence * 25
        
        # Engine Weight Score (0-20 คะแนน)
        engine_weight = self.engine_weights.get(signal.source_engine, 0.1)
        score += engine_weight * 20
        
        # Market Conditions Score (0-15 คะแนน)
        volatility_score = {"LOW": 5, "MEDIUM": 10, "HIGH": 15}.get(signal.market_volatility, 8)
        score += volatility_score
        
        # Risk-Reward Ratio Score (0-10 คะแนน)
        rr_score = min(signal.risk_reward_ratio * 3, 10)
        score += rr_score
        
        return min(score, 100.0)  # ไม่เกิน 100 คะแนน

class SignalGenerator:
    """
    🎯 Main Signal Generator Class
    
    ทำหน้าที่ประสานงานการสร้าง Entry Signals
    รองรับ High-Frequency Trading และ Adaptive Strategy Selection
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
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
        
    def _calculate_target_signals(self) -> int:
        """
        คำนวณเป้าหมาย Signals ต่อชั่วโมง
        เพื่อให้ได้ Volume 50-100 lots/วัน
        """
        # คำนวณจาก daily volume target
        daily_target = (self.settings.daily_volume_target_min + 
                       self.settings.daily_volume_target_max) / 2
        
        # 24 ชั่วโมงการเทรด
        hourly_target = daily_target / 24
        
        # เผื่อสำหรับ signals ที่ไม่ได้ execute
        return int(hourly_target * 1.5)
    
    @handle_trading_errors(ErrorCategory.SIGNAL_GENERATION, ErrorSeverity.MEDIUM)
    async def start_signal_generation(self) -> None:
        """
        เริ่มต้นการสร้าง Signals
        """
        if self.generator_active:
            self.logger.warning("⚠️ Signal Generator กำลังทำงานอยู่แล้ว")
            return
        
        self.logger.info("🚀 เริ่มต้น Signal Generation System")
        
        # เชื่อมต่อ Market Analyzer
        try:
            from market_intelligence.market_analyzer import MarketAnalyzer
            self.market_analyzer = MarketAnalyzer()
            await self.market_analyzer.start_analysis()
        except ImportError:
            self.logger.error("❌ ไม่สามารถเชื่อมต่อ Market Analyzer")
            return
        
        # เชื่อมต่อ Strategy Selector
        try:
            from adaptive_entries.strategy_selector import StrategySelector
            self.strategy_selector = StrategySelector()
        except ImportError:
            self.logger.error("❌ ไม่สามารถเชื่อมต่อ Strategy Selector")
            return
        
        # เริ่มต้น Entry Engines
        await self._initialize_entry_engines()
        
        # เริ่ม Threads
        self.generator_active = True
        self.generator_thread = threading.Thread(target=self._signal_generation_loop, daemon=True)
        self.signal_monitor_thread = threading.Thread(target=self._signal_monitoring_loop, daemon=True)
        
        self.generator_thread.start()
        self.signal_monitor_thread.start()
        
        self.logger.info("✅ Signal Generation System เริ่มทำงานแล้ว")
    
    async def _initialize_entry_engines(self) -> None:
        """
        เริ่มต้น Entry Engines ทั้งหมด
        """
        try:
            # Trend Following Engine
            from adaptive_entries.entry_engines.trend_following import TrendFollowingEngine
            trend_engine = TrendFollowingEngine()
            self.signal_aggregator.register_entry_engine(EntryStrategy.TREND_FOLLOWING, trend_engine)
            
            # Mean Reversion Engine  
            from adaptive_entries.entry_engines.mean_reversion import MeanReversionEngine
            mean_engine = MeanReversionEngine()
            self.signal_aggregator.register_entry_engine(EntryStrategy.MEAN_REVERSION, mean_engine)
            
            # อื่นๆ จะเพิ่มเมื่อสร้างไฟล์
            self.logger.info("✅ เริ่มต้น Entry Engines สำเร็จ")
            
        except ImportError as e:
            self.logger.error(f"❌ ไม่สามารถโหลด Entry Engines: {e}")
    
    def _signal_generation_loop(self) -> None:
        """
        Main Signal Generation Loop
        รันใน separate thread
        """
        self.logger.info("🔄 เริ่มต้น Signal Generation Loop")
        
        while self.generator_active:
            try:
                # ตรวจสอบเวลาระหว่าง Signals
                time_since_last = datetime.now() - self.last_signal_time
                if time_since_last < self.min_signal_interval:
                    time.sleep(0.1)
                    continue
                
                # สร้าง Signals จาก Entry Engines
                self._generate_signals_from_engines()
                
                # พัก 100ms ก่อน loop ถัดไป
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Signal Generation Loop: {e}")
                time.sleep(1)
    
    def _generate_signals_from_engines(self) -> None:
        """
        สร้าง Signals จาก Entry Engines ทั้งหมด
        """
        if not self.market_analyzer or not self.strategy_selector:
            return
        
        # ได้ Market Conditions ปัจจุบัน
        market_state = self.market_analyzer.get_current_market_state()
        current_session = self.market_analyzer.get_current_session()
        
        # เลือก Active Strategies ตาม Market Conditions
        active_strategies = self.strategy_selector.select_strategies(market_state, current_session)
        
        # สร้าง Signals จาก Active Engines
        for strategy in active_strategies:
            if strategy in self.signal_aggregator.entry_engines:
                engine = self.signal_aggregator.entry_engines[strategy]
                try:
                    # เรียก generate_signal จาก engine
                    if hasattr(engine, 'generate_signal'):
                        signal = engine.generate_signal(market_state, current_session)
                        if signal:
                            self.signal_aggregator.add_signal(signal)
                            self.signals_generated_today += 1
                            self.last_signal_time = datetime.now()
                            
                except Exception as e:
                    self.logger.error(f"❌ ข้อผิดพลาดใน {strategy.value} Engine: {e}")
    
    def _signal_monitoring_loop(self) -> None:
        """
        ตรวจสอบและประมวลผล Signals ที่เข้ามา
        """
        self.logger.info("👁️ เริ่มต้น Signal Monitoring Loop")
        
        while self.generator_active:
            try:
                # ดึง Signal จาก Queue (timeout 1 วินาที)
                if not self.signal_aggregator.signal_queue.empty():
                    signal = self.signal_aggregator.signal_queue.get(timeout=1)
                    
                    # ประมวลผล Signal
                    self._process_final_signal(signal)
                else:
                    time.sleep(0.1)
                    
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Signal Monitoring: {e}")
                time.sleep(1)
    
    def _process_final_signal(self, signal: EntrySignal) -> None:
        """
        ประมวลผล Final Signal และตัดสินใจส่งออร์เดอร์
        """
        try:
            # ตรวจสอบ Final Signal Quality
            if signal.signal_quality_score < self.signal_aggregator.min_quality_score:
                self.logger.debug(f"🚫 Final Signal คุณภาพต่ำ: {signal.signal_id}")
                return
            
            # บันทึก Signal
            self.signal_aggregator.active_signals.append(signal)
            self.signal_aggregator.signal_history.append(signal)
            
            # เตรียมส่งออร์เดอร์
            self._prepare_order_execution(signal)
            
            self.logger.info(f"✅ ประมวลผล Signal: {signal.signal_id} | "
                           f"Direction: {signal.direction.value} | "
                           f"Score: {signal.signal_quality_score:.1f}")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการประมวลผล Final Signal: {e}")
    
    def _prepare_order_execution(self, signal: EntrySignal) -> None:
        """
        เตรียมข้อมูลสำหรับส่งออร์เดอร์
        """
        try:
            # TODO: เชื่อมต่อไป mt5_integration/order_executor.py
            self.logger.info(f"📤 เตรียมส่งออร์เดอร์: {signal.direction.value} "
                           f"{signal.suggested_volume} lots")
            
            # เพิ่มจำนวน signals ที่ execute
            self.signals_executed_today += 1
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเตรียมออร์เดอร์: {e}")
    
    def stop_signal_generation(self) -> None:
        """
        หยุดการสร้าง Signals
        """
        self.logger.info("🛑 หยุด Signal Generation System")
        
        self.generator_active = False
        
        # รอให้ Threads จบ
        if self.generator_thread and self.generator_thread.is_alive():
            self.generator_thread.join(timeout=5)
        
        if self.signal_monitor_thread and self.signal_monitor_thread.is_alive():
            self.signal_monitor_thread.join(timeout=5)
        
        self.logger.info("✅ Signal Generation System หยุดแล้ว")
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """
        ดึงสถิติการทำงานของ Signal Generator
        """
        return {
            "signals_generated_today": self.signals_generated_today,
            "signals_executed_today": self.signals_executed_today,
            "target_signals_per_hour": self.target_signals_per_hour,
            "active_signals_count": len(self.signal_aggregator.active_signals),
            "signal_history_count": len(self.signal_aggregator.signal_history),
            "execution_rate": (self.signals_executed_today / max(self.signals_generated_today, 1)) * 100,
            "generator_active": self.generator_active
        }
    
    def get_active_signals(self) -> List[EntrySignal]:
        """
        ดึงรายการ Active Signals
        """
        return self.signal_aggregator.active_signals.copy()
    
    def clear_old_signals(self, max_age_minutes: int = 30) -> int:
        """
        ลบ Signals เก่าออก
        """
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(minutes=max_age_minutes)
        
        # นับ signals เก่า
        old_count = len([s for s in self.signal_aggregator.active_signals 
                        if s.timestamp < cutoff_time])
        
        # ลบ signals เก่า
        self.signal_aggregator.active_signals = [
            s for s in self.signal_aggregator.active_signals 
            if s.timestamp >= cutoff_time
        ]
        
        if old_count > 0:
            self.logger.info(f"🧹 ลบ Signals เก่า {old_count} รายการ")
        
        return old_count

# === GLOBAL SIGNAL GENERATOR INSTANCE ===
_global_signal_generator: Optional[SignalGenerator] = None

def get_signal_generator() -> SignalGenerator:
    """
    ดึง SignalGenerator แบบ Singleton
    """
    global _global_signal_generator
    if _global_signal_generator is None:
        _global_signal_generator = SignalGenerator()
    return _global_signal_generator

async def main():
    """
    ทดสอบการทำงานของ Signal Generator
    """
    print("🧪 ทดสอบ Signal Generator")
    
    generator = get_signal_generator()
    
    try:
        await generator.start_signal_generation()
        
        # รัน 10 วินาที
        await asyncio.sleep(10)
        
        # แสดงสถิติ
        stats = generator.get_signal_statistics()
        print(f"📊 สถิติ: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
    finally:
        generator.stop_signal_generation()

if __name__ == "__main__":
    asyncio.run(main())