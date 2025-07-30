#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RECOVERY SELECTOR - ระบบเลือกกลยุทธ์การกู้คืนอัจฉริยะ
==================================================
ระบบเลือกและจัดการกลยุทธ์การกู้คืนสำหรับ Intelligent Gold Trading
รองรับการแก้ไม้แบบต่างๆ ตามสภาวะตลาดและ position ที่ขาดทุน

🎯 ฟีเจอร์หลัก:
- Martingale Recovery (การเพิ่ม lot แบบทวีคูณ)
- Grid Recovery (การเปิด position แบบ grid)
- Hedging Recovery (การ hedge ด้วย position ตรงข้าม)
- Averaging Recovery (การเฉลี่ยราคา)
- Correlation Recovery (การใช้ correlation กู้คืน)
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import math

class RecoveryStrategy(Enum):
   """กลยุทธ์การกู้คืน"""
   MARTINGALE = "Martingale"
   GRID_TRADING = "Grid Trading"
   HEDGING = "Hedging"
   AVERAGING = "Averaging"
   CORRELATION = "Correlation"
   SMART_RECOVERY = "Smart Recovery"
   NO_RECOVERY = "No Recovery"

class RecoveryStatus(Enum):
   """สถานะการกู้คืน"""
   WAITING = "รอการกู้คืน"
   ACTIVE = "กำลังกู้คืน"
   SUCCESS = "กู้คืนสำเร็จ"
   FAILED = "กู้คืนล้มเหลว"
   PAUSED = "หยุดชั่วคราว"

class PositionType(Enum):
   """ประเภท Position"""
   BUY = "BUY"
   SELL = "SELL"

@dataclass
class LosingPosition:
   """ข้อมูล Position ที่ขาดทุน"""
   ticket: int = 0
   symbol: str = "XAUUSD"
   position_type: PositionType = PositionType.BUY
   lot_size: float = 0.1
   open_price: float = 0.0
   current_price: float = 0.0
   unrealized_pnl: float = 0.0
   open_time: datetime = field(default_factory=datetime.now)
   
   # Recovery tracking
   recovery_attempts: int = 0
   recovery_strategy: Optional[RecoveryStrategy] = None
   recovery_lot_used: float = 0.0
   
   def calculate_loss_amount(self) -> float:
       """คำนวณจำนวนเงินขาดทุน"""
       return abs(self.unrealized_pnl)
   
   def calculate_loss_pips(self) -> float:
       """คำนวณ pips ที่ขาดทุน"""
       price_diff = abs(self.current_price - self.open_price)
       return price_diff * 10000  # แปลงเป็น pips (สำหรับ XAUUSD ใช้ 10)

@dataclass
class RecoveryPlan:
   """แผนการกู้คืน"""
   strategy: RecoveryStrategy
   target_positions: List[LosingPosition]
   
   # Recovery parameters
   total_recovery_lot: float = 0.0
   expected_recovery_price: float = 0.0
   max_recovery_attempts: int = 5
   recovery_multiplier: float = 2.0
   
   # Risk management
   max_total_exposure: float = 1.0
   stop_recovery_loss: float = 100.0
   
   # Execution details
   next_entry_price: float = 0.0
   next_lot_size: float = 0.0
   recovery_direction: PositionType = PositionType.BUY
   
   # Status tracking
   status: RecoveryStatus = RecoveryStatus.WAITING
   created_time: datetime = field(default_factory=datetime.now)
   estimated_success_probability: float = 0.0

