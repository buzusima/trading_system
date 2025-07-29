#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERROR HANDLER - ระบบจัดการ Error ขั้นสูง (COMPLETE)
==================================================
ระบบจัดการ Error แบบครอบคลุมสำหรับ Intelligent Gold Trading System
รองรับ error tracking, reporting, และ recovery mechanisms

🎯 ฟีเจอร์หลัก:
- Multi-level error categorization
- Automatic error recovery strategies
- Error statistics และ trending
- Real-time error monitoring
- Custom error handlers
- Exception chaining และ context
- Performance impact analysis
"""

import sys
import traceback
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import json
import inspect
import functools

class ErrorCategory(Enum):
    """หมวดหมู่ของ Error"""
    SYSTEM = "SYSTEM"                    # ระบบโดยรวม
    TRADING = "TRADING"                  # การเทรดและ execution
    MT5_CONNECTION = "MT5_CONNECTION"    # การเชื่อมต่อ MT5
    DATA_PROCESSING = "DATA_PROCESSING"  # การประมวลผลข้อมูล
    GUI = "GUI"                         # User interface
    CONFIGURATION = "CONFIGURATION"     # การตั้งค่า
    RECOVERY = "RECOVERY"               # ระบบ recovery
    NETWORK = "NETWORK"                 # เครือข่าย
    ALGORITHM = "ALGORITHM"             # อัลกอริทึม trading
    MARKET_DATA = "MARKET_DATA"         # ข้อมูลตลาด

class ErrorSeverity(Enum):
    """ระดับความรุนแรงของ Error"""
    LOW = "LOW"             # ไม่กระทบการทำงาน
    MEDIUM = "MEDIUM"       # กระทบบางส่วน
    HIGH = "HIGH"           # กระทบอย่างมาก
    CRITICAL = "CRITICAL"   # หยุดการทำงาน
    FATAL = "FATAL"         # ต้องปิดระบบ

class ErrorStatus(Enum):
    """สถานะการจัดการ Error"""
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"
    RECURRING = "RECURRING"

@dataclass
class ErrorInfo:
    """ข้อมูล Error แบบละเอียด"""
    error_id: str
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    status: ErrorStatus = ErrorStatus.NEW
    
    # Error details
    message: str = ""
    exception_type: str = ""
    exception_message: str = ""
    traceback_info: str = ""
    
    # Context information
    function_name: str = ""
    module_name: str = ""
    line_number: int = 0
    thread_name: str = ""
    
    # Additional data
    context_data: Dict[str, Any] = field(default_factory=dict)
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_method: str = ""
    
    # Statistics
    occurrence_count: int = 1
    first_occurrence: datetime = field(default_factory=datetime.now)
    last_occurrence: datetime = field(default_factory=datetime.now)
    
    # Resolution
    resolution_notes: str = ""
    resolved_by: str = ""
    resolved_at: Optional[datetime] = None

class ErrorRecoveryStrategy:
    """Error Recovery Strategy Base Class"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.success_count = 0
        self.failure_count = 0
        self.last_used = None
    
    def can_handle(self, error_info: ErrorInfo) -> bool:
        """ตรวจสอบว่าสามารถจัดการ error นี้ได้หรือไม่"""
        return False
    
    def attempt_recovery(self, error_info: ErrorInfo, context: Dict[str, Any] = None) -> bool:
        """พยายาม recover จาก error"""
        try:
            self.last_used = datetime.now()
            success = self._execute_recovery(error_info, context or {})
            
            if success:
                self.success_count += 1
            else:
                self.failure_count += 1
            
            return success
            
        except Exception as e:
            self.failure_count += 1
            return False
    
    def _execute_recovery(self, error_info: ErrorInfo, context: Dict[str, Any]) -> bool:
        """Override this method in subclasses"""
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """ดึงสถิติการ recovery"""
        total_attempts = self.success_count + self.failure_count
        success_rate = (self.success_count / total_attempts * 100) if total_attempts > 0 else 0
        
        return {
            'name': self.name,
            'description': self.description,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'total_attempts': total_attempts,
            'success_rate': success_rate,
            'last_used': self.last_used.isoformat() if self.last_used else None
        }

