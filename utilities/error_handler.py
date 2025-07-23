#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPREHENSIVE ERROR HANDLING - ระบบจัดการข้อผิดพลาดแบบครบครัน
========================================================
ระบบจัดการข้อผิดพลาดระดับมืออาชีพสำหรับการเทรดดิ้ง
รองรับการ recovery อัตโนมัติและการแจ้งเตือนแบบเรียลไทม์

เชื่อมต่อไปยัง:
- utilities/professional_logger.py (การ log ข้อผิดพลาด)
- mt5_integration/connection_manager.py (จัดการการเชื่อมต่อ)
- gui_system/components/* (แสดงข้อผิดพลาดใน GUI)
"""

import sys
import traceback
import threading
import functools
from typing import Dict, List, Optional, Callable, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import logging
from pathlib import Path

class ErrorSeverity(Enum):
    """ระดับความรุนแรงของข้อผิดพลาด"""
    LOW = "LOW"           # ข้อผิดพลาดเล็กน้อย - ระบบทำงานต่อได้
    MEDIUM = "MEDIUM"     # ข้อผิดพลาดปานกลาง - อาจต้อง retry
    HIGH = "HIGH"         # ข้อผิดพลาดร้อนแรง - ต้องหยุดการทำงานชั่วคราว
    CRITICAL = "CRITICAL" # ข้อผิดพลาดวิกฤต - ต้องหยุดระบบ

class ErrorCategory(Enum):
    """ประเภทของข้อผิดพลาด"""
    CONNECTION = "CONNECTION"     # ปัญหาการเชื่อมต่อ MT5
    TRADING = "TRADING"          # ปัญหาการเทรด/ส่งออร์เดอร์
    MARKET_DATA = "MARKET_DATA"  # ปัญหาข้อมูลตลาด
    SYSTEM = "SYSTEM"            # ปัญหาระบบ
    RECOVERY = "RECOVERY"        # ปัญหาระบบ Recovery
    GUI = "GUI"                  # ปัญหา User Interface
    DATA = "DATA"                # ปัญหาการจัดการข้อมูล

@dataclass
class ErrorInfo:
    """ข้อมูลรายละเอียดของข้อผิดพลาด"""
    timestamp: datetime
    error_type: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    traceback_str: str
    function_name: str
    line_number: int
    recovery_attempted: bool = False
    recovery_successful: bool = False
    retry_count: int = 0
    context_data: Dict[str, Any] = field(default_factory=dict)

class RecoveryStrategy:
    """กลยุทธ์การ Recovery สำหรับข้อผิดพลาดแต่ละประเภท"""
    
    def __init__(self, name: str, max_retries: int = 3, delay: float = 1.0):
        self.name = name
        self.max_retries = max_retries
        self.delay = delay
        self.success_count = 0
        self.failure_count = 0
    
    def execute(self, error_info: ErrorInfo, recovery_func: Callable) -> bool:
        """
        ดำเนินการ Recovery Strategy
        """
        try:
            recovery_func(error_info)
            self.success_count += 1
            return True
        except Exception as e:
            self.failure_count += 1
            return False

class GlobalErrorHandler:
    """
    ตัวจัดการข้อผิดพลาดหลักของระบบ
    รองรับการ recovery อัตโนมัติและการติดตามข้อผิดพลาด
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger
        self.error_history: List[ErrorInfo] = []
        self.recovery_strategies: Dict[ErrorCategory, RecoveryStrategy] = {}
        self.error_callbacks: List[Callable[[ErrorInfo], None]] = []
        self.lock = threading.Lock()
        
        # สถิติข้อผิดพลาด
        self.error_counts: Dict[ErrorCategory, int] = {cat: 0 for cat in ErrorCategory}
        self.last_error_time: Dict[ErrorCategory, datetime] = {}
        
        # ตั้งค่า Recovery Strategies
        self._setup_recovery_strategies()
    
    def _setup_recovery_strategies(self):
        """ตั้งค่า Recovery Strategies สำหรับข้อผิดพลาดแต่ละประเภท"""
        
        # Connection Recovery - เชื่อมต่อ MT5 ใหม่
        self.recovery_strategies[ErrorCategory.CONNECTION] = RecoveryStrategy(
            name="MT5_Reconnect",
            max_retries=5,
            delay=2.0
        )
        
        # Trading Recovery - ลองส่งออร์เดอร์ใหม่
        self.recovery_strategies[ErrorCategory.TRADING] = RecoveryStrategy(
            name="Retry_Order",
            max_retries=3,
            delay=1.0
        )
        
        # Market Data Recovery - รีเฟรชข้อมูลตลาด
        self.recovery_strategies[ErrorCategory.MARKET_DATA] = RecoveryStrategy(
            name="Refresh_MarketData",
            max_retries=2,
            delay=0.5
        )
        
        # System Recovery - รีสตาร์ทโมดูลที่มีปัญหา
        self.recovery_strategies[ErrorCategory.SYSTEM] = RecoveryStrategy(
            name="Module_Restart",
            max_retries=2,
            delay=3.0
        )
    
    def setup_global_exception_handling(self):
        """ตั้งค่าการจัดการ Exception ระดับ Global"""
        
        def handle_exception(exc_type, exc_value, exc_traceback):
            """จัดการ Exception ที่ไม่ถูกจับ"""
            if issubclass(exc_type, KeyboardInterrupt):
                # ให้ KeyboardInterrupt ผ่านไปตามปกติ
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            error_info = self._create_error_info(
                exc_value,
                ErrorSeverity.CRITICAL,
                ErrorCategory.SYSTEM,
                exc_traceback
            )
            
            self.handle_error(error_info)
        
        # ตั้งค่า Global Exception Handler
        sys.excepthook = handle_exception
        
        # ตั้งค่า Threading Exception Handler (Python 3.8+)
        if hasattr(threading, 'excepthook'):
            def thread_exception_handler(args):
                error_info = self._create_error_info(
                    args.exc_value,
                    ErrorSeverity.HIGH,
                    ErrorCategory.SYSTEM,
                    args.exc_traceback
                )
                self.handle_error(error_info)
            
            threading.excepthook = thread_exception_handler
    
    def handle_error(self, error_info: ErrorInfo) -> bool:
        """
        จัดการข้อผิดพลาดหลัก
        Returns: True ถ้า recovery สำเร็จ, False ถ้าไม่สำเร็จ
        """
        with self.lock:
            # บันทึกข้อผิดพลาด
            self.error_history.append(error_info)
            self.error_counts[error_info.category] += 1
            self.last_error_time[error_info.category] = error_info.timestamp
            
            # Log ข้อผิดพลาด
            self._log_error(error_info)
            
            # แจ้งเตือน callbacks
            self._notify_callbacks(error_info)
            
            # ลอง Recovery (ถ้าเป็นข้อผิดพลาดที่ recovery ได้)
            recovery_success = self._attempt_recovery(error_info)
            
            # อัพเดทสถานะ recovery
            error_info.recovery_attempted = True
            error_info.recovery_successful = recovery_success
            
            return recovery_success
    
    def _create_error_info(self, 
                          exception: Exception, 
                          severity: ErrorSeverity,
                          category: ErrorCategory,
                          tb: Optional[Any] = None) -> ErrorInfo:
        """สร้าง ErrorInfo จาก Exception"""
        
        # ดึงข้อมูล traceback
        if tb is None:
            tb = sys.exc_info()[2]
        
        traceback_str = ''.join(traceback.format_exception(type(exception), exception, tb))
        
        # ดึงข้อมูลตำแหน่งข้อผิดพลาด
        frame = tb.tb_frame if tb else None
        function_name = frame.f_code.co_name if frame else "unknown"
        line_number = tb.tb_lineno if tb else 0
        
        return ErrorInfo(
            timestamp=datetime.now(),
            error_type=type(exception).__name__,
            message=str(exception),
            severity=severity,
            category=category,
            traceback_str=traceback_str,
            function_name=function_name,
            line_number=line_number
        )
    
    def _log_error(self, error_info: ErrorInfo):
        """บันทึก log ข้อผิดพลาด"""
        if not self.logger:
            return
        
        severity_emoji = {
            ErrorSeverity.LOW: "🟡",
            ErrorSeverity.MEDIUM: "🟠", 
            ErrorSeverity.HIGH: "🔴",
            ErrorSeverity.CRITICAL: "💥"
        }
        
        emoji = severity_emoji.get(error_info.severity, "❌")
        
        log_msg = (
            f"{emoji} {error_info.category.value} ERROR: {error_info.error_type} "
            f"in {error_info.function_name}:{error_info.line_number} - {error_info.message}"
        )
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_msg)
            self.logger.critical(f"Full traceback:\n{error_info.traceback_str}")
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_msg)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)
    
    def _notify_callbacks(self, error_info: ErrorInfo):
        """แจ้งเตือน callbacks ที่ลงทะเบียนไว้"""
        for callback in self.error_callbacks:
            try:
                callback(error_info)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in error callback: {e}")
    
    def _attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """ลอง Recovery ข้อผิดพลาด"""
        
        # ตรวจสอบว่ามี Recovery Strategy หรือไม่
        if error_info.category not in self.recovery_strategies:
            return False
        
        strategy = self.recovery_strategies[error_info.category]
        
        # ตรวจสอบจำนวนครั้งที่ retry แล้ว
        if error_info.retry_count >= strategy.max_retries:
            if self.logger:
                self.logger.warning(f"🚫 เกินจำนวน retry สำหรับ {error_info.category.value}")
            return False
        
        # ลอง Recovery
        if self.logger:
            self.logger.info(f"🔄 พยายาม Recovery: {strategy.name} (ครั้งที่ {error_info.retry_count + 1})")
        
        # TODO: Implement specific recovery functions
        # ตอนนี้จะ return False ก่อน จนกว่าจะมีการ implement recovery functions
        
        return False
        
    def add_error_callback(self, callback: Callable[[ErrorInfo], None]):
        """เพิ่ม callback สำหรับการแจ้งเตือนข้อผิดพลาด"""
        self.error_callbacks.append(callback)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """ดึงสถิติข้อผิดพลาด"""
        with self.lock:
            total_errors = len(self.error_history)
            recent_errors = [
                err for err in self.error_history 
                if err.timestamp > datetime.now() - timedelta(hours=1)
            ]
            
            return {
                "total_errors": total_errors,
                "recent_errors_1h": len(recent_errors),
                "error_by_category": dict(self.error_counts),
                "last_error_times": {
                    cat.value: time.isoformat() if time else None
                    for cat, time in self.last_error_time.items()
                },
                "recovery_stats": {
                    cat.value: {
                        "strategy": strategy.name,
                        "success_count": strategy.success_count,
                        "failure_count": strategy.failure_count,
                        "success_rate": (
                            strategy.success_count / 
                            (strategy.success_count + strategy.failure_count)
                            if (strategy.success_count + strategy.failure_count) > 0 else 0
                        )
                    }
                    for cat, strategy in self.recovery_strategies.items()
                }
            }
    
    def clear_old_errors(self, days: int = 7):
        """ลบข้อผิดพลาดเก่าออก"""
        cutoff_time = datetime.now() - timedelta(days=days)
        with self.lock:
            self.error_history = [
                err for err in self.error_history 
                if err.timestamp > cutoff_time
            ]

# === ERROR HANDLING DECORATORS ===

def handle_trading_errors(category: ErrorCategory = ErrorCategory.TRADING,
                         severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """
    Decorator สำหรับจัดการข้อผิดพลาดในการเทรด
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # สร้าง ErrorInfo
                error_info = ErrorInfo(
                    timestamp=datetime.now(),
                    error_type=type(e).__name__,
                    message=str(e),
                    severity=severity,
                    category=category,
                    traceback_str=traceback.format_exc(),
                    function_name=func.__name__,
                    line_number=0,  # จะได้จาก traceback
                    context_data={"function_args": args, "function_kwargs": kwargs}
                )
                
                # TODO: ใช้ global error handler
                # _global_error_handler.handle_error(error_info)
                
                # Re-raise exception สำหรับตอนนี้
                raise
        return wrapper
    return decorator

def handle_connection_errors(max_retries: int = 3, retry_delay: float = 1.0):
    """
    Decorator สำหรับจัดการข้อผิดพลาดการเชื่อมต่อ
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # รอก่อน retry
                        import time
                        time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        # หมดจำนวน retry แล้ว
                        error_info = ErrorInfo(
                            timestamp=datetime.now(),
                            error_type=type(e).__name__,
                            message=str(e),
                            severity=ErrorSeverity.HIGH,
                            category=ErrorCategory.CONNECTION,
                            traceback_str=traceback.format_exc(),
                            function_name=func.__name__,
                            line_number=0,
                            retry_count=max_retries,
                            context_data={"max_retries": max_retries, "retry_delay": retry_delay}
                        )
                        
                        # TODO: ใช้ global error handler
                        raise last_exception
            
            return None
        return wrapper
    return decorator

# === SPECIALIZED ERROR CLASSES ===

class TradingError(Exception):
    """ข้อผิดพลาดเฉพาะการเทรด"""
    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[Dict] = None):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}

class MT5ConnectionError(TradingError):
    """ข้อผิดพลาดการเชื่อมต่อ MT5"""
    pass

class OrderExecutionError(TradingError):
    """ข้อผิดพลาดการส่งออร์เดอร์"""
    pass

class MarketDataError(TradingError):
    """ข้อผิดพลาดข้อมูลตลาด"""
    pass

class RecoveryError(TradingError):
    """ข้อผิดพลาดระบบ Recovery"""
    pass

# === GLOBAL ERROR HANDLER INSTANCE ===
_global_error_handler: Optional[GlobalErrorHandler] = None

def get_global_error_handler() -> GlobalErrorHandler:
    """ดึง Global Error Handler (Singleton)"""
    global _global_error_handler
    if _global_error_handler is None:
        from .professional_logger import setup_error_logger
        logger = setup_error_logger()
        _global_error_handler = GlobalErrorHandler(logger)
    return _global_error_handler

def report_error(exception: Exception, 
                category: ErrorCategory = ErrorCategory.SYSTEM,
                severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                context: Optional[Dict] = None) -> bool:
    """
    รายงานข้อผิดพลาดไปยัง Global Error Handler
    """
    handler = get_global_error_handler()
    
    error_info = ErrorInfo(
        timestamp=datetime.now(),
        error_type=type(exception).__name__,
        message=str(exception),
        severity=severity,
        category=category,
        traceback_str=traceback.format_exc(),
        function_name="unknown",
        line_number=0,
        context_data=context or {}
    )
    
    return handler.handle_error(error_info)