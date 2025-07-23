#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEWS REACTION ENGINE - News Reaction Trading Strategy
===================================================
Engine สำหรับเทรดโดยใช้ปฏิกิริยาต่อข่าวเศรษฐกิจ
เชี่ยวชาญในการจับจังหวะ News Impact และ Market Reaction

Key Features:
- Economic calendar integration
- Real-time news impact analysis
- Market volatility prediction
- Pre/post news positioning strategies
- Gold-specific economic indicator modeling
- Integration with news_monitor

เชื่อมต่อไปยัง:
- adaptive_entries/signal_generator.py (ส่ง signals)
- market_intelligence/news_monitor.py (ข้อมูล news)
- market_intelligence/volatility_engine.py (ข้อมูล volatility)
- config/trading_params.py (parameters)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import requests
import json
from collections import deque, defaultdict
import time

# เชื่อมต่อ internal modules
from config.settings import get_system_settings
from config.trading_params import get_trading_parameters
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class NewsImpact(Enum):
    """ระดับผลกระทบของข่าว"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class NewsDirection(Enum):
    """ทิศทางของข่าวต่อสกุลเงิน"""
    BULLISH = "BULLISH"    # ดีต่อสกุลเงิน
    BEARISH = "BEARISH"    # แย่ต่อสกุลเงิน
    NEUTRAL = "NEUTRAL"    # เป็นกลาง
    UNKNOWN = "UNKNOWN"    # ไม่ทราบ

class ReactionPhase(Enum):
    """ช่วงของ Market Reaction"""
    PRE_NEWS = "PRE_NEWS"           # ก่อนออกข่าว
    IMMEDIATE = "IMMEDIATE"         # ทันทีหลังออกข่าว (0-5 นาที)
    SHORT_TERM = "SHORT_TERM"       # ระยะสั้น (5-30 นาที)
    MEDIUM_TERM = "MEDIUM_TERM"     # ระยะกลาง (30-120 นาที)
    REVERSAL = "REVERSAL"           # การกลับตัว

@dataclass
class EconomicEvent:
    """ข้อมูลเหตุการณ์เศรษฐกิจ"""
    event_id: str
    title: str
    country: str
    currency: str
    importance: NewsImpact
    scheduled_time: datetime
    actual_value: Optional[float] = None
    forecast_value: Optional[float] = None
    previous_value: Optional[float] = None
    deviation_percent: Optional[float] = None
    market_impact_direction: NewsDirection = NewsDirection.UNKNOWN
    is_released: bool = False
    
    @property
    def surprise_factor(self) -> float:
        """คำนวณ Surprise Factor จากความแตกต่างระหว่าง Actual vs Forecast"""
        if self.actual_value is None or self.forecast_value is None:
            return 0.0
        
        if self.forecast_value == 0:
            return 0.0
        
        return abs((self.actual_value - self.forecast_value) / self.forecast_value) * 100

@dataclass
class NewsReactionSignal:
    """ข้อมูล News Reaction Signal"""
    signal_id: str
    timestamp: datetime
    event: EconomicEvent
    reaction_phase: ReactionPhase
    entry_direction: int  # 1 for BUY, -1 for SELL
    entry_price: float
    confidence: float  # 0-100
    expected_volatility: float
    time_horizon_minutes: int
    stop_loss: float
    take_profit: float
    strategy_type: str  # 'momentum', 'reversal', 'fade', 'breakout'
    market_conditions: Dict[str, Any] = field(default_factory=dict)

class GoldNewsImpactModel:
    """
    โมเดลสำหรับประเมินผลกระทบของข่าวต่อราคาทอง
    """
    
    def __init__(self):
        # Gold-specific news impact weights
        self.impact_weights = {
            # US Economic Indicators
            'NFP': {'weight': 0.9, 'volatility_multiplier': 2.5},
            'CPI': {'weight': 0.95, 'volatility_multiplier': 3.0},
            'Core CPI': {'weight': 0.9, 'volatility_multiplier': 2.8},
            'PPI': {'weight': 0.7, 'volatility_multiplier': 1.8},
            'GDP': {'weight': 0.8, 'volatility_multiplier': 2.0},
            'Unemployment Rate': {'weight': 0.75, 'volatility_multiplier': 1.9},
            'Retail Sales': {'weight': 0.65, 'volatility_multiplier': 1.6},
            
            # Federal Reserve
            'FOMC Rate Decision': {'weight': 1.0, 'volatility_multiplier': 3.5},
            'Fed Chair Speech': {'weight': 0.85, 'volatility_multiplier': 2.2},
            'FOMC Minutes': {'weight': 0.8, 'volatility_multiplier': 2.0},
            'Fed Officials Speech': {'weight': 0.6, 'volatility_multiplier': 1.5},
            
            # Market Sentiment & Risk
            'VIX': {'weight': 0.7, 'volatility_multiplier': 1.8},
            'Dollar Index': {'weight': 0.8, 'volatility_multiplier': 2.0},
            'Treasury Yields': {'weight': 0.75, 'volatility_multiplier': 1.9},
            
            # Geopolitical
            'Geopolitical Events': {'weight': 0.9, 'volatility_multiplier': 2.8},
            'Trade War News': {'weight': 0.8, 'volatility_multiplier': 2.2},
            
            # Global Economic
            'ECB Rate Decision': {'weight': 0.7, 'volatility_multiplier': 1.8},
            'BOJ Rate Decision': {'weight': 0.6, 'volatility_multiplier': 1.5},
            'China GDP': {'weight': 0.7, 'volatility_multiplier': 1.7}
        }
    
    def calculate_gold_impact(self, event: EconomicEvent) -> Dict[str, Any]:
        """คำนวณผลกระทบต่อราคาทอง"""
        impact_data = {
            'direction': NewsDirection.NEUTRAL,
            'magnitude': 0.0,
            'volatility_expectation': 1.0,
            'confidence': 0.0
        }
        
        # Get event weight
        event_weight = self._get_event_weight(event.title)
        if event_weight['weight'] == 0:
            return impact_data
        
        # Calculate magnitude based on surprise factor
        surprise = event.surprise_factor
        magnitude = min(surprise * event_weight['weight'] / 100, 1.0)
        
        # Determine direction based on event type and actual vs forecast
        direction = self._determine_gold_direction(event)
        
        # Calculate volatility expectation
        volatility_exp = event_weight['volatility_multiplier'] * (1 + surprise / 100)
        
        # Calculate confidence based on historical patterns
        confidence = self._calculate_confidence(event, surprise)
        
        impact_data.update({
            'direction': direction,
            'magnitude': magnitude,
            'volatility_expectation': volatility_exp,
            'confidence': confidence
        })
        
        return impact_data
    
    def _get_event_weight(self, event_title: str) -> Dict[str, float]:
        """ดึง Weight ของเหตุการณ์"""
        for key, weight_data in self.impact_weights.items():
            if key.lower() in event_title.lower():
                return weight_data
        
        return {'weight': 0.0, 'volatility_multiplier': 1.0}
    
    def _determine_gold_direction(self, event: EconomicEvent) -> NewsDirection:
        """กำหนดทิศทางผลกระทบต่อทอง"""
        if event.actual_value is None or event.forecast_value is None:
            return NewsDirection.NEUTRAL
        
        actual_vs_forecast = event.actual_value - event.forecast_value
        
        # Gold typically moves inverse to USD strength indicators
        usd_positive_indicators = [
            'NFP', 'GDP', 'Retail Sales', 'CPI', 'Core CPI'
        ]
        
        usd_negative_indicators = [
            'Unemployment Rate', 'Initial Jobless Claims'
        ]
        
        event_title_lower = event.title.lower()
        
        # Check if it's a USD positive indicator
        if any(indicator.lower() in event_title_lower for indicator in usd_positive_indicators):
            if actual_vs_forecast > 0:  # Better than expected = USD strength = Gold weakness
                return NewsDirection.BEARISH
            else:  # Worse than expected = USD weakness = Gold strength
                return NewsDirection.BULLISH
        
        # Check if it's a USD negative indicator
        elif any(indicator.lower() in event_title_lower for indicator in usd_negative_indicators):
            if actual_vs_forecast > 0:  # Worse than expected = USD weakness = Gold strength
                return NewsDirection.BULLISH
            else:  # Better than expected = USD strength = Gold weakness
                return NewsDirection.BEARISH
        
        # Fed rate decisions
        elif 'fomc' in event_title_lower or 'fed rate' in event_title_lower:
            if actual_vs_forecast > 0:  # Higher rates = USD strength = Gold weakness
                return NewsDirection.BEARISH
            else:  # Lower rates = USD weakness = Gold strength
                return NewsDirection.BULLISH
        
        return NewsDirection.NEUTRAL
    
    def _calculate_confidence(self, event: EconomicEvent, surprise: float) -> float:
        """คำนวณความมั่นใจในการคาดการณ์"""
        base_confidence = 60.0
        
        # Higher surprise = higher confidence
        surprise_boost = min(surprise * 2, 30)
        
        # High importance events = higher confidence
        importance_boost = {
            NewsImpact.CRITICAL: 20,
            NewsImpact.HIGH: 15,
            NewsImpact.MEDIUM: 10,
            NewsImpact.LOW: 5
        }.get(event.importance, 0)
        
        # USD events affect gold more = higher confidence
        if event.currency == 'USD':
            currency_boost = 10
        else:
            currency_boost = 0
        
        total_confidence = base_confidence + surprise_boost + importance_boost + currency_boost
        return min(total_confidence, 95.0)

class NewsReactionEngine:
    """
    📰 News Reaction Trading Engine
    
    Engine สำหรับเทรดโดยใช้ปฏิกิริยาต่อข่าวเศรษฐกิจ
    """
    
    def __init__(self):
        self.logger = setup_component_logger("NewsReactionEngine")
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # News Impact Model
        self.gold_model = GoldNewsImpactModel()
        
        # Configuration
        self.config = {
            # News Monitoring
            'news_lookback_hours': 24,
            'news_lookahead_hours': 8,
            'min_event_importance': NewsImpact.MEDIUM,
            
            # Reaction Timing
            'pre_news_window_minutes': 15,
            'immediate_reaction_minutes': 5,
            'short_term_reaction_minutes': 30,
            'medium_term_reaction_minutes': 120,
            
            # Signal Generation
            'min_surprise_factor': 20.0,  # Minimum deviation to generate signal
            'min_signal_confidence': 70.0,
            'max_signals_per_event': 2,
            
            # Risk Management
            'max_news_exposure_percent': 5.0,  # Max % of account for news trades
            'volatility_stop_multiplier': 1.5,
            'take_profit_multiplier': 2.0
        }
        
        # Data Storage
        self.economic_calendar = {}  # {date: List[EconomicEvent]}
        self.market_data = {}        # {timeframe: DataFrame}
        self.news_signals = deque(maxlen=100)
        self.active_events = deque(maxlen=20)
        
        # Market State
        self.current_volatility = 1.0
        self.pre_news_price = None
        self.last_calendar_update = None
        
        self.logger.info("📰 เริ่มต้น News Reaction Engine")
    
    def update_economic_calendar(self, events: List[Dict[str, Any]]) -> None:
        """อัพเดท Economic Calendar"""
        try:
            for event_data in events:
                event = EconomicEvent(
                    event_id=event_data.get('id', ''),
                    title=event_data.get('title', ''),
                    country=event_data.get('country', ''),
                    currency=event_data.get('currency', ''),
                    importance=NewsImpact(event_data.get('importance', 'LOW')),
                    scheduled_time=datetime.fromisoformat(event_data.get('scheduled_time', '')),
                    actual_value=event_data.get('actual'),
                    forecast_value=event_data.get('forecast'),
                    previous_value=event_data.get('previous'),
                    is_released=event_data.get('is_released', False)
                )
                
                # Store by date
                event_date = event.scheduled_time.date()
                if event_date not in self.economic_calendar:
                    self.economic_calendar[event_date] = []
                
                # Update existing event or add new one
                existing_event = next(
                    (e for e in self.economic_calendar[event_date] if e.event_id == event.event_id),
                    None
                )
                
                if existing_event:
                    # Update existing event
                    existing_event.actual_value = event.actual_value
                    existing_event.is_released = event.is_released
                else:
                    # Add new event
                    self.economic_calendar[event_date].append(event)
            
            self.last_calendar_update = datetime.now()
            self.logger.debug(f"📅 อัพเดท Economic Calendar: {len(events)} events")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Economic Calendar: {e}")
    
    def update_market_data(self, timeframe: str, data: pd.DataFrame) -> None:
        """อัพเดทข้อมูล Market"""
        try:
            if data is not None and not data.empty:
                self.market_data[timeframe] = data.copy()
                
                # Update current volatility
                if timeframe == 'M1':
                    self._update_current_volatility(data)
                
                self.logger.debug(f"📊 อัพเดท Market Data: {timeframe}")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Market Data: {e}")
    
    def _update_current_volatility(self, data: pd.DataFrame) -> None:
        """อัพเดท Current Volatility"""
        try:
            if len(data) < 20:
                return
            
            # Calculate ATR-based volatility
            recent_data = data.tail(20)
            true_ranges = []
            
            for i in range(1, len(recent_data)):
                current = recent_data.iloc[i]
                previous = recent_data.iloc[i-1]
                
                tr = max(
                    current['high'] - current['low'],
                    abs(current['high'] - previous['close']),
                    abs(current['low'] - previous['close'])
                )
                true_ranges.append(tr)
            
            if true_ranges:
                current_atr = np.mean(true_ranges)
                historical_atr = np.mean(true_ranges[-100:]) if len(true_ranges) >= 100 else current_atr
                
                self.current_volatility = current_atr / historical_atr if historical_atr > 0 else 1.0
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Volatility: {e}")
    
    def analyze_news_opportunities(self) -> List[NewsReactionSignal]:
        """วิเคราะห์หาโอกาสเทรดจากข่าว"""
        try:
            signals = []
            current_time = datetime.now()
            
            # Get relevant events (past 2 hours to future 8 hours)
            relevant_events = self._get_relevant_events(
                start_time=current_time - timedelta(hours=2),
                end_time=current_time + timedelta(hours=8)
            )
            
            for event in relevant_events:
                # Determine reaction phase
                phase = self._determine_reaction_phase(event, current_time)
                
                # Generate signals based on phase
                event_signals = self._generate_phase_signals(event, phase, current_time)
                signals.extend(event_signals)
            
            # Filter and rank signals
            filtered_signals = self._filter_and_rank_news_signals(signals)
            
            # Store signals
            for signal in filtered_signals:
                self.news_signals.append(signal)
            
            if filtered_signals:
                self.logger.info(f"📰 พบ News Signals: {len(filtered_signals)} signals")
            
            return filtered_signals
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์ News Opportunities: {e}")
            return []
    
    def _get_relevant_events(self, start_time: datetime, end_time: datetime) -> List[EconomicEvent]:
        """ดึงเหตุการณ์ที่เกี่ยวข้องในช่วงเวลาที่กำหนด"""
        try:
            relevant_events = []
            
            # Check each date in the range
            current_date = start_time.date()
            end_date = end_time.date()
            
            while current_date <= end_date:
                if current_date in self.economic_calendar:
                    for event in self.economic_calendar[current_date]:
                        if (start_time <= event.scheduled_time <= end_time and
                            event.importance.value in ['MEDIUM', 'HIGH', 'CRITICAL'] and
                            event.currency in ['USD', 'EUR', 'JPY']):  # Major currencies affecting gold
                            relevant_events.append(event)
                
                current_date += timedelta(days=1)
            
            return relevant_events
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึง Relevant Events: {e}")
            return []
    
    def _determine_reaction_phase(self, event: EconomicEvent, current_time: datetime) -> ReactionPhase:
        """กำหนด Reaction Phase"""
        time_diff = (current_time - event.scheduled_time).total_seconds() / 60  # minutes
        
        if time_diff < -self.config['pre_news_window_minutes']:
            return ReactionPhase.PRE_NEWS
        elif -self.config['pre_news_window_minutes'] <= time_diff <= self.config['immediate_reaction_minutes']:
            return ReactionPhase.IMMEDIATE
        elif self.config['immediate_reaction_minutes'] < time_diff <= self.config['short_term_reaction_minutes']:
            return ReactionPhase.SHORT_TERM
        elif self.config['short_term_reaction_minutes'] < time_diff <= self.config['medium_term_reaction_minutes']:
            return ReactionPhase.MEDIUM_TERM
        else:
            return ReactionPhase.REVERSAL
    
    def _generate_phase_signals(self, event: EconomicEvent, phase: ReactionPhase, 
                               current_time: datetime) -> List[NewsReactionSignal]:
        """สร้าง Signals ตาม Reaction Phase"""
        try:
            signals = []
            
            # Only generate signals for events with sufficient impact
            if event.importance == NewsImpact.LOW:
                return signals
            
            # Get market impact analysis
            impact_analysis = self.gold_model.calculate_gold_impact(event)
            
            if phase == ReactionPhase.PRE_NEWS:
                signals.extend(self._generate_pre_news_signals(event, impact_analysis, current_time))
            
            elif phase == ReactionPhase.IMMEDIATE:
                signals.extend(self._generate_immediate_signals(event, impact_analysis, current_time))
            
            elif phase == ReactionPhase.SHORT_TERM:
                signals.extend(self._generate_short_term_signals(event, impact_analysis, current_time))
            
            elif phase == ReactionPhase.MEDIUM_TERM:
                signals.extend(self._generate_medium_term_signals(event, impact_analysis, current_time))
            
            elif phase == ReactionPhase.REVERSAL:
                signals.extend(self._generate_reversal_signals(event, impact_analysis, current_time))
            
            return signals
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Phase Signals: {e}")
            return []
    
    def _generate_pre_news_signals(self, event: EconomicEvent, impact_analysis: Dict[str, Any], 
                                  current_time: datetime) -> List[NewsReactionSignal]:
        """สร้าง Pre-News Signals"""
        signals = []
        
        try:
            # Pre-news positioning based on expected volatility
            if impact_analysis['volatility_expectation'] > 1.5:
                
                # Strategy: Position before news with tight stops
                current_price = self._get_current_price()
                if current_price is None:
                    return signals
                
                # Store pre-news price for later comparison
                self.pre_news_price = current_price
                
                # Generate conservative positioning signal
                signal = NewsReactionSignal(
                    signal_id=f"PRE_{event.event_id}_{int(current_time.timestamp())}",
                    timestamp=current_time,
                    event=event,
                    reaction_phase=ReactionPhase.PRE_NEWS,
                    entry_direction=0,  # Neutral positioning
                    entry_price=current_price,
                    confidence=impact_analysis['confidence'] * 0.6,  # Lower confidence for pre-news
                    expected_volatility=impact_analysis['volatility_expectation'],
                    time_horizon_minutes=self.config['pre_news_window_minutes'],
                    stop_loss=0.0,  # Will be calculated
                    take_profit=0.0,  # Will be calculated
                    strategy_type='pre_news_positioning',
                    market_conditions={
                        'volatility': self.current_volatility,
                        'time_to_news': (event.scheduled_time - current_time).total_seconds() / 60
                    }
                )
                
                self._calculate_news_signal_parameters(signal)
                signals.append(signal)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Pre-News Signals: {e}")
        
        return signals
    
    def _generate_immediate_signals(self, event: EconomicEvent, impact_analysis: Dict[str, Any], 
                                   current_time: datetime) -> List[NewsReactionSignal]:
        """สร้าง Immediate Reaction Signals"""
        signals = []
        
        try:
            # Only if event is released with significant surprise
            if not event.is_released or event.surprise_factor < self.config['min_surprise_factor']:
                return signals
            
            current_price = self._get_current_price()
            if current_price is None:
                return signals
            
            direction = impact_analysis['direction']
            if direction == NewsDirection.NEUTRAL:
                return signals
            
            # Momentum signal: Trade in the direction of news impact
            entry_direction = 1 if direction == NewsDirection.BULLISH else -1
            
            momentum_signal = NewsReactionSignal(
                signal_id=f"IMM_MOM_{event.event_id}_{int(current_time.timestamp())}",
                timestamp=current_time,
                event=event,
                reaction_phase=ReactionPhase.IMMEDIATE,
                entry_direction=entry_direction,
                entry_price=current_price,
                confidence=impact_analysis['confidence'],
                expected_volatility=impact_analysis['volatility_expectation'],
                time_horizon_minutes=self.config['immediate_reaction_minutes'],
                stop_loss=0.0,
                take_profit=0.0,
                strategy_type='momentum',
                market_conditions={
                    'surprise_factor': event.surprise_factor,
                    'volatility': self.current_volatility
                }
            )
            
            self._calculate_news_signal_parameters(momentum_signal)
            signals.append(momentum_signal)
            
            # Fade signal: Bet against immediate overreaction (if high volatility)
            if impact_analysis['volatility_expectation'] > 2.0:
                fade_signal = NewsReactionSignal(
                    signal_id=f"IMM_FADE_{event.event_id}_{int(current_time.timestamp())}",
                    timestamp=current_time,
                    event=event,
                    reaction_phase=ReactionPhase.IMMEDIATE,
                    entry_direction=-entry_direction,  # Opposite direction
                    entry_price=current_price,
                    confidence=impact_analysis['confidence'] * 0.7,  # Lower confidence
                    expected_volatility=impact_analysis['volatility_expectation'],
                    time_horizon_minutes=self.config['short_term_reaction_minutes'],
                    stop_loss=0.0,
                    take_profit=0.0,
                    strategy_type='fade',
                    market_conditions={
                        'surprise_factor': event.surprise_factor,
                        'volatility': self.current_volatility
                    }
                )
                
                self._calculate_news_signal_parameters(fade_signal)
                signals.append(fade_signal)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Immediate Signals: {e}")
        
        return signals
    
    def _generate_short_term_signals(self, event: EconomicEvent, impact_analysis: Dict[str, Any], 
                                    current_time: datetime) -> List[NewsReactionSignal]:
        """สร้าง Short-term Signals"""
        signals = []
        
        try:
            if not event.is_released:
                return signals
            
            current_price = self._get_current_price()
            if current_price is None or self.pre_news_price is None:
                return signals
            
            # Analyze price movement since news release
            price_change = current_price - self.pre_news_price
            direction = impact_analysis['direction']
            
            # Check if market moved as expected
            expected_move = (direction == NewsDirection.BULLISH and price_change > 0) or \
                           (direction == NewsDirection.BEARISH and price_change < 0)
            
            if expected_move:
                # Continuation signal: Trend likely to continue
                entry_direction = 1 if direction == NewsDirection.BULLISH else -1
                
                continuation_signal = NewsReactionSignal(
                    signal_id=f"ST_CONT_{event.event_id}_{int(current_time.timestamp())}",
                    timestamp=current_time,
                    event=event,
                    reaction_phase=ReactionPhase.SHORT_TERM,
                    entry_direction=entry_direction,
                    entry_price=current_price,
                    confidence=impact_analysis['confidence'] * 0.8,
                    expected_volatility=impact_analysis['volatility_expectation'] * 0.8,
                    time_horizon_minutes=self.config['short_term_reaction_minutes'],
                    stop_loss=0.0,
                    take_profit=0.0,
                    strategy_type='continuation',
                    market_conditions={
                        'price_change': price_change,
                        'expected_move': expected_move
                    }
                )
                
                self._calculate_news_signal_parameters(continuation_signal)
                signals.append(continuation_signal)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Short-term Signals: {e}")
        
        return signals
    
    def _generate_medium_term_signals(self, event: EconomicEvent, impact_analysis: Dict[str, Any], 
                                     current_time: datetime) -> List[NewsReactionSignal]:
        """สร้าง Medium-term Signals"""
        signals = []
        
        try:
            # Medium-term signals based on fundamental impact
            if event.importance in [NewsImpact.HIGH, NewsImpact.CRITICAL]:
                current_price = self._get_current_price()
                if current_price is None:
                    return signals
                
                direction = impact_analysis['direction']
                if direction != NewsDirection.NEUTRAL:
                    entry_direction = 1 if direction == NewsDirection.BULLISH else -1
                    
                    fundamental_signal = NewsReactionSignal(
                        signal_id=f"MT_FUND_{event.event_id}_{int(current_time.timestamp())}",
                        timestamp=current_time,
                        event=event,
                        reaction_phase=ReactionPhase.MEDIUM_TERM,
                        entry_direction=entry_direction,
                        entry_price=current_price,
                        confidence=impact_analysis['confidence'] * 0.9,
                        expected_volatility=impact_analysis['volatility_expectation'] * 0.6,
                        time_horizon_minutes=self.config['medium_term_reaction_minutes'],
                        stop_loss=0.0,
                        take_profit=0.0,
                        strategy_type='fundamental',
                        market_conditions={
                            'event_importance': event.importance.value,
                            'time_since_release': (current_time - event.scheduled_time).total_seconds() / 60
                        }
                    )
                    
                    self._calculate_news_signal_parameters(fundamental_signal)
                    signals.append(fundamental_signal)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Medium-term Signals: {e}")
        
        return signals
    
    def _generate_reversal_signals(self, event: EconomicEvent, impact_analysis: Dict[str, Any], 
                                  current_time: datetime) -> List[NewsReactionSignal]:
        """สร้าง Reversal Signals"""
        signals = []
        
        try:
            # Look for overextended moves that might reverse
            if not event.is_released or self.pre_news_price is None:
                return signals
            
            current_price = self._get_current_price()
            if current_price is None:
                return signals
            
            # Calculate total move since news
            total_move = abs(current_price - self.pre_news_price)
            expected_move_size = self._estimate_expected_move(event, impact_analysis)
            
            # If move is significantly larger than expected, consider reversal
            if total_move > expected_move_size * 1.5:
                direction = impact_analysis['direction']
                price_change = current_price - self.pre_news_price
                
                # Determine if move was in expected direction
                move_with_news = (direction == NewsDirection.BULLISH and price_change > 0) or \
                                (direction == NewsDirection.BEARISH and price_change < 0)
                
                if move_with_news:
                    # Reversal signal: Bet against overextension
                    entry_direction = -1 if direction == NewsDirection.BULLISH else 1
                    
                    reversal_signal = NewsReactionSignal(
                        signal_id=f"REV_{event.event_id}_{int(current_time.timestamp())}",
                        timestamp=current_time,
                        event=event,
                        reaction_phase=ReactionPhase.REVERSAL,
                        entry_direction=entry_direction,
                        entry_price=current_price,
                        confidence=impact_analysis['confidence'] * 0.6,  # Lower confidence
                        expected_volatility=impact_analysis['volatility_expectation'] * 0.5,
                        time_horizon_minutes=60,  # Shorter horizon for reversals
                        stop_loss=0.0,
                        take_profit=0.0,
                        strategy_type='reversal',
                        market_conditions={
                            'overextension_ratio': total_move / expected_move_size,
                            'total_move': total_move
                        }
                    )
                    
                    self._calculate_news_signal_parameters(reversal_signal)
                    signals.append(reversal_signal)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Reversal Signals: {e}")
        
        return signals
    
    def _estimate_expected_move(self, event: EconomicEvent, impact_analysis: Dict[str, Any]) -> float:
        """ประมาณการขนาดการเคลื่อนไหวที่คาดหวัง"""
        try:
            # Base move estimation (in points for XAUUSD)
            base_move = {
                NewsImpact.CRITICAL: 50.0,
                NewsImpact.HIGH: 30.0,
                NewsImpact.MEDIUM: 20.0,
                NewsImpact.LOW: 10.0
            }.get(event.importance, 10.0)
            
            # Adjust by surprise factor
            surprise_multiplier = 1 + (event.surprise_factor / 100)
            
            # Adjust by volatility
            volatility_multiplier = impact_analysis['volatility_expectation']
            
            expected_move = base_move * surprise_multiplier * volatility_multiplier
            
            return expected_move
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการประมาณ Expected Move: {e}")
            return 20.0  # Default
    
    def _calculate_news_signal_parameters(self, signal: NewsReactionSignal) -> None:
        """คำนวณ Parameters สำหรับ News Signal"""
        try:
            current_price = signal.entry_price
            
            # Calculate stop loss based on volatility and strategy type
            if signal.strategy_type in ['momentum', 'continuation']:
                # Tighter stops for momentum plays
                stop_distance = 15.0 * self.current_volatility * signal.expected_volatility
            elif signal.strategy_type == 'fade':
                # Wider stops for fade plays
                stop_distance = 25.0 * self.current_volatility * signal.expected_volatility
            elif signal.strategy_type == 'reversal':
                # Medium stops for reversals
                stop_distance = 20.0 * self.current_volatility * signal.expected_volatility
            else:
                # Default
                stop_distance = 18.0 * self.current_volatility * signal.expected_volatility
            
            # Apply direction
            if signal.entry_direction == 1:  # BUY
                signal.stop_loss = current_price - stop_distance
                signal.take_profit = current_price + (stop_distance * self.config['take_profit_multiplier'])
            else:  # SELL
                signal.stop_loss = current_price + stop_distance
                signal.take_profit = current_price - (stop_distance * self.config['take_profit_multiplier'])
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ News Signal Parameters: {e}")
    
    def _get_current_price(self) -> Optional[float]:
        """ดึงราคาปัจจุบัน"""
        try:
            if 'M1' in self.market_data and not self.market_data['M1'].empty:
                return self.market_data['M1'].iloc[-1]['close']
            return None
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงราคาปัจจุบัน: {e}")
            return None
    
    def _filter_and_rank_news_signals(self, signals: List[NewsReactionSignal]) -> List[NewsReactionSignal]:
        """Filter และจัดอันดับ News Signals"""
        try:
            if not signals:
                return []
            
            # Filter by minimum confidence
            min_confidence = self.config['min_signal_confidence']
            filtered_signals = [
                signal for signal in signals 
                if signal.confidence >= min_confidence
            ]
            
            # Remove duplicate signals for same event
            event_signals = defaultdict(list)
            for signal in filtered_signals:
                event_signals[signal.event.event_id].append(signal)
            
            # Keep only best signals per event (limit by config)
            final_signals = []
            for event_id, event_signal_list in event_signals.items():
                # Sort by confidence
                event_signal_list.sort(key=lambda x: x.confidence, reverse=True)
                
                # Take top N signals per event
                max_signals = self.config['max_signals_per_event']
                final_signals.extend(event_signal_list[:max_signals])
            
            # Sort all signals by confidence
            final_signals.sort(key=lambda x: x.confidence, reverse=True)
            
            return final_signals
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการ Filter News Signals: {e}")
            return []
    
    def get_upcoming_events(self, hours_ahead: int = 8) -> List[EconomicEvent]:
        """ดึงเหตุการณ์ที่จะเกิดขึ้น"""
        try:
            current_time = datetime.now()
            end_time = current_time + timedelta(hours=hours_ahead)
            
            upcoming_events = []
            
            current_date = current_time.date()
            end_date = end_time.date()
            
            while current_date <= end_date:
                if current_date in self.economic_calendar:
                    for event in self.economic_calendar[current_date]:
                        if (current_time <= event.scheduled_time <= end_time and
                            not event.is_released and
                            event.importance.value in ['MEDIUM', 'HIGH', 'CRITICAL']):
                            upcoming_events.append(event)
                
                current_date += timedelta(days=1)
            
            # Sort by scheduled time
            upcoming_events.sort(key=lambda x: x.scheduled_time)
            
            return upcoming_events
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึง Upcoming Events: {e}")
            return []
    
    def get_recent_signals(self, hours_back: int = 6) -> List[NewsReactionSignal]:
        """ดึง Recent Signals"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            recent_signals = [
                signal for signal in self.news_signals
                if signal.timestamp >= cutoff_time
            ]
            
            return recent_signals
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึง Recent Signals: {e}")
            return []
    
    def get_news_summary(self) -> Dict[str, Any]:
        """ดึงสรุปข้อมูล News Engine"""
        try:
            current_time = datetime.now()
            
            # Count events by importance
            total_events = sum(len(events) for events in self.economic_calendar.values())
            upcoming_events = self.get_upcoming_events(24)
            recent_signals = self.get_recent_signals(24)
            
            summary = {
                'total_events_tracked': total_events,
                'upcoming_events_24h': len(upcoming_events),
                'high_impact_upcoming': len([e for e in upcoming_events if e.importance == NewsImpact.HIGH]),
                'critical_impact_upcoming': len([e for e in upcoming_events if e.importance == NewsImpact.CRITICAL]),
                'signals_24h': len(recent_signals),
                'average_signal_confidence': 0.0,
                'current_volatility': self.current_volatility,
                'last_calendar_update': self.last_calendar_update.isoformat() if self.last_calendar_update else None,
                'strategy_distribution': defaultdict(int)
            }
            
            # Calculate average confidence
            if recent_signals:
                summary['average_signal_confidence'] = sum(s.confidence for s in recent_signals) / len(recent_signals)
                
                # Strategy distribution
                for signal in recent_signals:
                    summary['strategy_distribution'][signal.strategy_type] += 1
            
            # Next critical event
            critical_events = [e for e in upcoming_events if e.importance == NewsImpact.CRITICAL]
            if critical_events:
                next_critical = critical_events[0]
                summary['next_critical_event'] = {
                    'title': next_critical.title,
                    'time': next_critical.scheduled_time.isoformat(),
                    'currency': next_critical.currency,
                    'time_until_minutes': (next_critical.scheduled_time - current_time).total_seconds() / 60
                }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึง News Summary: {e}")
            return {}
    
    def cleanup_old_data(self) -> None:
        """ทำความสะอาดข้อมูลเก่า"""
        try:
            current_time = datetime.now()
            
            # Remove old calendar entries (older than 7 days)
            cutoff_date = (current_time - timedelta(days=7)).date()
            
            old_dates = [date for date in self.economic_calendar.keys() if date < cutoff_date]
            for old_date in old_dates:
                del self.economic_calendar[old_date]
            
            # Limit market data size
            for timeframe in self.market_data:
                if len(self.market_data[timeframe]) > 1000:
                    self.market_data[timeframe] = self.market_data[timeframe].tail(1000)
            
            self.logger.debug("🧹 ทำความสะอาดข้อมูล News Engine")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการทำความสะอาด News Data: {e}")


