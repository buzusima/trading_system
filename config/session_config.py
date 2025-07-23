#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SESSION CONFIGURATION - การตั้งค่าเฉพาะช่วงเวลาการเทรด
=================================================
จัดการการตั้งค่าที่แตกต่างกันสำหรับแต่ละ session การเทรด
รองรับการปรับเปลี่ยนพฤติกรรมตามช่วงเวลาและลักษณะตลาด

เชื่อมต่อไปยัง:
- config/trading_params.py (พารามิเตอร์การเทรด)
- market_intelligence/session_manager.py (จัดการ session)
- adaptive_entries/strategy_selector.py (เลือกกลยุทธ์)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, time, timezone, timedelta
from enum import Enum
import pytz

class SessionType(Enum):
    """ประเภทของ session การเทรด"""
    ASIAN = "ASIAN"
    LONDON = "LONDON" 
    NEW_YORK = "NEW_YORK"
    OVERLAP_LONDON_NY = "OVERLAP_LONDON_NY"
    QUIET_HOURS = "QUIET_HOURS"
    PRE_MARKET = "PRE_MARKET"
    POST_MARKET = "POST_MARKET"

class MarketCharacteristic(Enum):
    """ลักษณะของตลาดในแต่ละ session"""
    LOW_VOLATILITY = "LOW_VOLATILITY"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    NEWS_DRIVEN = "NEWS_DRIVEN"
    TECHNICAL_DRIVEN = "TECHNICAL_DRIVEN"

@dataclass
class SessionTimeConfig:
    """การตั้งค่าเวลาสำหรับแต่ละ session"""
    
    name: str
    start_time: time
    end_time: time
    timezone_gmt_offset: int = 7  # GMT+7 (Thailand)
    is_active: bool = True
    
    # ช่วงเวลาพิเศษ
    peak_hours: Optional[Tuple[time, time]] = None      # ช่วงเวลาที่เทรดหนักที่สุด
    quiet_hours: Optional[Tuple[time, time]] = None     # ช่วงเวลาเงียบ
    news_hours: List[time] = field(default_factory=list) # เวลาที่มักมีข่าวสำคัญ
    
    def is_session_active(self, current_time: datetime) -> bool:
        """ตรวจสอบว่า session นี้กำลัง active อยู่หรือไม่"""
        # แปลงเวลาปัจจุบันเป็น local time
        local_tz = pytz.timezone(f'Etc/GMT{-self.timezone_gmt_offset:+d}')
        local_time = current_time.astimezone(local_tz).time()
        
        if self.start_time <= self.end_time:
            # Session ไม่ข้ามวัน
            return self.start_time <= local_time <= self.end_time
        else:
            # Session ข้ามวัน (เช่น 22:00 - 08:00)
            return local_time >= self.start_time or local_time <= self.end_time
    
    def is_peak_hours(self, current_time: datetime) -> bool:
        """ตรวจสอบว่าอยู่ในช่วง peak hours หรือไม่"""
        if not self.peak_hours:
            return False
            
        local_tz = pytz.timezone(f'Etc/GMT{-self.timezone_gmt_offset:+d}')
        local_time = current_time.astimezone(local_tz).time()
        
        start_peak, end_peak = self.peak_hours
        if start_peak <= end_peak:
            return start_peak <= local_time <= end_peak
        else:
            return local_time >= start_peak or local_time <= end_peak

