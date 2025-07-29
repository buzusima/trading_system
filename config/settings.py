#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SYSTEM SETTINGS - การตั้งค่าระบบหลัก (COMPLETE)
============================================
จัดการการตั้งค่าทั้งหมดของระบบ Intelligent Gold Trading
ฉบับสมบูรณ์แบบที่รองรับ configuration management ขั้นสูง

🎯 ฟีเจอร์หลัก:
- Hierarchical configuration system
- Environment-based settings
- Hot-reload configuration
- Validation และ type checking
- Export/Import capabilities
- Default fallback values
- Profile-based configurations
- Settings history tracking
"""

import os
import json
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime, time as dt_time
import copy

class TradingMode(Enum):
    """โหมดการเทรดของระบบ"""
    LIVE = "LIVE"                    # เทรดจริงเท่านั้น (ตาม requirement)
    DEMO = "DEMO"                    # บัญชี Demo (สำหรับทดสอบ)
    SIMULATION = "SIMULATION"        # จำลองเทรด (ไม่ต่อ MT5)

class MarketSession(Enum):
    """เซสชันตลาดต่างๆ"""
    ASIAN = "ASIAN"                  # 22:00-08:00 GMT+7
    LONDON = "LONDON"                # 15:00-00:00 GMT+7  
    NEW_YORK = "NEW_YORK"            # 20:30-05:30 GMT+7
    OVERLAP = "OVERLAP"              # 20:30-00:00 GMT+7
    QUIET = "QUIET"                  # ช่วงเงียบ

class LogLevel(Enum):
    """ระดับ Logging"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Theme(Enum):
    """ธีม GUI"""
    DARK = "DARK"
    LIGHT = "LIGHT"
    AUTO = "AUTO"

@dataclass
class SessionTiming:
    """การตั้งค่าเวลาของ session"""
    start_hour: int
    start_minute: int = 0
    end_hour: int = 0
    end_minute: int = 0
    timezone: str = "GMT+7"
    active_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Mon-Fri
    
    def get_start_time(self) -> dt_time:
        """ดึงเวลาเริ่มต้น"""
        return dt_time(self.start_hour, self.start_minute)
    
    def get_end_time(self) -> dt_time:
        """ดึงเวลาสิ้นสุด"""
        return dt_time(self.end_hour, self.end_minute)

@dataclass
class TradingLimits:
    """ขีดจำกัดการเทรด"""
    max_daily_volume: float = 100.0         # lots/วัน สูงสุด
    max_hourly_volume: float = 10.0          # lots/ชั่วโมง สูงสุด
    max_positions_total: int = 50            # จำนวน positions สูงสุด
    max_positions_per_symbol: int = 10       # positions ต่อ symbol
    max_daily_trades: int = 200              # จำนวนเทรดต่อวัน
    max_spread: float = 5.0                  # spread สูงสุดที่ยอมรับ
    min_equity: float = 1000.0               # equity ขั้นต่ำ
    max_drawdown_percent: float = 30.0       # drawdown สูงสุด (%)

@dataclass
class RiskManagement:
    """การจัดการความเสี่ยง"""
    use_stop_loss: bool = False              # ❌ ห้ามใช้ SL ตาม requirement
    use_take_profit: bool = False            # ❌ ห้ามใช้ TP แบบดั้งเดิม
    recovery_mandatory: bool = True          # ✅ บังคับใช้ Recovery
    max_recovery_levels: int = 10            # ระดับ recovery สูงสุด
    recovery_multiplier: float = 1.5         # ตัวคูณ recovery
    emergency_stop_enabled: bool = True      # เปิดใช้หยุดฉุกเฉิน
    correlation_limit: float = 0.8           # จำกัด correlation
    news_trading_enabled: bool = True        # เทรดช่วงข่าว
    weekend_trading: bool = False            # เทรดช่วงวันหยุด

