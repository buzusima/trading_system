#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STRATEGY SELECTOR - ระบบเลือกกลยุทธ์การเทรดอัจฉริยะ
=================================================
ระบบเลือกกลยุทธ์การเทรดแบบอัตโนมัติตามสภาวะตลาด
รองรับการปรับเปลี่ยนกลยุทธ์แบบเรียลไทม์

🎯 ฟีเจอร์หลัก:
- เลือกกลยุทธ์ตามสภาวะตลาด
- ปรับพารามิเตอร์แบบอัตโนมัติ
- รองรับหลายกลยุทธ์พร้อมกัน
- ประเมินประสิทธิภาพแบบเรียลไทม์
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import random

# Import market analyzer
try:
    from market_intelligence.market_analyzer import MarketAnalyzer

except ImportError:
    # Fallback definitions if import fails
    class TrendDirection(Enum):
        STRONG_UPTREND = "เทรนด์ขึ้นแรง"
        UPTREND = "เทรนด์ขึ้น"
        SIDEWAYS = "เทรนด์ข้าง"
        DOWNTREND = "เทรนด์ลง"
        STRONG_DOWNTREND = "เทรนด์ลงแรง"
        UNCERTAIN = "ไม่แน่นอน"
    
    class MarketCondition(Enum):
        TRENDING = "Trending"
        RANGING = "Ranging"
        VOLATILE = "Volatile"
        QUIET = "Quiet"
        NEWS_IMPACT = "News Impact"
        BREAKOUT = "Breakout"
    
    class TradingSession(Enum):
        ASIAN = "Asian"
        LONDON = "London"
        NEW_YORK = "New York"
        OVERLAP = "Overlap"
        CLOSED = "Market Closed"
    
    class VolatilityLevel(Enum):
        VERY_LOW = "ต่ำมาก"
        LOW = "ต่ำ"
        NORMAL = "ปกติ"
        HIGH = "สูง"
        VERY_HIGH = "สูงมาก"

class EntryStrategy(Enum):
    """กลยุทธ์การเข้าเทรด"""
    TREND_FOLLOWING = "Trend Following"
    MEAN_REVERSION = "Mean Reversion"
    BREAKOUT = "Breakout"
    SCALPING = "Scalping"
    NEWS_TRADING = "News Trading"
    GRID_TRADING = "Grid Trading"
    HEDGING = "Hedging"

class EntrySignal(Enum):
    """สัญญาณการเข้าเทรด"""
    STRONG_BUY = "BUY แรง"
    BUY = "BUY"
    WEAK_BUY = "BUY อ่อน"
    NEUTRAL = "เป็นกลาง"
    WEAK_SELL = "SELL อ่อน"
    SELL = "SELL"
    STRONG_SELL = "SELL แรง"
    NO_SIGNAL = "ไม่มีสัญญาณ"

class OrderType(Enum):
    """ประเภทคำสั่งซื้อขาย"""
    MARKET = "Market"
    LIMIT = "Limit"
    STOP = "Stop"
    STOP_LIMIT = "Stop Limit"

@dataclass
class StrategyParameters:
    """พารามิเตอร์กลยุทธ์"""
    strategy: EntryStrategy
    
    # การตั้งค่าทั่วไป
    lot_size: float = 0.1
    max_spread: float = 1.0
    min_volatility: float = 0.5
    max_volatility: float = 3.0
    
    # การตั้งค่าเวลา
    min_trade_interval: int = 60  # วินาที
    max_trades_per_hour: int = 10
    preferred_sessions: List[TradingSession] = field(default_factory=list)
    
    # การตั้งค่าเทคนิค
    rsi_oversold: float = 30
    rsi_overbought: float = 70
    adx_threshold: float = 25
    atr_multiplier: float = 2.0
    
    # การจัดการความเสี่ยง
    max_drawdown: float = 5.0
    profit_target: float = 2.0
    risk_reward_ratio: float = 1.5

