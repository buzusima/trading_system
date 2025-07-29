#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKET DATA STREAM - ระบบรับข้อมูลตลาดแบบเรียลไทม์
=============================================
รับและประมวลผลข้อมูลตลาด XAUUSD แบบ streaming
รองรับการอัพเดทราคา tick, candle และ indicators

เชื่อมต่อไปยัง:
- mt5_integration/mt5_connector.py (การเชื่อมต่อ MT5)
- market_intelligence/market_analyzer.py (ส่งข้อมูลให้วิเคราะห์)
- gui_system/components/trading_dashboard.py (แสดงข้อมูลใน GUI)
- utilities/professional_logger.py (logging)
"""

import MetaTrader5 as mt5
import threading
import time
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any , Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    from mt5_integration.mt5_connector import get_mt5_connector, ensure_mt5_connection
    from utilities.professional_logger import setup_market_logger
    from utilities.error_handler import handle_trading_errors, MarketDataError, ErrorCategory, ErrorSeverity
except ImportError as e:
    print(f"Import Error in market_data_stream.py: {e}")

class DataType(Enum):
    """ประเภทข้อมูลตลาด"""
    TICK = "TICK"           # ข้อมูล tick
    CANDLE = "CANDLE"       # ข้อมูล candle
    BOOK = "BOOK"           # Market depth
    NEWS = "NEWS"           # ข่าวสาร

@dataclass
class TickData:
    """ข้อมูล Tick"""
    symbol: str
    time: datetime
    bid: float
    ask: float
    last: float
    volume: int
    spread: float
    
    def __post_init__(self):
        self.spread = self.ask - self.bid

@dataclass
class CandleData:
    """ข้อมูล Candle"""
    symbol: str
    timeframe: str
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    tick_volume: int

@dataclass
class MarketDataSubscription:
    """การสมัครรับข้อมูลตลาด"""
    symbol: str
    data_type: DataType
    timeframe: Optional[str] = None
    callback: Optional[Callable] = None
    active: bool = True

class MarketDataStream:
    """
    ระบบ Stream ข้อมูลตลาดหลัก
    รับและกระจายข้อมูลตลาดแบบเรียลไทม์
    """
    
    def __init__(self):
        self.logger = setup_market_logger()
        
        # การจัดการ subscriptions
        self.subscriptions: Dict[str, MarketDataSubscription] = {}
        self.tick_callbacks: List[Callable] = []
        self.candle_callbacks: List[Callable] = []
        
        # Threading และ Queue
        self.data_queue = queue.Queue(maxsize=1000)
        self.streaming_active = False
        self.stream_thread: Optional[threading.Thread] = None
        self.processor_thread: Optional[threading.Thread] = None
        
        # Cache ข้อมูล
        self.latest_ticks: Dict[str, TickData] = {}
        self.latest_candles: Dict[str, Dict[str, CandleData]] = {}  # symbol -> timeframe -> candle
        
        # สถิติ
        self.tick_count = 0
        self.candle_count = 0
        self.last_tick_time: Optional[datetime] = None
        self.data_latency_ms = 0.0
        
        self.logger.info("📊 เริ่มต้น Market Data Stream")
    
    def start_streaming(self):
        """เริ่มการ stream ข้อมูล"""
        if self.streaming_active:
            return
        
        if not ensure_mt5_connection():
            self.logger.error("❌ ไม่สามารถเชื่อมต่อ MT5 สำหรับ streaming")
            return
        
        self.streaming_active = True
        
        # เริ่ม stream thread
        self.stream_thread = threading.Thread(
            target=self._streaming_loop,
            daemon=True,
            name="MarketDataStream"
        )
        self.stream_thread.start()
        
        # เริ่ม processor thread
        self.processor_thread = threading.Thread(
            target=self._data_processor_loop,
            daemon=True,
            name="DataProcessor"
        )
        self.processor_thread.start()
        
        self.logger.info("🚀 เริ่ม Market Data Streaming")
    
    def stop_streaming(self):
        """หยุดการ stream ข้อมูล"""
        self.streaming_active = False
        
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=5.0)
        
        if self.processor_thread and self.processor_thread.is_alive():
            self.processor_thread.join(timeout=5.0)
        
        self.logger.info("🛑 หยุด Market Data Streaming")
    
    def subscribe_tick_data(self, symbol: str, callback: Optional[Callable] = None) -> str:
        """สมัครรับข้อมูล tick"""
        subscription_id = f"tick_{symbol}_{len(self.subscriptions)}"
        
        subscription = MarketDataSubscription(
            symbol=symbol,
            data_type=DataType.TICK,
            callback=callback
        )
        
        self.subscriptions[subscription_id] = subscription
        
        if callback:
            self.tick_callbacks.append(callback)
        
        self.logger.info(f"📈 สมัครรับข้อมูล Tick: {symbol}")
        return subscription_id
    
    def subscribe_candle_data(self, symbol: str, timeframe: str, 
                            callback: Optional[Callable] = None) -> str:
        """สมัครรับข้อมูล candle"""
        subscription_id = f"candle_{symbol}_{timeframe}_{len(self.subscriptions)}"
        
        subscription = MarketDataSubscription(
            symbol=symbol,
            data_type=DataType.CANDLE,
            timeframe=timeframe,
            callback=callback
        )
        
        self.subscriptions[subscription_id] = subscription
        
        if callback:
            self.candle_callbacks.append(callback)
        
        self.logger.info(f"📊 สมัครรับข้อมูล Candle: {symbol} {timeframe}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """ยกเลิกการสมัครรับข้อมูล"""
        if subscription_id in self.subscriptions:
            subscription = self.subscriptions[subscription_id]
            
            # ลบ callback
            if subscription.callback:
                if subscription.data_type == DataType.TICK:
                    if subscription.callback in self.tick_callbacks:
                        self.tick_callbacks.remove(subscription.callback)
                elif subscription.data_type == DataType.CANDLE:
                    if subscription.callback in self.candle_callbacks:
                        self.candle_callbacks.remove(subscription.callback)
            
            # ลบ subscription
            del self.subscriptions[subscription_id]
            
            self.logger.info(f"❌ ยกเลิกการสมัครรับข้อมูล: {subscription_id}")
            return True
        
        return False
    
    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """ดึงข้อมูล tick ล่าสุด"""
        return self.latest_ticks.get(symbol)
    
    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[CandleData]:
        """ดึงข้อมูล candle ล่าสุด"""
        if symbol in self.latest_candles:
            return self.latest_candles[symbol].get(timeframe)
        return None
    
    def get_current_spread(self, symbol: str) -> Optional[float]:
        """ดึงค่า spread ปัจจุบัน"""
        tick = self.get_latest_tick(symbol)
        return tick.spread if tick else None
    
    @handle_trading_errors(ErrorCategory.MARKET_DATA, ErrorSeverity.MEDIUM)
    def _streaming_loop(self):
        """ลูปหลักสำหรับ streaming ข้อมูล"""
        while self.streaming_active:
            try:
                # ดึงข้อมูล tick สำหรับ symbols ที่สมัคร
                symbols_to_stream = set()
                for subscription in self.subscriptions.values():
                    if subscription.active and subscription.data_type == DataType.TICK:
                        symbols_to_stream.add(subscription.symbol)
                
                # ดึงข้อมูล tick
                for symbol in symbols_to_stream:
                    tick_info = mt5.symbol_info_tick(symbol)
                    if tick_info:
                        tick_data = TickData(
                            symbol=symbol,
                            time=datetime.fromtimestamp(tick_info.time),
                            bid=tick_info.bid,
                            ask=tick_info.ask,
                            last=tick_info.last,
                            volume=tick_info.volume,
                            spread=tick_info.ask - tick_info.bid
                        )
                        
                        # เพิ่มเข้า queue
                        try:
                            self.data_queue.put_nowait(('TICK', tick_data))
                        except queue.Full:
                            self.logger.warning("⚠️ Data queue เต็ม - ข้าม tick")
                
                # ดึงข้อมูล candle
                self._fetch_candle_data()
                
                # รอก่อนรอบถัดไป (100ms for tick data)
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน streaming loop: {e}")
                time.sleep(1.0)
    
    def _fetch_candle_data(self):
        """ดึงข้อมูล candle"""
        for subscription in self.subscriptions.values():
            if (subscription.active and 
                subscription.data_type == DataType.CANDLE and 
                subscription.timeframe):
                
                try:
                    # แปลง timeframe
                    mt5_timeframe = self._convert_timeframe_to_mt5(subscription.timeframe)
                    
                    # ดึงข้อมูล candle ล่าสุด
                    rates = mt5.copy_rates_from_pos(subscription.symbol, mt5_timeframe, 0, 1)
                    
                    if rates is not None and len(rates) > 0:
                        rate = rates[0]
                        
                        candle_data = CandleData(
                            symbol=subscription.symbol,
                            timeframe=subscription.timeframe,
                            time=datetime.fromtimestamp(rate['time']),
                            open=rate['open'],
                            high=rate['high'],
                            low=rate['low'],
                            close=rate['close'],
                            volume=rate['real_volume'],
                            tick_volume=rate['tick_volume']
                        )
                        
                        # ตรวจสอบว่าเป็น candle ใหม่หรือไม่
                        current_candle = self.get_latest_candle(
                            subscription.symbol, 
                            subscription.timeframe
                        )
                        
                        if (not current_candle or 
                            candle_data.time > current_candle.time):
                            
                            # เพิ่มเข้า queue
                            try:
                                self.data_queue.put_nowait(('CANDLE', candle_data))
                            except queue.Full:
                                self.logger.warning("⚠️ Data queue เต็ม - ข้าม candle")
                
                except Exception as e:
                    self.logger.warning(f"⚠️ ข้อผิดพลาดในการดึง candle {subscription.symbol}: {e}")
    
    def _data_processor_loop(self):
        """ลูปประมวลผลข้อมูล"""
        while self.streaming_active:
            try:
                # ดึงข้อมูลจาก queue
                try:
                    data_type, data = self.data_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # ประมวลผลตามประเภทข้อมูล
                if data_type == 'TICK':
                    self._process_tick_data(data)
                elif data_type == 'CANDLE':
                    self._process_candle_data(data)
                
                # Mark task as done
                self.data_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน data processor: {e}")
                time.sleep(0.1)
    
    def _process_tick_data(self, tick_data: TickData):
        """ประมวลผลข้อมูล tick"""
        
        # อัพเดท cache
        self.latest_ticks[tick_data.symbol] = tick_data
        
        # อัพเดทสถิติ
        self.tick_count += 1
        self.last_tick_time = tick_data.time
        
        # คำนวณ latency
        now = datetime.now()
        latency = (now - tick_data.time).total_seconds() * 1000
        self.data_latency_ms = latency
        
        # เรียก callbacks
        for callback in self.tick_callbacks:
            try:
                callback(tick_data)
            except Exception as e:
                self.logger.warning(f"⚠️ ข้อผิดพลาดใน tick callback: {e}")
        
        # Log ข้อมูลสำคัญ (ทุก 100 ticks)
        if self.tick_count % 100 == 0:
            self.logger.debug(
                f"📊 Tick {tick_data.symbol}: {tick_data.bid:.5f}/{tick_data.ask:.5f} "
                f"Spread: {tick_data.spread*10000:.1f} pips | Count: {self.tick_count}"
            )
    
    def _process_candle_data(self, candle_data: CandleData):
        """ประมวลผลข้อมูล candle"""
        
        # อัพเดท cache
        if candle_data.symbol not in self.latest_candles:
            self.latest_candles[candle_data.symbol] = {}
        
        self.latest_candles[candle_data.symbol][candle_data.timeframe] = candle_data
        
        # อัพเดทสถิติ
        self.candle_count += 1
        
        # เรียก callbacks
        for callback in self.candle_callbacks:
            try:
                callback(candle_data)
            except Exception as e:
                self.logger.warning(f"⚠️ ข้อผิดพลาดใน candle callback: {e}")
        
        # Log candle ใหม่
        self.logger.debug(
            f"🕯️ New {candle_data.timeframe} Candle {candle_data.symbol}: "
            f"O:{candle_data.open:.2f} H:{candle_data.high:.2f} "
            f"L:{candle_data.low:.2f} C:{candle_data.close:.2f}"
        )
    
    def _convert_timeframe_to_mt5(self, timeframe: str) -> int:
        """แปลงไทม์เฟรมเป็นรูปแบบ MT5"""
        timeframe_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1
        }
        return timeframe_map.get(timeframe, mt5.TIMEFRAME_M1)
    
    def get_streaming_statistics(self) -> Dict:
        """ดึงสถิติการ streaming"""
        return {
            "streaming_active": self.streaming_active,
            "total_subscriptions": len(self.subscriptions),
            "tick_count": self.tick_count,
            "candle_count": self.candle_count,
            "queue_size": self.data_queue.qsize(),
            "data_latency_ms": round(self.data_latency_ms, 2),
            "last_tick_time": self.last_tick_time.isoformat() if self.last_tick_time else None,
            "symbols_streaming": list(set(s.symbol for s in self.subscriptions.values()))
        }
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """ดึงข้อมูลพื้นฐานของ symbol"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info:
                return {
                    "name": symbol_info.name,
                    "description": symbol_info.description,
                    "currency_base": symbol_info.currency_base,
                    "currency_profit": symbol_info.currency_profit,
                    "currency_margin": symbol_info.currency_margin,
                    "digits": symbol_info.digits,
                    "point": symbol_info.point,
                    "spread": symbol_info.spread,
                    "contract_size": symbol_info.trade_contract_size,
                    "volume_min": symbol_info.volume_min,
                    "volume_max": symbol_info.volume_max,
                    "volume_step": symbol_info.volume_step,
                    "margin_initial": symbol_info.margin_initial,
                    "trade_allowed": symbol_info.visible
                }
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล symbol {symbol}: {e}")
        
        return None

