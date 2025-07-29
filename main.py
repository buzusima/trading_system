#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELLIGENT GOLD TRADING SYSTEM - MAIN ENTRY POINT (REAL ONLY)
==============================================================
ไฟล์หลักสำหรับเริ่มต้นระบบเทรด Gold แบบ Live Trading เท่านั้น
ลบ Mock และ Simulation ทั้งหมด - ใช้ MT5 จริงเท่านั้น

🚨 ข้อกำหนดสำคัญ:
- Live Trading เท่านั้น ไม่มี Demo/Simulation
- ต้องมี MT5 และ Live Account
- ใช้เงินจริงในการเทรด
- ไม่มี Mock Components ใดๆ

🎯 การทำงาน:
1. ตรวจสอบ MT5 Connection
2. โหลด Real Components เท่านั้น
3. เริ่ม Live Trading System
4. เปิด GUI สำหรับควบคุม
"""

import sys
import os
import traceback
from pathlib import Path

# เพิ่ม project root เข้า sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_mt5_requirements():
   """ตรวจสอบความพร้อมของ MT5 และหา Gold Symbol อัตโนมัติ"""
   print("🔍 ตรวจสอบ MT5 Requirements และ Gold Symbols...")
   
   try:
       import MetaTrader5 as mt5
       print("✅ MetaTrader5 module พร้อมใช้งาน")
       
       # ทดสอบเชื่อมต่อ
       if not mt5.initialize():
           print("❌ ไม่สามารถเชื่อมต่อ MT5 ได้")
           print("📋 ตรวจสอบ:")
           print("   - MT5 เปิดอยู่หรือไม่")
           print("   - Login เข้า Account แล้วหรือไม่")
           print("   - Account เป็น Live Account หรือไม่")
           return False
       
       # ตรวจสอบ account info
       account_info = mt5.account_info()
       if not account_info:
           print("❌ ไม่สามารถดึงข้อมูล Account ได้")
           mt5.shutdown()
           return False
       
       # ตรวจสอบ trading permission
       if not account_info.trade_allowed:
           print("❌ Account ไม่อนุญาตให้เทรด")
           mt5.shutdown()
           return False
       
       # แสดงข้อมูล account
       print(f"✅ Account Connected: {account_info.login}")
       print(f"📊 Server: {account_info.server}")
       print(f"💰 Balance: {account_info.balance:.2f} {account_info.currency}")
       print(f"💰 Equity: {account_info.equity:.2f}")
       print(f"✅ Trade Allowed: {account_info.trade_allowed}")
       
       # ===== AUTO-DETECT GOLD SYMBOL =====
       print("\n🔍 กำลังหา Gold Symbol อัตโนมัติ...")
       
       try:
           from mt5_integration.gold_symbol_detector import GoldSymbolDetector
           
           # สร้าง detector
           detector = GoldSymbolDetector()
           
           # ค้นหา gold symbols
           if detector.detect_gold_symbols():
               print(f"🎯 พบ Gold Symbols: {len(detector.found_symbols)} symbols")
               
               # แสดงรายการ symbols ที่พบ
               print("\n📋 Gold Symbols ที่พบ:")
               for i, gold_info in enumerate(detector.found_symbols[:5], 1):  # แสดง 5 อันดับแรก
                   status = "✅" if gold_info.is_tradable else "❌"
                   print(f"   {i}. {gold_info.symbol:<12} - Spread: {gold_info.spread_points:<6.1f} - Quality: {gold_info.quality.value} {status}")
               
               # แสดง symbol ที่แนะนำ
               if detector.best_symbol:
                   print(f"\n🏆 แนะนำให้ใช้: {detector.best_symbol.symbol}")
                   print(f"💰 Spread: {detector.best_symbol.spread_points:.1f} points")
                   print(f"📊 Quality: {detector.best_symbol.quality.value}")
                   print(f"📈 ราคาปัจจุบัน: {detector.best_symbol.current_bid:.2f} / {detector.best_symbol.current_ask:.2f}")
                   
                   # ตรวจสอบการเทรดอีกครั้ง
                   verification = detector.verify_symbol_trading(detector.best_symbol.symbol)
                   if verification['available']:
                       print("✅ Symbol พร้อมสำหรับการเทรดจริง")
                   else:
                       print(f"❌ Symbol ไม่พร้อมเทรด: {verification['error']}")
                       return False
               else:
                   print("❌ ไม่พบ Gold Symbol ที่เหมาะสม")
                   return False
           else:
               print("❌ ไม่สามารถค้นหา Gold Symbols ได้")
               return False
               
       except Exception as e:
           print(f"⚠️ ไม่สามารถใช้ Gold Symbol Detector: {e}")
           print("🔄 ตรวจสอบ XAUUSD แบบ manual...")
           
           # ตรวจสอบ XAUUSD แบบ manual
           symbol_info = mt5.symbol_info("XAUUSD.v")
           if not symbol_info:
               print("❌ ไม่พบ Symbol XAUUSD")
               
               # ลองหา GOLD
               symbol_info = mt5.symbol_info("GOLD")
               if symbol_info:
                   print("✅ พบ Symbol GOLD")
               else:
                   print("❌ ไม่พบ Symbol GOLD")
                   mt5.shutdown()
                   return False
           else:
               print("✅ พบ Symbol XAUUSD")
           
           if not symbol_info.visible:
               symbol_name = symbol_info.name
               if not mt5.symbol_select(symbol_name, True):
                   print(f"❌ ไม่สามารถเลือก Symbol {symbol_name}")
                   mt5.shutdown()
                   return False
           
           # ตรวจสอบ market status
           tick = mt5.symbol_info_tick(symbol_info.name)
           if tick:
               print(f"📈 {symbol_info.name} Price: {tick.bid:.2f} / {tick.ask:.2f}")
               print(f"📊 Spread: {(tick.ask - tick.bid):.2f}")
           else:
               print(f"❌ ไม่สามารถดึงราคา {symbol_info.name}")
               mt5.shutdown()
               return False
       
       mt5.shutdown()
       return True
       
   except ImportError:
       print("❌ ไม่พบ MetaTrader5 module")
       print("📋 ติดตั้งโดย: pip install MetaTrader5")
       return False
   except Exception as e:
       print(f"❌ ข้อผิดพลาดใน MT5: {e}")
       return False

def check_system_dependencies():
   """ตรวจสอบ dependencies ของระบบ"""
   print("\n🔍 ตรวจสอบ System Dependencies...")
   
   required_modules = [
       'threading',
       'datetime', 
       'json',
       'queue',
       'tkinter',
       'pandas',
       'numpy'
   ]
   
   missing_modules = []
   
   for module_name in required_modules:
       try:
           __import__(module_name)
           print(f"✅ {module_name}")
       except ImportError:
           missing_modules.append(module_name)
           print(f"❌ {module_name}")
   
   if missing_modules:
       print(f"\n❌ ขาด modules: {missing_modules}")
       print("📋 ติดตั้งโดย: pip install pandas numpy")
       return False
   
   return True

def load_real_trading_system():
   """โหลด Real Trading System พร้อม Auto Gold Symbol"""
   print("\n🚀 กำลังโหลด Real Trading System...")
   
   try:
       # Import core system
       from core_system.trading_system import get_real_trading_system
       
       # แสดงข้อมูล Gold Symbol ที่จะใช้
       from config.trading_params import get_current_gold_symbol
       current_symbol = get_current_gold_symbol()
       print(f"🎯 Gold Symbol ที่ใช้: {current_symbol}")
       
       # สร้าง trading system
       trading_system = get_real_trading_system()
       print("✅ สร้าง Real Trading System สำเร็จ")
       
       # เริ่มต้นระบบ
       if not trading_system.initialize_system():
           print("❌ ไม่สามารถเริ่มต้นระบบได้")
           return None
       
       print("✅ เริ่มต้นระบบสำเร็จ")
       print(f"💡 ระบบพร้อมเทรด {current_symbol}")
       return trading_system
       
   except Exception as e:
       print(f"❌ ไม่สามารถโหลด Trading System: {e}")
       traceback.print_exc()
       return None

def load_gui_system(trading_system):
   """โหลด GUI System"""
   print("\n🖥️ กำลังโหลด GUI System...")
   
   try:
       # Import GUI
       from gui_system.main_window import create_main_window
       
       # สร้าง main window
       main_window = create_main_window(trading_system)
       print("✅ สร้าง GUI สำเร็จ")
       
       return main_window
       
   except Exception as e:
       print(f"❌ ไม่สามารถโหลด GUI: {e}")
       print("⚠️ ระบบจะทำงานแบบ Console เท่านั้น")
       return None

def console_interface(trading_system):
   """Interface แบบ Console สำหรับควบคุมระบบ"""
   # ดึงข้อมูล symbol ปัจจุบัน
   from config.trading_params import get_current_gold_symbol, get_trading_parameters
   
   print("\n" + "=" * 60)
   print("🎯 INTELLIGENT GOLD TRADING SYSTEM - CONSOLE MODE")
   print("=" * 60)
   print("⚠️ LIVE TRADING MODE - ใช้เงินจริง")
   
   # แสดงข้อมูล Symbol
   current_symbol = get_current_gold_symbol()
   params = get_trading_parameters()
   symbol_info = params.get_symbol_info()
   
   print(f"🥇 Trading Symbol: {current_symbol}")
   print(f"🔍 Auto-detect: {'เปิด' if symbol_info['auto_detect_enabled'] else 'ปิด'}")
   print(f"✅ Verified: {'ใช่' if symbol_info['symbol_verified'] else 'ไม่'}")
   
   print("\n📋 Commands:")
   print("   start    - เริ่มการเทรด")
   print("   stop     - หยุดการเทรด") 
   print("   status   - แสดงสถานะ")
   print("   stats    - แสดงสถิติ")
   print("   symbol   - แสดงข้อมูล Symbol")
   print("   detect   - หา Gold Symbol ใหม่")
   print("   set <symbol> - กำหนด Symbol (เช่น: set GOLD)")
   print("   quit     - ออกจากระบบ")
   print("=" * 60)
   
   while True:
       try:
           command_input = input(f"\n🎯 Command [{current_symbol}]: ").strip()
           command_parts = command_input.split()
           command = command_parts[0].lower() if command_parts else ""
           
           if command == "start":
               print("🚀 กำลังเริ่มการเทรด...")
               if trading_system.start_trading():
                   print(f"✅ เริ่มการเทรด {current_symbol} สำเร็จ")
                   print("⚠️ ระบบกำลังเทรดด้วยเงินจริง!")
               else:
                   print("❌ ไม่สามารถเริ่มการเทรดได้")
           
           elif command == "stop":
               print("⏹️ กำลังหยุดการเทรด...")
               if trading_system.stop_trading():
                   print("✅ หยุดการเทรดสำเร็จ")
               else:
                   print("❌ ไม่สามารถหยุดการเทรดได้")
           
           elif command == "status":
               status = trading_system.get_system_status()
               print(f"\n📊 System Status: {status.get('system_state', 'UNKNOWN')}")
               print(f"🔄 Trading Active: {status.get('trading_active', False)}")
               print(f"⏱️ Uptime: {status.get('uptime', 0):.0f} seconds")
               print(f"🔌 MT5 Connected: {status.get('mt5_connected', False)}")
               
               account_info = status.get('account_info', {})
               print(f"💰 Balance: {account_info.get('balance', 0):.2f}")
               print(f"💰 Equity: {account_info.get('equity', 0):.2f}")
               print(f"📍 Positions: {status.get('position_count', 0)}")
               print(f"🎯 Trading Symbol: {current_symbol}")
           
           elif command == "stats":
               stats = trading_system.get_trading_statistics()
               print(f"\n📈 Trading Statistics for {current_symbol}:")
               
               if 'signals' in stats:
                   signals = stats['signals']
                   print(f"🎯 Total Signals: {signals.get('total_signals', 0)}")
                   print(f"✅ Executed: {signals.get('signals_executed', 0)}")
                   print(f"❌ Rejected: {signals.get('signals_rejected', 0)}")
                   print(f"📊 Success Rate: {signals.get('success_rate', 0):.2%}")
               
               if 'executions' in stats:
                   executions = stats['executions']
                   print(f"⚡ Total Orders: {executions.get('total_orders', 0)}")
                   print(f"📊 Volume Traded: {executions.get('total_volume', 0):.2f}")
           
           elif command == "symbol":
               # แสดงข้อมูล symbol ปัจจุบัน
               symbol_info = params.get_symbol_info()
               print(f"\n🥇 Symbol Information:")
               print(f"🎯 Primary Symbol: {symbol_info['primary_symbol']}")
               print(f"🔍 Auto-detect Enabled: {symbol_info['auto_detect_enabled']}")
               print(f"✅ Symbol Verified: {symbol_info['symbol_verified']}")
               print(f"⏰ Last Detection: {symbol_info['last_detection_time']}")
               print(f"📝 Notes: {symbol_info['detection_notes']}")
               
               # ตรวจสอบ symbol ปัจจุบันใน MT5
               try:
                   import MetaTrader5 as mt5
                   if mt5.initialize():
                       symbol_mt5 = mt5.symbol_info(current_symbol)
                       if symbol_mt5:
                           tick = mt5.symbol_info_tick(current_symbol)
                           if tick:
                               print(f"📈 Current Price: {tick.bid:.2f} / {tick.ask:.2f}")
                               print(f"📊 Spread: {(tick.ask - tick.bid):.2f}")
                       mt5.shutdown()
               except Exception as e:
                   print(f"⚠️ ไม่สามารถดึงข้อมูล live: {e}")
           
           elif command == "detect":
               print("🔍 กำลังหา Gold Symbol ใหม่...")
               from config.trading_params import force_symbol_detection
               new_symbol = force_symbol_detection()
               if new_symbol:
                   current_symbol = new_symbol
                   print(f"✅ พบ Symbol ใหม่: {new_symbol}")
               else:
                   print("❌ ไม่พบ Symbol ใหม่")
           
           elif command == "set" and len(command_parts) >= 2:
               new_symbol = command_parts[1].upper()
               print(f"🔄 กำลังเปลี่ยนเป็น Symbol: {new_symbol}")
               if params.set_symbol(new_symbol, verify=True):
                   current_symbol = new_symbol
                   print(f"✅ เปลี่ยน Symbol เป็น: {new_symbol}")
               else:
                   print(f"❌ ไม่สามารถใช้ Symbol: {new_symbol}")
           
           elif command == "quit":
               print("👋 กำลังออกจากระบบ...")
               if trading_system.trading_active:
                   print("⏹️ หยุดการเทรดก่อนออก...")
                   trading_system.stop_trading()
               print("✅ ออกจากระบบสำเร็จ")
               break
           
           elif command == "help":
               print("📋 Available Commands:")
               print("   start        - เริ่มการเทรด")
               print("   stop         - หยุดการเทรด") 
               print("   status       - แสดงสถานะ")
               print("   stats        - แสดงสถิติ")
               print("   symbol       - แสดงข้อมูล Symbol")
               print("   detect       - หา Gold Symbol ใหม่")
               print("   set <symbol> - กำหนด Symbol")
               print("   quit         - ออกจากระบบ")
           
           else:
               print("❌ Command ไม่ถูกต้อง (ใช้ 'help' เพื่อดู commands)")
               
       except KeyboardInterrupt:
           print("\n\n👋 Ctrl+C ตรวจพบ - กำลังออกจากระบบ...")
           if trading_system.trading_active:
               trading_system.stop_trading()
           break
       except Exception as e:
           print(f"❌ ข้อผิดพลาด: {e}")

def show_startup_warning():
   """แสดงคำเตือนก่อนเริ่มระบบ"""
   print("\n" + "🚨" * 20)
   print("⚠️  LIVE GOLD TRADING SYSTEM WARNING  ⚠️")
   print("🚨" * 20)
   print("ระบบนี้จะทำการเทรดทอง (Gold) ด้วยเงินจริงใน MT5 Live Account")
   print("ระบบจะหานามสกุลทอง (XAUUSD, GOLD, etc.) อัตโนมัติจากโบรกเกอร์")
   print("ไม่มีโหมด Demo หรือ Simulation")
   print("การเทรดทองมีความเสี่ยงสูง - อาจสูญเสียเงินทุน")
   print("กรุณาใช้ด้วยความระมัดระวัง")
   print("🚨" * 20)
   
   response = input("\nคุณยืนยันที่จะใช้ระบบ Live Gold Trading? (yes/no): ")
   if response.lower() not in ['yes', 'y', 'ใช่']:
       print("❌ ยกเลิกการเริ่มระบบ")
       return False
   
   return True

def main():
   """ฟังก์ชันหลัก"""
   print("🚀 INTELLIGENT GOLD TRADING SYSTEM")
   print("🎯 Live Trading Mode Only")
   print("=" * 50)
   
   try:
       # แสดงคำเตือน
       if not show_startup_warning():
           return
       
       # ตรวจสอบ system dependencies
       if not check_system_dependencies():
           print("\n❌ System dependencies ไม่ครบ")
           return
       
       # ตรวจสอบ MT5 (บังคับ)
       if not check_mt5_requirements():
           print("\n❌ MT5 requirements ไม่ครบ")
           print("📋 กรุณา:")
           print("   1. ติดตั้ง MetaTrader 5")
           print("   2. เปิด MT5 และ Login เข้า Live Account")
           print("   3. ตรวจสอบว่า Account อนุญาตให้เทรด")
           return
       
       # โหลด Real Trading System
       trading_system = load_real_trading_system()
       if not trading_system:
           print("\n❌ ไม่สามารถโหลด Trading System ได้")
           return
       
       # พยายามโหลด GUI
       main_window = load_gui_system(trading_system)
       
       if main_window:
           # เริ่ม GUI Mode
           print("\n🖥️ เริ่ม GUI Mode...")
           print("⚠️ ปิด GUI เพื่อหยุดระบบ")
           
           try:
               main_window.mainloop()
           except KeyboardInterrupt:
               print("\n👋 Keyboard interrupt - หยุดระบบ")
           finally:
               if trading_system.trading_active:
                   trading_system.stop_trading()
       else:
           # เริ่ม Console Mode
           print("\n💻 เริ่ม Console Mode...")
           console_interface(trading_system)
       
       print("\n✅ ระบบปิดสมบูรณ์")
       
   except Exception as e:
       print(f"\n❌ ข้อผิดพลาดร้ายแรง: {e}")
       traceback.print_exc()
       
   finally:
       # Cleanup
       try:
           import MetaTrader5 as mt5
           mt5.shutdown()
           print("🔌 ปิดการเชื่อมต่อ MT5")
       except:
           pass

if __name__ == "__main__":
   main()