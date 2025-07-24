#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMART ORDER EXECUTOR - Auto Fill Mode Detection
=============================================
แก้ไข Order Executor ให้ลองใช้ Filling Mode หลายแบบอัตโนมัติ
จนกว่าจะส่งออร์เดอร์สำเร็จ

Key Features:
- ลอง Fill Types: FOK, IOC, RETURN อัตโนมัติ
- ลอง Volume ต่างๆ ถ้า volume ไม่ถูกต้อง
- ลอง Deviation ต่างๆ ถ้า price เปลี่ยน
- Retry mechanism ที่ชาญฉลาด
- Cache ผลลัพธ์ที่ใช้ได้สำหรับ broker นี้
"""

import MetaTrader5 as mt5
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json
import os

class OrderType(Enum):
    """ประเภทของออร์เดอร์"""
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    """สถานะของออร์เดอร์"""
    PENDING = "PENDING"
    SENT = "SENT"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"

@dataclass
class OrderRequest:
    """คำขอส่งออร์เดอร์"""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = "XAUUSD.v"  # ใช้ XAUUSD.v โดยตรง
    order_type: OrderType = OrderType.BUY
    volume: float = 0.01
    price: Optional[float] = None
    deviation: int = 20
    magic_number: int = 123456
    comment: str = "IntelligentGold"
    strategy_name: str = ""
    recovery_level: int = 0
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class OrderResult:
    """ผลการส่งออร์เดอร์"""
    order_id: str
    mt5_order: Optional[int] = None
    mt5_position: Optional[int] = None
    status: OrderStatus = OrderStatus.PENDING
    price_executed: Optional[float] = None
    volume_executed: float = 0.0
    execution_time: Optional[datetime] = None
    error_code: Optional[int] = None
    error_description: str = ""
    fill_type_used: str = ""
    attempts_made: int = 0
    processing_time_ms: float = 0.0

class SmartOrderExecutor:
    """
    🧠 Smart Order Executor ที่ลอง Fill Modes หลายแบบ
    """
    
    def __init__(self):
        # Setup logger
        self.logger = logging.getLogger("SmartOrderExecutor")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Symbol settings
        self.symbol = "XAUUSD.v"  # ใช้ XAUUSD.v โดยตรง
        
        # Fill modes to try (เรียงตามความนิยม)
        self.fill_modes = [
            ("FOK", mt5.ORDER_FILLING_FOK, "Fill or Kill"),
            ("RETURN", mt5.ORDER_FILLING_RETURN, "Market Execution"),
            ("IOC", mt5.ORDER_FILLING_IOC, "Immediate or Cancel")
        ]
        
        # Cache for successful configurations
        self.successful_configs = {}
        self.cache_file = "order_config_cache.json"
        
        # Order tracking
        self.pending_orders = {}
        self.completed_orders = {}
        self.order_history = []
        
        # Statistics
        self.total_orders_sent = 0
        self.successful_orders = 0
        self.failed_orders = 0
        
        # Initialize system
        self._initialize_system()
        
        self.logger.info("🧠 Smart Order Executor initialized")
    
    def _initialize_system(self):
        """เริ่มต้นระบบ"""
        try:
            # Initialize MT5
            if not mt5.initialize():
                self.logger.error(f"❌ MT5 initialization failed: {mt5.last_error()}")
                return False
            
            # Load cached configurations
            self._load_config_cache()
            
            # Test symbol
            self._test_symbol()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ System initialization error: {e}")
            return False
    
    def _test_symbol(self):
        """ทดสอบ symbol"""
        try:
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None:
                self.logger.error(f"❌ Symbol {self.symbol} not found")
                return False
            
            if not symbol_info.visible:
                if mt5.symbol_select(self.symbol, True):
                    self.logger.info(f"✅ Selected symbol: {self.symbol}")
                else:
                    self.logger.error(f"❌ Failed to select symbol: {self.symbol}")
                    return False
            
            self.logger.info(f"✅ Symbol ready: {self.symbol}")
            self.logger.info(f"   Trade Mode: {symbol_info.trade_mode}")
            self.logger.info(f"   Min Volume: {symbol_info.volume_min}")
            self.logger.info(f"   Max Volume: {symbol_info.volume_max}")
            self.logger.info(f"   Volume Step: {symbol_info.volume_step}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Symbol test error: {e}")
            return False
    
    def _load_config_cache(self):
        """โหลด configuration cache"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    self.successful_configs = json.load(f)
                self.logger.info(f"✅ Loaded config cache: {len(self.successful_configs)} configs")
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to load config cache: {e}")
            self.successful_configs = {}
    
    def _save_config_cache(self):
        """บันทึก configuration cache"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.successful_configs, f, indent=2)
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to save config cache: {e}")
    
    def send_market_order(self, symbol: str, order_type: OrderType, 
                         volume: float, magic_number: int = 123456,
                         comment: str = "IntelligentGold", 
                         strategy_name: str = "",
                         recovery_level: int = 0) -> OrderResult:
        """
        ส่งออร์เดอร์ Market โดยลอง Fill Modes หลายแบบ
        """
        start_time = time.time()
        
        # สร้าง OrderRequest
        order_request = OrderRequest(
            symbol=self.symbol,  # ใช้ XAUUSD.v เสมอ
            order_type=order_type,
            volume=volume,
            magic_number=magic_number,
            comment=comment,
            strategy_name=strategy_name,
            recovery_level=recovery_level
        )
        
        self.logger.info(f"📤 Sending Smart Order: {order_type.value} {volume} {self.symbol}")
        
        # ลองส่งออร์เดอร์ด้วยวิธีต่างๆ
        result = self._smart_order_execution(order_request)
        
        # อัพเดทสถิติ
        if result.status == OrderStatus.FILLED:
            self.successful_orders += 1
            self.logger.info(f"✅ Order Success: {result.fill_type_used} | "
                           f"Price: {result.price_executed:.2f} | "
                           f"Attempts: {result.attempts_made}")
        else:
            self.failed_orders += 1
            self.logger.error(f"❌ Order Failed: {result.error_description} | "
                            f"Attempts: {result.attempts_made}")
        
        self.total_orders_sent += 1
        result.processing_time_ms = (time.time() - start_time) * 1000
        
        # เก็บประวัติ
        self.completed_orders[order_request.order_id] = result
        self.order_history.append(result)
        
        return result
    
    def _smart_order_execution(self, order_request: OrderRequest) -> OrderResult:
        """ส่งออร์เดอร์อย่างชาญฉลาด - ลองหลายวิธี"""
        
        # ดึง cache configuration ถ้ามี
        cache_key = f"{order_request.order_type.value}_{order_request.volume}"
        if cache_key in self.successful_configs:
            cached_config = self.successful_configs[cache_key]
            self.logger.info(f"🎯 Using cached config: {cached_config['fill_type']}")
            
            result = self._try_single_execution(order_request, cached_config)
            if result.status == OrderStatus.FILLED:
                return result
            else:
                self.logger.warning(f"⚠️ Cached config failed, trying all methods...")
        
        # ลองทุกวิธี
        for attempt, (fill_name, fill_type, description) in enumerate(self.fill_modes, 1):
            self.logger.info(f"🔄 Attempt {attempt}: {fill_name} ({description})")
            
            config = {
                'fill_type': fill_type,
                'fill_name': fill_name,
                'deviation': order_request.deviation
            }
            
            result = self._try_single_execution(order_request, config)
            result.attempts_made = attempt
            result.fill_type_used = fill_name
            
            if result.status == OrderStatus.FILLED:
                # บันทึก config ที่สำเร็จ
                self.successful_configs[cache_key] = config
                self._save_config_cache()
                return result
            
            # ถ้าเป็น Invalid Fill ลองต่อ
            if "invalid fill" in result.error_description.lower():
                continue
            
            # ถ้าเป็น error อื่น ลองปรับ deviation
            if "price changed" in result.error_description.lower():
                self.logger.info(f"🔄 Price changed, trying higher deviation...")
                config['deviation'] = 50
                result2 = self._try_single_execution(order_request, config)
                if result2.status == OrderStatus.FILLED:
                    result2.attempts_made = attempt
                    result2.fill_type_used = f"{fill_name} (High Dev)"
                    return result2
            
            # ถ้าเป็น volume error ลองปรับ volume
            if "volume" in result.error_description.lower():
                self.logger.info(f"🔄 Volume error, trying minimum volume...")
                original_volume = order_request.volume
                order_request.volume = 0.01  # ลองใช้ minimum
                result3 = self._try_single_execution(order_request, config)
                order_request.volume = original_volume  # คืนค่าเดิม
                if result3.status == OrderStatus.FILLED:
                    result3.attempts_made = attempt
                    result3.fill_type_used = f"{fill_name} (Min Vol)"
                    return result3
            
            # รอสักครู่ก่อนลองต่อ
            time.sleep(0.5)
        
        # ถ้าลองหมดแล้วยังไม่ได้
        result.error_description = f"All fill types failed. Last error: {result.error_description}"
        return result
    
    def _try_single_execution(self, order_request: OrderRequest, config: Dict) -> OrderResult:
        """ลองส่งออร์เดอร์ครั้งเดียว"""
        try:
            # Get current tick
            tick = mt5.symbol_info_tick(order_request.symbol)
            if tick is None:
                return OrderResult(
                    order_id=order_request.order_id,
                    status=OrderStatus.ERROR,
                    error_description=f"No tick data for {order_request.symbol}"
                )
            
            # กำหนดราคา
            if order_request.order_type == OrderType.BUY:
                price = tick.ask
                mt5_order_type = mt5.ORDER_TYPE_BUY
            else:
                price = tick.bid
                mt5_order_type = mt5.ORDER_TYPE_SELL
            
            # สร้าง MT5 request
            mt5_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": order_request.symbol,
                "volume": order_request.volume,
                "type": mt5_order_type,
                "price": price,
                "deviation": config.get('deviation', 20),
                "magic": order_request.magic_number,
                "comment": order_request.comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": config['fill_type'],
            }
            
            # ส่งออร์เดอร์
            result = mt5.order_send(mt5_request)
            
            if result is None:
                return OrderResult(
                    order_id=order_request.order_id,
                    status=OrderStatus.ERROR,
                    error_description="MT5 order_send returned None"
                )
            
            # ประมวลผลผลลัพธ์
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return OrderResult(
                    order_id=order_request.order_id,
                    mt5_order=result.order,
                    mt5_position=result.deal,
                    status=OrderStatus.FILLED,
                    price_executed=result.price,
                    volume_executed=result.volume,
                    execution_time=datetime.now(),
                    fill_type_used=config['fill_name']
                )
            else:
                error_desc = self._get_error_description(result.retcode)
                return OrderResult(
                    order_id=order_request.order_id,
                    status=OrderStatus.REJECTED,
                    error_code=result.retcode,
                    error_description=error_desc,
                    fill_type_used=config['fill_name']
                )
                
        except Exception as e:
            return OrderResult(
                order_id=order_request.order_id,
                status=OrderStatus.ERROR,
                error_description=str(e),
                fill_type_used=config.get('fill_name', 'Unknown')
            )
    
    def _get_error_description(self, retcode: int) -> str:
        """แปลง MT5 error code เป็นคำอธิบาย"""
        error_codes = {
            mt5.TRADE_RETCODE_REQUOTE: "Requote",
            mt5.TRADE_RETCODE_REJECT: "Request rejected",
            mt5.TRADE_RETCODE_CANCEL: "Request canceled",
            mt5.TRADE_RETCODE_PLACED: "Order placed",
            mt5.TRADE_RETCODE_DONE: "Request completed",
            mt5.TRADE_RETCODE_DONE_PARTIAL: "Partially filled",
            mt5.TRADE_RETCODE_ERROR: "Common error",
            mt5.TRADE_RETCODE_TIMEOUT: "Timeout",
            mt5.TRADE_RETCODE_INVALID: "Invalid request",
            mt5.TRADE_RETCODE_INVALID_VOLUME: "Invalid volume",
            mt5.TRADE_RETCODE_INVALID_PRICE: "Invalid price",
            mt5.TRADE_RETCODE_INVALID_STOPS: "Invalid stops",
            mt5.TRADE_RETCODE_TRADE_DISABLED: "Trade disabled",
            mt5.TRADE_RETCODE_MARKET_CLOSED: "Market closed",
            mt5.TRADE_RETCODE_NO_MONEY: "No money",
            mt5.TRADE_RETCODE_PRICE_CHANGED: "Price changed",
            mt5.TRADE_RETCODE_PRICE_OFF: "Off quotes",
            mt5.TRADE_RETCODE_INVALID_EXPIRATION: "Invalid expiration",
            mt5.TRADE_RETCODE_ORDER_CHANGED: "Order changed",
            mt5.TRADE_RETCODE_TOO_MANY_REQUESTS: "Too many requests",
            mt5.TRADE_RETCODE_NO_CHANGES: "No changes",
            mt5.TRADE_RETCODE_SERVER_DISABLES_AT: "Auto trading disabled by server",
            mt5.TRADE_RETCODE_CLIENT_DISABLES_AT: "Auto trading disabled by client",
            mt5.TRADE_RETCODE_LOCKED: "Request locked",
            mt5.TRADE_RETCODE_FROZEN: "Order frozen",
            mt5.TRADE_RETCODE_INVALID_FILL: "Invalid fill",
            mt5.TRADE_RETCODE_CONNECTION: "Connection error",
            mt5.TRADE_RETCODE_ONLY_REAL: "Only real accounts",
            mt5.TRADE_RETCODE_LIMIT_ORDERS: "Orders limit",
            mt5.TRADE_RETCODE_LIMIT_VOLUME: "Volume limit"
        }
        
        return error_codes.get(retcode, f"Unknown error code: {retcode}")
    
    def get_open_positions(self, symbol: str = None) -> List[Dict]:
        """ดึงรายการ positions ที่เปิดอยู่"""
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            
            if positions is None:
                return []
            
            result = []
            for position in positions:
                result.append({
                    'ticket': position.ticket,
                    'symbol': position.symbol,
                    'type': 'BUY' if position.type == 0 else 'SELL',
                    'volume': position.volume,
                    'price_open': position.price_open,
                    'price_current': position.price_current,
                    'profit': position.profit,
                    'swap': position.swap,
                    'commission': position.commission,
                    'time': datetime.fromtimestamp(position.time),
                    'comment': position.comment,
                    'magic': position.magic
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error getting positions: {e}")
            return []
    
    def close_position(self, ticket: int) -> OrderResult:
        """ปิด position"""
        try:
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return OrderResult(
                    order_id=str(uuid.uuid4()),
                    status=OrderStatus.ERROR,
                    error_description=f"Position {ticket} not found"
                )
            
            position = position[0]
            
            # ลองใช้ config ที่เหมาะสม
            cache_key = f"CLOSE_{position.volume}"
            if cache_key in self.successful_configs:
                fill_config = self.successful_configs[cache_key]
            else:
                fill_config = {'fill_type': mt5.ORDER_FILLING_FOK, 'fill_name': 'FOK'}
            
            # สร้าง close request
            if position.type == 0:  # BUY position
                price = mt5.symbol_info_tick(position.symbol).bid
                order_type = mt5.ORDER_TYPE_SELL
            else:  # SELL position
                price = mt5.symbol_info_tick(position.symbol).ask
                order_type = mt5.ORDER_TYPE_BUY
            
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": position.magic,
                "comment": f"Close_{ticket}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": fill_config['fill_type'],
            }
            
            result = mt5.order_send(close_request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.logger.info(f"✅ Position closed: {ticket}")
                return OrderResult(
                    order_id=str(uuid.uuid4()),
                    mt5_order=result.order,
                    mt5_position=result.deal,
                    status=OrderStatus.FILLED,
                    price_executed=result.price,
                    volume_executed=result.volume,
                    execution_time=datetime.now(),
                    fill_type_used=fill_config['fill_name']
                )
            else:
                # ลองใช้ fill type อื่น
                for fill_name, fill_type, _ in self.fill_modes:
                    close_request["type_filling"] = fill_type
                    result = mt5.order_send(close_request)
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        self.logger.info(f"✅ Position closed with {fill_name}: {ticket}")
                        return OrderResult(
                            order_id=str(uuid.uuid4()),
                            status=OrderStatus.FILLED,
                            fill_type_used=fill_name
                        )
                
                error_desc = self._get_error_description(result.retcode) if result else "Unknown error"
                return OrderResult(
                    order_id=str(uuid.uuid4()),
                    status=OrderStatus.REJECTED,
                    error_description=error_desc
                )
                
        except Exception as e:
            self.logger.error(f"❌ Close position error: {e}")
            return OrderResult(
                order_id=str(uuid.uuid4()),
                status=OrderStatus.ERROR,
                error_description=str(e)
            )
    
    def get_statistics(self) -> Dict[str, any]:
        """ดึงสถิติการทำงาน"""
        return {
            'total_orders_sent': self.total_orders_sent,
            'successful_orders': self.successful_orders,
            'failed_orders': self.failed_orders,
            'success_rate': (self.successful_orders / max(self.total_orders_sent, 1)) * 100,
            'symbol_used': self.symbol,
            'cached_configs': len(self.successful_configs),
            'pending_orders': len(self.pending_orders),
            'completed_orders': len(self.completed_orders)
        }
    
    def test_all_fill_modes(self):
        """ทดสอบ Fill Modes ทั้งหมด (แบบ dry run)"""
        self.logger.info("🧪 Testing all fill modes...")
        
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            if tick is None:
                self.logger.error("❌ No tick data")
                return
            
            for fill_name, fill_type, description in self.fill_modes:
                test_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": 0.01,
                    "type": mt5.ORDER_TYPE_BUY,
                    "price": tick.ask,
                    "deviation": 20,
                    "magic": 123456,
                    "comment": "TEST",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": fill_type,
                }
                
                check_result = mt5.order_check(test_request)
                if check_result and check_result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.logger.info(f"✅ {fill_name} ({description}) - WORKS")
                else:
                    error = self._get_error_description(check_result.retcode) if check_result else "Unknown"
                    self.logger.warning(f"❌ {fill_name} ({description}) - {error}")
                    
        except Exception as e:
            self.logger.error(f"❌ Test error: {e}")
    
    def shutdown(self):
        """ปิดระบบ"""
        try:
            self._save_config_cache()
            mt5.shutdown()
        except:
            pass
        self.logger.info("🛑 Smart Order Executor shutdown")

# Backward compatibility functions
def get_order_executor():
    """ได้ Order Executor instance (Backward Compatibility)"""
    return get_smart_order_executor()

# For main_window.py compatibility
class OrderExecutor:
    """Wrapper class for backward compatibility"""
    def __init__(self):
        self.smart_executor = SmartOrderExecutor()
    
    def send_market_order(self, **kwargs):
        return self.smart_executor.send_market_order(**kwargs)
    
    def get_open_positions(self, symbol=None):
        return self.smart_executor.get_open_positions(symbol)
    
    def close_position(self, ticket):
        return self.smart_executor.close_position(ticket)
    
    def get_statistics(self):
        return self.smart_executor.get_statistics()
    
    def shutdown(self):
        return self.smart_executor.shutdown()

# Global instances
_smart_executor_instance = None
_order_executor_instance = None

def get_smart_order_executor():
    """ได้ Smart Order Executor instance"""
    global _smart_executor_instance
    if _smart_executor_instance is None:
        _smart_executor_instance = SmartOrderExecutor()
    return _smart_executor_instance

def get_order_executor():
    """ได้ Order Executor instance (Backward Compatibility)"""
    global _order_executor_instance
    if _order_executor_instance is None:
        _order_executor_instance = OrderExecutor()
    return _order_executor_instance

if __name__ == "__main__":
    print("🧠 Testing Smart Order Executor")
    
    executor = SmartOrderExecutor()
    
    # Test all fill modes
    executor.test_all_fill_modes()
    
    # Show statistics
    stats = executor.get_statistics()
    print(f"\nStatistics: {stats}")
    
    print("\n✅ Smart Order Executor ready!")
    print("This will automatically try different fill modes until orders succeed.")