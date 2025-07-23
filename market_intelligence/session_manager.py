# market_intelligence/session_manager.py - Trading Session Management System

import numpy as np
import pandas as pd
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import pytz

class TradingSession(Enum):
    """📅 เซสชั่นการเทรด"""
    ASIAN = "asian"         # เอเชีย
    LONDON = "london"       # ลอนดอน
    NY = "ny"              # นิวยอร์ก
    OVERLAP = "overlap"     # ซ้อนทับ
    QUIET = "quiet"        # เงียบ

class SessionCharacteristic(Enum):
    """📊 ลักษณะของเซสชั่น"""
    LOW_VOLATILITY = "low_volatility"
    HIGH_VOLATILITY = "high_volatility"
    TRENDING = "trending"
    RANGING = "ranging"
    HIGH_VOLUME = "high_volume"
    LOW_VOLUME = "low_volume"

@dataclass
class SessionInfo:
    """ℹ️ ข้อมูลเซสชั่น"""
    session: TradingSession
    start_time: time
    end_time: time
    timezone: str
    characteristics: List[SessionCharacteristic]
    volatility_multiplier: float
    volume_multiplier: float
    spread_multiplier: float
    optimal_strategies: List[str]

@dataclass
class SessionAnalysis:
    """📈 ผลการวิเคราะห์เซสชั่น"""
    current_session: TradingSession
    next_session: TradingSession
    time_to_next_session: timedelta
    session_progress: float  # 0.0 - 1.0
    volatility_expected: str  # "low", "medium", "high"
    volume_expected: str     # "low", "medium", "high"
    optimal_entry_methods: List[str]
    optimal_recovery_methods: List[str]
    risk_level: str         # "low", "medium", "high"
    confidence: float

