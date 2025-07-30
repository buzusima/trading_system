#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELLIGENT GOLD TRADING SYSTEM - MAIN ENTRY POINT with GUI
==========================================================
จุดเริ่มต้นหลักของระบบเทรดทองอัจฉริยะพร้อม GUI Interface
แก้ไขปัญหา XAUUSD Symbol Loading Error และเปิด GUI
"""

import sys
import os
import time
import threading
from datetime import datetime
from pathlib import Path

# เพิ่ม path สำหรับ imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# Core imports
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("⚠️ MetaTrader5 module ไม่พร้อมใช้งาน")

# GUI imports
try:
    import tkinter as tk
    from gui_system.main_window import TradingSystemGUI
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("⚠️ GUI system ไม่พร้อมใช้งาน")

# System imports
try:
    from market_intelligence.market_analyzer import MarketAnalyzer
    from adaptive_entries.strategy_selector import StrategySelector
    from intelligent_recovery.recovery_selector import RecoverySelector
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ บาง Components ไม่พร้อม: {e}")
    COMPONENTS_AVAILABLE = False

class IntelligentTradingSystem:
    """ระบบเทรดทองอัจฉริยะหลัก"""
    
    def __init__(self):
        self.symbol = None
        self.components = {}
        self.gui = None
        self.is_running = False
        
    def initialize_system(self):
        """เริ่มต้นระบบ"""
        print("🚀 INTELLIGENT GOLD TRADING SYSTEM v2.0")
        print("=" * 50)
        
        # 1. เชื่อมต่อ MT5
        if not self._connect_mt5():
            return False
        
        # 2. ค้นหา Gold Symbol
        symbol = self._detect_gold_symbol()
        if not symbol:
            return False
        
        self.symbol = symbol
        
        # 3. โหลด Components
        if COMPONENTS_AVAILABLE:
            self._load_components()
        
        print("✅ ระบบเริ่มต้นสำเร็จ")
        return True
    
    def _connect_mt5(self):
        """เชื่อมต่อ MT5"""
        if not MT5_AVAILABLE:
            print("❌ MetaTrader5 module ไม่พร้อมใช้งาน")
            return False
        
        if not mt5.initialize():
            print("❌ ไม่สามารถเชื่อมต่อ MT5 ได้")
            return False
        
        print("✅ เชื่อมต่อ MT5 สำเร็จ")
        
        # แสดงข้อมูลบัญชี
        account_info = mt5.account_info()
        if account_info:
            print(f"📊 บัญชี: {account_info.login}")
            print(f"💰 Balance: ${account_info.balance:,.2f}")
            print(f"🏦 โบรกเกอร์: {account_info.company}")
        
        return True
    
    def _detect_gold_symbol(self):
        """ค้นหา Gold Symbol"""
        print("🔍 กำลังค้นหา Gold Symbol...")
        
        gold_symbols = [
            "XAUUSD", "XAUUSD.v", "XAUUSD.a", "XAUUSD.c", "XAUUSD.e",
            "XAUUSD.m", "GOLD", "GOLDUSD", "GOLD.USD", "XAU.USD"
        ]
        
        for symbol in gold_symbols:
            try:
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info:
                    # Enable symbol ถ้าไม่ visible
                    if not symbol_info.visible:
                        mt5.symbol_select(symbol, True)
                    
                    # ตรวจสอบราคา
                    tick = mt5.symbol_info_tick(symbol)
                    if tick and tick.bid > 0:
                        print(f"🎯 พบ Symbol: {symbol}")
                        print(f"💰 ราคา: {tick.bid:.2f} / {tick.ask:.2f}")
                        return symbol
            except:
                continue
        
        print("❌ ไม่พบ Gold Symbol")
        return None
    
    def _load_components(self):
        """โหลด Components"""
        print("🔧 กำลังโหลด Components...")
        
        try:
            # Market Analyzer
            self.components['market_analyzer'] = MarketAnalyzer(self.symbol)
            print("✅ Market Analyzer โหลดสำเร็จ")
            
            # Strategy Selector
            self.components['strategy_selector'] = StrategySelector(self.symbol)
            print("✅ Strategy Selector โหลดสำเร็จ")
            
            # Recovery Selector
            self.components['recovery_selector'] = RecoverySelector(self.symbol)
            print("✅ Recovery Selector โหลดสำเร็จ")
            
        except Exception as e:
            print(f"⚠️ ข้อผิดพลาดในการโหลด Components: {e}")
    
    def start_gui(self):
        """เริ่ม GUI Interface"""
        if not GUI_AVAILABLE:
            print("❌ GUI System ไม่พร้อมใช้งาน")
            return False
        
        try:
            print("🖥️ กำลังเปิด GUI Interface...")
            
            # สร้าง GUI
            self.gui = TradingSystemGUI(
                trading_system=self,
                symbol=self.symbol,
                components=self.components
            )
            
            print("✅ GUI เริ่มต้นสำเร็จ")
            print("💡 ใช้ GUI เพื่อควบคุมระบบเทรด")
            
            # เริ่ม GUI mainloop
            self.gui.root.mainloop()
            
            return True
            
        except Exception as e:
            print(f"❌ ข้อผิดพลาดใน GUI: {e}")
            return False
    
    def start_console_mode(self):
        """เริ่มโหมด Console"""
        print("💻 เริ่มโหมด Console...")
        print("📊 กำลังติดตาม", self.symbol)
        
        try:
            for i in range(20):  # รัน 20 รอบ
                if self.symbol and MT5_AVAILABLE:
                    tick = mt5.symbol_info_tick(self.symbol)
                    if tick:
                        time_str = datetime.now().strftime('%H:%M:%S')
                        print(f"💰 {time_str} | {self.symbol}: {tick.bid:.2f}/{tick.ask:.2f}")
                
                time.sleep(3)  # รอ 3 วินาที
                
        except KeyboardInterrupt:
            print("\n👋 หยุดระบบด้วย Ctrl+C")
    
    def shutdown(self):
        """ปิดระบบ"""
        print("🔄 กำลังปิดระบบ...")
        
        self.is_running = False
        
        if MT5_AVAILABLE:
            mt5.shutdown()
            print("✅ ปิดการเชื่อมต่อ MT5")
        
        print("👋 ปิดระบบเรียบร้อย")

def main():
    """ฟังก์ชันหลัก"""
    system = IntelligentTradingSystem()
    
    try:
        # เริ่มต้นระบบ
        if not system.initialize_system():
            print("❌ ไม่สามารถเริ่มต้นระบบได้")
            return
        
        print("\n" + "=" * 50)
        print("🎯 เลือกโหมดการทำงาน:")
        print("1. GUI Mode (แนะนำ)")
        print("2. Console Mode")
        print("=" * 50)
        
        # ถาม user ต้องการโหมดไหน
        try:
            choice = input("เลือก (1/2) [ค่าเริ่มต้น: 1]: ").strip()
            if not choice:
                choice = "1"
        except:
            choice = "1"
        
        if choice == "1":
            # GUI Mode
            if not system.start_gui():
                print("❌ GUI ไม่สามารถเริ่มได้ - เปลี่ยนเป็น Console Mode")
                system.start_console_mode()
        else:
            # Console Mode
            system.start_console_mode()
    
    except KeyboardInterrupt:
        print("\n👋 หยุดระบบด้วย Ctrl+C")
    except Exception as e:
        print(f"❌ ข้อผิดพลาด: {e}")
    finally:
        system.shutdown()

if __name__ == "__main__":
    main()