@dataclass
class PerformanceSettings:
    """การตั้งค่าประสิทธิภาพ"""
    max_cpu_usage: float = 80.0              # CPU สูงสุด (%)
    max_memory_usage: float = 1024.0         # Memory สูงสุด (MB)
    update_interval_ms: int = 1000           # GUI update interval
    data_cache_size: int = 10000             # ขนาด cache ข้อมูล
    log_buffer_size: int = 1000              # ขนาด log buffer
    cleanup_interval_hours: int = 24         # ทำความสะอาดทุกกี่ชั่วโมง
    backup_interval_hours: int = 6           # สำรองข้อมูลทุกกี่ชั่วโมง

@dataclass
class NotificationSettings:
    """การตั้งค่าการแจ้งเตือน"""
    enable_sound: bool = True                # เสียงแจ้งเตือน
    enable_popup: bool = True                # popup แจ้งเตือน
    enable_email: bool = False               # email แจ้งเตือน
    enable_line: bool = False                # LINE แจ้งเตือน
    
    # Email settings
    email_smtp_server: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_to: List[str] = field(default_factory=list)
    
    # LINE settings
    line_token: str = ""
    
    # Notification triggers
    notify_on_error: bool = True
    notify_on_position_open: bool = False
    notify_on_position_close: bool = True
    notify_on_recovery: bool = True
    notify_on_profit_target: bool = True
    notify_on_system_start: bool = True

