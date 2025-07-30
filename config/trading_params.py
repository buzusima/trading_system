#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRADING PARAMETERS - Auto Gold Symbol Support
=============================================
ไฟล์การตั้งค่าพารามิเตอร์ที่รองรับการหา Gold Symbol อัตโนมัติ
ปรับให้ใช้นามสกุลทองที่โบรกเกอร์มีจริง

🔧 การปรับปรุง:
- เพิ่ม Auto Gold Symbol Detection
- รองรับ XAUUSD, GOLD, GOLDUSD, etc.
- ปรับ Symbol ตามโบรกเกอร์อัตโนมัติ
"""

import threading
import json
from datetime import time, datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Tuple

# Import Gold Symbol Detector
try:
    from mt5_integration.gold_symbol_detector import auto_detect_gold_symbol
    GOLD_DETECTOR_AVAILABLE = True
except ImportError:
    GOLD_DETECTOR_AVAILABLE = False
    def auto_detect_gold_symbol():
        return "XAUUSD.v"  # Fallback

# ===== ENUMS - Trading Logic Definitions =====

class EntryStrategy(Enum):
    """กลยุทธ์การเข้า Position"""
    TREND_FOLLOWING = "TREND_FOLLOWING"
    MEAN_REVERSION = "MEAN_REVERSION"
    BREAKOUT_FALSE = "BREAKOUT_FALSE"
    NEWS_REACTION = "NEWS_REACTION"
    SCALPING_FAST = "SCALPING_FAST"
    GRID_ENTRY = "GRID_ENTRY"
    AUTO_SELECT = "AUTO_SELECT"

class RecoveryMethod(Enum):
    """วิธีการ Recovery Position"""
    MARTINGALE_SMART = "MARTINGALE_SMART"
    GRID_INTELLIGENT = "GRID_INTELLIGENT"
    HEDGING_ADVANCED = "HEDGING_ADVANCED"
    AVERAGING_INTELLIGENT = "AVERAGING_INTELLIGENT"
    CORRELATION_RECOVERY = "CORRELATION_RECOVERY"
    QUICK_RECOVERY = "QUICK_RECOVERY"
    CONSERVATIVE_RECOVERY = "CONSERVATIVE_RECOVERY"
    AUTO_SELECT = "AUTO_SELECT"

class MarketCondition(Enum):
    """สภาพตลาด"""
    TRENDING_STRONG = "TRENDING_STRONG"
    TRENDING_WEAK = "TRENDING_WEAK"
    RANGING_TIGHT = "RANGING_TIGHT"
    RANGING_WIDE = "RANGING_WIDE"
    VOLATILE_HIGH = "VOLATILE_HIGH"
    VOLATILE_NEWS = "VOLATILE_NEWS"
    QUIET_LOW = "QUIET_LOW"
    UNKNOWN = "UNKNOWN"

class SessionType(Enum):
    """ประเภทเซสชัน"""
    ASIAN = "ASIAN"
    LONDON = "LONDON"
    NY = "NY"
    OVERLAP = "OVERLAP"

class TimeFrame(Enum):
    """กรอบเวลา"""
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"

# ===== DATA CLASSES - Trading Parameters =====

@dataclass
class VolumeSettings:
    """การตั้งค่าเกี่ยวกับ Volume"""
    base_lot_size: float = 0.01
    max_lot_size: float = 1.0
    daily_volume_target_min: float = 50.0
    daily_volume_target_max: float = 100.0
    volume_multiplier_recovery: float = 1.5
    max_positions_per_direction: int = 10

@dataclass
class RiskSettings:
    """การตั้งค่าเกี่ยวกับความเสี่ยง"""
    use_stop_loss: bool = False
    use_take_profit: bool = False
    max_drawdown_percent: float = 20.0
    max_daily_loss: float = 1000.0
    recovery_mandatory: bool = True
    max_recovery_attempts: int = 100
    emergency_close_threshold: float = 50.0

@dataclass
class EntrySettings:
    """การตั้งค่าการเข้า Position"""
    min_entry_gap_seconds: int = 10
    max_entries_per_minute: int = 6
    max_entries_per_hour: int = 50
    signal_confidence_min: float = 0.6
    market_condition_weight: float = 0.7
@dataclass
class EntrySettings:
    """การตั้งค่าการเข้า Position"""
    min_entry_gap_seconds: int = 10
    max_entries_per_minute: int = 6
    max_entries_per_hour: int = 50
    signal_confidence_min: float = 0.6
    market_condition_weight: float = 0.7
    session_weight: float = 0.3

@dataclass
class RecoverySettings:
    """การตั้งค่า Recovery System"""
    martingale_multiplier: float = 1.5
    grid_step_points: int = 100
    hedge_activation_loss: float = 50.0
    averaging_max_positions: int = 5
    recovery_timeout_hours: int = 24
    correlation_threshold: float = 0.8

@dataclass
class SessionSettings:
    """การตั้งค่าแต่ละ Session"""
    name: str
    start_time: time
    end_time: time
    preferred_strategies: List[EntryStrategy]
    preferred_recovery: List[RecoveryMethod]
    max_concurrent_positions: int
    volume_multiplier: float
    volatility_expectation: str

@dataclass
class SymbolSettings:
    """การตั้งค่า Symbol (รองรับ Auto Detection)"""
    primary_symbol: str = ""
    alternative_symbols: List[str] = field(default_factory=list)
    auto_detect_enabled: bool = True
    symbol_verified: bool = False
    last_detection_time: Optional[datetime] = None
    detection_notes: str = ""

# ===== TRADING LOGIC MAPPING =====

class TradingLogic:
    """Trading Logic Configuration"""
    
    # Strategy Selection Logic
    STRATEGY_SELECTION = {
        MarketCondition.TRENDING_STRONG: {
            'primary': EntryStrategy.TREND_FOLLOWING,
            'secondary': EntryStrategy.GRID_ENTRY,
            'recovery': RecoveryMethod.GRID_INTELLIGENT,
            'confidence': 0.9
        },
        MarketCondition.TRENDING_WEAK: {
            'primary': EntryStrategy.TREND_FOLLOWING,
            'secondary': EntryStrategy.MEAN_REVERSION,
            'recovery': RecoveryMethod.MARTINGALE_SMART,
            'confidence': 0.7
        },
        MarketCondition.RANGING_TIGHT: {
            'primary': EntryStrategy.SCALPING_FAST,
            'secondary': EntryStrategy.MEAN_REVERSION,
            'recovery': RecoveryMethod.QUICK_RECOVERY,
            'confidence': 0.8
        },
        MarketCondition.RANGING_WIDE: {
            'primary': EntryStrategy.MEAN_REVERSION,
            'secondary': EntryStrategy.GRID_ENTRY,
            'recovery': RecoveryMethod.AVERAGING_INTELLIGENT,
            'confidence': 0.8
        },
        MarketCondition.VOLATILE_HIGH: {
            'primary': EntryStrategy.BREAKOUT_FALSE,
            'secondary': EntryStrategy.NEWS_REACTION,
            'recovery': RecoveryMethod.HEDGING_ADVANCED,
            'confidence': 0.6
        },
        MarketCondition.VOLATILE_NEWS: {
            'primary': EntryStrategy.NEWS_REACTION,
            'secondary': EntryStrategy.BREAKOUT_FALSE,
            'recovery': RecoveryMethod.QUICK_RECOVERY,
            'confidence': 0.5
        },
        MarketCondition.QUIET_LOW: {
            'primary': EntryStrategy.SCALPING_FAST,
            'secondary': EntryStrategy.GRID_ENTRY,
            'recovery': RecoveryMethod.CONSERVATIVE_RECOVERY,
            'confidence': 0.7
        }
    }
    
    # Session-based Configuration
    SESSION_CONFIG = {
        SessionType.ASIAN: {
            'volatility': 'LOW',
            'preferred_strategies': [EntryStrategy.MEAN_REVERSION, EntryStrategy.SCALPING_FAST],
            'preferred_recovery': [RecoveryMethod.CONSERVATIVE_RECOVERY, RecoveryMethod.QUICK_RECOVERY],
            'max_positions': 15,
            'volume_multiplier': 0.8
        },
        SessionType.LONDON: {
            'volatility': 'HIGH',
            'preferred_strategies': [EntryStrategy.TREND_FOLLOWING, EntryStrategy.BREAKOUT_FALSE],
            'preferred_recovery': [RecoveryMethod.GRID_INTELLIGENT, RecoveryMethod.HEDGING_ADVANCED],
            'max_positions': 25,
            'volume_multiplier': 1.2
        },
        SessionType.NY: {
            'volatility': 'HIGH',
            'preferred_strategies': [EntryStrategy.NEWS_REACTION, EntryStrategy.TREND_FOLLOWING],
            'preferred_recovery': [RecoveryMethod.QUICK_RECOVERY, RecoveryMethod.MARTINGALE_SMART],
            'max_positions': 30,
            'volume_multiplier': 1.5
        },
        SessionType.OVERLAP: {
            'volatility': 'VERY_HIGH',
            'preferred_strategies': [EntryStrategy.BREAKOUT_FALSE, EntryStrategy.NEWS_REACTION],
            'preferred_recovery': [RecoveryMethod.HEDGING_ADVANCED, RecoveryMethod.CORRELATION_RECOVERY],
            'max_positions': 35,
            'volume_multiplier': 2.0
        }
    }
    
    # Recovery Configuration
    RECOVERY_CONFIG = {
        RecoveryMethod.MARTINGALE_SMART: {
            'multiplier': 1.5,
            'max_levels': 7,
            'activation_loss': 10.0,
            'risk_level': 'MEDIUM'
        },
        RecoveryMethod.GRID_INTELLIGENT: {
            'grid_step': 100,
            'max_grid_levels': 10,
            'activation_loss': 20.0,
            'risk_level': 'LOW'
        },
        RecoveryMethod.HEDGING_ADVANCED: {
            'hedge_ratio': 1.0,
            'correlation_threshold': 0.8,
            'activation_loss': 50.0,
            'risk_level': 'HIGH'
        },
        RecoveryMethod.AVERAGING_INTELLIGENT: {
            'averaging_step': 50,
            'max_positions': 5,
            'activation_loss': 15.0,
            'risk_level': 'LOW'
        },
        RecoveryMethod.QUICK_RECOVERY: {
            'quick_multiplier': 2.0,
            'max_attempts': 3,
            'activation_loss': 5.0,
            'risk_level': 'HIGH'
        },
        RecoveryMethod.CONSERVATIVE_RECOVERY: {
            'conservative_multiplier': 1.2,
            'max_attempts': 10,
            'activation_loss': 30.0,
            'risk_level': 'LOW'
        }
    }

# ===== MAIN CONFIGURATION CLASS =====

@dataclass
class TradingParameters:
    """พารามิเตอร์การเทรดหลัก (รองรับ Auto Gold Symbol)"""
    
    # Symbol Settings (Auto-detect)
    symbol_settings: SymbolSettings = field(default_factory=SymbolSettings)
    magic_number: int = 123456
    slippage: int = 3
    
    # Volume & Risk Settings
    volume_settings: VolumeSettings = field(default_factory=VolumeSettings)
    risk_settings: RiskSettings = field(default_factory=RiskSettings)
    entry_settings: EntrySettings = field(default_factory=EntrySettings)
    recovery_settings: RecoverySettings = field(default_factory=RecoverySettings)
    
    # Session Configurations
    session_configs: Dict[SessionType, SessionSettings] = field(init=False)
    
    # Trading Logic Access
    trading_logic: TradingLogic = field(default_factory=TradingLogic)
    
    def __post_init__(self):
        """สร้าง Session Configurations และ Auto-detect Symbol"""
        # สร้าง Session Configurations
        self.session_configs = {
            SessionType.ASIAN: SessionSettings(
                name="Asian Session",
                start_time=time(22, 0),
                end_time=time(8, 0),
                preferred_strategies=[EntryStrategy.MEAN_REVERSION, EntryStrategy.SCALPING_FAST],
                preferred_recovery=[RecoveryMethod.CONSERVATIVE_RECOVERY],
                max_concurrent_positions=15,
                volume_multiplier=0.8,
                volatility_expectation="LOW"
            ),
            SessionType.LONDON: SessionSettings(
                name="London Session",
                start_time=time(15, 0),
                end_time=time(0, 0),
                preferred_strategies=[EntryStrategy.TREND_FOLLOWING, EntryStrategy.BREAKOUT_FALSE],
                preferred_recovery=[RecoveryMethod.GRID_INTELLIGENT],
                max_concurrent_positions=25,
                volume_multiplier=1.2,
                volatility_expectation="HIGH"
            ),
            SessionType.NY: SessionSettings(
                name="New York Session",
                start_time=time(20, 30),
                end_time=time(5, 30),
                preferred_strategies=[EntryStrategy.NEWS_REACTION, EntryStrategy.TREND_FOLLOWING],
                preferred_recovery=[RecoveryMethod.QUICK_RECOVERY],
                max_concurrent_positions=30,
                volume_multiplier=1.5,
                volatility_expectation="HIGH"
            ),
            SessionType.OVERLAP: SessionSettings(
                name="Overlap Session",
                start_time=time(20, 30),
                end_time=time(0, 0),
                preferred_strategies=[EntryStrategy.BREAKOUT_FALSE, EntryStrategy.NEWS_REACTION],
                preferred_recovery=[RecoveryMethod.HEDGING_ADVANCED],
                max_concurrent_positions=35,
                volume_multiplier=2.0,
                volatility_expectation="VERY_HIGH"
            )
        }
        
        # Auto-detect Gold Symbol
        self.auto_detect_gold_symbol()
    
    def auto_detect_gold_symbol(self) -> bool:
        """หา Gold Symbol อัตโนมัติ"""
        try:
            if not self.symbol_settings.auto_detect_enabled:
                return True  # ปิดการ auto-detect
            
            # ตรวจสอบว่าเคย detect ไปแล้วหรือไม่
            if (self.symbol_settings.symbol_verified and 
                self.symbol_settings.last_detection_time and
                (datetime.now() - self.symbol_settings.last_detection_time).total_seconds() < 3600):
                # ใช้ symbol ที่ detect ไว้แล้ว (ภายใน 1 ชั่วโมง)
                return True
            
            print("🔍 กำลังหา Gold Symbol อัตโนมัติ...")
            
            # ใช้ Gold Symbol Detector
            detected_symbol = auto_detect_gold_symbol()
            
            if detected_symbol:
                self.symbol_settings.primary_symbol = detected_symbol
                self.symbol_settings.symbol_verified = True
                self.symbol_settings.last_detection_time = datetime.now()
                self.symbol_settings.detection_notes = f"Auto-detected: {detected_symbol}"
                
                print(f"✅ พบ Gold Symbol: {detected_symbol}")
                return True
            else:
                # Fallback ไปยัง default symbols
                fallback_symbols = ["XAUUSD", "GOLD", "GOLDUSD"]
                for symbol in fallback_symbols:
                    try:
                        import MetaTrader5 as mt5
                        if mt5.symbol_info(symbol):
                            self.symbol_settings.primary_symbol = symbol
                            self.symbol_settings.symbol_verified = False
                            self.symbol_settings.detection_notes = f"Fallback to: {symbol}"
                            print(f"⚠️ ใช้ Fallback Symbol: {symbol}")
                            return True
                    except:
                        continue
                
                print("❌ ไม่พบ Gold Symbol ใดๆ")
                return False
                
        except Exception as e:
            print(f"❌ ข้อผิดพลาดในการหา Gold Symbol: {e}")
            # ใช้ default
            self.symbol_settings.primary_symbol = "XAUUSD.v"
            self.symbol_settings.symbol_verified = False
            self.symbol_settings.detection_notes = f"Error occurred, using default: {e}"
            return False
    
    def get_current_symbol(self) -> str:
        """ดึง Symbol ปัจจุบันที่ใช้"""
        if self.symbol_settings.primary_symbol:
            return self.symbol_settings.primary_symbol
        else:
            # Auto-detect ถ้ายังไม่มี
            self.auto_detect_gold_symbol()
            return self.symbol_settings.primary_symbol or "XAUUSD.v"
    
    def set_symbol(self, symbol: str, verify: bool = True) -> bool:
        """กำหนด Symbol ด้วยตนเอง"""
        try:
            if verify:
                import MetaTrader5 as mt5
                if not mt5.initialize():
                    print("❌ ไม่สามารถเชื่อมต่อ MT5 เพื่อตรวจสอบ Symbol")
                    return False
                
                symbol_info = mt5.symbol_info(symbol)
                if not symbol_info:
                    print(f"❌ ไม่พบ Symbol {symbol}")
                    return False
            
            self.symbol_settings.primary_symbol = symbol
            self.symbol_settings.symbol_verified = verify
            self.symbol_settings.last_detection_time = datetime.now()
            self.symbol_settings.detection_notes = f"Manually set: {symbol}"
            self.symbol_settings.auto_detect_enabled = False  # ปิด auto-detect
            
            print(f"✅ กำหนด Symbol: {symbol}")
            return True
            
        except Exception as e:
            print(f"❌ ไม่สามารถกำหนด Symbol: {e}")
            return False
    
    def enable_auto_detect(self, enable: bool = True):
        """เปิด/ปิด Auto Detection"""
        self.symbol_settings.auto_detect_enabled = enable
        if enable:
            print("✅ เปิด Auto Symbol Detection")
            self.auto_detect_gold_symbol()
        else:
            print("⚠️ ปิด Auto Symbol Detection")
    
    def get_symbol_info(self) -> Dict[str, Any]:
        """ดึงข้อมูล Symbol ปัจจุบัน"""
        return {
            'primary_symbol': self.symbol_settings.primary_symbol,
            'alternative_symbols': self.symbol_settings.alternative_symbols,
            'auto_detect_enabled': self.symbol_settings.auto_detect_enabled,
            'symbol_verified': self.symbol_settings.symbol_verified,
            'last_detection_time': self.symbol_settings.last_detection_time,
            'detection_notes': self.symbol_settings.detection_notes
        }
    
    def get_strategy_for_condition(self, condition: MarketCondition) -> Dict[str, Any]:
        """ดึงกลยุทธ์สำหรับสภาพตลาด"""
        return self.trading_logic.STRATEGY_SELECTION.get(condition, {
            'primary': EntryStrategy.AUTO_SELECT,
            'secondary': EntryStrategy.SCALPING_FAST,
            'recovery': RecoveryMethod.AUTO_SELECT,
            'confidence': 0.5
        })
    
    def get_session_config(self, session: SessionType) -> SessionSettings:
        """ดึงการตั้งค่าของ Session"""
        return self.session_configs.get(session, self.session_configs[SessionType.ASIAN])
    
    def get_recovery_config(self, method: RecoveryMethod) -> Dict[str, Any]:
        """ดึงการตั้งค่า Recovery Method"""
        return self.trading_logic.RECOVERY_CONFIG.get(method, {
            'multiplier': 1.5,
            'max_levels': 5,
            'activation_loss': 20.0,
            'risk_level': 'MEDIUM'
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """แปลงเป็น Dictionary"""
        return {
            'symbol_settings': {
                'primary_symbol': self.symbol_settings.primary_symbol,
                'auto_detect_enabled': self.symbol_settings.auto_detect_enabled,
                'symbol_verified': self.symbol_settings.symbol_verified,
                'detection_notes': self.symbol_settings.detection_notes
            },
            'magic_number': self.magic_number,
            'slippage': self.slippage,
            'volume_settings': self.volume_settings.__dict__,
            'risk_settings': self.risk_settings.__dict__,
            'entry_settings': self.entry_settings.__dict__,
            'recovery_settings': self.recovery_settings.__dict__
        }
    
    def validate_parameters(self) -> Tuple[bool, List[str]]:
        """ตรวจสอบความถูกต้องของพารามิเตอร์"""
        errors = []
        
        # ตรวจสอบ Symbol
        if not self.symbol_settings.primary_symbol:
            errors.append("ไม่มี Primary Symbol")
        
        # ตรวจสอบ Volume Settings
        if self.volume_settings.base_lot_size <= 0:
            errors.append("Base lot size ต้องมากกว่า 0")
        
        if self.volume_settings.daily_volume_target_min <= 0:
            errors.append("Daily volume target ต้องมากกว่า 0")
        
        # ตรวจสอบ Risk Settings
        if self.risk_settings.max_drawdown_percent <= 0:
            errors.append("Max drawdown percent ต้องมากกว่า 0")
        
        # ตรวจสอบ Entry Settings
        if self.entry_settings.min_entry_gap_seconds < 1:
            errors.append("Min entry gap ต้องอย่างน้อย 1 วินาที")
        
        return len(errors) == 0, errors

# ===== GLOBAL INSTANCE AND FUNCTIONS =====

# สร้าง Global Instance
_trading_parameters_instance = None
_trading_parameters_lock = threading.Lock()

def get_trading_parameters() -> TradingParameters:
    """ดึง Trading Parameters (Singleton Pattern)"""
    global _trading_parameters_instance
    
    if _trading_parameters_instance is None:
        with _trading_parameters_lock:
            if _trading_parameters_instance is None:
                _trading_parameters_instance = TradingParameters()
    
    return _trading_parameters_instance

def reset_trading_parameters():
    """รีเซ็ต Trading Parameters (สำหรับ Testing)"""
    global _trading_parameters_instance
    with _trading_parameters_lock:
        _trading_parameters_instance = None

def get_current_gold_symbol() -> str:
    """ดึง Gold Symbol ปัจจุบัน"""
    params = get_trading_parameters()
    return params.get_current_symbol()

def set_gold_symbol(symbol: str, verify: bool = True) -> bool:
    """กำหนด Gold Symbol"""
    params = get_trading_parameters()
    return params.set_symbol(symbol, verify)

def force_symbol_detection() -> str:
    """บังคับหา Symbol ใหม่"""
    params = get_trading_parameters()
    params.symbol_settings.symbol_verified = False
    params.symbol_settings.last_detection_time = None
    params.auto_detect_gold_symbol()
    return params.get_current_symbol()

# ===== COMPATIBILITY EXPORTS =====

# Export สำหรับ backwards compatibility
TRADING_LOGIC = TradingLogic()

# Export main functions และ classes
__all__ = [
    'TradingParameters',
    'TradingLogic',
    'EntryStrategy',
    'RecoveryMethod', 
    'MarketCondition',
    'SessionType',
    'TimeFrame',
    'SymbolSettings',
    'VolumeSettings',
    'RiskSettings',
    'EntrySettings',
    'RecoverySettings',
    'SessionSettings',
    'get_trading_parameters',
    'reset_trading_parameters',
    'get_current_gold_symbol',
    'set_gold_symbol',
    'force_symbol_detection',
    'TRADING_LOGIC'
]

# ===== TESTING SECTION =====

if __name__ == "__main__":
    """ทดสอบ Auto Gold Symbol Detection"""
    
    print("🧪 ทดสอบ Auto Gold Symbol Detection")
    print("=" * 50)
    
    # ทดสอบการสร้าง instance
    params = get_trading_parameters()
    print(f"✅ สร้าง Trading Parameters")
    
    # แสดงข้อมูล Symbol
    symbol_info = params.get_symbol_info()
    print(f"🎯 Current Symbol: {symbol_info['primary_symbol']}")
    print(f"🔍 Auto Detect: {symbol_info['auto_detect_enabled']}")
    print(f"✅ Verified: {symbol_info['symbol_verified']}")
    print(f"📝 Notes: {symbol_info['detection_notes']}")
    
    # ทดสอบการเปลี่ยน symbol
    print(f"\n🔄 ทดสอบการกำหนด Symbol ใหม่...")
    if params.set_symbol("GOLD", verify=False):
        print(f"✅ เปลี่ยนเป็น: {params.get_current_symbol()}")
    
    # ทดสอบการ force detection
    print(f"\n🔍 ทดสอบ Force Detection...")
    new_symbol = force_symbol_detection()
    print(f"🎯 Symbol หลังจาก Force Detection: {new_symbol}")
    
    print("\n🎯 Gold Symbol Auto-Detection พร้อมใช้งาน!")