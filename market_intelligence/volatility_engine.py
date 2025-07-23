# market_intelligence/volatility_engine.py - Advanced Volatility Analysis Engine

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import math

class VolatilityLevel(Enum):
    """📈 ระดับความผันผวน"""
    EXTREMELY_LOW = "extremely_low"    # < 10 pips/hour
    LOW = "low"                        # 10-20 pips/hour
    MODERATE = "moderate"              # 20-40 pips/hour
    HIGH = "high"                      # 40-70 pips/hour
    EXTREMELY_HIGH = "extremely_high"  # > 70 pips/hour

class VolatilityTrend(Enum):
    """📊 แนวโน้มความผันผวน"""
    INCREASING = "increasing"          # ความผันผวนเพิ่มขึ้น
    DECREASING = "decreasing"          # ความผันผวนลดลง
    STABLE = "stable"                  # ความผันผวนคงที่
    VOLATILE = "volatile"              # ความผันผวนแปรปรวน

class VolatilityRegime(Enum):
    """🌊 ระบอบความผันผวน"""
    CALM = "calm"                      # ตลาดเงียบ
    NORMAL = "normal"                  # ตลาดปกติ
    TURBULENT = "turbulent"            # ตลาดป่วน
    CRISIS = "crisis"                  # ตลาดวิกฤต

@dataclass
class VolatilityMeasurement:
    """📏 การวัดความผันผวน"""
    atr_value: float                   # Average True Range
    atr_pips: float                    # ATR ในหน่วย pips
    realized_volatility: float         # ความผันผวนที่เกิดขึ้นจริง
    implied_volatility: float          # ความผันผวนโดยนัย
    volatility_percentile: float       # เปอร์เซ็นไทล์ความผันผวน
    intraday_range: float              # ช่วงราคาภายในวัน
    hourly_volatility: float           # ความผันผวนต่อชั่วโมง

@dataclass
class VolatilityAnalysis:
    """🔍 ผลการวิเคราะห์ความผันผวน"""
    current_level: VolatilityLevel
    trend: VolatilityTrend
    regime: VolatilityRegime
    measurements: VolatilityMeasurement
    
    # การคาดการณ์
    expected_range_next_hour: Tuple[float, float]
    expected_range_next_4hours: Tuple[float, float]
    breakout_probability: float
    
    # คำแนะนำ
    optimal_strategies: List[str]
    risk_adjustment: float
    position_sizing_multiplier: float
    
    confidence: float
    analysis_time: datetime

