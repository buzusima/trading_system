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
    # 🚀 AUTO-DETECT: ระบบจะดึงข้อมูลจาก MT5 ที่ Login ไว้แล้วอัตโนมัติ
    mt5_login: Optional[int] = None             # จะดึงจาก MT5 ที่เปิดอยู่
    mt5_password: Optional[str] = None          # ไม่ต้องใส่รหัสผ่าน
    mt5_server: Optional[str] = None            # จะดึงจาก MT5 ที่เปิดอยู่
    mt5_path: Optional[str] = None              # Path ไปยัง terminal64.exe (ถ้าไม่ระบุจะหาอัตโนมัติ)
    use_existing_connection: bool = True        # ใช้การเชื่อมต่อที่มีอยู่แล้ว
    
    connection_timeout: int = 30                # Timeout การเชื่อมต่อ (วินาที)
    reconnect_attempts: int = 5                 # จำนวนครั้งที่พยายาม reconnect
    
    # === GUI SETTINGS ===
    gui_update_interval: int = 1000            # GUI update ทุก 1 วินาที
    enable_real_time_charts: bool = True       # เปิดกราฟเรียลไทม์
    
    # === LOGGING SETTINGS ===
    log_level: str = "INFO"                    # DEBUG, INFO, WARNING, ERROR
    log_to_file: bool = True                   # เซฟ log ลงไฟล์
    log_max_files: int = 10                    # จำนวนไฟล์ log สูงสุด
    
    # === SAFETY SETTINGS ===
    max_drawdown_percent: float = 20.0         # Drawdown สูงสุด 20%
    max_daily_trades: int = 200                # จำนวน trades สูงสุดต่อวัน
    emergency_stop_enabled: bool = True        # ระบบหยุดฉุกเฉิน
    
    def __post_init__(self):
        """ตรวจสอบการตั้งค่าหลังจากสร้าง instance"""
        self._validate_settings()
    
    def _validate_settings(self):
        """ตรวจสอบความถูกต้องของการตั้งค่า"""
        
        # ตรวจสอบ Trading Mode ต้องเป็น LIVE เท่านั้น
        if self.trading_mode != TradingMode.LIVE:
            raise ValueError("❌ ระบบรองรับเฉพาะ LIVE Trading เท่านั้น!")
        
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
        # หากใช้การเชื่อมต่อที่มีอยู่แล้ว ไม่ต้องตรวจสอบ credentials
        if self.use_existing_connection:
            return True
            
        required_fields = [self.mt5_server, self.mt5_login, self.mt5_password]
        missing_fields = []
        
        if not self.mt5_login:
            missing_fields.append("mt5_login")
        if not self.mt5_password:
            missing_fields.append("mt5_password")  
        if not self.mt5_server:
            missing_fields.append("mt5_server")
            
        if missing_fields:
            print(f"❌ ข้อมูล MT5 ที่ขาดหายไป: {', '.join(missing_fields)}")
            return False
            
        return True
    
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
    
    def get_mt5_info_string(self) -> str:
        """สร้าง string แสดงข้อมูล MT5"""
        if self.use_existing_connection:
            return "MT5: ใช้การเชื่อมต่อที่มีอยู่แล้ว"
        elif self.validate_mt5_settings():
            return f"Login: {self.mt5_login} | Server: {self.mt5_server}"
        else:
            return "MT5 Settings: ❌ Not Configured"
    
    def set_mt5_credentials(self, login: int, password: str, server: str, path: Optional[str] = None):
        """
        ตั้งค่าข้อมูล MT5 ใหม่
        
        Args:
            login: หมายเลขบัญชี MT5
            password: รหัสผ่าน MT5  
            server: ชื่อ Server MT5
            path: path ไปยัง terminal64.exe (optional)
        """
        self.mt5_login = login
        self.mt5_password = password
        self.mt5_server = server
        self.mt5_path = path
        self.use_existing_connection = False  # เปลี่ยนเป็น manual login
        
        print(f"✅ อัพเดทข้อมูล MT5: {self.get_mt5_info_string()}")

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

def setup_mt5_connection(login: int, password: str, server: str, path: Optional[str] = None) -> SystemSettings:
    """
    ตั้งค่าการเชื่อมต่อ MT5 แบบง่าย
    
    Args:
        login: หมายเลขบัญชี MT5
        password: รหัสผ่าน MT5
        server: ชื่อ Server MT5  
        path: path ไปยัง terminal64.exe (optional)
        
    Returns:
        SystemSettings instance ที่ตั้งค่าแล้ว
        
    Example:
        >>> settings = setup_mt5_connection(
        ...     login=51050633,
        ...     password="YourPassword123", 
        ...     server="MetaQuotes-Demo"
        ... )
    """
    settings = get_system_settings()
    settings.set_mt5_credentials(login, password, server, path)
    return settings

# === MT5 CONFIGURATION HELPER ===
def get_common_mt5_servers() -> List[str]:
    """รายชื่อ MT5 Server ที่ใช้กันทั่วไป"""
    return [
        # Demo Servers
        "MetaQuotes-Demo",
        "MetaQuotes-Server", 
        
        # Popular Brokers
        "ICMarkets-Live-01", "ICMarkets-Live-02", "ICMarkets-Live-16",
        "FTMO-Server", "FTMO-Server2", "FTMO-Demo",
        "XM-Server", "XM-Real", "XM-Demo", 
        "Exness-MT5Real", "Exness-MT5Real2", "Exness-Demo",
        "Admiral-Real", "Admiral-Demo",
        "FXCM-USDReal", "FXCM-Demo",
        "Pepperstone-Live", "Pepperstone-Demo",
        "Oanda-v20Live", "Oanda-Demo",
        
        # Thai Brokers
        "FSMSmart-Server", "FSMSmart-Demo",
        "KTZMaximusLive", "KTZMaximus-Demo"
    ]

def print_mt5_setup_instructions():
   """แสดงคำแนะนำการตั้งค่า MT5"""
   print("""
🔧 MT5 AUTO-DETECT CONNECTION SETUP
===================================

✅ วิธีใช้งาน (แนะนำ):
1. เปิด MetaTrader 5
2. Login เข้าบัญชีของคุณให้เรียบร้อย
3. เปิด AutoTrading (กดปุ่ม Algo Trading)
4. รันโปรแกรม - ระบบจะ Auto-detect การเชื่อมต่อ

🔧 หากต้องการ Manual Setup:
ใช้ฟังก์ชัน setup_mt5_connection():

from config.settings import setup_mt5_connection
settings = setup_mt5_connection(
   login=your_account_number,
   password="your_password", 
   server="your_server_name"
)

📋 ตรวจสอบการตั้งค่า:
- MT5 เปิดอยู่และเชื่อมต่อ Server แล้ว
- AutoTrading เปิดอยู่ (สีเขียว)
- Symbol XAUUSD พร้อมใช้งาน
- ไม่มี Error ใน Expert/Journal tab
   """)

# Auto-print setup instructions when imported
if __name__ == "__main__":
   print_mt5_setup_instructions()
