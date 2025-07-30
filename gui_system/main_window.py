#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELLIGENT GOLD TRADING SYSTEM - MAIN GUI DASHBOARD
===================================================
หน้าจอควบคุมหลักสำหรับระบบเทรดทองอัจฉริยะ
แสดงผลแบบ Real-time และควบคุมการทำงานของระบบ

🎯 FEATURES:
- Real-time trading dashboard
- Position monitoring และ management
- Recovery system control
- Market intelligence display
- Performance analytics
- Risk management panel
- System control และ monitoring
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import json
from dataclasses import asdict

# Internal imports (จะต้องมี modules เหล่านี้)
try:
    import sys
    from pathlib import Path
    current_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(current_dir))
    
    from mt5_integration.mt5_connector import RealMT5Connector, auto_connect_mt5
    from market_intelligence.market_analyzer import RealTimeMarketAnalyzer, IntelligentStrategySelector
    from intelligent_recovery.recovery_engine import RealRecoveryEngine
    from position_management.position_tracker import RealPositionTracker
    
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Module import error: {e}")
    MODULES_AVAILABLE = False

class TradingDashboard:
    """
    Main Trading Dashboard - หน้าจอควบคุมหลัก
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🚀 Intelligent Gold Trading System - Professional Dashboard v1.0")
        self.root.geometry("1400x900")
        self.root.configure(bg="#1e1e1e")
        
        # System components
        self.mt5_connector = None
        self.market_analyzer = None
        self.strategy_selector = None
        self.recovery_engine = None
        self.position_tracker = None
        
        # GUI state
        self.is_system_running = False
        self.is_trading_active = False
        self.is_recovery_active = False
        self.update_thread = None
        self.should_update = False
        
        # Data storage
        self.last_market_analysis = None
        self.last_portfolio_metrics = None
        self.last_recovery_stats = None
        
        # Create GUI
        self._setup_styles()
        self._create_menu()
        self._create_main_layout()
        self._create_status_bar()
        
        # Bind events
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        print("🖥️ GUI Dashboard initialized")
    
    def _setup_styles(self):
        """ตั้งค่า themes และ styles"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Define colors
        self.colors = {
            'bg_dark': '#1e1e1e',
            'bg_medium': '#2d2d2d',
            'bg_light': '#3d3d3d',
            'text_white': '#ffffff',
            'text_gray': '#cccccc',
            'accent_blue': '#0078d4',
            'accent_green': '#10b981',
            'accent_red': '#ef4444',
            'accent_yellow': '#f59e0b'
        }
        
        # Configure styles
        self.style.configure('Dark.TFrame', background=self.colors['bg_dark'])
        self.style.configure('Medium.TFrame', background=self.colors['bg_medium'])
        self.style.configure('Light.TFrame', background=self.colors['bg_light'])
        
        self.style.configure('White.TLabel', 
                           background=self.colors['bg_dark'], 
                           foreground=self.colors['text_white'],
                           font=('Segoe UI', 10))
        
        self.style.configure('Title.TLabel', 
                           background=self.colors['bg_dark'], 
                           foreground=self.colors['text_white'],
                           font=('Segoe UI', 12, 'bold'))
        
        self.style.configure('Success.TButton', 
                           background=self.colors['accent_green'],
                           foreground='white',
                           font=('Segoe UI', 10, 'bold'))
        
        self.style.configure('Danger.TButton', 
                           background=self.colors['accent_red'],
                           foreground='white',
                           font=('Segoe UI', 10, 'bold'))
        
        self.style.configure('Primary.TButton', 
                           background=self.colors['accent_blue'],
                           foreground='white',
                           font=('Segoe UI', 10, 'bold'))
    
    def _create_menu(self):
        """สร้าง menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # System menu
        system_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="System", menu=system_menu)
        system_menu.add_command(label="Connect MT5", command=self._connect_mt5)
        system_menu.add_command(label="Disconnect MT5", command=self._disconnect_mt5)
        system_menu.add_separator()
        system_menu.add_command(label="Start System", command=self._start_system)
        system_menu.add_command(label="Stop System", command=self._stop_system)
        system_menu.add_separator()
        system_menu.add_command(label="Exit", command=self._on_closing)
        
        # Trading menu
        trading_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Trading", menu=trading_menu)
        trading_menu.add_command(label="Start Trading", command=self._start_trading)
        trading_menu.add_command(label="Stop Trading", command=self._stop_trading)
        trading_menu.add_separator()
        trading_menu.add_command(label="Start Recovery", command=self._start_recovery)
        trading_menu.add_command(label="Stop Recovery", command=self._stop_recovery)
        trading_menu.add_separator()
        trading_menu.add_command(label="Emergency Stop", command=self._emergency_stop)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Export Positions", command=self._export_positions)
        tools_menu.add_command(label="Performance Report", command=self._show_performance_report)
        tools_menu.add_command(label="Risk Analysis", command=self._show_risk_analysis)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _create_main_layout(self):
        """สร้าง layout หลัก"""
        # Main container
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Top section - System Status และ Controls
        self._create_top_section(main_frame)
        
        # Middle section - Trading Dashboard
        self._create_middle_section(main_frame)
        
        # Bottom section - Logs และ Details
        self._create_bottom_section(main_frame)
    
    def _create_top_section(self, parent):
        """สร้างส่วนบน - System Status และ Controls"""
        top_frame = ttk.Frame(parent, style='Medium.TFrame')
        top_frame.pack(fill='x', pady=(0, 10))
        
        # System Status Panel
        status_frame = ttk.LabelFrame(top_frame, text="🔧 System Status", style='Medium.TFrame')
        status_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # Status indicators
        self.status_labels = {}
        status_items = [
            ('MT5 Connection', 'mt5_status'),
            ('Market Analyzer', 'analyzer_status'),
            ('Recovery Engine', 'recovery_status'),
            ('Position Tracker', 'tracker_status'),
            ('Trading Active', 'trading_status')
        ]
        
        for i, (label, key) in enumerate(status_items):
            row = i // 3
            col = i % 3
            
            ttk.Label(status_frame, text=f"{label}:", style='White.TLabel').grid(
                row=row*2, column=col*2, sticky='w', padx=5, pady=2
            )
            
            status_label = ttk.Label(status_frame, text="🔴 Disconnected", style='White.TLabel')
            status_label.grid(row=row*2+1, column=col*2, sticky='w', padx=5, pady=2)
            self.status_labels[key] = status_label
        
        # Control Panel
        control_frame = ttk.LabelFrame(top_frame, text="🎮 System Control", style='Medium.TFrame')
        control_frame.pack(side='right', fill='y', padx=(5, 0))
        
        # Control buttons
        ttk.Button(control_frame, text="🔌 Connect MT5", 
                  command=self._connect_mt5, style='Primary.TButton').pack(pady=2, padx=5, fill='x')
        
        ttk.Button(control_frame, text="🚀 Start System", 
                  command=self._start_system, style='Success.TButton').pack(pady=2, padx=5, fill='x')
        
        ttk.Button(control_frame, text="💰 Start Trading", 
                  command=self._start_trading, style='Success.TButton').pack(pady=2, padx=5, fill='x')
        
        ttk.Button(control_frame, text="🔧 Start Recovery", 
                  command=self._start_recovery, style='Primary.TButton').pack(pady=2, padx=5, fill='x')
        
        ttk.Button(control_frame, text="⏹️ Stop All", 
                  command=self._stop_system, style='Danger.TButton').pack(pady=2, padx=5, fill='x')
        
        ttk.Button(control_frame, text="🚨 EMERGENCY", 
                  command=self._emergency_stop, style='Danger.TButton').pack(pady=10, padx=5, fill='x')
    
    def _create_middle_section(self, parent):
        """สร้างส่วนกลาง - Trading Dashboard"""
        middle_frame = ttk.Frame(parent, style='Dark.TFrame')
        middle_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Left panel - Market Intelligence และ Trading Performance
        left_panel = ttk.Frame(middle_frame, style='Dark.TFrame')
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        self._create_market_intelligence_panel(left_panel)
        self._create_trading_performance_panel(left_panel)
        
        # Right panel - Positions และ Recovery
        right_panel = ttk.Frame(middle_frame, style='Dark.TFrame')
        right_panel.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        self._create_positions_panel(right_panel)
        self._create_recovery_panel(right_panel)
    
    def _create_market_intelligence_panel(self, parent):
        """สร้าง Market Intelligence Panel"""
        market_frame = ttk.LabelFrame(parent, text="🧠 Market Intelligence", style='Medium.TFrame')
        market_frame.pack(fill='x', pady=(0, 5))
        
        # Market data display
        self.market_labels = {}
        market_data = [
            ('Current Price:', 'current_price'),
            ('Market Condition:', 'market_condition'),
            ('Trading Session:', 'trading_session'),
            ('Trend Direction:', 'trend_direction'),
            ('Trend Strength:', 'trend_strength'),
            ('Volatility Level:', 'volatility_level'),
            ('Recommended Strategy:', 'recommended_strategy'),
            ('Confidence Score:', 'confidence_score'),
            ('Spread Quality:', 'spread_quality'),
            ('Liquidity Score:', 'liquidity_score')
        ]
        
        for i, (label, key) in enumerate(market_data):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(market_frame, text=label, style='White.TLabel').grid(
                row=row, column=col, sticky='w', padx=5, pady=2
            )
            
            value_label = ttk.Label(market_frame, text="N/A", style='White.TLabel')
            value_label.grid(row=row, column=col+1, sticky='w', padx=5, pady=2)
            self.market_labels[key] = value_label
    
    def _create_trading_performance_panel(self, parent):
        """สร้าง Trading Performance Panel"""
        perf_frame = ttk.LabelFrame(parent, text="📊 Trading Performance", style='Medium.TFrame')
        perf_frame.pack(fill='x', pady=(5, 0))
        
        # Performance metrics
        self.performance_labels = {}
        perf_data = [
            ('Net P&L:', 'net_pnl'),
            ('Unrealized P&L:', 'unrealized_pnl'),
            ('Volume Today:', 'volume_today'),
            ('Win Rate:', 'win_rate'),
            ('Recovery Rate:', 'recovery_rate'),
            ('Profit Factor:', 'profit_factor'),
            ('Total Trades:', 'total_trades'),
            ('Active Positions:', 'active_positions'),
            ('Active Recoveries:', 'active_recoveries'),
            ('Risk Score:', 'risk_score')
        ]
        
        for i, (label, key) in enumerate(perf_data):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(perf_frame, text=label, style='White.TLabel').grid(
                row=row, column=col, sticky='w', padx=5, pady=2
            )
            
            value_label = ttk.Label(perf_frame, text="$0.00", style='White.TLabel')
            value_label.grid(row=row, column=col+1, sticky='w', padx=5, pady=2)
            self.performance_labels[key] = value_label
    
    def _create_positions_panel(self, parent):
        """สร้าง Active Positions Panel"""
        pos_frame = ttk.LabelFrame(parent, text="🔒 Active Positions", style='Medium.TFrame')
        pos_frame.pack(fill='both', expand=True, pady=(0, 5))
        
        # Positions treeview
        columns = ('Ticket', 'Type', 'Volume', 'Entry', 'Current', 'P&L', 'Duration', 'Risk')
        self.positions_tree = ttk.Treeview(pos_frame, columns=columns, show='headings', height=8)
        
        # Configure columns
        column_widths = {'Ticket': 80, 'Type': 50, 'Volume': 60, 'Entry': 80, 
                        'Current': 80, 'P&L': 80, 'Duration': 80, 'Risk': 60}
        
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=column_widths.get(col, 100), anchor='center')
        
        # Scrollbar for positions
        pos_scrollbar = ttk.Scrollbar(pos_frame, orient='vertical', command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=pos_scrollbar.set)
        
        self.positions_tree.pack(side='left', fill='both', expand=True)
        pos_scrollbar.pack(side='right', fill='y')
        
        # Position context menu
        self.positions_tree.bind('<Button-3>', self._show_position_context_menu)
    
    def _create_recovery_panel(self, parent):
        """สร้าง Recovery Panel"""
        recovery_frame = ttk.LabelFrame(parent, text="🔧 Recovery Operations", style='Medium.TFrame')
        recovery_frame.pack(fill='both', expand=True, pady=(5, 0))
        
        # Recovery treeview
        columns = ('Recovery ID', 'Strategy', 'Original Ticket', 'Target', 'Current P&L', 'Status')
        self.recovery_tree = ttk.Treeview(recovery_frame, columns=columns, show='headings', height=6)
        
        # Configure columns
        recovery_widths = {'Recovery ID': 120, 'Strategy': 100, 'Original Ticket': 100, 
                          'Target': 80, 'Current P&L': 100, 'Status': 80}
        
        for col in columns:
            self.recovery_tree.heading(col, text=col)
            self.recovery_tree.column(col, width=recovery_widths.get(col, 100), anchor='center')
        
        # Scrollbar for recovery
        recovery_scrollbar = ttk.Scrollbar(recovery_frame, orient='vertical', command=self.recovery_tree.yview)
        self.recovery_tree.configure(yscrollcommand=recovery_scrollbar.set)
        
        self.recovery_tree.pack(side='left', fill='both', expand=True)
        recovery_scrollbar.pack(side='right', fill='y')
        
        # Recovery context menu
        self.recovery_tree.bind('<Button-3>', self._show_recovery_context_menu)
    
    def _create_bottom_section(self, parent):
        """สร้างส่วนล่าง - Logs และ Activity"""
        bottom_frame = ttk.Frame(parent, style='Dark.TFrame')
        bottom_frame.pack(fill='x')
        
        # Activity Log
        log_frame = ttk.LabelFrame(bottom_frame, text="📝 Activity Log", style='Medium.TFrame')
        log_frame.pack(fill='x')
        
        # Log text widget
        self.log_text = tk.Text(log_frame, height=8, bg=self.colors['bg_light'], 
                               fg=self.colors['text_white'], font=('Consolas', 9))
        log_scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
    
    def _create_status_bar(self):
        """สร้าง status bar"""
        self.status_bar = ttk.Frame(self.root, style='Medium.TFrame')
        self.status_bar.pack(side='bottom', fill='x')
        
        # Status bar labels
        self.status_text = ttk.Label(self.status_bar, text="System Ready", style='White.TLabel')
        self.status_text.pack(side='left', padx=5)
        
        self.time_label = ttk.Label(self.status_bar, text="", style='White.TLabel')
        self.time_label.pack(side='right', padx=5)
        
        # Update time
        self._update_time()
    
    def _update_time(self):
        """อัพเดทเวลา"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self._update_time)
    
    # ===== EVENT HANDLERS =====
    
    def _connect_mt5(self):
        """เชื่อมต่อ MT5"""
        try:
            if not MODULES_AVAILABLE:
                messagebox.showerror("Error", "Required modules not available")
                return
            
            self._log_message("🔌 Connecting to MT5...")
            
            # Create MT5 connector
            self.mt5_connector = auto_connect_mt5(["XAUUSD.v"])
            
            # Update status
            self.status_labels['mt5_status'].config(text="🟢 Connected")
            self._log_message("✅ MT5 connected successfully")
            
            # Update status bar
            self.status_text.config(text="MT5 Connected")
            
        except Exception as e:
            self._log_message(f"❌ MT5 connection failed: {e}")
            messagebox.showerror("Connection Error", f"Failed to connect MT5: {e}")
    
    def _disconnect_mt5(self):
        """ตัดการเชื่อมต่อ MT5"""
        try:
            if self.mt5_connector:
                self.mt5_connector.disconnect()
                self.mt5_connector = None
            
            self.status_labels['mt5_status'].config(text="🔴 Disconnected")
            self._log_message("⏹️ MT5 disconnected")
            self.status_text.config(text="MT5 Disconnected")
            
        except Exception as e:
            self._log_message(f"❌ Disconnect error: {e}")
    
    def _start_system(self):
        """เริ่มระบบ"""
        try:
            if not self.mt5_connector or not self.mt5_connector.is_connected():
                messagebox.showwarning("Warning", "Please connect to MT5 first")
                return
            
            self._log_message("🚀 Starting system components...")
            
            # Start Market Analyzer
            self.market_analyzer = RealTimeMarketAnalyzer("XAUUSD.v")
            self.strategy_selector = IntelligentStrategySelector()
            self.market_analyzer.start_analysis()
            self.status_labels['analyzer_status'].config(text="🟢 Running")
            
            # Start Recovery Engine
            self.recovery_engine = RealRecoveryEngine("XAUUSD.v")
            self.recovery_engine.start_recovery_monitoring()
            self.status_labels['recovery_status'].config(text="🟢 Monitoring")
            
            # Start Position Tracker
            self.position_tracker = RealPositionTracker("XAUUSD.v")
            self.position_tracker.start_tracking()
            self.status_labels['tracker_status'].config(text="🟢 Tracking")
            
            # Start GUI updates
            self.is_system_running = True
            self.should_update = True
            self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()
            
            self._log_message("✅ System started successfully")
            self.status_text.config(text="System Running")
            
        except Exception as e:
            self._log_message(f"❌ System start failed: {e}")
            messagebox.showerror("System Error", f"Failed to start system: {e}")
    
    def _stop_system(self):
        """หยุดระบบ"""
        try:
            self._log_message("⏹️ Stopping system...")
            
            # Stop GUI updates
            self.should_update = False
            self.is_system_running = False
            
            # Stop components
            if self.market_analyzer:
                self.market_analyzer.stop_analysis()
                self.status_labels['analyzer_status'].config(text="🔴 Stopped")
            
            if self.recovery_engine:
                self.recovery_engine.stop_recovery_monitoring()
                self.status_labels['recovery_status'].config(text="🔴 Stopped")
            
            if self.position_tracker:
                self.position_tracker.stop_tracking()
                self.status_labels['tracker_status'].config(text="🔴 Stopped")
            
            # Update trading status
            self.is_trading_active = False
            self.is_recovery_active = False
            self.status_labels['trading_status'].config(text="🔴 Inactive")
            
            self._log_message("✅ System stopped")
            self.status_text.config(text="System Stopped")
            
        except Exception as e:
            self._log_message(f"❌ System stop error: {e}")
    
    def _start_trading(self):
        """เริ่มการเทรด"""
        try:
            if not self.is_system_running:
                messagebox.showwarning("Warning", "Please start system first")
                return
            
            # Confirmation dialog
            result = messagebox.askyesno(
                "Confirm Trading", 
                "⚠️ This will start LIVE TRADING with real money.\n\nAre you sure you want to continue?",
                icon='warning'
            )
            
            if not result:
                return
            
            self.is_trading_active = True
            self.status_labels['trading_status'].config(text="🟢 Active")
            self._log_message("💰 Live trading started")
            self.status_text.config(text="LIVE TRADING ACTIVE")
            
        except Exception as e:
            self._log_message(f"❌ Trading start error: {e}")
    
    def _stop_trading(self):
        """หยุดการเทรด"""
        try:
            self.is_trading_active = False
            self.status_labels['trading_status'].config(text="🔴 Inactive")
            self._log_message("⏹️ Trading stopped")
            self.status_text.config(text="Trading Stopped")
            
        except Exception as e:
            self._log_message(f"❌ Trading stop error: {e}")
    
    def _start_recovery(self):
        """เริ่มระบบ Recovery"""
        try:
            if not self.recovery_engine:
                messagebox.showwarning("Warning", "Recovery engine not available")
                return
            
            self.is_recovery_active = True
            self._log_message("🔧 Recovery system activated")
            
        except Exception as e:
            self._log_message(f"❌ Recovery start error: {e}")
    
    def _stop_recovery(self):
        """หยุดระบบ Recovery"""
        try:
            self.is_recovery_active = False
            self._log_message("⏹️ Recovery system deactivated")
            
        except Exception as e:
            self._log_message(f"❌ Recovery stop error: {e}")
    
    def _emergency_stop(self):
        """หยุดฉุกเฉิน"""
        try:
            # Confirmation dialog
            result = messagebox.askyesno(
                "EMERGENCY STOP", 
                "🚨 This will immediately:\n" +
                "• Stop all trading\n" +
                "• Close all open positions\n" +
                "• Stop all recovery operations\n\n" +
                "This action cannot be undone!\n\n" +
                "Are you sure?",
                icon='warning'
            )
            
            if not result:
                return
            
            self._log_message("🚨 EMERGENCY STOP INITIATED")
            
            # Stop all trading
            self.is_trading_active = False
            self.is_recovery_active = False
            
            # Emergency close all positions
            if self.position_tracker:
                self.position_tracker.emergency_close_all()
            
            # Stop all components
            self._stop_system()
            
            self._log_message("🚨 EMERGENCY STOP COMPLETED")
            self.status_text.config(text="EMERGENCY STOP")
            
            messagebox.showinfo("Emergency Stop", "Emergency stop completed successfully")
            
        except Exception as e:
            self._log_message(f"❌ Emergency stop error: {e}")
            messagebox.showerror("Error", f"Emergency stop failed: {e}")
    
    def _export_positions(self):
        """Export ข้อมูล positions"""
        try:
            if not self.position_tracker:
                messagebox.showwarning("Warning", "Position tracker not available")
                return
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                export_file = self.position_tracker.export_positions_to_json(filename)
                if export_file:
                    self._log_message(f"💾 Positions exported to {export_file}")
                    messagebox.showinfo("Export", f"Positions exported successfully to:\n{export_file}")
            
        except Exception as e:
            self._log_message(f"❌ Export error: {e}")
            messagebox.showerror("Export Error", f"Failed to export positions: {e}")
    
    def _show_performance_report(self):
        """แสดงรายงานผลการดำเนินงาน"""
        try:
            if not self.position_tracker:
                messagebox.showwarning("Warning", "Position tracker not available")
                return
            
            report = self.position_tracker.get_position_performance_report()
            
            # Create report window
            report_window = tk.Toplevel(self.root)
            report_window.title("📊 Performance Report")
            report_window.geometry("600x500")
            report_window.configure(bg=self.colors['bg_dark'])
            
            # Report text
            report_text = tk.Text(report_window, bg=self.colors['bg_light'], 
                                 fg=self.colors['text_white'], font=('Consolas', 10))
            
            # Format report
            report_content = self._format_performance_report(report)
            report_text.insert(tk.END, report_content)
            report_text.config(state='disabled')
            
            report_text.pack(fill='both', expand=True, padx=10, pady=10)
            
        except Exception as e:
            self._log_message(f"❌ Performance report error: {e}")
            messagebox.showerror("Report Error", f"Failed to generate report: {e}")
    
    def _show_risk_analysis(self):
        """แสดงการวิเคราะห์ความเสี่ยง"""
        try:
            if not self.position_tracker:
                messagebox.showwarning("Warning", "Position tracker not available")
                return
            
            # Create risk analysis window
            risk_window = tk.Toplevel(self.root)
            risk_window.title("⚠️ Risk Analysis")
            risk_window.geometry("700x600")
            risk_window.configure(bg=self.colors['bg_dark'])
            
            # Get risk data
            portfolio_metrics = self.position_tracker.get_portfolio_metrics()
            risk_positions = {
                'Critical': self.position_tracker.get_positions_by_risk('CRITICAL'),
                'High': self.position_tracker.get_positions_by_risk('HIGH'),
                'Medium': self.position_tracker.get_positions_by_risk('MEDIUM'),
                'Low': self.position_tracker.get_positions_by_risk('LOW')
            }
            
            # Risk analysis content
            risk_content = self._format_risk_analysis(portfolio_metrics, risk_positions)
            
            # Risk text widget
            risk_text = tk.Text(risk_window, bg=self.colors['bg_light'], 
                                fg=self.colors['text_white'], font=('Consolas', 10))
            risk_text.insert(tk.END, risk_content)
            risk_text.config(state='disabled')
            
            risk_text.pack(fill='both', expand=True, padx=10, pady=10)
            
        except Exception as e:
            self._log_message(f"❌ Risk analysis error: {e}")
            messagebox.showerror("Risk Analysis Error", f"Failed to generate risk analysis: {e}")
   
    def _show_about(self):
        """แสดงข้อมูล About"""
        about_text = """
🚀 Intelligent Gold Trading System v1.0

Professional Live Trading Platform for XAUUSD

Features:
- Real-time MT5 integration
- Intelligent market analysis
- Advanced recovery strategies
- Portfolio risk management
- Professional GUI dashboard

⚠️ WARNING: This system trades with real money.
Use at your own risk. Past performance does not guarantee future results.

© 2024 Intelligent Trading Systems
       """
       
        messagebox.showinfo("About", about_text)
    
    def _show_position_context_menu(self, event):
        """แสดง context menu สำหรับ positions"""
        try:
            item = self.positions_tree.selection()[0]
            ticket = self.positions_tree.item(item, 'values')[0]
            
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label=f"Close Position {ticket}", 
                                    command=lambda: self._close_position(int(ticket)))
            context_menu.add_command(label=f"Force Recovery {ticket}", 
                                    command=lambda: self._force_recovery(int(ticket)))
            context_menu.add_separator()
            context_menu.add_command(label="Position Details", 
                                    command=lambda: self._show_position_details(int(ticket)))
            
            context_menu.tk_popup(event.x_root, event.y_root)
            
        except (IndexError, ValueError):
            pass
    
    def _show_recovery_context_menu(self, event):
        """แสดง context menu สำหรับ recovery"""
        try:
            item = self.recovery_tree.selection()[0]
            recovery_id = self.recovery_tree.item(item, 'values')[0]
            
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label=f"Cancel Recovery {recovery_id}", 
                                    command=lambda: self._cancel_recovery(recovery_id))
            context_menu.add_command(label="Recovery Details", 
                                    command=lambda: self._show_recovery_details(recovery_id))
            
            context_menu.tk_popup(event.x_root, event.y_root)
            
        except (IndexError, ValueError):
            pass
    
    def _close_position(self, ticket: int):
        """ปิด position"""
        try:
            if not self.position_tracker:
                return
            
            result = messagebox.askyesno("Confirm", f"Close position {ticket}?")
            if result:
                success = self.position_tracker._close_position(ticket)
                if success:
                    self._log_message(f"✅ Position {ticket} closed successfully")
                else:
                    self._log_message(f"❌ Failed to close position {ticket}")
                    
        except Exception as e:
            self._log_message(f"❌ Close position error: {e}")
    
    def _force_recovery(self, ticket: int):
        """บังคับเริ่ม recovery"""
        try:
            if not self.recovery_engine:
                return
            
            result = messagebox.askyesno("Confirm", f"Force recovery for position {ticket}?")
            if result:
                success = self.recovery_engine.force_recovery(ticket)
                if success:
                    self._log_message(f"🔧 Recovery initiated for position {ticket}")
                else:
                    self._log_message(f"❌ Failed to start recovery for position {ticket}")
                    
        except Exception as e:
            self._log_message(f"❌ Force recovery error: {e}")
    
    def _cancel_recovery(self, recovery_id: str):
        """ยกเลิก recovery"""
        try:
            if not self.recovery_engine:
                return
            
            result = messagebox.askyesno("Confirm", f"Cancel recovery {recovery_id}?")
            if result:
                success = self.recovery_engine.cancel_recovery(recovery_id)
                if success:
                    self._log_message(f"⏹️ Recovery {recovery_id} cancelled")
                else:
                    self._log_message(f"❌ Failed to cancel recovery {recovery_id}")
                    
        except Exception as e:
            self._log_message(f"❌ Cancel recovery error: {e}")
    
    def _show_position_details(self, ticket: int):
        """แสดงรายละเอียด position"""
        try:
            if not self.position_tracker:
                return
            
            position = self.position_tracker.get_position(ticket)
            if not position:
                messagebox.showwarning("Warning", f"Position {ticket} not found")
                return
            
            # Create details window
            details_window = tk.Toplevel(self.root)
            details_window.title(f"📊 Position {ticket} Details")
            details_window.geometry("500x400")
            details_window.configure(bg=self.colors['bg_dark'])
            
            # Position details
            details_content = self._format_position_details(position)
            
            details_text = tk.Text(details_window, bg=self.colors['bg_light'], 
                                    fg=self.colors['text_white'], font=('Consolas', 10))
            details_text.insert(tk.END, details_content)
            details_text.config(state='disabled')
            
            details_text.pack(fill='both', expand=True, padx=10, pady=10)
            
        except Exception as e:
            self._log_message(f"❌ Position details error: {e}")
    
    def _show_recovery_details(self, recovery_id: str):
        """แสดงรายละเอียด recovery"""
        try:
            if not self.recovery_engine:
                return
            
            # Create recovery details window
            details_window = tk.Toplevel(self.root)
            details_window.title(f"🔧 Recovery {recovery_id} Details")
            details_window.geometry("500x400")
            details_window.configure(bg=self.colors['bg_dark'])
            
            # Recovery details content
            details_content = f"Recovery ID: {recovery_id}\n\nDetails will be implemented..."
            
            details_text = tk.Text(details_window, bg=self.colors['bg_light'], 
                                    fg=self.colors['text_white'], font=('Consolas', 10))
            details_text.insert(tk.END, details_content)
            details_text.config(state='disabled')
            
            details_text.pack(fill='both', expand=True, padx=10, pady=10)
            
        except Exception as e:
            self._log_message(f"❌ Recovery details error: {e}")
    
    # ===== UPDATE METHODS =====
    
    def _update_loop(self):
        """Loop การอัพเดท GUI"""
        while self.should_update:
            try:
                self._update_market_intelligence()
                self._update_trading_performance()
                self._update_positions_display()
                self._update_recovery_display()
                
                time.sleep(1)  # Update every second
                
            except Exception as e:
                self._log_message(f"❌ Update loop error: {e}")
                time.sleep(5)
    
    def _update_market_intelligence(self):
        """อัพเดท Market Intelligence display"""
        try:
            if not self.market_analyzer:
                return
            
            analysis = self.market_analyzer.get_current_analysis()
            if not analysis:
                return
            
            # Update market data labels
            self.market_labels['current_price'].config(text=f"${analysis.current_price:.2f}")
            self.market_labels['market_condition'].config(text=analysis.condition.value)
            self.market_labels['trading_session'].config(text=analysis.session.value)
            self.market_labels['trend_direction'].config(text=analysis.trend_direction.value)
            self.market_labels['trend_strength'].config(text=f"{analysis.trend_strength:.1f}%")
            self.market_labels['volatility_level'].config(text=f"{analysis.volatility_level:.1f}%")
            self.market_labels['recommended_strategy'].config(text=analysis.recommended_strategy.value)
            self.market_labels['confidence_score'].config(text=f"{analysis.confidence_score:.1f}%")
            self.market_labels['spread_quality'].config(text=f"{analysis.spread_score:.1f}%")
            self.market_labels['liquidity_score'].config(text=f"{analysis.liquidity_score:.1f}%")
            
            self.last_market_analysis = analysis
            
        except Exception as e:
            self._log_message(f"❌ Market intelligence update error: {e}")
    
    def _update_trading_performance(self):
        """อัพเดท Trading Performance display"""
        try:
            if not self.position_tracker:
                return
            
            metrics = self.position_tracker.get_portfolio_metrics()
            stats = self.position_tracker.get_tracking_stats()
            recovery_stats = self.recovery_engine.get_recovery_stats() if self.recovery_engine else {}
            
            # Update performance labels
            self.performance_labels['net_pnl'].config(text=f"${metrics.total_profit:.2f}")
            self.performance_labels['unrealized_pnl'].config(text=f"${metrics.total_profit:.2f}")
            self.performance_labels['volume_today'].config(text=f"{metrics.total_volume:.2f} lots")
            self.performance_labels['win_rate'].config(text=f"{stats.get('win_rate', 0):.1f}%")
            self.performance_labels['recovery_rate'].config(text=f"{recovery_stats.get('success_rate', 0):.1f}%")
            self.performance_labels['profit_factor'].config(text=f"{metrics.profit_factor:.2f}")
            self.performance_labels['total_trades'].config(text=str(stats.get('total_trades', 0)))
            self.performance_labels['active_positions'].config(text=str(metrics.total_positions))
            self.performance_labels['active_recoveries'].config(text=str(recovery_stats.get('active_recoveries', 0)))
            self.performance_labels['risk_score'].config(text=f"{metrics.risk_score:.1f}")
            
            # Color coding for P&L
            pnl_color = self.colors['accent_green'] if metrics.total_profit >= 0 else self.colors['accent_red']
            self.performance_labels['net_pnl'].config(foreground=pnl_color)
            self.performance_labels['unrealized_pnl'].config(foreground=pnl_color)
            
            # Risk score color coding
            risk_color = self.colors['text_white']
            if metrics.risk_score > 70:
                risk_color = self.colors['accent_red']
            elif metrics.risk_score > 50:
                risk_color = self.colors['accent_yellow']
            else:
                risk_color = self.colors['accent_green']
            
            self.performance_labels['risk_score'].config(foreground=risk_color)
            
            self.last_portfolio_metrics = metrics
            
        except Exception as e:
            self._log_message(f"❌ Performance update error: {e}")
    
    def _update_positions_display(self):
        """อัพเดท Positions display"""
        try:
            if not self.position_tracker:
                return
            
            # Clear existing items
            for item in self.positions_tree.get_children():
                self.positions_tree.delete(item)
            
            # Get positions
            positions = self.position_tracker.positions
            
            # Sort by profit (descending)
            sorted_positions = sorted(positions.values(), key=lambda x: x.profit, reverse=True)
            
            for position in sorted_positions:
                # Format duration
                duration_str = str(position.duration).split('.')[0]  # Remove microseconds
                
                # Risk level emoji
                risk_emojis = {
                    'LOW': '🟢',
                    'MEDIUM': '🟡',
                    'HIGH': '🟠',
                    'CRITICAL': '🔴'
                }
                risk_display = f"{risk_emojis.get(position.risk_level.value, '⚪')} {position.risk_level.value}"
                
                # Insert into treeview
                item_id = self.positions_tree.insert('', 'end', values=(
                    position.ticket,
                    position.position_type.value,
                    f"{position.volume:.2f}",
                    f"{position.open_price:.2f}",
                    f"{position.current_price:.2f}",
                    f"${position.profit:.2f}",
                    duration_str,
                    risk_display
                ))
                
                # Color coding for P&L
                if position.profit >= 0:
                    self.positions_tree.set(item_id, 'P&L', f"${position.profit:.2f}")
                else:
                    self.positions_tree.set(item_id, 'P&L', f"${position.profit:.2f}")
                    
        except Exception as e:
            self._log_message(f"❌ Positions display update error: {e}")
    
    def _update_recovery_display(self):
        """อัพเดท Recovery display"""
        try:
            if not self.recovery_engine:
                return
            
            # Clear existing items
            for item in self.recovery_tree.get_children():
                self.recovery_tree.delete(item)
            
            # Get active recoveries
            active_recoveries = self.recovery_engine.active_recoveries
            
            for recovery_id, plan in active_recoveries.items():
                # Insert into treeview
                self.recovery_tree.insert('', 'end', values=(
                    recovery_id,
                    plan.strategy.value,
                    plan.original_position.ticket,
                    f"${plan.target_profit:.2f}",
                    f"${plan.current_profit:.2f}",
                    plan.status.value
                ))
                
        except Exception as e:
            self._log_message(f"❌ Recovery display update error: {e}")
    
    # ===== UTILITY METHODS =====
    
    def _log_message(self, message: str):
        """เพิ่มข้อความใน activity log"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
            
            # Print to console as well
            print(log_entry.strip())
            
        except Exception as e:
            print(f"❌ Log error: {e}")
   
    def _format_performance_report(self, report: Dict[str, Any]) -> str:
        """จัดรูปแบบรายงานผลการดำเนินงาน"""
        content = f"""
