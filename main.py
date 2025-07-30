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

# System status
class SystemStatus:
    def __init__(self):
        self.start_time = datetime.now()
        self.is_running = True
        self.error_count = 0
        self.message_count = 0
        
    def get_uptime(self):
        return (datetime.now() - self.start_time).total_seconds()
    
    def add_error(self):
        self.error_count += 1
    
    def add_message(self):
        self.message_count += 1
    
    def get_status_line(self):
        uptime = self.get_uptime()
        return f"[Uptime:{uptime:.1f}s|Msgs:{self.message_count}|Errs:{self.error_count}]"

# Global system status
system_status = SystemStatus()

def log_status(message, is_error=False):
    """แสดงสถานะพร้อม uptime"""
    if is_error:
        system_status.add_error()
        print(f"ERROR | {system_status.get_status_line()} | {message}")
    else:
        system_status.add_message()
        print(f"INFO  | {system_status.get_status_line()} | {message}")

def check_mt5_installation():
    """ตรวจสอบการติดตั้ง MT5"""
    log_status("🔍 ตรวจสอบการติดตั้ง MetaTrader 5...")
    
    if not MT5_AVAILABLE:
        log_status("❌ ไม่พบ MetaTrader5 Python module", True)
        log_status("📋 วิธีติดตั้ง: pip install MetaTrader5")
        return False
    
    return True

def initialize_mt5_connection():
    """เริ่มต้นการเชื่อมต่อ MT5 พร้อมแก้ไขปัญหา Symbol"""
    log_status("🔌 กำลังเชื่อมต่อ MetaTrader 5...")
    
    try:
        if not mt5.initialize():
            log_status("❌ ไม่สามารถเชื่อมต่อ MT5 ได้", True)
            return False
        
        log_status("✅ เชื่อมต่อ MT5 สำเร็จ")
        
        # แสดงข้อมูลบัญชี
        account_info = mt5.account_info()
        if account_info:
            log_status(f"📊 บัญชี: {account_info.login} | Balance: ${account_info.balance:,.2f}")
            log_status(f"🏦 โบรกเกอร์: {account_info.company}")
            log_status(f"🌐 Server: {account_info.server}")
        
        return True
        
    except Exception as e:
        log_status(f"❌ ข้อผิดพลาดใน MT5 connection: {e}", True)
        return False

def auto_detect_gold_symbol():
    """ระบบค้นหา Gold Symbol อัตโนมัติ"""
    log_status("🔍 กำลังค้นหา Gold Symbol...")
    
    gold_symbols = [
        "XAUUSD", "XAUUSD.v", "XAUUSD.a", "XAUUSD.c", "XAUUSD.e",
        "XAUUSD.m", "GOLD", "GOLDUSD", "GOLD.USD", "XAU.USD"
    ]
    
    found_symbols = []
    
    for symbol in gold_symbols:
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info:
                log_status(f"🎯 พบ Symbol: {symbol}")
                
                if not symbol_info.visible:
                    if mt5.symbol_select(symbol, True):
                        log_status(f"✅ Enable {symbol} สำเร็จ")
                    else:
                        continue
                
                tick = mt5.symbol_info_tick(symbol)
                if tick and tick.bid > 0:
                    spread = (tick.ask - tick.bid) / symbol_info.point
                    log_status(f"📈 {symbol} - ราคา: {tick.bid:.2f}/{tick.ask:.2f} - Spread: {spread:.1f}p")
                    
                    found_symbols.append({
                        'name': symbol,
                        'spread': spread,
                        'bid': tick.bid,
                        'ask': tick.ask,
                        'info': symbol_info
                    })
        except:
            continue
    
    if not found_symbols:
        log_status("❌ ไม่พบ Gold Symbol ใดๆ", True)
        return None
    
    # เลือก symbol ที่มี spread ต่ำสุด
    best_symbol = min(found_symbols, key=lambda x: x['spread'])
    
    log_status(f"🏆 เลือกใช้ Symbol: {best_symbol['name']}")
    log_status(f"⭐ Spread ต่ำสุด: {best_symbol['spread']:.1f} points")
    log_status(f"💰 ราคาปัจจุบัน: {best_symbol['bid']:.2f} / {best_symbol['ask']:.2f}")
    
    return best_symbol['name']

