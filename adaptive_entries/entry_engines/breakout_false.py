#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FALSE BREAKOUT ENGINE - False Breakout Exploitation Strategy
==========================================================
Engine สำหรับตรวจจับและใช้ประโยชน์จาก False Breakout
เป็น Entry Strategy ที่เชี่ยวชาญในการหา False Breakout Opportunities

Key Features:
- Support/resistance level detection
- Volume analysis for breakout validation
- Multi-timeframe confirmation system
- High probability false breakout identification
- Dynamic entry timing optimization
- Integration with signal_generator

เชื่อมต่อไปยัง:
- adaptive_entries/signal_generator.py (ส่ง signals)
- market_intelligence/market_analyzer.py (ข้อมูล market)
- market_intelligence/volatility_engine.py (ข้อมูล volatility)
- config/trading_params.py (parameters)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import ta
from collections import deque

# เชื่อมต่อ internal modules
from config.settings import get_system_settings
from config.trading_params import get_trading_parameters
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class BreakoutType(Enum):
    """ประเภทของ Breakout"""
    SUPPORT_BREAK = "SUPPORT_BREAK"
    RESISTANCE_BREAK = "RESISTANCE_BREAK"
    RANGE_BREAK_UP = "RANGE_BREAK_UP"
    RANGE_BREAK_DOWN = "RANGE_BREAK_DOWN"
    TRENDLINE_BREAK = "TRENDLINE_BREAK"

class BreakoutValidation(Enum):
    """สถานะการ Validate Breakout"""
    VALID = "VALID"
    FALSE = "FALSE"
    PENDING = "PENDING"
    UNCERTAIN = "UNCERTAIN"

@dataclass
class SupportResistanceLevel:
    """ข้อมูล Support/Resistance Level"""
    price: float
    strength: float  # 0-100
    touches: int
    first_touch_time: datetime
    last_touch_time: datetime
    level_type: str  # 'support', 'resistance', 'pivot'
    timeframe: str
    is_active: bool = True

@dataclass
class BreakoutSignal:
    """ข้อมูล Breakout Signal"""
    signal_id: str
    timestamp: datetime
    breakout_type: BreakoutType
    entry_price: float
    direction: int  # 1 for BUY, -1 for SELL
    level_broken: SupportResistanceLevel
    validation_status: BreakoutValidation
    confidence: float  # 0-100
    volume_ratio: float
    price_penetration: float
    time_to_validate: int  # minutes
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float

