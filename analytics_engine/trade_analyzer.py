#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRADE ANALYZER - Individual Trade Analysis System
===============================================
ระบบวิเคราะห์การเทรดรายตัวแบบละเอียดและครอบคลุม
รองรับการวิเคราะห์ประสิทธิภาพของแต่ละเทรดและการจัดกลุ่มเทรด

Key Features:
- Detailed trade performance breakdown
- Entry/exit timing analysis
- Strategy effectiveness evaluation
- Market condition correlation analysis
- Trade pattern recognition
- Recovery trade analysis
- High-frequency trade processing (50-100 lots/day)

เชื่อมต่อไปยัง:
- analytics_engine/performance_tracker.py (บันทึกผลการวิเคราะห์)
- position_management/position_tracker.py (ข้อมูล positions)
- intelligent_recovery/recovery_engine.py (ข้อมูล recovery trades)
- adaptive_entries/signal_generator.py (ข้อมูล entry signals)
- market_intelligence/market_analyzer.py (ข้อมูล market conditions)
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
import sqlite3
from collections import defaultdict, deque

# เชื่อมต่อ internal modules
from config.settings import get_system_settings, MarketSession
from config.trading_params import get_trading_parameters, EntryStrategy, RecoveryMethod
from utilities.professional_logger import setup_trading_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class TradeType(Enum):
    """ประเภทของเทรด"""
    REGULAR = "regular"                 # เทรดปกติ
    RECOVERY = "recovery"               # เทรด Recovery
    SCALPING = "scalping"              # เทรด Scalping
    SWING = "swing"                    # เทรด Swing
    NEWS = "news"                      # เทรดตามข่าว
    HEDGE = "hedge"                    # เทรด Hedge

class TradeStatus(Enum):
    """สถานะของเทรด"""
    OPEN = "open"                      # เปิดอยู่
    CLOSED_PROFIT = "closed_profit"    # ปิดกำไร
    CLOSED_LOSS = "closed_loss"        # ปิดขาดทุน
    RECOVERED = "recovered"            # ถูก Recover แล้ว
    PENDING_RECOVERY = "pending_recovery"  # รอ Recovery
    CANCELLED = "cancelled"            # ยกเลิก

class TradeQuality(Enum):
    """คุณภาพของเทรด"""
    EXCELLENT = "excellent"            # ดีเลิศ (>200 pips กำไร)
    GOOD = "good"                     # ดี (50-200 pips กำไร)
    AVERAGE = "average"               # ปานกลาง (0-50 pips กำไร)
    POOR = "poor"                     # แย่ (-50-0 pips)
    TERRIBLE = "terrible"             # แย่มาก (<-50 pips)

class ExitReason(Enum):
    """เหตุผลการปิดเทรด"""
    TAKE_PROFIT = "take_profit"        # ถึง Take Profit
    STOP_LOSS = "stop_loss"           # ถึง Stop Loss (ไม่ควรมีในระบบนี้)
    MANUAL_CLOSE = "manual_close"     # ปิดด้วยตนเอง
    RECOVERY_CLOSE = "recovery_close" # ปิดเพื่อ Recovery
    TIME_EXIT = "time_exit"           # ปิดตามเวลา
    MARKET_CLOSE = "market_close"     # ปิดตามตลาด
    SYSTEM_EXIT = "system_exit"       # ปิดโดยระบบ

@dataclass
class TradeMetrics:
    """เมตริกส์การวิเคราะห์เทรด"""
    # Basic Metrics
    gross_pnl: float = 0.0             # P&L รวม
    net_pnl: float = 0.0               # P&L สุทธิ (หัก spread/commission)
    pips_gained: float = 0.0            # จำนวน pips ที่ได้/เสีย
    
    # Risk Metrics
    risk_reward_ratio: float = 0.0      # อัตราส่วน Risk:Reward
    max_adverse_excursion: float = 0.0  # MAE
    max_favorable_excursion: float = 0.0 # MFE
    
    # Timing Metrics
    hold_time_minutes: float = 0.0      # เวลาถือ (นาที)
    entry_delay_seconds: float = 0.0    # ความล่าช้าในการเข้า
    exit_efficiency: float = 100.0      # ประสิทธิภาพการออก (%)
    
    # Quality Metrics
    trade_quality: TradeQuality = TradeQuality.AVERAGE
    entry_precision: float = 0.0        # ความแม่นยำการเข้า (%)
    exit_timing: float = 0.0            # จังหวะการออก (%)
    
    # Market Metrics
    market_impact: float = 0.0          # ผลกระทบต่อตลาด
    slippage_cost: float = 0.0          # ต้นทุน Slippage
    opportunity_cost: float = 0.0       # ต้นทุนโอกาส

@dataclass
class TradeContext:
    """บริบทของเทรด"""
    # Market Context
    market_session: MarketSession = MarketSession.ASIAN
    market_state: str = "UNKNOWN"       # TRENDING, RANGING, VOLATILE
    volatility_level: float = 1.0       # ระดับความผันผวน
    
    # Technical Context
    trend_direction: str = "NEUTRAL"    # BULLISH, BEARISH, NEUTRAL
    support_resistance_nearby: bool = False
    key_level_distance: float = 0.0    # ระยะห่างจาก Key Level (pips)
    
    # News Context
    news_impact_level: str = "NONE"     # HIGH, MEDIUM, LOW, NONE
    economic_events: List[str] = field(default_factory=list)
    
    # System Context
    concurrent_trades: int = 0          # จำนวนเทรดพร้อมกัน
    system_load: float = 0.0           # โหลดของระบบ (%)
    recovery_active: bool = False       # มี Recovery ทำงานหรือไม่

@dataclass
class TradeRecord:
    """บันทึกการเทรดรายตัว"""
    # Basic Information
    trade_id: str
    position_id: str
    symbol: str = "XAUUSD"
    
    # Trade Details
    trade_type: TradeType = TradeType.REGULAR
    entry_strategy: EntryStrategy = EntryStrategy.TREND_FOLLOWING
    direction: str = "BUY"              # BUY หรือ SELL
    volume: float = 0.01                # ขนาด position (lots)
    
    # Price Information
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    current_price: float = 0.0
    
    # Timing Information
    open_time: datetime = field(default_factory=datetime.now)
    close_time: Optional[datetime] = None
    signal_time: Optional[datetime] = None
    
    # Status
    status: TradeStatus = TradeStatus.OPEN
    exit_reason: Optional[ExitReason] = None
    
    # Context & Metrics
    trade_context: TradeContext = field(default_factory=TradeContext)
    trade_metrics: TradeMetrics = field(default_factory=TradeMetrics)
    
    # Recovery Information
    is_recovery_trade: bool = False
    original_trade_id: Optional[str] = None
    recovery_method: Optional[RecoveryMethod] = None
    recovery_attempt: int = 0
    
    # Additional Data
    entry_confidence: float = 0.0       # ความมั่นใจของสัญญาณ
    signal_quality: float = 0.0         # คุณภาพสัญญาণ
    notes: str = ""                     # หมายเหตุเพิ่มเติม
    
    # System Generated
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class TradeAnalysisResult:
    """ผลการวิเคราะห์เทรด"""
    trade_id: str
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    
    # Performance Scores
    overall_performance_score: float = 0.0    # 0-100
    entry_score: float = 0.0                  # คะแนนการเข้า
    exit_score: float = 0.0                   # คะแนนการออก
    timing_score: float = 0.0                 # คะแนนจังหวะเวลา
    risk_management_score: float = 0.0        # คะแนนบริหารความเสี่ยง
    
    # Detailed Analysis
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    
    # Comparative Analysis
    strategy_rank: int = 0                    # อันดับในกลุ่ม Strategy
    session_rank: int = 0                     # อันดับในกลุ่ม Session
    percentile_performance: float = 0.0       # เปอร์เซ็นไทล์ประสิทธิภาพ
    
    # Pattern Recognition
    identified_patterns: List[str] = field(default_factory=list)
    pattern_confidence: float = 0.0           # ความมั่นใจในการจดจำ Pattern
    
    # Recommendations
    strategy_adjustments: List[str] = field(default_factory=list)
    optimal_entry_suggestions: List[str] = field(default_factory=list)
    risk_optimization: List[str] = field(default_factory=list)

