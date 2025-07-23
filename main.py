#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELLIGENT GOLD TRADING SYSTEM - MAIN ENTRY POINT
=================================================
ไฟล์หลักสำหรับเริ่มต้นระบบเทรด Gold แบบอัตโนมัติ
ทำหน้าที่เป็น Entry Point เพียงอย่างเดียว (< 50 lines ตาม requirement)

เชื่อมต่อไปยัง:
- config/settings.py (การตั้งค่าระบบ)
- gui_system/main_window.py (หน้าต่างหลัก)
- utilities/professional_logger.py (ระบบ logging)
- utilities/error_handler.py (จัดการข้อผิดพลาด)
"""

import sys
import os
from pathlib import Path

# เพิ่ม path ของโปรเจคเข้าไปใน sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # นำเข้าระบบการตั้งค่าหลัก
    from config.settings import SystemSettings
    from utilities.professional_logger import setup_main_logger
    from utilities.error_handler import GlobalErrorHandler
    from gui_system.main_window import TradingSystemGUI
    
    def main():
        """
        ฟังก์ชันหลักสำหรับเริ่มต้นระบบ
        - ตั้งค่า Logger หลัก
        - เริ่มต้น Error Handler
        - เปิดหน้าต่าง GUI หลัก
        """
        # ตั้งค่า Logger หลักของระบบ
        logger = setup_main_logger("IntelligentGoldTrading")
        logger.info("🚀 เริ่มต้นระบบ Intelligent Gold Trading System")
        
        # ตั้งค่า Global Error Handler
        error_handler = GlobalErrorHandler(logger)
        error_handler.setup_global_exception_handling()
        
        # โหลดการตั้งค่าระบบ
        settings = SystemSettings()
        logger.info(f"📋 โหลดการตั้งค่าระบบสำเร็จ - Mode: {settings.trading_mode}")
        
        # เริ่มต้น GUI หลัก
        app = TradingSystemGUI(settings, logger)
        logger.info("🖥️ เปิดหน้าต่างระบบเทรดดิ้ง")
        
        # รันระบบ
        app.run()
        
        logger.info("🛑 ปิดระบบ Intelligent Gold Trading System")

    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"❌ ข้อผิดพลาดในการนำเข้าโมดูล: {e}")
    print("🔧 กรุณาตรวจสอบการติดตั้ง dependencies และโครงสร้างไฟล์")
    sys.exit(1)
except Exception as e:
    print(f"💥 ข้อผิดพลาดร้อนแรงในการเริ่มต้นระบบ: {e}")
    sys.exit(1)