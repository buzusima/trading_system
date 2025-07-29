#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORE TRADING SYSTEM - ระบบเทรดหลัก (COMPLETE FIXED)
=================================================
ระบบเทรดหลักสำหรับ Intelligent Gold Trading System
ฉบับสมบูรณ์แบบที่แก้ไขปัญหา Import และ Component Initialization

🔧 ปัญหาที่แก้ไข:
- Circular Import Dependencies
- Component Initialization Order
- Safe Module Loading
- Error Handling ในการโหลด Components
- Mock Components สำหรับ Development

🎯 หน้าที่หลัก:
- จัดการ lifecycle ของระบบเทรด
- เชื่อมต่อ components ทั้งหมด
- ควบคุมการเริ่มต้นและหยุดระบบ
- ติดตาม health ของระบบ
- จัดการ Recovery และ Position Management
- Performance Tracking
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
import random
from pathlib import Path
from collections import defaultdict, deque

# Safe imports with fallback
def safe_import(module_name: str, fallback_value: Any = None):
    """Import module แบบปลอดภัย"""
    try:
        parts = module_name.split('.')
        module = __import__(module_name)
        for part in parts[1:]:
            module = getattr(module, part)
        return module
    except ImportError as e:
        print(f"⚠️ ไม่สามารถ import {module_name}: {e}")
        return fallback_value
    except Exception as e:
        print(f"⚠️ ข้อผิดพลาดใน import {module_name}: {e}")
        return fallback_value

# Import required modules with safe fallback
try:
    from utilities.professional_logger import setup_main_logger, setup_component_logger
    from utilities.error_handler import GlobalErrorHandler, ErrorCategory, ErrorSeverity, handle_trading_errors
except ImportError:
    # Fallback to basic logging
    import logging
    def setup_main_logger(name="TradingSystem"):
        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def setup_component_logger(name):
        return setup_main_logger(name)
    
    class ErrorCategory(Enum):
        SYSTEM = "SYSTEM"
        TRADING = "TRADING"
        MT5_CONNECTION = "MT5_CONNECTION"
        RECOVERY = "RECOVERY"
    
    class ErrorSeverity(Enum):
        LOW = "LOW"
        MEDIUM = "MEDIUM"
        HIGH = "HIGH"
        CRITICAL = "CRITICAL"
    
    def handle_trading_errors(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"Trading Error in {func.__name__}: {e}")
                raise
        return wrapper
    
    class GlobalErrorHandler:
        def __init__(self, logger=None):
            self.logger = logger
        
        def setup_global_exception_handling(self):
            pass
        
        def handle_error(self, category, severity, message, exc_info=None):
            if self.logger:
                self.logger.error(f"[{category.value}] {message}")
            else:
                print(f"[{category.value}] {message}")

# System State Management
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
    STOPPED = "STOPPED"
    ERROR = "ERROR"

@dataclass
class ComponentInfo:
    """ข้อมูลของ Component"""
    name: str
    status: ComponentStatus = ComponentStatus.NOT_LOADED
    instance: Optional[Any] = None
    error_message: Optional[str] = None
    load_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    health_status: str = "UNKNOWN"

@dataclass
class SystemMetrics:
    """เมตริกของระบบ"""
    start_time: datetime = field(default_factory=datetime.now)
    components_loaded: int = 0
    components_running: int = 0
    total_components: int = 0
    last_update: datetime = field(default_factory=datetime.now)
    uptime_seconds: int = 0
    errors_count: int = 0
    signals_generated: int = 0
    orders_executed: int = 0
    recovery_operations: int = 0

class MockMarketAnalyzer:
    """Mock Market Analyzer สำหรับการทดสอบ"""
    
    def __init__(self):
        self.analysis_active = False
        self.current_condition = "RANGING"
        self.current_session = "ASIAN"
    
    def start_analysis(self):
        self.analysis_active = True
        print("🧠 Mock Market Analyzer เริ่มการวิเคราะห์")
    
    def stop_analysis(self):
        self.analysis_active = False
        print("🛑 Mock Market Analyzer หยุดการวิเคราะห์")
    
    def get_current_condition(self):
        conditions = ["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE", "QUIET"]
        return random.choice(conditions)
    
    def get_current_session(self):
        hour = datetime.now().hour
        if 22 <= hour or hour < 8:
            return "ASIAN"
        elif 15 <= hour < 20:
            return "LONDON"
        elif 20 <= hour < 22:
            return "OVERLAP"
        else:
            return "NEW_YORK"

class MockSignalGenerator:
    """Mock Signal Generator สำหรับการทดสอบ"""
    
    def __init__(self):
        self.generation_active = False
        self.signals_generated = 0
        self.signals_queue = queue.Queue(maxsize=50)
    
    def start_signal_generation(self):
        self.generation_active = True
        print("🎯 Mock Signal Generator เริ่มสร้างสัญญาณ")
        return True
    
    def stop_signal_generation(self):
        self.generation_active = False
        print("🛑 Mock Signal Generator หยุดสร้างสัญญาณ")
    
    def get_next_signal(self, timeout=1.0):
        if random.random() > 0.7:  # 30% chance ได้สัญญาณ
            return {
                'signal_id': f'MOCK_{int(time.time())}',
                'signal_type': random.choice(['BUY', 'SELL']),
                'confidence': random.uniform(0.5, 0.9),
                'entry_price': 2000 + random.uniform(-10, 10),
                'volume': 0.01
            }
        return None
    
    def get_statistics(self):
        return {
            'generation_active': self.generation_active,
            'signals_generated_today': self.signals_generated,
            'queue_size': self.signals_queue.qsize()
        }

class MockRecoveryEngine:
    """Mock Recovery Engine สำหรับการทดสอบ"""
    
    def __init__(self):
        self.recovery_active = False
        self.recovery_operations = 0
        self.positions_in_recovery = []
    
    def start_recovery_system(self):
        self.recovery_active = True
        print("🔄 Mock Recovery Engine เริ่มระบบ Recovery")
        return True
    
    def stop_recovery_system(self):
        self.recovery_active = False
        print("🛑 Mock Recovery Engine หยุดระบบ Recovery")
    
    def add_position_to_recovery(self, position_data):
        self.positions_in_recovery.append({
            'position_id': position_data.get('ticket', f'MOCK_{int(time.time())}'),
            'entry_price': position_data.get('price', 2000),
            'volume': position_data.get('volume', 0.01),
            'type': position_data.get('type', 'BUY'),
            'recovery_level': 0,
            'timestamp': datetime.now()
        })
        self.recovery_operations += 1
        print(f"🔄 เพิ่มตำแหน่งเข้าระบบ Recovery: {position_data}")
    
    def get_recovery_status(self):
        return {
            'recovery_active': self.recovery_active,
            'positions_in_recovery': len(self.positions_in_recovery),
            'recovery_operations': self.recovery_operations
        }