@dataclass
class SystemSettings:
    """
    คลาสหลักสำหรับการตั้งค่าระบบ - ฉบับสมบูรณ์
    รวบรวมการตั้งค่าทั้งหมดไว้ในที่เดียวอย่างเป็นระบบ
    """
    
    # === CORE SYSTEM SETTINGS ===
    trading_mode: TradingMode = TradingMode.LIVE
    symbol: str = "XAUUSD"                   # Gold เท่านั้น
    environment: str = "production"          # production, development, testing
    
    # === VOLUME & REBATE TARGETS ===
    daily_volume_target_min: float = 50.0   # lots/วัน ขั้นต่ำ
    daily_volume_target_max: float = 100.0  # lots/วัน สูงสุด
    rebate_optimization: bool = True         # เปิดการเพิ่มประสิทธิภาพ rebate
    target_rebate_per_day: float = 500.0     # เป้าหมาย rebate ต่อวัน ($)
    
    # === MARKET INTELLIGENCE SETTINGS ===
    timeframes_analysis: List[str] = field(default_factory=lambda: ["M1", "M5", "M15", "H1"])
    market_analysis_interval: int = 1        # วินาที - ความถี่ในการวิเคราะห์ตลาด
    
    # Technical Analysis Parameters
    adx_trending_threshold: float = 25.0     # ADX > 25 = Trending
    adx_ranging_threshold: float = 20.0      # ADX < 20 = Ranging
    atr_period: int = 14                     # ATR period
    atr_multiplier_high: float = 1.5         # ATR * 1.5 = High Volatility
    atr_multiplier_low: float = 0.8          # ATR * 0.8 = Low Volatility
    rsi_period: int = 14                     # RSI period
    rsi_overbought: float = 70.0             # RSI overbought level
    rsi_oversold: float = 30.0               # RSI oversold level
    bollinger_period: int = 20               # Bollinger Bands period
    bollinger_deviation: float = 2.0         # Standard deviation
    
    # === SESSION CONFIGURATIONS ===
    session_timings: Dict[str, SessionTiming] = field(default_factory=lambda: {
        "ASIAN": SessionTiming(22, 0, 8, 0),
        "LONDON": SessionTiming(15, 0, 20, 0),
        "NEW_YORK": SessionTiming(20, 30, 5, 30),
        "OVERLAP": SessionTiming(20, 30, 0, 0)
    })
    
    # Session-specific parameters
    session_parameters: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "ASIAN": {
            "volatility_expectation": "LOW",
            "preferred_strategies": ["MEAN_REVERSION", "SCALPING_ENGINE"],
            "max_spread": 2.5,
            "position_sizing_multiplier": 0.8,
            "signal_frequency": "NORMAL"
        },
        "LONDON": {
            "volatility_expectation": "HIGH",
            "preferred_strategies": ["TREND_FOLLOWING", "BREAKOUT_FALSE"],
            "max_spread": 3.0,
            "position_sizing_multiplier": 1.2,
            "signal_frequency": "HIGH"
        },
        "NEW_YORK": {
            "volatility_expectation": "VERY_HIGH",
            "preferred_strategies": ["NEWS_REACTION", "TREND_FOLLOWING"],
            "max_spread": 3.5,
            "position_sizing_multiplier": 1.5,
            "signal_frequency": "VERY_HIGH"
        },
        "OVERLAP": {
            "volatility_expectation": "EXTREME",
            "preferred_strategies": ["BREAKOUT_FALSE", "NEWS_REACTION"],
            "max_spread": 4.0,
            "position_sizing_multiplier": 1.8,
            "signal_frequency": "EXTREME"
        }
    })
    
    # === ENTRY FREQUENCY SETTINGS ===
    high_frequency_mode: bool = True         # เปิดโหมด High Frequency
    max_positions_per_hour: int = 50         # จำนวนออร์เดอร์สูงสุดต่อชั่วโมง
    min_entry_interval_seconds: int = 10     # ช่วงเวลาขั้นต่ำระหว่างการเข้าออร์เดอร์
    signal_cooldown_seconds: int = 15        # cooldown ระหว่างสัญญาณ
    
    # === MT5 CONNECTION SETTINGS ===
    mt5_login: Optional[int] = None          # จะ auto-detect
    mt5_password: Optional[str] = None       # ไม่ต้องใส่รหัสผ่าน
    mt5_server: Optional[str] = None         # จะ auto-detect
    mt5_path: Optional[str] = None           # auto-detect terminal path
    mt5_timeout: int = 10000                 # Timeout in milliseconds
    mt5_portable: bool = False               # Portable mode
    mt5_auto_detect: bool = True             # Auto-detect settings
    
    # === GUI SETTINGS ===
    gui_theme: Theme = Theme.DARK            # Dark theme สำหรับ professional look
    gui_update_interval: int = 1000          # GUI update interval (ms)
    gui_width: int = 1400                    # หน้าจอกว้าง
    gui_height: int = 900                    # หน้าจอสูง
    gui_resizable: bool = True               # ปรับขนาดได้
    gui_always_on_top: bool = False          # อยู่บนสุดเสมอ
    gui_minimize_to_tray: bool = True        # ย่อเก็บใน system tray
    gui_show_splash: bool = True             # แสดง splash screen
    
    # === LOGGING SETTINGS ===
    log_level: LogLevel = LogLevel.INFO
    log_to_file: bool = True
    log_file_path: str = "logs/trading_system.log"
    log_max_file_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    log_console_output: bool = True
    log_performance_metrics: bool = True
    
    # === ADVANCED SETTINGS ===
    trading_limits: TradingLimits = field(default_factory=TradingLimits)
    risk_management: RiskManagement = field(default_factory=RiskManagement)
    performance_settings: PerformanceSettings = field(default_factory=PerformanceSettings)
    notification_settings: NotificationSettings = field(default_factory=NotificationSettings)
    
    # === SYSTEM METADATA ===
    version: str = "2.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    profile_name: str = "default"
    config_file_path: str = "config/settings.json"
    
    # === DEVELOPMENT SETTINGS ===
    debug_mode: bool = False
    enable_profiling: bool = False
    mock_mt5: bool = False                   # บังคับใช้ Mock MT5
    simulation_speed: float = 1.0            # ความเร็วการจำลอง (1.0 = realtime)
    
    def __post_init__(self):
        """การตั้งค่าเพิ่มเติมหลังจาก initialization"""
        self._validate_settings()
        self._setup_directories()
        self.updated_at = datetime.now()
    
    def _validate_settings(self):
        """ตรวจสอบความถูกต้องของการตั้งค่า"""
        # ตรวจสอบ volume targets
        if self.daily_volume_target_min > self.daily_volume_target_max:
            self.daily_volume_target_min = 50.0
            self.daily_volume_target_max = 100.0
        
        # ตรวจสอบ ADX thresholds
        if self.adx_ranging_threshold >= self.adx_trending_threshold:
            self.adx_ranging_threshold = 20.0
            self.adx_trending_threshold = 25.0
        
        # ตรวจสอบ GUI dimensions
        if self.gui_width < 800:
            self.gui_width = 800
        if self.gui_height < 600:
            self.gui_height = 600
        
        # ตรวจสอบ RSI levels
        if self.rsi_oversold >= self.rsi_overbought:
            self.rsi_oversold = 30.0
            self.rsi_overbought = 70.0
        
        # ตรวจสอบ timeframes
        valid_timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
        self.timeframes_analysis = [tf for tf in self.timeframes_analysis if tf in valid_timeframes]
        if not self.timeframes_analysis:
            self.timeframes_analysis = ["M1", "M5", "M15", "H1"]
    
    def _setup_directories(self):
        """สร้างโฟลเดอร์ที่จำเป็น"""
        directories = [
            "logs",
            "config",
            "data",
            "backups",
            "exports"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_session_config(self, session_name: str) -> Dict[str, Any]:
        """ดึงการตั้งค่าของ session"""
        return self.session_parameters.get(session_name, {})
    
    def get_session_timing(self, session_name: str) -> Optional[SessionTiming]:
        """ดึงเวลาของ session"""
        return self.session_timings.get(session_name)
    
    def update_session_config(self, session_name: str, config: Dict[str, Any]):
        """อัพเดทการตั้งค่าของ session"""
        if session_name in self.session_parameters:
            self.session_parameters[session_name].update(config)
            self.updated_at = datetime.now()
    
    def get_current_session(self) -> str:
        """กำหนด session ปัจจุบันตามเวลา"""
        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()
        
        # ตรวจสอบว่าเป็นวันทำการหรือไม่
        if current_weekday >= 5:  # Saturday, Sunday
            return "QUIET"
        
        # ตรวจสอบ session ตามเวลา
        for session_name, timing in self.session_timings.items():
            start_time = timing.get_start_time()
            end_time = timing.get_end_time()
            
            # Handle overnight sessions
            if start_time > end_time:  # เช่น 22:00 - 08:00
                if current_time >= start_time or current_time <= end_time:
                    return session_name
            else:  # เช่น 15:00 - 20:00
                if start_time <= current_time <= end_time:
                    return session_name
        
        return "QUIET"
    
    def is_trading_hours(self) -> bool:
        """ตรวจสอบว่าอยู่ในช่วงเวลาเทรดหรือไม่"""
        current_session = self.get_current_session()
        
        # ถ้าไม่อนุญาตให้เทรดช่วงวันหยุด
        if not self.risk_management.weekend_trading:
            now = datetime.now()
            if now.weekday() >= 5:  # Saturday, Sunday
                return False
        
        return current_session != "QUIET"
    
    def get_max_spread_for_session(self, session_name: str = None) -> float:
        """ดึง max spread สำหรับ session"""
        if session_name is None:
            session_name = self.get_current_session()
        
        session_config = self.get_session_config(session_name)
        return session_config.get("max_spread", self.trading_limits.max_spread)
    
    def save_to_file(self, file_path: Optional[str] = None):
        """บันทึกการตั้งค่าลงไฟล์"""
        if file_path is None:
            file_path = self.config_file_path
        
        try:
            # สร้างโฟลเดอร์ถ้าไม่มี
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # แปลงเป็น dict และจัดการ special types
            config_dict = self._to_serializable_dict()
            
            # บันทึกลงไฟล์
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False, default=str)
            
            self.updated_at = datetime.now()
            return True
            
        except Exception as e:
            print(f"❌ ไม่สามารถบันทึกการตั้งค่า: {e}")
            return False
    
    def _to_serializable_dict(self) -> Dict[str, Any]:
        """แปลงเป็น dict ที่สามารถ serialize ได้"""
        result = {}
        
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, Enum):
                result[field_name] = field_value.value
            elif isinstance(field_value, datetime):
                result[field_name] = field_value.isoformat()
            elif hasattr(field_value, '__dict__'):  # dataclass objects
                if hasattr(field_value, '_to_serializable_dict'):
                    result[field_name] = field_value._to_serializable_dict()
                else:
                    result[field_name] = asdict(field_value)
            elif isinstance(field_value, dict):
                # Handle nested dicts with special objects
                nested_dict = {}
                for key, value in field_value.items():
                    if isinstance(value, Enum):
                        nested_dict[key] = value.value
                    elif hasattr(value, '__dict__'):
                        nested_dict[key] = asdict(value) if hasattr(value, '__dataclass_fields__') else str(value)
                    else:
                        nested_dict[key] = value
                result[field_name] = nested_dict
            elif isinstance(field_value, list):
                # Handle lists with special objects
                nested_list = []
                for item in field_value:
                    if isinstance(item, Enum):
                        nested_list.append(item.value)
                    elif hasattr(item, '__dict__'):
                        nested_list.append(asdict(item) if hasattr(item, '__dataclass_fields__') else str(item))
                    else:
                        nested_list.append(item)
                result[field_name] = nested_list
            else:
                result[field_name] = field_value
        
        return result
    
    @classmethod
    def load_from_file(cls, file_path: Optional[str] = None) -> 'SystemSettings':
        """โหลดการตั้งค่าจากไฟล์"""
        if file_path is None:
            file_path = "config/settings.json"
        
        try:
            if not Path(file_path).exists():
                # ไฟล์ไม่มี - ใช้ค่าเริ่มต้น
                settings = cls()
                settings.config_file_path = file_path
                settings.save_to_file(file_path)  # สร้างไฟล์เริ่มต้น
                return settings
            
            with open(file_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            # Convert back to appropriate types
            return cls._from_dict(config_dict)
            
        except Exception as e:
            print(f"⚠️ ไม่สามารถโหลดการตั้งค่าจากไฟล์: {e}")
            # ใช้ค่าเริ่มต้น
            settings = cls()
            settings.config_file_path = file_path or "config/settings.json"
            return settings
    
    @classmethod
    def _from_dict(cls, config_dict: Dict[str, Any]) -> 'SystemSettings':
        """สร้าง instance จาก dictionary"""
        # Handle enum conversions
        if 'trading_mode' in config_dict:
            config_dict['trading_mode'] = TradingMode(config_dict['trading_mode'])
        if 'gui_theme' in config_dict:
            config_dict['gui_theme'] = Theme(config_dict['gui_theme'])
        if 'log_level' in config_dict:
            config_dict['log_level'] = LogLevel(config_dict['log_level'])
        
        # Handle datetime conversions
        if 'created_at' in config_dict and isinstance(config_dict['created_at'], str):
            config_dict['created_at'] = datetime.fromisoformat(config_dict['created_at'])
        if 'updated_at' in config_dict and isinstance(config_dict['updated_at'], str):
            config_dict['updated_at'] = datetime.fromisoformat(config_dict['updated_at'])
        
        # Handle complex objects
        if 'session_timings' in config_dict:
            session_timings = {}
            for session_name, timing_data in config_dict['session_timings'].items():
                session_timings[session_name] = SessionTiming(**timing_data)
            config_dict['session_timings'] = session_timings
        
        if 'trading_limits' in config_dict:
            config_dict['trading_limits'] = TradingLimits(**config_dict['trading_limits'])
        
        if 'risk_management' in config_dict:
            config_dict['risk_management'] = RiskManagement(**config_dict['risk_management'])
        
        if 'performance_settings' in config_dict:
            config_dict['performance_settings'] = PerformanceSettings(**config_dict['performance_settings'])
        
        if 'notification_settings' in config_dict:
            config_dict['notification_settings'] = NotificationSettings(**config_dict['notification_settings'])
        
        return cls(**config_dict)
    
    def create_profile(self, profile_name: str) -> 'SystemSettings':
        """สร้าง profile ใหม่"""
        new_settings = copy.deepcopy(self)
        new_settings.profile_name = profile_name
        new_settings.created_at = datetime.now()
        new_settings.updated_at = datetime.now()
        new_settings.config_file_path = f"config/settings_{profile_name}.json"
        return new_settings
    
    def load_profile(self, profile_name: str) -> 'SystemSettings':
        """โหลด profile"""
        profile_path = f"config/settings_{profile_name}.json"
        return self.load_from_file(profile_path)
    
    def get_available_profiles(self) -> List[str]:
        """ดึงรายชื่อ profiles ที่มี"""
        try:
            config_dir = Path("config")
            if not config_dir.exists():
                return ["default"]
            
            profiles = []
            for file_path in config_dir.glob("settings_*.json"):
                profile_name = file_path.stem.replace("settings_", "")
                profiles.append(profile_name)
            
            if not profiles:
                profiles = ["default"]
            
            return sorted(profiles)
            
        except Exception:
            return ["default"]
    
    def export_profile(self, export_path: str, include_sensitive: bool = False) -> bool:
        """ส่งออก profile"""
        try:
            export_data = self._to_serializable_dict()
            
            # Remove sensitive data if requested
            if not include_sensitive:
                sensitive_fields = [
                    'mt5_password', 'email_password', 'line_token'
                ]
                for field in sensitive_fields:
                    if field in export_data:
                        export_data[field] = "***HIDDEN***"
                
                # Remove sensitive notification settings
                if 'notification_settings' in export_data:
                    notif_settings = export_data['notification_settings']
                    notif_settings['email_password'] = "***HIDDEN***"
                    notif_settings['line_token'] = "***HIDDEN***"
            
            # Add export metadata
            export_data['export_info'] = {
                'exported_at': datetime.now().isoformat(),
                'exported_by': os.getenv('USERNAME', 'unknown'),
                'include_sensitive': include_sensitive,
                'source_profile': self.profile_name
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"❌ ไม่สามารถส่งออก profile: {e}")
            return False
    
    def import_profile(self, import_path: str, merge: bool = False) -> bool:
        """นำเข้า profile"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Remove export metadata
            if 'export_info' in import_data:
                del import_data['export_info']
            
            if merge:
                # Merge with current settings
                for key, value in import_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            else:
                # Replace current settings
                imported_settings = self._from_dict(import_data)
                self.__dict__.update(imported_settings.__dict__)
            
            self.updated_at = datetime.now()
            return True
            
        except Exception as e:
            print(f"❌ ไม่สามารถนำเข้า profile: {e}")
            return False
    
    def reset_to_defaults(self):
        """รีเซ็ตเป็นค่าเริ่มต้น"""
        default_settings = SystemSettings()
        
        # Keep some current values
        current_profile = self.profile_name
        current_config_path = self.config_file_path
        
        # Update with defaults
        self.__dict__.update(default_settings.__dict__)
        
        # Restore preserved values
        self.profile_name = current_profile
        self.config_file_path = current_config_path
        self.updated_at = datetime.now()
    
    def validate_configuration(self) -> Dict[str, List[str]]:
        """ตรวจสอบความถูกต้องของการตั้งค่า"""
        issues = {
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        # ตรวจสอบค่าพื้นฐาน
        if self.daily_volume_target_min <= 0:
            issues['errors'].append("daily_volume_target_min ต้องมากกว่า 0")
        
        if self.daily_volume_target_max <= self.daily_volume_target_min:
            issues['errors'].append("daily_volume_target_max ต้องมากกว่า daily_volume_target_min")
        
        # ตรวจสอบ technical parameters
        if self.atr_period <= 0:
            issues['errors'].append("atr_period ต้องมากกว่า 0")
        
        if self.rsi_period <= 0:
            issues['errors'].append("rsi_period ต้องมากกว่า 0")
        
        # ตรวจสอบ GUI settings
        if self.gui_update_interval < 100:
            issues['warnings'].append("gui_update_interval น้อยกว่า 100ms อาจทำให้ CPU สูง")
        
        # ตรวจสอบ risk management
        if not self.risk_management.recovery_mandatory and not self.risk_management.use_stop_loss:
            issues['warnings'].append("ไม่มี stop loss และไม่บังคับ recovery - ความเสี่ยงสูง")
        
        # ตรวจสอบ session timings
        for session_name, timing in self.session_timings.items():
            if timing.start_hour < 0 or timing.start_hour > 23:
                issues['errors'].append(f"Session {session_name}: start_hour ต้องอยู่ระหว่าง 0-23")
        
        return issues
    
    def get_summary(self) -> Dict[str, Any]:
        """ดึงสรุปการตั้งค่า"""
        validation_result = self.validate_configuration()
        
        return {
            'profile_info': {
                'name': self.profile_name,
                'version': self.version,
                'created_at': self.created_at.isoformat(),
                'updated_at': self.updated_at.isoformat(),
                'environment': self.environment
            },
            'trading_config': {
                'mode': self.trading_mode.value,
                'symbol': self.symbol,
                'high_frequency': self.high_frequency_mode,
                'volume_target': f"{self.daily_volume_target_min}-{self.daily_volume_target_max} lots/day",
                'recovery_enabled': self.risk_management.recovery_mandatory
            },
            'system_config': {
                'gui_theme': self.gui_theme.value,
                'log_level': self.log_level.value,
                'debug_mode': self.debug_mode,
                'mock_mt5': self.mock_mt5
            },
            'validation': {
                'errors_count': len(validation_result['errors']),
                'warnings_count': len(validation_result['warnings']),
                'status': 'VALID' if not validation_result['errors'] else 'INVALID'
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """แปลงเป็น dictionary"""
        return self._to_serializable_dict()

# ===============================
# GLOBAL SETTINGS MANAGEMENT
# ===============================

_global_settings: Optional[SystemSettings] = None
_settings_lock = threading.Lock()

def get_system_settings() -> SystemSettings:
   """ดึง SystemSettings instance (Singleton pattern)"""
   global _global_settings
   
   with _settings_lock:
       if _global_settings is None:
           try:
               _global_settings = SystemSettings.load_from_file()
           except Exception as e:
               print(f"⚠️ ใช้การตั้งค่าเริ่มต้น: {e}")
               _global_settings = SystemSettings()
   
   return _global_settings

def reload_system_settings(file_path: Optional[str] = None) -> SystemSettings:
   """โหลดการตั้งค่าใหม่"""
   global _global_settings
   
   with _settings_lock:
       _global_settings = SystemSettings.load_from_file(file_path)
   
   return _global_settings

def save_system_settings(settings: SystemSettings = None):
   """บันทึกการตั้งค่าระบบ"""
   global _global_settings
   
   with _settings_lock:
       if settings:
           _global_settings = settings
       
       if _global_settings:
           _global_settings.save_to_file()

def switch_profile(profile_name: str) -> SystemSettings:
   """เปลี่ยน profile"""
   global _global_settings
   
   with _settings_lock:
       _global_settings = SystemSettings().load_profile(profile_name)
   
   return _global_settings

# ===============================
# CONFIGURATION UTILITIES
# ===============================

def create_development_config() -> SystemSettings:
   """สร้างการตั้งค่าสำหรับ development"""
   settings = SystemSettings()
   settings.environment = "development"
   settings.debug_mode = True
   settings.mock_mt5 = True
   settings.log_level = LogLevel.DEBUG
   settings.trading_mode = TradingMode.SIMULATION
   settings.daily_volume_target_min = 10.0
   settings.daily_volume_target_max = 20.0
   settings.profile_name = "development"
   return settings

def create_production_config() -> SystemSettings:
   """สร้างการตั้งค่าสำหรับ production"""
   settings = SystemSettings()
   settings.environment = "production"
   settings.debug_mode = False
   settings.mock_mt5 = False
   settings.log_level = LogLevel.INFO
   settings.trading_mode = TradingMode.LIVE
   settings.profile_name = "production"
   return settings

def create_testing_config() -> SystemSettings:
   """สร้างการตั้งค่าสำหรับ testing"""
   settings = SystemSettings()
   settings.environment = "testing"
   settings.debug_mode = True
   settings.mock_mt5 = True
   settings.log_level = LogLevel.DEBUG
   settings.trading_mode = TradingMode.DEMO
   settings.daily_volume_target_min = 5.0
   settings.daily_volume_target_max = 10.0
   settings.profile_name = "testing"
   return settings

def get_config_template() -> Dict[str, Any]:
   """ดึง template การตั้งค่า"""
   return SystemSettings()._to_serializable_dict()

def validate_config_file(file_path: str) -> Dict[str, Any]:
   """ตรวจสอบไฟล์การตั้งค่า"""
   try:
       settings = SystemSettings.load_from_file(file_path)
       validation_result = settings.validate_configuration()
       
       return {
           'valid': len(validation_result['errors']) == 0,
           'file_exists': Path(file_path).exists(),
           'validation_result': validation_result,
           'settings_summary': settings.get_summary()
       }
       
   except Exception as e:
       return {
           'valid': False,
           'file_exists': Path(file_path).exists(),
           'error': str(e),
           'validation_result': {'errors': [str(e)], 'warnings': [], 'info': []}
       }

# ===============================
# TEST FUNCTIONS
# ===============================

def test_system_settings():
   """ทดสอบ SystemSettings"""
   print("🧪 ทดสอบ System Settings...")
   
   # ทดสอบการสร้าง instance
   settings = SystemSettings()
   print(f"✅ สร้าง instance: {settings.symbol}")
   
   # ทดสอบ validation
   validation = settings.validate_configuration()
   print(f"✅ Validation - Errors: {len(validation['errors'])}, Warnings: {len(validation['warnings'])}")
   
   # ทดสอบ session detection
   current_session = settings.get_current_session()
   print(f"✅ Current session: {current_session}")
   
   # ทดสอบ trading hours
   is_trading_hours = settings.is_trading_hours()
   print(f"✅ Is trading hours: {is_trading_hours}")
   
   # ทดสอบการบันทึกและโหลด
   test_file = "test_settings.json"
   settings.save_to_file(test_file)
   loaded_settings = SystemSettings.load_from_file(test_file)
   print(f"✅ บันทึกและโหลด: {loaded_settings.symbol}")
   
   # ทดสอบ profile management
   dev_config = create_development_config()
   print(f"✅ Development config: {dev_config.environment}")
   
   # ทดสอบ export/import
   export_file = "test_export.json"
   success = settings.export_profile(export_file)
   print(f"✅ Export profile: {'สำเร็จ' if success else 'ล้มเหลว'}")
   
   # ลบไฟล์ทดสอบ
   for test_file in ["test_settings.json", "test_export.json"]:
       try:
           Path(test_file).unlink()
       except:
           pass
   
   print("✅ ทดสอบ System Settings เสร็จสิ้น")

def benchmark_settings_performance():
   """ทดสอบประสิทธิภาพ Settings"""
   print("⚡ ทดสอบประสิทธิภาพ Settings...")
   
   import time
   
   # Test loading time
   start_time = time.time()
   for i in range(100):
       settings = SystemSettings()
   creation_time = time.time() - start_time
   
   print(f"📊 ผลลัพธ์:")
   print(f"   เวลาสร้าง instance (100 ครั้ง): {creation_time:.3f} วินาที")
   print(f"   เฉลี่ย: {creation_time*10:.2f} ms/instance")
   
   # Test validation time
   settings = SystemSettings()
   start_time = time.time()
   for i in range(100):
       settings.validate_configuration()
   validation_time = time.time() - start_time
   
   print(f"   เวลา validation (100 ครั้ง): {validation_time:.3f} วินาที")
   print(f"   เฉลี่ย: {validation_time*10:.2f} ms/validation")
   
   # Test serialization time
   start_time = time.time()
   for i in range(100):
       settings._to_serializable_dict()
   serialization_time = time.time() - start_time
   
   print(f"   เวลา serialization (100 ครั้ง): {serialization_time:.3f} วินาที")
   print(f"   เฉลี่ย: {serialization_time*10:.2f} ms/serialization")

if __name__ == "__main__":
   test_system_settings()
   print("\n" + "="*50)
   benchmark_settings_performance()

