#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELLIGENT RECOVERY SELECTOR - ระบบเลือกวิธี Recovery อัจฉริยะ
========================================================
เลือกวิธี Recovery ที่เหมาะสมที่สุดตามสภาพตลาดและสถานการณ์การขาดทุน
รองรับการปรับตัวและเรียนรู้จากประสิทธิภาพการ Recovery

เชื่อมต่อไปยัง:
- market_intelligence/market_analyzer.py (การวิเคราะห์ตลาด)
- intelligent_recovery/strategies/* (วิธี Recovery ต่างๆ)
- position_management/position_tracker.py (ติดตาม positions)
- config/trading_params.py (พารามิเตอร์ Recovery)
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
        get_market_analyzer, MarketCondition, TrendDirection, MarketAnalysis
    )
    from config.trading_params import get_trading_parameters, RecoveryMethod
    from config.session_config import get_session_manager, SessionType
    from utilities.professional_logger import setup_trading_logger
    from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity
except ImportError as e:
    print(f"Import Error in recovery_selector.py: {e}")

class RecoveryUrgency(Enum):
    """ระดับความเร่งด่วนในการ Recovery"""
    LOW = "LOW"           # ขาดทุนน้อย ไม่เร่งด่วน
    MEDIUM = "MEDIUM"     # ขาดทุนปานกลาง ต้องระวัง
    HIGH = "HIGH"         # ขาดทุนมาก ต้องรีบ Recovery
    CRITICAL = "CRITICAL" # ขาดทุนมากมาย ต้อง Recovery ทันที

class RecoverySuccess(Enum):
    """ผลสำเร็จของการ Recovery"""
    PENDING = "PENDING"           # กำลัง Recovery
    SUCCESS = "SUCCESS"           # Recovery สำเร็จ
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"  # Recovery บางส่วน
    FAILED = "FAILED"             # Recovery ไม่สำเร็จ
    ABANDONED = "ABANDONED"       # ยกเลิก Recovery

@dataclass
class LossPosition:
    """ข้อมูล Position ที่ขาดทุน"""
    position_id: str
    symbol: str
    entry_price: float
    current_price: float
    volume: float
    loss_amount: float
    loss_percentage: float
    entry_time: datetime
    holding_time_minutes: float
    entry_strategy: str
    market_condition_at_entry: str

@dataclass
class RecoveryStats:
    """สถิติประสิทธิภาพของวิธี Recovery"""
    method: RecoveryMethod
    total_attempts: int = 0
    successful_recoveries: int = 0
    partial_recoveries: int = 0
    failed_recoveries: int = 0
    total_recovery_time_minutes: float = 0.0
    total_recovery_cost: float = 0.0  # ต้นทุนเพิ่มเติมในการ Recovery
    avg_recovery_time: float = 0.0
    success_rate: float = 0.0
    efficiency_score: float = 0.0  # คะแนนประสิทธิภาพรวม
    
    # ประสิทธิภาพในสภาพตลาดต่างๆ
    condition_success_rates: Dict[str, float] = field(default_factory=dict)
    urgency_success_rates: Dict[str, float] = field(default_factory=dict)
    
    def update_stats(self):
        """อัพเดทสถิติที่คำนวณได้"""
        if self.total_attempts > 0:
            self.success_rate = (self.successful_recoveries / self.total_attempts) * 100
            
            if self.successful_recoveries > 0:
                self.avg_recovery_time = self.total_recovery_time_minutes / self.successful_recoveries
            
            # คำนวณ efficiency score
            success_weight = self.success_rate / 100
            time_weight = max(0, 1.0 - (self.avg_recovery_time / 1440))  # 1440 min = 1 day
            cost_weight = max(0, 1.0 - (abs(self.total_recovery_cost) / 1000))  # normalize by 1000
            
            self.efficiency_score = (success_weight * 0.6 + time_weight * 0.2 + cost_weight * 0.2)

@dataclass
class RecoveryRecommendation:
    """คำแนะนำวิธี Recovery"""
    primary_method: RecoveryMethod
    alternative_methods: List[RecoveryMethod]
    confidence_score: float  # 0.0-1.0
    urgency_level: RecoveryUrgency
    estimated_recovery_time_minutes: float
    estimated_additional_risk: float  # ความเสี่ยงเพิ่มเติม
    recommended_parameters: Dict[str, Any]
    reasoning: List[str]
    success_probability: float  # 0.0-1.0

class RecoverySelector:
    """
    ตัวเลือกวิธี Recovery อัจฉริยะ
    เลือกวิธี Recovery ที่เหมาะสมที่สุดตามสถานการณ์
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.market_analyzer = get_market_analyzer()
        self.session_manager = get_session_manager()
        self.trading_params = get_trading_parameters()
        
        # สถิติประสิทธิภาพ
        self.recovery_stats: Dict[RecoveryMethod, RecoveryStats] = {}
        self.active_recoveries: Dict[str, Dict] = {}  # recovery_id -> recovery_info
        self.recovery_history: List[Dict] = []
        
        # การตั้งค่า
        self.min_attempts_for_stats = 5  # จำนวนครั้งขั้นต่ำก่อนใช้สถิติ
        self.max_concurrent_recoveries = 10  # จำนวน Recovery พร้อมกันสูงสุด
        
        # Threading
        self.selector_lock = threading.Lock()
        
        # เริ่มต้นสถิติ
        self._initialize_recovery_stats()
        
        self.logger.info("🔄 เริ่มต้น Recovery Selector")
    
    def _initialize_recovery_stats(self):
        """เริ่มต้นสถิติสำหรับวิธี Recovery ทั้งหมด"""
        for method in RecoveryMethod:
            self.recovery_stats[method] = RecoveryStats(method=method)
    
    @handle_trading_errors(ErrorCategory.RECOVERY, ErrorSeverity.HIGH)
    def select_recovery_method(self, loss_positions: List[LossPosition]) -> Optional[RecoveryRecommendation]:
        """
        เลือกวิธี Recovery ที่เหมาะสมสำหรับ positions ที่ขาดทุน
        """
        with self.selector_lock:
            try:
                if not loss_positions:
                    return None
                
                # วิเคราะห์สถานการณ์การขาดทุน
                loss_analysis = self._analyze_loss_situation(loss_positions)
                
                # วิเคราะห์ตลาดปัจจุบัน
                market_analysis = self.market_analyzer.get_current_analysis()
                if not market_analysis:
                    self.logger.warning("⚠️ ไม่สามารถวิเคราะห์ตลาดสำหรับ Recovery ได้")
                    return None
                
                # คำนวณระดับความเร่งด่วน
                urgency_level = self._calculate_urgency_level(loss_analysis)
                
                # คำนวณคะแนนสำหรับแต่ละวิธี Recovery
                method_scores = self._calculate_recovery_scores(
                    loss_analysis, 
                    market_analysis, 
                    urgency_level
                )
                
                # เลือกวิธีที่ดีที่สุด
                best_method = max(method_scores.keys(), key=lambda m: method_scores[m])
                
                # เรียงวิธีทางเลือก
                alternative_methods = sorted(
                    [m for m in method_scores.keys() if m != best_method],
                    key=lambda m: method_scores[m],
                    reverse=True
                )[:2]
                
                # สร้างคำแนะนำ
                recommendation = self._create_recovery_recommendation(
                    best_method,
                    alternative_methods,
                    method_scores[best_method],
                    loss_analysis,
                    market_analysis,
                    urgency_level
                )
                
                self.logger.info(
                    f"🔄 เลือกวิธี Recovery: {best_method.value} "
                    f"(Confidence: {recommendation.confidence_score:.2f}) "
                    f"Urgency: {urgency_level.value} "
                    f"Loss: {loss_analysis['total_loss']:.2f}"
                )
                
                return recommendation
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดในการเลือกวิธี Recovery: {e}")
                return None
    
    def _analyze_loss_situation(self, loss_positions: List[LossPosition]) -> Dict:
        """วิเคราะห์สถานการณ์การขาดทุน"""
        
        total_loss = sum(pos.loss_amount for pos in loss_positions)
        total_volume = sum(pos.volume for pos in loss_positions)
        avg_loss_percentage = statistics.mean([pos.loss_percentage for pos in loss_positions])
        max_loss_percentage = max(pos.loss_percentage for pos in loss_positions)
        
        # วิเคราะห์การกระจายของ positions
        symbols = list(set(pos.symbol for pos in loss_positions))
        entry_strategies = list(set(pos.entry_strategy for pos in loss_positions))
        
        # คำนวณเวลาถือ position เฉลี่ย
        avg_holding_time = statistics.mean([pos.holding_time_minutes for pos in loss_positions])
        max_holding_time = max(pos.holding_time_minutes for pos in loss_positions)
        
        # วิเคราะห์ pattern การขาดทุน
        loss_trend = self._analyze_loss_trend(loss_positions)
        
        return {
            "position_count": len(loss_positions),
            "total_loss": total_loss,
            "total_volume": total_volume,
            "avg_loss_percentage": avg_loss_percentage,
            "max_loss_percentage": max_loss_percentage,
            "symbols": symbols,
            "entry_strategies": entry_strategies,
            "avg_holding_time": avg_holding_time,
            "max_holding_time": max_holding_time,
            "loss_trend": loss_trend,
            "loss_concentration": len(symbols) / len(loss_positions)  # ค่าใกล้ 1 = กระจาย, ใกล้ 0 = รวมกัน
        }
    
    def _analyze_loss_trend(self, loss_positions: List[LossPosition]) -> str:
        """วิเคราะห์แนวโน้มการขาดทุน"""
        
        # เรียงตามเวลา entry
        sorted_positions = sorted(loss_positions, key=lambda p: p.entry_time)
        
        if len(sorted_positions) < 2:
            return "STABLE"
        
        # คำนวณแนวโน้มการขาดทุน
        recent_losses = [pos.loss_percentage for pos in sorted_positions[-3:]]  # 3 positions ล่าสุด
        earlier_losses = [pos.loss_percentage for pos in sorted_positions[:-3]]
        
        if not earlier_losses:
            return "INSUFFICIENT_DATA"
        
        recent_avg = statistics.mean(recent_losses)
        earlier_avg = statistics.mean(earlier_losses)
        
        if recent_avg > earlier_avg * 1.2:
            return "WORSENING"
        elif recent_avg < earlier_avg * 0.8:
            return "IMPROVING"
        else:
            return "STABLE"
    
    def _calculate_urgency_level(self, loss_analysis: Dict) -> RecoveryUrgency:
        """คำนวณระดับความเร่งด่วน"""
        
        urgency_score = 0
        
        # ขาดทุนรวม
        if abs(loss_analysis["total_loss"]) > 1000:
            urgency_score += 3
        elif abs(loss_analysis["total_loss"]) > 500:
            urgency_score += 2
        elif abs(loss_analysis["total_loss"]) > 100:
            urgency_score += 1
        
        # เปอร์เซ็นต์การขาดทุนสูงสุด
        if loss_analysis["max_loss_percentage"] > 50:
            urgency_score += 3
        elif loss_analysis["max_loss_percentage"] > 30:
            urgency_score += 2
        elif loss_analysis["max_loss_percentage"] > 15:
            urgency_score += 1
        
        # แนวโน้มการขาดทุน
        if loss_analysis["loss_trend"] == "WORSENING":
            urgency_score += 2
        elif loss_analysis["loss_trend"] == "IMPROVING":
            urgency_score -= 1
        
        # เวลาถือ position
        if loss_analysis["max_holding_time"] > 1440:  # > 1 วัน
            urgency_score += 1
        
        # จำนวน positions
        if loss_analysis["position_count"] > 10:
            urgency_score += 2
        elif loss_analysis["position_count"] > 5:
            urgency_score += 1
        
        # กำหนดระดับความเร่งด่วน
        if urgency_score >= 8:
            return RecoveryUrgency.CRITICAL
        elif urgency_score >= 5:
            return RecoveryUrgency.HIGH
        elif urgency_score >= 2:
            return RecoveryUrgency.MEDIUM
        else:
            return RecoveryUrgency.LOW
    
    def _calculate_recovery_scores(self, loss_analysis: Dict, 
                                 market_analysis: MarketAnalysis,
                                 urgency_level: RecoveryUrgency) -> Dict[RecoveryMethod, float]:
        """คำนวณคะแนนสำหรับแต่ละวิธี Recovery"""
        
        scores = {}
        
        for method in RecoveryMethod:
            score = 0.0
            
            # คะแนนพื้นฐานตามประเภทของการขาดทุน (30%)
            base_score = self._get_base_recovery_score(method, loss_analysis)
            
            # คะแนนจากประสิทธิภาพในอดีต (25%)
            performance_score = self._get_recovery_performance_score(method, market_analysis, urgency_level)
            
            # คะแนนจากความเหมาะสมกับสภาพตลาด (25%)
            market_compatibility_score = self._get_market_compatibility_score(method, market_analysis)
            
            # คะแนนจากความเร่งด่วน (20%)
            urgency_compatibility_score = self._get_urgency_compatibility_score(method, urgency_level)
            
            # รวมคะแนน
            total_score = (base_score * 0.3 + 
                          performance_score * 0.25 + 
                          market_compatibility_score * 0.25 + 
                          urgency_compatibility_score * 0.2)
            
            scores[method] = min(max(total_score, 0.0), 1.0)
        
        return scores
    
    def _get_base_recovery_score(self, method: RecoveryMethod, loss_analysis: Dict) -> float:
        """คะแนนพื้นฐานตามลักษณะการขาดทุน"""
        
        # Martingale Smart - เหมาะกับการขาดทุนน้อย positions น้อย
        if method == RecoveryMethod.MARTINGALE_SMART:
            if (loss_analysis["position_count"] <= 3 and 
                loss_analysis["max_loss_percentage"] <= 20):
                return 0.9
            elif loss_analysis["position_count"] <= 5:
                return 0.7
            else:
                return 0.3
        
        # Grid Intelligent - เหมาะกับการขาดทุนปานกลาง
        elif method == RecoveryMethod.GRID_INTELLIGENT:
            if (loss_analysis["position_count"] <= 8 and 
                10 <= loss_analysis["max_loss_percentage"] <= 40):
                return 0.9
            elif loss_analysis["position_count"] <= 12:
                return 0.7
            else:
                return 0.4
        
        # Hedging Advanced - เหมาะกับการขาดทุนมาก ต้องการ Recovery เร็ว
        elif method == RecoveryMethod.HEDGING_ADVANCED:
            if (loss_analysis["max_loss_percentage"] > 30 or 
                abs(loss_analysis["total_loss"]) > 500):
                return 0.9
            elif loss_analysis["max_loss_percentage"] > 15:
                return 0.7
            else:
                return 0.4
        
        # Averaging Intelligent - เหมาะกับ positions หลายตัว
        elif method == RecoveryMethod.AVERAGING_INTELLIGENT:
            if (loss_analysis["position_count"] >= 5 and 
                loss_analysis["loss_concentration"] > 0.5):  # กระจาย
                return 0.8
            elif loss_analysis["position_count"] >= 3:
                return 0.6
            else:
                return 0.3
        
        # Correlation Recovery - เหมาะกับ positions หลาย symbol
        elif method == RecoveryMethod.CORRELATION_RECOVERY:
            if len(loss_analysis["symbols"]) > 1:
                return 0.8
            else:
                return 0.2
        
        return 0.5
    
    def _get_recovery_performance_score(self, method: RecoveryMethod, 
                                      market_analysis: MarketAnalysis,
                                      urgency_level: RecoveryUrgency) -> float:
        """คะแนนจากประสิทธิภาพในอดีต"""
        
        stats = self.recovery_stats.get(method)
        if not stats or stats.total_attempts < self.min_attempts_for_stats:
            return 0.5  # คะแนนกลางถ้าไม่มีข้อมูลเพียงพอ
        
        # คะแนนพื้นฐานจาก success rate
        base_performance = stats.success_rate / 100
        
        # ปรับตามสภาพตลาด
        condition_key = market_analysis.primary_condition.value
        condition_performance = stats.condition_success_rates.get(condition_key, stats.success_rate) / 100
        
        # ปรับตามความเร่งด่วน
        urgency_key = urgency_level.value
        urgency_performance = stats.urgency_success_rates.get(urgency_key, stats.success_rate) / 100
        
        # รวมคะแนน
        performance_score = (base_performance * 0.4 + 
                           condition_performance * 0.3 + 
                           urgency_performance * 0.3)
        
        return performance_score
    
    def _get_market_compatibility_score(self, method: RecoveryMethod, 
                                      market_analysis: MarketAnalysis) -> float:
        """คะแนนความเหมาะสมกับสภาพตลาด"""
        
        # Matrix ความเหมาะสมระหว่างวิธี Recovery และสภาพตลาด
        compatibility_matrix = {
            RecoveryMethod.MARTINGALE_SMART: {
                MarketCondition.RANGING_TIGHT: 0.9,
                MarketCondition.RANGING_WIDE: 0.7,
                MarketCondition.TRENDING_WEAK: 0.6,
                MarketCondition.TRENDING_STRONG: 0.3,
                MarketCondition.VOLATILE_HIGH: 0.2,
                MarketCondition.NEWS_IMPACT: 0.1
            },
            RecoveryMethod.GRID_INTELLIGENT: {
                MarketCondition.TRENDING_STRONG: 0.9,
                MarketCondition.TRENDING_WEAK: 0.8,
                MarketCondition.RANGING_WIDE: 0.6,
                MarketCondition.RANGING_TIGHT: 0.5,
                MarketCondition.VOLATILE_HIGH: 0.4,
                MarketCondition.NEWS_IMPACT: 0.3
            },
            RecoveryMethod.HEDGING_ADVANCED: {
                MarketCondition.VOLATILE_HIGH: 1.0,
                MarketCondition.NEWS_IMPACT: 0.9,
                MarketCondition.TRENDING_STRONG: 0.7,
                MarketCondition.TRENDING_WEAK: 0.6,
                MarketCondition.RANGING_WIDE: 0.4,
                MarketCondition.RANGING_TIGHT: 0.3
            },
            RecoveryMethod.AVERAGING_INTELLIGENT: {
                MarketCondition.RANGING_TIGHT: 0.8,
                MarketCondition.RANGING_WIDE: 0.9,
                MarketCondition.TRENDING_WEAK: 0.7,
                MarketCondition.TRENDING_STRONG: 0.5,
                MarketCondition.VOLATILE_HIGH: 0.4,
                MarketCondition.NEWS_IMPACT: 0.3
            },
            RecoveryMethod.CORRELATION_RECOVERY: {
                MarketCondition.VOLATILE_HIGH: 0.8,
                MarketCondition.NEWS_IMPACT: 0.7,
                MarketCondition.TRENDING_STRONG: 0.6,
                MarketCondition.TRENDING_WEAK: 0.5,
                MarketCondition.RANGING_WIDE: 0.4,
                MarketCondition.RANGING_TIGHT: 0.3
            }
        }
        
        method_compatibility = compatibility_matrix.get(method, {})
        return method_compatibility.get(market_analysis.primary_condition, 0.5)
    
    def _get_urgency_compatibility_score(self, method: RecoveryMethod, 
                                       urgency_level: RecoveryUrgency) -> float:
        """คะแนนความเหมาะสมกับระดับความเร่งด่วน"""
        
        # วิธี Recovery แต่ละแบบมีความเหมาะสมกับความเร่งด่วนต่างกัน
        urgency_compatibility = {
            RecoveryMethod.MARTINGALE_SMART: {
                RecoveryUrgency.LOW: 0.9,
                RecoveryUrgency.MEDIUM: 0.7,
                RecoveryUrgency.HIGH: 0.4,
                RecoveryUrgency.CRITICAL: 0.2
            },
            RecoveryMethod.GRID_INTELLIGENT: {
                RecoveryUrgency.LOW: 0.8,
                RecoveryUrgency.MEDIUM: 0.9,
                RecoveryUrgency.HIGH: 0.7,
                RecoveryUrgency.CRITICAL: 0.5
            },
            RecoveryMethod.HEDGING_ADVANCED: {
                RecoveryUrgency.LOW: 0.5,
                RecoveryUrgency.MEDIUM: 0.7,
                RecoveryUrgency.HIGH: 0.9,
                RecoveryUrgency.CRITICAL: 1.0
            },
            RecoveryMethod.AVERAGING_INTELLIGENT: {
                RecoveryUrgency.LOW: 0.8,
                RecoveryUrgency.MEDIUM: 0.8,
                RecoveryUrgency.HIGH: 0.6,
                RecoveryUrgency.CRITICAL: 0.4
            },
            RecoveryMethod.CORRELATION_RECOVERY: {
                RecoveryUrgency.LOW: 0.6,
                RecoveryUrgency.MEDIUM: 0.7,
                RecoveryUrgency.HIGH: 0.8,
                RecoveryUrgency.CRITICAL: 0.7
            }
        }
        
        method_urgency = urgency_compatibility.get(method, {})
        return method_urgency.get(urgency_level, 0.5)
    
    def _create_recovery_recommendation(self, primary_method: RecoveryMethod,
                                      alternative_methods: List[RecoveryMethod],
                                      confidence_score: float,
                                      loss_analysis: Dict,
                                      market_analysis: MarketAnalysis,
                                      urgency_level: RecoveryUrgency) -> RecoveryRecommendation:
        """สร้างคำแนะนำ Recovery"""
        
        # สร้างเหตุผล
        reasoning = []
        reasoning.append(f"การขาดทุนรวม: {loss_analysis['total_loss']:.2f}")
        reasoning.append(f"จำนวน Positions: {loss_analysis['position_count']}")
        reasoning.append(f"การขาดทุนสูงสุด: {loss_analysis['max_loss_percentage']:.1f}%")
        reasoning.append(f"สภาพตลาด: {market_analysis.primary_condition.value}")
        reasoning.append(f"ระดับความเร่งด่วน: {urgency_level.value}")
        
        # ประมาณเวลา Recovery
        estimated_time = self._estimate_recovery_time(primary_method, loss_analysis, urgency_level)
        
        # ประมาณความเสี่ยงเพิ่มเติม
        additional_risk = self._estimate_additional_risk(primary_method, loss_analysis)
        
        # ความน่าจะเป็นที่จะสำเร็จ
        success_probability = self._estimate_success_probability(primary_method, loss_analysis, market_analysis)
        
        # พารามิเตอร์ที่แนะนำ
        recommended_params = self._get_recommended_parameters(primary_method, loss_analysis, market_analysis)
        
        return RecoveryRecommendation(
            primary_method=primary_method,
            alternative_methods=alternative_methods,
            confidence_score=confidence_score,
            urgency_level=urgency_level,
            estimated_recovery_time_minutes=estimated_time,
            estimated_additional_risk=additional_risk,
            recommended_parameters=recommended_params,
            reasoning=reasoning,
            success_probability=success_probability
        )
    
    def _estimate_recovery_time(self, method: RecoveryMethod, 
                              loss_analysis: Dict, urgency_level: RecoveryUrgency) -> float:
        """ประมาณเวลาที่ต้องใช้ในการ Recovery"""
        
        # เวลาพื้นฐานตามวิธี
        base_times = {
            RecoveryMethod.MARTINGALE_SMART: 60,      # 1 ชั่วโมง
            RecoveryMethod.GRID_INTELLIGENT: 240,     # 4 ชั่วโมง
            RecoveryMethod.HEDGING_ADVANCED: 30,      # 30 นาที
            RecoveryMethod.AVERAGING_INTELLIGENT: 180, # 3 ชั่วโมง
            RecoveryMethod.CORRELATION_RECOVERY: 120   # 2 ชั่วโมง
        }
        
        base_time = base_times.get(method, 120)
        
        # ปรับตามขนาดการขาดทุน
        loss_multiplier = 1.0 + (abs(loss_analysis["total_loss"]) / 1000)
        
        # ปรับตามจำนวน positions
        position_multiplier = 1.0 + (loss_analysis["position_count"] / 10)
        
        # ปรับตามความเร่งด่วน (เร่งด่วนมาก = เวลาน้อยลง แต่เสี่ยงมากขึ้น)
        urgency_multipliers = {
            RecoveryUrgency.LOW: 1.5,
            RecoveryUrgency.MEDIUM: 1.0,
            RecoveryUrgency.HIGH: 0.7,
            RecoveryUrgency.CRITICAL: 0.5
        }
        urgency_multiplier = urgency_multipliers.get(urgency_level, 1.0)
        
        estimated_time = base_time * loss_multiplier * position_multiplier * urgency_multiplier
        
        return max(15, min(estimated_time, 1440))  # จำกัดระหว่าง 15 นาที - 1 วัน
    
    def _estimate_additional_risk(self, method: RecoveryMethod, loss_analysis: Dict) -> float:
        """ประมาณความเสี่ยงเพิ่มเติมในการ Recovery"""
        
        # ความเสี่ยงพื้นฐานตามวิธี (% ของการขาดทุนปัจจุบัน)
        base_risks = {
            RecoveryMethod.MARTINGALE_SMART: 0.5,      # 50% ของการขาดทุนปัจจุบัน
            RecoveryMethod.GRID_INTELLIGENT: 0.3,      # 30%
            RecoveryMethod.HEDGING_ADVANCED: 0.2,      # 20%
            RecoveryMethod.AVERAGING_INTELLIGENT: 0.4, # 40%
            RecoveryMethod.CORRELATION_RECOVERY: 0.6   # 60%
        }
        
        base_risk = base_risks.get(method, 0.4)
        current_loss = abs(loss_analysis["total_loss"])
        
        # ปรับตามขนาดการขาดทุน (ขาดทุนมาก = เสี่ยงมากขึ้น)
        if current_loss > 1000:
            risk_multiplier = 1.5
        elif current_loss > 500:
            risk_multiplier = 1.2  
        else:
            risk_multiplier = 1.0
        
        # ปรับตามจำนวน positions
        if loss_analysis["position_count"] > 10:
            position_risk_multiplier = 1.3
        elif loss_analysis["position_count"] > 5:
            position_risk_multiplier = 1.1
        else:
            position_risk_multiplier = 1.0
        
        additional_risk = current_loss * base_risk * risk_multiplier * position_risk_multiplier
        
        return additional_risk
    
    def _estimate_success_probability(self, method: RecoveryMethod, 
                                    loss_analysis: Dict, 
                                    market_analysis: MarketAnalysis) -> float:
        """ประมาณความน่าจะเป็นที่จะ Recovery สำเร็จ"""
        
        # ความน่าจะเป็นพื้นฐานจากสถิติ
        stats = self.recovery_stats.get(method)
        if stats and stats.total_attempts >= self.min_attempts_for_stats:
            base_probability = stats.success_rate / 100
        else:
            # ค่าเริ่มต้นตามลักษณะของวิธี
            default_probabilities = {
                RecoveryMethod.MARTINGALE_SMART: 0.75,
                RecoveryMethod.GRID_INTELLIGENT: 0.80,
                RecoveryMethod.HEDGING_ADVANCED: 0.70,
                RecoveryMethod.AVERAGING_INTELLIGENT: 0.78,
                RecoveryMethod.CORRELATION_RECOVERY: 0.65
            }
            base_probability = default_probabilities.get(method, 0.70)
        
        # ปรับตามสภาพตลาด
        market_adjustment = self._get_market_compatibility_score(method, market_analysis)
        
        # ปรับตามขนาดการขาดทุน (ขาดทุนมาก = โอกาสสำเร็จน้อยลง)
        if loss_analysis["max_loss_percentage"] > 50:
            loss_adjustment = 0.7
        elif loss_analysis["max_loss_percentage"] > 30:
            loss_adjustment = 0.8
        elif loss_analysis["max_loss_percentage"] > 15:
            loss_adjustment = 0.9
        else:
            loss_adjustment = 1.0
        
        # ปรับตามแนวโน้มการขาดทุน
        if loss_analysis["loss_trend"] == "WORSENING":
            trend_adjustment = 0.8
        elif loss_analysis["loss_trend"] == "IMPROVING":
            trend_adjustment = 1.1
        else:
            trend_adjustment = 1.0
        
        # คำนวณความน่าจะเป็นสุดท้าย
        final_probability = (base_probability * 0.4 + 
                            market_adjustment * 0.3 + 
                            base_probability * loss_adjustment * 0.2 + 
                            base_probability * trend_adjustment * 0.1)
        
        return min(max(final_probability, 0.1), 0.95)  # จำกัดระหว่าง 10%-95%
    
    def _get_recommended_parameters(self, method: RecoveryMethod,
                                    loss_analysis: Dict,
                                    market_analysis: MarketAnalysis) -> Dict[str, Any]:
        """ดึงพารามิเตอร์ที่แนะนำสำหรับวิธี Recovery"""
        
        # ดึงพารามิเตอร์พื้นฐานจาก trading_params
        base_params = self.trading_params.get_recovery_params(method)
        
        # ปรับพารามิเตอร์ตามสถานการณ์
        recommended_params = base_params.copy()
        
        # ปรับตามขนาดการขาดทุน
        loss_severity = loss_analysis["max_loss_percentage"]
        
        if method == RecoveryMethod.MARTINGALE_SMART:
            # ปรับ multiplier ตามการขาดทุน
            if loss_severity > 30:
                recommended_params["initial_multiplier"] = min(
                    recommended_params.get("initial_multiplier", 2.0) * 0.8, 
                    recommended_params.get("max_multiplier", 8.0)
                )
            
        elif method == RecoveryMethod.GRID_INTELLIGENT:
            # ปรับระยะห่าง grid ตาม volatility
            if market_analysis.volatility_level == "HIGH":
                recommended_params["grid_spacing_pips"] = int(
                    recommended_params.get("grid_spacing_pips", 30) * 1.5
                )
            elif market_analysis.volatility_level == "LOW":
                recommended_params["grid_spacing_pips"] = int(
                    recommended_params.get("grid_spacing_pips", 30) * 0.7
                )
        
        elif method == RecoveryMethod.HEDGING_ADVANCED:
            # ปรับ hedge ratio ตามความเร่งด่วน
            if loss_severity > 40:
                recommended_params["hedge_ratio"] = min(
                    recommended_params.get("hedge_ratio", 1.0) * 1.2, 2.0
                )
        
        return recommended_params
    
    def start_recovery(self, recovery_id: str, method: RecoveryMethod,
                        loss_positions: List[LossPosition],
                        parameters: Dict[str, Any]) -> bool:
        """เริ่มต้นการ Recovery"""
        
        if len(self.active_recoveries) >= self.max_concurrent_recoveries:
            self.logger.warning("⚠️ เกินจำนวน Recovery พร้อมกันสูงสุด")
            return False
        
        recovery_info = {
            "recovery_id": recovery_id,
            "method": method,
            "start_time": datetime.now(),
            "loss_positions": loss_positions,
            "parameters": parameters,
            "status": RecoverySuccess.PENDING,
            "initial_loss": sum(pos.loss_amount for pos in loss_positions),
            "current_loss": sum(pos.loss_amount for pos in loss_positions),
            "recovery_cost": 0.0
        }
        
        self.active_recoveries[recovery_id] = recovery_info
        
        self.logger.info(
            f"🔄 เริ่ม Recovery: {recovery_id} Method: {method.value} "
            f"Positions: {len(loss_positions)} Loss: {recovery_info['initial_loss']:.2f}"
        )
        
        return True
    
    def update_recovery_progress(self, recovery_id: str, 
                                current_loss: float, additional_cost: float = 0.0):
        """อัพเดทความคืบหน้าการ Recovery"""
        
        if recovery_id not in self.active_recoveries:
            return
        
        recovery_info = self.active_recoveries[recovery_id]
        recovery_info["current_loss"] = current_loss
        recovery_info["recovery_cost"] += additional_cost
        
        # ตรวจสอบสถานะ
        initial_loss = abs(recovery_info["initial_loss"])
        current_loss_abs = abs(current_loss)
        
        if current_loss_abs <= initial_loss * 0.05:  # Recovery 95%+
            recovery_info["status"] = RecoverySuccess.SUCCESS
        elif current_loss_abs <= initial_loss * 0.5:  # Recovery 50%+
            recovery_info["status"] = RecoverySuccess.PARTIAL_SUCCESS
    
    def complete_recovery(self, recovery_id: str, final_result: RecoverySuccess,
                            market_condition: MarketCondition):
        """จบการ Recovery และบันทึกผล"""
        
        if recovery_id not in self.active_recoveries:
            return
        
        recovery_info = self.active_recoveries[recovery_id]
        method = recovery_info["method"]
        
        # คำนวณเวลาที่ใช้
        recovery_time = (datetime.now() - recovery_info["start_time"]).total_seconds() / 60
        
        # อัพเดทสถิติ
        stats = self.recovery_stats[method]
        stats.total_attempts += 1
        stats.total_recovery_time_minutes += recovery_time
        stats.total_recovery_cost += recovery_info["recovery_cost"]
        
        if final_result == RecoverySuccess.SUCCESS:
            stats.successful_recoveries += 1
        elif final_result == RecoverySuccess.PARTIAL_SUCCESS:
            stats.partial_recoveries += 1
        else:
            stats.failed_recoveries += 1
        
        # อัพเดทประสิทธิภาพตามสภาพตลาด
        condition_key = market_condition.value
        if condition_key not in stats.condition_success_rates:
            stats.condition_success_rates[condition_key] = 0.0
        
        if final_result == RecoverySuccess.SUCCESS:
            stats.condition_success_rates[condition_key] = min(
                stats.condition_success_rates[condition_key] + 10, 100
            )
        else:
            stats.condition_success_rates[condition_key] = max(
                stats.condition_success_rates[condition_key] - 5, 0
            )
        
        # อัพเดทสถิติที่คำนวณได้
        stats.update_stats()
        
        # บันทึกประวัติ
        recovery_record = {
            "recovery_id": recovery_id,
            "method": method.value,
            "start_time": recovery_info["start_time"].isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_minutes": recovery_time,
            "initial_loss": recovery_info["initial_loss"],
            "final_loss": recovery_info["current_loss"],
            "recovery_cost": recovery_info["recovery_cost"],
            "result": final_result.value,
            "market_condition": market_condition.value,
            "position_count": len(recovery_info["loss_positions"])
        }
        
        self.recovery_history.append(recovery_record)
        
        # จำกัดประวัติ
        if len(self.recovery_history) > 500:
            self.recovery_history = self.recovery_history[-500:]
        
        # ลบจาก active recoveries
        del self.active_recoveries[recovery_id]
        
        self.logger.info(
            f"✅ จบ Recovery: {recovery_id} Result: {final_result.value} "
            f"Time: {recovery_time:.1f}min Recovery: {((abs(recovery_info['initial_loss']) - abs(recovery_info['current_loss'])) / abs(recovery_info['initial_loss']) * 100):.1f}%"
        )
    
    def get_recovery_statistics(self) -> Dict[str, Dict]:
        """ดึงสถิติ Recovery ทั้งหมด"""
        
        stats_summary = {}
        
        for method, stats in self.recovery_stats.items():
            stats_summary[method.value] = {
                "total_attempts": stats.total_attempts,
                "success_rate": round(stats.success_rate, 2),
                "efficiency_score": round(stats.efficiency_score, 3),
                "avg_recovery_time_minutes": round(stats.avg_recovery_time, 1),
                "condition_success_rates": stats.condition_success_rates,
                "urgency_success_rates": stats.urgency_success_rates
            }
        
        return stats_summary
    
    def get_active_recoveries(self) -> List[Dict]:
        """ดึงข้อมูล Recovery ที่กำลังดำเนินการ"""
        
        active_list = []
        
        for recovery_id, info in self.active_recoveries.items():
            active_list.append({
                "recovery_id": recovery_id,
                "method": info["method"].value,
                "start_time": info["start_time"].isoformat(),
                "duration_minutes": (datetime.now() - info["start_time"]).total_seconds() / 60,
                "initial_loss": info["initial_loss"],
                "current_loss": info["current_loss"],
                "recovery_progress": ((abs(info["initial_loss"]) - abs(info["current_loss"])) / abs(info["initial_loss"]) * 100) if info["initial_loss"] != 0 else 0,
                "status": info["status"].value,
                "position_count": len(info["loss_positions"])
            })
        
        return active_list

# === HELPER FUNCTIONS ===

def get_recovery_recommendation_for_losses(loss_positions: List[LossPosition]) -> Optional[RecoveryRecommendation]:
   """ดึงคำแนะนำ Recovery สำหรับ positions ที่ขาดทุน"""
   selector = get_recovery_selector()
   return selector.select_recovery_method(loss_positions)

def start_automated_recovery(recovery_id: str, loss_positions: List[LossPosition]) -> bool:
   """เริ่ม Recovery อัตโนมัติ"""
   selector = get_recovery_selector()
   
   # ขอคำแนะนำ
   recommendation = selector.select_recovery_method(loss_positions)
   if not recommendation:
       return False
   
   # เริ่ม Recovery
   return selector.start_recovery(
       recovery_id,
       recommendation.primary_method,
       loss_positions,
       recommendation.recommended_parameters
   )

def get_recovery_status_summary() -> Dict:
   """ดึงสรุปสถานะ Recovery"""
   selector = get_recovery_selector()
   
   active_recoveries = selector.get_active_recoveries()
   stats = selector.get_recovery_statistics()
   
   return {
       "active_count": len(active_recoveries),
       "total_initial_loss": sum(r["initial_loss"] for r in active_recoveries),
       "total_current_loss": sum(r["current_loss"] for r in active_recoveries),
       "average_progress": statistics.mean([r["recovery_progress"] for r in active_recoveries]) if active_recoveries else 0,
       "methods_performance": stats
   }

# === GLOBAL INSTANCE ===
_global_recovery_selector: Optional[RecoverySelector] = None

def get_recovery_selector() -> RecoverySelector:
   """ดึง Recovery Selector แบบ Singleton"""
   global _global_recovery_selector
   if _global_recovery_selector is None:
       _global_recovery_selector = RecoverySelector()
   return _global_recovery_selector