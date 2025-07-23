# position_management/pair_matcher.py - Intelligent Position Pairing System

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum
import itertools
import math

class PairType(Enum):
    """🔗 ประเภทของการจับคู่ Position"""
    HEDGE_PAIR = "hedge_pair"               # คู่ hedge (BUY/SELL)
    RECOVERY_GROUP = "recovery_group"       # กลุ่ม recovery
    PROFIT_PAIR = "profit_pair"             # คู่ที่ทำกำไรร่วมกัน
    CORRELATION_PAIR = "correlation_pair"   # คู่ที่มี correlation
    ARBITRAGE_PAIR = "arbitrage_pair"       # คู่ arbitrage

class PairStatus(Enum):
    """📊 สถานะของคู่ Position"""
    ACTIVE = "active"           # ใช้งานอยู่
    PROFITABLE = "profitable"   # ทำกำไรแล้ว
    RECOVERING = "recovering"   # กำลัง recovery
    FAILED = "failed"           # ล้มเหลว
    CLOSED = "closed"           # ปิดแล้ว

@dataclass
class Position:
    """📈 ข้อมูล Position"""
    ticket: int
    symbol: str
    position_type: str          # "BUY" or "SELL"
    volume: float
    open_price: float
    current_price: float
    unrealized_pnl: float
    open_time: datetime
    magic_number: int = 0
    comment: str = ""
    swap: float = 0.0
    commission: float = 0.0

@dataclass
class PositionPair:
    """🔗 คู่ Position ที่จับคู่แล้ว"""
    pair_id: str
    pair_type: PairType
    positions: List[Position]
    creation_time: datetime
    status: PairStatus
    
    # การคำนวณ
    combined_pnl: float = 0.0
    hedge_ratio: float = 0.0        # อัตราส่วน hedge
    correlation: float = 0.0        # ความสัมพันธ์
    risk_exposure: float = 0.0      # ความเสี่ยงรวม
    
    # เป้าหมาย
    profit_target: float = 0.0
    max_loss_limit: float = 0.0
    
    # สถิติ
    max_profit: float = 0.0
    max_loss: float = 0.0
    duration: timedelta = timedelta()
    
    reasoning: str = ""

@dataclass
class PairDecision:
    """🎯 การตัดสินใจเกี่ยวกับ Position Pairs"""
    should_create_pairs: bool
    recommended_pairs: List[PositionPair]
    should_close_pairs: List[str]  # pair_ids to close
    should_modify_pairs: List[str]  # pair_ids to modify
    reasoning: str
    confidence: float

