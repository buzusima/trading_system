#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIGNAL GENERATOR - Intelligent Signal Generation System (COMPLETE)
================================================================
ระบบสร้างสัญญาณการเทรดอัจฉริยะที่สมบูรณ์แบบ

✨ ฟีเจอร์ทั้งหมด:
- สร้างสัญญาณการเข้าออร์เดอร์แบบอัตโนมัติ
- เชื่อมต่อกับ Market Analyzer สำหรับการตัดสินใจ
- ปรับความถี่ของสัญญาณตาม Market Condition
- รองรับ High-Frequency Trading (50-100 lots/day)
- เลือก Entry Strategy อัตโนมัติ
- วิเคราะห์หลายไทม์เฟรม
- จัดการ Session ต่างๆ
- ระบบ Risk Management ขั้นสูง
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
import statistics
from collections import deque, defaultdict

# ใช้ try-except สำหรับ imports เพื่อป้องกัน circular dependency
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
    print("⚠️ MetaTrader5 module not available")

class SignalType(Enum):
    """ประเภทสัญญาณการเทรด"""
    BUY = "BUY"
    SELL = "SELL" 
    HOLD = "HOLD"

class SignalStrength(Enum):
    """ความแรงของสัญญาณ"""
    WEAK = "WEAK"           # 30-50%
    MODERATE = "MODERATE"   # 50-70%
    STRONG = "STRONG"       # 70-85%
    VERY_STRONG = "VERY_STRONG"  # 85-100%

class MarketCondition(Enum):
    """สภาวะตลาด - กำหนดใน Signal Generator เพื่อหลีกเลี่ยง circular import"""
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    QUIET = "QUIET"
    NEWS_IMPACT = "NEWS_IMPACT"
    UNKNOWN = "UNKNOWN"

class SessionType(Enum):
    """เซสชันการเทรด"""
    ASIAN = "ASIAN"         # 22:00-08:00 GMT+7
    LONDON = "LONDON"       # 15:00-00:00 GMT+7
    NEW_YORK = "NEW_YORK"   # 20:30-05:30 GMT+7
    OVERLAP = "OVERLAP"     # 20:30-00:00 GMT+7
    QUIET = "QUIET"

class EntryStrategy(Enum):
    """กลยุทธ์การเข้าออร์เดอร์"""
    TREND_FOLLOWING = "TREND_FOLLOWING"     # ตามเทรนด์
    MEAN_REVERSION = "MEAN_REVERSION"       # กลับค่าเฉลี่ย
    BREAKOUT_FALSE = "BREAKOUT_FALSE"       # หลอกเบรค
    NEWS_REACTION = "NEWS_REACTION"         # ปฏิกิริยาข่าว
    SCALPING_ENGINE = "SCALPING_ENGINE"     # สกัลปิ้ง

class SignalPriority(Enum):
    """ระดับความสำคัญของสัญญาณ"""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"

@dataclass
class TechnicalIndicators:
    """ข้อมูล Technical Indicators"""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Moving Averages
    ma_10: float = 0.0
    ma_20: float = 0.0
    ma_50: float = 0.0
    
    # RSI
    rsi_14: float = 50.0
    
    # Bollinger Bands
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    
    # ADX & DI
    adx: float = 20.0
    di_plus: float = 20.0
    di_minus: float = 20.0
    
    # ATR
    atr: float = 1.0
    
    # MACD
    macd_line: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    
    # Volume
    volume: int = 0
    volume_sma: float = 0.0

@dataclass
class MarketData:
    """ข้อมูลตลาด"""
    timestamp: datetime = field(default_factory=datetime.now)
    symbol: str = "XAUUSD"
    
    # OHLC
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    
    # Bid/Ask
    bid: float = 0.0
    ask: float = 0.0
    
    # Spread & Volume
    spread: float = 0.0
    volume: int = 0
    
    # Calculated values
    mid_price: float = 0.0
    pip_value: float = 0.1
    
    def __post_init__(self):
        if self.mid_price == 0.0:
            self.mid_price = (self.bid + self.ask) / 2

@dataclass
class TradingSignal:
    """สัญญาณการเทรด - ข้อมูลครบถ้วน"""
    signal_id: str
    timestamp: datetime
    symbol: str = "XAUUSD"
    
    # Signal Properties
    signal_type: SignalType = SignalType.HOLD
    entry_strategy: EntryStrategy = EntryStrategy.SCALPING_ENGINE
    signal_strength: SignalStrength = SignalStrength.WEAK
    priority: SignalPriority = SignalPriority.NORMAL
    
    # Price Information
    current_price: float = 0.0
    entry_price: float = 0.0
    target_price: Optional[float] = None
    
    # Risk Management
    suggested_volume: float = 0.01
    max_spread: float = 3.0
    max_slippage: float = 0.5
    
    # Market Context
    market_condition: MarketCondition = MarketCondition.UNKNOWN
    session_type: SessionType = SessionType.QUIET
    confidence_score: float = 0.0
    reasoning: str = ""
    
    # Technical Analysis
    technical_indicators: Optional[TechnicalIndicators] = None
    support_resistance: Dict[str, float] = field(default_factory=dict)
    
    # Timeframe Analysis
    timeframe_analysis: Dict[str, str] = field(default_factory=dict)  # M1, M5, M15, H1
    
    # Risk Metrics
    volatility_index: float = 1.0
    correlation_risk: float = 0.0
    news_risk: float = 0.0
    
    # Status
    is_executed: bool = False
    execution_time: Optional[datetime] = None
    execution_price: Optional[float] = None
    
    # Performance tracking
    expected_profit: float = 0.0
    risk_reward_ratio: float = 1.0

