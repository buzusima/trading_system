#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SYSTEM SETTINGS - การตั้งค่าระบบหลัก
================================
จัดการการตั้งค่าทั้งหมดของระบบ Intelligent Gold Trading

เชื่อมต่อไปยัง:
- config/trading_params.py (พารามิเตอร์การเทรด)
- config/session_config.py (การตั้งค่า session)
- utilities/configuration_manager.py (จัดการ config file)
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class TradingMode(Enum):
    """โหมดการเทรดของระบบ"""
    LIVE = "LIVE"           # เทรดจริงเท่านั้น (ตาม requirement)
    
class MarketSession(Enum):
    """เซสชันตลาดต่างๆ"""
    ASIAN = "ASIAN"         # 22:00-08:00 GMT+7
    LONDON = "LONDON"       # 15:00-00:00 GMT+7  
    NEW_YORK = "NEW_YORK"   # 20:30-05:30 GMT+7
    OVERLAP = "OVERLAP"     # 20:30-00:00 GMT+7

@dataclass
class SystemSettings:
    """
    คลาสหลักสำหรับการตั้งค่าระบบ
    รวบรวมการตั้งค่าทั้งหมดไว้ในที่เดียว
    """
    
    # === CORE SYSTEM SETTINGS ===
    trading_mode: TradingMode = TradingMode.LIVE
    symbol: str = "XAUUSD"  # Gold เท่านั้น
    
    # === VOLUME & REBATE TARGETS ===
    daily_volume_target_min: float = 50.0   # lots/วัน (minimum)
    daily_volume_target_max: float = 100.0  # lots/วัน (maximum)
    rebate_optimization: bool = True         # เปิดการเพิ่มประสิทธิภาพ rebate
    
    # === MARKET INTELLIGENCE SETTINGS ===
    timeframes_analysis: List[str] = field(default_factory=lambda: ["M1", "M5", "M15", "H1"])
    market_analysis_interval: int = 1  # วินาที - ความถี่ในการวิเคราะห์ตลาด
    
    # ADX Settings สำหรับ Trend Detection
    adx_trending_threshold: float = 25.0    # ADX > 25 = Trending
    adx_ranging_threshold: float = 20.0     # ADX < 20 = Ranging
    
    # ATR Settings สำหรับ Volatility Detection  
    atr_period: int = 14
    atr_multiplier_high: float = 1.5        # ATR * 1.5 = High Volatility
    atr_multiplier_low: float = 0.8         # ATR * 0.8 = Low Volatility
    
    # === RECOVERY SYSTEM SETTINGS ===
    use_stop_loss: bool = False              # ✅ FORBIDDEN - ห้ามใช้ SL
    recovery_mandatory: bool = True          # ✅ บังคับใช้ระบบ Recovery
    max_recovery_attempts: int = 999         # ไม่จำกัดจำนวนครั้งในการ Recovery
    
    # === ENTRY FREQUENCY SETTINGS ===
    high_frequency_mode: bool = True         # เปิดโหมด High Frequency
    max_positions_per_hour: int = 50         # จำนวนออร์เดอร์สูงสุดต่อชั่วโมง
    min_entry_interval_seconds: int = 10     # ช่วงเวลาขั้นต่ำระหว่างการเข้าออร์เดอร์
    
    # === MT5 CONNECTION SETTINGS ===
    mt5_server: Optional[str] = None         # จะตั้งค่าจาก MT5
    mt5_login: Optional[int] = None          # จะตั้งค่าจาก MT5  
    mt5_password: Optional[str] = None       # จะตั้งค่าจาก MT5
    mt5_path: Optional[str] = None           # Path ไปยัง MT5
    
    connection_timeout: int = 30             # Timeout สำหรับการเชื่อมต่อ (วินาที)
    reconnect_attempts: int = 5              # จำนวนครั้งในการ reconnect
    order_execution_timeout: int = 10        # Timeout สำหรับการส่งออร์เดอร์
    
    # === POSITION MANAGEMENT ===
    unlimited_positions: bool = True         # ✅ ไม่จำกัดจำนวน positions
    position_tracking_precision: int = 5     # ทศนิยม 5 ตำแหน่ง
    
    # === MONEY MANAGEMENT ===
    base_lot_size: float = 0.01             # ขนาด lot พื้นฐาน
    account_balance_buffer: float = 0.95     # ใช้ 95% ของ balance (5% buffer)
    
    # === GUI SETTINGS ===
    gui_update_interval: int = 500           # มิลลิวินาที - อัพเดท GUI
    gui_theme: str = "professional_dark"     # ธีมของ GUI
    
    # === LOGGING SETTINGS ===
    log_level: str = "INFO"                  # ระดับการ log
    log_to_file: bool = True                 # บันทึก log ลงไฟล์
    log_file_max_size: int = 50              # MB
    log_backup_count: int = 5                # จำนวนไฟล์ backup
    
    # === ANALYTICS SETTINGS ===
    performance_tracking: bool = True        # เปิดการติดตามผลการดำเนินงาน
    trade_history_days: int = 30             # เก็บประวัติเทรด 30 วัน
    
    def __post_init__(self):
        """
        ตรวจสอบและปรับแต่งการตั้งค่าหลังจากสร้าง object
        """
        # ตรวจสอบ Trading Mode ต้องเป็น LIVE เท่านั้น
        if self.trading_mode != TradingMode.LIVE:
            raise ValueError("❌ ระบบรองรับเฉพาะ LIVE TRADING เท่านั้น!")
            
        # ตรวจสอบ Symbol ต้องเป็น XAUUSD เท่านั้น
        if self.symbol != "XAUUSD":
            raise ValueError("❌ ระบบรองรับเฉพาะ XAUUSD (Gold) เท่านั้น!")
            
        # ตรวจสอบ Stop Loss ต้องปิดเสมอ
        if self.use_stop_loss:
            raise ValueError("❌ ห้ามใช้ Stop Loss! ใช้ Recovery System เท่านั้น!")
            
        # ตรวจสอบ Recovery ต้องเปิดเสมอ
        if not self.recovery_mandatory:
            raise ValueError("❌ Recovery System เป็นสิ่งจำเป็น!")
    
    @classmethod
    def load_from_file(cls, config_path: Optional[str] = None) -> 'SystemSettings':
        """
        โหลดการตั้งค่าจากไฟล์ config
        เชื่อมต่อไป: utilities/configuration_manager.py
        """
        # TODO: Implement file loading logic
        return cls()
    
    def save_to_file(self, config_path: Optional[str] = None) -> bool:
        """
        บันทึกการตั้งค่าลงไฟล์
        เชื่อมต่อไป: utilities/configuration_manager.py
        """
        # TODO: Implement file saving logic
        return True
    
    def validate_mt5_settings(self) -> bool:
        """
        ตรวจสอบการตั้งค่า MT5
        เชื่อมต่อไป: mt5_integration/mt5_connector.py
        """
        required_fields = [self.mt5_server, self.mt5_login, self.mt5_password]
        return all(field is not None for field in required_fields)
    
    def get_session_settings(self, session: MarketSession) -> Dict:
        """
        ดึงการตั้งค่าเฉพาะสำหรับแต่ละ session
        เชื่อมต่อไป: config/session_config.py
        """
        # TODO: Implement session-specific settings
        return {}
    
    def get_trading_parameters(self) -> Dict:
        """
        ดึงพารามิเตอร์การเทรด
        เชื่อมต่อไป: config/trading_params.py
        """
        # TODO: Implement trading parameters loading
        return {}

# === GLOBAL SETTINGS INSTANCE ===
# สร้าง instance เดียวให้ใช้ทั้งระบบ
_global_settings: Optional[SystemSettings] = None

def get_system_settings() -> SystemSettings:
    """
    ดึง SystemSettings แบบ Singleton
    ใช้ instance เดียวกันทั้งระบบ
    """
    global _global_settings
    if _global_settings is None:
        _global_settings = SystemSettings()
    return _global_settings

def update_system_settings(new_settings: SystemSettings) -> None:
    """
    อัพเดทการตั้งค่าระบบ
    """
    global _global_settings
    _global_settings = new_settings