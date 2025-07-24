#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RISK CALCULATOR - Advanced Risk Calculation Engine
=================================================
เครื่องมือคำนวณความเสี่ยงแบบครอบคลุมและ Real-time
รองรับการคำนวณความเสี่ยงสำหรับ Recovery System และ High-Frequency Trading

Key Features:
- Real-time risk metrics calculation
- Portfolio risk assessment และ correlation analysis
- Dynamic risk adjustment algorithms
- Risk scenario modeling และ stress testing
- Recovery-focused risk management
- High-frequency risk monitoring (50-100 lots/วัน)
- Multi-timeframe risk analysis

เชื่อมต่อไปยัง:
- position_management/position_tracker.py (ข้อมูล positions)
- money_management/position_sizer.py (ข้อมูล sizing)
- intelligent_recovery/recovery_engine.py (ข้อมูล recovery)
- market_intelligence/market_analyzer.py (ข้อมูล market)
- analytics_engine/performance_tracker.py (ข้อมูล performance)
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

class RiskMetric(Enum):
    """ประเภทของ Risk Metrics"""
    VALUE_AT_RISK = "value_at_risk"                    # VaR
    CONDITIONAL_VAR = "conditional_var"                # CVaR
    MAXIMUM_DRAWDOWN = "maximum_drawdown"              # Max DD
    SHARPE_RATIO = "sharpe_ratio"                      # Sharpe Ratio
    SORTINO_RATIO = "sortino_ratio"                    # Sortino Ratio
    CORRELATION_RISK = "correlation_risk"              # Correlation Risk
    POSITION_CONCENTRATION = "position_concentration"   # Position Concentration
    RECOVERY_RISK = "recovery_risk"                    # Recovery System Risk
    LIQUIDITY_RISK = "liquidity_risk"                  # Liquidity Risk
    OPERATIONAL_RISK = "operational_risk"              # Operational Risk

class RiskLevel(Enum):
    """ระดับความเสี่ยง"""
    VERY_LOW = 1      # 0-20%
    LOW = 2           # 20-40%
    MODERATE = 3      # 40-60%
    HIGH = 4          # 60-80%
    CRITICAL = 5      # 80-100%

class RiskTimeframe(Enum):
    """กรอบเวลาสำหรับการคำนวณความเสี่ยง"""
    INTRADAY = "INTRADAY"         # ภายในวัน
    DAILY = "DAILY"               # รายวัน
    WEEKLY = "WEEKLY"             # รายสัปดาห์
    MONTHLY = "MONTHLY"           # รายเดือน
    ANNUAL = "ANNUAL"             # รายปี

@dataclass
class RiskParameters:
    """พารามิเตอร์สำหรับการคำนวณความเสี่ยง"""
    # Account Information
    account_balance: float = 10000.0
    account_equity: float = 10000.0
    free_margin: float = 10000.0
    used_margin: float = 0.0
    
    # Risk Limits
    max_daily_risk_percent: float = 5.0        # % ของ equity
    max_single_position_risk: float = 2.0      # % ของ equity
    max_correlation_exposure: float = 70.0     # % correlation limit
    max_drawdown_limit: float = 15.0           # % max drawdown
    
    # Position Information
    total_positions: int = 0
    open_lot_size: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl_today: float = 0.0
    
    # Market Conditions
    current_volatility: float = 1.0
    market_stress_level: float = 0.0           # 0-1 scale
    liquidity_level: float = 1.0               # 0-2 scale
    
    # Recovery Context
    active_recovery_tasks: int = 0
    recovery_capital_allocated: float = 0.0
    avg_recovery_success_rate: float = 95.0

@dataclass
class RiskResult:
    """ผลการคำนวณความเสี่ยง"""
    metric_type: RiskMetric
    risk_value: float
    risk_level: RiskLevel
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    
    # ข้อมูลเพิ่มเติม
    calculation_method: str = ""
    time_horizon: RiskTimeframe = RiskTimeframe.DAILY
    stress_test_result: Optional[float] = None
    
    # คำอธิบายและคำแนะนำ
    interpretation: str = ""
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Metadata
    calculation_time: datetime = field(default_factory=datetime.now)
    data_points_used: int = 0
    reliability_score: float = 0.0

@dataclass
class PortfolioRiskSummary:
    """สรุปความเสี่ยงของ Portfolio"""
    overall_risk_score: float = 0.0           # 0-100
    risk_level: RiskLevel = RiskLevel.MODERATE
    
    # Key Risk Metrics
    current_var_1d: float = 0.0               # VaR 1 วัน
    current_drawdown: float = 0.0             # Current DD %
    position_concentration: float = 0.0        # Concentration %
    correlation_exposure: float = 0.0          # Correlation %
    
    # Risk Budget Usage
    daily_risk_used: float = 0.0              # % ของ daily limit
    position_risk_used: float = 0.0           # % ของ position limit
    margin_utilization: float = 0.0           # % ของ margin
    
    # Risk Breakdown
    individual_risks: Dict[RiskMetric, RiskResult] = field(default_factory=dict)
    risk_contributors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Recovery Risk Assessment
    recovery_risk_level: RiskLevel = RiskLevel.LOW
    recovery_capacity_remaining: float = 100.0  # %
    
    # Recommendations
    immediate_actions: List[str] = field(default_factory=list)
    risk_optimization_suggestions: List[str] = field(default_factory=list)
    
    # Metadata
    calculation_timestamp: datetime = field(default_factory=datetime.now)
    market_conditions_snapshot: Dict[str, Any] = field(default_factory=dict)

