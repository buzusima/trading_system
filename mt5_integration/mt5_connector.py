#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT5 CONNECTOR - Real MetaTrader 5 Connection Manager
==================================================
ระบบจัดการการเชื่อมต่อ MetaTrader 5 แบบครอบคลุม
รองรับ connection management, error handling, และ failover mechanisms

🎯 FEATURES:
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
import traceback

# Safe MT5 import
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None
    print("⚠️ MetaTrader5 module ไม่พร้อมใช้งาน")

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

class OrderResult(Enum):
    """ผลการส่ง Order"""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    TIMEOUT = "TIMEOUT"

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
    verify_symbols: List[str] = field(default_factory=lambda: ["XAUUSD.v"])
    
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
    visible: bool = False
    select: bool = False
    digits: int = 5
    point: float = 0.00001
    spread: int = 0
    trade_mode: int = 0
    volume_min: float = 0.01
    volume_max: float = 1000.0
    volume_step: float = 0.01
    swap_long: float = 0.0
    swap_short: float = 0.0
    margin_initial: float = 0.0
    session_deals: int = 0
    session_buy_orders: int = 0
    session_sell_orders: int = 0
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class TradeRequest:
    """คำขอเทรด"""
    action: int
    symbol: str
    volume: float
    type: int
    price: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    deviation: int = 3
    magic: int = 0
    comment: str = ""
    type_time: int = 0
    type_filling: int = 0
    expiration: int = 0

@dataclass
class TradeResult:
    """ผลการเทรด"""
    retcode: int = 0
    order: int = 0
    deal: int = 0
    volume: float = 0.0
    price: float = 0.0
    comment: str = ""
    request_id: int = 0
    retcode_external: int = 0
    success: bool = False
    error_message: str = ""