class TradeMetricsCalculator:
    """
    คำนวณเมตริกส์ต่างๆ สำหรับการเทรด
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Constants for XAUUSD
        self.pip_value = 0.01               # 1 pip = $0.01 per 0.01 lot
        self.pip_size = 0.1                 # 1 pip = 0.1 points for Gold
        self.spread_typical = 2.0           # Typical spread in pips
        self.commission_per_lot = 0.0       # Commission per lot
    
    def calculate_trade_metrics(self, trade: TradeRecord, 
                              price_history: List[Dict[str, Any]] = None) -> TradeMetrics:
        """
        คำนวณเมตริกส์ทั้งหมดสำหรับเทรด
        
        Args:
            trade: ข้อมูลเทรด
            price_history: ประวัติราคาของเทรด
            
        Returns:
            TradeMetrics: เมตริกส์ที่คำนวณแล้ว
        """
        try:
            metrics = TradeMetrics()
            
            # คำนวณ Basic Metrics
            metrics.gross_pnl = self._calculate_gross_pnl(trade)
            metrics.net_pnl = self._calculate_net_pnl(trade, metrics.gross_pnl)
            metrics.pips_gained = self._calculate_pips_gained(trade)
            
            # คำนวณ Risk Metrics
            if price_history:
                metrics.max_adverse_excursion = self._calculate_mae(trade, price_history)
                metrics.max_favorable_excursion = self._calculate_mfe(trade, price_history)
            
            metrics.risk_reward_ratio = self._calculate_risk_reward_ratio(trade, metrics)
            
            # คำนวณ Timing Metrics
            metrics.hold_time_minutes = self._calculate_hold_time(trade)
            metrics.entry_delay_seconds = self._calculate_entry_delay(trade)
            metrics.exit_efficiency = self._calculate_exit_efficiency(trade, metrics)
            
            # คำนวณ Quality Metrics
            metrics.trade_quality = self._determine_trade_quality(metrics.pips_gained)
            metrics.entry_precision = self._calculate_entry_precision(trade, metrics)
            metrics.exit_timing = self._calculate_exit_timing(trade, metrics)
            
            # คำนวณ Market Impact
            metrics.market_impact = self._calculate_market_impact(trade)
            metrics.slippage_cost = self._calculate_slippage_cost(trade)
            metrics.opportunity_cost = self._calculate_opportunity_cost(trade, metrics)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Trade Metrics: {e}")
            return TradeMetrics()
    
    def _calculate_gross_pnl(self, trade: TradeRecord) -> float:
        """คำนวณ Gross P&L"""
        if trade.status == TradeStatus.OPEN:
            exit_price = trade.current_price
        elif trade.exit_price is not None:
            exit_price = trade.exit_price
        else:
            return 0.0
        
        # คำนวณ P&L
        if trade.direction == "BUY":
            price_diff = exit_price - trade.entry_price
        else:  # SELL
            price_diff = trade.entry_price - exit_price
        
        # แปลงเป็นเงิน (สำหรับ XAUUSD)
        pnl = price_diff * trade.volume * 100  # $1 per pip per 0.01 lot
        
        return pnl
    
    def _calculate_net_pnl(self, trade: TradeRecord, gross_pnl: float) -> float:
        """คำนวณ Net P&L (หักค่าใช้จ่าย)"""
        # คำนวณ Spread Cost
        spread_cost = self.spread_typical * trade.volume * self.pip_value * 100
        
        # คำนวณ Commission
        commission_cost = self.commission_per_lot * trade.volume
        
        # Net P&L
        net_pnl = gross_pnl - spread_cost - commission_cost
        
        return net_pnl
    
    def _calculate_pips_gained(self, trade: TradeRecord) -> float:
        """คำนวณจำนวน Pips ที่ได้/เสีย"""
        if trade.status == TradeStatus.OPEN:
            exit_price = trade.current_price
        elif trade.exit_price is not None:
            exit_price = trade.exit_price
        else:
            return 0.0
        
        # คำนวณ Pips
        if trade.direction == "BUY":
            pips = (exit_price - trade.entry_price) / self.pip_size
        else:  # SELL
            pips = (trade.entry_price - exit_price) / self.pip_size
        
        return pips
    
    def _calculate_mae(self, trade: TradeRecord, price_history: List[Dict[str, Any]]) -> float:
        """คำนวณ Maximum Adverse Excursion"""
        if not price_history:
            return 0.0
        
        max_adverse = 0.0
        entry_price = trade.entry_price
        
        for price_point in price_history:
            timestamp = price_point.get('timestamp')
            if timestamp and timestamp < trade.open_time:
                continue
            
            if trade.direction == "BUY":
                # สำหรับ BUY, MAE คือราคาต่ำสุดที่ต่ำกว่า Entry
                low_price = price_point.get('low', price_point.get('price', entry_price))
                adverse = entry_price - low_price
            else:  # SELL
                # สำหรับ SELL, MAE คือราคาสูงสุดที่สูงกว่า Entry
                high_price = price_point.get('high', price_point.get('price', entry_price))
                adverse = high_price - entry_price
            
            if adverse > max_adverse:
                max_adverse = adverse
        
        # แปลงเป็น Pips
        return max_adverse / self.pip_size
    
    def _calculate_mfe(self, trade: TradeRecord, price_history: List[Dict[str, Any]]) -> float:
        """คำนวณ Maximum Favorable Excursion"""
        if not price_history:
            return 0.0
        
        max_favorable = 0.0
        entry_price = trade.entry_price
        
        for price_point in price_history:
            timestamp = price_point.get('timestamp')
            if timestamp and timestamp < trade.open_time:
                continue
            
            if trade.direction == "BUY":
                # สำหรับ BUY, MFE คือราคาสูงสุดที่สูงกว่า Entry
                high_price = price_point.get('high', price_point.get('price', entry_price))
                favorable = high_price - entry_price
            else:  # SELL
                # สำหรับ SELL, MFE คือราคาต่ำสุดที่ต่ำกว่า Entry
                low_price = price_point.get('low', price_point.get('price', entry_price))
                favorable = entry_price - low_price
            
            if favorable > max_favorable:
                max_favorable = favorable
        
        # แปลงเป็น Pips
        return max_favorable / self.pip_size
    
    def _calculate_risk_reward_ratio(self, trade: TradeRecord, metrics: TradeMetrics) -> float:
        """คำนวณ Risk-Reward Ratio"""
        if metrics.max_adverse_excursion <= 0:
            return 0.0
        
        if metrics.pips_gained > 0:
            return metrics.pips_gained / metrics.max_adverse_excursion
        else:
            return 0.0
    
    def _calculate_hold_time(self, trade: TradeRecord) -> float:
        """คำนวณเวลาการถือเทรด (นาที)"""
        if trade.status == TradeStatus.OPEN:
            end_time = datetime.now()
        elif trade.close_time:
            end_time = trade.close_time
        else:
            return 0.0
        
        time_diff = end_time - trade.open_time
        return time_diff.total_seconds() / 60.0
    
    def _calculate_entry_delay(self, trade: TradeRecord) -> float:
        """คำนวณความล่าช้าในการเข้าเทรด"""
        if trade.signal_time is None:
            return 0.0
        
        entry_delay = trade.open_time - trade.signal_time
        return entry_delay.total_seconds()
    
    def _calculate_exit_efficiency(self, trade: TradeRecord, metrics: TradeMetrics) -> float:
        """คำนวณประสิทธิภาพการออกจากเทรด"""
        if trade.status == TradeStatus.OPEN or metrics.max_favorable_excursion <= 0:
            return 100.0
        
        # ประสิทธิภาพ = (Pips ที่ได้จริง / MFE) * 100
        if metrics.pips_gained > 0:
            efficiency = (metrics.pips_gained / metrics.max_favorable_excursion) * 100.0
            return min(100.0, efficiency)
        else:
            return 0.0
    
    def _determine_trade_quality(self, pips_gained: float) -> TradeQuality:
        """กำหนดคุณภาพเทรดจากจำนวน Pips"""
        if pips_gained >= 200:
            return TradeQuality.EXCELLENT
        elif pips_gained >= 50:
            return TradeQuality.GOOD
        elif pips_gained >= 0:
            return TradeQuality.AVERAGE
        elif pips_gained >= -50:
            return TradeQuality.POOR
        else:
            return TradeQuality.TERRIBLE
    
    def _calculate_entry_precision(self, trade: TradeRecord, metrics: TradeMetrics) -> float:
        """คำนวณความแม่นยำการเข้าเทรด"""
        if metrics.max_adverse_excursion <= 0 and metrics.max_favorable_excursion <= 0:
            return 100.0
        
        total_movement = metrics.max_adverse_excursion + metrics.max_favorable_excursion
        if total_movement <= 0:
            return 100.0
        
        # ความแม่นยำ = (MFE / Total Movement) * 100
        precision = (metrics.max_favorable_excursion / total_movement) * 100.0
        return min(100.0, precision)
    
    def _calculate_exit_timing(self, trade: TradeRecord, metrics: TradeMetrics) -> float:
        """คำนวณจังหวะการออกจากเทรด"""
        if trade.status == TradeStatus.OPEN:
            return 50.0  # ยังไม่ปิด
        
        return metrics.exit_efficiency
    
    def _calculate_market_impact(self, trade: TradeRecord) -> float:
        """คำนวณผลกระทบต่อตลาด"""
        # สำหรับ Retail trading ผลกระทบต่อตลาดน้อยมาก
        # คำนวณจากขนาด position เทียบกับ volume ปกติ
        
        if trade.volume <= 0.1:
            return 0.1  # ผลกระทบน้อยมาก
        elif trade.volume <= 1.0:
            return 0.5  # ผลกระทบต่ำ
        else:
            return 1.0  # ผลกระทบปานกลาง
    
    def _calculate_slippage_cost(self, trade: TradeRecord) -> float:
        """คำนวณต้นทุน Slippage"""
        # ประมาณการ Slippage จาก Market Session และ Volume
        base_slippage = 0.5  # 0.5 pips base
        
        # ปรับตาม Market Session
        session_multipliers = {
            MarketSession.ASIAN: 1.0,
            MarketSession.LONDON: 0.8,
            MarketSession.NEW_YORK: 0.9,
            MarketSession.OVERLAP: 0.7
        }
        
        session_multiplier = session_multipliers.get(trade.trade_context.market_session, 1.0)
        
        # ปรับตาม Volume
        volume_multiplier = 1.0 + (trade.volume - 0.01) * 0.1
        
        # ปรับตาม Volatility
        volatility_multiplier = trade.trade_context.volatility_level
        
        slippage = base_slippage * session_multiplier * volume_multiplier * volatility_multiplier
        
        # แปลงเป็นเงิน
        slippage_cost = slippage * trade.volume * self.pip_value * 100
        
        return slippage_cost
    
    def _calculate_opportunity_cost(self, trade: TradeRecord, metrics: TradeMetrics) -> float:
        """คำนวณต้นทุนโอกาส"""
        if trade.status == TradeStatus.OPEN:
            return 0.0
        
        # ต้นทุนโอกาส = MFE - Pips ที่ได้จริง
        opportunity_cost_pips = metrics.max_favorable_excursion - metrics.pips_gained
        
        if opportunity_cost_pips > 0:
            # แปลงเป็นเงิน
            return opportunity_cost_pips * trade.volume * self.pip_value * 100
        
        return 0.0

class TradePatternRecognizer:
    """
    จดจำรูปแบบการเทรดและ Pattern ต่างๆ
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Pattern Definitions
        self.known_patterns = {
            'quick_scalp': {
                'hold_time_max': 15,      # นาที
                'pips_target': 5,         # pips
                'description': 'Quick Scalping Pattern'
            },
            'trend_rider': {
                'hold_time_min': 60,      # นาที
                'pips_target': 50,        # pips
                'direction_consistency': True,
                'description': 'Trend Following Pattern'
            },
            'reversal_play': {
                'hold_time_range': (30, 120),  # นาที
                'entry_precision_min': 80,     # %
                'description': 'Market Reversal Pattern'
            },
            'breakout_chase': {
                'entry_delay_max': 30,     # วินาที
                'volatility_min': 1.2,     # ระดับ
                'description': 'Breakout Momentum Pattern'
            },
            'news_reaction': {
                'news_proximity': True,
                'hold_time_max': 45,      # นาที
                'description': 'News Reaction Pattern'
            }
        }
    
    def identify_patterns(self, trade: TradeRecord, metrics: TradeMetrics) -> Tuple[List[str], float]:
        """
        จดจำ Pattern จากการเทรด
        
        Args:
            trade: ข้อมูลเทรด
            metrics: เมตริกส์เทรด
            
        Returns:
            Tuple[List[str], float]: (รายการ patterns, ความมั่นใจ)
        """
        try:
            identified_patterns = []
            confidence_scores = []
            
            # ตรวจสอบแต่ละ Pattern
            for pattern_name, pattern_def in self.known_patterns.items():
                match_score = self._check_pattern_match(trade, metrics, pattern_def)
                
                if match_score > 0.6:  # ความมั่นใจ > 60%
                    identified_patterns.append(pattern_name)
                    confidence_scores.append(match_score)
            
            # คำนวณความมั่นใจรวม
            overall_confidence = statistics.mean(confidence_scores) if confidence_scores else 0.0
            
            return identified_patterns, overall_confidence
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการจดจำ Pattern: {e}")
            return [], 0.0
    
    def _check_pattern_match(self, trade: TradeRecord, metrics: TradeMetrics, 
                           pattern_def: Dict[str, Any]) -> float:
        """ตรวจสอบการจับคู่ Pattern"""
        match_score = 0.0
        criteria_count = 0
        
        # ตรวจสอบเกณฑ์ต่างๆ
        
        # Hold Time
        if 'hold_time_max' in pattern_def:
            criteria_count += 1
            if metrics.hold_time_minutes <= pattern_def['hold_time_max']:
                match_score += 1.0
        
        if 'hold_time_min' in pattern_def:
            criteria_count += 1
            if metrics.hold_time_minutes >= pattern_def['hold_time_min']:
                match_score += 1.0
        
        if 'hold_time_range' in pattern_def:
            criteria_count += 1
            min_time, max_time = pattern_def['hold_time_range']
            if min_time <= metrics.hold_time_minutes <= max_time:
                match_score += 1.0
        
        # Pips Target
        if 'pips_target' in pattern_def:
            criteria_count += 1
            target_pips = pattern_def['pips_target']
            if abs(metrics.pips_gained) >= target_pips * 0.8:  # 80% ของเป้าหมาย
                match_score += 1.0
        
        # Entry Precision
        if 'entry_precision_min' in pattern_def:
            criteria_count += 1
            if metrics.entry_precision >= pattern_def['entry_precision_min']:
                match_score += 1.0
        
        # Entry Delay
        if 'entry_delay_max' in pattern_def:
            criteria_count += 1
            if metrics.entry_delay_seconds <= pattern_def['entry_delay_max']:
                match_score += 1.0
        
        # Volatility
        if 'volatility_min' in pattern_def:
            criteria_count += 1
            if trade.trade_context.volatility_level >= pattern_def['volatility_min']:
                match_score += 1.0
        
        # News Proximity
        if 'news_proximity' in pattern_def:
            criteria_count += 1
            if trade.trade_context.news_impact_level != "NONE":
                match_score += 1.0
        
        # คำนวณคะแนนเฉลี่ย
        return match_score / criteria_count if criteria_count > 0 else 0.0
    