class MockPositionTracker:
    """Mock Position Tracker สำหรับการทดสอบ"""
    
    def __init__(self):
        self.tracking_active = False
        self.open_positions = []
        self.closed_positions = []
        self.total_profit = 0.0
    
    def start_position_tracking(self):
        self.tracking_active = True
        print("📊 Mock Position Tracker เริ่มติดตาม")
        return True
    
    def stop_position_tracking(self):
        self.tracking_active = False
        print("🛑 Mock Position Tracker หยุดติดตาม")
    
    def add_position(self, position_data):
        position = {
            'ticket': position_data.get('ticket', f'POS_{int(time.time())}'),
            'symbol': position_data.get('symbol', 'XAUUSD'),
            'type': position_data.get('type', 'BUY'),
            'volume': position_data.get('volume', 0.01),
            'open_price': position_data.get('price', 2000),
            'open_time': datetime.now(),
            'profit': 0.0,
            'status': 'OPEN'
        }
        self.open_positions.append(position)
        print(f"➕ เพิ่มตำแหน่งใหม่: {position['ticket']}")
        return position['ticket']
    
    def close_position(self, ticket, close_price=None, profit=0.0):
        for i, pos in enumerate(self.open_positions):
            if pos['ticket'] == ticket:
                pos['close_price'] = close_price or (pos['open_price'] + random.uniform(-5, 5))
                pos['close_time'] = datetime.now()
                pos['profit'] = profit
                pos['status'] = 'CLOSED'
                
                self.closed_positions.append(pos)
                self.open_positions.pop(i)
                self.total_profit += profit
                
                print(f"➖ ปิดตำแหน่ง: {ticket} | กำไร: {profit}")
                return True
        return False
    
    def get_open_positions(self):
        return self.open_positions.copy()
    
    def get_position_summary(self):
        return {
            'tracking_active': self.tracking_active,
            'open_positions_count': len(self.open_positions),
            'closed_positions_count': len(self.closed_positions),
            'total_profit': self.total_profit,
            'open_volume': sum(pos['volume'] for pos in self.open_positions)
        }

class MockOrderExecutor:
    """Mock Order Executor สำหรับการทดสอบ"""
    
    def __init__(self):
        self.execution_active = False
        self.orders_executed = 0
        self.execution_success_rate = 0.85  # 85% success rate
    
    def start_order_execution(self):
        self.execution_active = True
        print("⚡ Mock Order Executor เริ่มการ execute")
        return True
    
    def stop_order_execution(self):
        self.execution_active = False
        print("🛑 Mock Order Executor หยุดการ execute")
    
    def execute_market_order(self, symbol, order_type, volume, comment=""):
        if not self.execution_active:
            return None
        
        # จำลองการ execute
        if random.random() < self.execution_success_rate:
            order_result = {
                'ticket': f'ORDER_{int(time.time())}_{random.randint(1000, 9999)}',
                'symbol': symbol,
                'type': order_type,
                'volume': volume,
                'price': 2000 + random.uniform(-2, 2),
                'time': datetime.now(),
                'comment': comment,
                'profit': 0.0,
                'status': 'FILLED'
            }
            self.orders_executed += 1
            print(f"✅ Execute สำเร็จ: {order_result['ticket']} | {order_type} {volume} lots")
            return order_result
        else:
            print(f"❌ Execute ล้มเหลว: {order_type} {volume} lots")
            return None
    
    def get_execution_statistics(self):
        return {
            'execution_active': self.execution_active,
            'orders_executed': self.orders_executed,
            'success_rate': self.execution_success_rate
        }

class MockPerformanceTracker:
    """Mock Performance Tracker สำหรับการทดสอบ"""
    
    def __init__(self):
        self.tracking_active = False
        self.daily_profit = 0.0
        self.weekly_profit = 0.0
        self.monthly_profit = 0.0
        self.win_rate = 0.0
        self.total_trades = 0
        self.winning_trades = 0
    
    def start_performance_tracking(self):
        self.tracking_active = True
        print("📈 Mock Performance Tracker เริ่มติดตาม")
        return True
    
    def stop_performance_tracking(self):
        self.tracking_active = False
        print("🛑 Mock Performance Tracker หยุดติดตาม")
    
    def record_trade(self, profit, is_win=None):
        self.total_trades += 1
        self.daily_profit += profit
        self.weekly_profit += profit
        self.monthly_profit += profit
        
        if is_win is None:
            is_win = profit > 0
        
        if is_win:
            self.winning_trades += 1
        
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100
    
    def get_performance_summary(self):
        return {
            'tracking_active': self.tracking_active,
            'daily_profit': self.daily_profit,
            'weekly_profit': self.weekly_profit,
            'monthly_profit': self.monthly_profit,
            'win_rate_percent': self.win_rate,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades
        }