@dataclass
class SessionTradingProfile:
    """โปรไฟล์การเทรดสำหรับแต่ละ session"""
    
    # === GENERAL CHARACTERISTICS ===
    session_type: SessionType
    market_characteristics: List[MarketCharacteristic]
    average_volatility: str  # "LOW", "MEDIUM", "HIGH", "EXTREME"
    typical_spread: float    # Spread เฉลี่ย (pips)
    liquidity_level: str    # "LOW", "MEDIUM", "HIGH"
    
    # === TRADING BEHAVIOR ===
    preferred_strategies: List[str]          # กลยุทธ์ที่แนะนำ
    avoid_strategies: List[str] = field(default_factory=list)  # กลยุทธ์ที่ควรหลีกเลี่ยง
    recovery_method_preference: str = "GRID_INTELLIGENT"  # วิธี recovery ที่แนะนำ
    
    # === POSITION MANAGEMENT ===
    max_positions_per_hour: int = 30        # จำนวน position สูงสุดต่อชั่วโมง
    max_concurrent_positions: int = 10      # จำนวน position พร้อมกันสูงสุด
    position_hold_time_avg_minutes: int = 15  # เวลาถือ position เฉลี่ย
    
    # === LOT SIZING ===
    base_lot_multiplier: float = 1.0        # ตัวคูณ lot size พื้นฐาน
    volatility_lot_adjustment: float = 1.0  # ปรับ lot ตาม volatility
    max_lot_per_position: float = 1.0       # lot สูงสุดต่อ position
    
    # === RISK PARAMETERS ===
    spread_tolerance: float = 2.0           # Spread สูงสุดที่ยอมรับ (pips)
    slippage_expectation: float = 0.5       # Slippage ที่คาดหวัง (pips)
    news_impact_sensitivity: float = 1.0    # ความไวต่อข่าว (0.0-2.0)
    
    # === TIMING PARAMETERS ===
    entry_timing_precision: float = 1.0     # ความแม่นยำ timing (0.5=รวดเร็ว, 2.0=รอดู)
    exit_timing_aggressiveness: float = 1.0 # ความเร็วในการออก (0.5=ช้า, 2.0=เร็ว)
    
    def get_adjusted_lot_size(self, base_lot: float, current_volatility: float) -> float:
        """คำนวณขนาด lot ที่ปรับแล้วตาม session และ volatility"""
        adjusted_lot = base_lot * self.base_lot_multiplier
        
        # ปรับตาม volatility
        if current_volatility > 1.5:  # High volatility
            adjusted_lot *= 0.8
        elif current_volatility < 0.8:  # Low volatility  
            adjusted_lot *= 1.2
            
        return min(adjusted_lot, self.max_lot_per_position)
    
    def should_avoid_trading(self, current_spread: float, news_upcoming_minutes: int) -> bool:
        """ตรวจสอบว่าควรหลีกเลี่ยงการเทรดหรือไม่"""
        # หลีกเลี่ยงถ้า spread สูงเกินไป
        if current_spread > self.spread_tolerance:
            return True
            
        # หลีกเลี่ยงก่อนข่าวสำคัญ
        if news_upcoming_minutes <= 5 and self.news_impact_sensitivity > 1.0:
            return True
            
        return False