class FalseBreakoutEngine:
    """
    🎯 False Breakout Exploitation Engine
    
    Engine สำหรับตรวจจับและใช้ประโยชน์จาก False Breakout
    ใช้การวิเคราะห์หลายมิติเพื่อหา High Probability False Breakout
    """
    
    def __init__(self):
        self.logger = setup_component_logger("FalseBreakoutEngine")
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Configuration
        self.config = {
            # Level Detection
            'lookback_periods': {
                'M1': 100,
                'M5': 200,
                'M15': 150,
                'H1': 100
            },
            'min_level_strength': 60.0,
            'min_touches': 3,
            'level_proximity_pips': 5.0,
            
            # Breakout Detection
            'breakout_threshold_pips': 3.0,
            'min_breakout_volume_ratio': 1.5,
            'max_validation_time_minutes': 15,
            
            # False Breakout Criteria
            'false_breakout_retest_pips': 2.0,
            'min_false_signal_confidence': 75.0,
            'volume_decline_threshold': 0.7,
            
            # Entry Settings
            'entry_delay_minutes': 2,
            'max_risk_per_trade': 1.0,  # % of account
            'min_risk_reward_ratio': 2.0
        }
        
        # Data Storage
        self.market_data = {}  # {timeframe: DataFrame}
        self.sr_levels = {}    # {timeframe: List[SupportResistanceLevel]}
        self.active_breakouts = deque(maxlen=50)
        self.signal_history = deque(maxlen=100)
        
        # Analysis State
        self.last_analysis_time = {}
        self.analysis_lock = False
        
        self.logger.info("🎯 เริ่มต้น False Breakout Engine")
    
    def update_market_data(self, timeframe: str, data: pd.DataFrame) -> None:
        """อัพเดทข้อมูล Market"""
        try:
            if data is not None and not data.empty:
                self.market_data[timeframe] = data.copy()
                self.last_analysis_time[timeframe] = datetime.now()
                
                # Update S/R levels for this timeframe
                self._update_sr_levels(timeframe)
                
                self.logger.debug(f"📊 อัพเดท Market Data: {timeframe} - {len(data)} bars")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Market Data: {e}")
    
    def _update_sr_levels(self, timeframe: str) -> None:
        """อัพเดท Support/Resistance Levels"""
        try:
            if timeframe not in self.market_data:
                return
            
            data = self.market_data[timeframe]
            if data.empty:
                return
            
            # Detect new levels
            new_levels = self._detect_sr_levels(data, timeframe)
            
            # Update existing levels and add new ones
            if timeframe not in self.sr_levels:
                self.sr_levels[timeframe] = []
            
            # Merge with existing levels
            self.sr_levels[timeframe] = self._merge_sr_levels(
                self.sr_levels[timeframe], new_levels
            )
            
            # Clean up old/invalid levels
            self._cleanup_sr_levels(timeframe)
            
            self.logger.debug(f"🎯 อัพเดท S/R Levels {timeframe}: {len(self.sr_levels[timeframe])} levels")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท S/R Levels: {e}")
    
    def _detect_sr_levels(self, data: pd.DataFrame, timeframe: str) -> List[SupportResistanceLevel]:
        """ตรวจจับ Support/Resistance Levels"""
        try:
            levels = []
            lookback = self.config['lookback_periods'].get(timeframe, 100)
            
            if len(data) < lookback:
                return levels
            
            # Use recent data for analysis
            recent_data = data.tail(lookback).copy()
            
            # Find pivot highs and lows
            pivot_highs = self._find_pivot_points(recent_data['high'], order=5)
            pivot_lows = self._find_pivot_points(recent_data['low'], order=5, find_peaks=False)
            
            # Process resistance levels (pivot highs)
            for idx in pivot_highs:
                if idx < len(recent_data):
                    price = recent_data.iloc[idx]['high']
                    timestamp = recent_data.index[idx]
                    
                    # Calculate level strength
                    touches, strength = self._calculate_level_strength(
                        recent_data, price, 'resistance'
                    )
                    
                    if touches >= self.config['min_touches'] and strength >= self.config['min_level_strength']:
                        level = SupportResistanceLevel(
                            price=price,
                            strength=strength,
                            touches=touches,
                            first_touch_time=timestamp,
                            last_touch_time=timestamp,
                            level_type='resistance',
                            timeframe=timeframe
                        )
                        levels.append(level)
            
            # Process support levels (pivot lows)
            for idx in pivot_lows:
                if idx < len(recent_data):
                    price = recent_data.iloc[idx]['low']
                    timestamp = recent_data.index[idx]
                    
                    # Calculate level strength
                    touches, strength = self._calculate_level_strength(
                        recent_data, price, 'support'
                    )
                    
                    if touches >= self.config['min_touches'] and strength >= self.config['min_level_strength']:
                        level = SupportResistanceLevel(
                            price=price,
                            strength=strength,
                            touches=touches,
                            first_touch_time=timestamp,
                            last_touch_time=timestamp,
                            level_type='support',
                            timeframe=timeframe
                        )
                        levels.append(level)
            
            return levels
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ S/R Levels: {e}")
            return []
    
    def _find_pivot_points(self, series: pd.Series, order: int = 5, find_peaks: bool = True) -> List[int]:
        """หา Pivot Points ใน Price Series"""
        try:
            if find_peaks:
                # Find peaks (resistance)
                from scipy.signal import find_peaks
                peaks, _ = find_peaks(series.values, distance=order)
                return peaks.tolist()
            else:
                # Find troughs (support) by inverting the series
                from scipy.signal import find_peaks
                troughs, _ = find_peaks(-series.values, distance=order)
                return troughs.tolist()
                
        except ImportError:
            # Fallback method if scipy is not available
            pivots = []
            for i in range(order, len(series) - order):
                if find_peaks:
                    # Check if it's a local maximum
                    is_pivot = all(series.iloc[i] >= series.iloc[j] for j in range(i-order, i+order+1) if j != i)
                else:
                    # Check if it's a local minimum
                    is_pivot = all(series.iloc[i] <= series.iloc[j] for j in range(i-order, i+order+1) if j != i)
                
                if is_pivot:
                    pivots.append(i)
            
            return pivots
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการหา Pivot Points: {e}")
            return []
    
    def _calculate_level_strength(self, data: pd.DataFrame, price: float, level_type: str) -> Tuple[int, float]:
        """คำนวณความแข็งแกร่งของ Level"""
        try:
            proximity_pips = self.config['level_proximity_pips']
            pip_value = 0.0001  # สำหรับ XAUUSD ใช้ 0.01
            if 'XAU' in self.settings.symbol:
                pip_value = 0.01
            
            proximity = proximity_pips * pip_value
            touches = 0
            total_volume = 0
            
            for _, row in data.iterrows():
                if level_type == 'resistance':
                    # Check if price touched resistance
                    if abs(row['high'] - price) <= proximity:
                        touches += 1
                        total_volume += row.get('volume', 1)
                elif level_type == 'support':
                    # Check if price touched support
                    if abs(row['low'] - price) <= proximity:
                        touches += 1
                        total_volume += row.get('volume', 1)
            
            # Calculate strength based on touches and volume
            base_strength = min(touches * 15, 85)  # Max 85 from touches
            volume_boost = min(total_volume / len(data) * 10, 15)  # Max 15 from volume
            
            strength = base_strength + volume_boost
            
            return touches, min(strength, 100.0)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Level Strength: {e}")
            return 0, 0.0
    
    def _merge_sr_levels(self, existing_levels: List[SupportResistanceLevel], 
                        new_levels: List[SupportResistanceLevel]) -> List[SupportResistanceLevel]:
        """รวม Support/Resistance Levels"""
        try:
            merged_levels = existing_levels.copy()
            proximity_pips = self.config['level_proximity_pips']
            pip_value = 0.01 if 'XAU' in self.settings.symbol else 0.0001
            proximity = proximity_pips * pip_value
            
            for new_level in new_levels:
                # Check if similar level already exists
                similar_found = False
                
                for i, existing_level in enumerate(merged_levels):
                    if (existing_level.level_type == new_level.level_type and
                        existing_level.timeframe == new_level.timeframe and
                        abs(existing_level.price - new_level.price) <= proximity):
                        
                        # Update existing level with new information
                        merged_levels[i].touches = max(existing_level.touches, new_level.touches)
                        merged_levels[i].strength = max(existing_level.strength, new_level.strength)
                        merged_levels[i].last_touch_time = max(existing_level.last_touch_time, 
                                                             new_level.last_touch_time)
                        similar_found = True
                        break
                
                if not similar_found:
                    merged_levels.append(new_level)
            
            return merged_levels
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการรวม S/R Levels: {e}")
            return existing_levels
    
    def _cleanup_sr_levels(self, timeframe: str) -> None:
        """ทำความสะอาด S/R Levels ที่เก่าหรือไม่ใช้แล้ว"""
        try:
            if timeframe not in self.sr_levels:
                return
            
            current_time = datetime.now()
            max_age_hours = 24  # Remove levels older than 24 hours
            
            # Filter out old levels
            self.sr_levels[timeframe] = [
                level for level in self.sr_levels[timeframe]
                if (current_time - level.last_touch_time).total_seconds() < max_age_hours * 3600
                and level.is_active
            ]
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการทำความสะอาด S/R Levels: {e}")
    
    def analyze_breakouts(self) -> List[BreakoutSignal]:
        """วิเคราะห์หา Breakout Opportunities"""
        try:
            if self.analysis_lock:
                return []
            
            self.analysis_lock = True
            signals = []
            
            # Analyze each timeframe
            for timeframe in ['M1', 'M5', 'M15']:
                if timeframe in self.market_data and timeframe in self.sr_levels:
                    timeframe_signals = self._analyze_timeframe_breakouts(timeframe)
                    signals.extend(timeframe_signals)
            
            # Filter and rank signals
            filtered_signals = self._filter_and_rank_signals(signals)
            
            # Update signal history
            for signal in filtered_signals:
                self.signal_history.append(signal)
            
            self.analysis_lock = False
            
            if filtered_signals:
                self.logger.info(f"🎯 พบ False Breakout Signals: {len(filtered_signals)} signals")
            
            return filtered_signals
            
        except Exception as e:
            self.analysis_lock = False
            self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์ Breakouts: {e}")
            return []
    
    def _analyze_timeframe_breakouts(self, timeframe: str) -> List[BreakoutSignal]:
        """วิเคราะห์ Breakouts สำหรับ Timeframe เฉพาะ"""
        try:
            signals = []
            data = self.market_data[timeframe]
            levels = self.sr_levels[timeframe]
            
            if data.empty or not levels:
                return signals
            
            # Get recent bars for analysis
            recent_bars = data.tail(20)
            current_bar = recent_bars.iloc[-1]
            current_price = current_bar['close']
            
            # Check each level for potential breakouts
            for level in levels:
                if not level.is_active:
                    continue
                
                # Detect breakout
                breakout_signal = self._detect_level_breakout(
                    recent_bars, level, timeframe
                )
                
                if breakout_signal:
                    # Validate if it's a false breakout
                    validation_result = self._validate_false_breakout(
                        recent_bars, breakout_signal, level
                    )
                    
                    if validation_result['is_false_breakout']:
                        breakout_signal.validation_status = BreakoutValidation.FALSE
                        breakout_signal.confidence = validation_result['confidence']
                        signals.append(breakout_signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์ Timeframe Breakouts: {e}")
            return []
    
    def _detect_level_breakout(self, data: pd.DataFrame, level: SupportResistanceLevel, 
                              timeframe: str) -> Optional[BreakoutSignal]:
        """ตรวจจับการ Breakout ของ Level"""
        try:
            if data.empty:
                return None
            
            current_bar = data.iloc[-1]
            breakout_threshold_pips = self.config['breakout_threshold_pips']
            pip_value = 0.01 if 'XAU' in self.settings.symbol else 0.0001
            breakout_threshold = breakout_threshold_pips * pip_value
            
            # Check for resistance breakout
            if level.level_type == 'resistance':
                if current_bar['high'] > level.price + breakout_threshold:
                    # Price broke above resistance
                    signal = BreakoutSignal(
                        signal_id=f"FB_{timeframe}_{int(datetime.now().timestamp())}",
                        timestamp=datetime.now(),
                        breakout_type=BreakoutType.RESISTANCE_BREAK,
                        entry_price=level.price,  # Entry back at the level
                        direction=-1,  # SELL (expecting false breakout)
                        level_broken=level,
                        validation_status=BreakoutValidation.PENDING,
                        confidence=0.0,
                        volume_ratio=self._calculate_volume_ratio(data),
                        price_penetration=current_bar['high'] - level.price,
                        time_to_validate=self.config['max_validation_time_minutes'],
                        stop_loss=0.0,  # Will be calculated later
                        take_profit=0.0,  # Will be calculated later
                        risk_reward_ratio=0.0  # Will be calculated later
                    )
                    return signal
            
            # Check for support breakout
            elif level.level_type == 'support':
                if current_bar['low'] < level.price - breakout_threshold:
                    # Price broke below support
                    signal = BreakoutSignal(
                        signal_id=f"FB_{timeframe}_{int(datetime.now().timestamp())}",
                        timestamp=datetime.now(),
                        breakout_type=BreakoutType.SUPPORT_BREAK,
                        entry_price=level.price,  # Entry back at the level
                        direction=1,  # BUY (expecting false breakout)
                        level_broken=level,
                        validation_status=BreakoutValidation.PENDING,
                        confidence=0.0,
                        volume_ratio=self._calculate_volume_ratio(data),
                        price_penetration=level.price - current_bar['low'],
                        time_to_validate=self.config['max_validation_time_minutes'],
                        stop_loss=0.0,  # Will be calculated later
                        take_profit=0.0,  # Will be calculated later
                        risk_reward_ratio=0.0  # Will be calculated later
                    )
                    return signal
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจจับ Level Breakout: {e}")
            return None
    
    def _calculate_volume_ratio(self, data: pd.DataFrame) -> float:
        """คำนวณ Volume Ratio"""
        try:
            if 'volume' not in data.columns or len(data) < 10:
                return 1.0
            
            recent_volume = data.tail(5)['volume'].mean()
            avg_volume = data.tail(20)['volume'].mean()
            
            if avg_volume > 0:
                return recent_volume / avg_volume
            
            return 1.0
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Volume Ratio: {e}")
            return 1.0
    
    def _validate_false_breakout(self, data: pd.DataFrame, signal: BreakoutSignal, 
                                level: SupportResistanceLevel) -> Dict[str, Any]:
        """ตรวจสอบว่าเป็น False Breakout หรือไม่"""
        try:
            validation_result = {
                'is_false_breakout': False,
                'confidence': 0.0,
                'reasons': []
            }
            
            current_bar = data.iloc[-1]
            retest_pips = self.config['false_breakout_retest_pips']
            pip_value = 0.01 if 'XAU' in self.settings.symbol else 0.0001
            retest_threshold = retest_pips * pip_value
            
            confidence_factors = []
            
            # Factor 1: Price has returned to level vicinity
            if signal.breakout_type == BreakoutType.RESISTANCE_BREAK:
                if current_bar['low'] <= level.price + retest_threshold:
                    confidence_factors.append(('price_return', 25))
                    validation_result['reasons'].append('Price returned to resistance level')
            
            elif signal.breakout_type == BreakoutType.SUPPORT_BREAK:
                if current_bar['high'] >= level.price - retest_threshold:
                    confidence_factors.append(('price_return', 25))
                    validation_result['reasons'].append('Price returned to support level')
            
            # Factor 2: Volume analysis
            if signal.volume_ratio < self.config['min_breakout_volume_ratio']:
                confidence_factors.append(('low_volume', 20))
                validation_result['reasons'].append('Breakout on low volume')
            
            # Factor 3: Level strength
            if level.strength >= 80:
                confidence_factors.append(('strong_level', 20))
                validation_result['reasons'].append('Breaking strong S/R level')
            
            # Factor 4: Market context (trend, volatility)
            market_context = self._analyze_market_context(data)
            if market_context['supports_false_breakout']:
                confidence_factors.append(('market_context', 15))
                validation_result['reasons'].append('Market context supports false breakout')
            
            # Factor 5: Time factor
            bars_since_breakout = self._count_bars_since_breakout(data, signal)
            if 2 <= bars_since_breakout <= 10:  # Optimal timing
                confidence_factors.append(('timing', 10))
                validation_result['reasons'].append('Optimal timing for false breakout')
            
            # Factor 6: Previous false breakouts at this level
            if level.touches >= 5:  # Level has been tested many times
                confidence_factors.append(('multiple_tests', 10))
                validation_result['reasons'].append('Level tested multiple times')
            
            # Calculate total confidence
            total_confidence = sum(score for _, score in confidence_factors)
            
            # Determine if it's a valid false breakout signal
            min_confidence = self.config['min_false_signal_confidence']
            if total_confidence >= min_confidence:
                validation_result['is_false_breakout'] = True
                validation_result['confidence'] = min(total_confidence, 100.0)
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจสอบ False Breakout: {e}")
            return {'is_false_breakout': False, 'confidence': 0.0, 'reasons': []}
    
    def _analyze_market_context(self, data: pd.DataFrame) -> Dict[str, Any]:
        """วิเคราะห์บริบทของตลาด"""
        try:
            context = {
                'supports_false_breakout': False,
                'trend_strength': 0.0,
                'volatility_level': 'normal'
            }
            
            if len(data) < 20:
                return context
            
            # Calculate trend strength using ADX
            if len(data) >= 14:
                try:
                    adx = ta.trend.ADXIndicator(data['high'], data['low'], data['close'], window=14)
                    current_adx = adx.adx().iloc[-1]
                    context['trend_strength'] = current_adx
                    
                    # Weak trend supports false breakouts
                    if current_adx < 25:
                        context['supports_false_breakout'] = True
                        
                except Exception:
                    pass
            
            # Calculate volatility
            if len(data) >= 14:
                try:
                    atr = ta.volatility.AverageTrueRange(data['high'], data['low'], data['close'], window=14)
                    current_atr = atr.average_true_range().iloc[-1]
                    avg_atr = atr.average_true_range().tail(50).mean()
                    
                    if current_atr < avg_atr * 0.8:
                        context['volatility_level'] = 'low'
                        context['supports_false_breakout'] = True
                    elif current_atr > avg_atr * 1.2:
                        context['volatility_level'] = 'high'
                        
                except Exception:
                    pass
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์ Market Context: {e}")
            return {'supports_false_breakout': False, 'trend_strength': 0.0, 'volatility_level': 'normal'}
    
    def _count_bars_since_breakout(self, data: pd.DataFrame, signal: BreakoutSignal) -> int:
        """นับจำนวน Bars ตั้งแต่ Breakout"""
        try:
            # For simplicity, assume breakout happened 1-3 bars ago
            # In real implementation, this would track actual breakout timing
            return 2
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการนับ Bars Since Breakout: {e}")
            return 0
    
    def _filter_and_rank_signals(self, signals: List[BreakoutSignal]) -> List[BreakoutSignal]:
        """Filter และจัดอันดับ Signals"""
        try:
            if not signals:
                return []
            
            # Filter by minimum confidence
            min_confidence = self.config['min_false_signal_confidence']
            filtered_signals = [
                signal for signal in signals 
                if signal.confidence >= min_confidence
            ]
            
            # Calculate entry parameters for each signal
            for signal in filtered_signals:
                self._calculate_entry_parameters(signal)
            
            # Filter by risk-reward ratio
            min_rr = self.config['min_risk_reward_ratio']
            filtered_signals = [
                signal for signal in filtered_signals
                if signal.risk_reward_ratio >= min_rr
            ]
            
            # Sort by confidence (highest first)
            filtered_signals.sort(key=lambda x: x.confidence, reverse=True)
            
            # Limit to top signals to avoid over-trading
            max_signals = 3
            return filtered_signals[:max_signals]
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการ Filter และ Rank Signals: {e}")
            return []
    
    def _calculate_entry_parameters(self, signal: BreakoutSignal) -> None:
        """คำนวณ Entry Parameters"""
        try:
            level_price = signal.level_broken.price
            pip_value = 0.01 if 'XAU' in self.settings.symbol else 0.0001
            
            # Set entry price at the level
            signal.entry_price = level_price
            
            # Calculate stop loss
            stop_distance_pips = 15  # Standard stop distance
            stop_distance = stop_distance_pips * pip_value
            
            if signal.direction == 1:  # BUY
                signal.stop_loss = signal.entry_price - stop_distance
            else:  # SELL
                signal.stop_loss = signal.entry_price + stop_distance
            
            # Calculate take profit
            take_profit_distance = stop_distance * 2.5  # 2.5:1 R:R
            
            if signal.direction == 1:  # BUY
                signal.take_profit = signal.entry_price + take_profit_distance
            else:  # SELL
                signal.take_profit = signal.entry_price - take_profit_distance
            
            # Calculate risk-reward ratio
            risk = abs(signal.entry_price - signal.stop_loss)
            reward = abs(signal.take_profit - signal.entry_price)
            
            if risk > 0:
                signal.risk_reward_ratio = reward / risk
            else:
                signal.risk_reward_ratio = 0.0
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Entry Parameters: {e}")

    def get_signal_summary(self) -> Dict[str, Any]:
        """ดึงสรุปข้อมูล Signals"""
        try:
            recent_signals = list(self.signal_history)[-20:]  # Last 20 signals
            
            summary = {
                'total_signals': len(self.signal_history),
                'recent_signals': len(recent_signals),
                'active_levels': {
                    timeframe: len([l for l in levels if l.is_active])
                    for timeframe, levels in self.sr_levels.items()
                },
                'average_confidence': 0.0,
                'signal_types': {
                    'resistance_breaks': 0,
                    'support_breaks': 0
                },
                'last_signal_time': None
            }
            
            if recent_signals:
                # Calculate average confidence
                summary['average_confidence'] = sum(s.confidence for s in recent_signals) / len(recent_signals)
                
                # Count signal types
                for signal in recent_signals:
                    if signal.breakout_type == BreakoutType.RESISTANCE_BREAK:
                        summary['signal_types']['resistance_breaks'] += 1
                    elif signal.breakout_type == BreakoutType.SUPPORT_BREAK:
                        summary['signal_types']['support_breaks'] += 1
                
                # Last signal time
                summary['last_signal_time'] = recent_signals[-1].timestamp
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงสรุป Signals: {e}")
            return {}
    
    def get_active_levels(self, timeframe: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """ดึงข้อมูล Active S/R Levels"""
        try:
            if timeframe:
                timeframes = [timeframe] if timeframe in self.sr_levels else []
            else:
                timeframes = list(self.sr_levels.keys())
            
            levels_data = {}
            
            for tf in timeframes:
                levels = self.sr_levels[tf]
                active_levels = [l for l in levels if l.is_active]
                
                levels_data[tf] = [
                    {
                        'price': level.price,
                        'type': level.level_type,
                        'strength': level.strength,
                        'touches': level.touches,
                        'age_hours': (datetime.now() - level.first_touch_time).total_seconds() / 3600,
                        'last_touch': level.last_touch_time.isoformat()
                    }
                    for level in active_levels
                ]
            
            return levels_data
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึง Active Levels: {e}")
            return {}
    
    def validate_signal_performance(self, signal_id: str, outcome: str, pnl: float) -> None:
        """บันทึกผลลัพธ์ของ Signal"""
        try:
            # Find the signal in history
            signal = next((s for s in self.signal_history if s.signal_id == signal_id), None)
            
            if signal:
                # Store performance data (would be in database in real implementation)
                performance_data = {
                    'signal_id': signal_id,
                    'outcome': outcome,  # 'win', 'loss', 'breakeven'
                    'pnl': pnl,
                    'confidence': signal.confidence,
                    'entry_price': signal.entry_price,
                    'direction': signal.direction,
                    'timestamp': datetime.now()
                }
                
                self.logger.info(f"📊 บันทึกผลลัพธ์ Signal {signal_id}: {outcome} - P&L: ${pnl:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการบันทึกผลลัพธ์ Signal: {e}")
    
    def cleanup_old_data(self) -> None:
        """ทำความสะอาดข้อมูลเก่า"""
        try:
            current_time = datetime.now()
            
            # Clean up old market data (keep last 1000 bars per timeframe)
            for timeframe in self.market_data:
                if len(self.market_data[timeframe]) > 1000:
                    self.market_data[timeframe] = self.market_data[timeframe].tail(1000)
            
            # Clean up old levels
            for timeframe in self.sr_levels:
                self._cleanup_sr_levels(timeframe)
            
            # Clean up old breakouts
            max_age_hours = 6
            self.active_breakouts = deque([
                breakout for breakout in self.active_breakouts
                if (current_time - breakout.timestamp).total_seconds() < max_age_hours * 3600
            ], maxlen=50)
            
            self.logger.debug("🧹 ทำความสะอาดข้อมูลเก่าเสร็จสิ้น")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการทำความสะอาดข้อมูล: {e}")


# Test Functions
def test_false_breakout_engine():
    """ทดสอบ False Breakout Engine"""
    
    # Create test data
    import random
    
    def create_test_data(bars: int = 100) -> pd.DataFrame:
        """สร้างข้อมูลทดสอบ"""
        np.random.seed(42)
        
        # Create price series with support/resistance levels
        base_price = 2020.0
        data = []
        
        for i in range(bars):
            # Add some noise and trend
            noise = np.random.normal(0, 2.0)
            trend = i * 0.1
            
            # Create support at 2020 and resistance at 2040
            if i > 50:  # After bar 50, create false breakout scenario
                if i < 60:
                    price = base_price + trend + noise
                elif i < 65:  # False breakout above resistance
                    price = 2042.0 + np.random.normal(0, 1.0)
                else:  # Return to level
                    price = 2038.0 + np.random.normal(0, 1.5)
            else:
                price = base_price + trend + noise
            
            # Ensure OHLC relationships
            high = price + abs(np.random.normal(0, 1.0))
            low = price - abs(np.random.normal(0, 1.0))
            close = price + np.random.normal(0, 0.5)
            volume = random.randint(50, 200)
            
            data.append({
                'timestamp': datetime.now() - timedelta(minutes=bars-i),
                'open': price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    print("🎯 ทดสอบ False Breakout Engine")
    
    # Create engine
    engine = FalseBreakoutEngine()
    
    # Create test data
    test_data_m1 = create_test_data(100)
    test_data_m5 = create_test_data(80)
    test_data_m15 = create_test_data(60)
    
    print("📊 สร้างข้อมูลทดสอบเสร็จสิ้น")
    
    # Update market data
    engine.update_market_data('M1', test_data_m1)
    engine.update_market_data('M5', test_data_m5)
    engine.update_market_data('M15', test_data_m15)
    
    print("📈 อัพเดทข้อมูลตลาดเสร็จสิ้น")
    
    # Get active levels
    levels = engine.get_active_levels()
    print(f"🎯 S/R Levels ที่ตรวจพบ:")
    for timeframe, tf_levels in levels.items():
        print(f"  {timeframe}: {len(tf_levels)} levels")
        for level in tf_levels[:3]:  # Show first 3 levels
            print(f"    - {level['type']}: {level['price']:.2f} (Strength: {level['strength']:.1f})")
    
    # Analyze breakouts
    signals = engine.analyze_breakouts()
    print(f"\n🔍 False Breakout Signals: {len(signals)}")
    
    for signal in signals:
        print(f"  📊 Signal: {signal.signal_id}")
        print(f"     Type: {signal.breakout_type.value}")
        print(f"     Direction: {'BUY' if signal.direction == 1 else 'SELL'}")
        print(f"     Entry: {signal.entry_price:.2f}")
        print(f"     SL: {signal.stop_loss:.2f}")
        print(f"     TP: {signal.take_profit:.2f}")
        print(f"     R:R: {signal.risk_reward_ratio:.2f}")
        print(f"     Confidence: {signal.confidence:.1f}%")
        print(f"     Volume Ratio: {signal.volume_ratio:.2f}")
        print()
    
    # Get summary
    summary = engine.get_signal_summary()
    print(f"📊 Signal Summary:")
    print(f"  Total Signals: {summary.get('total_signals', 0)}")
    print(f"  Recent Signals: {summary.get('recent_signals', 0)}")
    print(f"  Average Confidence: {summary.get('average_confidence', 0):.1f}%")
    print(f"  Active Levels: {summary.get('active_levels', {})}")
    
    # Test signal validation
    if signals:
        test_signal = signals[0]
        print(f"\n🧪 ทดสอบการบันทึกผลลัพธ์:")
        engine.validate_signal_performance(test_signal.signal_id, 'win', 25.50)
    
    # Cleanup
    engine.cleanup_old_data()
    print("🧹 ทำความสะอาดข้อมูลเสร็จสิ้น")
    
    print("✅ การทดสอบ False Breakout Engine เสร็จสิ้น")


if __name__ == "__main__":
    test_false_breakout_engine()