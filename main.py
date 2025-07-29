#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELLIGENT GOLD TRADING SYSTEM - MAIN ENTRY POINT (FIXED)
=========================================================
ไฟล์หลักสำหรับเริ่มต้นระบบเทรด Gold แบบอัตโนมัติ
แก้ไขปัญหา Circular Import และ Module Loading

🔧 ปัญหาที่แก้ไข:
- Circular Import Dependencies
- Import Path ที่ไม่ถูกต้อง  
- Module Loading Order
- Error Handling ที่ดีขึ้น

🚀 หน้าที่หลัก:
- เริ่มต้นระบบ Logger และ Error Handler
- โหลดการตั้งค่าระบบ
- เริ่มต้น Core Trading System
- เปิด GUI หลัก
- จัดการการปิดระบบ
"""

import sys
import os
import traceback
from pathlib import Path

# เพิ่ม project root เข้า sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_basic_logging():
    """ตั้งค่า logging พื้นฐานสำหรับการ debug"""
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('trading_system.log', encoding='utf-8')
        ]
    )
    
    return logging.getLogger("IntelligentGoldTrading")

def check_dependencies():
    """ตรวจสอบ dependencies ที่จำเป็น"""
    required_modules = [
        'tkinter',
        'threading', 
        'datetime',
        'queue',
        'json',
        'sqlite3'
    ]
    
    missing_modules = []
    
    for module_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing_modules.append(module_name)
    
    # ตรวจสอบ MetaTrader5 (ไม่บังคับ)
    try:
        import MetaTrader5 as mt5
        print("✅ MetaTrader5 module พร้อมใช้งาน")
    except ImportError:
        print("⚠️ MetaTrader5 module ไม่พร้อมใช้งาน - จะใช้โหมดจำลอง")
    
    if missing_modules:
        print(f"❌ ขาด modules ที่จำเป็น: {missing_modules}")
        return False
    
    return True

def load_config_safe():
    """โหลดการตั้งค่าแบบปลอดภัย"""
    try:
        from config.settings import SystemSettings
        settings = SystemSettings()
        print(f"✅ โหลดการตั้งค่าระบบ - Mode: {settings.trading_mode}")
        return settings
    except ImportError as e:
        print(f"⚠️ ไม่สามารถโหลด config.settings: {e}")
        # ใช้การตั้งค่าเริ่มต้น
        class DefaultSettings:
            trading_mode = "LIVE"
            symbol = "XAUUSD"
            high_frequency_mode = True
        
        return DefaultSettings()

def initialize_logger_safe():
    """เริ่มต้น Logger แบบปลอดภัย"""
    try:
        from utilities.professional_logger import setup_main_logger
        logger = setup_main_logger("IntelligentGoldTrading")
        logger.info("🚀 เริ่มต้นระบบ Intelligent Gold Trading System")
        return logger
    except ImportError as e:
        print(f"⚠️ ไม่สามารถโหลด professional logger: {e}")
        return setup_basic_logging()

def initialize_error_handler_safe(logger):
    """เริ่มต้น Error Handler แบบปลอดภัย"""
    try:
        from utilities.error_handler import GlobalErrorHandler
        error_handler = GlobalErrorHandler(logger)
        error_handler.setup_global_exception_handling()
        logger.info("✅ เริ่มต้น Global Error Handler")
        return error_handler
    except ImportError as e:
        logger.warning(f"⚠️ ไม่สามารถโหลด error handler: {e}")
        return None

def initialize_trading_system_safe(settings, logger):
    """เริ่มต้น Trading System แบบปลอดภัย"""
    try:
        from core_system.trading_system import IntelligentTradingSystem
        trading_system = IntelligentTradingSystem(settings, logger)
        logger.info("🧠 เริ่มต้นระบบเทรดหลัก")
        return trading_system
    except ImportError as e:
        logger.error(f"❌ ไม่สามารถโหลด trading system: {e}")
        traceback.print_exc()
        return None
    except Exception as e:
        logger.error(f"❌ ข้อผิดพลาดในการเริ่มต้น trading system: {e}")
        traceback.print_exc()
        return None

def initialize_gui_safe(settings, logger, trading_system):
    """เริ่มต้น GUI แบบปลอดภัย"""
    try:
        from gui_system.main_window import TradingSystemGUI
        gui = TradingSystemGUI(settings, logger, trading_system)
        logger.info("🖥️ เปิดหน้าต่างระบบเทรดดิ้ง")
        return gui
    except ImportError as e:
        logger.error(f"❌ ไม่สามารถโหลด GUI system: {e}")
        traceback.print_exc()
        return None
    except Exception as e:
        logger.error(f"❌ ข้อผิดพลาดในการเริ่มต้น GUI: {e}")
        traceback.print_exc()
        return None

def create_fallback_gui(logger):
    """สร้าง GUI สำรองเมื่อโหลดหลักไม่ได้"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        class FallbackGUI:
            def __init__(self):
                self.root = tk.Tk()
                self.root.title("Intelligent Gold Trading System - Emergency Mode")
                self.root.geometry("600x400")
                self.root.configure(bg='#1a1a2e')
                
                # Title
                title_label = tk.Label(
                    self.root,
                    text="🔧 EMERGENCY MODE",
                    font=("Arial", 20, "bold"),
                    fg='#e94560',
                    bg='#1a1a2e'
                )
                title_label.pack(pady=20)
                
                # Status
                status_text = tk.Text(
                    self.root,
                    height=15,
                    width=70,
                    bg='#16213e',
                    fg='#ffffff',
                    font=("Consolas", 10)
                )
                status_text.pack(pady=10)
                
                # อ่าน log file และแสดง
                try:
                    with open('trading_system.log', 'r', encoding='utf-8') as f:
                        log_content = f.read()
                        status_text.insert(tk.END, log_content)
                except:
                    status_text.insert(tk.END, "ไม่สามารถอ่าน log file ได้")
                
                # Button
                close_btn = tk.Button(
                    self.root,
                    text="ปิดระบบ",
                    command=self.root.quit,
                    bg='#e94560',
                    fg='white',
                    font=("Arial", 12),
                    width=15
                )
                close_btn.pack(pady=10)
            
            def run(self):
                self.root.mainloop()
        
        return FallbackGUI()
        
    except Exception as e:
        logger.error(f"❌ ไม่สามารถสร้าง Fallback GUI: {e}")
        return None

