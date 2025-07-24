#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAPITAL ALLOCATOR - Intelligent Capital Allocation System
=======================================================
ระบบจัดสรรเงินทุนแบบอัจฉริยะสำหรับ High-Frequency Trading และ Recovery System
รองรับการจัดสรรเงินทุนแบบ Dynamic ตามสภาพตลาดและประสิทธิภาพ

Key Features:
- Dynamic capital distribution algorithms
- Strategy-based allocation optimization
- Risk-adjusted capital allocation
- Recovery budget management
- Performance-based allocation adjustment
- Real-time capital rebalancing
- High-frequency allocation decisions (50-100 lots/day)

เชื่อมต่อไปยัง:
- money_management/position_sizer.py (ข้อมูล sizing)
- money_management/risk_calculator.py (ข้อมูล risk)
- analytics_engine/performance_tracker.py (ข้อมูล performance)
- intelligent_recovery/recovery_engine.py (ข้อมูล recovery)
- position_management/position_tracker.py (ข้อมูล positions)
"""

import asyncio
import threading
import time
import math
import statistics
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from enum import Enum
import json
from collections import defaultdict, deque

# เชื่อมต่อ internal modules
from config.settings import get_system_settings, MarketSession
from config.trading_params import get_trading_parameters, EntryStrategy, RecoveryMethod
from utilities.professional_logger import setup_trading_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class AllocationStrategy(Enum):
    """กลยุทธ์การจัดสรรเงินทุน"""
    EQUAL_WEIGHT = "equal_weight"                    # จัดสรรเท่าๆ กัน
    PERFORMANCE_BASED = "performance_based"          # ตามประสิทธิภาพ
    RISK_ADJUSTED = "risk_adjusted"                  # ปรับตามความเสี่ยง
    VOLATILITY_TARGETING = "volatility_targeting"    # เป้าหมาย Volatility
    KELLY_CRITERION = "kelly_criterion"              # Kelly Criterion
    DYNAMIC_REBALANCING = "dynamic_rebalancing"      # Rebalancing แบบ Dynamic
    RECOVERY_PRIORITIZED = "recovery_prioritized"    # ให้ความสำคัญกับ Recovery
    SESSION_ADAPTIVE = "session_adaptive"            # ปรับตาม Trading Session

class AllocationCategory(Enum):
    """ประเภทการจัดสรรเงินทุน"""
    TRADING_CAPITAL = "trading_capital"              # เงินทุนสำหรับเทรด
    RECOVERY_RESERVE = "recovery_reserve"            # เงินสำรองสำหรับ Recovery
    EMERGENCY_FUND = "emergency_fund"                # เงินฉุกเฉิน
    STRATEGY_ALLOCATION = "strategy_allocation"      # จัดสรรตาม Strategy
    SESSION_ALLOCATION = "session_allocation"        # จัดสรรตาม Session
    RISK_BUFFER = "risk_buffer"                      # Buffer สำหรับความเสี่ยง

class RebalancingTrigger(Enum):
    """เงื่อนไขการ Rebalancing"""
    TIME_BASED = "time_based"                        # ตามเวลา
    PERFORMANCE_THRESHOLD = "performance_threshold"   # ตามประสิทธิภาพ
    RISK_THRESHOLD = "risk_threshold"                # ตามความเสี่ยง
    ALLOCATION_DRIFT = "allocation_drift"            # การเบี่ยงเบนจากเป้าหมาย
    MARKET_CONDITION_CHANGE = "market_condition_change" # เปลี่ยนสภาพตลาด
    RECOVERY_EVENT = "recovery_event"                # เหตุการณ์ Recovery

@dataclass
class AllocationTarget:
    """เป้าหมายการจัดสรรเงินทุน"""
    category: AllocationCategory
    target_percentage: float                         # % ของเงินทุนทั้งหมด
    current_percentage: float = 0.0                  # % ปัจจุบัน
    target_amount: float = 0.0                       # จำนวนเงินเป้าหมาย
    current_amount: float = 0.0                      # จำนวนเงินปัจจุบัน
    
    # Constraints
    min_percentage: float = 0.0                      # % ขั้นต่ำ
    max_percentage: float = 100.0                    # % สูงสุด
    
    # Performance Metrics
    allocation_efficiency: float = 0.0               # ประสิทธิภาพการจัดสรร
    risk_adjusted_return: float = 0.0               # ผลตอบแทนปรับความเสี่ยง
    
    # Metadata
    last_rebalanced: datetime = field(default_factory=datetime.now)
    rebalancing_frequency: timedelta = field(default_factory=lambda: timedelta(hours=1))

@dataclass
class StrategyAllocation:
    """การจัดสรรเงินทุนตาม Strategy"""
    strategy: EntryStrategy
    allocated_capital: float = 0.0                  # เงินทุนที่จัดสรร
    allocated_percentage: float = 0.0               # % ของเงินทุนรวม
    used_capital: float = 0.0                       # เงินทุนที่ใช้ไปแล้ว
    available_capital: float = 0.0                  # เงินทุนที่เหลือใช้ได้
    
    # Performance Metrics
    strategy_performance: float = 0.0               # ประสิทธิภาพของ Strategy
    win_rate: float = 0.0                          # อัตราชนะ
    profit_factor: float = 0.0                     # Profit Factor
    sharpe_ratio: float = 0.0                      # Sharpe Ratio
    
    # Allocation Metrics
    capital_efficiency: float = 0.0                # ประสิทธิภาพการใช้เงินทุน
    utilization_rate: float = 0.0                 # อัตราการใช้เงินทุน
    
    # Constraints
    max_allocation_percentage: float = 30.0        # % สูงสุดที่จัดสรรได้
    min_allocation_percentage: float = 5.0         # % ขั้นต่ำ
    
    # Rebalancing Info
    last_performance_review: datetime = field(default_factory=datetime.now)
    performance_trend: str = "STABLE"              # IMPROVING, STABLE, DECLINING

@dataclass
class SessionAllocation:
    """การจัดสรรเงินทุนตาม Trading Session"""
    session: MarketSession
    allocated_capital: float = 0.0
    allocated_percentage: float = 0.0
    target_volume_lots: float = 0.0                # เป้าหมาย Volume
    achieved_volume_lots: float = 0.0              # Volume ที่ทำได้
    
    # Session Characteristics
    expected_volatility: float = 1.0               # Volatility ที่คาดหวัง
    expected_opportunities: int = 10               # โอกาสการเทรดที่คาดหวัง
    risk_tolerance: float = 1.0                    # ความทนต่อความเสี่ยง
    
    # Performance Tracking
    session_pnl: float = 0.0                      # P&L ของ Session
    session_efficiency: float = 0.0               # ประสิทธิภาพ Session

@dataclass
class RecoveryAllocation:
    """การจัดสรรเงินทุนสำหรับ Recovery System"""
    total_recovery_budget: float = 0.0            # งบประมาณ Recovery รวม
    allocated_recovery_capital: float = 0.0       # เงินทุนที่จัดสรรแล้ว
    available_recovery_capital: float = 0.0       # เงินทุนที่เหลือใช้ได้
    
    # Method-based Allocation
    method_allocations: Dict[RecoveryMethod, float] = field(default_factory=dict)
    
    # Recovery Metrics
    recovery_success_rate: float = 95.0           # อัตราสำเร็จ Recovery
    average_recovery_time: float = 24.0           # เวลาเฉลี่ย Recovery (ชั่วโมง)
    recovery_efficiency: float = 0.0              # ประสิทธิภาพ Recovery
    
    # Risk Metrics
    max_concurrent_recoveries: int = 5             # จำนวน Recovery พร้อมกันสูงสุด
    current_active_recoveries: int = 0            # จำนวน Recovery ที่ทำงานอยู่
    recovery_capacity_utilization: float = 0.0    # % การใช้ Recovery Capacity

@dataclass
class AllocationResult:
    """ผลการจัดสรรเงินทุน"""
    allocation_id: str
    allocation_strategy: AllocationStrategy
    total_capital: float
    
    # Allocation Breakdown
    category_allocations: Dict[AllocationCategory, AllocationTarget] = field(default_factory=dict)
    strategy_allocations: Dict[EntryStrategy, StrategyAllocation] = field(default_factory=dict)
    session_allocations: Dict[MarketSession, SessionAllocation] = field(default_factory=dict)
    recovery_allocation: Optional[RecoveryAllocation] = None
    
    # Overall Metrics
    allocation_efficiency: float = 0.0            # ประสิทธิภาพการจัดสรรรวม
    diversification_score: float = 0.0            # คะแนน Diversification
    risk_utilization: float = 0.0                 # การใช้ Risk Budget
    
    # Rebalancing Info
    needs_rebalancing: bool = False
    rebalancing_urgency: str = "LOW"               # LOW, MEDIUM, HIGH, CRITICAL
    rebalancing_triggers: List[RebalancingTrigger] = field(default_factory=list)
    
    # Recommendations
    optimization_opportunities: List[str] = field(default_factory=list)
    allocation_warnings: List[str] = field(default_factory=list)
    
    # Metadata
    calculation_timestamp: datetime = field(default_factory=datetime.now)
    next_review_time: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=1))

class PerformanceBasedAllocator:
    """
    จัดสรรเงินทุนตามประสิทธิภาพของแต่ละ Strategy
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.lookback_period = 30  # วัน
        self.min_trades_for_evaluation = 10
    
    def calculate_strategy_allocations(self, total_capital: float, 
                                     performance_data: Dict[EntryStrategy, Dict[str, Any]]) -> Dict[EntryStrategy, StrategyAllocation]:
        """
        คำนวณการจัดสรรเงินทุนตาม Strategy Performance
        
        Args:
            total_capital: เงินทุนรวม
            performance_data: ข้อมูลประสิทธิภาพของแต่ละ Strategy
            
        Returns:
            Dict[EntryStrategy, StrategyAllocation]: การจัดสรรตาม Strategy
        """
        try:
            strategy_allocations = {}
            
            # คำนวณ Performance Scores
            performance_scores = self._calculate_performance_scores(performance_data)
            
            # คำนวณ Allocation Weights
            allocation_weights = self._calculate_allocation_weights(performance_scores)
            
            # สร้าง Strategy Allocations
            for strategy, weight in allocation_weights.items():
                perf_data = performance_data.get(strategy, {})
                
                allocated_amount = total_capital * weight
                
                strategy_allocation = StrategyAllocation(
                    strategy=strategy,
                    allocated_capital=allocated_amount,
                    allocated_percentage=weight * 100,
                    available_capital=allocated_amount,
                    
                    # Performance Metrics
                    strategy_performance=performance_scores.get(strategy, 0.0),
                    win_rate=perf_data.get('win_rate', 0.0),
                    profit_factor=perf_data.get('profit_factor', 1.0),
                    sharpe_ratio=perf_data.get('sharpe_ratio', 0.0),
                    
                    # Calculate efficiency
                    capital_efficiency=self._calculate_capital_efficiency(perf_data),
                    utilization_rate=0.0,  # จะอัพเดทตอนใช้งาน
                    
                    # Performance trend
                    performance_trend=self._determine_performance_trend(perf_data)
                )
                
                strategy_allocations[strategy] = strategy_allocation
            
            self.logger.info(f"📊 คำนวณ Strategy Allocations สำเร็จ - {len(strategy_allocations)} strategies")
            
            return strategy_allocations
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Strategy Allocations: {e}")
            return self._create_fallback_strategy_allocations(total_capital)
    
    def _calculate_performance_scores(self, performance_data: Dict[EntryStrategy, Dict[str, Any]]) -> Dict[EntryStrategy, float]:
        """คำนวณคะแนนประสิทธิภาพของแต่ละ Strategy"""
        scores = {}
        
        for strategy, data in performance_data.items():
            score = 0.0
            
            # Win Rate (30%)
            win_rate = data.get('win_rate', 0.0)
            score += (win_rate / 100.0) * 30.0
            
            # Profit Factor (25%)
            profit_factor = data.get('profit_factor', 1.0)
            pf_score = min(25.0, max(0.0, (profit_factor - 1.0) * 25.0))
            score += pf_score
            
            # Sharpe Ratio (20%)
            sharpe_ratio = data.get('sharpe_ratio', 0.0)
            sharpe_score = min(20.0, max(0.0, sharpe_ratio * 10.0))
            score += sharpe_score
            
            # Recovery Rate (15%) - สำคัญสำหรับระบบนี้
            recovery_rate = data.get('recovery_rate', 95.0)
            score += (recovery_rate / 100.0) * 15.0
            
            # Consistency (10%)
            consistency = data.get('consistency_score', 50.0)
            score += (consistency / 100.0) * 10.0
            
            scores[strategy] = score
        
        return scores
    
    def _calculate_allocation_weights(self, performance_scores: Dict[EntryStrategy, float]) -> Dict[EntryStrategy, float]:
        """คำนวณน้ำหนักการจัดสรรจากคะแนนประสิทธิภาพ"""
        if not performance_scores:
            return {}
        
        # ปรับคะแนนให้เป็นบวกทั้งหมด
        min_score = min(performance_scores.values())
        if min_score < 0:
            adjusted_scores = {k: v - min_score + 1.0 for k, v in performance_scores.items()}
        else:
            adjusted_scores = performance_scores.copy()
        
        # คำนวณน้ำหนัก
        total_score = sum(adjusted_scores.values())
        if total_score == 0:
            # Equal weight fallback
            equal_weight = 1.0 / len(adjusted_scores)
            return {strategy: equal_weight for strategy in adjusted_scores.keys()}
        
        # Softmax-like allocation with constraints
        weights = {}
        for strategy, score in adjusted_scores.items():
            base_weight = score / total_score
            
            # Apply constraints
            constrained_weight = max(0.05, min(0.35, base_weight))  # 5-35%
            weights[strategy] = constrained_weight
        
        # Normalize to sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        return weights
    
    def _calculate_capital_efficiency(self, perf_data: Dict[str, Any]) -> float:
        """คำนวณประสิทธิภาพการใช้เงินทุน"""
        try:
            total_trades = perf_data.get('total_trades', 0)
            total_volume = perf_data.get('total_volume', 0.0)
            net_profit = perf_data.get('net_profit', 0.0)
            
            if total_volume == 0:
                return 0.0
            
            # Profit per lot
            profit_per_lot = net_profit / total_volume if total_volume > 0 else 0.0
            
            # Trade frequency efficiency
            trade_efficiency = min(1.0, total_trades / 100.0)  # Normalize to 100 trades
            
            # Combined efficiency
            efficiency = (profit_per_lot * 10.0 + trade_efficiency * 50.0) / 2.0
            
            return max(0.0, min(100.0, efficiency))
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Capital Efficiency: {e}")
            return 50.0
    
    def _determine_performance_trend(self, perf_data: Dict[str, Any]) -> str:
        """กำหนดแนวโน้มประสิทธิภาพ"""
        try:
            recent_performance = perf_data.get('recent_performance', [])
            
            if len(recent_performance) < 3:
                return "STABLE"
            
            # คำนวณแนวโน้ม
            recent_avg = statistics.mean(recent_performance[-7:])  # 7 วันล่าสุด
            older_avg = statistics.mean(recent_performance[-14:-7])  # 7 วันก่อนหน้า
            
            improvement = (recent_avg - older_avg) / older_avg if older_avg != 0 else 0.0
            
            if improvement > 0.1:  # ปรับปรุงมากกว่า 10%
                return "IMPROVING"
            elif improvement < -0.1:  # แย่ลงมากกว่า 10%
                return "DECLINING"
            else:
                return "STABLE"
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการกำหนด Performance Trend: {e}")
            return "STABLE"
    
    def _create_fallback_strategy_allocations(self, total_capital: float) -> Dict[EntryStrategy, StrategyAllocation]:
        """สร้าง Fallback Strategy Allocations"""
        strategies = list(EntryStrategy)
        equal_allocation = total_capital / len(strategies)
        equal_percentage = 100.0 / len(strategies)
        
        allocations = {}
        for strategy in strategies:
            allocations[strategy] = StrategyAllocation(
                strategy=strategy,
                allocated_capital=equal_allocation,
                allocated_percentage=equal_percentage,
                available_capital=equal_allocation,
                strategy_performance=50.0,
                win_rate=50.0,
                profit_factor=1.0,
                sharpe_ratio=0.0,
                capital_efficiency=50.0,
                utilization_rate=0.0,
                performance_trend="STABLE"
            )
        
        return allocations