class IntelligentTradingSystem:
    """🧠 ระบบเทรดอัจฉริยะหลัก - ฉบับสมบูรณ์"""
    
    def __init__(self, settings=None, logger=None):
        """เริ่มต้นระบบเทรด"""
        # Core attributes
        self.logger = logger or setup_main_logger("IntelligentTradingSystem")
        self.settings = settings
        self.system_state = SystemState.INITIALIZING
        
        # Component management
        self.components: Dict[str, ComponentInfo] = {}
        self.component_dependencies: Dict[str, List[str]] = {}
        
        # System metrics
        self.metrics = SystemMetrics()
        
        # Threading
        self.system_thread: Optional[threading.Thread] = None
        self.monitoring_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        
        # Trading control
        self.trading_active = False
        self.auto_trading_enabled = False
        
        # Component instances (safe initialization)
        self.market_analyzer = None
        self.signal_generator = None
        self.recovery_engine = None
        self.position_tracker = None
        self.order_executor = None
        self.performance_tracker = None
        
        # Error handling
        self.error_handler = GlobalErrorHandler(self.logger)
        
        # Statistics
        self.system_statistics = {
            'start_time': datetime.now(),
            'total_uptime': 0,
            'components_health': {},
            'last_health_check': None,
            'performance_metrics': {},
            'error_log': deque(maxlen=100)
        }
        
        self.logger.info("🧠 เริ่มต้น Intelligent Trading System (COMPLETE)")
        
        # เริ่มต้นระบบ
        self._setup_components()
    
    def _setup_components(self):
        """ตั้งค่า components และ dependencies"""
        # กำหนด components และ dependencies
        self.component_dependencies = {
            'settings': [],
            'error_handler': ['settings'],
            'market_analyzer': ['settings', 'error_handler'],
            'signal_generator': ['settings', 'market_analyzer', 'error_handler'],
            'recovery_engine': ['settings', 'error_handler'],
            'position_tracker': ['settings', 'error_handler'],
            'order_executor': ['settings', 'position_tracker', 'error_handler'],
            'performance_tracker': ['settings', 'position_tracker', 'error_handler']
        }
        
        # สร้าง ComponentInfo สำหรับแต่ละ component
        for component_name in self.component_dependencies.keys():
            self.components[component_name] = ComponentInfo(component_name)
        
        self.metrics.total_components = len(self.components)
        self.logger.info(f"📋 ตั้งค่า {self.metrics.total_components} components")
    
    def initialize_components(self) -> int:
        """เริ่มต้น components ทั้งหมด"""
        self.logger.info("🔧 กำลังเริ่มต้น components...")
        success_count = 0
        
        # เรียงลำดับการโหลดตาม dependencies
        load_order = self._get_load_order()
        
        for component_name in load_order:
            try:
                self.logger.info(f"📦 กำลังโหลด {component_name}...")
                success = self._load_component(component_name)
                
                if success:
                    success_count += 1
                    self.components[component_name].status = ComponentStatus.LOADED
                    self.components[component_name].load_time = datetime.now()
                    self.components[component_name].health_status = "HEALTHY"
                    self.logger.info(f"✅ โหลด {component_name} สำเร็จ")
                else:
                    self.components[component_name].status = ComponentStatus.ERROR
                    self.components[component_name].health_status = "ERROR"
                    self.logger.error(f"❌ โหลด {component_name} ล้มเหลว")
                    
            except Exception as e:
                self.logger.error(f"💥 ข้อผิดพลาดในการโหลด {component_name}: {e}")
                traceback.print_exc()
                self.components[component_name].status = ComponentStatus.ERROR
                self.components[component_name].error_message = str(e)
                self.components[component_name].health_status = "CRITICAL"
        
        self.metrics.components_loaded = success_count
        self.logger.info(f"📊 โหลด components สำเร็จ: {success_count}/{self.metrics.total_components}")
        
        # อัพเดทสถานะระบบ
        if success_count >= 4:  # อย่างน้อย 4 components หลัก
            self.system_state = SystemState.READY
            self.logger.info("✅ ระบบพร้อมใช้งาน")
        else:
            self.system_state = SystemState.ERROR
            self.logger.error("❌ ระบบไม่พร้อมใช้งาน - components ไม่เพียงพอ")
        
        return success_count
    
    def _get_load_order(self) -> List[str]:
        """กำหนดลำดับการโหลด components ตาม dependencies"""
        loaded = set()
        order = []
        
        def can_load(component: str) -> bool:
            dependencies = self.component_dependencies.get(component, [])
            return all(dep in loaded for dep in dependencies)
        
        while len(loaded) < len(self.component_dependencies):
            progress_made = False
            
            for component in self.component_dependencies:
                if component not in loaded and can_load(component):
                    order.append(component)
                    loaded.add(component)
                    progress_made = True
                    break
            
            if not progress_made:
                # ถ้าไม่มี component ไหนโหลดได้ ให้โหลดที่เหลือ
                remaining = set(self.component_dependencies.keys()) - loaded
                if remaining:
                    order.extend(remaining)
                    loaded.update(remaining)
                break
        
        return order
    
    def _load_component(self, component_name: str) -> bool:
        """โหลด component เฉพาะ"""
        self.components[component_name].status = ComponentStatus.LOADING
        
        try:
            if component_name == 'settings':
                return self._load_settings()
            elif component_name == 'error_handler':
                return self._load_error_handler()
            elif component_name == 'market_analyzer':
                return self._load_market_analyzer()
            elif component_name == 'signal_generator':
                return self._load_signal_generator()
            elif component_name == 'recovery_engine':
                return self._load_recovery_engine()
            elif component_name == 'position_tracker':
                return self._load_position_tracker()
            elif component_name == 'order_executor':
                return self._load_order_executor()
            elif component_name == 'performance_tracker':
                return self._load_performance_tracker()
            else:
                self.logger.warning(f"⚠️ ไม่รู้จัก component: {component_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการโหลด {component_name}: {e}")
            traceback.print_exc()
            return False
    
    def _load_settings(self) -> bool:
        """โหลดการตั้งค่าระบบ"""
        try:
            if self.settings is None:
                # พยายามโหลดจาก config
                try:
                    from config.settings import get_system_settings
                    self.settings = get_system_settings()
                    self.logger.info("📋 โหลด SystemSettings จาก config module")
                except ImportError:
                    # ใช้การตั้งค่าเริ่มต้น
                    class DefaultSettings:
                        trading_mode = "LIVE"
                        symbol = "XAUUSD"
                        high_frequency_mode = True
                        daily_volume_target_min = 50.0
                        daily_volume_target_max = 100.0
                        recovery_mandatory = True
                        use_stop_loss = False
                    
                    self.settings = DefaultSettings()
                    self.logger.warning("⚠️ ใช้ Default Settings")
            
            self.components['settings'].instance = self.settings
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถโหลดการตั้งค่า: {e}")
            return False
    
    def _load_error_handler(self) -> bool:
        """โหลด Error Handler"""
        try:
            self.error_handler.setup_global_exception_handling()
            self.components['error_handler'].instance = self.error_handler
            return True
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถโหลด Error Handler: {e}")
            return False
    
    def _load_market_analyzer(self) -> bool:
        """โหลด Market Analyzer"""
        try:
            # ลองโหลดจาก market_intelligence
            market_analyzer_module = safe_import('market_intelligence.market_analyzer')
            if market_analyzer_module and hasattr(market_analyzer_module, 'get_market_analyzer'):
                self.market_analyzer = market_analyzer_module.get_market_analyzer()
                self.components['market_analyzer'].instance = self.market_analyzer
                self.logger.info("✅ โหลด Real Market Analyzer")
                return True
            else:
                # สร้าง Mock Market Analyzer
                self.market_analyzer = MockMarketAnalyzer()
                self.components['market_analyzer'].instance = self.market_analyzer
                self.logger.warning("⚠️ ใช้ Mock Market Analyzer")
                return True
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถโหลด Market Analyzer: {e}")
            return False
    
    def _load_signal_generator(self) -> bool:
        """โหลด Signal Generator"""
        try:
            # ลองโหลดจาก adaptive_entries
            signal_generator_module = safe_import('adaptive_entries.signal_generator')
            if signal_generator_module and hasattr(signal_generator_module, 'get_intelligent_signal_generator'):
                self.signal_generator = signal_generator_module.get_intelligent_signal_generator()
                self.components['signal_generator'].instance = self.signal_generator
                self.logger.info("✅ โหลด Real Signal Generator")
                return True
            else:
                # สร้าง Mock Signal Generator
                self.signal_generator = MockSignalGenerator()
                self.components['signal_generator'].instance = self.signal_generator
                self.logger.warning("⚠️ ใช้ Mock Signal Generator")
                return True
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถโหลด Signal Generator: {e}")
            return False
    
    def _load_recovery_engine(self) -> bool:
        """โหลด Recovery Engine"""
        try:
            # ลองโหลดจาก intelligent_recovery
            recovery_module = safe_import('intelligent_recovery.recovery_engine')
            if recovery_module and hasattr(recovery_module, 'get_recovery_engine'):
                self.recovery_engine = recovery_module.get_recovery_engine()
                self.components['recovery_engine'].instance = self.recovery_engine
                self.logger.info("✅ โหลด Real Recovery Engine")
                return True
            else:
                # สร้าง Mock Recovery Engine
                self.recovery_engine = MockRecoveryEngine()
                self.components['recovery_engine'].instance = self.recovery_engine
                self.logger.warning("⚠️ ใช้ Mock Recovery Engine")
                return True
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถโหลด Recovery Engine: {e}")
            return False
    
    def _load_position_tracker(self) -> bool:
        """โหลด Position Tracker"""
        try:
            # ลองโหลดจาก position_management
            position_module = safe_import('position_management.position_tracker')
            if position_module and hasattr(position_module, 'get_position_tracker'):
                self.position_tracker = position_module.get_position_tracker()
                self.components['position_tracker'].instance = self.position_tracker
                self.logger.info("✅ โหลด Real Position Tracker")
                return True
            else:
                # สร้าง Mock Position Tracker
                self.position_tracker = MockPositionTracker()
                self.components['position_tracker'].instance = self.position_tracker
                self.logger.warning("⚠️ ใช้ Mock Position Tracker")
                return True
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถโหลด Position Tracker: {e}")
            return False
    
    def _load_order_executor(self) -> bool:
        """โหลด Order Executor"""
        try:
            # ลองโหลดจาก mt5_integration
            executor_module = safe_import('mt5_integration.order_executor')
            if executor_module and hasattr(executor_module, 'get_smart_order_executor'):
                self.order_executor = executor_module.get_smart_order_executor()
                self.components['order_executor'].instance = self.order_executor
                self.logger.info("✅ โหลด Real Order Executor")
                return True
            else:
                # สร้าง Mock Order Executor
                self.order_executor = MockOrderExecutor()
                self.components['order_executor'].instance = self.order_executor
                self.logger.warning("⚠️ ใช้ Mock Order Executor")
                return True
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถโหลด Order Executor: {e}")
            return False
    
    def _load_performance_tracker(self) -> bool:
        """โหลด Performance Tracker"""
        try:
            # ลองโหลดจาก analytics_engine
            performance_module = safe_import('analytics_engine.performance_tracker')
            if performance_module and hasattr(performance_module, 'get_performance_tracker'):
                self.performance_tracker = performance_module.get_performance_tracker()
                self.components['performance_tracker'].instance = self.performance_tracker
                self.logger.info("✅ โหลด Real Performance Tracker")
                return True
            else:
                # สร้าง Mock Performance Tracker
                self.performance_tracker = MockPerformanceTracker()
                self.components['performance_tracker'].instance = self.performance_tracker
                self.logger.warning("⚠️ ใช้ Mock Performance Tracker")
                return True
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถโหลด Performance Tracker: {e}")
            return False
        
   
    def start_trading(self) -> bool:
        """🎯 เริ่มการเทรด"""
        if self.system_state != SystemState.READY:
            self.logger.error("❌ ระบบยังไม่พร้อม - ไม่สามารถเริ่มการเทรดได้")
            return False
        
        if self.trading_active:
            self.logger.warning("⚠️ การเทรดเปิดอยู่แล้ว")
            return True
        
        try:
            self.logger.info("🚀 เริ่มระบบการเทรด...")
            
            # เริ่มต้น components ตามลำดับ
            components_started = 0
            
            # 1. Market Analyzer
            if self.market_analyzer and hasattr(self.market_analyzer, 'start_analysis'):
                if self.market_analyzer.start_analysis():
                    components_started += 1
                    self.components['market_analyzer'].status = ComponentStatus.RUNNING
                    self.components['market_analyzer'].start_time = datetime.now()
            
            # 2. Position Tracker
            if self.position_tracker and hasattr(self.position_tracker, 'start_position_tracking'):
                if self.position_tracker.start_position_tracking():
                    components_started += 1
                    self.components['position_tracker'].status = ComponentStatus.RUNNING
                    self.components['position_tracker'].start_time = datetime.now()
            
            # 3. Order Executor
            if self.order_executor and hasattr(self.order_executor, 'start_order_execution'):
                if self.order_executor.start_order_execution():
                    components_started += 1
                    self.components['order_executor'].status = ComponentStatus.RUNNING
                    self.components['order_executor'].start_time = datetime.now()
            
            # 4. Recovery Engine
            if self.recovery_engine and hasattr(self.recovery_engine, 'start_recovery_system'):
                if self.recovery_engine.start_recovery_system():
                    components_started += 1
                    self.components['recovery_engine'].status = ComponentStatus.RUNNING
                    self.components['recovery_engine'].start_time = datetime.now()
            
            # 5. Performance Tracker
            if self.performance_tracker and hasattr(self.performance_tracker, 'start_performance_tracking'):
                if self.performance_tracker.start_performance_tracking():
                    components_started += 1
                    self.components['performance_tracker'].status = ComponentStatus.RUNNING
                    self.components['performance_tracker'].start_time = datetime.now()
            
            # 6. Signal Generator (เริ่มสุดท้าย)
            if self.signal_generator and hasattr(self.signal_generator, 'start_signal_generation'):
                if self.signal_generator.start_signal_generation():
                    components_started += 1
                    self.components['signal_generator'].status = ComponentStatus.RUNNING
                    self.components['signal_generator'].start_time = datetime.now()
            
            self.metrics.components_running = components_started
            
            if components_started >= 3:  # อย่างน้อย 3 components สำคัญ
                self.trading_active = True
                self.system_state = SystemState.RUNNING
                
                # เริ่ม system monitoring
                self._start_system_monitoring()
                
                # เริ่ม main trading loop
                self._start_trading_loop()
                
                self.logger.info(f"✅ เริ่มการเทรดสำเร็จ - Components ที่ทำงาน: {components_started}")
                return True
            else:
                self.logger.error(f"❌ Components ไม่เพียงพอ - เริ่มได้เพียง {components_started}")
                return False
        
        except Exception as e:
            self.logger.error(f"💥 ข้อผิดพลาดในการเริ่มการเทรด: {e}")
            traceback.print_exc()
            return False
    
    def stop_trading(self):
        """🛑 หยุดการเทรด"""
        if not self.trading_active:
            self.logger.info("ℹ️ การเทรดไม่ได้เปิดอยู่")
            return
        
        try:
            self.logger.info("🛑 กำลังหยุดระบบการเทรด...")
            self.system_state = SystemState.STOPPING
            
            # หยุด trading loop
            self.shutdown_event.set()
            
            # หยุด components ตามลำดับย้อนกลับ
            components_to_stop = [
                ('signal_generator', 'stop_signal_generation'),
                ('performance_tracker', 'stop_performance_tracking'),
                ('recovery_engine', 'stop_recovery_system'),
                ('order_executor', 'stop_order_execution'),
                ('position_tracker', 'stop_position_tracking'),
                ('market_analyzer', 'stop_analysis')
            ]
            
            for component_name, stop_method in components_to_stop:
                try:
                    component = getattr(self, component_name)
                    if component and hasattr(component, stop_method):
                        getattr(component, stop_method)()
                        self.components[component_name].status = ComponentStatus.STOPPED
                        self.logger.info(f"🛑 หยุด {component_name}")
                except Exception as e:
                    self.logger.error(f"❌ ไม่สามารถหยุด {component_name}: {e}")
            
            # รอให้ threads หยุด
            if self.system_thread and self.system_thread.is_alive():
                self.system_thread.join(timeout=10.0)
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5.0)
            
            self.trading_active = False
            self.system_state = SystemState.STOPPED
            self.metrics.components_running = 0
            
            self.logger.info("✅ หยุดการเทรดสำเร็จ")
            
        except Exception as e:
            self.logger.error(f"💥 ข้อผิดพลาดในการหยุดการเทรด: {e}")
            traceback.print_exc()
    
    def _start_system_monitoring(self):
        """เริ่มระบบ monitoring"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        self.monitoring_thread = threading.Thread(
            target=self._system_monitoring_loop,
            daemon=True,
            name="SystemMonitoring"
        )
        self.monitoring_thread.start()
        self.logger.info("🔍 เริ่มระบบ monitoring")
    
    def _system_monitoring_loop(self):
        """ลูป monitoring ระบบ"""
        while not self.shutdown_event.is_set() and self.trading_active:
            try:
                # อัพเดท system metrics
                self._update_system_metrics()
                
                # ตรวจสอบ health ของ components
                self._check_components_health()
                
                # อัพเดท performance metrics
                self._update_performance_metrics()
                
                # พัก 30 วินาที
                self.shutdown_event.wait(30)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน monitoring loop: {e}")
                self.shutdown_event.wait(60)
    
    def _start_trading_loop(self):
        """เริ่ม main trading loop"""
        if self.system_thread and self.system_thread.is_alive():
            return
        
        self.system_thread = threading.Thread(
            target=self._main_trading_loop,
            daemon=True,
            name="MainTradingLoop"
        )
        self.system_thread.start()
        self.logger.info("🔄 เริ่ม main trading loop")
    
    def _main_trading_loop(self):
        """ลูปการเทรดหลัก"""
        self.logger.info("🔄 เริ่ม main trading loop")
        
        while not self.shutdown_event.is_set() and self.trading_active:
            try:
                # ดึงสัญญาณจาก Signal Generator
                if self.signal_generator:
                    signal = self._get_next_trading_signal()
                    
                    if signal:
                        self.logger.info(f"📊 ได้รับสัญญาณ: {signal.get('signal_type', 'UNKNOWN')}")
                        
                        # ประมวลผลสัญญาณ
                        if self._should_execute_signal(signal):
                            self._execute_trading_signal(signal)
                    
                    # อัพเดท statistics
                    self.metrics.signals_generated += 1
                
                # ตรวจสอบและจัดการ positions
                self._manage_existing_positions()
                
                # ตรวจสอบ recovery operations
                self._check_recovery_operations()
                
                # พักสักครู่
                self.shutdown_event.wait(2)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน trading loop: {e}")
                traceback.print_exc()
                self.shutdown_event.wait(10)
        
        self.logger.info("🛑 หยุด main trading loop")
    
    def _get_next_trading_signal(self):
        """ดึงสัญญาณการเทรดถัดไป"""
        try:
            if hasattr(self.signal_generator, 'get_next_signal'):
                return self.signal_generator.get_next_signal(timeout=1.0)
            else:
                # Mock signal generation
                return self.signal_generator.get_next_signal()
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถดึงสัญญาณ: {e}")
            return None
    
    def _should_execute_signal(self, signal) -> bool:
        """ตรวจสอบว่าควร execute สัญญาณหรือไม่"""
        if not signal:
            return False
        
        # ตรวจสอบ confidence threshold
        confidence = signal.get('confidence', 0.0)
        if confidence < 0.5:
            self.logger.info(f"⚠️ Confidence ต่ำเกินไป: {confidence}")
            return False
        
        # ตรวจสอบ spread (ถ้ามี)
        max_spread = getattr(self.settings, 'max_spread', 3.0)
        current_spread = signal.get('spread', 0.0)
        if current_spread > max_spread:
            self.logger.info(f"⚠️ Spread สูงเกินไป: {current_spread}")
            return False
        
        # ตรวจสอบจำนวน positions ปัจจุบัน
        if self.position_tracker:
            open_positions = self._get_open_positions_count()
            max_positions = getattr(self.settings, 'max_positions_total', 100)
            if open_positions >= max_positions:
                self.logger.info(f"⚠️ ถึงขีดจำกัด positions: {open_positions}")
                return False
        
        return True
    
    def _execute_trading_signal(self, signal):
        """Execute สัญญาณการเทรด"""
        try:
            if not self.order_executor:
                self.logger.error("❌ Order Executor ไม่พร้อมใช้งาน")
                return
            
            symbol = signal.get('symbol', 'XAUUSD')
            order_type = signal.get('signal_type', 'BUY')
            volume = signal.get('volume', 0.01)
            comment = f"AUTO_{signal.get('signal_id', 'UNKNOWN')}"
            
            # Execute order
            if hasattr(self.order_executor, 'execute_market_order'):
                result = self.order_executor.execute_market_order(symbol, order_type, volume, comment)
            else:
                result = self.order_executor.execute_market_order(symbol, order_type, volume, comment)
            
            if result:
                self.logger.info(f"✅ Execute สำเร็จ: {result.get('ticket', 'UNKNOWN')}")
                
                # เพิ่ม position เข้าระบบติดตาม
                if self.position_tracker and hasattr(self.position_tracker, 'add_position'):
                    self.position_tracker.add_position(result)
                
                # อัพเดท statistics
                self.metrics.orders_executed += 1
                
                # Mark signal as executed
                if hasattr(self.signal_generator, 'mark_signal_executed'):
                    self.signal_generator.mark_signal_executed(
                        signal.get('signal_id', ''),
                        result.get('price', 0.0)
                    )
            else:
                self.logger.warning(f"❌ Execute ล้มเหลว: {signal.get('signal_id', 'UNKNOWN')}")
                
        except Exception as e:
            self.logger.error(f"💥 ข้อผิดพลาดใน execute signal: {e}")
            traceback.print_exc()
    
    def _manage_existing_positions(self):
        """จัดการ positions ที่มีอยู่"""
        try:
            if not self.position_tracker:
                return
            
            if hasattr(self.position_tracker, 'get_open_positions'):
                open_positions = self.position_tracker.get_open_positions()
            else:
                open_positions = []
            
            for position in open_positions:
                # ตรวจสอบว่าต้อง recovery หรือไม่
                if self._should_add_to_recovery(position):
                    self._add_position_to_recovery(position)
                
                # ตรวจสอบการปิด position (กำไร)
                elif self._should_close_position(position):
                    self._close_position(position)
                    
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการจัดการ positions: {e}")
    
    def _should_add_to_recovery(self, position) -> bool:
        """ตรวจสอบว่าควรเพิ่ม position เข้า recovery หรือไม่"""
        # ตรวจสอบว่า position ขาดทุนมากพอหรือไม่
        current_profit = position.get('profit', 0.0)
        entry_price = position.get('open_price', 0.0)
        volume = position.get('volume', 0.01)
        
        # เงื่อนไขการเข้า recovery: ขาดทุนมากกว่า 50 pips หรือ กำไร/ขาดทุน < -$10
        loss_threshold = -10.0  # $10
        
        if current_profit < loss_threshold:
            self.logger.info(f"🔄 Position {position.get('ticket', 'UNKNOWN')} เข้าเงื่อนไข Recovery - Loss: ${abs(current_profit)}")
            return True
        
        return False
    
    def _add_position_to_recovery(self, position):
        """เพิ่ม position เข้าระบบ recovery"""
        try:
            if not self.recovery_engine:
                self.logger.error("❌ Recovery Engine ไม่พร้อมใช้งาน")
                return
            
            if hasattr(self.recovery_engine, 'add_position_to_recovery'):
                self.recovery_engine.add_position_to_recovery(position)
                self.metrics.recovery_operations += 1
                self.logger.info(f"🔄 เพิ่ม position {position.get('ticket', 'UNKNOWN')} เข้า Recovery")
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถเพิ่ม position เข้า recovery: {e}")
    
    def _should_close_position(self, position) -> bool:
        """ตรวจสอบว่าควรปิด position หรือไม่"""
        current_profit = position.get('profit', 0.0)
        
        # ปิดเมื่อกำไรมากกว่า $5
        profit_threshold = 5.0
        
        if current_profit > profit_threshold:
            return True
        
        # หรือเมื่อถึงเวลาที่กำหนด (24 ชั่วโมง)
        open_time = position.get('open_time')
        if open_time and isinstance(open_time, datetime):
            time_diff = datetime.now() - open_time
            if time_diff.total_seconds() > 24 * 3600:  # 24 hours
                return True
        
        return False
    
    def _close_position(self, position):
        """ปิด position"""
        try:
            ticket = position.get('ticket')
            current_profit = position.get('profit', 0.0)
            
            if self.position_tracker and hasattr(self.position_tracker, 'close_position'):
                success = self.position_tracker.close_position(ticket, profit=current_profit)
                
                if success:
                    self.logger.info(f"✅ ปิด position {ticket} - กำไร: ${current_profit}")
                    
                    # บันทึกผลงาน
                    if self.performance_tracker and hasattr(self.performance_tracker, 'record_trade'):
                        self.performance_tracker.record_trade(current_profit)
                    
                    # Mark signal as successful ถ้ากำไร
                    if current_profit > 0 and hasattr(self.signal_generator, 'mark_signal_successful'):
                        comment = position.get('comment', '')
                        if 'AUTO_' in comment:
                            signal_id = comment.replace('AUTO_', '')
                            self.signal_generator.mark_signal_successful(signal_id, current_profit)
                
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถปิด position: {e}")
    
    def _check_recovery_operations(self):
        """ตรวจสอบ recovery operations"""
        try:
            if not self.recovery_engine:
                return
            
            if hasattr(self.recovery_engine, 'get_recovery_status'):
                recovery_status = self.recovery_engine.get_recovery_status()
                
                positions_in_recovery = recovery_status.get('positions_in_recovery', 0)
                if positions_in_recovery > 0:
                    self.logger.info(f"🔄 Recovery: {positions_in_recovery} positions กำลังถูก recover")
                    
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจสอบ recovery: {e}")
    
    def _get_open_positions_count(self) -> int:
        """ดึงจำนวน positions ที่เปิดอยู่"""
        try:
            if self.position_tracker and hasattr(self.position_tracker, 'get_open_positions'):
                positions = self.position_tracker.get_open_positions()
                return len(positions) if positions else 0
            return 0
        except:
            return 0
    
    def _update_system_metrics(self):
        """อัพเดท system metrics"""
        try:
            current_time = datetime.now()
            self.metrics.last_update = current_time
            
            # คำนวณ uptime
            uptime = current_time - self.metrics.start_time
            self.metrics.uptime_seconds = int(uptime.total_seconds())
            
            # อัพเดท component running count
            running_count = 0
            for component_info in self.components.values():
                if component_info.status == ComponentStatus.RUNNING:
                    running_count += 1
            self.metrics.components_running = running_count
            
            # อัพเดท system statistics
            self.system_statistics['total_uptime'] = self.metrics.uptime_seconds
            self.system_statistics['last_health_check'] = current_time
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถอัพเดท system metrics: {e}")
    
    def _check_components_health(self):
        """ตรวจสอบ health ของ components"""
        try:
            health_status = {}
            
            for name, component_info in self.components.items():
                if component_info.instance:
                    # ตรวจสอบ health แต่ละ component
                    if hasattr(component_info.instance, 'get_health_status'):
                        health = component_info.instance.get_health_status()
                    else:
                        # Default health check
                        if component_info.status == ComponentStatus.RUNNING:
                            health = "HEALTHY"
                        elif component_info.status == ComponentStatus.ERROR:
                            health = "ERROR"
                        else:
                            health = "UNKNOWN"
                    
                    health_status[name] = health
                    component_info.health_status = health
                    component_info.last_update = datetime.now()
            
            self.system_statistics['components_health'] = health_status
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถตรวจสอบ components health: {e}")
    
    def _update_performance_metrics(self):
        """อัพเดท performance metrics"""
        try:
            performance_data = {}
            
            # Signal Generator metrics
            if self.signal_generator and hasattr(self.signal_generator, 'get_statistics'):
                performance_data['signal_generator'] = self.signal_generator.get_statistics()
            
            # Position Tracker metrics
            if self.position_tracker and hasattr(self.position_tracker, 'get_position_summary'):
                performance_data['position_tracker'] = self.position_tracker.get_position_summary()
            
            # Recovery Engine metrics
            if self.recovery_engine and hasattr(self.recovery_engine, 'get_recovery_status'):
                performance_data['recovery_engine'] = self.recovery_engine.get_recovery_status()
            
            # Order Executor metrics
            if self.order_executor and hasattr(self.order_executor, 'get_execution_statistics'):
                performance_data['order_executor'] = self.order_executor.get_execution_statistics()
            
            # Performance Tracker metrics
            if self.performance_tracker and hasattr(self.performance_tracker, 'get_performance_summary'):
                performance_data['performance_tracker'] = self.performance_tracker.get_performance_summary()
            
            self.system_statistics['performance_metrics'] = performance_data
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถอัพเดท performance metrics: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """ดึงสถานะระบบปัจจุบัน"""
        try:
            # Basic system info
            current_time = datetime.now()
            uptime = current_time - self.metrics.start_time
            
            # Component status summary
            component_status_summary = {}
            for name, info in self.components.items():
                component_status_summary[name] = {
                    'status': info.status.value,
                    'health': info.health_status,
                    'load_time': info.load_time.strftime('%H:%M:%S') if info.load_time else None,
                    'start_time': info.start_time.strftime('%H:%M:%S') if info.start_time else None,
                    'error': info.error_message
                }
            
            # Performance summary
            performance_summary = {}
            if self.system_statistics.get('performance_metrics'):
                perf_data = self.system_statistics['performance_metrics']
                
                # Signal Generator summary
                if 'signal_generator' in perf_data:
                    sg_data = perf_data['signal_generator']
                    performance_summary['signals'] = {
                        'generated_today': sg_data.get('signals_generated_today', 0),
                        'executed_today': sg_data.get('signals_executed_today', 0),
                        'success_rate': sg_data.get('success_rate_percent', 0.0),
                        'queue_size': sg_data.get('queue_size', 0)
                    }
                
                # Position summary
                if 'position_tracker' in perf_data:
                    pt_data = perf_data['position_tracker']
                    performance_summary['positions'] = {
                        'open_count': pt_data.get('open_positions_count', 0),
                        'total_profit': pt_data.get('total_profit', 0.0),
                        'open_volume': pt_data.get('open_volume', 0.0)
                    }
                
                # Recovery summary
                if 'recovery_engine' in perf_data:
                    re_data = perf_data['recovery_engine']
                    performance_summary['recovery'] = {
                        'positions_in_recovery': re_data.get('positions_in_recovery', 0),
                        'recovery_operations': re_data.get('recovery_operations', 0)
                    }
            
            return {
                # System Overview
                'system_state': self.system_state.value,
                'trading_active': self.trading_active,
                'auto_trading_enabled': self.auto_trading_enabled,
                
                # Time & Uptime
                'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                'start_time': self.metrics.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'uptime_hours': round(uptime.total_seconds() / 3600, 2),
                'uptime_formatted': str(uptime).split('.')[0],  # Remove microseconds
                
                # Components
                'components_loaded': self.metrics.components_loaded,
                'components_running': self.metrics.components_running,
                'total_components': self.metrics.total_components,
                'components_status': component_status_summary,
                
                # Performance
                'performance_summary': performance_summary,
                
                # System Metrics
                'system_metrics': {
                    'signals_generated': self.metrics.signals_generated,
                    'orders_executed': self.metrics.orders_executed,
                    'recovery_operations': self.metrics.recovery_operations,
                    'errors_count': self.metrics.errors_count
                },
                
                # Health Check
                'last_health_check': self.system_statistics.get('last_health_check', '').strftime('%H:%M:%S') if self.system_statistics.get('last_health_check') else 'Never'
            }
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถดึงสถานะระบบ: {e}")
            return {
                'system_state': 'ERROR',
                'error_message': str(e),
                'trading_active': False
            }
    
    def get_detailed_performance(self) -> Dict[str, Any]:
        """ดึงข้อมูล performance แบบละเอียด"""
        try:
            detailed_performance = {}
            
            # Signal Generator Performance
            if self.signal_generator and hasattr(self.signal_generator, 'get_strategy_performance'):
                detailed_performance['signal_strategies'] = self.signal_generator.get_strategy_performance()
                
            if self.signal_generator and hasattr(self.signal_generator, 'get_session_analysis'):
                detailed_performance['session_analysis'] = self.signal_generator.get_session_analysis()
            
            # Position Performance
            if self.position_tracker and hasattr(self.position_tracker, 'get_detailed_summary'):
                detailed_performance['positions_detailed'] = self.position_tracker.get_detailed_summary()
            
            # Recovery Performance
            if self.recovery_engine and hasattr(self.recovery_engine, 'get_detailed_status'):
                detailed_performance['recovery_detailed'] = self.recovery_engine.get_detailed_status()
            
            # Overall Performance
            if self.performance_tracker and hasattr(self.performance_tracker, 'get_detailed_metrics'):
                detailed_performance['overall_metrics'] = self.performance_tracker.get_detailed_metrics()
            
            return detailed_performance
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถดึง detailed performance: {e}")
            return {}
    
    def enable_auto_trading(self):
        """เปิดใช้งาน auto trading"""
        self.auto_trading_enabled = True
        self.logger.info("✅ เปิดใช้งาน Auto Trading")
    
    def disable_auto_trading(self):
        """ปิดใช้งาน auto trading"""
        self.auto_trading_enabled = False
        self.logger.info("⏸️ ปิดใช้งาน Auto Trading")
    
    def restart_component(self, component_name: str) -> bool:
        """รีสตาร์ท component เฉพาะ"""
        try:
            if component_name not in self.components:
                self.logger.error(f"❌ ไม่พบ component: {component_name}")
                return False
            
            self.logger.info(f"🔄 กำลังรีสตาร์ท {component_name}...")
            
            # หยุด component
            component = getattr(self, component_name, None)
            if component:
                # หยุดการทำงาน
                stop_methods = {
                    'market_analyzer': 'stop_analysis',
                    'signal_generator': 'stop_signal_generation',
                    'recovery_engine': 'stop_recovery_system',
                    'position_tracker': 'stop_position_tracking',
                    'order_executor': 'stop_order_execution',
                    'performance_tracker': 'stop_performance_tracking'
                }
                
                stop_method = stop_methods.get(component_name)
                if stop_method and hasattr(component, stop_method):
                    getattr(component, stop_method)()
                    self.logger.info(f"🛑 หยุด {component_name}")
            
            # โหลดใหม่
            success = self._load_component(component_name)
            
            if success:
                self.components[component_name].status = ComponentStatus.LOADED
                self.components[component_name].load_time = datetime.now()
                self.logger.info(f"✅ รีสตาร์ท {component_name} สำเร็จ")
                
                # เริ่มใหม่ถ้าระบบกำลังทำงาน
                if self.trading_active:
                    start_methods = {
                        'market_analyzer': 'start_analysis',
                        'signal_generator': 'start_signal_generation',
                        'recovery_engine': 'start_recovery_system',
                        'position_tracker': 'start_position_tracking',
                        'order_executor': 'start_order_execution',
                        'performance_tracker': 'start_performance_tracking'
                    }
                    
                    start_method = start_methods.get(component_name)
                    new_component = getattr(self, component_name, None)
                    if start_method and new_component and hasattr(new_component, start_method):
                        if getattr(new_component, start_method)():
                            self.components[component_name].status = ComponentStatus.RUNNING
                            self.components[component_name].start_time = datetime.now()
                            self.logger.info(f"🚀 เริ่ม {component_name} ใหม่")
                
                return True
            else:
                self.logger.error(f"❌ รีสตาร์ท {component_name} ล้มเหลว")
                return False
                
        except Exception as e:
            self.logger.error(f"💥 ข้อผิดพลาดในการรีสตาร์ท {component_name}: {e}")
            traceback.print_exc()
            return False

    def force_close_all_positions(self):
        """บังคับปิด positions ทั้งหมด"""
        try:
            self.logger.warning("⚠️ บังคับปิด positions ทั้งหมด...")
            
            if not self.position_tracker:
                self.logger.error("❌ Position Tracker ไม่พร้อมใช้งาน")
                return
            
            if hasattr(self.position_tracker, 'get_open_positions'):
                open_positions = self.position_tracker.get_open_positions()
                
                if not open_positions:
                    self.logger.info("ℹ️ ไม่มี positions ที่เปิดอยู่")
                    return
                
                closed_count = 0
                for position in open_positions:
                    try:
                        ticket = position.get('ticket')
                        current_profit = position.get('profit', 0.0)
                        
                        if hasattr(self.position_tracker, 'close_position'):
                            success = self.position_tracker.close_position(ticket, profit=current_profit)
                            if success:
                                closed_count += 1
                                self.logger.info(f"✅ ปิด position {ticket} (บังคับ)")
                    
                    except Exception as e:
                        self.logger.error(f"❌ ไม่สามารถปิด position {position.get('ticket', 'UNKNOWN')}: {e}")
                
                self.logger.info(f"✅ ปิด positions ทั้งหมด: {closed_count}/{len(open_positions)}")
            
        except Exception as e:
            self.logger.error(f"💥 ข้อผิดพลาดในการปิด positions: {e}")
            traceback.print_exc()
    
    def emergency_stop(self):
        """หยุดฉุกเฉิน"""
        try:
            self.logger.critical("🚨 EMERGENCY STOP - หยุดระบบฉุกเฉิน!")
            
            # หยุดการเทรดทันที
            self.trading_active = False
            self.auto_trading_enabled = False
            self.system_state = SystemState.ERROR
            
            # ส่งสัญญาณหยุด
            self.shutdown_event.set()
            
            # หยุด Signal Generator ก่อน
            if self.signal_generator and hasattr(self.signal_generator, 'stop_signal_generation'):
                self.signal_generator.stop_signal_generation()
                self.logger.critical("🛑 หยุด Signal Generator ฉุกเฉิน")
            
            # บังคับปิด positions ทั้งหมด
            self.force_close_all_positions()
            
            # หยุด components อื่นๆ
            components_to_stop = [
                'order_executor', 'recovery_engine', 'position_tracker', 
                'performance_tracker', 'market_analyzer'
            ]
            
            for component_name in components_to_stop:
                try:
                    component = getattr(self, component_name, None)
                    if component:
                        stop_methods = {
                            'market_analyzer': 'stop_analysis',
                            'recovery_engine': 'stop_recovery_system',
                            'position_tracker': 'stop_position_tracking',
                            'order_executor': 'stop_order_execution',
                            'performance_tracker': 'stop_performance_tracking'
                        }
                        
                        stop_method = stop_methods.get(component_name)
                        if stop_method and hasattr(component, stop_method):
                            getattr(component, stop_method)()
                            self.components[component_name].status = ComponentStatus.STOPPED
                
                except Exception as e:
                    self.logger.error(f"❌ ไม่สามารถหยุด {component_name} ฉุกเฉิน: {e}")
            
            self.logger.critical("🚨 EMERGENCY STOP เสร็จสิ้น")
            
        except Exception as e:
            self.logger.critical(f"💥 ข้อผิดพลาดใน Emergency Stop: {e}")
            traceback.print_exc()
    
    def reset_system(self):
        """รีเซ็ตระบบทั้งหมด"""
        try:
            self.logger.info("🔄 กำลังรีเซ็ตระบบ...")
            
            # หยุดระบบก่อน
            if self.trading_active:
                self.stop_trading()
            
            # รอให้ระบบหยุดสมบูรณ์
            time.sleep(2)
            
            # รีเซ็ต metrics
            self.metrics = SystemMetrics()
            
            # รีเซ็ต statistics
            self.system_statistics = {
                'start_time': datetime.now(),
                'total_uptime': 0,
                'components_health': {},
                'last_health_check': None,
                'performance_metrics': {},
                'error_log': deque(maxlen=100)
            }
            
            # รีเซ็ต component status
            for component_info in self.components.values():
                component_info.status = ComponentStatus.NOT_LOADED
                component_info.error_message = None
                component_info.load_time = None
                component_info.start_time = None
                component_info.health_status = "UNKNOWN"
            
            # รีเซ็ตสถานะระบบ
            self.system_state = SystemState.INITIALIZING
            self.trading_active = False
            self.auto_trading_enabled = False
            
            # รีเซ็ต shutdown event
            self.shutdown_event.clear()
            
            self.logger.info("✅ รีเซ็ตระบบเสร็จสิ้น")
            
        except Exception as e:
            self.logger.error(f"💥 ข้อผิดพลาดในการรีเซ็ตระบบ: {e}")
            traceback.print_exc()
    
    def export_system_logs(self, filename: Optional[str] = None) -> str:
        """ส่งออก system logs"""
        try:
            if filename is None:
                filename = f"system_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'system_status': self.get_system_status(),
                'detailed_performance': self.get_detailed_performance(),
                'system_statistics': {
                    'start_time': self.system_statistics['start_time'].isoformat() if isinstance(self.system_statistics['start_time'], datetime) else str(self.system_statistics['start_time']),
                    'total_uptime': self.system_statistics['total_uptime'],
                    'components_health': self.system_statistics['components_health'],
                    'last_health_check': self.system_statistics['last_health_check'].isoformat() if isinstance(self.system_statistics['last_health_check'], datetime) else str(self.system_statistics['last_health_check']),
                    'error_log': list(self.system_statistics['error_log'])
                },
                'components_info': {}
            }
            
            # Component details
            for name, info in self.components.items():
                export_data['components_info'][name] = {
                    'status': info.status.value,
                    'health_status': info.health_status,
                    'error_message': info.error_message,
                    'load_time': info.load_time.isoformat() if info.load_time else None,
                    'start_time': info.start_time.isoformat() if info.start_time else None,
                    'last_update': info.last_update.isoformat() if info.last_update else None
                }
            
            # Individual component exports
            if self.signal_generator and hasattr(self.signal_generator, 'export_signal_history'):
                signal_history_file = self.signal_generator.export_signal_history()
                if signal_history_file:
                    export_data['signal_history_file'] = signal_history_file
            
            # Write main export file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"📁 ส่งออก system logs: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถส่งออก system logs: {e}")
            return ""
    
    def get_component_instance(self, component_name: str):
        """ดึง instance ของ component"""
        return getattr(self, component_name, None)
    
    def is_trading_active(self) -> bool:
        """ตรวจสอบว่าการเทรดเปิดอยู่หรือไม่"""
        return self.trading_active
    
    def is_system_ready(self) -> bool:
        """ตรวจสอบว่าระบบพร้อมหรือไม่"""
        return self.system_state == SystemState.READY or self.system_state == SystemState.RUNNING
    
    def get_uptime(self) -> timedelta:
        """ดึงเวลาที่ระบบทำงาน"""
        return datetime.now() - self.metrics.start_time
    
    def get_system_health(self) -> str:
        """ดึงสุขภาพระบบโดยรวม"""
        if self.system_state == SystemState.ERROR:
            return "ERROR"
        elif self.system_state == SystemState.RUNNING and self.trading_active:
            return "HEALTHY"
        elif self.system_state == SystemState.READY:
            return "READY"
        elif self.system_state == SystemState.INITIALIZING:
            return "INITIALIZING"
        else:
            return "UNKNOWN"
    
    def __del__(self):
        """Destructor - ทำความสะอาดเมื่อ object ถูกลบ"""
        try:
            if self.trading_active:
                self.stop_trading()
        except:
            pass

# ===============================
# GLOBAL INSTANCE MANAGEMENT
# ===============================

_trading_system_instance: Optional[IntelligentTradingSystem] = None

def get_intelligent_trading_system(settings=None, logger=None) -> IntelligentTradingSystem:
    """ดึง Trading System instance (Singleton pattern)"""
    global _trading_system_instance
    if _trading_system_instance is None:
        _trading_system_instance = IntelligentTradingSystem(settings, logger)
    return _trading_system_instance

def reset_trading_system():
    """รีเซ็ต Trading System instance"""
    global _trading_system_instance
    if _trading_system_instance:
        _trading_system_instance.emergency_stop()
        time.sleep(2)
    _trading_system_instance = None

# ===============================
# UTILITY FUNCTIONS
# ===============================

def create_trading_system_report(trading_system: IntelligentTradingSystem) -> Dict[str, Any]:
    """สร้างรายงานระบบเทรด"""
    try:
        system_status = trading_system.get_system_status()
        detailed_performance = trading_system.get_detailed_performance()
        
        # Component health summary
        components_health = system_status.get('components_status', {})
        healthy_components = sum(1 for comp in components_health.values() if comp.get('health') == 'HEALTHY')
        total_components = len(components_health)
        
        # Performance summary
        performance_summary = system_status.get('performance_summary', {})
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'system_overview': {
                'system_state': system_status.get('system_state'),
                'trading_active': system_status.get('trading_active'),
                'uptime_formatted': system_status.get('uptime_formatted'),
                'health_score': f"{healthy_components}/{total_components}",
                'overall_health': trading_system.get_system_health()
            },
            'trading_performance': {
                'signals_today': performance_summary.get('signals', {}).get('generated_today', 0),
                'execution_rate': performance_summary.get('signals', {}).get('success_rate', 0),
                'open_positions': performance_summary.get('positions', {}).get('open_count', 0),
                'total_profit': performance_summary.get('positions', {}).get('total_profit', 0.0),
                'recovery_operations': performance_summary.get('recovery', {}).get('recovery_operations', 0)
            },
            'system_metrics': system_status.get('system_metrics', {}),
            'components_status': components_health,
            'detailed_performance': detailed_performance
        }
        
        return report
        
    except Exception as e:
        return {
            'report_timestamp': datetime.now().isoformat(),
            'error': f"ไม่สามารถสร้างรายงาน: {e}",
            'system_overview': {'overall_health': 'ERROR'}
        }

# ===============================
# TEST FUNCTIONS
# ===============================

def test_trading_system():
    """ทดสอบ Trading System แบบครบถ้วน"""
    print("🧪 เริ่มทดสอบ Intelligent Trading System...")
    
    # สร้าง Trading System
    trading_system = IntelligentTradingSystem()
    
    try:
        # ทดสอบการเริ่มต้น components
        print("\n📦 ทดสอบการโหลด Components...")
        components_loaded = trading_system.initialize_components()
        print(f"   Components โหลดสำเร็จ: {components_loaded}")
        
        # ทดสอบสถานะระบบ
        print("\n📊 ทดสอบสถานะระบบ...")
        system_status = trading_system.get_system_status()
        print(f"   System State: {system_status.get('system_state')}")
        print(f"   Components Running: {system_status.get('components_running')}")
        print(f"   System Health: {trading_system.get_system_health()}")
        
        # ทดสอบการเริ่มการเทรด
        if trading_system.is_system_ready():
            print("\n🚀 ทดสอบการเริ่มการเทรด...")
            success = trading_system.start_trading()
            print(f"   การเริ่มการเทรด: {'สำเร็จ' if success else 'ล้มเหลว'}")
            
            if success:
                # รอสักครู่เพื่อให้ระบบทำงาน
                print("   รอให้ระบบทำงาน 10 วินาที...")
                time.sleep(10)
                
                # ตรวจสอบสถานะหลังเริ่มเทรด
                updated_status = trading_system.get_system_status()
                print(f"   Trading Active: {updated_status.get('trading_active')}")
                
                # สร้างรายงาน
                print("\n📋 สร้างรายงานระบบ...")
                report = create_trading_system_report(trading_system)
                print(f"   รายงานสถานะ: {report['system_overview']['overall_health']}")
                
                # ทดสอบการหยุด
                print("\n🛑 ทดสอบการหยุดการเทรด...")
                trading_system.stop_trading()
                print("   หยุดการเทรดเสร็จสิ้น")
        
        print("\n✅ ทดสอบ Trading System เสร็จสิ้น")
        
    except Exception as e:
        print(f"\n❌ ข้อผิดพลาดในการทดสอบ: {e}")
        traceback.print_exc()
    
    finally:
        # ทำความสะอาด
        if trading_system.trading_active:
            trading_system.emergency_stop()

def benchmark_trading_system():
   """ทดสอบประสิทธิภาพ Trading System"""
   print("⚡ ทดสอบประสิทธิภาพ Trading System...")
   
   trading_system = IntelligentTradingSystem()
   
   try:
       # วัดเวลาการโหลด components
       start_time = time.time()
       components_loaded = trading_system.initialize_components()
       load_time = time.time() - start_time
       
       print(f"📊 ผลลัพธ์การทดสอบ:")
       print(f"   เวลาโหลด Components: {load_time:.2f} วินาที")
       print(f"   Components โหลดสำเร็จ: {components_loaded}")
       
       # วัดเวลาการดึงสถานะ
       start_time = time.time()
       for i in range(10):
           trading_system.get_system_status()
       status_time = (time.time() - start_time) / 10
       
       print(f"   เวลาดึงสถานะเฉลี่ย: {status_time*1000:.2f} ms")
       
       # ทดสอบ memory usage (ถ้าสามารถ)
       try:
           import psutil
           process = psutil.Process()
           memory_mb = process.memory_info().rss / 1024 / 1024
           print(f"   Memory Usage: {memory_mb:.1f} MB")
       except ImportError:
           print("   Memory Usage: ไม่สามารถวัดได้ (ต้องติดตั้ง psutil)")
       
   except Exception as e:
       print(f"❌ ข้อผิดพลาดในการทดสอบประสิทธิภาพ: {e}")

if __name__ == "__main__":
   test_trading_system()
   print("\n" + "="*60)
   benchmark_trading_system()
