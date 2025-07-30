#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELLIGENT STRATEGY SELECTION - ระบบเลือกกลยุทธ์อัจฉริยะ
=================================================
เลือกกลยุทธ์การเข้าออร์เดอร์แบบอัตโนมัติตามสภาพตลาด
รองรับการปรับตัวและเรียนรู้จากประสิทธิภาพ

เชื่อมต่อไปยัง:
- market_intelligence/market_analyzer.py (การวิเคราะห์ตลาด)
- adaptive_entries/entry_engines/* (กลยุทธ์ต่างๆ)
- config/trading_params.py (พารามิเตอร์กลยุทธ์)
- config/session_config.py (การตั้งค่า session)
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import statistics

try:
    from market_intelligence.market_analyzer import (
        MarketAnalyzer, MarketCondition, TrendDirection, MarketAnalysis
    )
    from config.trading_params import get_trading_parameters, EntryStrategy, RecoveryMethod
    from config.session_config import get_session_manager, SessionType
    from utilities.professional_logger import setup_trading_logger
    from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity
except ImportError as e:
    print(f"Import Error in strategy_selector.py: {e}")

class StrategyPerformance(Enum):
    """ระดับประสิทธิภาพของกลยุทธ์"""
    EXCELLENT = "EXCELLENT"     # >90%
    GOOD = "GOOD"              # 70-90%
    AVERAGE = "AVERAGE"        # 50-70%
    POOR = "POOR"              # 30-50%
    VERY_POOR = "VERY_POOR"    # <30%

@dataclass
class StrategyStats:
    """สถิติประสิทธิภาพของกลยุทธ์"""
    strategy: EntryStrategy
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    avg_profit_per_trade: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    avg_holding_time_minutes: float = 0.0
    performance_rating: StrategyPerformance = StrategyPerformance.AVERAGE
    
    # เงื่อนไขตลาดที่เหมาะสม
    best_market_conditions: List[MarketCondition] = field(default_factory=list)
    best_sessions: List[SessionType] = field(default_factory=list)
    
    # ประสิทธิภาพในแต่ละเงื่อนไข
    condition_performance: Dict[str, float] = field(default_factory=dict)
    session_performance: Dict[str, float] = field(default_factory=dict)
    
    def update_stats(self):
        """อัพเดทสถิติที่คำนวณได้"""
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100
            self.avg_profit_per_trade = (self.total_profit + self.total_loss) / self.total_trades
            
            if abs(self.total_loss) > 0:
                self.profit_factor = self.total_profit / abs(self.total_loss)
            
            # กำหนด performance rating
            if self.win_rate >= 90:
                self.performance_rating = StrategyPerformance.EXCELLENT
            elif self.win_rate >= 70:
                self.performance_rating = StrategyPerformance.GOOD
            elif self.win_rate >= 50:
                self.performance_rating = StrategyPerformance.AVERAGE
            elif self.win_rate >= 30:
                self.performance_rating = StrategyPerformance.POOR
            else:
                self.performance_rating = StrategyPerformance.VERY_POOR

@dataclass
class StrategyRecommendation:
    """คำแนะนำกลยุทธ์"""
    primary_strategy: EntryStrategy
    alternative_strategies: List[EntryStrategy]
    confidence_score: float  # 0.0-1.0
    reasoning: List[str]
    market_condition: MarketCondition
    expected_win_rate: float
    recommended_lot_size: float
    risk_level: str  # LOW, MEDIUM, HIGH
    timing_score: float  # 0.0-1.0 (1.0 = perfect timing)

class StrategySelector:
    """
    ตัวเลือกกลยุทธ์อัจฉริยะ
    เลือกกลยุทธ์ที่เหมาะสมที่สุดตามสภาพตลาดและประสิทธิภาพในอดีต
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.market_analyzer = MarketAnalyzer("XAUUSD.v")()
        self.session_manager = get_session_manager()
        self.trading_params = get_trading_parameters()
        
        # สถิติประสิทธิภาพ
        self.strategy_stats: Dict[EntryStrategy, StrategyStats] = {}
        self.selection_history: List[Tuple[datetime, EntryStrategy, MarketCondition]] = []
        
        # การตั้งค่า
        self.min_trades_for_stats = 10  # จำนวนเทรดขั้นต่ำก่อนใช้สถิติ
        self.stats_window_days = 30     # หน้าต่างเวลาสำหรับสถิติ
        
        # Threading
        self.selector_lock = threading.Lock()
        
        # เริ่มต้นสถิติ
        self._initialize_strategy_stats()
        
        self.logger.info("🎯 เริ่มต้น Strategy Selector")
    
    def _initialize_strategy_stats(self):
        """เริ่มต้นสถิติสำหรับกลยุทธ์ทั้งหมด"""
        for strategy in EntryStrategy:
            self.strategy_stats[strategy] = StrategyStats(strategy=strategy)
    
    @handle_trading_errors(ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM)
    def select_best_strategy(self, force_analysis: bool = False) -> Optional[StrategyRecommendation]:
        """
        เลือกกลยุทธ์ที่ดีที่สุดสำหรับสภาพตลาดปัจจุบัน
        """
        with self.selector_lock:
            try:
                # วิเคราะห์ตลาดปัจจุบัน
                market_analysis = self.market_analyzer.get_current_analysis(force_update=force_analysis)
                if not market_analysis:
                    self.logger.warning("⚠️ ไม่สามารถดึงข้อมูลการวิเคราะห์ตลาดได้")
                    return None
                
                # ดึงกลยุทธ์ที่แนะนำจากการวิเคราะห์ตลาด
                recommended_strategies = market_analysis.recommended_entry_strategies
                
                if not recommended_strategies:
                    recommended_strategies = [EntryStrategy.MEAN_REVERSION]  # default
                
                # คำนวณคะแนนสำหรับแต่ละกลยุทธ์
                strategy_scores = self._calculate_strategy_scores(
                    recommended_strategies, 
                    market_analysis
                )
                
                # เลือกกลยุทธ์ที่ดีที่สุด
                best_strategy = max(strategy_scores.keys(), key=lambda s: strategy_scores[s])
                
                # เรียงกลยุทธ์ทางเลือกตามคะแนน
                alternative_strategies = sorted(
                    [s for s in strategy_scores.keys() if s != best_strategy],
                    key=lambda s: strategy_scores[s],
                    reverse=True
                )[:2]  # เอา 2 อันดับถัดไป
                
                # สร้างคำแนะนำ
                recommendation = self._create_recommendation(
                    best_strategy,
                    alternative_strategies,
                    strategy_scores[best_strategy],
                    market_analysis
                )
                
                # บันทึกประวัติการเลือก
                self.selection_history.append((
                    datetime.now(),
                    best_strategy,
                    market_analysis.primary_condition
                ))
                
                # จำกัดประวัติ
                if len(self.selection_history) > 1000:
                    self.selection_history = self.selection_history[-1000:]
                
                self.logger.info(
                    f"🎯 เลือกกลยุทธ์: {best_strategy.value} "
                    f"(Confidence: {recommendation.confidence_score:.2f}) "
                    f"Market: {market_analysis.primary_condition.value}"
                )
                
                return recommendation
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดในการเลือกกลยุทธ์: {e}")
                return None
    
    def _calculate_strategy_scores(self, strategies: List[EntryStrategy], 
                                 market_analysis: MarketAnalysis) -> Dict[EntryStrategy, float]:
        """คำนวณคะแนนสำหรับแต่ละกลยุทธ์"""
        scores = {}
        
        for strategy in strategies:
            score = 0.0
            
            # คะแนนพื้นฐานจากการแนะนำของตลาด (40%)
            base_score = 0.4
            
            # คะแนนจากประสิทธิภาพในอดีต (30%)
            performance_score = self._get_performance_score(strategy, market_analysis)
            
            # คะแนนจากความเหมาะสมกับ session (20%)
            session_score = self._get_session_compatibility_score(strategy, market_analysis)
            
            # คะแนนจากความเหมาะสมกับสภาพตลาดเฉพาะ (10%)
            condition_score = self._get_condition_compatibility_score(strategy, market_analysis)
            
            # รวมคะแนน
            total_score = (base_score + 
                          performance_score * 0.3 + 
                          session_score * 0.2 + 
                          condition_score * 0.1)
            
            scores[strategy] = min(max(total_score, 0.0), 1.0)  # จำกัดระหว่าง 0-1
        
        return scores
    
    def _get_performance_score(self, strategy: EntryStrategy, 
                             market_analysis: MarketAnalysis) -> float:
        """คำนวณคะแนนจากประสิทธิภาพในอดีต"""
        stats = self.strategy_stats.get(strategy)
        if not stats or stats.total_trades < self.min_trades_for_stats:
            return 0.5  # คะแนนกลางถ้าไม่มีข้อมูลเพียงพอ
        
        # คะแนนจาก win rate
        win_rate_score = stats.win_rate / 100
        
        # คะแนนจาก profit factor
        profit_factor_score = min(stats.profit_factor / 2.0, 1.0) if stats.profit_factor > 0 else 0.0
        
        # คะแนนจากสภาพตลาดที่เหมาะสม
        condition_match_score = 0.0
        if market_analysis.primary_condition.value in stats.condition_performance:
            condition_match_score = stats.condition_performance[market_analysis.primary_condition.value] / 100
        
        # รวมคะแนน
        performance_score = (win_rate_score * 0.4 + 
                           profit_factor_score * 0.3 + 
                           condition_match_score * 0.3)
        
        return performance_score
    
    def _get_session_compatibility_score(self, strategy: EntryStrategy, 
                                       market_analysis: MarketAnalysis) -> float:
        """คำนวณคะแนนความเหมาะสมกับ session"""
        if not market_analysis.current_session:
            return 0.5
        
        # ดึงการตั้งค่า session
        session_profile = self.session_manager.get_session_profile(market_analysis.current_session)
        if not session_profile:
            return 0.5
        
        # ตรวจสอบว่ากลยุทธ์อยู่ในรายการที่แนะนำหรือไม่
        if strategy.value in session_profile.preferred_strategies:
            return 1.0
        elif strategy.value in session_profile.avoid_strategies:
            return 0.1
        else:
            return 0.5
    
    def _get_condition_compatibility_score(self, strategy: EntryStrategy, 
                                         market_analysis: MarketAnalysis) -> float:
        """คำนวณคะแนนความเหมาะสมกับสภาพตลาด"""
        
        # กำหนดความเหมาะสมระหว่างกลยุทธ์และสภาพตลาด
        compatibility_matrix = {
            EntryStrategy.TREND_FOLLOWING: {
                MarketCondition.TRENDING_STRONG: 1.0,
                MarketCondition.TRENDING_WEAK: 0.8,
                MarketCondition.RANGING_TIGHT: 0.2,
                MarketCondition.RANGING_WIDE: 0.3,
                MarketCondition.VOLATILE_HIGH: 0.6,
                MarketCondition.NEWS_IMPACT: 0.7
            },
            EntryStrategy.MEAN_REVERSION: {
                MarketCondition.TRENDING_STRONG: 0.2,
                MarketCondition.TRENDING_WEAK: 0.4,
                MarketCondition.RANGING_TIGHT: 1.0,
                MarketCondition.RANGING_WIDE: 0.9,
                MarketCondition.VOLATILE_HIGH: 0.5,
                MarketCondition.NEWS_IMPACT: 0.3
            },
            EntryStrategy.BREAKOUT_FALSE: {
                MarketCondition.TRENDING_STRONG: 0.7,
                MarketCondition.TRENDING_WEAK: 0.5,
                MarketCondition.RANGING_TIGHT: 0.6,
                MarketCondition.RANGING_WIDE: 0.8,
                MarketCondition.VOLATILE_HIGH: 1.0,
                MarketCondition.NEWS_IMPACT: 0.9
            },
            EntryStrategy.NEWS_REACTION: {
                MarketCondition.TRENDING_STRONG: 0.6,
                MarketCondition.TRENDING_WEAK: 0.4,
                MarketCondition.RANGING_TIGHT: 0.3,
                MarketCondition.RANGING_WIDE: 0.5,
                MarketCondition.VOLATILE_HIGH: 0.8,
                MarketCondition.NEWS_IMPACT: 1.0
            },
            EntryStrategy.SCALPING_ENGINE: {
                MarketCondition.TRENDING_STRONG: 0.4,
                MarketCondition.TRENDING_WEAK: 0.6,
                MarketCondition.RANGING_TIGHT: 0.9,
                MarketCondition.RANGING_WIDE: 0.7,
                MarketCondition.VOLATILE_HIGH: 0.3,
                MarketCondition.NEWS_IMPACT: 0.2
            }
        }
        
        strategy_compatibility = compatibility_matrix.get(strategy, {})
        return strategy_compatibility.get(market_analysis.primary_condition, 0.5)
    
    def _create_recommendation(self, primary_strategy: EntryStrategy,
                             alternative_strategies: List[EntryStrategy],
                             confidence_score: float,
                             market_analysis: MarketAnalysis) -> StrategyRecommendation:
        """สร้างคำแนะนำกลยุทธ์"""
        
        # สร้างเหตุผล
        reasoning = []
        reasoning.append(f"สภาพตลาด: {market_analysis.primary_condition.value}")
        reasoning.append(f"ทิศทาง Trend: {market_analysis.trend_direction.value}")
        reasoning.append(f"ความแรง ADX: {market_analysis.adx_value:.1f}")
        
        if market_analysis.current_session:
            reasoning.append(f"Session: {market_analysis.current_session.value}")
        
        # ประมาณ win rate
        strategy_stats = self.strategy_stats.get(primary_strategy)
        expected_win_rate = strategy_stats.win_rate if strategy_stats and strategy_stats.total_trades >= self.min_trades_for_stats else 65.0
        
        # แนะนำขนาด lot
        recommended_lot_size = self._calculate_recommended_lot_size(market_analysis, confidence_score)
        
        # ประเมินความเสี่ยง
        risk_level = self._assess_risk_level(market_analysis, confidence_score)
        
        # คะแนน timing
        timing_score = self._calculate_timing_score(market_analysis)
        
        return StrategyRecommendation(
            primary_strategy=primary_strategy,
            alternative_strategies=alternative_strategies,
            confidence_score=confidence_score,
            reasoning=reasoning,
            market_condition=market_analysis.primary_condition,
            expected_win_rate=expected_win_rate,
            recommended_lot_size=recommended_lot_size,
            risk_level=risk_level,
            timing_score=timing_score
        )
    
    def _calculate_recommended_lot_size(self, market_analysis: MarketAnalysis, 
                                      confidence_score: float) -> float:
        """คำนวณขนาด lot ที่แนะนำ"""
        base_lot = 0.01
        
        # ปรับตาม confidence
        confidence_multiplier = 0.5 + (confidence_score * 0.5)  # 0.5-1.0
        
        # ปรับตาม volatility
        volatility_multipliers = {
            'LOW': 1.2,
            'NORMAL': 1.0,
            'HIGH': 0.8,
            'EXTREME': 0.6
        }
        volatility_multiplier = volatility_multipliers.get(market_analysis.volatility_level, 1.0)
        
        # ปรับตาม session
        session_multiplier = 1.0
        if market_analysis.current_session:
            session_profile = self.session_manager.get_session_profile(market_analysis.current_session)
            if session_profile:
                session_multiplier = session_profile.base_lot_multiplier
        
        # คำนวณขนาดสุดท้าย
        recommended_lot = base_lot * confidence_multiplier * volatility_multiplier * session_multiplier
        
        return max(0.01, min(recommended_lot, 0.5))  # จำกัดระหว่าง 0.01-0.5
    
    def _assess_risk_level(self, market_analysis: MarketAnalysis, confidence_score: float) -> str:
        """ประเมินระดับความเสี่ยง"""
        risk_factors = 0
        
        # ความเสี่ยงจาก volatility
        if market_analysis.volatility_level in ['HIGH', 'EXTREME']:
            risk_factors += 2
        elif market_analysis.volatility_level == 'LOW':
            risk_factors += 1
        
        # ความเสี่ยงจาก confidence
        if confidence_score < 0.3:
            risk_factors += 2
        elif confidence_score < 0.6:
            risk_factors += 1
        
        # ความเสี่ยงจาก trend uncertainty
        if market_analysis.trend_direction == TrendDirection.UNCERTAIN:
            risk_factors += 1
        
        # ความเสี่ยงจาก session
        if market_analysis.current_session == SessionType.QUIET_HOURS:
            risk_factors += 1
        
        # ประเมินระดับ
        if risk_factors >= 4:
            return "HIGH"
        elif risk_factors >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _calculate_timing_score(self, market_analysis: MarketAnalysis) -> float:
        """คำนวณคะแนน timing"""
        timing_factors = []
        
        # RSI timing
        if 30 <= market_analysis.rsi_value <= 70:
            rsi_score = 1.0 - (abs(market_analysis.rsi_value - 50) / 20)
            timing_factors.append(rsi_score)
        else:
            timing_factors.append(0.3)  # Extreme RSI = bad timing
        
        # MACD timing
        if market_analysis.macd_value != 0 and market_analysis.macd_signal != 0:
            macd_momentum = abs(market_analysis.macd_value - market_analysis.macd_signal)
            macd_score = min(macd_momentum * 10, 1.0)  # Normalize
            timing_factors.append(macd_score)
        
        # ADX timing
        if market_analysis.adx_value > 0:
            if 20 <= market_analysis.adx_value <= 40:
                adx_score = 1.0
            elif market_analysis.adx_value < 20:
                adx_score = market_analysis.adx_value / 20
            else:
                adx_score = max(0.5, 1.0 - ((market_analysis.adx_value - 40) / 40))
            timing_factors.append(adx_score)
        
        return statistics.mean(timing_factors) if timing_factors else 0.5
    
    def record_strategy_result(self, strategy: EntryStrategy, profit: float, 
                             holding_time_minutes: float, market_condition: MarketCondition):
        """บันทึกผลลัพธ์ของกลยุทธ์"""
        with self.selector_lock:
            stats = self.strategy_stats.get(strategy)
            if not stats:
                return
            
            # อัพเดทสถิติพื้นฐาน
            stats.total_trades += 1
            
            if profit > 0:
                stats.winning_trades += 1
                stats.total_profit += profit
            else:
                stats.losing_trades += 1
                stats.total_loss += profit  # profit เป็นลบแล้ว
            
            # อัพเดทเวลาถือ position
            if stats.total_trades == 1:
                stats.avg_holding_time_minutes = holding_time_minutes
            else:
                stats.avg_holding_time_minutes = (
                    (stats.avg_holding_time_minutes * (stats.total_trades - 1) + holding_time_minutes) 
                    / stats.total_trades
                )
            
            # อัพเดทประสิทธิภาพตามสภาพตลาด
            condition_key = market_condition.value
            if condition_key not in stats.condition_performance:
                stats.condition_performance[condition_key] = 0.0
            
            # คำนวณ win rate ใหม่สำหรับสภาพตลาดนี้
            # (ตัวอย่างง่ายๆ - ควรมีการเก็บข้อมูลแยกตามสภาพตลาด)
            current_rate = stats.condition_performance[condition_key]
            if profit > 0:
                new_rate = min(current_rate + 5, 100)  # เพิ่ม 5% เมื่อชนะ
            else:
                new_rate = max(current_rate - 3, 0)    # ลด 3% เมื่อแพ้
            stats.condition_performance[condition_key] = new_rate
            
            # อัพเดทสถิติที่คำนวณได้
            stats.update_stats()
            
            self.logger.debug(
                f"📊 บันทึกผล {strategy.value}: "
                f"Profit: {profit:.2f} Win Rate: {stats.win_rate:.1f}% "
                f"Total Trades: {stats.total_trades}"
            )
    
    def get_strategy_statistics(self) -> Dict[str, Dict]:
        """ดึงสถิติกลยุทธ์ทั้งหมด"""
        stats_summary = {}
        
        for strategy, stats in self.strategy_stats.items():
            stats_summary[strategy.value] = {
                "total_trades": stats.total_trades,
                "win_rate": round(stats.win_rate, 2),
                "profit_factor": round(stats.profit_factor, 2),
                "avg_profit_per_trade": round(stats.avg_profit_per_trade, 2),
                "performance_rating": stats.performance_rating.value,
                "avg_holding_time_minutes": round(stats.avg_holding_time_minutes, 1),
                "best_conditions": list(stats.best_market_conditions),
                "condition_performance": stats.condition_performance
            }
        
        return stats_summary
    
    def get_selection_history(self, hours: int = 24) -> List[Dict]:
        """ดึงประวัติการเลือกกลยุทธ์"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_selections = [
            selection for selection in self.selection_history 
            if selection[0] > cutoff_time
        ]
        
        return [
            {
                "timestamp": selection[0].isoformat(),
                "strategy": selection[1].value,
                "market_condition": selection[2].value
            }
            for selection in recent_selections
        ]

# === HELPER FUNCTIONS ===

def get_current_strategy_recommendation() -> Optional[StrategyRecommendation]:
    """ดึงคำแนะนำกลยุทธ์ปัจจุบัน"""
    selector = get_strategy_selector()
    return selector.select_best_strategy()

def record_trade_result(strategy_name: str, profit: float, 
                       holding_time_minutes: float, market_condition_name: str):
    """บันทึกผลการเทรด"""
    try:
        strategy = EntryStrategy(strategy_name)
        condition = MarketCondition(market_condition_name)
        
        selector = get_strategy_selector()
        selector.record_strategy_result(strategy, profit, holding_time_minutes, condition)
        
    except ValueError as e:
        print(f"Invalid strategy or condition name: {e}")

# === GLOBAL INSTANCE ===
_global_strategy_selector: Optional[StrategySelector] = None

def get_strategy_selector() -> StrategySelector:
    """ดึง Strategy Selector แบบ Singleton"""
    global _global_strategy_selector
    if _global_strategy_selector is None:
        _global_strategy_selector = StrategySelector()
    return _global_strategy_selector