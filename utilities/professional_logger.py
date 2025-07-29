#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROFESSIONAL LOGGER - ระบบ Logging แบบมืออาชีพ (COMPLETE)
==========================================================
ระบบ logging ขั้นสูงสำหรับ Intelligent Gold Trading System
รองรับ multi-level logging, file rotation, และ real-time monitoring

🎯 ฟีเจอร์หลัก:
- Multi-level logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Automatic file rotation และ backup
- Real-time console output
- Thread-safe operations
- Custom formatters สำหรับแต่ละ output
- Performance monitoring
- Error tracking และ statistics
"""

import logging
import logging.handlers
import sys
import os
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
import json
import time

class LogLevel:
    """Log Level Constants"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

class ColoredFormatter(logging.Formatter):
    """Colored console formatter"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)

class PerformanceFilter(logging.Filter):
    """Filter for performance monitoring"""
    
    def __init__(self):
        super().__init__()
        self.start_time = time.time()
        self.message_count = defaultdict(int)
        self.error_count = 0
    
    def filter(self, record):
        # Count messages by level
        self.message_count[record.levelname] += 1
        
        # Count errors
        if record.levelno >= logging.ERROR:
            self.error_count += 1
        
        # Add performance info to record
        record.uptime = time.time() - self.start_time
        record.msg_count = sum(self.message_count.values())
        record.error_count = self.error_count
        
        return True

class ProfessionalLogger:
    """
    Professional Logger Class
    ระบบ logging ขั้นสูงสำหรับการเทรด
    """
    
    def __init__(self, name: str = "TradingSystem", 
                 log_level: int = logging.INFO,
                 log_file: Optional[str] = None,
                 max_file_size: int = 10*1024*1024,  # 10MB
                 backup_count: int = 5,
                 enable_console: bool = True,
                 enable_performance: bool = True):
        
        self.name = name
        self.log_level = log_level
        self.log_file = log_file
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.enable_console = enable_console
        self.enable_performance = enable_performance
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        
        # Clear existing handlers
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Statistics
        self.stats = {
            'messages_logged': 0,
            'errors_logged': 0,
            'warnings_logged': 0,
            'start_time': datetime.now(),
            'last_message_time': None
        }
        
        # Message buffer for GUI
        self.message_buffer = deque(maxlen=1000)
        
        # Thread lock for thread safety
        self.lock = threading.Lock()
        
        # Setup formatters
        self._setup_formatters()
        
        # Setup handlers
        self._setup_handlers()
        
        # Performance filter
        if self.enable_performance:
            self.performance_filter = PerformanceFilter()
            self.logger.addFilter(self.performance_filter)
        
        self.logger.info(f"🚀 เริ่มต้น Professional Logger: {name}")
    
    def _setup_formatters(self):
        """Setup different formatters"""
        
        # Console formatter (สั้นและกระชับ)
        self.console_formatter = ColoredFormatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # File formatter (ละเอียดสำหรับ debugging)
        self.file_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Performance formatter
        self.performance_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | [Uptime:%(uptime).1fs|Msgs:%(msg_count)d|Errs:%(error_count)d] | %(message)s',
            datefmt='%H:%M:%S'
        )
    
    def _setup_handlers(self):
        """Setup logging handlers"""
        
        # Console Handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            
            if self.enable_performance:
                console_handler.setFormatter(self.performance_formatter)
            else:
                console_handler.setFormatter(self.console_formatter)
            
            self.logger.addHandler(console_handler)
        
        # File Handler
        if self.log_file:
            self._setup_file_handler()
        
        # Error File Handler (แยกไฟล์สำหรับ errors)
        if self.log_file:
            self._setup_error_file_handler()
    
    def _setup_file_handler(self):
        """Setup rotating file handler"""
        try:
            # Create log directory
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Rotating file handler
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            
            file_handler.setLevel(logging.DEBUG)  # File gets all messages
            file_handler.setFormatter(self.file_formatter)
            
            self.logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"⚠️ ไม่สามารถสร้าง file handler: {e}")
    
    def _setup_error_file_handler(self):
        """Setup separate error file handler"""
        try:
            # Error file path
            log_path = Path(self.log_file)
            error_file = log_path.parent / f"{log_path.stem}_errors{log_path.suffix}"
            
            from logging.handlers import RotatingFileHandler
            error_handler = RotatingFileHandler(
                str(error_file),
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            
            error_handler.setLevel(logging.ERROR)  # Only errors and critical
            error_handler.setFormatter(self.file_formatter)
            
            self.logger.addHandler(error_handler)
            
        except Exception as e:
            print(f"⚠️ ไม่สามารถสร้าง error file handler: {e}")
    
    def _update_stats(self, level: int):
        """Update logging statistics"""
        with self.lock:
            self.stats['messages_logged'] += 1
            self.stats['last_message_time'] = datetime.now()
            
            if level >= logging.ERROR:
                self.stats['errors_logged'] += 1
            elif level >= logging.WARNING:
                self.stats['warnings_logged'] += 1
    
    def _add_to_buffer(self, message: str, level: str):
        """Add message to buffer for GUI"""
        with self.lock:
            self.message_buffer.append({
                'timestamp': datetime.now(),
                'message': message,
                'level': level,
                'logger': self.name
            })
    
    def debug(self, message: str, extra: Dict[str, Any] = None):
        """Log debug message"""
        self._update_stats(logging.DEBUG)
        self._add_to_buffer(message, 'DEBUG')
        self.logger.debug(message, extra=extra or {})
    
    def info(self, message: str, extra: Dict[str, Any] = None):
        """Log info message"""
        self._update_stats(logging.INFO)
        self._add_to_buffer(message, 'INFO')
        self.logger.info(message, extra=extra or {})
    
    def warning(self, message: str, extra: Dict[str, Any] = None):
        """Log warning message"""
        self._update_stats(logging.WARNING)
        self._add_to_buffer(message, 'WARNING')
        self.logger.warning(message, extra=extra or {})
    
    def error(self, message: str, extra: Dict[str, Any] = None):
        """Log error message"""
        self._update_stats(logging.ERROR)
        self._add_to_buffer(message, 'ERROR')
        self.logger.error(message, extra=extra or {})
    
    def critical(self, message: str, extra: Dict[str, Any] = None):
        """Log critical message"""
        self._update_stats(logging.CRITICAL)
        self._add_to_buffer(message, 'CRITICAL')
        self.logger.critical(message, extra=extra or {})
    
    def exception(self, message: str, extra: Dict[str, Any] = None):
        """Log exception with traceback"""
        self._update_stats(logging.ERROR)
        self._add_to_buffer(f"EXCEPTION: {message}", 'ERROR')
        self.logger.exception(message, extra=extra or {})
    
    def trading_event(self, event_type: str, message: str, data: Dict[str, Any] = None):
        """Log trading-specific events"""
        trading_data = {
            'event_type': event_type,
            'trading_data': data or {},
            'timestamp': datetime.now().isoformat()
        }
        
        formatted_message = f"[TRADING:{event_type}] {message}"
        if data:
            formatted_message += f" | Data: {data}"
        
        self.info(formatted_message, extra=trading_data)
    
    def performance_log(self, operation: str, duration: float, success: bool = True, extra_data: Dict[str, Any] = None):
        """Log performance metrics"""
        perf_data = {
            'operation': operation,
            'duration_ms': round(duration * 1000, 2),
            'success': success,
            'performance_data': extra_data or {}
        }
        
        status = "SUCCESS" if success else "FAILED"
        message = f"[PERFORMANCE] {operation}: {perf_data['duration_ms']}ms ({status})"
        
        if success:
            self.info(message, extra=perf_data)
        else:
            self.warning(message, extra=perf_data)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get logging statistics"""
        with self.lock:
            uptime = datetime.now() - self.stats['start_time']
            
            return {
                'logger_name': self.name,
                'uptime_seconds': uptime.total_seconds(),
                'messages_logged': self.stats['messages_logged'],
                'errors_logged': self.stats['errors_logged'],
                'warnings_logged': self.stats['warnings_logged'],
                'last_message_time': self.stats['last_message_time'].isoformat() if self.stats['last_message_time'] else None,
                'buffer_size': len(self.message_buffer),
                'log_level': logging.getLevelName(self.log_level),
                'handlers_count': len(self.logger.handlers),
                'log_file': self.log_file
            }
    
    def get_recent_messages(self, count: int = 50, level_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent messages from buffer"""
        with self.lock:
            messages = list(self.message_buffer)
            
            # Filter by level if specified
            if level_filter:
                messages = [msg for msg in messages if msg['level'] == level_filter.upper()]
            
            # Return most recent
            return messages[-count:] if count < len(messages) else messages
    
    def clear_buffer(self):
        """Clear message buffer"""
        with self.lock:
            self.message_buffer.clear()
    
    def set_level(self, level: int):
        """Change log level"""
        self.log_level = level
        self.logger.setLevel(level)
        self.info(f"📊 เปลี่ยน log level เป็น: {logging.getLevelName(level)}")
    
    def add_custom_handler(self, handler: logging.Handler):
        """Add custom handler"""
        self.logger.addHandler(handler)
        self.info(f"➕ เพิ่ม custom handler: {type(handler).__name__}")
    
    def export_logs(self, filename: Optional[str] = None, include_stats: bool = True) -> str:
        """Export logs to file"""
        try:
            if filename is None:
                filename = f"exported_logs_{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            export_data = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'logger_name': self.name,
                    'export_filename': filename
                },
                'messages': self.get_recent_messages(1000),  # Export up to 1000 messages
            }
            
            if include_stats:
                export_data['statistics'] = self.get_statistics()
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.info(f"📁 ส่งออก logs เสร็จสิ้น: {filename}")
            return filename
            
        except Exception as e:
            self.error(f"❌ ไม่สามารถส่งออก logs: {e}")
            return ""
    
    def cleanup_old_logs(self, max_age_days: int = 30):
        """Clean up old log files"""
        try:
            if not self.log_file:
                return
            
            log_dir = Path(self.log_file).parent
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            
            cleaned_files = 0
            for log_file in log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    cleaned_files += 1
            
            if cleaned_files > 0:
                self.info(f"🧹 ลบไฟล์ log เก่า: {cleaned_files} ไฟล์")
                
        except Exception as e:
            self.error(f"❌ ไม่สามารถลบไฟล์ log เก่า: {e}")
    
    def __del__(self):
        """Cleanup when logger is destroyed"""
        try:
            # Close all handlers
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
        except:
            pass

# ===============================
# GLOBAL LOGGER MANAGEMENT
# ===============================

_loggers: Dict[str, ProfessionalLogger] = {}
_default_config = {
    'log_level': logging.INFO,
    'enable_console': True,
    'enable_performance': True,
    'max_file_size': 10*1024*1024,
    'backup_count': 5
}

def setup_main_logger(name: str = "IntelligentGoldTrading", **kwargs) -> ProfessionalLogger:
    """Setup main system logger"""
    if name not in _loggers:
        config = {**_default_config, **kwargs}
        log_file = f"logs/{name.lower()}.log"
        
        _loggers[name] = ProfessionalLogger(
            name=name,
            log_file=log_file,
            **config
        )
    
    return _loggers[name]

def setup_component_logger(component_name: str, **kwargs) -> ProfessionalLogger:
    """Setup logger for specific component"""
    if component_name not in _loggers:
        config = {**_default_config, **kwargs}
        log_file = f"logs/{component_name.lower()}.log"
        
        _loggers[component_name] = ProfessionalLogger(
            name=component_name,
            log_file=log_file,
            **config
        )
    
    return _loggers[component_name]

def setup_trading_logger(**kwargs) -> ProfessionalLogger:
    """Setup specialized trading logger"""
    return setup_component_logger("TradingEngine", **kwargs)

def get_all_loggers() -> Dict[str, ProfessionalLogger]:
    """Get all active loggers"""
    return _loggers.copy()

def get_logger_statistics() -> Dict[str, Dict[str, Any]]:
    """Get statistics from all loggers"""
    stats = {}
    for name, logger in _loggers.items():
        stats[name] = logger.get_statistics()
    return stats

def cleanup_all_loggers():
    """Cleanup all loggers"""
    for logger in _loggers.values():
        logger.cleanup_old_logs()

def export_all_logs(base_filename: Optional[str] = None) -> List[str]:
    """Export logs from all loggers"""
    exported_files = []
    
    for name, logger in _loggers.items():
        if base_filename:
            filename = f"{base_filename}_{name}.json"
        else:
            filename = None
        
        exported_file = logger.export_logs(filename)
        if exported_file:
            exported_files.append(exported_file)
    
    return exported_files

# ===============================
# SPECIALIZED LOGGERS
# ===============================

class TradingEventLogger(ProfessionalLogger):
    """Specialized logger for trading events"""
    
    def __init__(self, **kwargs):
        super().__init__(name="TradingEvents", **kwargs)
        
        # Trading-specific message types
        self.event_types = {
            'SIGNAL': 'Signal Generated',
            'ORDER': 'Order Executed',
            'POSITION': 'Position Update',
            'RECOVERY': 'Recovery Operation',
            'PROFIT': 'Profit/Loss Event'
        }
    
    def signal_generated(self, signal_data: Dict[str, Any]):
        """Log signal generation"""
        self.trading_event('SIGNAL', 
                          f"Signal: {signal_data.get('type', 'UNKNOWN')} | "
                          f"Confidence: {signal_data.get('confidence', 0):.2f}",
                          signal_data)
    
    def order_executed(self, order_data: Dict[str, Any]):
        """Log order execution"""
        self.trading_event('ORDER',
                          f"Order: {order_data.get('type', 'UNKNOWN')} | "
                          f"Volume: {order_data.get('volume', 0)} | "
                          f"Price: {order_data.get('price', 0)}",
                          order_data)
    
    def position_update(self, position_data: Dict[str, Any]):
        """Log position updates"""
        self.trading_event('POSITION',
                          f"Position {position_data.get('ticket', 'UNKNOWN')}: "
                          f"P&L: {position_data.get('profit', 0):.2f}",
                          position_data)
    
    def recovery_operation(self, recovery_data: Dict[str, Any]):
        """Log recovery operations"""
        self.trading_event('RECOVERY',
                          f"Recovery: {recovery_data.get('method', 'UNKNOWN')} | "
                          f"Level: {recovery_data.get('level', 0)}",
                          recovery_data)

def setup_trading_event_logger(**kwargs) -> TradingEventLogger:
    """Setup trading event logger"""
    if "TradingEvents" not in _loggers:
        config = {**_default_config, **kwargs}
        log_file = "logs/trading_events.log"
        
        _loggers["TradingEvents"] = TradingEventLogger(
            log_file=log_file,
            **config
        )
    
    return _loggers["TradingEvents"]

# ===============================
# TEST FUNCTIONS
# ===============================

def test_professional_logger():
    """Test professional logger functionality"""
    print("🧪 ทดสอบ Professional Logger...")
    
    # Create logger
    logger = setup_main_logger("TestLogger")
    
    # Test different log levels
    logger.debug("🔧 Debug message")
    logger.info("ℹ️ Info message")
    logger.warning("⚠️ Warning message")
    logger.error("❌ Error message")
    logger.critical("🚨 Critical message")
    
    # Test trading event
    logger.trading_event("TEST", "Test trading event", {"test_data": 123})
    
    # Test performance log
    logger.performance_log("test_operation", 0.05, True, {"extra": "data"})
    
    # Get statistics
    stats = logger.get_statistics()
    print(f"📊 Statistics: {stats}")
    
    # Get recent messages
    messages = logger.get_recent_messages(5)
    print(f"📨 Recent messages: {len(messages)}")
    
    # Export logs
    exported_file = logger.export_logs()
    print(f"📁 Exported: {exported_file}")
    
    print("✅ ทดสอบ Professional Logger เสร็จสิ้น")

def benchmark_logger_performance():
    """Benchmark logger performance"""
    print("⚡ ทดสอบประสิทธิภาพ Logger...")
    
    logger = setup_main_logger("BenchmarkLogger", enable_console=False)
    
    # Benchmark logging speed
    import time
    
    start_time = time.time()
    for i in range(1000):
        logger.info(f"Test message {i}")
    
    duration = time.time() - start_time
    messages_per_second = 1000 / duration
    
    print(f"📊 ผลลัพธ์:")
    print(f"   ข้อความ: 1000")
    print(f"   เวลา: {duration:.2f} วินาที")
    print(f"   ความเร็ว: {messages_per_second:.0f} messages/second")
    
    # Memory usage
    import sys
    buffer_size = sys.getsizeof(logger.message_buffer)
    print(f"   Buffer memory: {buffer_size} bytes")

if __name__ == "__main__":
    test_professional_logger()
    print("\n" + "="*50)
    benchmark_logger_performance()