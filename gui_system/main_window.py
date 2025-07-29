#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAIN WINDOW - Updated for Core Trading System Integration
======================================================
หน้าต่างหลักของระบบ GUI ที่ปรับปรุงให้ทำงานกับ Core Trading System

🔄 การเปลี่ยนแปลงหลัก:
- รับ trading_system parameter จาก main.py
- เชื่อมต่อกับ IntelligentTradingSystem แทน Components แยกๆ
- ปรับปรุง Event Handling และ Data Binding
- เพิ่ม Real-time Status Updates จาก Core System
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from collections import deque

# เชื่อมต่อ internal modules
from config.settings import SystemSettings
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class TradingSystemGUI:
    """
    🖥️ Main Trading System GUI - Updated for Core System
    
    หน้าต่างหลักที่เชื่อมต่อกับ IntelligentTradingSystem
    """
    
    def __init__(self, settings: SystemSettings, logger, trading_system):
        self.settings = settings
        self.logger = logger
        self.trading_system = trading_system  # 🔗 Core Trading System
        
        # GUI State
        self.is_connected = False
        self.is_trading = False
        self.system_status = "INITIALIZING"
        
        # Data for display
        self.positions_data = []
        self.performance_data = {}
        self.log_messages = deque(maxlen=1000)
        
        # Threading for UI updates
        self.update_active = False
        self.update_thread = None
        
        # Initialize GUI
        self._setup_main_window()
        self._create_gui_components()
        self._setup_menu()
        self._setup_status_bar()
        
        # Connect to trading system events
        self._connect_to_trading_system()
        
        self.logger.info("🖥️ เริ่มต้น Trading System GUI")
    
    def _setup_main_window(self):
        """ตั้งค่าหน้าต่างหลัก"""
        self.root = tk.Tk()
        self.root.title("🚀 Intelligent Gold Trading System v1.0")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1a1a2e')
        
        # Configure grid weights
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_gui_components(self):
        """สร้าง GUI Components หลัก"""
        
        # === TOP TOOLBAR ===
        self._create_toolbar()
        
        # === MAIN CONTENT AREA ===
        main_frame = tk.Frame(self.root, bg='#1a1a2e')
        main_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Left Panel - Trading Controls & Status
        self._create_left_panel(main_frame)
        
        # Right Panel - Positions & Performance
        self._create_right_panel(main_frame)
        
        # === BOTTOM LOG AREA ===
        self._create_log_area()
    
    def _create_toolbar(self):
        """สร้าง Toolbar"""
        toolbar = tk.Frame(self.root, bg='#16213e', height=60)
        toolbar.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        toolbar.grid_propagate(False)
        
        # Connection Section
        conn_frame = tk.Frame(toolbar, bg='#16213e')
        conn_frame.pack(side='left', padx=10, pady=10)
        
        tk.Label(conn_frame, text="🔌 MT5 Status:", 
                bg='#16213e', fg='white', font=('Arial', 10, 'bold')).pack(side='left')
        
        self.status_label = tk.Label(conn_frame, text="DISCONNECTED", 
                                   bg='#16213e', fg='#e74c3c', font=('Arial', 10, 'bold'))
        self.status_label.pack(side='left', padx=(5, 0))
        
        # Connect Button
        self.connect_btn = tk.Button(conn_frame, text="🔌 Connect MT5", 
                                   command=self._connect_mt5,
                                   bg='#2980b9', fg='white', 
                                   font=('Arial', 9, 'bold'))
        self.connect_btn.pack(side='left', padx=(10, 0))
        
        # Trading Controls Section
        trading_frame = tk.Frame(toolbar, bg='#16213e')
        trading_frame.pack(side='left', padx=20)
        
        # Start Trading Button
        self.start_trading_btn = tk.Button(trading_frame, text="🚀 Start Trading", 
                                         command=self._start_trading,
                                         bg='#27ae60', fg='white', 
                                         font=('Arial', 9, 'bold'),
                                         state='disabled')
        self.start_trading_btn.pack(side='left', padx=5)
        
        # Stop Trading Button
        self.stop_trading_btn = tk.Button(trading_frame, text="🛑 Stop Trading", 
                                        command=self._stop_trading,
                                        bg='#e74c3c', fg='white', 
                                        font=('Arial', 9, 'bold'),
                                        state='disabled')
        self.stop_trading_btn.pack(side='left', padx=5)
        
        # Emergency Stop Button
        self.emergency_btn = tk.Button(trading_frame, text="🚨 EMERGENCY", 
                                     command=self._emergency_stop,
                                     bg='#8b0000', fg='white', 
                                     font=('Arial', 9, 'bold'))
        self.emergency_btn.pack(side='left', padx=5)
        
        # System Status Section
        status_frame = tk.Frame(toolbar, bg='#16213e')
        status_frame.pack(side='right', padx=10)
        
        tk.Label(status_frame, text="System:", 
                bg='#16213e', fg='white', font=('Arial', 10)).pack(side='left')
        
        self.system_status_label = tk.Label(status_frame, text="INITIALIZING", 
                                          bg='#16213e', fg='#f39c12', 
                                          font=('Arial', 10, 'bold'))
        self.system_status_label.pack(side='left', padx=(5, 0))
    
    def _create_left_panel(self, parent):
        """สร้าง Left Panel"""
        left_frame = tk.Frame(parent, bg='#1a1a2e')
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        # Account Info
        self._create_account_info_panel(left_frame)
        
        # Trading Statistics
        self._create_trading_stats_panel(left_frame)
        
        # System Metrics
        self._create_system_metrics_panel(left_frame)
    
    def _create_right_panel(self, parent):
        """สร้าง Right Panel"""
        right_frame = tk.Frame(parent, bg='#1a1a2e')
        right_frame.grid(row=0, column=1, sticky='nsew')
        
        # Create notebook for tabs
        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Positions Tab
        positions_frame = tk.Frame(notebook, bg='#1a1a2e')
        notebook.add(positions_frame, text='📊 Positions')
        self._create_positions_table(positions_frame)
        
        # Performance Tab
        performance_frame = tk.Frame(notebook, bg='#1a1a2e')
        notebook.add(performance_frame, text='📈 Performance')
        self._create_performance_panel(performance_frame)
        
        # Recovery Tab
        recovery_frame = tk.Frame(notebook, bg='#1a1a2e')
        notebook.add(recovery_frame, text='🔄 Recovery')
        self._create_recovery_panel(recovery_frame)
    
    def _create_account_info_panel(self, parent):
        """สร้าง Account Info Panel"""
        info_frame = tk.LabelFrame(parent, text="💳 Account Information", 
                                 bg='#16213e', fg='white', font=('Arial', 10, 'bold'))
        info_frame.pack(fill='x', padx=5, pady=5)
        
        # Account details will be updated from MT5
        self.account_labels = {}
        for i, (key, label) in enumerate([
            ('login', 'Account:'),
            ('balance', 'Balance:'),
            ('equity', 'Equity:'),
            ('profit', 'Profit:'),
            ('margin', 'Margin:')
        ]):
            tk.Label(info_frame, text=label, bg='#16213e', fg='#bdc3c7').grid(
                row=i, column=0, sticky='w', padx=5, pady=2)
            
            self.account_labels[key] = tk.Label(info_frame, text="--", 
                                              bg='#16213e', fg='white', font=('Arial', 9))
            self.account_labels[key].grid(row=i, column=1, sticky='w', padx=5, pady=2)
    
    def _create_trading_stats_panel(self, parent):
        """สร้าง Trading Statistics Panel"""
        stats_frame = tk.LabelFrame(parent, text="📊 Trading Statistics", 
                                  bg='#16213e', fg='white', font=('Arial', 10, 'bold'))
        stats_frame.pack(fill='x', padx=5, pady=5)
        
        self.stats_labels = {}
        for i, (key, label) in enumerate([
            ('total_positions', 'Total Positions:'),
            ('active_positions', 'Active:'),
            ('daily_volume', 'Daily Volume:'),
            ('total_profit', 'Total P&L:'),
            ('win_rate', 'Win Rate:')
        ]):
            tk.Label(stats_frame, text=label, bg='#16213e', fg='#bdc3c7').grid(
                row=i, column=0, sticky='w', padx=5, pady=2)
            
            self.stats_labels[key] = tk.Label(stats_frame, text="--", 
                                            bg='#16213e', fg='white', font=('Arial', 9))
            self.stats_labels[key].grid(row=i, column=1, sticky='w', padx=5, pady=2)
    
    def _create_system_metrics_panel(self, parent):
        """สร้าง System Metrics Panel"""
        metrics_frame = tk.LabelFrame(parent, text="🔧 System Metrics", 
                                    bg='#16213e', fg='white', font=('Arial', 10, 'bold'))
        metrics_frame.pack(fill='x', padx=5, pady=5)
        
        self.metrics_labels = {}
        for i, (key, label) in enumerate([
            ('uptime', 'Uptime:'),
            ('cpu_usage', 'CPU Usage:'),
            ('memory_usage', 'Memory:'),
            ('last_signal', 'Last Signal:'),
            ('last_order', 'Last Order:')
        ]):
            tk.Label(metrics_frame, text=label, bg='#16213e', fg='#bdc3c7').grid(
                row=i, column=0, sticky='w', padx=5, pady=2)
            
            self.metrics_labels[key] = tk.Label(metrics_frame, text="--", 
                                              bg='#16213e', fg='white', font=('Arial', 9))
            self.metrics_labels[key].grid(row=i, column=1, sticky='w', padx=5, pady=2)
    
    def _create_positions_table(self, parent):
        """สร้าง Positions Table"""
        # Table frame
        table_frame = tk.Frame(parent, bg='#1a1a2e')
        table_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create Treeview
        columns = ('Ticket', 'Type', 'Volume', 'Entry', 'Current', 'P&L', 'Pips', 'Time', 'Status')
        self.positions_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=100, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack table and scrollbar
        self.positions_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Context menu for positions
        self.positions_tree.bind("<Button-3>", self._show_position_context_menu)
    
    def _create_performance_panel(self, parent):
        """สร้าง Performance Panel"""
        perf_frame = tk.Frame(parent, bg='#1a1a2e')
        perf_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Performance metrics
        tk.Label(perf_frame, text="📈 Performance Analytics", 
                bg='#1a1a2e', fg='white', font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Performance data will be displayed here
        self.performance_text = tk.Text(perf_frame, bg='#16213e', fg='white', 
                                      font=('Courier', 10), height=20)
        perf_scrollbar = ttk.Scrollbar(perf_frame, command=self.performance_text.yview)
        self.performance_text.configure(yscrollcommand=perf_scrollbar.set)
        
        self.performance_text.pack(side='left', fill='both', expand=True)
        perf_scrollbar.pack(side='right', fill='y')
    
    def _create_recovery_panel(self, parent):
        """สร้าง Recovery Panel"""
        recovery_frame = tk.Frame(parent, bg='#1a1a2e')
        recovery_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Recovery controls
        tk.Label(recovery_frame, text="🔄 Recovery Management", 
                bg='#1a1a2e', fg='white', font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Recovery status and controls will be added here
        self.recovery_text = tk.Text(recovery_frame, bg='#16213e', fg='white', 
                                   font=('Courier', 10), height=20)
        recovery_scrollbar = ttk.Scrollbar(recovery_frame, command=self.recovery_text.yview)
        self.recovery_text.configure(yscrollcommand=recovery_scrollbar.set)
        
        self.recovery_text.pack(side='left', fill='both', expand=True)
        recovery_scrollbar.pack(side='right', fill='y')
    
    def _create_log_area(self):
        """สร้าง Log Area"""
        log_frame = tk.LabelFrame(self.root, text="📝 System Log", 
                                bg='#16213e', fg='white', font=('Arial', 10, 'bold'))
        log_frame.grid(row=2, column=0, sticky='ew', padx=5, pady=5)
        
        # Log text widget
        self.log_text = tk.Text(log_frame, bg='#0f0f23', fg='#00ff00', 
                              font=('Courier', 9), height=8)
        log_scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
        # Add initial log message
        self._add_log_message("🚀 System initialized - Ready for trading", "INFO")
    
    def _setup_menu(self):
        """ตั้งค่า Menu Bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Data", command=self._export_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_closing)
        
        # Trading Menu
        trading_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Trading", menu=trading_menu)
        trading_menu.add_command(label="Start Trading", command=self._start_trading)
        trading_menu.add_command(label="Stop Trading", command=self._stop_trading)
        trading_menu.add_separator()
        trading_menu.add_command(label="Emergency Stop", command=self._emergency_stop)
        
        # Tools Menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Settings", command=self._show_settings)
        tools_menu.add_command(label="Recovery Manager", command=self._show_recovery_manager)
        
        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Manual", command=self._show_manual)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _setup_status_bar(self):
        """ตั้งค่า Status Bar"""
        status_frame = tk.Frame(self.root, bg='#16213e', height=25)
        status_frame.grid(row=3, column=0, sticky='ew')
        status_frame.grid_propagate(False)
        
        # Status message
        self.status_msg = tk.Label(status_frame, text="Ready", 
                                 bg='#16213e', fg='white', font=('Arial', 9))
        self.status_msg.pack(side='left', padx=10, pady=5)
        
        # Time display
        self.time_label = tk.Label(status_frame, text="", 
                                 bg='#16213e', fg='white', font=('Arial', 9))
        self.time_label.pack(side='right', padx=10, pady=5)
        
        # Start time update
        self._update_time()
    
    def _connect_to_trading_system(self):
        """เชื่อมต่อกับ Trading System"""
        if self.trading_system:
            # Initialize trading system
            success = self.trading_system.initialize_system()
            if success:
                self.system_status = "READY"
                self.system_status_label.config(text="READY", fg='#27ae60')
                self._add_log_message("✅ Trading System initialized successfully", "SUCCESS")
            else:
                self.system_status = "ERROR"
                self.system_status_label.config(text="ERROR", fg='#e74c3c')
                self._add_log_message("❌ Trading System initialization failed", "ERROR")
        
        # Start UI update thread
        self._start_ui_updates()
    
    def _start_ui_updates(self):
        """เริ่ม UI Updates"""
        if not self.update_active:
            self.update_active = True
            self.update_thread = threading.Thread(target=self._ui_update_loop, daemon=True)
            self.update_thread.start()
            self._add_log_message("🔄 Started UI update thread", "INFO")
    
    def _ui_update_loop(self):
        """UI Update Loop"""
        while self.update_active:
            try:
                if self.trading_system:
                    # Get system status
                    status = self.trading_system.get_system_status()
                    
                    # Update GUI in main thread
                    self.root.after(0, lambda: self._update_gui_from_status(status))
                
                time.sleep(2)  # Update every 2 seconds
                
            except Exception as e:
                self.logger.error(f"❌ UI Update Error: {e}")
                time.sleep(5)
    
    def _update_gui_from_status(self, status):
        """อัพเดท GUI จาก System Status"""
        try:
            # Update system status
            if status.get('state'):
                self.system_status_label.config(text=status['state'])
                
                # Set color based on state
                state_colors = {
                    'READY': '#27ae60',
                    'TRADING_ACTIVE': '#2ecc71',
                    'RECOVERY_MODE': '#f39c12',
                    'EMERGENCY_STOP': '#e74c3c'
                }
                color = state_colors.get(status['state'], '#bdc3c7')
                self.system_status_label.config(fg=color)
            
            # Update metrics
            metrics = status.get('metrics', {})
            if metrics:
                self.stats_labels['total_positions'].config(text=str(metrics.get('total_positions', 0)))
                self.stats_labels['active_positions'].config(text=str(metrics.get('active_positions', 0)))
                self.stats_labels['total_profit'].config(text=f"${metrics.get('total_profit', 0):.2f}")
                self.stats_labels['daily_volume'].config(text=f"{metrics.get('daily_volume', 0):.2f} lots")
                
                if metrics.get('uptime'):
                    self.metrics_labels['uptime'].config(text=metrics['uptime'])
            
            # Update positions
            if self.trading_system:
                positions = self.trading_system.get_current_positions()
                self._update_positions_display(positions)
                
        except Exception as e:
            self.logger.error(f"❌ GUI Update Error: {e}")
    
    def _update_positions_display(self, positions):
        """อัพเดท Positions Display"""
        try:
            # Clear existing items
            for item in self.positions_tree.get_children():
                self.positions_tree.delete(item)
            
            # Add positions
            for position in positions:
                values = (
                    getattr(position, 'ticket', '--'),
                    getattr(position, 'type_str', '--'),
                    f"{getattr(position, 'volume', 0):.2f}",
                    f"{getattr(position, 'price_open', 0):.5f}",
                    f"{getattr(position, 'price_current', 0):.5f}",
                    f"{getattr(position, 'profit', 0):.2f}",
                    f"{getattr(position, 'pips', 0):.1f}",
                    getattr(position, 'time_str', '--'),
                    getattr(position, 'status', '--')
                )
                
                item = self.positions_tree.insert('', 'end', values=values)
                
                # Color coding based on profit
                profit = getattr(position, 'profit', 0)
                if profit > 0:
                    self.positions_tree.set(item, 'P&L', f"+{profit:.2f}")
                elif profit < 0:
                    self.positions_tree.set(item, 'P&L', f"{profit:.2f}")
                    
        except Exception as e:
            self.logger.error(f"❌ Positions Display Error: {e}")
    
    # === EVENT HANDLERS ===
    
    def _connect_mt5(self):
        """เชื่อมต่อ MT5"""
        if self.is_connected:
            return
        
        self._add_log_message("🔌 Connecting to MT5...", "INFO")
        
        def connect_thread():
            try:
                # Here you would implement MT5 connection
                # For now, simulate connection
                time.sleep(2)
                
                self.is_connected = True
                self.root.after(0, self._update_connection_success)
                
            except Exception as e:
                self.root.after(0, lambda: self._update_connection_failed(str(e)))
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def _update_connection_success(self):
        """Update after successful MT5 connection"""
        self.status_label.config(text="CONNECTED", fg='#27ae60')
        self.start_trading_btn.config(state='normal')
        self._add_log_message("✅ MT5 connected successfully", "SUCCESS")
    
    def _update_connection_failed(self, error_msg):
        """Update after failed MT5 connection"""
        self.status_label.config(text="FAILED", fg='#e74c3c')
        self._add_log_message(f"❌ MT5 connection failed: {error_msg}", "ERROR")
    
    def _start_trading(self):
        """เริ่มการเทรด"""
        if not self.is_connected:
            messagebox.showwarning("Connection Required", "Please connect to MT5 first")
            return
        
        if self.trading_system:
            success = self.trading_system.start_trading()
            if success:
                self.is_trading = True
                self.start_trading_btn.config(state='disabled')
                self.stop_trading_btn.config(state='normal')
                self._add_log_message("🚀 Trading started!", "SUCCESS")
            else:
                self._add_log_message("❌ Failed to start trading", "ERROR")
    
    def _stop_trading(self):
        """หยุดการเทรด"""
        if self.trading_system:
            success = self.trading_system.stop_trading()
            if success:
                self.is_trading = False
                self.start_trading_btn.config(state='normal')
                self.stop_trading_btn.config(state='disabled')
                self._add_log_message("🛑 Trading stopped", "INFO")
    
    def _emergency_stop(self):
        """หยุดฉุกเฉิน"""
        if messagebox.askyesno("Emergency Stop", "Are you sure you want to trigger emergency stop?"):
            if self.trading_system:
                self.trading_system.emergency_stop()
                self.is_trading = False
                self.start_trading_btn.config(state='disabled')
                self.stop_trading_btn.config(state='disabled')
                self._add_log_message("🚨 EMERGENCY STOP ACTIVATED!", "CRITICAL")
    
    def _show_position_context_menu(self, event):
        """แสดง Context Menu สำหรับ Position"""
        # Context menu implementation
        pass
    
    def _export_data(self):
        """Export ข้อมูล"""
        messagebox.showinfo("Export", "Export feature coming soon!")
    
    def _show_settings(self):
        """แสดงหน้าต่างการตั้งค่า"""
        messagebox.showinfo("Settings", "Settings feature coming soon!")
    
    def _show_recovery_manager(self):
        """แสดง Recovery Manager"""
        messagebox.showinfo("Recovery Manager", "Recovery Manager feature coming soon!")
    
    def _show_manual(self):
        """แสดงคู่มือ"""
        messagebox.showinfo("Manual", "Manual feature coming soon!")
    
    def _show_about(self):
        """แสดงเกี่ยวกับ"""
        about_text = """
🚀 Intelligent Gold Trading System v1.0

Professional XAUUSD Trading Platform
- Live MT5 Integration
- Recovery-Based Trading (แก้ไม้)
- High-Frequency Automated Trading
- Real-time Market Analysis

Built with Python & Core Trading System
        """
        messagebox.showinfo("About", about_text)
    
    def _add_log_message(self, message: str, level: str = "INFO"):
        """เพิ่มข้อความใน Log"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Color mapping
            colors = {
                "INFO": "#00ff00",
                "SUCCESS": "#00ff00",
                "WARNING": "#ffff00",
                "ERROR": "#ff0000",
                "CRITICAL": "#ff0000"
            }
            
            formatted_msg = f"[{timestamp}] {message}\n"
            
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, formatted_msg)
            self.log_text.config(state='disabled')
            self.log_text.see(tk.END)
            
            # Keep log size manageable
            lines = self.log_text.get(1.0, tk.END).split('\n')
            if len(lines) > 500:
                self.log_text.config(state='normal')
                self.log_text.delete(1.0, "50.0")
                self.log_text.config(state='disabled')
                
        except Exception as e:
            self.logger.error(f"❌ Log message error: {e}")
    
    def _update_time(self):
        """อัพเดทเวลา"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self._update_time)
    
    def _on_closing(self):
        """จัดการเมื่อปิดหน้าต่าง"""
        if self.is_trading:
            if not messagebox.askyesno("Confirm Exit", "Trading is active. Exit anyway?"):
                return
        
        # Stop UI updates
        self.update_active = False
        
        # Shutdown trading system
        if self.trading_system:
            self.trading_system.shutdown_system()
        
        self._add_log_message("🛑 Shutting down system...", "INFO")
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """เริ่มต้น GUI Application"""
        self._add_log_message("🖥️ Starting Trading System GUI", "INFO")
        self.root.mainloop()