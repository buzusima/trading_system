#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT5 CONNECTOR - เชื่อมต่อ MetaTrader 5 (COMPLETE)
==============================================
ระบบเชื่อมต่อ MetaTrader 5 แบบครอบคลุมสำหรับ Intelligent Gold Trading System
รองรับ connection management, error handling, และ failover mechanisms

🎯 ฟีเจอร์หลัก:
- Auto-detection ของ MT5 installation
- Connection pooling และ management
- Automatic reconnection strategies
- Symbol และ account validation
- Market hours checking
- Error handling และ recovery
- Performance monitoring
- Thread-safe operations
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import random
# Safe MT5 import
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None
    print("⚠️ MetaTrader5 module ไม่พร้อมใช้งาน - จะใช้โหมดจำลอง")

class ConnectionStatus(Enum):
    """สถานะการเชื่อมต่อ"""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"
    MAINTENANCE = "MAINTENANCE"

class MarketStatus(Enum):
    """สถานะตลาด"""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    PRE_MARKET = "PRE_MARKET"
    POST_MARKET = "POST_MARKET"
    UNKNOWN = "UNKNOWN"

@dataclass
class MT5Config:
    """การตั้งค่า MT5"""
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None
    path: Optional[str] = None
    timeout: int = 10000
    portable: bool = False
    
    # Auto-detection settings
    auto_detect: bool = True
    verify_trade_allowed: bool = True
    verify_symbols: List[str] = field(default_factory=lambda: ["XAUUSD"])
    
    # Connection settings
    max_reconnect_attempts: int = 5
    reconnect_delay: float = 5.0
    connection_timeout: float = 30.0
    
    # Performance settings
    enable_logging: bool = True
    log_trades: bool = True
    cache_symbols: bool = True

@dataclass
class AccountInfo:
    """ข้อมูลบัญชี"""
    login: int = 0
    trade_mode: str = ""
    name: str = ""
    server: str = ""
    currency: str = ""
    company: str = ""
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    margin_level: float = 0.0
    credit: float = 0.0
    profit: float = 0.0
    trade_allowed: bool = False
    expert_allowed: bool = False
    margin_call: float = 0.0
    margin_so_call: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class SymbolInfo:
    """ข้อมูล Symbol"""
    name: str = ""
    description: str = ""
    currency_base: str = ""
    currency_profit: str = ""
    currency_margin: str = ""
    digits: int = 0
    point: float = 0.0
    multiply: int = 0
    minimum: float = 0.0
    maximum: float = 0.0
    step: float = 0.0
    trade_mode: int = 0
    trade_execution: int = 0
    spread: float = 0.0
    volume_min: float = 0.0
    volume_max: float = 0.0
    volume_step: float = 0.0
    market_open: bool = False
    last_update: datetime = field(default_factory=datetime.now)

class MT5MockConnector:
    """Mock MT5 Connector สำหรับการทดสอบ"""
    
    def __init__(self):
        self.connected = False
        self.account_info = AccountInfo(
            login=12345678,
            trade_mode="DEMO",
            name="Demo Account",
            server="Demo-Server",
            currency="USD",
            company="Mock Broker",
            balance=10000.0,
            equity=10000.0,
            trade_allowed=True,
            expert_allowed=True
        )
        
        self.symbols = {
            "XAUUSD": SymbolInfo(
                name="XAUUSD",
                description="Gold vs US Dollar",
                currency_base="XAU",
                currency_profit="USD",
                digits=2,
                point=0.01,
                spread=0.3,
                volume_min=0.01,
                volume_max=100.0,
                volume_step=0.01,
                market_open=True
            )
        }
    
    def initialize(self, path=None, login=None, password=None, server=None, timeout=10000, portable=False):
        self.connected = True
        return True
    
    def shutdown(self):
        self.connected = False
    
    def account_info(self):
        return self.account_info if self.connected else None
    
    def symbol_info(self, symbol):
        return self.symbols.get(symbol) if self.connected else None
    
    def symbol_info_tick(self, symbol):
        if not self.connected or symbol not in self.symbols:
            return None
        
        # จำลอง tick data
        import random
        base_price = 2000.0
        spread = 0.3
        
        class MockTick:
            def __init__(self):
                self.time = int(time.time())
                self.bid = base_price + random.uniform(-10, 10)
                self.ask = self.bid + spread
                self.last = self.bid
                self.volume = random.randint(1, 100)
        
        return MockTick()
    
    def positions_get(self, symbol=None):
        return [] if self.connected else None
    
    def orders_get(self, symbol=None):
        return [] if self.connected else None
    
    def order_send(self, request):
        if not self.connected:
            return None
        
        # จำลองการส่ง order
        class MockResult:
            def __init__(self):
                self.retcode = 10009  # TRADE_RETCODE_DONE
                self.deal = random.randint(100000, 999999)
                self.order = random.randint(100000, 999999)
                self.volume = request.get('volume', 0.01)
                self.price = request.get('price', 2000.0)
                self.comment = request.get('comment', '')
        
        return MockResult()

