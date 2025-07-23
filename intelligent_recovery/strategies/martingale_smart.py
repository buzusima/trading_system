# intelligent_recovery/strategies/martingale_smart.py - Smart Martingale Recovery System

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import math

class RecoveryState(Enum):
    """🔄 สถานะการ Recovery"""
    INACTIVE = "inactive"       # ไม่มี position ขาดทุน
    ACTIVE = "active"           # กำลัง recovery
    CRITICAL = "critical"       # ขาดทุนเยอะ ต้องระวัง
    EMERGENCY = "emergency"     # ขาดทุนมาก ต้องหยุดชั่วคราว

class MartingaleType(Enum):
    """📈 ประเภทของ Martingale"""
    CLASSIC = "classic"         # เพิ่ม 2x เสมอ
    PROGRESSIVE = "progressive" # เพิ่มตามขั้นตอน
    ADAPTIVE = "adaptive"       # ปรับตามสภาพตลาด
    FIBONACCI = "fibonacci"     # ใช้ลำดับ Fibonacci

@dataclass
class RecoveryPosition:
    """📊 ข้อมูล Position ที่ต้อง Recovery"""
    ticket: int
    symbol: str
    position_type: str          # "BUY" or "SELL"
    volume: float
    open_price: float
    current_price: float
    unrealized_pnl: float
    open_time: datetime
    recovery_level: int         # ระดับ recovery (0 = original)
    original_volume: float      # volume เดิม
    accumulated_loss: float     # ขาดทุนสะสม

@dataclass
class MartingaleDecision:
    """🎯 คำตัดสินใจ Recovery แบบ Martingale"""
    should_recover: bool
    recovery_type: str          # "BUY" or "SELL"
    recovery_volume: float
    recovery_price: float
    target_profit: float
    max_loss_limit: float
    reasoning: str
    confidence: float
    risk_level: str             # "LOW", "MEDIUM", "HIGH", "CRITICAL"