# === HELPER FUNCTIONS ===

def start_market_data_streaming():
    """เริ่มการ stream ข้อมูลตลาด"""
    stream = get_market_data_stream()
    stream.start_streaming()

def stop_market_data_streaming():
    """หยุดการ stream ข้อมูลตลาด"""
    stream = get_market_data_stream()
    stream.stop_streaming()

def subscribe_xauusd_data(tick_callback: Optional[Callable] = None,
                         candle_callback: Optional[Callable] = None) -> List[str]:
    """สมัครรับข้อมูล XAUUSD แบบครบชุด"""
    stream = get_market_data_stream()
    subscription_ids = []
    
    # สมัครรับ tick data
    if tick_callback:
        tick_id = stream.subscribe_tick_data("XAUUSD", tick_callback)
        subscription_ids.append(tick_id)
    
    # สมัครรับ candle data หลายไทม์เฟรม
    timeframes = ["M1", "M5", "M15", "H1"]
    for tf in timeframes:
        if candle_callback:
            candle_id = stream.subscribe_candle_data("XAUUSD", tf, candle_callback)
            subscription_ids.append(candle_id)
    
    return subscription_ids

def get_current_xauusd_price() -> Optional[Tuple[float, float, float]]:
    """ดึงราคา XAUUSD ปัจจุบัน (bid, ask, spread)"""
    stream = get_market_data_stream()
    tick = stream.get_latest_tick("XAUUSD")
    
    if tick:
        return tick.bid, tick.ask, tick.spread
    return None

# === GLOBAL INSTANCE ===
_global_market_data_stream: Optional[MarketDataStream] = None

def get_market_data_stream() -> MarketDataStream:
    """ดึง Market Data Stream แบบ Singleton"""
    global _global_market_data_stream
    if _global_market_data_stream is None:
        _global_market_data_stream = MarketDataStream()
    return _global_market_data_stream