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
- position_management/ (ระบบ Profit ที่มีอยู่แล้ว)
- adaptive_entries/ (Signal Generator)
- mt5_integration/ (Order Executor)
"""

import sys
import os
import threading
import time
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
    
    # 🔗 นำเข้าระบบ Profit ที่มีอยู่แล้ว
    from position_management.position_tracker import get_position_tracker
    from position_management.profit_optimizer import get_profit_taker
    
    # 🎯 นำเข้าระบบ Signal และ Order
    from adaptive_entries.signal_generator import get_signal_generator
    from mt5_integration.order_executor import get_smart_order_executor, OrderType
    
    def intelligent_position_manager(signal_generator, order_executor, position_tracker, logger):
        """
        🧠 Intelligent Position Manager - ระบบจัดการ Position อัจฉริยะ
        
        Logic:
        1. ไม่มี positions → วิเคราะห์และสร้าง position ใหม่
        2. มี positions กำไร → ปล่อยให้ Profit System เก็บ
        3. มี positions ขาดทุน → ใช้ Recovery ช่วยให้ปิดเร็วขึ้น
        4. ปิดครบหมดแล้ว → กลับไปข้อ 1
        """
        logger.info("🧠 Intelligent Position Manager เริ่มทำงาน")
        
        # สถานะระบบ
        current_cycle = "ANALYSIS"  # ANALYSIS, MONITORING, RECOVERY
        last_analysis_time = 0
        analysis_cooldown = 120  # วิเคราะห์ใหม่ทุก 2 นาที (หลังจากปิดครบ)
        
        while True:
            try:
                # ตรวจสอบ positions ปัจจุบัน
                current_positions = order_executor.get_open_positions("XAUUSD")
                total_positions = len(current_positions)
                
                if total_positions == 0:
                    # 🎯 ไม่มี positions → โหมดวิเคราะห์
                    current_cycle = "ANALYSIS"
                    current_time = time.time()
                    
                    # 🔄 เริ่ม Signal Generator ใหม่เมื่อไม่มี positions
                    try:
                        signal_generator.start_signal_generation()
                        logger.info("🔄 เริ่ม Signal Generator ใหม่ - พร้อมวิเคราะห์")
                    except Exception as e:
                        logger.warning(f"⚠️ ไม่สามารถเริ่ม Signal Generator: {e}")
                    
                    # ตรวจสอบ cooldown
                    if current_time - last_analysis_time >= analysis_cooldown:
                        logger.info("🔍 ไม่มี positions → เริ่มวิเคราะห์ตลาดใหม่")
                        
                        # รับ signal จาก Signal Generator
                        signal = signal_generator.get_next_signal()
                        
                        if signal:
                            logger.info(f"📨 Signal ใหม่: {signal.signal_id} | {signal.direction.value} | "
                                      f"Price: {signal.current_price:.2f} | Confidence: {signal.confidence:.2f}")
                            
                            # แปลง Signal เป็น Order
                            if signal.direction.value == "BUY":
                                order_type = OrderType.BUY
                            elif signal.direction.value == "SELL":
                                order_type = OrderType.SELL
                            else:
                                logger.warning(f"⚠️ Invalid signal direction: {signal.direction.value}")
                                time.sleep(10)
                                continue
                            
                            # กำหนด volume (เริ่มต้นด้วย 0.01)
                            volume = 0.01
                            
                            # ส่งออเดอร์
                            result = order_executor.send_market_order(
                                symbol="XAUUSD.v",
                                order_type=order_type,
                                volume=volume,
                                comment=f"Smart_{signal.signal_id[:8]}",
                                strategy_name=signal.source_engine.value,
                                recovery_level=0
                            )
                            
                            if result.status.value == "FILLED":
                                last_analysis_time = current_time
                                current_cycle = "MONITORING"
                                
                                # 🛑 หยุด Signal Generator หลังส่งออเดอร์สำเร็จ
                                try:
                                    signal_generator.stop_signal_generation()
                                    logger.info("🛑 หยุด Signal Generator - รอให้ position ปิดก่อน")
                                except Exception as e:
                                    logger.warning(f"⚠️ ไม่สามารถหยุด Signal Generator: {e}")
                                
                                logger.info(f"✅ Position ใหม่สร้างสำเร็จ: {order_type.value} {volume} lots | "
                                          f"Price: {result.price_executed:.2f}")
                                logger.info("👁️ เปลี่ยนสู่โหมด MONITORING - รอดูผลลัพธ์")
                            else:
                                logger.error(f"❌ สร้าง Position ล้มเหลว: {result.error_description}")
                        
                        else:
                            logger.info("📊 ไม่มี Signal ในขณะนี้ - รอการวิเคราะห์")
                    
                    else:
                        time_left = int(analysis_cooldown - (current_time - last_analysis_time))
                        logger.info(f"⏳ รอ Cooldown อีก {time_left} วินาที ก่อนวิเคราะห์ใหม่")
                
                else:
                    # 📊 มี positions → โหมดจัดการ
                    # คำนวณ P&L รวม
                    total_pnl = sum(pos['profit'] for pos in current_positions)
                    profitable_positions = [pos for pos in current_positions if pos['profit'] > 0]
                    losing_positions = [pos for pos in current_positions if pos['profit'] < -30.0]  # ขาดทุนเกิน $30
                    
                    logger.info(f"📊 Positions: {total_positions} | Total P&L: ${total_pnl:.2f} | "
                              f"Profit: {len(profitable_positions)} | Loss: {len(losing_positions)}")
                    
                    if losing_positions:
                        # 🔄 มี positions ขาดทุน → โหมด RECOVERY
                        current_cycle = "RECOVERY"
                        logger.warning(f"🔄 โหมด RECOVERY - มี {len(losing_positions)} positions ขาดทุน")
                        
                        # หา position ขาดทุนมากที่สุด
                        worst_position = min(losing_positions, key=lambda p: p['profit'])
                        loss_amount = abs(worst_position['profit'])
                        
                        logger.info(f"🎯 Target Recovery: Position {worst_position['ticket']} | "
                                  f"Loss: ${loss_amount:.2f} | Type: {worst_position['type']}")
                        
                        # คำนวณ Recovery Order
                        recovery_volume = min(worst_position['volume'] * 1.5, 0.05)  # Martingale x1.5, จำกัด 0.05
                        recovery_type = OrderType.SELL if worst_position['type'] == 'BUY' else OrderType.BUY
                        
                        # ส่ง Recovery Order
                        recovery_result = order_executor.send_market_order(
                            symbol="XAUUSD",
                            order_type=recovery_type,
                            volume=recovery_volume,
                            comment=f"Recov_{worst_position['ticket']}",
                            strategy_name="SMART_RECOVERY",
                            recovery_level=1
                        )
                        
                        if recovery_result.status.value == "FILLED":
                            logger.info(f"✅ Recovery Order สำเร็จ: {recovery_type.value} {recovery_volume} lots | "
                                      f"Price: {recovery_result.price_executed:.2f}")
                        else:
                            logger.error(f"❌ Recovery Order ล้มเหลว: {recovery_result.error_description}")
                    
                    elif total_pnl > 0:
                        # 💰 P&L รวมเป็นบวก → โหมด MONITORING (ปล่อยให้ Profit System ทำงาน)
                        current_cycle = "MONITORING"
                        logger.info("💰 Portfolio มีกำไร - ปล่อยให้ Profit System เก็บกำไร")
                    
                    else:
                        # 📊 สถานะปกติ → โหมด MONITORING
                        current_cycle = "MONITORING"
                        logger.info("📊 กำลังติดตาม positions - รอดูการเปลี่ยนแปลง")
                
                # รอก่อนรอบถัดไป
                if current_cycle == "ANALYSIS":
                    time.sleep(30)  # วิเคราะห์ทุก 30 วินาที
                elif current_cycle == "MONITORING":
                    time.sleep(15)  # ติดตามทุก 15 วินาที
                elif current_cycle == "RECOVERY":
                    time.sleep(10)  # Recovery ทุก 10 วินาที
                
            except Exception as e:
                logger.error(f"❌ Position Manager error: {e}")
                time.sleep(20)
    
    def main():
        """
        ฟังก์ชันหลักสำหรับเริ่มต้นระบบ
        - ตั้งค่า Logger หลัก
        - เริ่มต้น Error Handler
        - เชื่อมต่อระบบ Profit
        - เริ่ม Intelligent Position Manager
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
        
        # 🔗 เชื่อมต่อระบบ Profit
        logger.info("🔗 เชื่อมต่อระบบ Profit...")
        
        # เริ่มต้น Position Tracker
        position_tracker = get_position_tracker()
        logger.info("✅ Position Tracker เชื่อมต่อแล้ว")
        
        # เริ่มต้น Profit Optimizer
        profit_optimizer = get_profit_taker()
        profit_optimizer.start_profit_taking()
        logger.info("✅ Profit Optimizer เริ่มทำงานแล้ว")
        
        # 🧠 เชื่อมต่อระบบ Intelligent Position Manager
        logger.info("🧠 เชื่อมต่อ Intelligent Position Manager...")
        
        # เริ่มต้น Signal Generator (แต่ยังไม่เริ่มส่ง signals)
        signal_generator = get_signal_generator()
        # signal_generator.start_signal_generation()  # ปิดไว้ก่อน - จะเริ่มใน Position Manager
        logger.info("✅ Signal Generator พร้อมใช้งาน (ยังไม่เริ่มส่ง signals)")
        
        # เริ่มต้น Order Executor
        order_executor = get_smart_order_executor()
        logger.info("✅ Order Executor พร้อมใช้งาน")
        
        # เริ่ม Intelligent Position Manager Thread
        manager_thread = threading.Thread(
            target=intelligent_position_manager,
            args=(signal_generator, order_executor, position_tracker, logger),
            daemon=True,
            name="IntelligentPositionManager"
        )
        manager_thread.start()
        logger.info("🧠 Intelligent Position Manager เชื่อมต่อแล้ว!")
        
        # เริ่มต้น GUI หลัก
        app = TradingSystemGUI(settings, logger)
        logger.info("🖥️ เปิดหน้าต่างระบบเทรดดิ้ง")
        
        # รันระบบ
        app.run()
        
        # ปิดระบบเมื่อจบการทำงาน
        logger.info("🛑 กำลังปิดระบบ...")
        signal_generator.stop_signal_generation()
        profit_optimizer.stop_profit_taking()
        position_tracker.stop_tracking()
        logger.info("🛑 ปิดระบบ Intelligent Gold Trading System")

    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"❌ ข้อผิดพลาดในการนำเข้าโมดูล: {e}")
    print("🔧 กรุณาตรวจสอบการติดตั้ง dependencies และโครงสร้างไฟล์")
    print("📁 ตรวจสอบว่ามีไฟล์ต่อไปนี้:")
    print("   - position_management/position_tracker.py")
    print("   - position_management/profit_optimizer.py")
    print("   - adaptive_entries/signal_generator.py")
    print("   - mt5_integration/order_executor.py")
    sys.exit(1)
except Exception as e:
    print(f"💥 ข้อผิดพลาดร้อนแรงในการเริ่มต้นระบบ: {e}")
    sys.exit(1)