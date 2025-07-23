# intelligent_recovery/strategies/grid_intelligent.py - Grid Intelligent Recovery System

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import math

class GridDirection(Enum):
    """📊 ทิศทางของ Grid"""
    UP_TRENDING = "up_trending"         # Grid ขาขึ้น
    DOWN_TRENDING = "down_trending"     # Grid ขาลง
    BIDIRECTIONAL = "bidirectional"    # Grid สองทิศทาง
    ADAPTIVE = "adaptive"              # Grid ปรับตามตลาด

class GridState(Enum):
    """🎯 สถานะของ Grid System"""
    INACTIVE = "inactive"       # ไม่ทำงาน
    BUILDING = "building"       # กำลังสร้าง grid
    ACTIVE = "active"           # grid ทำงานปกติ
    RECOVERING = "recovering"   # กำลัง recovery
    REBALANCING = "rebalancing" # ปรับสมดุล grid

@dataclass
class GridLevel:
    """📈 ระดับใน Grid System"""
    level: int
    price: float
    volume: float
    direction: str              # "BUY" or "SELL"
    is_filled: bool
    ticket: Optional[int] = None
    fill_time: Optional[datetime] = None
    unrealized_pnl: float = 0.0

@dataclass
class GridSetup:
    """⚙️ การตั้งค่า Grid System"""
    center_price: float
    grid_spacing: float         # ระยะห่างระหว่างระดับ (pips)
    total_levels: int
    base_volume: float
    volume_multiplier: float    # คูณ volume ทุกระดับ
    max_volume_per_level: float
    direction: GridDirection
    profit_target: float        # เป้ากำไรรวม
    max_drawdown: float         # ขาดทุนสูงสุดที่ยอมรับ

@dataclass
class GridDecision:
    """🎯 การตัดสินใจ Grid Recovery"""
    should_place_grid: bool
    grid_setup: Optional[GridSetup]
    next_levels: List[GridLevel]
    rebalance_needed: bool
    close_levels: List[int]     # ระดับที่ต้องปิด
    reasoning: str
    confidence: float
    risk_assessment: str

