#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROFESSIONAL LOGGING SYSTEM - ระบบ Logging มืออาชีพ
================================================
ระบบ logging แบบครบครันสำหรับระบบเทรดดิ้ง
รองรับการแยกประเภท log และการบันทึกแบบหลายระดับ

เชื่อมต่อไปยัง:
- config/settings.py (การตั้งค่า logging)
- utilities/data_manager.py (การจัดเก็บ log data)
- ใช้ในทุกโมดูลของระบบ
"""

import logging
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from logging.handlers import RotatingFileHandler
import threading
from dataclasses import dataclass

@dataclass
class LoggerConfig:
    """การตั้งค่าสำหรับ Logger แต่ละตัว"""
    name: str
    level: str = "INFO"
    log_to_file: bool = True
    log_to_console: bool = True
    file_max_size: int = 50  # MB
    backup_count: int = 5
    format_string: Optional[str] = None

class TradingLoggerFormatter(logging.Formatter):
    """
    Custom Formatter สำหรับระบบเทรดดิ้ง
    เพิ่มสี และ emoji สำหรับแยกประเภท log
    """
    
    # สีสำหรับแต่ละระดับ
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green  
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    # Emoji สำหรับแต่ละประเภท
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': '📘', 
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '💥',
        'TRADING': '📊',
        'ORDER': '📈',
        'RECOVERY': '🔄',
        'MARKET': '🌍',
        'SYSTEM': '⚙️'
    }
    
    def format(self, record):
        """
        จัดรูปแบบ log message พร้อมสีและ emoji
        """
        # เพิ่ม emoji ตามประเภท
        emoji = self.EMOJIS.get(record.levelname, self.EMOJIS.get('INFO'))
        
        # เพิ่มสี (สำหรับ console เท่านั้น)
        if hasattr(record, 'add_color') and record.add_color:
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            record.levelname = f"{color}{record.levelname}{reset}"
        
        # จัดรูปแบบเวลา
        record.asctime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # สร้าง format string
        if not hasattr(self, '_style'):
            fmt = f"{emoji} %(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s"
        else:
            fmt = self._fmt or f"{emoji} %(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s"
            
        formatter = logging.Formatter(fmt)
        return formatter.format(record)

class TradingLogger:
    """
    ระบบ Logger หลักสำหรับการเทรดดิ้ง
    รองรับการสร้าง logger หลายตัว พร้อมการจัดการไฟล์อัตโนมัติ
    """
    
    _instances: Dict[str, logging.Logger] = {}
    _lock = threading.Lock()
    
    @classmethod
    def get_logger(cls, config: LoggerConfig) -> logging.Logger:
        """
        สร้างหรือดึง Logger ตาม config ที่กำหนด (Singleton pattern)
        """
        with cls._lock:
            if config.name in cls._instances:
                return cls._instances[config.name]
            
            logger = cls._create_logger(config)
            cls._instances[config.name] = logger
            return logger
    
    @classmethod
    def _create_logger(cls, config: LoggerConfig) -> logging.Logger:
        """
        สร้าง Logger ใหม่ตาม configuration
        """
        logger = logging.getLogger(config.name)
        logger.setLevel(getattr(logging, config.level.upper()))
        
        # ป้องกันการเพิ่ม handler ซ้ำ
        if logger.handlers:
            logger.handlers.clear()
        
        # สร้าง formatter
        formatter = TradingLoggerFormatter()
        
        # เพิ่ม Console Handler
        if config.log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            
            # เพิ่มสีสำหรับ console
            console_filter = cls._ColorFilter()
            console_handler.addFilter(console_filter)
            
            logger.addHandler(console_handler)
        
        # เพิ่ม File Handler
        if config.log_to_file:
            file_handler = cls._create_file_handler(config, formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    @classmethod
    def _create_file_handler(cls, config: LoggerConfig, formatter) -> RotatingFileHandler:
        """
        สร้าง File Handler พร้อม rotation
        """
        # สร้างโฟลเดอร์ logs ถ้ายังไม่มี
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # สร้างชื่อไฟล์ตามวันที่
        today = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"{config.name}_{today}.log"
        
        # สร้าง RotatingFileHandler
        file_handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=config.file_max_size * 1024 * 1024,  # Convert MB to bytes
            backupCount=config.backup_count,
            encoding='utf-8'
        )
        
        file_handler.setFormatter(formatter)
        return file_handler
    
    class _ColorFilter(logging.Filter):
        """Filter สำหรับเพิ่มสีใน console"""
        def filter(self, record):
            record.add_color = True
            return True

# === SPECIALIZED LOGGERS ===

def setup_main_logger(name: str = "IntelligentGoldTrading") -> logging.Logger:
    """
    ตั้งค่า Logger หลักของระบบ
    ใช้สำหรับ main.py และโมดูลหลัก
    """
    config = LoggerConfig(
        name=name,
        level="INFO",
        log_to_file=True,
        log_to_console=True
    )
    return TradingLogger.get_logger(config)

def setup_trading_logger(name: str = "Trading") -> logging.Logger:
    """
    ตั้งค่า Logger สำหรับการเทรดดิ้ง
    ใช้สำหรับ entry, recovery, position management
    """
    config = LoggerConfig(
        name=name,
        level="DEBUG",  # ต้องการรายละเอียดมากสำหรับการเทรด
        log_to_file=True,
        log_to_console=True
    )
    return TradingLogger.get_logger(config)

def setup_market_logger(name: str = "Market") -> logging.Logger:
    """
    ตั้งค่า Logger สำหรับการวิเคราะห์ตลาด
    ใช้สำหรับ market intelligence และ analysis
    """
    config = LoggerConfig(
        name=name,
        level="INFO",
        log_to_file=True,
        log_to_console=False  # ไม่แสดงใน console เพื่อลด noise
    )
    return TradingLogger.get_logger(config)

def setup_mt5_logger(name: str = "MT5") -> logging.Logger:
    """
    ตั้งค่า Logger สำหรับ MT5 Integration
    ใช้สำหรับการเชื่อมต่อและส่งออร์เดอร์
    """
    config = LoggerConfig(
        name=name,
        level="DEBUG",
        log_to_file=True,
        log_to_console=True
    )
    return TradingLogger.get_logger(config)

def setup_error_logger(name: str = "Error") -> logging.Logger:
    """
    ตั้งค่า Logger สำหรับ Error และ Exception
    ใช้สำหรับการจัดการข้อผิดพลาด
    """
    config = LoggerConfig(
        name=name,
        level="ERROR",
        log_to_file=True,
        log_to_console=True,
        file_max_size=100,  # ไฟล์ใหญ่ขึ้นสำหรับ error logs
        backup_count=10
    )
    return TradingLogger.get_logger(config)

def setup_performance_logger(name: str = "Performance") -> logging.Logger:
    """
    ตั้งค่า Logger สำหรับ Performance Tracking
    ใช้สำหรับการติดตามประสิทธิภาพ
    """
    config = LoggerConfig(
        name=name,
        level="INFO",
        log_to_file=True,
        log_to_console=False
    )
    return TradingLogger.get_logger(config)

# === UTILITY FUNCTIONS ===

def get_all_loggers() -> Dict[str, logging.Logger]:
    """
    ดึง Logger ทั้งหมดที่ถูกสร้างแล้ว
    """
    return TradingLogger._instances.copy()

def set_global_log_level(level: str) -> None:
    """
    ตั้งค่าระดับ log สำหรับ Logger ทั้งหมด
    """
    numeric_level = getattr(logging, level.upper())
    for logger in TradingLogger._instances.values():
        logger.setLevel(numeric_level)

def close_all_loggers() -> None:
    """
    ปิด Logger ทั้งหมดและปล่อย resources
    """
    for logger in TradingLogger._instances.values():
        for handler in logger.handlers:
            handler.close()
            logger.removeHandler(handler)
    
    TradingLogger._instances.clear()

# === LOGGING DECORATORS ===

def log_function_call(logger: Optional[logging.Logger] = None):
    """
    Decorator สำหรับ log การเรียกใช้ function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            _logger = logger or setup_trading_logger()
            _logger.debug(f"🔧 เรียกใช้ {func.__name__} - args: {args}, kwargs: {kwargs}")
            
            try:
                result = func(*args, **kwargs)
                _logger.debug(f"✅ {func.__name__} สำเร็จ - result: {result}")
                return result
            except Exception as e:
                _logger.error(f"❌ {func.__name__} ผิดพลาด - error: {e}")
                raise
        return wrapper
    return decorator

def log_trading_action(action_type: str):
    """
    Decorator สำหรับ log การทำ trading actions
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = setup_trading_logger()
            logger.info(f"📊 {action_type}: เริ่มต้น {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                logger.info(f"✅ {action_type}: {func.__name__} สำเร็จ")
                return result
            except Exception as e:
                logger.error(f"❌ {action_type}: {func.__name__} ผิดพลาด - {e}")
                raise
        return wrapper
    return decorator