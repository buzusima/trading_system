#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RECOVERY ENGINE - Real MT5 Integration Version (COMPLETE)
========================================================
เครื่องมือหลักสำหรับ Execute Recovery Strategies
เชื่อมต่อกับ MT5 จริง ไม่ใช่ Mock Data
"""

import threading
import time
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
import queue

# เชื่อมต่อ internal modules
from config.settings import get_system_settings, MarketSession
from config.trading_params import get_trading_parameters, RecoveryMethod
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class RecoveryStatus(Enum):
    """สถานะของการ Recovery"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    FAILED = "FAILED"

class RecoveryPriority(Enum):
    """ระดับความสำคัญของการ Recovery"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5

class RecoveryTrigger(Enum):
    """สิ่งที่กระตุ้นให้เริ่ม Recovery"""
    LOSING_POSITION = "LOSING_POSITION"
    DRAWDOWN_THRESHOLD = "DRAWDOWN_THRESHOLD"
    TIME_BASED = "TIME_BASED"
    MARKET_CONDITION = "MARKET_CONDITION"
    MANUAL_TRIGGER = "MANUAL_TRIGGER"

@dataclass
class RecoveryTask:
    """คลาสสำหรับเก็บข้อมูล Recovery Task"""
    task_id: str
    created_time: datetime
    position_id: str
    recovery_method: RecoveryMethod
    priority: RecoveryPriority
    trigger: RecoveryTrigger
    original_symbol: str
    original_direction: str
    original_volume: float
    original_price: float
    current_price: float
    unrealized_loss: float
    status: RecoveryStatus = RecoveryStatus.PENDING
    recovery_positions: List[str] = field(default_factory=list)
    total_recovery_volume: float = 0.0
    recovery_cost: float = 0.0
    estimated_completion_time: Optional[datetime] = None
    started_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    notes: str = ""

class RecoveryScheduler:
    """จัดลำดับและจัดการ Recovery Tasks"""
    
    def __init__(self):
        self.logger = setup_component_logger("RecoveryScheduler")
        
        # Task Management
        self.pending_tasks: Dict[str, RecoveryTask] = {}
        self.active_tasks: Dict[str, RecoveryTask] = {}
        self.completed_tasks: List[RecoveryTask] = []
        self.task_queue = queue.PriorityQueue()
        
        # Configuration
        self.max_concurrent_recoveries = 3
        
        self.logger.info("📅 เริ่มต้น Recovery Scheduler")
    
    def add_recovery_task(self, task: RecoveryTask) -> bool:
        """เพิ่ม Recovery Task"""
        try:
            self.pending_tasks[task.task_id] = task
            
            # เพิ่มเข้า Priority Queue (priority สูง = เลขน้อย)
            priority = 6 - task.priority.value
            self.task_queue.put((priority, task.created_time, task))
            
            self.logger.info(f"📋 เพิ่ม Recovery Task: {task.task_id} | "
                           f"Priority: {task.priority.value} | "
                           f"Method: {task.recovery_method.value}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถเพิ่ม Recovery Task ได้: {e}")
            return False
    
    def get_next_task(self) -> Optional[RecoveryTask]:
        """ดึง Task ถัดไป"""
        try:
            if self.task_queue.empty():
                return None
            
            # ตรวจสอบว่ามี slot ว่างหรือไม่
            if len(self.active_tasks) >= self.max_concurrent_recoveries:
                return None
            
            priority, created_time, task = self.task_queue.get_nowait()
            
            # ย้ายจาก pending ไปยัง active
            if task.task_id in self.pending_tasks:
                del self.pending_tasks[task.task_id]
                self.active_tasks[task.task_id] = task
                task.status = RecoveryStatus.IN_PROGRESS
                task.started_time = datetime.now()
            
            return task
            
        except queue.Empty:
            return None
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึง Next Task: {e}")
            return None
    
    def complete_task(self, task_id: str, success: bool = True) -> bool:
        """ทำเครื่องหมาย Task เสร็จสิ้น"""
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

class RecoveryEngine:
    """🛠️ Recovery Engine - Real MT5 Integration"""
    
    def __init__(self):
        self.logger = setup_component_logger("RecoveryEngine")
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Core Components
        self.scheduler = RecoveryScheduler()
        
        # Engine Status
        self.engine_active = False
        self.recovery_thread = None
        self.monitor_thread = None
        
        # Statistics
        self.total_recoveries_attempted = 0
        self.total_recoveries_successful = 0
        
        # MT5 Connection
        self.mt5_connected = False
        
        self.logger.info("🛠️ เริ่มต้น Recovery Engine (Real MT5)")
    
    def start_recovery_engine(self) -> None:
        """เริ่มต้น Recovery Engine"""
        if self.engine_active:
            self.logger.warning("⚠️ Recovery Engine กำลังทำงานอยู่แล้ว")
            return
        
        self.logger.info("🚀 เริ่มต้น Recovery Engine System")
        
        # ตรวจสอบการเชื่อมต่อ MT5
        if not self._ensure_mt5_connection():
            self.logger.error("❌ ไม่สามารถเชื่อมต่อ MT5 ได้")
            return
        
        # เริ่ม Engine Threads
        self.engine_active = True
        self.recovery_thread = threading.Thread(
            target=self._recovery_execution_loop, 
            daemon=True,
            name="RecoveryExecutionLoop"
        )
        self.monitor_thread = threading.Thread(
            target=self._recovery_monitoring_loop, 
            daemon=True,
            name="RecoveryMonitorLoop"
        )
        
        self.recovery_thread.start()
        self.monitor_thread.start()
        
        self.logger.info("✅ Recovery Engine System เริ่มทำงานแล้ว")
    
    def stop_recovery_engine(self) -> None:
        """หยุด Recovery Engine"""
        self.engine_active = False
        
        if self.recovery_thread and self.recovery_thread.is_alive():
            self.recovery_thread.join(timeout=10.0)
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10.0)
        
        self.logger.info("🛑 หยุด Recovery Engine System")
    
    def _ensure_mt5_connection(self) -> bool:
        """ตรวจสอบการเชื่อมต่อ MT5"""
        try:
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                self.logger.error("❌ MT5 ไม่ได้เปิดหรือไม่ได้เชื่อมต่อ")
                return False
            
            if not terminal_info.connected:
                self.logger.error("❌ MT5 ไม่ได้เชื่อมต่อกับ Server")
                return False
            
            account_info = mt5.account_info()
            if account_info is None:
                self.logger.error("❌ ไม่สามารถดึงข้อมูลบัญชี MT5 ได้")
                return False
            
            self.mt5_connected = True
            self.logger.info(f"✅ เชื่อมต่อ MT5 สำเร็จ - Account: {account_info.login}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการตรวจสอบ MT5: {e}")
            return False
    
    def trigger_recovery(self, position_id: str, trigger_type: RecoveryTrigger,
                        priority: RecoveryPriority = RecoveryPriority.MEDIUM) -> bool:
        """เรียกใช้การ Recovery สำหรับ Position"""
        try:
            # ดึงข้อมูล Position จริง
            position_info = self._get_real_position_info(position_id)
            if not position_info:
                self.logger.error(f"❌ ไม่พบข้อมูล Position: {position_id}")
                return False
            
            # สร้าง Recovery Task
            recovery_task = self._create_recovery_task(position_info, trigger_type, priority)
            
            # เพิ่มเข้า Scheduler
            success = self.scheduler.add_recovery_task(recovery_task)
            
            if success:
                self.total_recoveries_attempted += 1
                self.logger.info(f"🔄 เริ่ม Recovery: {position_id} | Task: {recovery_task.task_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถเริ่ม Recovery ได้: {e}")
            return False
    
    def _create_recovery_task(self, position_info: Dict[str, Any], 
                            trigger_type: RecoveryTrigger,
                            priority: RecoveryPriority) -> RecoveryTask:
        """สร้าง Recovery Task"""
        task_id = f"REC_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{position_info['position_id']}"
        
        return RecoveryTask(
            task_id=task_id,
            created_time=datetime.now(),
            position_id=position_info['position_id'],
            recovery_method=RecoveryMethod.MARTINGALE_SMART,  # Default
            priority=priority,
            trigger=trigger_type,
            original_symbol=position_info['symbol'],
            original_direction=position_info['direction'],
            original_volume=position_info['volume'],
            original_price=position_info['open_price'],
            current_price=position_info['current_price'],
            unrealized_loss=position_info['unrealized_loss']
        )
    
    def _recovery_execution_loop(self) -> None:
        """Main Recovery Execution Loop"""
        self.logger.info("🔄 เริ่มต้น Recovery Execution Loop")
        
        while self.engine_active:
            try:
                if len(self.scheduler.active_tasks) >= self.scheduler.max_concurrent_recoveries:
                    time.sleep(1)
                    continue
                
                task = self.scheduler.get_next_task()
                if not task:
                    time.sleep(1)
                    continue
                
                self._execute_recovery_task(task)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Recovery Execution Loop: {e}")
                time.sleep(5)
    
    def _execute_recovery_task(self, task: RecoveryTask) -> None:
        """Execute Recovery Task"""
        try:
            self.logger.info(f"🔧 กำลัง Execute Recovery: {task.task_id}")
            
            # Execute Martingale Recovery (Default)
            success = self._execute_martingale_recovery(task)
            
            if success:
                self.total_recoveries_successful += 1
                self.logger.info(f"✅ Recovery สำเร็จ: {task.task_id}")
            else:
                self.logger.warning(f"⚠️ Recovery ไม่สำเร็จ: {task.task_id}")
            
            self.scheduler.complete_task(task.task_id, success=success)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Execute Recovery: {e}")
            self.scheduler.complete_task(task.task_id, success=False)
    
    def _get_real_position_info(self, position_ticket: str) -> Optional[Dict[str, Any]]:
        """ดึงข้อมูล Position จริงจาก MT5"""
        try:
            if not self.mt5_connected:
                return None
            
            position = mt5.positions_get(ticket=int(position_ticket))
            if not position or len(position) == 0:
                self.logger.warning(f"⚠️ ไม่พบ Position: {position_ticket}")
                return None
            
            pos = position[0]
            tick = mt5.symbol_info_tick(pos.symbol)
            current_price = tick.bid if pos.type == 1 else tick.ask
            
            return {
                'position_id': str(pos.ticket),
                'symbol': pos.symbol,
                'direction': 'BUY' if pos.type == 0 else 'SELL',
                'volume': pos.volume,
                'open_price': pos.price_open,
                'current_price': current_price,
                'unrealized_loss': pos.profit,
                'swap': pos.swap,
                'commission': pos.commission,
                'magic_number': pos.magic,
                'comment': pos.comment,
                'time_open': datetime.fromtimestamp(pos.time)
            }
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถดึงข้อมูล Position จาก MT5: {e}")
            return None
    
    def _execute_martingale_recovery(self, task: RecoveryTask) -> bool:
        """Execute Martingale Recovery จริง"""
        try:
            position_info = self._get_real_position_info(task.position_id)
            if not position_info:
                return False
            
            original_volume = position_info['volume']
            recovery_volume = original_volume * 2.0
            
            original_direction = position_info['direction']
            recovery_direction = 'SELL' if original_direction == 'BUY' else 'BUY'
            
            self.logger.info(f"🔄 Martingale Recovery: {task.position_id} | "
                           f"Original: {original_direction} {original_volume} | "
                           f"Recovery: {recovery_direction} {recovery_volume}")
            
            return self._send_recovery_order(
                symbol=position_info['symbol'],
                direction=recovery_direction,
                volume=recovery_volume,
                comment=f"Recovery_Martingale_{task.position_id}"
            )
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Martingale Recovery: {e}")
            return False
    
    def _send_recovery_order(self, symbol: str, direction: str, volume: float, comment: str) -> bool:
        """ส่งออร์เดอร์ Recovery ไปยัง MT5"""
        try:
            if not self.mt5_connected:
                return False
            
            order_type = mt5.ORDER_TYPE_BUY if direction == 'BUY' else mt5.ORDER_TYPE_SELL
            
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return False
            
            price = tick.ask if direction == 'BUY' else tick.bid
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": 123456,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"❌ ส่งออร์เดอร์ Recovery ไม่สำเร็จ: {result.retcode if result else 'None'}")
                return False
            
            self.logger.info(f"✅ ส่งออร์เดอร์ Recovery สำเร็จ: {result.order}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการส่งออร์เดอร์ Recovery: {e}")
            return False
    
    def _recovery_monitoring_loop(self) -> None:
        """Recovery Monitoring Loop"""
        while self.engine_active:
            try:
                # ตรวจสอบสถานะ Active Tasks
                for task_id, task in list(self.scheduler.active_tasks.items()):
                    self._monitor_recovery_progress_real(task)
                
                time.sleep(30)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Recovery Monitoring Loop: {e}")
                time.sleep(60)
    
    def _monitor_recovery_progress_real(self, task: RecoveryTask) -> None:
        """ติดตามความคืบหน้าของ Recovery จาก MT5 จริง"""
        try:
            position_info = self._get_real_position_info(task.position_id)
            if not position_info:
                # Position ปิดแล้ว = Recovery สำเร็จ
                self.scheduler.complete_task(task.task_id, success=True)
                self.total_recoveries_successful += 1
                self.logger.info(f"🎉 Recovery สำเร็จ (Position ปิดแล้ว): {task.task_id}")
                return
            
            current_loss = position_info['unrealized_loss']
            if current_loss >= 0:
                self.logger.info(f"🎉 Recovery กำลังจะสำเร็จ: {task.task_id} | P&L: ${current_loss:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Monitor Recovery: {e}")
    
    def get_recovery_summary(self) -> Dict[str, Any]:
        """สรุปผลการ Recovery ทั้งหมด"""
        success_rate = 0.0
        if self.total_recoveries_attempted > 0:
            success_rate = (self.total_recoveries_successful / self.total_recoveries_attempted) * 100
        
        return {
            "total_recovery_tasks": len(self.scheduler.completed_tasks),
            "total_attempted": self.total_recoveries_attempted,
            "total_successful": self.total_recoveries_successful,
            "success_rate": success_rate,
            "active_recoveries": len(self.scheduler.active_tasks),
            "pending_recoveries": len(self.scheduler.pending_tasks),
            "engine_active": self.engine_active
        }

# === GLOBAL RECOVERY ENGINE INSTANCE ===
_global_recovery_engine: Optional[RecoveryEngine] = None

def get_recovery_engine() -> RecoveryEngine:
    """ดึง RecoveryEngine แบบ Singleton"""
    global _global_recovery_engine
    if _global_recovery_engine is None:
        _global_recovery_engine = RecoveryEngine()
    return _global_recovery_engine