class VolatilityEngine:
    """
    🔬 Volatility Analysis Engine - เครื่องมือวิเคราะห์ความผันผวนขั้นสูง
    
    ⚡ หน้าที่หลัก:
    - วิเคราะห์ความผันผวนแบบ Real-time
    - คาดการณ์ความผันผวนในอนาคต
    - จำแนกระบอบความผันผวน (Volatility Regimes)
    - แนะนำกลยุทธ์ตามระดับความผันผวน
    - ปรับ Risk Management ตามความผันผวน
    
    🎯 วิธีการวิเคราะห์:
    - Average True Range (ATR)
    - Realized Volatility
    - GARCH Models (simplified)
    - Bollinger Bands Width
    - Price Range Analysis
    - Volume-Price Volatility
    """
    
    def __init__(self, config: Dict):
        print("🔬 Initializing Volatility Engine...")
        
        self.config = config
        
        # Volatility parameters
        self.atr_period = config.get('atr_period', 14)
        self.volatility_lookback = config.get('volatility_lookback', 100)
        self.regime_lookback = config.get('regime_lookback', 50)
        
        # Volatility thresholds (in pips for XAUUSD)
        self.thresholds = {
            'extremely_low': config.get('extremely_low_threshold', 10),
            'low': config.get('low_threshold', 20),
            'moderate': config.get('moderate_threshold', 40),
            'high': config.get('high_threshold', 70)
        }
        
        # Bollinger Bands parameters
        self.bb_period = config.get('bb_period', 20)
        self.bb_std = config.get('bb_std', 2.0)
        
        # GARCH parameters (simplified)
        self.garch_alpha = config.get('garch_alpha', 0.05)
        self.garch_beta = config.get('garch_beta', 0.90)
        
        # Historical data cache
        self.volatility_history = []
        self.regime_history = []
        self.last_analysis = None
        self.last_analysis_time = None
        
        # Statistics
        self.analysis_count = 0
        self.regime_changes = 0
        
        print("✅ Volatility Engine initialized")
        print(f"   - ATR Period: {self.atr_period}")
        print(f"   - Volatility Lookback: {self.volatility_lookback}")
        print(f"   - Thresholds: {self.thresholds}")
    
    def analyze_volatility(self, market_data: pd.DataFrame) -> VolatilityAnalysis:
        """
        🔍 วิเคราะห์ความผันผวนแบบครอบคลุม
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            VolatilityAnalysis object
        """
        try:
            if len(market_data) < self.atr_period + 10:
                print("❌ Insufficient data for volatility analysis")
                return self._create_default_analysis()
            
            # คำนวณ volatility measurements
            measurements = self._calculate_volatility_measurements(market_data)
            
            # จำแนกระดับความผันผวน
            current_level = self._classify_volatility_level(measurements)
            
            # วิเคราะห์แนวโน้ม
            trend = self._analyze_volatility_trend(market_data, measurements)
            
            # จำแนกระบอบความผันผวน
            regime = self._classify_volatility_regime(market_data, measurements)
            
            # คาดการณ์ช่วงราคา
            next_hour_range = self._predict_price_range(market_data, 1)
            next_4hours_range = self._predict_price_range(market_data, 4)
            
            # คำนวณความน่าจะเป็นของ breakout
            breakout_prob = self._calculate_breakout_probability(market_data, measurements)
            
            # แนะนำกลยุทธ์
            optimal_strategies = self._recommend_strategies(current_level, trend, regime)
            
            # คำนวณการปรับ risk
            risk_adjustment = self._calculate_risk_adjustment(current_level, regime)
            
            # คำนวณตัวคูณ position sizing
            position_multiplier = self._calculate_position_multiplier(current_level, trend)
            
            # คำนวณความเชื่อมั่น
            confidence = self._calculate_analysis_confidence(market_data, measurements)
            
            analysis = VolatilityAnalysis(
                current_level=current_level,
                trend=trend,
                regime=regime,
                measurements=measurements,
                expected_range_next_hour=next_hour_range,
                expected_range_next_4hours=next_4hours_range,
                breakout_probability=breakout_prob,
                optimal_strategies=optimal_strategies,
                risk_adjustment=risk_adjustment,
                position_sizing_multiplier=position_multiplier,
                confidence=confidence,
                analysis_time=datetime.now()
            )
            
            # Cache analysis
            self._cache_analysis(analysis)
            
            return analysis
            
        except Exception as e:
            print(f"❌ Volatility analysis error: {e}")
            return self._create_default_analysis()
    
    def _calculate_volatility_measurements(self, market_data: pd.DataFrame) -> VolatilityMeasurement:
        """คำนวณการวัดความผันผวนต่างๆ"""
        try:
            df = market_data.copy()
            
            # 1. Average True Range (ATR)
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift(1))
            low_close = abs(df['low'] - df['close'].shift(1))
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr_value = true_range.rolling(window=self.atr_period).mean().iloc[-1]
            atr_pips = atr_value * 10  # แปลงเป็น pips สำหรับ XAUUSD
            
            # 2. Realized Volatility (การเคลื่อนไหวจริง)
            returns = df['close'].pct_change().dropna()
            realized_vol = returns.rolling(window=self.atr_period).std().iloc[-1] * np.sqrt(1440)  # Annualized
            
            # 3. Implied Volatility (ประมาณจาก Bollinger Bands)
            bb_middle = df['close'].rolling(window=self.bb_period).mean()
            bb_std = df['close'].rolling(window=self.bb_period).std()
            bb_width = (bb_std * self.bb_std * 2) / bb_middle
            implied_vol = bb_width.iloc[-1] * 100  # เป็น %
            
            # 4. Volatility Percentile
            recent_vol = true_range.rolling(window=self.atr_period).mean()
            vol_percentile = (recent_vol.iloc[-1] <= recent_vol.tail(self.volatility_lookback)).mean()
            
            # 5. Intraday Range
            if len(df) >= 24:  # อย่างน้อย 24 periods (2 ชั่วโมงสำหรับ M5)
                recent_24 = df.tail(24)
                intraday_range = (recent_24['high'].max() - recent_24['low'].min()) * 10  # pips
            else:
                intraday_range = atr_pips * 2
            
            # 6. Hourly Volatility
            if len(df) >= 12:  # 12 periods = 1 ชั่วโมง (M5)
                hourly_data = df.tail(12)
                hourly_vol = (hourly_data['high'].max() - hourly_data['low'].min()) * 10  # pips
            else:
                hourly_vol = atr_pips
            
            return VolatilityMeasurement(
                atr_value=atr_value,
                atr_pips=atr_pips,
                realized_volatility=realized_vol,
                implied_volatility=implied_vol,
                volatility_percentile=vol_percentile,
                intraday_range=intraday_range,
                hourly_volatility=hourly_vol
            )
            
        except Exception as e:
            print(f"❌ Volatility measurements calculation error: {e}")
            return VolatilityMeasurement(
                atr_value=0.5, atr_pips=5.0, realized_volatility=0.01,
                implied_volatility=1.0, volatility_percentile=0.5,
                intraday_range=20.0, hourly_volatility=10.0
            )
    
    def _classify_volatility_level(self, measurements: VolatilityMeasurement) -> VolatilityLevel:
        """จำแนกระดับความผันผวน"""
        try:
            atr_pips = measurements.atr_pips
            
            if atr_pips < self.thresholds['extremely_low']:
                return VolatilityLevel.EXTREMELY_LOW
            elif atr_pips < self.thresholds['low']:
                return VolatilityLevel.LOW
            elif atr_pips < self.thresholds['moderate']:
                return VolatilityLevel.MODERATE
            elif atr_pips < self.thresholds['high']:
                return VolatilityLevel.HIGH
            else:
                return VolatilityLevel.EXTREMELY_HIGH
                
        except Exception as e:
            print(f"❌ Volatility level classification error: {e}")
            return VolatilityLevel.MODERATE
    
    def _analyze_volatility_trend(self, market_data: pd.DataFrame, 
                                measurements: VolatilityMeasurement) -> VolatilityTrend:
        """วิเคราะห์แนวโน้มความผันผวน"""
        try:
            if len(market_data) < 30:
                return VolatilityTrend.STABLE
            
            # คำนวณ ATR ย้อนหลัง
            df = market_data.copy()
            
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift(1))
            low_close = abs(df['low'] - df['close'].shift(1))
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr_series = true_range.rolling(window=self.atr_period).mean()
            
            # เปรียบเทียบ ATR ปัจจุบันกับอดีต
            current_atr = atr_series.iloc[-1]
            past_atr_short = atr_series.iloc[-10:-1].mean()  # 10 periods ที่แล้ว
            past_atr_long = atr_series.iloc[-20:-10].mean()   # 20-10 periods ที่แล้ว
            
            # คำนวณการเปลี่ยนแปลง
            short_change = (current_atr - past_atr_short) / past_atr_short
            long_change = (past_atr_short - past_atr_long) / past_atr_long
            
            # จำแนกแนวโน้ม
            if short_change > 0.1 and long_change > 0.05:
                return VolatilityTrend.INCREASING
            elif short_change < -0.1 and long_change < -0.05:
                return VolatilityTrend.DECREASING
            elif abs(short_change) > 0.15 or abs(long_change) > 0.15:
                return VolatilityTrend.VOLATILE
            else:
                return VolatilityTrend.STABLE
                
        except Exception as e:
            print(f"❌ Volatility trend analysis error: {e}")
            return VolatilityTrend.STABLE
    
    def _classify_volatility_regime(self, market_data: pd.DataFrame, 
                                  measurements: VolatilityMeasurement) -> VolatilityRegime:
        """จำแนกระบอบความผันผวน"""
        try:
            # ใช้ percentile และ absolute level
            vol_percentile = measurements.volatility_percentile
            atr_pips = measurements.atr_pips
            
            # คำนวณคะแนนระบอบ
            regime_score = 0
            
            # ปรับตาม percentile
            if vol_percentile > 0.8:
                regime_score += 2  # ความผันผวนสูงกว่าปกติมาก
            elif vol_percentile > 0.6:
                regime_score += 1  # ความผันผวนสูงกว่าปกติ
            elif vol_percentile < 0.2:
                regime_score -= 1  # ความผันผวนต่ำกว่าปกติ
            
            # ปรับตาม absolute level
            if atr_pips > 70:
                regime_score += 2
            elif atr_pips > 40:
                regime_score += 1
            elif atr_pips < 15:
                regime_score -= 1
            
            # ปรับตาม intraday range
            if measurements.intraday_range > atr_pips * 5:
                regime_score += 1  # ช่วงกว้างผิดปกติ
            
            # จำแนกระบอบ
            if regime_score >= 4:
                return VolatilityRegime.CRISIS
            elif regime_score >= 2:
                return VolatilityRegime.TURBULENT
            elif regime_score <= -1:
                return VolatilityRegime.CALM
            else:
                return VolatilityRegime.NORMAL
                
        except Exception as e:
            print(f"❌ Volatility regime classification error: {e}")
            return VolatilityRegime.NORMAL
    
    def _predict_price_range(self, market_data: pd.DataFrame, hours_ahead: int) -> Tuple[float, float]:
        """คาดการณ์ช่วงราคาในอนาคต"""
        try:
            current_price = market_data['close'].iloc[-1]
            
            # คำนวณ ATR
            df = market_data.copy()
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift(1))
            low_close = abs(df['low'] - df['close'].shift(1))
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(window=self.atr_period).mean().iloc[-1]
            
            # คำนวณ expected range
            # ใช้ square root rule สำหรับ time scaling
            time_multiplier = np.sqrt(hours_ahead / 24)  # scale จาก daily
            expected_range = atr * time_multiplier * 2  # ±2 ATR
            
            # ปรับตาม volatility regime ถ้ามีข้อมูล
            if hasattr(self, 'last_analysis') and self.last_analysis:
                regime = self.last_analysis.regime
                if regime == VolatilityRegime.CRISIS:
                    expected_range *= 1.5
                elif regime == VolatilityRegime.TURBULENT:
                    expected_range *= 1.2
                elif regime == VolatilityRegime.CALM:
                    expected_range *= 0.7
            
            lower_bound = current_price - expected_range
            upper_bound = current_price + expected_range
            
            return (lower_bound, upper_bound)
            
        except Exception as e:
            print(f"❌ Price range prediction error: {e}")
            current_price = market_data['close'].iloc[-1]
            default_range = current_price * 0.01  # 1%
            return (current_price - default_range, current_price + default_range)
    
    def _calculate_breakout_probability(self, market_data: pd.DataFrame, 
                                      measurements: VolatilityMeasurement) -> float:
        """คำนวณความน่าจะเป็นของ breakout"""
        try:
            probability = 0.3  # base probability
            
            # ปรับตามระดับความผันผวน
            atr_pips = measurements.atr_pips
            if atr_pips > 50:
                probability += 0.3
            elif atr_pips > 30:
                probability += 0.2
            elif atr_pips < 15:
                probability -= 0.2
            
            # ปรับตาม volatility percentile
            vol_percentile = measurements.volatility_percentile
            if vol_percentile > 0.8:
                probability += 0.2
            elif vol_percentile < 0.3:
                probability -= 0.1
            
            # ปรับตาม price compression
            if len(market_data) >= 20:
                recent_range = market_data['high'].tail(20).max() - market_data['low'].tail(20).min()
                avg_range = measurements.atr_value * 20
                
                compression_ratio = recent_range / avg_range
                if compression_ratio < 0.7:  # ราคาบีบตัว
                    probability += 0.2
                elif compression_ratio > 1.5:  # ราคากระจาย
                    probability -= 0.1
            
            # ปรับตาม volume (ถ้ามี)
            if 'volume' in market_data.columns:
                recent_volume = market_data['volume'].tail(10).mean()
                avg_volume = market_data['volume'].tail(50).mean()
                
                if recent_volume > avg_volume * 1.5:
                    probability += 0.1
            
            return max(0.05, min(probability, 0.95))
            
        except Exception as e:
            print(f"❌ Breakout probability calculation error: {e}")
            return 0.3
    
    def _recommend_strategies(self, level: VolatilityLevel, trend: VolatilityTrend, 
                            regime: VolatilityRegime) -> List[str]:
        """แนะนำกลยุทธ์ตามความผันผวน"""
        try:
            strategies = []
            
            # แนะนำตามระดับความผันผวน
            if level == VolatilityLevel.EXTREMELY_LOW:
                strategies.extend(["scalping", "mean_reversion", "range_trading"])
            elif level == VolatilityLevel.LOW:
                strategies.extend(["mean_reversion", "martingale_smart", "grid_small"])
            elif level == VolatilityLevel.MODERATE:
                strategies.extend(["trend_following", "grid_intelligent", "breakout"])
            elif level == VolatilityLevel.HIGH:
                strategies.extend(["trend_following", "momentum", "false_breakout"])
            else:  # EXTREMELY_HIGH
                strategies.extend(["trend_following", "momentum", "hedge"])
            
            # ปรับตาม trend
            if trend == VolatilityTrend.INCREASING:
                strategies.insert(0, "volatility_breakout")
            elif trend == VolatilityTrend.DECREASING:
                strategies.insert(0, "mean_reversion")
            elif trend == VolatilityTrend.VOLATILE:
                strategies.insert(0, "adaptive_hedge")
            
            # ปรับตาม regime
            if regime == VolatilityRegime.CRISIS:
                strategies = ["hedge", "correlation", "safe_haven"]
            elif regime == VolatilityRegime.TURBULENT:
                strategies.insert(0, "volatility_trading")
            elif regime == VolatilityRegime.CALM:
                strategies.extend(["carry_trade", "accumulation"])
            
            # ลบ strategies ที่ซ้ำและจำกัดจำนวน
            unique_strategies = []
            for strategy in strategies:
                if strategy not in unique_strategies:
                    unique_strategies.append(strategy)
                if len(unique_strategies) >= 5:
                    break
            
            return unique_strategies
            
        except Exception as e:
            print(f"❌ Strategy recommendation error: {e}")
            return ["mean_reversion", "trend_following"]
    
    def _calculate_risk_adjustment(self, level: VolatilityLevel, regime: VolatilityRegime) -> float:
        """คำนวณการปรับ risk"""
        try:
            # ปรับตามระดับความผันผวน
            level_adjustments = {
                VolatilityLevel.EXTREMELY_LOW: 1.2,   # เพิ่ม risk ได้
                VolatilityLevel.LOW: 1.1,
                VolatilityLevel.MODERATE: 1.0,        # baseline
                VolatilityLevel.HIGH: 0.8,            # ลด risk
                VolatilityLevel.EXTREMELY_HIGH: 0.6
            }
            
            # ปรับตาม regime
            regime_adjustments = {
                VolatilityRegime.CALM: 1.1,
                VolatilityRegime.NORMAL: 1.0,
                VolatilityRegime.TURBULENT: 0.8,
                VolatilityRegime.CRISIS: 0.5
            }
            
            level_adj = level_adjustments.get(level, 1.0)
            regime_adj = regime_adjustments.get(regime, 1.0)
            
            # รวมการปรับ
            combined_adjustment = level_adj * regime_adj
            
            return max(0.3, min(combined_adjustment, 2.0))
            
        except Exception as e:
            print(f"❌ Risk adjustment calculation error: {e}")
            return 1.0
    
    def _calculate_position_multiplier(self, level: VolatilityLevel, 
                                     trend: VolatilityTrend) -> float:
        """คำนวณตัวคูณ position sizing"""
        try:
            # ตัวคูณพื้นฐานตามระดับความผันผวน
            base_multipliers = {
                VolatilityLevel.EXTREMELY_LOW: 1.5,   # เพิ่ม position ได้
                VolatilityLevel.LOW: 1.2,
                VolatilityLevel.MODERATE: 1.0,        # baseline
                VolatilityLevel.HIGH: 0.8,            # ลด position
                VolatilityLevel.EXTREMELY_HIGH: 0.6
            }
            
            # ปรับตาม trend
            trend_adjustments = {
                VolatilityTrend.STABLE: 1.1,          # เสถียร เพิ่มได้
                VolatilityTrend.INCREASING: 0.9,      # เพิ่มขึ้น ระวัง
                VolatilityTrend.DECREASING: 1.0,      # ลดลง ปกติ
                VolatilityTrend.VOLATILE: 0.7         # แปรปรวน ระวังมาก
            }
            
            base_mult = base_multipliers.get(level, 1.0)
            trend_mult = trend_adjustments.get(trend, 1.0)
            
            return max(0.3, min(base_mult * trend_mult, 2.0))
            
        except Exception as e:
            print(f"❌ Position multiplier calculation error: {e}")
            return 1.0
    
    def _calculate_analysis_confidence(self, market_data: pd.DataFrame, 
                                     measurements: VolatilityMeasurement) -> float:
        """คำนวณความเชื่อมั่นในการวิเคราะห์"""
        try:
            confidence = 0.7  # base confidence
            
            # ปรับตามจำนวนข้อมูล
            data_length = len(market_data)
            if data_length >= self.volatility_lookback:
                confidence += 0.2
            elif data_length >= self.atr_period * 2:
                confidence += 0.1
            else:
                confidence -= 0.2
            
            # ปรับตาม volatility percentile (ยิ่งอยู่กลางยิ่งเชื่อมั่น)
            vol_percentile = measurements.volatility_percentile
            percentile_confidence = 1 - abs(vol_percentile - 0.5) * 2
            confidence += percentile_confidence * 0.15
            
            # ปรับตามความสอดคล้องของ measurements
            atr_normalized = measurements.atr_pips / 30  # normalize to ~30 pips
            hourly_normalized = measurements.hourly_volatility / 30
            
            consistency = 1 - abs(atr_normalized - hourly_normalized)
            confidence += consistency * 0.1
            
            # ปรับตามประวัติการวิเคราะห์
            if self.analysis_count > 10:
                confidence += 0.05
            
            return max(0.3, min(confidence, 0.95))
            
        except Exception as e:
            print(f"❌ Analysis confidence calculation error: {e}")
            return 0.7
    
    def _cache_analysis(self, analysis: VolatilityAnalysis):
        """Cache การวิเคราะห์"""
        try:
            self.last_analysis = analysis
            self.last_analysis_time = analysis.analysis_time
            self.analysis_count += 1
            
            # เก็บประวัติ
            self.volatility_history.append({
                'timestamp': analysis.analysis_time,
                'level': analysis.current_level.value,
                'atr_pips': analysis.measurements.atr_pips,
                'regime': analysis.regime.value
            })
            
            # ตรวจสอบการเปลี่ยน regime
            if len(self.regime_history) > 0:
                if self.regime_history[-1]['regime'] != analysis.regime.value:
                    self.regime_changes += 1
            
            self.regime_history.append({
                'timestamp': analysis.analysis_time,
                'regime': analysis.regime.value,
                'level': analysis.current_level.value
            })
            
            # จำกัดขนาดประวัติ
            if len(self.volatility_history) > 1000:
                self.volatility_history = self.volatility_history[-500:]
            
            if len(self.regime_history) > 1000:
                self.regime_history = self.regime_history[-500:]
                
        except Exception as e:
            print(f"❌ Analysis caching error: {e}")
    
    def _create_default_analysis(self) -> VolatilityAnalysis:
        """สร้าง analysis เริ่มต้นเมื่อเกิดข้อผิดพลาด"""
        default_measurements = VolatilityMeasurement(
            atr_value=0.5, atr_pips=20.0, realized_volatility=0.02,
            implied_volatility=2.0, volatility_percentile=0.5,
            intraday_range=40.0, hourly_volatility=15.0
        )
        
        return VolatilityAnalysis(
            current_level=VolatilityLevel.MODERATE,
            trend=VolatilityTrend.STABLE,
            regime=VolatilityRegime.NORMAL,
            measurements=default_measurements,
            expected_range_next_hour=(1990.0, 2010.0),
            expected_range_next_4hours=(1980.0, 2020.0),
            breakout_probability=0.3,
            optimal_strategies=["mean_reversion", "trend_following"],
            risk_adjustment=1.0,
            position_sizing_multiplier=1.0,
            confidence=0.5,
            analysis_time=datetime.now()
        )
    
    def get_volatility_summary(self) -> Dict:
        """ดึงสรุปข้อมูลความผันผวน"""
        try:
            if not self.last_analysis:
                return {'status': 'No analysis available'}
            
            analysis = self.last_analysis
            measurements = analysis.measurements
            
            return {
                'current_level': analysis.current_level.value,
                'atr_pips': f"{measurements.atr_pips:.1f}",
                'trend': analysis.trend.value,
                'regime': analysis.regime.value,
                'volatility_percentile': f"{measurements.volatility_percentile*100:.1f}%",
                'hourly_volatility': f"{measurements.hourly_volatility:.1f} pips",
                'intraday_range': f"{measurements.intraday_range:.1f} pips",
                'breakout_probability': f"{analysis.breakout_probability*100:.1f}%",
                'risk_adjustment': f"{analysis.risk_adjustment:.2f}x",
                'position_multiplier': f"{analysis.position_sizing_multiplier:.2f}x",
                'confidence': f"{analysis.confidence*100:.1f}%",
                'optimal_strategies': analysis.optimal_strategies[:3],
                'last_analysis': analysis.analysis_time.strftime("%H:%M:%S")
            }
            
        except Exception as e:
            print(f"❌ Volatility summary error: {e}")
            return {'error': str(e)}
    
    def get_volatility_forecast(self, hours_ahead: int = 4) -> List[Dict]:
        """
        🔮 คาดการณ์ความผันผวนในอนาคต
        
        Args:
            hours_ahead: จำนวนชั่วโมงที่ต้องการคาดการณ์
            
        Returns:
            รายการการคาดการณ์
        """
        try:
            if not self.last_analysis:
                return []
            
            forecasts = []
            current_analysis = self.last_analysis
            
            for hour in range(1, hours_ahead + 1):
                # ใช้ simple persistence model กับการปรับแต่ง
                forecast_time = datetime.now() + timedelta(hours=hour)
                
                # ปรับระดับความผันผวนตามเวลา (เซสชั่นการเทรด)
                hour_of_day = forecast_time.hour
                
                # ปรับตามเซสชั่น (GMT+7)
                if 22 <= hour_of_day or hour_of_day <= 8:  # Asian session
                    vol_multiplier = 0.7
                    expected_level = "low"
                elif 15 <= hour_of_day <= 24:  # London session
                    vol_multiplier = 1.3
                    expected_level = "high"
                elif 20 <= hour_of_day <= 5:  # NY session
                    vol_multiplier = 1.4
                    expected_level = "high"
                else:  # Quiet period
                    vol_multiplier = 0.5
                    expected_level = "low"
                
                # ปรับตามแนวโน้มปัจจุบัน
                if current_analysis.trend == VolatilityTrend.INCREASING:
                    vol_multiplier *= 1.1
                elif current_analysis.trend == VolatilityTrend.DECREASING:
                    vol_multiplier *= 0.9
                
                # คำนวณ expected ATR
                expected_atr = current_analysis.measurements.atr_pips * vol_multiplier
                
                # จำแนกระดับ
                if expected_atr < 15:
                    expected_level = "low"
                elif expected_atr < 30:
                    expected_level = "moderate"
                else:
                    expected_level = "high"
                
                forecast = {
                    'hour': hour,
                    'time': forecast_time.strftime("%H:%M"),
                    'expected_level': expected_level,
                    'expected_atr_pips': f"{expected_atr:.1f}",
                    'volatility_multiplier': f"{vol_multiplier:.2f}",
                    'recommended_strategies': self._get_strategies_for_level(expected_level)
                }
                
                forecasts.append(forecast)
            
            return forecasts
            
        except Exception as e:
            print(f"❌ Volatility forecast error: {e}")
            return []
    
    def _get_strategies_for_level(self, level_str: str) -> List[str]:
        """ดึงกลยุทธ์ที่เหมาะสมสำหรับระดับความผันผวน"""
        strategy_map = {
            'low': ['mean_reversion', 'scalping', 'range_trading'],
            'moderate': ['trend_following', 'grid_intelligent', 'breakout'],
            'high': ['momentum', 'trend_following', 'volatility_breakout']
        }
        return strategy_map.get(level_str, ['mean_reversion'])
    
    def compare_volatility_regimes(self, lookback_hours: int = 24) -> Dict:
        """
        📊 เปรียบเทียบ volatility regimes ย้อนหลัง
        
        Args:
            lookback_hours: จำนวนชั่วโมงที่ต้องการเปรียบเทียบ
            
        Returns:
            การเปรียบเทียบ regimes
        """
        try:
            if not self.regime_history:
                return {'status': 'No regime history available'}
            
            # หาข้อมูลย้อนหลัง
            cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
            recent_regimes = [
                r for r in self.regime_history 
                if r['timestamp'] >= cutoff_time
            ]
            
            if not recent_regimes:
                return {'status': 'No recent regime data'}
            
            # นับ regimes
            regime_counts = {}
            level_counts = {}
            
            for record in recent_regimes:
                regime = record['regime']
                level = record['level']
                
                regime_counts[regime] = regime_counts.get(regime, 0) + 1
                level_counts[level] = level_counts.get(level, 0) + 1
            
            # หา regime ที่พบบ่อยที่สุด
            most_common_regime = max(regime_counts, key=regime_counts.get) if regime_counts else 'normal'
            most_common_level = max(level_counts, key=level_counts.get) if level_counts else 'moderate'
            
            # คำนวณเสถียรภาพ
            total_records = len(recent_regimes)
            regime_stability = max(regime_counts.values()) / total_records if total_records > 0 else 0
            
            return {
                'lookback_hours': lookback_hours,
                'total_observations': total_records,
                'regime_distribution': regime_counts,
                'level_distribution': level_counts,
                'most_common_regime': most_common_regime,
                'most_common_level': most_common_level,
                'regime_stability': f"{regime_stability*100:.1f}%",
                'regime_changes': self.regime_changes,
                'analysis_count': self.analysis_count
            }
            
        except Exception as e:
            print(f"❌ Regime comparison error: {e}")
            return {'error': str(e)}
    
    def get_trading_recommendations(self) -> Dict:
        """
        💡 ดึงคำแนะนำการเทรดตามความผันผวนปัจจุบัน
        
        Returns:
            คำแนะนำครอบคลุม
        """
        try:
            if not self.last_analysis:
                return {'status': 'No analysis available for recommendations'}
            
            analysis = self.last_analysis
            
            # คำแนะนำเชิงกลยุทธ์
            strategy_recommendations = {
                'primary_strategies': analysis.optimal_strategies[:2],
                'secondary_strategies': analysis.optimal_strategies[2:4],
                'avoid_strategies': self._get_strategies_to_avoid(analysis)
            }
            
            # คำแนะนำ Risk Management
            risk_recommendations = {
                'position_size_adjustment': f"{analysis.position_sizing_multiplier:.2f}x",
                'risk_per_trade_adjustment': f"{analysis.risk_adjustment:.2f}x",
                'max_positions_recommended': self._get_max_positions_recommendation(analysis),
                'stop_loss_adjustment': self._get_stop_loss_recommendation(analysis)
            }
            
            # คำแนะนำ Entry/Exit
            entry_recommendations = {
                'entry_timing': self._get_entry_timing_advice(analysis),
                'exit_timing': self._get_exit_timing_advice(analysis),
                'breakout_watch': f"{analysis.breakout_probability*100:.1f}% probability",
                'range_expectation': f"{analysis.expected_range_next_hour[0]:.2f} - {analysis.expected_range_next_hour[1]:.2f}"
            }
            
            # คำแนะนำทั่วไป
            general_advice = self._get_general_advice(analysis)
            
            return {
                'analysis_timestamp': analysis.analysis_time.strftime("%Y-%m-%d %H:%M:%S"),
                'current_volatility': analysis.current_level.value,
                'volatility_regime': analysis.regime.value,
                'confidence_level': f"{analysis.confidence*100:.1f}%",
                'strategy_recommendations': strategy_recommendations,
                'risk_management': risk_recommendations,
                'entry_exit_guidance': entry_recommendations,
                'general_advice': general_advice
            }
            
        except Exception as e:
            print(f"❌ Trading recommendations error: {e}")
            return {'error': str(e)}
    
    def _get_strategies_to_avoid(self, analysis: VolatilityAnalysis) -> List[str]:
        """ดึงกลยุทธ์ที่ควรหลีกเลี่ยง"""
        avoid_strategies = []
        
        if analysis.current_level == VolatilityLevel.EXTREMELY_HIGH:
            avoid_strategies.extend(['scalping', 'range_trading', 'mean_reversion'])
        elif analysis.current_level == VolatilityLevel.EXTREMELY_LOW:
            avoid_strategies.extend(['momentum', 'breakout', 'trend_following'])
        
        if analysis.regime == VolatilityRegime.CRISIS:
            avoid_strategies.extend(['carry_trade', 'grid_trading'])
        elif analysis.regime == VolatilityRegime.CALM:
            avoid_strategies.extend(['volatility_trading', 'momentum'])
        
        return list(set(avoid_strategies))  # ลบ duplicates
    
    def _get_max_positions_recommendation(self, analysis: VolatilityAnalysis) -> int:
        """แนะนำจำนวน positions สูงสุด"""
        base_positions = 5
        
        if analysis.regime == VolatilityRegime.CRISIS:
            return max(1, int(base_positions * 0.4))
        elif analysis.regime == VolatilityRegime.TURBULENT:
            return max(2, int(base_positions * 0.6))
        elif analysis.regime == VolatilityRegime.CALM:
            return int(base_positions * 1.5)
        else:
            return base_positions
    
    def _get_stop_loss_recommendation(self, analysis: VolatilityAnalysis) -> str:
        """แนะนำการปรับ Stop Loss"""
        atr_pips = analysis.measurements.atr_pips
        
        if analysis.current_level == VolatilityLevel.EXTREMELY_HIGH:
            return f"Widen stops to {atr_pips * 2.5:.1f} pips (2.5x ATR)"
        elif analysis.current_level == VolatilityLevel.HIGH:
            return f"Widen stops to {atr_pips * 2:.1f} pips (2x ATR)"
        elif analysis.current_level == VolatilityLevel.LOW:
            return f"Tighten stops to {atr_pips * 1.2:.1f} pips (1.2x ATR)"
        else:
            return f"Standard stops at {atr_pips * 1.5:.1f} pips (1.5x ATR)"
    
    def _get_entry_timing_advice(self, analysis: VolatilityAnalysis) -> str:
        """แนะนำ timing การ entry"""
        if analysis.trend == VolatilityTrend.INCREASING:
            return "Wait for volatility expansion confirmation before entering"
        elif analysis.trend == VolatilityTrend.DECREASING:
            return "Good time for range-based entries as volatility contracts"
        elif analysis.breakout_probability > 0.7:
            return "High breakout probability - consider breakout strategies"
        else:
            return "Standard entry timing - follow your strategy signals"
    
    def _get_exit_timing_advice(self, analysis: VolatilityAnalysis) -> str:
        """แนะนำ timing การ exit"""
        if analysis.regime == VolatilityRegime.CRISIS:
            return "Consider quick exits - market regime is unstable"
        elif analysis.current_level == VolatilityLevel.EXTREMELY_HIGH:
            return "Take profits quickly in high volatility environment"
        elif analysis.current_level == VolatilityLevel.LOW:
            return "Can hold positions longer in low volatility conditions"
        else:
            return "Standard exit timing based on your strategy"
    
    def _get_general_advice(self, analysis: VolatilityAnalysis) -> List[str]:
        """แนะนำทั่วไป"""
        advice = []
        
        if analysis.confidence < 0.6:
            advice.append("⚠️ Low confidence analysis - trade with extra caution")
        
        if analysis.regime == VolatilityRegime.CRISIS:
            advice.append("🚨 Crisis regime detected - focus on capital preservation")
        
        if analysis.breakout_probability > 0.8:
            advice.append("📈 High breakout probability - prepare for significant moves")
        
        if analysis.current_level == VolatilityLevel.EXTREMELY_LOW:
            advice.append("😴 Very quiet market - consider lower position sizes")
        
        if analysis.trend == VolatilityTrend.VOLATILE:
            advice.append("🌪️ Volatile volatility trend - expect unexpected moves")
        
        return advice

