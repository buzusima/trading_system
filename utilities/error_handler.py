#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERROR HANDLER - ระบบจัดการข้อผิดพลาด (UPDATED)
=============================================
แก้ไข ErrorCategory ให้ครบถ้วน
"""

import sys
import traceback
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
import logging

# ===== ERROR CATEGORIES - เพิ่มครบถ้วน =====

class ErrorCategory(Enum):
    """ประเภทข้อผิดพลาด - ครบถ้วน"""
    SYSTEM = "SYSTEM"
    TRADING_LOGIC = "TRADING_LOGIC"  # ✅ เพิ่มตัวนี้
    MARKET_DATA = "MARKET_DATA"
    MT5_CONNECTION = "MT5_CONNECTION"
    RECOVERY = "RECOVERY"
    POSITION_MANAGEMENT = "POSITION_MANAGEMENT"
    SIGNAL_GENERATION = "SIGNAL_GENERATION"
    ORDER_EXECUTION = "ORDER_EXECUTION"
    PERFORMANCE_TRACKING = "PERFORMANCE_TRACKING"
    GUI = "GUI"
    CONFIGURATION = "CONFIGURATION"
    NETWORK = "NETWORK"
    DATABASE = "DATABASE"

class ErrorSeverity(Enum):
    """ระดับความร้ายแรง"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class ErrorInfo:
    """ข้อมูลข้อผิดพลาด"""
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    function_name: str
    file_name: str
    line_number: int
    traceback_info: str
    context: Dict[str, Any] = field(default_factory=dict)

class GlobalErrorHandler:
    """ตัวจัดการข้อผิดพลาดหลัก"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("ErrorHandler")
        self.error_history: List[ErrorInfo] = []
        self.error_lock = threading.Lock()
        
        # Error counters
        self.error_counts = {category: 0 for category in ErrorCategory}
        
    def setup_global_exception_handling(self):
        """ตั้งค่าการจัดการ exception แบบ global"""
        sys.excepthook = self._global_exception_handler
        
    def _global_exception_handler(self, exc_type, exc_value, exc_traceback):
        """จัดการ exception แบบ global"""
        error_msg = f"Uncaught exception: {exc_type.__name__}: {exc_value}"
        self.handle_error(
            ErrorCategory.SYSTEM,
            ErrorSeverity.CRITICAL,
            error_msg,
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
    def handle_error(self, category: ErrorCategory, severity: ErrorSeverity, 
                    message: str, exc_info=None):
        """จัดการข้อผิดพลาด"""
        try:
            # สร้าง ErrorInfo
            if exc_info:
                tb_info = ''.join(traceback.format_exception(*exc_info))
                frame = exc_info[2].tb_frame if exc_info[2] else None
                func_name = frame.f_code.co_name if frame else "unknown"
                file_name = frame.f_code.co_filename if frame else "unknown"
                line_no = frame.f_lineno if frame else 0
            else:
                tb_info = ''.join(traceback.format_stack())
                frame = sys._getframe(1)
                func_name = frame.f_code.co_name
                file_name = frame.f_code.co_filename
                line_no = frame.f_lineno
            
            error_info = ErrorInfo(
                timestamp=datetime.now(),
                category=category,
                severity=severity,
                message=message,
                function_name=func_name,
                file_name=file_name,
                line_number=line_no,
                traceback_info=tb_info
            )
            
            # บันทึก error
            with self.error_lock:
                self.error_history.append(error_info)
                self.error_counts[category] += 1
            
            # Log ข้อผิดพลาด
            log_msg = f"[{category.value}][{severity.value}] {message}"
            
            if severity == ErrorSeverity.CRITICAL:
                self.logger.critical(log_msg)
            elif severity == ErrorSeverity.HIGH:
                self.logger.error(log_msg)
            elif severity == ErrorSeverity.MEDIUM:
                self.logger.warning(log_msg)
            else:
                self.logger.info(log_msg)
                
        except Exception as e:
            # Error ในการจัดการ error
            print(f"Error in error handler: {e}")

# ===== DECORATOR FUNCTION =====

def handle_trading_errors(category: ErrorCategory, severity: ErrorSeverity):
    """Decorator สำหรับจัดการ trading errors"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # ใช้ global error handler ถ้ามี
                error_handler = getattr(wrapper, '_error_handler', None)
                if error_handler:
                    error_handler.handle_error(
                        category, 
                        severity, 
                        f"Error in {func.__name__}: {e}",
                        exc_info=sys.exc_info()
                    )
                else:
                    # Fallback logging
                    print(f"[{category.value}][{severity.value}] Error in {func.__name__}: {e}")
                
                # Re-raise critical errors
                if severity == ErrorSeverity.CRITICAL:
                    raise
                
                return None
        
        # เก็บ reference ไปยัง original function
        wrapper.__wrapped__ = func
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        
        return wrapper
    return decorator

# ===== GLOBAL INSTANCE =====

_global_error_handler = None

def get_global_error_handler() -> GlobalErrorHandler:
    """ดึง Global Error Handler"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = GlobalErrorHandler()
    return _global_error_handler

def setup_error_handling(logger=None):
    """ตั้งค่า Error Handling"""
    global _global_error_handler
    _global_error_handler = GlobalErrorHandler(logger)
    _global_error_handler.setup_global_exception_handling()
    return _global_error_handler

# ===== TESTING =====

if __name__ == "__main__":
    print("🧪 ทดสอบ Error Handler")
    
    # สร้าง error handler
    handler = setup_error_handling()
    
    # ทดสอบ decorator
    @handle_trading_errors(ErrorCategory.TRADING_LOGIC, ErrorSeverity.MEDIUM)
    def test_function():
        raise ValueError("Test error")
    
    print("✅ Error Handler พร้อมใช้งาน")
    print("📊 Error Categories:")
    for category in ErrorCategory:
        print(f"   - {category.value}")