class MT5Connector:
    """MT5 Connector หลัก"""
    
    def __init__(self, config: MT5Config = None, logger=None):
        self.config = config or MT5Config()
        self.logger = logger
        
        # Connection state
        self.status = ConnectionStatus.DISCONNECTED
        self.connection_start_time = None
        self.last_connection_attempt = None
        self.reconnect_attempts = 0
        
        # Account and symbol info
        self.account_info: Optional[AccountInfo] = None
        self.symbols_info: Dict[str, SymbolInfo] = {}
        
        # Statistics
        self.connection_stats = {
            'total_connections': 0,
            'successful_connections': 0,
            'connection_failures': 0,
            'total_uptime': 0.0,
            'reconnections': 0,
            'last_error': None
        }
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Monitoring thread
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # Use mock if MT5 not available
        if not MT5_AVAILABLE:
            self.mt5 = MT5MockConnector()
            self.is_mock = True
            if self.logger:
                self.logger.warning("⚠️ ใช้ Mock MT5 Connector")
        else:
            self.mt5 = mt5
            self.is_mock = False
        
        if self.logger:
            self.logger.info("🔌 เริ่มต้น MT5 Connector")
    
    def connect(self, auto_retry: bool = True) -> bool:
        """เชื่อมต่อ MT5"""
        with self.lock:
            if self.status == ConnectionStatus.CONNECTED:
                return True
            
            self.status = ConnectionStatus.CONNECTING
            self.last_connection_attempt = datetime.now()
            
            try:
                if self.logger:
                    self.logger.info("🔌 กำลังเชื่อมต่อ MT5...")
                
                # Initialize MT5
                success = self._initialize_mt5()
                
                if success:
                    # Verify connection
                    if self._verify_connection():
                        self.status = ConnectionStatus.CONNECTED
                        self.connection_start_time = datetime.now()
                        self.reconnect_attempts = 0
                        
                        # Update statistics
                        self.connection_stats['total_connections'] += 1
                        self.connection_stats['successful_connections'] += 1
                        
                        # Load account and symbol info
                        self._load_account_info()
                        self._load_symbols_info()
                        
                        # Start monitoring
                        self._start_monitoring()
                        
                        if self.logger:
                            self.logger.info("✅ เชื่อมต่อ MT5 สำเร็จ")
                        
                        return True
                    else:
                        self.status = ConnectionStatus.ERROR
                        self.connection_stats['connection_failures'] += 1
                        
                        if self.logger:
                            self.logger.error("❌ การตรวจสอบการเชื่อมต่อล้มเหลว")
                
                else:
                    self.status = ConnectionStatus.ERROR
                    self.connection_stats['connection_failures'] += 1
                    
                    if self.logger:
                        self.logger.error("❌ ไม่สามารถเชื่อมต่อ MT5")
                
                # Auto retry if enabled
                if auto_retry and self.reconnect_attempts < self.config.max_reconnect_attempts:
                    self.reconnect_attempts += 1
                    if self.logger:
                        self.logger.info(f"🔄 พยายามเชื่อมต่อใหม่ครั้งที่ {self.reconnect_attempts}")
                    
                    time.sleep(self.config.reconnect_delay)
                    return self.connect(auto_retry)
                
                return False
                
            except Exception as e:
                self.status = ConnectionStatus.ERROR
                self.connection_stats['connection_failures'] += 1
                self.connection_stats['last_error'] = str(e)
                
                if self.logger:
                    self.logger.error(f"💥 ข้อผิดพลาดในการเชื่อมต่อ MT5: {e}")
                
                return False
    
    def _initialize_mt5(self) -> bool:
        """เริ่มต้น MT5"""
        try:
            # Auto-detect or use provided config
            if self.config.auto_detect and not self.is_mock:
                # Try to initialize without parameters first
                if self.mt5.initialize():
                    return True
                
                # If failed, try with detected parameters
                detected_config = self._detect_mt5_installation()
                if detected_config:
                    return self.mt5.initialize(
                        path=detected_config.get('path'),
                        login=detected_config.get('login'),
                        password=detected_config.get('password'),
                        server=detected_config.get('server'),
                        timeout=self.config.timeout,
                        portable=self.config.portable
                    )
            
            # Use provided configuration
            return self.mt5.initialize(
                path=self.config.path,
                login=self.config.login,
                password=self.config.password,
                server=self.config.server,
                timeout=self.config.timeout,
                portable=self.config.portable
            )
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ ข้อผิดพลาดในการเริ่มต้น MT5: {e}")
            return False
    
    def _detect_mt5_installation(self) -> Optional[Dict[str, Any]]:
        """ตรวจจับการติดตั้ง MT5"""
        try:
            # Common MT5 installation paths
            common_paths = [
                r"C:\Program Files\MetaTrader 5\terminal64.exe",
                r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
                r"C:\Users\{}\AppData\Roaming\MetaQuotes\Terminal\*.exe".format(os.getenv('USERNAME', '')),
            ]
            
            for path_pattern in common_paths:
                if '*' in path_pattern:
                    # Search pattern
                    from glob import glob
                    matches = glob(path_pattern)
                    if matches:
                        return {'path': matches[0]}
                else:
                    # Direct path
                    if Path(path_pattern).exists():
                        return {'path': path_pattern}
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ ไม่สามารถตรวจจับ MT5 installation: {e}")
            return None
    
    def _verify_connection(self) -> bool:
        """ตรวจสอบการเชื่อมต่อ"""
        try:
            # Check account info
            account = self.mt5.account_info()
            if account is None:
                return False
            
            # Check if trading is allowed
            if self.config.verify_trade_allowed and not account.trade_allowed:
                if self.logger:
                    self.logger.warning("⚠️ การเทรดไม่ได้รับอนุญาตในบัญชีนี้")
                return False
            
            # Verify symbols
            for symbol in self.config.verify_symbols:
                symbol_info = self.mt5.symbol_info(symbol)
                if symbol_info is None:
                    if self.logger:
                        self.logger.warning(f"⚠️ ไม่พบ symbol: {symbol}")
                    return False
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ ข้อผิดพลาดในการตรวจสอบการเชื่อมต่อ: {e}")
            return False
    
    def _load_account_info(self):
        """โหลดข้อมูลบัญชี"""
        try:
            account = self.mt5.account_info()
            if account:
                self.account_info = AccountInfo(
                    login=account.login,
                    trade_mode=account.trade_mode,
                    name=account.name,
                    server=account.server,
                    currency=account.currency,
                    company=account.company,
                    balance=account.balance,
                    equity=account.equity,
                    margin=account.margin,
                    free_margin=account.free_margin,
                    margin_level=account.margin_level,
                    credit=account.credit,
                    profit=account.profit,
                    trade_allowed=account.trade_allowed,
                    expert_allowed=account.expert_allowed,
                    margin_call=account.margin_call,
                    margin_so_call=account.margin_so_call
                )
                
                if self.logger:
                    self.logger.info(f"📊 โหลดข้อมูลบัญชี: {account.login}")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ ไม่สามารถโหลดข้อมูลบัญชี: {e}")
    
    def _load_symbols_info(self):
        """โหลดข้อมูล symbols"""
        try:
            for symbol_name in self.config.verify_symbols:
                symbol = self.mt5.symbol_info(symbol_name)
                if symbol:
                    self.symbols_info[symbol_name] = SymbolInfo(
                        name=symbol.name,
                        description=symbol.description if hasattr(symbol, 'description') else symbol_name,
                        currency_base=symbol.currency_base if hasattr(symbol, 'currency_base') else "",
                        currency_profit=symbol.currency_profit if hasattr(symbol, 'currency_profit') else "",
                        currency_margin=symbol.currency_margin if hasattr(symbol, 'currency_margin') else "",
                        digits=symbol.digits,
                        point=symbol.point,
                        multiply=symbol.multiply if hasattr(symbol, 'multiply') else 1,
                        minimum=symbol.minimum if hasattr(symbol, 'minimum') else 0.0,
                        maximum=symbol.maximum if hasattr(symbol, 'maximum') else 1000.0,
                        step=symbol.step if hasattr(symbol, 'step') else 0.01,
                        trade_mode=symbol.trade_mode if hasattr(symbol, 'trade_mode') else 0,
                        trade_execution=symbol.trade_execution if hasattr(symbol, 'trade_execution') else 0,
                        spread=symbol.spread if hasattr(symbol, 'spread') else 0.0,
                        volume_min=symbol.volume_min,
                        volume_max=symbol.volume_max,
                        volume_step=symbol.volume_step,
                        market_open=True  # Assume open for mock
                    )
                    
                    if self.logger:
                        self.logger.info(f"📈 โหลดข้อมูล symbol: {symbol_name}")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ ไม่สามารถโหลดข้อมูล symbols: {e}")
    
    def _start_monitoring(self):
        """เริ่มการตรวจสอบการเชื่อมต่อ"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="MT5Monitoring"
        )
        self.monitoring_thread.start()
        
        if self.logger:
            self.logger.info("🔍 เริ่มการตรวจสอบ MT5 connection")
    
    def _monitoring_loop(self):
        """ลูปการตรวจสอบการเชื่อมต่อ"""
        while self.monitoring_active and self.status == ConnectionStatus.CONNECTED:
            try:
                # Check connection health
                if not self._health_check():
                    if self.logger:
                        self.logger.warning("⚠️ MT5 connection health check ล้มเหลว")
                    
                    # Attempt reconnection
                    if self._should_reconnect():
                        self.reconnect()
                
                # Update account info periodically
                if self.account_info:
                    self._update_account_info()
                
                # Sleep for next check
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"❌ ข้อผิดพลาดใน monitoring loop: {e}")
                time.sleep(60)
    
    def _health_check(self) -> bool:
        """ตรวจสอบสุขภาพการเชื่อมต่อ"""
        try:
            # Simple health check - try to get account info
            account = self.mt5.account_info()
            return account is not None
            
        except Exception:
            return False
    
    def _should_reconnect(self) -> bool:
        """ตรวจสอบว่าควร reconnect หรือไม่"""
        return (self.status != ConnectionStatus.CONNECTED and 
                self.reconnect_attempts < self.config.max_reconnect_attempts)
    
    def _update_account_info(self):
        """อัพเดทข้อมูลบัญชี"""
        try:
            account = self.mt5.account_info()
            if account and self.account_info:
                self.account_info.balance = account.balance
                self.account_info.equity = account.equity
                self.account_info.margin = account.margin
                self.account_info.free_margin = account.free_margin
                self.account_info.margin_level = account.margin_level
                self.account_info.profit = account.profit
                self.account_info.last_update = datetime.now()
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ ไม่สามารถอัพเดทข้อมูลบัญชี: {e}")
    
    def disconnect(self):
        """ตัดการเชื่อมต่อ MT5"""
        with self.lock:
            if self.logger:
                self.logger.info("🔌 กำลังตัดการเชื่อมต่อ MT5...")
            
            # Stop monitoring
            self.monitoring_active = False
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5.0)
            
            # Shutdown MT5
            try:
                if hasattr(self.mt5, 'shutdown'):
                    self.mt5.shutdown()
            except Exception as e:
                if self.logger:
                    self.logger.error(f"❌ ข้อผิดพลาดในการปิด MT5: {e}")
            
            # Update status
            self.status = ConnectionStatus.DISCONNECTED
            
            # Update statistics
            if self.connection_start_time:
                uptime = (datetime.now() - self.connection_start_time).total_seconds()
                self.connection_stats['total_uptime'] += uptime
            
            self.connection_start_time = None
            
            if self.logger:
                self.logger.info("✅ ตัดการเชื่อมต่อ MT5 เรียบร้อย")
    
    def reconnect(self) -> bool:
        """เชื่อมต่อใหม่"""
        if self.logger:
            self.logger.info("🔄 กำลังเชื่อมต่อ MT5 ใหม่...")
        
        self.status = ConnectionStatus.RECONNECTING
        self.connection_stats['reconnections'] += 1
        
        # Disconnect first
        try:
            if hasattr(self.mt5, 'shutdown'):
                self.mt5.shutdown()
        except:
            pass
        
        # Wait before reconnecting
        time.sleep(self.config.reconnect_delay)
        
        # Connect again
        return self.connect(auto_retry=False)
    
    def is_connected(self) -> bool:
        """ตรวจสอบสถานะการเชื่อมต่อ"""
        return self.status == ConnectionStatus.CONNECTED
    
    def get_connection_status(self) -> Dict[str, Any]:
        """ดึงสถานะการเชื่อมต่อ"""
        with self.lock:
            uptime = 0
            if self.connection_start_time:
                uptime = (datetime.now() - self.connection_start_time).total_seconds()
            
            return {
                'status': self.status.value,
                'is_connected': self.is_connected(),
                'is_mock': self.is_mock,
                'connection_start_time': self.connection_start_time.isoformat() if self.connection_start_time else None,
                'current_uptime': uptime,
                'reconnect_attempts': self.reconnect_attempts,
                'max_reconnect_attempts': self.config.max_reconnect_attempts,
                'last_connection_attempt': self.last_connection_attempt.isoformat() if self.last_connection_attempt else None,
                'account_info': {
                    'login': self.account_info.login if self.account_info else None,
                    'server': self.account_info.server if self.account_info else None,
                    'balance': self.account_info.balance if self.account_info else 0.0,
                    'equity': self.account_info.equity if self.account_info else 0.0,
                    'trade_allowed': self.account_info.trade_allowed if self.account_info else False
                },
                'statistics': self.connection_stats
            }
    
    def get_account_info(self) -> Optional[AccountInfo]:
        """ดึงข้อมูลบัญชี"""
        return self.account_info
    
    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """ดึงข้อมูล symbol"""
        return self.symbols_info.get(symbol)
    
    def get_tick(self, symbol: str) -> Optional[Any]:
        """ดึงข้อมูล tick ล่าสุด"""
        try:
            if not self.is_connected():
                return None
            
            return self.mt5.symbol_info_tick(symbol)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ ไม่สามารถดึงข้อมูล tick สำหรับ {symbol}: {e}")
            return None
    
    def get_positions(self, symbol: str = None) -> List[Any]:
        """ดึงข้อมูล positions"""
        try:
            if not self.is_connected():
                return []
            
            positions = self.mt5.positions_get(symbol=symbol)
            return list(positions) if positions else []
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ ไม่สามารถดึงข้อมูล positions: {e}")
            return []
    
    def get_orders(self, symbol: str = None) -> List[Any]:
        """ดึงข้อมูล pending orders"""
        try:
            if not self.is_connected():
                return []
            
            orders = self.mt5.orders_get(symbol=symbol)
            return list(orders) if orders else []
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ ไม่สามารถดึงข้อมูล orders: {e}")
            return []
    
    def send_order(self, request: Dict[str, Any]) -> Optional[Any]:
        """ส่ง order"""
        try:
            if not self.is_connected():
                if self.logger:
                    self.logger.error("❌ ไม่ได้เชื่อมต่อ MT5")
                return None
            
            result = self.mt5.order_send(request)
            
            if result and hasattr(result, 'retcode'):
                if result.retcode == 10009:  # TRADE_RETCODE_DONE
                    if self.logger:
                        self.logger.info(f"✅ ส่ง order สำเร็จ: {result.order}")
                else:
                    if self.logger:
                        self.logger.error(f"❌ ส่ง order ล้มเหลว: retcode {result.retcode}")
            
            return result
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ ข้อผิดพลาดในการส่ง order: {e}")
            return None
    
    def check_market_status(self, symbol: str) -> MarketStatus:
        """ตรวจสอบสถานะตลาด"""
        try:
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                return MarketStatus.UNKNOWN
            
            # Simple market hours check (can be enhanced)
            now = datetime.now()
            hour = now.hour
            
            # Forex markets are generally open 24/5
            if symbol.startswith('XAU'):  # Gold
                if 0 <= hour <= 23:  # Almost 24/7 for gold
                    return MarketStatus.OPEN
                else:
                    return MarketStatus.CLOSED
            
            # Default
            return MarketStatus.OPEN if symbol_info.market_open else MarketStatus.CLOSED
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ ไม่สามารถตรวจสอบสถานะตลาดสำหรับ {symbol}: {e}")
            return MarketStatus.UNKNOWN
    
    def __del__(self):
        """Cleanup เมื่อ object ถูกลบ"""
        try:
            if self.is_connected():
                self.disconnect()
        except:
            pass

# ===============================
# GLOBAL FUNCTIONS
# ===============================

_global_mt5_connector: Optional[MT5Connector] = None

def ensure_mt5_connection(config: MT5Config = None, logger=None) -> bool:
    """ตรวจสอบและสร้างการเชื่อมต่อ MT5"""
    global _global_mt5_connector
    
    if _global_mt5_connector is None:
        _global_mt5_connector = MT5Connector(config, logger)
    
    if not _global_mt5_connector.is_connected():
        return _global_mt5_connector.connect()
    return True

def get_mt5_connector() -> Optional[MT5Connector]:
    """ดึง MT5 Connector instance"""
    return _global_mt5_connector

def disconnect_mt5():
    """ตัดการเชื่อมต่อ MT5"""
    global _global_mt5_connector
    if _global_mt5_connector:
        _global_mt5_connector.disconnect()
        _global_mt5_connector = None

# ===============================
# UTILITY FUNCTIONS
# ===============================

def validate_symbol(symbol: str, connector: MT5Connector = None) -> bool:
    """ตรวจสอบความถูกต้องของ symbol"""
    try:
        if connector is None:
            connector = get_mt5_connector()
        
        if not connector or not connector.is_connected():
            return False
        
        symbol_info = connector.get_symbol_info(symbol)
        return symbol_info is not None
        
    except Exception:
        return False

def get_symbol_point_value(symbol: str, connector: MT5Connector = None) -> float:
    """ดึงค่า point ของ symbol"""
    try:
        if connector is None:
            connector = get_mt5_connector()
        
        if not connector or not connector.is_connected():
            return 0.01  # Default for XAUUSD
        
        symbol_info = connector.get_symbol_info(symbol)
        return symbol_info.point if symbol_info else 0.01
        
    except Exception:
        return 0.01

def calculate_lot_size(symbol: str, risk_amount: float, stop_loss_pips: float, 
                        connector: MT5Connector = None) -> float:
    """คำนวณขนาด lot ตาม risk"""
    try:
        if connector is None:
            connector = get_mt5_connector()
        
        if not connector or not connector.is_connected():
            return 0.01
        
        symbol_info = connector.get_symbol_info(symbol)
        if not symbol_info:
            return 0.01
        
        # Calculate pip value
        pip_value = symbol_info.point * 10  # Standard pip
        
        # Calculate lot size
        lot_size = risk_amount / (stop_loss_pips * pip_value)
        
        # Apply symbol constraints
        lot_size = max(symbol_info.volume_min, lot_size)
        lot_size = min(symbol_info.volume_max, lot_size)
        
        # Round to step
        if symbol_info.volume_step > 0:
            lot_size = round(lot_size / symbol_info.volume_step) * symbol_info.volume_step
        
        return lot_size
        
    except Exception:
        return 0.01

def get_current_spread(symbol: str, connector: MT5Connector = None) -> float:
    """ดึง spread ปัจจุบัน"""
    try:
        if connector is None:
            connector = get_mt5_connector()
        
        if not connector or not connector.is_connected():
            return 0.0
        
        tick = connector.get_tick(symbol)
        if tick and hasattr(tick, 'ask') and hasattr(tick, 'bid'):
            symbol_info = connector.get_symbol_info(symbol)
            if symbol_info:
                return (tick.ask - tick.bid) / symbol_info.point
        
        return 0.0
        
    except Exception:
        return 0.0

# ===============================
# TEST FUNCTIONS
# ===============================

def test_mt5_connector():
    """ทดสอบ MT5 Connector"""
    print("🧪 ทดสอบ MT5 Connector...")
    
    # Create config
    config = MT5Config(
        auto_detect=True,
        verify_symbols=["XAUUSD"],
        max_reconnect_attempts=3
    )
    
    # Create connector
    connector = MT5Connector(config)
    
    # Test connection
    print("🔌 ทดสอบการเชื่อมต่อ...")
    success = connector.connect()
    print(f"   การเชื่อมต่อ: {'สำเร็จ' if success else 'ล้มเหลว'}")
    
    if success:
        # Test connection status
        status = connector.get_connection_status()
        print(f"   สถานะ: {status['status']}")
        print(f"   Mock: {status['is_mock']}")
        
        # Test account info
        account = connector.get_account_info()
        if account:
            print(f"   บัญชี: {account.login}")
            print(f"   Balance: ${account.balance:,.2f}")
            print(f"   Trading allowed: {account.trade_allowed}")
        
        # Test symbol info
        symbol_info = connector.get_symbol_info("XAUUSD")
        if symbol_info:
            print(f"   Symbol: {symbol_info.name}")
            print(f"   Digits: {symbol_info.digits}")
            print(f"   Min volume: {symbol_info.volume_min}")
        
        # Test tick data
        tick = connector.get_tick("XAUUSD")
        if tick:
            print(f"   Bid: {tick.bid}")
            print(f"   Ask: {tick.ask}")
            print(f"   Spread: {get_current_spread('XAUUSD', connector):.1f} pips")
        
        # Test positions
        positions = connector.get_positions()
        print(f"   Open positions: {len(positions)}")
        
        # Disconnect
        connector.disconnect()
        print("✅ ตัดการเชื่อมต่อ")
    
    print("✅ ทดสอบ MT5 Connector เสร็จสิ้น")

def test_utility_functions():
    """ทดสอบ utility functions"""
    print("🧪 ทดสอบ Utility Functions...")
    
    # Test ensure connection
    success = ensure_mt5_connection()
    print(f"📊 Ensure connection: {'สำเร็จ' if success else 'ล้มเหลว'}")
    
    if success:
        # Test symbol validation
        valid = validate_symbol("XAUUSD")
        print(f"   XAUUSD valid: {valid}")
        
        # Test point value
        point = get_symbol_point_value("XAUUSD")
        print(f"   XAUUSD point: {point}")
        
        # Test lot size calculation
        lot_size = calculate_lot_size("XAUUSD", 100.0, 10.0)
        print(f"   Calculated lot size: {lot_size}")
        
        # Test spread
        spread = get_current_spread("XAUUSD")
        print(f"   Current spread: {spread:.1f} pips")
        
        # Disconnect
        disconnect_mt5()
        print("✅ ตัดการเชื่อมต่อ")
    
    print("✅ ทดสอบ Utility Functions เสร็จสิ้น")

def benchmark_connection_speed():
    """ทดสอบความเร็วการเชื่อมต่อ"""
    print("⚡ ทดสอบความเร็วการเชื่อมต่อ...")
    
    import time
    
    # Test connection time
    start_time = time.time()
    success = ensure_mt5_connection()
    connection_time = time.time() - start_time
    
    print(f"📊 ผลลัพธ์:")
    print(f"   เวลาเชื่อมต่อ: {connection_time:.2f} วินาที")
    print(f"   สถานะ: {'สำเร็จ' if success else 'ล้มเหลว'}")
    
    if success:
        connector = get_mt5_connector()
        
        # Test data retrieval speed
        start_time = time.time()
        for i in range(100):
            tick = connector.get_tick("XAUUSD")
        data_time = time.time() - start_time
        
        print(f"   เวลาดึงข้อมูล (100 ticks): {data_time:.2f} วินาที")
        print(f"   ความเร็วเฉลี่ย: {data_time/100*1000:.2f} ms/tick")
        
        # Connection statistics
        status = connector.get_connection_status()
        stats = status.get('statistics', {})
        print(f"   Total connections: {stats.get('total_connections', 0)}")
        print(f"   Success rate: {stats.get('successful_connections', 0)}/{stats.get('total_connections', 0)}")
        
        disconnect_mt5()
    
    print("✅ ทดสอบความเร็วเสร็จสิ้น")

if __name__ == "__main__":
    test_mt5_connector()
    print("\n" + "="*50)
    test_utility_functions()
    print("\n" + "="*50)
    benchmark_connection_speed()