📊 PERFORMANCE REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

📈 SUMMARY
Total Positions: {report['summary']['total_positions']}
Profitable Positions: {report['summary']['profitable_positions']}
Losing Positions: {report['summary']['losing_positions']}
Total Profit: ${report['summary']['total_profit']:.2f}
Win Rate: {report['summary']['win_rate']:.1f}%

⚠️ RISK ANALYSIS
Low Risk: {report['risk_analysis']['low_risk']} positions
Medium Risk: {report['risk_analysis']['medium_risk']} positions
High Risk: {report['risk_analysis']['high_risk']} positions
Critical Risk: {report['risk_analysis']['critical_risk']} positions
Portfolio Risk Score: {report['risk_analysis']['portfolio_risk_score']:.1f}

📊 EXPOSURE ANALYSIS
Long Exposure: {report['exposure_analysis']['long_exposure']:.2f} lots
Short Exposure: {report['exposure_analysis']['short_exposure']:.2f} lots
Net Exposure: {report['exposure_analysis']['net_exposure']:.2f} lots
Total Volume: {report['exposure_analysis']['total_volume']:.2f} lots

📉 PERFORMANCE METRICS
Max Drawdown: {report['performance_metrics']['max_drawdown']:.2f}%
Current Drawdown: {report['performance_metrics']['current_drawdown']:.2f}%
Margin Level: {report['performance_metrics']['margin_level']:.1f}%
Free Margin: ${report['performance_metrics']['free_margin']:.2f}