class SessionConfigManager:
    """ตัวจัดการการตั้งค่า session ทั้งหมด"""
    
    def __init__(self):
        self.sessions: Dict[SessionType, SessionTimeConfig] = {}
        self.trading_profiles: Dict[SessionType, SessionTradingProfile] = {}
        self.current_session: Optional[SessionType] = None
        self.session_transitions: List[Tuple[datetime, SessionType]] = []
        
        # ตั้งค่า sessions
        self._setup_default_sessions()
        self._setup_trading_profiles()
    
    def _setup_default_sessions(self):
        """ตั้งค่า session เริ่มต้นตาม GMT+7"""
        
        # ASIAN SESSION (22:00-08:00)
        self.sessions[SessionType.ASIAN] = SessionTimeConfig(
            name="Asian Session",
            start_time=time(22, 0),   # 22:00
            end_time=time(8, 0),      # 08:00
            peak_hours=(time(0, 0), time(4, 0)),  # 00:00-04:00
            quiet_hours=(time(4, 0), time(8, 0)), # 04:00-08:00
            news_hours=[time(9, 30), time(10, 0)] # ข่าวญี่ปุ่น, จีน
        )
        
        # LONDON SESSION (15:00-00:00)
        self.sessions[SessionType.LONDON] = SessionTimeConfig(
            name="London Session", 
            start_time=time(15, 0),   # 15:00
            end_time=time(0, 0),      # 00:00
            peak_hours=(time(16, 0), time(19, 0)),  # 16:00-19:00
            news_hours=[time(16, 30), time(18, 0)]  # ข่าวยุโรป
        )
        
        # NEW YORK SESSION (20:30-05:30)
        self.sessions[SessionType.NEW_YORK] = SessionTimeConfig(
            name="New York Session",
            start_time=time(20, 30),  # 20:30
            end_time=time(5, 30),     # 05:30
            peak_hours=(time(21, 0), time(1, 0)),   # 21:00-01:00
            news_hours=[time(21, 30), time(23, 0)]  # ข่าวสหรัฐฯ
        )
        
        # OVERLAP SESSION (20:30-00:00) - London/NY Overlap
        self.sessions[SessionType.OVERLAP_LONDON_NY] = SessionTimeConfig(
            name="London-NY Overlap",
            start_time=time(20, 30),  # 20:30
            end_time=time(0, 0),      # 00:00
            peak_hours=(time(21, 0), time(23, 0)),   # 21:00-23:00
            news_hours=[time(21, 30), time(22, 30)]  # ข่าวทั้งสองตลาด
        )
        
        # QUIET HOURS (08:00-15:00)
        self.sessions[SessionType.QUIET_HOURS] = SessionTimeConfig(
            name="Quiet Hours",
            start_time=time(8, 0),    # 08:00
            end_time=time(15, 0),     # 15:00
            is_active=False  # ไม่เทรดในช่วงนี้โดยปกติ
        )
    
    def _setup_trading_profiles(self):
        """ตั้งค่า trading profile สำหรับแต่ละ session"""
        
        # === ASIAN SESSION PROFILE ===
        self.trading_profiles[SessionType.ASIAN] = SessionTradingProfile(
            session_type=SessionType.ASIAN,
            market_characteristics=[
                MarketCharacteristic.LOW_VOLATILITY,
                MarketCharacteristic.RANGING,
                MarketCharacteristic.TECHNICAL_DRIVEN
            ],
            average_volatility="LOW",
            typical_spread=1.8,
            liquidity_level="MEDIUM",
            preferred_strategies=[
                "MEAN_REVERSION",
                "SCALPING_ENGINE", 
                "GRID_INTELLIGENT"
            ],
            avoid_strategies=[
                "BREAKOUT_FALSE",
                "NEWS_REACTION"
            ],
            recovery_method_preference="AVERAGING_INTELLIGENT",
            max_positions_per_hour=20,
            max_concurrent_positions=8,
            position_hold_time_avg_minutes=25,
            base_lot_multiplier=0.8,
            spread_tolerance=2.5,
            news_impact_sensitivity=0.6
        )
        
        # === LONDON SESSION PROFILE ===
        self.trading_profiles[SessionType.LONDON] = SessionTradingProfile(
            session_type=SessionType.LONDON,
            market_characteristics=[
                MarketCharacteristic.HIGH_VOLATILITY,
                MarketCharacteristic.TRENDING,
                MarketCharacteristic.NEWS_DRIVEN
            ],
            average_volatility="HIGH",
            typical_spread=1.2,
            liquidity_level="HIGH",
            preferred_strategies=[
                "TREND_FOLLOWING",
                "BREAKOUT_FALSE",
                "NEWS_REACTION"
            ],
            avoid_strategies=[
                "SCALPING_ENGINE"
            ],
            recovery_method_preference="GRID_INTELLIGENT",
            max_positions_per_hour=40,
            max_concurrent_positions=15,
            position_hold_time_avg_minutes=12,
            base_lot_multiplier=1.2,
            spread_tolerance=2.0,
            news_impact_sensitivity=1.2
        )
        
        # === NEW YORK SESSION PROFILE ===
        self.trading_profiles[SessionType.NEW_YORK] = SessionTradingProfile(
            session_type=SessionType.NEW_YORK,
            market_characteristics=[
                MarketCharacteristic.HIGH_VOLATILITY,
                MarketCharacteristic.NEWS_DRIVEN,
                MarketCharacteristic.TRENDING
            ],
            average_volatility="HIGH",
            typical_spread=1.0,
            liquidity_level="HIGH",
            preferred_strategies=[
                "NEWS_REACTION",
                "TREND_FOLLOWING",
                "BREAKOUT_FALSE"
            ],
            avoid_strategies=[],
            recovery_method_preference="HEDGING_ADVANCED",
            max_positions_per_hour=50,
            max_concurrent_positions=18,
            position_hold_time_avg_minutes=10,
            base_lot_multiplier=1.0,
            spread_tolerance=1.5,
            news_impact_sensitivity=1.5
        )
        
        # === OVERLAP SESSION PROFILE ===
        self.trading_profiles[SessionType.OVERLAP_LONDON_NY] = SessionTradingProfile(
            session_type=SessionType.OVERLAP_LONDON_NY,
            market_characteristics=[
                MarketCharacteristic.HIGH_VOLATILITY,
                MarketCharacteristic.NEWS_DRIVEN,
                MarketCharacteristic.TRENDING
            ],
            average_volatility="EXTREME",
            typical_spread=0.8,
            liquidity_level="HIGH",
            preferred_strategies=[
                "BREAKOUT_FALSE",
                "NEWS_REACTION",
                "SCALPING_ENGINE",
                "TREND_FOLLOWING"
            ],
            avoid_strategies=[],
            recovery_method_preference="MARTINGALE_SMART",
            max_positions_per_hour=60,
            max_concurrent_positions=20,
            position_hold_time_avg_minutes=8,
            base_lot_multiplier=1.5,
            spread_tolerance=1.0,
            news_impact_sensitivity=2.0,
            entry_timing_precision=0.8,      # เร็วขึ้น
            exit_timing_aggressiveness=1.5   # aggressive ขึ้น
        )
    
    def get_current_session(self, current_time: Optional[datetime] = None) -> Optional[SessionType]:
        """หา session ปัจจุบัน"""
        if current_time is None:
            current_time = datetime.now()
        
        # ตรวจสอบ overlap session ก่อน (มีความสำคัญสูงกว่า)
        if self.sessions[SessionType.OVERLAP_LONDON_NY].is_session_active(current_time):
            return SessionType.OVERLAP_LONDON_NY
        
        # ตรวจสอบ session อื่นๆ
        for session_type, session_config in self.sessions.items():
            if session_type == SessionType.OVERLAP_LONDON_NY:
                continue  # ตรวจแล้วข้างบน
                
            if session_config.is_session_active(current_time):
                return session_type
        
        # ถ้าไม่อยู่ใน session ใดเลย ให้ return QUIET_HOURS
        return SessionType.QUIET_HOURS
    
    def get_session_profile(self, session_type: Optional[SessionType] = None) -> Optional[SessionTradingProfile]:
        """ดึง trading profile สำหรับ session"""
        if session_type is None:
            session_type = self.get_current_session()
        
        return self.trading_profiles.get(session_type)
    
    def get_next_session_change(self, current_time: Optional[datetime] = None) -> Optional[Tuple[datetime, SessionType]]:
        """หาเวลาที่ session จะเปลี่ยนครั้งถัดไป"""
        if current_time is None:
            current_time = datetime.now()
        
        # สร้างรายการเวลาเปลี่ยน session สำหรับ 24 ชั่วโมงข้างหน้า
        session_changes = []
        
        for i in range(24):  # ตรวจ 24 ชั่วโมงข้างหน้า
            check_time = current_time + timedelta(hours=i)
            
            for session_type, session_config in self.sessions.items():
                # ตรวจสอบเวลาเริ่มต้น session
                start_datetime = check_time.replace(
                    hour=session_config.start_time.hour,
                    minute=session_config.start_time.minute,
                    second=0,
                    microsecond=0
                )
                
                if start_datetime > current_time:
                    session_changes.append((start_datetime, session_type))
        
        # เรียงตามเวลาและส่งคืนอันแรก
        session_changes.sort(key=lambda x: x[0])
        return session_changes[0] if session_changes else None
    
    def is_news_time(self, current_time: Optional[datetime] = None, 
                     window_minutes: int = 30) -> Tuple[bool, List[time]]:
        """ตรวจสอบว่าใกล้เวลาข่าวหรือไม่"""
        if current_time is None:
            current_time = datetime.now()
        
        current_session = self.get_current_session(current_time)
        if not current_session or current_session not in self.sessions:
            return False, []
        
        session_config = self.sessions[current_session]
        current_time_only = current_time.time()
        
        upcoming_news = []
        for news_time in session_config.news_hours:
            # คำนวณช่วงเวลาก่อนข่าว
            news_datetime = current_time.replace(
                hour=news_time.hour,
                minute=news_time.minute,
                second=0,
                microsecond=0
            )
            
            time_diff = (news_datetime - current_time).total_seconds() / 60
            
            if 0 <= time_diff <= window_minutes:
                upcoming_news.append(news_time)
        
        return len(upcoming_news) > 0, upcoming_news
    
    def get_session_statistics(self, session_type: SessionType, 
                             start_date: datetime, end_date: datetime) -> Dict:
        """ดึงสถิติการเทรดของ session"""
        # TODO: Implement session statistics calculation
        # จะเชื่อมต่อกับ analytics_engine/performance_tracker.py
        
        return {
            "session_type": session_type.value,
            "total_trading_hours": 0,
            "average_positions_per_hour": 0,
            "average_profit_per_hour": 0,
            "recovery_success_rate": 0,
            "most_successful_strategy": "",
            "average_position_hold_time": 0
        }
    
    def optimize_session_parameters(self, session_type: SessionType, 
                                   performance_data: Dict) -> SessionTradingProfile:
        """ปรับแต่งพารามิเตอร์ session ตามผลการดำเนินงาน"""
        current_profile = self.trading_profiles[session_type]
        
        # สร้าง optimized profile
        optimized_profile = SessionTradingProfile(
            session_type=current_profile.session_type,
            market_characteristics=current_profile.market_characteristics,
            average_volatility=current_profile.average_volatility,
            typical_spread=current_profile.typical_spread,
            liquidity_level=current_profile.liquidity_level,
            preferred_strategies=current_profile.preferred_strategies.copy(),
            avoid_strategies=current_profile.avoid_strategies.copy(),
            recovery_method_preference=current_profile.recovery_method_preference,
            max_positions_per_hour=current_profile.max_positions_per_hour,
            max_concurrent_positions=current_profile.max_concurrent_positions,
            position_hold_time_avg_minutes=current_profile.position_hold_time_avg_minutes,
            base_lot_multiplier=current_profile.base_lot_multiplier,
            spread_tolerance=current_profile.spread_tolerance,
            news_impact_sensitivity=current_profile.news_impact_sensitivity
        )
        
        # ปรับแต่งตามผลการดำเนินงาน
        if performance_data.get("success_rate", 0) < 0.7:
            # ลดความเสี่ยงถ้าผลงานไม่ดี
            optimized_profile.base_lot_multiplier *= 0.9
            optimized_profile.max_positions_per_hour = int(
                optimized_profile.max_positions_per_hour * 0.8
            )
        elif performance_data.get("success_rate", 0) > 0.85:
            # เพิ่มความเสี่ยงถ้าผลงานดี
            optimized_profile.base_lot_multiplier *= 1.1
            optimized_profile.max_positions_per_hour = int(
                optimized_profile.max_positions_per_hour * 1.2
            )
        
        return optimized_profile

