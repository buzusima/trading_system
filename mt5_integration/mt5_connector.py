#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT5 CONNECTION MANAGER - ตัวจัดการการเชื่อมต่อ MetaTrader 5
====================================================
จัดการการเชื่อมต่อกับ MT5 แบบเสถียร พร้อมระบบ auto-reconnect
รองรับการตรวจสอบสถานะและจัดการข้อผิดพลาดการเชื่อมต่อ

เชื่อมต่อไปยัง:
- config/settings.py (การตั้งค่า MT5)
- utilities/professional_logger.py (logging)
- utilities/error_handler.py (จัดการข้อผิดพลาด)
- mt5_integration/connection_manager.py (จัดการเสถียรภาพการเชื่อมต่อ)
- mt5_integration/account_monitor.py (ติดตามบัญชี)
"""

import MetaTrader5 as mt5
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
from enum import Enum

from config.settings import get_system_settings
from utilities.professional_logger import setup_mt5_logger
from utilities.error_handler import handle_connection_errors, MT5ConnectionError, report_error, ErrorCategory, ErrorSeverity

class ConnectionStatus(Enum):
    """สถานะการเชื่อมต่อ MT5"""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"

@dataclass
class MT5AccountInfo:
    """ข้อมูลบัญชี MT5"""
    login: int
    name: str
    server: str
    currency: str
    balance: float
    equity: float
    margin: float
    margin_free: float
    margin_level: float
    profit: float
    company: str
    trade_allowed: bool
    trade_expert: bool
    leverage: int
    limit_orders: int
    margin_so_mode: int
    margin_so_call: float
    margin_so_so: float

@dataclass
class ConnectionMetrics:
    """เมตริกการเชื่อมต่อ"""
    connect_time: datetime
    last_ping: Optional[datetime] = None
    ping_count: int = 0
    reconnect_count: int = 0
    error_count: int = 0
    uptime_seconds: float = 0.0
    avg_response_time_ms: float = 0.0

class MT5Connector:
    """
    ตัวจัดการการเชื่อมต่อ MT5 หลัก
    รองรับการเชื่อมต่อแบบเสถียรและ auto-reconnect
    """
    
    def __init__(self):
        self.logger = setup_mt5_logger()
        self.settings = get_system_settings()
        
        # สถานะการเชื่อมต่อ
        self.status = ConnectionStatus.DISCONNECTED
        self.account_info: Optional[MT5AccountInfo] = None
        self.metrics = ConnectionMetrics(connect_time=datetime.now())
        
        # Threading
        self.connection_lock = threading.Lock()
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        
        # การตั้งค่าการเชื่อมต่อ
        self.connection_timeout = self.settings.connection_timeout
        self.reconnect_attempts = self.settings.reconnect_attempts
        self.reconnect_delay = 5.0  # วินาที
        
        # ตัวแปรสำหรับติดตาม
        self.last_error: Optional[str] = None
        self.connection_callbacks: List[callable] = []
        
        self.logger.info("🔧 เริ่มต้น MT5 Connector")
    
    @handle_connection_errors(max_retries=3, retry_delay=2.0)
    def connect(self, login: Optional[int] = None, 
                password: Optional[str] = None, 
                server: Optional[str] = None,
                path: Optional[str] = None) -> bool:
        """
        เชื่อมต่อกับ MT5
        """
        with self.connection_lock:
            try:
                self.status = ConnectionStatus.CONNECTING
                self.logger.info("🔌 กำลังเชื่อมต่อ MT5...")
                
                # ใช้ค่าจาก settings ถ้าไม่ได้ระบุ
                login = login or self.settings.mt5_login
                password = password or self.settings.mt5_password
                server = server or self.settings.mt5_server
                path = path or self.settings.mt5_path
                
                # ตรวจสอบข้อมูลที่จำเป็น
                if not all([login, password, server]):
                    raise MT5ConnectionError("ข้อมูลการเชื่อมต่อ MT5 ไม่ครบถ้วน")
                
                # เริ่มต้น MT5
                if path:
                    if not mt5.initialize(path=path):
                        raise MT5ConnectionError(f"ไม่สามารถเริ่มต้น MT5 ได้: {mt5.last_error()}")
                else:
                    if not mt5.initialize():
                        raise MT5ConnectionError(f"ไม่สามารถเริ่มต้น MT5 ได้: {mt5.last_error()}")
                
                # เชื่อมต่อบัญชี
                if not mt5.login(login, password=password, server=server):
                    error_code, error_desc = mt5.last_error()
                    raise MT5ConnectionError(f"ไม่สามารถล็อกอินได้: {error_desc} (Code: {error_code})")
                
                # ดึงข้อมูลบัญชี
                account_info = mt5.account_info()
                if account_info is None:
                    raise MT5ConnectionError("ไม่สามารถดึงข้อมูลบัญชีได้")
                
                # บันทึกข้อมูลบัญชี
                self.account_info = MT5AccountInfo(
                    login=account_info.login,
                    name=account_info.name,
                    server=account_info.server,
                    currency=account_info.currency,
                    balance=account_info.balance,
                    equity=account_info.equity,
                    margin=account_info.margin,
                    margin_free=account_info.margin_free,
                    margin_level=account_info.margin_level,
                    profit=account_info.profit,
                    company=account_info.company,
                    trade_allowed=account_info.trade_allowed,
                    trade_expert=account_info.trade_expert,
                    leverage=account_info.leverage,
                    limit_orders=account_info.limit_orders,
                    margin_so_mode=account_info.margin_so_mode,
                    margin_so_call=account_info.margin_so_call,
                    margin_so_so=account_info.margin_so_so
                )
                
                # อัพเดทสถานะ
                self.status = ConnectionStatus.CONNECTED
                self.metrics.connect_time = datetime.now()
                self.metrics.reconnect_count = 0
                
                # เริ่ม monitoring thread
                self._start_connection_monitor()
                
                # แจ้งเตือน callbacks
                self._notify_connection_callbacks(True)
                
                self.logger.info(f"✅ เชื่อมต่อ MT5 สำเร็จ - Account: {self.account_info.login} "
                               f"Server: {self.account_info.server} Balance: {self.account_info.balance:.2f} "
                               f"{self.account_info.currency}")
                
                return True
                
            except Exception as e:
                self.status = ConnectionStatus.ERROR
                self.last_error = str(e)
                self.logger.error(f"❌ เชื่อมต่อ MT5 ไม่สำเร็จ: {e}")
                
                # รายงานข้อผิดพลาด
                report_error(e, ErrorCategory.CONNECTION, ErrorSeverity.HIGH)
                
                return False
    
    def disconnect(self) -> bool:
        """
        ตัดการเชื่อมต่อ MT5
        """
        with self.connection_lock:
            try:
                self.logger.info("🔌 กำลังตัดการเชื่อมต่อ MT5...")
                
                # หยุด monitoring
                self._stop_connection_monitor()
                
                # ตัดการเชื่อมต่อ
                mt5.shutdown()
                
                # รีเซ็ตสถานะ
                self.status = ConnectionStatus.DISCONNECTED
                self.account_info = None
                
                # แจ้งเตือน callbacks
                self._notify_connection_callbacks(False)
                
                self.logger.info("✅ ตัดการเชื่อมต่อ MT5 สำเร็จ")
                return True
                
            except Exception as e:
                self.logger.error(f"❌ ตัดการเชื่อมต่อ MT5 ไม่สำเร็จ: {e}")
                return False
    
    def is_connected(self) -> bool:
        """ตรวจสอบสถานะการเชื่อมต่อ"""
        return self.status == ConnectionStatus.CONNECTED and mt5.terminal_info() is not None
    
    def ping(self) -> Tuple[bool, float]:
        """
        ทดสอบการเชื่อมต่อและวัดเวลาตอบสนอง
        Returns: (success, response_time_ms)
        """
        start_time = time.time()
        
        try:
            # ทดสอบด้วยการดึงข้อมูล terminal
            terminal_info = mt5.terminal_info()
            
            if terminal_info is not None:
                response_time = (time.time() - start_time) * 1000  # convert to ms
                
                # อัพเดทเมตริก
                self.metrics.last_ping = datetime.now()
                self.metrics.ping_count += 1
                
                # คำนวณ average response time
                if self.metrics.ping_count == 1:
                    self.metrics.avg_response_time_ms = response_time
                else:
                    self.metrics.avg_response_time_ms = (
                        (self.metrics.avg_response_time_ms * (self.metrics.ping_count - 1) + response_time) 
                        / self.metrics.ping_count
                    )
                
                return True, response_time
            else:
                return False, 0.0
                
        except Exception as e:
            self.logger.warning(f"⚠️ Ping MT5 ไม่สำเร็จ: {e}")
            return False, 0.0
    
    def reconnect(self) -> bool:
        """
        เชื่อมต่อใหม่อัตโนมัติ
        """
        self.logger.info("🔄 กำลัง Reconnect MT5...")
        self.status = ConnectionStatus.RECONNECTING
        
        for attempt in range(self.reconnect_attempts):
            self.logger.info(f"🔄 ความพยายามที่ {attempt + 1}/{self.reconnect_attempts}")
            
            # รอก่อน reconnect
            if attempt > 0:
                time.sleep(self.reconnect_delay * attempt)  # Exponential backoff
            
            # ตัดการเชื่อมต่อเก่า
            try:
                mt5.shutdown()
            except:
                pass
            
            # ลองเชื่อมต่อใหม่
            if self.connect():
                self.metrics.reconnect_count += 1
                self.logger.info(f"✅ Reconnect สำเร็จในความพยายามที่ {attempt + 1}")
                return True
        
        self.logger.error(f"❌ Reconnect ไม่สำเร็จหลังจากพยายาม {self.reconnect_attempts} ครั้ง")
        self.status = ConnectionStatus.ERROR
        return False
    
    def get_account_info(self, refresh: bool = False) -> Optional[MT5AccountInfo]:
        """
        ดึงข้อมูลบัญชี
        """
        if not self.is_connected():
            return None
        
        if refresh or self.account_info is None:
            try:
                account_info = mt5.account_info()
                if account_info:
                    self.account_info = MT5AccountInfo(
                        login=account_info.login,
                        name=account_info.name,
                        server=account_info.server,
                        currency=account_info.currency,
                        balance=account_info.balance,
                        equity=account_info.equity,
                        margin=account_info.margin,
                        margin_free=account_info.margin_free,
                        margin_level=account_info.margin_level,
                        profit=account_info.profit,
                        company=account_info.company,
                        trade_allowed=account_info.trade_allowed,
                        trade_expert=account_info.trade_expert,
                        leverage=account_info.leverage,
                        limit_orders=account_info.limit_orders,
                        margin_so_mode=account_info.margin_so_mode,
                        margin_so_call=account_info.margin_so_call,
                        margin_so_so=account_info.margin_so_so
                    )
            except Exception as e:
                self.logger.error(f"❌ ไม่สามารถดึงข้อมูลบัญชีได้: {e}")
                return None
        
        return self.account_info
    
    def get_connection_metrics(self) -> ConnectionMetrics:
        """ดึงเมตริกการเชื่อมต่อ"""
        if self.status == ConnectionStatus.CONNECTED:
            self.metrics.uptime_seconds = (datetime.now() - self.metrics.connect_time).total_seconds()
        
        return self.metrics
    
    def get_terminal_info(self) -> Optional[Dict]:
        """ดึงข้อมูล Terminal MT5"""
        if not self.is_connected():
            return None
        
        try:
            terminal_info = mt5.terminal_info()
            if terminal_info:
                return {
                    "name": terminal_info.name,
                    "path": terminal_info.path,
                    "data_path": terminal_info.data_path,
                    "commondata_path": terminal_info.commondata_path,
                    "language": terminal_info.language,
                    "company": terminal_info.company,
                    "build": terminal_info.build,
                    "connected": terminal_info.connected,
                    "dlls_allowed": terminal_info.dlls_allowed,
                    "trade_allowed": terminal_info.trade_allowed,
                    "tradeapi_disabled": terminal_info.tradeapi_disabled,
                    "email_enabled": terminal_info.email_enabled,
                    "ftp_enabled": terminal_info.ftp_enabled,
                    "notifications_enabled": terminal_info.notifications_enabled,
                    "mqid": terminal_info.mqid,
                    "retransmission": terminal_info.retransmission,
                    "ping_last": terminal_info.ping_last,
                    "community_account": terminal_info.community_account,
                    "community_connection": terminal_info.community_connection
                }
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถดึงข้อมูล Terminal ได้: {e}")
            return None
    
    def add_connection_callback(self, callback: callable):
        """เพิ่ม callback สำหรับการแจ้งเตือนสถานะการเชื่อมต่อ"""
        self.connection_callbacks.append(callback)
    
    def _notify_connection_callbacks(self, connected: bool):
        """แจ้งเตือน callbacks เมื่อสถานะการเชื่อมต่อเปลี่ยน"""
        for callback in self.connection_callbacks:
            try:
                callback(connected, self.account_info)
            except Exception as e:
                self.logger.error(f"❌ Error in connection callback: {e}")
    
    def _start_connection_monitor(self):
        """เริ่ม thread สำหรับติดตามการเชื่อมต่อ"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._connection_monitor_loop,
            daemon=True,
            name="MT5ConnectionMonitor"
        )
        self.monitor_thread.start()
        self.logger.info("🔍 เริ่มต้น Connection Monitor")
    
    def _stop_connection_monitor(self):
        """หยุด connection monitor"""
        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("🛑 หยุด Connection Monitor")
    
    def _connection_monitor_loop(self):
        """ลูปติดตามการเชื่อมต่อ"""
        while self.monitoring_active:
            try:
                # ตรวจสอบการเชื่อมต่อทุก 30 วินาที
                time.sleep(30)
                
                if not self.monitoring_active:
                    break
                
                # Ping เพื่อตรวจสอบการเชื่อมต่อ
                is_connected, response_time = self.ping()
                
                if not is_connected and self.status == ConnectionStatus.CONNECTED:
                    self.logger.warning("⚠️ ตรวจพบการเชื่อมต่อขาดหาย - เริ่ม Auto Reconnect")
                    self.status = ConnectionStatus.ERROR
                    
                    # ลอง reconnect
                    if self.reconnect():
                        self.logger.info("✅ Auto Reconnect สำเร็จ")
                    else:
                        self.logger.error("❌ Auto Reconnect ไม่สำเร็จ")
                        self.metrics.error_count += 1
                
                elif is_connected and response_time > 5000:  # 5 วินาที
                    self.logger.warning(f"⚠️ การเชื่อมต่อช้า: {response_time:.2f} ms")
                
            except Exception as e:
                self.logger.error(f"❌ Error in connection monitor: {e}")
                self.metrics.error_count += 1