class TradeComparator:
    """
    เปรียบเทียบเทรดกับเทรดอื่นๆ และสร้างการจัดอันดับ
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
    
    def compare_trade_performance(self, trade: TradeRecord, metrics: TradeMetrics,
                                comparison_trades: List[Tuple[TradeRecord, TradeMetrics]]) -> Dict[str, Any]:
        """
        เปรียบเทียบประสิทธิภาพของเทรดกับเทรดอื่นๆ
        
        Args:
            trade: เทรดที่ต้องการเปรียบเทียบ
            metrics: เมตริกส์ของเทรด
            comparison_trades: รายการเทรดสำหรับเปรียบเทียบ
            
        Returns:
            Dict: ผลการเปรียบเทียบ
        """
        try:
            if not comparison_trades:
                return {"error": "ไม่มีเทรดสำหรับเปรียบเทียบ"}
            
            # กรองเทรดที่เปรียบเทียบได้
            comparable_trades = self._filter_comparable_trades(trade, comparison_trades)
            
            if not comparable_trades:
                return {"error": "ไม่มีเทรดที่เปรียบเทียบได้"}
            
            # เปรียบเทียบแต่ละเมตริก
            comparison_result = {
                'total_comparisons': len(comparable_trades),
                'strategy_rank': self._calculate_strategy_rank(trade, metrics, comparable_trades),
                'session_rank': self._calculate_session_rank(trade, metrics, comparable_trades),
                'percentile_performance': self._calculate_percentile_performance(metrics, comparable_trades),
                'relative_performance': self._calculate_relative_performance(metrics, comparable_trades),
                'benchmark_comparison': self._compare_against_benchmarks(metrics, comparable_trades)
            }
            
            return comparison_result
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเปรียบเทียบเทรด: {e}")
            return {"error": str(e)}
    
    def _filter_comparable_trades(self, trade: TradeRecord, 
                                comparison_trades: List[Tuple[TradeRecord, TradeMetrics]]) -> List[Tuple[TradeRecord, TradeMetrics]]:
        """กรองเทรดที่เปรียบเทียบได้"""
        comparable = []
        
        for comp_trade, comp_metrics in comparison_trades:
            # เปรียบเทียบได้ถ้า:
            # 1. Symbol เดียวกัน
            # 2. ปิดเทรดแล้ว
            # 3. ไม่ใช่เทรดเดียวกัน
            
            if (comp_trade.symbol == trade.symbol and 
                comp_trade.status in [TradeStatus.CLOSED_PROFIT, TradeStatus.CLOSED_LOSS, TradeStatus.RECOVERED] and
                comp_trade.trade_id != trade.trade_id):
                comparable.append((comp_trade, comp_metrics))
        
        return comparable
    
    def _calculate_strategy_rank(self, trade: TradeRecord, metrics: TradeMetrics,
                                comparable_trades: List[Tuple[TradeRecord, TradeMetrics]]) -> int:
        """คำนวณอันดับในกลุ่ม Strategy เดียวกัน"""
        strategy_trades = [
            (t, m) for t, m in comparable_trades 
            if t.entry_strategy == trade.entry_strategy
        ]
        
        if not strategy_trades:
            return 1
        
        # เรียงตาม Net P&L
        strategy_trades.sort(key=lambda x: x[1].net_pnl, reverse=True)
        
        # หาอันดับ
        current_pnl = metrics.net_pnl
        rank = 1
        
        for _, comp_metrics in strategy_trades:
            if comp_metrics.net_pnl > current_pnl:
                rank += 1
            else:
                break
        
        return rank
    
    def _calculate_session_rank(self, trade: TradeRecord, metrics: TradeMetrics,
                                comparable_trades: List[Tuple[TradeRecord, TradeMetrics]]) -> int:
        """คำนวณอันดับในกลุ่ม Session เดียวกัน"""
        session_trades = [
            (t, m) for t, m in comparable_trades 
            if t.trade_context.market_session == trade.trade_context.market_session
        ]
        
        if not session_trades:
            return 1
        
        # เรียงตาม Net P&L
        session_trades.sort(key=lambda x: x[1].net_pnl, reverse=True)
        
        # หาอันดับ
        current_pnl = metrics.net_pnl
        rank = 1
        
        for _, comp_metrics in session_trades:
            if comp_metrics.net_pnl > current_pnl:
                rank += 1
            else:
                break
        
        return rank
    
    def _calculate_percentile_performance(self, metrics: TradeMetrics,
                                        comparable_trades: List[Tuple[TradeRecord, TradeMetrics]]) -> float:
        """คำนวณเปอร์เซ็นไทล์ประสิทธิภาพ"""
        if not comparable_trades:
            return 50.0
        
        # รวบรวม Net P&L ของเทรดทั้งหมด
        all_pnl = [m.net_pnl for _, m in comparable_trades]
        all_pnl.append(metrics.net_pnl)
        all_pnl.sort()
        
        # หาตำแหน่งของเทรดปัจจุบัน
        current_position = all_pnl.index(metrics.net_pnl)
        
        # คำนวณเปอร์เซ็นไทล์
        percentile = (current_position / (len(all_pnl) - 1)) * 100.0
        
        return percentile
    
    def _calculate_relative_performance(self, metrics: TradeMetrics,
                                        comparable_trades: List[Tuple[TradeRecord, TradeMetrics]]) -> Dict[str, float]:
        """คำนวณประสิทธิภาพเทียบกับค่าเฉลี่ย"""
        if not comparable_trades:
            return {}
        
        # รวบรวมข้อมูลสำหรับเปรียบเทียบ
        pnl_values = [m.net_pnl for _, m in comparable_trades]
        pips_values = [m.pips_gained for _, m in comparable_trades]
        hold_times = [m.hold_time_minutes for _, m in comparable_trades]
        
        # คำนวณค่าเฉลี่ย
        avg_pnl = statistics.mean(pnl_values) if pnl_values else 0.0
        avg_pips = statistics.mean(pips_values) if pips_values else 0.0
        avg_hold_time = statistics.mean(hold_times) if hold_times else 0.0
        
        # คำนวณ Relative Performance
        relative_performance = {
            'pnl_vs_average': ((metrics.net_pnl - avg_pnl) / abs(avg_pnl)) * 100.0 if avg_pnl != 0 else 0.0,
            'pips_vs_average': ((metrics.pips_gained - avg_pips) / abs(avg_pips)) * 100.0 if avg_pips != 0 else 0.0,
            'hold_time_vs_average': ((metrics.hold_time_minutes - avg_hold_time) / avg_hold_time) * 100.0 if avg_hold_time != 0 else 0.0,
            'average_pnl': avg_pnl,
            'average_pips': avg_pips,
            'average_hold_time': avg_hold_time
        }
        
        return relative_performance
    
    def _compare_against_benchmarks(self, metrics: TradeMetrics,
                                    comparable_trades: List[Tuple[TradeRecord, TradeMetrics]]) -> Dict[str, Any]:
        """เปรียบเทียบกับ Benchmark ต่างๆ"""
        benchmarks = {
            'top_10_percent': self._get_top_percentile_benchmark(comparable_trades, 90),
            'top_25_percent': self._get_top_percentile_benchmark(comparable_trades, 75),
            'median': self._get_median_benchmark(comparable_trades),
            'break_even': {'net_pnl': 0.0, 'pips_gained': 0.0}
        }
        
        comparisons = {}
        
        for benchmark_name, benchmark_data in benchmarks.items():
            if benchmark_data:
                comparison = {
                    'pnl_difference': metrics.net_pnl - benchmark_data.get('net_pnl', 0.0),
                    'pips_difference': metrics.pips_gained - benchmark_data.get('pips_gained', 0.0),
                    'outperformed': metrics.net_pnl > benchmark_data.get('net_pnl', 0.0)
                }
                comparisons[benchmark_name] = comparison
        
        return comparisons
    
    def _get_top_percentile_benchmark(self, comparable_trades: List[Tuple[TradeRecord, TradeMetrics]], 
                                    percentile: float) -> Dict[str, float]:
        """ดึง Benchmark จากเปอร์เซ็นไทล์บนสุด"""
        if not comparable_trades:
            return {}
        
        pnl_values = [m.net_pnl for _, m in comparable_trades]
        pips_values = [m.pips_gained for _, m in comparable_trades]
        
        pnl_values.sort(reverse=True)
        pips_values.sort(reverse=True)
        
        index = int(len(pnl_values) * percentile / 100.0)
        index = min(index, len(pnl_values) - 1)
        
        return {
            'net_pnl': pnl_values[index],
            'pips_gained': pips_values[index]
        }
    
    def _get_median_benchmark(self, comparable_trades: List[Tuple[TradeRecord, TradeMetrics]]) -> Dict[str, float]:
        """ดึง Median Benchmark"""
        if not comparable_trades:
            return {}
        
        pnl_values = [m.net_pnl for _, m in comparable_trades]
        pips_values = [m.pips_gained for _, m in comparable_trades]
        
        return {
            'net_pnl': statistics.median(pnl_values) if pnl_values else 0.0,
            'pips_gained': statistics.median(pips_values) if pips_values else 0.0
        }

class TradeAnalyzer:
    """
    🎯 Main Trade Analyzer Class
    
    ระบบวิเคราะห์การเทรดรายตัวแบบครอบคลุม
    รวบรวมการวิเคราะห์จากทุก Analyzer เข้าด้วยกัน
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Initialize Analyzers
        self.metrics_calculator = TradeMetricsCalculator()
        self.pattern_recognizer = TradePatternRecognizer()
        self.trade_comparator = TradeComparator()
        
        # Trade Database
        self.trade_database = {}  # In-memory database for quick access
        self.analysis_cache = {}  # Cache for analysis results
        
        # External Connections
        self.performance_tracker = None   # จะเชื่อมต่อใน start()
        self.market_analyzer = None       # จะเชื่อมต่อใน start()
        
        # Threading
        self.analysis_queue = deque(maxlen=1000)
        self.analysis_active = False
        self.analysis_thread = None
        
        self.logger.info("📊 เริ่มต้น Trade Analyzer")
    
    @handle_trading_errors(ErrorCategory.TRADE_ANALYSIS, ErrorSeverity.MEDIUM)
    async def start_trade_analyzer(self) -> None:
        """
        เริ่มต้น Trade Analyzer
        """
        self.logger.info("🚀 เริ่มต้น Trade Analyzer System")
        
        # เชื่อมต่อ External Components
        try:
            from analytics_engine.performance_tracker import get_performance_tracker
            self.performance_tracker = get_performance_tracker()
            
            from market_intelligence.market_analyzer import MarketAnalyzer
            self.market_analyzer = MarketAnalyzer()
            
            self.logger.info("✅ เชื่อมต่อ External Components สำเร็จ")
            
        except ImportError as e:
            self.logger.warning(f"⚠️ ไม่สามารถเชื่อมต่อบาง Components: {e}")
        
        # เริ่ม Analysis Processing
        await self._start_analysis_processing()
        
        self.logger.info("✅ Trade Analyzer พร้อมทำงาน")
   
    async def analyze_trade(self, trade: TradeRecord, 
                            price_history: List[Dict[str, Any]] = None,
                            comparison_scope: int = 100) -> TradeAnalysisResult:
        """
        วิเคราะห์เทรดแบบครอบคลุม
        
        Args:
            trade: ข้อมูลเทรด
            price_history: ประวัติราคาของเทรด
            comparison_scope: จำนวนเทรดสำหรับเปรียบเทียบ
            
        Returns:
            TradeAnalysisResult: ผลการวิเคราะห์
        """
        try:
            self.logger.info(f"📊 เริ่มวิเคราะห์เทรด: {trade.trade_id}")
            
            # 1. คำนวณ Trade Metrics
            trade_metrics = self.metrics_calculator.calculate_trade_metrics(trade, price_history)
            
            # 2. จดจำ Patterns
            identified_patterns, pattern_confidence = self.pattern_recognizer.identify_patterns(trade, trade_metrics)
            
            # 3. เปรียบเทียบกับเทรดอื่นๆ
            comparison_trades = self._get_comparison_trades(trade, comparison_scope)
            comparison_result = self.trade_comparator.compare_trade_performance(
                trade, trade_metrics, comparison_trades
            )
            
            # 4. คำนวณคะแนนต่างๆ
            performance_scores = self._calculate_performance_scores(trade, trade_metrics)
            
            # 5. วิเคราะห์จุดแข็ง-จุดอ่อน
            strengths, weaknesses = self._analyze_strengths_weaknesses(trade, trade_metrics)
            
            # 6. สร้างคำแนะนำ
            improvement_suggestions = self._generate_improvement_suggestions(trade, trade_metrics)
            strategy_adjustments = self._generate_strategy_adjustments(trade, trade_metrics)
            optimization_suggestions = self._generate_optimization_suggestions(trade, trade_metrics)
            
            # สร้าง Analysis Result
            analysis_result = TradeAnalysisResult(
                trade_id=trade.trade_id,
                analysis_timestamp=datetime.now(),
                
                # Performance Scores
                overall_performance_score=performance_scores.get('overall', 0.0),
                entry_score=performance_scores.get('entry', 0.0),
                exit_score=performance_scores.get('exit', 0.0),
                timing_score=performance_scores.get('timing', 0.0),
                risk_management_score=performance_scores.get('risk_management', 0.0),
                
                # Analysis Results
                strengths=strengths,
                weaknesses=weaknesses,
                improvement_suggestions=improvement_suggestions,
                
                # Comparative Analysis
                strategy_rank=comparison_result.get('strategy_rank', 0),
                session_rank=comparison_result.get('session_rank', 0),
                percentile_performance=comparison_result.get('percentile_performance', 0.0),
                
                # Pattern Recognition
                identified_patterns=identified_patterns,
                pattern_confidence=pattern_confidence,
                
                # Recommendations
                strategy_adjustments=strategy_adjustments,
                optimal_entry_suggestions=optimization_suggestions.get('entry', []),
                risk_optimization=optimization_suggestions.get('risk', [])
            )
            
            # บันทึกผลการวิเคราะห์
            self._save_analysis_result(trade, trade_metrics, analysis_result)
            
            self.logger.info(f"✅ วิเคราะห์เทรดเสร็จสิ้น: {trade.trade_id} - Score: {analysis_result.overall_performance_score:.1f}")
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์เทรด {trade.trade_id}: {e}")
            return self._create_fallback_analysis_result(trade.trade_id)
    
    def _get_comparison_trades(self, trade: TradeRecord, scope: int) -> List[Tuple[TradeRecord, TradeMetrics]]:
        """ดึงเทรดสำหรับเปรียบเทียบ"""
        try:
            comparison_trades = []
            
            # ดึงจาก Database
            for stored_trade_id, stored_data in self.trade_database.items():
                if len(comparison_trades) >= scope:
                    break
                
                stored_trade = stored_data.get('trade')
                stored_metrics = stored_data.get('metrics')
                
                if stored_trade and stored_metrics and stored_trade.trade_id != trade.trade_id:
                    comparison_trades.append((stored_trade, stored_metrics))
            
            # ถ้าไม่เพียงพอ ดึงจาก Performance Tracker
            if len(comparison_trades) < scope and self.performance_tracker:
                additional_trades = self.performance_tracker.get_recent_trades(scope - len(comparison_trades))
                
                for additional_trade in additional_trades:
                    # แปลงเป็น TradeRecord และคำนวณ Metrics
                    trade_record = self._convert_to_trade_record(additional_trade)
                    trade_metrics = self.metrics_calculator.calculate_trade_metrics(trade_record)
                    
                    comparison_trades.append((trade_record, trade_metrics))
            
            return comparison_trades
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงเทรดเปรียบเทียบ: {e}")
            return []
    
    def _calculate_performance_scores(self, trade: TradeRecord, metrics: TradeMetrics) -> Dict[str, float]:
        """คำนวณคะแนนประสิทธิภาพต่างๆ"""
        try:
            scores = {}
            
            # Entry Score (0-100)
            entry_score = 0.0
            entry_score += min(30.0, metrics.entry_precision * 0.3)  # Entry Precision
            entry_score += min(20.0, max(0, 10 - metrics.entry_delay_seconds) * 2)  # Entry Speed
            entry_score += min(25.0, trade.entry_confidence * 0.25)  # Entry Confidence
            entry_score += min(25.0, trade.signal_quality * 0.25)  # Signal Quality
            scores['entry'] = entry_score
            
            # Exit Score (0-100)
            if trade.status != TradeStatus.OPEN:
                exit_score = 0.0
                exit_score += min(40.0, metrics.exit_efficiency * 0.4)  # Exit Efficiency
                exit_score += min(30.0, metrics.exit_timing * 0.3)  # Exit Timing
                
                # Exit Reason Score
                if trade.exit_reason == ExitReason.TAKE_PROFIT:
                    exit_score += 30.0
                elif trade.exit_reason == ExitReason.RECOVERY_CLOSE:
                    exit_score += 20.0
                elif trade.exit_reason == ExitReason.TIME_EXIT:
                    exit_score += 15.0
                else:
                    exit_score += 10.0
                
                scores['exit'] = exit_score
            else:
                scores['exit'] = 50.0  # เทรดยังเปิดอยู่
            
            # Timing Score (0-100)
            timing_score = 0.0
            
            # Hold Time Appropriateness
            if metrics.hold_time_minutes <= 15:  # Scalping
                if trade.entry_strategy == EntryStrategy.SCALPING_QUICK:
                    timing_score += 30.0
                else:
                    timing_score += 15.0
            elif metrics.hold_time_minutes <= 240:  # Intraday
                timing_score += 25.0
            else:  # Swing
                if trade.entry_strategy in [EntryStrategy.TREND_FOLLOWING]:
                    timing_score += 30.0
                else:
                    timing_score += 20.0
            
            # Market Session Appropriateness
            session_score = self._calculate_session_timing_score(trade)
            timing_score += session_score * 0.4
            
            # News Timing
            if trade.trade_context.news_impact_level == "NONE":
                timing_score += 30.0  # ไม่มีข่าวคือดี
            elif trade.entry_strategy == EntryStrategy.NEWS_REACTION:
                timing_score += 25.0  # News strategy ในช่วงข่าว
            else:
                timing_score += 10.0  # เทรดปกติในช่วงข่าว
            
            scores['timing'] = min(100.0, timing_score)
            
            # Risk Management Score (0-100)
            risk_score = 0.0
            
            # MAE Control
            if metrics.max_adverse_excursion <= 20:  # MAE < 20 pips
                risk_score += 30.0
            elif metrics.max_adverse_excursion <= 50:
                risk_score += 20.0
            else:
                risk_score += 10.0
            
            # Risk-Reward Ratio
            if metrics.risk_reward_ratio >= 2.0:
                risk_score += 30.0
            elif metrics.risk_reward_ratio >= 1.0:
                risk_score += 20.0
            else:
                risk_score += 10.0
            
            # Position Sizing Appropriateness
            if trade.volume <= 0.1:  # Conservative sizing
                risk_score += 25.0
            elif trade.volume <= 0.5:
                risk_score += 20.0
            else:
                risk_score += 10.0
            
            # Recovery Potential
            if trade.is_recovery_trade:
                if trade.status == TradeStatus.RECOVERED:
                    risk_score += 15.0  # Successful recovery
                else:
                    risk_score += 10.0  # Recovery in progress
            else:
                risk_score += 15.0  # No recovery needed
            
            scores['risk_management'] = min(100.0, risk_score)
            
            # Overall Score (weighted average)
            weights = {
                'entry': 0.25,
                'exit': 0.25,
                'timing': 0.25,
                'risk_management': 0.25
            }
            
            overall_score = sum(scores[key] * weights[key] for key in weights.keys())
            scores['overall'] = overall_score
            
            return scores
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการคำนวณ Performance Scores: {e}")
            return {'overall': 50.0, 'entry': 50.0, 'exit': 50.0, 'timing': 50.0, 'risk_management': 50.0}
    
    def _calculate_session_timing_score(self, trade: TradeRecord) -> float:
        """คำนวณคะแนนจังหวะเวลาตาม Session"""
        strategy = trade.entry_strategy
        session = trade.trade_context.market_session
        
        # Session-Strategy Optimal Matching
        optimal_matches = {
            (EntryStrategy.SCALPING_QUICK, MarketSession.LONDON): 100.0,
            (EntryStrategy.SCALPING_QUICK, MarketSession.NEW_YORK): 90.0,
            (EntryStrategy.SCALPING_QUICK, MarketSession.OVERLAP): 95.0,
            (EntryStrategy.SCALPING_QUICK, MarketSession.ASIAN): 60.0,
            
            (EntryStrategy.TREND_FOLLOWING, MarketSession.LONDON): 95.0,
            (EntryStrategy.TREND_FOLLOWING, MarketSession.NEW_YORK): 90.0,
            (EntryStrategy.TREND_FOLLOWING, MarketSession.OVERLAP): 100.0,
            (EntryStrategy.TREND_FOLLOWING, MarketSession.ASIAN): 70.0,
            
            (EntryStrategy.MEAN_REVERSION, MarketSession.ASIAN): 95.0,
            (EntryStrategy.MEAN_REVERSION, MarketSession.LONDON): 75.0,
            (EntryStrategy.MEAN_REVERSION, MarketSession.NEW_YORK): 80.0,
            (EntryStrategy.MEAN_REVERSION, MarketSession.OVERLAP): 70.0,
            
            (EntryStrategy.NEWS_REACTION, MarketSession.LONDON): 90.0,
            (EntryStrategy.NEWS_REACTION, MarketSession.NEW_YORK): 100.0,
            (EntryStrategy.NEWS_REACTION, MarketSession.OVERLAP): 95.0,
            (EntryStrategy.NEWS_REACTION, MarketSession.ASIAN): 50.0,
        }
        
        return optimal_matches.get((strategy, session), 75.0)  # Default 75%
    
    def _analyze_strengths_weaknesses(self, trade: TradeRecord, metrics: TradeMetrics) -> Tuple[List[str], List[str]]:
        """วิเคราะห์จุดแข็งและจุดอ่อน"""
        strengths = []
        weaknesses = []
        
        try:
            # วิเคราะห์จุดแข็ง
            
            # Entry Precision
            if metrics.entry_precision > 80:
                strengths.append("🎯 การเข้าเทรดแม่นยำสูง")
            
            # Exit Efficiency
            if metrics.exit_efficiency > 85:
                strengths.append("🚪 การออกจากเทรดมีประสิทธิภาพ")
            
            # Risk-Reward Ratio
            if metrics.risk_reward_ratio > 2.0:
                strengths.append("⚖️ Risk-Reward Ratio ดีเยี่ยม")
            
            # Hold Time
            if trade.entry_strategy == EntryStrategy.SCALPING_QUICK and metrics.hold_time_minutes <= 15:
                strengths.append("⚡ การถือเทรดเหมาะสมกับ Scalping")
            elif trade.entry_strategy == EntryStrategy.TREND_FOLLOWING and metrics.hold_time_minutes >= 60:
                strengths.append("📈 การถือเทรดเหมาะสมกับ Trend Following")
            
            # News Timing
            if trade.trade_context.news_impact_level == "NONE":
                strengths.append("📰 หลีกเลี่ยงช่วงข่าวได้ดี")
            
            # Profit Achievement
            if metrics.pips_gained > 50:
                strengths.append("💰 ทำกำไรได้ดี")
            
            # วิเคราะห์จุดอ่อน
            
            # Entry Delay
            if metrics.entry_delay_seconds > 60:
                weaknesses.append("🐌 เข้าเทรดช้าเกินไป")
            
            # High MAE
            if metrics.max_adverse_excursion > 50:
                weaknesses.append("📉 เทรดไปทางตรงข้ามมากเกินไป")
            
            # Poor Exit Timing
            if metrics.exit_efficiency < 50:
                weaknesses.append("❌ ออกจากเทรดไม่เหมาะสม")
            
            # Risk-Reward Issues
            if metrics.risk_reward_ratio < 1.0:
                weaknesses.append("⚠️ Risk-Reward Ratio ต่ำเกินไป")
            
            # Position Size Issues
            if trade.volume > 1.0:
                weaknesses.append("📊 ขนาด Position ใหญ่เกินไป")
            
            # Hold Time Issues
            if trade.entry_strategy == EntryStrategy.SCALPING_QUICK and metrics.hold_time_minutes > 60:
                weaknesses.append("⏰ ถือเทรดนานเกินไปสำหรับ Scalping")
            
            # News Impact
            if (trade.trade_context.news_impact_level == "HIGH" and 
                trade.entry_strategy != EntryStrategy.NEWS_REACTION):
                weaknesses.append("📰 เทรดในช่วงข่าวสำคัญ")
            
            # Loss Issues
            if metrics.pips_gained < -20:
                weaknesses.append("💸 ขาดทุนมากเกินไป")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการวิเคราะห์จุดแข็ง-จุดอ่อน: {e}")
        
        return strengths, weaknesses

    def _generate_improvement_suggestions(self, trade: TradeRecord, metrics: TradeMetrics) -> List[str]:
        """สร้างคำแนะนำการปรับปรุง"""
        suggestions = []
        
        try:
            # คำแนะนำตาม Entry Performance
            if metrics.entry_precision < 70:
                suggestions.append("🎯 ปรับปรุงการวิเคราะห์ก่อนเข้าเทรด - ใช้ Indicator เพิ่มเติม")
            
            if metrics.entry_delay_seconds > 30:
                suggestions.append("⚡ เพิ่มความเร็วในการตัดสินใจเข้าเทรด")
            
            # คำแนะนำตาม Exit Performance
            if metrics.exit_efficiency < 60:
                suggestions.append("🚪 ปรับปรุงกลยุทธ์การออกจากเทรด - ใช้ Trailing Stop")
            
            if metrics.exit_timing < 50:
                suggestions.append("⏰ ปรับปรุงจังหวะการออกจากเทรด")
            
            # คำแนะนำตาม Risk Management
            if metrics.max_adverse_excursion > 30:
                suggestions.append("🛡️ ปรับปรุงการบริหารความเสี่ยง - ลดขนาด Position")
            
            if metrics.risk_reward_ratio < 1.5:
                suggestions.append("⚖️ เพิ่ม Target Profit หรือลด Risk")
            
            # คำแนะนำตาม Strategy
            if trade.entry_strategy == EntryStrategy.SCALPING_QUICK and metrics.hold_time_minutes > 30:
                suggestions.append("⚡ สำหรับ Scalping ควรออกจากเทรดเร็วขึ้น")
            
            if trade.entry_strategy == EntryStrategy.TREND_FOLLOWING and metrics.hold_time_minutes < 30:
                suggestions.append("📈 สำหรับ Trend Following ควรถือเทรดนานขึ้น")
            
            # คำแนะนำตาม Session
            session_score = self._calculate_session_timing_score(trade)
            if session_score < 80:
                suggestions.append(f"🕐 เลือก Trading Session ที่เหมาะสมกับ {trade.entry_strategy.value}")
            
            # คำแนะนำตาม Market Conditions
            if trade.trade_context.volatility_level > 1.5 and trade.volume > 0.1:
                suggestions.append("📊 ในช่วง Volatility สูง ควรลดขนาด Position")
            
            # คำแนะนำทั่วไป
            if len(suggestions) == 0:
                suggestions.append("✅ เทรดนี้มีคุณภาพดี - คงการตั้งค่าปัจจุบัน")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้างคำแนะนำ: {e}")
        
        return suggestions[:5]  # จำกัดไม่เกิน 5 คำแนะนำ
    
    def _generate_strategy_adjustments(self, trade: TradeRecord, metrics: TradeMetrics) -> List[str]:
        """สร้างคำแนะนำการปรับ Strategy"""
        adjustments = []
        
        try:
            strategy = trade.entry_strategy
            
            # Strategy-specific adjustments
            if strategy == EntryStrategy.SCALPING_QUICK:
                if metrics.hold_time_minutes > 15:
                    adjustments.append("⚡ ลดเวลาการถือ Scalping Position")
                if metrics.pips_gained < 5 and metrics.pips_gained > 0:
                    adjustments.append("🎯 เพิ่ม Target สำหรับ Scalping")
            
            elif strategy == EntryStrategy.TREND_FOLLOWING:
                if metrics.exit_efficiency < 70:
                    adjustments.append("📈 ใช้ Trailing Stop สำหรับ Trend Following")
                if metrics.hold_time_minutes < 60:
                    adjustments.append("⏰ ถือ Trend Position นานขึ้น")
            
            elif strategy == EntryStrategy.MEAN_REVERSION:
                if metrics.entry_precision < 75:
                    adjustments.append("🎯 ปรับปรุงการหาจุด Entry สำหรับ Mean Reversion")
                if trade.trade_context.market_state == "TRENDING":
                    adjustments.append("⚠️ หลีกเลี่ยง Mean Reversion ในตลาด Trending")
            
            elif strategy == EntryStrategy.NEWS_REACTION:
                if metrics.entry_delay_seconds > 10:
                    adjustments.append("⚡ เร่งความเร็วการเข้าเทรดหลังข่าว")
                if trade.trade_context.news_impact_level == "LOW":
                    adjustments.append("📰 เลือกข่าวที่มีผลกระทบสูงกว่า")
            
            # General Strategy Adjustments
            if metrics.risk_reward_ratio < 1.0:
                adjustments.append("⚖️ ปรับ Strategy ให้มี Risk-Reward ดีขึ้น")
            
            if metrics.max_adverse_excursion > 40:
                adjustments.append("🛡️ เพิ่มการกรอง Entry Signal")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้างคำแนะนำ Strategy: {e}")
        
        return adjustments[:3]  # จำกัดไม่เกิน 3 คำแนะนำ
    
    def _generate_optimization_suggestions(self, trade: TradeRecord, metrics: TradeMetrics) -> Dict[str, List[str]]:
        """สร้างคำแนะนำการเพิ่มประสิทธิภาพ"""
        suggestions = {
            'entry': [],
            'exit': [],
            'risk': [],
            'general': []
        }
        
        try:
            # Entry Optimization
            if metrics.entry_precision < 80:
                suggestions['entry'].append("🎯 ใช้ Multiple Timeframe Analysis")
                suggestions['entry'].append("📊 เพิ่ม Confirmation Indicators")
            
            if trade.entry_confidence < 0.8:
                suggestions['entry'].append("💡 รอสัญญาณที่มีความมั่นใจสูงกว่า")
            
            # Exit Optimization
            if metrics.exit_efficiency < 75:
                suggestions['exit'].append("🚪 ใช้ Partial Profit Taking")
                suggestions['exit'].append("📈 ปรับ Take Profit ตาม Market Condition")
            
            if metrics.opportunity_cost > 50:
                suggestions['exit'].append("💰 ปรับปรุงการจับ Peak ของเทรด")
            
            # Risk Optimization
            if metrics.max_adverse_excursion > 25:
                suggestions['risk'].append("🛡️ ใช้ Smaller Position Size")
                suggestions['risk'].append("📉 ปรับปรุงการหา Stop Level")
            
            if trade.volume > 0.5:
                suggestions['risk'].append("📊 ลดขนาด Position ในช่วงทดสอบ Strategy")
            
            # General Optimization
            if trade.trade_context.market_session != self._get_optimal_session(trade.entry_strategy):
                optimal_session = self._get_optimal_session(trade.entry_strategy)
                suggestions['general'].append(f"🕐 เทรดใน {optimal_session.value} Session จะดีกว่า")
            
            if trade.trade_context.concurrent_trades > 5:
                suggestions['general'].append("🔢 ลดจำนวนเทรดพร้อมกัน")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการสร้างคำแนะนำ Optimization: {e}")
        
        return suggestions
    
    def _get_optimal_session(self, strategy: EntryStrategy) -> MarketSession:
        """หา Session ที่เหมาะสมที่สุดสำหรับ Strategy"""
        optimal_sessions = {
            EntryStrategy.SCALPING_QUICK: MarketSession.LONDON,
            EntryStrategy.TREND_FOLLOWING: MarketSession.OVERLAP,
            EntryStrategy.MEAN_REVERSION: MarketSession.ASIAN,
            EntryStrategy.BREAKOUT_MOMENTUM: MarketSession.LONDON,
            EntryStrategy.FALSE_BREAKOUT: MarketSession.OVERLAP,
            EntryStrategy.NEWS_REACTION: MarketSession.NEW_YORK
        }
        
        return optimal_sessions.get(strategy, MarketSession.LONDON)
    
    def _convert_to_trade_record(self, trade_data: Dict[str, Any]) -> TradeRecord:
        """แปลงข้อมูลเทรดเป็น TradeRecord"""
        # สร้าง TradeRecord จากข้อมูลที่ได้จาก Performance Tracker
        return TradeRecord(
            trade_id=trade_data.get('trade_id', 'UNKNOWN'),
            position_id=trade_data.get('position_id', 'UNKNOWN'),
            symbol=trade_data.get('symbol', 'XAUUSD'),
            direction=trade_data.get('direction', 'BUY'),
            volume=trade_data.get('volume', 0.01),
            entry_price=trade_data.get('entry_price', 0.0),
            exit_price=trade_data.get('exit_price'),
            open_time=trade_data.get('open_time', datetime.now()),
            close_time=trade_data.get('close_time'),
            status=TradeStatus.CLOSED_PROFIT if trade_data.get('pnl', 0) > 0 else TradeStatus.CLOSED_LOSS,
            entry_strategy=EntryStrategy(trade_data.get('entry_strategy', 'TREND_FOLLOWING'))
        )
    
    def _save_analysis_result(self, trade: TradeRecord, metrics: TradeMetrics, 
                            analysis_result: TradeAnalysisResult) -> None:
        """บันทึกผลการวิเคราะห์"""
        try:
            # บันทึกใน Memory Database
            self.trade_database[trade.trade_id] = {
                'trade': trade,
                'metrics': metrics,
                'analysis': analysis_result,
                'timestamp': datetime.now()
            }
            
            # บันทึกใน Cache
            self.analysis_cache[trade.trade_id] = analysis_result
            
            # บันทึกไปยัง Performance Tracker
            if self.performance_tracker:
                asyncio.create_task(self.performance_tracker.record_trade_analysis(trade, analysis_result))
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการบันทึกผลการวิเคราะห์: {e}")
    
    def _create_fallback_analysis_result(self, trade_id: str) -> TradeAnalysisResult:
        """สร้าง Fallback Analysis Result"""
        return TradeAnalysisResult(
            trade_id=trade_id,
            overall_performance_score=50.0,
            entry_score=50.0,
            exit_score=50.0,
            timing_score=50.0,
            risk_management_score=50.0,
            strengths=["ไม่สามารถวิเคราะห์ได้"],
            weaknesses=["ข้อมูลไม่เพียงพอ"],
            improvement_suggestions=["ตรวจสอบระบบการวิเคราะห์"],
            identified_patterns=[],
            pattern_confidence=0.0,
            strategy_adjustments=[],
            optimal_entry_suggestions=[],
            risk_optimization=[]
        )
    
    async def _start_analysis_processing(self) -> None:
        """เริ่ม Analysis Processing แบบต่อเนื่อง"""
        if self.analysis_active:
            return
        
        self.analysis_active = True
        self.analysis_thread = threading.Thread(target=self._analysis_processing_loop, daemon=True)
        self.analysis_thread.start()
        
        self.logger.info("🔄 เริ่ม Analysis Processing แบบต่อเนื่อง")
    
    def _analysis_processing_loop(self) -> None:
        """Analysis Processing Loop"""
        try:
            while self.analysis_active:
                if self.analysis_queue:
                    # ดึงเทรดจาก Queue
                    analysis_task = self.analysis_queue.popleft()
                    
                    # ประมวลผลการวิเคราะห์
                    try:
                        result = asyncio.run(self.analyze_trade(
                            analysis_task['trade'],
                            analysis_task.get('price_history'),
                            analysis_task.get('comparison_scope', 100)
                        ))
                        
                        # Callback ถ้ามี
                        if analysis_task.get('callback'):
                            analysis_task['callback'](result)
                            
                    except Exception as e:
                        self.logger.error(f"❌ ข้อผิดพลาดในการประมวลผล Analysis: {e}")
                
                time.sleep(1)  # รอ 1 วินาที
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Analysis Processing Loop: {e}")
        finally:
            self.analysis_active = False
    
    def queue_trade_analysis(self, trade: TradeRecord, 
                            price_history: List[Dict[str, Any]] = None,
                            comparison_scope: int = 100,
                            callback: Callable = None) -> None:
        """เพิ่มเทรดเข้า Analysis Queue"""
        analysis_task = {
            'trade': trade,
            'price_history': price_history,
            'comparison_scope': comparison_scope,
            'callback': callback,
            'queued_at': datetime.now()
        }
        
        self.analysis_queue.append(analysis_task)
        self.logger.debug(f"📥 เพิ่มเทรดเข้า Analysis Queue: {trade.trade_id}")
    
    def get_trade_analysis(self, trade_id: str) -> Optional[TradeAnalysisResult]:
        """ดึงผลการวิเคราะห์ของเทรด"""
        return self.analysis_cache.get(trade_id)
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """ดึงสถิติการวิเคราะห์"""
        try:
            total_analyzed = len(self.trade_database)
            
            if total_analyzed == 0:
                return {"total_analyzed": 0}
            
            # คำนวณคะแนนเฉลี่ย
            all_scores = []
            pattern_counts = defaultdict(int)
            
            for trade_data in self.trade_database.values():
                analysis = trade_data.get('analysis')
                if analysis:
                    all_scores.append(analysis.overall_performance_score)
                    for pattern in analysis.identified_patterns:
                        pattern_counts[pattern] += 1
            
            avg_score = statistics.mean(all_scores) if all_scores else 0.0
            
            # Top Patterns
            top_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                "total_analyzed": total_analyzed,
                "average_performance_score": avg_score,
                "queue_size": len(self.analysis_queue),
                "analysis_active": self.analysis_active,
                "top_patterns": top_patterns,
                "cache_size": len(self.analysis_cache)
            }
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงสถิติ: {e}")
            return {"error": str(e)}
    
    def stop_trade_analyzer(self) -> None:
        """หยุด Trade Analyzer"""
        self.analysis_active = False
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=5)
        
        self.logger.info("🛑 หยุด Trade Analyzer")

