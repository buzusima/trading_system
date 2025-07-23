# adaptive_entries/entry_engines/mean_reversion.py - Mean Reversion Entry Logic

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class ReversionStrength(Enum):
    """📉 ความแรงของการ Mean Reversion"""
    WEAK = "weak"           # RSI 45-55, BB squeeze
    MODERATE = "moderate"   # RSI 35-45 หรือ 55-65
    STRONG = "strong"       # RSI 25-35 หรือ 65-75
    EXTREME = "extreme"     # RSI < 25 หรือ > 75

class MarketState(Enum):
    """🎯 สภาพตลาด"""
    OVERSOLD = "oversold"       # เกินขาย
    OVERBOUGHT = "overbought"   # เกินซื้อ
    NEUTRAL = "neutral"         # กลาง
    RANGING = "ranging"         # ไซด์เวย์

@dataclass
class ReversionAnalysis:
    """📊 ผลการวิเคราะห์ Mean Reversion"""
    market_state: MarketState
    reversion_strength: ReversionStrength
    rsi_value: float
    bb_position: float  # 0-1, position within Bollinger Bands
    distance_from_mean: float
    support_resistance_level: float
    confidence: float
    entry_signal: bool
    entry_type: str  # "BUY" or "SELL"
    entry_price: float
    mean_target: float
    reversion_probability: float

@dataclass
class ReversionEntry:
    """🎯 สัญญาณ Entry จาก Mean Reversion"""
    timestamp: datetime
    signal_type: str        # "REVERSION_BUY" or "REVERSION_SELL"
    entry_price: float
    confidence: float
    reversion_strength: ReversionStrength
    mean_target: float
    distance_from_mean: float
    support_resistance_confirmation: bool
    volume_confirmation: bool
    session_multiplier: float
    lot_size: float
    reasoning: str