class PositionPairMatcher:
    """
    🧠 Position Pair Matcher - Intelligent Position Pairing for Recovery
    
    ⚡ หน้าที่หลัก:
    - จับคู่ positions เพื่อลดความเสี่ยง
    - สร้าง hedge pairs อัตโนมัติ
    - จัดกลุ่ม recovery positions
    - ติดตาม correlation ระหว่าง positions
    - ปรับปรุง portfolio balance
    
    🎯 กลยุทธ์:
    - Perfect Hedge: BUY/SELL คู่เดียวกัน
    - Volume Weighted Hedge: ปรับ volume ให้เหมาะสม
    - Time-based Pairing: จับคู่ตามเวลาเปิด position
    - P&L Balance Pairing: จับคู่เพื่อสมดุล P&L
    """
    
    def __init__(self, config: Dict):
        print("🧠 Initializing Position Pair Matcher...")
        
        self.config = config
        
        # Pairing parameters
        self.max_pair_age = config.get('max_pair_age_hours', 24)  # hours
        self.min_correlation = config.get('min_correlation', 0.3)
        self.hedge_tolerance = config.get('hedge_tolerance', 0.1)  # 10%
        self.min_volume_ratio = config.get('min_volume_ratio', 0.5)
        self.max_volume_ratio = config.get('max_volume_ratio', 2.0)
        
        # Risk management
        self.max_pair_exposure = config.get('max_pair_exposure', 1.0)  # lots
        self.target_hedge_ratio = config.get('target_hedge_ratio', 1.0)
        self.profit_target_multiplier = config.get('profit_target_multiplier', 0.5)
        
        # Current state
        self.active_pairs = {}  # pair_id -> PositionPair
        self.pair_counter = 0
        self.unpaired_positions = set()  # ticket numbers
        
        # Statistics
        self.pair_history = []
        self.successful_pairs = 0
        self.failed_pairs = 0
        self.total_pair_profit = 0.0
        
        print("✅ Position Pair Matcher initialized")
        print(f"   - Max Pair Age: {self.max_pair_age}h")
        print(f"   - Min Correlation: {self.min_correlation}")
        print(f"   - Target Hedge Ratio: {self.target_hedge_ratio}")
    
    def analyze_positions(self, positions: List[Dict]) -> List[Position]:
        """
        🔍 วิเคราะห์และแปลง positions เป็น Position objects
        
        Args:
            positions: รายการ positions จาก MT5
            
        Returns:
            รายการ Position objects
        """
        try:
            position_objects = []
            
            for pos in positions:
                try:
                    position = Position(
                        ticket=pos.get('ticket', 0),
                        symbol=pos.get('symbol', 'XAUUSD'),
                        position_type=pos.get('type', 'BUY'),
                        volume=pos.get('volume', 0.01),
                        open_price=pos.get('price_open', 0.0),
                        current_price=pos.get('current_price', 0.0),
                        unrealized_pnl=pos.get('profit', 0.0),
                        open_time=pos.get('time', datetime.now()),
                        magic_number=pos.get('magic', 0),
                        comment=pos.get('comment', ''),
                        swap=pos.get('swap', 0.0),
                        commission=pos.get('commission', 0.0)
                    )
                    
                    position_objects.append(position)
                    
                except Exception as e:
                    print(f"❌ Position conversion error: {e}")
                    continue
            
            print(f"📊 Analyzed {len(position_objects)} positions")
            return position_objects
            
        except Exception as e:
            print(f"❌ Position analysis error: {e}")
            return []
    
    def find_pairing_opportunities(self, positions: List[Position]) -> PairDecision:
        """
        🔍 หาโอกาสในการจับคู่ positions
        
        Args:
            positions: รายการ Position objects
            
        Returns:
            PairDecision object
        """
        try:
            recommended_pairs = []
            
            # อัปเดต unpaired positions
            self._update_unpaired_positions(positions)
            
            # หา hedge pairs
            hedge_pairs = self._find_hedge_pairs(positions)
            recommended_pairs.extend(hedge_pairs)
            
            # หา recovery groups
            recovery_groups = self._find_recovery_groups(positions)
            recommended_pairs.extend(recovery_groups)
            
            # หา profit pairs
            profit_pairs = self._find_profit_pairs(positions)
            recommended_pairs.extend(profit_pairs)
            
            # หา correlation pairs
            correlation_pairs = self._find_correlation_pairs(positions)
            recommended_pairs.extend(correlation_pairs)
            
            # หาคู่ที่ควรปิด
            should_close = self._identify_pairs_to_close(positions)
            
            # หาคู่ที่ควรปรับแต่ง
            should_modify = self._identify_pairs_to_modify(positions)
            
            # ประเมินความเชื่อมั่น
            confidence = self._calculate_pairing_confidence(recommended_pairs, positions)
            
            decision = PairDecision(
                should_create_pairs=len(recommended_pairs) > 0,
                recommended_pairs=recommended_pairs,
                should_close_pairs=should_close,
                should_modify_pairs=should_modify,
                reasoning=self._create_pairing_reasoning(recommended_pairs),
                confidence=confidence
            )
            
            if recommended_pairs:
                print(f"🔗 Pairing Opportunities Found:")
                print(f"   Recommended Pairs: {len(recommended_pairs)}")
                print(f"   Hedge Pairs: {len(hedge_pairs)}")
                print(f"   Recovery Groups: {len(recovery_groups)}")
                print(f"   Profit Pairs: {len(profit_pairs)}")
                print(f"   Confidence: {confidence:.2f}")
            
            return decision
            
        except Exception as e:
            print(f"❌ Pairing opportunity analysis error: {e}")
            return PairDecision(False, [], [], [], "Error occurred", 0.0)
    
    def _update_unpaired_positions(self, positions: List[Position]):
        """อัปเดตรายการ positions ที่ยังไม่ได้จับคู่"""
        try:
            all_tickets = {pos.ticket for pos in positions}
            paired_tickets = set()
            
            # หา tickets ที่จับคู่แล้ว
            for pair in self.active_pairs.values():
                for pos in pair.positions:
                    paired_tickets.add(pos.ticket)
            
            # อัปเดต unpaired positions
            self.unpaired_positions = all_tickets - paired_tickets
            
        except Exception as e:
            print(f"❌ Unpaired positions update error: {e}")
    
    def _find_hedge_pairs(self, positions: List[Position]) -> List[PositionPair]:
        """หา Perfect Hedge Pairs (BUY/SELL คู่เดียวกัน)"""
        try:
            hedge_pairs = []
            unpaired_positions = [pos for pos in positions if pos.ticket in self.unpaired_positions]
            
            # จับคู่ BUY/SELL
            buy_positions = [pos for pos in unpaired_positions if pos.position_type == 'BUY']
            sell_positions = [pos for pos in unpaired_positions if pos.position_type == 'SELL']
            
            for buy_pos in buy_positions:
                for sell_pos in sell_positions:
                    # ตรวจสอบเงื่อนไขการ hedge
                    if self._is_valid_hedge_pair(buy_pos, sell_pos):
                        pair = self._create_hedge_pair(buy_pos, sell_pos)
                        if pair:
                            hedge_pairs.append(pair)
                            # ลบออกจาก unpaired เพื่อไม่ให้จับคู่ซ้ำ
                            self.unpaired_positions.discard(buy_pos.ticket)
                            self.unpaired_positions.discard(sell_pos.ticket)
                            break  # หาคู่ให้ buy_pos แล้ว
            
            return hedge_pairs
            
        except Exception as e:
            print(f"❌ Hedge pairs finding error: {e}")
            return []
    
    def _is_valid_hedge_pair(self, buy_pos: Position, sell_pos: Position) -> bool:
        """ตรวจสอบว่าเป็นคู่ hedge ที่ถูกต้องหรือไม่"""
        try:
            # ตรวจสอบ symbol เดียวกัน
            if buy_pos.symbol != sell_pos.symbol:
                return False
            
            # ตรวจสอบ volume ratio
            volume_ratio = buy_pos.volume / sell_pos.volume
            if volume_ratio < self.min_volume_ratio or volume_ratio > self.max_volume_ratio:
                return False
            
            # ตรวจสอบราคาใกล้เคียงกัน (ไม่ห่างเกิน 5%)
            price_diff = abs(buy_pos.open_price - sell_pos.open_price) / buy_pos.open_price
            if price_diff > 0.05:
                return False
            
            # ตรวจสอบเวลาเปิด position (ไม่ห่างเกิน 1 ชั่วโมง)
            time_diff = abs((buy_pos.open_time - sell_pos.open_time).total_seconds())
            if time_diff > 3600:  # 1 hour
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Hedge pair validation error: {e}")
            return False
    
    def _create_hedge_pair(self, buy_pos: Position, sell_pos: Position) -> Optional[PositionPair]:
        """สร้าง Hedge Pair"""
        try:
            self.pair_counter += 1
            pair_id = f"HEDGE_{self.pair_counter:04d}"
            
            # คำนวณ hedge ratio
            hedge_ratio = buy_pos.volume / sell_pos.volume
            
            # คำนวณ combined P&L
            combined_pnl = buy_pos.unrealized_pnl + sell_pos.unrealized_pnl
            
            # คำนวณ risk exposure (ผลต่างระหว่าง volume)
            risk_exposure = abs(buy_pos.volume - sell_pos.volume)
            
            # คำนวณ profit target
            avg_volume = (buy_pos.volume + sell_pos.volume) / 2
            profit_target = avg_volume * 50 * self.profit_target_multiplier  # 50 USD per 0.01 lot
            
            pair = PositionPair(
                pair_id=pair_id,
                pair_type=PairType.HEDGE_PAIR,
                positions=[buy_pos, sell_pos],
                creation_time=datetime.now(),
                status=PairStatus.ACTIVE,
                combined_pnl=combined_pnl,
                hedge_ratio=hedge_ratio,
                correlation=-1.0,  # Perfect negative correlation for hedge
                risk_exposure=risk_exposure,
                profit_target=profit_target,
                max_loss_limit=avg_volume * 100,  # 100 USD per 0.01 lot
                reasoning=f"Perfect hedge: {buy_pos.volume} BUY vs {sell_pos.volume} SELL"
            )
            
            return pair
            
        except Exception as e:
            print(f"❌ Hedge pair creation error: {e}")
            return None
    
    def _find_recovery_groups(self, positions: List[Position]) -> List[PositionPair]:
        """หากลุ่ม Recovery (positions ขาดทุนที่ควรจัดกลุ่มเข้าด้วยกัน)"""
        try:
            recovery_groups = []
            unpaired_positions = [pos for pos in positions if pos.ticket in self.unpaired_positions]
            
            # หา positions ที่ขาดทุน
            losing_positions = [pos for pos in unpaired_positions if pos.unrealized_pnl < -10]
            
            if len(losing_positions) < 2:
                return recovery_groups
            
            # จัดกลุ่มตามทิศทางเดียวกัน
            buy_losers = [pos for pos in losing_positions if pos.position_type == 'BUY']
            sell_losers = [pos for pos in losing_positions if pos.position_type == 'SELL']
            
            # สร้างกลุ่ม recovery สำหรับ BUY positions
            if len(buy_losers) >= 2:
                recovery_group = self._create_recovery_group(buy_losers, "BUY")
                if recovery_group:
                    recovery_groups.append(recovery_group)
            
            # สร้างกลุ่ม recovery สำหรับ SELL positions
            if len(sell_losers) >= 2:
                recovery_group = self._create_recovery_group(sell_losers, "SELL")
                if recovery_group:
                    recovery_groups.append(recovery_group)
            
            return recovery_groups
            
        except Exception as e:
            print(f"❌ Recovery groups finding error: {e}")
            return []
    
    def _create_recovery_group(self, losing_positions: List[Position], direction: str) -> Optional[PositionPair]:
        """สร้างกลุ่ม Recovery"""
        try:
            if len(losing_positions) < 2:
                return None
            
            self.pair_counter += 1
            pair_id = f"RECOVERY_{direction}_{self.pair_counter:04d}"
            
            # คำนวณสถิติรวม
            total_volume = sum(pos.volume for pos in losing_positions)
            total_pnl = sum(pos.unrealized_pnl for pos in losing_positions)
            avg_price = sum(pos.open_price * pos.volume for pos in losing_positions) / total_volume
            
            # คำนวณ profit target (ต้องการกำไรเท่ากับขาดทุนปัจจุบัน + 20%)
            profit_target = abs(total_pnl) * 1.2
            
            pair = PositionPair(
                pair_id=pair_id,
                pair_type=PairType.RECOVERY_GROUP,
                positions=losing_positions,
                creation_time=datetime.now(),
                status=PairStatus.RECOVERING,
                combined_pnl=total_pnl,
                hedge_ratio=0.0,  # ไม่ใช่ hedge
                correlation=0.8,  # ทิศทางเดียวกัน
                risk_exposure=total_volume,
                profit_target=profit_target,
                max_loss_limit=abs(total_pnl) * 2,
                reasoning=f"Recovery group: {len(losing_positions)} {direction} positions, ${total_pnl:.2f} loss"
            )
            
            # ลบออกจาก unpaired
            for pos in losing_positions:
                self.unpaired_positions.discard(pos.ticket)
            
            return pair
            
        except Exception as e:
            print(f"❌ Recovery group creation error: {e}")
            return None
    
    def _find_profit_pairs(self, positions: List[Position]) -> List[PositionPair]:
        """หาคู่ที่ทำกำไรและควรปิดร่วมกัน"""
        try:
            profit_pairs = []
            unpaired_positions = [pos for pos in positions if pos.ticket in self.unpaired_positions]
            
            # หา positions ที่ทำกำไร
            profitable_positions = [pos for pos in unpaired_positions if pos.unrealized_pnl > 20]
            
            if len(profitable_positions) < 2:
                return profit_pairs
            
            # จับคู่ positions ที่ทำกำไรใกล้เคียงกัน
            for i, pos1 in enumerate(profitable_positions):
                for pos2 in profitable_positions[i+1:]:
                    if self._is_good_profit_pair(pos1, pos2):
                        pair = self._create_profit_pair(pos1, pos2)
                        if pair:
                            profit_pairs.append(pair)
                            self.unpaired_positions.discard(pos1.ticket)
                            self.unpaired_positions.discard(pos2.ticket)
                            break
            
            return profit_pairs
            
        except Exception as e:
            print(f"❌ Profit pairs finding error: {e}")
            return []
    
    def _is_good_profit_pair(self, pos1: Position, pos2: Position) -> bool:
        """ตรวจสอบว่าเป็นคู่ profit ที่ดีหรือไม่"""
        try:
            # ทั้งคู่ต้องทำกำไร
            if pos1.unrealized_pnl <= 0 or pos2.unrealized_pnl <= 0:
                return False
            
            # กำไรต้องใกล้เคียงกัน (ไม่ห่างเกิน 50%)
            profit_ratio = min(pos1.unrealized_pnl, pos2.unrealized_pnl) / max(pos1.unrealized_pnl, pos2.unrealized_pnl)
            if profit_ratio < 0.5:
                return False
            
            # Volume ต้องใกล้เคียงกัน
            volume_ratio = min(pos1.volume, pos2.volume) / max(pos1.volume, pos2.volume)
            if volume_ratio < 0.5:
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Profit pair validation error: {e}")
            return False
    
    def _create_profit_pair(self, pos1: Position, pos2: Position) -> Optional[PositionPair]:
        """สร้าง Profit Pair"""
        try:
            self.pair_counter += 1
            pair_id = f"PROFIT_{self.pair_counter:04d}"
            
            combined_pnl = pos1.unrealized_pnl + pos2.unrealized_pnl
            combined_volume = pos1.volume + pos2.volume
            
            pair = PositionPair(
                pair_id=pair_id,
                pair_type=PairType.PROFIT_PAIR,
                positions=[pos1, pos2],
                creation_time=datetime.now(),
                status=PairStatus.PROFITABLE,
                combined_pnl=combined_pnl,
                hedge_ratio=0.0,
                correlation=0.6,
                risk_exposure=combined_volume,
                profit_target=combined_pnl * 0.8,  # ตั้งเป้า 80% ของกำไรปัจจุบัน
                max_loss_limit=combined_pnl * 0.5,  # ยอมให้กำไรลดลงได้ 50%
                reasoning=f"Profit pair: ${combined_pnl:.2f} combined profit"
            )
            
            return pair
            
        except Exception as e:
            print(f"❌ Profit pair creation error: {e}")
            return None
    
    def _find_correlation_pairs(self, positions: List[Position]) -> List[PositionPair]:
        """หา Correlation Pairs (positions ที่เคลื่อนไหวสัมพันธ์กัน)"""
        try:
            correlation_pairs = []
            unpaired_positions = [pos for pos in positions if pos.ticket in self.unpaired_positions]
            
            if len(unpaired_positions) < 2:
                return correlation_pairs
            
            # หาคู่ที่เปิดใกล้เคียงกันและราคาใกล้เคียงกัน
            for i, pos1 in enumerate(unpaired_positions):
                for pos2 in unpaired_positions[i+1:]:
                    correlation = self._calculate_position_correlation(pos1, pos2)
                    if correlation >= self.min_correlation:
                        pair = self._create_correlation_pair(pos1, pos2, correlation)
                        if pair:
                            correlation_pairs.append(pair)
                            self.unpaired_positions.discard(pos1.ticket)
                            self.unpaired_positions.discard(pos2.ticket)
                            break
            
            return correlation_pairs
            
        except Exception as e:
            print(f"❌ Correlation pairs finding error: {e}")
            return []
    
    def _calculate_position_correlation(self, pos1: Position, pos2: Position) -> float:
        """คำนวณ correlation ระหว่าง 2 positions"""
        try:
            correlation_score = 0.0
            
            # Time correlation (เปิดใกล้เคียงกัน)
            time_diff = abs((pos1.open_time - pos2.open_time).total_seconds())
            if time_diff < 300:  # 5 minutes
                correlation_score += 0.4
            elif time_diff < 900:  # 15 minutes
                correlation_score += 0.2
            
            # Price correlation (ราคาใกล้เคียงกัน)
            price_diff = abs(pos1.open_price - pos2.open_price) / pos1.open_price
            if price_diff < 0.001:  # 0.1%
                correlation_score += 0.3
            elif price_diff < 0.005:  # 0.5%
                correlation_score += 0.2
            
            # Direction correlation
            if pos1.position_type == pos2.position_type:
                correlation_score += 0.2
            else:
                correlation_score -= 0.1  # ทิศทางตรงข้าม
            
            # Volume correlation
            volume_ratio = min(pos1.volume, pos2.volume) / max(pos1.volume, pos2.volume)
            correlation_score += volume_ratio * 0.1
            
            return max(0.0, min(correlation_score, 1.0))
            
        except Exception as e:
            print(f"❌ Correlation calculation error: {e}")
            return 0.0
    
    def _create_correlation_pair(self, pos1: Position, pos2: Position, correlation: float) -> Optional[PositionPair]:
        """สร้าง Correlation Pair"""
        try:
            self.pair_counter += 1
            pair_id = f"CORR_{self.pair_counter:04d}"
            
            combined_pnl = pos1.unrealized_pnl + pos2.unrealized_pnl
            combined_volume = pos1.volume + pos2.volume
            
            pair = PositionPair(
                pair_id=pair_id,
                pair_type=PairType.CORRELATION_PAIR,
                positions=[pos1, pos2],
                creation_time=datetime.now(),
                status=PairStatus.ACTIVE,
                combined_pnl=combined_pnl,
                hedge_ratio=0.0,
                correlation=correlation,
                risk_exposure=combined_volume,
                profit_target=abs(combined_pnl) * 0.5 if combined_pnl < 0 else combined_pnl * 1.2,
                max_loss_limit=abs(combined_pnl) * 1.5 if combined_pnl < 0 else combined_pnl * 0.3,
                reasoning=f"Correlation pair: {correlation:.2f} correlation score"
            )
            
            return pair
            
        except Exception as e:
            print(f"❌ Correlation pair creation error: {e}")
            return None
    
    def _identify_pairs_to_close(self, positions: List[Position]) -> List[str]:
        """ระบุคู่ที่ควรปิด"""
        try:
            pairs_to_close = []
            
            for pair_id, pair in self.active_pairs.items():
                should_close = False
                
                # ปิดถ้าถึง profit target
                if pair.combined_pnl >= pair.profit_target:
                    should_close = True
                
                # ปิดถ้าขาดทุนเกิน limit
                if pair.combined_pnl <= -pair.max_loss_limit:
                    should_close = True
                
                # ปิดถ้าอายุเกิน limit
                age_hours = (datetime.now() - pair.creation_time).total_seconds() / 3600
                if age_hours > self.max_pair_age:
                    should_close = True
                
                if should_close:
                    pairs_to_close.append(pair_id)
            
            return pairs_to_close
            
        except Exception as e:
            print(f"❌ Pairs to close identification error: {e}")
            return []
    
    def _identify_pairs_to_modify(self, positions: List[Position]) -> List[str]:
        """ระบุคู่ที่ควรปรับแต่ง"""
        try:
            pairs_to_modify = []
            
            for pair_id, pair in self.active_pairs.items():
                should_modify = False
                
                # ปรับแต่งถ้า hedge ratio เบี่ยงเบนมาก
                if pair.pair_type == PairType.HEDGE_PAIR:
                    if abs(pair.hedge_ratio - self.target_hedge_ratio) > self.hedge_tolerance:
                        should_modify = True
                
                # ปรับแต่งถ้า risk exposure สูงเกินไป
                if pair.risk_exposure > self.max_pair_exposure:
                    should_modify = True
                
                if should_modify:
                    pairs_to_modify.append(pair_id)
            
            return pairs_to_modify
            
        except Exception as e:
            print(f"❌ Pairs to modify identification error: {e}")
            return []
    
    def _calculate_pairing_confidence(self, recommended_pairs: List[PositionPair], 
                                    positions: List[Position]) -> float:
        """คำนวณความเชื่อมั่นในการจับคู่"""
        try:
            if not recommended_pairs:
                return 0.0
            
            confidence = 0.5  # base confidence
            
            # ปรับตามจำนวนคู่ที่แนะนำ
            pair_count_factor = min(len(recommended_pairs) / 5, 0.3)  # สูงสุด 0.3
            confidence += pair_count_factor
            
            # ปรับตามประเภทของคู่
            hedge_pairs = [p for p in recommended_pairs if p.pair_type == PairType.HEDGE_PAIR]
            if hedge_pairs:
                confidence += 0.2  # hedge pairs มีความเชื่อมั่นสูง
            
            # ปรับตาม correlation average
            correlations = [abs(p.correlation) for p in recommended_pairs if p.correlation != 0]
            if correlations:
                avg_correlation = sum(correlations) / len(correlations)
                confidence += avg_correlation * 0.2
            
            # ปรับตาม P&L balance
            total_pnl = sum(p.combined_pnl for p in recommended_pairs)
            if abs(total_pnl) < 50:  # P&L สมดุล
                confidence += 0.1
            
            return max(0.1, min(confidence, 0.95))
            
        except Exception as e:
            print(f"❌ Pairing confidence calculation error: {e}")
            return 0.5
    
    def _create_pairing_reasoning(self, recommended_pairs: List[PositionPair]) -> str:
        """สร้างเหตุผลการจับคู่"""
        if not recommended_pairs:
            return "No pairing opportunities found"
        
        reasons = []
        
        # นับประเภทของคู่
        pair_types = {}
        for pair in recommended_pairs:
            pair_type = pair.pair_type.value
            pair_types[pair_type] = pair_types.get(pair_type, 0) + 1
        
        for pair_type, count in pair_types.items():
            reasons.append(f"{count} {pair_type}")
        
        # เพิ่มข้อมูล P&L
        total_pnl = sum(p.combined_pnl for p in recommended_pairs)
        reasons.append(f"Combined P&L: ${total_pnl:.2f}")
        
        return " | ".join(reasons)
    
    def execute_pair_creation(self, decision: PairDecision) -> bool:
        """
        ⚡ สร้างคู่ positions ตามการตัดสินใจ
        
        Args:
            decision: PairDecision object
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            if not decision.should_create_pairs:
                return False
            
            print(f"🔗 Creating Position Pairs...")
            
            success_count = 0
            
            for pair in decision.recommended_pairs:
                try:
                    # เพิ่มคู่เข้าสู่ active pairs
                    self.active_pairs[pair.pair_id] = pair
                    
                    # บันทึกประวัติ
                    self._record_pair_creation(pair)
                    
                    success_count += 1
                    print(f"   ✅ Created: {pair.pair_id} ({pair.pair_type.value})")
                    
                except Exception as e:
                    print(f"   ❌ Failed to create pair: {e}")
            
            print(f"✅ Pair creation completed: {success_count}/{len(decision.recommended_pairs)} pairs created")
            
            return success_count > 0
            
        except Exception as e:
            print(f"❌ Pair creation execution error: {e}")
            return False
    
    def execute_pair_closure(self, pair_ids_to_close: List[str], mt5_interface) -> bool:
        """
        ⚡ ปิดคู่ positions ตามรายการ
        
        Args:
            pair_ids_to_close: รายการ pair IDs ที่ต้องปิด
            mt5_interface: MT5 interface object
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            if not pair_ids_to_close:
                return True
            
            print(f"🔄 Closing Position Pairs...")
            
            success_count = 0
            
            for pair_id in pair_ids_to_close:
                try:
                    if pair_id not in self.active_pairs:
                        continue
                    
                    pair = self.active_pairs[pair_id]
                    
                    # ปิด positions ในคู่
                    pair_closed = self._close_pair_positions(pair, mt5_interface)
                    
                    if pair_closed:
                        # อัปเดตสถิติ
                        self._update_pair_statistics(pair)
                        
                        # ลบออกจาก active pairs
                        del self.active_pairs[pair_id]
                        
                        success_count += 1
                        print(f"   ✅ Closed: {pair_id} (P&L: ${pair.combined_pnl:.2f})")
                    else:
                        print(f"   ❌ Failed to close: {pair_id}")
                
                except Exception as e:
                    print(f"   ❌ Error closing pair {pair_id}: {e}")
            
            print(f"✅ Pair closure completed: {success_count}/{len(pair_ids_to_close)} pairs closed")
            
            return success_count > 0
            
        except Exception as e:
            print(f"❌ Pair closure execution error: {e}")
            return False
    
    def _close_pair_positions(self, pair: PositionPair, mt5_interface) -> bool:
        """ปิด positions ในคู่"""
        try:
            success_count = 0
            
            for position in pair.positions:
                try:
                    # สร้าง close request
                    close_request = {
                        'action': 'TRADE_ACTION_DEAL',
                        'position': position.ticket,
                        'symbol': position.symbol,
                        'volume': position.volume,
                        'type': 'ORDER_TYPE_SELL' if position.position_type == 'BUY' else 'ORDER_TYPE_BUY',
                        'deviation': 20,
                        'magic': position.magic_number,
                        'comment': f"Pair Close {pair.pair_id}"
                    }
                    
                    # Execute close
                    result = mt5_interface.close_position(close_request)
                    
                    if result and result.get('retcode') == 10009:
                        success_count += 1
                    
                except Exception as e:
                    print(f"     ❌ Error closing position {position.ticket}: {e}")
            
            return success_count == len(pair.positions)
            
        except Exception as e:
            print(f"❌ Pair positions closure error: {e}")
            return False
    
    def _record_pair_creation(self, pair: PositionPair):
        """บันทึกประวัติการสร้างคู่"""
        try:
            record = {
                'timestamp': datetime.now(),
                'action': 'pair_created',
                'pair_id': pair.pair_id,
                'pair_type': pair.pair_type.value,
                'positions_count': len(pair.positions),
                'combined_pnl': pair.combined_pnl,
                'correlation': pair.correlation
            }
            
            self.pair_history.append(record)
            
            # จำกัดประวัติ
            if len(self.pair_history) > 1000:
                self.pair_history = self.pair_history[-500:]
                
        except Exception as e:
            print(f"❌ Pair creation record error: {e}")
    
    def _update_pair_statistics(self, pair: PositionPair):
        """อัปเดตสถิติคู่"""
        try:
            # อัปเดตสถิติ
            if pair.combined_pnl > 0:
                self.successful_pairs += 1
                self.total_pair_profit += pair.combined_pnl
            else:
                self.failed_pairs += 1
            
            # บันทึกประวัติ
            record = {
                'timestamp': datetime.now(),
                'action': 'pair_closed',
                'pair_id': pair.pair_id,
                'pair_type': pair.pair_type.value,
                'final_pnl': pair.combined_pnl,
                'duration_hours': (datetime.now() - pair.creation_time).total_seconds() / 3600
            }
            
            self.pair_history.append(record)
            
        except Exception as e:
            print(f"❌ Pair statistics update error: {e}")
    
    def update_pairs_status(self, current_positions: List[Position]):
        """
        📊 อัปเดตสถานะของคู่ positions ทั้งหมด
        
        Args:
            current_positions: รายการ positions ปัจจุบัน
        """
        try:
            # สร้าง dictionary สำหรับ lookup
            position_dict = {pos.ticket: pos for pos in current_positions}
            
            pairs_to_remove = []
            
            for pair_id, pair in self.active_pairs.items():
                try:
                    # อัปเดต positions ในคู่
                    updated_positions = []
                    all_positions_exist = True
                    
                    for old_pos in pair.positions:
                        if old_pos.ticket in position_dict:
                            updated_positions.append(position_dict[old_pos.ticket])
                        else:
                            all_positions_exist = False
                            break
                    
                    if not all_positions_exist:
                        # Position บางตัวถูกปิดแล้ว
                        pairs_to_remove.append(pair_id)
                        continue
                    
                    # อัปเดตข้อมูลคู่
                    pair.positions = updated_positions
                    pair.combined_pnl = sum(pos.unrealized_pnl for pos in updated_positions)
                    pair.duration = datetime.now() - pair.creation_time
                    
                    # อัปเดต max profit/loss
                    if pair.combined_pnl > pair.max_profit:
                        pair.max_profit = pair.combined_pnl
                    if pair.combined_pnl < pair.max_loss:
                        pair.max_loss = pair.combined_pnl
                    
                    # อัปเดตสถานะ
                    if pair.combined_pnl >= pair.profit_target:
                        pair.status = PairStatus.PROFITABLE
                    elif pair.combined_pnl <= -pair.max_loss_limit:
                        pair.status = PairStatus.FAILED
                    elif pair.pair_type == PairType.RECOVERY_GROUP and pair.combined_pnl < 0:
                        pair.status = PairStatus.RECOVERING
                    else:
                        pair.status = PairStatus.ACTIVE
                
                except Exception as e:
                    print(f"❌ Error updating pair {pair_id}: {e}")
                    pairs_to_remove.append(pair_id)
            
            # ลบคู่ที่มีปัญหา
            for pair_id in pairs_to_remove:
                if pair_id in self.active_pairs:
                    del self.active_pairs[pair_id]
            
        except Exception as e:
            print(f"❌ Pairs status update error: {e}")
    
    def get_pairs_status(self) -> Dict:
        """ดึงสถานะคู่ positions ทั้งหมด"""
        try:
            if not self.active_pairs:
                return {
                    'active_pairs': 0,
                    'total_combined_pnl': 0.0,
                    'successful_pairs': self.successful_pairs,
                    'failed_pairs': self.failed_pairs
                }
            
            total_pnl = sum(pair.combined_pnl for pair in self.active_pairs.values())
            
            # จำแนกตามประเภท
            pair_types = {}
            for pair in self.active_pairs.values():
                pair_type = pair.pair_type.value
                pair_types[pair_type] = pair_types.get(pair_type, 0) + 1
            
            # จำแนกตามสถานะ
            pair_statuses = {}
            for pair in self.active_pairs.values():
                status = pair.status.value
                pair_statuses[status] = pair_statuses.get(status, 0) + 1
            
            return {
                'active_pairs': len(self.active_pairs),
                'total_combined_pnl': total_pnl,
                'pair_types': pair_types,
                'pair_statuses': pair_statuses,
                'successful_pairs': self.successful_pairs,
                'failed_pairs': self.failed_pairs,
                'total_pair_profit': self.total_pair_profit,
                'unpaired_positions': len(self.unpaired_positions)
            }
            
        except Exception as e:
            print(f"❌ Pairs status error: {e}")
            return {'error': str(e)}
    
    def get_performance_stats(self) -> Dict:
        """ดึงสถิติการทำงาน"""
        try:
            total_pairs = self.successful_pairs + self.failed_pairs
            success_rate = (self.successful_pairs / total_pairs * 100) if total_pairs > 0 else 0
            
            avg_profit = (self.total_pair_profit / self.successful_pairs) if self.successful_pairs > 0 else 0
            
            # วิเคราะห์ประวัติล่าสุด
            recent_pairs = [h for h in self.pair_history if h['action'] == 'pair_closed'][-20:]
            recent_success = len([p for p in recent_pairs if p.get('final_pnl', 0) > 0])
            recent_success_rate = (recent_success / len(recent_pairs) * 100) if recent_pairs else 0
            
            # วิเคราะห์ประเภทคู่ที่สำเร็จ
            successful_types = {}
            for record in self.pair_history:
                if record['action'] == 'pair_closed' and record.get('final_pnl', 0) > 0:
                    pair_type = record['pair_type']
                    successful_types[pair_type] = successful_types.get(pair_type, 0) + 1
            
            return {
                'total_pairs_created': total_pairs,
                'successful_pairs': self.successful_pairs,
                'failed_pairs': self.failed_pairs,
                'success_rate': success_rate,
                'total_profit': self.total_pair_profit,
                'avg_profit_per_pair': avg_profit,
                'recent_success_rate': recent_success_rate,
                'successful_pair_types': successful_types,
                'pair_history_count': len(self.pair_history),
                'last_pair_action': self.pair_history[-1]['timestamp'].strftime("%Y-%m-%d %H:%M:%S") if self.pair_history else "Never"
            }
            
        except Exception as e:
            print(f"❌ Performance stats error: {e}")
            return {'error': str(e)}