# Global Trade Analyzer Instance
_global_trade_analyzer: Optional[TradeAnalyzer] = None

def get_trade_analyzer() -> TradeAnalyzer:
    """
    ดึง Trade Analyzer Instance (Singleton Pattern)
    
    Returns:
        TradeAnalyzer: Instance ของ Trade Analyzer
    """
    global _global_trade_analyzer
    
    if _global_trade_analyzer is None:
        _global_trade_analyzer = TradeAnalyzer()
    
    return _global_trade_analyzer

# Utility Functions
async def quick_trade_analysis(trade: TradeRecord) -> TradeAnalysisResult:
    """
    วิเคราะห์เทรดแบบเร็ว
    
    Args:
        trade: ข้อมูลเทรด
        
    Returns:
        TradeAnalysisResult: ผลการวิเคราะห์
    """
    analyzer = get_trade_analyzer()
    return await analyzer.analyze_trade(trade)

def create_trade_record(trade_id: str, position_id: str, direction: str, 
                      volume: float, entry_price: float, 
                      entry_strategy: EntryStrategy = EntryStrategy.TREND_FOLLOWING,
                      exit_price: Optional[float] = None,
                      trade_type: TradeType = TradeType.REGULAR) -> TradeRecord:
    """
    สร้าง TradeRecord สำหรับการวิเคราะห์
    
    Utility function สำหรับสร้าง TradeRecord ได้ง่ายๆ
    """
    trade = TradeRecord(
        trade_id=trade_id,
        position_id=position_id,
        direction=direction,
        volume=volume,
        entry_price=entry_price,
        exit_price=exit_price,
        entry_strategy=entry_strategy,
        trade_type=trade_type,
        current_price=exit_price or entry_price
    )
    
    # ตั้งค่า Status
    if exit_price is not None:
        if direction == "BUY":
            profit = exit_price - entry_price
        else:
            profit = entry_price - exit_price
        
        trade.status = TradeStatus.CLOSED_PROFIT if profit > 0 else TradeStatus.CLOSED_LOSS
        trade.close_time = datetime.now()
    
    return trade