class MeanReversionEngine:
    """
    🔄 Mean Reversion Entry Engine - Advanced Contrarian Trading Logic
    
    เหมาะสำหรับ:
    - Asian Session (22:00-08:00 GMT+7) - ความผันผวนต่ำ
    - Ranging Markets (ADX < 20)
    - Consolidation periods
    
    กลยุทธ์:
    - เทรดกลับจาก extreme levels
    - ใช้ RSI และ Bollinger Bands
    - หา Support/Resistance levels
    - Recovery ด้วย Smart Martingale (เพิ่มเมื่อไปต่อ)
    """
    
    def __init__(self, config: Dict):
        print("🔄 Initializing Mean Reversion Engine...")
        
        self.config = config
        
        # RSI parameters
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.rsi_extreme_oversold = config.get('rsi_extreme_oversold', 20)
        self.rsi_extreme_overbought = config.get('rsi_extreme_overbought', 80)
        
        # Bollinger Bands parameters
        self.bb_period = config.get('bb_period', 20)
        self.bb_std = config.get('bb_std', 2.0)
        
        # Support/Resistance parameters
        self.sr_lookback = config.get('sr_lookback', 50)
        self.sr_threshold = config.get('sr_threshold', 5.0)  # pips
        
        # Entry parameters
        self.min_confidence = config.get('min_confidence', 0.65)
        self.max_distance_from_mean = config.get('max_distance_from_mean', 100.0)  # pips
        self.min_reversion_probability = config.get('min_reversion_probability', 0.6)
        
        # Session multipliers
        self.session_multipliers = {
            'asian': config.get('asian_multiplier', 1.5),    # ดีที่สุดสำหรับ mean reversion
            'london': config.get('london_multiplier', 0.8),  # ระวังเทรนด์แรง
            'ny': config.get('ny_multiplier', 0.7),          # ระวังเทรนด์แรง
            'overlap': config.get('overlap_multiplier', 0.6), # หลีกเลี่ยง
            'quiet': config.get('quiet_multiplier', 2.0)     # ช่วงเงียบ
        }
        
        # Risk parameters
        self.base_lot = config.get('base_lot', 0.01)
        self.max_lot = config.get('max_lot', 0.3)
        self.risk_per_trade = config.get('risk_per_trade', 0.8)  # %
        
        # Cache
        self.last_analysis = None
        self.last_update = None
        self.reversion_history = []
        self.support_resistance_levels = []
        
        print("✅ Mean Reversion Engine initialized")
        print(f"   - RSI Period: {self.rsi_period}")
        print(f"   - RSI Levels: {self.rsi_oversold}/{self.rsi_overbought}")
        print(f"   - BB Period: {self.bb_period} (±{self.bb_std}σ)")
        print(f"   - Min Confidence: {self.min_confidence}")
    
    def analyze_reversion(self, market_data: pd.DataFrame) -> ReversionAnalysis:
        """
        🔍 วิเคราะห์โอกาส Mean Reversion
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            ReversionAnalysis object
        """
        try:
            if len(market_data) < max(self.rsi_period, self.bb_period, self.sr_lookback) + 10:
                print("❌ Insufficient data for reversion analysis")
                return self._create_neutral_analysis()
            
            # คำนวณ indicators
            df = market_data.copy()
            df = self._calculate_reversion_indicators(df)
            
            # วิเคราะห์สภาพตลาด
            current_data = df.iloc[-1]
            
            # 1. RSI Analysis
            rsi_value = current_data['rsi']
            market_state = self._classify_market_state(rsi_value, current_data)
            
            # 2. Bollinger Bands Position
            bb_position = current_data['bb_position']
            
            # 3. Distance from Mean
            distance_from_mean = abs(current_data['distance_from_mean'])
            
            # 4. Support/Resistance Analysis
            sr_level = self._find_nearest_sr_level(current_data['close'])
            
            # 5. Reversion Strength
            reversion_strength = self._classify_reversion_strength(
                rsi_value, bb_position, distance_from_mean
            )
            
            # 6. Confidence Calculation
            confidence = self._calculate_reversion_confidence(
                current_data, market_state, reversion_strength, sr_level
            )
            
            # 7. Entry Signal Generation
            entry_signal, entry_type = self._generate_reversion_signal(
                market_state, reversion_strength, confidence, current_data
            )
            
            # 8. Mean Target Calculation
            mean_target = current_data['bb_middle']  # Use BB middle as mean
            
            # 9. Reversion Probability
            reversion_probability = self._calculate_reversion_probability(
                rsi_value, bb_position, distance_from_mean
            )
            
            analysis = ReversionAnalysis(
                market_state=market_state,
                reversion_strength=reversion_strength,
                rsi_value=rsi_value,
                bb_position=bb_position,
                distance_from_mean=distance_from_mean,
                support_resistance_level=sr_level,
                confidence=confidence,
                entry_signal=entry_signal,
                entry_type=entry_type,
                entry_price=current_data['close'],
                mean_target=mean_target,
                reversion_probability=reversion_probability
            )
            
            # Cache analysis
            self.last_analysis = analysis
            self.last_update = datetime.now()
            
            return analysis
            
        except Exception as e:
            print(f"❌ Reversion analysis error: {e}")
            return self._create_neutral_analysis()
    
    def _calculate_reversion_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """คำนวณ indicators สำหรับ Mean Reversion"""
        try:
            # RSI Calculation
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=self.bb_period).mean()
            bb_std = df['close'].rolling(window=self.bb_period).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * self.bb_std)
            df['bb_lower'] = df['bb_middle'] - (bb_std * self.bb_std)
            
            # BB Position (0 = lower band, 1 = upper band)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            df['bb_position'] = df['bb_position'].clip(0, 1)
            
            # Distance from mean (in pips, assuming XAUUSD)
            df['distance_from_mean'] = (df['close'] - df['bb_middle']) * 10  # Convert to pips
            
            # Price momentum (short-term)
            df['momentum_3'] = df['close'].pct_change(3) * 100
            df['momentum_5'] = df['close'].pct_change(5) * 100
            
            # ATR for volatility
            df['tr'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            df['atr'] = df['tr'].rolling(window=14).mean()
            
            # Volume-based indicators (if available)
            if 'volume' in df.columns:
                df['volume_ma'] = df['volume'].rolling(window=20).mean()
                df['volume_ratio'] = df['volume'] / df['volume_ma']
            else:
                df['volume_ratio'] = 1.0
            
            # Update Support/Resistance levels
            self._update_support_resistance_levels(df)
            
            return df
            
        except Exception as e:
            print(f"❌ Reversion indicator calculation error: {e}")
            return df
    
    def _classify_market_state(self, rsi_value: float, data: pd.Series) -> MarketState:
        """จำแนกสภาพตลาดจาก RSI และ indicators อื่น"""
        try:
            bb_position = data['bb_position']
            
            # Extreme conditions
            if rsi_value <= self.rsi_extreme_oversold and bb_position <= 0.1:
                return MarketState.OVERSOLD
            elif rsi_value >= self.rsi_extreme_overbought and bb_position >= 0.9:
                return MarketState.OVERBOUGHT
            
            # Moderate conditions
            elif rsi_value <= self.rsi_oversold and bb_position <= 0.2:
                return MarketState.OVERSOLD
            elif rsi_value >= self.rsi_overbought and bb_position >= 0.8:
                return MarketState.OVERBOUGHT
            
            # Ranging market (price within BB middle range)
            elif 0.3 <= bb_position <= 0.7 and 40 <= rsi_value <= 60:
                return MarketState.RANGING
            
            else:
                return MarketState.NEUTRAL
                
        except Exception as e:
            print(f"❌ Market state classification error: {e}")
            return MarketState.NEUTRAL
    
    def _classify_reversion_strength(self, rsi_value: float, bb_position: float, 
                                   distance_from_mean: float) -> ReversionStrength:
        """จำแนกความแรงของ reversion opportunity"""
        try:
            score = 0
            
            # RSI contribution
            if rsi_value <= self.rsi_extreme_oversold or rsi_value >= self.rsi_extreme_overbought:
                score += 3
            elif rsi_value <= self.rsi_oversold or rsi_value >= self.rsi_overbought:
                score += 2
            elif rsi_value <= 35 or rsi_value >= 65:
                score += 1
            
            # BB position contribution
            if bb_position <= 0.05 or bb_position >= 0.95:
                score += 3
            elif bb_position <= 0.15 or bb_position >= 0.85:
                score += 2
            elif bb_position <= 0.25 or bb_position >= 0.75:
                score += 1
            
            # Distance from mean contribution
            if abs(distance_from_mean) >= 50:
                score += 2
            elif abs(distance_from_mean) >= 30:
                score += 1
            
            # Classify based on total score
            if score >= 7:
                return ReversionStrength.EXTREME
            elif score >= 5:
                return ReversionStrength.STRONG
            elif score >= 3:
                return ReversionStrength.MODERATE
            else:
                return ReversionStrength.WEAK
                
        except Exception as e:
            print(f"❌ Reversion strength classification error: {e}")
            return ReversionStrength.WEAK
    
    def _update_support_resistance_levels(self, df: pd.DataFrame):
        """อัพเดต Support/Resistance levels"""
        try:
            if len(df) < self.sr_lookback:
                return
            
            # Get recent data
            recent_data = df.tail(self.sr_lookback)
            
            # Find potential levels from highs and lows
            highs = recent_data['high'].rolling(window=5, center=True).max()
            lows = recent_data['low'].rolling(window=5, center=True).min()
            
            # Identify peaks and valleys
            peaks = recent_data[recent_data['high'] == highs]['high'].values
            valleys = recent_data[recent_data['low'] == lows]['low'].values
            
            # Combine and remove duplicates
            all_levels = np.concatenate([peaks, valleys])
            
            # Group nearby levels (within threshold)
            levels = []
            for level in sorted(all_levels):
                if not levels or abs(level - levels[-1]) > self.sr_threshold:
                    levels.append(level)
            
            self.support_resistance_levels = levels[-10:]  # Keep last 10 levels
            
        except Exception as e:
            print(f"❌ S/R level update error: {e}")
    
    def _find_nearest_sr_level(self, current_price: float) -> float:
        """หา S/R level ที่ใกล้ที่สุด"""
        try:
            if not self.support_resistance_levels:
                return current_price
            
            distances = [abs(current_price - level) for level in self.support_resistance_levels]
            nearest_index = np.argmin(distances)
            
            return self.support_resistance_levels[nearest_index]
            
        except Exception as e:
            print(f"❌ Nearest S/R level error: {e}")
            return current_price
    
    def _calculate_reversion_confidence(self, data: pd.Series, market_state: MarketState,
                                      strength: ReversionStrength, sr_level: float) -> float:
        """คำนวณความเชื่อมั่นใน reversion trade"""
        try:
            confidence = 0.0
            
            # Market state contribution (0-0.3)
            state_confidence = {
                MarketState.OVERSOLD: 0.25,
                MarketState.OVERBOUGHT: 0.25,
                MarketState.RANGING: 0.15,
                MarketState.NEUTRAL: 0.05
            }
            confidence += state_confidence[market_state]
            
            # Reversion strength contribution (0-0.3)
            strength_confidence = {
                ReversionStrength.EXTREME: 0.3,
                ReversionStrength.STRONG: 0.22,
                ReversionStrength.MODERATE: 0.15,
                ReversionStrength.WEAK: 0.05
            }
            confidence += strength_confidence[strength]
            
            # Support/Resistance confirmation (0-0.2)
            distance_to_sr = abs(data['close'] - sr_level)
            if distance_to_sr <= self.sr_threshold:
                confidence += 0.2
            elif distance_to_sr <= self.sr_threshold * 2:
                confidence += 0.1
            
            # Volume confirmation (0-0.1)
            if data['volume_ratio'] > 1.2:  # Above average volume
                confidence += 0.1
            elif data['volume_ratio'] > 1.0:
                confidence += 0.05
            
            # Recent momentum divergence (0-0.1)
            momentum_3 = data['momentum_3']
            momentum_5 = data['momentum_5']
            
            # Look for momentum slowing (divergence)
            if abs(momentum_3) < abs(momentum_5):
                confidence += 0.1
            elif abs(momentum_3) > abs(momentum_5) * 1.5:
                confidence -= 0.05  # Momentum accelerating (bad for reversion)
            
            return max(0.0, min(confidence, 1.0))
            
        except Exception as e:
            print(f"❌ Confidence calculation error: {e}")
            return 0.0
    
    def _calculate_reversion_probability(self, rsi_value: float, bb_position: float,
                                       distance_from_mean: float) -> float:
        """คำนวณความน่าจะเป็นของการ revert กลับ mean"""
        try:
            probability = 0.5  # Base probability
            
            # RSI-based probability adjustment
            if rsi_value <= 20:
                probability += 0.3
            elif rsi_value <= 30:
                probability += 0.2
            elif rsi_value >= 80:
                probability += 0.3
            elif rsi_value >= 70:
                probability += 0.2
            
            # BB position adjustment
            if bb_position <= 0.1 or bb_position >= 0.9:
                probability += 0.2
            elif bb_position <= 0.2 or bb_position >= 0.8:
                probability += 0.1
            
            # Distance from mean adjustment
            distance_factor = min(abs(distance_from_mean) / 100.0, 0.2)
            probability += distance_factor
            
            return max(0.1, min(probability, 0.95))
            
        except Exception as e:
            print(f"❌ Reversion probability error: {e}")
            return 0.5
    
    def _generate_reversion_signal(self, market_state: MarketState, strength: ReversionStrength,
                                 confidence: float, data: pd.Series) -> Tuple[bool, str]:
        """สร้างสัญญาณ reversion entry"""
        try:
            # ตรวจสอบเงื่อนไขพื้นฐาน
            if confidence < self.min_confidence:
                return False, ""
            
            if strength == ReversionStrength.WEAK:
                return False, ""
            
            distance = abs(data['distance_from_mean'])
            if distance > self.max_distance_from_mean:
                return False, ""
            
            # Generate signals based on market state
            if market_state == MarketState.OVERSOLD:
                # Price is oversold, expect reversion up
                if data['rsi'] <= self.rsi_oversold and data['bb_position'] <= 0.3:
                    return True, "BUY"
            
            elif market_state == MarketState.OVERBOUGHT:
                # Price is overbought, expect reversion down
                if data['rsi'] >= self.rsi_overbought and data['bb_position'] >= 0.7:
                    return True, "SELL"
            
            elif market_state == MarketState.RANGING:
                # In ranging market, trade both directions
                if data['bb_position'] <= 0.25:
                    return True, "BUY"
                elif data['bb_position'] >= 0.75:
                    return True, "SELL"
            
            return False, ""
            
        except Exception as e:
            print(f"❌ Reversion signal error: {e}")
            return False, ""
    
    def generate_entry_signal(self, market_data: pd.DataFrame,
                            current_session: str = 'asian') -> Optional[ReversionEntry]:
        """
        🎯 สร้างสัญญาณ Entry สำหรับ Mean Reversion
        
        Args:
            market_data: ข้อมูลตลาดล่าสุด
            current_session: เซสชั่นปัจจุบัน
            
        Returns:
            ReversionEntry object หรือ None
        """
        try:
            # วิเคราะห์ reversion opportunity
            analysis = self.analyze_reversion(market_data)
            
            if not analysis.entry_signal:
                return None
            
            # ตรวจสอบ reversion probability
            if analysis.reversion_probability < self.min_reversion_probability:
                return None
            
            # คำนวณ lot size ตาม session และ confidence
            session_multiplier = self.session_multipliers.get(current_session, 1.0)
            confidence_multiplier = analysis.confidence
            reversion_multiplier = min(analysis.reversion_probability * 2, 1.5)
            
            base_lot = self.base_lot * session_multiplier * confidence_multiplier * reversion_multiplier
            lot_size = min(base_lot, self.max_lot)
            
            # ปรับ lot size ตาม distance from mean (ยิ่งไกลยิ่งเพิ่ม)
            distance_multiplier = 1 + (abs(analysis.distance_from_mean) / 200.0)
            lot_size = min(lot_size * distance_multiplier, self.max_lot)
            
            # สร้างสัญญาณ
            entry = ReversionEntry(
                timestamp=datetime.now(),
                signal_type=f"REVERSION_{analysis.entry_type}",
                entry_price=analysis.entry_price,
                confidence=analysis.confidence,
                reversion_strength=analysis.reversion_strength,
                mean_target=analysis.mean_target,
                distance_from_mean=analysis.distance_from_mean,
                support_resistance_confirmation=abs(analysis.entry_price - analysis.support_resistance_level) <= self.sr_threshold,
                volume_confirmation=True,  # Placeholder
                session_multiplier=session_multiplier,
                lot_size=lot_size,
                reasoning=self._create_reversion_reasoning(analysis)
            )
            
            # บันทึกประวัติ
            self.reversion_history.append({
                'timestamp': entry.timestamp,
                'signal': entry.signal_type,
                'price': entry.entry_price,
                'confidence': entry.confidence,
                'rsi': analysis.rsi_value,
                'bb_position': analysis.bb_position,
                'distance_from_mean': analysis.distance_from_mean
            })
            
            # จำกัดประวัติ
            if len(self.reversion_history) > 1000:
                self.reversion_history = self.reversion_history[-500:]
            
            print(f"✅ Mean Reversion Signal Generated:")
            print(f"   Type: {entry.signal_type}")
            print(f"   Price: ${entry.entry_price:.2f}")
            print(f"   Confidence: {entry.confidence:.2f}")
            print(f"   Lot Size: {entry.lot_size}")
            print(f"   Mean Target: ${entry.mean_target:.2f}")
            print(f"   Distance: {entry.distance_from_mean:.1f} pips")
            print(f"   Reasoning: {entry.reasoning}")
            
            return entry
            
        except Exception as e:
            print(f"❌ Reversion entry generation error: {e}")
            return None
    
    def _create_reversion_reasoning(self, analysis: ReversionAnalysis) -> str:
        """สร้างเหตุผลสำหรับการ entry"""
        reasons = []
        
        reasons.append(f"State: {analysis.market_state.value}")
        reasons.append(f"RSI: {analysis.rsi_value:.1f}")
        reasons.append(f"BB: {analysis.bb_position:.2f}")
        reasons.append(f"Distance: {analysis.distance_from_mean:.1f}p")
        reasons.append(f"Strength: {analysis.reversion_strength.value}")
        reasons.append(f"Confidence: {analysis.confidence:.2f}")
        reasons.append(f"Rev.Prob: {analysis.reversion_probability:.2f}")
        
        return " | ".join(reasons)
    
    def _create_neutral_analysis(self) -> ReversionAnalysis:
        """สร้าง analysis แบบ neutral เมื่อเกิดข้อผิดพลาด"""
        return ReversionAnalysis(
            market_state=MarketState.NEUTRAL,
            reversion_strength=ReversionStrength.WEAK,
            rsi_value=50.0,
            bb_position=0.5,
            distance_from_mean=0.0,
            support_resistance_level=0.0,
            confidence=0.0,
            entry_signal=False,
            entry_type="",
            entry_price=0.0,
            mean_target=0.0,
            reversion_probability=0.5
        )
    
    def get_current_reversion_status(self) -> Dict:
        """ดึงสถานะ reversion ปัจจุบัน"""
        if self.last_analysis:
            return {
                'market_state': self.last_analysis.market_state.value,
                'strength': self.last_analysis.reversion_strength.value,
                'rsi': self.last_analysis.rsi_value,
                'bb_position': self.last_analysis.bb_position,
                'confidence': self.last_analysis.confidence,
                'reversion_probability': self.last_analysis.reversion_probability,
                'last_update': self.last_update.strftime("%H:%M:%S") if self.last_update else "Never"
            }
        return {'status': 'No analysis available'}
    
    def get_support_resistance_levels(self) -> List[float]:
        """ดึง Support/Resistance levels ปัจจุบัน"""
        return self.support_resistance_levels.copy()
    
    def get_performance_stats(self) -> Dict:
        """ดึงสถิติการทำงาน"""
        if not self.reversion_history:
            return {'status': 'No trading history'}
        
        total_signals = len(self.reversion_history)
        buy_signals = len([h for h in self.reversion_history if 'BUY' in h['signal']])
        sell_signals = total_signals - buy_signals
        
        avg_confidence = np.mean([h['confidence'] for h in self.reversion_history])
        avg_rsi = np.mean([h['rsi'] for h in self.reversion_history])
        avg_distance = np.mean([abs(h['distance_from_mean']) for h in self.reversion_history])
        
        return {
            'total_signals': total_signals,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'avg_confidence': avg_confidence,
            'avg_rsi': avg_rsi,
            'avg_distance_from_mean': avg_distance,
            'sr_levels_count': len(self.support_resistance_levels),
            'last_signal': self.reversion_history[-1]['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        }

def main():
    """Test the Mean Reversion Engine"""
    print("🧪 Testing Mean Reversion Engine...")
    
    # Sample configuration
    config = {
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'bb_period': 20,
        'bb_std': 2.0,
        'min_confidence': 0.65,
        'base_lot': 0.01,
        'asian_multiplier': 1.5
    }
    
    # Initialize engine
    engine = MeanReversionEngine(config)
    
    # Generate sample ranging data
    dates = pd.date_range(start='2024-01-01', periods=200, freq='5min')
    np.random.seed(42)
    
    # Create ranging market data
    base_price = 2000
    noise = np.random.randn(200) * 0.8
    trend = np.sin(np.linspace(0, 4*np.pi, 200)) * 10  # Sine wave for ranging
    prices = base_price + trend + noise
    
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices + np.random.rand(200) * 3,
        'low': prices - np.random.rand(200) * 3,
        'close': prices + np.random.randn(200) * 0.5,
        'volume': np.random.randint(100, 1000, 200)
    })
    
    # Test analysis
    analysis = engine.analyze_reversion(sample_data)
    print(f"\n📊 Analysis Result:")
    print(f"   Market State: {analysis.market_state.value}")
    print(f"   Strength: {analysis.reversion_strength.value}")
    print(f"   RSI: {analysis.rsi_value:.2f}")
    print(f"   BB Position: {analysis.bb_position:.2f}")
    print(f"   Distance from Mean: {analysis.distance_from_mean:.1f} pips")
    print(f"   Confidence: {analysis.confidence:.2f}")
    print(f"   Entry Signal: {analysis.entry_signal}")
    
    # Test entry generation
    entry = engine.generate_entry_signal(sample_data, 'asian')
    if entry:
        print(f"\n🎯 Entry Signal:")
        print(f"   Type: {entry.signal_type}")
        print(f"   Price: ${entry.entry_price:.2f}")
        print(f"   Lot Size: {entry.lot_size}")
        print(f"   Mean Target: ${entry.mean_target:.2f}")
        print(f"   Confidence: {entry.confidence:.2f}")
    else:
        print("\n❌ No reversion signal generated")
    
    # Test S/R levels
    sr_levels = engine.get_support_resistance_levels()
    print(f"\n📈 Support/Resistance Levels: {len(sr_levels)} levels found")
    for i, level in enumerate(sr_levels[:5]):  # Show first 5 levels
        print(f"   Level {i+1}: ${level:.2f}")
    
    print("\n✅ Mean Reversion Engine test completed")

if __name__ == "__main__":
    main()