@dataclass 
class EntrySignalData:
    """ข้อมูลสัญญาณเข้าเทรด"""
    signal: EntrySignal = EntrySignal.NO_SIGNAL
    strategy: EntryStrategy = EntryStrategy.TREND_FOLLOWING
    confidence: float = 0.0
    entry_price: float = 0.0
    suggested_lot: float = 0.1
    order_type: OrderType = OrderType.MARKET
    
    # เหตุผลการตัดสินใจ
    reasoning: str = ""
    technical_score: float = 0.0
    market_score: float = 0.0
    
    # การจัดการความเสี่ยง
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward: float = 0.0
    
    # เวลา
    timestamp: datetime = field(default_factory=datetime.now)
    valid_until: datetime = field(default_factory=datetime.now)

class StrategySelector:
    """ระบบเลือกกลยุทธ์หลัก"""
    
    def __init__(self, symbol: str = "XAUUSD.v"):
        self.symbol = symbol
        self.current_strategy: Optional[EntryStrategy] = None
        self.strategy_params: Dict[EntryStrategy, StrategyParameters] = {}
        self.performance_history: Dict[EntryStrategy, List[float]] = {}
        
        # สถิติ
        self.total_signals = 0
        self.successful_signals = 0
        self.last_signal_time: Optional[datetime] = None
        
        # เริ่มต้นกลยุทธ์
        self._initialize_strategies()
        
        print(f"🎯 เริ่มต้น Strategy Selector สำหรับ {symbol}")
    
    def _initialize_strategies(self):
        """เริ่มต้นกลยุทธ์ทั้งหมด"""
        
        # Trend Following Strategy
        self.strategy_params[EntryStrategy.TREND_FOLLOWING] = StrategyParameters(
            strategy=EntryStrategy.TREND_FOLLOWING,
            lot_size=0.1,
            adx_threshold=25,
            preferred_sessions=[TradingSession.LONDON, TradingSession.NEW_YORK],
            max_trades_per_hour=5
        )
        
        # Mean Reversion Strategy
        self.strategy_params[EntryStrategy.MEAN_REVERSION] = StrategyParameters(
            strategy=EntryStrategy.MEAN_REVERSION,
            lot_size=0.05,
            rsi_oversold=25,
            rsi_overbought=75,
            preferred_sessions=[TradingSession.ASIAN],
            max_trades_per_hour=8
        )
        
        # Breakout Strategy
        self.strategy_params[EntryStrategy.BREAKOUT] = StrategyParameters(
            strategy=EntryStrategy.BREAKOUT,
            lot_size=0.15,
            min_volatility=1.0,
            preferred_sessions=[TradingSession.LONDON, TradingSession.OVERLAP],
            max_trades_per_hour=3
        )
        
        # Scalping Strategy
        self.strategy_params[EntryStrategy.SCALPING] = StrategyParameters(
            strategy=EntryStrategy.SCALPING,
            lot_size=0.2,
            max_spread=0.5,
            min_trade_interval=30,
            max_trades_per_hour=20,
            preferred_sessions=[TradingSession.OVERLAP]
        )
        
        # Grid Trading Strategy
        self.strategy_params[EntryStrategy.GRID_TRADING] = StrategyParameters(
            strategy=EntryStrategy.GRID_TRADING,
            lot_size=0.05,
            min_volatility=0.3,
            max_volatility=2.0,
            max_trades_per_hour=15
        )
        
        # เริ่มต้น performance history
        for strategy in EntryStrategy:
            self.performance_history[strategy] = []
    
    def select_optimal_strategy(self, market_analysis: Any) -> EntryStrategy:
        """เลือกกลยุทธ์ที่เหมาะสมที่สุด"""
        try:
            strategy_scores = {}
            
            # คำนวณคะแนนสำหรับแต่ละกลยุทธ์
            for strategy in EntryStrategy:
                strategy_scores[strategy] = self._calculate_strategy_score(strategy, market_analysis)
            
            # เลือกกลยุทธ์ที่มีคะแนนสูงสุด
            best_strategy = max(strategy_scores, key=strategy_scores.get)
            best_score = strategy_scores[best_strategy]
            
            # ตรวจสอบว่าคะแนนดีพอหรือไม่
            if best_score > 60:
                self.current_strategy = best_strategy
                print(f"🎯 เลือกกลยุทธ์: {best_strategy.value} (คะแนน: {best_score:.1f})")
                return best_strategy
            else:
                print(f"⚠️ ไม่มีกลยุทธ์ที่เหมาะสม (คะแนนสูงสุด: {best_score:.1f})")
                return EntryStrategy.TREND_FOLLOWING  # default
                
        except Exception as e:
            print(f"❌ ข้อผิดพลาดในการเลือกกลยุทธ์: {e}")
            return EntryStrategy.TREND_FOLLOWING
    
    def _calculate_strategy_score(self, strategy: EntryStrategy, market_analysis: Any) -> float:
        """คำนวณคะแนนความเหมาะสมของกลยุทธ์"""
        score = 50.0  # คะแนนพื้นฐาน
        
        try:
            # ได้คะแนนจาก Market Condition
            if hasattr(market_analysis, 'market_condition'):
                condition = market_analysis.market_condition
                
                if strategy == EntryStrategy.TREND_FOLLOWING:
                    if condition == MarketCondition.TRENDING:
                        score += 30
                    elif condition == MarketCondition.BREAKOUT:
                        score += 20
                    elif condition == MarketCondition.RANGING:
                        score -= 20
                
                elif strategy == EntryStrategy.MEAN_REVERSION:
                    if condition == MarketCondition.RANGING:
                        score += 30
                    elif condition == MarketCondition.QUIET:
                        score += 20
                    elif condition == MarketCondition.TRENDING:
                        score -= 20
                
                elif strategy == EntryStrategy.BREAKOUT:
                    if condition == MarketCondition.BREAKOUT:
                        score += 35
                    elif condition == MarketCondition.VOLATILE:
                        score += 25
                    elif condition == MarketCondition.QUIET:
                        score -= 25
                
                elif strategy == EntryStrategy.SCALPING:
                    if condition == MarketCondition.VOLATILE:
                        score += 25
                    elif condition == MarketCondition.RANGING:
                        score += 15
                    elif condition == MarketCondition.QUIET:
                        score -= 30
            
            # ได้คะแนนจาก Trading Session
            if hasattr(market_analysis, 'trading_session'):
                session = market_analysis.trading_session
                params = self.strategy_params.get(strategy)
                
                if params and session in params.preferred_sessions:
                    score += 15
                elif session == TradingSession.CLOSED:
                    score -= 40
            
            # ได้คะแนนจาก Volatility
            if hasattr(market_analysis, 'volatility_level'):
                volatility = market_analysis.volatility_level
                
                if strategy == EntryStrategy.SCALPING:
                    if volatility in [VolatilityLevel.HIGH, VolatilityLevel.VERY_HIGH]:
                        score += 20
                    elif volatility == VolatilityLevel.VERY_LOW:
                        score -= 25
                
                elif strategy == EntryStrategy.GRID_TRADING:
                    if volatility in [VolatilityLevel.LOW, VolatilityLevel.NORMAL]:
                        score += 20
                    elif volatility == VolatilityLevel.VERY_HIGH:
                        score -= 20
            
            # ได้คะแนนจาก Trend Strength
            if hasattr(market_analysis, 'trend_strength'):
                trend_strength = market_analysis.trend_strength
                
                if strategy == EntryStrategy.TREND_FOLLOWING:
                    if trend_strength > 70:
                        score += 25
                    elif trend_strength < 30:
                        score -= 20
                
                elif strategy == EntryStrategy.MEAN_REVERSION:
                    if trend_strength < 30:
                        score += 20
                    elif trend_strength > 70:
                        score -= 25
            
            # ได้คะแนนจาก Performance History
            if strategy in self.performance_history:
                recent_performance = self.performance_history[strategy][-10:]  # 10 ครั้งล่าสุด
                if recent_performance:
                    avg_performance = sum(recent_performance) / len(recent_performance)
                    score += (avg_performance - 50) * 0.3  # ปรับคะแนนตาม performance
            
            return max(0, min(100, score))  # จำกัดคะแนนระหว่าง 0-100
            
        except Exception as e:
            print(f"⚠️ ข้อผิดพลาดในการคำนวณคะแนน {strategy}: {e}")
            return 50.0
    
    def generate_entry_signal(self, market_analysis: Any) -> EntrySignalData:
        """สร้างสัญญาณเข้าเทรด"""
        signal_data = EntrySignalData()
        
        try:
            # เลือกกลยุทธ์ที่เหมาะสม
            strategy = self.select_optimal_strategy(market_analysis)
            signal_data.strategy = strategy
            
            # สร้างสัญญาณตามกลยุทธ์
            if strategy == EntryStrategy.TREND_FOLLOWING:
                signal_data = self._generate_trend_following_signal(market_analysis, signal_data)
            elif strategy == EntryStrategy.MEAN_REVERSION:
                signal_data = self._generate_mean_reversion_signal(market_analysis, signal_data)
            elif strategy == EntryStrategy.BREAKOUT:
                signal_data = self._generate_breakout_signal(market_analysis, signal_data)
            elif strategy == EntryStrategy.SCALPING:
                signal_data = self._generate_scalping_signal(market_analysis, signal_data)
            elif strategy == EntryStrategy.GRID_TRADING:
                signal_data = self._generate_grid_signal(market_analysis, signal_data)
            
            # บันทึกสถิติ
            self.total_signals += 1
            self.last_signal_time = datetime.now()
            
            # แสดงผล
            if signal_data.signal != EntrySignal.NO_SIGNAL:
                print(f"📡 สัญญาณ: {signal_data.signal.value} | "
                        f"กลยุทธ์: {signal_data.strategy.value} | "
                        f"ความมั่นใจ: {signal_data.confidence:.1f}%")
                print(f"💡 เหตุผล: {signal_data.reasoning}")
            
            return signal_data
            
        except Exception as e:
            print(f"❌ ข้อผิดพลาดในการสร้างสัญญาณ: {e}")
            signal_data.signal = EntrySignal.NO_SIGNAL
            return signal_data
    
    def _generate_trend_following_signal(self, market_analysis: Any, signal_data: EntrySignalData) -> EntrySignalData:
        """สร้างสัญญาณ Trend Following"""
        try:
            if not hasattr(market_analysis, 'trend_direction'):
                return signal_data
            
            trend = market_analysis.trend_direction
            strength = getattr(market_analysis, 'trend_strength', 0)
            
            if trend == TrendDirection.STRONG_UPTREND and strength > 70:
                signal_data.signal = EntrySignal.STRONG_BUY
                signal_data.confidence = strength
                signal_data.reasoning = f"เทรนด์ขึ้นแรง ความแข็งแกร่ง {strength:.1f}%"
            elif trend == TrendDirection.UPTREND and strength > 50:
                signal_data.signal = EntrySignal.BUY
                signal_data.confidence = strength * 0.8
                signal_data.reasoning = f"เทรนด์ขึ้น ความแข็งแกร่ง {strength:.1f}%"
            elif trend == TrendDirection.STRONG_DOWNTREND and strength > 70:
                signal_data.signal = EntrySignal.STRONG_SELL
                signal_data.confidence = strength
                signal_data.reasoning = f"เทรนด์ลงแรง ความแข็งแกร่ง {strength:.1f}%"
            elif trend == TrendDirection.DOWNTREND and strength > 50:
                signal_data.signal = EntrySignal.SELL
                signal_data.confidence = strength * 0.8
                signal_data.reasoning = f"เทรนด์ลง ความแข็งแกร่ง {strength:.1f}%"
            else:
                signal_data.signal = EntrySignal.NO_SIGNAL
                signal_data.reasoning = "เทรนด์ไม่ชัดเจน"
            
            return signal_data
            
        except Exception as e:
            print(f"⚠️ ข้อผิดพลาดใน trend following signal: {e}")
            return signal_data
    
    def _generate_mean_reversion_signal(self, market_analysis: Any, signal_data: EntrySignalData) -> EntrySignalData:
        """สร้างสัญญาณ Mean Reversion"""
        try:
            # ใช้ข้อมูล momentum เป็นตัวแทน RSI
            momentum = getattr(market_analysis, 'momentum_score', 50)
            
            if momentum < 20:  # Oversold
                signal_data.signal = EntrySignal.BUY
                signal_data.confidence = (20 - momentum) * 4  # แปลงเป็น 0-80
                signal_data.reasoning = f"ตลาดขายเกิน Momentum: {momentum:.1f}"
            elif momentum > 80:  # Overbought
                signal_data.signal = EntrySignal.SELL
                signal_data.confidence = (momentum - 80) * 4
                signal_data.reasoning = f"ตลาดซื้อเกิน Momentum: {momentum:.1f}"
            else:
                signal_data.signal = EntrySignal.NO_SIGNAL
                signal_data.reasoning = "ตลาดในช่วงปกติ"
            
            return signal_data
            
        except Exception as e:
            print(f"⚠️ ข้อผิดพลาดใน mean reversion signal: {e}")
            return signal_data
    
    def _generate_breakout_signal(self, market_analysis: Any, signal_data: EntrySignalData) -> EntrySignalData:
        """สร้างสัญญาณ Breakout"""
        try:
            volatility = getattr(market_analysis, 'volatility_score', 50)
            current_price = getattr(market_analysis, 'current_price', 0)
            resistance = getattr(market_analysis, 'resistance_level', 0)
            support = getattr(market_analysis, 'support_level', 0)
            
            if volatility > 70 and current_price > 0:
                if resistance > 0 and current_price > resistance * 1.001:  # Breakout above resistance
                    signal_data.signal = EntrySignal.BUY
                    signal_data.confidence = volatility
                    signal_data.reasoning = f"Breakout เหนือ Resistance {resistance:.2f}"
                elif support > 0 and current_price < support * 0.999:  # Breakdown below support
                    signal_data.signal = EntrySignal.SELL
                    signal_data.confidence = volatility
                    signal_data.reasoning = f"Breakdown ต่ำกว่า Support {support:.2f}"
                else:
                    signal_data.signal = EntrySignal.NO_SIGNAL
                    signal_data.reasoning = "รอ Breakout ที่ชัดเจน"
            else:
                signal_data.signal = EntrySignal.NO_SIGNAL
                signal_data.reasoning = "ความผันผวนต่ำเกินไป"
            
            return signal_data
            
        except Exception as e:
            print(f"⚠️ ข้อผิดพลาดใน breakout signal: {e}")
            return signal_data
    
    def _generate_scalping_signal(self, market_analysis: Any, signal_data: EntrySignalData) -> EntrySignalData:
        """สร้างสัญญาณ Scalping"""
        try:
            # Scalping ต้องการสัญญาณเร็วและถี่
            trend = getattr(market_analysis, 'trend_direction', TrendDirection.SIDEWAYS)
            volatility = getattr(market_analysis, 'volatility_score', 50)
            
            if volatility > 40:  # ต้องมีความผันผวนพอ
                # สุ่มสัญญาณเพื่อจำลอง high-frequency trading
                random_signal = random.choice([EntrySignal.BUY, EntrySignal.SELL, EntrySignal.NO_SIGNAL])
                
                if random_signal != EntrySignal.NO_SIGNAL:
                    signal_data.signal = random_signal
                    signal_data.confidence = volatility * 0.8
                    signal_data.reasoning = f"Scalping โอกาส ความผันผวน: {volatility:.1f}"
                else:
                    signal_data.signal = EntrySignal.NO_SIGNAL
                    signal_data.reasoning = "รอโอกาส Scalping"
            else:
                signal_data.signal = EntrySignal.NO_SIGNAL
                signal_data.reasoning = "ความผันผวนต่ำเกินไปสำหรับ Scalping"
            
            return signal_data
            
        except Exception as e:
            print(f"⚠️ ข้อผิดพลาดใน scalping signal: {e}")
            return signal_data
    
    def _generate_grid_signal(self, market_analysis: Any, signal_data: EntrySignalData) -> EntrySignalData:
        """สร้างสัญญาณ Grid Trading"""
        try:
            # Grid Trading เหมาะกับตลาดที่ไม่มีเทรนด์ชัด
            trend_strength = getattr(market_analysis, 'trend_strength', 50)
            
            if trend_strength < 40:  # เทรนด์อ่อน เหมาะกับ Grid
                # สลับ BUY/SELL สำหรับ Grid
                signal_choice = random.choice([EntrySignal.BUY, EntrySignal.SELL])
                signal_data.signal = signal_choice
                signal_data.confidence = 60
                signal_data.reasoning = f"Grid Trading - เทรนด์อ่อน {trend_strength:.1f}%"
            else:
                signal_data.signal = EntrySignal.NO_SIGNAL
                signal_data.reasoning = "เทรนด์แรงเกินไปสำหรับ Grid"
            
            return signal_data
            
        except Exception as e:
            print(f"⚠️ ข้อผิดพลาดใน grid signal: {e}")
            return signal_data
    
    def update_strategy_performance(self, strategy: EntryStrategy, performance_score: float):
        """อัพเดทประสิทธิภาพกลยุทธ์"""
        try:
            if strategy not in self.performance_history:
                self.performance_history[strategy] = []
            
            self.performance_history[strategy].append(performance_score)
            
            # เก็บข้อมูลแค่ 50 ครั้งล่าสุด
            if len(self.performance_history[strategy]) > 50:
                self.performance_history[strategy].pop(0)
            
            print(f"📊 อัพเดทประสิทธิภาพ {strategy.value}: {performance_score:.1f}")
            
        except Exception as e:
            print(f"⚠️ ข้อผิดพลาดในการอัพเดทประสิทธิภาพ: {e}")
    
    def get_strategy_statistics(self) -> Dict[str, Any]:
        """ดึงสถิติกลยุทธ์"""
        stats = {
            'current_strategy': self.current_strategy.value if self.current_strategy else "ไม่มี",
            'total_signals': self.total_signals,
            'success_rate': (self.successful_signals / max(self.total_signals, 1)) * 100,
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None,
            'strategy_performance': {}
        }
        
        # สถิติแต่ละกลยุทธ์
        for strategy, performance_list in self.performance_history.items():
            if performance_list:
                stats['strategy_performance'][strategy.value] = {
                    'average_score': sum(performance_list) / len(performance_list),
                    'total_uses': len(performance_list),
                    'recent_score': performance_list[-1] if performance_list else 0
                }
        
        return stats