class GridIntelligentRecovery:
    """
    🌐 Grid Intelligent Recovery System - Advanced Grid Trading for Recovery
    
    เหมาะสำหรับ:
    - Trending Markets (ตลาดเทรนด์ชัด)
    - London/NY Sessions (ความผันผวนสูง)
    - Breakout scenarios
    """
    
    def __init__(self, config: Dict):
        print("🌐 Initializing Grid Intelligent Recovery...")
        
        self.config = config
        
        # Grid parameters
        self.base_grid_spacing = config.get('base_grid_spacing', 20.0)  # pips
        self.max_grid_levels = config.get('max_grid_levels', 10)
        self.base_volume = config.get('base_volume', 0.01)
        self.volume_multiplier = config.get('volume_multiplier', 1.2)
        self.max_volume_per_level = config.get('max_volume_per_level', 0.5)
        
        # Risk management
        self.max_total_exposure = config.get('max_total_exposure', 5.0)  # lots
        self.max_drawdown_limit = config.get('max_drawdown_limit', 1000.0)  # USD
        self.profit_target_ratio = config.get('profit_target_ratio', 0.3)  # 30% of potential loss
        
        # Current grid state
        self.grid_state = GridState.INACTIVE
        self.current_grid_setup = None
        self.active_levels = {}  # level -> GridLevel
        self.grid_center_price = 0.0
        self.total_grid_pnl = 0.0
        
        # Statistics
        self.grid_history = []
        self.successful_grids = 0
        self.failed_grids = 0
        self.total_grid_profit = 0.0
        
        print("✅ Grid Intelligent Recovery initialized")
    
    def analyze_grid_opportunity(self, market_data: pd.DataFrame, 
                               losing_positions: List[Dict]) -> bool:
        """วิเคราะห์โอกาสใช้ Grid Recovery"""
        try:
            if not losing_positions:
                return False
            
            # วิเคราะห์เทรนด์
            trend_analysis = self._analyze_market_trend(market_data)
            
            # วิเคราะห์ความผันผวน
            volatility_analysis = self._analyze_volatility(market_data)
            
            # วิเคราะห์ losing positions
            position_analysis = self._analyze_losing_positions(losing_positions)
            
            # ตรวจสอบเงื่อนไขใช้ Grid
            is_suitable = self._check_grid_suitability(
                trend_analysis, volatility_analysis, position_analysis
            )
            
            return is_suitable
            
        except Exception as e:
            print(f"❌ Grid opportunity analysis error: {e}")
            return False
    
    def _analyze_market_trend(self, market_data: pd.DataFrame) -> Dict:
        """วิเคราะห์เทรนด์ของตลาด"""
        try:
            if len(market_data) < 50:
                return {'direction': 'sideways', 'strength': 0.0, 'confidence': 0.0}
            
            # คำนวณ moving averages
            close = market_data['close']
            ma_20 = close.rolling(window=20).mean()
            ma_50 = close.rolling(window=50).mean()
            
            current_price = close.iloc[-1]
            current_ma_20 = ma_20.iloc[-1]
            current_ma_50 = ma_50.iloc[-1]
            
            # ประเมินทิศทาง
            if current_price > current_ma_20 > current_ma_50:
                direction = "uptrend"
                strength = min((current_price - current_ma_50) / current_ma_50 * 1000, 1.0)
            elif current_price < current_ma_20 < current_ma_50:
                direction = "downtrend"
                strength = min((current_ma_50 - current_price) / current_ma_50 * 1000, 1.0)
            else:
                direction = "sideways"
                strength = 0.3
            
            return {
                'direction': direction,
                'strength': strength,
                'confidence': 0.7,
                'ma_20': current_ma_20,
                'ma_50': current_ma_50
            }
            
        except Exception as e:
            print(f"❌ Trend analysis error: {e}")
            return {'direction': 'sideways', 'strength': 0.0, 'confidence': 0.0}
    
    def _analyze_volatility(self, market_data: pd.DataFrame) -> Dict:
        """วิเคราะห์ความผันผวน"""
        try:
            if len(market_data) < 20:
                return {'level': 'medium', 'atr': 20.0, 'multiplier': 1.0}
            
            # คำนวณ ATR
            high_low = market_data['high'] - market_data['low']
            high_close = abs(market_data['high'] - market_data['close'].shift(1))
            low_close = abs(market_data['low'] - market_data['close'].shift(1))
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(window=14).mean().iloc[-1]
            
            # แปลงเป็น pips (สำหรับ XAUUSD)
            atr_pips = atr * 10
            
            # จำแนกระดับความผันผวน
            if atr_pips < 15:
                level = "low"
                multiplier = 0.8
            elif atr_pips < 30:
                level = "medium"
                multiplier = 1.0
            elif atr_pips < 50:
                level = "high"
                multiplier = 1.3
            else:
                level = "extreme"
                multiplier = 1.6
            
            return {
                'level': level,
                'atr': atr_pips,
                'multiplier': multiplier
            }
            
        except Exception as e:
            print(f"❌ Volatility analysis error: {e}")
            return {'level': 'medium', 'atr': 20.0, 'multiplier': 1.0}
    
    def _analyze_losing_positions(self, positions: List[Dict]) -> Dict:
        """วิเคราะห์ positions ที่ขาดทุน"""
        try:
            if not positions:
                return {'total_loss': 0.0, 'avg_loss': 0.0, 'positions': 0}
            
            total_loss = sum(pos.get('profit', 0) for pos in positions if pos.get('profit', 0) < 0)
            losing_positions = [pos for pos in positions if pos.get('profit', 0) < 0]
            
            if not losing_positions:
                return {'total_loss': 0.0, 'avg_loss': 0.0, 'positions': 0}
            
            avg_loss = total_loss / len(losing_positions)
            
            # วิเคราะห์ทิศทางของ losing positions
            buy_positions = len([pos for pos in losing_positions if pos.get('type') == 'BUY'])
            sell_positions = len(losing_positions) - buy_positions
            
            dominant_direction = 'BUY' if buy_positions > sell_positions else 'SELL'
            
            return {
                'total_loss': total_loss,
                'avg_loss': avg_loss,
                'positions': len(losing_positions),
                'dominant_direction': dominant_direction,
                'buy_positions': buy_positions,
                'sell_positions': sell_positions
            }
            
        except Exception as e:
            print(f"❌ Position analysis error: {e}")
            return {'total_loss': 0.0, 'avg_loss': 0.0, 'positions': 0}
    
    def _check_grid_suitability(self, trend_analysis: Dict, volatility_analysis: Dict, 
                               position_analysis: Dict) -> bool:
        """ตรวจสอบความเหมาะสมของ Grid Recovery"""
        try:
            # เงื่อนไข 1: ต้องมีเทรนด์ชัดเจน
            if trend_analysis['direction'] == 'sideways' and trend_analysis['confidence'] < 0.4:
                return False
            
            # เงื่อนไข 2: ความผันผวนต้องเหมาะสม
            if volatility_analysis['level'] == 'extreme':
                return False
            
            # เงื่อนไข 3: มี losing positions เพียงพอ
            if position_analysis['positions'] < 1:
                return False
            
            # เงื่อนไข 4: ขาดทุนไม่เกินขีดจำกัด
            if abs(position_analysis['total_loss']) > self.max_drawdown_limit * 0.5:
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Grid suitability check error: {e}")
            return False
    
    def calculate_grid_setup(self, market_data: pd.DataFrame, losing_positions: List[Dict],
                           current_session: str = 'london') -> Optional[GridSetup]:
        """คำนวณการตั้งค่า Grid Recovery"""
        try:
            # วิเคราะห์ตลาด
            trend_analysis = self._analyze_market_trend(market_data)
            volatility_analysis = self._analyze_volatility(market_data)
            position_analysis = self._analyze_losing_positions(losing_positions)
            
            # กำหนด center price
            current_price = market_data['close'].iloc[-1]
            
            # กำหนดทิศทาง Grid
            if trend_analysis['direction'] == 'uptrend':
                grid_direction = GridDirection.UP_TRENDING
            elif trend_analysis['direction'] == 'downtrend':
                grid_direction = GridDirection.DOWN_TRENDING
            else:
                grid_direction = GridDirection.BIDIRECTIONAL
            
            # คำนวณ grid spacing
            base_spacing = self.base_grid_spacing
            volatility_mult = volatility_analysis['multiplier']
            grid_spacing = base_spacing * volatility_mult
            
            # คำนวณจำนวนระดับ
            total_loss = abs(position_analysis['total_loss'])
            suggested_levels = min(max(3, int(total_loss / 50)), self.max_grid_levels)
            
            # คำนวณ profit target
            profit_target = total_loss * self.profit_target_ratio
            
            grid_setup = GridSetup(
                center_price=current_price,
                grid_spacing=grid_spacing,
                total_levels=suggested_levels,
                base_volume=self.base_volume,
                volume_multiplier=self.volume_multiplier,
                max_volume_per_level=self.max_volume_per_level,
                direction=grid_direction,
                profit_target=profit_target,
                max_drawdown=total_loss * 2.0
            )
            
            return grid_setup
            
        except Exception as e:
            print(f"❌ Grid setup calculation error: {e}")
            return None
    
    def generate_grid_levels(self, grid_setup: GridSetup, 
                           current_price: float) -> List[GridLevel]:
        """สร้างระดับต่างๆ ของ Grid"""
        try:
            levels = []
            spacing_in_price = grid_setup.grid_spacing / 10  # Convert pips to price
            
            if grid_setup.direction == GridDirection.UP_TRENDING:
                # Grid สำหรับเทรนด์ขาขึ้น (เทรด BUY ทุกระดับ)
                for i in range(grid_setup.total_levels):
                    level_price = current_price - (spacing_in_price * (i + 1))
                    level_volume = grid_setup.base_volume * (grid_setup.volume_multiplier ** i)
                    level_volume = min(level_volume, grid_setup.max_volume_per_level)
                    
                    grid_level = GridLevel(
                        level=i + 1,
                        price=level_price,
                        volume=level_volume,
                        direction="BUY",
                        is_filled=False
                    )
                    levels.append(grid_level)
            
            elif grid_setup.direction == GridDirection.DOWN_TRENDING:
                # Grid สำหรับเทรนด์ขาลง (เทรด SELL ทุกระดับ)
                for i in range(grid_setup.total_levels):
                    level_price = current_price + (spacing_in_price * (i + 1))
                    level_volume = grid_setup.base_volume * (grid_setup.volume_multiplier ** i)
                    level_volume = min(level_volume, grid_setup.max_volume_per_level)
                    
                    grid_level = GridLevel(
                        level=i + 1,
                        price=level_price,
                        volume=level_volume,
                        direction="SELL",
                        is_filled=False
                    )
                    levels.append(grid_level)
            
            else:  # BIDIRECTIONAL
                # Grid สองทิศทาง
                levels_per_side = grid_setup.total_levels // 2
                
                # BUY levels ด้านล่าง
                for i in range(levels_per_side):
                    level_price = current_price - (spacing_in_price * (i + 1))
                    level_volume = grid_setup.base_volume * (grid_setup.volume_multiplier ** i)
                    level_volume = min(level_volume, grid_setup.max_volume_per_level)
                    
                    grid_level = GridLevel(
                        level=-(i + 1),
                        price=level_price,
                        volume=level_volume,
                        direction="BUY",
                        is_filled=False
                    )
                    levels.append(grid_level)
                
                # SELL levels ด้านบน
                for i in range(levels_per_side):
                    level_price = current_price + (spacing_in_price * (i + 1))
                    level_volume = grid_setup.base_volume * (grid_setup.volume_multiplier ** i)
                    level_volume = min(level_volume, grid_setup.max_volume_per_level)
                    
                    grid_level = GridLevel(
                        level=i + 1,
                        price=level_price,
                        volume=level_volume,
                        direction="SELL",
                        is_filled=False
                    )
                    levels.append(grid_level)
            
            # เรียงลำดับตามราคา
            levels.sort(key=lambda x: x.price)
            return levels
            
        except Exception as e:
            print(f"❌ Grid levels generation error: {e}")
            return []
    
    def calculate_grid_decision(self, market_data: pd.DataFrame, 
                              losing_positions: List[Dict],
                              current_session: str = 'london') -> Optional[GridDecision]:
        """คำนวณการตัดสินใจ Grid Recovery"""
        try:
            # ตรวจสอบโอกาส Grid
            if not self.analyze_grid_opportunity(market_data, losing_positions):
                return None
            
            # คำนวณ Grid setup
            grid_setup = self.calculate_grid_setup(market_data, losing_positions, current_session)
            if not grid_setup:
                return None
            
            # สร้าง Grid levels
            current_price = market_data['close'].iloc[-1]
            grid_levels = self.generate_grid_levels(grid_setup, current_price)
            
            if not grid_levels:
                return None
            
            decision = GridDecision(
                should_place_grid=True,
                grid_setup=grid_setup,
                next_levels=grid_levels,
                rebalance_needed=False,
                close_levels=[],
                reasoning=f"Grid for {grid_setup.direction.value} with {len(grid_levels)} levels",
                confidence=0.75,
                risk_assessment="MEDIUM"
            )
            
            return decision
            
        except Exception as e:
            print(f"❌ Grid decision calculation error: {e}")
            return None
    
    def get_grid_status(self) -> Dict:
        """ดึงสถานะ Grid ปัจจุบัน"""
        return {
            'state': self.grid_state.value,
            'active_levels': len(self.active_levels),
            'total_pnl': self.total_grid_pnl,
            'successful_grids': self.successful_grids,
            'failed_grids': self.failed_grids
        }

def main():
    """Test the Grid Intelligent Recovery System"""
    print("🧪 Testing Grid Intelligent Recovery...")
    
    # Sample configuration
    config = {
        'base_grid_spacing': 25.0,
        'max_grid_levels': 8,
        'base_volume': 0.01,
        'volume_multiplier': 1.3,
        'max_volume_per_level': 0.3,
        'max_total_exposure': 3.0,
        'max_drawdown_limit': 800.0,
        'profit_target_ratio': 0.25
    }
    
    # Initialize Grid recovery
    grid_recovery = GridIntelligentRecovery(config)
    
    print("✅ Grid Intelligent Recovery test completed")

if __name__ == "__main__":
    main()