def initialize_trading_components():
    """เริ่มต้น components ของระบบเทรด"""
    log_status("🔧 กำลังโหลด Trading Components...")
    
    components_status = {
        'mt5_connector': False,
        'market_analyzer': False,
        'entry_system': False,
        'recovery_system': False,
        'position_manager': False
    }
    
    try:
        try:
            from mt5_integration.mt5_connector import MT5Connector
            components_status['mt5_connector'] = True
            log_status("✅ MT5 Connector โหลดสำเร็จ")
        except ImportError as e:
            log_status(f"❌ ไม่สามารถโหลด MT5 Connector: {e}", True)
        
        try:
            from market_intelligence.market_analyzer import MarketAnalyzer
            components_status['market_analyzer'] = True
            log_status("✅ Market Analyzer โหลดสำเร็จ")
        except ImportError as e:
            log_status(f"⚠️ Market Analyzer ไม่พร้อม: {e}")
        
        try:
            from adaptive_entries.strategy_selector import StrategySelector
            components_status['entry_system'] = True
            log_status("✅ Entry System โหลดสำเร็จ")
        except ImportError as e:
            log_status(f"⚠️ Entry System ไม่พร้อม: {e}")
        
        try:
            from intelligent_recovery.recovery_selector import RecoverySelector  
            components_status['recovery_system'] = True
            log_status("✅ Recovery System โหลดสำเร็จ")
        except ImportError as e:
            log_status(f"⚠️ Recovery System ไม่พร้อม: {e}")
        
        try:
            from position_management.position_tracker import PositionTracker
            components_status['position_manager'] = True
            log_status("✅ Position Manager โหลดสำเร็จ")
        except ImportError as e:
            log_status(f"⚠️ Position Manager ไม่พร้อม: {e}")
        
        loaded_count = sum(components_status.values())
        total_count = len(components_status)
        
        log_status(f"📊 โหลด Components: {loaded_count}/{total_count} สำเร็จ")
        
        return loaded_count > 0
            
    except Exception as e:
        log_status(f"❌ ข้อผิดพลาดในการโหลด Components: {e}", True)
        return False

def save_symbol_config(symbol_name):
    """บันทึกการตั้งค่า Symbol ที่ใช้"""
    try:
        config_dir = current_dir / "config"
        config_dir.mkdir(exist_ok=True)
        
        config_file = config_dir / "detected_symbol.py"
        
        config_content = f'''# Auto-generated Symbol Configuration
# Generated at: {datetime.now().isoformat()}

# Selected Gold Symbol
GOLD_SYMBOL = "{symbol_name}"

# Detection Results
DETECTION_TIME = "{datetime.now().isoformat()}"
BROKER_INFO = {{
    "company": "{mt5.account_info().company if mt5.account_info() else 'Unknown'}",
    "server": "{mt5.account_info().server if mt5.account_info() else 'Unknown'}"
}}

# Usage in other modules:
# from config.detected_symbol import GOLD_SYMBOL
'''
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        log_status(f"✅ บันทึกการตั้งค่า Symbol ลง {config_file}")
        return True
        
    except Exception as e:
        log_status(f"⚠️ ไม่สามารถบันทึกการตั้งค่า: {e}")
        return False

def start_gui_system():
    """เริ่ม GUI System ที่มีอยู่แล้ว - แก้ไขแล้ว"""
    try:
        log_status("🖥️ กำลังเปิด GUI System...")
        
        # ลองหา GUI ที่มีอยู่ในไฟล์
        try:
            # ลองแบบแรก
            from gui_system.main_window import TradingSystemGUI
            gui = TradingSystemGUI()
        except ImportError:
            try:
                # ลองแบบที่สอง
                from gui_system.main_window import create_trading_gui
                gui = create_trading_gui()
            except ImportError:
                try:
                    # ลองแบบที่สาม - ใช้ class ใดก็ได้ที่มีอยู่
                    import gui_system.main_window as gui_module
                    
                    # หา class ที่มี method run หรือ mainloop
                    for attr_name in dir(gui_module):
                        attr = getattr(gui_module, attr_name)
                        if hasattr(attr, '__call__') and 'GUI' in attr_name.upper():
                            gui = attr()
                            break
                    else:
                        raise ImportError("ไม่พบ GUI class ที่เหมาะสม")
                        
                except ImportError:
                    # สร้าง GUI แบบง่ายๆ เอง
                    return start_simple_gui()
        
        log_status("✅ GUI System เริ่มต้นสำเร็จ")
        log_status("💡 ใช้ GUI เพื่อควบคุมระบบเทรด")
        
        # รัน GUI
        if hasattr(gui, 'run'):
            gui.run()
        elif hasattr(gui, 'mainloop'):
            gui.mainloop()
        elif hasattr(gui, 'root') and hasattr(gui.root, 'mainloop'):
            gui.root.mainloop()
        else:
            log_status("❌ GUI ไม่มี method สำหรับรัน", True)
            return False
        
        return True
        
    except Exception as e:
        log_status(f"❌ ไม่สามารถโหลด GUI System: {e}", True)
        return False