class RiskAdjustedAllocator:
    """
    จัดสรรเงินทุนตามความเสี่ยงที่ปรับแล้ว
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.target_portfolio_volatility = 0.15  # 15% ต่อปี
        self.max_individual_allocation = 0.35     # 35% สูงสุดต่อ Strategy
    
    def calculate_risk_adjusted_allocations(self, total_capital: float,
                                          strategy_risks: Dict[EntryStrategy, Dict[str, Any]],
                                          correlation_matrix: np.ndarray = None) -> Dict[EntryStrategy, StrategyAllocation]:
        """
        คำนวณการจัดสรรเงินทุนตามความเสี่ยงที่ปรับแล้ว
        
        Args:
            total_capital: เงินทุนรวม
            strategy_risks: ข้อมูลความเสี่ยงของแต่ละ Strategy
            correlation_matrix: Matrix ความสัมพันธ์ระหว่าง Strategies
            
        Returns:
            Dict[EntryStrategy, StrategyAllocation]: การจัดสรรตามความเสี่ยง
        """
        try:
            # คำนวณ Risk-Adjusted Weights
            if correlation_matrix is not None and correlation_matrix.size > 0:
                # ใช้ Mean-Variance Optimization
                weights = self._calculate_mean_variance_weights(strategy_risks, correlation_matrix)
            else:
                # ใช้ Risk Parity approach
                weights = self._calculate_risk_parity_weights(strategy_risks)
            
            # สร้าง Strategy Allocations
            strategy_allocations = {}
            
            for strategy, weight in weights.items():
                risk_data = strategy_risks.get(strategy, {})
                allocated_amount = total_capital * weight
                
                strategy_allocation = StrategyAllocation(
                    strategy=strategy,
                    allocated_capital=allocated_amount,
                    allocated_percentage=weight * 100,
                    available_capital=allocated_amount,
                    
                    # Risk Metrics
                    strategy_performance=self._calculate_risk_adjusted_performance(risk_data),
                    win_rate=risk_data.get('win_rate', 50.0),
                    profit_factor=risk_data.get('profit_factor', 1.0),
                    sharpe_ratio=risk_data.get('sharpe_ratio', 0.0),
                    
                    capital_efficiency=self._calculate_risk_efficiency(risk_data),
                    utilization_rate=0.0,
                    performance_trend="STABLE"
                )
                
                strategy_allocations[strategy] = strategy_allocation
            
            self.logger.info(f"📊 คำนวณ Risk-Adjusted Allocations สำเร็จ")
            
            return strategy_allocations
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Risk-Adjusted Allocations: {e}")
            return self._create_equal_weight_allocations(total_capital, list(strategy_risks.keys()))
    
    def _calculate_mean_variance_weights(self, strategy_risks: Dict[EntryStrategy, Dict[str, Any]],
                                       correlation_matrix: np.ndarray) -> Dict[EntryStrategy, float]:
        """คำนวณน้ำหนักตาม Mean-Variance Optimization"""
        try:
            strategies = list(strategy_risks.keys())
            n_strategies = len(strategies)
            
            # สร้าง Expected Returns Vector
            expected_returns = np.array([
                strategy_risks[strategy].get('expected_return', 0.02) for strategy in strategies
            ])
            
            # สร้าง Volatility Vector
            volatilities = np.array([
                strategy_risks[strategy].get('volatility', 0.10) for strategy in strategies
            ])
            
            # สร้าง Covariance Matrix
            if correlation_matrix.shape[0] != n_strategies:
                # สร้าง Identity matrix หาก correlation matrix ไม่ตรง
                correlation_matrix = np.eye(n_strategies)
            
            covariance_matrix = np.outer(volatilities, volatilities) * correlation_matrix
            
            # Solve for optimal weights (Mean-Variance)
            # เป้าหมาย: Maximize Sharpe Ratio
            inv_cov = np.linalg.pinv(covariance_matrix)
            ones = np.ones((n_strategies, 1))
            
            # Calculate optimal weights
            weights_raw = inv_cov @ expected_returns
            weights_sum = np.sum(weights_raw)
            
            if weights_sum != 0:
                weights = weights_raw / weights_sum
            else:
                weights = np.ones(n_strategies) / n_strategies
            
            # Apply constraints
            weights = np.clip(weights, 0.05, self.max_individual_allocation)
            weights = weights / np.sum(weights)  # Normalize
            
            # Convert to dictionary
            weight_dict = {}
            for i, strategy in enumerate(strategies):
                weight_dict[strategy] = float(weights[i])
            
            return weight_dict
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Mean-Variance Optimization: {e}")
            return self._calculate_risk_parity_weights(strategy_risks)
    
    def _calculate_risk_parity_weights(self, strategy_risks: Dict[EntryStrategy, Dict[str, Any]]) -> Dict[EntryStrategy, float]:
        """คำนวณน้ำหนักตาม Risk Parity"""
        try:
            # คำนวณ Inverse Volatility Weights
            volatilities = {}
            for strategy, risk_data in strategy_risks.items():
                vol = risk_data.get('volatility', 0.10)
                # ใช้ inverse volatility สำหรับ Risk Parity
                volatilities[strategy] = 1.0 / vol if vol > 0 else 1.0
            
            # Normalize weights
            total_inv_vol = sum(volatilities.values())
            if total_inv_vol > 0:
                weights = {strategy: inv_vol / total_inv_vol for strategy, inv_vol in volatilities.items()}
            else:
                # Equal weight fallback
                n_strategies = len(strategy_risks)
                weights = {strategy: 1.0 / n_strategies for strategy in strategy_risks.keys()}
            
            # Apply constraints
            constrained_weights = {}
            for strategy, weight in weights.items():
                constrained_weights[strategy] = max(0.05, min(self.max_individual_allocation, weight))
            
            # Renormalize
            total_weight = sum(constrained_weights.values())
            if total_weight > 0:
                constrained_weights = {k: v / total_weight for k, v in constrained_weights.items()}
            
            return constrained_weights
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Risk Parity calculation: {e}")
            # Equal weight fallback
            n_strategies = len(strategy_risks)
            return {strategy: 1.0 / n_strategies for strategy in strategy_risks.keys()}
    
    def _calculate_risk_adjusted_performance(self, risk_data: Dict[str, Any]) -> float:
        """คำนวณประสิทธิภาพที่ปรับด้วยความเสี่ยง"""
        try:
            expected_return = risk_data.get('expected_return', 0.02)
            volatility = risk_data.get('volatility', 0.10)
            max_drawdown = risk_data.get('max_drawdown', 0.05)
            
            # Sharpe Ratio component
            sharpe = expected_return / volatility if volatility > 0 else 0.0
            
            # Calmar Ratio component
            calmar = expected_return / max_drawdown if max_drawdown > 0 else 0.0
            
            # Combined risk-adjusted performance
            risk_adj_perf = (sharpe * 60.0 + calmar * 40.0) / 2.0
            
            return max(0.0, min(100.0, risk_adj_perf * 10.0))
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Risk-Adjusted Performance: {e}")
            return 50.0
    
    def _calculate_risk_efficiency(self, risk_data: Dict[str, Any]) -> float:
        """คำนวณประสิทธิภาพความเสี่ยง"""
        try:
            return_vol_ratio = risk_data.get('expected_return', 0.02) / risk_data.get('volatility', 0.10)
            recovery_rate = risk_data.get('recovery_rate', 95.0) / 100.0
            
            risk_efficiency = (return_vol_ratio * 50.0 + recovery_rate * 50.0)
            
            return max(0.0, min(100.0, risk_efficiency))
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Risk Efficiency: {e}")
            return 50.0
    
    def _create_equal_weight_allocations(self, total_capital: float, 
                                        strategies: List[EntryStrategy]) -> Dict[EntryStrategy, StrategyAllocation]:
        """สร้าง Equal Weight Allocations"""
        if not strategies:
            strategies = list(EntryStrategy)
        
        equal_allocation = total_capital / len(strategies)
        equal_percentage = 100.0 / len(strategies)
        
        allocations = {}
        for strategy in strategies:
            allocations[strategy] = StrategyAllocation(
                strategy=strategy,
                allocated_capital=equal_allocation,
                allocated_percentage=equal_percentage,
                available_capital=equal_allocation,
                strategy_performance=50.0,
                win_rate=50.0,
                profit_factor=1.0,
                sharpe_ratio=0.0,
                capital_efficiency=50.0,
                utilization_rate=0.0,
                performance_trend="STABLE"
            )
        
        return allocations

class SessionBasedAllocator:
    """
    จัดสรรเงินทุนตาม Trading Sessions
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Session Characteristics
        self.session_characteristics = {
            MarketSession.ASIAN: {
                'volatility_multiplier': 0.7,
                'opportunity_factor': 0.6,
                'risk_tolerance': 0.8,
                'typical_volume_percentage': 15.0
            },
            MarketSession.LONDON: {
                'volatility_multiplier': 1.2,
                'opportunity_factor': 1.0,
                'risk_tolerance': 1.1,
                'typical_volume_percentage': 35.0
            },
            MarketSession.NEW_YORK: {
                'volatility_multiplier': 1.1,
                'opportunity_factor': 0.9,
                'risk_tolerance': 1.0,
                'typical_volume_percentage': 30.0
            },
            MarketSession.OVERLAP: {
                'volatility_multiplier': 1.5,
                'opportunity_factor': 1.3,
                'risk_tolerance': 1.2,
                'typical_volume_percentage': 20.0
            }
        }
    
    def calculate_session_allocations(self, total_capital: float,
                                    daily_volume_target: float,
                                    session_performance: Dict[MarketSession, Dict[str, Any]]) -> Dict[MarketSession, SessionAllocation]:
        """
        คำนวณการจัดสรรเงินทุนตาม Trading Sessions
        
        Args:
            total_capital: เงินทุนรวม
            daily_volume_target: เป้าหมาย Volume รายวัน
            session_performance: ข้อมูลประสิทธิภาพของแต่ละ Session
            
        Returns:
            Dict[MarketSession, SessionAllocation]: การจัดสรรตาม Session
        """
        try:
            session_allocations = {}
            
            # คำนวณ Session Weights
            session_weights = self._calculate_session_weights(session_performance)
            
            # คำนวณ Volume Distribution
            volume_distribution = self._calculate_volume_distribution(daily_volume_target, session_performance)
            
            for session in MarketSession:
                characteristics = self.session_characteristics.get(session, {})
                performance = session_performance.get(session, {})
                
                allocated_amount = total_capital * session_weights.get(session, 0.25)
                allocated_percentage = session_weights.get(session, 0.25) * 100
                target_volume = volume_distribution.get(session, daily_volume_target / 4)
                
                session_allocation = SessionAllocation(
                    session=session,
                    allocated_capital=allocated_amount,
                    allocated_percentage=allocated_percentage,
                    target_volume_lots=target_volume,
                    achieved_volume_lots=0.0,  # จะอัพเดทในระหว่างการเทรด
                    
                    # Session Characteristics
                    expected_volatility=characteristics.get('volatility_multiplier', 1.0),
                    expected_opportunities=int(characteristics.get('opportunity_factor', 1.0) * 20),
                    risk_tolerance=characteristics.get('risk_tolerance', 1.0),
                    
                    # Performance
                    session_pnl=0.0,  # จะอัพเดทในระหว่างการเทรด
                    session_efficiency=performance.get('efficiency', 50.0)
                )
                
                session_allocations[session] = session_allocation
            
            self.logger.info(f"📊 คำนวณ Session Allocations สำเร็จ")
            
            return session_allocations
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Session Allocations: {e}")
            return self._create_default_session_allocations(total_capital, daily_volume_target)
    
    def _calculate_session_weights(self, session_performance: Dict[MarketSession, Dict[str, Any]]) -> Dict[MarketSession, float]:
        """คำนวณน้ำหนักการจัดสรรตาม Session Performance"""
        try:
            # คำนวณ Performance Score ของแต่ละ Session
            session_scores = {}
            
            for session in MarketSession:
                performance = session_performance.get(session, {})
                characteristics = self.session_characteristics.get(session, {})
                
                # Base score จาก characteristics
                base_score = characteristics.get('opportunity_factor', 1.0) * 50.0
                
                # Performance adjustment
                win_rate = performance.get('win_rate', 50.0)
                profit_factor = performance.get('profit_factor', 1.0)
                efficiency = performance.get('efficiency', 50.0)
                
                performance_score = (win_rate * 0.4 + (profit_factor - 1.0) * 25.0 + efficiency * 0.35)
                
                # Combined score
                total_score = (base_score * 0.6 + performance_score * 0.4)
                session_scores[session] = max(10.0, total_score)  # ขั้นต่ำ 10%
            
            # Normalize to weights
            total_score = sum(session_scores.values())
            if total_score > 0:
                weights = {session: score / total_score for session, score in session_scores.items()}
            else:
                # Equal weight fallback
                weights = {session: 0.25 for session in MarketSession}
            
            return weights
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Session Weights: {e}")
            return {session: 0.25 for session in MarketSession}
    
    def _calculate_volume_distribution(self, daily_volume_target: float,
                                        session_performance: Dict[MarketSession, Dict[str, Any]]) -> Dict[MarketSession, float]:
        """คำนวณการกระจาย Volume ตาม Sessions"""
        try:
            volume_distribution = {}
            
            # เริ่มจาก typical percentages
            base_distribution = {}
            for session in MarketSession:
                characteristics = self.session_characteristics.get(session, {})
                base_percentage = characteristics.get('typical_volume_percentage', 25.0) / 100.0
                base_distribution[session] = base_percentage
            
            # ปรับตาม performance
            for session in MarketSession:
                performance = session_performance.get(session, {})
                
                # Performance multiplier
                efficiency = performance.get('efficiency', 50.0) / 50.0  # Normalize to 1.0
                volume_achievement = performance.get('volume_achievement_rate', 100.0) / 100.0
                
                performance_multiplier = (efficiency * 0.6 + volume_achievement * 0.4)
                
                # Apply multiplier with limits
                adjusted_percentage = base_distribution[session] * performance_multiplier
                adjusted_percentage = max(0.10, min(0.50, adjusted_percentage))  # 10-50%
                
                volume_distribution[session] = daily_volume_target * adjusted_percentage
            
            # Normalize to target
            total_volume = sum(volume_distribution.values())
            if total_volume > 0:
                normalization_factor = daily_volume_target / total_volume
                volume_distribution = {session: vol * normalization_factor 
                                        for session, vol in volume_distribution.items()}
            
            return volume_distribution
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Volume Distribution: {e}")
            equal_volume = daily_volume_target / len(MarketSession)
            return {session: equal_volume for session in MarketSession}
    
    def _create_default_session_allocations(self, total_capital: float, 
                                            daily_volume_target: float) -> Dict[MarketSession, SessionAllocation]:
        """สร้าง Default Session Allocations"""
        equal_capital = total_capital / len(MarketSession)
        equal_percentage = 100.0 / len(MarketSession)
        equal_volume = daily_volume_target / len(MarketSession)
        
        allocations = {}
        for session in MarketSession:
            characteristics = self.session_characteristics.get(session, {})
            
            allocations[session] = SessionAllocation(
                session=session,
                allocated_capital=equal_capital,
                allocated_percentage=equal_percentage,
                target_volume_lots=equal_volume,
                achieved_volume_lots=0.0,
                expected_volatility=characteristics.get('volatility_multiplier', 1.0),
                expected_opportunities=int(characteristics.get('opportunity_factor', 1.0) * 20),
                risk_tolerance=characteristics.get('risk_tolerance', 1.0),
                session_pnl=0.0,
                session_efficiency=50.0
            )
        
        return allocations