class RestartComponentStrategy(ErrorRecoveryStrategy):
    """Strategy สำหรับรีสตาร์ท component"""
    
    def __init__(self):
        super().__init__("RestartComponent", "Restart failed component")
    
    def can_handle(self, error_info: ErrorInfo) -> bool:
        return error_info.category in [ErrorCategory.SYSTEM, ErrorCategory.TRADING]
    
    def _execute_recovery(self, error_info: ErrorInfo, context: Dict[str, Any]) -> bool:
        # จำลองการรีสตาร์ท component
        time.sleep(1)  # Simulate restart time
        return True

class ReconnectStrategy(ErrorRecoveryStrategy):
    """Strategy สำหรับเชื่อมต่อใหม่"""
    
    def __init__(self):
        super().__init__("Reconnect", "Attempt to reconnect")
    
    def can_handle(self, error_info: ErrorInfo) -> bool:
        return error_info.category in [ErrorCategory.MT5_CONNECTION, ErrorCategory.NETWORK]
    
    def _execute_recovery(self, error_info: ErrorInfo, context: Dict[str, Any]) -> bool:
        # จำลองการเชื่อมต่อใหม่
        time.sleep(2)  # Simulate reconnection time
        return True

class RetryOperationStrategy(ErrorRecoveryStrategy):
    """Strategy สำหรับลองใหม่"""
    
    def __init__(self):
        super().__init__("RetryOperation", "Retry failed operation")
        self.max_retries = 3
    
    def can_handle(self, error_info: ErrorInfo) -> bool:
        return error_info.occurrence_count <= self.max_retries
    
    def _execute_recovery(self, error_info: ErrorInfo, context: Dict[str, Any]) -> bool:
        # จำลองการลองใหม่
        time.sleep(0.5)
        return error_info.occurrence_count <= 2  # สำเร็จใน 2 ครั้งแรก