class ValueAtRiskCalculator:
    """
    คำนวณ Value at Risk (VaR) และ Conditional VaR
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.confidence_levels = [0.95, 0.99]  # 95% และ 99%
        self.lookback_periods = [30, 60, 120]  # วัน
    
    def calculate_var(self, returns: List[float], confidence_level: float = 0.95,
                     method: str = "historical") -> Tuple[float, Dict[str, Any]]:
        """
        คำนวณ Value at Risk
        
        Args:
            returns: รายการผลตอบแทน
            confidence_level: ระดับความเชื่อมั่น
            method: วิธีการคำนวณ (historical, parametric, monte_carlo)
            
        Returns:
            Tuple[float, Dict]: (VaR value, metadata)
        """
        try:
            if not returns or len(returns) < 10:
                return 0.0, {"error": "ข้อมูลไม่เพียงพอ"}
            
            metadata = {
                "method": method,
                "confidence_level": confidence_level,
                "sample_size": len(returns),
                "calculation_time": datetime.now()
            }
            
            if method == "historical":
                var_value = self._calculate_historical_var(returns, confidence_level)
                metadata["percentile_used"] = (1 - confidence_level) * 100
                
            elif method == "parametric":
                var_value = self._calculate_parametric_var(returns, confidence_level)
                metadata["mean"] = statistics.mean(returns)
                metadata["std_dev"] = statistics.stdev(returns) if len(returns) > 1 else 0
                
            elif method == "monte_carlo":
                var_value = self._calculate_monte_carlo_var(returns, confidence_level)
                metadata["simulations"] = 10000
                
            else:
                var_value = self._calculate_historical_var(returns, confidence_level)
                metadata["method"] = "historical_fallback"
            
            return abs(var_value), metadata
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ VaR: {e}")
            return 0.0, {"error": str(e)}
    
    def _calculate_historical_var(self, returns: List[float], confidence_level: float) -> float:
        """คำนวณ Historical VaR"""
        sorted_returns = sorted(returns)
        index = int((1 - confidence_level) * len(sorted_returns))
        return sorted_returns[max(0, index - 1)]
    
    def _calculate_parametric_var(self, returns: List[float], confidence_level: float) -> float:
        """คำนวณ Parametric VaR (สมมติ Normal Distribution)"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = statistics.mean(returns)
        std_dev = statistics.stdev(returns)
        
        # Z-score สำหรับ confidence level
        z_scores = {0.90: -1.282, 0.95: -1.645, 0.99: -2.326}
        z_score = z_scores.get(confidence_level, -1.645)
        
        return mean_return + (z_score * std_dev)
    
    def _calculate_monte_carlo_var(self, returns: List[float], confidence_level: float) -> float:
        """คำนวณ Monte Carlo VaR"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = statistics.mean(returns)
        std_dev = statistics.stdev(returns)
        
        # สร้าง Monte Carlo simulations
        np.random.seed(42)  # สำหรับผลลัพธ์ที่สม่ำเสมอ
        simulated_returns = np.random.normal(mean_return, std_dev, 10000)
        
        # คำนวณ VaR จาก simulations
        index = int((1 - confidence_level) * len(simulated_returns))
        return np.sort(simulated_returns)[index]
    
    def calculate_conditional_var(self, returns: List[float], confidence_level: float = 0.95) -> Tuple[float, Dict[str, Any]]:
        """
        คำนวณ Conditional VaR (Expected Shortfall)
        """
        try:
            var_value, var_metadata = self.calculate_var(returns, confidence_level, "historical")
            
            if var_value == 0:
                return 0.0, var_metadata
            
            # หา returns ที่แย่กว่า VaR
            worse_returns = [r for r in returns if r <= -var_value]
            
            if not worse_returns:
                cvar_value = var_value
            else:
                cvar_value = abs(statistics.mean(worse_returns))
            
            metadata = {
                "var_value": var_value,
                "cvar_value": cvar_value,
                "tail_observations": len(worse_returns),
                "tail_percentage": (len(worse_returns) / len(returns)) * 100
            }
            
            return cvar_value, metadata
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ CVaR: {e}")
            return 0.0, {"error": str(e)}

class DrawdownCalculator:
    """
    คำนวณ Maximum Drawdown และ Drawdown Duration
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
    
    def calculate_drawdown_metrics(self, equity_curve: List[float]) -> Dict[str, Any]:
        """
        คำนวณ Drawdown metrics ต่างๆ
        
        Args:
            equity_curve: เส้นโค้ง equity ตามเวลา
            
        Returns:
            Dict: Drawdown metrics
        """
        try:
            if not equity_curve or len(equity_curve) < 2:
                return self._get_empty_drawdown_metrics()
            
            # คำนวณ Running Maximum
            running_max = []
            current_max = equity_curve[0]
            
            for value in equity_curve:
                current_max = max(current_max, value)
                running_max.append(current_max)
            
            # คำนวณ Drawdown ในแต่ละจุด
            drawdowns = []
            for i, value in enumerate(equity_curve):
                if running_max[i] > 0:
                    dd = ((value - running_max[i]) / running_max[i]) * 100
                    drawdowns.append(dd)
                else:
                    drawdowns.append(0.0)
            
            # หา Maximum Drawdown
            max_drawdown = min(drawdowns) if drawdowns else 0.0
            
            # คำนวณ Current Drawdown
            current_drawdown = drawdowns[-1] if drawdowns else 0.0
            
            # หา Drawdown Duration
            max_duration, current_duration = self._calculate_drawdown_durations(drawdowns)
            
            # คำนวณ Drawdown Recovery Time
            recovery_time = self._calculate_recovery_time(drawdowns)
            
            return {
                "maximum_drawdown": abs(max_drawdown),
                "current_drawdown": abs(current_drawdown),
                "max_drawdown_duration": max_duration,
                "current_drawdown_duration": current_duration,
                "average_recovery_time": recovery_time,
                "drawdown_frequency": self._calculate_drawdown_frequency(drawdowns),
                "underwater_periods": self._identify_underwater_periods(drawdowns),
                "drawdown_volatility": statistics.stdev(drawdowns) if len(drawdowns) > 1 else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Drawdown: {e}")
            return self._get_empty_drawdown_metrics()
    
    def _calculate_drawdown_durations(self, drawdowns: List[float]) -> Tuple[int, int]:
        """คำนวณระยะเวลา Drawdown"""
        max_duration = 0
        current_duration = 0
        temp_duration = 0
        
        for dd in drawdowns:
            if dd < 0:  # อยู่ใน Drawdown
                temp_duration += 1
                current_duration = temp_duration
            else:  # ออกจาก Drawdown
                max_duration = max(max_duration, temp_duration)
                temp_duration = 0
                current_duration = 0
        
        max_duration = max(max_duration, temp_duration)
        return max_duration, current_duration
    
    def _calculate_recovery_time(self, drawdowns: List[float]) -> float:
        """คำนวณเวลาเฉลี่ยในการ Recovery"""
        recovery_times = []
        in_drawdown = False
        drawdown_start = 0
        
        for i, dd in enumerate(drawdowns):
            if dd < 0 and not in_drawdown:  # เริ่ม Drawdown
                in_drawdown = True
                drawdown_start = i
            elif dd >= 0 and in_drawdown:  # จบ Drawdown
                in_drawdown = False
                recovery_time = i - drawdown_start
                recovery_times.append(recovery_time)
        
        return statistics.mean(recovery_times) if recovery_times else 0.0
    
    def _calculate_drawdown_frequency(self, drawdowns: List[float]) -> float:
        """คำนวณความถี่ของ Drawdown"""
        drawdown_periods = 0
        in_drawdown = False
        
        for dd in drawdowns:
            if dd < 0 and not in_drawdown:
                drawdown_periods += 1
                in_drawdown = True
            elif dd >= 0:
                in_drawdown = False
        
        return (drawdown_periods / len(drawdowns)) * 100 if drawdowns else 0.0
    
    def _identify_underwater_periods(self, drawdowns: List[float]) -> List[Dict[str, Any]]:
        """ระบุช่วงเวลาที่อยู่ใต้น้ำ (Underwater Periods)"""
        periods = []
        current_period = None
        
        for i, dd in enumerate(drawdowns):
            if dd < 0:  # อยู่ใน Drawdown
                if current_period is None:
                    current_period = {"start": i, "max_dd": dd, "duration": 1}
                else:
                    current_period["duration"] += 1
                    current_period["max_dd"] = min(current_period["max_dd"], dd)
            else:  # ออกจาก Drawdown
                if current_period is not None:
                    current_period["end"] = i - 1
                    periods.append(current_period)
                    current_period = None
        
        # จัดการ period ที่ยังไม่จบ
        if current_period is not None:
            current_period["end"] = len(drawdowns) - 1
            periods.append(current_period)
        
        return periods
    
    def _get_empty_drawdown_metrics(self) -> Dict[str, Any]:
        """Return empty metrics เมื่อไม่มีข้อมูล"""
        return {
            "maximum_drawdown": 0.0,
            "current_drawdown": 0.0,
            "max_drawdown_duration": 0,
            "current_drawdown_duration": 0,
            "average_recovery_time": 0.0,
            "drawdown_frequency": 0.0,
            "underwater_periods": [],
            "drawdown_volatility": 0.0
        }

class CorrelationAnalyzer:
    """
    วิเคราะห์ความสัมพันธ์ระหว่าง Positions และ Portfolio Correlation Risk
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.correlation_threshold_high = 0.7    # Correlation สูง
        self.correlation_threshold_medium = 0.4  # Correlation ปานกลาง
    
    def calculate_portfolio_correlation_risk(self, positions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        คำนวณความเสี่ยงจาก Correlation ของ Portfolio
        
        Args:
            positions_data: ข้อมูล positions ทั้งหมด
            
        Returns:
            Dict: Correlation risk metrics
        """
        try:
            if not positions_data or len(positions_data) < 2:
                return self._get_empty_correlation_metrics()
            
            # สร้าง Correlation Matrix
            correlation_matrix = self._build_correlation_matrix(positions_data)
            
            # คำนวณ Correlation Risk Metrics
            max_correlation = self._find_max_correlation(correlation_matrix)
            avg_correlation = self._calculate_average_correlation(correlation_matrix)
            correlation_clusters = self._identify_correlation_clusters(correlation_matrix, positions_data)
            
            # คำนวณ Portfolio Concentration Risk
            concentration_risk = self._calculate_concentration_risk(positions_data)
            
            # ประเมิน Overall Correlation Risk
            overall_risk_score = self._calculate_overall_correlation_risk(
                max_correlation, avg_correlation, concentration_risk
            )
            
            # สร้าง Risk Level
            risk_level = self._determine_correlation_risk_level(overall_risk_score)
            
            return {
                "overall_correlation_risk": overall_risk_score,
                "risk_level": risk_level.value,
                "max_correlation": max_correlation,
                "average_correlation": avg_correlation,
                "correlation_matrix": correlation_matrix.tolist() if hasattr(correlation_matrix, 'tolist') else [],
                "high_correlation_pairs": self._find_high_correlation_pairs(correlation_matrix, positions_data),
                "correlation_clusters": correlation_clusters,
                "concentration_risk": concentration_risk,
                "diversification_ratio": self._calculate_diversification_ratio(correlation_matrix),
                "recommendations": self._generate_correlation_recommendations(overall_risk_score, correlation_clusters)
            }
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Correlation Risk: {e}")
            return self._get_empty_correlation_metrics()
    
    def _build_correlation_matrix(self, positions_data: List[Dict[str, Any]]) -> np.ndarray:
        """สร้าง Correlation Matrix"""
        try:
            # ในระบบจริงจะใช้ price returns ของแต่ละ position
            # ที่นี่จะใช้การจำลองตาม position characteristics
            
            n_positions = len(positions_data)
            correlation_matrix = np.eye(n_positions)  # เริ่มด้วย Identity matrix
            
            for i in range(n_positions):
                for j in range(i + 1, n_positions):
                    # คำนวณ correlation ตามลักษณะของ positions
                    correlation = self._estimate_position_correlation(
                        positions_data[i], positions_data[j]
                    )
                    correlation_matrix[i, j] = correlation
                    correlation_matrix[j, i] = correlation  # Symmetric matrix
            
            return correlation_matrix
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Correlation Matrix: {e}")
            return np.eye(len(positions_data))
    
    def _estimate_position_correlation(self, pos1: Dict[str, Any], pos2: Dict[str, Any]) -> float:
        """ประมาณ correlation ระหว่าง 2 positions"""
        correlation = 0.0
        
        # Same symbol = high correlation
        if pos1.get('symbol') == pos2.get('symbol'):
            correlation += 0.8
        
        # Same direction = medium correlation
        if pos1.get('direction') == pos2.get('direction'):
            correlation += 0.3
        else:
            correlation -= 0.2  # Opposite direction = negative correlation
        
        # Same entry strategy = medium correlation
        if pos1.get('entry_strategy') == pos2.get('entry_strategy'):
            correlation += 0.2
        
        # Same timeframe = low correlation
        if pos1.get('timeframe') == pos2.get('timeframe'):
            correlation += 0.1
        
        # Opened at similar time = low correlation
        time1 = pos1.get('open_time', datetime.now())
        time2 = pos2.get('open_time', datetime.now())
        if isinstance(time1, datetime) and isinstance(time2, datetime):
            time_diff = abs((time1 - time2).total_seconds() / 3600)  # hours
            if time_diff < 1:  # ภายใน 1 ชั่วโมง
                correlation += 0.1
        
        # จำกัดค่าระหว่าง -1 และ 1
        return max(-1.0, min(1.0, correlation))
    
    def _find_max_correlation(self, correlation_matrix: np.ndarray) -> float:
        """หา correlation สูงสุด (ไม่รวม diagonal)"""
        n = correlation_matrix.shape[0]
        max_corr = 0.0
        
        for i in range(n):
            for j in range(i + 1, n):
                max_corr = max(max_corr, abs(correlation_matrix[i, j]))
        
        return max_corr
    
    def _calculate_average_correlation(self, correlation_matrix: np.ndarray) -> float:
        """คำนวณ correlation เฉลี่ย"""
        n = correlation_matrix.shape[0]
        if n < 2:
            return 0.0
        
        total_corr = 0.0
        count = 0
        
        for i in range(n):
            for j in range(i + 1, n):
                total_corr += abs(correlation_matrix[i, j])
                count += 1
        
        return total_corr / count if count > 0 else 0.0
    
    def _identify_correlation_clusters(self, correlation_matrix: np.ndarray, 
                                     positions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """ระบุกลุ่มของ positions ที่มี correlation สูง"""
        clusters = []
        n = correlation_matrix.shape[0]
        processed = set()
        
        for i in range(n):
            if i in processed:
                continue
            
            cluster = [i]
            cluster_positions = [positions_data[i]['position_id']]
            
            for j in range(i + 1, n):
                if j not in processed and abs(correlation_matrix[i, j]) >= self.correlation_threshold_high:
                    cluster.append(j)
                    cluster_positions.append(positions_data[j]['position_id'])
                    processed.add(j)
            
            if len(cluster) > 1:
                avg_correlation = np.mean([abs(correlation_matrix[i, j]) 
                                         for i in cluster for j in cluster if i != j])
                
                clusters.append({
                    "cluster_id": len(clusters) + 1,
                    "position_indices": cluster,
                    "position_ids": cluster_positions,
                    "cluster_size": len(cluster),
                    "average_correlation": avg_correlation,
                    "risk_contribution": len(cluster) / n * 100
                })
                
                processed.update(cluster)
        
        return clusters
    
    def _calculate_concentration_risk(self, positions_data: List[Dict[str, Any]]) -> float:
        """คำนวณ Concentration Risk"""
        if not positions_data:
            return 0.0
        
        # คำนวณ weight ของแต่ละ position
        total_exposure = sum(abs(pos.get('unrealized_pnl', 0) + pos.get('volume', 0) * 1000) 
                           for pos in positions_data)
        
        if total_exposure == 0:
            return 0.0
        
        weights = []
        for pos in positions_data:
            exposure = abs(pos.get('unrealized_pnl', 0) + pos.get('volume', 0) * 1000)
            weight = exposure / total_exposure
            weights.append(weight)
        
        # คำนวณ Herfindahl-Hirschman Index
        hhi = sum(w ** 2 for w in weights)
        
        # แปลงเป็น Concentration Score (0-100)
        # HHI = 1/n สำหรับ perfectly diversified portfolio
        # HHI = 1 สำหรับ completely concentrated portfolio
        max_diversification_hhi = 1.0 / len(positions_data)
        concentration_score = ((hhi - max_diversification_hhi) / (1.0 - max_diversification_hhi)) * 100
        
        return max(0.0, min(100.0, concentration_score))
    
    def _calculate_overall_correlation_risk(self, max_correlation: float, 
                                          avg_correlation: float, concentration_risk: float) -> float:
        """คำนวณ Overall Correlation Risk Score"""
        # Weight components
        max_corr_weight = 0.4
        avg_corr_weight = 0.3
        concentration_weight = 0.3
        
        # Scale correlations to 0-100
        max_corr_score = max_correlation * 100
        avg_corr_score = avg_correlation * 100
        
        # Calculate weighted score
        overall_score = (max_corr_score * max_corr_weight + 
                        avg_corr_score * avg_corr_weight + 
                        concentration_risk * concentration_weight)
        
        return min(100.0, overall_score)
    
    def _determine_correlation_risk_level(self, risk_score: float) -> RiskLevel:
        """กำหนด Risk Level จาก score"""
        if risk_score >= 80:
            return RiskLevel.CRITICAL
        elif risk_score >= 60:
            return RiskLevel.HIGH
        elif risk_score >= 40:
            return RiskLevel.MODERATE
        elif risk_score >= 20:
            return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW
    
    def _find_high_correlation_pairs(self, correlation_matrix: np.ndarray, 
                                    positions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """หาคู่ positions ที่มี correlation สูง"""
        high_corr_pairs = []
        n = correlation_matrix.shape[0]
        
        for i in range(n):
            for j in range(i + 1, n):
                correlation = correlation_matrix[i, j]
                if abs(correlation) >= self.correlation_threshold_high:
                    high_corr_pairs.append({
                        "position_1": positions_data[i]['position_id'],
                        "position_2": positions_data[j]['position_id'],
                        "correlation": correlation,
                        "risk_level": "HIGH" if abs(correlation) >= 0.8 else "MEDIUM",
                        "combined_exposure": (positions_data[i].get('volume', 0) + 
                                            positions_data[j].get('volume', 0))
                    })
        
        # เรียงตาม correlation จากสูงไปต่ำ
        high_corr_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
        
        return high_corr_pairs
    
    def _calculate_diversification_ratio(self, correlation_matrix: np.ndarray) -> float:
        """คำนวณ Diversification Ratio"""
        n = correlation_matrix.shape[0]
        if n < 2:
            return 1.0
        
        # Portfolio variance (สมมติ equal weights)
        equal_weight = 1.0 / n
        portfolio_variance = 0.0
        
        for i in range(n):
            for j in range(n):
                portfolio_variance += equal_weight * equal_weight * correlation_matrix[i, j]
        
        # Diversification ratio = 1 / sqrt(portfolio_variance)
        return 1.0 / math.sqrt(portfolio_variance) if portfolio_variance > 0 else 1.0
    
    def _generate_correlation_recommendations(self, risk_score: float, 
                                            clusters: List[Dict[str, Any]]) -> List[str]:
        """สร้างคำแนะนำเกี่ยวกับ Correlation Risk"""
        recommendations = []
        
        if risk_score >= 70:
            recommendations.append("🚨 Correlation Risk สูงมาก - ลดการเปิด positions ในทิศทางเดียวกัน")
            recommendations.append("💡 พิจารณาปิดบาง positions ที่มี correlation สูง")
        elif risk_score >= 50:
            recommendations.append("⚠️ Correlation Risk ปานกลาง - ระวังการเปิด positions เพิ่ม")
            recommendations.append("💡 เน้นหา opportunities ที่มี correlation ต่ำ")
        
        if clusters and len(clusters) > 0:
            largest_cluster = max(clusters, key=lambda x: x['cluster_size'])
            if largest_cluster['cluster_size'] >= 3:
                recommendations.append(f"📊 มี cluster ขนาดใหญ่ ({largest_cluster['cluster_size']} positions) - พิจารณาลด exposure")
        
        return recommendations
    
    def _get_empty_correlation_metrics(self) -> Dict[str, Any]:
        """Return empty metrics เมื่อไม่มีข้อมูล"""
        return {
            "overall_correlation_risk": 0.0,
            "risk_level": RiskLevel.VERY_LOW.value,
            "max_correlation": 0.0,
            "average_correlation": 0.0,
            "correlation_matrix": [],
            "high_correlation_pairs": [],
            "correlation_clusters": [],
            "concentration_risk": 0.0,
            "diversification_ratio": 1.0,
            "recommendations": []
        }

class RecoveryRiskAnalyzer:
    """
    วิเคราะห์ความเสี่ยงจากระบบ Recovery
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.max_recovery_budget_percent = 20.0  # % ของ equity
    
    def analyze_recovery_risk(self, recovery_data: Dict[str, Any], 
                            account_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        วิเคราะห์ความเสี่ยงจากระบบ Recovery
        
        Args:
            recovery_data: ข้อมูลระบบ Recovery
            account_data: ข้อมูลบัญชี
            
        Returns:
            Dict: Recovery risk analysis
        """
        try:
            account_equity = account_data.get('equity', 10000.0)
            
            # คำนวณ Recovery Capital Utilization
            allocated_capital = recovery_data.get('allocated_capital', 0.0)
            capital_utilization = (allocated_capital / account_equity) * 100 if account_equity > 0 else 0.0
            
            # วิเคราะห์ Active Recovery Tasks
            active_tasks = recovery_data.get('active_tasks', [])
            task_risk_analysis = self._analyze_recovery_tasks(active_tasks, account_equity)
            
            # คำนวณ Recovery Success Rate Impact
            success_rate = recovery_data.get('success_rate', 95.0)
            success_rate_risk = self._calculate_success_rate_risk(success_rate)
            
            # วิเคราะห์ Recovery Method Distribution
            method_distribution = recovery_data.get('method_distribution', {})
            method_risk = self._analyze_recovery_method_risk(method_distribution)
            
            # คำนวณ Recovery Capacity Remaining
            max_recovery_budget = account_equity * (self.max_recovery_budget_percent / 100)
            remaining_capacity = max(0, max_recovery_budget - allocated_capital)
            capacity_percentage = (remaining_capacity / max_recovery_budget) * 100 if max_recovery_budget > 0 else 0.0
            
            # คำนวณ Overall Recovery Risk Score
            overall_risk = self._calculate_overall_recovery_risk(
                capital_utilization, task_risk_analysis['total_risk'], 
                success_rate_risk, method_risk
            )
            
            return {
                "overall_recovery_risk": overall_risk,
                "risk_level": self._determine_recovery_risk_level(overall_risk).value,
                "capital_utilization": capital_utilization,
                "allocated_capital": allocated_capital,
                "remaining_capacity": remaining_capacity,
                "capacity_percentage": capacity_percentage,
                "active_tasks_count": len(active_tasks),
                "task_risk_analysis": task_risk_analysis,
                "success_rate": success_rate,
                "success_rate_risk": success_rate_risk,
                "method_distribution": method_distribution,
                "method_risk_score": method_risk,
                "recommendations": self._generate_recovery_recommendations(overall_risk, capital_utilization),
                "capacity_warnings": self._generate_capacity_warnings(capital_utilization, capacity_percentage)
            }
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์ Recovery Risk: {e}")
            return self._get_empty_recovery_metrics()
    
    def _analyze_recovery_tasks(self, active_tasks: List[Dict[str, Any]], 
                                account_equity: float) -> Dict[str, Any]:
        """วิเคราะห์ความเสี่ยงจาก Recovery Tasks ที่กำลังทำงาน"""
        if not active_tasks:
            return {"total_risk": 0.0, "task_details": [], "risk_breakdown": {}}
        
        task_details = []
        total_risk_amount = 0.0
        risk_breakdown = defaultdict(float)
        
        for task in active_tasks:
            task_risk = self._calculate_single_task_risk(task, account_equity)
            task_details.append(task_risk)
            total_risk_amount += task_risk['risk_amount']
            risk_breakdown[task_risk['recovery_method']] += task_risk['risk_amount']
        
        total_risk_percentage = (total_risk_amount / account_equity) * 100 if account_equity > 0 else 0.0
        
        return {
            "total_risk": total_risk_percentage,
            "total_risk_amount": total_risk_amount,
            "task_details": task_details,
            "risk_breakdown": dict(risk_breakdown),
            "highest_risk_task": max(task_details, key=lambda x: x['risk_amount']) if task_details else None,
            "average_task_risk": total_risk_amount / len(active_tasks) if active_tasks else 0.0
        }
    
    def _calculate_single_task_risk(self, task: Dict[str, Any], account_equity: float) -> Dict[str, Any]:
        """คำนวณความเสี่ยงของ Recovery Task เดียว"""
        original_loss = abs(task.get('original_loss', 0.0))
        recovery_method = task.get('recovery_method', 'UNKNOWN')
        attempts_made = task.get('attempts_made', 0)
        
        # Risk Multipliers ตาม Recovery Method
        method_risk_multipliers = {
            'MARTINGALE_SMART': 2.0,      # Martingale มีความเสี่ยงสูง
            'GRID_INTELLIGENT': 1.5,     # Grid มีความเสี่ยงปานกลาง
            'HEDGING_ADVANCED': 1.2,     # Hedging มีความเสี่ยงต่ำ
            'AVERAGING_INTELLIGENT': 1.3, # Averaging มีความเสี่ยงปานกลาง
            'CORRELATION_RECOVERY': 1.1   # Correlation มีความเสี่ยงต่ำ
        }
        
        base_multiplier = method_risk_multipliers.get(recovery_method, 1.5)
        
        # ปรับตามจำนวนครั้งที่พยายาม
        attempt_multiplier = 1.0 + (attempts_made * 0.2)  # เพิ่ม 20% ต่อครั้ง
        
        # คำนวณ Risk Amount
        risk_amount = original_loss * base_multiplier * attempt_multiplier
        risk_percentage = (risk_amount / account_equity) * 100 if account_equity > 0 else 0.0
        
        return {
            "task_id": task.get('task_id', 'UNKNOWN'),
            "recovery_method": recovery_method,
            "original_loss": original_loss,
            "attempts_made": attempts_made,
            "risk_amount": risk_amount,
            "risk_percentage": risk_percentage,
            "risk_level": "HIGH" if risk_percentage > 5 else "MEDIUM" if risk_percentage > 2 else "LOW"
        }
    
    def _calculate_success_rate_risk(self, success_rate: float) -> float:
        """คำนวณความเสี่ยงจาก Success Rate"""
        if success_rate >= 95:
            return 10.0   # Risk ต่ำ
        elif success_rate >= 90:
            return 25.0   # Risk ปานกลาง
        elif success_rate >= 80:
            return 50.0   # Risk สูง
        else:
            return 80.0   # Risk สูงมาก
    
    def _analyze_recovery_method_risk(self, method_distribution: Dict[str, int]) -> float:
        """วิเคราะห์ความเสี่ยงจากการกระจาย Recovery Methods"""
        if not method_distribution:
            return 0.0
        
        # Risk Scores สำหรับแต่ละ method
        method_risk_scores = {
            'MARTINGALE_SMART': 80.0,
            'GRID_INTELLIGENT': 50.0,
            'HEDGING_ADVANCED': 30.0,
            'AVERAGING_INTELLIGENT': 40.0,
            'CORRELATION_RECOVERY': 25.0
        }
        
        total_tasks = sum(method_distribution.values())
        if total_tasks == 0:
            return 0.0
        
        weighted_risk = 0.0
        for method, count in method_distribution.items():
            weight = count / total_tasks
            risk_score = method_risk_scores.get(method, 50.0)
            weighted_risk += weight * risk_score
        
        return weighted_risk
    
    def _calculate_overall_recovery_risk(self, capital_utilization: float, task_risk: float,
                                        success_rate_risk: float, method_risk: float) -> float:
        """คำนวณ Overall Recovery Risk Score"""
        # Weights
        capital_weight = 0.3
        task_weight = 0.3
        success_rate_weight = 0.25
        method_weight = 0.15
        
        # Scale capital utilization to 0-100
        capital_risk = min(100.0, (capital_utilization / self.max_recovery_budget_percent) * 100)
        
        # Calculate weighted score
        overall_risk = (capital_risk * capital_weight +
                        task_risk * task_weight +
                        success_rate_risk * success_rate_weight +
                        method_risk * method_weight)
        
        return min(100.0, overall_risk)
    
    def _determine_recovery_risk_level(self, risk_score: float) -> RiskLevel:
        """กำหนด Recovery Risk Level"""
        if risk_score >= 80:
            return RiskLevel.CRITICAL
        elif risk_score >= 60:
            return RiskLevel.HIGH
        elif risk_score >= 40:
            return RiskLevel.MODERATE
        elif risk_score >= 20:
            return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW
    
    def _generate_recovery_recommendations(self, risk_score: float, 
                                            capital_utilization: float) -> List[str]:
        """สร้างคำแนะนำเกี่ยวกับ Recovery Risk"""
        recommendations = []
        
        if risk_score >= 80:
            recommendations.append("🚨 Recovery Risk อยู่ในระดับวิกฤต - พิจารณาหยุดเปิด positions ใหม่")
            recommendations.append("💡 เน้น recovery tasks ที่มีโอกาสสำเร็จสูง")
        elif risk_score >= 60:
            recommendations.append("⚠️ Recovery Risk สูง - จำกัดการใช้ Recovery Methods ที่เสี่ยง")
            recommendations.append("💡 ปรับ Recovery Strategy ให้ conservative มากขึ้น")
        
        if capital_utilization > 15:
            recommendations.append(f"📊 ใช้ Recovery Capital {capital_utilization:.1f}% - ใกล้ขีดจำกัด")
        
        return recommendations
    
    def _generate_capacity_warnings(self, capital_utilization: float, 
                                    capacity_percentage: float) -> List[str]:
        """สร้างคำเตือนเกี่ยวกับ Recovery Capacity"""
        warnings = []
        
        if capital_utilization > 18:
            warnings.append("🚨 Recovery Capital ใกล้เต็มขีดจำกัด")
        elif capital_utilization > 15:
            warnings.append("⚠️ Recovery Capital ใช้ไปมากแล้ว")
        
        if capacity_percentage < 20:
            warnings.append("🚨 Recovery Capacity เหลือน้อยมาก")
        elif capacity_percentage < 50:
            warnings.append("⚠️ Recovery Capacity เหลือน้อย")
        
        return warnings
    
    def _get_empty_recovery_metrics(self) -> Dict[str, Any]:
        """Return empty recovery metrics"""
        return {
            "overall_recovery_risk": 0.0,
            "risk_level": RiskLevel.VERY_LOW.value,
            "capital_utilization": 0.0,
            "allocated_capital": 0.0,
            "remaining_capacity": 100.0,
            "capacity_percentage": 100.0,
            "active_tasks_count": 0,
            "task_risk_analysis": {"total_risk": 0.0, "task_details": []},
            "success_rate": 100.0,
            "success_rate_risk": 0.0,
            "method_distribution": {},
            "method_risk_score": 0.0,
            "recommendations": [],
            "capacity_warnings": []
        }

class RiskCalculator:
    """
    🎯 Main Risk Calculator Class
    
    เครื่องมือหลักสำหรับคำนวณความเสี่ยงแบบครอบคลุมและ Real-time
    รวบรวมการวิเคราะห์จากทุก Risk Analyzer เข้าด้วยกัน
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Initialize Risk Analyzers
        self.var_calculator = ValueAtRiskCalculator()
        self.drawdown_calculator = DrawdownCalculator()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.recovery_risk_analyzer = RecoveryRiskAnalyzer()
        
        # External Connections
        self.position_tracker = None      # จะเชื่อมต่อใน start()
        self.performance_tracker = None   # จะเชื่อมต่อใน start()
        self.market_analyzer = None       # จะเชื่อมต่อใน start()
        self.recovery_engine = None       # จะเชื่อมต่อใน start()
        
        # Risk Parameters
        self.current_parameters = RiskParameters()
        
        # Risk History
        self.risk_history = deque(maxlen=1000)
        self.calculation_count = 0
        
        # Threading
        self.risk_monitor_active = False
        self.monitor_thread = None
        self.parameters_lock = threading.Lock()
        
        self.logger.info("⚠️ เริ่มต้น Risk Calculator")
    
    @handle_trading_errors(ErrorCategory.RISK_CALCULATION, ErrorSeverity.HIGH)
    async def start_risk_calculator(self) -> None:
        """
        เริ่มต้น Risk Calculator
        """
        self.logger.info("🚀 เริ่มต้น Risk Calculator System")
        
        # เชื่อมต่อ External Components
        try:
            from position_management.position_tracker import PositionTracker
            self.position_tracker = PositionTracker()
            
            from analytics_engine.performance_tracker import get_performance_tracker
            self.performance_tracker = get_performance_tracker()
            
            from market_intelligence.market_analyzer import MarketAnalyzer
            self.market_analyzer = MarketAnalyzer()
            
            from intelligent_recovery.recovery_engine import get_recovery_engine
            self.recovery_engine = get_recovery_engine()
            
            self.logger.info("✅ เชื่อมต่อ External Components สำเร็จ")
            
        except ImportError as e:
            self.logger.warning(f"⚠️ ไม่สามารถเชื่อมต่อบาง Components: {e}")
        
        # เริ่ม Risk Monitoring
        await self._start_risk_monitoring()
        
        self.logger.info("✅ Risk Calculator พร้อมทำงาน")
    
    async def calculate_comprehensive_risk(self, timeframe: RiskTimeframe = RiskTimeframe.DAILY) -> PortfolioRiskSummary:
        """
        คำนวณความเสี่ยงแบบครอบคลุม
        
        Args:
            timeframe: กรอบเวลาสำหรับการคำนวณ
            
        Returns:
            PortfolioRiskSummary: สรุปความเสี่ยงของ Portfolio
        """
        try:
            self.logger.info(f"🔍 เริ่มคำนวณความเสี่ยงครอบคลุม - Timeframe: {timeframe.value}")
            
            # อัพเดท Risk Parameters
            await self._update_risk_parameters()
            
            # เก็บข้อมูลที่จำเป็น
            positions_data = await self._get_positions_data()
            equity_curve = await self._get_equity_curve(timeframe)
            returns_data = await self._get_returns_data(timeframe)
            recovery_data = await self._get_recovery_data()
            account_data = await self._get_account_data()
            
            # คำนวณ Risk Metrics แต่ละประเภท
            risk_results = {}
            
            # 1. Value at Risk
            if returns_data and len(returns_data) >= 10:
                var_95, var_metadata = self.var_calculator.calculate_var(returns_data, 0.95)
                var_99, _ = self.var_calculator.calculate_var(returns_data, 0.99)
                cvar_95, cvar_metadata = self.var_calculator.calculate_conditional_var(returns_data, 0.95)
                
                risk_results[RiskMetric.VALUE_AT_RISK] = RiskResult(
                    metric_type=RiskMetric.VALUE_AT_RISK,
                    risk_value=var_95,
                    risk_level=self._classify_var_risk_level(var_95),
                    confidence_interval=(var_95, var_99),
                    calculation_method="historical",
                    time_horizon=timeframe,
                    interpretation=f"VaR 95%: {var_95:.2f}, CVaR: {cvar_95:.2f}",
                    data_points_used=len(returns_data),
                    reliability_score=self._calculate_var_reliability(len(returns_data))
                )
                
                risk_results[RiskMetric.CONDITIONAL_VAR] = RiskResult(
                    metric_type=RiskMetric.CONDITIONAL_VAR,
                    risk_value=cvar_95,
                    risk_level=self._classify_var_risk_level(cvar_95),
                    calculation_method="expected_shortfall",
                    time_horizon=timeframe,
                    interpretation=f"Expected Shortfall: {cvar_95:.2f}",
                    data_points_used=len(returns_data)
                )
            
            # 2. Drawdown Analysis
            if equity_curve and len(equity_curve) >= 5:
                dd_metrics = self.drawdown_calculator.calculate_drawdown_metrics(equity_curve)
                
                risk_results[RiskMetric.MAXIMUM_DRAWDOWN] = RiskResult(
                    metric_type=RiskMetric.MAXIMUM_DRAWDOWN,
                    risk_value=dd_metrics['maximum_drawdown'],
                    risk_level=self._classify_drawdown_risk_level(dd_metrics['maximum_drawdown']),
                    calculation_method="peak_to_trough",
                    time_horizon=timeframe,
                    interpretation=f"Max DD: {dd_metrics['maximum_drawdown']:.2f}%, Current: {dd_metrics['current_drawdown']:.2f}%",
                    recommendations=self._generate_drawdown_recommendations(dd_metrics),
                    data_points_used=len(equity_curve)
                )
            
            # 3. Correlation Risk
            if positions_data and len(positions_data) >= 2:
                corr_analysis = self.correlation_analyzer.calculate_portfolio_correlation_risk(positions_data)
                
                risk_results[RiskMetric.CORRELATION_RISK] = RiskResult(
                    metric_type=RiskMetric.CORRELATION_RISK,
                    risk_value=corr_analysis['overall_correlation_risk'],
                    risk_level=RiskLevel(corr_analysis['risk_level']) if isinstance(corr_analysis['risk_level'], int) else RiskLevel.MODERATE,
                    calculation_method="correlation_matrix",
                    interpretation=f"Max Correlation: {corr_analysis['max_correlation']:.2f}",
                    recommendations=corr_analysis['recommendations'],
                    data_points_used=len(positions_data)
                )
                
                risk_results[RiskMetric.POSITION_CONCENTRATION] = RiskResult(
                    metric_type=RiskMetric.POSITION_CONCENTRATION,
                    risk_value=corr_analysis['concentration_risk'],
                    risk_level=self._classify_concentration_risk_level(corr_analysis['concentration_risk']),
                    calculation_method="herfindahl_index",
                    interpretation=f"Concentration: {corr_analysis['concentration_risk']:.1f}%"
                )
            
            # 4. Recovery Risk
            if recovery_data:
                recovery_analysis = self.recovery_risk_analyzer.analyze_recovery_risk(recovery_data, account_data)
                
                risk_results[RiskMetric.RECOVERY_RISK] = RiskResult(
                    metric_type=RiskMetric.RECOVERY_RISK,
                    risk_value=recovery_analysis['overall_recovery_risk'],
                    risk_level=RiskLevel(recovery_analysis['risk_level']) if isinstance(recovery_analysis['risk_level'], int) else RiskLevel.MODERATE,
                    calculation_method="recovery_system_analysis",
                    interpretation=f"Capital Utilization: {recovery_analysis['capital_utilization']:.1f}%",
                    recommendations=recovery_analysis['recommendations'],
                    warnings=recovery_analysis['capacity_warnings']
                )
            
            # 5. Performance Ratios
            if returns_data and len(returns_data) >= 30:
                sharpe_ratio = self._calculate_sharpe_ratio(returns_data)
                sortino_ratio = self._calculate_sortino_ratio(returns_data)
                
                risk_results[RiskMetric.SHARPE_RATIO] = RiskResult(
                    metric_type=RiskMetric.SHARPE_RATIO,
                    risk_value=sharpe_ratio,
                    risk_level=self._classify_ratio_risk_level(sharpe_ratio, "sharpe"),
                    calculation_method="sharpe_ratio",
                    interpretation=f"Risk-adjusted return: {sharpe_ratio:.2f}"
                )
                
                risk_results[RiskMetric.SORTINO_RATIO] = RiskResult(
                    metric_type=RiskMetric.SORTINO_RATIO,
                    risk_value=sortino_ratio,
                    risk_level=self._classify_ratio_risk_level(sortino_ratio, "sortino"),
                    calculation_method="sortino_ratio",
                    interpretation=f"Downside risk-adjusted return: {sortino_ratio:.2f}"
                )
            
            # สร้าง Portfolio Risk Summary
            summary = await self._create_portfolio_risk_summary(risk_results, positions_data, account_data)
            
            # บันทึกลง History
            self.risk_history.append({
                "timestamp": datetime.now(),
                "summary": summary,
                "timeframe": timeframe.value
            })
            
            self.calculation_count += 1
            
            self.logger.info(f"✅ คำนวณความเสี่ยงเสร็จสิ้น - Overall Score: {summary.overall_risk_score:.1f}")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณความเสี่ยง: {e}")
            return self._create_fallback_risk_summary()
    
    async def _update_risk_parameters(self) -> None:
        """อัพเดท Risk Parameters จาก External Sources"""
        try:
            with self.parameters_lock:
                # อัพเดท Account Data
                if hasattr(self, 'account_monitor'):
                    account_info = await self.account_monitor.get_account_info()
                    if account_info:
                        self.current_parameters.account_balance = account_info.get('balance', 10000.0)
                        self.current_parameters.account_equity = account_info.get('equity', 10000.0)
                        self.current_parameters.free_margin = account_info.get('free_margin', 10000.0)
                        self.current_parameters.used_margin = account_info.get('used_margin', 0.0)
                
                # อัพเดท Position Data
                if self.position_tracker:
                    positions = self.position_tracker.get_all_positions()
                    self.current_parameters.total_positions = len(positions)
                    self.current_parameters.open_lot_size = sum(pos.get('volume', 0) for pos in positions)
                    self.current_parameters.unrealized_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
                
                # อัพเดท Market Conditions
                if self.market_analyzer:
                    market_data = self.market_analyzer.get_current_market_state()
                    self.current_parameters.current_volatility = market_data.get('volatility_level', 1.0)
                    self.current_parameters.market_stress_level = market_data.get('stress_level', 0.0)
                
                # อัพเดท Recovery Data
                if self.recovery_engine:
                    recovery_info = self.recovery_engine.get_recovery_status()
                    self.current_parameters.active_recovery_tasks = recovery_info.get('active_tasks', 0)
                    self.current_parameters.recovery_capital_allocated = recovery_info.get('allocated_capital', 0.0)
                    self.current_parameters.avg_recovery_success_rate = recovery_info.get('success_rate', 95.0)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Risk Parameters: {e}")
    
    async def _get_positions_data(self) -> List[Dict[str, Any]]:
        """ดึงข้อมูล Positions"""
        try:
            if self.position_tracker:
                return self.position_tracker.get_all_positions()
            return []
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Positions: {e}")
            return []
    
    async def _get_equity_curve(self, timeframe: RiskTimeframe) -> List[float]:
        """ดึงข้อมูล Equity Curve"""
        try:
            if self.performance_tracker:
                days_back = self._get_days_back_for_timeframe(timeframe)
                return self.performance_tracker.get_equity_curve(days_back)
            return []
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึง Equity Curve: {e}")
            return []
    
    async def _get_returns_data(self, timeframe: RiskTimeframe) -> List[float]:
        """ดึงข้อมูล Returns"""
        try:
            if self.performance_tracker:
                days_back = self._get_days_back_for_timeframe(timeframe)
                return self.performance_tracker.get_returns_data(days_back)
            return []
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Returns: {e}")
            return []
    
    async def _get_recovery_data(self) -> Dict[str, Any]:
        """ดึงข้อมูล Recovery System"""
        try:
            if self.recovery_engine:
                return {
                    'allocated_capital': self.recovery_engine.get_allocated_capital(),
                    'active_tasks': self.recovery_engine.get_active_recovery_tasks(),
                    'success_rate': self.recovery_engine.get_success_rate(),
                    'method_distribution': self.recovery_engine.get_method_distribution()
                }
            return {}
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Recovery: {e}")
            return {}
    
    async def _get_account_data(self) -> Dict[str, Any]:
        """ดึงข้อมูล Account"""
        try:
            return {
                'balance': self.current_parameters.account_balance,
                'equity': self.current_parameters.account_equity,
                'free_margin': self.current_parameters.free_margin,
                'used_margin': self.current_parameters.used_margin
            }
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Account: {e}")
            return {'balance': 10000.0, 'equity': 10000.0, 'free_margin': 10000.0, 'used_margin': 0.0}
    
    def _get_days_back_for_timeframe(self, timeframe: RiskTimeframe) -> int:
        """กำหนดจำนวนวันย้อนหลังตาม Timeframe"""
        timeframe_days = {
            RiskTimeframe.INTRADAY: 1,
            RiskTimeframe.DAILY: 30,
            RiskTimeframe.WEEKLY: 90,
            RiskTimeframe.MONTHLY: 365,
            RiskTimeframe.ANNUAL: 1095  # 3 ปี
        }
        return timeframe_days.get(timeframe, 30)
    
    def _classify_var_risk_level(self, var_value: float) -> RiskLevel:
        """จำแนกระดับความเสี่ยงจาก VaR"""
        if var_value >= 10.0:
            return RiskLevel.CRITICAL
        elif var_value >= 7.0:
            return RiskLevel.HIGH
        elif var_value >= 4.0:
            return RiskLevel.MODERATE
        elif var_value >= 2.0:
            return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW
    
    def _classify_drawdown_risk_level(self, drawdown_percent: float) -> RiskLevel:
        """จำแนกระดับความเสี่ยงจาก Drawdown"""
        if drawdown_percent >= 20.0:
            return RiskLevel.CRITICAL
        elif drawdown_percent >= 15.0:
            return RiskLevel.HIGH
        elif drawdown_percent >= 10.0:
            return RiskLevel.MODERATE
        elif drawdown_percent >= 5.0:
            return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW
    
    def _classify_concentration_risk_level(self, concentration_percent: float) -> RiskLevel:
        """จำแนกระดับความเสี่ยงจาก Concentration"""
        if concentration_percent >= 80.0:
            return RiskLevel.CRITICAL
        elif concentration_percent >= 60.0:
            return RiskLevel.HIGH
        elif concentration_percent >= 40.0:
            return RiskLevel.MODERATE
        elif concentration_percent >= 20.0:
            return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW
    
    def _classify_ratio_risk_level(self, ratio_value: float, ratio_type: str) -> RiskLevel:
        """จำแนกระดับความเสี่ยงจาก Performance Ratios"""
        if ratio_type == "sharpe":
            if ratio_value >= 2.0:
                return RiskLevel.VERY_LOW   # Sharpe สูง = Risk ต่ำ
            elif ratio_value >= 1.0:
                return RiskLevel.LOW
            elif ratio_value >= 0.5:
                return RiskLevel.MODERATE
            elif ratio_value >= 0.0:
                return RiskLevel.HIGH
            else:
                return RiskLevel.CRITICAL   # Sharpe ติดลบ = Risk สูงมาก
        
        else:  # sortino
            if ratio_value >= 2.5:
                return RiskLevel.VERY_LOW
            elif ratio_value >= 1.5:
                return RiskLevel.LOW
            elif ratio_value >= 0.8:
                return RiskLevel.MODERATE
            elif ratio_value >= 0.0:
                return RiskLevel.HIGH
            else:
                return RiskLevel.CRITICAL
    
    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """คำนวณ Sharpe Ratio"""
        try:
            if len(returns) < 2:
                return 0.0
            
            mean_return = statistics.mean(returns)
            std_return = statistics.stdev(returns)
            
            if std_return == 0:
                return 0.0
            
            # สมมติ risk-free rate = 0 (สำหรับความง่าย)
            return mean_return / std_return
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Sharpe Ratio: {e}")
            return 0.0
    
    def _calculate_sortino_ratio(self, returns: List[float]) -> float:
        """คำนวณ Sortino Ratio"""
        try:
            if len(returns) < 2:
                return 0.0
            
            mean_return = statistics.mean(returns)
            
            # คำนวณ Downside Deviation
            negative_returns = [r for r in returns if r < 0]
            if not negative_returns:
                return float('inf') if mean_return > 0 else 0.0
            
            downside_deviation = statistics.stdev(negative_returns) if len(negative_returns) > 1 else abs(negative_returns[0])
            
            if downside_deviation == 0:
                return 0.0
            
            return mean_return / downside_deviation
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Sortino Ratio: {e}")
            return 0.0
    
    def _calculate_var_reliability(self, sample_size: int) -> float:
        """คำนวณความน่าเชื่อถือของ VaR"""
        if sample_size >= 250:  # 1 ปีของข้อมูลรายวัน
            return 95.0
        elif sample_size >= 120:  # 6 เดือน
            return 80.0
        elif sample_size >= 60:   # 3 เดือน
            return 60.0
        elif sample_size >= 30:   # 1 เดือน
            return 40.0
        else:
            return 20.0
    
    def _generate_drawdown_recommendations(self, dd_metrics: Dict[str, Any]) -> List[str]:
        """สร้างคำแนะนำจาก Drawdown Analysis"""
        recommendations = []
        
        max_dd = dd_metrics.get('maximum_drawdown', 0)
        current_dd = dd_metrics.get('current_drawdown', 0)
        duration = dd_metrics.get('current_drawdown_duration', 0)
        
        if current_dd > 15:
            recommendations.append("🚨 Current Drawdown สูงมาก - ลดการเสี่ยงทันที")
        elif current_dd > 10:
            recommendations.append("⚠️ Current Drawdown สูง - ระมัดระวังการเปิด positions ใหม่")
        
        if duration > 7:
            recommendations.append(f"⏰ อยู่ใน Drawdown นาน {duration} วัน - พิจารณาปรับ Strategy")
        
        if max_dd > 20:
            recommendations.append("📊 Maximum Drawdown เกินขีดจำกัด - ต้องปรับ Risk Management")
        
        return recommendations
    
    async def _create_portfolio_risk_summary(self, risk_results: Dict[RiskMetric, RiskResult],
                                            positions_data: List[Dict[str, Any]], 
                                            account_data: Dict[str, Any]) -> PortfolioRiskSummary:
        """สร้าง Portfolio Risk Summary"""
        try:
            # คำนวณ Overall Risk Score
            overall_score = self._calculate_overall_risk_score(risk_results)
            risk_level = self._determine_overall_risk_level(overall_score)
            
            # ดึงค่า Key Metrics
            var_result = risk_results.get(RiskMetric.VALUE_AT_RISK)
            dd_result = risk_results.get(RiskMetric.MAXIMUM_DRAWDOWN)
            corr_result = risk_results.get(RiskMetric.CORRELATION_RISK)
            conc_result = risk_results.get(RiskMetric.POSITION_CONCENTRATION)
            recovery_result = risk_results.get(RiskMetric.RECOVERY_RISK)
            
            # คำนวณ Risk Budget Usage
            daily_risk_used = self._calculate_daily_risk_usage()
            position_risk_used = self._calculate_position_risk_usage()
            margin_utilization = self._calculate_margin_utilization(account_data)
            
            # สร้าง Risk Contributors
            risk_contributors = self._identify_risk_contributors(positions_data, risk_results)
            
            # สร้าง Recommendations
            immediate_actions = self._generate_immediate_actions(risk_results, overall_score)
            optimization_suggestions = self._generate_optimization_suggestions(risk_results)
            
            return PortfolioRiskSummary(
                overall_risk_score=overall_score,
                risk_level=risk_level,
                
                # Key Metrics
                current_var_1d=var_result.risk_value if var_result else 0.0,
                current_drawdown=dd_result.risk_value if dd_result else 0.0,
                position_concentration=conc_result.risk_value if conc_result else 0.0,
                correlation_exposure=corr_result.risk_value if corr_result else 0.0,
                
                # Risk Budget Usage
                daily_risk_used=daily_risk_used,
                position_risk_used=position_risk_used,
                margin_utilization=margin_utilization,
                
                # Detailed Results
                individual_risks=risk_results,
                risk_contributors=risk_contributors,
                
                # Recovery Risk
                recovery_risk_level=recovery_result.risk_level if recovery_result else RiskLevel.LOW,
                recovery_capacity_remaining=self._calculate_recovery_capacity_remaining(),
                
                # Recommendations
                immediate_actions=immediate_actions,
                risk_optimization_suggestions=optimization_suggestions,
                
                # Metadata
                calculation_timestamp=datetime.now(),
                market_conditions_snapshot=await self._create_market_snapshot()
            )
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Portfolio Risk Summary: {e}")
            return self._create_fallback_risk_summary()
    
    def _calculate_overall_risk_score(self, risk_results: Dict[RiskMetric, RiskResult]) -> float:
        """คำนวณ Overall Risk Score"""
        try:
            # Weights สำหรับแต่ละ Risk Metric
            weights = {
                RiskMetric.VALUE_AT_RISK: 0.20,
                RiskMetric.MAXIMUM_DRAWDOWN: 0.25,
                RiskMetric.CORRELATION_RISK: 0.15,
                RiskMetric.POSITION_CONCENTRATION: 0.10,
                RiskMetric.RECOVERY_RISK: 0.20,
                RiskMetric.SHARPE_RATIO: 0.05,
                RiskMetric.SORTINO_RATIO: 0.05
            }
            
            total_score = 0.0
            total_weight = 0.0
            
            for metric, result in risk_results.items():
                weight = weights.get(metric, 0.05)
                
                # แปลง Risk Level เป็น Score (0-100)
                if metric in [RiskMetric.SHARPE_RATIO, RiskMetric.SORTINO_RATIO]:
                    # สำหรับ Performance Ratios, Risk Level ต่ำ = Score ต่ำ (ดี)
                    risk_score = (5 - result.risk_level.value) * 20
                else:
                    # สำหรับ Risk Metrics อื่นๆ, Risk Level สูง = Score สูง (แย่)
                    risk_score = result.risk_level.value * 20
                
                total_score += risk_score * weight
                total_weight += weight
            
            return total_score / total_weight if total_weight > 0 else 50.0
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Overall Risk Score: {e}")
            return 50.0
    
    def _determine_overall_risk_level(self, risk_score: float) -> RiskLevel:
        """กำหนด Overall Risk Level"""
        if risk_score >= 80:
            return RiskLevel.CRITICAL
        elif risk_score >= 60:
            return RiskLevel.HIGH
        elif risk_score >= 40:
            return RiskLevel.MODERATE
        elif risk_score >= 20:
            return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW
    
    def _calculate_daily_risk_usage(self) -> float:
        """คำนวณการใช้ Daily Risk Budget"""
        try:
            max_daily_risk = self.current_parameters.account_equity * (self.current_parameters.max_daily_risk_percent / 100)
            current_risk = abs(self.current_parameters.unrealized_pnl) + abs(self.current_parameters.realized_pnl_today)
            
            return (current_risk / max_daily_risk) * 100 if max_daily_risk > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Daily Risk Usage: {e}")
            return 0.0
    
    def _calculate_position_risk_usage(self) -> float:
        """คำนวณการใช้ Position Risk Budget"""
        try:
            max_position_risk = self.current_parameters.account_equity * (self.current_parameters.max_single_position_risk / 100)
            
            if self.current_parameters.total_positions == 0:
                return 0.0
            
            avg_position_risk = abs(self.current_parameters.unrealized_pnl) / self.current_parameters.total_positions
            
            return (avg_position_risk / max_position_risk) * 100 if max_position_risk > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Position Risk Usage: {e}")
            return 0.0
    
    def _calculate_margin_utilization(self, account_data: Dict[str, Any]) -> float:
        """คำนวณการใช้ Margin"""
        try:
            total_margin = account_data.get('free_margin', 0) + account_data.get('used_margin', 0)
            used_margin = account_data.get('used_margin', 0)
            
            return (used_margin / total_margin) * 100 if total_margin > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Margin Utilization: {e}")
            return 0.0
    
    def _identify_risk_contributors(self, positions_data: List[Dict[str, Any]], 
                                    risk_results: Dict[RiskMetric, RiskResult]) -> List[Dict[str, Any]]:
        """ระบุตัวการสำคัญที่ก่อให้เกิดความเสี่ยง"""
        contributors = []
        
        try:
            # Risk จาก Positions แต่ละตัว
            for pos in positions_data:
                position_risk = abs(pos.get('unrealized_pnl', 0))
                if position_risk > 0:
                    contributors.append({
                        "type": "position",
                        "id": pos.get('position_id', 'UNKNOWN'),
                        "risk_amount": position_risk,
                        "risk_percentage": (position_risk / self.current_parameters.account_equity) * 100,
                        "description": f"Position {pos.get('symbol', 'UNKNOWN')} {pos.get('direction', 'UNKNOWN')}"
                    })
            
            # Risk จาก Recovery System
            recovery_result = risk_results.get(RiskMetric.RECOVERY_RISK)
            if recovery_result and recovery_result.risk_value > 0:
                contributors.append({
                    "type": "recovery_system",
                    "id": "recovery_system",
                    "risk_amount": self.current_parameters.recovery_capital_allocated,
                    "risk_percentage": recovery_result.risk_value,
                    "description": f"Recovery System ({self.current_parameters.active_recovery_tasks} active tasks)"
                })
            
            # เรียงตาม Risk Amount
            contributors.sort(key=lambda x: x['risk_amount'], reverse=True)
            
            return contributors[:10]  # Top 10 contributors
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการระบุ Risk Contributors: {e}")
            return []
    
    def _calculate_recovery_capacity_remaining(self) -> float:
        """คำนวณ Recovery Capacity ที่เหลือ"""
        try:
            max_recovery_budget = self.current_parameters.account_equity * 0.20  # 20% ของ equity
            used_recovery_capital = self.current_parameters.recovery_capital_allocated
            
            remaining = max_recovery_budget - used_recovery_capital
            return (remaining / max_recovery_budget) * 100 if max_recovery_budget > 0 else 100.0
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Recovery Capacity: {e}")
            return 100.0
    
    def _generate_immediate_actions(self, risk_results: Dict[RiskMetric, RiskResult], 
                                    overall_score: float) -> List[str]:
        """สร้างคำแนะนำสำหรับการดำเนินการทันที"""
        actions = []
        
        try:
            # ตาม Overall Score
            if overall_score >= 80:
                actions.append("🚨 ความเสี่ยงระดับวิกฤต - หยุดเปิด positions ใหม่ทันที")
                actions.append("🛑 ปิด positions ที่มีความเสี่ยงสูงที่สุด")
            elif overall_score >= 60:
                actions.append("⚠️ ความเสี่ยงสูง - จำกัดการเปิด positions ใหม่")
                actions.append("🔍 ตรวจสอบ Risk Management parameters")
            
            # ตาม Specific Risks
            dd_result = risk_results.get(RiskMetric.MAXIMUM_DRAWDOWN)
            if dd_result and dd_result.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                actions.append("📉 Drawdown สูงเกินไป - ลดขนาด positions")
            
            corr_result = risk_results.get(RiskMetric.CORRELATION_RISK)
            if corr_result and corr_result.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                actions.append("🔗 Correlation Risk สูง - เพิ่ม diversification")
            
            recovery_result = risk_results.get(RiskMetric.RECOVERY_RISK)
            if recovery_result and recovery_result.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                actions.append("🔄 Recovery Risk สูง - ปรับ Recovery Strategy")
            
            return actions[:5]  # จำกัดไม่เกิน 5 actions
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Immediate Actions: {e}")
            return []
    
    def _generate_optimization_suggestions(self, risk_results: Dict[RiskMetric, RiskResult]) -> List[str]:
        """สร้างคำแนะนำสำหรับการเพิ่มประสิทธิภาพ"""
        suggestions = []
        
        try:
            # Performance Ratio Improvements
            sharpe_result = risk_results.get(RiskMetric.SHARPE_RATIO)
            if sharpe_result and sharpe_result.risk_value < 1.0:
                suggestions.append("📈 ปรับปรุง Sharpe Ratio ด้วยการลด Volatility")
            
            # Concentration Improvements
            conc_result = risk_results.get(RiskMetric.POSITION_CONCENTRATION)
            if conc_result and conc_result.risk_value > 60:
                suggestions.append("🎯 เพิ่ม Diversification เพื่อลด Concentration Risk")
            
            # Recovery Optimization
            recovery_result = risk_results.get(RiskMetric.RECOVERY_RISK)
            if recovery_result and recovery_result.risk_value > 40:
                suggestions.append("⚙️ ปรับแต่ง Recovery Methods ให้มีประสิทธิภาพมากขึ้น")
            
            # General Optimizations
            suggestions.append("📊 ติดตาม Risk Metrics แบบ Real-time")
            suggestions.append("🔧 ปรับ Position Sizing ตาม Market Volatility")
            
            return suggestions[:5]
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Optimization Suggestions: {e}")
            return []
    
    async def _create_market_snapshot(self) -> Dict[str, Any]:
        """สร้าง Market Conditions Snapshot"""
        try:
            if self.market_analyzer:
                return {
                    "market_state": self.market_analyzer.get_market_state(),
                    "volatility_level": self.current_parameters.current_volatility,
                    "stress_level": self.current_parameters.market_stress_level,
                    "liquidity_level": self.current_parameters.liquidity_level,
                    "session": self.market_analyzer.get_current_session().value if hasattr(self.market_analyzer, 'get_current_session') else 'UNKNOWN'
                }
            return {}
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้าง Market Snapshot: {e}")
            return {}
    
    def _create_fallback_risk_summary(self) -> PortfolioRiskSummary:
        """สร้าง Fallback Risk Summary เมื่อเกิดข้อผิดพลาด"""
        return PortfolioRiskSummary(
            overall_risk_score=50.0,
            risk_level=RiskLevel.MODERATE,
            current_var_1d=0.0,
            current_drawdown=0.0,
            position_concentration=0.0,
            correlation_exposure=0.0,
            daily_risk_used=0.0,
            position_risk_used=0.0,
            margin_utilization=0.0,
            individual_risks={},
            risk_contributors=[],
            recovery_risk_level=RiskLevel.LOW,
            recovery_capacity_remaining=100.0,
            immediate_actions=["⚠️ ไม่สามารถคำนวณความเสี่ยงได้ - ตรวจสอบระบบ"],
            risk_optimization_suggestions=[],
            calculation_timestamp=datetime.now(),
            market_conditions_snapshot={}
        )
    
    async def _start_risk_monitoring(self) -> None:
        """เริ่ม Risk Monitoring แบบต่อเนื่อง"""
        if self.risk_monitor_active:
            return
        
        self.risk_monitor_active = True
        self.monitor_thread = threading.Thread(target=self._risk_monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("📊 เริ่ม Risk Monitoring แบบต่อเนื่อง")
    
    def _risk_monitoring_loop(self) -> None:
        """Risk Monitoring Loop"""
        try:
            while self.risk_monitor_active:
                # อัพเดท Risk Parameters ทุก 30 วินาที
                asyncio.run(self._update_risk_parameters())
                
                # คำนวณความเสี่ยงทุก 5 นาที
                if self.calculation_count % 10 == 0:  # ทุก 10 รอบ = 5 นาที
                    summary = asyncio.run(self.calculate_comprehensive_risk(RiskTimeframe.INTRADAY))
                    
                    # ตรวจสอบ Critical Risk
                    if summary.risk_level == RiskLevel.CRITICAL:
                        self.logger.critical(f"🚨 CRITICAL RISK DETECTED - Score: {summary.overall_risk_score:.1f}")
                
                time.sleep(30)  # รอ 30 วินาที
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Risk Monitoring Loop: {e}")
        finally:
            self.risk_monitor_active = False
    
    def stop_risk_calculator(self) -> None:
        """หยุด Risk Calculator"""
        self.risk_monitor_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("🛑 หยุด Risk Calculator")
    
    def get_risk_statistics(self) -> Dict[str, Any]:
        """ดึงสถิติ Risk Calculator"""
        try:
            recent_calculations = list(self.risk_history)[-10:] if self.risk_history else []
            
            return {
                "total_calculations": self.calculation_count,
                "recent_calculations_count": len(recent_calculations),
                "average_risk_score": statistics.mean([calc["summary"].overall_risk_score for calc in recent_calculations]) if recent_calculations else 0.0,
                "current_risk_level": recent_calculations[-1]["summary"].risk_level.value if recent_calculations else "UNKNOWN",
                "risk_parameters": {
                    "max_daily_risk_percent": self.current_parameters.max_daily_risk_percent,
                    "max_single_position_risk": self.current_parameters.max_single_position_risk,
                    "max_correlation_exposure": self.current_parameters.max_correlation_exposure,
                    "max_drawdown_limit": self.current_parameters.max_drawdown_limit
                },
                "monitoring_status": "ACTIVE" if self.risk_monitor_active else "INACTIVE"
            }
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงสถิติ: {e}")
            return {}

# Global Risk Calculator Instance
_global_risk_calculator: Optional[RiskCalculator] = None

def get_risk_calculator() -> RiskCalculator:
    """
    ดึง Risk Calculator Instance (Singleton Pattern)
    
    Returns:
        RiskCalculator: Instance ของ Risk Calculator
    """
    global _global_risk_calculator
    
    if _global_risk_calculator is None:
        _global_risk_calculator = RiskCalculator()
    
    return _global_risk_calculator

# Utility Functions
async def quick_risk_assessment(timeframe: RiskTimeframe = RiskTimeframe.DAILY) -> PortfolioRiskSummary:
    """
    ประเมินความเสี่ยงแบบเร็ว
    
    Args:
        timeframe: กรอบเวลาสำหรับการประเมิน
        
    Returns:
        PortfolioRiskSummary: สรุปความเสี่ยงแบบย่อ
    """
    risk_calculator = get_risk_calculator()
    return await risk_calculator.calculate_comprehensive_risk(timeframe)

async def calculate_position_risk(position_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    คำนวณความเสี่ยงของ Position เดียว
    
    Args:
        position_data: ข้อมูล Position
        
    Returns:
        Dict: Risk metrics ของ Position
    """
    try:
        risk_calculator = get_risk_calculator()
        
        position_value = abs(position_data.get('unrealized_pnl', 0) + 
                            position_data.get('volume', 0) * 1000)
        
        account_equity = risk_calculator.current_parameters.account_equity
        
        risk_percentage = (position_value / account_equity) * 100 if account_equity > 0 else 0.0
        
        # จำแนก Risk Level
        if risk_percentage >= 10:
            risk_level = RiskLevel.CRITICAL
        elif risk_percentage >= 5:
            risk_level = RiskLevel.HIGH
        elif risk_percentage >= 2:
            risk_level = RiskLevel.MODERATE
        elif risk_percentage >= 1:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.VERY_LOW
        
        return {
            "position_id": position_data.get('position_id', 'UNKNOWN'),
            "risk_amount": position_value,
            "risk_percentage": risk_percentage,
            "risk_level": risk_level.value,
            "risk_level_name": risk_level.name,
            "recommendations": _generate_position_risk_recommendations(risk_level, risk_percentage)
        }
        
    except Exception as e:
        return {
            "error": f"ไม่สามารถคำนวณความเสี่ยงได้: {e}",
            "risk_level": RiskLevel.MODERATE.value
        }

def _generate_position_risk_recommendations(risk_level: RiskLevel, risk_percentage: float) -> List[str]:
    """สร้างคำแนะนำสำหรับ Position Risk"""
    recommendations = []
    
    if risk_level == RiskLevel.CRITICAL:
        recommendations.append("🚨 ความเสี่ยงสูงมาก - พิจารณาปิด Position ทันที")
        recommendations.append("🛑 หยุดเพิ่ม Volume ใน Position นี้")
    elif risk_level == RiskLevel.HIGH:
        recommendations.append("⚠️ ความเสี่ยงสูง - ลดขนาด Position")
        recommendations.append("🔍 ติดตามใกล้ชิดสำหรับการ Recovery")
    elif risk_level == RiskLevel.MODERATE:
        recommendations.append("📊 ความเสี่ยงปานกลาง - ติดตามต่อไป")
        recommendations.append("💡 พิจารณาใช้ Recovery Method ที่เหมาะสม")
    else:
        recommendations.append("✅ ความเสี่ยงต่ำ - สามารถดำเนินการต่อได้")
    
    return recommendations

def calculate_recovery_risk_impact(recovery_method: RecoveryMethod, 
                                original_loss: float, 
                                account_equity: float) -> Dict[str, Any]:
    """
    คำนวณผลกระทบความเสี่ยงจาก Recovery Method
    
    Args:
        recovery_method: วิธี Recovery
        original_loss: ขาดทุนเริ่มต้น
        account_equity: Equity ของบัญชี
        
    Returns:
        Dict: Risk impact analysis
    """
    try:
        # Risk Multipliers ตาม Recovery Method
        risk_multipliers = {
            RecoveryMethod.MARTINGALE_SMART: 3.0,      # Martingale มีความเสี่ยงสูงสุด
            RecoveryMethod.GRID_INTELLIGENT: 2.0,     # Grid มีความเสี่ยงปานกลาง
            RecoveryMethod.HEDGING_ADVANCED: 1.2,     # Hedging มีความเสี่ยงต่ำ
            RecoveryMethod.AVERAGING_INTELLIGENT: 1.5, # Averaging มีความเสี่ยงปานกลาง
            RecoveryMethod.CORRELATION_RECOVERY: 1.1   # Correlation มีความเสี่ยงต่ำสุด
        }
        
        multiplier = risk_multipliers.get(recovery_method, 2.0)
        max_potential_loss = abs(original_loss) * multiplier
        risk_percentage = (max_potential_loss / account_equity) * 100 if account_equity > 0 else 0.0
        
        # กำหนด Risk Level
        if risk_percentage >= 15:
            risk_level = RiskLevel.CRITICAL
        elif risk_percentage >= 10:
            risk_level = RiskLevel.HIGH
        elif risk_percentage >= 5:
            risk_level = RiskLevel.MODERATE
        elif risk_percentage >= 2:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.VERY_LOW
        
        # สร้างคำแนะนำ
        recommendations = []
        if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            recommendations.append("⚠️ Recovery Method นี้มีความเสี่ยงสูง")
            recommendations.append("💡 พิจารณาใช้ Recovery Method ที่ปลอดภัยกว่า")
        
        return {
            "recovery_method": recovery_method.value,
            "original_loss": abs(original_loss),
            "max_potential_loss": max_potential_loss,
            "risk_multiplier": multiplier,
            "risk_percentage": risk_percentage,
            "risk_level": risk_level.value,
            "risk_level_name": risk_level.name,
            "is_acceptable": risk_level in [RiskLevel.VERY_LOW, RiskLevel.LOW, RiskLevel.MODERATE],
            "recommendations": recommendations
        }
        
    except Exception as e:
        return {
            "error": f"ไม่สามารถคำนวณ Recovery Risk ได้: {e}",
            "is_acceptable": False
        }

def get_risk_limits() -> Dict[str, float]:
    """
    ดึงขีดจำกัดความเสี่ยงปัจจุบัน
    
    Returns:
        Dict: Risk limits configuration
    """
    risk_calculator = get_risk_calculator()
    params = risk_calculator.current_parameters
    
    return {
        "max_daily_risk_percent": params.max_daily_risk_percent,
        "max_single_position_risk": params.max_single_position_risk,
        "max_correlation_exposure": params.max_correlation_exposure,
        "max_drawdown_limit": params.max_drawdown_limit,
        "current_daily_risk_used": risk_calculator._calculate_daily_risk_usage(),
        "current_position_risk_used": risk_calculator._calculate_position_risk_usage(),
        "margin_utilization": risk_calculator._calculate_margin_utilization({
            'free_margin': params.free_margin,
            'used_margin': params.used_margin
        })
    }

async def stress_test_portfolio(stress_scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    ทำ Stress Test กับ Portfolio
    
    Args:
        stress_scenarios: รายการ Stress scenarios
        
    Returns:
        Dict: ผลการ Stress Test
    """
    try:
        risk_calculator = get_risk_calculator()
        
        # ดึงข้อมูล Portfolio ปัจจุบัน
        current_summary = await risk_calculator.calculate_comprehensive_risk()
        
        stress_results = []
        
        for scenario in stress_scenarios:
            scenario_name = scenario.get('name', 'Unknown Scenario')
            price_shock = scenario.get('price_shock_percent', 0.0)  # % การเปลี่ยนแปลงราคา
            volatility_multiplier = scenario.get('volatility_multiplier', 1.0)
            correlation_increase = scenario.get('correlation_increase', 0.0)
            
            # จำลองผลกระทบ
            stressed_var = current_summary.current_var_1d * (1 + price_shock / 100) * volatility_multiplier
            stressed_correlation = min(1.0, current_summary.correlation_exposure + correlation_increase)
            
            # คำนวณ Portfolio Value impact
            portfolio_impact = abs(price_shock) * current_summary.position_concentration / 100
            
            # กำหนด Severity
            if portfolio_impact >= 20:
                severity = "EXTREME"
            elif portfolio_impact >= 10:
                severity = "HIGH"
            elif portfolio_impact >= 5:
                severity = "MEDIUM"
            else:
                severity = "LOW"
            
            stress_results.append({
                "scenario_name": scenario_name,
                "price_shock_percent": price_shock,
                "portfolio_impact_percent": portfolio_impact,
                "stressed_var": stressed_var,
                "stressed_correlation": stressed_correlation,
                "severity": severity,
                "survival_probability": max(0, 100 - portfolio_impact * 2),  # ประมาณการ
                "recovery_time_estimate": abs(portfolio_impact) * 2  # วัน
            })
        
        # หา Worst Case Scenario
        worst_case = max(stress_results, key=lambda x: x['portfolio_impact_percent']) if stress_results else None
        
        return {
            "current_portfolio_state": {
                "overall_risk_score": current_summary.overall_risk_score,
                "risk_level": current_summary.risk_level.value
            },
            "stress_test_results": stress_results,
            "worst_case_scenario": worst_case,
            "portfolio_resilience": _calculate_portfolio_resilience(stress_results),
            "recommendations": _generate_stress_test_recommendations(stress_results)
        }
        
    except Exception as e:
        return {
            "error": f"ไม่สามารถทำ Stress Test ได้: {e}",
            "stress_test_results": []
        }

def _calculate_portfolio_resilience(stress_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """คำนวณความยืดหยุ่นของ Portfolio"""
    if not stress_results:
        return {"score": 0, "level": "UNKNOWN"}
    
    # คำนวณค่าเฉลี่ยของ survival probability
    avg_survival = statistics.mean([result['survival_probability'] for result in stress_results])
    
    # คำนวณค่าเฉลี่ยของ portfolio impact
    avg_impact = statistics.mean([result['portfolio_impact_percent'] for result in stress_results])
    
    # คำนวณ Resilience Score
    resilience_score = (avg_survival + max(0, 100 - avg_impact * 2)) / 2
    
    # กำหนดระดับ
    if resilience_score >= 80:
        level = "EXCELLENT"
    elif resilience_score >= 60:
        level = "GOOD"
    elif resilience_score >= 40:
        level = "FAIR"
    elif resilience_score >= 20:
        level = "POOR"
    else:
        level = "CRITICAL"
    
    return {
        "score": resilience_score,
        "level": level,
        "average_survival_probability": avg_survival,
        "average_impact": avg_impact
    }

def _generate_stress_test_recommendations(stress_results: List[Dict[str, Any]]) -> List[str]:
    """สร้างคำแนะนำจากผล Stress Test"""
    recommendations = []
    
    if not stress_results:
        return ["ไม่สามารถสร้างคำแนะนำได้ - ไม่มีผล Stress Test"]
    
    # หา High Impact Scenarios
    high_impact_scenarios = [r for r in stress_results if r['severity'] in ['HIGH', 'EXTREME']]
    
    if high_impact_scenarios:
        recommendations.append(f"⚠️ มี {len(high_impact_scenarios)} scenarios ที่ส่งผลกระทบสูง")
        recommendations.append("🛡️ เพิ่มมาตรการป้องกันความเสี่ยงในสถานการณ์วิกฤต")
    
    # ตรวจสอบ Recovery Time
    max_recovery_time = max([r['recovery_time_estimate'] for r in stress_results])
    if max_recovery_time > 30:  # มากกว่า 30 วัน
        recommendations.append(f"⏰ เวลา Recovery สูงสุด {max_recovery_time:.1f} วัน - ปรับ Recovery Strategy")
    
    # ตรวจสอบ Survival Probability
    min_survival = min([r['survival_probability'] for r in stress_results])
    if min_survival < 70:
        recommendations.append(f"🚨 Survival Probability ต่ำสุด {min_survival:.1f}% - ลดความเสี่ยง")
    
    return recommendations

if __name__ == "__main__":
    """
    ทดสอบ Risk Calculator System
    """
    import asyncio
    
    async def test_risk_calculator():
        """ทดสอบการทำงานของ Risk Calculator"""
        
        print("🧪 เริ่มทดสอบ Risk Calculator System")
        
        # เริ่มต้น Risk Calculator
        risk_calculator = get_risk_calculator()
        await risk_calculator.start_risk_calculator()
        
        try:
            # ทดสอบการคำนวณความเสี่ยงครอบคลุม
            print("\n📊 ทดสอบการคำนวณความเสี่ยงครอบคลุม...")
            risk_summary = await risk_calculator.calculate_comprehensive_risk(RiskTimeframe.DAILY)
            
            print(f"   Overall Risk Score: {risk_summary.overall_risk_score:.1f}/100")
            print(f"   Risk Level: {risk_summary.risk_level.name}")
            print(f"   Current VaR (1D): {risk_summary.current_var_1d:.2f}")
            print(f"   Current Drawdown: {risk_summary.current_drawdown:.2f}%")
            print(f"   Position Concentration: {risk_summary.position_concentration:.1f}%")
            print(f"   Correlation Exposure: {risk_summary.correlation_exposure:.1f}%")
            
            print(f"\n📈 Risk Budget Usage:")
            print(f"   Daily Risk Used: {risk_summary.daily_risk_used:.1f}%")
            print(f"   Position Risk Used: {risk_summary.position_risk_used:.1f}%")
            print(f"   Margin Utilization: {risk_summary.margin_utilization:.1f}%")
            
            if risk_summary.immediate_actions:
                print(f"\n🚨 Immediate Actions:")
                for action in risk_summary.immediate_actions:
                    print(f"   {action}")
            
            if risk_summary.risk_optimization_suggestions:
                print(f"\n💡 Optimization Suggestions:")
                for suggestion in risk_summary.risk_optimization_suggestions:
                    print(f"   {suggestion}")
            
            # ทดสอบ Position Risk
            print(f"\n🔍 ทดสอบ Position Risk...")
            test_position = {
                "position_id": "TEST_POS_001",
                "symbol": "XAUUSD",
                "direction": "BUY",
                "volume": 0.1,
                "unrealized_pnl": -150.0
            }
            
            position_risk = await calculate_position_risk(test_position)
            print(f"   Position Risk: {position_risk['risk_percentage']:.2f}%")
            print(f"   Risk Level: {position_risk['risk_level_name']}")
            
            # ทดสอบ Recovery Risk
            print(f"\n🔄 ทดสอบ Recovery Risk...")
            recovery_risk = calculate_recovery_risk_impact(
                RecoveryMethod.MARTINGALE_SMART, 
                -100.0, 
                risk_calculator.current_parameters.account_equity
            )
            print(f"   Recovery Method: {recovery_risk['recovery_method']}")
            print(f"   Max Potential Loss: ${recovery_risk['max_potential_loss']:.2f}")
            print(f"   Risk Percentage: {recovery_risk['risk_percentage']:.2f}%")
            print(f"   Acceptable: {recovery_risk['is_acceptable']}")
            
            # ทดสอบ Stress Test
            print(f"\n🧪 ทดสอบ Stress Test...")
            stress_scenarios = [
                {"name": "Market Crash", "price_shock_percent": -10, "volatility_multiplier": 2.0},
                {"name": "High Volatility", "price_shock_percent": 5, "volatility_multiplier": 3.0},
                {"name": "Correlation Spike", "price_shock_percent": 0, "correlation_increase": 0.3}
            ]
            
            stress_results = await stress_test_portfolio(stress_scenarios)
            print(f"   Portfolio Resilience: {stress_results['portfolio_resilience']['level']}")
            print(f"   Resilience Score: {stress_results['portfolio_resilience']['score']:.1f}")
            
            if stress_results.get('worst_case_scenario'):
                worst = stress_results['worst_case_scenario']
                print(f"   Worst Case: {worst['scenario_name']} ({worst['portfolio_impact_percent']:.1f}% impact)")
            
            # แสดงสถิติ
            stats = risk_calculator.get_risk_statistics()
            print(f"\n📈 Risk Calculator Statistics:")
            print(f"   Total Calculations: {stats['total_calculations']}")
            print(f"   Monitoring Status: {stats['monitoring_status']}")
            print(f"   Current Risk Level: {stats['current_risk_level']}")
            
        finally:
            risk_calculator.stop_risk_calculator()
        
        print("\n✅ ทดสอบ Risk Calculator เสร็จสิ้น")
    
    # รันการทดสอบ
    asyncio.run(test_risk_calculator())