class SmartMartingaleRecovery:
    """
    🧠 Smart Martingale Recovery System - Advanced Recovery Logic
    
    ⚡ เหมาะสำหรับ:
    - Mean Reversion scenarios (ตลาดไซด์เวย์)
    - Asian Session (ความผันผวนต่ำ)
    - Ranging markets
    
    🎯 กลยุทธ์:
    - เพิ่ม position ในทิศทางเดิม เมื่อราคาไปต่อ
    - ใช้ multiple lot size formulas
    - ปรับตามความผันผวนของตลาด
    - หยุดเมื่อถึงขีดจำกัดความเสี่ยง
    - ใช้ Target Profit แบบ dynamic
    
    ⚠️ ข้อควรระวัง:
    - อันตรายในตลาดเทรนด์แรง
    - ต้องมี capital เพียงพอ
    - ต้องกำหนด max levels
    """
    
    def __init__(self, config: Dict):
        print("🧠 Initializing Smart Martingale Recovery...")
        
        self.config = config
        
        # Martingale parameters
        self.martingale_type = config.get('martingale_type', 'adaptive')
        self.max_recovery_levels = config.get('max_recovery_levels', 5)
        self.base_multiplier = config.get('base_multiplier', 1.8)
        self.max_multiplier = config.get('max_multiplier', 8.0)
        
        # Risk management
        self.max_total_loss = config.get('max_total_loss', 500.0)  # USD
        self.max_position_size = config.get('max_position_size', 2.0)  # lots
        self.recovery_threshold = config.get('recovery_threshold', -20.0)  # USD trigger
        
        # Market condition adjustments
        self.volatility_adjustment = config.get('volatility_adjustment', True)
        self.session_adjustment = config.get('session_adjustment', True)
        self.trend_awareness = config.get('trend_awareness', True)
        
        # Fibonacci sequence for Fibonacci martingale
        self.fibonacci_sequence = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
        
        # Progressive multipliers for different strategies
        self.progressive_multipliers = {
            'conservative': [1.0, 1.5, 2.0, 2.5, 3.0],
            'moderate': [1.0, 1.8, 2.5, 3.5, 5.0],
            'aggressive': [1.0, 2.0, 3.0, 5.0, 8.0]
        }
        
        # Session multipliers
        self.session_multipliers = {
            'asian': 1.2,       # ดีที่สุดสำหรับ martingale
            'london': 0.8,      # ระวังเทรนด์
            'ny': 0.7,          # ระวังเทรนด์
            'overlap': 0.6,     # หลีกเลี่ยง
            'quiet': 1.5        # เงียบ เหมาะมาก
        }
        
        # Current state
        self.recovery_positions = {}  # ticket -> RecoveryPosition
        self.recovery_state = RecoveryState.INACTIVE
        self.total_unrealized_loss = 0.0
        self.max_drawdown_reached = 0.0
        
        # Statistics
        self.recovery_history = []
        self.success_count = 0
        self.failure_count = 0
        
        print("✅ Smart Martingale Recovery initialized")
        print(f"   - Type: {self.martingale_type}")
        print(f"   - Max Levels: {self.max_recovery_levels}")
        print(f"   - Base Multiplier: {self.base_multiplier}")
        print(f"   - Recovery Threshold: ${self.recovery_threshold}")
    
    def analyze_recovery_need(self, positions: List[Dict]) -> bool:
        """
        🔍 วิเคราะห์ว่าต้อง Recovery หรือไม่
        
        Args:
            positions: รายการ positions ปัจจุบัน
            
        Returns:
            True ถ้าต้อง recovery
        """
        try:
            # อัพเดต recovery positions
            self._update_recovery_positions(positions)
            
            # คำนวณขาดทุนรวม
            total_loss = sum(pos.unrealized_pnl for pos in self.recovery_positions.values())
            self.total_unrealized_loss = total_loss
            
            # อัพเดต recovery state
            self._update_recovery_state(total_loss)
            
            # ตรวจสอบเงื่อนไข recovery
            needs_recovery = self._check_recovery_conditions(total_loss)
            
            if needs_recovery:
                print(f"🔄 Recovery needed - Total Loss: ${total_loss:.2f}")
                print(f"   State: {self.recovery_state.value}")
                print(f"   Positions: {len(self.recovery_positions)}")
            
            return needs_recovery
            
        except Exception as e:
            print(f"❌ Recovery analysis error: {e}")
            return False
    
    def _update_recovery_positions(self, positions: List[Dict]):
        """อัพเดตข้อมูล recovery positions"""
        try:
            current_tickets = set()
            
            for pos in positions:
                ticket = pos.get('ticket')
                if not ticket:
                    continue
                
                current_tickets.add(ticket)
                
                # อัพเดตหรือเพิ่ม position ใหม่
                if ticket in self.recovery_positions:
                    # อัพเดต position เดิม
                    recovery_pos = self.recovery_positions[ticket]
                    recovery_pos.current_price = pos.get('current_price', recovery_pos.current_price)
                    recovery_pos.unrealized_pnl = pos.get('profit', 0.0)
                else:
                    # เพิ่ม position ใหม่ (ถ้าขาดทุน)
                    profit = pos.get('profit', 0.0)
                    if profit < 0:  # เฉพาะ position ขาดทุน
                        recovery_pos = RecoveryPosition(
                            ticket=ticket,
                            symbol=pos.get('symbol', 'XAUUSD'),
                            position_type=pos.get('type', 'BUY'),
                            volume=pos.get('volume', 0.01),
                            open_price=pos.get('price_open', 0.0),
                            current_price=pos.get('current_price', 0.0),
                            unrealized_pnl=profit,
                            open_time=pos.get('time', datetime.now()),
                            recovery_level=0,
                            original_volume=pos.get('volume', 0.01),
                            accumulated_loss=profit
                        )
                        self.recovery_positions[ticket] = recovery_pos
            
            # ลบ positions ที่ปิดแล้ว
            closed_tickets = set(self.recovery_positions.keys()) - current_tickets
            for ticket in closed_tickets:
                del self.recovery_positions[ticket]
                
        except Exception as e:
            print(f"❌ Recovery positions update error: {e}")
    
    def _update_recovery_state(self, total_loss: float):
        """อัพเดตสถานะ recovery"""
        try:
            if total_loss >= -50:
                self.recovery_state = RecoveryState.INACTIVE
            elif total_loss >= -200:
                self.recovery_state = RecoveryState.ACTIVE
            elif total_loss >= -400:
                self.recovery_state = RecoveryState.CRITICAL
            else:
                self.recovery_state = RecoveryState.EMERGENCY
                
            # อัพเดต max drawdown
            if abs(total_loss) > self.max_drawdown_reached:
                self.max_drawdown_reached = abs(total_loss)
                
        except Exception as e:
            print(f"❌ Recovery state update error: {e}")
    
    def _check_recovery_conditions(self, total_loss: float) -> bool:
        """ตรวจสอบเงื่อนไขการ recovery"""
        try:
            # เงื่อนไขพื้นฐาน
            if total_loss > self.recovery_threshold:
                return False  # ขาดทุนไม่ถึงเกณฑ์
            
            if self.recovery_state == RecoveryState.EMERGENCY:
                return False  # หยุด recovery ในสถานะฉุกเฉิน
            
            if abs(total_loss) >= self.max_total_loss:
                return False  # เกินขีดจำกัดขาดทุน
            
            # ตรวจสอบจำนวน recovery levels
            max_level = max((pos.recovery_level for pos in self.recovery_positions.values()), default=0)
            if max_level >= self.max_recovery_levels:
                return False  # เกิน max recovery levels
            
            return True
            
        except Exception as e:
            print(f"❌ Recovery condition check error: {e}")
            return False
    
    def calculate_recovery_decision(self, market_data: pd.DataFrame, 
                                  current_session: str = 'asian') -> Optional[MartingaleDecision]:
        """
        🧮 คำนวณการตัดสินใจ Recovery แบบ Martingale
        
        Args:
            market_data: ข้อมูลตลาดล่าสุด
            current_session: เซสชั่นปัจจุบัน
            
        Returns:
            MartingaleDecision หรือ None
        """
        try:
            if not self.recovery_positions:
                return None
            
            # หา position ที่ขาดทุนมากที่สุด
            worst_position = min(self.recovery_positions.values(), 
                                key=lambda x: x.unrealized_pnl)
            
            if worst_position.unrealized_pnl > self.recovery_threshold:
                return None  # ไม่ต้อง recovery
            
            # คำนวณ recovery volume
            recovery_volume = self._calculate_recovery_volume(
                worst_position, market_data, current_session
            )
            
            if recovery_volume <= 0 or recovery_volume > self.max_position_size:
                return None  # ปริมาณไม่เหมาะสม
            
            # กำหนดทิศทาง recovery (ทิศทางเดียวกัน)
            recovery_type = worst_position.position_type
            
            # คำนวณราคาเป้าหมาย
            current_price = market_data['close'].iloc[-1]
            recovery_price = current_price
            
            # คำนวณ target profit
            target_profit = self._calculate_target_profit(worst_position, recovery_volume)
            
            # คำนวณ max loss limit
            max_loss_limit = self._calculate_max_loss_limit(worst_position)
            
            # ประเมินความเสี่ยง
            risk_level = self._assess_risk_level(worst_position, recovery_volume, market_data)
            
            # คำนวณ confidence
            confidence = self._calculate_recovery_confidence(
                worst_position, market_data, current_session
            )
            
            decision = MartingaleDecision(
                should_recover=True,
                recovery_type=recovery_type,
                recovery_volume=recovery_volume,
                recovery_price=recovery_price,
                target_profit=target_profit,
                max_loss_limit=max_loss_limit,
                reasoning=self._create_recovery_reasoning(worst_position, recovery_volume),
                confidence=confidence,
                risk_level=risk_level
            )
            
            print(f"🎯 Martingale Recovery Decision:")
            print(f"   Type: {decision.recovery_type}")
            print(f"   Volume: {decision.recovery_volume}")
            print(f"   Target Profit: ${decision.target_profit:.2f}")
            print(f"   Risk Level: {decision.risk_level}")
            print(f"   Confidence: {decision.confidence:.2f}")
            
            return decision
            
        except Exception as e:
            print(f"❌ Recovery decision error: {e}")
            return None
    
    def _calculate_recovery_volume(self, worst_position: RecoveryPosition, 
                                 market_data: pd.DataFrame, session: str) -> float:
        """คำนวณปริมาณ recovery ตามแต่ละประเภท martingale"""
        try:
            base_volume = worst_position.original_volume
            current_level = worst_position.recovery_level + 1
            
            # เลือกวิธีคำนวณตาม martingale type
            if self.martingale_type == 'classic':
                multiplier = self.base_multiplier ** current_level
                
            elif self.martingale_type == 'progressive':
                strategy = self.config.get('progressive_strategy', 'moderate')
                multipliers = self.progressive_multipliers[strategy]
                multiplier = multipliers[min(current_level, len(multipliers)-1)]
                
            elif self.martingale_type == 'fibonacci':
                fib_index = min(current_level, len(self.fibonacci_sequence)-1)
                multiplier = self.fibonacci_sequence[fib_index]
                
            elif self.martingale_type == 'adaptive':
                multiplier = self._calculate_adaptive_multiplier(
                    worst_position, market_data, session
                )
            else:
                multiplier = self.base_multiplier
            
            # จำกัด multiplier สูงสุด
            multiplier = min(multiplier, self.max_multiplier)
            
            # คำนวณ volume
            recovery_volume = base_volume * multiplier
            
            # ปรับตาม session
            session_mult = self.session_multipliers.get(session, 1.0)
            recovery_volume *= session_mult
            
            # ปรับตามความผันผวน
            if self.volatility_adjustment:
                volatility_mult = self._calculate_volatility_multiplier(market_data)
                recovery_volume *= volatility_mult
            
            # จำกัดขนาดสูงสุด
            recovery_volume = min(recovery_volume, self.max_position_size)
            
            return round(recovery_volume, 2)
            
        except Exception as e:
            print(f"❌ Recovery volume calculation error: {e}")
            return 0.0
    
    def _calculate_adaptive_multiplier(self, position: RecoveryPosition,
                                     market_data: pd.DataFrame, session: str) -> float:
        """คำนวณ multiplier แบบ adaptive ตามสภาพตลาด"""
        try:
            base_multiplier = self.base_multiplier
            
            # ปรับตามขาดทุนปัจจุบัน
            loss_ratio = abs(position.unrealized_pnl) / abs(self.recovery_threshold)
            loss_adjustment = 1.0 + (loss_ratio * 0.3)  # เพิ่มได้สูงสุด 30%
            
            # ปรับตาม recovery level
            level_adjustment = 1.0 + (position.recovery_level * 0.2)
            
            # ปรับตาม session
            session_adjustment = self.session_multipliers.get(session, 1.0)
            
            # ปรับตามเทรนด์ (ถ้าเปิดไว้)
            trend_adjustment = 1.0
            if self.trend_awareness:
                trend_adjustment = self._calculate_trend_adjustment(market_data, position)
            
            # รวมการปรับค่า
            adaptive_multiplier = (base_multiplier * loss_adjustment * 
                                 level_adjustment * session_adjustment * trend_adjustment)
            
            return min(adaptive_multiplier, self.max_multiplier)
            
        except Exception as e:
            print(f"❌ Adaptive multiplier calculation error: {e}")
            return self.base_multiplier
    
    def _calculate_volatility_multiplier(self, market_data: pd.DataFrame) -> float:
        """คำนวณ multiplier ตามความผันผวน"""
        try:
            if len(market_data) < 20:
                return 1.0
            
            # คำนวณ ATR
            high_low = market_data['high'] - market_data['low']
            high_close = abs(market_data['high'] - market_data['close'].shift(1))
            low_close = abs(market_data['low'] - market_data['close'].shift(1))
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(window=14).mean().iloc[-1]
            
            # ปรับตาม ATR (ยิ่งผันผวนมาก ลด multiplier)
            atr_normalized = atr / market_data['close'].iloc[-1] * 100  # เป็น %
            
            if atr_normalized > 1.5:  # ผันผวนสูง
                return 0.8
            elif atr_normalized > 1.0:  # ผันผวนปานกลาง
                return 0.9
            elif atr_normalized < 0.5:  # ผันผวนต่ำ
                return 1.2
            else:
                return 1.0
                
        except Exception as e:
            print(f"❌ Volatility multiplier calculation error: {e}")
            return 1.0
    
    def _calculate_trend_adjustment(self, market_data: pd.DataFrame, 
                                  position: RecoveryPosition) -> float:
        """คำนวณการปรับค่าตามเทรนด์"""
        try:
            if len(market_data) < 50:
                return 1.0
            
            # คำนวณ moving averages
            ma_20 = market_data['close'].rolling(window=20).mean().iloc[-1]
            ma_50 = market_data['close'].rolling(window=50).mean().iloc[-1]
            current_price = market_data['close'].iloc[-1]
            
            # ประเมินเทรนด์
            if ma_20 > ma_50 and current_price > ma_20:
                trend = "uptrend"
            elif ma_20 < ma_50 and current_price < ma_20:
                trend = "downtrend"
            else:
                trend = "sideways"
            
            # ปรับตามทิศทางของ position และเทรนด์
            if position.position_type == "BUY":
                if trend == "downtrend":
                    return 0.7  # ลด multiplier เพราะต่อต้านเทรนด์
                elif trend == "sideways":
                    return 1.1  # เพิ่มเล็กน้อยในตลาดไซด์เวย์
                else:
                    return 0.9  # เทรนด์เดียวกัน แต่ระวัง overbought
            else:  # SELL
                if trend == "uptrend":
                    return 0.7  # ลด multiplier เพราะต่อต้านเทรนด์
                elif trend == "sideways":
                    return 1.1  # เพิ่มเล็กน้อยในตลาดไซด์เวย์
                else:
                    return 0.9  # เทรนด์เดียวกัน แต่ระวัง oversold
                    
        except Exception as e:
            print(f"❌ Trend adjustment calculation error: {e}")
            return 1.0
    
    def _calculate_target_profit(self, position: RecoveryPosition, recovery_volume: float) -> float:
        """คำนวณ target profit สำหรับการ recovery"""
        try:
            # ขาดทุนปัจจุบัน
            current_loss = abs(position.accumulated_loss)
            
            # เป้าหมายกำไร = ขาดทุน + กำไรเพิ่ม
            base_target = current_loss * 1.1  # เพิ่ม 10%
            
            # ปรับตาม recovery level (ยิ่งลึก ต้องการกำไรมากขึ้น)
            level_adjustment = 1.0 + (position.recovery_level * 0.05)
            
            # ปรับตาม volume ที่เพิ่ม
            volume_ratio = recovery_volume / position.original_volume
            volume_adjustment = 1.0 + (volume_ratio * 0.02)
            
            target_profit = base_target * level_adjustment * volume_adjustment
            
            return round(target_profit, 2)
            
        except Exception as e:
            print(f"❌ Target profit calculation error: {e}")
            return 50.0
    
    def _calculate_max_loss_limit(self, position: RecoveryPosition) -> float:
        """คำนวณ max loss limit สำหรับการ recovery"""
        try:
            # ใช้เป็นเปอร์เซ็นต์ของ max total loss
            remaining_capacity = self.max_total_loss - abs(self.total_unrealized_loss)
            max_additional_loss = remaining_capacity * 0.3  # ใช้ได้ 30% ของที่เหลือ
            
            return max(max_additional_loss, 100.0)  # อย่างน้อย $100
            
        except Exception as e:
            print(f"❌ Max loss limit calculation error: {e}")
            return 100.0
    
    def _assess_risk_level(self, position: RecoveryPosition, recovery_volume: float,
                          market_data: pd.DataFrame) -> str:
        """ประเมินระดับความเสี่ยง"""
        try:
            risk_score = 0
            
            # ความเสี่ยงจาก recovery level
            risk_score += position.recovery_level * 2
            
            # ความเสี่ยงจาก volume
            volume_ratio = recovery_volume / position.original_volume
            if volume_ratio > 5:
                risk_score += 3
            elif volume_ratio > 3:
                risk_score += 2
            elif volume_ratio > 2:
                risk_score += 1
            
            # ความเสี่ยงจากขาดทุนสะสม
            loss_ratio = abs(self.total_unrealized_loss) / self.max_total_loss
            if loss_ratio > 0.8:
                risk_score += 3
            elif loss_ratio > 0.6:
                risk_score += 2
            elif loss_ratio > 0.4:
                risk_score += 1
            
            # ความเสี่ยงจากความผันผวน
            if len(market_data) >= 14:
                volatility = market_data['close'].pct_change().rolling(14).std().iloc[-1]
                if volatility > 0.02:  # ผันผวนสูง
                    risk_score += 2
                elif volatility > 0.015:
                    risk_score += 1
            
            # จำแนกระดับความเสี่ยง
            if risk_score <= 2:
                return "LOW"
            elif risk_score <= 5:
                return "MEDIUM"
            elif risk_score <= 8:
                return "HIGH"
            else:
                return "CRITICAL"
                
        except Exception as e:
            print(f"❌ Risk assessment error: {e}")
            return "MEDIUM"
    
    def _calculate_recovery_confidence(self, position: RecoveryPosition,
                                     market_data: pd.DataFrame, session: str) -> float:
        """คำนวณความเชื่อมั่นในการ recovery"""
        try:
            confidence = 0.5  # base confidence
            
            # ปรับตาม session (martingale ดีในตลาดไซด์เวย์)
            session_confidence = {
                'asian': 0.8,
                'quiet': 0.85,
                'london': 0.4,
                'ny': 0.3,
                'overlap': 0.25
            }
            confidence = session_confidence.get(session, 0.5)
            
            # ปรับตาม recovery level (ยิ่งลึก ความมั่นใจลด)
            level_penalty = position.recovery_level * 0.1
            confidence -= level_penalty
            
            # ปรับตามความผันผวน (ยิ่งเงียบ ยิ่งดี)
            if len(market_data) >= 14:
                volatility = market_data['close'].pct_change().rolling(14).std().iloc[-1]
                if volatility < 0.01:  # ตลาดเงียบ
                    confidence += 0.1
                elif volatility > 0.02:  # ตลาดผันผวน
                    confidence -= 0.15
            
            # ปรับตามสถานะ recovery state
            if self.recovery_state == RecoveryState.CRITICAL:
                confidence -= 0.2
            elif self.recovery_state == RecoveryState.EMERGENCY:
                confidence -= 0.4
            
            return max(0.1, min(confidence, 0.95))
            
        except Exception as e:
            print(f"❌ Recovery confidence calculation error: {e}")
            return 0.5
    
    def _create_recovery_reasoning(self, position: RecoveryPosition, recovery_volume: float) -> str:
        """สร้างเหตุผลการ recovery"""
        reasons = []
        
        reasons.append(f"Position: {position.position_type}")
        reasons.append(f"Level: {position.recovery_level + 1}")
        reasons.append(f"Loss: ${position.unrealized_pnl:.2f}")
        reasons.append(f"Volume: {recovery_volume}")
        reasons.append(f"Type: {self.martingale_type}")
        reasons.append(f"State: {self.recovery_state.value}")
        
        return " | ".join(reasons)
    
    def execute_recovery(self, decision: MartingaleDecision, mt5_interface) -> bool:
        """
        ⚡ Execute recovery trade ผ่าน MT5
        
        Args:
            decision: MartingaleDecision object
            mt5_interface: MT5 interface object
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            if not decision.should_recover:
                return False
            
            print(f"🔄 Executing Martingale Recovery...")
            print(f"   Type: {decision.recovery_type}")
            print(f"   Volume: {decision.recovery_volume}")
            print(f"   Risk Level: {decision.risk_level}")
            
            # สร้าง order request
            order_request = {
                'action': 'TRADE_ACTION_DEAL',
                'symbol': 'XAUUSD',
                'volume': decision.recovery_volume,
                'type': 'ORDER_TYPE_BUY' if decision.recovery_type == 'BUY' else 'ORDER_TYPE_SELL',
                'price': decision.recovery_price,
                'deviation': 20,
                'magic': 12345,
                'comment': f"Martingale Recovery L{self._get_next_recovery_level()}",
                'type_time': 'ORDER_TIME_GTC',
                'type_filling': 'ORDER_FILLING_IOC'
            }
            
            # Execute order ผ่าน MT5
            result = mt5_interface.place_order(order_request)
            
            if result and result.get('retcode') == 10009:  # SUCCESS
                # อัปเดต recovery level
                self._update_recovery_level(result.get('order'))
                
                # บันทึกประวัติ
                self._record_recovery_execution(decision, result, True)
                
                print(f"✅ Martingale recovery executed successfully")
                print(f"   Order: {result.get('order')}")
                print(f"   Price: ${result.get('price'):.2f}")
                
                return True
            else:
                error_msg = result.get('comment', 'Unknown error') if result else 'No response'
                print(f"❌ Martingale recovery failed: {error_msg}")
                
                # บันทึกความล้มเหลว
                self._record_recovery_execution(decision, result, False)
                
                return False
                
        except Exception as e:
            print(f"❌ Recovery execution error: {e}")
            return False
    
    def _get_next_recovery_level(self) -> int:
        """ดึง recovery level ถัดไป"""
        if not self.recovery_positions:
            return 1
        return max(pos.recovery_level for pos in self.recovery_positions.values()) + 1
    
    def _update_recovery_level(self, order_ticket: int):
        """อัปเดต recovery level หลังจาก execute สำเร็จ"""
        try:
            # หา position ที่เกี่ยวข้อง และอัปเดต level
            for pos in self.recovery_positions.values():
                if pos.unrealized_pnl < self.recovery_threshold:
                    pos.recovery_level += 1
                    break
                    
        except Exception as e:
            print(f"❌ Recovery level update error: {e}")
    
    def _record_recovery_execution(self, decision: MartingaleDecision, result: Dict, success: bool):
        """บันทึกประวัติการ execute recovery"""
        try:
            record = {
                'timestamp': datetime.now(),
                'success': success,
                'recovery_type': decision.recovery_type,
                'volume': decision.recovery_volume,
                'target_profit': decision.target_profit,
                'risk_level': decision.risk_level,
                'confidence': decision.confidence,
                'total_loss_before': self.total_unrealized_loss,
                'result': result
            }
            
            self.recovery_history.append(record)
            
            # อัปเดตสถิติ
            if success:
                self.success_count += 1
            else:
                self.failure_count += 1
            
            # จำกัดประวัติ
            if len(self.recovery_history) > 1000:
                self.recovery_history = self.recovery_history[-500:]
                
        except Exception as e:
            print(f"❌ Recovery record error: {e}")
    
    def check_recovery_success(self, positions: List[Dict]) -> bool:
        """
        ✅ ตรวจสอบว่า recovery สำเร็จหรือไม่
        
        Args:
            positions: รายการ positions ปัจจุบัน
            
        Returns:
            True ถ้า recovery สำเร็จ
        """
        try:
            if not self.recovery_positions:
                return False
            
            # คำนวณ P&L รวมของ positions ทั้งหมด
            total_pnl = sum(pos.get('profit', 0) for pos in positions)
            
            # ถ้า P&L รวมเป็นบวก = recovery สำเร็จ
            if total_pnl > 0:
                print(f"🎉 Martingale Recovery SUCCESS!")
                print(f"   Total Profit: ${total_pnl:.2f}")
                print(f"   Recovery Levels Used: {max(pos.recovery_level for pos in self.recovery_positions.values())}")
                
                # รีเซ็ต recovery state
                self._reset_recovery_state()
                
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Recovery success check error: {e}")
            return False
    
    def _reset_recovery_state(self):
        """รีเซ็ตสถานะ recovery หลังจากสำเร็จ"""
        try:
            self.recovery_positions.clear()
            self.recovery_state = RecoveryState.INACTIVE
            self.total_unrealized_loss = 0.0
            
            print("🔄 Recovery state reset - Ready for new trades")
            
        except Exception as e:
            print(f"❌ Recovery state reset error: {e}")
    
    def get_recovery_status(self) -> Dict:
        """ดึงสถานะ recovery ปัจจุบัน"""
        try:
            if not self.recovery_positions:
                return {
                    'state': 'INACTIVE',
                    'positions': 0,
                    'total_loss': 0.0,
                    'max_drawdown': self.max_drawdown_reached
                }
            
            max_level = max(pos.recovery_level for pos in self.recovery_positions.values())
            worst_loss = min(pos.unrealized_pnl for pos in self.recovery_positions.values())
            
            return {
                'state': self.recovery_state.value,
                'positions': len(self.recovery_positions),
                'total_loss': self.total_unrealized_loss,
                'max_level': max_level,
                'worst_position_loss': worst_loss,
                'max_drawdown': self.max_drawdown_reached,
                'remaining_capacity': self.max_total_loss - abs(self.total_unrealized_loss)
            }
            
        except Exception as e:
            print(f"❌ Recovery status error: {e}")
            return {'error': str(e)}
    
    def get_performance_stats(self) -> Dict:
        """ดึงสถิติการทำงาน"""
        try:
            if not self.recovery_history:
                return {
                    'total_recoveries': 0,
                    'success_rate': 0.0,
                    'avg_confidence': 0.0
                }
            
            total_recoveries = len(self.recovery_history)
            success_rate = self.success_count / total_recoveries * 100
            
            # คำนวณ average confidence
            confidences = [r['confidence'] for r in self.recovery_history]
            avg_confidence = np.mean(confidences)
            
            # คำนวณ average target profit
            targets = [r['target_profit'] for r in self.recovery_history]
            avg_target = np.mean(targets)
            
            # Risk level distribution
            risk_levels = [r['risk_level'] for r in self.recovery_history]
            risk_distribution = {level: risk_levels.count(level) for level in set(risk_levels)}
            
            return {
                'total_recoveries': total_recoveries,
                'successful_recoveries': self.success_count,
                'failed_recoveries': self.failure_count,
                'success_rate': success_rate,
                'avg_confidence': avg_confidence,
                'avg_target_profit': avg_target,
                'max_drawdown_reached': self.max_drawdown_reached,
                'risk_distribution': risk_distribution,
                'martingale_type': self.martingale_type,
                'last_recovery': self.recovery_history[-1]['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            print(f"❌ Performance stats error: {e}")
            return {'error': str(e)}
    
    def optimize_parameters(self, historical_results: List[Dict]) -> Dict:
        """
        🔧 ปรับแต่งพารามิเตอร์ตามผลการทำงานในอดีต
        
        Args:
            historical_results: ผลการ recovery ในอดีต
            
        Returns:
            พารามิเตอร์ที่ปรับแต่งแล้ว
        """
        try:
            if not historical_results:
                return self.config
            
            print("🔧 Optimizing Martingale parameters...")
            
            # วิเคราะห์ success rate ตาม multiplier
            multiplier_success = {}
            for result in historical_results:
                multiplier = result.get('multiplier_used', self.base_multiplier)
                success = result.get('success', False)
                
                if multiplier not in multiplier_success:
                    multiplier_success[multiplier] = {'total': 0, 'success': 0}
                
                multiplier_success[multiplier]['total'] += 1
                if success:
                    multiplier_success[multiplier]['success'] += 1
            
            # หา multiplier ที่ดีที่สุด
            best_multiplier = self.base_multiplier
            best_success_rate = 0
            
            for multiplier, stats in multiplier_success.items():
                if stats['total'] >= 10:  # ต้องมีข้อมูลพอ
                    success_rate = stats['success'] / stats['total']
                    if success_rate > best_success_rate:
                        best_success_rate = success_rate
                        best_multiplier = multiplier
            
            # วิเคราะห์ recovery threshold
            threshold_analysis = [r.get('loss_before_recovery', 0) for r in historical_results if r.get('success')]
            if threshold_analysis:
                avg_successful_threshold = np.mean([abs(t) for t in threshold_analysis])
                optimal_threshold = -min(avg_successful_threshold * 1.2, abs(self.recovery_threshold))
            else:
                optimal_threshold = self.recovery_threshold
            
            # สร้างพารามิเตอร์ที่ปรับแต่งแล้ว
            optimized_config = self.config.copy()
            optimized_config.update({
                'base_multiplier': best_multiplier,
                'recovery_threshold': optimal_threshold,
                'optimization_date': datetime.now().isoformat(),
                'optimization_data_points': len(historical_results)
            })
            
            print(f"✅ Parameters optimized:")
            print(f"   Base Multiplier: {self.base_multiplier} -> {best_multiplier}")
            print(f"   Recovery Threshold: ${self.recovery_threshold} -> ${optimal_threshold:.2f}")
            print(f"   Based on {len(historical_results)} data points")
            
            return optimized_config
            
        except Exception as e:
            print(f"❌ Parameter optimization error: {e}")
            return self.config

def main():
    """Test the Smart Martingale Recovery System"""
    print("🧪 Testing Smart Martingale Recovery...")
    
    # Sample configuration
    config = {
        'martingale_type': 'adaptive',
        'max_recovery_levels': 5,
        'base_multiplier': 1.8,
        'max_total_loss': 500.0,
        'recovery_threshold': -20.0,
        'max_position_size': 2.0,
        'progressive_strategy': 'moderate'
    }
    
    # Initialize recovery system
    recovery = SmartMartingaleRecovery(config)
    
    # Create sample losing positions
    sample_positions = [
        {
            'ticket': 12345,
            'symbol': 'XAUUSD',
            'type': 'BUY',
            'volume': 0.01,
            'price_open': 2000.0,
            'current_price': 1980.0,
            'profit': -25.0,
            'time': datetime.now() - timedelta(minutes=30)
        },
        {
            'ticket': 12346,
            'symbol': 'XAUUSD',
            'type': 'SELL',
            'volume': 0.01,
            'price_open': 1990.0,
            'current_price': 2000.0,
            'profit': -15.0,
            'time': datetime.now() - timedelta(minutes=15)
        }
    ]
    
    # Test recovery need analysis
    needs_recovery = recovery.analyze_recovery_need(sample_positions)
    print(f"\n📊 Recovery Analysis:")
    print(f"   Needs Recovery: {needs_recovery}")
    print(f"   Recovery State: {recovery.recovery_state.value}")
    print(f"   Total Loss: ${recovery.total_unrealized_loss:.2f}")
    
    if needs_recovery:
        # Generate sample market data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
        np.random.seed(42)
        prices = 2000 + np.random.randn(100).cumsum() * 0.5
        
        market_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + np.random.rand(100) * 2,
            'low': prices - np.random.rand(100) * 2,
            'close': prices + np.random.randn(100) * 0.3,
            'volume': np.random.randint(100, 1000, 100)
        })
        
        # Test recovery decision
        decision = recovery.calculate_recovery_decision(market_data, 'asian')
        
        if decision:
            print(f"\n🎯 Recovery Decision:")
            print(f"   Should Recover: {decision.should_recover}")
            print(f"   Type: {decision.recovery_type}")
            print(f"   Volume: {decision.recovery_volume}")
            print(f"   Target Profit: ${decision.target_profit:.2f}")
            print(f"   Risk Level: {decision.risk_level}")
            print(f"   Confidence: {decision.confidence:.2f}")
            print(f"   Reasoning: {decision.reasoning}")
        else:
            print("\n❌ No recovery decision generated")
    
    # Test status
    status = recovery.get_recovery_status()
    print(f"\n📈 Recovery Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Test performance stats
    stats = recovery.get_performance_stats()
    print(f"\n📊 Performance Stats:")
    for key, value in stats.items():
        if isinstance(value, dict):
            continue
        print(f"   {key}: {value}")
    
    print("\n✅ Smart Martingale Recovery test completed")

if __name__ == "__main__":
    main()