# === SPECIALIZED SESSION FUNCTIONS ===

def get_session_overlap_periods() -> List[Tuple[SessionType, SessionType, time, time]]:
    """ดึงช่วงเวลาที่ session ทับซ้อนกัน"""
    overlaps = [
        # London-NY Overlap
        (SessionType.LONDON, SessionType.NEW_YORK, time(20, 30), time(0, 0)),
        # Asian-London Mini Overlap (ไม่ค่อยสำคัญ)
        # (SessionType.ASIAN, SessionType.LONDON, time(15, 0), time(16, 0))
    ]
    return overlaps

def calculate_session_volume_distribution() -> Dict[SessionType, float]:
    """คำนวณการกระจายปริมาณการเทรดในแต่ละ session"""
    return {
        SessionType.ASIAN: 0.20,           # 20% ของปริมาณรวม
        SessionType.LONDON: 0.35,          # 35% ของปริมาณรวม
        SessionType.NEW_YORK: 0.30,        # 30% ของปริมาณรวม
        SessionType.OVERLAP_LONDON_NY: 0.15 # 15% ของปริมาณรวม (นับเป็นส่วนเพิ่ม)
    }

def get_session_news_schedule() -> Dict[SessionType, List[Tuple[time, str, str]]]:
    """ดึงตารางข่าวสำคัญในแต่ละ session"""
    return {
        SessionType.ASIAN: [
            (time(9, 30), "JPY", "Tokyo CPI"),
            (time(10, 0), "CNY", "China PMI"),
            (time(11, 0), "AUD", "RBA Rate Decision")
        ],
        SessionType.LONDON: [
            (time(16, 30), "EUR", "ECB Rate Decision"),
            (time(17, 0), "GBP", "BOE Rate Decision"),
            (time(18, 0), "EUR", "German IFO")
        ],
        SessionType.NEW_YORK: [
            (time(21, 30), "USD", "FOMC Rate Decision"),
            (time(22, 30), "USD", "NFP Release"),
            (time(23, 0), "USD", "CPI Data")
        ]
    }

