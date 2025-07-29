#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORE TRADING SYSTEM - REAL IMPLEMENTATION ONLY
==============================================
ระบบเทรดหลักสำหรับ Live Trading เท่านั้น
ลบ Mock Components ทั้งหมด - ใช้ Real MT5 Integration เท่านั้น

🚨 ข้อกำหนดสำคัญ:
- ไม่มี Mock หรือ Simulation ใดๆ
- ใช้ MT5 Live Connection เท่านั้น
- ไม่มี Demo Mode
- Error หากไม่สามารถเชื่อมต่อ MT5
"""

import threading
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import queue
import sys
from pathlib import Path
from collections import defaultdict, deque

# MT5 Integration - Required
import MetaTrader5 as mt5

# Internal imports
from config.settings import get_system_settings
from config.trading_params import get_trading_parameters
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

# Real Components - No Mock Allowed
from market_intelligence.market_analyzer import get_market_analyzer
from adaptive_entries.signal_generator import get_intelligent_signal_generator
from mt5_integration.order_executor import get_smart_order_executor
from position_management.position_tracker import get_enhanced_position_tracker
from intelligent_recovery.recovery_engine import get_recovery_engine
from analytics_engine.performance_tracker import get_performance_tracker

class SystemState(Enum):
    """สถานะของระบบ"""
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"

class ComponentStatus(Enum):
    """สถานะของ Component"""
    NOT_LOADED = "NOT_LOADED"
    LOADING = "LOADING"
    LOADED = "LOADED"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    STOPPED = "STOPPED"

@dataclass
class ComponentInfo:
    """ข้อมูล Component"""
    name: str
    status: ComponentStatus = ComponentStatus.NOT_LOADED
    instance: Optional[Any] = None
    start_time: Optional[datetime] = None
    error_message: str = ""
    dependencies: List[str] = field(default_factory=list)

class RealTradingSystem:
    """Real Trading System - ไม่มี Mock"""
    
    def __init__(self):
        self.logger = setup_component_logger("RealTradingSystem")
        
        # ตรวจสอบ MT5 connection ทันที
        if not mt5.initialize():
            raise RuntimeError("❌ ไม่สามารถเชื่อมต่อ MT5 ได้ - ระบบไม่สามารถทำงานได้")
        
        # ตรวจสอบ account
        account_info = mt5.account_info()
        if not account_info:
            mt5.shutdown()
            raise RuntimeError("❌ ไม่สามารถดึงข้อมูล MT5 Account ได้")
        
        if not account_info.trade_allowed:
            mt5.shutdown()
            raise RuntimeError("❌ Account ไม่อนุญาตให้เทรด")
        
        self.logger.info(f"✅ เชื่อมต่อ MT5 สำเร็จ: {account_info.login} ({account_info.server})")
        
        # System state
        self.system_state = SystemState.INITIALIZING
        self.trading_active = False
        self.start_time: Optional[datetime] = None
        
        # Load settings
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Components registry
        self.components: Dict[str, ComponentInfo] = {
            'market_analyzer': ComponentInfo('Market Analyzer', dependencies=[]),
            'signal_generator': ComponentInfo('Signal Generator', dependencies=['market_analyzer']),
            'order_executor': ComponentInfo('Order Executor', dependencies=[]),
            'position_tracker': ComponentInfo('Position Tracker', dependencies=[]),
            'recovery_engine': ComponentInfo('Recovery Engine', dependencies=['position_tracker', 'order_executor']),
            'performance_tracker': ComponentInfo('Performance Tracker', dependencies=['position_tracker'])
        }
        
        # Component instances
        self.market_analyzer = None
        self.signal_generator = None
        self.order_executor = None
        self.position_tracker = None
        self.recovery_engine = None
        self.performance_tracker = None
        
        # System monitoring
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        self.logger.info("🎯 Real Trading System พร้อมเริ่มต้น (Live Trading Only)")
    
    @handle_trading_errors(ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL)
    def initialize_system(self) -> bool:
        """เริ่มต้นระบบทั้งหมด"""
        try:
            self.logger.info("🚀 เริ่มต้น Real Trading System...")
            
            # Load components ตามลำดับ dependency
            if not self._load_all_components():
                self.system_state = SystemState.ERROR
                return False
            
            # Verify all components
            if not self._verify_all_components():
                self.system_state = SystemState.ERROR
                return False
            
            # Setup component connections
            self._setup_component_connections()
            
            self.system_state = SystemState.READY
            self.logger.info("✅ Real Trading System พร้อมใช้งาน")
            return True
            
        except Exception as e:
            self.system_state = SystemState.ERROR
            self.logger.error(f"❌ ไม่สามารถเริ่มต้นระบบ: {e}")
            traceback.print_exc()
            return False
    
    def _load_all_components(self) -> bool:
        """โหลด Components ทั้งหมด (Real เท่านั้น)"""
        try:
            # 1. Market Analyzer
            self.logger.info("📊 โหลด Market Analyzer...")
            self.components['market_analyzer'].status = ComponentStatus.LOADING
            self.market_analyzer = get_market_analyzer()
            if not self.market_analyzer:
                raise RuntimeError("ไม่สามารถโหลด Market Analyzer ได้")
            self.components['market_analyzer'].instance = self.market_analyzer
            self.components['market_analyzer'].status = ComponentStatus.LOADED
            self.logger.info("✅ Market Analyzer โหลดสำเร็จ")
            
            # 2. Order Executor
            self.logger.info("⚡ โหลด Order Executor...")
            self.components['order_executor'].status = ComponentStatus.LOADING
            self.order_executor = get_smart_order_executor()
            if not self.order_executor:
                raise RuntimeError("ไม่สามารถโหลด Order Executor ได้")
            self.components['order_executor'].instance = self.order_executor
            self.components['order_executor'].status = ComponentStatus.LOADED
            self.logger.info("✅ Order Executor โหลดสำเร็จ")
            
            # 3. Position Tracker
            self.logger.info("📍 โหลด Position Tracker...")
            self.components['position_tracker'].status = ComponentStatus.LOADING
            self.position_tracker = get_enhanced_position_tracker()
            if not self.position_tracker:
                raise RuntimeError("ไม่สามารถโหลด Position Tracker ได้")
            self.components['position_tracker'].instance = self.position_tracker
            self.components['position_tracker'].status = ComponentStatus.LOADED
            self.logger.info("✅ Position Tracker โหลดสำเร็จ")
            
            # 4. Signal Generator (depends on Market Analyzer)
            self.logger.info("🎯 โหลด Signal Generator...")
            self.components['signal_generator'].status = ComponentStatus.LOADING
            self.signal_generator = get_intelligent_signal_generator(
                market_analyzer=self.market_analyzer,
                order_executor=self.order_executor
            )
            if not self.signal_generator:
                raise RuntimeError("ไม่สามารถโหลด Signal Generator ได้")
            self.components['signal_generator'].instance = self.signal_generator
            self.components['signal_generator'].status = ComponentStatus.LOADED
            self.logger.info("✅ Signal Generator โหลดสำเร็จ")
            
            # 5. Recovery Engine (depends on Position Tracker และ Order Executor)
            self.logger.info("🔄 โหลด Recovery Engine...")
            self.components['recovery_engine'].status = ComponentStatus.LOADING
            self.recovery_engine = get_recovery_engine(
                position_tracker=self.position_tracker,
                order_executor=self.order_executor
            )
            if not self.recovery_engine:
                raise RuntimeError("ไม่สามารถโหลด Recovery Engine ได้")
            self.components['recovery_engine'].instance = self.recovery_engine
            self.components['recovery_engine'].status = ComponentStatus.LOADED
            self.logger.info("✅ Recovery Engine โหลดสำเร็จ")
            
            # 6. Performance Tracker (depends on Position Tracker)
            self.logger.info("📈 โหลด Performance Tracker...")
            self.components['performance_tracker'].status = ComponentStatus.LOADING
            self.performance_tracker = get_performance_tracker(
                position_tracker=self.position_tracker
            )
            if not self.performance_tracker:
                raise RuntimeError("ไม่สามารถโหลด Performance Tracker ได้")
            self.components['performance_tracker'].instance = self.performance_tracker
            self.components['performance_tracker'].status = ComponentStatus.LOADED
            self.logger.info("✅ Performance Tracker โหลดสำเร็จ")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถโหลด Components: {e}")
            return False
    
    def _verify_all_components(self) -> bool:
        """ตรวจสอบ Components ทั้งหมด"""
        try:
            for name, component in self.components.items():
                if component.status != ComponentStatus.LOADED:
                    self.logger.error(f"❌ Component {name} ไม่ได้โหลด")
                    return False
                
                if not component.instance:
                    self.logger.error(f"❌ Component {name} ไม่มี instance")
                    return False
                
                # ตรวจสอบ methods ที่จำเป็น
                if not self._verify_component_interface(name, component.instance):
                    self.logger.error(f"❌ Component {name} interface ไม่ถูกต้อง")
                    return False
            
            self.logger.info("✅ ตรวจสอบ Components ทั้งหมดสำเร็จ")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถตรวจสอบ Components: {e}")
            return False
    
    def _verify_component_interface(self, name: str, instance: Any) -> bool:
        """ตรวจสอบ Interface ของ Component"""
        required_methods = {
            'market_analyzer': ['start_analysis', 'stop_analysis', 'get_current_analysis'],
            'signal_generator': ['start_signal_generation', 'stop_signal_generation'],
            'order_executor': ['start_execution_engine', 'stop_execution_engine', 'execute_signal'],
            'position_tracker': ['start_tracking', 'stop_tracking', 'get_all_positions'],
            'recovery_engine': ['start_recovery_engine', 'stop_recovery_engine'],
            'performance_tracker': ['start_tracking', 'stop_tracking']
        }
        
        methods = required_methods.get(name, [])
        
        for method in methods:
            if not hasattr(instance, method):
                self.logger.error(f"❌ Component {name} ขาด method {method}")
                return False
        
        return True
    
    def _setup_component_connections(self):
        """ตั้งค่าการเชื่อมต่อระหว่าง Components"""
        try:
            # Market Analyzer -> Signal Generator callback
            if self.market_analyzer and self.signal_generator:
                if hasattr(self.market_analyzer, 'add_analysis_callback'):
                    self.market_analyzer.add_analysis_callback(
                        self._on_market_analysis_update
                    )
            
            # Position Tracker -> Recovery Engine callback
            if self.position_tracker and self.recovery_engine:
                if hasattr(self.position_tracker, 'add_position_callback'):
                    self.position_tracker.add_position_callback(
                        self._on_position_update
                    )
            
            # Position Tracker -> Performance Tracker callback
            if self.position_tracker and self.performance_tracker:
                if hasattr(self.position_tracker, 'add_position_callback'):
                    self.position_tracker.add_position_callback(
                        self._on_performance_update
                    )
            
            self.logger.info("✅ ตั้งค่าการเชื่อมต่อ Components สำเร็จ")
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถตั้งค่าการเชื่อมต่อ: {e}")
    
    def _on_market_analysis_update(self, analysis):
        """Callback สำหรับ Market Analysis Update"""
        try:
            # Log analysis
            self.logger.info(f"📊 Market Update: {analysis.condition.value} - {analysis.recommended_strategy.value}")
            
            # อัปเดต Strategy ใน Signal Generator ถ้าจำเป็น
            if self.signal_generator and hasattr(self.signal_generator, 'update_strategy'):
                self.signal_generator.update_strategy(analysis)
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน market analysis callback: {e}")
    
    def _on_position_update(self, position_data):
        """Callback สำหรับ Position Update"""
        try:
            # ตรวจสอบว่ามี position ที่ต้อง recovery หรือไม่
            if self.recovery_engine and hasattr(self.recovery_engine, 'check_recovery_needed'):
                self.recovery_engine.check_recovery_needed(position_data)
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน position update callback: {e}")
    
    def _on_performance_update(self, performance_data):
        """Callback สำหรับ Performance Update"""
        try:
            # Log performance
            if 'profit' in performance_data:
                self.logger.info(f"💰 Performance Update: Profit {performance_data['profit']:.2f}")
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน performance update callback: {e}")
    
    @handle_trading_errors(ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL)
    def start_trading(self) -> bool:
        """เริ่มการเทรด (Live Trading เท่านั้น)"""
        if self.system_state != SystemState.READY:
            self.logger.error("❌ ระบบยังไม่พร้อม - ไม่สามารถเริ่มการเทรดได้")
            return False
        
        if self.trading_active:
            self.logger.warning("⚠️ การเทรดเปิดอยู่แล้ว")
            return True
        
        try:
            self.logger.info("🚀 เริ่มการเทรด (LIVE TRADING)...")
            
            # เริ่มต้น components ตามลำดับ
            components_started = 0
            
            # 1. Market Analyzer
            if self.market_analyzer.start_analysis():
                self.components['market_analyzer'].status = ComponentStatus.RUNNING
                self.components['market_analyzer'].start_time = datetime.now()
                components_started += 1
                self.logger.info("✅ Market Analyzer เริ่มทำงาน")
            else:
                raise RuntimeError("ไม่สามารถเริ่ม Market Analyzer")
            
            # 2. Position Tracker
            if self.position_tracker.start_tracking():
                self.components['position_tracker'].status = ComponentStatus.RUNNING
                self.components['position_tracker'].start_time = datetime.now()
                components_started += 1
                self.logger.info("✅ Position Tracker เริ่มทำงาน")
            else:
                raise RuntimeError("ไม่สามารถเริ่ม Position Tracker")
            
            # 3. Order Executor
            if self.order_executor.start_execution_engine():
                self.components['order_executor'].status = ComponentStatus.RUNNING
                self.components['order_executor'].start_time = datetime.now()
                components_started += 1
                self.logger.info("✅ Order Executor เริ่มทำงาน")
            else:
                raise RuntimeError("ไม่สามารถเริ่ม Order Executor")
            
            # 4. Recovery Engine
            if self.recovery_engine.start_recovery_engine():
                self.components['recovery_engine'].status = ComponentStatus.RUNNING
                self.components['recovery_engine'].start_time = datetime.now()
                components_started += 1
                self.logger.info("✅ Recovery Engine เริ่มทำงาน")
            else:
                raise RuntimeError("ไม่สามารถเริ่ม Recovery Engine")
            
            # 5. Performance Tracker
            if self.performance_tracker.start_tracking():
                self.components['performance_tracker'].status = ComponentStatus.RUNNING
                self.components['performance_tracker'].start_time = datetime.now()
                components_started += 1
                self.logger.info("✅ Performance Tracker เริ่มทำงาน")
            else:
                raise RuntimeError("ไม่สามารถเริ่ม Performance Tracker")
            
            # 6. Signal Generator (สุดท้าย)
            if self.signal_generator.start_signal_generation():
                self.components['signal_generator'].status = ComponentStatus.RUNNING
                self.components['signal_generator'].start_time = datetime.now()
                components_started += 1
                self.logger.info("✅ Signal Generator เริ่มทำงาน")
            else:
                raise RuntimeError("ไม่สามารถเริ่ม Signal Generator")
            
            # เริ่ม system monitoring
            self._start_system_monitoring()
            
            # อัปเดตสถานะ
            self.system_state = SystemState.RUNNING
            self.trading_active = True
            self.start_time = datetime.now()
            
            self.logger.info(f"🎯 เริ่มการเทรดสำเร็จ - Components: {components_started}/6")
            self.logger.info("⚠️ ระบบกำลังเทรดด้วยเงินจริงใน MT5 Live Account")
            
            return True
            
        except Exception as e:
            self.system_state = SystemState.ERROR
            self.logger.error(f"❌ ไม่สามารถเริ่มการเทรด: {e}")
            # พยายามหยุด components ที่เริ่มแล้ว
            self._emergency_stop_all_components()
            return False
    
    @handle_trading_errors(ErrorCategory.SYSTEM, ErrorSeverity.HIGH)
    def stop_trading(self) -> bool:
        """หยุดการเทรด"""
        if not self.trading_active:
            self.logger.warning("⚠️ การเทรดไม่ได้ทำงานอยู่")
            return True
        
        try:
            self.logger.info("⏹️ หยุดการเทรด...")
            self.system_state = SystemState.STOPPING
            
            # หยุด Signal Generator ก่อน (หยุดการสร้าง signal ใหม่)
            if self.signal_generator:
                self.signal_generator.stop_signal_generation()
                self.components['signal_generator'].status = ComponentStatus.STOPPED
                self.logger.info("⏹️ Signal Generator หยุดแล้ว")
            
            # รอให้ orders ที่ค้างอยู่เสร็จสิ้น
            time.sleep(2)
            
            # หยุด components อื่นๆ
            components_to_stop = [
                ('recovery_engine', self.recovery_engine),
                ('order_executor', self.order_executor),
                ('performance_tracker', self.performance_tracker),
                ('position_tracker', self.position_tracker),
                ('market_analyzer', self.market_analyzer)
            ]
            
            for comp_name, comp_instance in components_to_stop:
                if comp_instance:
                    try:
                        if hasattr(comp_instance, 'stop_tracking'):
                            comp_instance.stop_tracking()
                        elif hasattr(comp_instance, 'stop_analysis'):
                            comp_instance.stop_analysis()
                        elif hasattr(comp_instance, 'stop_execution_engine'):
                            comp_instance.stop_execution_engine()
                        elif hasattr(comp_instance, 'stop_recovery_engine'):
                            comp_instance.stop_recovery_engine()
                        
                        self.components[comp_name].status = ComponentStatus.STOPPED
                        self.logger.info(f"⏹️ {comp_name} หยุดแล้ว")
                    except Exception as e:
                        self.logger.error(f"❌ ไม่สามารถหยุด {comp_name}: {e}")
            
            # หยุด system monitoring
            self._stop_system_monitoring()
            
            # อัปเดตสถานะ
            self.trading_active = False
            self.system_state = SystemState.STOPPED
            
            self.logger.info("✅ หยุดการเทรดสำเร็จ")
            return True
            
        except Exception as e:
            self.system_state = SystemState.ERROR
            self.logger.error(f"❌ ไม่สามารถหยุดการเทรด: {e}")
            return False
    
    def _start_system_monitoring(self):
        """เริ่ม System Monitoring"""
        try:
            self.stop_event.clear()
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                name="SystemMonitoringThread",
                daemon=True
            )
            self.monitoring_thread.start()
            self.logger.info("🔍 เริ่ม System Monitoring")
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถเริ่ม System Monitoring: {e}")
    
    def _stop_system_monitoring(self):
        """หยุด System Monitoring"""
        try:
            self.stop_event.set()
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=3.0)
            self.logger.info("⏹️ หยุด System Monitoring")
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถหยุด System Monitoring: {e}")
    
    def _monitoring_loop(self):
        """Loop สำหรับ Monitor ระบบ"""
        last_status_report = datetime.now()
        
        while not self.stop_event.is_set():
            try:
                # ตรวจสอบ MT5 connection
                if not mt5.terminal_info():
                    self.logger.error("❌ การเชื่อมต่อ MT5 ขาดหาย!")
                    self._handle_mt5_disconnection()
                
                # ตรวจสอบ component health
                self._check_component_health()
                
                # รายงานสถานะทุก 30 วินาที
                if (datetime.now() - last_status_report).total_seconds() >= 30:
                    self._log_system_status()
                    last_status_report = datetime.now()
                
                time.sleep(5)  # ตรวจสอบทุก 5 วินาที
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Monitoring Loop: {e}")
                time.sleep(10)
    
    def _check_component_health(self):
        """ตรวจสอบสุขภาพของ Components"""
        for name, component in self.components.items():
            if component.status == ComponentStatus.RUNNING:
                try:
                    # ตรวจสอบว่า component ยังทำงานอยู่หรือไม่
                    if hasattr(component.instance, 'get_status'):
                        status = component.instance.get_status()
                        if not status or status.get('error'):
                            self.logger.warning(f"⚠️ Component {name} มีปัญหา: {status}")
                    
                except Exception as e:
                    self.logger.error(f"❌ ไม่สามารถตรวจสอบ {name}: {e}")
                    component.status = ComponentStatus.ERROR
                    component.error_message = str(e)
    
    def _handle_mt5_disconnection(self):
        """จัดการเมื่อ MT5 disconnected"""
        self.logger.error("🚨 MT5 Disconnected - พยายาม Reconnect...")
        
        # พยายาม reconnect
        for attempt in range(3):
            time.sleep(5)
            if mt5.initialize():
                self.logger.info(f"✅ MT5 Reconnected (ครั้งที่ {attempt + 1})")
                return
        
        # ไม่สามารถ reconnect ได้ - หยุดระบบ
        self.logger.error("❌ ไม่สามารถ Reconnect MT5 ได้ - หยุดระบบ")
        self.stop_trading()
    
    def _emergency_stop_all_components(self):
        """หยุด Components ทั้งหมดแบบฉุกเฉิน"""
        self.logger.warning("🚨 Emergency Stop All Components")
        
        for name, component in self.components.items():
            if component.instance and component.status == ComponentStatus.RUNNING:
                try:
                    # พยายามหยุดแบบปกติ
                    if hasattr(component.instance, 'stop_analysis'):
                        component.instance.stop_analysis()
                    elif hasattr(component.instance, 'stop_tracking'):
                        component.instance.stop_tracking()
                    elif hasattr(component.instance, 'stop_execution_engine'):
                        component.instance.stop_execution_engine()
                    elif hasattr(component.instance, 'stop_recovery_engine'):
                        component.instance.stop_recovery_engine()
                    elif hasattr(component.instance, 'stop_signal_generation'):
                        component.instance.stop_signal_generation()
                    
                    component.status = ComponentStatus.STOPPED
                    self.logger.info(f"⏹️ Emergency stopped {name}")
                    
                except Exception as e:
                    self.logger.error(f"❌ ไม่สามารถหยุด {name} แบบฉุกเฉิน: {e}")
                    component.status = ComponentStatus.ERROR
    
    def _log_system_status(self):
        """Log สถานะระบบ"""
        try:
            # System status
            uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            # Component status
            running_components = sum(1 for c in self.components.values() if c.status == ComponentStatus.RUNNING)
            total_components = len(self.components)
            
            # MT5 Account info
            account_info = mt5.account_info()
            balance = account_info.balance if account_info else 0
            equity = account_info.equity if account_info else 0
            
            # Positions count
            positions = mt5.positions_get(symbol="XAUUSD.v")
            position_count = len(positions) if positions else 0
            
            self.logger.info(
                f"📊 System Status: {self.system_state.value} | "
                f"Components: {running_components}/{total_components} | "
                f"Uptime: {uptime:.0f}s | "
                f"Balance: {balance:.2f} | "
                f"Equity: {equity:.2f} | "
                f"Positions: {position_count}"
            )
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถ log system status: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """ดึงสถานะระบบ"""
        try:
            # MT5 info
            account_info = mt5.account_info()
            terminal_info = mt5.terminal_info()
            
            # Component status
            component_status = {}
            for name, component in self.components.items():
                component_status[name] = {
                    'status': component.status.value,
                    'start_time': component.start_time,
                    'error_message': component.error_message
                }
            
            # Positions
            positions = mt5.positions_get(symbol="XAUUSD.v")
            position_count = len(positions) if positions else 0
            
            return {
                'system_state': self.system_state.value,
                'trading_active': self.trading_active,
                'start_time': self.start_time,
                'uptime': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                'mt5_connected': terminal_info is not None,
                'account_info': {
                    'login': account_info.login if account_info else None,
                    'balance': account_info.balance if account_info else 0,
                    'equity': account_info.equity if account_info else 0,
                    'margin_free': account_info.margin_free if account_info else 0,
                    'trade_allowed': account_info.trade_allowed if account_info else False
                },
                'position_count': position_count,
                'components': component_status
            }
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถดึงสถานะระบบ: {e}")
            return {'error': str(e)}
    
    def force_recovery_check(self) -> bool:
        """บังคับตรวจสอบ Recovery"""
        try:
            if self.recovery_engine and hasattr(self.recovery_engine, 'force_recovery_check'):
                return self.recovery_engine.force_recovery_check()
            return False
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถบังคับตรวจสอบ Recovery: {e}")
            return False
    
    def get_trading_statistics(self) -> Dict[str, Any]:
        """ดึงสถิติการเทรด"""
        try:
            stats = {}
            
            # Signal Generator stats
            if self.signal_generator and hasattr(self.signal_generator, 'get_signal_statistics'):
                stats['signals'] = self.signal_generator.get_signal_statistics()
            
            # Order Executor stats
            if self.order_executor and hasattr(self.order_executor, 'get_execution_statistics'):
                stats['executions'] = self.order_executor.get_execution_statistics()
            
            # Performance stats
            if self.performance_tracker and hasattr(self.performance_tracker, 'get_performance_summary'):
                stats['performance'] = self.performance_tracker.get_performance_summary()
            
            # Position stats
            if self.position_tracker and hasattr(self.position_tracker, 'get_position_statistics'):
                stats['positions'] = self.position_tracker.get_position_statistics()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถดึงสถิติการเทรด: {e}")
            return {'error': str(e)}
    
    def __del__(self):
        """Cleanup เมื่อ object ถูกทำลาย"""
        try:
            if self.trading_active:
                self.stop_trading()
            mt5.shutdown()
        except:
            pass

# ===== FACTORY FUNCTION =====

def get_real_trading_system() -> RealTradingSystem:
    """Factory function สำหรับสร้าง Real Trading System"""
    return RealTradingSystem()

# ===== MAIN TESTING =====

if __name__ == "__main__":
    """ทดสอบ Real Trading System"""
    
    print("🧪 ทดสอบ Real Trading System")
    print("=" * 50)
    print("⚠️ ระบบนี้จะเชื่อมต่อ MT5 จริงและอาจทำการเทรดด้วยเงินจริง")
    
    try:
        # สร้าง trading system
        trading_system = RealTradingSystem()
        print("✅ สร้าง Real Trading System สำเร็จ")
        
        # เริ่มต้นระบบ
        if trading_system.initialize_system():
            print("✅ เริ่มต้นระบบสำเร็จ")
            
            # แสดงสถานะ
            status = trading_system.get_system_status()
            print(f"📊 System State: {status.get('system_state')}")
            print(f"💰 Account Balance: {status.get('account_info', {}).get('balance', 0):.2f}")
            print(f"📍 Positions: {status.get('position_count', 0)}")
            
            print("\n🎯 Real Trading System พร้อมใช้งาน!")
            print("⚠️ ใช้ start_trading() เพื่อเริ่มการเทรดจริง")
            
        else:
            print("❌ ไม่สามารถเริ่มต้นระบบได้")
            
    except Exception as e:
        print(f"❌ ข้อผิดพลาด: {e}")
        import traceback
        traceback.print_exc()