# === GLOBAL MT5 CONNECTOR INSTANCE ===
_global_mt5_connector: Optional[MT5Connector] = None

def get_mt5_connector() -> MT5Connector:
    """ดึง MT5 Connector แบบ Singleton"""
    global _global_mt5_connector
    if _global_mt5_connector is None:
        _global_mt5_connector = MT5Connector()
    return _global_mt5_connector

def ensure_mt5_connection() -> bool:
    """ตรวจสอบและรับประกันการเชื่อมต่อ MT5"""
    connector = get_mt5_connector()
    
    if connector.is_connected():
        return True
    
    # ลองเชื่อมต่อใหม่
    return connector.connect()

def get_account_balance() -> Optional[float]:
    """ดึงยอดเงินในบัญชี"""
    connector = get_mt5_connector()
    account_info = connector.get_account_info(refresh=True)
    
    return account_info.balance if account_info else None

def get_account_equity() -> Optional[float]:
    """ดึง Equity ในบัญชี"""
    connector = get_mt5_connector()
    account_info = connector.get_account_info(refresh=True)
    
    return account_info.equity if account_info else None

def get_margin_level() -> Optional[float]:
    """ดึงระดับ Margin"""
    connector = get_mt5_connector()
    account_info = connector.get_account_info(refresh=True)
    
    return account_info.margin_level if account_info else None

def is_trading_allowed() -> bool:
    """ตรวจสอบว่าสามารถเทรดได้หรือไม่"""
    connector = get_mt5_connector()
    
    if not connector.is_connected():
        return False
    
    account_info = connector.get_account_info()
    if not account_info:
        return False
    
    return account_info.trade_allowed and account_info.trade_expert