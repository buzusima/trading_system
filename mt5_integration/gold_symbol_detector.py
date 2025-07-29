#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD SYMBOL AUTO-DETECTOR - ระบบหานามสกุลทองอัตโนมัติ
======================================================
ระบบค้นหานามสกุลทอง (Gold Symbol) ที่แต่ละโบรกเกอร์ใช้
เพราะโบรกเกอร์แต่ละรายอาจใช้ชื่อต่างกัน เช่น XAUUSD, GOLD, GOLD.USD, etc.

🎯 หน้าที่:
- หานามสกุลทองที่ถูกต้องในโบรกเกอร์
- ตรวจสอบความพร้อมในการเทรด
- วิเคราะห์ Spread และ Trading Conditions
- เลือกนามสกุลที่ดีที่สุดสำหรับเทรด
"""

import MetaTrader5 as mt5
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import re
from collections import defaultdict

# Internal imports
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class GoldSymbolQuality(Enum):
    """คุณภาพของ Gold Symbol"""
    EXCELLENT = "EXCELLENT"     # Spread ต่ำ, Volume สูง, เทรดได้ดี
    GOOD = "GOOD"              # เทรดได้ปกติ
    FAIR = "FAIR"              # เทรดได้แต่ค่าใช้จ่ายสูง
    POOR = "POOR"              # ไม่แนะนำให้เทรด

@dataclass
class GoldSymbolInfo:
    """ข้อมูล Gold Symbol"""
    symbol: str
    description: str
    
    # Trading availability
    is_visible: bool = False
    is_tradable: bool = False
    market_open: bool = False
    trade_allowed: bool = False
    
    # Volume settings
    volume_min: float = 0.0
    volume_max: float = 0.0
    volume_step: float = 0.0
    
    # Price settings
    digits: int = 0
    point: float = 0.0
    
    # Current market data
    current_bid: float = 0.0
    current_ask: float = 0.0
    spread_points: float = 0.0
    spread_percent: float = 0.0
    
    # Trading costs
    commission: float = 0.0
    swap_long: float = 0.0
    swap_short: float = 0.0
    
    # Quality assessment
    quality: GoldSymbolQuality = GoldSymbolQuality.FAIR
    quality_score: float = 0.0
    
    # Additional info
    server_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    notes: str = ""

class GoldSymbolDetector:
    """ตัวค้นหา Gold Symbol อัตโนมัติ"""
    
    def __init__(self):
        self.logger = setup_component_logger("GoldSymbolDetector")
        
        # ตรวจสอบ MT5 connection
        if not mt5.initialize():
            raise RuntimeError("❌ ไม่สามารถเชื่อมต่อ MT5 ได้")
        
        self.logger.info("✅ เชื่อมต่อ MT5 สำหรับ Gold Symbol Detection")
        
        # Gold symbol patterns ที่โบรกเกอร์นิยมใช้
        self.gold_patterns = [
            # Standard patterns
            r'^XAUUSD$',
            r'^GOLD$',
            r'^GOLDUSD$',
            r'^GOLD\.USD$',
            r'^XAU\.USD$',
            r'^XAUUSD\..*$',
            
            # Broker-specific patterns
            r'^.*XAUUSD.*$',
            r'^.*GOLD.*USD.*$',
            r'^AU.*USD$',
            r'^GOLD.*$',
            
            # Alternative formats
            r'^XAU/USD$',
            r'^GOLD/USD$',
            r'^XAU_USD$',
            r'^GOLD_USD$'
        ]
        
        # Results
        self.found_symbols: List[GoldSymbolInfo] = []
        self.best_symbol: Optional[GoldSymbolInfo] = None
        self.recommended_symbol: str = ""
        
    @handle_trading_errors(ErrorCategory.MARKET_DATA, ErrorSeverity.MEDIUM)
    def detect_gold_symbols(self) -> bool:
        """ค้นหา Gold Symbols ทั้งหมด"""
        try:
            self.logger.info("🔍 กำลังค้นหา Gold Symbols...")
            
            # ดึง symbols ทั้งหมด
            all_symbols = mt5.symbols_get()
            if not all_symbols:
                self.logger.error("❌ ไม่สามารถดึง symbols ได้")
                return False
            
            self.logger.info(f"📊 ตรวจสอบจาก {len(all_symbols)} symbols")
            
            # ค้นหา symbols ที่ตรงกับ gold patterns
            potential_gold_symbols = []
            
            for symbol_info in all_symbols:
                symbol_name = symbol_info.name
                
                # ตรวจสอบกับ patterns
                for pattern in self.gold_patterns:
                    if re.match(pattern, symbol_name, re.IGNORECASE):
                        potential_gold_symbols.append(symbol_info)
                        break
            
            self.logger.info(f"🎯 พบ Potential Gold Symbols: {len(potential_gold_symbols)}")
            
            # วิเคราะห์แต่ละ symbol
            for symbol_info in potential_gold_symbols:
                gold_info = self._analyze_gold_symbol(symbol_info)
                if gold_info:
                    self.found_symbols.append(gold_info)
                    self.logger.info(f"✅ วิเคราะห์ {symbol_info.name} สำเร็จ")
            
            # เรียงลำดับตามคุณภาพ
            self.found_symbols.sort(key=lambda x: x.quality_score, reverse=True)
            
            # เลือก symbol ที่ดีที่สุด
            if self.found_symbols:
                self.best_symbol = self.found_symbols[0]
                self.recommended_symbol = self.best_symbol.symbol
                
                self.logger.info(f"🏆 Gold Symbol ที่แนะนำ: {self.recommended_symbol}")
                self.logger.info(f"📊 Quality Score: {self.best_symbol.quality_score:.2f}")
                self.logger.info(f"💰 Spread: {self.best_symbol.spread_points:.1f} points")
                
                return True
            else:
                self.logger.error("❌ ไม่พบ Gold Symbol ที่เหมาะสม")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถค้นหา Gold Symbols: {e}")
            return False
    
    @handle_trading_errors(ErrorCategory.MARKET_DATA, ErrorSeverity.LOW)
    def _analyze_gold_symbol(self, symbol_info) -> Optional[GoldSymbolInfo]:
        """วิเคราะห์ Gold Symbol เดี่ยว"""
        try:
            symbol_name = symbol_info.name
            
            # ดึงข้อมูล symbol detail
            if not symbol_info.visible:
                # พยายาม select symbol
                if not mt5.symbol_select(symbol_name, True):
                    self.logger.warning(f"⚠️ ไม่สามารถ select {symbol_name}")
                    return None
            
            # ดึงข้อมูล tick
            tick = mt5.symbol_info_tick(symbol_name)
            if not tick:
                self.logger.warning(f"⚠️ ไม่มี tick data สำหรับ {symbol_name}")
                return None
            
            # ตรวจสอบว่าเป็นทองจริงหรือไม่ (ราคาอยู่ในช่วงทอง)
            if not self._verify_gold_price_range(tick.bid, tick.ask):
                self.logger.warning(f"⚠️ {symbol_name} ราคาไม่ใช่ทอง")
                return None
            
            # คำนวณ spread
            spread_points = tick.ask - tick.bid
            spread_percent = (spread_points / tick.bid) * 100 if tick.bid > 0 else 0
            
            # สร้าง GoldSymbolInfo
            gold_info = GoldSymbolInfo(
                symbol=symbol_name,
                description=symbol_info.description or symbol_name,
                is_visible=symbol_info.visible,
                is_tradable=symbol_info.trade_mode != 0,
                market_open=True,  # ถ้าได้ tick มาแสดงว่าตลาดเปิด
                trade_allowed=symbol_info.trade_mode in [1, 2, 3, 4],  # Trade modes ที่อนุญาต
                volume_min=symbol_info.volume_min,
                volume_max=symbol_info.volume_max,
                volume_step=symbol_info.volume_step,
                digits=symbol_info.digits,
                point=symbol_info.point,
                current_bid=tick.bid,
                current_ask=tick.ask,
                spread_points=spread_points,
                spread_percent=spread_percent,
                server_time=datetime.now(),
                last_update=datetime.now()
            )
            
            # ประเมินคุณภาพ
            self._assess_symbol_quality(gold_info)
            
            return gold_info
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถวิเคราะห์ {symbol_info.name}: {e}")
            return None
    
    def _verify_gold_price_range(self, bid: float, ask: float) -> bool:
        """ตรวจสอบว่าราคาอยู่ในช่วงของทอง"""
        try:
            # ทองมักมีราคาอยู่ระหว่าง 1000-3000 USD
            avg_price = (bid + ask) / 2
            
            # ช่วงราคาทองที่สมเหตุสมผล
            if 1000 <= avg_price <= 5000:
                return True
            
            # ตรวจสอบราคาใน pips (บางโบรกเกอร์อาจแสดงราคาต่างกัน)
            if 100000 <= avg_price <= 500000:  # ราคาในรูปแบบ pips
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถตรวจสอบราคาทอง: {e}")
            return False
    
    def _assess_symbol_quality(self, gold_info: GoldSymbolInfo):
        """ประเมินคุณภาพของ Gold Symbol"""
        try:
            score = 0.0
            notes = []
            
            # Trading availability (40 points)
            if gold_info.is_tradable and gold_info.trade_allowed:
                score += 40
                notes.append("เทรดได้")
            else:
                notes.append("เทรดไม่ได้")
            
            # Market status (20 points)
            if gold_info.market_open:
                score += 20
                notes.append("ตลาดเปิด")
            else:
                notes.append("ตลาดปิด")
            
            # Spread quality (30 points)
            if gold_info.spread_points <= 0.3:
                score += 30
                notes.append("Spread ต่ำมาก")
            elif gold_info.spread_points <= 0.5:
                score += 25
                notes.append("Spread ต่ำ")
            elif gold_info.spread_points <= 1.0:
                score += 20
                notes.append("Spread ปานกลาง")
            elif gold_info.spread_points <= 2.0:
                score += 15
                notes.append("Spread สูง")
            else:
                score += 5
                notes.append("Spread สูงมาก")
            
            # Volume settings (10 points)
            if gold_info.volume_min <= 0.01 and gold_info.volume_max >= 1.0:
                score += 10
                notes.append("Volume ยืดหยุ่น")
            elif gold_info.volume_min <= 0.1:
                score += 5
                notes.append("Volume พอใช้")
            else:
                notes.append("Volume จำกัด")
            
            # กำหนดคุณภาพ
            if score >= 90:
                gold_info.quality = GoldSymbolQuality.EXCELLENT
            elif score >= 75:
                gold_info.quality = GoldSymbolQuality.GOOD
            elif score >= 50:
                gold_info.quality = GoldSymbolQuality.FAIR
            else:
                gold_info.quality = GoldSymbolQuality.POOR
            
            gold_info.quality_score = score
            gold_info.notes = "; ".join(notes)
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถประเมินคุณภาพ: {e}")
            gold_info.quality = GoldSymbolQuality.POOR
            gold_info.quality_score = 0.0
    
    def get_best_gold_symbol(self) -> Optional[str]:
        """ดึง Gold Symbol ที่ดีที่สุด"""
        return self.recommended_symbol if self.recommended_symbol else None
    
    def get_all_gold_symbols(self) -> List[GoldSymbolInfo]:
        """ดึง Gold Symbols ทั้งหมดที่พบ"""
        return self.found_symbols.copy()
    
    def get_symbol_details(self, symbol: str) -> Optional[GoldSymbolInfo]:
        """ดึงรายละเอียดของ Symbol เฉพาะ"""
        for gold_info in self.found_symbols:
            if gold_info.symbol == symbol:
                return gold_info
        return None
    
    def verify_symbol_trading(self, symbol: str) -> Dict[str, Any]:
        """ตรวจสอบความพร้อมในการเทรดของ Symbol"""
        try:
            # ดึงข้อมูล symbol
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return {
                    'available': False,
                    'error': 'Symbol not found'
                }
            
            # ดึงข้อมูล tick
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return {
                    'available': False,
                    'error': 'No tick data'
                }
            
            # ตรวจสอบ account
            account_info = mt5.account_info()
            if not account_info or not account_info.trade_allowed:
                return {
                    'available': False,
                    'error': 'Account not allowed to trade'
                }
            
            return {
                'available': True,
                'symbol': symbol,
                'bid': tick.bid,
                'ask': tick.ask,
                'spread': tick.ask - tick.bid,
                'volume_min': symbol_info.volume_min,
                'volume_max': symbol_info.volume_max,
                'digits': symbol_info.digits,
                'trade_mode': symbol_info.trade_mode,
                'market_open': True,
                'account_currency': account_info.currency,
                'account_balance': account_info.balance
            }
            
        except Exception as e:
            return {
                'available': False,
                'error': str(e)
            }
    
    def auto_select_best_symbol(self) -> Optional[str]:
        """เลือก Symbol ที่ดีที่สุดอัตโนมัติ"""
        try:
            if not self.detect_gold_symbols():
                return None
            
            # ถ้ามี symbols ให้เลือก
            if self.found_symbols:
                # เลือก symbol ที่ดีที่สุด
                best = self.found_symbols[0]
                
                # ตรวจสอบความพร้อมอีกครั้ง
                verification = self.verify_symbol_trading(best.symbol)
                if verification['available']:
                    self.logger.info(f"🏆 เลือก Gold Symbol: {best.symbol}")
                    self.logger.info(f"💰 Spread: {best.spread_points:.1f} points")
                    self.logger.info(f"📊 Quality: {best.quality.value}")
                    return best.symbol
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถเลือก Symbol อัตโนมัติ: {e}")
            return None
    
    def get_detection_report(self) -> Dict[str, Any]:
        """สร้างรายงานการค้นหา"""
        try:
            report = {
                'detection_time': datetime.now(),
                'symbols_found': len(self.found_symbols),
                'recommended_symbol': self.recommended_symbol,
                'symbols_detail': []
            }
            
            for gold_info in self.found_symbols:
                symbol_detail = {
                    'symbol': gold_info.symbol,
                    'description': gold_info.description,
                    'quality': gold_info.quality.value,
                    'quality_score': gold_info.quality_score,
                    'spread_points': gold_info.spread_points,
                    'spread_percent': gold_info.spread_percent,
                    'is_tradable': gold_info.is_tradable,
                    'volume_min': gold_info.volume_min,
                    'volume_max': gold_info.volume_max,
                    'current_price': gold_info.current_bid,
                    'notes': gold_info.notes
                }
                report['symbols_detail'].append(symbol_detail)
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถสร้างรายงาน: {e}")
            return {'error': str(e)}
    
    def print_detection_summary(self):
        """แสดงสรุปการค้นหา"""
        print("\n" + "🏆" * 50)
        print("🥇 GOLD SYMBOL DETECTION SUMMARY")
        print("🏆" * 50)
        
        if not self.found_symbols:
            print("❌ ไม่พบ Gold Symbol ใดๆ")
            return
        
        print(f"📊 พบ Gold Symbols: {len(self.found_symbols)} symbols")
        print(f"🎯 แนะนำ: {self.recommended_symbol}")
        
        print("\n📋 รายละเอียด Gold Symbols:")
        print("-" * 80)
        print(f"{'Symbol':<15} {'Quality':<12} {'Spread':<10} {'Tradable':<10} {'Price':<10}")
        print("-" * 80)
        
        for gold_info in self.found_symbols:
            tradable = "✅" if gold_info.is_tradable else "❌"
            print(f"{gold_info.symbol:<15} {gold_info.quality.value:<12} "
                  f"{gold_info.spread_points:<10.1f} {tradable:<10} {gold_info.current_bid:<10.2f}")
        
        print("-" * 80)
        
        if self.best_symbol:
            print(f"\n🏆 แนะนำให้ใช้: {self.best_symbol.symbol}")
            print(f"📊 คุณภาพ: {self.best_symbol.quality.value} ({self.best_symbol.quality_score:.1f}/100)")
            print(f"💰 Spread: {self.best_symbol.spread_points:.1f} points ({self.best_symbol.spread_percent:.3f}%)")
            print(f"📈 ราคาปัจจุบัน: {self.best_symbol.current_bid:.2f} / {self.best_symbol.current_ask:.2f}")
            print(f"📦 Volume: {self.best_symbol.volume_min} - {self.best_symbol.volume_max}")
            print(f"💡 หมายเหตุ: {self.best_symbol.notes}")

# ===== FACTORY FUNCTION =====

def get_gold_symbol_detector() -> GoldSymbolDetector:
    """Factory function สำหรับสร้าง Gold Symbol Detector"""
    return GoldSymbolDetector()

def auto_detect_gold_symbol() -> Optional[str]:
    """ฟังก์ชันสำหรับหา Gold Symbol อัตโนมัติ"""
    try:
        detector = GoldSymbolDetector()
        return detector.auto_select_best_symbol()
    except Exception as e:
        print(f"❌ ไม่สามารถหา Gold Symbol อัตโนมัติ: {e}")
        return None

# ===== MAIN TESTING =====

if __name__ == "__main__":
    """ทดสอบ Gold Symbol Detection"""
    
    print("🧪 ทดสอบ Gold Symbol Detection")
    print("=" * 50)
    
    try:
        # สร้าง detector
        detector = GoldSymbolDetector()
        print("✅ สร้าง Gold Symbol Detector สำเร็จ")
        
        # ค้นหา symbols
        if detector.detect_gold_symbols():
            print("✅ ค้นหา Gold Symbols สำเร็จ")
            
            # แสดงผลลัพธ์
            detector.print_detection_summary()
            
            # ทดสอบการเลือกอัตโนมัติ
            auto_symbol = detector.auto_select_best_symbol()
            if auto_symbol:
                print(f"\n🎯 Auto-selected Symbol: {auto_symbol}")
                
                # ตรวจสอบการเทรด
                verification = detector.verify_symbol_trading(auto_symbol)
                if verification['available']:
                    print("✅ Symbol พร้อมสำหรับการเทรด")
                    print(f"💰 Current Spread: {verification['spread']:.1f}")
                    print(f"📦 Volume Range: {verification['volume_min']} - {verification['volume_max']}")
                else:
                    print(f"❌ Symbol ไม่พร้อมเทรด: {verification['error']}")
            else:
                print("❌ ไม่สามารถเลือก Symbol อัตโนมัติได้")
        else:
            print("❌ ไม่สามารถค้นหา Gold Symbols ได้")
            
    except Exception as e:
        print(f"❌ ข้อผิดพลาด: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎯 การทดสอบเสร็จสิ้น")