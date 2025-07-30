#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELLIGENT GOLD TRADING SYSTEM - MAIN ENTRY POINT (FINAL WORKING VERSION)
=========================================================================
เชื่อมต่อกับระบบทั้งหมดใน git และแก้ไข imports ให้ตรงถูกต้อง
"""

import sys
import os
import time
import threading
import traceback
from datetime import datetime, timedelta
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

# ===== FIX IMPORTS BEFORE LOADING =====
def patch_signal_generator_imports():
    """แก้ไข imports ใน signal_generator ก่อนโหลด"""
    try:
        signal_gen_path = current_dir / "adaptive_entries" / "signal_generator.py"
        if signal_gen_path.exists():
            content = signal_gen_path.read_text(encoding='utf-8')
            
            # แก้ไข import ที่ผิด
            fixes = [
                ('from market_intelligence.market_analyzer import MarketAnalyzer', 
                 'from market_intelligence.market_analyzer import RealTimeMarketAnalyzer as MarketAnalyzer'),
                ('self.market_analyzer = MarketAnalyzer("XAUUSD")()', 
                 'self.market_analyzer = MarketAnalyzer("XAUUSD")'),
                ('if not self.market_analyzer.analysis_active:', 
                 'if not getattr(self.market_analyzer, "is_analyzing", False):'),
                ('params.min_volume', 'getattr(params, "min_volume", getattr(params.volume_settings, "base_lot_size", 0.01))'),
                ('params.max_volume', 'getattr(params, "max_volume", getattr(params.volume_settings, "max_lot_size", 1.0))'),
                ('params.max_spread', 'getattr(params, "max_spread", 3.0)'),
                ('params.signal_cooldown', 'getattr(params, "signal_cooldown", 15)'),
                ('params.strategy_weights', 'getattr(params, "strategy_weights", {})'),
                ('params.session_parameters', 'getattr(params, "session_parameters", {})')
            ]
            
            for old, new in fixes:
                if old in content:
                    content = content.replace(old, new)
                    log_status(f"✅ Fixed: {old[:50]}...")
            
            # เขียนกลับ
            signal_gen_path.write_text(content, encoding='utf-8')
            log_status("✅ Signal generator imports fixed")
            return True
    except Exception as e:
        log_status(f"❌ Failed to patch signal generator: {e}", True)
    return False

# แก้ไข imports ก่อนโหลดโมดูล
patch_signal_generator_imports()

# ===== SYSTEM IMPORTS =====
components_loaded = {}

# Config
try:
    from config.settings import get_system_settings
    components_loaded['settings'] = True
    log_status("✅ Settings loaded")
except ImportError as e:
    components_loaded['settings'] = False
    log_status(f"❌ Settings failed: {e}")

try:
    from config.trading_params import get_trading_parameters
    components_loaded['trading_params'] = True
    log_status("✅ Trading parameters loaded")
except ImportError as e:
    components_loaded['trading_params'] = False
    log_status(f"❌ Trading parameters failed: {e}")

# Market Intelligence
try:
    from market_intelligence.market_analyzer import RealTimeMarketAnalyzer
    components_loaded['market_analyzer'] = True
    log_status("✅ Market analyzer loaded")
except ImportError as e:
    components_loaded['market_analyzer'] = False
    log_status(f"❌ Market analyzer failed: {e}")

# Signal Generator
try:
    from adaptive_entries.signal_generator import get_intelligent_signal_generator
    components_loaded['signal_generator'] = True
    log_status("✅ Signal generator loaded")
except ImportError as e:
    components_loaded['signal_generator'] = False
    log_status(f"❌ Signal generator failed: {e}")

# Order Executor
try:
    from mt5_integration.order_executor import RealOrderExecutor
    components_loaded['order_executor'] = True
    log_status("✅ Order executor loaded")
except ImportError as e:
    components_loaded['order_executor'] = False
    log_status(f"❌ Order executor failed: {e}")

# Recovery Engine
try:
    from intelligent_recovery.recovery_engine import RealRecoveryEngine
    components_loaded['recovery_engine'] = True
    log_status("✅ Recovery engine loaded")
except ImportError as e:
    components_loaded['recovery_engine'] = False
    log_status(f"❌ Recovery engine failed: {e}")

# Position Tracker
try:
    from position_management.position_tracker import RealPositionTracker
    components_loaded['position_tracker'] = True
    log_status("✅ Position tracker loaded")
except ImportError as e:
    components_loaded['position_tracker'] = False
    log_status(f"❌ Position tracker failed: {e}")

# GUI System
try:
    from gui_system.main_window import TradingDashboard
    components_loaded['gui'] = True
    log_status("✅ GUI loaded")
except ImportError as e:
    components_loaded['gui'] = False
    log_status(f"❌ GUI failed: {e}")

class IntelligentTradingSystem:
    """Intelligent Trading System - เชื่อมต่อกับระบบใน git"""
    
    def __init__(self):
        self.is_running = False
        self.mt5_connected = False
        self.gold_symbol = "XAUUSD"
        
        # Core components
        self.market_analyzer = None
        self.signal_generator = None
        self.order_executor = None
        self.recovery_engine = None
        self.position_tracker = None
        
        # Threads
        self.system_thread = None
        self.monitor_thread = None
        self.start_time = None
        
        log_status("🚀 Intelligent Trading System initialized")
    
    def check_components(self):
        """ตรวจสอบ components"""
        total = len(components_loaded)
        loaded = sum(1 for status in components_loaded.values() if status)
        
        log_status(f"📊 Components: {loaded}/{total}")
        
        for name, status in components_loaded.items():
            log_status(f"  {'✅' if status else '❌'} {name}")
        
        return loaded >= 4
    
    def initialize_mt5(self):
        """เชื่อมต่อ MT5"""
        if not MT5_AVAILABLE:
            log_status("❌ MT5 not available", True)
            return False
        
        try:
            if not mt5.initialize():
                log_status("❌ MT5 initialization failed", True)
                return False
            
            # Auto-detect gold symbol
            symbols = ["XAUUSD.v", "XAUUSD", "GOLD", "GOLDUSD", "XAU/USD"]
            for symbol in symbols:
                info = mt5.symbol_info(symbol)
                if info and info.visible:
                    self.gold_symbol = symbol
                    log_status(f"✅ Found gold symbol: {symbol}")
                    break
            
            # Verify account
            account_info = mt5.account_info()
            if not account_info:
                log_status("❌ Cannot get account info", True)
                return False
            
            if not account_info.trade_allowed:
                log_status("❌ Trading not allowed on this account", True)
                return False
            
            self.mt5_connected = True
            log_status(f"✅ MT5 connected - Account: {account_info.login}")
            return True
            
        except Exception as e:
            log_status(f"❌ MT5 connection error: {e}", True)
            return False
    
    def initialize_components(self):
        """เริ่มต้น components"""
        if not self.mt5_connected:
            log_status("❌ MT5 not connected", True)
            return False
        
        success_count = 0
        
        # 1. Market Analyzer
        if components_loaded['market_analyzer']:
            try:
                self.market_analyzer = RealTimeMarketAnalyzer(self.gold_symbol)
                log_status("✅ Market analyzer initialized")
                success_count += 1
            except Exception as e:
                log_status(f"❌ Market analyzer error: {e}", True)
        
        # 2. Order Executor
        if components_loaded['order_executor']:
            try:
                self.order_executor = RealOrderExecutor()
                log_status("✅ Order executor initialized")
                success_count += 1
            except Exception as e:
                log_status(f"❌ Order executor error: {e}", True)
        
        # 3. Position Tracker
        if components_loaded['position_tracker']:
            try:
                self.position_tracker = RealPositionTracker()
                log_status("✅ Position tracker initialized")
                success_count += 1
            except Exception as e:
                log_status(f"❌ Position tracker error: {e}", True)
        
        # 4. Recovery Engine
        if components_loaded['recovery_engine']:
            try:
                self.recovery_engine = RealRecoveryEngine()
                log_status("✅ Recovery engine initialized")
                success_count += 1
            except Exception as e:
                log_status(f"❌ Recovery engine error: {e}", True)
        
        # 5. Signal Generator (last)
        if components_loaded['signal_generator']:
            try:
                self.signal_generator = get_intelligent_signal_generator()
                log_status("✅ Signal generator initialized")
                success_count += 1
            except Exception as e:
                log_status(f"❌ Signal generator error: {e}", True)
                traceback.print_exc()
        
        log_status(f"📊 Components initialized: {success_count}")
        
        # Connect components
        self._connect_components()
        
        return success_count >= 3
    
    def _connect_components(self):
        """เชื่อมต่อ components เข้าด้วยกัน"""
        connections = 0
        
        # Signal Generator → Order Executor
        if self.signal_generator and self.order_executor:
            if hasattr(self.signal_generator, 'order_executor'):
                self.signal_generator.order_executor = self.order_executor
                connections += 1
                log_status("✅ Signal Generator → Order Executor")
        
        # Market Analyzer → Signal Generator
        if self.market_analyzer and self.signal_generator:
            if hasattr(self.signal_generator, 'market_analyzer'):
                self.signal_generator.market_analyzer = self.market_analyzer
                connections += 1
                log_status("✅ Market Analyzer → Signal Generator")
        
        # Order Executor → Position Tracker
        if self.order_executor and self.position_tracker:
            if hasattr(self.order_executor, 'position_tracker'):
                self.order_executor.position_tracker = self.position_tracker
                connections += 1
                log_status("✅ Order Executor → Position Tracker")
        
        # Position Tracker → Recovery Engine
        if self.position_tracker and self.recovery_engine:
            if hasattr(self.recovery_engine, 'position_tracker'):
                self.recovery_engine.position_tracker = self.position_tracker
                connections += 1
                log_status("✅ Position Tracker → Recovery Engine")
        
        log_status(f"🔗 Component connections: {connections}")
    
    def start_all_components(self):
        """เริ่มต้น components ทั้งหมด"""
        try:
            # 1. Market Analyzer
            if self.market_analyzer and hasattr(self.market_analyzer, 'start_analysis'):
                self.market_analyzer.start_analysis()
                log_status("✅ Market analysis started")
            
            # 2. Order Executor
            if self.order_executor and hasattr(self.order_executor, 'start_execution_engine'):
                self.order_executor.start_execution_engine()
                log_status("✅ Order execution started")
            
            # 3. Position Tracker
            if self.position_tracker and hasattr(self.position_tracker, 'start_tracking'):
                self.position_tracker.start_tracking()
                log_status("✅ Position tracking started")
            
            # 4. Recovery Engine
            if self.recovery_engine:
                if hasattr(self.recovery_engine, 'start_recovery_monitoring'):
                    self.recovery_engine.start_recovery_monitoring()
                elif hasattr(self.recovery_engine, 'start_recovery_engine'):
                    self.recovery_engine.start_recovery_engine()
                log_status("✅ Recovery engine started")
            
            # 5. Signal Generator (last and most important)
            if self.signal_generator:
                if hasattr(self.signal_generator, 'start_signal_generation'):
                    if self.signal_generator.start_signal_generation():
                        log_status("🎯 SIGNAL GENERATOR STARTED!")
                        log_status("🚀 SYSTEM IS NOW GENERATING TRADING SIGNALS!")
                    else:
                        log_status("❌ Signal generator failed to start", True)
                        return False
                else:
                    # Manual activation
                    if hasattr(self.signal_generator, 'generation_active'):
                        self.signal_generator.generation_active = True
                        log_status("🎯 Signal generator activated manually")
            
            return True
            
        except Exception as e:
            log_status(f"❌ Component start error: {e}", True)
            return False
    
    def start_trading_system(self):
        """เริ่มระบบเทรด"""
        try:
            log_status("🚀 STARTING INTELLIGENT TRADING SYSTEM...")
            self.start_time = datetime.now()
            self.is_running = True
            
            # Start all components
            if not self.start_all_components():
                log_status("❌ Failed to start components", True)
                return False
            
            # Start monitoring
            self.monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
            self.monitor_thread.start()
            
            log_status("✅ TRADING SYSTEM FULLY OPERATIONAL!")
            log_status("📡 Signal Generator → Order Executor → MT5 Pipeline Active")
            return True
            
        except Exception as e:
            log_status(f"❌ System start error: {e}", True)
            self.is_running = False
            return False
    
    def _monitor_system(self):
        """Monitor ระบบ"""
        log_status("🔄 System monitoring started")
        
        while self.is_running:
            try:
                # แสดงสถานะทุก 30 วินาที
                if int(time.time()) % 30 == 0:
                    self._show_status()
                
                time.sleep(1)
                
            except Exception as e:
                log_status(f"❌ Monitor error: {e}", True)
                time.sleep(5)
    
    def _show_status(self):
        """แสดงสถานะระบบ"""
        try:
            uptime = datetime.now() - self.start_time if self.start_time else timedelta(0)
            
            # Get current market data
            current_price = 0.0
            if MT5_AVAILABLE and self.mt5_connected:
                tick = mt5.symbol_info_tick(self.gold_symbol)
                if tick:
                    current_price = (tick.bid + tick.ask) / 2
            
            # Get signal generator stats
            signal_stats = {}
            if self.signal_generator and hasattr(self.signal_generator, 'get_statistics'):
                signal_stats = self.signal_generator.get_statistics()
            
            log_status("=" * 60)
            log_status("📊 INTELLIGENT TRADING SYSTEM STATUS")
            log_status(f"⏱️ Uptime: {uptime}")
            log_status(f"💰 Gold Price: ${current_price:.2f}")
            log_status(f"🔌 MT5: {'✅ Connected' if self.mt5_connected else '❌ Disconnected'}")
            log_status(f"🎯 Signals: {'✅ Active' if self.signal_generator and getattr(self.signal_generator, 'generation_active', False) else '❌ Inactive'}")
            log_status(f"⚡ Orders: {'✅ Running' if self.order_executor and getattr(self.order_executor, 'is_running', False) else '❌ Stopped'}")
            log_status(f"📊 Market: {'✅ Analyzing' if self.market_analyzer and getattr(self.market_analyzer, 'is_analyzing', False) else '❌ Idle'}")
            
            if signal_stats:
                log_status(f"📈 Signals Generated Today: {signal_stats.get('signals_generated_today', 0)}")
                log_status(f"📋 Signals Executed: {signal_stats.get('signals_executed_today', 0)}")
                log_status(f"🎯 Success Rate: {signal_stats.get('success_rate_percent', 0):.1f}%")
                log_status(f"📊 Volume Today: {signal_stats.get('daily_volume_generated', 0):.2f} lots")
            
            log_status("=" * 60)
            
        except Exception as e:
            log_status(f"❌ Status error: {e}", True)
    
    def stop_system(self):
        """หยุดระบบ"""
        try:
            log_status("🛑 Stopping trading system...")
            self.is_running = False
            
            # Stop Signal Generator first
            if self.signal_generator and hasattr(self.signal_generator, 'stop_signal_generation'):
                self.signal_generator.stop_signal_generation()
                log_status("🛑 Signal generator stopped")
            
            # Stop Order Executor
            if self.order_executor and hasattr(self.order_executor, 'stop_execution_engine'):
                self.order_executor.stop_execution_engine()
                log_status("🛑 Order executor stopped")
            
            # Stop Market Analyzer
            if self.market_analyzer and hasattr(self.market_analyzer, 'stop_analysis'):
                self.market_analyzer.stop_analysis()
                log_status("🛑 Market analyzer stopped")
            
            # Stop Position Tracker
            if self.position_tracker and hasattr(self.position_tracker, 'stop_tracking'):
                self.position_tracker.stop_tracking()
                log_status("🛑 Position tracker stopped")
            
            # Stop Recovery Engine
            if self.recovery_engine and hasattr(self.recovery_engine, 'stop_recovery_engine'):
                self.recovery_engine.stop_recovery_engine()
                log_status("🛑 Recovery engine stopped")
            
            log_status("✅ All systems stopped")
            
        except Exception as e:
            log_status(f"❌ Stop error: {e}", True)
    
    def run_console_mode(self):
        """Console mode"""
        log_status("💻 Console mode activated")
        
        if not self.start_trading_system():
            log_status("❌ Failed to start trading system", True)
            return
        
        try:
            log_status("🎮 Commands: [s]tatus, [p]erformance, [q]uit")
            
            while True:
                cmd = input("\n🎮 Command: ").strip().lower()
                
                if cmd in ['q', 'quit', 'exit']:
                    break
                elif cmd in ['s', 'status']:
                    self._show_status()
                elif cmd in ['p', 'performance']:
                    self._show_performance()
                elif cmd in ['h', 'help']:
                    self._show_commands()
                else:
                    print("Unknown command. Type 'h' for help.")
                    
        except KeyboardInterrupt:
            log_status("👋 Interrupted by user")
        finally:
            self.stop_system()
    
    def _show_performance(self):
        """แสดงประสิทธิภาพ"""
        if self.signal_generator and hasattr(self.signal_generator, 'get_strategy_performance'):
            performance = self.signal_generator.get_strategy_performance()
            
            log_status("📈 STRATEGY PERFORMANCE")
            log_status("-" * 40)
            for strategy, stats in performance.items():
                log_status(f"{strategy}:")
                log_status(f"  Generated: {stats['signals_generated']}")
                log_status(f"  Executed: {stats['signals_executed']}")
                log_status(f"  Success Rate: {stats['success_rate_percent']}%")
                log_status(f"  Last Used: {stats['last_used']}")
    
    def _show_commands(self):
        """แสดงคำสั่ง"""
        print("\n🎮 Available Commands:")
        print("  s - Show system status")
        print("  p - Show performance stats")
        print("  h - Show this help")
        print("  q - Quit system")
    
    def run_gui_mode(self):
        """GUI mode"""
        if not components_loaded['gui']:
            log_status("❌ GUI not available - switching to console", True)
            return self.run_console_mode()
        
        try:
            log_status("🖥️ Starting GUI mode...")
            
            # Start trading system
            if not self.start_trading_system():
                log_status("❌ Failed to start trading system", True)
                return self.run_console_mode()
            
            # Create and run GUI
            dashboard = TradingDashboard()
            
            # Set trading system reference
            if hasattr(dashboard, 'set_trading_system'):
                dashboard.set_trading_system(self)
            
            # Run GUI main loop
            dashboard.root.mainloop()
            
        except Exception as e:
            log_status(f"❌ GUI error: {e}", True)
            traceback.print_exc()
            log_status("🔄 Switching to console mode...")
            return self.run_console_mode()
        finally:
            self.stop_system()

def main():
    """Main entry point"""
    print("🚀 INTELLIGENT GOLD TRADING SYSTEM")
    print("=" * 50)
    print("⚠️  LIVE TRADING - REAL MONEY")
    print("⚠️  CONNECTED TO YOUR GIT SYSTEM")
    print("⚠️  ALL IMPORTS FIXED")
    print("=" * 50)
    
    system = IntelligentTradingSystem()
    
    try:
        # Check components
        if not system.check_components():
            log_status("❌ Not enough components loaded", True)
            input("Press Enter to exit...")
            return
        
        # Connect to MT5
        if not system.initialize_mt5():
            log_status("❌ Failed to connect to MT5", True)
            input("Press Enter to exit...")
            return
        
        # Initialize components
        if not system.initialize_components():
            log_status("❌ Failed to initialize components", True)
            input("Press Enter to exit...")
            return
        
        # Select mode
        print("\n🎮 Select Mode:")
        print("1. Console Mode (Recommended for debugging)")
        print("2. GUI Mode (Visual interface)")
        
        while True:
            try:
                choice = input("\nEnter choice (1 or 2): ").strip()
                
                if choice == "1":
                    log_status("💻 Starting console mode...")
                    system.run_console_mode()
                    break
                elif choice == "2":
                    log_status("🖥️ Starting GUI mode...")
                    system.run_gui_mode()
                    break
                else:
                    print("❌ Invalid choice. Enter 1 or 2.")
                    
            except KeyboardInterrupt:
                log_status("👋 Goodbye!")
                break
    
    except Exception as e:
        log_status(f"💥 Fatal error: {e}", True)
        traceback.print_exc()
    
    finally:
        # Cleanup
        if hasattr(system, 'stop_system'):
            system.stop_system()
        
        if MT5_AVAILABLE:
            mt5.shutdown()
            log_status("🔌 MT5 disconnected")
        
        log_status("🔚 System shutdown complete")

if __name__ == "__main__":
    main()