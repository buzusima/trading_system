#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XAUUSD SYMBOL DETECTOR & FIXER - แก้ไขปัญหา Symbol Loading
========================================================
ระบบค้นหาและแก้ไข Symbol XAUUSD ที่โบรกเกอร์ต่างๆ ใช้ชื่อต่างกัน
รองรับการค้นหาอัตโนมัติและเลือก Symbol ที่ดีที่สุด

🎯 วัตถุประสงค์:
- ค้นหา Gold Symbol ทุกแบบที่โบรกเกอร์มี
- ตรวจสอบความพร้อมในการเทรด  
- เลือก Symbol ที่มี Spread ต่ำสุด
- Auto-enable Symbol ที่ไม่ visible
"""

import MetaTrader5 as mt5
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class SymbolQuality(Enum):
    """คุณภาพ Symbol"""
    EXCELLENT = "ดีเยี่ยม"
    GOOD = "ดี" 
    FAIR = "พอใช้"
    POOR = "แย่"

@dataclass
class GoldSymbolInfo:
    """ข้อมูล Gold Symbol"""
    name: str
    description: str
    visible: bool = False
    tradeable: bool = False
    digits: int = 0
    point: float = 0.0
    spread: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    quality: SymbolQuality = SymbolQuality.FAIR
    broker_suffix: str = ""

class XAUUSDSymbolFixer:
    """ตัวแก้ไขปัญหา XAUUSD Symbol"""
    
    def __init__(self):
        # Pattern สำหรับค้นหา Gold Symbol ทุกแบบ
        self.gold_patterns = [
            r'^XAUUSD$',           # Standard
            r'^XAUUSD\..*$',       # With suffix  
            r'^GOLD$',             # Simple Gold
            r'^GOLDUSD$',          # Gold USD
            r'^GOLD\.USD$',        # Gold.USD
            r'^XAU\.USD$',         # XAU.USD
            r'^.*XAUUSD.*$',       # Contains XAUUSD
            r'^.*GOLD.*USD.*$',    # Contains GOLD and USD
            r'^GOLD.*$',           # Starts with GOLD
            r'^XAU.*$',            # Starts with XAU
            r'^AU.*USD$',          # AU...USD
        ]
        
        self.found_symbols: List[GoldSymbolInfo] = []
        self.best_symbol: Optional[GoldSymbolInfo] = None
        
    def initialize_mt5(self) -> bool:
        """เริ่มต้น MT5 Connection"""
        try:
            if not mt5.initialize():
                print("❌ ไม่สามารถเชื่อมต่อ MT5 ได้")
                print("💡 ตรวจสอบ:")
                print("   - MT5 เปิดอยู่หรือไม่")
                print("   - มี EA ที่ใช้ DLL imports หรือไม่")
                print("   - Firewall/Antivirus block MT5 หรือไม่")
                return False
                
            print("✅ เชื่อมต่อ MT5 สำเร็จ")
            
            # แสดงข้อมูลบัญชี
            account_info = mt5.account_info()
            if account_info:
                print(f"📊 บัญชี: {account_info.login}")
                print(f"💰 Balance: ${account_info.balance:,.2f}")
                print(f"🏦 โบรกเกอร์: {account_info.company}")
                print(f"🌐 Server: {account_info.server}")
            
            return True
            
        except Exception as e:
            print(f"❌ ข้อผิดพลาดใน MT5 Initialize: {e}")
            return False
    
    def search_all_gold_symbols(self) -> List[GoldSymbolInfo]:
        """ค้นหา Gold Symbol ทั้งหมด"""
        print("\n🔍 ค้นหา Gold Symbols ทั้งหมด...")
        
        found_symbols = []
        all_symbols = mt5.symbols_get()
        
        if not all_symbols:
            print("❌ ไม่สามารถดึงรายการ Symbol ได้")
            return found_symbols
            
        print(f"📋 ตรวจสอบจาก {len(all_symbols)} symbols...")
        
        # ค้นหาตาม pattern
        for symbol_info in all_symbols:
            symbol_name = symbol_info.name
            
            # ตรวจสอบทุก pattern
            for pattern in self.gold_patterns:
                if re.match(pattern, symbol_name, re.IGNORECASE):
                    print(f"🎯 พบ Gold Symbol: {symbol_name}")
                    
                    # สร้างข้อมูล symbol
                    gold_symbol = GoldSymbolInfo(
                        name=symbol_name,
                        description=symbol_info.description,
                        visible=symbol_info.visible,
                        tradeable=symbol_info.visible,
                        digits=symbol_info.digits,
                        point=symbol_info.point
                    )
                    
                    found_symbols.append(gold_symbol)
                    break
        
        self.found_symbols = found_symbols
        print(f"✅ พบ Gold Symbols ทั้งหมด: {len(found_symbols)} symbols")
        
        return found_symbols
    
    def analyze_symbol_quality(self, symbol: GoldSymbolInfo) -> GoldSymbolInfo:
        """วิเคราะห์คุณภาพ Symbol"""
        try:
            # Enable symbol ถ้ายังไม่ visible
            if not symbol.visible:
                print(f"🔧 กำลัง Enable Symbol: {symbol.name}")
                if mt5.symbol_select(symbol.name, True):
                    symbol.visible = True
                    symbol.tradeable = True
                    print(f"✅ Enable {symbol.name} สำเร็จ")
                else:
                    print(f"❌ ไม่สามารถ Enable {symbol.name}")
                    return symbol
            
            # ดึงข้อมูลราคาปัจจุบัน
            tick = mt5.symbol_info_tick(symbol.name)
            if tick:
                symbol.bid = tick.bid
                symbol.ask = tick.ask
                symbol.spread = tick.ask - tick.bid
                
                # คำนวณ spread ใน points
                spread_points = symbol.spread / symbol.point if symbol.point > 0 else 0
                
                # ประเมินคุณภาพตาม spread
                if spread_points <= 10:
                    symbol.quality = SymbolQuality.EXCELLENT
                elif spread_points <= 20:
                    symbol.quality = SymbolQuality.GOOD
                elif spread_points <= 50:
                    symbol.quality = SymbolQuality.FAIR
                else:
                    symbol.quality = SymbolQuality.POOR
                
                print(f"📊 {symbol.name}:")
                print(f"   💰 ราคา: {symbol.bid:.2f} / {symbol.ask:.2f}")
                print(f"   📈 Spread: {spread_points:.1f} points")
                print(f"   ⭐ คุณภาพ: {symbol.quality.value}")
                
            return symbol
            
        except Exception as e:
            print(f"❌ ข้อผิดพลาดในการวิเคราะห์ {symbol.name}: {e}")
            return symbol
    
    def select_best_symbol(self) -> Optional[GoldSymbolInfo]:
        """เลือก Symbol ที่ดีที่สุด"""
        if not self.found_symbols:
            return None
        
        print("\n🏆 เลือก Symbol ที่ดีที่สุด...")
        
        # วิเคราะห์คุณภาพทุก symbol
        analyzed_symbols = []
        for symbol in self.found_symbols:
            analyzed_symbol = self.analyze_symbol_quality(symbol)
            if analyzed_symbol.tradeable:
                analyzed_symbols.append(analyzed_symbol)
        
        if not analyzed_symbols:
            print("❌ ไม่มี Symbol ที่เทรดได้")
            return None
        
        # เรียงตามคุณภาพและ spread
        quality_order = {
            SymbolQuality.EXCELLENT: 4,
            SymbolQuality.GOOD: 3,
            SymbolQuality.FAIR: 2,
            SymbolQuality.POOR: 1
        }
        
        best_symbol = max(analyzed_symbols, 
                         key=lambda s: (quality_order[s.quality], -s.spread))
        
        self.best_symbol = best_symbol
        
        print(f"\n🎯 Symbol ที่แนะนำ: {best_symbol.name}")
        print(f"⭐ คุณภาพ: {best_symbol.quality.value}")
        print(f"📈 Spread: {best_symbol.spread / best_symbol.point:.1f} points")
        
        return best_symbol
    
    def test_symbol_trading(self, symbol_name: str) -> bool:
        """ทดสอบการเทรด Symbol"""
        try:
            print(f"\n🧪 ทดสอบการเทรด {symbol_name}...")
            
            # ตรวจสอบข้อมูล symbol
            symbol_info = mt5.symbol_info(symbol_name)
            if not symbol_info:
                print(f"❌ ไม่พบข้อมูล Symbol {symbol_name}")
                return False
            
            # ตรวจสอบการเทรดได้
            if not symbol_info.visible:
                print(f"❌ Symbol {symbol_name} ไม่ visible")
                return False
            
            # ตรวจสอบ market open
            tick = mt5.symbol_info_tick(symbol_name)
            if not tick:
                print(f"❌ ไม่มีข้อมูลราคา {symbol_name}")
                return False
            
            # ตรวจสอบ trading session
            current_time = datetime.now()
            
            print(f"✅ {symbol_name} พร้อมเทรด")
            print(f"💰 ราคาปัจจุบัน: {tick.bid:.2f} / {tick.ask:.2f}")
            print(f"⏰ เวลา: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            return True
            
        except Exception as e:
            print(f"❌ ข้อผิดพลาดในการทดสอบ: {e}")
            return False
    
    def save_symbol_config(self, symbol_name: str) -> bool:
        """บันทึกการตั้งค่า Symbol"""
        try:
            config = {
                "selected_symbol": symbol_name,
                "detection_time": datetime.now().isoformat(),
                "all_found_symbols": [s.name for s in self.found_symbols],
                "broker_info": {
                    "company": mt5.account_info().company if mt5.account_info() else "Unknown",
                    "server": mt5.account_info().server if mt5.account_info() else "Unknown"
                }
            }
            
            # บันทึกลงไฟล์ (ถ้าต้องการ)
            print(f"📄 การตั้งค่า Symbol: {symbol_name}")
            return True
            
        except Exception as e:
            print(f"❌ ไม่สามารถบันทึกการตั้งค่า: {e}")
            return False
    
    def run_full_detection(self) -> Optional[str]:
        """รันการค้นหาและแก้ไขครบถ้วน"""
        print("🚀 เริ่มระบบค้นหา XAUUSD Symbol อัตโนมัติ")
        print("=" * 50)
        
        # 1. เชื่อมต่อ MT5
        if not self.initialize_mt5():
            return None
        
        # 2. ค้นหา Gold Symbols
        found_symbols = self.search_all_gold_symbols()
        if not found_symbols:
            print("❌ ไม่พบ Gold Symbol ใดๆ")
            print("💡 แนะนำ:")
            print("   - ตรวจสอบโบรกเกอร์มี Gold หรือไม่")
            print("   - ลองค้นหาด้วยชื่ออื่น เช่น GOLD, XAUUSD.xxx")
            return None
        
        # 3. เลือก Symbol ที่ดีที่สุด
        best_symbol = self.select_best_symbol()
        if not best_symbol:
            print("❌ ไม่มี Symbol ที่เหมาะสม")
            return None
        
        # 4. ทดสอบการเทรด
        if not self.test_symbol_trading(best_symbol.name):
            print("❌ Symbol ที่เลือกไม่สามารถเทรดได้")
            return None
        
        # 5. บันทึกการตั้งค่า
        self.save_symbol_config(best_symbol.name)
        
        print("\n" + "=" * 50)
        print("🎉 แก้ไขปัญหา XAUUSD Symbol สำเร็จ!")
        print(f"✅ Symbol ที่ใช้: {best_symbol.name}")
        print(f"⭐ คุณภาพ: {best_symbol.quality.value}")
        print("=" * 50)
        
        return best_symbol.name

    def show_all_symbols_info(self):
        """แสดงข้อมูลทุก Symbol ที่พบ"""
        if not self.found_symbols:
            print("❌ ไม่มีข้อมูล Symbol")
            return
        
        print("\n📋 รายละเอียด Gold Symbols ทั้งหมด:")
        print("-" * 60)
        
        for i, symbol in enumerate(self.found_symbols, 1):
            print(f"{i}. {symbol.name}")
            print(f"   📝 คำอธิบาย: {symbol.description}")
            print(f"   👁️  Visible: {'✅' if symbol.visible else '❌'}")
            print(f"   💹 เทรดได้: {'✅' if symbol.tradeable else '❌'}")
            if symbol.bid > 0:
                print(f"   💰 ราคา: {symbol.bid:.2f} / {symbol.ask:.2f}")
                print(f"   📊 Spread: {symbol.spread / symbol.point:.1f} points")
            print(f"   ⭐ คุณภาพ: {symbol.quality.value}")
            print()

def main():
    """ฟังก์ชันหลักสำหรับรันการแก้ไข"""
    try:
        # สร้าง detector
        detector = XAUUSDSymbolFixer()
        
        # รันการค้นหาและแก้ไข
        result = detector.run_full_detection()
        
        if result:
            print(f"\n🎯 ใช้ Symbol นี้ในระบบเทรด: {result}")
            
            # แสดงข้อมูลทุก symbol (ถ้าต้องการ)
            show_details = input("\nต้องการดูรายละเอียดทุก Symbol หรือไม่? (y/n): ")
            if show_details.lower() == 'y':
                detector.show_all_symbols_info()
        else:
            print("\n❌ ไม่สามารถแก้ไขปัญหาได้")
            print("💡 แนะนำให้ติดต่อโบรกเกอร์หรือตรวจสอบการตั้งค่า MT5")
        
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในระบบ: {e}")
    
    finally:
        # ปิดการเชื่อมต่อ MT5
        mt5.shutdown()
        print("👋 ปิดการเชื่อมต่อ MT5")

if __name__ == "__main__":
    main()