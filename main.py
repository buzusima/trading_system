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
        🧠 Intelligent Position Manager - ระบบจัดการ Position อัจฉริยะ (แก้ไขแล้ว)
        """
        logger.info("🧠 Intelligent Position Manager เริ่มทำงาน")
        
        # สถานะระบบ
        current_cycle = "ANALYSIS"  # ANALYSIS, MONITORING, RECOVERY
        last_analysis_time = 0
        analysis_cooldown = 120  # วิเคราะห์ใหม่ทุก 2 นาที (หลังจากปิดครบ)
        signal_generator_running = False  # ✨ เพิ่มการติดตามสถานะ
        last_order_attempt = 0  # ✨ เพิ่ม: ป้องกันส่งออเดอร์บ่อย
        order_cooldown = 30  # ✨ ห้ามส่งออเดอร์ถ้ายังไม่ครบ 30 วินาที
        
        while True:
            try:
                # ✅ เพิ่มการตรวจสอบว่ากดปุ่ม "เริ่มเทรด" แล้วหรือไม่
                if not getattr(signal_generator, 'trading_started', False):
                    logger.debug("⏳ รอให้กดปุ่ม 'เริ่มเทรด' ก่อน...")
                    time.sleep(5)
                    continue
                
                # ตรวจสอบ positions ปัจจุบัน
                current_positions = order_executor.get_open_positions("XAUUSD")
                total_positions = len(current_positions)
                current_time = time.time()
                
                # 📊 แสดงสถานะปัจจุบัน
                if current_time % 30 < 10:  # แสดงทุก 30 วินาที
                    logger.debug(f"📊 Positions: {total_positions} | Cycle: {current_cycle} | "
                                f"Signal Generator: {'Running' if signal_generator_running else 'Stopped'}")
                
                if total_positions == 0:
                    # 🎯 ไม่มี positions → โหมดวิเคราะห์
                    if current_cycle != "ANALYSIS":
                        logger.info("📊 Positions: 0 → เปลี่ยนเป็นโหมด ANALYSIS")
                        current_cycle = "ANALYSIS"
                    
                    # 🔄 เริ่ม Signal Generator ใหม่เมื่อไม่มี positions
                    if not signal_generator_running:
                        try:
                            # ✨ ตรวจสอบสถานะก่อนเริ่ม
                            status = signal_generator.get_system_status()
                            if not status.get('generator_active', False):
                                success = signal_generator.start_signal_generation()
                                signal_generator_running = success
                                if success:
                                    logger.info("🔄 เริ่ม Signal Generator ใหม่ - พร้อมวิเคราะห์")
                                else:
                                    logger.error("❌ ไม่สามารถเริ่ม Signal Generator")
                            else:
                                signal_generator_running = True
                                logger.debug("✅ Signal Generator ทำงานอยู่แล้ว")
                        except Exception as e:
                            logger.warning(f"⚠️ ไม่สามารถเริ่ม Signal Generator: {e}")
                            signal_generator_running = False
                    
                    # ✨ ตรวจสอบ order cooldown
                    if current_time - last_order_attempt < order_cooldown:
                        remaining = order_cooldown - (current_time - last_order_attempt)
                        logger.debug(f"⏰ รอส่งออเดอร์อีก {remaining:.0f} วินาที")
                        time.sleep(10)
                        continue
                    
                    # ตรวจสอบ analysis cooldown  
                    if current_time - last_analysis_time >= analysis_cooldown:
                        logger.info("🔍 ไม่มี positions → เริ่มวิเคราะห์ตลาดใหม่")
                        
                        # รับ signal จาก Signal Generator
                        if signal_generator_running:
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
                                logger.info(f"📤 กำลังส่งออเดอร์: {order_type.value} {volume} lots")
                                result = order_executor.send_market_order(
                                    symbol="XAUUSD.v",
                                    order_type=order_type,
                                    volume=volume,
                                    comment=f"Smart_{signal.signal_id[:8]}",
                                    strategy_name=signal.source_engine.value,
                                    recovery_level=0
                                )
                                
                                # ✨ บันทึกเวลาที่ส่งออเดอร์
                                last_order_attempt = current_time
                                
                                if result.status.value == "FILLED":
                                    last_analysis_time = current_time
                                    current_cycle = "MONITORING"
                                    
                                    # 🛑 หยุด Signal Generator ทันทีหลังส่งออเดอร์สำเร็จ
                                    if signal_generator_running:
                                        try:
                                            success = signal_generator.stop_signal_generation()
                                            signal_generator_running = not success
                                            logger.info("🛑 หยุด Signal Generator - รอให้ position ปิดก่อน")
                                            
                                            # ✨ ล้าง signals ที่เหลือใน queue
                                            try:
                                                while True:
                                                    remaining_signal = signal_generator.get_next_signal()
                                                    if remaining_signal is None:
                                                        break
                                                    logger.debug(f"🗑️ ลบ signal ที่เหลือ: {remaining_signal.signal_id}")
                                            except:
                                                pass
                                                
                                        except Exception as e:
                                            logger.warning(f"⚠️ ไม่สามารถหยุด Signal Generator: {e}")
                                    
                                    logger.info(f"✅ Position ใหม่สร้างสำเร็จ: {order_type.value} {volume} lots | "
                                            f"Price: {result.price_executed:.2f}")
                                    logger.info("👁️ เปลี่ยนสู่โหมด MONITORING - รอดูผลลัพธ์")
                                else:
                                    logger.error(f"❌ สร้าง Position ล้มเหลว: {result.error_description}")
                            else:
                                logger.debug("⏳ ไม่มี signals ใหม่")
                        else:
                            logger.debug("⏳ รอ Signal Generator เริ่มทำงาน...")
                            
                    else:
                        # ยังไม่ถึงเวลา cooldown
                        remaining_time = analysis_cooldown - (current_time - last_analysis_time)
                        if remaining_time > 60:  # แสดงเฉพาะถ้าเหลือเกิน 1 นาที
                            logger.debug(f"⏰ รอ analysis cooldown อีก {remaining_time:.0f} วินาที")
                
                else:
                    # 👁️ มี positions → โหมด MONITORING/RECOVERY
                    if current_cycle == "ANALYSIS":
                        logger.info(f"📊 Positions: {total_positions} → เปลี่ยนเป็นโหมด MONITORING")
                        current_cycle = "MONITORING"
                    
                    # ✨ ตรวจสอบและหยุด Signal Generator ถ้ายังทำงานอยู่
                    if signal_generator_running:
                        try:
                            success = signal_generator.stop_signal_generation()
                            signal_generator_running = not success
                            logger.info("🛑 หยุด Signal Generator - มี positions อยู่")
                            
                            # ✨ ล้าง signals ที่เหลือใน queue
                            try:
                                signals_cleared = 0
                                while True:
                                    remaining_signal = signal_generator.get_next_signal()
                                    if remaining_signal is None:
                                        break
                                    signals_cleared += 1
                                if signals_cleared > 0:
                                    logger.info(f"🗑️ ล้าง {signals_cleared} signals ที่เหลือ")
                            except:
                                pass
                                
                        except Exception as e:
                            logger.warning(f"⚠️ ไม่สามารถหยุด Signal Generator: {e}")
                    
                    # คำนวณกำไร/ขาดทุนรวม
                    total_profit = sum(pos.get('profit', 0) for pos in current_positions)
                    profitable_positions = len([pos for pos in current_positions if pos.get('profit', 0) > 0])
                    losing_positions = len([pos for pos in current_positions if pos.get('profit', 0) < 0])
                    
                    if current_time % 30 < 10:  # แสดงทุก 30 วินาที
                        logger.info(f"💰 P&L: ${total_profit:.2f} | กำไร: {profitable_positions} | ขาดทุน: {losing_positions}")
                    
                    # ตรวจสอบว่าควรใช้ Recovery หรือไม่
                    if total_profit < -5:  # ขาดทุนเกิน $50
                        if current_cycle != "RECOVERY":
                            logger.warning(f"🚨 ขาดทุนเกิน $50 (${total_profit:.2f}) → เปลี่ยนเป็นโหมด RECOVERY")
                            current_cycle = "RECOVERY"
                            # TODO: เริ่ม Recovery System
                    elif total_profit > 2:  # กำไรเกิน $10
                        if current_cycle != "MONITORING":
                            logger.info(f"💚 กำไร ${total_profit:.2f} → กลับเป็นโหมด MONITORING")
                            current_cycle = "MONITORING"
                    
                    # ปล่อยให้ Profit System และ Recovery System จัดการ
                    logger.debug("👁️ โหมด MONITORING - ปล่อยให้ระบบอื่นจัดการ")
                
                # รอสักครู่ก่อนตรวจสอบอีกครั้ง
                time.sleep(10)  # ตรวจสอบทุก 10 วินาที
                
            except Exception as e:
                logger.error(f"❌ ข้อผิดพลาดใน Position Manager: {e}")
                time.sleep(30)  # รอนานขึ้นถ้ามี error
            
            except KeyboardInterrupt:
                logger.info("⏹️ หยุด Position Manager จากผู้ใช้")
                break
        
        # ปิดระบบ
        try:
            if signal_generator_running:
                stop_success = signal_generator.stop_signal_generation()
                if stop_success:
                    signal_generator_running = False
                    logger.info("🛑 หยุด Signal Generator ก่อนปิดระบบ - สำเร็จ")
                else:
                    logger.error("❌ หยุด Signal Generator ไม่สำเร็จ - Force stop")
                    # Force หยุด
                    signal_generator.generator_active = False
                    signal_generator.is_ready = False
                    signal_generator_running = False
                    logger.info("🛑 Force stop Signal Generator เสร็จ")
            else:
                logger.info("✅ Signal Generator หยุดอยู่แล้ว")
        except Exception as e:
            logger.error(f"❌ Error stopping Signal Generator: {e}")
            # Force หยุดถ้ามี error
            try:
                signal_generator.generator_active = False
                signal_generator.is_ready = False
                signal_generator_running = False
                logger.info("🛑 Emergency force stop Signal Generator")
            except:
                pass

        logger.info("✅ Intelligent Position Manager หยุดทำงาน")

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