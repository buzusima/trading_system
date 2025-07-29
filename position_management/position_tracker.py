#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSITION TRACKER - Simple and Working Version
===========================================
ไฟล์ที่แน่ใจว่าจะทำงานได้ - เรียบง่ายและมี compatibility ครบ
"""

import MetaTrader5 as mt5
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

# Simple fallback logger
def setup_component_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

# Simple error decorator
def handle_trading_errors(category, severity):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Error in {func.__name__}: {e}")
                return None
        return wrapper
    return decorator

# Simple connection check
def ensure_mt5_connection():
    try:
        if not mt5.initialize():
            return False
        return True
    except:
        return False

@dataclass
class Position:
    """Position Class - ชื่อที่ต้องการสำหรับ import"""
    ticket: str
    symbol: str = "XAUUSD"
    type: str = "BUY"
    volume: float = 0.01
    open_price: float = 0.0
    current_price: float = 0.0
    profit: float = 0.0
    swap: float = 0.0
    commission: float = 0.0
    time_open: datetime = None
    comment: str = ""
    
    # Recovery fields
    recovery_group: Optional[str] = None
    recovery_level: int = 0
    is_recovery_position: bool = False
    
    def __post_init__(self):
        if self.time_open is None:
            self.time_open = datetime.now()
    
    @property
    def is_open(self) -> bool:
        return True
    
    @property
    def is_losing(self) -> bool:
        return self.profit < -0.01
    
    @property
    def is_profitable(self) -> bool:
        return self.profit > 0.01
    
    @property
    def needs_recovery(self) -> bool:
        return self.profit < -5.0
    
    @property
    def age_minutes(self) -> int:
        if self.time_open:
            return int((datetime.now() - self.time_open).total_seconds() / 60)
        return 0
    
    @property
    def pips_profit(self) -> float:
        if self.open_price == 0:
            return 0.0
        pip_value = 0.1 if 'JPY' in self.symbol else 0.0001
        if self.type == "BUY":
            return (self.current_price - self.open_price) / pip_value
        else:
            return (self.open_price - self.current_price) / pip_value
    
    @property
    def pips(self) -> float:
        return self.pips_profit
    
    @property
    def type_str(self) -> str:
        return self.type
    
    @property
    def time_str(self) -> str:
        if self.time_open:
            return self.time_open.strftime("%H:%M:%S")
        return "--:--:--"
    
    @property
    def status(self) -> str:
        if self.needs_recovery:
            return "NEEDS_RECOVERY"
        elif self.is_recovery_position:
            return f"RECOVERY_L{self.recovery_level}"
        elif self.is_profitable:
            return "PROFITABLE"
        else:
            return "NORMAL"

class EnhancedPositionTracker:
    """Position Tracker ที่ทำงานได้แน่นอน"""
    
    def __init__(self):
        self.logger = setup_component_logger("PositionTracker")
        self.positions: Dict[str, Position] = {}
        self.tracking_active = False
        self.tracking_thread = None
        self.last_update_time = None
        self.tracker_lock = threading.Lock()
        self.update_interval = 2
        
        self.logger.info("Position Tracker initialized")
    
    def start_tracking(self) -> bool:
        if self.tracking_active:
            return True
        
        try:
            if not ensure_mt5_connection():
                self.logger.error("Cannot connect to MT5")
                return False
            
            self.tracking_active = True
            self.tracking_thread = threading.Thread(
                target=self._tracking_loop,
                daemon=True,
                name="PositionTracker"
            )
            self.tracking_thread.start()
            self.logger.info("Position tracking started")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start tracking: {e}")
            return False
    
    def stop_tracking(self):
        self.tracking_active = False
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=5.0)
        self.logger.info("Position tracking stopped")
    
    def _tracking_loop(self):
        while self.tracking_active:
            try:
                self._update_positions_from_mt5()
                self.last_update_time = datetime.now()
                time.sleep(self.update_interval)
            except Exception as e:
                self.logger.error(f"Tracking loop error: {e}")
                time.sleep(5.0)
    
    def _update_positions_from_mt5(self):
        if not ensure_mt5_connection():
            return
        
        try:
            mt5_positions = mt5.positions_get()
            if mt5_positions is None:
                mt5_positions = []
            
            current_tickets = set()
            
            with self.tracker_lock:
                for mt5_pos in mt5_positions:
                    ticket = str(mt5_pos.ticket)
                    current_tickets.add(ticket)
                    
                    # Get current price
                    symbol_info = mt5.symbol_info_tick(mt5_pos.symbol)
                    current_price = 0.0
                    if symbol_info:
                        if mt5_pos.type == mt5.ORDER_TYPE_BUY:
                            current_price = symbol_info.bid
                        else:
                            current_price = symbol_info.ask
                    
                    if ticket in self.positions:
                        # Update existing position
                        pos = self.positions[ticket]
                        pos.current_price = current_price
                        pos.profit = mt5_pos.profit
                        pos.swap = mt5_pos.swap
                        pos.commission = mt5_pos.commission
                    else:
                        # Create new position
                        position = Position(
                            ticket=ticket,
                            symbol=mt5_pos.symbol,
                            type="BUY" if mt5_pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                            volume=mt5_pos.volume,
                            open_price=mt5_pos.price_open,
                            current_price=current_price,
                            profit=mt5_pos.profit,
                            swap=mt5_pos.swap,
                            commission=mt5_pos.commission,
                            time_open=datetime.fromtimestamp(mt5_pos.time),
                            comment=mt5_pos.comment
                        )
                        self.positions[ticket] = position
                        self.logger.info(f"New position: {ticket} {position.type} {position.volume}")
                
                # Remove closed positions
                closed_tickets = set(self.positions.keys()) - current_tickets
                for ticket in closed_tickets:
                    closed_pos = self.positions.pop(ticket)
                    self.logger.info(f"Position closed: {ticket} P&L: ${closed_pos.profit:.2f}")
                
        except Exception as e:
            self.logger.error(f"Update positions error: {e}")
    
    # Core methods that other files need
    def get_all_positions(self) -> List[Position]:
        with self.tracker_lock:
            return list(self.positions.values())
    
    def get_positions_needing_recovery(self) -> List[Position]:
        with self.tracker_lock:
            return [pos for pos in self.positions.values() 
                   if pos.needs_recovery and not pos.is_recovery_position]
    
    def get_position_by_ticket(self, ticket: str) -> Optional[Position]:
        with self.tracker_lock:
            return self.positions.get(ticket)
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        with self.tracker_lock:
            positions = list(self.positions.values())
            if not positions:
                return {
                    'total_positions': 0,
                    'total_profit': 0.0,
                    'total_volume': 0.0,
                    'profitable_positions': 0,
                    'losing_positions': 0,
                    'recovery_positions': 0,
                    'positions_needing_recovery': 0
                }
            
            return {
                'total_positions': len(positions),
                'total_profit': sum(pos.profit for pos in positions),
                'total_volume': sum(pos.volume for pos in positions),
                'profitable_positions': len([p for p in positions if p.is_profitable]),
                'losing_positions': len([p for p in positions if not p.is_profitable]),
                'recovery_positions': len([p for p in positions if p.is_recovery_position]),
                'positions_needing_recovery': len([p for p in positions if p.needs_recovery and not p.is_recovery_position]),
                'last_update': self.last_update_time.isoformat() if self.last_update_time else None
            }

# Singleton
_position_tracker_instance = None

def get_position_tracker() -> EnhancedPositionTracker:
    global _position_tracker_instance
    if _position_tracker_instance is None:
        _position_tracker_instance = EnhancedPositionTracker()
    return _position_tracker_instance

# Additional aliases for compatibility
PositionData = Position
PositionInfo = Position
TradePosition = Position

# Legacy functions
def get_tracker():
    return get_position_tracker()

def create_position_tracker():
    return EnhancedPositionTracker()

# Export everything
__all__ = [
    'Position', 'PositionData', 'PositionInfo', 'TradePosition',
    'EnhancedPositionTracker',
    'get_position_tracker', 'get_tracker', 'create_position_tracker'
]