class GlobalErrorHandler:
    """Global Error Handler หลัก"""
    
    def __init__(self, logger=None):
        self.logger = logger
        self.setup_complete = False
        
        # Error storage
        self.errors: Dict[str, ErrorInfo] = {}
        self.error_history: deque = deque(maxlen=1000)
        
        # Statistics
        self.error_stats = defaultdict(int)
        self.category_stats = defaultdict(int)
        self.severity_stats = defaultdict(int)
        
        # Recovery strategies
        self.recovery_strategies: List[ErrorRecoveryStrategy] = []
        self._setup_default_strategies()
        
        # Custom handlers
        self.custom_handlers: Dict[ErrorCategory, List[Callable]] = defaultdict(list)
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Performance tracking
        self.performance_impact = {
            'total_errors': 0,
            'critical_errors': 0,
            'recovery_time_total': 0.0,
            'system_downtime': 0.0
        }
        
        # Error patterns
        self.error_patterns = defaultdict(list)
        
        # Notifications
        self.notification_callbacks: List[Callable] = []
    
    def _setup_default_strategies(self):
        """ตั้งค่า recovery strategies เริ่มต้น"""
        self.recovery_strategies = [
            RestartComponentStrategy(),
            ReconnectStrategy(),
            RetryOperationStrategy()
        ]
    
    def setup_global_exception_handling(self):
        """ตั้งค่า Global Exception Handling"""
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                # ปล่อยให้ KeyboardInterrupt ผ่านไปตามปกติ
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            # สร้าง ErrorInfo
            error_info = self._create_error_info(
                ErrorCategory.SYSTEM,
                ErrorSeverity.CRITICAL,
                f"Uncaught exception: {exc_type.__name__}: {exc_value}",
                exc_type=exc_type,
                exc_value=exc_value,
                exc_traceback=exc_traceback
            )
            
            # จัดการ error
            self.handle_error(error_info)
        
        sys.excepthook = handle_exception
        self.setup_complete = True
        
        if self.logger:
            self.logger.info("✅ Global Exception Handling ตั้งค่าเรียบร้อย")
    
    def _create_error_info(self, category: ErrorCategory, severity: ErrorSeverity, 
                          message: str, exc_type=None, exc_value=None, exc_traceback=None,
                          context_data: Dict[str, Any] = None) -> ErrorInfo:
        """สร้าง ErrorInfo object"""
        
        error_id = f"ERR_{int(time.time())}_{hash(message) % 10000}"
        
        # Extract traceback info
        traceback_info = ""
        function_name = ""
        module_name = ""
        line_number = 0
        
        if exc_traceback:
            traceback_info = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            tb_frame = exc_traceback.tb_frame
            function_name = tb_frame.f_code.co_name
            module_name = tb_frame.f_code.co_filename
            line_number = exc_traceback.tb_lineno
        else:
            # Get current frame info
            frame = inspect.currentframe()
            if frame and frame.f_back:
                caller_frame = frame.f_back.f_back  # Skip this function and handle_error
                if caller_frame:
                    function_name = caller_frame.f_code.co_name
                    module_name = caller_frame.f_code.co_filename
                    line_number = caller_frame.f_lineno
        
        return ErrorInfo(
            error_id=error_id,
            timestamp=datetime.now(),
            category=category,
            severity=severity,
            message=message,
            exception_type=exc_type.__name__ if exc_type else "",
            exception_message=str(exc_value) if exc_value else "",
            traceback_info=traceback_info,
            function_name=function_name,
            module_name=module_name,
            line_number=line_number,
            thread_name=threading.current_thread().name,
            context_data=context_data or {}
        )
    
    def handle_error(self, error_info: ErrorInfo = None, category: ErrorCategory = None, 
                    severity: ErrorSeverity = None, message: str = "", 
                    exc_info: Optional[tuple] = None, context_data: Dict[str, Any] = None):
        """จัดการ Error หลัก"""
        
        with self.lock:
            # Create ErrorInfo if not provided
            if error_info is None:
                if exc_info:
                    error_info = self._create_error_info(
                        category, severity, message,
                        exc_info[0], exc_info[1], exc_info[2],
                        context_data
                    )
                else:
                    error_info = self._create_error_info(
                        category, severity, message,
                        context_data=context_data
                    )
            
            # Check for duplicate errors
            duplicate_key = f"{error_info.category.value}_{error_info.message}"
            if duplicate_key in self.error_patterns:
                # Update existing error
                existing_error_id = self.error_patterns[duplicate_key][-1]
                if existing_error_id in self.errors:
                    existing_error = self.errors[existing_error_id]
                    existing_error.occurrence_count += 1
                    existing_error.last_occurrence = datetime.now()
                    existing_error.status = ErrorStatus.RECURRING
                    error_info = existing_error
            else:
                # New error
                self.errors[error_info.error_id] = error_info
                self.error_patterns[duplicate_key].append(error_info.error_id)
            
            # Update statistics
            self._update_statistics(error_info)
            
            # Add to history
            self.error_history.append(error_info.error_id)
            
            # Log the error
            self._log_error(error_info)
            
            # Attempt recovery
            self._attempt_recovery(error_info)
            
            # Call custom handlers
            self._call_custom_handlers(error_info)
            
            # Send notifications
            self._send_notifications(error_info)
            
            return error_info.error_id
    
    def _update_statistics(self, error_info: ErrorInfo):
        """อัพเดทสถิติ"""
        self.error_stats[error_info.error_id] += 1
        self.category_stats[error_info.category.value] += 1
        self.severity_stats[error_info.severity.value] += 1
        
        self.performance_impact['total_errors'] += 1
        if error_info.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            self.performance_impact['critical_errors'] += 1
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error"""
        if not self.logger:
            return
        
        log_message = f"[{error_info.category.value}] {error_info.message}"
        
        if error_info.severity == ErrorSeverity.FATAL:
            self.logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Log traceback for critical errors
        if error_info.traceback_info and error_info.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            self.logger.error(f"Traceback:\n{error_info.traceback_info}")
    
    def _attempt_recovery(self, error_info: ErrorInfo):
        """พยายาม recover จาก error"""
        if error_info.recovery_attempted:
            return
        
        recovery_start_time = time.time()
        
        for strategy in self.recovery_strategies:
            if strategy.can_handle(error_info):
                try:
                    if self.logger:
                        self.logger.info(f"🔄 พยายาม recovery ด้วย: {strategy.name}")
                    
                    success = strategy.attempt_recovery(error_info)
                    
                    error_info.recovery_attempted = True
                    error_info.recovery_successful = success
                    error_info.recovery_method = strategy.name
                    
                    if success:
                        error_info.status = ErrorStatus.RESOLVED
                        if self.logger:
                            self.logger.info(f"✅ Recovery สำเร็จด้วย: {strategy.name}")
                        break
                    else:
                        if self.logger:
                            self.logger.warning(f"❌ Recovery ล้มเหลวด้วย: {strategy.name}")
                
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"💥 ข้อผิดพลาดใน recovery strategy {strategy.name}: {e}")
        
        # Track recovery time
        recovery_time = time.time() - recovery_start_time
        self.performance_impact['recovery_time_total'] += recovery_time
    
    def _call_custom_handlers(self, error_info: ErrorInfo):
        """เรียก custom handlers"""
        handlers = self.custom_handlers.get(error_info.category, [])
        
        for handler in handlers:
            try:
                handler(error_info)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"❌ ข้อผิดพลาดใน custom handler: {e}")
    
    def _send_notifications(self, error_info: ErrorInfo):
        """ส่ง notifications"""
        for callback in self.notification_callbacks:
            try:
                callback(error_info)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"❌ ข้อผิดพลาดใน notification callback: {e}")
    
    def register_custom_handler(self, category: ErrorCategory, handler: Callable):
        """ลงทะเบียน custom handler"""
        self.custom_handlers[category].append(handler)
        if self.logger:
            self.logger.info(f"➕ ลงทะเบียน custom handler สำหรับ {category.value}")
    
    def register_recovery_strategy(self, strategy: ErrorRecoveryStrategy):
        """ลงทะเบียน recovery strategy"""
        self.recovery_strategies.append(strategy)
        if self.logger:
            self.logger.info(f"➕ ลงทะเบียน recovery strategy: {strategy.name}")
    
    def register_notification_callback(self, callback: Callable):
        """ลงทะเบียน notification callback"""
        self.notification_callbacks.append(callback)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """ดึงสถิติ error"""
        with self.lock:
            total_errors = sum(self.error_stats.values())
            
            # Category breakdown
            category_breakdown = {}
            for category, count in self.category_stats.items():
                percentage = (count / total_errors * 100) if total_errors > 0 else 0
                category_breakdown[category] = {
                    'count': count,
                    'percentage': round(percentage, 2)
                }
            
            # Severity breakdown
            severity_breakdown = {}
            for severity, count in self.severity_stats.items():
                percentage = (count / total_errors * 100) if total_errors > 0 else 0
                severity_breakdown[severity] = {
                    'count': count,
                    'percentage': round(percentage, 2)
                }
            
            # Recent errors (last hour)
            recent_threshold = datetime.now() - timedelta(hours=1)
            recent_errors = [
                error_id for error_id in self.error_history
                if error_id in self.errors and self.errors[error_id].timestamp > recent_threshold
            ]
            
            return {
                'total_errors': total_errors,
                'unique_errors': len(self.errors),
                'recent_errors_1h': len(recent_errors),
                'category_breakdown': category_breakdown,
                'severity_breakdown': severity_breakdown,
                'performance_impact': self.performance_impact,
                'recovery_strategies_count': len(self.recovery_strategies),
                'custom_handlers_count': sum(len(handlers) for handlers in self.custom_handlers.values())
            }
    
    def get_recent_errors(self, count: int = 10, category: ErrorCategory = None, 
                         severity: ErrorSeverity = None) -> List[ErrorInfo]:
        """ดึง error ล่าสุด"""
        with self.lock:
            recent_error_ids = list(self.error_history)[-count:]
            recent_errors = []
            
            for error_id in reversed(recent_error_ids):  # ล่าสุดก่อน
                if error_id in self.errors:
                    error = self.errors[error_id]
                    
                    # Filter by category
                    if category and error.category != category:
                        continue
                    
                    # Filter by severity
                    if severity and error.severity != severity:
                        continue
                    
                    recent_errors.append(error)
            
            return recent_errors
    
    def get_error_by_id(self, error_id: str) -> Optional[ErrorInfo]:
        """ดึง error ตาม ID"""
        return self.errors.get(error_id)
    
    def resolve_error(self, error_id: str, resolution_notes: str = "", resolved_by: str = ""):
        """ทำเครื่องหมาย error ว่าแก้ไขแล้ว"""
        if error_id in self.errors:
            error = self.errors[error_id]
            error.status = ErrorStatus.RESOLVED
            error.resolution_notes = resolution_notes
            error.resolved_by = resolved_by
            error.resolved_at = datetime.now()
            
            if self.logger:
                self.logger.info(f"✅ แก้ไข error {error_id}: {resolution_notes}")
    
    def ignore_error(self, error_id: str):
        """ทำเครื่องหมาย error ว่าละเว้น"""
        if error_id in self.errors:
            self.errors[error_id].status = ErrorStatus.IGNORED
            
            if self.logger:
                self.logger.info(f"🙈 ละเว้น error {error_id}")
    
    def get_recovery_strategy_statistics(self) -> List[Dict[str, Any]]:
        """ดึงสถิติ recovery strategies"""
        return [strategy.get_statistics() for strategy in self.recovery_strategies]
    
    def export_error_report(self, filename: Optional[str] = None, 
                           include_resolved: bool = True) -> str:
        """ส่งออกรายงาน error"""
        try:
            if filename is None:
                filename = f"error_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Filter errors
            errors_to_export = []
            for error in self.errors.values():
                if not include_resolved and error.status == ErrorStatus.RESOLVED:
                    continue
                
                # Convert ErrorInfo to dict
                error_dict = {
                    'error_id': error.error_id,
                    'timestamp': error.timestamp.isoformat(),
                    'category': error.category.value,
                    'severity': error.severity.value,
                    'status': error.status.value,
                    'message': error.message,
                    'exception_type': error.exception_type,
                    'exception_message': error.exception_message,
                    'function_name': error.function_name,
                    'module_name': error.module_name,
                    'line_number': error.line_number,
                    'thread_name': error.thread_name,
                    'context_data': error.context_data,
                    'occurrence_count': error.occurrence_count,
                    'first_occurrence': error.first_occurrence.isoformat(),
                    'last_occurrence': error.last_occurrence.isoformat(),
                    'recovery_attempted': error.recovery_attempted,
                    'recovery_successful': error.recovery_successful,
                    'recovery_method': error.recovery_method,
                    'resolution_notes': error.resolution_notes,
                    'resolved_by': error.resolved_by,
                    'resolved_at': error.resolved_at.isoformat() if error.resolved_at else None
                }
                errors_to_export.append(error_dict)
            
            # Create report
            report = {
                'report_info': {
                    'generated_at': datetime.now().isoformat(),
                    'total_errors': len(errors_to_export),
                    'include_resolved': include_resolved
                },
                'statistics': self.get_error_statistics(),
                'recovery_strategies': self.get_recovery_strategy_statistics(),
                'errors': errors_to_export
            }
            
            # Write to file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            if self.logger:
                self.logger.info(f"📁 ส่งออกรายงาน error: {filename}")
            
            return filename
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ ไม่สามารถส่งออกรายงาน error: {e}")
            return ""
    
    def cleanup_old_errors(self, max_age_days: int = 30):
        """ลบ error เก่า"""
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            
            with self.lock:
                errors_to_remove = []
                for error_id, error in self.errors.items():
                    if (error.status == ErrorStatus.RESOLVED and 
                        error.resolved_at and 
                        error.resolved_at < cutoff_date):
                        errors_to_remove.append(error_id)
                
                for error_id in errors_to_remove:
                    del self.errors[error_id]
                
                if errors_to_remove and self.logger:
                    self.logger.info(f"🧹 ลบ error เก่า: {len(errors_to_remove)} รายการ")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ ไม่สามารถลบ error เก่า: {e}")

# ===============================
# DECORATORS
# ===============================

def handle_trading_errors(category: ErrorCategory = ErrorCategory.TRADING, 
                         severity: ErrorSeverity = ErrorSeverity.HIGH):
    """Decorator สำหรับจัดการ Trading Errors"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get global error handler
                error_handler = get_global_error_handler()
                error_handler.handle_error(
                    category=category,
                    severity=severity,
                    message=f"Error in {func.__name__}: {str(e)}",
                    exc_info=sys.exc_info(),
                    context_data={
                        'function': func.__name__,
                        'args': str(args)[:200],  # Limit length
                        'kwargs': str(kwargs)[:200]
                    }
                )
                raise
        return wrapper
    return decorator