class RecoverySelector:
   """ระบบเลือกกลยุทธ์การกู้คืนหลัก"""
   
   def __init__(self, symbol: str = "XAUUSD"):
       self.symbol = symbol
       self.active_recoveries: Dict[int, RecoveryPlan] = {}
       self.recovery_history: List[Dict] = []
       
       # การตั้งค่า
       self.max_concurrent_recoveries = 3
       self.max_recovery_drawdown = 200.0  # USD
       self.recovery_success_target = 0.5  # 50 cents profit target
       
       # สถิติ
       self.total_recovery_attempts = 0
       self.successful_recoveries = 0
       self.failed_recoveries = 0
       
       print(f"🔄 เริ่มต้น Recovery Selector สำหรับ {symbol}")
   
   def analyze_losing_positions(self, positions: List[Any]) -> List[LosingPosition]:
       """วิเคราะห์ positions ที่ขาดทุน"""
       losing_positions = []
       
       try:
           for pos in positions:
               # แปลงข้อมูล position เป็น LosingPosition object
               if hasattr(pos, 'profit') and pos.profit < 0:
                   losing_pos = LosingPosition(
                       ticket=getattr(pos, 'ticket', 0),
                       symbol=getattr(pos, 'symbol', self.symbol),
                       position_type=PositionType.BUY if getattr(pos, 'type', 0) == 0 else PositionType.SELL,
                       lot_size=getattr(pos, 'volume', 0.1),
                       open_price=getattr(pos, 'price_open', 0.0),
                       current_price=getattr(pos, 'price_current', 0.0),
                       unrealized_pnl=getattr(pos, 'profit', 0.0),
                       open_time=datetime.fromtimestamp(getattr(pos, 'time', 0))
                   )
                   losing_positions.append(losing_pos)
           
           print(f"📊 พบ positions ขาดทุน: {len(losing_positions)} positions")
           
           # เรียงตามจำนวนขาดทุน (มากไปน้อย)
           losing_positions.sort(key=lambda x: x.calculate_loss_amount(), reverse=True)
           
           return losing_positions
           
       except Exception as e:
           print(f"❌ ข้อผิดพลาดในการวิเคราะห์ positions: {e}")
           return []
   
   def select_recovery_strategy(self, losing_positions: List[LosingPosition], 
                              market_analysis: Any = None) -> RecoveryStrategy:
       """เลือกกลยุทธ์การกู้คืนที่เหมาะสม"""
       
       if not losing_positions:
           return RecoveryStrategy.NO_RECOVERY
       
       try:
           # วิเคราะห์สถานการณ์
           total_loss = sum(pos.calculate_loss_amount() for pos in losing_positions)
           max_single_loss = max(pos.calculate_loss_amount() for pos in losing_positions)
           avg_loss_pips = sum(pos.calculate_loss_pips() for pos in losing_positions) / len(losing_positions)
           
           print(f"💰 วิเคราะห์การขาดทุน:")
           print(f"   รวมขาดทุน: ${total_loss:.2f}")
           print(f"   ขาดทุนสูงสุด: ${max_single_loss:.2f}")
           print(f"   เฉลี่ย pips: {avg_loss_pips:.1f}")
           
           # เลือกกลยุทธ์ตามสถานการณ์
           
           # 1. ถ้าขาดทุนน้อย ใช้ Averaging
           if total_loss < 10.0:
               return RecoveryStrategy.AVERAGING
           
           # 2. ถ้าขาดทุนปานกลาง และมี positions เยอะ ใช้ Grid
           elif total_loss < 50.0 and len(losing_positions) > 2:
               return RecoveryStrategy.GRID_TRADING
           
           # 3. ถ้าขาดทุนมาก แต่ยังจัดการได้ ใช้ Martingale
           elif total_loss < 100.0 and len(losing_positions) <= 3:
               return RecoveryStrategy.MARTINGALE
           
           # 4. ถ้าขาดทุนมากมาย ใช้ Hedging
           elif total_loss < 200.0:
               return RecoveryStrategy.HEDGING
           
           # 5. ถ้าขาดทุนมหาศาล ใช้ Smart Recovery
           else:
               return RecoveryStrategy.SMART_RECOVERY
               
       except Exception as e:
           print(f"❌ ข้อผิดพลาดในการเลือกกลยุทธ์: {e}")
           return RecoveryStrategy.AVERAGING  # default safe strategy
   
   def create_recovery_plan(self, losing_positions: List[LosingPosition], 
                          strategy: RecoveryStrategy, 
                          market_analysis: Any = None) -> RecoveryPlan:
       """สร้างแผนการกู้คืน"""
       
       plan = RecoveryPlan(
           strategy=strategy,
           target_positions=losing_positions.copy()
       )
       
       try:
           if strategy == RecoveryStrategy.MARTINGALE:
               plan = self._create_martingale_plan(plan, losing_positions)
           elif strategy == RecoveryStrategy.GRID_TRADING:
               plan = self._create_grid_plan(plan, losing_positions)
           elif strategy == RecoveryStrategy.HEDGING:
               plan = self._create_hedging_plan(plan, losing_positions)
           elif strategy == RecoveryStrategy.AVERAGING:
               plan = self._create_averaging_plan(plan, losing_positions)
           elif strategy == RecoveryStrategy.SMART_RECOVERY:
               plan = self._create_smart_recovery_plan(plan, losing_positions)
           
           # คำนวณความน่าจะเป็นของความสำเร็จ
           plan.estimated_success_probability = self._estimate_success_probability(plan, market_analysis)
           
           print(f"📋 สร้างแผนกู้คืน: {strategy.value}")
           print(f"   🎯 Lot รวม: {plan.total_recovery_lot:.2f}")
           print(f"   💰 ราคาเป้าหมาย: {plan.expected_recovery_price:.2f}")
           print(f"   📈 ความน่าจะเป็นสำเร็จ: {plan.estimated_success_probability:.1f}%")
           
           return plan
           
       except Exception as e:
           print(f"❌ ข้อผิดพลาดในการสร้างแผน: {e}")
           return plan
   
   def _create_martingale_plan(self, plan: RecoveryPlan, positions: List[LosingPosition]) -> RecoveryPlan:
       """สร้างแผน Martingale Recovery"""
       
       # หา position ที่ขาดทุนมากที่สุด
       main_position = max(positions, key=lambda x: x.calculate_loss_amount())
       
       # คำนวณ lot size สำหรับ recovery
       total_loss = sum(pos.calculate_loss_amount() for pos in positions)
       recovery_lot = main_position.lot_size * plan.recovery_multiplier
       
       # กำหนดทิศทางการกู้คืน (ตรงข้ามกับ position หลัก)
       plan.recovery_direction = PositionType.SELL if main_position.position_type == PositionType.BUY else PositionType.BUY
       
       # คำนวณราคา entry
       if plan.recovery_direction == PositionType.BUY:
           plan.next_entry_price = main_position.current_price - (total_loss / recovery_lot / 10)
       else:
           plan.next_entry_price = main_position.current_price + (total_loss / recovery_lot / 10)
       
       plan.total_recovery_lot = recovery_lot
       plan.next_lot_size = recovery_lot
       plan.max_recovery_attempts = 3
       
       return plan
   
   def _create_grid_plan(self, plan: RecoveryPlan, positions: List[LosingPosition]) -> RecoveryPlan:
       """สร้างแผน Grid Recovery"""
       
       # คำนวณช่วงราคาของ positions
       prices = [pos.open_price for pos in positions]
       min_price = min(prices)
       max_price = max(prices)
       price_range = max_price - min_price
       
       # กำหนด grid spacing
       grid_spacing = max(0.5, price_range / 5)  # อย่างน้อย 0.5 point
       
       # คำนวณ lot size เฉลี่ย
       avg_lot = sum(pos.lot_size for pos in positions) / len(positions)
       
       plan.total_recovery_lot = avg_lot * 0.5  # ใช้ lot เล็กกว่าเดิม
       plan.next_lot_size = plan.total_recovery_lot
       plan.max_recovery_attempts = 5
       
       # ทิศทางขึ้นอยู่กับ position ส่วนใหญ่
       buy_positions = sum(1 for pos in positions if pos.position_type == PositionType.BUY)
       plan.recovery_direction = PositionType.SELL if buy_positions > len(positions) / 2 else PositionType.BUY
       
       # กำหนดราคา entry ตาม grid
       current_price = positions[0].current_price
       if plan.recovery_direction == PositionType.BUY:
           plan.next_entry_price = current_price - grid_spacing
       else:
           plan.next_entry_price = current_price + grid_spacing
       
       return plan
   
   def _create_hedging_plan(self, plan: RecoveryPlan, positions: List[LosingPosition]) -> RecoveryPlan:
       """สร้างแผน Hedging Recovery"""
       
       # คำนวณ net position
       net_buy_lot = sum(pos.lot_size for pos in positions if pos.position_type == PositionType.BUY)
       net_sell_lot = sum(pos.lot_size for pos in positions if pos.position_type == PositionType.SELL)
       
       net_lot = abs(net_buy_lot - net_sell_lot)
       
       # hedge ด้วย position ตรงข้าม
       if net_buy_lot > net_sell_lot:
           plan.recovery_direction = PositionType.SELL
       else:
           plan.recovery_direction = PositionType.BUY
       
       # ใช้ lot เท่ากับ net position
       plan.total_recovery_lot = net_lot
       plan.next_lot_size = net_lot
       plan.next_entry_price = positions[0].current_price  # Market price
       plan.max_recovery_attempts = 2
       
       return plan
   
   def _create_averaging_plan(self, plan: RecoveryPlan, positions: List[LosingPosition]) -> RecoveryPlan:
       """สร้างแผน Averaging Recovery"""
       
       # หา position ที่ขาดทุนมากที่สุด
       main_position = max(positions, key=lambda x: x.calculate_loss_amount())
       
       # ใช้ lot size เดียวกับ position เดิม
       plan.total_recovery_lot = main_position.lot_size
       plan.next_lot_size = main_position.lot_size
       plan.recovery_direction = main_position.position_type  # ทิศทางเดียวกัน
       
       # เข้าในราคาที่ดีกว่า
       loss_pips = main_position.calculate_loss_pips()
       price_improvement = loss_pips / 2 / 10000  # ปรับปรุงราคาครึ่งหนึ่ง
       
       if plan.recovery_direction == PositionType.BUY:
           plan.next_entry_price = main_position.current_price - price_improvement
       else:
           plan.next_entry_price = main_position.current_price + price_improvement
       
       plan.max_recovery_attempts = 2
       
       return plan
   
   def _create_smart_recovery_plan(self, plan: RecoveryPlan, positions: List[LosingPosition]) -> RecoveryPlan:
       """สร้างแผน Smart Recovery (รวมหลากกลยุทธ์)"""
       
       # วิเคราะห์สถานการณ์
       total_loss = sum(pos.calculate_loss_amount() for pos in positions)
       
       # เริ่มด้วย partial hedging
       net_buy_lot = sum(pos.lot_size for pos in positions if pos.position_type == PositionType.BUY)
       net_sell_lot = sum(pos.lot_size for pos in positions if pos.position_type == PositionType.SELL)
       
       # Hedge บางส่วน (70%)
       if net_buy_lot > net_sell_lot:
           plan.recovery_direction = PositionType.SELL
           plan.total_recovery_lot = (net_buy_lot - net_sell_lot) * 0.7
       else:
           plan.recovery_direction = PositionType.BUY
           plan.total_recovery_lot = (net_sell_lot - net_buy_lot) * 0.7
       
       plan.next_lot_size = plan.total_recovery_lot
       plan.next_entry_price = positions[0].current_price
       plan.max_recovery_attempts = 3
       
       return plan
   
   def _estimate_success_probability(self, plan: RecoveryPlan, market_analysis: Any = None) -> float:
       """ประเมินความน่าจะเป็นของความสำเร็จ"""
       
       base_probability = 70.0  # ความน่าจะเป็นพื้นฐาน
       
       try:
           # ปรับตามกลยุทธ์
           strategy_adjustments = {
               RecoveryStrategy.AVERAGING: 10,
               RecoveryStrategy.GRID_TRADING: 5,
               RecoveryStrategy.MARTINGALE: -5,
               RecoveryStrategy.HEDGING: 15,
               RecoveryStrategy.SMART_RECOVERY: 20
           }
           
           base_probability += strategy_adjustments.get(plan.strategy, 0)
           
           # ปรับตาม lot size (lot ใหญ่เสี่ยงมากขึ้น)
           if plan.total_recovery_lot > 0.5:
               base_probability -= (plan.total_recovery_lot - 0.5) * 10
           
           # ปรับตามจำนวน attempts
           if plan.max_recovery_attempts > 3:
               base_probability -= (plan.max_recovery_attempts - 3) * 5
           
           # ปรับตาม market analysis (ถ้ามี)
           if market_analysis:
               if hasattr(market_analysis, 'volatility_score'):
                   volatility = market_analysis.volatility_score
                   if volatility > 80:  # ความผันผวนสูงลดโอกาสสำเร็จ
                       base_probability -= 15
                   elif volatility < 30:  # ความผันผวนต่ำเพิ่มโอกาสสำเร็จ
                       base_probability += 10
           
           return max(10, min(95, base_probability))  # จำกัดระหว่าง 10-95%
           
       except Exception as e:
           print(f"⚠️ ข้อผิดพลาดในการประเมินความน่าจะเป็น: {e}")
           return 50.0
   
   def execute_recovery_plan(self, plan: RecoveryPlan) -> bool:
       """ดำเนินการตามแผนการกู้คืน"""
       
       try:
           print(f"🚀 เริ่มดำเนินการกู้คืน: {plan.strategy.value}")
           print(f"   💹 ทิศทาง: {plan.recovery_direction.value}")
           print(f"   📊 Lot Size: {plan.next_lot_size:.2f}")
           print(f"   💰 ราคาเป้าหมาย: {plan.next_entry_price:.2f}")
           
           # จำลองการส่งคำสั่ง (ในระบบจริงจะเชื่อมต่อกับ MT5)
           plan.status = RecoveryStatus.ACTIVE
           
           # เพิ่มสถิติ
           self.total_recovery_attempts += 1
           
           # บันทึกในประวัติ
           recovery_record = {
               'strategy': plan.strategy.value,
               'timestamp': datetime.now().isoformat(),
               'lot_size': plan.next_lot_size,
               'entry_price': plan.next_entry_price,
               'direction': plan.recovery_direction.value,
               'success_probability': plan.estimated_success_probability
           }
           
           self.recovery_history.append(recovery_record)
           
           # จำลองผล (ในระบบจริงจะติดตามผลจริง)
           import random
           success_chance = plan.estimated_success_probability / 100
           
           if random.random() < success_chance:
               plan.status = RecoveryStatus.SUCCESS
               self.successful_recoveries += 1
               print("✅ จำลองการกู้คืนสำเร็จ")
               return True
           else:
               plan.status = RecoveryStatus.FAILED
               self.failed_recoveries += 1
               print("❌ จำลองการกู้คืนล้มเหลว")
               return False
               
       except Exception as e:
           print(f"❌ ข้อผิดพลาดในการดำเนินการกู้คืน: {e}")
           plan.status = RecoveryStatus.FAILED
           return False
   
   def get_recovery_statistics(self) -> Dict[str, Any]:
       """ดึงสถิติการกู้คืน"""
       
       success_rate = (self.successful_recoveries / max(self.total_recovery_attempts, 1)) * 100
       
       return {
           'total_attempts': self.total_recovery_attempts,
           'successful_recoveries': self.successful_recoveries,
           'failed_recoveries': self.failed_recoveries,
           'success_rate': success_rate,
           'active_recoveries': len(self.active_recoveries),
           'max_concurrent_recoveries': self.max_concurrent_recoveries,
           'recent_strategies': [record['strategy'] for record in self.recovery_history[-5:]]
       }

