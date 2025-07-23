#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI CONTROLLER - GUI Business Logic Controller
============================================
Controller หลักสำหรับจัดการ Business Logic ของ GUI System
ใช้ MVC Pattern สำหรับการแยก Presentation และ Business Logic

Key Features:
- MVC pattern implementation
- Centralized event handling and state management
- Component communication coordination  
- Data binding between models and views
- User action validation and processing

เชื่อมต่อไปยัง:
- gui_system/main_window.py (View หลัก)
- gui_system/components/ (View components ต่างๆ)
- position_management/position_tracker.py (Model - Position data)
- analytics_engine/performance_tracker.py (Model - Performance data)
- intelligent_recovery/recovery_engine.py (Model - Recovery data)
"""

import tkinter as tk
from tkinter import messagebox
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
import json
import queue
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from collections import defaultdict, deque

# เชื่อมต่อ internal modules
from config.settings import get_system_settings, SystemSettings
from config.trading_params import get_trading_parameters
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class ComponentState(Enum):
    """สถานะของ GUI Components"""
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    UPDATING = "UPDATING"
    ERROR = "ERROR"
    DISABLED = "DISABLED"

class DataUpdateType(Enum):
    """ประเภทของ Data Update"""
    POSITION_UPDATE = "POSITION_UPDATE"
    PERFORMANCE_UPDATE = "PERFORMANCE_UPDATE"
    RECOVERY_UPDATE = "RECOVERY_UPDATE"
    MARKET_UPDATE = "MARKET_UPDATE"
    SYSTEM_UPDATE = "SYSTEM_UPDATE"

@dataclass
class ComponentRegistry:
    """Registry สำหรับเก็บ GUI Components"""
    main_window: Optional[Any] = None
    trading_dashboard: Optional[Any] = None
    position_monitor: Optional[Any] = None
    recovery_panel: Optional[Any] = None
    performance_analytics: Optional[Any] = None
    market_intelligence_panel: Optional[Any] = None
    risk_control_panel: Optional[Any] = None
    
    def get_all_components(self) -> List[Any]:
        """ดึง Components ทั้งหมดที่ไม่เป็น None"""
        components = []
        for field_name, field_value in self.__dict__.items():
            if field_value is not None:
                components.append(field_value)
        return components

@dataclass
class SystemState:
    """สถานะของระบบ"""
    is_trading_active: bool = False
    is_recovery_active: bool = False
    is_connected_mt5: bool = False
    last_update_time: Optional[datetime] = None
    total_positions: int = 0
    total_pnl: float = 0.0
    active_recovery_sessions: int = 0
    system_health_score: float = 100.0
    current_session: str = "UNKNOWN"

class GuiController:
    """
    🎮 Main GUI Controller
    
    Controller หลักสำหรับจัดการ Business Logic ของ GUI System
    ใช้ MVC Pattern และ Event-Driven Architecture
    """
    
    def __init__(self):
        self.logger = setup_component_logger("GuiController")
        
        # System Configuration
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Component Registry
        self.components = ComponentRegistry()
        self.component_states = {}
        
        # System State
        self.system_state = SystemState()
        
        # Event Management
        self.event_handlers = defaultdict(list)
        self.event_queue = queue.Queue()
        
        # Data Management
        self.data_cache = {}
        self.data_subscribers = defaultdict(list)
        self.data_update_queue = queue.Queue()
        
        # Threading
        self.controller_active = False
        self.event_thread = None
        self.data_thread = None
        
        # Update Intervals (seconds)
        self.update_intervals = {
            DataUpdateType.POSITION_UPDATE: 1.0,
            DataUpdateType.PERFORMANCE_UPDATE: 5.0,
            DataUpdateType.RECOVERY_UPDATE: 2.0,
            DataUpdateType.MARKET_UPDATE: 1.0,
            DataUpdateType.SYSTEM_UPDATE: 10.0
        }
        
        self.logger.info("🎮 เริ่มต้น GUI Controller")
    
    # === COMPONENT REGISTRATION ===
    
    def register_component(self, component_name: str, component_instance: Any) -> None:
        """ลงทะเบียน GUI Component"""
        try:
            if hasattr(self.components, component_name):
                setattr(self.components, component_name, component_instance)
                self.component_states[component_name] = ComponentState.INITIALIZING
                
                self.logger.info(f"📝 ลงทะเบียน Component: {component_name}")
                
                # Setup component event bindings
                self._setup_component_bindings(component_name, component_instance)
                
                # Mark as ready
                self.component_states[component_name] = ComponentState.READY
                
            else:
                self.logger.warning(f"⚠️ Component name ไม่รู้จัก: {component_name}")
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการลงทะเบียน Component {component_name}: {e}")
            self.component_states[component_name] = ComponentState.ERROR
    
    def _setup_component_bindings(self, component_name: str, component: Any) -> None:
        """ตั้งค่า Event Bindings สำหรับ Component"""
        try:
            # Setup data subscriptions based on component type
            if component_name == "position_monitor":
                self.subscribe_to_data(component, DataUpdateType.POSITION_UPDATE)
                self.subscribe_to_data(component, DataUpdateType.PERFORMANCE_UPDATE)
                
            elif component_name == "recovery_panel":
                self.subscribe_to_data(component, DataUpdateType.RECOVERY_UPDATE)
                self.subscribe_to_data(component, DataUpdateType.POSITION_UPDATE)
                
            elif component_name == "trading_dashboard":
                # Dashboard subscribes to all data types
                for data_type in DataUpdateType:
                    self.subscribe_to_data(component, data_type)
                    
            elif component_name == "performance_analytics":
                self.subscribe_to_data(component, DataUpdateType.PERFORMANCE_UPDATE)
                self.subscribe_to_data(component, DataUpdateType.POSITION_UPDATE)
                
            # Setup component-specific event handlers
            self._bind_component_events(component_name, component)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตั้งค่า Component Bindings: {e}")
    
    def _bind_component_events(self, component_name: str, component: Any) -> None:
        """Bind Component-specific Events"""
        try:
            # Check if component has event binding methods
            if hasattr(component, 'bind_controller_events'):
                component.bind_controller_events(self)
                
            # Register common event handlers
            if hasattr(component, 'on_data_update'):
                self.register_event_handler(f"{component_name}_data_update", component.on_data_update)
                
            if hasattr(component, 'on_system_state_change'):
                self.register_event_handler("system_state_change", component.on_system_state_change)
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการ Bind Component Events: {e}")
    
    def unregister_component(self, component_name: str) -> None:
        """ยกเลิกการลงทะเบียน Component"""
        try:
            if hasattr(self.components, component_name):
                component = getattr(self.components, component_name)
                
                # Cleanup component
                if hasattr(component, 'cleanup'):
                    component.cleanup()
                
                # Remove from registry
                setattr(self.components, component_name, None)
                self.component_states.pop(component_name, None)
                
                # Remove data subscriptions
                for data_type in DataUpdateType:
                    if component in self.data_subscribers[data_type]:
                        self.data_subscribers[data_type].remove(component)
                
                self.logger.info(f"🗑️ ยกเลิกการลงทะเบียน Component: {component_name}")
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการยกเลิกการลงทะเบียน Component: {e}")
    
    # === EVENT MANAGEMENT ===
    
    def register_event_handler(self, event_name: str, handler: Callable) -> None:
        """ลงทะเบียน Event Handler"""
        try:
            self.event_handlers[event_name].append(handler)
            self.logger.debug(f"📝 ลงทะเบียน Event Handler: {event_name}")
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการลงทะเบียน Event Handler: {e}")
    
    def unregister_event_handler(self, event_name: str, handler: Callable) -> None:
        """ยกเลิกการลงทะเบียน Event Handler"""
        try:
            if handler in self.event_handlers[event_name]:
                self.event_handlers[event_name].remove(handler)
                self.logger.debug(f"🗑️ ยกเลิกการลงทะเบียน Event Handler: {event_name}")
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการยกเลิก Event Handler: {e}")
    
    def emit_event(self, event_name: str, event_data: Any = None) -> None:
        """ส่ง Event"""
        try:
            event = {
                'name': event_name,
                'data': event_data,
                'timestamp': datetime.now()
            }
            
            self.event_queue.put(event)
            self.logger.debug(f"📤 ส่ง Event: {event_name}")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการส่ง Event: {e}")
    
    def _process_events(self) -> None:
        """ประมวลผล Events ใน Queue"""
        while self.controller_active:
            try:
                if not self.event_queue.empty():
                    event = self.event_queue.get_nowait()
                    self._handle_event(event)
                
                time.sleep(0.01)  # Small delay to prevent excessive CPU usage
                
            except queue.Empty:
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดในการประมวลผล Events: {e}")
                time.sleep(0.1)
    
    def _handle_event(self, event: Dict[str, Any]) -> None:
        """จัดการ Event"""
        try:
            event_name = event['name']
            event_data = event['data']
            
            # Execute all registered handlers for this event
            for handler in self.event_handlers[event_name]:
                try:
                    handler(event_data)
                except Exception as e:
                    self.logger.error(f"❌ ข้อผิดพลาดใน Event Handler {event_name}: {e}")
            
            self.logger.debug(f"✅ ประมวลผล Event: {event_name}")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการจัดการ Event: {e}")
    
    # === DATA MANAGEMENT ===
    
    def subscribe_to_data(self, component: Any, data_type: DataUpdateType) -> None:
        """Subscribe Component ให้รับ Data Updates"""
        try:
            if component not in self.data_subscribers[data_type]:
                self.data_subscribers[data_type].append(component)
                self.logger.debug(f"📝 Subscribe Component ให้รับ {data_type.value}")
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการ Subscribe Data: {e}")
    
    def unsubscribe_from_data(self, component: Any, data_type: DataUpdateType) -> None:
        """Unsubscribe Component จาก Data Updates"""
        try:
            if component in self.data_subscribers[data_type]:
                self.data_subscribers[data_type].remove(component)
                self.logger.debug(f"🗑️ Unsubscribe Component จาก {data_type.value}")
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการ Unsubscribe Data: {e}")
    
    def update_data(self, data_type: DataUpdateType, data: Any) -> None:
        """อัพเดทข้อมูลและแจ้ง Subscribers"""
        try:
            # Cache the data
            self.data_cache[data_type] = {
                'data': data,
                'timestamp': datetime.now()
            }
            
            # Queue data update for processing
            update_info = {
                'type': data_type,
                'data': data,
                'timestamp': datetime.now()
            }
            
            self.data_update_queue.put(update_info)
            self.logger.debug(f"📊 อัพเดทข้อมูล: {data_type.value}")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดทข้อมูล: {e}")
    
    def get_cached_data(self, data_type: DataUpdateType) -> Optional[Any]:
        """ดึงข้อมูลที่ Cache ไว้"""
        try:
            cached = self.data_cache.get(data_type)
            if cached:
                return cached['data']
            return None
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Cache: {e}")
            return None
    
    def _process_data_updates(self) -> None:
        """ประมวลผล Data Updates"""
        while self.controller_active:
            try:
                if not self.data_update_queue.empty():
                    update_info = self.data_update_queue.get_nowait()
                    self._notify_data_subscribers(update_info)
                
                time.sleep(0.01)
                
            except queue.Empty:
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดในการประมวลผล Data Updates: {e}")
                time.sleep(0.1)
    
    def _notify_data_subscribers(self, update_info: Dict[str, Any]) -> None:
        """แจ้ง Data Subscribers"""
        try:
            data_type = update_info['type']
            data = update_info['data']
            
            # Notify all subscribers for this data type
            for subscriber in self.data_subscribers[data_type]:
                try:
                    if hasattr(subscriber, 'on_data_received'):
                        subscriber.on_data_received(data_type, data)
                    elif hasattr(subscriber, 'update_data'):
                        subscriber.update_data(data)
                    
                except Exception as e:
                    self.logger.error(f"❌ ข้อผิดพลาดในการแจ้ง Subscriber: {e}")
            
            self.logger.debug(f"📢 แจ้ง {len(self.data_subscribers[data_type])} subscribers สำหรับ {data_type.value}")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการแจ้ง Data Subscribers: {e}")
    
    # === SYSTEM STATE MANAGEMENT ===
    
    def update_system_state(self, **kwargs) -> None:
        """อัพเดทสถานะระบบ"""
        try:
            state_changed = False
            
            for key, value in kwargs.items():
                if hasattr(self.system_state, key):
                    old_value = getattr(self.system_state, key)
                    if old_value != value:
                        setattr(self.system_state, key, value)
                        state_changed = True
                        self.logger.debug(f"🔄 อัพเดทสถานะระบบ: {key} = {value}")
            
            if state_changed:
                self.system_state.last_update_time = datetime.now()
                self.emit_event("system_state_change", self.system_state)
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดทสถานะระบบ: {e}")
    
    def get_system_state(self) -> SystemState:
        """ดึงสถานะระบบปัจจุบัน"""
        return self.system_state
    
    def is_system_healthy(self) -> bool:
        """ตรวจสอบสุขภาพของระบบ"""
        try:
            health_score = self.system_state.system_health_score
            return health_score >= 80.0
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจสอบสุขภาพระบบ: {e}")
            return False
    
    # === USER ACTION PROCESSING ===
    
    def process_user_action(self, action_type: str, action_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """ประมวลผล User Action"""
        try:
            self.logger.info(f"🎯 ประมวลผล User Action: {action_type}")
            
            # Validate action
            if not self._validate_user_action(action_type, action_data):
                return {
                    'success': False,
                    'error': 'Invalid action or insufficient permissions'
                }
            
            # Process specific actions
            result = self._execute_user_action(action_type, action_data)
            
            # Log action result
            if result.get('success', False):
                self.logger.info(f"✅ User Action สำเร็จ: {action_type}")
            else:
                self.logger.warning(f"⚠️ User Action ล้มเหลว: {action_type} - {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการประมวลผล User Action: {e}")
            return {
                'success': False,
                'error': f'Action processing failed: {str(e)}'
            }
    
    def _validate_user_action(self, action_type: str, action_data: Dict[str, Any]) -> bool:
        """ตรวจสอบความถูกต้องของ User Action"""
        try:
            # Check if system is in appropriate state for the action
            if action_type in ['start_trading', 'place_order']:
                return self.system_state.is_connected_mt5
            
            elif action_type in ['stop_trading', 'close_all_positions']:
                return self.system_state.is_trading_active
            
            elif action_type in ['start_recovery', 'pause_recovery']:
                return self.system_state.total_positions > 0
            
            # Default: allow action
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจสอบ User Action: {e}")
            return False
    
    def _execute_user_action(self, action_type: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """ดำเนินการ User Action"""
        try:
            action_handlers = {
                'start_trading': self._handle_start_trading,
                'stop_trading': self._handle_stop_trading,
                'close_position': self._handle_close_position,
                'close_all_positions': self._handle_close_all_positions,
                'start_recovery': self._handle_start_recovery,
                'pause_recovery': self._handle_pause_recovery,
                'emergency_stop': self._handle_emergency_stop,
                'refresh_data': self._handle_refresh_data,
                'export_data': self._handle_export_data
            }
            
            handler = action_handlers.get(action_type)
            if handler:
                return handler(action_data or {})
            else:
                return {
                    'success': False,
                    'error': f'Unknown action type: {action_type}'
                }
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดำเนินการ User Action: {e}")
            return {
                'success': False,
                'error': f'Action execution failed: {str(e)}'
            }
    
    # === ACTION HANDLERS ===
    
    def _handle_start_trading(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """จัดการการเริ่มเทรด"""
        try:
            # TODO: เชื่อมต่อกับ Trading Engine
            self.update_system_state(is_trading_active=True)
            self.emit_event("trading_started", action_data)
            
            return {
                'success': True,
                'message': 'Trading started successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to start trading: {str(e)}'
            }
    
    def _handle_stop_trading(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """จัดการการหยุดเทรด"""
        try:
            # TODO: เชื่อมต่อกับ Trading Engine
            self.update_system_state(is_trading_active=False)
            self.emit_event("trading_stopped", action_data)
            
            return {
                'success': True,
                'message': 'Trading stopped successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to stop trading: {str(e)}'
            }
    
    def _handle_close_position(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """จัดการการปิด Position"""
        try:
            position_ticket = action_data.get('ticket')
            if not position_ticket:
                return {
                    'success': False,
                    'error': 'Position ticket required'
                }
            
            # TODO: เชื่อมต่อกับ Position Manager
            self.emit_event("position_closed", {'ticket': position_ticket})
            
            return {
                'success': True,
                'message': f'Position {position_ticket} closed successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to close position: {str(e)}'
            }
    
    def _handle_close_all_positions(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """จัดการการปิด Position ทั้งหมด"""
        try:
            # TODO: เชื่อมต่อกับ Position Manager
            self.update_system_state(total_positions=0, total_pnl=0.0)
            self.emit_event("all_positions_closed", action_data)
            
            return {
                'success': True,
                'message': 'All positions closed successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to close all positions: {str(e)}'
            }
    
    def _handle_start_recovery(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """จัดการการเริ่ม Recovery"""
        try:
            strategy = action_data.get('strategy', 'auto')
            
            # TODO: เชื่อมต่อกับ Recovery Engine
            self.update_system_state(is_recovery_active=True)
            self.emit_event("recovery_started", action_data)
            
            return {
                'success': True,
                'message': f'Recovery started with strategy: {strategy}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to start recovery: {str(e)}'
            }
    
    def _handle_pause_recovery(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """จัดการการหยุด Recovery ชั่วคราว"""
        try:
            # TODO: เชื่อมต่อกับ Recovery Engine
            self.update_system_state(is_recovery_active=False)
            self.emit_event("recovery_paused", action_data)
            
            return {
                'success': True,
                'message': 'Recovery paused successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to pause recovery: {str(e)}'
            }
    
    def _handle_emergency_stop(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """จัดการ Emergency Stop"""
        try:
            # TODO: เชื่อมต่อกับ Emergency System
            self.update_system_state(
                is_trading_active=False,
                is_recovery_active=False,
                system_health_score=50.0
            )
            self.emit_event("emergency_stop", action_data)
            
            return {
                'success': True,
                'message': 'Emergency stop executed successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to execute emergency stop: {str(e)}'
            }
    
    def _handle_refresh_data(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """จัดการการ Refresh ข้อมูล"""
        try:
            # Force refresh all data types
            for data_type in DataUpdateType:
                # TODO: เชื่อมต่อกับ Data Sources
                pass
            
            self.emit_event("data_refreshed", action_data)
            
            return {
                'success': True,
                'message': 'Data refreshed successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to refresh data: {str(e)}'
            }
    
    def _handle_export_data(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """จัดการการ Export ข้อมูล"""
        try:
            export_type = action_data.get('type', 'all')
            file_path = action_data.get('file_path', 'export.json')
            
            # TODO: Implement data export
            self.emit_event("data_exported", {'file_path': file_path})
            
            return {
                'success': True,
                'message': f'Data exported to {file_path}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to export data: {str(e)}'
            }
    
    # === LIFECYCLE MANAGEMENT ===
    
    def start_controller(self) -> None:
        """เริ่มต้น Controller"""
        if not self.controller_active:
            self.controller_active = True
            
            # Start event processing thread
            self.event_thread = threading.Thread(target=self._process_events, daemon=True)
            self.event_thread.start()
            
            # Start data processing thread
            self.data_thread = threading.Thread(target=self._process_data_updates, daemon=True)
            self.data_thread.start()
            
            self.logger.info("🚀 เริ่มต้น GUI Controller")
    
    def stop_controller(self) -> None:
        """หยุด Controller"""
        if self.controller_active:
            self.controller_active = False
            
            # Wait for threads to finish
            if self.event_thread and self.event_thread.is_alive():
                self.event_thread.join(timeout=1)
            
            if self.data_thread and self.data_thread.is_alive():
                self.data_thread.join(timeout=1)
            
            self.logger.info("⏹️ หยุด GUI Controller")
    
    def cleanup(self) -> None:
        """ทำความสะอาด Controller"""
        try:
            # Stop controller
            self.stop_controller()
            
            # Cleanup all registered components
            for component in self.components.get_all_components():
                if hasattr(component, 'cleanup'):
                    component.cleanup()
            
            # Clear data structures
            self.event_handlers.clear()
            self.data_subscribers.clear()
            self.data_cache.clear()
            
            # Clear queues
            while not self.event_queue.empty():
                self.event_queue.get_nowait()
            
            while not self.data_update_queue.empty():
                self.data_update_queue.get_nowait()
            
            self.logger.info("🧹 ทำความสะอาด GUI Controller")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการทำความสะอาด Controller: {e}")

# === UTILITY METHODS ===

def get_component_state(self, component_name: str) -> Optional[ComponentState]:
    """ดึงสถานะของ Component"""
    return self.component_states.get(component_name)

def get_all_component_states(self) -> Dict[str, ComponentState]:
    """ดึงสถานะของ Components ทั้งหมด"""
    return self.component_states.copy()

def is_component_ready(self, component_name: str) -> bool:
    """ตรวจสอบว่า Component พร้อมใช้งานหรือไม่"""
    state = self.get_component_state(component_name)
    return state == ComponentState.READY

def broadcast_message(self, message: str, message_type: str = "info") -> None:
    """ส่งข้อความไปยัง Components ทั้งหมด"""
    try:
        message_data = {
            'message': message,
            'type': message_type,
            'timestamp': datetime.now()
        }
        
        self.emit_event("broadcast_message", message_data)
        self.logger.info(f"📢 ส่งข้อความ: {message}")
        
    except Exception as e:
        self.logger.error(f"❌ ข้อผิดพลาดในการส่งข้อความ: {e}")

def request_component_status(self) -> Dict[str, Any]:
    """ขอข้อมูลสถานะจาก Components ทั้งหมด"""
    try:
        status_report = {
            'controller_status': 'ACTIVE' if self.controller_active else 'INACTIVE',
            'system_state': self.system_state.__dict__,
            'component_states': self.component_states,
            'active_subscribers': {
                data_type.value: len(subscribers) 
                for data_type, subscribers in self.data_subscribers.items()
            },
            'cached_data_types': list(self.data_cache.keys()),
            'event_queue_size': self.event_queue.qsize(),
            'data_queue_size': self.data_update_queue.qsize(),
            'timestamp': datetime.now().isoformat()
        }
        
        return status_report
        
    except Exception as e:
        self.logger.error(f"❌ ข้อผิดพลาดในการขอข้อมูลสถานะ: {e}")
        return {}


# === TESTING AND DEBUGGING ===

class MockDataGenerator:
    """
    สร้างข้อมูลจำลองสำหรับการทดสอบ Controller
    """
    
    @staticmethod
    def generate_position_data() -> List[Dict[str, Any]]:
        """สร้างข้อมูล Position จำลอง"""
        return [
            {
                'ticket': 123456789,
                'symbol': 'XAUUSD',
                'type': 0,  # BUY
                'volume': 0.1,
                'price_open': 2020.50,
                'price_current': 2022.30,
                'profit': 18.00,
                'swap': -0.50,
                'commission': -3.00,
                'time': datetime.now() - timedelta(minutes=15),
                'comment': 'Auto Entry - Trend Following'
            },
            {
                'ticket': 123456790,
                'symbol': 'XAUUSD',
                'type': 1,  # SELL
                'volume': 0.2,
                'price_open': 2025.80,
                'price_current': 2022.30,
                'profit': 70.00,
                'swap': -1.20,
                'commission': -6.00,
                'time': datetime.now() - timedelta(hours=2),
                'comment': 'Recovery Level 2 - Martingale'
            }
        ]
    
    @staticmethod
    def generate_performance_data() -> Dict[str, Any]:
        """สร้างข้อมูล Performance จำลอง"""
        return {
            'total_trades': 150,
            'winning_trades': 135,
            'losing_trades': 15,
            'win_rate': 90.0,
            'total_profit': 1250.75,
            'total_loss': -180.50,
            'net_profit': 1070.25,
            'max_drawdown': 45.30,
            'current_drawdown': 12.80,
            'profit_factor': 6.93,
            'average_win': 9.26,
            'average_loss': -12.03,
            'largest_win': 89.50,
            'largest_loss': -25.60,
            'volume_today': 87.5,
            'trades_today': 62,
            'last_update': datetime.now()
        }
    
    @staticmethod
    def generate_recovery_data() -> List[Dict[str, Any]]:
        """สร้างข้อมูล Recovery จำลอง"""
        return [
            {
                'session_id': 'REC_001',
                'position_ticket': 123456789,
                'strategy_name': 'Smart Martingale',
                'start_time': datetime.now() - timedelta(minutes=5),
                'status': 'ACTIVE',
                'current_level': 2,
                'max_level': 5,
                'total_volume': 0.3,
                'unrealized_pnl': -45.50,
                'recovery_orders': ['REC_001_1', 'REC_001_2']
            },
            {
                'session_id': 'REC_002',
                'position_ticket': 123456790,
                'strategy_name': 'Dynamic Grid',
                'start_time': datetime.now() - timedelta(minutes=15),
                'status': 'SUCCESS',
                'current_level': 3,
                'max_level': 4,
                'total_volume': 0.7,
                'unrealized_pnl': 25.30,
                'recovery_orders': ['REC_002_1', 'REC_002_2', 'REC_002_3']
            }
        ]
    
    @staticmethod
    def generate_market_data() -> Dict[str, Any]:
        """สร้างข้อมูล Market จำลอง"""
        return {
            'symbol': 'XAUUSD',
            'bid': 2022.15,
            'ask': 2022.35,
            'spread': 2.0,
            'atr': 15.8,
            'adx': 28.5,
            'trend_direction': 'UP',
            'volatility_level': 'MEDIUM',
            'session': 'LONDON',
            'market_state': 'TRENDING',
            'timestamp': datetime.now()
        }


def demo_gui_controller():
    """
    Demo function สำหรับทดสอบ GUI Controller
    """
    
    class MockComponent:
        """Mock Component สำหรับการทดสอบ"""
        
        def __init__(self, name: str):
            self.name = name
            self.received_data = []
            self.received_events = []
        
        def on_data_received(self, data_type: DataUpdateType, data: Any) -> None:
            """จัดการข้อมูลที่ได้รับ"""
            self.received_data.append({
                'type': data_type,
                'data': data,
                'timestamp': datetime.now()
            })
            print(f"📊 {self.name} received {data_type.value} data")
        
        def on_system_state_change(self, system_state: SystemState) -> None:
            """จัดการการเปลี่ยนแปลงสถานะระบบ"""
            print(f"🔄 {self.name} received system state change")
        
        def cleanup(self) -> None:
            """ทำความสะอาด Component"""
            print(f"🧹 {self.name} cleanup")
    
    # Create controller
    controller = GuiController()
    controller.start_controller()
    
    # Create mock components
    dashboard = MockComponent("TradingDashboard")
    position_monitor = MockComponent("PositionMonitor")
    recovery_panel = MockComponent("RecoveryPanel")
    
    # Register components
    controller.register_component("trading_dashboard", dashboard)
    controller.register_component("position_monitor", position_monitor)
    controller.register_component("recovery_panel", recovery_panel)
    
    print("✅ GUI Controller Demo เริ่มต้นแล้ว")
    print("🔄 กำลังทดสอบ Data Updates...")
    
    try:
        # Test data updates
        time.sleep(1)
        
        # Update position data
        position_data = MockDataGenerator.generate_position_data()
        controller.update_data(DataUpdateType.POSITION_UPDATE, position_data)
        print("📊 ส่ง Position Data")
        
        time.sleep(0.5)
        
        # Update performance data
        performance_data = MockDataGenerator.generate_performance_data()
        controller.update_data(DataUpdateType.PERFORMANCE_UPDATE, performance_data)
        print("📈 ส่ง Performance Data")
        
        time.sleep(0.5)
        
        # Update recovery data
        recovery_data = MockDataGenerator.generate_recovery_data()
        controller.update_data(DataUpdateType.RECOVERY_UPDATE, recovery_data)
        print("🔄 ส่ง Recovery Data")
        
        time.sleep(0.5)
        
        # Test system state updates
        controller.update_system_state(
            is_trading_active=True,
            total_positions=2,
            total_pnl=1070.25,
            is_connected_mt5=True
        )
        print("🔄 อัพเดทสถานะระบบ")
        
        time.sleep(0.5)
        
        # Test user actions
        print("\n🎯 ทดสอบ User Actions:")
        
        result = controller.process_user_action("start_trading", {"mode": "auto"})
        print(f"🚀 Start Trading: {result}")
        
        result = controller.process_user_action("start_recovery", {"strategy": "martingale"})
        print(f"🔄 Start Recovery: {result}")
        
        result = controller.process_user_action("refresh_data")
        print(f"🔄 Refresh Data: {result}")
        
        # Show status report
        time.sleep(1)
        status = controller.request_component_status()
        print(f"\n📊 Controller Status Report:")
        print(f"  - Controller: {status.get('controller_status')}")
        print(f"  - Components: {len(status.get('component_states', {}))}")
        print(f"  - Active Subscribers: {status.get('active_subscribers')}")
        print(f"  - Event Queue Size: {status.get('event_queue_size')}")
        print(f"  - Data Queue Size: {status.get('data_queue_size')}")
        
        print("\n✅ การทดสอบเสร็จสิ้น - กด Enter เพื่อปิด...")
        input()
        
    except KeyboardInterrupt:
        print("\n⏹️ หยุดการทดสอบ")
    
    finally:
        # Cleanup
        controller.cleanup()
        print("🧹 ทำความสะอาดเสร็จสิ้น")


if __name__ == "__main__":
    demo_gui_controller()