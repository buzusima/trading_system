#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORE TRADING SYSTEM - Intelligent Trading System Core
==================================================
ระบบเทรดหลักที่รวม Logic ทั้งหมดเข้าด้วยกัน
รับผิดชอบการประสานงานระหว่างระบบต่างๆ และจัดการ Threading

🧠 หน้าที่หลัก:
- จัดการระบบเทรดทั้งหมด (Position, Signal, Recovery)
- ประสานงานระหว่าง Components ต่างๆ
- จัดการ Threading และ State Management
- Intelligent Position Management
- Market Analysis และ Strategy Selection

🎯 Architecture:
- Single Responsibility: จัดการระบบเทรดเท่านั้น
- Thread Safe: ใช้ Lock และ Queue สำหรับ Thread Communication
- Event Driven: ใช้ Event System สำหรับการสื่อสาร
- Recovery Focused: แก้ไม้ทุก Position ไม่มี Stop Loss
"""

import threading
import time
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

# Internal imports
from config.settings import SystemSettings, MarketSession
from config.trading_params import get_trading_parameters
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

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
    """
    🧠 Intelligent Trading System - ระบบเทรดหลัก
    
    ระบบเทรดที่อัจฉริยะสำหรับ Gold Trading
    รวมการจัดการทุกระบบไว้ในที่เดียว
    """
    
    def __init__(self, settings: SystemSettings, logger):
        self.settings = settings
        self.logger = logger
        self.trading_params = get_trading_parameters()
        
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
        
        # Component References (will be initialized)
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
        
        # Timing Control
        self.last_analysis_time = 0
        self.last_signal_time = 0
        self.last_order_time = 0
        self.analysis_interval = 30  # วินาที
        self.signal_cooldown = 10    # วินาที
        self.order_cooldown = 15     # วินาที
        
        self.logger.info("🧠 เริ่มต้น Intelligent Trading System")
        
    def initialize_system(self) -> bool:
        """🚀 เริ่มต้นระบบทั้งหมด"""
        try:
            self.logger.info("🔧 กำลังเริ่มต้นระบบ Components...")
            
            # Initialize core components
            self._initialize_components()
            
            # Setup event handlers
            self._setup_event_handlers()
            
            # Start background threads
            self._start_background_threads()
            
            self.system_state = SystemState.READY
            self.logger.info("✅ ระบบเริ่มต้นเสร็จสิ้น - พร้อมใช้งาน")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเริ่มต้นระบบ: {e}")
            self.system_state = SystemState.EMERGENCY_STOP
            return False
    
    def _initialize_components(self):
        """เริ่มต้น Components ทั้งหมด"""
        try:
            # Position Management
            from position_management.position_tracker import get_position_tracker
            from position_management.profit_optimizer import get_profit_taker
            
            self.position_tracker = get_position_tracker()
            self.profit_optimizer = get_profit_taker()
            
            # Trading Engines
            from adaptive_entries.signal_generator import get_signal_generator
            from mt5_integration.order_executor import get_smart_order_executor
            
            self.signal_generator = get_signal_generator()
            self.order_executor = get_smart_order_executor()
            
            # Market Intelligence
            from market_intelligence.market_analyzer import get_market_analyzer
            from intelligent_recovery.recovery_engine import get_recovery_engine
            
            self.market_analyzer = get_market_analyzer()
            self.recovery_engine = get_recovery_engine()
            
            self.logger.info("✅ เริ่มต้น Components ทั้งหมดสำเร็จ")
            
        except ImportError as e:
            self.logger.warning(f"⚠️ บาง Component ยังไม่พร้อม: {e}")
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเริ่มต้น Components: {e}")
            raise
    
    def _setup_event_handlers(self):
        """ตั้งค่า Event Handlers"""
        self.event_handlers = {
            'position_opened': self._handle_position_opened,
            'position_closed': self._handle_position_closed,
            'signal_generated': self._handle_signal_generated,
            'market_analysis_complete': self._handle_market_analysis,
            'recovery_needed': self._handle_recovery_needed,
            'emergency_stop': self._handle_emergency_stop
        }
        
        self.logger.info("✅ ตั้งค่า Event Handlers เสร็จสิ้น")
    
    def _start_background_threads(self):
        """เริ่ม Background Threads"""
        threads_to_start = [
            ("SystemMonitor", self._system_monitor_loop),
            ("EventProcessor", self._event_processor_loop),
            ("IntelligentManager", self._intelligent_manager_loop)
        ]
        
        for thread_name, target_func in threads_to_start:
            thread = threading.Thread(
                target=target_func,
                daemon=True,
                name=thread_name
            )
            self.threads[thread_name] = thread
            thread.start()
            
        self.system_active = True
        self.logger.info(f"🚀 เริ่ม Background Threads: {list(self.threads.keys())}")
    
    def start_trading(self) -> bool:
        """🎯 เริ่มการเทรด"""
        if self.system_state != SystemState.READY:
            self.logger.error("❌ ระบบยังไม่พร้อมสำหรับการเทรด")
            return False
        
        try:
            # Start components
            if self.position_tracker:
                self.position_tracker.start_tracking()
            
            if self.profit_optimizer:
                self.profit_optimizer.start_profit_taking()
            
            if self.signal_generator:
                self.signal_generator.start_signal_generation()
            
            # Enable trading
            self.trading_enabled = True
            self.system_state = SystemState.TRADING_ACTIVE
            
            self.logger.info("🚀 เริ่มการเทรดแล้ว!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเริ่มเทรด: {e}")
            return False
    
    def stop_trading(self) -> bool:
        """🛑 หยุดการเทรด"""
        try:
            # Disable trading
            self.trading_enabled = False
            
            # Stop signal generation
            if self.signal_generator:
                self.signal_generator.stop_signal_generation()
            
            self.system_state = SystemState.READY
            self.logger.info("🛑 หยุดการเทรดแล้ว")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการหยุดเทรด: {e}")
            return False
    
    def emergency_stop(self):
        """🚨 หยุดฉุกเฉิน"""
        self.emergency_stop_triggered = True
        self.trading_enabled = False
        self.system_state = SystemState.EMERGENCY_STOP
        
        # Add to event queue
        self.event_queue.put(('emergency_stop', {'timestamp': datetime.now()}))
        
        self.logger.critical("🚨 EMERGENCY STOP ACTIVATED!")
    
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
        except:
            pass
        
        # Wait for threads to finish
        for thread_name, thread in self.threads.items():
            if thread.is_alive():
                thread.join(timeout=5.0)
                self.logger.info(f"🛑 หยุด Thread: {thread_name}")
        
        self.logger.info("✅ ปิดระบบเสร็จสิ้น")
    
    def _intelligent_manager_loop(self):
        """🧠 Main Intelligent Manager Loop"""
        self.logger.info("🧠 เริ่ม Intelligent Manager Loop")
        
        while self.system_active:
            try:
                if not self.trading_enabled:
                    time.sleep(1)
                    continue
                
                current_time = time.time()
                
                # Phase 1: Market Analysis
                if current_time - self.last_analysis_time > self.analysis_interval:
                    self._perform_market_analysis()
                    self.last_analysis_time = current_time
                
                # Phase 2: Signal Generation & Order Execution
                if (self.trading_enabled and 
                    current_time - self.last_signal_time > self.signal_cooldown):
                    self._process_signals_and_orders()
                    self.last_signal_time = current_time
                
                # Phase 3: Position Monitoring & Recovery
                self._monitor_positions_and_recovery()
                
                # Phase 4: Update Metrics
                self._update_system_metrics()
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Intelligent Manager: {e}")
                time.sleep(5)
    
    def _perform_market_analysis(self):
        """📊 ทำการวิเคราะห์ตลาด"""
        if self.market_analyzer:
            try:
                analysis = self.market_analyzer.analyze_market()
                if analysis:
                    self.event_queue.put(('market_analysis_complete', analysis))
            except Exception as e:
                self.logger.error(f"❌ Market Analysis Error: {e}")
    
    def _process_signals_and_orders(self):
        """🎯 ประมวลผล Signals และ Orders"""
        if not self.signal_generator or not self.order_executor:
            return
        
        try:
            # Get latest signals
            signals = self.signal_generator.get_latest_signals()
            
            for signal in signals:
                # Check order cooldown
                if time.time() - self.last_order_time < self.order_cooldown:
                    continue
                
                # Execute order
                success = self.order_executor.execute_signal(signal)
                if success:
                    self.last_order_time = time.time()
                    self.event_queue.put(('signal_executed', signal))
                    
        except Exception as e:
            self.logger.error(f"❌ Signal Processing Error: {e}")
    
    def _monitor_positions_and_recovery(self):
        """🔄 ติดตาม Position และ Recovery"""
        if not self.position_tracker:
            return
        
        try:
            # Get positions needing recovery
            positions = self.position_tracker.get_positions_needing_recovery()
            
            for position in positions:
                if self.recovery_engine:
                    self.recovery_engine.trigger_recovery(position)
                    
        except Exception as e:
            self.logger.error(f"❌ Position Recovery Error: {e}")
    
    def _update_system_metrics(self):
        """📈 อัพเดท System Metrics"""
        try:
            if self.position_tracker:
                positions = self.position_tracker.get_all_positions()
                self.system_metrics.total_positions = len(positions)
                self.system_metrics.active_positions = len([p for p in positions if p.is_open])
                self.system_metrics.total_profit = sum(p.profit for p in positions)
            
            self.system_metrics.system_uptime = datetime.now() - self.start_time
            
        except Exception as e:
            self.logger.error(f"❌ Metrics Update Error: {e}")
    
    def _system_monitor_loop(self):
        """🔍 System Monitor Loop"""
        while self.system_active:
            try:
                # Monitor system health
                self._check_system_health()
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"❌ System Monitor Error: {e}")
                time.sleep(10)
    
    def _event_processor_loop(self):
        """⚡ Event Processor Loop"""
        while self.system_active:
            try:
                # Process events
                try:
                    event_type, event_data = self.event_queue.get(timeout=1)
                    handler = self.event_handlers.get(event_type)
                    if handler:
                        handler(event_data)
                except queue.Empty:
                    continue
                    
            except Exception as e:
                self.logger.error(f"❌ Event Processor Error: {e}")
                time.sleep(1)
    
    def _check_system_health(self):
        """🏥 ตรวจสอบสุขภาพระบบ"""
        # Check if emergency stop is needed
        if self.emergency_stop_triggered:
            return
        
        # Add health checks here
        pass
    
    # Event Handlers
    def _handle_position_opened(self, data):
        """จัดการเมื่อเปิด Position ใหม่"""
        self.logger.info(f"📈 Position Opened: {data}")
    
    def _handle_position_closed(self, data):
        """จัดการเมื่อปิด Position"""
        self.logger.info(f"📉 Position Closed: {data}")
    
    def _handle_signal_generated(self, data):
        """จัดการเมื่อมี Signal ใหม่"""
        self.logger.info(f"🎯 Signal Generated: {data}")
    
    def _handle_market_analysis(self, data):
        """จัดการผลการวิเคราะห์ตลาด"""
        self.logger.info(f"📊 Market Analysis: {data}")
    
    def _handle_recovery_needed(self, data):
        """จัดการเมื่อต้องการ Recovery"""
        self.logger.info(f"🔄 Recovery Needed: {data}")
    
    def _handle_emergency_stop(self, data):
        """จัดการ Emergency Stop"""
        self.logger.critical(f"🚨 Emergency Stop: {data}")
        self.stop_trading()
    
    # Public Methods for GUI/External Access
    def get_system_status(self) -> Dict[str, Any]:
        """ดึงสถานะระบบ"""
        return {
            'state': self.system_state.value,
            'phase': self.current_phase.value,
            'trading_enabled': self.trading_enabled,
            'metrics': {
                'total_positions': self.system_metrics.total_positions,
                'active_positions': self.system_metrics.active_positions,
                'total_profit': self.system_metrics.total_profit,
                'daily_volume': self.system_metrics.daily_volume,
                'uptime': str(self.system_metrics.system_uptime)
            }
        }
    
    def get_current_positions(self) -> List[Any]:
        """ดึงรายการ Position ปัจจุบัน"""
        if self.position_tracker:
            return self.position_tracker.get_all_positions()
        return []
    
    def force_recovery(self, position_id: str) -> bool:
        """บังคับ Recovery Position"""
        if self.recovery_engine:
            return self.recovery_engine.force_recovery(position_id)
        return False