def safe_execute(default_return=None, log_errors=True):
    """Decorator สำหรับ safe execution"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    error_handler = get_global_error_handler()
                    error_handler.handle_error(
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.MEDIUM,
                        message=f"Safe execution failed in {func.__name__}: {str(e)}",
                        exc_info=sys.exc_info()
                    )
                return default_return
        return wrapper
    return decorator

# ===============================
# GLOBAL INSTANCE
# ===============================

_global_error_handler: Optional[GlobalErrorHandler] = None

def get_global_error_handler() -> GlobalErrorHandler:
    """ดึง Global Error Handler"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = GlobalErrorHandler()
    return _global_error_handler

def setup_global_error_handler(logger=None) -> GlobalErrorHandler:
    """ตั้งค่า Global Error Handler"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = GlobalErrorHandler(logger)
        _global_error_handler.setup_global_exception_handling()
    return _global_error_handler

# ===============================
# TEST FUNCTIONS
# ===============================

def test_error_handler():
    """ทดสอบ Error Handler"""
    print("🧪 ทดสอบ Error Handler...")
    
    # Setup
    error_handler = setup_global_error_handler()
    
    # Test different error types
    error_handler.handle_error(
        category=ErrorCategory.TRADING,
        severity=ErrorSeverity.HIGH,
        message="Test trading error"
    )
    
    error_handler.handle_error(
        category=ErrorCategory.MT5_CONNECTION,
        severity=ErrorSeverity.CRITICAL,
        message="Test connection error"
    )
    
    # Test exception handling
    try:
        raise ValueError("Test exception")
    except Exception:
        error_handler.handle_error(
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            message="Test exception handling",
            exc_info=sys.exc_info()
        )
    
    # Get statistics
    stats = error_handler.get_error_statistics()
    print(f"📊 Error Statistics: {stats}")
    
    # Get recent errors
    recent = error_handler.get_recent_errors(5)
    print(f"📋 Recent Errors: {len(recent)}")
    
    # Export report
    report_file = error_handler.export_error_report()
    print(f"📁 Exported report: {report_file}")
   
    print("✅ ทดสอบ Error Handler เสร็จสิ้น")

if __name__ == "__main__":
   test_error_handler()