class SessionManager:
    """
    🌍 Trading Session Manager - เซสชั่นและการปรับกลยุทธ์
    
    ⚡ หน้าที่หลัก:
    - ติดตามเซสชั่นปัจจุบันและถัดไป
    - ปรับพารามิเตอร์ตามลักษณะของเซสชั่น
    - แนะนำกลยุทธ์ที่เหมาะสมสำหรับแต่ละเซสชั่น
    - วิเคราะห์ความผันผวนตามเวลา
    - จัดการ timezone และเวลาท้องถิ่น
    
    🎯 เซสชั่นต่างๆ (GMT+7):
    - Asian: 22:00-08:00 (ความผันผวนต่ำ, เหมาะ Mean Reversion)
    - London: 15:00-00:00 (ความผันผวนสูง, เหมาะ Trend Following) 
    - NY: 20:30-05:30 (ปริมาณสูง, เหมาะ Breakout)
    - Overlap: 20:30-00:00 (โอกาสสูงสุด, เหมาะ Grid/False Breakout)
    """
    
    def __init__(self, config: Dict):
        print("🌍 Initializing Trading Session Manager...")
        
        self.config = config
        
        # Timezone setup
        self.local_timezone = config.get('local_timezone', 'Asia/Bangkok')  # GMT+7
        self.broker_timezone = config.get('broker_timezone', 'Europe/London')
        
        # Session definitions (in local time GMT+7)
        self.session_definitions = self._define_trading_sessions()
        
        # Current state
        self.current_session_info = None
        self.last_analysis_time = None
        self.session_change_callbacks = []
        
        # Session statistics
        self.session_stats = {}  # session -> statistics
        self.session_history = []
        
        # Market hours and holidays
        self.market_holidays = config.get('market_holidays', [])
        self.weekend_trading = config.get('weekend_trading', False)
        
        print("✅ Trading Session Manager initialized")
        print(f"   - Local Timezone: {self.local_timezone}")
        print(f"   - Sessions Defined: {len(self.session_definitions)}")
    
    def _define_trading_sessions(self) -> Dict[TradingSession, SessionInfo]:
        """กำหนดข้อมูลเซสชั่นการเทรด"""
        try:
            sessions = {}
            
            # Asian Session (Tokyo + Sydney)
            sessions[TradingSession.ASIAN] = SessionInfo(
                session=TradingSession.ASIAN,
                start_time=time(22, 0),  # 22:00 GMT+7
                end_time=time(8, 0),     # 08:00 GMT+7 (next day)
                timezone=self.local_timezone,
                characteristics=[
                    SessionCharacteristic.LOW_VOLATILITY,
                    SessionCharacteristic.RANGING,
                    SessionCharacteristic.LOW_VOLUME
                ],
                volatility_multiplier=0.7,
                volume_multiplier=0.6,
                spread_multiplier=1.2,
                optimal_strategies=["mean_reversion", "martingale_smart", "scalping"]
            )
            
            # London Session
            sessions[TradingSession.LONDON] = SessionInfo(
                session=TradingSession.LONDON,
                start_time=time(15, 0),  # 15:00 GMT+7
                end_time=time(0, 0),     # 00:00 GMT+7 (next day)
                timezone=self.local_timezone,
                characteristics=[
                    SessionCharacteristic.HIGH_VOLATILITY,
                    SessionCharacteristic.TRENDING,
                    SessionCharacteristic.HIGH_VOLUME
                ],
                volatility_multiplier=1.4,
                volume_multiplier=1.3,
                spread_multiplier=0.8,
                optimal_strategies=["trend_following", "grid_intelligent", "breakout"]
            )
            
            # New York Session
            sessions[TradingSession.NY] = SessionInfo(
                session=TradingSession.NY,
                start_time=time(20, 30),  # 20:30 GMT+7
                end_time=time(5, 30),     # 05:30 GMT+7 (next day)
                timezone=self.local_timezone,
                characteristics=[
                    SessionCharacteristic.HIGH_VOLATILITY,
                    SessionCharacteristic.TRENDING,
                    SessionCharacteristic.HIGH_VOLUME
                ],
                volatility_multiplier=1.5,
                volume_multiplier=1.5,
                spread_multiplier=0.7,
                optimal_strategies=["trend_following", "news_reaction", "breakout"]
            )
            
            # Overlap Session (London + NY)
            sessions[TradingSession.OVERLAP] = SessionInfo(
                session=TradingSession.OVERLAP,
                start_time=time(20, 30),  # 20:30 GMT+7
                end_time=time(0, 0),      # 00:00 GMT+7 (next day)
                timezone=self.local_timezone,
                characteristics=[
                    SessionCharacteristic.HIGH_VOLATILITY,
                    SessionCharacteristic.TRENDING,
                    SessionCharacteristic.HIGH_VOLUME
                ],
                volatility_multiplier=1.8,
                volume_multiplier=2.0,
                spread_multiplier=0.6,
                optimal_strategies=["grid_intelligent", "false_breakout", "hedging"]
            )
            
            # Quiet Session (between major sessions)
            sessions[TradingSession.QUIET] = SessionInfo(
                session=TradingSession.QUIET,
                start_time=time(8, 0),   # 08:00 GMT+7
                end_time=time(15, 0),    # 15:00 GMT+7
                timezone=self.local_timezone,
                characteristics=[
                    SessionCharacteristic.LOW_VOLATILITY,
                    SessionCharacteristic.RANGING,
                    SessionCharacteristic.LOW_VOLUME
                ],
                volatility_multiplier=0.5,
                volume_multiplier=0.4,
                spread_multiplier=1.5,
                optimal_strategies=["mean_reversion", "scalping"]
            )
            
            return sessions
            
        except Exception as e:
            print(f"❌ Session definition error: {e}")
            return {}
    
    def get_current_session(self, current_time: Optional[datetime] = None) -> SessionAnalysis:
        """
        🕐 ดึงข้อมูลเซสชั่นปัจจุบัน
        
        Args:
            current_time: เวลาปัจจุบัน (ถ้าไม่ระบุจะใช้เวลาปัจจุบัน)
            
        Returns:
            SessionAnalysis object
        """
        try:
            if current_time is None:
                current_time = datetime.now()
            
            # แปลงเป็น local timezone
            if current_time.tzinfo is None:
                local_tz = pytz.timezone(self.local_timezone)
                current_time = local_tz.localize(current_time)
            
            current_time_local = current_time.astimezone(pytz.timezone(self.local_timezone))
            current_time_only = current_time_local.time()
            
            # หาเซสชั่นปัจจุบัน
            current_session = self._identify_current_session(current_time_only)
            
            # หาเซสชั่นถัดไป
            next_session = self._identify_next_session(current_session, current_time_local)
            
            # คำนวณเวลาถึงเซสชั่นถัดไป
            time_to_next = self._calculate_time_to_next_session(current_session, next_session, current_time_local)
            
            # คำนวณความคืบหน้าของเซสชั่นปัจจุบัน
            session_progress = self._calculate_session_progress(current_session, current_time_only)
            
            # วิเคราะห์ความผันผวนและปริมาณที่คาดหวัง
            volatility_expected = self._predict_volatility(current_session, session_progress)
            volume_expected = self._predict_volume(current_session, session_progress)
            
            # แนะนำวิธี entry และ recovery
            optimal_entry_methods = self._recommend_entry_methods(current_session)
            optimal_recovery_methods = self._recommend_recovery_methods(current_session)
            
            # ประเมินระดับความเสี่ยง
            risk_level = self._assess_session_risk(current_session, session_progress)
            
            # คำนวณความเชื่อมั่น
            confidence = self._calculate_session_confidence(current_session, current_time_local)
            
            analysis = SessionAnalysis(
                current_session=current_session,
                next_session=next_session,
                time_to_next_session=time_to_next,
                session_progress=session_progress,
                volatility_expected=volatility_expected,
                volume_expected=volume_expected,
                optimal_entry_methods=optimal_entry_methods,
                optimal_recovery_methods=optimal_recovery_methods,
                risk_level=risk_level,
                confidence=confidence
            )
            
            # Cache analysis
            self.current_session_info = analysis
            self.last_analysis_time = current_time
            
            return analysis
            
        except Exception as e:
            print(f"❌ Current session analysis error: {e}")
            return self._create_default_analysis()
    
    def _identify_current_session(self, current_time: time) -> TradingSession:
        """ระบุเซสชั่นปัจจุบัน"""
        try:
            # ตรวจสอบ Overlap session ก่อน (มีความสำคัญสูงสุด)
            overlap_info = self.session_definitions[TradingSession.OVERLAP]
            if self._is_time_in_session(current_time, overlap_info.start_time, overlap_info.end_time):
                return TradingSession.OVERLAP
            
            # ตรวจสอบเซสชั่นอื่นๆ
            for session, info in self.session_definitions.items():
                if session == TradingSession.OVERLAP:
                    continue  # ตรวจแล้ว
                
                if self._is_time_in_session(current_time, info.start_time, info.end_time):
                    return session
            
            # ถ้าไม่อยู่ในเซสชั่นไหน ให้เป็น QUIET
            return TradingSession.QUIET
            
        except Exception as e:
            print(f"❌ Session identification error: {e}")
            return TradingSession.QUIET
    
    def _is_time_in_session(self, current_time: time, start_time: time, end_time: time) -> bool:
        """ตรวจสอบว่าเวลาอยู่ในเซสชั่นหรือไม่"""
        try:
            if start_time <= end_time:
                # เซสชั่นไม่ข้ามวัน
                return start_time <= current_time <= end_time
            else:
                # เซสชั่นข้ามวัน (เช่น 22:00 - 08:00)
                return current_time >= start_time or current_time <= end_time
                
        except Exception as e:
            print(f"❌ Time in session check error: {e}")
            return False
    
    def _identify_next_session(self, current_session: TradingSession, current_time: datetime) -> TradingSession:
        """ระบุเซสชั่นถัดไป"""
        try:
            session_order = [
                TradingSession.QUIET,
                TradingSession.LONDON,
                TradingSession.OVERLAP,
                TradingSession.NY,
                TradingSession.ASIAN
            ]
            
            try:
                current_index = session_order.index(current_session)
                next_index = (current_index + 1) % len(session_order)
                return session_order[next_index]
            except ValueError:
                # ถ้าไม่เจอใน order ให้ใช้ logic อื่น
                if current_session == TradingSession.OVERLAP:
                    return TradingSession.NY
                else:
                    return TradingSession.QUIET
                    
        except Exception as e:
            print(f"❌ Next session identification error: {e}")
            return TradingSession.QUIET
    
    def _calculate_time_to_next_session(self, current_session: TradingSession, 
                                      next_session: TradingSession, current_time: datetime) -> timedelta:
        """คำนวณเวลาถึงเซสชั่นถัดไป"""
        try:
            current_info = self.session_definitions[current_session]
            next_info = self.session_definitions[next_session]
            
            current_time_only = current_time.time()
            
            # หาเวลาสิ้นสุดของเซสชั่นปัจจุบัน
            end_time = current_info.end_time
            
            # คำนวณเวลาที่เหลือ
            if end_time > current_time_only:
                # เซสชั่นสิ้นสุดวันเดียวกัน
                end_datetime = current_time.replace(
                    hour=end_time.hour, 
                    minute=end_time.minute, 
                    second=0, 
                    microsecond=0
                )
            else:
                # เซสชั่นสิ้นสุดวันถัดไป
                end_datetime = current_time.replace(
                    hour=end_time.hour, 
                    minute=end_time.minute, 
                    second=0, 
                    microsecond=0
                ) + timedelta(days=1)
            
            time_to_end = end_datetime - current_time
            
            return time_to_end
            
        except Exception as e:
            print(f"❌ Time to next session calculation error: {e}")
            return timedelta(hours=1)
    
    def _calculate_session_progress(self, session: TradingSession, current_time: time) -> float:
        """คำนวณความคืบหน้าของเซสชั่น (0.0 - 1.0)"""
        try:
            session_info = self.session_definitions[session]
            start_time = session_info.start_time
            end_time = session_info.end_time
            
            # แปลงเป็นนาทีตั้งแต่เที่ยงคืน
            start_minutes = start_time.hour * 60 + start_time.minute
            current_minutes = current_time.hour * 60 + current_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute
            
            # จัดการเซสชั่นข้ามวัน
            if start_time > end_time:
                if current_time >= start_time:
                    # ยังอยู่วันเดียวกัน
                    session_length = (24 * 60) - start_minutes + end_minutes
                    current_progress = current_minutes - start_minutes
                else:
                    # ข้ามไปวันถัดไปแล้ว
                    session_length = (24 * 60) - start_minutes + end_minutes
                    current_progress = (24 * 60) - start_minutes + current_minutes
            else:
                # เซสชั่นไม่ข้ามวัน
                session_length = end_minutes - start_minutes
                current_progress = current_minutes - start_minutes
            
            progress = current_progress / session_length if session_length > 0 else 0.0
            return max(0.0, min(progress, 1.0))
            
        except Exception as e:
            print(f"❌ Session progress calculation error: {e}")
            return 0.5
    
    def _predict_volatility(self, session: TradingSession, progress: float) -> str:
        """คาดการณ์ความผันผวน"""
        try:
            session_info = self.session_definitions[session]
            base_volatility = session_info.volatility_multiplier
            
            # ปรับตามความคืบหน้าของเซสชั่น
            if session in [TradingSession.LONDON, TradingSession.NY, TradingSession.OVERLAP]:
                # เซสชั่นหลัก - ความผันผวนสูงในช่วงแรกและกลาง
                if progress < 0.3 or 0.4 < progress < 0.7:
                    adjusted_volatility = base_volatility * 1.2
                else:
                    adjusted_volatility = base_volatility * 0.9
            else:
                # เซสชั่นรอง - ความผันผวนค่อนข้างคงที่
                adjusted_volatility = base_volatility
            
            # จำแนกระดับ
            if adjusted_volatility >= 1.4:
                return "high"
            elif adjusted_volatility >= 1.0:
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            print(f"❌ Volatility prediction error: {e}")
            return "medium"
    
    def _predict_volume(self, session: TradingSession, progress: float) -> str:
        """คาดการณ์ปริมาณการเทรด"""
        try:
            session_info = self.session_definitions[session]
            base_volume = session_info.volume_multiplier
            
            # ปรับตามความคืบหน้า
            if session in [TradingSession.LONDON, TradingSession.NY, TradingSession.OVERLAP]:
                # ปริมาณสูงในช่วงเปิดและก่อนปิด
                if progress < 0.2 or progress > 0.8:
                    adjusted_volume = base_volume * 1.3
                else:
                    adjusted_volume = base_volume
            else:
                adjusted_volume = base_volume
            
            # จำแนกระดับ
            if adjusted_volume >= 1.5:
                return "high"
            elif adjusted_volume >= 1.0:
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            print(f"❌ Volume prediction error: {e}")
            return "medium"
    
    def _recommend_entry_methods(self, session: TradingSession) -> List[str]:
        """แนะนำวิธี entry ที่เหมาะสม"""
        try:
            session_info = self.session_definitions[session]
            return session_info.optimal_strategies.copy()
            
        except Exception as e:
            print(f"❌ Entry methods recommendation error: {e}")
            return ["mean_reversion"]
    
    def _recommend_recovery_methods(self, session: TradingSession) -> List[str]:
        """แนะนำวิธี recovery ที่เหมาะสม"""
        try:
            recovery_mapping = {
                TradingSession.ASIAN: ["martingale_smart", "averaging"],
                TradingSession.LONDON: ["grid_intelligent", "hedging"],
                TradingSession.NY: ["grid_intelligent", "trend_recovery"],
                TradingSession.OVERLAP: ["hedging", "correlation_recovery"],
                TradingSession.QUIET: ["martingale_smart", "averaging"]
            }
            
            return recovery_mapping.get(session, ["martingale_smart"])
            
        except Exception as e:
            print(f"❌ Recovery methods recommendation error: {e}")
            return ["martingale_smart"]
    
    def _assess_session_risk(self, session: TradingSession, progress: float) -> str:
        """ประเมินระดับความเสี่ยงของเซสชั่น"""
        try:
            session_info = self.session_definitions[session]
            
            # ความเสี่ยงพื้นฐานตามเซสชั่น
            base_risk = {
                TradingSession.ASIAN: "low",
                TradingSession.LONDON: "medium",
                TradingSession.NY: "medium", 
                TradingSession.OVERLAP: "high",
                TradingSession.QUIET: "low"
            }
            
            risk = base_risk.get(session, "medium")
            
            # ปรับตามความคืบหน้า
            if session == TradingSession.OVERLAP:
                if 0.3 < progress < 0.7:  # ช่วงกลางของ overlap
                    risk = "high"
                else:
                    risk = "medium"
            
            return risk
            
        except Exception as e:
            print(f"❌ Session risk assessment error: {e}")
            return "medium"
    
    def _calculate_session_confidence(self, session: TradingSession, current_time: datetime) -> float:
        """คำนวณความเชื่อมั่นในการวิเคราะห์เซสชั่น"""
        try:
            confidence = 0.8  # base confidence
            
            # ปรับตามประวัติการทำงานของเซสชั่น
            if session in self.session_stats:
                stats = self.session_stats[session]
                success_rate = stats.get('success_rate', 0.5)
                confidence += (success_rate - 0.5) * 0.4  # ปรับได้สูงสุด ±0.2
            
            # ปรับตามวันในสัปดาห์
            weekday = current_time.weekday()  # 0=Monday, 6=Sunday
            if weekday < 5:  # จันทร์-ศุกร์
                confidence += 0.1
            else:  # เสาร์-อาทิตย์
                confidence -= 0.2
            
            # ปรับตามเทศกาลหรือวันหยุด
            if self._is_holiday(current_time):
                confidence -= 0.3
            
            return max(0.1, min(confidence, 0.95))
            
        except Exception as e:
            print(f"❌ Session confidence calculation error: {e}")
            return 0.7
    
    def _is_holiday(self, current_time: datetime) -> bool:
        """ตรวจสอบว่าเป็นวันหยุดหรือไม่"""
        try:
            date_str = current_time.strftime("%Y-%m-%d")
            return date_str in self.market_holidays
            
        except Exception as e:
            print(f"❌ Holiday check error: {e}")
            return False
    
    def _create_default_analysis(self) -> SessionAnalysis:
        """สร้าง analysis เริ่มต้นเมื่อเกิดข้อผิดพลาด"""
        return SessionAnalysis(
            current_session=TradingSession.QUIET,
            next_session=TradingSession.LONDON,
            time_to_next_session=timedelta(hours=1),
            session_progress=0.5,
            volatility_expected="medium",
            volume_expected="medium",
            optimal_entry_methods=["mean_reversion"],
            optimal_recovery_methods=["martingale_smart"],
            risk_level="medium",
            confidence=0.5
        )
    
    def get_session_multipliers(self, session: Optional[TradingSession] = None) -> Dict[str, float]:
        """
        📊 ดึงตัวคูณสำหรับเซสชั่น
        
        Args:
            session: เซสชั่นที่ต้องการ (ถ้าไม่ระบุจะใช้เซสชั่นปัจจุบัน)
            
        Returns:
            Dictionary ของตัวคูณต่างๆ
        """
        try:
            if session is None:
                analysis = self.get_current_session()
                session = analysis.current_session
            
            session_info = self.session_definitions[session]
            
            return {
                'volatility_multiplier': session_info.volatility_multiplier,
                'volume_multiplier': session_info.volume_multiplier,
                'spread_multiplier': session_info.spread_multiplier,
                'entry_frequency_multiplier': session_info.volume_multiplier * 0.8,
                'recovery_aggressiveness': session_info.volatility_multiplier * 0.7,
                'lot_size_multiplier': session_info.volume_multiplier * 0.6
            }
            
        except Exception as e:
            print(f"❌ Session multipliers error: {e}")
            return {
                'volatility_multiplier': 1.0,
                'volume_multiplier': 1.0,
                'spread_multiplier': 1.0,
                'entry_frequency_multiplier': 1.0,
                'recovery_aggressiveness': 1.0,
                'lot_size_multiplier': 1.0
            }
    
    def update_session_statistics(self, session_results: Dict):
        """
        📈 อัปเดตสถิติการทำงานของเซสชั่น
        
        Args:
            session_results: ผลการทำงานของเซสชั่น
        """
        try:
            session = session_results.get('session')
            if not session:
                return
            
            if session not in self.session_stats:
                self.session_stats[session] = {
                    'total_trades': 0,
                    'successful_trades': 0,
                    'total_profit': 0.0,
                    'success_rate': 0.0,
                    'avg_profit': 0.0,
                    'last_updated': datetime.now()
                }
            
            stats = self.session_stats[session]
            
            # อัปเดตสถิติ
            stats['total_trades'] += session_results.get('trades_count', 0)
            stats['successful_trades'] += session_results.get('successful_trades', 0)
            stats['total_profit'] += session_results.get('profit', 0.0)
            
            # คำนวณอัตราความสำเร็จ
            if stats['total_trades'] > 0:
                stats['success_rate'] = stats['successful_trades'] / stats['total_trades']
                stats['avg_profit'] = stats['total_profit'] / stats['total_trades']
            
            stats['last_updated'] = datetime.now()
            
            # บันทึกประวัติ
            self.session_history.append({
                'timestamp': datetime.now(),
                'session': session,
                'results': session_results
            })
            
            # จำกัดประวัติ
            if len(self.session_history) > 1000:
                self.session_history = self.session_history[-500:]
            
        except Exception as e:
            print(f"❌ Session statistics update error: {e}")
    
    def get_session_performance(self) -> Dict:
        """ดึงสถิติประสิทธิภาพของแต่ละเซสชั่น"""
        try:
            performance = {}
            
            for session, stats in self.session_stats.items():
                session_name = session.value if hasattr(session, 'value') else str(session)
                performance[session_name] = {
                    'total_trades': stats['total_trades'],
                    'success_rate': stats['success_rate'] * 100,  # แปลงเป็น %
                    'total_profit': stats['total_profit'],
                    'avg_profit': stats['avg_profit'],
                    'last_updated': stats['last_updated'].strftime("%Y-%m-%d %H:%M:%S")
                }
            
            # หาเซสชั่นที่ดีที่สุด
            best_session = None
            best_score = 0
            
            for session_name, data in performance.items():
                if data['total_trades'] >= 10:  # ต้องมีข้อมูลเพียงพอ
                    score = data['success_rate'] * 0.7 + (data['avg_profit'] / 10) * 0.3
                    if score > best_score:
                        best_score = score
                        best_session = session_name
            
            return {
                'sessions': performance,
                'best_session': best_session,
                'best_score': best_score,
                'total_sessions_tracked': len(self.session_stats)
            }
            
        except Exception as e:
            print(f"❌ Session performance error: {e}")
            return {'error': str(e)}
    
    def register_session_change_callback(self, callback_func):
        """ลงทะเบียน callback เมื่อเซสชั่นเปลี่ยน"""
        try:
            self.session_change_callbacks.append(callback_func)
            
        except Exception as e:
            print(f"❌ Callback registration error: {e}")
    
    def check_session_change(self) -> bool:
        """
        🔄 ตรวจสอบการเปลี่ยนเซสชั่นและเรียก callbacks
        
        Returns:
            True ถ้าเซสชั่นเปลี่ยน
        """
        try:
            current_analysis = self.get_current_session()
            
            # ตรวจสอบว่าเซสชั่นเปลี่ยนหรือไม่
            if (self.current_session_info and 
                self.current_session_info.current_session != current_analysis.current_session):
                
                old_session = self.current_session_info.current_session
                new_session = current_analysis.current_session
                
                print(f"🔄 Session changed: {old_session.value} -> {new_session.value}")
                
                # เรียก callbacks
                for callback in self.session_change_callbacks:
                    try:
                        callback(old_session, new_session, current_analysis)
                    except Exception as e:
                        print(f"❌ Callback error: {e}")
                
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Session change check error: {e}")
            return False
    
    def get_optimal_trading_parameters(self, strategy_type: str = "general") -> Dict:
        """
        ⚙️ ดึงพารามิเตอร์การเทรดที่เหมาะสมสำหรับเซสชั่นปัจจุบัน
        
        Args:
            strategy_type: ประเภทกลยุทธ์ที่ต้องการ
            
        Returns:
            Dictionary ของพารามิเตอร์
        """
        try:
            analysis = self.get_current_session()
            session = analysis.current_session
            multipliers = self.get_session_multipliers(session)
            
            # พารามิเตอร์พื้นฐาน
            base_params = {
                'lot_size_multiplier': multipliers['lot_size_multiplier'],
                'entry_frequency': multipliers['entry_frequency_multiplier'],
                'recovery_aggressiveness': multipliers['recovery_aggressiveness'],
                'risk_tolerance': self._get_risk_tolerance(session),
                'max_positions': self._get_max_positions(session),
                'spread_tolerance': multipliers['spread_multiplier']
            }
            
            # ปรับตามประเภทกลยุทธ์
            if strategy_type == "trend_following":
                base_params.update({
                    'trend_strength_threshold': 0.6 if session in [TradingSession.LONDON, TradingSession.NY] else 0.4,
                    'breakout_threshold': multipliers['volatility_multiplier'] * 20,  # pips
                    'pullback_tolerance': 0.3
                })
            
            elif strategy_type == "mean_reversion":
                base_params.update({
                    'overbought_threshold': 75 if session == TradingSession.ASIAN else 80,
                    'oversold_threshold': 25 if session == TradingSession.ASIAN else 20,
                    'reversion_strength': 0.7 if session == TradingSession.ASIAN else 0.5
                })
            
            elif strategy_type == "grid":
                base_params.update({
                    'grid_spacing': multipliers['volatility_multiplier'] * 15,  # pips
                    'max_grid_levels': 8 if session in [TradingSession.LONDON, TradingSession.NY] else 5,
                    'volume_multiplier': 1.2 if session == TradingSession.OVERLAP else 1.0
                })
            
            elif strategy_type == "martingale":
                base_params.update({
                    'martingale_multiplier': 1.6 if session == TradingSession.ASIAN else 1.8,
                    'max_levels': 5 if session == TradingSession.ASIAN else 4,
                    'recovery_threshold': -15 if session == TradingSession.ASIAN else -25
                })
            
            # เพิ่มข้อมูลเซสชั่น
            base_params.update({
                'current_session': session.value,
                'session_progress': analysis.session_progress,
                'volatility_expected': analysis.volatility_expected,
                'volume_expected': analysis.volume_expected,
                'risk_level': analysis.risk_level
            })
            
            return base_params
            
        except Exception as e:
            print(f"❌ Trading parameters error: {e}")
            return {'error': str(e)}
    
    def _get_risk_tolerance(self, session: TradingSession) -> float:
        """ดึงระดับความทนต่อความเสี่ยง"""
        risk_tolerance = {
            TradingSession.ASIAN: 0.8,      # ความเสี่ยงต่ำ
            TradingSession.LONDON: 0.6,     # ความเสี่ยงปานกลาง
            TradingSession.NY: 0.6,         # ความเสี่ยงปานกลาง
            TradingSession.OVERLAP: 0.4,    # ความเสี่ยงสูง
            TradingSession.QUIET: 0.9       # ความเสี่ยงต่ำมาก
        }
        return risk_tolerance.get(session, 0.7)
    
    def _get_max_positions(self, session: TradingSession) -> int:
        """ดึงจำนวน positions สูงสุดที่แนะนำ"""
        max_positions = {
            TradingSession.ASIAN: 8,        # ตลาดเงียบ เปิดได้เยอะ
            TradingSession.LONDON: 5,       # ตลาดผันผวน ระวัง
            TradingSession.NY: 5,           # ตลาดผันผวน ระวัง
            TradingSession.OVERLAP: 3,      # ตลาดผันผวนมาก ระวังสูง
            TradingSession.QUIET: 10        # ตลาดเงียบมาก เปิดได้เยอะที่สุด
        }
        return max_positions.get(session, 6)
    
    def get_session_forecast(self, hours_ahead: int = 4) -> List[Dict]:
        """
        🔮 คาดการณ์เซสชั่นในอนาคต
        
        Args:
            hours_ahead: จำนวนชั่วโมงที่ต้องการคาดการณ์
            
        Returns:
            รายการการคาดการณ์
        """
        try:
            forecasts = []
            current_time = datetime.now()
            
            for hour in range(1, hours_ahead + 1):
                future_time = current_time + timedelta(hours=hour)
                future_analysis = self.get_current_session(future_time)
                
                forecast = {
                    'time': future_time.strftime("%H:%M"),
                    'session': future_analysis.current_session.value,
                    'volatility': future_analysis.volatility_expected,
                    'volume': future_analysis.volume_expected,
                    'risk_level': future_analysis.risk_level,
                    'optimal_strategies': future_analysis.optimal_entry_methods[:3]  # เอาแค่ 3 อันดับแรก
                }
                
                forecasts.append(forecast)
            
            return forecasts
            
        except Exception as e:
            print(f"❌ Session forecast error: {e}")
            return []
    
    def get_current_status(self) -> Dict:
        """ดึงสถานะปัจจุบันของ Session Manager"""
        try:
            if not self.current_session_info:
                analysis = self.get_current_session()
            else:
                analysis = self.current_session_info
            
            return {
                'current_session': analysis.current_session.value,
                'next_session': analysis.next_session.value,
                'session_progress': f"{analysis.session_progress*100:.1f}%",
                'time_to_next': str(analysis.time_to_next_session).split('.')[0],  # ตัด microseconds
                'volatility_expected': analysis.volatility_expected,
                'volume_expected': analysis.volume_expected,
                'risk_level': analysis.risk_level,
                'confidence': f"{analysis.confidence*100:.1f}%",
                'optimal_entries': analysis.optimal_entry_methods,
                'optimal_recovery': analysis.optimal_recovery_methods,
                'sessions_tracked': len(self.session_stats),
                'last_analysis': self.last_analysis_time.strftime("%H:%M:%S") if self.last_analysis_time else "Never"
            }
            
        except Exception as e:
            print(f"❌ Current status error: {e}")
            return {'error': str(e)}