def test_strategy_selector():
    """ทดสอบ Strategy Selector"""
    print("🧪 ทดสอบ Strategy Selector...")
    
    try:
        # สร้าง selector
        selector = StrategySelector("XAUUSD")
        
        # จำลองข้อมูล market analysis
        class MockMarketAnalysis:
            def __init__(self):
                self.trend_direction = TrendDirection.UPTREND
                self.market_condition = MarketCondition.TRENDING
                self.trading_session = TradingSession.LONDON
                self.volatility_level = VolatilityLevel.NORMAL
                self.trend_strength = 65
                self.volatility_score = 55
                self.momentum_score = 30
                self.current_price = 2000.0
                self.resistance_level = 2010.0
                self.support_level = 1990.0
        
        mock_analysis = MockMarketAnalysis()
        
        # ทดสอบการเลือกกลยุทธ์
        print("📊 ทดสอบการเลือกกลยุทธ์...")
        strategy = selector.select_optimal_strategy(mock_analysis)
        print(f"✅ กลยุทธ์ที่เลือก: {strategy.value}")
        
        # ทดสอบการสร้างสัญญาณ
        print("\n📡 ทดสอบการสร้างสัญญาณ...")
        signal = selector.generate_entry_signal(mock_analysis)
        
        print(f"🎯 ผลลัพธ์:")
        print(f"   สัญญาณ: {signal.signal.value}")
        print(f"   กลยุทธ์: {signal.strategy.value}")
        print(f"   ความมั่นใจ: {signal.confidence:.1f}%")
        print(f"   เหตุผล: {signal.reasoning}")
        
        # ทดสอบการอัพเดทประสิทธิภาพ
        print("\n📈 ทดสอบการอัพเดทประสิทธิภาพ...")
        selector.update_strategy_performance(strategy, 75.0)
        
        # แสดงสถิติ
        print("\n📊 สถิติกลยุทธ์:")
        stats = selector.get_strategy_statistics()
        print(f"   กลยุทธ์ปัจจุบัน: {stats['current_strategy']}")
        print(f"   สัญญาณทั้งหมด: {stats['total_signals']}")
        print(f"   อัตราสำเร็จ: {stats['success_rate']:.1f}%")
        
        print("✅ ทดสอบ Strategy Selector เสร็จสิ้น")
        
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการทดสอบ: {e}")

if __name__ == "__main__":
   test_strategy_selector()