🏆 TOP PERFORMERS
"""
       
        for i, performer in enumerate(report['top_performers'], 1):
            content += f"{i}. Ticket {performer['ticket']}: ${performer['profit']:.2f} ({performer['roi_percent']:.1f}% ROI)\n"
        
        content += "\n📉 WORST PERFORMERS\n"
        for i, performer in enumerate(report['worst_performers'], 1):
            content += f"{i}. Ticket {performer['ticket']}: ${performer['profit']:.2f} ({performer['roi_percent']:.1f}% ROI)\n"
        
        if report['recommendations']['risk_warnings']:
            content += "\n🚨 RISK WARNINGS\n"
            for warning in report['recommendations']['risk_warnings']:
                content += f"• {warning}\n"
        
        return content
   
    def _format_risk_analysis(self, metrics, risk_positions) -> str:
        """จัดรูปแบบการวิเคราะห์ความเสี่ยง"""
        content = f"""
⚠️ RISK ANALYSIS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

🎯 PORTFOLIO OVERVIEW
Total Positions: {metrics.total_positions}
Total P&L: ${metrics.total_profit:.2f}
Risk Score: {metrics.risk_score:.1f}/100
Margin Level: {metrics.margin_level:.1f}%

📊 RISK DISTRIBUTION
Critical Risk: {len(risk_positions.get('Critical', []))} positions
High Risk: {len(risk_positions.get('High', []))} positions
Medium Risk: {len(risk_positions.get('Medium', []))} positions
Low Risk: {len(risk_positions.get('Low', []))} positions