def test_recovery_selector():
   """ทดสอบ Recovery Selector"""
   print("🧪 ทดสอบ Recovery Selector...")
   
   try:
       # สร้าง selector
       selector = RecoverySelector("XAUUSD")
       
       # จำลอง losing positions
       losing_positions = [
           LosingPosition(
               ticket=12345,
               position_type=PositionType.BUY,
               lot_size=0.1,
               open_price=2000.0,
               current_price=1995.0,
               unrealized_pnl=-50.0
           ),
           LosingPosition(
               ticket=12346,
               position_type=PositionType.SELL,
               lot_size=0.05,
               open_price=1990.0,
               current_price=1995.0,
               unrealized_pnl=-25.0
           )
       ]
       
       print(f"📊 จำลอง positions ขาดทุน: {len(losing_positions)} positions")
       
       # เลือกกลยุทธ์การกู้คืน
       strategy = selector.select_recovery_strategy(losing_positions)
       print(f"🎯 กลยุทธ์ที่เลือก: {strategy.value}")
       
       # สร้างแผนการกู้คืน
       plan = selector.create_recovery_plan(losing_positions, strategy)
       
       # ดำเนินการกู้คืน
       success = selector.execute_recovery_plan(plan)
       
       # แสดงสถิติ
       stats = selector.get_recovery_statistics()
       print(f"\n📊 สถิติการกู้คืน:")
       print(f"   การพยายามทั้งหมด: {stats['total_attempts']}")
       print(f"   สำเร็จ: {stats['successful_recoveries']}")
       print(f"   ล้มเหลว: {stats['failed_recoveries']}")
       print(f"   อัตราสำเร็จ: {stats['success_rate']:.1f}%")
       
       print("✅ ทดสอบ Recovery Selector เสร็จสิ้น")
       
   except Exception as e:
       print(f"❌ ข้อผิดพลาดในการทดสอบ: {e}")

if __name__ == "__main__":
   test_recovery_selector()