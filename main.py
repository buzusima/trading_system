#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELLIGENT GOLD TRADING SYSTEM - MAIN ENTRY POINT (CORRECTED)
=============================================================
จุดเริ่มต้นหลักของระบบเทรดทองอัจฉริยะ - เวอร์ชันที่แก้ไข import แล้ว
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

# ===== SYSTEM IMPORTS - แก้ไข CLASS NAMES =====
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

# Market Intelligence - แก้ไข CLASS NAME
try:
    from market_intelligence.market_analyzer import RealTimeMarketAnalyzer, IntelligentStrategySelector
    components_loaded['market_analyzer'] = True
except ImportError as e:
    components_loaded['market_analyzer'] = False
    log_status(f"⚠️ Market analyzer not loaded: {e}")

# Recovery System - แก้ไข CLASS NAME
try:
    from intelligent_recovery.recovery_engine import RealRecoveryEngine
    components_loaded['recovery_selector'] = True
except ImportError as e:
    components_loaded['recovery_selector'] = False
    log_status(f"⚠️ Recovery selector not loaded: {e}")

# Position Management - แก้ไข CLASS NAME
try:
    from position_management.position_tracker import RealPositionTracker
    components_loaded['position_tracker'] = True
except ImportError as e:
    components_loaded['position_tracker'] = False
    log_status(f"⚠️ Position tracker not loaded: {e}")

# MT5 Integration - แก้ไข CLASS NAME
try:
    from mt5_integration.mt5_connector import RealMT5Connector, auto_connect_mt5
    components_loaded['mt5_connector'] = True
except ImportError as e:
    components_loaded['mt5_connector'] = False
    log_status(f"⚠️ MT5 connector not loaded: {e}")

# GUI System
try:
    from gui_system.main_window import TradingDashboard
    components_loaded['gui'] = True
except ImportError as e:
    components_loaded['gui'] = False
    log_status(f"⚠️ GUI not loaded: {e}")

# ===== SYSTEM STATUS CLASS =====
class SystemStatus:
    """แสดงสถานะระบบ"""
    
    def __init__(self):
        self.uptime_start = datetime.now()
    
    def show_status(self):
        """แสดงสถานะปัจจุบัน"""
        print("\n" + "="*50)
        print("📊 SYSTEM STATUS")
        print("="*50)
        
        # Uptime
        uptime = datetime.now() - self.uptime_start
        print(f"⏱️ Uptime: {uptime}")
        
        # Components
        print(f"🔧 Components: {len(components_loaded)}")
        loaded_count = sum(1 for loaded in components_loaded.values() if loaded)
        print(f"✅ Loaded: {loaded_count}/{len(components_loaded)}")
        
        # Component details
        for component, loaded in components_loaded.items():
            status = "✅" if loaded else "❌"
            print(f"   {status} {component}")
        
        # MT5 Status
        if MT5_AVAILABLE:
            print(f"🔌 MT5: Available")
            if mt5.terminal_info():
                terminal_info = mt5.terminal_info()
                print(f"   Connected: {'Yes' if terminal_info.connected else 'No'}")
            else:
                print(f"   Connected: No")
        else:
            print(f"🔌 MT5: Not Available")
        
        print("="*50)

# ===== MAIN FUNCTION - เรียบง่าย =====
def main():
    """Main function - เวอร์ชันเรียบง่าย"""
    
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