def main():
    """Test the Volatility Engine"""
    print("🧪 Testing Volatility Engine...")
    
    # Sample configuration
    config = {
        'atr_period': 14,
        'volatility_lookback': 100,
        'regime_lookback': 50,
        'extremely_low_threshold': 10,
        'low_threshold': 20,
        'moderate_threshold': 40,
        'high_threshold': 70,
        'bb_period': 20,
        'bb_std': 2.0
    }
    
    # Initialize volatility engine
    vol_engine = VolatilityEngine(config)
    
    # Generate sample market data
    dates = pd.date_range(start='2024-01-01', periods=200, freq='5min')
    np.random.seed(42)
    
    # Create market data with varying volatility
    base_price = 2000
    volatility = np.random.uniform(0.5, 2.0, 200)  # Varying volatility
    prices = [base_price]
    
    for i in range(1, 200):
        change = np.random.normal(0, volatility[i] * 0.1)
        new_price = prices[-1] * (1 + change/100)
        prices.append(new_price)
    
    prices = np.array(prices)
    
    # Create OHLCV data
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices * (1 + np.random.uniform(0, 0.002, 200)),
        'low': prices * (1 - np.random.uniform(0, 0.002, 200)),
        'close': prices + np.random.normal(0, 0.5, 200),
        'volume': np.random.randint(100, 1000, 200)
    })
    
    # Test volatility analysis
    analysis = vol_engine.analyze_volatility(sample_data)
    print(f"\n📊 Volatility Analysis:")
    print(f"   Current Level: {analysis.current_level.value}")
    print(f"   Trend: {analysis.trend.value}")
    print(f"   Regime: {analysis.regime.value}")
    print(f"   ATR (pips): {analysis.measurements.atr_pips:.1f}")
    print(f"   Breakout Probability: {analysis.breakout_probability*100:.1f}%")
    print(f"   Risk Adjustment: {analysis.risk_adjustment:.2f}x")
    print(f"   Position Multiplier: {analysis.position_sizing_multiplier:.2f}x")
    print(f"   Confidence: {analysis.confidence*100:.1f}%")
    
    # Test volatility summary
    summary = vol_engine.get_volatility_summary()
    print(f"\n📋 Volatility Summary:")
    for key, value in summary.items():
        if key != 'optimal_strategies':
            print(f"   {key}: {value}")
    
    # Test forecast
    forecasts = vol_engine.get_volatility_forecast(4)
    print(f"\n🔮 Volatility Forecast:")
    for forecast in forecasts:
        print(f"   Hour {forecast['hour']} ({forecast['time']}): {forecast['expected_level']} "
                f"({forecast['expected_atr_pips']} pips)")
    
    # Test trading recommendations
    recommendations = vol_engine.get_trading_recommendations()
    print(f"\n💡 Trading Recommendations:")
    print(f"   Current Volatility: {recommendations['current_volatility']}")
    print(f"   Primary Strategies: {', '.join(recommendations['strategy_recommendations']['primary_strategies'])}")
    print(f"   Position Size Adjustment: {recommendations['risk_management']['position_size_adjustment']}")
    print(f"   General Advice: {len(recommendations['general_advice'])} recommendations")
    
    print("\n✅ Volatility Engine test completed")

if __name__ == "__main__":
   main()