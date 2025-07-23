#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIVE ORDER EXECUTION ENGINE - เครื่องมือส่งออร์เดอร์แบบเรียลไทม์
======================================================
จัดการการส่งออร์เดอร์ MT5 แบบมืออาชีพ พร้อมระบบตรวจสอบและ retry
รองรับการเทรดแบบ High-Frequency และ Recovery Strategies

เชื่อมต่อไปยัง:
- mt5_integration/mt5_connector.py (การเชื่อมต่อ MT5)
- config/trading_params.py (พารามิเตอร์การเทรด)
- utilities/professional_logger.py (logging)
- utilities/error_handler.py (จัดการข้อผิดพลาด)
- position_management/position_tracker.py (ติดตาม positions)
"""

import MetaTrader5 as mt5
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

from mt5_integration.mt5_connector import get_mt5_connector, ensure_mt5_connection
from config.trading_params import get_trading_parameters
from config.settings import get_system_settings
from utilities.professional_logger import setup_trading_logger
from utilities.error_handler import (
    handle_trading_errors, OrderExecutionError, report_error, 
    ErrorCategory, ErrorSeverity
)

class OrderType(Enum):
    """ประเภทของออร์เดอร์"""
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"

class OrderStatus(Enum):
    """สถานะของออร์เดอร์"""
    PENDING = "PENDING"
    SENT = "SENT"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    PARTIAL_FILLED = "PARTIAL_FILLED"
    ERROR = "ERROR"

@dataclass
class OrderRequest:
    """คำขอส่งออร์เดอร์"""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = "XAUUSD"
    order_type: OrderType = OrderType.BUY
    volume: float = 0.01
    price: Optional[float] = None          # ราคา (สำหรับ limit/stop orders)
    sl: Optional[float] = None             # Stop Loss (ห้ามใช้ตาม requirement)
    tp: Optional[float] = None             # Take Profit (ห้ามใช้ตาม requirement)
    deviation: int = 10                    # Slippage tolerance (points)
    magic_number: int = 123456             # Magic number สำหรับระบุออร์เดอร์
    comment: str = "IntelligentGold"       # Comment
    type_time: int = mt5.ORDER_TIME_GTC    # Order time type
    type_filling: int = mt5.ORDER_FILLING_IOC  # Order filling type
    
    # ข้อมูลเพิ่มเติม
    strategy_name: str = ""                # ชื่อกลยุทธ์
    recovery_level: int = 0                # ระดับ recovery (0 = entry แรก)
    parent_order_id: Optional[str] = None  # ID ของ parent order
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """ตรวจสอบข้อมูลหลังสร้าง"""
        # ตรวจสอบห้ามใช้ SL/TP ตาม requirement
        if self.sl is not None:
            raise ValueError("❌ ห้ามใช้ Stop Loss! ใช้ Recovery System เท่านั้น")
        if self.tp is not None:
            raise ValueError("❌ ห้ามใช้ Take Profit! ใช้ Smart Position Management เท่านั้น")

@dataclass
class OrderResult:
    """ผลการส่งออร์เดอร์"""
    order_id: str
    mt5_order: Optional[int] = None        # MT5 order ticket
    mt5_position: Optional[int] = None     # MT5 position ticket
    status: OrderStatus = OrderStatus.PENDING
    price_executed: Optional[float] = None # ราคาที่ execute จริง
    volume_executed: float = 0.0           # Volume ที่ execute จริง
    execution_time: Optional[datetime] = None
    error_code: Optional[int] = None
    error_description: str = ""
    slippage: float = 0.0                  # Slippage ที่เกิดขึ้น (points)
    commission: float = 0.0                # ค่าคอมมิชชั่น
    swap: float = 0.0                      # ค่า swap
    profit: float = 0.0                    # กำไร/ขาดทุนปัจจุบัน
    
    # เวลาประมวลผล
    processing_time_ms: float = 0.0        # เวลาที่ใช้ในการส่งออร์เดอร์
    network_latency_ms: float = 0.0        # Latency ของเครือข่าย

class OrderExecutor:
    """
    เครื่องมือส่งออร์เดอร์หลัก
    รองรับการส่งออร์เดอร์แบบ High-Frequency และจัดการข้อผิดพลาด
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # ติดตามออร์เดอร์
        self.pending_orders: Dict[str, OrderRequest] = {}
        self.completed_orders: Dict[str, OrderResult] = {}
        self.order_history: List[OrderResult] = []
        
        # Threading
        self.execution_lock = threading.Lock()
        self.order_queue = []
        self.queue_processor_active = False
        
        # สถิติ
        self.total_orders_sent = 0
        self.successful_orders = 0
        self.failed_orders = 0
        self.total_execution_time_ms = 0.0
        
        # เริ่มต้น queue processor
        self._start_queue_processor()
        
        self.logger.info("📈 เริ่มต้น Order Executor")
        
    @handle_trading_errors(ErrorCategory.TRADING, ErrorSeverity.HIGH)
    def send_market_order(self, symbol: str, order_type: OrderType, 
                         volume: float, magic_number: int = 123456,
                         comment: str = "IntelligentGold", 
                         strategy_name: str = "",
                         recovery_level: int = 0) -> OrderResult:
        """
        ส่งออร์เดอร์ Market แบบทันที
        """
        start_time = time.time()
        
        # สร้าง OrderRequest
        order_request = OrderRequest(
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            magic_number=magic_number,
            comment=comment,
            strategy_name=strategy_name,
            recovery_level=recovery_level
        )
        
        # ตรวจสอบการเชื่อมต่อ
        if not ensure_mt5_connection():
            return self._create_error_result(
                order_request, "ไม่สามารถเชื่อมต่อ MT5 ได้"
            )
        
        with self.execution_lock:
            try:
                # เพิ่มเข้า pending orders
                self.pending_orders[order_request.order_id] = order_request
                
                # Log การส่งออร์เดอร์
                self.logger.info(
                    f"📊 ส่งออร์เดอร์ {order_type.value}: {volume} lots {symbol} "
                    f"Strategy: {strategy_name} Level: {recovery_level}"
                )
                
                # เตรียมข้อมูลออร์เดอร์สำหรับ MT5
                mt5_order_type = self._convert_order_type_to_mt5(order_type)
                
                # ดึงราคาปัจจุบัน
                tick = mt5.symbol_info_tick(symbol)
                if tick is None:
                    return self._create_error_result(
                        order_request, f"ไม่สามารถดึงราคา {symbol} ได้"
                    )
                
                # กำหนดราคาสำหรับออร์เดอร์
                if order_type in [OrderType.BUY]:
                    price = tick.ask
                elif order_type in [OrderType.SELL]:
                    price = tick.bid
                else:
                    return self._create_error_result(
                        order_request, f"ประเภทออร์เดอร์ไม่รองรับ: {order_type}"
                    )
                
                # สร้าง trade request
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": volume,
                    "type": mt5_order_type,
                    "price": price,
                    "deviation": order_request.deviation,
                    "magic": magic_number,
                    "comment": comment,
                    "type_time": order_request.type_time,
                    "type_filling": order_request.type_filling,
                }
                
                # ส่งออร์เดอร์
                result = mt5.order_send(request)
                
                if result is None:
                    return self._create_error_result(
                        order_request, "MT5 order_send คืนค่า None"
                    )
                
                # ประมวลผลลัพธ์
                processing_time = (time.time() - start_time) * 1000
                order_result = self._process_order_result(
                    order_request, result, processing_time
                )
                
                # อัพเดทสถิติ
                self.total_orders_sent += 1
                self.total_execution_time_ms += processing_time
                
                if order_result.status == OrderStatus.FILLED:
                    self.successful_orders += 1
                    self.logger.info(
                        f"✅ ออร์เดอร์สำเร็จ: Ticket {order_result.mt5_order} "
                        f"Price: {order_result.price_executed} "
                        f"Time: {processing_time:.2f}ms"
                    )
                else:
                    self.failed_orders += 1
                    self.logger.error(
                        f"❌ ออร์เดอร์ไม่สำเร็จ: {order_result.error_description} "
                        f"Code: {order_result.error_code}"
                    )
                
                # ลบออกจาก pending orders
                self.pending_orders.pop(order_request.order_id, None)
                
                # เพิ่มเข้า completed orders
                self.completed_orders[order_request.order_id] = order_result
                self.order_history.append(order_result)
                
                return order_result
                
            except Exception as e:
                self.logger.error(f"❌ Exception ในการส่งออร์เดอร์: {e}")
                return self._create_error_result(order_request, str(e))
    
    @handle_trading_errors(ErrorCategory.TRADING, ErrorSeverity.MEDIUM)
    def send_pending_order(self, symbol: str, order_type: OrderType,
                          volume: float, price: float,
                          magic_number: int = 123456,
                          comment: str = "IntelligentGold",
                          strategy_name: str = "",
                          recovery_level: int = 0) -> OrderResult:
        """
        ส่งออร์เดอร์ Pending (Limit/Stop)
        """
        start_time = time.time()
        
        # สร้าง OrderRequest
        order_request = OrderRequest(
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            price=price,
            magic_number=magic_number,
            comment=comment,
            strategy_name=strategy_name,
            recovery_level=recovery_level
        )
        
        # ตรวจสอบการเชื่อมต่อ
        if not ensure_mt5_connection():
            return self._create_error_result(
                order_request, "ไม่สามารถเชื่อมต่อ MT5 ได้"
            )
        
        with self.execution_lock:
            try:
                # เพิ่มเข้า pending orders
                self.pending_orders[order_request.order_id] = order_request
                
                # Log การส่งออร์เดอร์
                self.logger.info(
                    f"📊 ส่งออร์เดอร์ Pending {order_type.value}: {volume} lots {symbol} "
                    f"@ {price} Strategy: {strategy_name}"
                )
                
                # เตรียมข้อมูลออร์เดอร์สำหรับ MT5
                mt5_order_type = self._convert_order_type_to_mt5(order_type)
                
                # สร้าง trade request
                request = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": symbol,
                    "volume": volume,
                    "type": mt5_order_type,
                    "price": price,
                    "magic": magic_number,
                    "comment": comment,
                    "type_time": order_request.type_time,
                    "type_filling": order_request.type_filling,
                }
                
                # ส่งออร์เดอร์
                result = mt5.order_send(request)
                
                if result is None:
                    return self._create_error_result(
                        order_request, "MT5 order_send คืนค่า None"
                    )
                
                # ประมวลผลลัพธ์
                processing_time = (time.time() - start_time) * 1000
                order_result = self._process_order_result(
                    order_request, result, processing_time
                )
                
                # อัพเดทสถิติ
                self.total_orders_sent += 1
                self.total_execution_time_ms += processing_time
                
                # ลบออกจาก pending orders
                self.pending_orders.pop(order_request.order_id, None)
                
                # เพิ่มเข้า completed orders
                self.completed_orders[order_request.order_id] = order_result
                self.order_history.append(order_result)
                
                return order_result
                
            except Exception as e:
                self.logger.error(f"❌ Exception ในการส่งออร์เดอร์ Pending: {e}")
                return self._create_error_result(order_request, str(e))
    
    @handle_trading_errors(ErrorCategory.TRADING, ErrorSeverity.MEDIUM)
    def close_position(self, position_ticket: int, volume: Optional[float] = None,
                      comment: str = "IntelligentGold_Close") -> OrderResult:
        """
        ปิด Position
        """
        start_time = time.time()
        
        # ตรวจสอบการเชื่อมต่อ
        if not ensure_mt5_connection():
            return self._create_error_result(
                None, "ไม่สามารถเชื่อมต่อ MT5 ได้"
            )
        
        with self.execution_lock:
            try:
                # ดึงข้อมูล position
                positions = mt5.positions_get(ticket=position_ticket)
                if not positions:
                    return self._create_error_result(
                        None, f"ไม่พบ Position {position_ticket}"
                    )
                
                position = positions[0]
                
                # กำหนด volume ถ้าไม่ได้ระบุ
                if volume is None:
                    volume = position.volume
                
                # กำหนดประเภทออร์เดอร์ปิด
                if position.type == mt5.POSITION_TYPE_BUY:
                    order_type = mt5.ORDER_TYPE_SELL
                    price = mt5.symbol_info_tick(position.symbol).bid
                else:
                    order_type = mt5.ORDER_TYPE_BUY
                    price = mt5.symbol_info_tick(position.symbol).ask
                
                # สร้าง close request
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": position.symbol,
                    "volume": volume,
                    "type": order_type,
                    "position": position_ticket,
                    "price": price,
                    "deviation": 10,
                    "magic": position.magic,
                    "comment": comment,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                
                # ส่งคำสั่งปิด
                result = mt5.order_send(request)
                
                if result is None:
                    return self._create_error_result(
                        None, "MT5 order_send คืนค่า None สำหรับการปิด position"
                    )
                
                # สร้าง OrderRequest สำหรับการปิด
                close_request = OrderRequest(
                    symbol=position.symbol,
                    order_type=OrderType.SELL if position.type == mt5.POSITION_TYPE_BUY else OrderType.BUY,
                    volume=volume,
                    magic_number=position.magic,
                    comment=comment
                )
                
                # ประมวลผลลัพธ์
                processing_time = (time.time() - start_time) * 1000
                order_result = self._process_order_result(
                    close_request, result, processing_time
                )
                
                # Log ผลการปิด position
                if order_result.status == OrderStatus.FILLED:
                    self.logger.info(
                        f"✅ ปิด Position สำเร็จ: {position_ticket} "
                        f"Volume: {volume} Price: {order_result.price_executed}"
                    )
                else:
                    self.logger.error(
                        f"❌ ปิด Position ไม่สำเร็จ: {order_result.error_description}"
                    )
                
                return order_result
                
            except Exception as e:
                self.logger.error(f"❌ Exception ในการปิด Position: {e}")
                return self._create_error_result(None, str(e))
    
    def cancel_pending_order(self, order_ticket: int) -> bool:
        """
        ยกเลิกออร์เดอร์ Pending
        """
        try:
            # ตรวจสอบการเชื่อมต่อ
            if not ensure_mt5_connection():
                return False
            
            # สร้าง cancel request
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": order_ticket,
            }
            
            # ส่งคำสั่งยกเลิก
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.logger.info(f"✅ ยกเลิกออร์เดอร์สำเร็จ: {order_ticket}")
                return True
            else:
                self.logger.error(f"❌ ยกเลิกออร์เดอร์ไม่สำเร็จ: {result.retcode if result else 'None'}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Exception ในการยกเลิกออร์เดอร์: {e}")
            return False
    
    def _convert_order_type_to_mt5(self, order_type: OrderType) -> int:
        """แปลงประเภทออร์เดอร์เป็นรูปแบบ MT5"""
        conversion_map = {
            OrderType.BUY: mt5.ORDER_TYPE_BUY,
            OrderType.SELL: mt5.ORDER_TYPE_SELL,
            OrderType.BUY_LIMIT: mt5.ORDER_TYPE_BUY_LIMIT,
            OrderType.SELL_LIMIT: mt5.ORDER_TYPE_SELL_LIMIT,
            OrderType.BUY_STOP: mt5.ORDER_TYPE_BUY_STOP,
            OrderType.SELL_STOP: mt5.ORDER_TYPE_SELL_STOP,
        }
        return conversion_map.get(order_type, mt5.ORDER_TYPE_BUY)
    
    def _process_order_result(self, order_request: OrderRequest, 
                            mt5_result, processing_time: float) -> OrderResult:
        """ประมวลผลลัพธ์จาก MT5"""
        
        # สร้าง OrderResult พื้นฐาน
        order_result = OrderResult(
            order_id=order_request.order_id,
            processing_time_ms=processing_time,
            execution_time=datetime.now()
        )
        
        if mt5_result.retcode == mt5.TRADE_RETCODE_DONE:
            # ออร์เดอร์สำเร็จ
            order_result.status = OrderStatus.FILLED
            order_result.mt5_order = mt5_result.order
            order_result.price_executed = mt5_result.price
            order_result.volume_executed = mt5_result.volume
            
            # คำนวณ slippage
            if order_request.price:
                order_result.slippage = abs(mt5_result.price - order_request.price)
            
            # ดึงข้อมูล position ถ้ามี
            if hasattr(mt5_result, 'position') and mt5_result.position:
                order_result.mt5_position = mt5_result.position
                
                # ดึงข้อมูล position เพิ่มเติม
                positions = mt5.positions_get(ticket=mt5_result.position)
                if positions:
                    position = positions[0]
                    order_result.commission = position.commission
                    order_result.swap = position.swap
                    order_result.profit = position.profit
        
        else:
            # ออร์เดอร์ไม่สำเร็จ
            order_result.status = OrderStatus.REJECTED
            order_result.error_code = mt5_result.retcode
            order_result.error_description = self._get_error_description(mt5_result.retcode)
        
        return order_result
    
    def _get_error_description(self, error_code: int) -> str:
        """แปลง Error Code เป็นคำอธิบาย"""
        error_descriptions = {
            mt5.TRADE_RETCODE_REQUOTE: "Requote",
            mt5.TRADE_RETCODE_REJECT: "Request rejected",
            mt5.TRADE_RETCODE_CANCEL: "Request canceled by trader",
            mt5.TRADE_RETCODE_PLACED: "Order placed",
            mt5.TRADE_RETCODE_DONE: "Request completed",
            mt5.TRADE_RETCODE_DONE_PARTIAL: "Request completed partially",
            mt5.TRADE_RETCODE_ERROR: "Request processing error",
            mt5.TRADE_RETCODE_TIMEOUT: "Request canceled by timeout",
            mt5.TRADE_RETCODE_INVALID: "Invalid request",
            mt5.TRADE_RETCODE_INVALID_VOLUME: "Invalid volume in the request",
            mt5.TRADE_RETCODE_INVALID_PRICE: "Invalid price in the request",
            mt5.TRADE_RETCODE_INVALID_STOPS: "Invalid stops in the request",
            mt5.TRADE_RETCODE_TRADE_DISABLED: "Trade is disabled",
            mt5.TRADE_RETCODE_MARKET_CLOSED: "Market is closed",
            mt5.TRADE_RETCODE_NO_MONEY: "There is not enough money to complete the request",
            mt5.TRADE_RETCODE_PRICE_CHANGED: "Price changed",
            mt5.TRADE_RETCODE_PRICE_OFF: "Price off",
            mt5.TRADE_RETCODE_INVALID_EXPIRATION: "Invalid request expiration",
            mt5.TRADE_RETCODE_ORDER_CHANGED: "Order state changed",
            mt5.TRADE_RETCODE_TOO_MANY_REQUESTS: "Too many requests",
            mt5.TRADE_RETCODE_NO_CHANGES: "No changes in request",
            mt5.TRADE_RETCODE_SERVER_DISABLES_AT: "Autotrading disabled by server",
            mt5.TRADE_RETCODE_CLIENT_DISABLES_AT: "Autotrading disabled by client",
            mt5.TRADE_RETCODE_LOCKED: "Request locked for processing",
            mt5.TRADE_RETCODE_FROZEN: "Order or position frozen",
            mt5.TRADE_RETCODE_INVALID_FILL: "Invalid order filling type",
            mt5.TRADE_RETCODE_CONNECTION: "No connection with the trade server",
            mt5.TRADE_RETCODE_ONLY_REAL: "Operation is allowed only for live accounts",
            mt5.TRADE_RETCODE_LIMIT_ORDERS: "The number of pending orders has reached the limit",
            mt5.TRADE_RETCODE_LIMIT_VOLUME: "The volume of orders and positions for the symbol has reached the limit",
        }
        
        return error_descriptions.get(error_code, f"Unknown error: {error_code}")
    
    def _create_error_result(self, order_request: Optional[OrderRequest], 
                           error_message: str) -> OrderResult:
        """สร้าง OrderResult สำหรับข้อผิดพลาด"""
        order_id = order_request.order_id if order_request else str(uuid.uuid4())
        
        return OrderResult(
            order_id=order_id,
            status=OrderStatus.ERROR,
            error_description=error_message,
            execution_time=datetime.now()
        )
    
    def _start_queue_processor(self):
        """เริ่ม thread สำหรับประมวลผล order queue"""
        if self.queue_processor_active:
            return
        
        self.queue_processor_active = True
        queue_thread = threading.Thread(
            target=self._process_order_queue,
            daemon=True,
            name="OrderQueueProcessor"
        )
        queue_thread.start()
        self.logger.info("🚀 เริ่มต้น Order Queue Processor")
    
    def _process_order_queue(self):
        """ประมวลผล order queue (สำหรับอนาคต)"""
        while self.queue_processor_active:
            try:
                # TODO: Implement order queue processing for high-frequency trading
                time.sleep(0.1)  # 100ms interval
                
            except Exception as e:
                self.logger.error(f"❌ Error in order queue processor: {e}")
                time.sleep(1.0)
    
    def get_execution_statistics(self) -> Dict:
        """ดึงสถิติการส่งออร์เดอร์"""
        success_rate = (
            (self.successful_orders / self.total_orders_sent * 100) 
            if self.total_orders_sent > 0 else 0
        )
        
        avg_execution_time = (
            (self.total_execution_time_ms / self.total_orders_sent)
            if self.total_orders_sent > 0 else 0
        )
        
        return {
            "total_orders": self.total_orders_sent,
            "successful_orders": self.successful_orders,
            "failed_orders": self.failed_orders,
            "success_rate_percent": round(success_rate, 2),
            "average_execution_time_ms": round(avg_execution_time, 2),
            "pending_orders_count": len(self.pending_orders),
            "completed_orders_count": len(self.completed_orders)
        }
    
    def get_recent_orders(self, limit: int = 10) -> List[OrderResult]:
        """ดึงออร์เดอร์ล่าสุด"""
        return self.order_history[-limit:] if self.order_history else []