# Test Functions
def test_news_reaction_engine():
    """ทดสอบ News Reaction Engine"""
    
    print("📰 ทดสอบ News Reaction Engine")
    
    # Create engine
    engine = NewsReactionEngine()
    
    # Create test economic events
    test_events = [
        {
            'id': 'NFP_2024_01',
            'title': 'Non-Farm Payrolls',
            'country': 'United States',
            'currency': 'USD',
            'importance': 'HIGH',
            'scheduled_time': (datetime.now() + timedelta(hours=2)).isoformat(),
            'forecast': 200000,
            'previous': 180000,
            'is_released': False
        },
        {
            'id': 'CPI_2024_01',
            'title': 'Consumer Price Index',
            'country': 'United States',
            'currency': 'USD',
            'importance': 'CRITICAL',
            'scheduled_time': (datetime.now() - timedelta(minutes=30)).isoformat(),
            'actual': 3.2,
            'forecast': 3.0,
            'previous': 3.1,
            'is_released': True
        },
        {
            'id': 'FOMC_2024_01',
            'title': 'FOMC Rate Decision',
            'country': 'United States',
            'currency': 'USD',
            'importance': 'CRITICAL',
            'scheduled_time': (datetime.now() + timedelta(hours=6)).isoformat(),
            'forecast': 5.25,
            'previous': 5.00,
            'is_released': False
        }
    ]
    
    # Update calendar
    engine.update_economic_calendar(test_events)
    print(f"📅 อัพเดท Economic Calendar: {len(test_events)} events")
    
    # Create test market data
    def create_test_market_data(bars: int = 100) -> pd.DataFrame:
        np.random.seed(42)
        base_price = 2020.0
        data = []
        
        for i in range(bars):
            price = base_price + i * 0.1 + np.random.normal(0, 2.0)
            high = price + abs(np.random.normal(0, 1.0))
            low = price - abs(np.random.normal(0, 1.0))
            close = price + np.random.normal(0, 0.5)
            volume = np.random.randint(50, 200)
            
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
    
    # Update market data
    test_data = create_test_market_data(100)
    engine.update_market_data('M1', test_data)
    print("📊 อัพเดท Market Data เสร็จสิ้น")
    
    # Test gold impact model
    print("\n🏅 ทดสอบ Gold Impact Model:")
    for event_data in test_events:
        if event_data.get('is_released'):
            event = EconomicEvent(
                event_id=event_data['id'],
                title=event_data['title'],
                country=event_data['country'],
                currency=event_data['currency'],
                importance=NewsImpact(event_data['importance']),
                scheduled_time=datetime.fromisoformat(event_data['scheduled_time']),
                actual_value=event_data.get('actual'),
                forecast_value=event_data.get('forecast'),
                previous_value=event_data.get('previous'),
                is_released=event_data.get('is_released', False)
            )
            
            impact = engine.gold_model.calculate_gold_impact(event)
            print(f"  📊 {event.title}:")
            print(f"     Surprise Factor: {event.surprise_factor:.1f}%")
            print(f"     Direction: {impact['direction'].value}")
            print(f"     Magnitude: {impact['magnitude']:.2f}")
            print(f"     Volatility Expectation: {impact['volatility_expectation']:.2f}")
            print(f"     Confidence: {impact['confidence']:.1f}%")
    
    # Analyze news opportunities
    print("\n🔍 วิเคราะห์ News Opportunities:")
    signals = engine.analyze_news_opportunities()
    print(f"พบ News Signals: {len(signals)}")
    
    for signal in signals:
        print(f"  📰 Signal: {signal.signal_id}")
        print(f"     Event: {signal.event.title}")
        print(f"     Phase: {signal.reaction_phase.value}")
        print(f"     Strategy: {signal.strategy_type}")
        print(f"     Direction: {'BUY' if signal.entry_direction == 1 else 'SELL'}")
        print(f"     Entry: {signal.entry_price:.2f}")
        print(f"     SL: {signal.stop_loss:.2f}")
        print(f"     TP: {signal.take_profit:.2f}")
        print(f"     Confidence: {signal.confidence:.1f}%")
        print(f"     Time Horizon: {signal.time_horizon_minutes} minutes")
        print()
    
    # Get upcoming events
    upcoming = engine.get_upcoming_events(24)
    print(f"📅 Upcoming Events (24h): {len(upcoming)}")
    for event in upcoming[:3]:
        time_until = (event.scheduled_time - datetime.now()).total_seconds() / 3600
        print(f"  📊 {event.title} - {event.importance.value} - in {time_until:.1f} hours")
    
    # Get summary
    summary = engine.get_news_summary()
    print(f"\n📊 News Engine Summary:")
    print(f"  Total Events Tracked: {summary.get('total_events_tracked', 0)}")
    print(f"  Upcoming Events (24h): {summary.get('upcoming_events_24h', 0)}")
    print(f"  High Impact Upcoming: {summary.get('high_impact_upcoming', 0)}")
    print(f"  Critical Impact Upcoming: {summary.get('critical_impact_upcoming', 0)}")
    print(f"  Signals (24h): {summary.get('signals_24h', 0)}")
    print(f"  Average Confidence: {summary.get('average_signal_confidence', 0):.1f}%")
    print(f"  Current Volatility: {summary.get('current_volatility', 1.0):.2f}")
    
    if 'next_critical_event' in summary:
        next_event = summary['next_critical_event']
        print(f"  Next Critical Event: {next_event['title']} in {next_event['time_until_minutes']:.0f} minutes")
    
    # Cleanup
    engine.cleanup_old_data()
    print("\n🧹 ทำความสะอาดข้อมูลเสร็จสิ้น")
    
    print("✅ การทดสอบ News Reaction Engine เสร็จสิ้น")


if __name__ == "__main__":
    test_news_reaction_engine()