def main():
   """Test the Position Pair Matcher"""
   print("🧪 Testing Position Pair Matcher...")
   
   # Sample configuration
   config = {
       'max_pair_age_hours': 24,
       'min_correlation': 0.3,
       'hedge_tolerance': 0.1,
       'min_volume_ratio': 0.5,
       'max_volume_ratio': 2.0,
       'max_pair_exposure': 1.0,
       'target_hedge_ratio': 1.0,
       'profit_target_multiplier': 0.5
   }
   
   # Initialize pair matcher
   pair_matcher = PositionPairMatcher(config)
   
   # Create sample positions
   sample_positions = [
       {
           'ticket': 11111,
           'symbol': 'XAUUSD',
           'type': 'BUY',
           'volume': 0.01,
           'price_open': 2000.0,
           'current_price': 1995.0,
           'profit': -15.0,
           'time': datetime.now() - timedelta(minutes=30),
           'magic': 12345,
           'comment': 'Entry signal'
       },
       {
           'ticket': 11112,
           'symbol': 'XAUUSD',
           'type': 'SELL',
           'volume': 0.01,
           'price_open': 2001.0,
           'current_price': 1995.0,
           'profit': 18.0,
           'time': datetime.now() - timedelta(minutes=25),
           'magic': 12345,
           'comment': 'Counter signal'
       },
       {
           'ticket': 11113,
           'symbol': 'XAUUSD',
           'type': 'BUY',
           'volume': 0.02,
           'price_open': 1990.0,
           'current_price': 1995.0,
           'profit': 25.0,
           'time': datetime.now() - timedelta(hours=2),
           'magic': 12345,
           'comment': 'Trend following'
       }
   ]
   
   # Test position analysis
   position_objects = pair_matcher.analyze_positions(sample_positions)
   print(f"\n📊 Position Analysis:")
   print(f"   Positions analyzed: {len(position_objects)}")
   
   # Test pairing opportunities
   decision = pair_matcher.find_pairing_opportunities(position_objects)
   print(f"\n🔗 Pairing Decision:")
   print(f"   Should create pairs: {decision.should_create_pairs}")
   print(f"   Recommended pairs: {len(decision.recommended_pairs)}")
   print(f"   Confidence: {decision.confidence:.2f}")
   print(f"   Reasoning: {decision.reasoning}")
   
   if decision.recommended_pairs:
       for pair in decision.recommended_pairs:
           print(f"\n   📋 Pair: {pair.pair_id}")
           print(f"      Type: {pair.pair_type.value}")
           print(f"      Positions: {len(pair.positions)}")
           print(f"      Combined P&L: ${pair.combined_pnl:.2f}")
           print(f"      Reasoning: {pair.reasoning}")
   
   # Test pair creation
   if decision.should_create_pairs:
       creation_success = pair_matcher.execute_pair_creation(decision)
       print(f"\n✅ Pair creation result: {creation_success}")
   
   # Test status
   status = pair_matcher.get_pairs_status()
   print(f"\n📈 Pairs Status:")
   for key, value in status.items():
       if isinstance(value, dict):
           print(f"   {key}:")
           for k, v in value.items():
               print(f"     {k}: {v}")
       else:
           print(f"   {key}: {value}")
   
   print("\n✅ Position Pair Matcher test completed")

if __name__ == "__main__":
   main()