# === GLOBAL SESSION MANAGER ===
_global_session_manager: Optional[SessionConfigManager] = None

def get_session_manager() -> SessionConfigManager:
    """ดึง Session Manager แบบ Singleton"""
    global _global_session_manager
    if _global_session_manager is None:
        _global_session_manager = SessionConfigManager()
    return _global_session_manager

def get_current_trading_profile() -> Optional[SessionTradingProfile]:
    """ดึง trading profile ปัจจุบัน"""
    manager = get_session_manager()
    return manager.get_session_profile()

def is_high_impact_time(current_time: Optional[datetime] = None) -> bool:
    """ตรวจสอบว่าเป็นช่วงเวลาที่มีผลกระทบสูงหรือไม่"""
    manager = get_session_manager()
    is_news, _ = manager.is_news_time(current_time, window_minutes=15)
    
    current_session = manager.get_current_session(current_time)
    if current_session == SessionType.OVERLAP_LONDON_NY:
        return True
    
    return is_news

def should_increase_trading_activity(current_time: Optional[datetime] = None) -> bool:
    """ตรวจสอบว่าควรเพิ่มกิจกรรมการเทรดหรือไม่"""
    manager = get_session_manager()
    current_session = manager.get_current_session(current_time)
    
    # เพิ่มกิจกรรมใน high liquidity sessions
    high_activity_sessions = [
        SessionType.LONDON,
        SessionType.NEW_YORK,
        SessionType.OVERLAP_LONDON_NY
    ]
    
    return current_session in high_activity_sessions

def get_recommended_strategies_for_current_session() -> List[str]:
    """ดึงกลยุทธ์ที่แนะนำสำหรับ session ปัจจุบัน"""
    profile = get_current_trading_profile()
    if not profile:
        return ["MEAN_REVERSION"]  # default strategy
    
    return profile.preferred_strategies