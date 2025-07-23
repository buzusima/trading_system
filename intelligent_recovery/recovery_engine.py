#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RECOVERY ENGINE - Recovery Execution Engine
==========================================
เครื่องมือหลักสำหรับ Execute Recovery Strategies
ระบบ "แก้ไม้" ที่ไม่ยอมให้เกิดการขาดทุน - Recovery เท่านั้น!

Key Features:
- Execute recovery strategies อัตโนมัติ
- ไม่ใช้ Stop Loss เด็ดขาด (ตาม requirement)
- รองรับ recovery methods หลากหลาย
- Intelligent recovery selection ตาม market conditions
- Real-time monitoring และ adjustment
- 100% Recovery Success Rate Target

เชื่อมต่อไปยัง:
- intelligent_recovery/strategies/* (กลยุทธ์ Recovery)
- intelligent_recovery/recovery_selector.py (เลือกกลยุทธ์)
- position_management/position_tracker.py (ติดตาม positions)
- mt5_integration/order_executor.py (ส่งออร์เดอร์)
- market_intelligence/market_analyzer.py (วิเคราะห์ตลาด)
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
import queue
import json

# เชื่อมต่อ internal modules
from config.settings import get_system_settings, MarketSession
from config.trading_params import get_trading_parameters, RecoveryMethod
from utilities.professional_logger import setup_trading_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class RecoveryStatus(Enum):
    """สถานะของการ Recovery"""
    PENDING = "PENDING"             # รอการ Recovery
    IN_PROGRESS = "IN_PROGRESS"     # กำลัง Recovery
    COMPLETED = "COMPLETED"         # Recovery สำเร็จ
    PAUSED = "PAUSED"              # หยุดชั่วคราว
    FAILED = "FAILED"              # Recovery ล้มเหลว (ไม่ควรเกิดขึ้น!)

class RecoveryPriority(Enum):
    """ระดับความสำคัญของการ Recovery"""
    LOW = 1         # Drawdown น้อย
    MEDIUM = 2      # Drawdown ปานกลาง
    HIGH = 3        # Drawdown สูง
    CRITICAL = 4    # Drawdown วิกฤต
    EMERGENCY = 5   # ต้อง Recovery ทันที

class RecoveryTrigger(Enum):
    """สิ่งที่กระตุ้นให้เริ่ม Recovery"""
    LOSING_POSITION = "LOSING_POSITION"         # มี position ขาดทุน
    DRAWDOWN_THRESHOLD = "DRAWDOWN_THRESHOLD"   # Drawdown เกินกำหนด
    TIME_BASED = "TIME_BASED"                   # ตาม เวลาที่กำหนด
    MARKET_CONDITION = "MARKET_CONDITION"       # สภาพตลาดเปลี่ยน
    MANUAL_TRIGGER = "MANUAL_TRIGGER"           # เรียกใช้ manual

@dataclass
class RecoveryTask:
    """
    คลาสสำหรับเก็บข้อมูล Recovery Task
    """
    task_id: str                               # ID เฉพาะของ Task
    created_time: datetime                     # เวลาที่สร้าง Task
    position_id: str                           # Position ที่ต้อง Recovery
    
    # Recovery Parameters
    recovery_method: RecoveryMethod            # วิธี Recovery ที่เลือก
    priority: RecoveryPriority                # ความสำคัญ
    trigger: RecoveryTrigger                  # สิ่งที่กระตุ้น
    
    # Position Information
    original_symbol: str                       # สัญลักษณ์ต้นฉบับ
    original_direction: str                    # ทิศทางต้นฉบับ (BUY/SELL)
    original_volume: float                     # Volume ต้นฉบับ
    original_price: float                      # ราคาเปิดต้นฉบับ
    current_price: float                       # ราคาปัจจุบัน
    unrealized_loss: float                     # ขาดทุนที่ยังไม่ตัด
    
    # Recovery Progress
    status: RecoveryStatus = RecoveryStatus.PENDING
    recovery_attempts: int = 0                 # จำนวนครั้งที่พยายาม Recovery
    recovery_positions: List[str] = field(default_factory=list)  # Positions ที่สร้างเพื่อ Recovery
    total_recovery_volume: float = 0.0         # Volume รวมที่ใช้ Recovery
    
    # Market Context
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    session_context: MarketSession = MarketSession.ASIAN
    volatility_level: str = "MEDIUM"
    
    # Recovery Metrics
    expected_recovery_time: timedelta = field(default_factory=lambda: timedelta(hours=1))
    max_recovery_budget: float = 0.0           # งบประมาณสูงสุดสำหรับ Recovery
    current_recovery_cost: float = 0.0         # ค่าใช้จ่าย Recovery ปัจจุบัน
    
    # Execution Details
    started_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    last_update_time: datetime = field(default_factory=datetime.now)
    
    # Additional Information
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class RecoveryScheduler:
    """
    จัดการลำดับการ Recovery และ Priority Queue
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Task Management
        self.pending_tasks: List[RecoveryTask] = []
        self.active_tasks: Dict[str, RecoveryTask] = {}
        self.completed_tasks: List[RecoveryTask] = []
        self.task_queue = queue.PriorityQueue()
        
        # Scheduler Settings
        self.max_concurrent_recoveries = 5      # Recovery พร้อมกันสูงสุด
        self.task_check_interval = 1.0          # ตรวจสอบทุก 1 วินาที
        
        self.logger.info("📋 เริ่มต้น Recovery Scheduler")
    
    def add_recovery_task(self, task: RecoveryTask) -> bool:
        """
        เพิ่ม Recovery Task เข้าสู่ระบบ
        """
        try:
            # ตรวจสอบ Task ซ้ำ
            if any(t.position_id == task.position_id for t in self.pending_tasks):
                self.logger.warning(f"⚠️ Recovery Task ซ้ำ: {task.position_id}")
                return False
            
            # เพิ่มเข้า Pending List
            self.pending_tasks.append(task)
            
            # เพิ่มเข้า Priority Queue (priority สูง = ค่าต่ำ)
            priority_value = -task.priority.value  # ค่าลบเพื่อให้ priority สูงขึ้นก่อน
            self.task_queue.put((priority_value, task.created_time, task))
            
            self.logger.info(f"✅ เพิ่ม Recovery Task: {task.task_id} | "
                           f"Position: {task.position_id} | "
                           f"Priority: {task.priority.name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเพิ่ม Recovery Task: {e}")
            return False
    
    def get_next_task(self) -> Optional[RecoveryTask]:
        """
        ดึง Recovery Task ถัดไปตาม Priority
        """
        try:
            if not self.task_queue.empty():
                _, _, task = self.task_queue.get_nowait()
                
                # ย้ายจาก pending ไป active
                if task in self.pending_tasks:
                    self.pending_tasks.remove(task)
                
                self.active_tasks[task.task_id] = task
                task.status = RecoveryStatus.IN_PROGRESS
                task.started_time = datetime.now()
                
                return task
            
            return None
            
        except queue.Empty:
            return None
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึง Next Task: {e}")
            return None
    
    def complete_task(self, task_id: str, success: bool = True) -> bool:
        """
        ทำเครื่องหมาย Task เสร็จสิ้น
        """
        try:
            if task_id not in self.active_tasks:
                self.logger.warning(f"⚠️ ไม่พบ Active Task: {task_id}")
                return False
            
            task = self.active_tasks.pop(task_id)
            task.completed_time = datetime.now()
            task.status = RecoveryStatus.COMPLETED if success else RecoveryStatus.FAILED
            
            self.completed_tasks.append(task)
            
            self.logger.info(f"✅ Recovery Task เสร็จสิ้น: {task_id} | "
                           f"สถานะ: {task.status.value}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการทำเครื่องหมาย Task เสร็จสิ้น: {e}")
            return False
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        ดึงสถานะของ Scheduler
        """
        return {
            "pending_tasks": len(self.pending_tasks),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "queue_size": self.task_queue.qsize(),
            "max_concurrent": self.max_concurrent_recoveries
        }

class RecoveryEngine:
    """
    🛠️ Main Recovery Engine Class
    
    เครื่องมือหลักสำหรับ Execute Recovery Strategies
    รองรับการ Recovery แบบ "แก้ไม้" - ไม่ยอมขาดทุน!
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Core Components
        self.scheduler = RecoveryScheduler()
        self.recovery_selector = None       # จะเชื่อมต่อใน start()
        self.position_tracker = None        # จะเชื่อมต่อใน start()
        self.market_analyzer = None         # จะเชื่อมต่อใน start()
        
        # Recovery Strategies
        self.recovery_strategies: Dict[RecoveryMethod, Any] = {}
        
        # Engine Status
        self.engine_active = False
        self.recovery_thread = None
        self.monitor_thread = None
        
        # Statistics
        self.total_recoveries_attempted = 0
        self.total_recoveries_successful = 0
        self.total_recovery_time = timedelta()
        self.current_recovery_budget = 0.0
        
        # Performance Metrics
        self.recovery_success_rate = 100.0  # เป้าหมาย 100%
        self.average_recovery_time = timedelta(minutes=30)
        
        self.logger.info("🛠️ เริ่มต้น Recovery Engine")
    
    @handle_trading_errors(ErrorCategory.RECOVERY, ErrorSeverity.CRITICAL)
    async def start_recovery_engine(self) -> None:
        """
        เริ่มต้น Recovery Engine
        """
        if self.engine_active:
            self.logger.warning("⚠️ Recovery Engine กำลังทำงานอยู่แล้ว")
            return
        
        self.logger.info("🚀 เริ่มต้น Recovery Engine System")
        
        # เชื่อมต่อ Recovery Selector
        try:
            from intelligent_recovery.recovery_selector import RecoverySelector
            self.recovery_selector = RecoverySelector()
        except ImportError:
            self.logger.error("❌ ไม่สามารถเชื่อมต่อ Recovery Selector")
            return
        
        # เชื่อมต่อ Position Tracker
        try:
            from position_management.position_tracker import PositionTracker
            self.position_tracker = PositionTracker()
        except ImportError:
            self.logger.error("❌ ไม่สามารถเชื่อมต่อ Position Tracker")
            return
        
        # เชื่อมต่อ Market Analyzer
        try:
            from market_intelligence.market_analyzer import MarketAnalyzer
            self.market_analyzer = MarketAnalyzer()
        except ImportError:
            self.logger.error("❌ ไม่สามารถเชื่อมต่อ Market Analyzer")
            return
        
        # เริ่มต้น Recovery Strategies
        await self._initialize_recovery_strategies()
        
        # เริ่ม Engine Threads
        self.engine_active = True
        self.recovery_thread = threading.Thread(target=self._recovery_execution_loop, daemon=True)
        self.monitor_thread = threading.Thread(target=self._recovery_monitoring_loop, daemon=True)
        
        self.recovery_thread.start()
        self.monitor_thread.start()
        
        self.logger.info("✅ Recovery Engine System เริ่มทำงานแล้ว")
    
    async def _initialize_recovery_strategies(self) -> None:
        """
        เริ่มต้น Recovery Strategies ทั้งหมด
        """
        try:
            # Martingale Smart Strategy
            from intelligent_recovery.strategies.martingale_smart import MartingaleSmartStrategy
            martingale_strategy = MartingaleSmartStrategy()
            self.recovery_strategies[RecoveryMethod.MARTINGALE_SMART] = martingale_strategy
            
            # Grid Intelligent Strategy
            from intelligent_recovery.strategies.grid_intelligent import GridIntelligentStrategy
            grid_strategy = GridIntelligentStrategy()
            self.recovery_strategies[RecoveryMethod.GRID_INTELLIGENT] = grid_strategy
            
            # อื่นๆ จะเพิ่มเมื่อสร้างไฟล์
            
            self.logger.info("✅ เริ่มต้น Recovery Strategies สำเร็จ")
            
        except ImportError as e:
            self.logger.error(f"❌ ไม่สามารถโหลด Recovery Strategies: {e}")
    
    def trigger_recovery(self, position_id: str, trigger_type: RecoveryTrigger,
                        priority: RecoveryPriority = RecoveryPriority.MEDIUM) -> bool:
        """
        เรียกใช้การ Recovery สำหรับ Position
        """
        try:
            # ดึงข้อมูล Position
            position_info = self._get_position_info(position_id)
            if not position_info:
                self.logger.error(f"❌ ไม่พบข้อมูล Position: {position_id}")
                return False
            
            # ตรวจสอบว่าต้อง Recovery หรือไม่
            if not self._should_trigger_recovery(position_info, trigger_type):
                self.logger.debug(f"📊 Position {position_id} ไม่ต้อง Recovery")
                return False
            
            # สร้าง Recovery Task
            recovery_task = self._create_recovery_task(position_info, trigger_type, priority)
            
            # เพิ่มเข้า Scheduler
            success = self.scheduler.add_recovery_task(recovery_task)
            
            if success:
                self.logger.info(f"🎯 เรียกใช้ Recovery: {position_id} | "
                               f"Trigger: {trigger_type.value} | "
                               f"Priority: {priority.name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเรียกใช้ Recovery: {e}")
            return False
    
    def _get_position_info(self, position_id: str) -> Optional[Dict[str, Any]]:
        """
        ดึงข้อมูล Position จาก Position Tracker
        """
        try:
            if self.position_tracker:
                return self.position_tracker.get_position(position_id)
            return None
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Position: {e}")
            return None
    
    def _should_trigger_recovery(self, position_info: Dict[str, Any], 
                               trigger_type: RecoveryTrigger) -> bool:
        """
        ตรวจสอบว่าควร Trigger Recovery หรือไม่
        """
        try:
            # ตรวจสอบ Unrealized Loss
            unrealized_pnl = position_info.get('unrealized_pnl', 0.0)
            
            # หาก Position กำไร ไม่ต้อง Recovery
            if unrealized_pnl >= 0:
                return False
            
            # ตรวจสอบตาม Trigger Type
            if trigger_type == RecoveryTrigger.LOSING_POSITION:
                # Trigger ทันทีสำหรับ Position ขาดทุน
                return True
            
            elif trigger_type == RecoveryTrigger.DRAWDOWN_THRESHOLD:
                # Trigger เมื่อ Drawdown เกินกำหนด
                drawdown_threshold = self.trading_params.get('recovery_drawdown_threshold', -100.0)
                return unrealized_pnl <= drawdown_threshold
            
            # อื่นๆ...
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจสอบ Recovery Trigger: {e}")
            return False
    
    def _create_recovery_task(self, position_info: Dict[str, Any], 
                            trigger_type: RecoveryTrigger,
                            priority: RecoveryPriority) -> RecoveryTask:
        """
        สร้าง Recovery Task
        """
        # สร้าง Task ID
        task_id = f"REC_{position_info['position_id']}_{int(time.time())}"
        
        # ดึง Market Conditions ปัจจุบัน
        market_conditions = {}
        current_session = MarketSession.ASIAN
        
        if self.market_analyzer:
            market_conditions = self.market_analyzer.get_current_market_state()
            current_session = self.market_analyzer.get_current_session()
        
        # เลือก Recovery Method
        recovery_method = RecoveryMethod.MARTINGALE_SMART  # Default
        if self.recovery_selector:
            recovery_method = self.recovery_selector.select_recovery_method(
                position_info, market_conditions, current_session
            )
        
        # สร้าง Recovery Task
        task = RecoveryTask(
            task_id=task_id,
            created_time=datetime.now(),
            position_id=position_info['position_id'],
            recovery_method=recovery_method,
            priority=priority,
            trigger=trigger_type,
            original_symbol=position_info.get('symbol', 'XAUUSD'),
            original_direction=position_info.get('direction', 'BUY'),
            original_volume=position_info.get('volume', 0.1),
            original_price=position_info.get('open_price', 0.0),
            current_price=position_info.get('current_price', 0.0),
            unrealized_loss=position_info.get('unrealized_pnl', 0.0),
            market_conditions=market_conditions,
            session_context=current_session
        )
        
        return task
    
    def _recovery_execution_loop(self) -> None:
        """
        Main Recovery Execution Loop
        รันใน separate thread
        """
        self.logger.info("🔄 เริ่มต้น Recovery Execution Loop")
        
        while self.engine_active:
            try:
                # ตรวจสอบว่ามี slot ว่างสำหรับ Recovery ใหม่
                if len(self.scheduler.active_tasks) >= self.scheduler.max_concurrent_recoveries:
                    time.sleep(1)
                    continue
                
                # ดึง Task ถัดไป
                task = self.scheduler.get_next_task()
                if not task:
                    time.sleep(1)
                    continue
                
                # Execute Recovery
                await self._execute_recovery_task(task)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Recovery Execution Loop: {e}")
                time.sleep(5)
    
    async def _execute_recovery_task(self, task: RecoveryTask) -> None:
        """
        Execute Recovery Task
        """
        self.logger.info(f"🎯 เริ่ม Recovery: {task.task_id} | "
                        f"Method: {task.recovery_method.value}")
        
        try:
            # ดึง Recovery Strategy
            if task.recovery_method not in self.recovery_strategies:
                self.logger.error(f"❌ ไม่พบ Recovery Strategy: {task.recovery_method.value}")
                self.scheduler.complete_task(task.task_id, success=False)
                return
            
            strategy = self.recovery_strategies[task.recovery_method]
            
            # Execute Recovery Strategy
            recovery_result = await strategy.execute_recovery(task)
            
            # อัพเดท Task Status
            if recovery_result.get('success', False):
                self.total_recoveries_successful += 1
                self.scheduler.complete_task(task.task_id, success=True)
                
                self.logger.info(f"✅ Recovery สำเร็จ: {task.task_id}")
            else:
                # Recovery ไม่สำเร็จ - พยายามใหม่หรือเปลี่ยนกลยุทธ์
                await self._handle_recovery_failure(task)
            
            self.total_recoveries_attempted += 1
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Recovery Execution: {e}")
            await self._handle_recovery_failure(task)
    
    async def _handle_recovery_failure(self, task: RecoveryTask) -> None:
        """
        จัดการกรณี Recovery ล้มเหลว
        """
        task.recovery_attempts += 1
        
        # ถ้าพยายามไม่เกิน 3 ครั้ง ลองใหม่
        if task.recovery_attempts < 3:
            self.logger.warning(f"⚠️ Recovery ล้มเหลว ครั้งที่ {task.recovery_attempts}: {task.task_id}")
            
            # เปลี่ยน Recovery Method
            if self.recovery_selector:
                new_method = self.recovery_selector.select_alternative_method(task)
                task.recovery_method = new_method
            
            # เพิ่มกลับเข้า Queue
            task.status = RecoveryStatus.PENDING
            self.scheduler.add_recovery_task(task)
            
        else:
            # Recovery ล้มเหลวหลายครั้ง - ต้องการการแทรกแซงพิเศษ
            self.logger.critical(f"🚨 Recovery ล้มเหลว 3 ครั้ง: {task.task_id}")
            
            # TODO: เรียกใช้ Emergency Recovery Protocol
            self.scheduler.complete_task(task.task_id, success=False)
    
    def _recovery_monitoring_loop(self) -> None:
        """
        ตรวจสอบและปรับปรุง Recovery Tasks
        """
        self.logger.info("👁️ เริ่มต้น Recovery Monitoring Loop")
        
        while self.engine_active:
            try:
                # ตรวจสอบ Active Tasks
                for task_id, task in list(self.scheduler.active_tasks.items()):
                    self._monitor_recovery_progress(task)
                
                # ทำความสะอาด Completed Tasks เก่า
                self._cleanup_old_tasks()
                
                time.sleep(self.scheduler.task_check_interval)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Recovery Monitoring: {e}")
                time.sleep(5)
    
    def _monitor_recovery_progress(self, task: RecoveryTask) -> None:
        """
        ติดตาม Progress ของ Recovery Task
        """
        try:
            # อัพเดทเวลา
            task.last_update_time = datetime.now()
            
            # ตรวจสอบ Timeout
            if task.started_time:
                elapsed = datetime.now() - task.started_time
                if elapsed > task.expected_recovery_time * 2:  # 2 เท่าของเวลาที่คาดหวัง
                    self.logger.warning(f"⏰ Recovery Timeout: {task.task_id}")
                    # TODO: Handle timeout
            
            # อัพเดทข้อมูล Position
            position_info = self._get_position_info(task.position_id)
            if position_info:
                task.current_price = position_info.get('current_price', task.current_price)
                task.unrealized_loss = position_info.get('unrealized_pnl', task.unrealized_loss)
                
                # ตรวจสอบว่า Recovery สำเร็จแล้วหรือยัง
                if task.unrealized_loss >= 0:
                    self.logger.info(f"🎉 Recovery สำเร็จโดยตลาด: {task.task_id}")
                    self.scheduler.complete_task(task.task_id, success=True)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการติดตาม Recovery Progress: {e}")
    
    def _cleanup_old_tasks(self) -> None:
        """
        ทำความสะอาด Tasks เก่า
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            # ลบ Completed Tasks เก่า
            original_count = len(self.scheduler.completed_tasks)
            self.scheduler.completed_tasks = [
                task for task in self.scheduler.completed_tasks
                if task.completed_time and task.completed_time > cutoff_time
            ]
            
            cleaned_count = original_count - len(self.scheduler.completed_tasks)
            if cleaned_count > 0:
                self.logger.info(f"🧹 ลบ Completed Tasks เก่า {cleaned_count} รายการ")
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการทำความสะอาด Tasks: {e}")
    
    def stop_recovery_engine(self) -> None:
        """
        หยุดการทำงานของ Recovery Engine
        """
        self.logger.info("🛑 หยุด Recovery Engine System")
        
        self.engine_active = False
        
        # รอให้ Threads จบ
        if self.recovery_thread and self.recovery_thread.is_alive():
            self.recovery_thread.join(timeout=10)
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("✅ Recovery Engine System หยุดแล้ว")
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """
        ดึงสถิติการทำงานของ Recovery Engine
        """
        # คำนวณ Success Rate
        if self.total_recoveries_attempted > 0:
            success_rate = (self.total_recoveries_successful / self.total_recoveries_attempted) * 100
        else:
            success_rate = 100.0
        
        return {
            "engine_active": self.engine_active,
            "total_recoveries_attempted": self.total_recoveries_attempted,
            "total_recoveries_successful": self.total_recoveries_successful,
            "recovery_success_rate": round(success_rate, 2),
            "current_recovery_budget": self.current_recovery_budget,
            "scheduler_status": self.scheduler.get_scheduler_status(),
            "available_strategies": [method.value for method in self.recovery_strategies.keys()],
            "average_recovery_time_minutes": self.average_recovery_time.total_seconds() / 60
        }
    
    def get_active_recoveries(self) -> List[Dict[str, Any]]:
        """
        ดึงรายการ Recovery ที่กำลังดำเนินการ
        """
        active_recoveries = []
        
        for task_id, task in self.scheduler.active_tasks.items():
            recovery_info = {
                "task_id": task.task_id,
                "position_id": task.position_id,
                "recovery_method": task.recovery_method.value,
                "priority": task.priority.name,
                "status": task.status.value,
                "unrealized_loss": task.unrealized_loss,
                "recovery_attempts": task.recovery_attempts,
                "started_time": task.started_time.isoformat() if task.started_time else None,
                "elapsed_time_minutes": (datetime.now() - task.started_time).total_seconds() / 60 if task.started_time else 0,
                "recovery_positions_count": len(task.recovery_positions)
            }
            active_recoveries.append(recovery_info)
        
        return active_recoveries
    
    def force_recovery_completion(self, task_id: str, success: bool = True) -> bool:
        """
        บังคับให้ Recovery เสร็จสิ้น (สำหรับการแทรกแซงแบบ Manual)
        """
        try:
            if task_id not in self.scheduler.active_tasks:
                self.logger.warning(f"⚠️ ไม่พบ Active Recovery Task: {task_id}")
                return False
            
            self.logger.info(f"⚡ บังคับให้ Recovery เสร็จสิ้น: {task_id} | Success: {success}")
            
            return self.scheduler.complete_task(task_id, success)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการบังคับ Recovery เสร็จสิ้น: {e}")
            return False
    
    def pause_recovery(self, task_id: str) -> bool:
        """
        หยุด Recovery ชั่วคราว
        """
        try:
            if task_id not in self.scheduler.active_tasks:
                return False
            
            task = self.scheduler.active_tasks[task_id]
            task.status = RecoveryStatus.PAUSED
            
            self.logger.info(f"⏸️ หยุด Recovery ชั่วคราว: {task_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการหยุด Recovery: {e}")
            return False
    
    def resume_recovery(self, task_id: str) -> bool:
        """
        เริ่ม Recovery ต่อ
        """
        try:
            if task_id not in self.scheduler.active_tasks:
                return False
            
            task = self.scheduler.active_tasks[task_id]
            if task.status == RecoveryStatus.PAUSED:
                task.status = RecoveryStatus.IN_PROGRESS
                
                self.logger.info(f"▶️ เริ่ม Recovery ต่อ: {task_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเริ่ม Recovery ต่อ: {e}")
            return False
    
    def emergency_recovery_shutdown(self) -> None:
        """
        หยุดการทำงานของ Recovery Engine แบบฉุกเฉิน
        """
        self.logger.critical("🚨 Emergency Recovery Shutdown!")
        
        try:
            # หยุด Engine ทันที
            self.engine_active = False
            
            # ทำเครื่องหมาย Active Tasks ว่าหยุดฉุกเฉิน
            for task_id, task in self.scheduler.active_tasks.items():
                task.status = RecoveryStatus.PAUSED
                task.notes += f" | Emergency shutdown at {datetime.now()}"
            
            self.logger.critical("🛑 Emergency Recovery Shutdown เสร็จสิ้น")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Emergency Shutdown: {e}")

# === RECOVERY POSITION MONITOR ===
class RecoveryPositionMonitor:
    """
    ติดตามผลการ Recovery แบบ Real-time
    """
    
    def __init__(self, recovery_engine: RecoveryEngine):
        self.recovery_engine = recovery_engine
        self.logger = setup_trading_logger()
        
        # Monitoring Data
        self.position_recovery_map: Dict[str, str] = {}  # position_id -> task_id
        self.recovery_performance: Dict[str, Dict] = {}
        
        self.logger.info("📊 เริ่มต้น Recovery Position Monitor")
    
    def track_recovery_position(self, position_id: str, task_id: str) -> None:
        """
        ติดตาม Position ที่อยู่ในขั้นตอน Recovery
        """
        self.position_recovery_map[position_id] = task_id
        
        # เริ่มต้นข้อมูล Performance
        self.recovery_performance[task_id] = {
            "start_time": datetime.now(),
            "initial_loss": 0.0,
            "current_loss": 0.0,
            "recovery_positions": [],
            "total_volume_used": 0.0,
            "recovery_cost": 0.0
        }
        
        self.logger.info(f"📍 ติดตาม Recovery Position: {position_id} -> {task_id}")
    
    def update_recovery_progress(self, task_id: str, progress_data: Dict[str, Any]) -> None:
        """
        อัพเดท Progress ของการ Recovery
        """
        if task_id in self.recovery_performance:
            self.recovery_performance[task_id].update(progress_data)
            
            # Log สำคัญ
            current_loss = progress_data.get('current_loss', 0.0)
            if current_loss >= 0:
                self.logger.info(f"🎉 Recovery กำลังจะสำเร็จ: {task_id} | "
                               f"Current P&L: {current_loss:.2f}")
    
    def get_recovery_summary(self) -> Dict[str, Any]:
        """
        สรุปผลการ Recovery ทั้งหมด
        """
        total_tasks = len(self.recovery_performance)
        successful_recoveries = 0
        total_recovery_time = timedelta()
        total_recovery_cost = 0.0
        
        for task_id, perf in self.recovery_performance.items():
            if perf.get('current_loss', -999) >= 0:
                successful_recoveries += 1
            
            if 'end_time' in perf:
                recovery_duration = perf['end_time'] - perf['start_time']
                total_recovery_time += recovery_duration
            
            total_recovery_cost += perf.get('recovery_cost', 0.0)
        
        return {
            "total_recovery_tasks": total_tasks,
            "successful_recoveries": successful_recoveries,
            "success_rate": (successful_recoveries / max(total_tasks, 1)) * 100,
            "average_recovery_time_minutes": (total_recovery_time.total_seconds() / 60) / max(total_tasks, 1),
            "total_recovery_cost": total_recovery_cost,
            "active_recoveries": len([p for p in self.recovery_performance.values() 
                                    if p.get('current_loss', -999) < 0])
        }

# === GLOBAL RECOVERY ENGINE INSTANCE ===
_global_recovery_engine: Optional[RecoveryEngine] = None

def get_recovery_engine() -> RecoveryEngine:
    """
    ดึง RecoveryEngine แบบ Singleton
    """
    global _global_recovery_engine
    if _global_recovery_engine is None:
        _global_recovery_engine = RecoveryEngine()
    return _global_recovery_engine

# === RECOVERY CONVENIENCE FUNCTIONS ===
def trigger_position_recovery(position_id: str, 
                            priority: RecoveryPriority = RecoveryPriority.MEDIUM) -> bool:
    """
    ฟังก์ชันสะดวกสำหรับเรียกใช้ Recovery
    """
    engine = get_recovery_engine()
    return engine.trigger_recovery(position_id, RecoveryTrigger.LOSING_POSITION, priority)

def get_recovery_status() -> Dict[str, Any]:
    """
    ฟังก์ชันสะดวกสำหรับดึงสถานะ Recovery
    """
    engine = get_recovery_engine()
    return engine.get_recovery_statistics()

def emergency_stop_all_recoveries() -> None:
    """
    ฟังก์ชันฉุกเฉินสำหรับหยุด Recovery ทั้งหมด
    """
    engine = get_recovery_engine()
    engine.emergency_recovery_shutdown()

async def main():
    """
    ทดสอบการทำงานของ Recovery Engine
    """
    print("🧪 ทดสอบ Recovery Engine")
    
    engine = get_recovery_engine()
    
    try:
        await engine.start_recovery_engine()
        
        # สร้าง Mock Recovery Task
        print("🎯 สร้าง Test Recovery Task")
        success = engine.trigger_recovery(
            position_id="TEST_POS_001",
            trigger_type=RecoveryTrigger.LOSING_POSITION,
            priority=RecoveryPriority.HIGH
        )
        print(f"Recovery Triggered: {success}")
        
        # รัน 15 วินาที
        await asyncio.sleep(15)
        
        # แสดงสถิติ
        stats = engine.get_recovery_statistics()
        print(f"📊 สถิติ Recovery Engine:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        # แสดง Active Recoveries
        active = engine.get_active_recoveries()
        print(f"🔄 Active Recoveries: {len(active)}")
        for recovery in active:
            print(f"  - {recovery['task_id']}: {recovery['status']} | Loss: {recovery['unrealized_loss']}")
        
    finally:
        engine.stop_recovery_engine()

if __name__ == "__main__":
    asyncio.run(main())