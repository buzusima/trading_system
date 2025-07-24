#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELLIGENT GOLD TRADING SYSTEM - MAIN WINDOW
============================================
หน้าต่างหลักของระบบเทรด Gold แบบอัตโนมัติ
Professional Trading Interface with Dark Theme

Key Features:
- Real-time trading dashboard
- Live position monitoring
- Recovery system control
- Market intelligence display
- Professional dark theme interface
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import time

class TradingSystemGUI:
    """
    🖥️ Main Trading System GUI - Professional Interface
    
    หน้าต่างหลักสำหรับการควบคุมระบบเทรดดิ้ง
    รวมทุก Component เข้าด้วยกันในรูปแบบ Professional
    """
    
    def __init__(self, settings, logger):
        """
        Initialize Trading System GUI
        
        Args:
            settings: System settings object
            logger: Logger instance
        """
        self.settings = settings
        self.logger = logger
        
        print("🖥️ Initializing Trading System GUI...")
        
        # Core setup
        self.root = tk.Tk()
        self._setup_main_window()
        self._setup_theme()
        
        # System status
        self.is_connected = False
        self.is_trading = False
        self.system_status = "DISCONNECTED"
        
        # Data storage
        self.account_info = {}
        self.positions = []
        self.market_data = {}
        self.performance_stats = {}
        
        # Components - Import MT5 Connector
        try:
            from mt5_integration.mt5_connector import get_mt5_connector
            self.mt5_connector = get_mt5_connector()
            self.logger.info("✅ MT5 Connector initialized")
        except ImportError as e:
            self.logger.warning(f"⚠️ MT5 Connector ไม่พร้อมใช้งาน: {e}")
            self.mt5_connector = None
        
        self.trading_system = None
        
        # Create interface
        self._create_menu_bar()
        self._create_main_layout()
        self._create_status_bar()
        
        # Start update threads
        self._start_update_threads()
        
        self.logger.info("✅ Trading System GUI initialized successfully")
    
    def _setup_main_window(self):
        """Setup main window properties"""
        self.root.title("🚀 Intelligent Gold Trading System - Professional v1.0")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1400 // 2)
        y = (self.root.winfo_screenheight() // 2) - (900 // 2)
        self.root.geometry(f"1400x900+{x}+{y}")
        
        # Window icon (if available)
        try:
            self.root.iconbitmap("assets/trading_icon.ico")
        except:
            pass
    
    def _setup_theme(self):
        """Setup professional dark theme"""
        # Colors
        self.colors = {
            'bg_dark': '#1a1a2e',
            'bg_medium': '#16213e',
            'bg_light': '#0f3460',
            'accent': '#e94560',
            'accent_light': '#f39c12',
            'text_white': '#ffffff',
            'text_gray': '#bdc3c7',
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger': '#e74c3c'
        }
        
        # Configure root
        self.root.configure(bg=self.colors['bg_dark'])
        
        # Configure styles
        style = ttk.Style()
        
        # Frame styles
        style.configure('Dark.TFrame', background=self.colors['bg_dark'])
        style.configure('Medium.TFrame', background=self.colors['bg_medium'])
        style.configure('Light.TFrame', background=self.colors['bg_light'])
        
        # Label styles
        style.configure('Title.TLabel', 
                       background=self.colors['bg_dark'],
                       foreground=self.colors['text_white'],
                       font=('Arial', 16, 'bold'))
        
        style.configure('Header.TLabel',
                       background=self.colors['bg_medium'],
                       foreground=self.colors['text_white'],
                       font=('Arial', 12, 'bold'))
        
        style.configure('Info.TLabel',
                       background=self.colors['bg_dark'],
                       foreground=self.colors['text_gray'],
                       font=('Arial', 10))
        
        # Button styles
        style.configure('Action.TButton',
                       background=self.colors['accent'],
                       foreground=self.colors['text_white'],
                       font=('Arial', 10, 'bold'))
    
    def _create_menu_bar(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root, bg=self.colors['bg_dark'],
                         fg=self.colors['text_white'])
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_medium'],
                           fg=self.colors['text_white'])
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Settings", command=self.load_settings)
        file_menu.add_command(label="Save Settings", command=self.save_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Export Report", command=self.export_report)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.exit_application)
        
        # Trading menu
        trading_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_medium'],
                              fg=self.colors['text_white'])
        menubar.add_cascade(label="Trading", menu=trading_menu)
        trading_menu.add_command(label="Connect MT5", command=self.connect_mt5)
        trading_menu.add_command(label="Disconnect", command=self.disconnect_mt5)
        trading_menu.add_separator()
        trading_menu.add_command(label="Start Trading", command=self.start_trading)
        trading_menu.add_command(label="Stop Trading", command=self.stop_trading)
        trading_menu.add_separator()
        trading_menu.add_command(label="Close All Positions", command=self.close_all_positions)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_medium'],
                            fg=self.colors['text_white'])
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Market Analysis", command=self.show_market_analysis)
        tools_menu.add_command(label="Recovery Settings", command=self.show_recovery_settings)
        tools_menu.add_command(label="Risk Manager", command=self.show_risk_manager)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_medium'],
                           fg=self.colors['text_white'])
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Manual", command=self.show_manual)
        help_menu.add_command(label="About", command=self.show_about)
    
    def _create_main_layout(self):
        """Create main application layout"""
        # Main container
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top panel - Controls and Status
        self._create_top_panel(main_frame)
        
        # Middle panel - Main content
        self._create_middle_panel(main_frame)
        
        # Bottom panel - Logs and messages
        self._create_bottom_panel(main_frame)
    
    def _create_top_panel(self, parent):
        """Create top control panel"""
        top_frame = ttk.Frame(parent, style='Medium.TFrame')
        top_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Connection status
        status_frame = ttk.Frame(top_frame, style='Medium.TFrame')
        status_frame.pack(side=tk.LEFT, padx=10, pady=10)
        
        ttk.Label(status_frame, text="🔌 MT5 Status:", style='Header.TLabel').pack(side=tk.LEFT)
        self.status_label = ttk.Label(status_frame, text="DISCONNECTED", 
                                     style='Info.TLabel')
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Control buttons
        button_frame = ttk.Frame(top_frame, style='Medium.TFrame')
        button_frame.pack(side=tk.RIGHT, padx=10, pady=10)
        
        self.connect_btn = ttk.Button(button_frame, text="Connect MT5",
                                     command=self.connect_mt5, style='Action.TButton')
        self.connect_btn.pack(side=tk.LEFT, padx=2)
        
        self.start_btn = ttk.Button(button_frame, text="Start Trading",
                                   command=self.start_trading, style='Action.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=2)
        
        self.stop_btn = ttk.Button(button_frame, text="Stop Trading",
                                  command=self.stop_trading, style='Action.TButton')
        self.stop_btn.pack(side=tk.LEFT, padx=2)
    
        self.status_btn = ttk.Button(button_frame, text="📊 Status", 
                               command=self.show_system_status, style='Action.TButton')
        self.status_btn.pack(side=tk.LEFT, padx=2)
        
        self.test_signal_btn = ttk.Button(button_frame, text="🧪 Test Signal", 
                                        command=self.create_test_signal, style='Action.TButton')
        self.test_signal_btn.pack(side=tk.LEFT, padx=2)

    def show_system_status(self):
        """แสดงสถานะระบบ"""
        try:
            status_msg = "📊 SYSTEM STATUS:\n\n"
            
            # Signal Generator Status
            if hasattr(self, 'signal_generator') and self.signal_generator:
                try:
                    stats = self.signal_generator.get_signal_statistics()
                    status_msg += f"🎯 Signal Generator: ACTIVE\n"
                    status_msg += f"   - Signals Today: {stats.get('signals_generated_today', 0)}\n"
                    status_msg += f"   - Active Signals: {stats.get('active_signals_count', 0)}\n"
                    status_msg += f"   - Last Signal: {stats.get('last_signal_time', 'Never')}\n\n"
                except Exception as e:
                    status_msg += f"🎯 Signal Generator: ERROR ({e})\n\n"
            else:
                status_msg += "🎯 Signal Generator: NOT READY\n\n"
            
            # Recovery Engine Status
            if hasattr(self, 'recovery_engine') and self.recovery_engine:
                try:
                    recovery_stats = self.recovery_engine.get_recovery_summary()
                    status_msg += f"🔄 Recovery Engine: ACTIVE\n"
                    status_msg += f"   - Total Attempts: {recovery_stats.get('total_attempted', 0)}\n"
                    status_msg += f"   - Success Rate: {recovery_stats.get('success_rate', 0):.1f}%\n"
                    status_msg += f"   - Active Recoveries: {recovery_stats.get('active_recoveries', 0)}\n\n"
                except Exception as e:
                    status_msg += f"🔄 Recovery Engine: ERROR ({e})\n\n"
            else:
                status_msg += "🔄 Recovery Engine: NOT READY\n\n"
            
            # MT5 Connection
            try:
                import MetaTrader5 as mt5
                positions = mt5.positions_get()
                status_msg += f"📈 MT5 Positions: {len(positions) if positions else 0}\n"
                
                account_info = mt5.account_info()
                if account_info:
                    status_msg += f"💰 Balance: ${account_info.balance:,.2f}\n"
                    status_msg += f"📊 Equity: ${account_info.equity:,.2f}\n"
            except Exception as e:
                status_msg += f"📈 MT5: Connection Error ({e})\n"
            
            messagebox.showinfo("System Status", status_msg)
            
        except Exception as e:
            self.log_message(f"❌ Status Check Error: {e}", "ERROR")
            messagebox.showerror("Error", f"Status check failed: {e}")

    def create_test_signal(self):
        """สร้าง Test Signal เพื่อทดสอบระบบ"""
        try:
            if hasattr(self, 'signal_generator') and self.signal_generator:
                from adaptive_entries.signal_generator import EntrySignal, SignalDirection, SignalStrength
                from config.trading_params import EntryStrategy
                from config.settings import MarketSession
                from datetime import datetime
                
                # สร้าง Test Signal
                test_signal = EntrySignal(
                    signal_id=f"TEST_{datetime.now().strftime('%H%M%S')}",
                    timestamp=datetime.now(),
                    source_engine=EntryStrategy.TREND_FOLLOWING,
                    direction=SignalDirection.BUY,
                    strength=SignalStrength.STRONG,
                    confidence=0.8,
                    current_price=2650.0,
                    suggested_volume=0.01,
                    signal_quality_score=80.0,
                    session=MarketSession.LONDON
                )
                
                # เพิ่มเข้าระบบ
                success = self.signal_generator.signal_aggregator.add_signal(test_signal)
                
                if success:
                    self.log_message("🧪 สร้าง Test Signal สำเร็จ", "SUCCESS")
                else:
                    self.log_message("❌ ไม่สามารถสร้าง Test Signal ได้", "ERROR")
            else:
                self.log_message("⚠️ Signal Generator ยังไม่พร้อม", "WARNING")
                
        except Exception as e:
            self.log_message(f"❌ Test Signal Error: {e}", "ERROR")

    def _create_middle_panel(self, parent):
        """Create middle content panel"""
        middle_frame = ttk.Frame(parent, style='Dark.TFrame')
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(middle_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Dashboard tab
        self._create_dashboard_tab()
        
        # Positions tab
        self._create_positions_tab()
        
        # Recovery tab
        self._create_recovery_tab()
        
        # Analytics tab
        self._create_analytics_tab()
    
    def _create_dashboard_tab(self):
        """Create main dashboard tab"""
        dashboard_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(dashboard_frame, text="📊 Dashboard")
        
        # Account info
        account_frame = ttk.LabelFrame(dashboard_frame, text="Account Information")
        account_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.account_labels = {}
        account_info = [
            ("Balance:", "balance"),
            ("Equity:", "equity"),
            ("Margin:", "margin"),
            ("Free Margin:", "margin_free"),
            ("Profit:", "profit")
        ]
        
        for i, (label, key) in enumerate(account_info):
            row_frame = ttk.Frame(account_frame)
            row_frame.pack(fill=tk.X, padx=5, pady=2)
            
            ttk.Label(row_frame, text=label, width=15).pack(side=tk.LEFT)
            self.account_labels[key] = ttk.Label(row_frame, text="0.00")
            self.account_labels[key].pack(side=tk.LEFT)
        
        # Market data
        market_frame = ttk.LabelFrame(dashboard_frame, text="XAUUSD Market Data")
        market_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.market_labels = {}
        market_info = [
            ("Bid:", "bid"),
            ("Ask:", "ask"),
            ("Spread:", "spread"),
            ("Last Update:", "time")
        ]
        
        for i, (label, key) in enumerate(market_info):
            row_frame = ttk.Frame(market_frame)
            row_frame.pack(fill=tk.X, padx=5, pady=2)
            
            ttk.Label(row_frame, text=label, width=15).pack(side=tk.LEFT)
            self.market_labels[key] = ttk.Label(row_frame, text="N/A")
            self.market_labels[key].pack(side=tk.LEFT)
    
    def _create_positions_tab(self):
        """Create positions monitoring tab"""
        positions_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(positions_frame, text="📈 Positions")
        
        # Positions table
        self.positions_tree = ttk.Treeview(positions_frame, 
                                         columns=('Ticket', 'Type', 'Volume', 'Price', 'Current', 'Profit'),
                                         show='headings')
        
        # Define headings
        self.positions_tree.heading('Ticket', text='Ticket')
        self.positions_tree.heading('Type', text='Type')
        self.positions_tree.heading('Volume', text='Volume')
        self.positions_tree.heading('Price', text='Open Price')
        self.positions_tree.heading('Current', text='Current Price')
        self.positions_tree.heading('Profit', text='Profit')
        
        # Configure column widths
        self.positions_tree.column('Ticket', width=100)
        self.positions_tree.column('Type', width=60)
        self.positions_tree.column('Volume', width=80)
        self.positions_tree.column('Price', width=100)
        self.positions_tree.column('Current', width=100)
        self.positions_tree.column('Profit', width=100)
        
        self.positions_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar for positions table
        positions_scroll = ttk.Scrollbar(positions_frame, orient=tk.VERTICAL, 
                                       command=self.positions_tree.yview)
        positions_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.positions_tree.configure(yscrollcommand=positions_scroll.set)
    
    def _create_recovery_tab(self):
        """Create recovery system tab"""
        recovery_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(recovery_frame, text="🔄 Recovery")
        
        # Recovery status
        status_frame = ttk.LabelFrame(recovery_frame, text="Recovery Status")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(status_frame, text="Recovery System: ").pack(side=tk.LEFT, padx=5)
        self.recovery_status = ttk.Label(status_frame, text="STANDBY")
        self.recovery_status.pack(side=tk.LEFT)
        
        # Recovery settings
        settings_frame = ttk.LabelFrame(recovery_frame, text="Recovery Settings")
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Strategy:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.recovery_strategy = ttk.Combobox(settings_frame, 
                                            values=["Smart Martingale", "Grid Trading", "Hedging"])
        self.recovery_strategy.grid(row=0, column=1, padx=5, pady=2)
        self.recovery_strategy.set("Smart Martingale")
        
        ttk.Label(settings_frame, text="Max Recovery Level:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.max_recovery = ttk.Entry(settings_frame)
        self.max_recovery.grid(row=1, column=1, padx=5, pady=2)
        self.max_recovery.insert(0, "5")
    
    def _create_analytics_tab(self):
        """Create analytics tab"""
        analytics_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(analytics_frame, text="📈 Analytics")
        
        # Performance summary
        perf_frame = ttk.LabelFrame(analytics_frame, text="Performance Summary")
        perf_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.perf_labels = {}
        perf_metrics = [
            ("Total Trades:", "total_trades"),
            ("Win Rate:", "win_rate"),
            ("Total Profit:", "total_profit"),
            ("Recovery Success:", "recovery_success")
        ]
        
        for i, (label, key) in enumerate(perf_metrics):
            row_frame = ttk.Frame(perf_frame)
            row_frame.pack(fill=tk.X, padx=5, pady=2)
            
            ttk.Label(row_frame, text=label, width=20).pack(side=tk.LEFT)
            self.perf_labels[key] = ttk.Label(row_frame, text="0")
            self.perf_labels[key].pack(side=tk.LEFT)
    
    def _create_bottom_panel(self, parent):
        """Create bottom panel for logs"""
        bottom_frame = ttk.Frame(parent, style='Medium.TFrame')
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Log area
        log_frame = ttk.LabelFrame(bottom_frame, text="System Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(log_frame, height=8, bg=self.colors['bg_dark'],
                               fg=self.colors['text_gray'], font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Log scrollbar
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=log_scroll.set)
    
    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = ttk.Frame(self.root, style='Medium.TFrame')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Status labels
        self.status_time = ttk.Label(self.status_bar, text="", style='Info.TLabel')
        self.status_time.pack(side=tk.RIGHT, padx=5)
        
        self.status_msg = ttk.Label(self.status_bar, text="Ready", style='Info.TLabel')
        self.status_msg.pack(side=tk.LEFT, padx=5)
    
    def _start_update_threads(self):
        """Start background update threads"""
        self.update_active = True
        
        # Time update thread
        time_thread = threading.Thread(target=self._update_time, daemon=True)
        time_thread.start()
        
        # Data update thread
        data_thread = threading.Thread(target=self._update_data, daemon=True)
        data_thread.start()
    
    def _update_time(self):
        """Update time display"""
        while self.update_active:
            try:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.status_time.config(text=current_time)
                time.sleep(1)
            except:
                break
    
    def _update_data(self):
        """Update trading data"""
        while self.update_active:
            try:
                if self.is_connected:
                    self._refresh_account_info()
                    self._refresh_positions()
                    self._refresh_market_data()
                time.sleep(2)
            except:
                break
    
    def _refresh_account_info(self):
        """Refresh account information"""
        if not self.is_connected or not self.mt5_connector:
            return
        
        try:
            # ดึงข้อมูลบัญชีจาก MT5
            account_info = self.mt5_connector.get_account_info(refresh=True)
            
            if account_info:
                # อัพเดทข้อมูลในหน้า GUI
                if hasattr(self, 'account_labels'):
                    self.account_labels['balance'].config(text=f"${account_info.balance:,.2f}")
                    self.account_labels['equity'].config(text=f"${account_info.equity:,.2f}")
                    self.account_labels['margin'].config(text=f"${account_info.margin:,.2f}")
                    self.account_labels['margin_free'].config(text=f"${account_info.margin_free:,.2f}")
                    self.account_labels['profit'].config(text=f"${account_info.profit:,.2f}")
                
                # เก็บข้อมูลไว้ใน instance
                self.account_info = {
                    'balance': account_info.balance,
                    'equity': account_info.equity,
                    'margin': account_info.margin,
                    'margin_free': account_info.margin_free,
                    'profit': account_info.profit,
                    'currency': account_info.currency,
                    'leverage': account_info.leverage
                }
                
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถดึงข้อมูลบัญชีได้: {e}")
            self.log_message(f"Error updating account info: {e}", "ERROR")
    
    def _refresh_positions(self):
        """Refresh positions data"""
        if not self.is_connected or not self.mt5_connector:
            return
        
        try:
            import MetaTrader5 as mt5
            
            # ดึงข้อมูล Positions จาก MT5
            positions = mt5.positions_get(symbol="XAUUSD")
            
            if positions:
                # Clear existing items
                if hasattr(self, 'positions_tree'):
                    for item in self.positions_tree.get_children():
                        self.positions_tree.delete(item)
                    
                    # Add new positions
                    for pos in positions:
                        pos_type = "BUY" if pos.type == 0 else "SELL"
                        
                        self.positions_tree.insert('', 'end', values=(
                            pos.ticket,
                            pos_type,
                            f"{pos.volume:.2f}",
                            f"{pos.price_open:.2f}",
                            f"{pos.price_current:.2f}",
                            f"${pos.profit:.2f}"
                        ))
                
                # เก็บข้อมูลไว้ใน instance
                self.positions = positions
                
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถดึงข้อมูล Positions ได้: {e}")
            self.log_message(f"Error updating positions: {e}", "ERROR")
    
    def _refresh_market_data(self):
        """Refresh market data"""
        if not self.is_connected or not self.mt5_connector:
            return
        
        try:
            import MetaTrader5 as mt5
            
            # ดึงข้อมูลราคา XAUUSD
            tick = mt5.symbol_info_tick("XAUUSD.v")
            
            if tick:
                bid = tick.bid
                ask = tick.ask
                spread = (ask - bid) * 10000  # คำนวณ spread ใน points
                last_update = datetime.fromtimestamp(tick.time).strftime("%H:%M:%S")
                
                # อัพเดทใน GUI
                if hasattr(self, 'market_labels'):
                    self.market_labels['bid'].config(text=f"{bid:.2f}")
                    self.market_labels['ask'].config(text=f"{ask:.2f}")
                    self.market_labels['spread'].config(text=f"{spread:.1f} pts")
                    self.market_labels['time'].config(text=last_update)
                
                # เก็บข้อมูลไว้ใน instance
                self.market_data = {
                    'bid': bid,
                    'ask': ask,
                    'spread': spread,
                    'time': tick.time,
                    'last_update': last_update
                }
                
        except Exception as e:
            self.logger.error(f"❌ ไม่สามารถดึงข้อมูลตลาดได้: {e}")
            self.log_message(f"Error updating market data: {e}", "ERROR")
    
    def log_message(self, message: str, level: str = "INFO"):
        """Log message to the log area"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        
        try:
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
        except:
            pass
    
    # Menu command methods
    def load_settings(self):
        """Load settings from file"""
        self.log_message("Loading settings...", "INFO")
    
    def save_settings(self):
        """Save current settings"""
        self.log_message("Saving settings...", "INFO")
    
    def export_report(self):
        """Export trading report"""
        self.log_message("Exporting report...", "INFO")
    
    # Trading command methods
    def connect_mt5(self):
        """Connect to MT5"""
        if not self.mt5_connector:
            messagebox.showerror("Error", "MT5 Connector ไม่พร้อมใช้งาน!")
            return
        
        self.log_message("🔌 กำลังเชื่อมต่อ MT5...", "INFO")
        
        # ใช้ thread เพื่อไม่ให้ GUI หยุดทำงาน
        def connect_thread():
            try:
                # เชื่อมต่อ MT5
                success = self.mt5_connector.connect()
                
                if success:
                    self.is_connected = True
                    self.system_status = "CONNECTED"
                    
                    # อัพเดท GUI ใน main thread
                    self.root.after(0, self._update_connection_success)
                    
                else:
                    # อัพเดท GUI ใน main thread
                    self.root.after(0, self._update_connection_failed)
                    
            except Exception as e:
                self.logger.error(f"❌ การเชื่อมต่อ MT5 ล้มเหลว: {e}")
                self.root.after(0, lambda: self._update_connection_failed(str(e)))
        
        # เริ่ม thread
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def _update_connection_success(self):
        """Update GUI after successful connection"""
        self.status_label.config(text="CONNECTED")
        self.status_msg.config(text="เชื่อมต่อ MT5 สำเร็จ")
        self.log_message("✅ เชื่อมต่อ MT5 สำเร็จ!", "SUCCESS")
        
        # เริ่มดึงข้อมูลทันที
        self._refresh_account_info()
        self._refresh_market_data()
        self._refresh_positions()
        
        # อัพเดทสถานะ account info
        if self.mt5_connector and self.mt5_connector.account_info:
            account = self.mt5_connector.account_info
            self.log_message(f"📊 Account: {account.login} | Balance: ${account.balance:,.2f} {account.currency}", "INFO")
            self.log_message(f"🏛️ Server: {account.server} | Leverage: 1:{account.leverage}", "INFO")
    
    def _update_connection_failed(self, error_msg=None):
        """Update GUI after failed connection"""
        self.is_connected = False
        self.system_status = "DISCONNECTED"
        self.status_label.config(text="DISCONNECTED")
        self.status_msg.config(text="การเชื่อมต่อ MT5 ล้มเหลว")
        
        if error_msg:
            self.log_message(f"❌ การเชื่อมต่อ MT5 ล้มเหลว: {error_msg}", "ERROR")
        else:
            self.log_message("❌ การเชื่อมต่อ MT5 ล้มเหลว", "ERROR")
        
        messagebox.showerror("Connection Error", 
                           f"ไม่สามารถเชื่อมต่อ MT5 ได้\n{error_msg if error_msg else 'กรุณาตรวจสอบการตั้งค่า'}")
    
    def disconnect_mt5(self):
        """Disconnect from MT5"""
        if not self.mt5_connector:
            return
        
        self.log_message("🔌 กำลังตัดการเชื่อมต่อ MT5...", "INFO")
        
        try:
            # หยุดการเทรดก่อน
            if self.is_trading:
                self.stop_trading()
            
            # ตัดการเชื่อมต่อ
            success = self.mt5_connector.disconnect()
            
            if success:
                self.is_connected = False
                self.system_status = "DISCONNECTED"
                self.status_label.config(text="DISCONNECTED")
                self.status_msg.config(text="ตัดการเชื่อมต่อ MT5 แล้ว")
                self.log_message("✅ ตัดการเชื่อมต่อ MT5 สำเร็จ", "INFO")
                
                # เคลียร์ข้อมูล
                self.account_info = {}
                self.positions = []
                self.market_data = {}
                
            else:
                self.log_message("❌ ไม่สามารถตัดการเชื่อมต่อ MT5 ได้", "ERROR")
                
        except Exception as e:
            self.logger.error(f"❌ Error disconnecting MT5: {e}")
            self.log_message(f"Error disconnecting: {e}", "ERROR")
    
    def start_trading(self):
        """Start trading system - เชื่อมต่อระบบเทรดจริง (แก้ไขแล้ว)"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to MT5 first!")
            return
        
        def start_trading_thread():
            """Run trading startup in separate thread"""
            try:
                self.root.after(0, lambda: self.log_message("🚀 กำลังเริ่มต้นระบบเทรดอัตโนมัติ...", "INFO"))
                
                # 1. เริ่มต้น Market Analyzer
                try:
                    from market_intelligence.market_analyzer import MarketAnalyzer
                    self.market_analyzer = MarketAnalyzer()
                    self.market_analyzer.start_analysis()  # SYNC method
                    self.root.after(0, lambda: self.log_message("✅ เริ่มต้น Market Analyzer สำเร็จ", "SUCCESS"))
                    time.sleep(1)
                except Exception as e:
                    error_msg = str(e)  # เก็บ error message ไว้ในตัวแปร
                    self.root.after(0, lambda msg=error_msg: self.log_message(f"⚠️ Market Analyzer: {msg}", "WARNING"))
                
                # 2. เริ่มต้น Signal Generator  
                try:
                    from adaptive_entries.signal_generator import SignalGenerator
                    self.signal_generator = SignalGenerator()
                    self.signal_generator.start_signal_generation()  # SYNC method
                    self.root.after(0, lambda: self.log_message("✅ เริ่มต้น Signal Generator สำเร็จ", "SUCCESS"))
                    time.sleep(1)
                except Exception as e:
                    error_msg = str(e)
                    self.root.after(0, lambda msg=error_msg: self.log_message(f"⚠️ Signal Generator: {msg}", "WARNING"))
                
                # 3. เริ่มต้น Recovery Engine
                try:
                    from intelligent_recovery.recovery_engine import RecoveryEngine
                    self.recovery_engine = RecoveryEngine()
                    self.recovery_engine.start_recovery_engine()  # SYNC method
                    self.root.after(0, lambda: self.log_message("✅ เริ่มต้น Recovery Engine สำเร็จ", "SUCCESS"))
                    time.sleep(1)
                except Exception as e:
                    error_msg = str(e)
                    self.root.after(0, lambda msg=error_msg: self.log_message(f"⚠️ Recovery Engine: {msg}", "WARNING"))
                
                # 4. เริ่มต้น Order Executor
                try:
                    from mt5_integration.order_executor import OrderExecutor
                    self.order_executor = OrderExecutor()
                    self.root.after(0, lambda: self.log_message("✅ เริ่มต้น Order Executor สำเร็จ", "SUCCESS"))
                    time.sleep(1)
                except Exception as e:
                    error_msg = str(e)
                    self.root.after(0, lambda msg=error_msg: self.log_message(f"⚠️ Order Executor: {msg}", "WARNING"))
                
                # 5. เริ่มระบบเทรดจริง
                try:
                    self._start_actual_trading()
                    self.root.after(0, lambda: self.log_message("🎯 เริ่มการเทรดแบบอัตโนมัติ", "SUCCESS"))
                except Exception as e:
                    error_msg = str(e)
                    self.root.after(0, lambda msg=error_msg: self.log_message(f"❌ ไม่สามารถเริ่มการเทรดได้: {msg}", "ERROR"))
                
                # อัพเดทสถานะใน main thread
                self.root.after(0, self._update_trading_started_success)
                
            except Exception as e:
                error_msg = str(e)  # เก็บ error message
                self.logger.error(f"❌ ไม่สามารถเริ่มระบบเทรดได้: {error_msg}")
                # อัพเดทสถานะใน main thread - แก้ไข lambda scope error
                self.root.after(0, lambda msg=error_msg: self._update_trading_started_error(msg))
        
        # เริ่ม thread
        import threading
        threading.Thread(target=start_trading_thread, daemon=True).start()

    def _update_trading_started_success(self):
        """Update GUI after successful trading start"""
        self.is_trading = True
        # แก้ไขจาก trading_status_label เป็น status_label
        self.status_label.config(text="TRADING ACTIVE")
        self.status_msg.config(text="ระบบเทรดอัตโนมัติทำงานอยู่")
        self.log_message("✅ ระบบเทรดอัตโนมัติเริ่มทำงานแล้ว!", "SUCCESS")
        self.log_message("🎯 ระบบกำลังมองหา Entry Signals...", "INFO")

    def _update_trading_started_error(self, error_msg):
        """Update GUI after failed trading start"""
        self.is_trading = False
        self.status_label.config(text="DISCONNECTED")
        self.status_msg.config(text="ไม่สามารถเริ่มระบบเทรดได้")
        self.log_message(f"❌ ไม่สามารถเริ่มระบบเทรดได้: {error_msg}", "ERROR")
        messagebox.showerror("Error", f"Trading system failed to start: {error_msg}")

    def stop_trading(self):
        """Stop trading system - แก้ไขให้หยุดจริง"""
        try:
            self.log_message("🛑 กำลังหยุดระบบเทรดอัตโนมัติ...", "INFO")
            
            # หยุด Trading Loop
            if hasattr(self, 'trading_loop_active'):
                self.trading_loop_active = False
            
            # หยุด Signal Generator
            if hasattr(self, 'signal_generator') and self.signal_generator:
                self.signal_generator.stop_signal_generation()
                self.log_message("✅ หยุด Signal Generator", "SUCCESS")
            
            # หยุด Market Analyzer
            if hasattr(self, 'market_analyzer') and self.market_analyzer:
                self.market_analyzer.stop_analysis()
                self.log_message("✅ หยุด Market Analyzer", "SUCCESS")
            
            # หยุด Recovery Engine
            if hasattr(self, 'recovery_engine') and self.recovery_engine:
                self.recovery_engine.stop_recovery_engine()
                self.log_message("✅ หยุด Recovery Engine", "SUCCESS")
            
            # อัพเดทสถานะ
            self.is_trading = False
            self.status_label.config(text="CONNECTED") 
            self.status_msg.config(text="หยุดระบบเทรดแล้ว")
            self.log_message("✅ หยุดระบบเทรดอัตโนมัติสำเร็จ", "SUCCESS")
            
        except Exception as e:
            self.logger.error(f"❌ Error stopping trading: {e}")
            self.log_message(f"Error stopping trading: {e}", "ERROR")

    def _start_actual_trading(self):
        """เริ่มการเทรดจริง"""
        if not hasattr(self, 'trading_loop_active'):
            self.trading_loop_active = False
        
        if self.trading_loop_active:
            return
        
        self.trading_loop_active = True
        
        def trading_loop():
            """Main Trading Loop"""
            self.root.after(0, lambda: self.log_message("🔄 เริ่ม Trading Loop หลัก", "INFO"))
            
            while self.trading_loop_active and self.is_trading:
                try:
                    # 1. ดึง Signal จาก Signal Generator
                    if hasattr(self, 'signal_generator') and self.signal_generator:
                        signal = self.signal_generator.get_next_entry_signal()
                        
                        if signal:
                            self.root.after(0, lambda s=signal: self.log_message(
                                f"📨 ได้รับ Signal: {s.direction.value} | "
                                f"Price: {s.current_price:.2f} | "
                                f"Confidence: {s.confidence:.2f}", "INFO"))
                            
                            # 2. ส่งออร์เดอร์
                            if hasattr(self, 'order_executor') and self.order_executor:
                                self._execute_trading_signal(signal)
                    
                    # 3. ตรวจสอบ Positions ที่ต้อง Recovery
                    self._check_positions_for_recovery()
                    
                    # รอก่อนรอบถัดไป
                    time.sleep(10)  # ตรวจสอบทุก 10 วินาที
                    
                except Exception as e:
                    error_msg = str(e)
                    self.root.after(0, lambda msg=error_msg: self.log_message(f"❌ Trading Loop Error: {msg}", "ERROR"))
                    time.sleep(30)  # รอนานขึ้นเมื่อมี error
        
        # เริ่ม Trading Loop ใน thread แยก
        import threading
        threading.Thread(target=trading_loop, daemon=True).start()

    def _execute_trading_signal(self, signal):
        """Execute Trading Signal"""
        try:
            from mt5_integration.order_executor import OrderType
            
            # กำหนด Order Type
            order_type = OrderType.BUY if signal.direction.value == "BUY" else OrderType.SELL
            
            # ส่งออร์เดอร์
            result = self.order_executor.send_market_order(
                symbol="XAUUSD",
                order_type=order_type,
                volume=signal.suggested_volume,
                comment=f"Signal_{signal.signal_id}",
                strategy_name=signal.source_engine.value
            )
            
            if result.status.value == "EXECUTED":
                self.root.after(0, lambda: self.log_message(
                    f"✅ ส่งออร์เดอร์สำเร็จ: {result.order_id} | "
                    f"Price: {result.price_executed:.2f} | "
                    f"Volume: {result.volume_executed:.2f}", "SUCCESS"))
            else:
                self.root.after(0, lambda: self.log_message(
                    f"❌ ส่งออร์เดอร์ไม่สำเร็จ: {result.error_description}", "ERROR"))
                
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self.log_message(f"❌ Execute Signal Error: {msg}", "ERROR"))

    def _check_positions_for_recovery(self):
        """ตรวจสอบ Positions ที่ต้อง Recovery"""
        try:
            if not hasattr(self, 'recovery_engine') or not self.recovery_engine:
                return
            
            # ดึง Positions จาก MT5
            import MetaTrader5 as mt5
            positions = mt5.positions_get(symbol="XAUUSD")
            
            if positions:
                for pos in positions:
                    # ตรวจสอบ P&L
                    if pos.profit < -20.0:  # ขาดทุนเกิน $20
                        from intelligent_recovery.recovery_engine import RecoveryTrigger, RecoveryPriority
                        
                        # เริ่ม Recovery
                        success = self.recovery_engine.trigger_recovery(
                            position_id=str(pos.ticket),
                            trigger_type=RecoveryTrigger.LOSING_POSITION,
                            priority=RecoveryPriority.HIGH if pos.profit < -50.0 else RecoveryPriority.MEDIUM
                        )
                        
                        if success:
                            ticket = pos.ticket
                            self.root.after(0, lambda t=ticket: self.log_message(
                                f"🔄 เริ่ม Recovery สำหรับ Position: {t}", "INFO"))
                            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self.log_message(f"❌ Check Recovery Error: {msg}", "ERROR"))

    def close_all_positions(self):
        """Close all open positions"""
        if not messagebox.askyesno("Confirm", "Close all positions?"):
            return
        
        self.log_message("Closing all positions...", "WARNING")
    
    # Tools command methods
    def show_market_analysis(self):
        """Show market analysis window"""
        messagebox.showinfo("Market Analysis", "Market Analysis feature coming soon!")
    
    def show_recovery_settings(self):
        """Show recovery settings window"""
        messagebox.showinfo("Recovery Settings", "Recovery Settings feature coming soon!")
    
    def show_risk_manager(self):
        """Show risk manager window"""
        messagebox.showinfo("Risk Manager", "Risk Manager feature coming soon!")
    
    # Help command methods
    def show_manual(self):
        """Show user manual"""
        messagebox.showinfo("User Manual", "User Manual feature coming soon!")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """
🚀 Intelligent Gold Trading System v1.0

Professional XAUUSD Trading Platform
- Live MT5 Integration
- Recovery-Based Trading (แก้ไม้)
- High-Frequency Automated Trading
- Real-time Market Analysis

Built with Python & MT5 API
        """
        messagebox.showinfo("About", about_text)
    
    def exit_application(self):
        """Exit application safely"""
        if self.is_trading:
            if not messagebox.askyesno("Confirm Exit", 
                                     "Trading is active. Exit anyway?"):
                return
        
        self.log_message("Shutting down system...", "INFO")
        self.update_active = False
        self.root.quit()
    
    def run(self):
        """Start the GUI application"""
        self.log_message("🚀 Trading System GUI Started", "INFO")
        self.log_message("Ready for MT5 connection and live trading", "INFO")
        self.root.mainloop()


def main():
    """Main entry point for GUI testing"""
    # For testing purposes
    class MockSettings:
        trading_mode = "LIVE"
    
    class MockLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
    
    settings = MockSettings()
    logger = MockLogger()
    
    app = TradingSystemGUI(settings, logger)
    app.run()


if __name__ == "__main__":
    main()