💰 EXPOSURE ANALYSIS
Long Exposure: {metrics.long_exposure:.2f} lots
Short Exposure: {metrics.short_exposure:.2f} lots
Net Exposure: {metrics.net_exposure:.2f} lots

📉 DRAWDOWN ANALYSIS
Current Drawdown: {metrics.current_drawdown:.2f}%
Max Drawdown: {metrics.max_drawdown:.2f}%

🚨 CRITICAL POSITIONS
"""
       
        critical_positions = risk_positions.get('Critical', [])
        if critical_positions:
            for pos in critical_positions:
                content += f"• Ticket {pos.ticket}: ${pos.profit:.2f} (Duration: {pos.duration})\n"
        else:
            content += "No critical risk positions.\n"
        
        content += f"""
📊 RECOMMENDATIONS
- Monitor positions with critical/high risk
- Consider reducing exposure if risk score > 70
- Maintain margin level above 200%
- Review recovery strategies for losing positions
"""
       
        return content
    
    def _format_position_details(self, position) -> str:
        """จัดรูปแบบรายละเอียด position"""
        content = f"""
📊 POSITION DETAILS
Ticket: {position.ticket}
{'='*50}

🎯 BASIC INFO
Symbol: {position.symbol}
Type: {position.position_type.value}
Volume: {position.volume:.2f} lots
Open Price: ${position.open_price:.2f}
Current Price: ${position.current_price:.2f}

