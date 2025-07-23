# adaptive_entries/entry_engines/trend_following.py - Trend Following Entry Logic

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class TrendStrength(Enum):
    """📈 ความแรงของเทรนด์"""
    WEAK = "weak"           # ADX 20-25
    MODERATE = "moderate"   # ADX 25-40
    STRONG = "strong"       # ADX 40+
    EXTREME = "extreme"     # ADX 60+

class TrendDirection(Enum):
    """🎯 ทิศทางของเทรนด์"""
    BULLISH = "bullish"     # ขาขึ้น
    BEARISH = "bearish"     # ขาลง
    SIDEWAYS = "sideways"   # ไซด์เวย์

@dataclass
class TrendAnalysis:
    """📊 ผลการวิเคราะห์เทรนด์"""
    direction: TrendDirection
    strength: TrendStrength
    adx_value: float
    ma_trend: str
    momentum_score: float
    confidence: float
    entry_signal: bool
    entry_type: str  # "BUY" or "SELL"
    entry_price: float
    stop_distance: float
    target_distance: float
    risk_reward: float

@dataclass
class TrendEntry:
    """🎯 สัญญาณ Entry จากเทรนด์"""
    timestamp: datetime
    signal_type: str        # "TREND_BUY" or "TREND_SELL"
    entry_price: float
    confidence: float
    trend_strength: TrendStrength
    ma_alignment: bool
    momentum_confirmation: bool
    volume_confirmation: bool
    session_multiplier: float
    lot_size: float
    reasoning: str