class RealMT5Connector:
    """
    Real MT5 Connector - เชื่อมต่อ MT5 จริงเท่านั้น
    """
    
    def __init__(self, config: Optional[MT5Config] = None):
        if not MT5_AVAILABLE:
            raise ImportError("MetaTrader5 module is required but not available")
        
        self.config = config or MT5Config()
        self.status = ConnectionStatus.DISCONNECTED
        self.account_info = AccountInfo()
        self.symbols_cache: Dict[str, SymbolInfo] = {}
        
        # Connection management
        self.connection_lock = threading.Lock()
        self.last_connection_time = None
        self.reconnect_attempts = 0
        self.connection_errors = []
        
        # Performance tracking
        self.connection_count = 0
        self.trade_count = 0
        self.error_count = 0
        
        # Monitoring
        self.monitor_thread = None
        self.is_monitoring = False
        
        print("🔌 MT5 Connector initialized")
    
    def connect(self) -> bool:
        """เชื่อมต่อกับ MT5"""
        with self.connection_lock:
            try:
                self.status = ConnectionStatus.CONNECTING
                print("🔌 Connecting to MT5...")
                
                # Initialize MT5
                if not self._initialize_mt5():
                    return False
                
                # Verify connection
                if not self._verify_connection():
                    return False
                
                # Load account info
                if not self._load_account_info():
                    return False
                
                # Cache symbols
                if self.config.cache_symbols:
                    self._cache_symbols()
                
                # Set status
                self.status = ConnectionStatus.CONNECTED
                self.last_connection_time = datetime.now()
                self.connection_count += 1
                self.reconnect_attempts = 0
                
                print("✅ MT5 connected successfully")
                return True
                
            except Exception as e:
                self.status = ConnectionStatus.ERROR
                self.error_count += 1
                self.connection_errors.append({
                    'timestamp': datetime.now(),
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
                print(f"❌ MT5 connection failed: {e}")
                return False
    
    def _initialize_mt5(self) -> bool:
        """Initialize MT5 terminal"""
        try:
            # Initialize without parameters first (auto-detect)
            if self.config.auto_detect:
                if mt5.initialize():
                    print("✅ MT5 auto-initialized")
                    return True
            
            # Initialize with specific parameters
            if self.config.path:
                if mt5.initialize(path=self.config.path, 
                                login=self.config.login,
                                password=self.config.password,
                                server=self.config.server,
                                timeout=self.config.timeout,
                                portable=self.config.portable):
                    print(f"✅ MT5 initialized with path: {self.config.path}")
                    return True
            
            # Try default initialization
            if mt5.initialize():
                print("✅ MT5 initialized with defaults")
                return True
            
            # Get last error
            error_code = mt5.last_error()
            print(f"❌ MT5 initialization failed: {error_code}")
            return False
            
        except Exception as e:
            print(f"❌ MT5 initialization error: {e}")
            return False
    
    def _verify_connection(self) -> bool:
        """ตรวจสอบการเชื่อมต่อ"""
        try:
            # Test basic functions
            terminal_info = mt5.terminal_info()
            if not terminal_info:
                print("❌ Cannot get terminal info")
                return False
            
            # Check if connected to trade server
            if not terminal_info.connected:
                print("❌ Not connected to trade server")
                return False
            
            # Test market data access
            symbols = mt5.symbols_get()
            if not symbols:
                print("⚠️ No symbols available")
                return False
            
            print(f"✅ Connection verified: {len(symbols)} symbols available")
            return True
            
        except Exception as e:
            print(f"❌ Connection verification failed: {e}")
            return False
    
    def _load_account_info(self) -> bool:
        """โหลดข้อมูลบัญชี"""
        try:
            account_info = mt5.account_info()
            if not account_info:
                print("❌ Cannot get account info")
                return False
            
            # Update account info
            self.account_info = AccountInfo(
                login=account_info.login,
                trade_mode=str(account_info.trade_mode),
                name=account_info.name,
                server=account_info.server,
                currency=account_info.currency,
                company=account_info.company,
                balance=account_info.balance,
                equity=account_info.equity,
                margin=account_info.margin,
                free_margin=account_info.margin_free,
                margin_level=account_info.margin_level,
                credit=account_info.credit,
                profit=account_info.profit,
                trade_allowed=account_info.trade_allowed,
                expert_allowed=account_info.trade_expert,
                margin_call=account_info.margin_so_call,
                margin_so_call=account_info.margin_so_call,
                last_update=datetime.now()
            )
            
            # Verify trading is allowed
            if self.config.verify_trade_allowed and not account_info.trade_allowed:
                print("❌ Trading not allowed on this account")
                return False
            
            print(f"✅ Account loaded: {account_info.login} - {account_info.server}")
            print(f"💰 Balance: ${account_info.balance:,.2f}")
            print(f"📈 Equity: ${account_info.equity:,.2f}")
            print(f"🔓 Trading: {'Allowed' if account_info.trade_allowed else 'Disabled'}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load account info: {e}")
            return False
    
    def _cache_symbols(self):
        """Cache symbols information"""
        try:
            print("📂 Caching symbols...")
            
            # Get all symbols
            symbols = mt5.symbols_get()
            if not symbols:
                return
            
            cached_count = 0
            for symbol in symbols:
                try:
                    symbol_info = SymbolInfo(
                        name=symbol.name,
                        visible=symbol.visible,
                        select=symbol.select,
                        digits=symbol.digits,
                        point=symbol.point,
                        spread=symbol.spread,
                        trade_mode=symbol.trade_mode,
                        volume_min=symbol.volume_min,
                        volume_max=symbol.volume_max,
                        volume_step=symbol.volume_step,
                        swap_long=symbol.swap_long,
                        swap_short=symbol.swap_short,
                        margin_initial=symbol.margin_initial,
                        session_deals=symbol.session_deals,
                        session_buy_orders=symbol.session_buy_orders,
                        session_sell_orders=symbol.session_sell_orders,
                        last_update=datetime.now()
                    )
                    
                    self.symbols_cache[symbol.name] = symbol_info
                    cached_count += 1
                    
                except Exception as e:
                    print(f"⚠️ Error caching symbol {symbol.name}: {e}")
            
            print(f"✅ Cached {cached_count} symbols")
            
            # Verify target symbols
            for symbol_name in self.config.verify_symbols:
                if symbol_name in self.symbols_cache:
                    symbol_info = self.symbols_cache[symbol_name]
                    print(f"✅ Target symbol {symbol_name}: Available")
                    print(f"   Digits: {symbol_info.digits}, Min Volume: {symbol_info.volume_min}")
                else:
                    print(f"⚠️ Target symbol {symbol_name}: Not available")
                    
        except Exception as e:
            print(f"❌ Symbol caching error: {e}")
    
    def disconnect(self):
        """ตัดการเชื่อมต่อ"""
        try:
            self.stop_monitoring()
            
            if self.status != ConnectionStatus.DISCONNECTED:
                mt5.shutdown()
                self.status = ConnectionStatus.DISCONNECTED
                print("⏹️ MT5 disconnected")
            
        except Exception as e:
            print(f"❌ Disconnect error: {e}")
    
    def reconnect(self) -> bool:
        """เชื่อมต่อใหม่"""
        if self.reconnect_attempts >= self.config.max_reconnect_attempts:
            print(f"❌ Max reconnect attempts reached: {self.reconnect_attempts}")
            return False
        
        self.status = ConnectionStatus.RECONNECTING
        self.reconnect_attempts += 1
        
        print(f"🔄 Reconnecting... (Attempt {self.reconnect_attempts})")
        
        # Wait before reconnecting
        time.sleep(self.config.reconnect_delay)
        
        # Disconnect first
        try:
            mt5.shutdown()
        except:
            pass
        
        # Try to connect
        return self.connect()
    
    def is_connected(self) -> bool:
        """ตรวจสอบสถานะการเชื่อมต่อ"""
        if self.status != ConnectionStatus.CONNECTED:
            return False
        
        try:
            # Quick connection test
            terminal_info = mt5.terminal_info()
            return terminal_info is not None and terminal_info.connected
        except:
            return False
    
    def ensure_connection(self) -> bool:
        """ตรวจสอบและรับรองการเชื่อมต่อ"""
        if self.is_connected():
            return True
        
        print("⚠️ Connection lost, attempting to reconnect...")
        return self.reconnect()
    
    def send_order(self, request: TradeRequest) -> TradeResult:
        """ส่ง order ไปยัง MT5"""
        try:
            if not self.ensure_connection():
                return TradeResult(
                    success=False,
                    error_message="No connection to MT5"
                )
            
            # Prepare MT5 request
            mt5_request = {
                "action": request.action,
                "symbol": request.symbol,
                "volume": request.volume,
                "type": request.type,
                "price": request.price,
                "sl": request.sl,
                "tp": request.tp,
                "deviation": request.deviation,
                "magic": request.magic,
                "comment": request.comment,
                "type_time": request.type_time,
                "type_filling": request.type_filling,
            }
            
            # Add expiration if needed
            if request.expiration > 0:
                mt5_request["expiration"] = request.expiration
            
            # Send order
            result = mt5.order_send(mt5_request)
            self.trade_count += 1
            
            if result is None:
                error = mt5.last_error()
                return TradeResult(
                    success=False,
                    error_message=f"Order send failed: {error}"
                )
            
            # Create result
            trade_result = TradeResult(
                retcode=result.retcode,
                order=result.order,
                deal=result.deal,
                volume=result.volume,
                price=result.price,
                comment=result.comment,
                request_id=result.request_id,
                retcode_external=result.retcode_external,
                success=(result.retcode == mt5.TRADE_RETCODE_DONE),
                error_message="" if result.retcode == mt5.TRADE_RETCODE_DONE else f"Error {result.retcode}: {result.comment}"
            )
            
            # Log trade if enabled
            if self.config.log_trades:
                status = "✅" if trade_result.success else "❌"
                print(f"{status} Order: {request.symbol} {request.volume} lots")
                if trade_result.success:
                    print(f"   Ticket: {trade_result.order}, Price: {trade_result.price}")
                else:
                    print(f"   Error: {trade_result.error_message}")
            
            return trade_result
            
        except Exception as e:
            self.error_count += 1
            return TradeResult(
                success=False,
                error_message=f"Exception in send_order: {e}"
            )
    
    def get_positions(self, symbol: Optional[str] = None) -> List[Any]:
        """ดึงข้อมูล positions"""
        try:
            if not self.ensure_connection():
                return []
            
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            
            return list(positions) if positions else []
            
        except Exception as e:
            print(f"❌ Error getting positions: {e}")
            return []
    
    def get_orders(self, symbol: Optional[str] = None) -> List[Any]:
        """ดึงข้อมูล pending orders"""
        try:
            if not self.ensure_connection():
                return []
            
            if symbol:
                orders = mt5.orders_get(symbol=symbol)
            else:
                orders = mt5.orders_get()
            
            return list(orders) if orders else []
            
        except Exception as e:
            print(f"❌ Error getting orders: {e}")
            return []
    
    def get_history_deals(self, date_from: datetime, date_to: datetime) -> List[Any]:
        """ดึงประวัติ deals"""
        try:
            if not self.ensure_connection():
                return []
            
            deals = mt5.history_deals_get(date_from, date_to)
            return list(deals) if deals else []
            
        except Exception as e:
            print(f"❌ Error getting history deals: {e}")
            return []
    
    def get_tick(self, symbol: str) -> Optional[Any]:
        """ดึงข้อมูล tick ล่าสุด"""
        try:
            if not self.ensure_connection():
                return None
            
            return mt5.symbol_info_tick(symbol)
            
        except Exception as e:
            print(f"❌ Error getting tick for {symbol}: {e}")
            return None
    
    def get_rates(self, symbol: str, timeframe: int, start_pos: int = 0, count: int = 100) -> Optional[Any]:
        """ดึงข้อมูลราคา"""
        try:
            if not self.ensure_connection():
                return None
            
            rates = mt5.copy_rates_from_pos(symbol, timeframe, start_pos, count)
            return rates
            
        except Exception as e:
            print(f"❌ Error getting rates for {symbol}: {e}")
            return None
    
    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """ดึงข้อมูล symbol"""
        try:
            # Check cache first
            if symbol in self.symbols_cache:
                cached_info = self.symbols_cache[symbol]
                # Check if cache is recent (less than 1 hour)
                if (datetime.now() - cached_info.last_update).total_seconds() < 3600:
                    return cached_info
            
            if not self.ensure_connection():
                return None
            
            # Get fresh data
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return None
            
            # Create SymbolInfo object
            info = SymbolInfo(
                name=symbol_info.name,
                visible=symbol_info.visible,
                select=symbol_info.select,
                digits=symbol_info.digits,
                point=symbol_info.point,
                spread=symbol_info.spread,
                trade_mode=symbol_info.trade_mode,
                volume_min=symbol_info.volume_min,
                volume_max=symbol_info.volume_max,
                volume_step=symbol_info.volume_step,
                swap_long=symbol_info.swap_long,
                swap_short=symbol_info.swap_short,
                margin_initial=symbol_info.margin_initial,
                session_deals=symbol_info.session_deals,
                session_buy_orders=symbol_info.session_buy_orders,
                session_sell_orders=symbol_info.session_sell_orders,
                last_update=datetime.now()
            )
            
            # Update cache
            self.symbols_cache[symbol] = info
            
            return info
            
        except Exception as e:
            print(f"❌ Error getting symbol info for {symbol}: {e}")
            return None
    
    def refresh_account_info(self) -> bool:
        """รีเฟรชข้อมูลบัญชี"""
        try:
            if not self.ensure_connection():
                return False
            
            return self._load_account_info()
            
        except Exception as e:
            print(f"❌ Error refreshing account info: {e}")
            return False
    
    def get_market_status(self) -> MarketStatus:
        """ตรวจสอบสถานะตลาด"""
        try:
            if not self.ensure_connection():
                return MarketStatus.UNKNOWN
            
            # Simple market status check based on time
            now = datetime.now()
            hour = now.hour
            weekday = now.weekday()
            
            # Weekend check
            if weekday >= 5:  # Saturday = 5, Sunday = 6
                return MarketStatus.CLOSED
            
            # Market hours (approximate for Forex/Gold)
            if 22 <= hour or hour < 2:  # 10 PM - 2 AM
                return MarketStatus.OPEN
            elif 2 <= hour < 6:  # 2 AM - 6 AM
                return MarketStatus.PRE_MARKET
            elif 6 <= hour < 22:  # 6 AM - 10 PM
                return MarketStatus.OPEN
            else:
                return MarketStatus.POST_MARKET
                
        except Exception as e:
            print(f"❌ Error checking market status: {e}")
            return MarketStatus.UNKNOWN
    
    def start_monitoring(self):
        """เริ่มการตรวจสอบการเชื่อมต่อ"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("✅ Connection monitoring started")
    
    def stop_monitoring(self):
        """หยุดการตรวจสอบ"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("⏹️ Connection monitoring stopped")
    
    def _monitor_loop(self):
        """Loop การตรวจสอบการเชื่อมต่อ"""
        while self.is_monitoring:
            try:
                if not self.is_connected():
                    print("⚠️ Connection lost, attempting reconnect...")
                    self.reconnect()
                
                # Refresh account info every 30 seconds
                if self.is_connected() and int(time.time()) % 30 == 0:
                    self.refresh_account_info()
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"❌ Monitor loop error: {e}")
                time.sleep(10)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """ดึงสถิติการเชื่อมต่อ"""
        return {
            'status': self.status.value,
            'connection_count': self.connection_count,
            'trade_count': self.trade_count,
            'error_count': self.error_count,
            'reconnect_attempts': self.reconnect_attempts,
            'last_connection_time': self.last_connection_time.isoformat() if self.last_connection_time else None,
            'account_login': self.account_info.login,
            'account_server': self.account_info.server,
            'symbols_cached': len(self.symbols_cache),
            'market_status': self.get_market_status().value,
            'is_monitoring': self.is_monitoring
        }

# ===== FACTORY FUNCTIONS =====

def create_mt5_connector(config: Optional[MT5Config] = None) -> RealMT5Connector:
    """สร้าง MT5 Connector"""
    try:
        connector = RealMT5Connector(config)
        print("✅ MT5 Connector created")
        return connector
    except Exception as e:
        print(f"❌ Failed to create MT5 Connector: {e}")
        raise

def auto_connect_mt5(symbols_to_verify: List[str] = None) -> RealMT5Connector:
    """เชื่อมต่อ MT5 แบบอัตโนมัติ"""
    config = MT5Config(
        auto_detect=True,
        verify_trade_allowed=True,
        verify_symbols=symbols_to_verify or ["XAUUSD.v"],
        cache_symbols=True,
        enable_logging=True
    )
    
    connector = create_mt5_connector(config)
    
    if connector.connect():
        connector.start_monitoring()
        print("✅ MT5 auto-connected and monitoring started")
        return connector
    else:
        raise ConnectionError("Failed to auto-connect to MT5")

# ===== TESTING FUNCTION =====

def test_mt5_connector():
    """ทดสอบ MT5 Connector"""
    print("🧪 Testing MT5 Connector...")
    
    try:
        # สร้างและเชื่อมต่อ
        connector = auto_connect_mt5(["XAUUSD.v"])
        
        # ทดสอบฟังก์ชันต่างๆ
        print("\n📊 Testing functions...")
        
        # Test account info
        connector.refresh_account_info()
        print(f"Account: {connector.account_info.login}")
        
        # Test symbol info
        symbol_info = connector.get_symbol_info("XAUUSD.v")
        if symbol_info:
            print(f"XAUUSD: Digits={symbol_info.digits}, Min Volume={symbol_info.volume_min}")
        
        # Test tick data
        tick = connector.get_tick("XAUUSD.v")
        if tick:
            print(f"XAUUSD Tick: Bid={tick.bid}, Ask={tick.ask}")
        
        # Test positions
        positions = connector.get_positions()
        print(f"Positions: {len(positions)}")
        
        # Test market status
        market_status = connector.get_market_status()
        print(f"Market Status: {market_status.value}")
        
        # Show stats
        stats = connector.get_connection_stats()
        print(f"\n📈 Connection Stats:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # รันทดสอบ 30 วินาที
        print("\n⏱️ Running 30-second test...")
        import time
        time.sleep(30)
        
        # ตัดการเชื่อมต่อ
        connector.disconnect()
        
        print("✅ MT5 Connector test completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    # ทดสอบหาก run โดยตรง
    test_mt5_connector()