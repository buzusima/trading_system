#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REAL ORDER EXECUTOR - Live MT5 Order Execution System
====================================================
ระบบส่ง Orders จริงไปยัง MT5 สำหรับ Live Trading เท่านั้น
ไม่มี Mock หรือ Simulation ใดๆ - ส่ง Orders จริงเท่านั้น

🎯 หน้าที่:
- Execute Orders ไปยัง MT5 Live Account
- Position Management แบบ Real-time
- Error Handling สำหรับ Live Trading
- Order Validation และ Risk Checks
"""

import MetaTrader5 as mt5
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import queue
from collections import deque

# Internal imports
from config.settings import get_system_settings
from config.trading_params import get_trading_parameters
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class OrderStatus(Enum):
    """สถานะ Order"""
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    SENDING = "SENDING"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

class OrderType(Enum):
    """ประเภท Order"""
    MARKET_BUY = "MARKET_BUY"
    MARKET_SELL = "MARKET_SELL"
    PENDING_BUY = "PENDING_BUY"
    PENDING_SELL = "PENDING_SELL"
    CLOSE_POSITION = "CLOSE_POSITION"

@dataclass
class ExecutionResult:
    """ผลการ Execute Order"""
    success: bool
    ticket: Optional[int] = None
    price: Optional[float] = None
    volume: Optional[float] = None
    error_code: Optional[int] = None
    error_message: str = ""
    execution_time: Optional[datetime] = None
    slippage: float = 0.0
    commission: float = 0.0
    swap: float = 0.0

@dataclass
class OrderRequest:
    """คำขอ Order"""
    request_id: str
    timestamp: datetime
    symbol: str
    order_type: OrderType
    volume: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    magic_number: int = 0
    comment: str = ""
    deviation: int = 3
    type_filling: int = mt5.ORDER_FILLING_IOC
    type_time: int = mt5.ORDER_TIME_GTC
    expiration: Optional[datetime] = None
    status: OrderStatus = OrderStatus.PENDING
    result: Optional[ExecutionResult] = None

class RealOrderExecutor:
    """Real Order Executor - ส่ง Orders จริง"""
    
    def __init__(self):
        self.logger = setup_component_logger("RealOrderExecutor")
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # ตรวจสอบ MT5 connection
        if not mt5.initialize():
            raise RuntimeError("❌ ไม่สามารถเชื่อมต่อ MT5 ได้")
        
        # ตรวจสอบ account
        account_info = mt5.account_info()
        if not account_info:
            raise RuntimeError("❌ ไม่สามารถดึงข้อมูล Account ได้")
        
        if not account_info.trade_allowed:
            raise RuntimeError("❌ Account ไม่อนุญาตให้เทรด")
        
        self.logger.info(f"✅ เชื่อมต่อ Account: {account_info.login} ({account_info.server})")
        self.logger.info(f"💰 Balance: {account_info.balance:.2f} {account_info.currency}")
        
        # Execution state
        self.is_running = False
        self.execution_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Order management
        self.order_queue: queue.Queue = queue.Queue()
        self.executed_orders: deque = deque(maxlen=1000)
        self.execution_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'success_rate': 0.0,
            'total_volume': 0.0,
            'total_commission': 0.0,
            'average_slippage': 0.0,
            'last_execution_time': None
        }
        
        # Symbol verification
        self.symbol = "XAUUSD"
        symbol_info = mt5.symbol_info(self.symbol)
        if not symbol_info:
            raise RuntimeError(f"❌ ไม่พบ Symbol {self.symbol}")
        
        if not symbol_info.visible:
            if not mt5.symbol_select(self.symbol, True):
                raise RuntimeError(f"❌ ไม่สามารถเลือก Symbol {self.symbol}")
        
        self.symbol_info = symbol_info
        self.logger.info(f"✅ Symbol {self.symbol} พร้อมใช้งาน")
    
    @handle_trading_errors(ErrorCategory.TRADING_LOGIC, ErrorSeverity.HIGH)
    def start_execution_engine(self) -> bool:
        """เริ่ม Execution Engine"""
        if self.is_running:
            self.logger.warning("⚠️ Order Executor ทำงานอยู่แล้ว")
            return True
        
        try:
            self.is_running = True
            self.stop_event.clear()
            
            # เริ่ม execution thread
            self.execution_thread = threading.Thread(
                target=self._execution_loop,
                name="OrderExecutionThread",
                daemon=True
            )
            self.execution_thread.start()
            
            self.logger.info("🚀 เริ่ม Real Order Execution Engine")
            return True
            
        except Exception as e:
            self.is_running = False
            self.logger.error(f"❌ ไม่สามารถเริ่ม Execution Engine: {e}")
            return False
    
    def stop_execution_engine(self) -> bool:
        """หยุด Execution Engine"""
        try:
            self.stop_event.set()
            self.is_running = False
            
            if self.execution_thread and self.execution_thread.is_alive():
                self.execution_thread.join(timeout=5.0)
            
            self.logger.info("⏹️ หยุด Order Execution Engine")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถหยุด Execution Engine: {e}")
            return False
    
    def _execution_loop(self):
        """Loop หลักสำหรับ Execute Orders"""
        self.logger.info("🔄 เริ่ม Order Execution Loop")
        
        while not self.stop_event.is_set():
            try:
                # ดึง Order จาก queue
                try:
                    order_request = self.order_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Execute Order
                self._execute_order_request(order_request)
                
                # Mark task as done
                self.order_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Execution Loop: {e}")
                time.sleep(1)
    
    def execute_signal(self, trading_signal) -> Dict[str, Any]:
        """Execute Signal (เชื่อมต่อกับ Signal Generator)"""
        try:
            # แปลง Trading Signal เป็น Order Request
            order_request = self._create_order_from_signal(trading_signal)
            
            # Execute Order แบบ synchronous
            self._execute_order_request(order_request)
            
            # Return result
            if order_request.result and order_request.result.success:
                return {
                    'success': True,
                    'ticket': order_request.result.ticket,
                    'price': order_request.result.price,
                    'volume': order_request.result.volume,
                    'execution_time': order_request.result.execution_time
                }
            else:
                return {
                    'success': False,
                    'error': order_request.result.error_message if order_request.result else "Unknown error"
                }
                
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถ execute signal: {e}")
            return {'success': False, 'error': str(e)}
    
    def submit_order(self, order_request: OrderRequest) -> bool:
        """ส่ง Order เข้า Queue"""
        try:
            self.order_queue.put(order_request)
            self.logger.info(f"📤 ส่ง Order เข้า Queue: {order_request.request_id}")
            return True
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถส่ง Order เข้า Queue: {e}")
            return False
    
    @handle_trading_errors(ErrorCategory.TRADING_LOGIC, ErrorSeverity.HIGH)
    def _execute_order_request(self, order_request: OrderRequest):
        """Execute Order Request"""
        try:
            order_request.status = OrderStatus.VALIDATING
            
            # Validate Order
            if not self._validate_order_request(order_request):
                order_request.status = OrderStatus.REJECTED
                order_request.result = ExecutionResult(
                    success=False,
                    error_message="Order validation failed"
                )
                return
            
            order_request.status = OrderStatus.SENDING
            
            # สร้าง MT5 Request
            mt5_request = self._create_mt5_request(order_request)
            if not mt5_request:
                order_request.status = OrderStatus.REJECTED
                order_request.result = ExecutionResult(
                    success=False,
                    error_message="Failed to create MT5 request"
                )
                return
            
            # ส่ง Order ไปยัง MT5
            execution_start = datetime.now()
            result = mt5.order_send(mt5_request)
            execution_end = datetime.now()
            
            # ประมวลผล Result
            order_request.result = self._process_mt5_result(result, execution_start, execution_end)
            
            if order_request.result.success:
                order_request.status = OrderStatus.EXECUTED
                self.stats['successful_orders'] += 1
                self.stats['total_volume'] += order_request.result.volume
                
                self.logger.info(
                    f"✅ Order executed: Ticket #{order_request.result.ticket} "
                    f"{order_request.order_type.value} {order_request.result.volume} "
                    f"@ {order_request.result.price:.2f}"
                )
            else:
                order_request.status = OrderStatus.REJECTED
                self.stats['failed_orders'] += 1
                
                self.logger.error(
                    f"❌ Order rejected: {order_request.result.error_message} "
                    f"Code: {order_request.result.error_code}"
                )
            
            # อัปเดตสถิติ
            with self.execution_lock:
                self.executed_orders.append(order_request)
                self.stats['total_orders'] += 1
                if self.stats['total_orders'] > 0:
                    self.stats['success_rate'] = self.stats['successful_orders'] / self.stats['total_orders']
                self.stats['last_execution_time'] = execution_end
            
        except Exception as e:
            order_request.status = OrderStatus.REJECTED
            order_request.result = ExecutionResult(
                success=False,
                error_message=f"Execution error: {e}"
            )
            self.logger.error(f"❌ ไม่สามารถ execute order: {e}")
    
    def _create_order_from_signal(self, trading_signal) -> OrderRequest:
        """สร้าง Order Request จาก Trading Signal"""
        signal_type = trading_signal.signal_type
        
        if signal_type.value == "BUY":
            order_type = OrderType.MARKET_BUY
        else:
            order_type = OrderType.MARKET_SELL
        
        return OrderRequest(
            request_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            symbol=trading_signal.symbol,
            order_type=order_type,
            volume=trading_signal.volume,
            price=trading_signal.entry_price,
            magic_number=trading_signal.magic_number,
            comment=f"{trading_signal.entry_strategy.value}_{trading_signal.signal_id[:8]}",
            deviation=self.trading_params.slippage
        )
    
    def _validate_order_request(self, order_request: OrderRequest) -> bool:
        """Validate Order Request"""
        try:
            # ตรวจสอบ Symbol
            if order_request.symbol != self.symbol:
                return False
            
            # ตรวจสอบ Volume
            if order_request.volume < self.symbol_info.volume_min:
                return False
            if order_request.volume > self.symbol_info.volume_max:
                return False
            
            # ตรวจสอบ Volume Step
            volume_steps = order_request.volume / self.symbol_info.volume_step
            if abs(volume_steps - round(volume_steps)) > 0.001:
                return False
            
            # ตรวจสอบ Market Status
            tick = mt5.symbol_info_tick(order_request.symbol)
            if not tick:
                return False
            
            # ตรวจสอบ Account Balance (basic check)
            account_info = mt5.account_info()
            if not account_info or not account_info.trade_allowed:
                return False
            
            # ตรวจสอบ Free Margin
            required_margin = order_request.volume * tick.ask * 0.01  # Rough calculation
            if account_info.margin_free < required_margin:
                self.logger.warning(f"⚠️ Free margin might be insufficient")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถ validate order: {e}")
            return False
    
    def _create_mt5_request(self, order_request: OrderRequest) -> Optional[Dict[str, Any]]:
        """สร้าง MT5 Request Dictionary"""
        try:
            # Get current tick
            tick = mt5.symbol_info_tick(order_request.symbol)
            if not tick:
                return None
            
            # Determine MT5 order type and price
            if order_request.order_type == OrderType.MARKET_BUY:
                mt5_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            elif order_request.order_type == OrderType.MARKET_SELL:
                mt5_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                # Pending orders
                mt5_type = mt5.ORDER_TYPE_BUY_LIMIT if order_request.order_type == OrderType.PENDING_BUY else mt5.ORDER_TYPE_SELL_LIMIT
                price = order_request.price or tick.ask
            
            # สร้าง request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": order_request.symbol,
                "volume": order_request.volume,
                "type": mt5_type,
                "price": price,
                "deviation": order_request.deviation,
                "magic": order_request.magic_number,
                "comment": order_request.comment,
                "type_time": order_request.type_time,
                "type_filling": order_request.type_filling,
            }
            
            # เพิ่ม SL/TP ถ้ามี (แต่ตาม requirement ไม่ใช้)
            if order_request.stop_loss:
                request["sl"] = order_request.stop_loss
            
            if order_request.take_profit:
                request["tp"] = order_request.take_profit
            
            # เพิ่ม expiration ถ้ามี
            if order_request.expiration:
                request["expiration"] = int(order_request.expiration.timestamp())
            
            return request
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถสร้าง MT5 request: {e}")
            return None
    
    def _process_mt5_result(self, mt5_result, start_time: datetime, end_time: datetime) -> ExecutionResult:
        """ประมวลผล MT5 Result"""
        try:
            if not mt5_result:
                return ExecutionResult(
                    success=False,
                    error_message="No result from MT5",
                    execution_time=end_time
                )
            
            # ตรวจสอบ Return Code
            if mt5_result.retcode == mt5.TRADE_RETCODE_DONE:
                # Success
                return ExecutionResult(
                    success=True,
                    ticket=mt5_result.order,
                    price=mt5_result.price,
                    volume=mt5_result.volume,
                    execution_time=end_time,
                    slippage=abs(mt5_result.price - mt5_result.request.price) if hasattr(mt5_result, 'request') else 0.0
                )
            else:
                # Error codes mapping
                error_messages = {
                    mt5.TRADE_RETCODE_REQUOTE: "Requote",
                    mt5.TRADE_RETCODE_REJECT: "Request rejected",
                    mt5.TRADE_RETCODE_CANCEL: "Request cancelled",
                    mt5.TRADE_RETCODE_PLACED: "Order placed",
                    mt5.TRADE_RETCODE_TIMEOUT: "Timeout",
                    mt5.TRADE_RETCODE_INVALID: "Invalid request",
                    mt5.TRADE_RETCODE_INVALID_VOLUME: "Invalid volume",
                    mt5.TRADE_RETCODE_INVALID_PRICE: "Invalid price",
                    mt5.TRADE_RETCODE_INVALID_STOPS: "Invalid stops",
                    mt5.TRADE_RETCODE_TRADE_DISABLED: "Trade disabled",
                    mt5.TRADE_RETCODE_MARKET_CLOSED: "Market closed",
                    mt5.TRADE_RETCODE_NO_MONEY: "No money",
                    mt5.TRADE_RETCODE_PRICE_CHANGED: "Price changed",
                    mt5.TRADE_RETCODE_PRICE_OFF: "Price off",
                    mt5.TRADE_RETCODE_INVALID_EXPIRATION: "Invalid expiration",
                    mt5.TRADE_RETCODE_ORDER_CHANGED: "Order changed",
                    mt5.TRADE_RETCODE_TOO_MANY_REQUESTS: "Too many requests",
                    mt5.TRADE_RETCODE_NO_CHANGES: "No changes",
                    mt5.TRADE_RETCODE_SERVER_DISABLES_AT: "Server disables AT",
                    mt5.TRADE_RETCODE_CLIENT_DISABLES_AT: "Client disables AT",
                    mt5.TRADE_RETCODE_LOCKED: "Locked",
                    mt5.TRADE_RETCODE_FROZEN: "Frozen",
                    mt5.TRADE_RETCODE_INVALID_FILL: "Invalid fill",
                    mt5.TRADE_RETCODE_CONNECTION: "Connection error",
                    mt5.TRADE_RETCODE_ONLY_REAL: "Only real accounts",
                    mt5.TRADE_RETCODE_LIMIT_ORDERS: "Limit orders",
                    mt5.TRADE_RETCODE_LIMIT_VOLUME: "Limit volume",
                }
                
                error_msg = error_messages.get(mt5_result.retcode, f"Unknown error: {mt5_result.retcode}")
                
                return ExecutionResult(
                    success=False,
                    error_code=mt5_result.retcode,
                    error_message=error_msg,
                    execution_time=end_time
                )
                
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"Result processing error: {e}",
                execution_time=end_time
            )
    
    def create_market_order(self, symbol: str, order_type: str, volume: float, 
                          magic_number: int = 0, comment: str = "") -> OrderRequest:
        """สร้าง Market Order"""
        
        order_type_enum = OrderType.MARKET_BUY if order_type.upper() == "BUY" else OrderType.MARKET_SELL
        
        return OrderRequest(
            request_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            symbol=symbol,
            order_type=order_type_enum,
            volume=volume,
            magic_number=magic_number,
            comment=comment
        )
    
    def close_position(self, ticket: int, volume: Optional[float] = None) -> bool:
        """ปิด Position"""
        try:
            # ดึงข้อมูล position
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                self.logger.error(f"❌ ไม่พบ Position #{ticket}")
                return False
            
            position = positions[0]
            close_volume = volume or position.volume
            
            # สร้าง close request
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(position.symbol).bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(position.symbol).ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": close_volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "magic": position.magic,
                "comment": f"Close_{ticket}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # ส่ง close order
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.logger.info(f"✅ ปิด Position #{ticket} สำเร็จ")
                return True
            else:
                self.logger.error(f"❌ ไม่สามารถปิด Position #{ticket}: {result.retcode if result else 'No result'}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถปิด Position #{ticket}: {e}")
            return False
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """ดึงสถิติการ Execute"""
        return {
            'total_orders': self.stats['total_orders'],
            'successful_orders': self.stats['successful_orders'],
            'failed_orders': self.stats['failed_orders'],
            'success_rate': self.stats['success_rate'],
            'total_volume': self.stats['total_volume'],
            'average_slippage': self.stats['average_slippage'],
            'last_execution_time': self.stats['last_execution_time'],
            'queue_size': self.order_queue.qsize(),
            'is_running': self.is_running
        }
    
    def get_recent_orders(self, count: int = 10) -> List[OrderRequest]:
        """ดึง Orders ล่าสุด"""
        with self.execution_lock:
            return list(self.executed_orders)[-count:]
    
    def get_mt5_account_info(self) -> Optional[Dict[str, Any]]:
        """ดึงข้อมูล Account จาก MT5"""
        try:
            account_info = mt5.account_info()
            if not account_info:
                return None
            
            return {
                'login': account_info.login,
                'server': account_info.server,
                'name': account_info.name,
                'company': account_info.company,
                'currency': account_info.currency,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'margin_level': account_info.margin_level,
                'trade_allowed': account_info.trade_allowed,
                'expert_allowed': account_info.expert_allowed
            }
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถดึงข้อมูล Account: {e}")
            return None
    
    def __del__(self):
        """Cleanup เมื่อ object ถูกทำลาย"""
        try:
            self.stop_execution_engine()
        except:
            pass

# ===== FACTORY FUNCTION =====

def get_smart_order_executor() -> RealOrderExecutor:
    """Factory function สำหรับสร้าง Real Order Executor"""
    return RealOrderExecutor()

# ===== MAIN TESTING =====

if __name__ == "__main__":
    """ทดสอบ Real Order Executor"""
    
    print("🧪 ทดสอบ Real Order Executor")
    print("=" * 50)
    
    try:
        # สร้าง order executor
        executor = RealOrderExecutor()
        print("✅ สร้าง Order Executor สำเร็จ")
        
        # แสดงข้อมูล account
        account_info = executor.get_mt5_account_info()
        if account_info:
            print(f"💰 Account: {account_info['login']} ({account_info['server']})")
            print(f"💰 Balance: {account_info['balance']:.2f} {account_info['currency']}")
            print(f"💰 Free Margin: {account_info['free_margin']:.2f}")
            print(f"💰 Trade Allowed: {account_info['trade_allowed']}")
        
        # แสดงสถิติ
        stats = executor.get_execution_statistics()
        print(f"📊 สถิติ: {stats}")
        
        print("\n🎯 Real Order Executor พร้อมใช้งาน")
        print("⚠️ ระบบนี้จะส่ง Orders จริงไปยัง MT5 Live Account")
        
    except Exception as e:
        print(f"❌ ข้อผิดพลาด: {e}")
        import traceback
        traceback.print_exc()