class TrendFollowingEngine:
    """
    🚀 Trend Following Entry Engine - Advanced Trend Detection & Entry Logic
    
    เหมาะสำหรับ:
    - London Session (15:00-00:00 GMT+7) - ความผันผวนสูง
    - NY Session (20:30-05:30 GMT+7) - ปริมาณการเทรดสูง
    - Trending Markets (ADX > 25)
    
    กลยุทธ์:
    - ตาม trend ที่แรง ไม่ต่อต้าน
    - ใช้ Moving Average alignment
    - ยืนยันด้วย momentum indicators
    - Recovery ด้วย Grid System (เพิ่มในทิศทางเดียวกับ trend)
    """
    
    def __init__(self, config: Dict):
        print("🚀 Initializing Trend Following Engine...")
        
        self.config = config
        
        # Trend detection parameters
        self.adx_period = config.get('adx_period', 14)
        self.ma_fast = config.get('ma_fast', 20)
        self.ma_slow = config.get('ma_slow', 50)
        self.ma_filter = config.get('ma_filter', 100)
        
        # Entry parameters
        self.min_adx = config.get('min_adx', 25.0)      # ความแรงขั้นต่ำ
        self.max_adx = config.get('max_adx', 80.0)      # ไม่เข้า overbought
        self.min_confidence = config.get('min_confidence', 0.7)
        self.pullback_threshold = config.get('pullback_threshold', 0.3)
        
        # Session multipliers
        self.session_multipliers = {
            'london': config.get('london_multiplier', 1.5),
            'ny': config.get('ny_multiplier', 1.8),
            'overlap': config.get('overlap_multiplier', 2.0),
            'asian': config.get('asian_multiplier', 0.8)
        }
        
        # Risk parameters
        self.base_lot = config.get('base_lot', 0.01)
        self.max_lot = config.get('max_lot', 0.5)
        self.risk_per_trade = config.get('risk_per_trade', 1.0)  # %
        
        # Cache
        self.last_analysis = None
        self.last_update = None
        self.trend_history = []
        
        print("✅ Trend Following Engine initialized")
        print(f"   - ADX Period: {self.adx_period}")
        print(f"   - MA Setup: {self.ma_fast}/{self.ma_slow}/{self.ma_filter}")
        print(f"   - Min ADX: {self.min_adx}")
        print(f"   - Min Confidence: {self.min_confidence}")
    
    def analyze_trend(self, market_data: pd.DataFrame) -> TrendAnalysis:
        """
        🔍 วิเคราะห์เทรนด์จากข้อมูลตลาด
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            TrendAnalysis object with complete trend information
        """
        try:
            if len(market_data) < max(self.adx_period, self.ma_filter) + 10:
                print("❌ Insufficient data for trend analysis")
                return self._create_neutral_analysis()
            
            # คำนวณ technical indicators
            df = market_data.copy()
            df = self._calculate_trend_indicators(df)
            
            # วิเคราะห์เทรนด์
            current_data = df.iloc[-1]
            
            # 1. ADX Analysis
            adx_value = current_data['adx']
            trend_strength = self._classify_trend_strength(adx_value)
            
            # 2. Moving Average Trend
            ma_trend = self._analyze_ma_trend(current_data)
            
            # 3. Momentum Analysis
            momentum_score = self._calculate_momentum_score(df)
            
            # 4. Overall Direction
            direction = self._determine_trend_direction(current_data, ma_trend)
            
            # 5. Confidence Calculation
            confidence = self._calculate_trend_confidence(
                current_data, trend_strength, ma_trend, momentum_score
            )
            
            # 6. Entry Signal Generation
            entry_signal, entry_type = self._generate_entry_signal(
                direction, trend_strength, confidence, current_data
            )
            
            # 7. Risk/Reward Calculation
            entry_price = current_data['close']
            stop_distance, target_distance = self._calculate_risk_reward(
                direction, current_data, trend_strength
            )
            
            risk_reward = target_distance / stop_distance if stop_distance > 0 else 0
            
            analysis = TrendAnalysis(
                direction=direction,
                strength=trend_strength,
                adx_value=adx_value,
                ma_trend=ma_trend,
                momentum_score=momentum_score,
                confidence=confidence,
                entry_signal=entry_signal,
                entry_type=entry_type,
                entry_price=entry_price,
                stop_distance=stop_distance,
                target_distance=target_distance,
                risk_reward=risk_reward
            )
            
            # Cache analysis
            self.last_analysis = analysis
            self.last_update = datetime.now()
            
            return analysis
            
        except Exception as e:
            print(f"❌ Trend analysis error: {e}")
            return self._create_neutral_analysis()
    
    def _calculate_trend_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """คำนวณ technical indicators สำหรับวิเคราะห์เทรนด์"""
        try:
            # Moving Averages
            df['ma_fast'] = df['close'].rolling(window=self.ma_fast).mean()
            df['ma_slow'] = df['close'].rolling(window=self.ma_slow).mean()
            df['ma_filter'] = df['close'].rolling(window=self.ma_filter).mean()
            
            # ADX Calculation (simplified)
            df['tr'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            
            df['plus_dm'] = np.where(
                (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
                np.maximum(df['high'] - df['high'].shift(1), 0),
                0
            )
            
            df['minus_dm'] = np.where(
                (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
                np.maximum(df['low'].shift(1) - df['low'], 0),
                0
            )
            
            # Smooth the values
            df['atr'] = df['tr'].rolling(window=self.adx_period).mean()
            df['plus_di'] = 100 * (df['plus_dm'].rolling(window=self.adx_period).mean() / df['atr'])
            df['minus_di'] = 100 * (df['minus_dm'].rolling(window=self.adx_period).mean() / df['atr'])
            
            df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
            df['adx'] = df['dx'].rolling(window=self.adx_period).mean()
            
            # Momentum indicators
            df['roc'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100
            df['momentum'] = df['close'] / df['close'].shift(10)
            
            # Price position relative to MAs
            df['price_vs_ma_fast'] = (df['close'] - df['ma_fast']) / df['ma_fast'] * 100
            df['price_vs_ma_slow'] = (df['close'] - df['ma_slow']) / df['ma_slow'] * 100
            
            return df
            
        except Exception as e:
            print(f"❌ Indicator calculation error: {e}")
            return df
    
    def _classify_trend_strength(self, adx_value: float) -> TrendStrength:
        """จำแนกความแรงของเทรนด์จาก ADX"""
        if adx_value >= 60:
            return TrendStrength.EXTREME
        elif adx_value >= 40:
            return TrendStrength.STRONG
        elif adx_value >= 25:
            return TrendStrength.MODERATE
        else:
            return TrendStrength.WEAK
    
    def _analyze_ma_trend(self, data: pd.Series) -> str:
        """วิเคราะห์เทรนด์จาก Moving Averages"""
        try:
            ma_fast = data['ma_fast']
            ma_slow = data['ma_slow']
            ma_filter = data['ma_filter']
            close = data['close']
            
            # MA Alignment Score
            alignment_score = 0
            
            # Price above all MAs = bullish
            if close > ma_fast > ma_slow > ma_filter:
                alignment_score = 3
                trend = "strong_bullish"
            elif close > ma_fast > ma_slow:
                alignment_score = 2
                trend = "moderate_bullish"
            elif close > ma_fast:
                alignment_score = 1
                trend = "weak_bullish"
            elif close < ma_fast < ma_slow < ma_filter:
                alignment_score = -3
                trend = "strong_bearish"
            elif close < ma_fast < ma_slow:
                alignment_score = -2
                trend = "moderate_bearish"
            elif close < ma_fast:
                alignment_score = -1
                trend = "weak_bearish"
            else:
                alignment_score = 0
                trend = "sideways"
            
            return trend
            
        except Exception as e:
            print(f"❌ MA trend analysis error: {e}")
            return "sideways"
    
    def _calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """คำนวณคะแนน momentum รวม"""
        try:
            current = df.iloc[-1]
            
            # ROC Score (Rate of Change)
            roc_score = np.tanh(current['roc'] / 5.0)  # Normalize to -1 to 1
            
            # Momentum Score
            momentum_raw = current['momentum'] - 1.0
            momentum_score = np.tanh(momentum_raw * 10)  # Normalize
            
            # Recent price action (last 5 candles)
            recent_change = (df['close'].iloc[-1] - df['close'].iloc[-6]) / df['close'].iloc[-6]
            recent_score = np.tanh(recent_change * 20)
            
            # Combined score
            total_score = (roc_score * 0.4 + momentum_score * 0.4 + recent_score * 0.2)
            
            return float(total_score)
            
        except Exception as e:
            print(f"❌ Momentum calculation error: {e}")
            return 0.0
    
    def _determine_trend_direction(self, data: pd.Series, ma_trend: str) -> TrendDirection:
        """กำหนดทิศทางเทรนด์โดยรวม"""
        try:
            adx = data['adx']
            plus_di = data['plus_di']
            minus_di = data['minus_di']
            
            # ADX direction
            if plus_di > minus_di and adx > self.min_adx:
                adx_direction = "bullish"
            elif minus_di > plus_di and adx > self.min_adx:
                adx_direction = "bearish"
            else:
                adx_direction = "sideways"
            
            # Combine with MA trend
            if "bullish" in ma_trend and adx_direction == "bullish":
                return TrendDirection.BULLISH
            elif "bearish" in ma_trend and adx_direction == "bearish":
                return TrendDirection.BEARISH
            else:
                return TrendDirection.SIDEWAYS
                
        except Exception as e:
            print(f"❌ Direction determination error: {e}")
            return TrendDirection.SIDEWAYS
    
    def _calculate_trend_confidence(self, data: pd.Series, strength: TrendStrength, 
                                  ma_trend: str, momentum: float) -> float:
        """คำนวณความเชื่อมั่นในเทรนด์"""
        try:
            confidence = 0.0
            
            # ADX strength contribution (0-0.4)
            adx_confidence = {
                TrendStrength.WEAK: 0.1,
                TrendStrength.MODERATE: 0.25,
                TrendStrength.STRONG: 0.35,
                TrendStrength.EXTREME: 0.4
            }
            confidence += adx_confidence[strength]
            
            # MA alignment contribution (0-0.3)
            ma_confidence = {
                "strong_bullish": 0.3, "strong_bearish": 0.3,
                "moderate_bullish": 0.2, "moderate_bearish": 0.2,
                "weak_bullish": 0.1, "weak_bearish": 0.1,
                "sideways": 0.0
            }
            confidence += ma_confidence.get(ma_trend, 0.0)
            
            # Momentum contribution (0-0.2)
            momentum_confidence = abs(momentum) * 0.2
            confidence += momentum_confidence
            
            # Price action contribution (0-0.1)
            price_vs_ma = abs(data['price_vs_ma_fast'])
            if price_vs_ma > 0.5:  # Price significantly away from MA
                confidence += 0.1
            
            return min(confidence, 1.0)
            
        except Exception as e:
            print(f"❌ Confidence calculation error: {e}")
            return 0.0
    
    def _generate_entry_signal(self, direction: TrendDirection, strength: TrendStrength,
                             confidence: float, data: pd.Series) -> Tuple[bool, str]:
        """สร้างสัญญาณ entry"""
        try:
            # ตรวจสอบเงื่อนไขพื้นฐาน
            if direction == TrendDirection.SIDEWAYS:
                return False, ""
            
            if confidence < self.min_confidence:
                return False, ""
            
            if data['adx'] < self.min_adx or data['adx'] > self.max_adx:
                return False, ""
            
            # ตรวจสอบ pullback opportunity
            if direction == TrendDirection.BULLISH:
                # ราคาอยู่ใกล้ MA แต่ไม่ต่ำเกินไป
                pullback = data['price_vs_ma_fast']
                if -self.pullback_threshold <= pullback <= 0.5:
                    return True, "BUY"
            
            elif direction == TrendDirection.BEARISH:
                # ราคาอยู่ใกล้ MA แต่ไม่สูงเกินไป
                pullback = data['price_vs_ma_fast']
                if -0.5 <= pullback <= self.pullback_threshold:
                    return True, "SELL"
            
            return False, ""
            
        except Exception as e:
            print(f"❌ Entry signal error: {e}")
            return False, ""
    
    def _calculate_risk_reward(self, direction: TrendDirection, data: pd.Series,
                             strength: TrendStrength) -> Tuple[float, float]:
        """คำนวณ Stop Loss และ Take Profit distance"""
        try:
            atr = data['atr']
            
            # Stop Loss distance based on ATR and trend strength
            stop_multiplier = {
                TrendStrength.WEAK: 1.5,
                TrendStrength.MODERATE: 2.0,
                TrendStrength.STRONG: 2.5,
                TrendStrength.EXTREME: 3.0
            }
            
            stop_distance = atr * stop_multiplier[strength]
            
            # Take Profit distance (aim for 2:1 minimum)
            target_distance = stop_distance * 2.5
            
            return float(stop_distance), float(target_distance)
            
        except Exception as e:
            print(f"❌ Risk/reward calculation error: {e}")
            return 50.0, 100.0  # Default values in pips
    
    def generate_entry_signal(self, market_data: pd.DataFrame, 
                            current_session: str = 'london') -> Optional[TrendEntry]:
        """
        🎯 สร้างสัญญาณ Entry สำหรับ Trend Following
        
        Args:
            market_data: ข้อมูลตลาดล่าสุด
            current_session: เซสชั่นปัจจุบัน
            
        Returns:
            TrendEntry object หรือ None
        """
        try:
            # วิเคราะห์เทรนด์
            analysis = self.analyze_trend(market_data)
            
            if not analysis.entry_signal:
                return None
            
            # คำนวณ lot size ตาม session และ confidence
            session_multiplier = self.session_multipliers.get(current_session, 1.0)
            confidence_multiplier = analysis.confidence
            
            base_lot = self.base_lot * session_multiplier * confidence_multiplier
            lot_size = min(base_lot, self.max_lot)
            
            # สร้างสัญญาณ
            entry = TrendEntry(
                timestamp=datetime.now(),
                signal_type=f"TREND_{analysis.entry_type}",
                entry_price=analysis.entry_price,
                confidence=analysis.confidence,
                trend_strength=analysis.strength,
                ma_alignment="strong" in analysis.ma_trend,
                momentum_confirmation=abs(analysis.momentum_score) > 0.5,
                volume_confirmation=True,  # Placeholder
                session_multiplier=session_multiplier,
                lot_size=lot_size,
                reasoning=self._create_entry_reasoning(analysis)
            )
            
            # บันทึกประวัติ
            self.trend_history.append({
                'timestamp': entry.timestamp,
                'signal': entry.signal_type,
                'price': entry.entry_price,
                'confidence': entry.confidence,
                'adx': analysis.adx_value
            })
            
            # จำกัดประวัติ
            if len(self.trend_history) > 1000:
                self.trend_history = self.trend_history[-500:]
            
            print(f"✅ Trend Following Signal Generated:")
            print(f"   Type: {entry.signal_type}")
            print(f"   Price: ${entry.entry_price:.2f}")
            print(f"   Confidence: {entry.confidence:.2f}")
            print(f"   Lot Size: {entry.lot_size}")
            print(f"   Reasoning: {entry.reasoning}")
            
            return entry
            
        except Exception as e:
            print(f"❌ Entry signal generation error: {e}")
            return None
    
    def _create_entry_reasoning(self, analysis: TrendAnalysis) -> str:
        """สร้างเหตุผลสำหรับการ entry"""
        reasons = []
        
        reasons.append(f"Trend: {analysis.direction.value}")
        reasons.append(f"ADX: {analysis.adx_value:.1f} ({analysis.strength.value})")
        reasons.append(f"MA: {analysis.ma_trend}")
        reasons.append(f"Momentum: {analysis.momentum_score:.2f}")
        reasons.append(f"Confidence: {analysis.confidence:.2f}")
        reasons.append(f"R/R: {analysis.risk_reward:.1f}")
        
        return " | ".join(reasons)
    
    def _create_neutral_analysis(self) -> TrendAnalysis:
        """สร้าง analysis แบบ neutral เมื่อเกิดข้อผิดพลาด"""
        return TrendAnalysis(
            direction=TrendDirection.SIDEWAYS,
            strength=TrendStrength.WEAK,
            adx_value=0.0,
            ma_trend="sideways",
            momentum_score=0.0,
            confidence=0.0,
            entry_signal=False,
            entry_type="",
            entry_price=0.0,
            stop_distance=0.0,
            target_distance=0.0,
            risk_reward=0.0
        )
    
    def get_current_trend_status(self) -> Dict:
        """ดึงสถานะเทรนด์ปัจจุบัน"""
        if self.last_analysis:
            return {
                'direction': self.last_analysis.direction.value,
                'strength': self.last_analysis.strength.value,
                'adx': self.last_analysis.adx_value,
                'confidence': self.last_analysis.confidence,
                'last_update': self.last_update.strftime("%H:%M:%S") if self.last_update else "Never"
            }
        return {'status': 'No analysis available'}
    
    def get_performance_stats(self) -> Dict:
        """ดึงสถิติการทำงาน"""
        if not self.trend_history:
            return {'status': 'No trading history'}
        
        total_signals = len(self.trend_history)
        buy_signals = len([h for h in self.trend_history if 'BUY' in h['signal']])
        sell_signals = total_signals - buy_signals
        
        avg_confidence = np.mean([h['confidence'] for h in self.trend_history])
        
        return {
            'total_signals': total_signals,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'avg_confidence': avg_confidence,
            'last_signal': self.trend_history[-1]['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        }

def main():
    """Test the Trend Following Engine"""
    print("🧪 Testing Trend Following Engine...")
    
    # Sample configuration
    config = {
        'adx_period': 14,
        'ma_fast': 20,
        'ma_slow': 50,
        'ma_filter': 100,
        'min_adx': 25.0,
        'min_confidence': 0.7,
        'base_lot': 0.01,
        'london_multiplier': 1.5
    }
    
    # Initialize engine
    engine = TrendFollowingEngine(config)
    
    # Generate sample data
    dates = pd.date_range(start='2024-01-01', periods=200, freq='5min')
    np.random.seed(42)
    
    # Create trending data
    trend = np.cumsum(np.random.randn(200) * 0.1)
    noise = np.random.randn(200) * 0.5
    prices = 2000 + trend + noise
    
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices + np.random.rand(200) * 2,
        'low': prices - np.random.rand(200) * 2,
        'close': prices + np.random.randn(200) * 0.3,
        'volume': np.random.randint(100, 1000, 200)
    })
    
    # Test analysis
    analysis = engine.analyze_trend(sample_data)
    print(f"\n📊 Analysis Result:")
    print(f"   Direction: {analysis.direction.value}")
    print(f"   Strength: {analysis.strength.value}")
    print(f"   ADX: {analysis.adx_value:.2f}")
    print(f"   Confidence: {analysis.confidence:.2f}")
    print(f"   Entry Signal: {analysis.entry_signal}")
    
    # Test entry generation
    entry = engine.generate_entry_signal(sample_data, 'london')
    if entry:
        print(f"\n🎯 Entry Signal:")
        print(f"   Type: {entry.signal_type}")
        print(f"   Price: ${entry.entry_price:.2f}")
        print(f"   Lot Size: {entry.lot_size}")
        print(f"   Confidence: {entry.confidence:.2f}")
    else:
        print("\n❌ No entry signal generated")
    
    print("\n✅ Trend Following Engine test completed")

if __name__ == "__main__":
    main()