def main():
    """🚀 Main Entry Point - เรียบง่ายและแข็งแกร่ง"""
    print("=" * 60)
    print("🚀 INTELLIGENT GOLD TRADING SYSTEM")
    print("   Starting up with enhanced error handling...")
    print("=" * 60)
    
    # ตรวจสอบ dependencies
    if not check_dependencies():
        input("กด Enter เพื่อปิดโปรแกรม...")
        sys.exit(1)
    
    # เริ่มต้น basic logging
    basic_logger = setup_basic_logging()
    
    try:
        # ขั้นตอนที่ 1: โหลดการตั้งค่า
        print("📋 กำลังโหลดการตั้งค่าระบบ...")
        settings = load_config_safe()
        
        # ขั้นตอนที่ 2: เริ่มต้น Logger
        print("📝 กำลังเริ่มต้น Logger...")
        logger = initialize_logger_safe()
        
        # ขั้นตอนที่ 3: เริ่มต้น Error Handler
        print("🛡️ กำลังเริ่มต้น Error Handler...")
        error_handler = initialize_error_handler_safe(logger)
        
        # ขั้นตอนที่ 4: เริ่มต้น Trading System
        print("🧠 กำลังเริ่มต้นระบบเทรด...")
        trading_system = initialize_trading_system_safe(settings, logger)
        
        # ขั้นตอนที่ 5: เริ่มต้น GUI
        print("🖥️ กำลังเริ่มต้น GUI...")
        gui = initialize_gui_safe(settings, logger, trading_system)
        
        # ตรวจสอบว่าทุกอย่างพร้อม
        if gui is None:
            print("⚠️ GUI หลักโหลดไม่ได้ - เปิด Emergency Mode")
            gui = create_fallback_gui(logger)
        
        if gui is None:
            print("❌ ไม่สามารถเริ่มต้น GUI ได้เลย")
            input("กด Enter เพื่อปิดโปรแกรม...")
            return
        
        # เริ่มระบบ
        print("✅ ระบบพร้อมใช้งาน - เปิด GUI...")
        print("=" * 60)
        
        # Start the application
        gui.run()
        
    except KeyboardInterrupt:
        print("\n🛑 ผู้ใช้หยุดโปรแกรม (Ctrl+C)")
    except ImportError as e:
        print(f"❌ ข้อผิดพลาดในการนำเข้าโมดูล: {e}")
        print("🔧 กรุณาตรวจสอบการติดตั้ง dependencies และโครงสร้างไฟล์")
        traceback.print_exc()
        input("กด Enter เพื่อปิดโปรแกรม...")
    except Exception as e:
        print(f"💥 ข้อผิดพลาดร้ายแรงในการเริ่มต้นระบบ: {e}")
        print("📋 รายละเอียด:")
        traceback.print_exc()
        input("กด Enter เพื่อปิดโปรแกรม...")
    finally:
        print("🛑 ปิดระบบ Intelligent Gold Trading System")
        print("=" * 60)

def test_imports():
    """ทดสอบการ import modules ทั้งหมด"""
    print("🧪 ทดสอบการ import modules...")
    
    modules_to_test = [
        'config.settings',
        'config.trading_params', 
        'utilities.professional_logger',
        'utilities.error_handler',
        'adaptive_entries.signal_generator',
        'market_intelligence.market_analyzer',
        'intelligent_recovery.recovery_engine'
    ]
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name}")
        except ImportError as e:
            print(f"❌ {module_name}: {e}")
        except Exception as e:
            print(f"⚠️ {module_name}: {e}")
    
    print("🧪 ทดสอบ imports เสร็จสิ้น")

if __name__ == "__main__":
    # ทดสอบ imports ก่อน (ถ้าต้องการ)
    if len(sys.argv) > 1 and sys.argv[1] == "--test-imports":
        test_imports()
    else:
        main()