#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELLIGENT GOLD TRADING SYSTEM - MAIN ENTRY POINT (SIMPLE)
==========================================================
จุดเริ่มต้นหลักของระบบเทรดทองอัจฉริยะ - เวอร์ชันเรียบง่าย
เป็นเพียง entry point ที่เรียกใช้ components อื่นๆ เท่านั้น
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

# ===== BASIC LOGGING =====
def log_status(message, is_error=False):
    timestamp = datetime.now().strftime('%H:%M:%S')
    level = "ERROR" if is_error else "INFO"
    print(f"{timestamp} | {level} | {message}")

# ===== CORE IMPORTS =====
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
    log_status("✅ MetaTrader5 module loaded")
except ImportError:
    MT5_AVAILABLE = False
    log_status("❌ MetaTrader5 module not available", True)

# ===== SYSTEM IMPORTS =====
components_loaded = {}

# Config
try:
    from config.settings import get_system_settings
    components_loaded['settings'] = True
except ImportError as e:
    components_loaded['settings'] = False
    log_status(f"⚠️ Settings not loaded: {e}")

try:
    from config.trading_params import get_trading_parameters
    components_loaded['trading_params'] = True
except ImportError as e:
    components_loaded['trading_params'] = False
    log_status(f"⚠️ Trading params not loaded: {e}")

# Market Intelligence
try:
    from market_intelligence.market_analyzer import MarketAnalyzer
    components_loaded['market_analyzer'] = True
except ImportError as e:
    components_loaded['market_analyzer'] = False
    log_status(f"⚠️ Market analyzer not loaded: {e}")

# Recovery System
try:
    from intelligent_recovery.recovery_selector import RecoverySelector
    components_loaded['recovery_selector'] = True
except ImportError as e:
    components_loaded['recovery_selector'] = False
    log_status(f"⚠️ Recovery selector not loaded: {e}")

# Position Management
try:
    from position_management.position_tracker import PositionTracker
    components_loaded['position_tracker'] = True
except ImportError as e:
    components_loaded['position_tracker'] = False
    log_status(f"⚠️ Position tracker not loaded: {e}")

# MT5 Integration
try:
    from mt5_integration.mt5_connector import MT5Connector
    components_loaded['mt5_connector'] = True
except ImportError as e:
    components_loaded['mt5_connector'] = False
    log_status(f"⚠️ MT5 connector not loaded: {e}")

# GUI
try:
    from gui_system.components.trading_dashboard import TradingDashboard
    components_loaded['gui'] = True
except ImportError as e:
    components_loaded['gui'] = False
    log_status(f"⚠️ GUI not loaded: {e}")

# ===== SIMPLE SYSTEM STATUS =====
class SystemStatus:
    def __init__(self):
        self.start_time = datetime.now()
        self.is_running = True
        self.components = components_loaded
        
    def get_uptime(self):
        return (datetime.now() - self.start_time).total_seconds()
    
    def show_status(self):
        uptime = self.get_uptime()
        loaded = sum(self.components.values())
        total = len(self.components)
        
        print(f"\n{'='*50}")
        print(f"🚀 SYSTEM STATUS")
        print(f"{'='*50}")
        print(f"⏰ Uptime: {uptime:.1f} seconds")
        print(f"🧩 Components: {loaded}/{total} loaded")
        print(f"🔌 MT5: {'Available' if MT5_AVAILABLE else 'Not Available'}")
        
        print(f"\n📊 Component Details:")
        for component, status in self.components.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {component}")
        print(f"{'='*50}\n")

# ===== MAIN FUNCTION =====
def main():
    """ฟังก์ชันหลัก - เรียบง่าย"""
    
    print("🚀 INTELLIGENT GOLD TRADING SYSTEM")
    print("Simple Entry Point Version")
    print("="*50)
    
    # สร้าง system status
    status = SystemStatus()
    status.show_status()
    
    # ตรวจสอบ MT5
    if not MT5_AVAILABLE:
        log_status("❌ Cannot proceed without MetaTrader5", True)
        return False
    
    # เชื่อมต่อ MT5
    log_status("🔌 Connecting to MT5...")
    if not mt5.initialize():
        log_status("❌ Failed to connect to MT5", True)
        return False
    
    log_status("✅ MT5 connected successfully")
    
    # เริ่ม GUI ถ้ามี
    if components_loaded.get('gui', False):
        try:
            log_status("🖥️ Starting GUI...")
            dashboard = TradingDashboard()
            dashboard.root.mainloop()
        except Exception as e:
            log_status(f"❌ GUI error: {e}", True)
    else:
        # Simple text interface
        log_status("📺 GUI not available, using simple interface")
        
        try:
            while True:
                command = input("\n[Trading System] Enter command (status/quit): ").strip().lower()
                
                if command == 'quit':
                    break
                elif command == 'status':
                    status.show_status()
                else:
                    print("Available commands: status, quit")
                    
        except KeyboardInterrupt:
            log_status("⌨️ Keyboard interrupt received")
    
    # ปิดระบบ
    log_status("🔄 Shutting down...")
    if MT5_AVAILABLE:
        mt5.shutdown()
        log_status("✅ MT5 disconnected")
    
    log_status("👋 System shutdown complete")
    return True

# ===== ENTRY POINT =====
if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        log_status(f"❌ Critical error: {e}", True)
        sys.exit(1)