class RecoveryCapitalManager:
    """
    จัดการเงินทุนสำหรับ Recovery System
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.max_recovery_percentage = 20.0  # สูงสุด 20% ของเงินทุนรวม
        self.emergency_reserve_percentage = 5.0  # 5% สำหรับฉุกเฉิน
    
    def calculate_recovery_allocation(self, total_capital: float,
                                    current_positions: List[Dict[str, Any]],
                                    recovery_performance: Dict[str, Any]) -> RecoveryAllocation:
        """
        คำนวณการจัดสรรเงินทุนสำหรับ Recovery System
        
        Args:
            total_capital: เงินทุนรวม
            current_positions: Positions ปัจจุบัน
            recovery_performance: ประสิทธิภาพของ Recovery System
            
        Returns:
            RecoveryAllocation: การจัดสรรเงินทุนสำหรับ Recovery
        """
        try:
            # คำนวณ Recovery Budget
            total_recovery_budget = total_capital * (self.max_recovery_percentage / 100.0)
            
            # คำนวณเงินทุนที่ใช้ไปแล้ว
            allocated_capital = self._calculate_current_recovery_allocation(current_positions)
            
            # คำนวณเงินทุนที่เหลือใช้ได้
            available_capital = max(0.0, total_recovery_budget - allocated_capital)
            
            # คำนวณการจัดสรรตาม Recovery Methods
            method_allocations = self._calculate_method_allocations(
                available_capital, recovery_performance
            )
            
            # คำนวณ Recovery Metrics
            recovery_metrics = self._calculate_recovery_metrics(recovery_performance, current_positions)
            
            recovery_allocation = RecoveryAllocation(
                total_recovery_budget=total_recovery_budget,
                allocated_recovery_capital=allocated_capital,
                available_recovery_capital=available_capital,
                method_allocations=method_allocations,
                
                # Recovery Metrics
                recovery_success_rate=recovery_metrics.get('success_rate', 95.0),
                average_recovery_time=recovery_metrics.get('avg_time', 24.0),
                recovery_efficiency=recovery_metrics.get('efficiency', 80.0),
                
                # Capacity Metrics
                max_concurrent_recoveries=recovery_metrics.get('max_concurrent', 5),
                current_active_recoveries=recovery_metrics.get('active_count', 0),
                recovery_capacity_utilization=recovery_metrics.get('capacity_util', 0.0)
            )
            
            self.logger.info(f"💰 คำนวณ Recovery Allocation สำเร็จ - Budget: ${total_recovery_budget:.2f}")
            
            return recovery_allocation
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Recovery Allocation: {e}")
            return self._create_default_recovery_allocation(total_capital)
    
    def _calculate_current_recovery_allocation(self, current_positions: List[Dict[str, Any]]) -> float:
        """คำนวณเงินทุนที่ใช้ใน Recovery ปัจจุบัน"""
        allocated_capital = 0.0
        
        for position in current_positions:
            if position.get('is_recovery_position', False):
                # คำนวณเงินทุนที่ใช้ในการ Recovery
                volume = position.get('volume', 0.0)
                margin_per_lot = 1000.0  # สมมติ margin requirement
                allocated_capital += volume * margin_per_lot
        
        return allocated_capital
    
    def _calculate_method_allocations(self, available_capital: float,
                                    recovery_performance: Dict[str, Any]) -> Dict[RecoveryMethod, float]:
        """คำนวณการจัดสรรเงินทุนตาม Recovery Methods"""
        try:
            method_allocations = {}
            
            # Base allocations ตาม Recovery Method characteristics
            base_allocations = {
                RecoveryMethod.MARTINGALE_SMART: 0.25,      # 25% - High risk, high reward
                RecoveryMethod.GRID_INTELLIGENT: 0.30,     # 30% - Balanced approach
                RecoveryMethod.HEDGING_ADVANCED: 0.20,     # 20% - Conservative
                RecoveryMethod.AVERAGING_INTELLIGENT: 0.15, # 15% - Moderate risk
                RecoveryMethod.CORRELATION_RECOVERY: 0.10   # 10% - Specialized
            }
            
            # ปรับตาม Performance
            for method, base_allocation in base_allocations.items():
                method_key = method.value.lower()
                
                # ดึง Performance metrics
                method_performance = recovery_performance.get(method_key, {})
                success_rate = method_performance.get('success_rate', 95.0) / 100.0
                efficiency = method_performance.get('efficiency', 80.0) / 100.0
                
                # Performance multiplier
                performance_multiplier = (success_rate * 0.7 + efficiency * 0.3)
                
                # Adjusted allocation
                adjusted_allocation = base_allocation * performance_multiplier
                
                # Apply constraints
                adjusted_allocation = max(0.05, min(0.40, adjusted_allocation))
                
                method_allocations[method] = available_capital * adjusted_allocation
            
            # Normalize allocations
            total_allocated = sum(method_allocations.values())
            if total_allocated > available_capital and total_allocated > 0:
                normalization_factor = available_capital / total_allocated
                method_allocations = {method: allocation * normalization_factor
                                    for method, allocation in method_allocations.items()}
            
            return method_allocations
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Method Allocations: {e}")
            # Equal allocation fallback
            equal_allocation = available_capital / len(RecoveryMethod)
            return {method: equal_allocation for method in RecoveryMethod}
    
    def _calculate_recovery_metrics(self, recovery_performance: Dict[str, Any],
                                    current_positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """คำนวณ Recovery Metrics"""
        try:
            # Active recovery positions
            active_recoveries = [pos for pos in current_positions if pos.get('is_recovery_position', False)]
            active_count = len(active_recoveries)
            
            # Overall metrics
            overall_success_rate = recovery_performance.get('overall_success_rate', 95.0)
            average_recovery_time = recovery_performance.get('average_recovery_time', 24.0)
            
            # Efficiency calculation
            total_recovered = recovery_performance.get('total_recovered_amount', 0.0)
            total_attempted = recovery_performance.get('total_attempted_amount', 1.0)
            efficiency = (total_recovered / total_attempted) * 100.0 if total_attempted > 0 else 80.0
            
            # Capacity utilization
            max_concurrent = 5  # สามารถปรับได้
            capacity_utilization = (active_count / max_concurrent) * 100.0
            
            return {
                'success_rate': overall_success_rate,
                'avg_time': average_recovery_time,
                'efficiency': efficiency,
                'max_concurrent': max_concurrent,
                'active_count': active_count,
                'capacity_util': capacity_utilization
            }
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Recovery Metrics: {e}")
            return {
                'success_rate': 95.0,
                'avg_time': 24.0,
                'efficiency': 80.0,
                'max_concurrent': 5,
                'active_count': 0,
                'capacity_util': 0.0
            }
    
    def _create_default_recovery_allocation(self, total_capital: float) -> RecoveryAllocation:
        """สร้าง Default Recovery Allocation"""
        total_budget = total_capital * (self.max_recovery_percentage / 100.0)
        
        # Default method allocations
        method_allocations = {
            RecoveryMethod.MARTINGALE_SMART: total_budget * 0.25,
            RecoveryMethod.GRID_INTELLIGENT: total_budget * 0.30,
            RecoveryMethod.HEDGING_ADVANCED: total_budget * 0.20,
            RecoveryMethod.AVERAGING_INTELLIGENT: total_budget * 0.15,
            RecoveryMethod.CORRELATION_RECOVERY: total_budget * 0.10
        }
        
        return RecoveryAllocation(
            total_recovery_budget=total_budget,
            allocated_recovery_capital=0.0,
            available_recovery_capital=total_budget,
            method_allocations=method_allocations,
            recovery_success_rate=95.0,
            average_recovery_time=24.0,
            recovery_efficiency=80.0,
            max_concurrent_recoveries=5,
            current_active_recoveries=0,
            recovery_capacity_utilization=0.0
        )

class CapitalAllocator:
    """
    🎯 Main Capital Allocator Class
    
    ระบบจัดสรรเงินทุนแบบอัจฉริยะและครอบคลุม
    รวบรวมการจัดสรรจากทุก Allocator เข้าด้วยกัน
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Initialize Allocators
        self.performance_allocator = PerformanceBasedAllocator()
        self.risk_allocator = RiskAdjustedAllocator()
        self.session_allocator = SessionBasedAllocator()
        self.recovery_manager = RecoveryCapitalManager()
        
        # External Connections
        self.performance_tracker = None   # จะเชื่อมต่อใน start()
        self.risk_calculator = None       # จะเชื่อมต่อใน start()
        self.position_tracker = None      # จะเชื่อมต่อใน start()
        self.recovery_engine = None       # จะเชื่อมต่อใน start()
        
        # Allocation State
        self.current_allocation: Optional[AllocationResult] = None
        self.allocation_history = deque(maxlen=100)
        
        # Rebalancing
        self.last_rebalancing = datetime.now()
        self.rebalancing_frequency = timedelta(hours=1)
        self.auto_rebalancing_enabled = True
        
        # Threading
        self.allocation_monitor_active = False
        self.monitor_thread = None
        self.allocation_lock = threading.Lock()
        
        self.logger.info("💰 เริ่มต้น Capital Allocator")
    
    @handle_trading_errors(ErrorCategory.CAPITAL_ALLOCATION, ErrorSeverity.HIGH)
    async def start_capital_allocator(self) -> None:
        """
        เริ่มต้น Capital Allocator
        """
        self.logger.info("🚀 เริ่มต้น Capital Allocator System")
        
        # เชื่อมต่อ External Components
        try:
            from analytics_engine.performance_tracker import get_performance_tracker
            self.performance_tracker = get_performance_tracker()
            
            from money_management.risk_calculator import get_risk_calculator
            self.risk_calculator = get_risk_calculator()
            
            from position_management.position_tracker import PositionTracker
            self.position_tracker = PositionTracker()
            
            from intelligent_recovery.recovery_engine import get_recovery_engine
            self.recovery_engine = get_recovery_engine()
            
            self.logger.info("✅ เชื่อมต่อ External Components สำเร็จ")
            
        except ImportError as e:
            self.logger.warning(f"⚠️ ไม่สามารถเชื่อมต่อบาง Components: {e}")
        
        # คำนวณ Initial Allocation
        await self._perform_initial_allocation()
        
        # เริ่ม Allocation Monitoring
        await self._start_allocation_monitoring()
        
        self.logger.info("✅ Capital Allocator พร้อมทำงาน")
    
    async def calculate_optimal_allocation(self, allocation_strategy: AllocationStrategy = AllocationStrategy.DYNAMIC_REBALANCING,
                                            total_capital: Optional[float] = None) -> AllocationResult:
        """
        คำนวณการจัดสรรเงินทุนที่เหมาะสมที่สุด
        
        Args:
            allocation_strategy: กลยุทธ์การจัดสรร
            total_capital: เงินทุนรวม (ถ้าไม่ระบุจะใช้จากบัญชี)
            
        Returns:
            AllocationResult: ผลการจัดสรรเงินทุน
        """
        try:
            self.logger.info(f"💰 เริ่มคำนวณการจัดสรรเงินทุน - Strategy: {allocation_strategy.value}")
            
            # ดึงข้อมูลที่จำเป็น
            if total_capital is None:
                total_capital = await self._get_total_capital()
            
            performance_data = await self._get_performance_data()
            risk_data = await self._get_risk_data()
            position_data = await self._get_position_data()
            recovery_data = await self._get_recovery_data()
            market_data = await self._get_market_data()
            
            # คำนวณการจัดสรรตามกลยุทธ์
            if allocation_strategy == AllocationStrategy.PERFORMANCE_BASED:
                strategy_allocations = self.performance_allocator.calculate_strategy_allocations(
                    total_capital * 0.8, performance_data  # 80% สำหรับ trading
                )
                
            elif allocation_strategy == AllocationStrategy.RISK_ADJUSTED:
                correlation_matrix = await self._get_correlation_matrix()
                strategy_allocations = self.risk_allocator.calculate_risk_adjusted_allocations(
                    total_capital * 0.8, risk_data, correlation_matrix
                )
                
            elif allocation_strategy == AllocationStrategy.DYNAMIC_REBALANCING:
                # รวม Performance และ Risk-based allocation
                perf_allocations = self.performance_allocator.calculate_strategy_allocations(
                    total_capital * 0.8, performance_data
                )
                risk_allocations = self.risk_allocator.calculate_risk_adjusted_allocations(
                    total_capital * 0.8, risk_data
                )
                
                # Blend allocations (60% performance, 40% risk)
                strategy_allocations = self._blend_allocations(
                    perf_allocations, risk_allocations, 0.6, 0.4
                )
                
            else:
                # Default to performance-based
                strategy_allocations = self.performance_allocator.calculate_strategy_allocations(
                    total_capital * 0.8, performance_data
                )
            
            # คำนวณ Session Allocations
            session_allocations = self.session_allocator.calculate_session_allocations(
                total_capital * 0.8,
                self.settings.daily_volume_target_max,
                await self._get_session_performance_data()
            )
            
            # คำนวณ Recovery Allocation
            recovery_allocation = self.recovery_manager.calculate_recovery_allocation(
                total_capital, position_data, recovery_data
            )
            
            # สร้าง Category Allocations
            category_allocations = self._create_category_allocations(
                total_capital, strategy_allocations, recovery_allocation
            )
            
            # สร้าง AllocationResult
            allocation_result = AllocationResult(
                allocation_id=f"ALLOC_{int(time.time())}",
                allocation_strategy=allocation_strategy,
                total_capital=total_capital,
                category_allocations=category_allocations,
                strategy_allocations=strategy_allocations,
                session_allocations=session_allocations,
                recovery_allocation=recovery_allocation,
                
                # คำนวณ Overall Metrics
                allocation_efficiency=self._calculate_allocation_efficiency(strategy_allocations, performance_data),
                diversification_score=self._calculate_diversification_score(strategy_allocations),
                risk_utilization=self._calculate_risk_utilization(strategy_allocations, risk_data),
                
                # Rebalancing Analysis
                needs_rebalancing=False,  # จะคำนวณใน _analyze_rebalancing_needs
                rebalancing_urgency="LOW",
                rebalancing_triggers=[],
                
                # Recommendations
                optimization_opportunities=self._identify_optimization_opportunities(strategy_allocations, performance_data),
                allocation_warnings=self._identify_allocation_warnings(strategy_allocations, risk_data),
                
                calculation_timestamp=datetime.now(),
                next_review_time=datetime.now() + self.rebalancing_frequency
            )
            
            # วิเคราะห์ Rebalancing Needs
            allocation_result = self._analyze_rebalancing_needs(allocation_result)
            
            # บันทึกผลลัพธ์
            with self.allocation_lock:
                self.current_allocation = allocation_result
                self.allocation_history.append(allocation_result)
            
            self.logger.info(f"✅ คำนวณการจัดสรรเงินทุนเสร็จสิ้น - Efficiency: {allocation_result.allocation_efficiency:.1f}%")
            
            return allocation_result
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณการจัดสรรเงินทุน: {e}")
            return self._create_fallback_allocation(total_capital or 10000.0)
    
    async def _get_total_capital(self) -> float:
        """ดึงเงินทุนรวมจากบัญชี"""
        try:
            if hasattr(self, 'account_monitor'):
                account_info = await self.account_monitor.get_account_info()
                return account_info.get('equity', 10000.0)
            return 10000.0  # Default
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงเงินทุนรวม: {e}")
            return 10000.0
    
    async def _get_performance_data(self) -> Dict[EntryStrategy, Dict[str, Any]]:
        """ดึงข้อมูลประสิทธิภาพของแต่ละ Strategy"""
        try:
            if self.performance_tracker:
                return self.performance_tracker.get_strategy_performance_breakdown()
            
            # Mock data for testing
            return {
                EntryStrategy.TREND_FOLLOWING: {
                    'win_rate': 65.0, 'profit_factor': 1.4, 'sharpe_ratio': 0.8,
                    'recovery_rate': 95.0, 'consistency_score': 70.0,
                    'total_trades': 50, 'total_volume': 5.0, 'net_profit': 250.0
                },
                EntryStrategy.MEAN_REVERSION: {
                    'win_rate': 58.0, 'profit_factor': 1.2, 'sharpe_ratio': 0.6,
                    'recovery_rate': 92.0, 'consistency_score': 75.0,
                    'total_trades': 45, 'total_volume': 4.5, 'net_profit': 180.0
                },
                EntryStrategy.BREAKOUT_MOMENTUM: {
                    'win_rate': 62.0, 'profit_factor': 1.3, 'sharpe_ratio': 0.7,
                    'recovery_rate': 90.0, 'consistency_score': 65.0,
                    'total_trades': 40, 'total_volume': 4.0, 'net_profit': 200.0
                },
                EntryStrategy.FALSE_BREAKOUT: {
                    'win_rate': 55.0, 'profit_factor': 1.1, 'sharpe_ratio': 0.5,
                    'recovery_rate': 88.0, 'consistency_score': 60.0,
                    'total_trades': 35, 'total_volume': 3.5, 'net_profit': 120.0
                },
                EntryStrategy.NEWS_REACTION: {
                    'win_rate': 60.0, 'profit_factor': 1.5, 'sharpe_ratio': 0.9,
                    'recovery_rate': 85.0, 'consistency_score': 55.0,
                    'total_trades': 25, 'total_volume': 2.5, 'net_profit': 300.0
                },
                EntryStrategy.SCALPING_QUICK: {
                    'win_rate': 52.0, 'profit_factor': 1.05, 'sharpe_ratio': 0.3,
                    'recovery_rate': 98.0, 'consistency_score': 80.0,
                    'total_trades': 100, 'total_volume': 10.0, 'net_profit': 150.0
                }
            }
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Performance: {e}")
            return {}

    async def _get_risk_data(self) -> Dict[EntryStrategy, Dict[str, Any]]:
        """ดึงข้อมูลความเสี่ยงของแต่ละ Strategy"""
        try:
            if self.risk_calculator:
                return self.risk_calculator.get_strategy_risk_breakdown()
            
            # Mock data for testing
            return {
                EntryStrategy.TREND_FOLLOWING: {
                    'expected_return': 0.05, 'volatility': 0.12, 'max_drawdown': 0.08,
                    'var_95': 2.5, 'recovery_rate': 95.0
                },
                EntryStrategy.MEAN_REVERSION: {
                    'expected_return': 0.03, 'volatility': 0.08, 'max_drawdown': 0.05,
                    'var_95': 1.8, 'recovery_rate': 92.0
                },
                EntryStrategy.BREAKOUT_MOMENTUM: {
                    'expected_return': 0.04, 'volatility': 0.15, 'max_drawdown': 0.10,
                    'var_95': 3.2, 'recovery_rate': 90.0
                },
                EntryStrategy.FALSE_BREAKOUT: {
                    'expected_return': 0.02, 'volatility': 0.10, 'max_drawdown': 0.07,
                    'var_95': 2.1, 'recovery_rate': 88.0
                },
                EntryStrategy.NEWS_REACTION: {
                    'expected_return': 0.06, 'volatility': 0.20, 'max_drawdown': 0.12,
                    'var_95': 4.0, 'recovery_rate': 85.0
                },
                EntryStrategy.SCALPING_QUICK: {
                    'expected_return': 0.01, 'volatility': 0.06, 'max_drawdown': 0.03,
                    'var_95': 1.2, 'recovery_rate': 98.0
                }
            }
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Risk: {e}")
            return {}
    
    async def _get_position_data(self) -> List[Dict[str, Any]]:
        """ดึงข้อมูล Positions ปัจจุบัน"""
        try:
            if self.position_tracker:
                return self.position_tracker.get_all_positions()
            return []
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Positions: {e}")
            return []
    
    async def _get_recovery_data(self) -> Dict[str, Any]:
        """ดึงข้อมูล Recovery System"""
        try:
            if self.recovery_engine:
                return {
                    'overall_success_rate': self.recovery_engine.get_success_rate(),
                    'average_recovery_time': self.recovery_engine.get_average_recovery_time(),
                    'total_recovered_amount': self.recovery_engine.get_total_recovered_amount(),
                    'total_attempted_amount': self.recovery_engine.get_total_attempted_amount(),
                    'martingale_smart': {'success_rate': 92.0, 'efficiency': 85.0},
                    'grid_intelligent': {'success_rate': 95.0, 'efficiency': 90.0},
                    'hedging_advanced': {'success_rate': 98.0, 'efficiency': 88.0},
                    'averaging_intelligent': {'success_rate': 94.0, 'efficiency': 87.0},
                    'correlation_recovery': {'success_rate': 89.0, 'efficiency': 82.0}
                }
            
            return {
                'overall_success_rate': 95.0,
                'average_recovery_time': 24.0,
                'total_recovered_amount': 5000.0,
                'total_attempted_amount': 5200.0,
                'martingale_smart': {'success_rate': 92.0, 'efficiency': 85.0},
                'grid_intelligent': {'success_rate': 95.0, 'efficiency': 90.0},
                'hedging_advanced': {'success_rate': 98.0, 'efficiency': 88.0},
                'averaging_intelligent': {'success_rate': 94.0, 'efficiency': 87.0},
                'correlation_recovery': {'success_rate': 89.0, 'efficiency': 82.0}
            }
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Recovery: {e}")
            return {}
    
    async def _get_market_data(self) -> Dict[str, Any]:
        """ดึงข้อมูลสภาพตลาด"""
        try:
            return {
                'current_session': MarketSession.LONDON,
                'volatility_level': 1.2,
                'market_state': 'TRENDING',
                'liquidity_level': 1.0
            }
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Market: {e}")
            return {}
    
    async def _get_session_performance_data(self) -> Dict[MarketSession, Dict[str, Any]]:
        """ดึงข้อมูลประสิทธิภาพของแต่ละ Session"""
        try:
            return {
                MarketSession.ASIAN: {
                    'win_rate': 55.0, 'profit_factor': 1.1, 'efficiency': 60.0,
                    'volume_achievement_rate': 85.0
                },
                MarketSession.LONDON: {
                    'win_rate': 65.0, 'profit_factor': 1.3, 'efficiency': 80.0,
                    'volume_achievement_rate': 95.0
                },
                MarketSession.NEW_YORK: {
                    'win_rate': 62.0, 'profit_factor': 1.25, 'efficiency': 75.0,
                    'volume_achievement_rate': 90.0
                },
                MarketSession.OVERLAP: {
                    'win_rate': 68.0, 'profit_factor': 1.4, 'efficiency': 85.0,
                    'volume_achievement_rate': 100.0
                }
            }
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Session Performance: {e}")
            return {}
    
    async def _get_correlation_matrix(self) -> Optional[np.ndarray]:
        """ดึง Correlation Matrix ระหว่าง Strategies"""
        try:
            if self.risk_calculator:
                # สร้าง mock correlation matrix
                n_strategies = len(EntryStrategy)
                correlation_matrix = np.eye(n_strategies)
                
                # เพิ่ม correlation ระหว่าง strategies ที่คล้ายกัน
                strategies = list(EntryStrategy)
                for i, strategy1 in enumerate(strategies):
                    for j, strategy2 in enumerate(strategies):
                        if i != j:
                            correlation = self._estimate_strategy_correlation(strategy1, strategy2)
                            correlation_matrix[i, j] = correlation
                
                return correlation_matrix
            
            return None
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึง Correlation Matrix: {e}")
            return None
    
    def _estimate_strategy_correlation(self, strategy1: EntryStrategy, strategy2: EntryStrategy) -> float:
        """ประมาณ correlation ระหว่าง 2 strategies"""
        # Correlation pairs based on strategy characteristics
        high_correlation_pairs = [
            (EntryStrategy.TREND_FOLLOWING, EntryStrategy.BREAKOUT_MOMENTUM),
            (EntryStrategy.MEAN_REVERSION, EntryStrategy.FALSE_BREAKOUT),
        ]
        
        medium_correlation_pairs = [
            (EntryStrategy.NEWS_REACTION, EntryStrategy.BREAKOUT_MOMENTUM),
            (EntryStrategy.SCALPING_QUICK, EntryStrategy.MEAN_REVERSION),
        ]
        
        if (strategy1, strategy2) in high_correlation_pairs or (strategy2, strategy1) in high_correlation_pairs:
            return 0.6
        elif (strategy1, strategy2) in medium_correlation_pairs or (strategy2, strategy1) in medium_correlation_pairs:
            return 0.3
        else:
            return 0.1  # Low correlation
    
    def _blend_allocations(self, alloc1: Dict[EntryStrategy, StrategyAllocation],
                            alloc2: Dict[EntryStrategy, StrategyAllocation],
                            weight1: float, weight2: float) -> Dict[EntryStrategy, StrategyAllocation]:
        """ผสมการจัดสรรจาก 2 วิธี"""
        blended_allocations = {}
        
        for strategy in EntryStrategy:
            allocation1 = alloc1.get(strategy)
            allocation2 = alloc2.get(strategy)
            
            if allocation1 and allocation2:
                # Blend the allocations
                blended_capital = (allocation1.allocated_capital * weight1 + 
                                    allocation2.allocated_capital * weight2)
                blended_percentage = (allocation1.allocated_percentage * weight1 + 
                                    allocation2.allocated_percentage * weight2)
                
                # เลือก metrics ที่ดีที่สุด
                better_allocation = allocation1 if allocation1.strategy_performance > allocation2.strategy_performance else allocation2
                
                blended_allocation = StrategyAllocation(
                    strategy=strategy,
                    allocated_capital=blended_capital,
                    allocated_percentage=blended_percentage,
                    available_capital=blended_capital,
                    
                    # Use better performance metrics
                    strategy_performance=better_allocation.strategy_performance,
                    win_rate=better_allocation.win_rate,
                    profit_factor=better_allocation.profit_factor,
                    sharpe_ratio=better_allocation.sharpe_ratio,
                    capital_efficiency=better_allocation.capital_efficiency,
                    utilization_rate=0.0,
                    performance_trend=better_allocation.performance_trend
                )
                
                blended_allocations[strategy] = blended_allocation
            
            elif allocation1:
                blended_allocations[strategy] = allocation1
            elif allocation2:
                blended_allocations[strategy] = allocation2
        
        return blended_allocations
    
    def _create_category_allocations(self, total_capital: float,
                                    strategy_allocations: Dict[EntryStrategy, StrategyAllocation],
                                    recovery_allocation: RecoveryAllocation) -> Dict[AllocationCategory, AllocationTarget]:
        """สร้าง Category Allocations"""
        category_allocations = {}
        
        # Trading Capital (80% of total)
        trading_capital = sum(alloc.allocated_capital for alloc in strategy_allocations.values())
        trading_percentage = (trading_capital / total_capital) * 100
        
        category_allocations[AllocationCategory.TRADING_CAPITAL] = AllocationTarget(
            category=AllocationCategory.TRADING_CAPITAL,
            target_percentage=80.0,
            current_percentage=trading_percentage,
            target_amount=total_capital * 0.8,
            current_amount=trading_capital,
            min_percentage=60.0,
            max_percentage=85.0,
            allocation_efficiency=85.0
        )
        
        # Recovery Reserve (15% of total)
        recovery_percentage = (recovery_allocation.total_recovery_budget / total_capital) * 100
        
        category_allocations[AllocationCategory.RECOVERY_RESERVE] = AllocationTarget(
            category=AllocationCategory.RECOVERY_RESERVE,
            target_percentage=15.0,
            current_percentage=recovery_percentage,
            target_amount=total_capital * 0.15,
            current_amount=recovery_allocation.total_recovery_budget,
            min_percentage=10.0,
            max_percentage=25.0,
            allocation_efficiency=recovery_allocation.recovery_efficiency
        )
        
        # Emergency Fund (5% of total)
        emergency_amount = total_capital * 0.05
        
        category_allocations[AllocationCategory.EMERGENCY_FUND] = AllocationTarget(
            category=AllocationCategory.EMERGENCY_FUND,
            target_percentage=5.0,
            current_percentage=5.0,
            target_amount=emergency_amount,
            current_amount=emergency_amount,
            min_percentage=5.0,
            max_percentage=10.0,
            allocation_efficiency=100.0  # Emergency fund is always 100% efficient
        )
        
        return category_allocations
    
    def _calculate_allocation_efficiency(self, strategy_allocations: Dict[EntryStrategy, StrategyAllocation],
                                        performance_data: Dict[EntryStrategy, Dict[str, Any]]) -> float:
        """คำนวณประสิทธิภาพการจัดสรรรวม"""
        try:
            if not strategy_allocations:
                return 0.0
            
            total_allocation = sum(alloc.allocated_capital for alloc in strategy_allocations.values())
            weighted_efficiency = 0.0
            
            for strategy, allocation in strategy_allocations.items():
                weight = allocation.allocated_capital / total_allocation if total_allocation > 0 else 0.0
                
                # Strategy efficiency based on performance
                perf_data = performance_data.get(strategy, {})
                win_rate = perf_data.get('win_rate', 50.0)
                profit_factor = perf_data.get('profit_factor', 1.0)
                recovery_rate = perf_data.get('recovery_rate', 95.0)
                
                strategy_efficiency = (win_rate * 0.4 + (profit_factor - 1.0) * 25.0 + recovery_rate * 0.35)
                weighted_efficiency += weight * strategy_efficiency
            
            return max(0.0, min(100.0, weighted_efficiency))
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Allocation Efficiency: {e}")
            return 50.0
    
    def _calculate_diversification_score(self, strategy_allocations: Dict[EntryStrategy, StrategyAllocation]) -> float:
        """คำนวณคะแนน Diversification"""
        try:
            if not strategy_allocations:
                return 0.0
            
            # คำนวณ Herfindahl-Hirschman Index
            total_allocation = sum(alloc.allocated_capital for alloc in strategy_allocations.values())
            
            if total_allocation == 0:
                return 0.0
            
            weights = [alloc.allocated_capital / total_allocation for alloc in strategy_allocations.values()]
            hhi = sum(w ** 2 for w in weights)
            
            # แปลงเป็น Diversification Score (0-100)
            # HHI = 1/n สำหรับ perfectly diversified
            n_strategies = len(strategy_allocations)
            perfect_diversification_hhi = 1.0 / n_strategies
            
            # คะแนน Diversification
            if hhi <= perfect_diversification_hhi:
                diversification_score = 100.0
            else:
                # ยิ่ง HHI สูง = Diversification ต่ำ
                diversification_score = max(0.0, 100.0 * (1.0 - hhi) / (1.0 - perfect_diversification_hhi))
            
            return diversification_score
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Diversification Score: {e}")
            return 50.0
    
    def _calculate_risk_utilization(self, strategy_allocations: Dict[EntryStrategy, StrategyAllocation],
                                    risk_data: Dict[EntryStrategy, Dict[str, Any]]) -> float:
        """คำนวณการใช้ Risk Budget"""
        try:
            total_allocation = sum(alloc.allocated_capital for alloc in strategy_allocations.values())
            total_risk = 0.0
            
            for strategy, allocation in strategy_allocations.items():
                weight = allocation.allocated_capital / total_allocation if total_allocation > 0 else 0.0
                strategy_risk = risk_data.get(strategy, {}).get('volatility', 0.10)
                total_risk += weight * strategy_risk
            
            # สมมติ Risk Budget = 15% volatility
            risk_budget = 0.15
            risk_utilization = (total_risk / risk_budget) * 100.0 if risk_budget > 0 else 0.0
            
            return min(100.0, risk_utilization)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Risk Utilization: {e}")
            return 50.0
    
    def _identify_optimization_opportunities(self, strategy_allocations: Dict[EntryStrategy, StrategyAllocation],
                                            performance_data: Dict[EntryStrategy, Dict[str, Any]]) -> List[str]:
        """ระบุโอกาสในการเพิ่มประสิทธิภาพ"""
        opportunities = []
        
        try:
            # หา Strategy ที่มี Performance ดีแต่ได้ Allocation น้อย
            for strategy, allocation in strategy_allocations.items():
                perf_data = performance_data.get(strategy, {})
                
                win_rate = perf_data.get('win_rate', 50.0)
                profit_factor = perf_data.get('profit_factor', 1.0)
                allocation_percentage = allocation.allocated_percentage
                
                # High performance, low allocation
                if win_rate > 60.0 and profit_factor > 1.2 and allocation_percentage < 15.0:
                    opportunities.append(f"💡 เพิ่ม allocation ให้ {strategy.value} (Performance ดี แต่ allocation ต่ำ)")
                
                # Low performance, high allocation
                elif win_rate < 50.0 and allocation_percentage > 20.0:
                    opportunities.append(f"⚠️ ลด allocation ของ {strategy.value} (Performance ต่ำ แต่ allocation สูง)")
                
                # High recovery rate strategy
                recovery_rate = perf_data.get('recovery_rate', 95.0)
                if recovery_rate > 98.0 and allocation_percentage < 20.0:
                    opportunities.append(f"🔄 เพิ่ม allocation ให้ {strategy.value} (Recovery rate สูงมาก)")
            
            # Portfolio-level opportunities
            total_strategies = len([alloc for alloc in strategy_allocations.values() if alloc.allocated_percentage > 5.0])
            if total_strategies < 4:
                opportunities.append("📊 เพิ่ม Diversification ด้วยการใช้ Strategy หลากหลายมากขึ้น")
            
            # Volume efficiency
            high_volume_strategies = [s for s, alloc in strategy_allocations.items() 
                                    if performance_data.get(s, {}).get('total_volume', 0) > 5.0]
            if len(high_volume_strategies) < 3:
                opportunities.append("📈 เน้น Strategy ที่สร้าง Volume สูงเพื่อเพิ่ม Rebate")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการระบุ Optimization Opportunities: {e}")
        
        return opportunities[:5]  # จำกัดไม่เกิน 5 opportunities
    
    def _identify_allocation_warnings(self, strategy_allocations: Dict[EntryStrategy, StrategyAllocation],
                                    risk_data: Dict[EntryStrategy, Dict[str, Any]]) -> List[str]:
        """ระบุคำเตือนเกี่ยวกับการจัดสรร"""
        warnings = []
        
        try:
            # ตรวจสอบ Over-concentration
            for strategy, allocation in strategy_allocations.items():
                if allocation.allocated_percentage > 35.0:
                    warnings.append(f"⚠️ {strategy.value} มี allocation สูงเกินไป ({allocation.allocated_percentage:.1f}%)")
            
            # ตรวจสอบ High-risk strategies
            for strategy, allocation in strategy_allocations.items():
                risk_info = risk_data.get(strategy, {})
                volatility = risk_info.get('volatility', 0.10)
                max_drawdown = risk_info.get('max_drawdown', 0.05)
                
                if volatility > 0.18 and allocation.allocated_percentage > 25.0:
                    warnings.append(f"🚨 {strategy.value} มี Volatility สูง ({volatility:.1%}) และ allocation มาก")
                
                if max_drawdown > 0.10 and allocation.allocated_percentage > 20.0:
                    warnings.append(f"📉 {strategy.value} มี Max Drawdown สูง ({max_drawdown:.1%})")
            
            # ตรวจสอบ Under-diversification
            active_strategies = len([alloc for alloc in strategy_allocations.values() 
                                    if alloc.allocated_percentage > 10.0])
            if active_strategies < 3:
                warnings.append("📊 Portfolio ขาด Diversification - ควรกระจาย Strategy มากขึ้น")
            
            # ตรวจสอบ Total risk
            total_risk = sum(allocation.allocated_percentage * risk_data.get(strategy, {}).get('volatility', 0.10) / 100.0
                            for strategy, allocation in strategy_allocations.items())
            if total_risk > 0.20:  # 20% portfolio volatility
                warnings.append(f"⚠️ Portfolio Risk สูงเกินไป (Volatility: {total_risk:.1%})")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการระบุ Allocation Warnings: {e}")
        
        return warnings[:5]  # จำกัดไม่เกิน 5 warnings
    
    def _analyze_rebalancing_needs(self, allocation_result: AllocationResult) -> AllocationResult:
        """วิเคราะห์ความจำเป็นในการ Rebalancing"""
        try:
            rebalancing_triggers = []
            urgency = "LOW"
            needs_rebalancing = False
            
            if self.current_allocation is None:
                # ครั้งแรก ไม่ต้อง rebalance
                allocation_result.needs_rebalancing = False
                allocation_result.rebalancing_urgency = "LOW"
                return allocation_result
            
            current_alloc = self.current_allocation
            
            # 1. Time-based trigger
            time_since_last = datetime.now() - self.last_rebalancing
            if time_since_last >= self.rebalancing_frequency:
                rebalancing_triggers.append(RebalancingTrigger.TIME_BASED)
                needs_rebalancing = True
            
            # 2. Performance threshold trigger
            current_efficiency = allocation_result.allocation_efficiency
            previous_efficiency = current_alloc.allocation_efficiency
            efficiency_change = abs(current_efficiency - previous_efficiency)
            
            if efficiency_change > 10.0:  # เปลี่ยนแปลงมากกว่า 10%
                rebalancing_triggers.append(RebalancingTrigger.PERFORMANCE_THRESHOLD)
                needs_rebalancing = True
                if efficiency_change > 20.0:
                    urgency = "HIGH"
                elif efficiency_change > 15.0:
                    urgency = "MEDIUM"
            
            # 3. Allocation drift trigger
            max_drift = 0.0
            for strategy in EntryStrategy:
                current_pct = allocation_result.strategy_allocations.get(strategy, StrategyAllocation(strategy=strategy)).allocated_percentage
                previous_pct = current_alloc.strategy_allocations.get(strategy, StrategyAllocation(strategy=strategy)).allocated_percentage
                drift = abs(current_pct - previous_pct)
                max_drift = max(max_drift, drift)
            
            if max_drift > 5.0:  # Drift มากกว่า 5%
                rebalancing_triggers.append(RebalancingTrigger.ALLOCATION_DRIFT)
                needs_rebalancing = True
                if max_drift > 15.0:
                    urgency = "CRITICAL"
                elif max_drift > 10.0:
                    urgency = "HIGH"
            
            # 4. Risk threshold trigger
            current_risk = allocation_result.risk_utilization
            previous_risk = current_alloc.risk_utilization
            risk_change = abs(current_risk - previous_risk)
            
            if risk_change > 15.0:  # Risk เปลี่ยนแปลงมากกว่า 15%
                rebalancing_triggers.append(RebalancingTrigger.RISK_THRESHOLD)
                needs_rebalancing = True
                if risk_change > 30.0:
                    urgency = "CRITICAL"
            
            # Update allocation result
            allocation_result.needs_rebalancing = needs_rebalancing
            allocation_result.rebalancing_urgency = urgency
            allocation_result.rebalancing_triggers = rebalancing_triggers
            
            return allocation_result
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์ Rebalancing: {e}")
            allocation_result.needs_rebalancing = False
            allocation_result.rebalancing_urgency = "LOW"
            return allocation_result
    
    def _create_fallback_allocation(self, total_capital: float) -> AllocationResult:
        """สร้าง Fallback Allocation"""
        # Equal allocation across all strategies
        n_strategies = len(EntryStrategy)
        equal_capital = (total_capital * 0.8) / n_strategies  # 80% for trading
        equal_percentage = 80.0 / n_strategies
        
        strategy_allocations = {}
        for strategy in EntryStrategy:
            strategy_allocations[strategy] = StrategyAllocation(
                strategy=strategy,
                allocated_capital=equal_capital,
                allocated_percentage=equal_percentage,
                available_capital=equal_capital,
                strategy_performance=50.0,
                win_rate=50.0,
                profit_factor=1.0,
                sharpe_ratio=0.0,
                capital_efficiency=50.0,
                utilization_rate=0.0,
                performance_trend="STABLE"
            )
        
        # Recovery allocation
        recovery_allocation = RecoveryAllocation(
            total_recovery_budget=total_capital * 0.15,
            allocated_recovery_capital=0.0,
            available_recovery_capital=total_capital * 0.15,
            recovery_success_rate=95.0,
            average_recovery_time=24.0,
            recovery_efficiency=80.0
        )
        
        # Category allocations
        category_allocations = {
            AllocationCategory.TRADING_CAPITAL: AllocationTarget(
                category=AllocationCategory.TRADING_CAPITAL,
                target_percentage=80.0,
                current_percentage=80.0,
                target_amount=total_capital * 0.8,
                current_amount=total_capital * 0.8
            ),
            AllocationCategory.RECOVERY_RESERVE: AllocationTarget(
                category=AllocationCategory.RECOVERY_RESERVE,
                target_percentage=15.0,
                current_percentage=15.0,
                target_amount=total_capital * 0.15,
                current_amount=total_capital * 0.15
            ),
            AllocationCategory.EMERGENCY_FUND: AllocationTarget(
                category=AllocationCategory.EMERGENCY_FUND,
                target_percentage=5.0,
                current_percentage=5.0,
                target_amount=total_capital * 0.05,
                current_amount=total_capital * 0.05
            )
        }
        
        return AllocationResult(
            allocation_id=f"FALLBACK_{int(time.time())}",
            allocation_strategy=AllocationStrategy.EQUAL_WEIGHT,
            total_capital=total_capital,
            category_allocations=category_allocations,
            strategy_allocations=strategy_allocations,
            session_allocations={},
            recovery_allocation=recovery_allocation,
            allocation_efficiency=50.0,
            diversification_score=85.0,  # Equal weight = high diversification
            risk_utilization=50.0,
            needs_rebalancing=False,
            rebalancing_urgency="LOW",
            rebalancing_triggers=[],
            optimization_opportunities=["📊 ปรับปรุงการจัดสรรตาม Performance"],
            allocation_warnings=["⚠️ ใช้ Fallback allocation - ตรวจสอบการเชื่อมต่อระบบ"],
            calculation_timestamp=datetime.now(),
            next_review_time=datetime.now() + timedelta(hours=1)
        )

    async def _perform_initial_allocation(self) -> None:
        """ทำการจัดสรรเริ่มต้น"""
        try:
            self.logger.info("🔄 ทำการจัดสรรเงินทุนเริ่มต้น...")
            
            initial_allocation = await self.calculate_optimal_allocation(
                AllocationStrategy.DYNAMIC_REBALANCING
            )
            
            self.logger.info(f"✅ จัดสรรเงินทุนเริ่มต้นเสร็จสิ้น - Efficiency: {initial_allocation.allocation_efficiency:.1f}%")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการจัดสรรเริ่มต้น: {e}")
    
    async def _start_allocation_monitoring(self) -> None:
        """เริ่ม Allocation Monitoring แบบต่อเนื่อง"""
        if self.allocation_monitor_active:
            return
        
        self.allocation_monitor_active = True
        self.monitor_thread = threading.Thread(target=self._allocation_monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("📊 เริ่ม Allocation Monitoring แบบต่อเนื่อง")
    
    def _allocation_monitoring_loop(self) -> None:
        """Allocation Monitoring Loop"""
        try:
            while self.allocation_monitor_active:
                # ตรวจสอบการ Rebalancing ทุก 15 นาที
                if self.auto_rebalancing_enabled and self.current_allocation:
                    time_since_last = datetime.now() - self.last_rebalancing
                    
                    # Auto rebalancing ตาม schedule
                    if time_since_last >= self.rebalancing_frequency:
                        self.logger.info("🔄 เริ่ม Auto Rebalancing...")
                        
                        try:
                            new_allocation = asyncio.run(self.calculate_optimal_allocation())
                            
                            if new_allocation.needs_rebalancing:
                                asyncio.run(self.execute_rebalancing(new_allocation))
                            
                        except Exception as e:
                            self.logger.error(f"❌ ข้อผิดพลาดใน Auto Rebalancing: {e}")
                
                time.sleep(900)  # รอ 15 นาที
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Allocation Monitoring Loop: {e}")
        finally:
            self.allocation_monitor_active = False
    
    async def execute_rebalancing(self, new_allocation: AllocationResult) -> bool:
        """
        ดำเนินการ Rebalancing จริง
        
        Args:
            new_allocation: การจัดสรรใหม่
            
        Returns:
            bool: สำเร็จหรือไม่
        """
        try:
            self.logger.info(f"🔄 เริ่มดำเนินการ Rebalancing - Urgency: {new_allocation.rebalancing_urgency}")
            
            if not new_allocation.needs_rebalancing:
                self.logger.info("ℹ️ ไม่จำเป็นต้อง Rebalancing")
                return True
            
            # 1. ตรวจสอบเงื่อนไขก่อน Rebalancing
            if not await self._validate_rebalancing_conditions(new_allocation):
                self.logger.warning("⚠️ เงื่อนไขไม่เหมาะสมสำหรับ Rebalancing")
                return False
            
            # 2. คำนวณการเปลี่ยนแปลง
            changes = self._calculate_allocation_changes(self.current_allocation, new_allocation)
            
            # 3. ดำเนินการปรับ Allocations
            success = await self._apply_allocation_changes(changes)
            
            if success:
                # 4. อัพเดท Current Allocation
                with self.allocation_lock:
                    self.current_allocation = new_allocation
                    self.last_rebalancing = datetime.now()
                
                self.logger.info("✅ Rebalancing สำเร็จ")
                
                # 5. แจ้งเตือน External Systems
                await self._notify_rebalancing_complete(new_allocation)
                
                return True
            else:
                self.logger.error("❌ Rebalancing ไม่สำเร็จ")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการ Rebalancing: {e}")
            return False
    
    async def _validate_rebalancing_conditions(self, new_allocation: AllocationResult) -> bool:
        """ตรวจสอบเงื่อนไขสำหรับ Rebalancing"""
        try:
            # 1. ตรวจสอบ Market Conditions
            market_data = await self._get_market_data()
            volatility = market_data.get('volatility_level', 1.0)
            
            if volatility > 2.0:  # Volatility สูงมาก
                self.logger.warning("⚠️ Market Volatility สูงเกินไป - เลื่อน Rebalancing")
                return False
            
            # 2. ตรวจสอบ Active Positions
            positions = await self._get_position_data()
            active_positions = len(positions)
            
            if active_positions > 20:  # Positions เยอะเกินไป
                self.logger.warning("⚠️ Active Positions เยอะเกินไป - เลื่อน Rebalancing")
                return False
            
            # 3. ตรวจสอบ Recovery Activities
            recovery_data = await self._get_recovery_data()
            active_recoveries = recovery_data.get('active_tasks', 0)
            
            if active_recoveries > 5:  # Recovery Activities เยอะเกินไป
                self.logger.warning("⚠️ Recovery Activities เยอะเกินไป - เลื่อน Rebalancing")
                return False
            
            # 4. ตรวจสอบ Trading Session
            current_hour = datetime.now().hour
            if 6 <= current_hour <= 8:  # ช่วงเปลี่ยน Session
                self.logger.warning("⚠️ ช่วงเปลี่ยน Trading Session - เลื่อน Rebalancing")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจสอบเงื่อนไข Rebalancing: {e}")
            return False
    
    def _calculate_allocation_changes(self, current_allocation: Optional[AllocationResult],
                                    new_allocation: AllocationResult) -> Dict[str, Any]:
        """คำนวณการเปลี่ยนแปลงการจัดสรร"""
        changes = {
            'strategy_changes': {},
            'session_changes': {},
            'recovery_changes': {},
            'total_changes': 0.0
        }
        
        try:
            if current_allocation is None:
                # ครั้งแรก - ทุก allocation เป็น change
                for strategy, allocation in new_allocation.strategy_allocations.items():
                    changes['strategy_changes'][strategy] = {
                        'from': 0.0,
                        'to': allocation.allocated_capital,
                        'change': allocation.allocated_capital,
                        'change_percentage': 100.0
                    }
                return changes
            
            # คำนวณการเปลี่ยนแปลง Strategy Allocations
            for strategy in EntryStrategy:
                current_alloc = current_allocation.strategy_allocations.get(strategy)
                new_alloc = new_allocation.strategy_allocations.get(strategy)
                
                current_capital = current_alloc.allocated_capital if current_alloc else 0.0
                new_capital = new_alloc.allocated_capital if new_alloc else 0.0
                
                change = new_capital - current_capital
                change_percentage = (change / current_capital) * 100.0 if current_capital > 0 else 0.0
                
                if abs(change) > 100.0:  # เปลี่ยนแปลงมากกว่า $100
                    changes['strategy_changes'][strategy] = {
                        'from': current_capital,
                        'to': new_capital,
                        'change': change,
                        'change_percentage': change_percentage
                    }
                    changes['total_changes'] += abs(change)
            
            # คำนวณการเปลี่ยนแปลง Session Allocations
            for session in MarketSession:
                current_session = current_allocation.session_allocations.get(session)
                new_session = new_allocation.session_allocations.get(session)
                
                if current_session and new_session:
                    change = new_session.allocated_capital - current_session.allocated_capital
                    if abs(change) > 50.0:  # เปลี่ยนแปลงมากกว่า $50
                        changes['session_changes'][session] = {
                            'from': current_session.allocated_capital,
                            'to': new_session.allocated_capital,
                            'change': change
                        }
            
            # คำนวณการเปลี่ยนแปลง Recovery Allocation
            if current_allocation.recovery_allocation and new_allocation.recovery_allocation:
                current_recovery = current_allocation.recovery_allocation.total_recovery_budget
                new_recovery = new_allocation.recovery_allocation.total_recovery_budget
                change = new_recovery - current_recovery
                
                if abs(change) > 100.0:
                    changes['recovery_changes'] = {
                        'from': current_recovery,
                        'to': new_recovery,
                        'change': change
                    }
            
            return changes
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Allocation Changes: {e}")
            return changes
    
    async def _apply_allocation_changes(self, changes: Dict[str, Any]) -> bool:
        """ปรับใช้การเปลี่ยนแปลงการจัดสรร"""
        try:
            # ในระบบจริง จะต้องเชื่อมต่อกับ Position Sizer และ Trading System
            # เพื่อปรับ Position Sizes และ Allocation Limits
            
            strategy_changes = changes.get('strategy_changes', {})
            total_changes = changes.get('total_changes', 0.0)
            
            if total_changes == 0:
                return True
            
            self.logger.info(f"📊 ปรับใช้การเปลี่ยนแปลง Allocation - Total: ${total_changes:.2f}")
            
            # จำลองการปรับ Allocation
            for strategy, change_info in strategy_changes.items():
                change = change_info['change']
                self.logger.info(f"   {strategy.value}: ${change:+.2f}")
            
            # ในระบบจริงจะต้อง:
            # 1. อัพเดท Position Sizer limits
            # 2. ปรับ Risk Calculator parameters
            # 3. แจ้ง Entry Generators ให้ปรับ Frequency
            # 4. อัพเดท Recovery Engine budgets
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการปรับใช้ Allocation Changes: {e}")
            return False
    
    async def _notify_rebalancing_complete(self, new_allocation: AllocationResult) -> None:
        """แจ้งเตือนเมื่อ Rebalancing เสร็จสิ้น"""
        try:
            # แจ้งเตือน External Systems
            if hasattr(self, 'position_sizer'):
                await self.position_sizer.update_allocation_limits(new_allocation.strategy_allocations)
            
            if hasattr(self, 'recovery_engine'):
                await self.recovery_engine.update_recovery_budget(new_allocation.recovery_allocation)
            
            self.logger.info("📢 แจ้งเตือน External Systems เรียบร้อย")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการแจ้งเตือน: {e}")
    
    def get_current_allocation(self) -> Optional[AllocationResult]:
        """ดึงการจัดสรรปัจจุบัน"""
        with self.allocation_lock:
            return self.current_allocation
    
    def get_allocation_statistics(self) -> Dict[str, Any]:
        """ดึงสถิติการจัดสรร"""
        try:
            if self.current_allocation is None:
                return {"status": "ไม่มีการจัดสรร"}
            
            current = self.current_allocation
            
            return {
                "current_allocation": {
                    "allocation_id": current.allocation_id,
                    "strategy": current.allocation_strategy.value,
                    "total_capital": current.total_capital,
                    "efficiency": current.allocation_efficiency,
                    "diversification": current.diversification_score,
                    "risk_utilization": current.risk_utilization
                },
                "rebalancing_status": {
                    "needs_rebalancing": current.needs_rebalancing,
                    "urgency": current.rebalancing_urgency,
                    "last_rebalancing": self.last_rebalancing.isoformat(),
                    "next_review": current.next_review_time.isoformat(),
                    "auto_enabled": self.auto_rebalancing_enabled
                },
                "allocation_breakdown": {
                    "strategy_count": len(current.strategy_allocations),
                    "session_count": len(current.session_allocations),
                    "recovery_budget": current.recovery_allocation.total_recovery_budget if current.recovery_allocation else 0.0
                },
                "history": {
                    "total_allocations": len(self.allocation_history),
                    "monitoring_active": self.allocation_monitor_active
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงสถิติ: {e}")
            return {"error": str(e)}
    
    def stop_capital_allocator(self) -> None:
        """หยุด Capital Allocator"""
        self.allocation_monitor_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("🛑 หยุด Capital Allocator")
    
    def set_auto_rebalancing(self, enabled: bool) -> None:
        """เปิด/ปิด Auto Rebalancing"""
        self.auto_rebalancing_enabled = enabled
        status = "เปิด" if enabled else "ปิด"
        self.logger.info(f"⚙️ {status} Auto Rebalancing")
    
    def set_rebalancing_frequency(self, frequency: timedelta) -> None:
        """ตั้งค่าความถี่ Rebalancing"""
        self.rebalancing_frequency = frequency
        self.logger.info(f"⏰ ตั้งค่า Rebalancing Frequency: {frequency}")

# Global Capital Allocator Instance
_global_capital_allocator: Optional[CapitalAllocator] = None

def get_capital_allocator() -> CapitalAllocator:
    """
    ดึง Capital Allocator Instance (Singleton Pattern)
    
    Returns:
        CapitalAllocator: Instance ของ Capital Allocator
    """
    global _global_capital_allocator
    
    if _global_capital_allocator is None:
        _global_capital_allocator = CapitalAllocator()
    
    return _global_capital_allocator

# Utility Functions
async def quick_allocation_analysis(allocation_strategy: AllocationStrategy = AllocationStrategy.DYNAMIC_REBALANCING) -> AllocationResult:
    """
    วิเคราะห์การจัดสรรแบบเร็ว
    
    Args:
        allocation_strategy: กลยุทธ์การจัดสรร
        
    Returns:
        AllocationResult: ผลการจัดสรร
    """
    allocator = get_capital_allocator()
    return await allocator.calculate_optimal_allocation(allocation_strategy)

def get_strategy_allocation_recommendation(strategy: EntryStrategy, 
                                        performance_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ให้คำแนะนำการจัดสรรสำหรับ Strategy เฉพาะ
    
    Args:
        strategy: Strategy ที่ต้องการคำแนะนำ
        performance_data: ข้อมูลประสิทธิภาพ
        
    Returns:
        Dict: คำแนะนำการจัดสรร
    """
    try:
        win_rate = performance_data.get('win_rate', 50.0)
        profit_factor = performance_data.get('profit_factor', 1.0)
        recovery_rate = performance_data.get('recovery_rate', 95.0)
        volatility = performance_data.get('volatility', 0.10)
        
        # คำนวณ Recommended Allocation Percentage
        base_allocation = 15.0  # Base 15%
        
        # ปรับตาม Win Rate
        if win_rate > 60:
            base_allocation += 5.0
        elif win_rate < 45:
            base_allocation -= 5.0
        
        # ปรับตาม Profit Factor
        if profit_factor > 1.3:
            base_allocation += 5.0
        elif profit_factor < 1.1:
            base_allocation -= 5.0
        
        # ปรับตาม Recovery Rate
        if recovery_rate > 95:
            base_allocation += 3.0
        elif recovery_rate < 90:
            base_allocation -= 3.0
        
        # ปรับตาม Volatility
        if volatility > 0.15:
            base_allocation -= 3.0
        elif volatility < 0.08:
            base_allocation += 2.0
        
        # จำกัดขีดจำกัด
        recommended_percentage = max(5.0, min(35.0, base_allocation))
        
        # สร้างคำแนะนำ
        recommendations = []
        
        if recommended_percentage > 25:
            recommendations.append("⭐ Strategy นี้มี Performance ดีเยี่ยม - เหมาะสำหรับ allocation สูง")
        elif recommended_percentage > 15:
            recommendations.append("✅ Strategy นี้มี Performance ดี - เหมาะสำหรับ allocation ปานกลาง")
        elif recommended_percentage > 8:
            recommendations.append("⚠️ Strategy นี้มี Performance ปานกลาง - ใช้ allocation ต่ำ")
        else:
            recommendations.append("❌ Strategy นี้มี Performance ต่ำ - ไม่แนะนำให้ใช้มาก")
        
        if recovery_rate > 95:
            recommendations.append("🔄 Recovery Rate สูง - เหมาะสำหรับระบบนี้")
        
        if volatility > 0.15:
            recommendations.append("📊 Volatility สูง - ต้องระมัดระวังการใช้")
        
        return {
            "strategy": strategy.value,
            "recommended_percentage": recommended_percentage,
            "recommended_amount": f"${recommended_percentage/100*10000:.2f} (สำหรับเงินทุน $10,000)",
            "performance_score": (win_rate + (profit_factor-1)*50 + recovery_rate) / 3,
            "risk_level": "HIGH" if volatility > 0.15 else "MEDIUM" if volatility > 0.10 else "LOW",
            "recommendations": recommendations,
            "allocation_rationale": f"Win Rate: {win_rate:.1f}%, Profit Factor: {profit_factor:.2f}, Recovery: {recovery_rate:.1f}%"
        }
        
    except Exception as e:
        return {
            "error": f"ไม่สามารถสร้างคำแนะนำได้: {e}",
            "recommended_percentage": 15.0
        }

if __name__ == "__main__":
    """
    ทดสอบ Capital Allocator System
    """
    import asyncio
    
    async def test_capital_allocator():
        """ทดสอบการทำงานของ Capital Allocator"""
        
        print("🧪 เริ่มทดสอบ Capital Allocator System")
        
        # เริ่มต้น Capital Allocator
        allocator = get_capital_allocator()
        await allocator.start_capital_allocator()
        
        try:
            # ทดสอบการคำนวณ Allocation
            print("\n💰 ทดสอบการคำนวณ Optimal Allocation...")
            allocation_result = await allocator.calculate_optimal_allocation(
                AllocationStrategy.DYNAMIC_REBALANCING, 10000.0
            )
            
            print(f"   Allocation Strategy: {allocation_result.allocation_strategy.value}")
            print(f"   Total Capital: ${allocation_result.total_capital:.2f}")
            print(f"   Allocation Efficiency: {allocation_result.allocation_efficiency:.1f}%")
            print(f"   Diversification Score: {allocation_result.diversification_score:.1f}%")
            print(f"   Risk Utilization: {allocation_result.risk_utilization:.1f}%")
            
            print(f"\n📊 Strategy Allocations:")
            for strategy, allocation in allocation_result.strategy_allocations.items():
                print(f"   {strategy.value}: ${allocation.allocated_capital:.2f} ({allocation.allocated_percentage:.1f}%)")
            
            print(f"\n🕐 Session Allocations:")
            for session, allocation in allocation_result.session_allocations.items():
                print(f"   {session.value}: ${allocation.allocated_capital:.2f} (Volume: {allocation.target_volume_lots:.1f} lots)")
            
            if allocation_result.recovery_allocation:
                print(f"\n🔄 Recovery Allocation:")
                print(f"   Total Budget: ${allocation_result.recovery_allocation.total_recovery_budget:.2f}")
                print(f"   Available: ${allocation_result.recovery_allocation.available_recovery_capital:.2f}")
                print(f"   Success Rate: {allocation_result.recovery_allocation.recovery_success_rate:.1f}%")
            
            print(f"\n🔄 Rebalancing Status:")
            print(f"   Needs Rebalancing: {allocation_result.needs_rebalancing}")
            print(f"   Urgency: {allocation_result.rebalancing_urgency}")
            print(f"   Triggers: {[t.value for t in allocation_result.rebalancing_triggers]}")
            
            if allocation_result.optimization_opportunities:
                print(f"\n💡 Optimization Opportunities:")
                for opportunity in allocation_result.optimization_opportunities:
                    print(f"   {opportunity}")
            
            if allocation_result.allocation_warnings:
                print(f"\n⚠️ Allocation Warnings:")
                for warning in allocation_result.allocation_warnings:
                    print(f"   {warning}")
            
            # ทดสอบ Strategy Recommendation
            print(f"\n📈 ทดสอบ Strategy Recommendation...")
            test_performance = {
                'win_rate': 65.0,
                'profit_factor': 1.4,
                'recovery_rate': 96.0,
                'volatility': 0.12
            }
            
            recommendation = get_strategy_allocation_recommendation(
                EntryStrategy.TREND_FOLLOWING, test_performance
            )
            
            print(f"   Strategy: {recommendation['strategy']}")
            print(f"   Recommended: {recommendation['recommended_percentage']:.1f}%")
            print(f"   Performance Score: {recommendation['performance_score']:.1f}")
            print(f"   Risk Level: {recommendation['risk_level']}")
            
            # ทดสอบสถิติ
            stats = allocator.get_allocation_statistics()
            print(f"\n📈 Capital Allocator Statistics:")
            print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))
            
        finally:
            allocator.stop_capital_allocator()
        
        print("\n✅ ทดสอบ Capital Allocator เสร็จสิ้น")
    
    # รันการทดสอบ
    asyncio.run(test_capital_allocator())