#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORE TRADING SYSTEM - Full Version with Detailed Error Logging
============================================================
ระบบเทรดเต็มพร้อม Error Logging รายละเอียด
"""

import threading
import time
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import traceback

# Internal imports with error catching
try:
    from config.settings import SystemSettings, MarketSession
    print("✅ config.settings imported successfully")
except Exception as e:
    print(f"❌ config.settings import error: {e}")
    traceback.print_exc()

try:
    from config.trading_params import get_trading_parameters
    print("✅ config.trading_params imported successfully")
except Exception as e:
    print(f"❌ config.trading_params import error: {e}")
    traceback.print_exc()

try:
    from utilities.professional_logger import setup_component_logger
    print("✅ utilities.professional_logger imported successfully")
except Exception as e:
    print(f"❌ utilities.professional_logger import error: {e}")
    traceback.print_exc()

try:
    from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity
    print("✅ utilities.error_handler imported successfully")
except Exception as e:
    print(f"❌ utilities.error_handler import error: {e}")
    traceback.print_exc()

class SystemState(Enum):
    """สถานะของระบบเทรด"""
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    TRADING_ACTIVE = "TRADING_ACTIVE"
    RECOVERY_MODE = "RECOVERY_MODE"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    SHUTTING_DOWN = "SHUTTING_DOWN"

class TradingPhase(Enum):
    """ช่วงการเทรด"""
    MARKET_ANALYSIS = "MARKET_ANALYSIS"
    SIGNAL_GENERATION = "SIGNAL_GENERATION"
    ORDER_EXECUTION = "ORDER_EXECUTION"
    POSITION_MONITORING = "POSITION_MONITORING"
    RECOVERY_EXECUTION = "RECOVERY_EXECUTION"
    PROFIT_TAKING = "PROFIT_TAKING"

@dataclass
class SystemMetrics:
    """เก็บข้อมูลสถิติของระบบ"""
    total_positions: int = 0
    active_positions: int = 0
    recovery_positions: int = 0
    total_profit: float = 0.0
    daily_volume: float = 0.0
    system_uptime: timedelta = field(default_factory=timedelta)
    last_signal_time: Optional[datetime] = None
    last_order_time: Optional[datetime] = None
    emergency_stops: int = 0

class IntelligentTradingSystem:
    """🧠 Intelligent Trading System - ระบบเทรดหลัก"""
    
    def __init__(self, settings: SystemSettings, logger):
        self.settings = settings
        self.logger = logger
        
        # Try to get trading parameters
        try:
            self.trading_params = get_trading_parameters()
            self.logger.info("✅ Trading parameters loaded successfully")
        except Exception as e:
            self.logger.error(f"❌ Trading parameters error: {e}")
            self.trading_params = None
        
        # System State
        self.system_state = SystemState.INITIALIZING
        self.current_phase = TradingPhase.MARKET_ANALYSIS
        self.system_metrics = SystemMetrics()
        self.start_time = datetime.now()
        
        # Threading
        self.system_active = False
        self.threads = {}
        self.thread_lock = threading.Lock()
        
        # Event System
        self.event_queue = queue.Queue()
        self.event_handlers = {}
        
        # Component References
        self.position_tracker = None
        self.profit_optimizer = None
        self.signal_generator = None
        self.order_executor = None
        self.market_analyzer = None
        self.recovery_engine = None
        
        # Control Flags
        self.trading_enabled = False
        self.recovery_enabled = True
        self.emergency_stop_triggered = False
        
        self.logger.info("🧠 เริ่มต้น Intelligent Trading System")
        
    def initialize_system(self) -> bool:
        """🚀 เริ่มต้นระบบทั้งหมด"""
        try:
            self.logger.info("🔧 กำลังเริ่มต้นระบบ Components...")
            
            # Initialize core components with detailed logging
            success_count = self._initialize_components()
            
            if success_count >= 2:  # At least position_tracker and profit_optimizer
                self.system_state = SystemState.READY
                self.logger.info(f"✅ ระบบเริ่มต้นเสร็จสิ้น - โหลดได้ {success_count} components")
                return True
            else:
                self.logger.error(f"❌ โหลด Components ได้เพียง {success_count}/6 - ระบบไม่พร้อม")
                self.system_state = SystemState.EMERGENCY_STOP
                return False
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเริ่มต้นระบบ: {e}")
            traceback.print_exc()
            self.system_state = SystemState.EMERGENCY_STOP
            return False
    
    def _initialize_components(self) -> int:
        """เริ่มต้น Components ทั้งหมดพร้อม Error Logging"""
        success_count = 0
        
        # === POSITION MANAGEMENT ===
        self.logger.info("📊 กำลังโหลด Position Management...")
        try:
            from position_management.position_tracker import get_position_tracker
            self.position_tracker = get_position_tracker()
            self.logger.info("✅ Position Tracker โหลดสำเร็จ")
            success_count += 1
        except ImportError as e:
            self.logger.error(f"❌ Position Tracker Import Error: {e}")
            traceback.print_exc()
        except Exception as e:
            self.logger.error(f"❌ Position Tracker General Error: {e}")
            traceback.print_exc()
        
        try:
            from position_management.profit_optimizer import get_profit_taker
            self.profit_optimizer = get_profit_taker()
            self.logger.info("✅ Profit Optimizer โหลดสำเร็จ")
            success_count += 1
        except ImportError as e:
            self.logger.error(f"❌ Profit Optimizer Import Error: {e}")
            traceback.print_exc()
        except Exception as e:
            self.logger.error(f"❌ Profit Optimizer General Error: {e}")
            traceback.print_exc()
        
        # === TRADING ENGINES ===
        self.logger.info("🎯 กำลังโหลด Trading Engines...")
        try:
            from adaptive_entries.signal_generator import get_signal_generator
            self.signal_generator = get_signal_generator()
            self.logger.info("✅ Signal Generator โหลดสำเร็จ")
            success_count += 1
        except ImportError as e:
            self.logger.error(f"❌ Signal Generator Import Error: {e}")
            traceback.print_exc()
        except Exception as e:
            self.logger.error(f"❌ Signal Generator General Error: {e}")
            traceback.print_exc()
        
        try:
            from mt5_integration.order_executor import get_smart_order_executor
            self.order_executor = get_smart_order_executor()
            self.logger.info("✅ Order Executor โหลดสำเร็จ")
            success_count += 1
        except ImportError as e:
            self.logger.error(f"❌ Order Executor Import Error: {e}")
            traceback.print_exc()
        except Exception as e:
            self.logger.error(f"❌ Order Executor General Error: {e}")
            traceback.print_exc()
        
        # === MARKET INTELLIGENCE ===
        self.logger.info("🧠 กำลังโหลด Market Intelligence...")
        try:
            from market_intelligence.market_analyzer import get_market_analyzer
            self.market_analyzer = get_market_analyzer()
            self.logger.info("✅ Market Analyzer โหลดสำเร็จ")
            success_count += 1
        except ImportError as e:
            self.logger.error(f"❌ Market Analyzer Import Error: {e}")
            traceback.print_exc()
        except Exception as e:
            self.logger.error(f"❌ Market Analyzer General Error: {e}")
            traceback.print_exc()
        
        try:
            from intelligent_recovery.recovery_engine import get_recovery_engine
            self.recovery_engine = get_recovery_engine()
            self.logger.info("✅ Recovery Engine โหลดสำเร็จ")
            success_count += 1
        except ImportError as e:
            self.logger.error(f"❌ Recovery Engine Import Error: {e}")
            traceback.print_exc()
        except Exception as e:
            self.logger.error(f"❌ Recovery Engine General Error: {e}")
            traceback.print_exc()
        
        self.logger.info(f"📊 สรุปการโหลด Components: {success_count}/6 สำเร็จ")
        return success_count
    
    def start_trading(self) -> bool:
        """🎯 เริ่มการเทรด"""
        if self.system_state != SystemState.READY:
            self.logger.error("❌ ระบบยังไม่พร้อมสำหรับการเทรด")
            return False
        
        try:
            components_started = 0
            
            # Start position tracking
            if self.position_tracker:
                try:
                    self.position_tracker.start_tracking()
                    self.logger.info("✅ Position Tracker เริ่มทำงาน")
                    components_started += 1
                except Exception as e:
                    self.logger.error(f"❌ Position Tracker start error: {e}")
            
            # Start profit optimization
            if self.profit_optimizer:
                try:
                    self.profit_optimizer.start_profit_taking()
                    self.logger.info("✅ Profit Optimizer เริ่มทำงาน")
                    components_started += 1
                except Exception as e:
                    self.logger.error(f"❌ Profit Optimizer start error: {e}")
            
            # Start signal generation
            if self.signal_generator:
                try:
                    self.signal_generator.start_signal_generation()
                    self.logger.info("✅ Signal Generator เริ่มทำงาน")
                    components_started += 1
                except Exception as e:
                    self.logger.error(f"❌ Signal Generator start error: {e}")
            
            # Start market analysis
            if self.market_analyzer:
                try:
                    self.market_analyzer.start_analysis()
                    self.logger.info("✅ Market Analyzer เริ่มทำงาน")
                    components_started += 1
                except Exception as e:
                    self.logger.error(f"❌ Market Analyzer start error: {e}")
            
            # Start recovery engine
            if self.recovery_engine:
                try:
                    self.recovery_engine.start_recovery_engine()
                    self.logger.info("✅ Recovery Engine เริ่มทำงาน")
                    components_started += 1
                except Exception as e:
                    self.logger.error(f"❌ Recovery Engine start error: {e}")
            
            if components_started >= 2:
                self.trading_enabled = True
                self.system_state = SystemState.TRADING_ACTIVE
                self.logger.info(f"🚀 เริ่มการเทรดแล้ว! ({components_started} components active)")
                return True
            else:
                self.logger.error(f"❌ Components เริ่มได้เพียง {components_started}/5 - ไม่เพียงพอ")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเริ่มเทรด: {e}")
            traceback.print_exc()
            return False
    
    def stop_trading(self) -> bool:
        """🛑 หยุดการเทรด"""
        try:
            self.trading_enabled = False
            components_stopped = 0
            
            # Stop signal generation
            if self.signal_generator:
                try:
                    self.signal_generator.stop_signal_generation()
                    self.logger.info("✅ Signal Generator หยุดแล้ว")
                    components_stopped += 1
                except Exception as e:
                    self.logger.error(f"❌ Signal Generator stop error: {e}")
            
            # Stop market analysis
            if self.market_analyzer:
                try:
                    self.market_analyzer.stop_analysis()
                    self.logger.info("✅ Market Analyzer หยุดแล้ว")
                    components_stopped += 1
                except Exception as e:
                    self.logger.error(f"❌ Market Analyzer stop error: {e}")
            
            # Stop recovery engine
            if self.recovery_engine:
                try:
                    self.recovery_engine.stop_recovery_engine()
                    self.logger.info("✅ Recovery Engine หยุดแล้ว")
                    components_stopped += 1
                except Exception as e:
                    self.logger.error(f"❌ Recovery Engine stop error: {e}")
            
            self.system_state = SystemState.READY
            self.logger.info(f"🛑 หยุดการเทรดแล้ว ({components_stopped} components stopped)")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการหยุดเทรด: {e}")
            traceback.print_exc()
            return False
    
    def emergency_stop(self):
        """🚨 หยุดฉุกเฉิน"""
        self.emergency_stop_triggered = True
        self.trading_enabled = False
        self.system_state = SystemState.EMERGENCY_STOP
        
        self.logger.critical("🚨 EMERGENCY STOP ACTIVATED!")
        self.stop_trading()
    
    def shutdown_system(self):
        """🔌 ปิดระบบ"""
        self.logger.info("🔌 กำลังปิดระบบ...")
        self.system_state = SystemState.SHUTTING_DOWN
        
        # Stop trading
        self.stop_trading()
        
        # Stop background threads
        self.system_active = False
        
        # Stop components
        try:
            if self.profit_optimizer:
                self.profit_optimizer.stop_profit_taking()
            if self.position_tracker:
                self.position_tracker.stop_tracking()
        except Exception as e:
            self.logger.error(f"❌ Shutdown error: {e}")
        
        self.logger.info("✅ ปิดระบบเสร็จสิ้น")
    
    def get_system_status(self) -> Dict[str, Any]:
        """ดึงสถานะระบบ"""
        component_status = {
            'position_tracker': self.position_tracker is not None,
            'profit_optimizer': self.profit_optimizer is not None,
            'signal_generator': self.signal_generator is not None,
            'order_executor': self.order_executor is not None,
            'market_analyzer': self.market_analyzer is not None,
            'recovery_engine': self.recovery_engine is not None
        }
        
        components_loaded = sum(component_status.values())
        
        return {
            'state': self.system_state.value,
            'phase': self.current_phase.value,
            'trading_enabled': self.trading_enabled,
            'components_loaded': f"{components_loaded}/6",
            'component_status': component_status,
            'metrics': {
                'total_positions': self.system_metrics.total_positions,
                'active_positions': self.system_metrics.active_positions,
                'total_profit': self.system_metrics.total_profit,
                'daily_volume': self.system_metrics.daily_volume,
                'uptime': str(datetime.now() - self.start_time)
            }
        }
    
    def get_current_positions(self) -> List[Any]:
        """ดึงรายการ Position ปัจจุบัน"""
        if self.position_tracker:
            try:
                return self.position_tracker.get_all_positions()
            except Exception as e:
                self.logger.error(f"❌ Get positions error: {e}")
                return []
        return []

print("✅ IntelligentTradingSystem class defined successfully")