if __name__ == "__main__":
    """
    ทดสอบ Trade Analyzer System
    """
    import asyncio
    
    async def test_trade_analyzer():
        """ทดสอบการทำงานของ Trade Analyzer"""
        
        print("🧪 เริ่มทดสอบ Trade Analyzer System")
        
        # เริ่มต้น Trade Analyzer
        analyzer = get_trade_analyzer()
        await analyzer.start_trade_analyzer()
        
        try:
            # สร้างเทรดทดสอบ
            test_trade = create_trade_record(
                trade_id="TEST_001",
                position_id="POS_001",
                direction="BUY",
                volume=0.1,
                entry_price=1850.50,
                exit_price=1852.30,  # กำไร 18 pips
                entry_strategy=EntryStrategy.TREND_FOLLOWING
            )
            
            # ตั้งค่า Context
            test_trade.trade_context.market_session = MarketSession.LONDON
            test_trade.trade_context.market_state = "TRENDING"
            test_trade.trade_context.volatility_level = 1.2
            test_trade.entry_confidence = 0.85
            test_trade.signal_quality = 0.80
            
            # สร้าง Price History
            price_history = [
                {"timestamp": test_trade.open_time, "high": 1851.0, "low": 1849.8, "price": 1850.50},
                {"timestamp": test_trade.open_time + timedelta(minutes=5), "high": 1851.5, "low": 1850.0, "price": 1851.0},
                {"timestamp": test_trade.open_time + timedelta(minutes=10), "high": 1852.5, "low": 1850.8, "price": 1852.0},
                {"timestamp": test_trade.open_time + timedelta(minutes=15), "high": 1853.0, "low": 1852.0, "price": 1852.30}
            ]
            
            # วิเคราะห์เทรด
            print(f"\n📊 ทดสอบการวิเคราะห์เทรด...")
            analysis_result = await analyzer.analyze_trade(test_trade, price_history)
            
            # แสดงผล
            print(f"   Trade ID: {analysis_result.trade_id}")
            print(f"   Overall Score: {analysis_result.overall_performance_score:.1f}/100")
            print(f"   Entry Score: {analysis_result.entry_score:.1f}/100")
            print(f"   Exit Score: {analysis_result.exit_score:.1f}/100")
            print(f"   Timing Score: {analysis_result.timing_score:.1f}/100")
            print(f"   Risk Management Score: {analysis_result.risk_management_score:.1f}/100")
            
            print(f"\n🎯 Identified Patterns:")
            for pattern in analysis_result.identified_patterns:
                print(f"   - {pattern}")
            print(f"   Pattern Confidence: {analysis_result.pattern_confidence:.1%}")
            
            print(f"\n💪 Strengths:")
            for strength in analysis_result.strengths:
                print(f"   {strength}")
            
            print(f"\n🔍 Weaknesses:")
            for weakness in analysis_result.weaknesses:
                print(f"   {weakness}")
            
            print(f"\n💡 Improvement Suggestions:")
            for suggestion in analysis_result.improvement_suggestions:
                print(f"   {suggestion}")
            
            print(f"\n⚙️ Strategy Adjustments:")
            for adjustment in analysis_result.strategy_adjustments:
                print(f"   {adjustment}")
            
            print(f"\n📈 Comparative Analysis:")
            print(f"   Strategy Rank: {analysis_result.strategy_rank}")
            print(f"   Session Rank: {analysis_result.session_rank}")
            print(f"   Percentile: {analysis_result.percentile_performance:.1f}%")
            
            # ทดสอบ Queue System
            print(f"\n🔄 ทดสอบ Queue System...")
            
            # สร้างเทรดเพิ่มเติม
            test_trade_2 = create_trade_record(
                trade_id="TEST_002",
                position_id="POS_002",
                direction="SELL",
                volume=0.05,
                entry_price=1851.00,
                exit_price=1849.50,  # กำไร 15 pips
                entry_strategy=EntryStrategy.SCALPING_QUICK
            )
            
            # เพิ่มเข้า Queue
            def analysis_callback(result):
                print(f"   📋 Queue Analysis Complete: {result.trade_id} - Score: {result.overall_performance_score:.1f}")
            
            analyzer.queue_trade_analysis(test_trade_2, callback=analysis_callback)
            
            # รอให้ประมวลผลเสร็จ
            await asyncio.sleep(3)
            
            # แสดงสถิติ
            stats = analyzer.get_analysis_statistics()
            print(f"\n📈 Trade Analyzer Statistics:")
            print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))
            
        finally:
            analyzer.stop_trade_analyzer()
        
        print("\n✅ ทดสอบ Trade Analyzer เสร็จสิ้น")
    
    # รันการทดสอบ
    asyncio.run(test_trade_analyzer())