💰 FINANCIAL INFO
Current P&L: ${position.profit:.2f}
Swap: ${position.swap:.2f}
Commission: ${position.commission:.2f}
ROI: {position.roi_percent:.2f}%

⏰ TIMING INFO
Open Time: {position.open_time.strftime('%Y-%m-%d %H:%M:%S')}
Duration: {position.duration}
Last Update: {position.last_update.strftime('%H:%M:%S')}

📈 PERFORMANCE METRICS
Max Profit: ${position.max_profit:.2f}
Max Loss: ${position.max_loss:.2f}
Drawdown from Peak: ${position.drawdown_from_peak:.2f}
Pip Movement: {position.pip_movement:.1f} pips

⚠️ RISK ASSESSMENT
Risk Level: {position.risk_level.value}
Entry Reason: {position.entry_reason}

🔧 RECOVERY INFO
Group: {position.group.value if position.group else 'STANDALONE'}
Group ID: {position.group_id or 'None'}
Recovery Attempts: {position.recovery_attempts}
"""
       
        return content
    
    def _on_closing(self):
        """เมื่อปิดหน้าต่าง"""
        try:
            # Confirmation dialog
            if self.is_system_running or self.is_trading_active:
                result = messagebox.askyesno(
                    "Confirm Exit", 
                    "⚠️ System is currently running.\n\nDo you want to stop all operations and exit?"
                )
                
                if not result:
                    return
            
            # Stop system
            self._stop_system()
            
            # Disconnect MT5
            self._disconnect_mt5()
            
            # Close window
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            print(f"❌ Closing error: {e}")
            self.root.quit()
            self.root.destroy()
    
    def run(self):
        """เริ่มการทำงานของ GUI"""
        try:
            self._log_message("🖥️ GUI Dashboard started")
            self._log_message("📝 Ready for trading operations")
            self.root.mainloop()
            
        except Exception as e:
            print(f"❌ GUI Runtime error: {e}")
            messagebox.showerror("Runtime Error", f"GUI error: {e}")

# ===== MAIN FUNCTION =====

def main():
    """ฟังก์ชันหลักสำหรับรันระบบ"""
    try:
        print("🚀 Starting Intelligent Gold Trading System GUI...")
        
        # Check module availability
        if not MODULES_AVAILABLE:
            print("⚠️ Some modules are not available. Limited functionality.")
        
        # Create and run dashboard
        dashboard = TradingDashboard()
        dashboard.run()
        
    except Exception as e:
        print(f"❌ Main execution error: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()