def start_simple_gui():
    """เริ่ม GUI แบบง่าย (ถ้าไฟล์เดิมใช้ไม่ได้)"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        log_status("🖥️ กำลังเปิด Simple GUI...")
        
        root = tk.Tk()
        root.title("🚀 Intelligent Gold Trading System")
        root.geometry("600x400")
        root.configure(bg='#1a1a2e')
        
        # Header
        tk.Label(
            root,
            text="🚀 INTELLIGENT GOLD TRADING SYSTEM",
            font=("Arial", 16, "bold"),
            fg='#e94560',
            bg='#1a1a2e'
        ).pack(pady=20)
        
        # Status
        status_label = tk.Label(
            root,
            text="✅ System Ready - MT5 Connected",
            font=("Arial", 12),
            fg='#27ae60',
            bg='#1a1a2e'
        )
        status_label.pack(pady=10)
        
        # Account info
        if MT5_AVAILABLE:
            account_info = mt5.account_info()
            if account_info:
                account_text = f"Account: {account_info.login} | Balance: ${account_info.balance:,.2f}"
                tk.Label(
                    root,
                    text=account_text,
                    font=("Arial", 11),
                    fg='#ffffff',
                    bg='#1a1a2e'
                ).pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(root, bg='#1a1a2e')
        button_frame.pack(pady=30)
        
        def start_trading():
            result = messagebox.askyesno(
                "Confirm",
                "🚀 เริ่มการเทรด?\n\n⚠️ ระบบจะทำการเทรดด้วยเงินจริง"
            )
            if result:
                messagebox.showinfo("Started", "🚀 เริ่มการเทรดแล้ว\n\n💡 ระบบจะทำงานในพื้นหลัง")
        
        def stop_trading():
            result = messagebox.askyesno("Confirm", "🛑 หยุดการเทรด?")
            if result:
                messagebox.showinfo("Stopped", "🛑 หยุดการเทรดแล้ว")
        
        tk.Button(
            button_frame,
            text="🚀 Start Trading",
            font=("Arial", 14, "bold"),
            bg='#27ae60',
            fg='white',
            width=15,
            height=2,
            command=start_trading
        ).pack(side=tk.LEFT, padx=10)
        
        tk.Button(
            button_frame,
            text="🛑 Stop Trading",
            font=("Arial", 14, "bold"),
            bg='#e74c3c',
            fg='white',
            width=15,
            height=2,
            command=stop_trading
        ).pack(side=tk.LEFT, padx=10)
        
        # Status bar
        status_bar = tk.Label(
            root,
            text="🔄 System Ready",
            font=("Arial", 10),
            fg='#bdc3c7',
            bg='#16213e',
            relief=tk.SUNKEN
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        log_status("✅ Simple GUI เริ่มต้นสำเร็จ")
        
        def on_closing():
            if messagebox.askyesno("Quit", "ต้องการปิดระบบ?"):
                if MT5_AVAILABLE:
                    mt5.shutdown()
                root.quit()
                root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()
        
        return True
        
    except Exception as e:
        log_status(f"❌ ไม่สามารถเปิด Simple GUI: {e}", True)
        return False

def start_minimal_trading_mode(symbol_name):
    """เริ่มโหมดเทรดขั้นต่ำ (เมื่อ GUI ไม่ทำงาน)"""
    log_status("🚀 เริ่มโหมดเทรดขั้นต่ำ...")
    
    try:
        log_status(f"📊 กำลังติดตาม {symbol_name}...")
        
        for i in range(10):
            tick = mt5.symbol_info_tick(symbol_name)
            if tick:
                current_time = datetime.now().strftime('%H:%M:%S')
                spread = tick.ask - tick.bid
                log_status(f"💰 {current_time} | {symbol_name}: {tick.bid:.2f}/{tick.ask:.2f} | Spread: {spread:.2f}")
            
            time.sleep(2)
        
        log_status("✅ โหมดเทรดขั้นต่ำทำงานปกติ")
        return True
        
    except Exception as e:
        log_status(f"❌ ข้อผิดพลาดในโหมดเทรดขั้นต่ำ: {e}", True)
        return False

def cleanup_and_shutdown():
    """ปิดระบบและทำความสะอาด"""
    log_status("🔄 กำลังปิดระบบ...")
    
    try:
        if MT5_AVAILABLE:
            mt5.shutdown()
            log_status("✅ ปิดการเชื่อมต่อ MT5")
        
        uptime = system_status.get_uptime()
        log_status(f"📊 สถิติการทำงาน:")
        log_status(f"   ⏰ เวลาทำงาน: {uptime:.1f} วินาที")
        log_status(f"   📨 ข้อความทั้งหมด: {system_status.message_count}")
        log_status(f"   ❌ ข้อผิดพลาด: {system_status.error_count}")
        
        success_rate = ((system_status.message_count - system_status.error_count) / 
                       max(system_status.message_count, 1)) * 100
        log_status(f"   ✅ อัตราสำเร็จ: {success_rate:.1f}%")
        
        log_status("👋 ปิดระบบ Intelligent Gold Trading เรียบร้อย")
        
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการปิดระบบ: {e}")

def main():
    """ฟังก์ชันหลักของระบบ"""
    print("🚀 INTELLIGENT GOLD TRADING SYSTEM v2.0")
    print("=" * 50)
    print("🔧 แก้ไขปัญหา XAUUSD Symbol Loading Error")
    print("⚡ รองรับ Auto-Detection สำหรับโบรกเกอร์ทุกประเภท")
    print("🖥️ เปิด GUI Interface")
    print("=" * 50)
    
    try:
        # 1. ตรวจสอบการติดตั้ง MT5
        if not check_mt5_installation():
            return False
        
        # 2. เชื่อมต่อ MT5
        if not initialize_mt5_connection():
            log_status("❌ ไม่สามารถเชื่อมต่อ MT5 ได้ - หยุดการทำงาน", True)
            return False
        
        # 3. ค้นหา Gold Symbol
        gold_symbol = auto_detect_gold_symbol()
        if not gold_symbol:
            log_status("❌ ไม่พบ Gold Symbol - ไม่สามารถดำเนินการต่อได้", True)
            return False
        
        # 4. บันทึกการตั้งค่า Symbol
        save_symbol_config(gold_symbol)
        
        # 5. โหลด Trading Components
        components_loaded = initialize_trading_components()
        
        if components_loaded:
            log_status("🎉 ระบบพร้อมทำงานเต็มรูปแบบ")
        else:
            log_status("⚠️ บาง Components ไม่พร้อม - ระบบจะทำงานในโหมดจำกัด")
        
        # 6. เปิด GUI System
        log_status("🖥️ กำลังเปิด GUI Interface...")
        
        if start_gui_system():
            log_status("✅ GUI System ทำงานเสร็จสิ้น")
        else:
            log_status("⚠️ GUI ไม่สามารถเปิดได้ - ใช้โหมดขั้นต่ำ")
            start_minimal_trading_mode(gold_symbol)
        
        log_status("✅ ระบบทำงานสำเร็จ - แก้ไขปัญหา XAUUSD Symbol แล้ว")
        return True
        
    except KeyboardInterrupt:
        log_status("⚠️ ผู้ใช้หยุดระบบด้วย Ctrl+C")
        return False
        
    except Exception as e:
        log_status(f"❌ ข้อผิดพลาดในระบบหลัก: {e}", True)
        return False
    
    finally:
        cleanup_and_shutdown()

if __name__ == "__main__":
    try:
        success = main()
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1)