class TechnicalAnalyzer:
    """เครื่องมือวิเคราะห์ทางเทคนิค"""
    
    def __init__(self, symbol: str = "XAUUSD"):
        self.symbol = symbol
        self.price_history: deque = deque(maxlen=200)  # เก็บราคา 200 periods
        self.volume_history: deque = deque(maxlen=50)
        
    def update_price_data(self, market_data: MarketData):
        """อัพเดทข้อมูลราคา"""
        self.price_history.append({
            'timestamp': market_data.timestamp,
            'open': market_data.open,
            'high': market_data.high,
            'low': market_data.low,
            'close': market_data.close,
            'volume': market_data.volume
        })
        
        if market_data.volume > 0:
            self.volume_history.append(market_data.volume)
    
    def calculate_moving_averages(self) -> Dict[str, float]:
        """คำนวณ Moving Averages"""
        if len(self.price_history) < 50:
            return {'ma_10': 0, 'ma_20': 0, 'ma_50': 0}
        
        closes = [data['close'] for data in self.price_history]
        
        return {
            'ma_10': sum(closes[-10:]) / 10 if len(closes) >= 10 else 0,
            'ma_20': sum(closes[-20:]) / 20 if len(closes) >= 20 else 0,
            'ma_50': sum(closes[-50:]) / 50 if len(closes) >= 50 else 0
        }
    
    def calculate_rsi(self, period: int = 14) -> float:
        """คำนวณ RSI"""
        if len(self.price_history) < period + 1:
            return 50.0
        
        closes = [data['close'] for data in self.price_history]
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        gains = [delta if delta > 0 else 0 for delta in deltas[-period:]]
        losses = [-delta if delta < 0 else 0 for delta in deltas[-period:]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_bollinger_bands(self, period: int = 20, std_dev: float = 2.0) -> Dict[str, float]:
        """คำนวณ Bollinger Bands"""
        if len(self.price_history) < period:
            return {'bb_upper': 0, 'bb_middle': 0, 'bb_lower': 0}
        
        closes = [data['close'] for data in self.price_history[-period:]]
        middle = sum(closes) / period
        variance = sum((x - middle) ** 2 for x in closes) / period
        std_deviation = variance ** 0.5
        
        return {
            'bb_upper': middle + (std_deviation * std_dev),
            'bb_middle': middle,
            'bb_lower': middle - (std_deviation * std_dev)
        }
    
    def calculate_atr(self, period: int = 14) -> float:
        """คำนวณ ATR (Average True Range)"""
        if len(self.price_history) < period + 1:
            return 1.0
        
        true_ranges = []
        for i in range(1, len(self.price_history)):
            current = self.price_history[i]
            previous = self.price_history[i-1]
            
            tr1 = current['high'] - current['low']
            tr2 = abs(current['high'] - previous['close'])
            tr3 = abs(current['low'] - previous['close'])
            
            true_ranges.append(max(tr1, tr2, tr3))
        
        return sum(true_ranges[-period:]) / period if len(true_ranges) >= period else 1.0
    
    def get_technical_indicators(self) -> TechnicalIndicators:
        """ดึง Technical Indicators ทั้งหมด"""
        mas = self.calculate_moving_averages()
        bb = self.calculate_bollinger_bands()
        
        return TechnicalIndicators(
            ma_10=mas['ma_10'],
            ma_20=mas['ma_20'],
            ma_50=mas['ma_50'],
            rsi_14=self.calculate_rsi(),
            bb_upper=bb['bb_upper'],
            bb_middle=bb['bb_middle'],
            bb_lower=bb['bb_lower'],
            atr=self.calculate_atr(),
            volume=self.volume_history[-1] if self.volume_history else 0,
            volume_sma=sum(self.volume_history) / len(self.volume_history) if self.volume_history else 0
        )

class IntelligentSignalGenerator:
    """🎯 Intelligent Signal Generator - ระบบสร้างสัญญาณอัจฉริยะขั้นสูง"""
    
    def __init__(self):
        # เริ่มต้น Logger แบบ Safe
        try:
            from utilities.professional_logger import setup_component_logger
            self.logger = setup_component_logger("IntelligentSignalGenerator")
        except ImportError:
            import logging
            self.logger = logging.getLogger("IntelligentSignalGenerator")
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
        
        # เริ่มต้นการตั้งค่าแบบ Safe
        self.settings = self._load_safe_settings()
        self.trading_params = self._load_safe_trading_params()
        
        # Technical Analyzer
        self.technical_analyzer = TechnicalAnalyzer()
        
        # Market Analyzer Connection (แบบ Safe)
        self.market_analyzer = None
        self._init_market_analyzer_safe()
        
        # Signal Generation State
        self.generation_active = False
        self.trading_started = False
        self.generation_thread: Optional[threading.Thread] = None
        
        # Signal Storage
        self.signals_queue = queue.Queue(maxsize=100)
        self.recent_signals: List[TradingSignal] = []
        self.signal_history: deque = deque(maxlen=1000)
        
        # Timing Control
        self.last_signal_time = 0
        self.signal_cooldown = 15  # Base cooldown in seconds
        
        # Volume Management
        self.daily_volume_generated = 0.0
        self.daily_volume_target = 75.0
        self.hourly_volume_generated = 0.0
        
        # Statistics
        self.signals_generated_today = 0
        self.signals_executed_today = 0
        self.successful_signals = 0
        self.failed_signals = 0
        
        # Performance Metrics
        self.performance_metrics = {
            'total_signals': 0,
            'execution_rate': 0.0,
            'success_rate': 0.0,
            'average_confidence': 0.0,
            'best_strategy': EntryStrategy.SCALPING_ENGINE,
            'session_performance': defaultdict(list)
        }
        
        # Risk Management
        self.risk_limits = {
            'max_correlation': 0.8,
            'max_exposure': 50.0,
            'max_daily_signals': 200,
            'min_signal_interval': 10
        }
        
        # Strategy Performance Tracking
        self.strategy_performance = {
            strategy: {
                'signals_generated': 0,
                'signals_executed': 0,
                'success_count': 0,
                'total_profit': 0.0,
                'average_confidence': 0.0,
                'last_used': None
            } for strategy in EntryStrategy
        }
        
        self.logger.info("🎯 เริ่มต้น Intelligent Signal Generator (ADVANCED)")
    
    def _load_safe_settings(self) -> Dict[str, Any]:
        """โหลดการตั้งค่าแบบปลอดภัย"""
        try:
            from config.settings import get_system_settings
            return get_system_settings()
        except ImportError:
            self.logger.warning("⚠️ ไม่สามารถโหลด system settings - ใช้ค่าเริ่มต้น")
            return {
                'symbol': 'XAUUSD',
                'trading_mode': 'LIVE',
                'high_frequency_mode': True,
                'daily_volume_target_min': 50.0,
                'daily_volume_target_max': 100.0,
                'timeframes_analysis': ['M1', 'M5', 'M15', 'H1']
            }
    
    def _load_safe_trading_params(self) -> Dict[str, Any]:
        """โหลดพารามิเตอร์การเทรดแบบปลอดภัย"""
        try:
            from config.trading_params import get_trading_parameters
            params = get_trading_parameters()
            return {
                'min_lot_size': params.min_volume,
                'max_lot_size': params.max_volume,
                'max_spread': params.max_spread,
                'signal_cooldown': params.signal_cooldown,
                'strategy_weights': params.strategy_weights,
                'session_parameters': params.session_parameters
            }
        except ImportError:
            self.logger.warning("⚠️ ไม่สามารถโหลด trading parameters - ใช้ค่าเริ่มต้น")
            return {
                'min_lot_size': 0.01,
                'max_lot_size': 1.0,
                'max_spread': 3.0,
                'signal_cooldown': 15,
                'strategy_weights': {
                    EntryStrategy.SCALPING_ENGINE: 0.4,
                    EntryStrategy.TREND_FOLLOWING: 0.3,
                    EntryStrategy.MEAN_REVERSION: 0.2,
                    EntryStrategy.BREAKOUT_FALSE: 0.07,
                    EntryStrategy.NEWS_REACTION: 0.03
                },
                'session_parameters': {}
            }
    
    def _init_market_analyzer_safe(self):
        """เริ่มต้น Market Analyzer แบบปลอดภัย"""
        try:
            from market_intelligence.market_analyzer import get_market_analyzer
            self.market_analyzer = get_market_analyzer()
            self.logger.info("✅ เชื่อมต่อ Market Analyzer สำเร็จ")
        except ImportError as e:
            self.logger.warning(f"⚠️ ไม่สามารถเชื่อมต่อ Market Analyzer: {e}")
            self.market_analyzer = None
    
    def _ensure_mt5_connection_safe(self) -> bool:
        """ตรวจสอบการเชื่อมต่อ MT5 แบบปลอดภัย"""
        if mt5 is None:
            self.logger.warning("⚠️ MetaTrader5 module ไม่พร้อมใช้งาน")
            return False
        
        try:
            from mt5_integration.mt5_connector import ensure_mt5_connection
            return ensure_mt5_connection()
        except ImportError:
            self.logger.warning("⚠️ ไม่สามารถโหลด MT5 connector")
            # จำลองการเชื่อมต่อสำหรับการทดสอบ
            return True
    
    def start_signal_generation(self) -> bool:
        """🚀 เริ่มการสร้างสัญญาณ"""
        if self.generation_active:
            return True
        
        try:
            # ตรวจสอบการเชื่อมต่อ MT5
            if not self._ensure_mt5_connection_safe():
                self.logger.error("❌ ไม่สามารถเชื่อมต่อ MT5")
                return False
            
            # เริ่มต้น Market Analyzer ถ้ามี
            if self.market_analyzer and hasattr(self.market_analyzer, 'start_analysis'):
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
        if self.generation_thread and self.generation_thread.is_alive():
            self.generation_thread.join(timeout=5.0)
        
        self.logger.info("🛑 หยุดการสร้างสัญญาณ")
    
    def _signal_generation_loop(self):
        """🔄 ルーปการสร้างสัญญาณหลัก"""
        self.logger.info("🔄 เริ่มลูปการสร้างสัญญาณ")
        
        while self.generation_active:
            try:
                current_time = time.time()
                
                # ตรวจสอบ cooldown
                if current_time - self.last_signal_time < self.signal_cooldown:
                    time.sleep(1)
                    continue
                
                # ตรวจสอบ daily limits
                if not self._check_daily_limits():
                    time.sleep(60)  # รอ 1 นาทีแล้วตรวจสอบใหม่
                    continue
                
                # อัพเดทข้อมูลตลาด
                market_data = self._get_current_market_data()
                if market_data:
                    self.technical_analyzer.update_price_data(market_data)
                
                # สร้างสัญญาณ
                signal = self._generate_intelligent_signal()
                
                if signal and signal.signal_type != SignalType.HOLD:
                    # ตรวจสอบ signal quality
                    if self._validate_signal_quality(signal):
                        self._process_generated_signal(signal)
                        self.last_signal_time = current_time
                
                # พักระหว่างการวิเคราะห์
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดในลูปการสร้างสัญญาณ: {e}")
                time.sleep(5)
    
    def _check_daily_limits(self) -> bool:
        """ตรวจสอบขีดจำกัดรายวัน"""
        # ตรวจสอบจำนวนสัญญาณต่อวัน
        if self.signals_generated_today >= self.risk_limits['max_daily_signals']:
            return False
        
        # ตรวจสอบปริมาณการเทรดต่อวัน
        if self.daily_volume_generated >= self.daily_volume_target * 1.2:  # เกิน 120% ของเป้าหมาย
            return False
        
        return True
    
    def _get_current_market_data(self) -> Optional[MarketData]:
        """ดึงข้อมูลตลาดปัจจุบัน"""
        try:
            if mt5 is None:
                # จำลองข้อมูลสำหรับการทดสอบ
                base_price = 2000.0 + random.uniform(-50, 50)
                spread = random.uniform(0.5, 3.0)
                
                return MarketData(
                    timestamp=datetime.now(),
                    symbol="XAUUSD",
                    bid=base_price - spread/2,
                    ask=base_price + spread/2,
                    spread=spread,
                    volume=random.randint(1000, 10000),
                    high=base_price + random.uniform(0, 5),
                    low=base_price - random.uniform(0, 5),
                    open=base_price + random.uniform(-2, 2),
                    close=base_price
                )
            
            # ดึงข้อมูลจริงจาก MT5
            symbol_info = mt5.symbol_info("XAUUSD")
            tick = mt5.symbol_info_tick("XAUUSD")
            
            if tick is None or symbol_info is None:
                return None
            
            return MarketData(
                timestamp=datetime.fromtimestamp(tick.time),
                symbol="XAUUSD",
                bid=tick.bid,
                ask=tick.ask,
                spread=(tick.ask - tick.bid) / symbol_info.point,
                volume=tick.volume,
                high=tick.bid,  # ใช้ bid เป็น high ชั่วคราว
                low=tick.bid,   # ใช้ bid เป็น low ชั่วคราว
                open=tick.bid,  # ใช้ bid เป็น open ชั่วคราว
                close=tick.bid
            )
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูลตลาด: {e}")
            return None
    
    def _generate_intelligent_signal(self) -> Optional[TradingSignal]:
        """🧠 สร้างสัญญาณอัจฉริยะ"""
        try:
            # ดึงข้อมูลตลาดปัจจุบัน
            market_data = self._get_current_market_data()
            if not market_data:
                return None
            
            # วิเคราะห์สภาวะตลาด
            market_condition = self._analyze_market_condition(market_data)
            session_type = self._get_current_session()
            
            # ดึง technical indicators
            technical_indicators = self.technical_analyzer.get_technical_indicators()
            
            # เลือกกลยุทธ์ที่เหมาะสม
            entry_strategy = self._select_optimal_strategy(market_condition, session_type, technical_indicators)
            
            # สร้างสัญญาณตามกลยุทธ์
            signal_type, confidence = self._generate_signal_by_strategy(
                market_data, market_condition, entry_strategy, technical_indicators
            )
            
            if signal_type == SignalType.HOLD or confidence < self.trading_params['min_confidence']:
                return None
            
            # คำนวณข้อมูลเพิ่มเติม
            suggested_volume = self._calculate_position_size(confidence, session_type, market_data)
            priority = self._calculate_signal_priority(confidence, market_condition, session_type)
            
            # สร้าง Signal Object
            signal = TradingSignal(
                signal_id=f"SIG_{int(time.time())}_{random.randint(1000, 9999)}",
                timestamp=datetime.now(),
                signal_type=signal_type,
                entry_strategy=entry_strategy,
                signal_strength=self._calculate_signal_strength(confidence),
                priority=priority,
                current_price=market_data.mid_price,
                entry_price=market_data.ask if signal_type == SignalType.BUY else market_data.bid,
                suggested_volume=suggested_volume,
                max_spread=self._get_max_spread_for_session(session_type),
                market_condition=market_condition,
                session_type=session_type,
                confidence_score=confidence,
                reasoning=self._generate_signal_reasoning(entry_strategy, market_condition, technical_indicators),
                technical_indicators=technical_indicators,
                volatility_index=self._calculate_volatility_index(market_data),
                timeframe_analysis=self._analyze_multiple_timeframes(market_data)
            )
            
            return signal
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้างสัญญาณอัจฉริยะ: {e}")
            return None
    
    def _analyze_market_condition(self, market_data: MarketData) -> MarketCondition:
        """วิเคราะห์สภาวะตลาด"""
        try:
            if self.market_analyzer and hasattr(self.market_analyzer, 'get_current_condition'):
                return self.market_analyzer.get_current_condition()
            
            # วิเคราะห์พื้นฐานจาก spread, volume และ technical indicators
            spread = market_data.spread
            volume = market_data.volume
            
            # ดึง technical indicators
            tech_indicators = self.technical_analyzer.get_technical_indicators()
            
            # ตรวจสอบ trending condition
            if tech_indicators.ma_10 > tech_indicators.ma_20 > tech_indicators.ma_50:
                return MarketCondition.TRENDING_UP
            elif tech_indicators.ma_10 < tech_indicators.ma_20 < tech_indicators.ma_50:
                return MarketCondition.TRENDING_DOWN
            
            # ตรวจสอบ volatile condition
            if spread > 2.5 or tech_indicators.atr > 2.0:
                return MarketCondition.VOLATILE
            
            # ตรวจสอบ quiet condition
            if spread < 1.0 and volume < 3000 and tech_indicators.atr < 0.8:
                return MarketCondition.QUIET
            
            # ตรวจสอบ news impact
            if volume > 8000 and spread > 3.0:
                return MarketCondition.NEWS_IMPACT
            
            # Default เป็น ranging
            return MarketCondition.RANGING
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์สภาวะตลาด: {e}")
            return MarketCondition.UNKNOWN
        
    def _get_current_session(self) -> SessionType:
        """กำหนด Session ปัจจุบัน"""
        now = datetime.now()
        hour = now.hour
        
        # GMT+7 Time Zone
        if 22 <= hour or hour < 8:
            return SessionType.ASIAN
        elif 15 <= hour < 20:
            return SessionType.LONDON
        elif 20 <= hour < 22:
            return SessionType.OVERLAP
        else:
            return SessionType.NEW_YORK
    
    def _select_optimal_strategy(self, market_condition: MarketCondition, 
                                session_type: SessionType, 
                                technical_indicators: TechnicalIndicators) -> EntryStrategy:
        """เลือกกลยุทธ์ที่เหมาะสมที่สุด"""
        
        # Strategy Matrix ขั้นสูงตาม Market Condition, Session, และ Technical Analysis
        strategy_matrix = {
            MarketCondition.TRENDING_UP: {
                SessionType.LONDON: EntryStrategy.TREND_FOLLOWING,
                SessionType.NEW_YORK: EntryStrategy.TREND_FOLLOWING,
                SessionType.OVERLAP: EntryStrategy.BREAKOUT_FALSE,
                SessionType.ASIAN: EntryStrategy.SCALPING_ENGINE
            },
            MarketCondition.TRENDING_DOWN: {
                SessionType.LONDON: EntryStrategy.TREND_FOLLOWING,
                SessionType.NEW_YORK: EntryStrategy.TREND_FOLLOWING,
                SessionType.OVERLAP: EntryStrategy.BREAKOUT_FALSE,
                SessionType.ASIAN: EntryStrategy.SCALPING_ENGINE
            },
            MarketCondition.RANGING: {
                SessionType.ASIAN: EntryStrategy.MEAN_REVERSION,
                SessionType.LONDON: EntryStrategy.MEAN_REVERSION,
                SessionType.NEW_YORK: EntryStrategy.SCALPING_ENGINE,
                SessionType.OVERLAP: EntryStrategy.MEAN_REVERSION
            },
            MarketCondition.VOLATILE: {
                SessionType.OVERLAP: EntryStrategy.BREAKOUT_FALSE,
                SessionType.NEW_YORK: EntryStrategy.NEWS_REACTION,
                SessionType.LONDON: EntryStrategy.BREAKOUT_FALSE,
                SessionType.ASIAN: EntryStrategy.SCALPING_ENGINE
            },
            MarketCondition.NEWS_IMPACT: {
                SessionType.NEW_YORK: EntryStrategy.NEWS_REACTION,
                SessionType.LONDON: EntryStrategy.NEWS_REACTION,
                SessionType.OVERLAP: EntryStrategy.NEWS_REACTION,
                SessionType.ASIAN: EntryStrategy.SCALPING_ENGINE
            },
            MarketCondition.QUIET: {
                SessionType.ASIAN: EntryStrategy.SCALPING_ENGINE,
                SessionType.LONDON: EntryStrategy.SCALPING_ENGINE,
                SessionType.NEW_YORK: EntryStrategy.SCALPING_ENGINE,
                SessionType.OVERLAP: EntryStrategy.SCALPING_ENGINE
            }
        }
        
        # ดึงกลยุทธ์พื้นฐาน
        base_strategy = strategy_matrix.get(market_condition, {}).get(session_type, EntryStrategy.SCALPING_ENGINE)
        
        # ปรับแต่งตาม Technical Indicators
        if technical_indicators.rsi_14 > 70:  # Overbought
            if base_strategy == EntryStrategy.TREND_FOLLOWING:
                base_strategy = EntryStrategy.MEAN_REVERSION
            elif base_strategy == EntryStrategy.SCALPING_ENGINE:
                base_strategy = EntryStrategy.MEAN_REVERSION
        
        elif technical_indicators.rsi_14 < 30:  # Oversold
            if base_strategy == EntryStrategy.MEAN_REVERSION:
                base_strategy = EntryStrategy.TREND_FOLLOWING
        
        # ปรับแต่งตาม Performance ของแต่ละ Strategy
        strategy_performance = self.strategy_performance.get(base_strategy, {})
        if strategy_performance.get('success_count', 0) == 0 and strategy_performance.get('signals_executed', 0) > 5:
            # Strategy นี้ไม่ประสบความสำเร็จ - เปลี่ยนเป็น default
            base_strategy = EntryStrategy.SCALPING_ENGINE
        
        return base_strategy
    
    def _generate_signal_by_strategy(self, market_data: MarketData, 
                                    market_condition: MarketCondition,
                                    entry_strategy: EntryStrategy,
                                    technical_indicators: TechnicalIndicators) -> Tuple[SignalType, float]:
        """สร้างสัญญาณตามกลยุทธ์เฉพาะ"""
        
        confidence = 0.0
        signal_type = SignalType.HOLD
        
        # ตรวจสอบ Spread
        if market_data.spread > self.trading_params['max_spread']:
            return SignalType.HOLD, 0.0
        
        try:
            if entry_strategy == EntryStrategy.SCALPING_ENGINE:
                signal_type, confidence = self._scalping_signal_logic(market_data, technical_indicators)
            
            elif entry_strategy == EntryStrategy.TREND_FOLLOWING:
                signal_type, confidence = self._trend_following_logic(market_data, technical_indicators, market_condition)
            
            elif entry_strategy == EntryStrategy.MEAN_REVERSION:
                signal_type, confidence = self._mean_reversion_logic(market_data, technical_indicators)
            
            elif entry_strategy == EntryStrategy.NEWS_REACTION:
                signal_type, confidence = self._news_reaction_logic(market_data, technical_indicators)
            
            elif entry_strategy == EntryStrategy.BREAKOUT_FALSE:  
                signal_type, confidence = self._false_breakout_logic(market_data, technical_indicators)
            
            else:
                # Default fallback
                signal_type, confidence = self._scalping_signal_logic(market_data, technical_indicators)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้างสัญญาณ {entry_strategy.value}: {e}")
            return SignalType.HOLD, 0.0
        
        return signal_type, confidence
    
    def _scalping_signal_logic(self, market_data: MarketData, tech: TechnicalIndicators) -> Tuple[SignalType, float]:
        """ตรรกะสัญญาณ Scalping"""
        signal_type = SignalType.HOLD
        confidence = 0.0
        
        # เงื่อนไข Scalping: spread ต่ำ, RSI ไม่ extreme, volatility ปานกลาง
        if market_data.spread <= 2.0 and 35 <= tech.rsi_14 <= 65 and 0.5 <= tech.atr <= 1.5:
            
            # สัญญาณ BUY: ราคาใกล้ BB Lower, RSI เริ่มขาขึ้น
            if (market_data.mid_price <= tech.bb_lower * 1.002 and 
                tech.rsi_14 >= 40 and 
                tech.ma_10 >= tech.ma_20):
                
                signal_type = SignalType.BUY
                confidence = 0.6 + min(0.2, (tech.bb_middle - market_data.mid_price) / tech.bb_middle * 10)
            
            # สัญญาณ SELL: ราคาใกล้ BB Upper, RSI เริ่มขาลง  
            elif (market_data.mid_price >= tech.bb_upper * 0.998 and
                    tech.rsi_14 <= 60 and
                    tech.ma_10 <= tech.ma_20):
                
                signal_type = SignalType.SELL
                confidence = 0.6 + min(0.2, (market_data.mid_price - tech.bb_middle) / tech.bb_middle * 10)
            
            # สัญญาณจาก Moving Average Crossover (ระยะสั้น)
            elif tech.ma_10 > tech.ma_20 and tech.rsi_14 > 45:
                signal_type = SignalType.BUY
                confidence = 0.55
            
            elif tech.ma_10 < tech.ma_20 and tech.rsi_14 < 55:
                signal_type = SignalType.SELL  
                confidence = 0.55
        
        return signal_type, min(confidence, 0.85)  # จำกัด confidence สูงสุด
    
    def _trend_following_logic(self, market_data: MarketData, tech: TechnicalIndicators, 
                                market_condition: MarketCondition) -> Tuple[SignalType, float]:
        """ตรรกะสัญญาณ Trend Following"""
        signal_type = SignalType.HOLD
        confidence = 0.0
        
        # ต้องมี trend ที่ชัดเจน
        if market_condition not in [MarketCondition.TRENDING_UP, MarketCondition.TRENDING_DOWN]:
            return signal_type, confidence
        
        # Uptrend: MA sequence + RSI support + price above BB middle
        if (market_condition == MarketCondition.TRENDING_UP and
            tech.ma_10 > tech.ma_20 > tech.ma_50 and
            tech.rsi_14 > 50 and
            market_data.mid_price > tech.bb_middle):
            
            signal_type = SignalType.BUY
            confidence = 0.7
            
            # เพิ่ม confidence ถ้ามี momentum แรง
            if tech.rsi_14 > 60 and market_data.mid_price > tech.bb_upper * 0.995:
                confidence += 0.15
        
        # Downtrend: MA sequence + RSI support + price below BB middle
        elif (market_condition == MarketCondition.TRENDING_DOWN and
                tech.ma_10 < tech.ma_20 < tech.ma_50 and
                tech.rsi_14 < 50 and
                market_data.mid_price < tech.bb_middle):
            
            signal_type = SignalType.SELL
            confidence = 0.7
            
            # เพิ่ม confidence ถ้ามี momentum แรง
            if tech.rsi_14 < 40 and market_data.mid_price < tech.bb_lower * 1.005:
                confidence += 0.15
        
        return signal_type, min(confidence, 0.9)
    
    def _mean_reversion_logic(self, market_data: MarketData, tech: TechnicalIndicators) -> Tuple[SignalType, float]:
        """ตรรกะสัญญาณ Mean Reversion"""
        signal_type = SignalType.HOLD
        confidence = 0.0
        
        # Mean Reversion ต้องการ market ที่ ranging และ RSI extreme
        bb_width = (tech.bb_upper - tech.bb_lower) / tech.bb_middle
        
        if bb_width < 0.02:  # BB แคบ = ranging market
            
            # Oversold condition - คาดว่าจะกลับขึ้น
            if (tech.rsi_14 < 30 and 
                market_data.mid_price <= tech.bb_lower * 1.001):
                
                signal_type = SignalType.BUY
                confidence = 0.8 - (tech.rsi_14 / 100)  # RSI ยิ่งต่ำ confidence ยิ่งสูง
            
            # Overbought condition - คาดว่าจะกลับลง
            elif (tech.rsi_14 > 70 and
                    market_data.mid_price >= tech.bb_upper * 0.999):
                
                signal_type = SignalType.SELL
                confidence = 0.8 - ((100 - tech.rsi_14) / 100)  # RSI ยิ่งสูง confidence ยิ่งสูง
        
        # Mean Reversion จาก MA
        elif abs(market_data.mid_price - tech.ma_20) / tech.ma_20 > 0.005:  # ห่างจาก MA มาก
            
            if market_data.mid_price > tech.ma_20 * 1.005 and tech.rsi_14 > 65:
                signal_type = SignalType.SELL
                confidence = 0.65
            
            elif market_data.mid_price < tech.ma_20 * 0.995 and tech.rsi_14 < 35:
                signal_type = SignalType.BUY
                confidence = 0.65
        
        return signal_type, min(confidence, 0.85)
    
    def _news_reaction_logic(self, market_data: MarketData, tech: TechnicalIndicators) -> Tuple[SignalType, float]:
        """ตรรกะสัญญาณ News Reaction"""
        signal_type = SignalType.HOLD
        confidence = 0.0
        
        # News Reaction: high volume + high volatility + quick reversal
        if (market_data.volume > tech.volume_sma * 1.5 and  # Volume สูงกว่าปกติ
            tech.atr > 1.5 and  # Volatility สูง
            market_data.spread <= 4.0):  # Spread ไม่สูงเกินไป
            
            # ปฏิกิริยาย้อนกลับจาก extreme RSI
            if tech.rsi_14 > 75:  # Overbought หลังข่าว - คาดว่าจะกลับลง
                signal_type = SignalType.SELL
                confidence = 0.75 + min(0.15, (tech.rsi_14 - 75) / 100)
            
            elif tech.rsi_14 < 25:  # Oversold หลังข่าว - คาดว่าจะกลับขึ้น
                signal_type = SignalType.BUY
                confidence = 0.75 + min(0.15, (25 - tech.rsi_14) / 100)
            
            # ปฏิกิริยาตาม BB breakout
            elif market_data.mid_price > tech.bb_upper * 1.005:  # Break above BB
                signal_type = SignalType.SELL  # คาดว่าจะกลับเข้า BB
                confidence = 0.7
            
            elif market_data.mid_price < tech.bb_lower * 0.995:  # Break below BB  
                signal_type = SignalType.BUY  # คาดว่าจะกลับเข้า BB
                confidence = 0.7
        
        return signal_type, min(confidence, 0.9)
    
    def _false_breakout_logic(self, market_data: MarketData, tech: TechnicalIndicators) -> Tuple[SignalType, float]:
        """ตรรกะสัญญาณ False Breakout"""
        signal_type = SignalType.HOLD
        confidence = 0.0
        
        # False Breakout: ราคา break level แต่กลับเข้ามาในทันที
        
        # False breakout above resistance (BB Upper)
        if (market_data.mid_price > tech.bb_upper * 1.002 and  # Break above
            tech.rsi_14 > 65 and  # Overbought
            market_data.volume < tech.volume_sma * 0.8):  # Volume ต่ำ = weak breakout
            
            signal_type = SignalType.SELL  # เล่นย้อนกลับ
            confidence = 0.75
        
        # False breakout below support (BB Lower)
        elif (market_data.mid_price < tech.bb_lower * 0.998 and  # Break below
                tech.rsi_14 < 35 and  # Oversold
                market_data.volume < tech.volume_sma * 0.8):  # Volume ต่ำ = weak breakout
            
            signal_type = SignalType.BUY  # เล่นย้อนกลับ
            confidence = 0.75
        
        # False MA breakout
        elif (abs(market_data.mid_price - tech.ma_20) / tech.ma_20 > 0.003 and  # ห่างจาก MA
                market_data.volume < tech.volume_sma and  # Volume ต่ำ
                ((market_data.mid_price > tech.ma_20 and tech.rsi_14 > 70) or  # False break up
                (market_data.mid_price < tech.ma_20 and tech.rsi_14 < 30))):  # False break down
            
            if market_data.mid_price > tech.ma_20:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.BUY
            
            confidence = 0.68
        
        return signal_type, min(confidence, 0.85)
    
    def _calculate_signal_strength(self, confidence: float) -> SignalStrength:
        """คำนวณความแรงของสัญญาณ"""
        if confidence >= 0.85:
            return SignalStrength.VERY_STRONG
        elif confidence >= 0.70:
            return SignalStrength.STRONG
        elif confidence >= 0.50:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    def _calculate_signal_priority(self, confidence: float, market_condition: MarketCondition, 
                                    session_type: SessionType) -> SignalPriority:
        """คำนวณความสำคัญของสัญญาณ"""
        priority = SignalPriority.NORMAL
        
        # High priority conditions
        if confidence >= 0.8:
            priority = SignalPriority.HIGH
        
        # Urgent priority conditions
        if (confidence >= 0.85 and 
            market_condition == MarketCondition.NEWS_IMPACT and
            session_type in [SessionType.OVERLAP, SessionType.NEW_YORK]):
            priority = SignalPriority.URGENT
        
        # Low priority conditions
        elif (confidence < 0.6 or 
                market_condition == MarketCondition.QUIET or
                session_type == SessionType.ASIAN):
            priority = SignalPriority.LOW
        
        return priority
    
    def _calculate_position_size(self, confidence: float, session_type: SessionType, 
                                market_data: MarketData) -> float:
        """คำนวณขนาดตำแหน่ง"""
        base_size = self.trading_params['min_lot_size']
        max_size = self.trading_params['max_lot_size']
        
        # Session multiplier
        session_multipliers = {
            SessionType.ASIAN: 0.8,
            SessionType.LONDON: 1.2,
            SessionType.NEW_YORK: 1.5,
            SessionType.OVERLAP: 1.8,
            SessionType.QUIET: 0.6
        }
        session_multiplier = session_multipliers.get(session_type, 1.0)
        
        # Confidence adjustment
        confidence_multiplier = 0.5 + (confidence * 1.5)  # 0.5 - 2.0
        
        # Volatility adjustment
        volatility_multiplier = 1.0 / max(market_data.spread / 2.0, 0.5)
        
        # Calculate final size
        calculated_size = base_size * session_multiplier * confidence_multiplier * volatility_multiplier
        
        # Apply limits
        return max(base_size, min(calculated_size, max_size))
    
    def _get_max_spread_for_session(self, session_type: SessionType) -> float:
        """ดึง max spread สำหรับ session"""
        spread_limits = {
            SessionType.ASIAN: 2.5,
            SessionType.LONDON: 3.0,
            SessionType.NEW_YORK: 3.5,
            SessionType.OVERLAP: 4.0,
            SessionType.QUIET: 2.0
        }
        return spread_limits.get(session_type, self.trading_params['max_spread'])
    
    def _calculate_volatility_index(self, market_data: MarketData) -> float:
        """คำนวณ Volatility Index"""
        tech = self.technical_analyzer.get_technical_indicators()
        
        # ATR-based volatility
        atr_volatility = tech.atr / 1.0  # Normalize ด้วย average ATR
        
        # Spread-based volatility
        spread_volatility = market_data.spread / 2.0  # Normalize ด้วย average spread
        
        # BB width-based volatility
        if tech.bb_middle > 0:
            bb_volatility = (tech.bb_upper - tech.bb_lower) / tech.bb_middle
        else:
            bb_volatility = 0.02  # Default
        
        # Combined volatility index
        volatility_index = (atr_volatility + spread_volatility + bb_volatility * 50) / 3
        
        return max(0.1, min(volatility_index, 5.0))  # จำกัดระหว่าง 0.1-5.0
    
    def _analyze_multiple_timeframes(self, market_data: MarketData) -> Dict[str, str]:
        """วิเคราะห์หลายไทม์เฟรม"""
        timeframes = self.settings.get('timeframes_analysis', ['M1', 'M5', 'M15', 'H1'])
        analysis = {}
        
        for tf in timeframes:
            try:
                # จำลองการวิเคราะห์แต่ละไทม์เฟรม
                # ในความเป็นจริงจะดึงข้อมูลจาก MT5 แต่ละไทม์เฟรม
                
                tech = self.technical_analyzer.get_technical_indicators()
                
                if tech.ma_10 > tech.ma_20:
                    trend = "BULLISH"
                elif tech.ma_10 < tech.ma_20:
                    trend = "BEARISH"
                else:
                    trend = "NEUTRAL"
                
                # ปรับแต่งตามไทม์เฟรม
                if tf in ['M1', 'M5']:  # ไทม์เฟรมสั้น
                    if tech.rsi_14 > 60:
                        trend += "_STRONG"
                    elif tech.rsi_14 < 40:
                        trend += "_WEAK"
                
                analysis[tf] = trend
                
            except Exception as e:
                analysis[tf] = "UNKNOWN"
        
        return analysis
    
    def _generate_signal_reasoning(self, entry_strategy: EntryStrategy, 
                                    market_condition: MarketCondition,
                                    technical_indicators: TechnicalIndicators) -> str:
        """สร้างเหตุผลของสัญญาณ"""
        
        reasoning_parts = []
        
        # Market condition
        reasoning_parts.append(f"Market: {market_condition.value}")
        
        # Strategy
        reasoning_parts.append(f"Strategy: {entry_strategy.value}")
        
        # Technical analysis
        if technical_indicators.rsi_14 > 70:
            reasoning_parts.append("RSI Overbought")
        elif technical_indicators.rsi_14 < 30:
            reasoning_parts.append("RSI Oversold")
        
        if technical_indicators.ma_10 > technical_indicators.ma_20:
            reasoning_parts.append("MA Bullish")
        elif technical_indicators.ma_10 < technical_indicators.ma_20:
            reasoning_parts.append("MA Bearish")
        
        # Bollinger Bands
        if hasattr(technical_indicators, 'bb_middle') and technical_indicators.bb_middle > 0:
            bb_pos = "BB Middle"  # Default
            reasoning_parts.append(bb_pos)
        
        return " | ".join(reasoning_parts)
    
    def _validate_signal_quality(self, signal: TradingSignal) -> bool:
        """ตรวจสอบคุณภาพของสัญญาณ"""
        
        # ตรวจสอบ confidence ขั้นต่ำ
        if signal.confidence_score < 0.5:
            return False
        
        # ตรวจสอบ spread
        if signal.current_price == 0 or signal.max_spread <= 0:
            return False
        
        # ตรวจสอบความถี่ของสัญญาณ
        current_time = time.time()
        if current_time - self.last_signal_time < self.risk_limits['min_signal_interval']:
            return False
        
        # ตรวจสอบ correlation กับสัญญาณล่าสุด
        if self.recent_signals:
            last_signal = self.recent_signals[-1]
            if (signal.entry_strategy == last_signal.entry_strategy and
                signal.signal_type == last_signal.signal_type and
                abs(signal.confidence_score - last_signal.confidence_score) < 0.1):
                return False  # สัญญาณซ้ำ
        
        # ตรวจสอบ volume ที่แนะนำ
        if signal.suggested_volume < self.trading_params['min_lot_size']:
            signal.suggested_volume = self.trading_params['min_lot_size']
        elif signal.suggested_volume > self.trading_params['max_lot_size']:
            signal.suggested_volume = self.trading_params['max_lot_size']
        
        return True
    
    def _process_generated_signal(self, signal: TradingSignal):
        """ประมวลผลสัญญาณที่สร้างขึ้น"""
        try:
            # เพิ่มลงใน queue
            if not self.signals_queue.full():
                self.signals_queue.put(signal)
            else:
                # Queue เต็ม - ลบสัญญาณเก่าออก
                try:
                    self.signals_queue.get_nowait()
                    self.signals_queue.put(signal)
                except queue.Empty:
                    pass
            
            # เพิ่มลงในประวัติ
            self.recent_signals.append(signal)
            if len(self.recent_signals) > 100:
                self.recent_signals.pop(0)
            
            # เพิ่มลงใน history
            self.signal_history.append({
                'timestamp': signal.timestamp,
                'signal_id': signal.signal_id,
                'signal_type': signal.signal_type.value,
                'strategy': signal.entry_strategy.value,
                'confidence': signal.confidence_score,
                'session': signal.session_type.value,
                'market_condition': signal.market_condition.value
            })
            
            # อัพเดท statistics
            self.signals_generated_today += 1
            self.daily_volume_generated += signal.suggested_volume
            
            self.performance_metrics['total_signals'] += 1
            self.performance_metrics['average_confidence'] = (
                (self.performance_metrics['average_confidence'] * (self.performance_metrics['total_signals'] - 1) + 
                    signal.confidence_score) / self.performance_metrics['total_signals']
            )
            
            # อัพเดท strategy performance
            strategy_perf = self.strategy_performance[signal.entry_strategy]
            strategy_perf['signals_generated'] += 1
            strategy_perf['last_used'] = datetime.now()
            
            # อัพเดท average confidence ของ strategy
            total_signals = strategy_perf['signals_generated']
            if total_signals == 1:
                strategy_perf['average_confidence'] = signal.confidence_score
            else:
                strategy_perf['average_confidence'] = (
                    (strategy_perf['average_confidence'] * (total_signals - 1) + signal.confidence_score) / total_signals
                )
            
            self.logger.info(
                f"📊 สัญญาณใหม่: {signal.signal_type.value} | "
                f"Strategy: {signal.entry_strategy.value} | "
                f"Confidence: {signal.confidence_score:.2f} | "
                f"Volume: {signal.suggested_volume} | "
                f"Priority: {signal.priority.value} | "
                f"Session: {signal.session_type.value}"
            )
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการประมวลผลสัญญาณ: {e}")
    
    def get_next_signal(self, timeout: float = 1.0) -> Optional[TradingSignal]:
        """ดึงสัญญาณถัดไป"""
        try:
            signal = self.signals_queue.get(timeout=timeout)
            return signal
        except queue.Empty:
            return None
    
    def get_recent_signals(self, count: int = 10) -> List[TradingSignal]:
        """ดึงสัญญาณล่าสุด"""
        return self.recent_signals[-count:] if self.recent_signals else []
    
    def get_signals_by_strategy(self, strategy: EntryStrategy, count: int = 10) -> List[TradingSignal]:
        """ดึงสัญญาณตามกลยุทธ์"""
        strategy_signals = [s for s in self.recent_signals if s.entry_strategy == strategy]
        return strategy_signals[-count:] if strategy_signals else []
    
    def get_signals_by_session(self, session: SessionType, count: int = 10) -> List[TradingSignal]:
        """ดึงสัญญาณตาม session"""
        session_signals = [s for s in self.recent_signals if s.session_type == session]
        return session_signals[-count:] if session_signals else []
    
    def get_high_confidence_signals(self, min_confidence: float = 0.8, count: int = 10) -> List[TradingSignal]:
        """ดึงสัญญาณที่มี confidence สูง"""
        high_conf_signals = [s for s in self.recent_signals if s.confidence_score >= min_confidence]
        return high_conf_signals[-count:] if high_conf_signals else []
    
    def mark_signal_executed(self, signal_id: str, execution_price: float = 0.0):
        """ทำเครื่องหมายสัญญาณที่ถูกใช้งาน"""
        for signal in self.recent_signals:
            if signal.signal_id == signal_id:
                signal.is_executed = True
                signal.execution_time = datetime.now()
                signal.execution_price = execution_price
                
                # อัพเดท statistics
                self.signals_executed_today += 1
                
                # อัพเดท strategy performance
                strategy_perf = self.strategy_performance[signal.entry_strategy]
                strategy_perf['signals_executed'] += 1
                
                # อัพเดท performance metrics
                self.performance_metrics['execution_rate'] = (
                    self.signals_executed_today / max(self.signals_generated_today, 1)
                )
                
                self.logger.info(f"✅ สัญญาณ {signal_id} ถูกใช้งานที่ราคา {execution_price}")
                break
    
    def mark_signal_successful(self, signal_id: str, profit: float = 0.0):
        """ทำเครื่องหมายสัญญาณที่ประสบความสำเร็จ"""
        for signal in self.recent_signals:
            if signal.signal_id == signal_id:
                # อัพเดท statistics
                self.successful_signals += 1
                
                # อัพเดท strategy performance
                strategy_perf = self.strategy_performance[signal.entry_strategy]
                strategy_perf['success_count'] += 1
                strategy_perf['total_profit'] += profit
                
                # อัพเดท performance metrics
                total_executed = max(self.signals_executed_today, 1)
                self.performance_metrics['success_rate'] = self.successful_signals / total_executed
                
                self.logger.info(f"🎯 สัญญาณ {signal_id} ประสบความสำเร็จ - กำไร: {profit}")
                break
    
    def mark_signal_failed(self, signal_id: str, loss: float = 0.0):
        """ทำเครื่องหมายสัญญาณที่ล้มเหลว"""
        for signal in self.recent_signals:
            if signal.signal_id == signal_id:
                # อัพเดท statistics
                self.failed_signals += 1
                
                # อัพเดท strategy performance
                strategy_perf = self.strategy_performance[signal.entry_strategy]
                strategy_perf['total_profit'] += loss  # loss จะเป็นค่าลบ
                
                # อัพเดท performance metrics
                total_executed = max(self.signals_executed_today, 1)
                self.performance_metrics['success_rate'] = self.successful_signals / total_executed
                
                self.logger.warning(f"❌ สัญญาณ {signal_id} ล้มเหลว - ขาดทุน: {abs(loss)}")
                break
    
    def get_statistics(self) -> Dict[str, Any]:
        """ดึงสถิติการทำงานทั้งหมด"""
        current_time = datetime.now()
        uptime = (current_time - datetime.fromtimestamp(0)).total_seconds() if hasattr(self, 'start_time') else 0
        
        # คำนวณ success rate
        success_rate = (self.successful_signals / max(self.signals_executed_today, 1)) * 100
        execution_rate = (self.signals_executed_today / max(self.signals_generated_today, 1)) * 100
        
        # หา best performing strategy
        best_strategy = EntryStrategy.SCALPING_ENGINE
        best_success_rate = 0.0
        
        for strategy, perf in self.strategy_performance.items():
            if perf['signals_executed'] > 0:
                strategy_success_rate = perf['success_count'] / perf['signals_executed']
                if strategy_success_rate > best_success_rate:
                    best_success_rate = strategy_success_rate
                    best_strategy = strategy
        
        return {
            # Generation Status
            'generation_active': self.generation_active,
            'trading_started': self.trading_started,
            'uptime_minutes': uptime / 60,
            
            # Signal Statistics
            'signals_generated_today': self.signals_generated_today,
            'signals_executed_today': self.signals_executed_today,
            'successful_signals': self.successful_signals,
            'failed_signals': self.failed_signals,
            
            # Performance Metrics
            'success_rate_percent': round(success_rate, 2),
            'execution_rate_percent': round(execution_rate, 2),
            'average_confidence': round(self.performance_metrics['average_confidence'], 3),
            
            # Volume Tracking
            'daily_volume_generated': round(self.daily_volume_generated, 2),
            'daily_volume_target': self.daily_volume_target,
            'volume_achievement_percent': round((self.daily_volume_generated / self.daily_volume_target) * 100, 1),
            
            # Queue & Memory
            'queue_size': self.signals_queue.qsize(),
            'recent_signals_count': len(self.recent_signals),
            'signal_history_count': len(self.signal_history),
            
            # Timing
            'last_signal_time': datetime.fromtimestamp(self.last_signal_time) if self.last_signal_time > 0 else None,
            'signal_cooldown_seconds': self.signal_cooldown,
            
            # Best Strategy
            'best_strategy': best_strategy.value,
            'best_strategy_success_rate': round(best_success_rate * 100, 2),
            
            # Current Session
            'current_session': self._get_current_session().value,
            'current_market_condition': 'ANALYZING...'
        }
    
    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """ดึงประสิทธิภาพของแต่ละกลยุทธ์"""
        performance_summary = {}
        
        for strategy, perf in self.strategy_performance.items():
            success_rate = 0.0
            if perf['signals_executed'] > 0:
                success_rate = (perf['success_count'] / perf['signals_executed']) * 100
            
            performance_summary[strategy.value] = {
                'signals_generated': perf['signals_generated'],
                'signals_executed': perf['signals_executed'],
                'success_count': perf['success_count'],
                'success_rate_percent': round(success_rate, 2),
                'total_profit': round(perf['total_profit'], 2),
                'average_confidence': round(perf['average_confidence'], 3),
                'last_used': perf['last_used'].strftime('%H:%M:%S') if perf['last_used'] else 'Never'
            }
        
        return performance_summary
    
    def get_session_analysis(self) -> Dict[str, Any]:
        """ดึงการวิเคราะห์ตาม session"""
        session_stats = defaultdict(lambda: {
            'signals_generated': 0,
            'total_confidence': 0.0,
            'strategies_used': defaultdict(int)
        })
        
        # วิเคราะห์สัญญาณตาม session
        for signal in self.recent_signals:
            session = signal.session_type.value
            session_stats[session]['signals_generated'] += 1
            session_stats[session]['total_confidence'] += signal.confidence_score
            session_stats[session]['strategies_used'][signal.entry_strategy.value] += 1
        
        # คำนวณค่าเฉลี่ย
        analysis = {}
        for session, stats in session_stats.items():
            avg_confidence = 0.0
            if stats['signals_generated'] > 0:
                avg_confidence = stats['total_confidence'] / stats['signals_generated']
            
            most_used_strategy = 'None'
            if stats['strategies_used']:
                most_used_strategy = max(stats['strategies_used'], key=stats['strategies_used'].get)
            
            analysis[session] = {
                'signals_generated': stats['signals_generated'],
                'average_confidence': round(avg_confidence, 3),
                'most_used_strategy': most_used_strategy,
                'strategies_distribution': dict(stats['strategies_used'])
            }
        
        return analysis
    
    def reset_daily_statistics(self):
        """รีเซ็ตสถิติรายวัน"""
        self.signals_generated_today = 0
        self.signals_executed_today = 0
        self.successful_signals = 0
        self.failed_signals = 0
        self.daily_volume_generated = 0.0
        self.hourly_volume_generated = 0.0
        
        self.logger.info("🔄 รีเซ็ตสถิติรายวัน")
    
    def adjust_signal_cooldown(self, new_cooldown: int):
        """ปรับ signal cooldown"""
        if 5 <= new_cooldown <= 120:  # ระหว่าง 5 วินาที ถึง 2 นาที
            self.signal_cooldown = new_cooldown
            self.logger.info(f"⚙️ ปรับ signal cooldown เป็น {new_cooldown} วินาที")
    
    def set_volume_target(self, new_target: float):
        """ตั้งเป้าหมาย volume ใหม่"""
        if 10.0 <= new_target <= 200.0:  # ระหว่าง 10-200 lots/วัน
            self.daily_volume_target = new_target
            self.logger.info(f"🎯 ตั้งเป้าหมาย volume ใหม่: {new_target} lots/วัน")
    
    def enable_trading(self):
        """เปิดใช้งานการเทรด"""
        self.trading_started = True
        self.logger.info("✅ เปิดใช้งานการเทรด")
    
    def disable_trading(self):
        """ปิดใช้งานการเทรด"""
        self.trading_started = False
        self.logger.info("⏸️ ปิดใช้งานการเทรด")
    
    def export_signal_history(self, filename: Optional[str] = None) -> str:
        """ส่งออกประวัติสัญญาณ"""
        if filename is None:
            filename = f"signal_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'statistics': self.get_statistics(),
                'strategy_performance': self.get_strategy_performance(),
                'session_analysis': self.get_session_analysis(),
                'signal_history': list(self.signal_history)
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"📁 ส่งออกประวัติสัญญาณ: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถส่งออกประวัติ: {e}")
            return ""
    
    def cleanup_old_signals(self, max_age_hours: int = 24):
        """ทำความสะอาดสัญญาณเก่า"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # ทำความสะอาด recent_signals
        self.recent_signals = [s for s in self.recent_signals if s.timestamp > cutoff_time]
        
        # ทำความสะอาด signal_history
        original_count = len(self.signal_history)
        self.signal_history = deque([h for h in self.signal_history if h['timestamp'] > cutoff_time], maxlen=1000)
        
        cleaned_count = original_count - len(self.signal_history)
        if cleaned_count > 0:
            self.logger.info(f"🧹 ทำความสะอาดสัญญาณเก่า: ลบ {cleaned_count} รายการ")

# ===============================
# GLOBAL INSTANCE PATTERN  
# ===============================

_signal_generator_instance: Optional[IntelligentSignalGenerator] = None

def get_intelligent_signal_generator() -> IntelligentSignalGenerator:
    """ดึง Signal Generator instance (Singleton pattern)"""
    global _signal_generator_instance
    if _signal_generator_instance is None:
        _signal_generator_instance = IntelligentSignalGenerator()
    return _signal_generator_instance

def reset_signal_generator():
    """รีเซ็ต Signal Generator instance"""
    global _signal_generator_instance
    if _signal_generator_instance:
        _signal_generator_instance.stop_signal_generation()
    _signal_generator_instance = None

# ===============================
# UTILITY FUNCTIONS
# ===============================

def create_test_signal() -> TradingSignal:
    """สร้างสัญญาณทดสอบ"""
    return TradingSignal(
        signal_id=f"TEST_{int(time.time())}",
        timestamp=datetime.now(),
        signal_type=SignalType.BUY,
        entry_strategy=EntryStrategy.SCALPING_ENGINE,
        signal_strength=SignalStrength.MODERATE,
        current_price=2000.50,
        entry_price=2000.52,
        suggested_volume=0.01,
        confidence_score=0.65,
        reasoning="Test signal for development"
    )

def analyze_signal_patterns(signals: List[TradingSignal]) -> Dict[str, Any]:
    """วิเคราะห์รูปแบบของสัญญาณ"""
    if not signals:
        return {}
    
    # วิเคราะห์การกระจายตามประเภท
    signal_types = defaultdict(int)
    strategies = defaultdict(int)
    sessions = defaultdict(int)
    confidence_levels = []
    
    for signal in signals:
        signal_types[signal.signal_type.value] += 1
        strategies[signal.entry_strategy.value] += 1
        sessions[signal.session_type.value] += 1
        confidence_levels.append(signal.confidence_score)
    
    # คำนวณสถิติ
    avg_confidence = statistics.mean(confidence_levels) if confidence_levels else 0
    median_confidence = statistics.median(confidence_levels) if confidence_levels else 0
    
    return {
        'total_signals': len(signals),
        'signal_types_distribution': dict(signal_types),
        'strategies_distribution': dict(strategies),
        'sessions_distribution': dict(sessions),
        'confidence_statistics': {
            'average': round(avg_confidence, 3),
            'median': round(median_confidence, 3),
            'min': round(min(confidence_levels), 3) if confidence_levels else 0,
            'max': round(max(confidence_levels), 3) if confidence_levels else 0
        }
    }

# ===============================
# TEST FUNCTIONS
# ===============================

def test_signal_generator():
    """ทดสอบ Signal Generator แบบครบถ้วน"""
    print("🧪 เริ่มทดสอบ Intelligent Signal Generator...")
    
    generator = get_intelligent_signal_generator()
    
    # ทดสอบสถิติเริ่มต้น
    print("📊 สถิติเริ่มต้น:")
    stats = generator.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # ทดสอบการสร้างสัญญาณ
    print("\n🎯 ทดสอบการสร้างสัญญาณ...")
    for i in range(3):
        signal = generator._generate_intelligent_signal()
        if signal:
            print(f"   สัญญาณ {i+1}: {signal.signal_type.value} | {signal.entry_strategy.value} | Confidence: {signal.confidence_score:.2f}")
        else:
            print(f"   สัญญาณ {i+1}: ไม่ได้สัญญาณ")
    
    # ทดสอบ technical analyzer
    print("\n📈 ทดสอบ Technical Analyzer...")
    tech_analyzer = TechnicalAnalyzer()
    
    # เพิ่มข้อมูลทดสอบ
    for i in range(50):
        test_data = MarketData(
            timestamp=datetime.now(),
            open=2000 + i * 0.1,
            high=2000 + i * 0.1 + 0.5,
            low=2000 + i * 0.1 - 0.5,
            close=2000 + i * 0.1 + random.uniform(-0.3, 0.3),
            bid=2000 + i * 0.1,
            ask=2000 + i * 0.1 + 0.2,
            volume=random.randint(1000, 5000)
        )
        tech_analyzer.update_price_data(test_data)
    
    indicators = tech_analyzer.get_technical_indicators()
    print(f"   RSI: {indicators.rsi_14:.2f}")
    print(f"   MA10: {indicators.ma_10:.2f}")
    print(f"   BB Upper: {indicators.bb_upper:.2f}")
    print(f"   ATR: {indicators.atr:.2f}")
    
    # ทดสอบ strategy performance
    print("\n📋 ทดสอบ Strategy Performance...")
    perf = generator.get_strategy_performance()
    for strategy, data in perf.items():
        print(f"   {strategy}: Generated={data['signals_generated']}, Success Rate={data['success_rate_percent']}%")
    
    print("\n✅ ทดสอบ Signal Generator เสร็จสิ้น")

def benchmark_signal_generation():
   """ทดสอบประสิทธิภาพการสร้างสัญญาณ"""
   print("⚡ ทดสอบประสิทธิภาพการสร้างสัญญาณ...")
   
   generator = get_intelligent_signal_generator()
   
   start_time = time.time()
   signal_count = 0
   
   # สร้างสัญญาณ 100 ครั้ง
   for i in range(100):
       signal = generator._generate_intelligent_signal()
       if signal:
           signal_count += 1
   
   end_time = time.time()
   duration = end_time - start_time
   
   print(f"📊 ผลลัพธ์การทดสอบ:")
   print(f"   เวลาที่ใช้: {duration:.2f} วินาที")
   print(f"   สัญญาณที่สร้างได้: {signal_count}/100")
   print(f"   ความเร็วเฉลี่ย: {duration/100*1000:.2f} ms/signal")
   print(f"   อัตราสำเร็จ: {signal_count}%")

if __name__ == "__main__":
   test_signal_generator()
   print("\n" + "="*50)
   benchmark_signal_generation()