# === HELPER FUNCTIONS ===

def quick_buy(symbol: str = "XAUUSD", volume: float = 0.01, 
              strategy: str = "", recovery_level: int = 0) -> OrderResult:
    """ฟังก์ชันช่วยสำหรับซื้อแบบเร็ว"""
    executor = get_order_executor()
    return executor.send_market_order(
        symbol=symbol,
        order_type=OrderType.BUY,
        volume=volume,
        strategy_name=strategy,
        recovery_level=recovery_level
    )

def quick_sell(symbol: str = "XAUUSD", volume: float = 0.01,
               strategy: str = "", recovery_level: int = 0) -> OrderResult:
    """ฟังก์ชันช่วยสำหรับขายแบบเร็ว"""
    executor = get_order_executor()
    return executor.send_market_order(
        symbol=symbol,
        order_type=OrderType.SELL,
        volume=volume,
        strategy_name=strategy,
        recovery_level=recovery_level
    )

def close_all_positions(symbol: str = "XAUUSD") -> List[OrderResult]:
    """ปิด positions ทั้งหมดของ symbol"""
    if not ensure_mt5_connection():
        return []
    
    executor = get_order_executor()
    results = []
    
    # ดึง positions ทั้งหมด
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        return results
    
    # ปิดทีละ position
    for position in positions:
        result = executor.close_position(position.ticket)
        results.append(result)
    
    return results

# === GLOBAL ORDER EXECUTOR INSTANCE ===
_global_order_executor: Optional[OrderExecutor] = None

def get_order_executor() -> OrderExecutor:
    """ดึง Order Executor แบบ Singleton"""
    global _global_order_executor
    if _global_order_executor is None:
        _global_order_executor = OrderExecutor()
    return _global_order_executor