def main():
   """Test the Session Manager"""
   print("🧪 Testing Trading Session Manager...")
   
   # Sample configuration
   config = {
       'local_timezone': 'Asia/Bangkok',
       'broker_timezone': 'Europe/London',
       'market_holidays': ['2024-12-25', '2024-01-01'],
       'weekend_trading': False
   }
   
   # Initialize session manager
   session_manager = SessionManager(config)
   
   # Test current session analysis
   analysis = session_manager.get_current_session()
   print(f"\n📊 Current Session Analysis:")
   print(f"   Current Session: {analysis.current_session.value}")
   print(f"   Next Session: {analysis.next_session.value}")
   print(f"   Session Progress: {analysis.session_progress*100:.1f}%")
   print(f"   Time to Next: {analysis.time_to_next_session}")
   print(f"   Volatility Expected: {analysis.volatility_expected}")
   print(f"   Volume Expected: {analysis.volume_expected}")
   print(f"   Risk Level: {analysis.risk_level}")
   print(f"   Confidence: {analysis.confidence*100:.1f}%")
   
   # Test session multipliers
   multipliers = session_manager.get_session_multipliers()
   print(f"\n⚙️ Session Multipliers:")
   for key, value in multipliers.items():
       print(f"   {key}: {value:.2f}")
   
   # Test optimal trading parameters
   params = session_manager.get_optimal_trading_parameters("trend_following")
   print(f"\n🎯 Optimal Trading Parameters (Trend Following):")
   for key, value in params.items():
       if isinstance(value, float):
           print(f"   {key}: {value:.2f}")
       else:
           print(f"   {key}: {value}")
   
   # Test session forecast
   forecasts = session_manager.get_session_forecast(4)
   print(f"\n🔮 Session Forecast (Next 4 hours):")
   for forecast in forecasts:
       print(f"   {forecast['time']}: {forecast['session']} "
             f"(Vol: {forecast['volatility']}, Risk: {forecast['risk_level']})")
   
   # Test current status
   status = session_manager.get_current_status()
   print(f"\n📈 Current Status:")
   for key, value in status.items():
       if isinstance(value, list):
           print(f"   {key}: {', '.join(value[:3])}")  # แสดงแค่ 3 รายการแรก
       else:
           print(f"   {key}: {value}")
   
   print("\n✅ Trading Session Manager test completed")

if __name__ == "__main__":
   main()