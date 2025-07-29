#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELLIGENT GOLD TRADING SYSTEM - MAIN ENTRY POINT
=================================================
ไฟล์หลักสำหรับเริ่มต้นระบบเทรด Gold แบบอัตโนมัติ
ทำหน้าที่เป็น Entry Point เพียงอย่างเดียว (< 30 lines ตาม requirement)

🚀 หน้าที่หลัก:
- เริ่มต้นระบบ Logger และ Error Handler
- โหลดการตั้งค่าระบบ
- เริ่มต้น Core Trading System
- เปิด GUI หลัก
- จัดการการปิดระบบ
"""

import sys
from pathlib import Path

# เพิ่ม project root เข้า sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """🚀 Main Entry Point - เรียบง่ายและชัดเจน"""
    try:
        # Setup core components
        from config.settings import SystemSettings
        from utilities.professional_logger import setup_main_logger
        from utilities.error_handler import GlobalErrorHandler
        from core_system.trading_system import IntelligentTradingSystem
        from gui_system.main_window import TradingSystemGUI
        
        # Initialize logger
        logger = setup_main_logger("IntelligentGoldTrading")
        logger.info("🚀 เริ่มต้นระบบ Intelligent Gold Trading System")
        
        # Setup global error handling
        error_handler = GlobalErrorHandler(logger)
        error_handler.setup_global_exception_handling()
        
        # Load system settings
        settings = SystemSettings()
        logger.info(f"📋 โหลดการตั้งค่าระบบ - Mode: {settings.trading_mode}")
        
        # Initialize core trading system
        trading_system = IntelligentTradingSystem(settings, logger)
        logger.info("🧠 เริ่มต้นระบบเทรดหลัก")
        
        # Initialize and start GUI
        gui = TradingSystemGUI(settings, logger, trading_system)
        logger.info("🖥️ เปิดหน้าต่างระบบเทรดดิ้ง")
        
        # Start the application
        gui.run()
        
    except ImportError as e:
        print(f"❌ ข้อผิดพลาดในการนำเข้าโมดูล: {e}")
        print("🔧 กรุณาตรวจสอบการติดตั้ง dependencies และโครงสร้างไฟล์")
        sys.exit(1)
    except Exception as e:
        print(f"💥 ข้อผิดพลาดร้ายแรงในการเริ่มต้นระบบ: {e}")
        sys.exit(1)
    finally:
        print("🛑 ปิดระบบ Intelligent Gold Trading System")

if __name__ == "__main__":
    main()