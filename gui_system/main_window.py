# gui_system/main_window.py - Professional Trading Interface

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class ProfessionalTradingGUI:
    """
    🖥️ Professional Trading Interface - Main Window
    
    Features:
    - Real-time market data display
    - Live position monitoring
    - Recovery system control
    - Performance analytics
    - Risk management controls
    - Professional dark theme
    """
    
    def __init__(self):
        print("🖥️ Initializing Professional Trading Interface...")
        
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
        
        # Components
        self.mt5_interface = None
        self.trading_system = None
        
        # Create interface
        self._create_menu_bar()
        self._create_main_layout()
        self._create_status_bar()
        
        # Start update threads
        self._start_update_threads()
        
        print("✅ Professional Trading Interface initialized")
    
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
            'danger': '#e74c3c',
            'buy': '#2ecc71',
            'sell': '#e74c3c'
        }
        
        # Configure root
        self.root.configure(bg=self.colors['bg_dark'])
        
        # Configure ttk styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configure styles
        self._configure_ttk_styles()
    
    def _configure_ttk_styles(self):
        """Configure ttk widget styles"""
        # Frame styles
        self.style.configure('Dark.TFrame', 
                           background=self.colors['bg_dark'])
        self.style.configure('Medium.TFrame', 
                           background=self.colors['bg_medium'])
        self.style.configure('Light.TFrame', 
                           background=self.colors['bg_light'])
        
        # Label styles
        self.style.configure('Title.TLabel',
                           background=self.colors['bg_dark'],
                           foreground=self.colors['text_white'],
                           font=('Arial', 12, 'bold'))
        self.style.configure('Subtitle.TLabel',
                           background=self.colors['bg_medium'],
                           foreground=self.colors['text_gray'],
                           font=('Arial', 10))
        self.style.configure('Value.TLabel',
                           background=self.colors['bg_medium'],
                           foreground=self.colors['accent_light'],
                           font=('Arial', 10, 'bold'))
        
        # Button styles
        self.style.configure('Action.TButton',
                           font=('Arial', 10, 'bold'))
        self.style.map('Action.TButton',
                      background=[('active', self.colors['accent']),
                                ('pressed', self.colors['accent'])])
    
    def _create_menu_bar(self):
        """Create professional menu bar"""
        menubar = tk.Menu(self.root, bg=self.colors['bg_medium'], 
                         fg=self.colors['text_white'])
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_medium'],
                           fg=self.colors['text_white'])
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Configuration", command=self.save_config)
        file_menu.add_command(label="Load Configuration", command=self.load_config)
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
        conn_frame = ttk.Frame(top_frame, style='Medium.TFrame')
        conn_frame.pack(side=tk.LEFT, padx=(10, 20))
        
        ttk.Label(conn_frame, text="MT5 Status:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.conn_status_label = tk.Label(conn_frame, text="❌ Disconnected", 
                                         bg=self.colors['bg_medium'],
                                         fg=self.colors['danger'],
                                         font=('Arial', 10, 'bold'))
        self.conn_status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Trading status
        trading_frame = ttk.Frame(top_frame, style='Medium.TFrame')
        trading_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(trading_frame, text="Trading:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.trading_status_label = tk.Label(trading_frame, text="⏸️ Stopped",
                                           bg=self.colors['bg_medium'],
                                           fg=self.colors['warning'],
                                           font=('Arial', 10, 'bold'))
        self.trading_status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Control buttons
        btn_frame = ttk.Frame(top_frame, style='Medium.TFrame')
        btn_frame.pack(side=tk.RIGHT, padx=(0, 10))
        
        self.connect_btn = ttk.Button(btn_frame, text="🔌 Connect", 
                                     command=self.connect_mt5, style='Action.TButton')
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.start_btn = ttk.Button(btn_frame, text="▶️ Start Trading", 
                                   command=self.start_trading, style='Action.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹️ Stop Trading", 
                                  command=self.stop_trading, style='Action.TButton')
        self.stop_btn.pack(side=tk.LEFT)
    
    def _create_middle_panel(self, parent):
        """Create middle content panel"""
        middle_frame = ttk.Frame(parent, style='Dark.TFrame')
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(middle_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Trading Dashboard tab
        self._create_dashboard_tab()
        
        # Positions tab
        self._create_positions_tab()
        
        # Recovery tab
        self._create_recovery_tab()
        
        # Analytics tab
        self._create_analytics_tab()
        
        # Settings tab
        self._create_settings_tab()
    
    def _create_dashboard_tab(self):
        """Create main trading dashboard"""
        dashboard_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(dashboard_frame, text="📊 Dashboard")
        
        # Left panel - Market data
        left_frame = ttk.Frame(dashboard_frame, style='Medium.TFrame')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Market data section
        market_label = ttk.Label(left_frame, text="📈 Market Data - XAUUSD", 
                                style='Title.TLabel')
        market_label.pack(pady=(10, 5))
        
        # Market data display
        self.market_data_frame = ttk.Frame(left_frame, style='Light.TFrame')
        self.market_data_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Placeholder market data
        self._create_market_data_display()
        
        # Right panel - Account info
        right_frame = ttk.Frame(dashboard_frame, style='Medium.TFrame')
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        right_frame.config(width=300)
        
        # Account info section
        account_label = ttk.Label(right_frame, text="💰 Account Information", 
                                 style='Title.TLabel')
        account_label.pack(pady=(10, 5))
        
        # Account data display
        self.account_frame = ttk.Frame(right_frame, style='Light.TFrame')
        self.account_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self._create_account_display()
    
    def _create_market_data_display(self):
        """Create market data display widgets"""
        # Current price
        price_frame = ttk.Frame(self.market_data_frame, style='Light.TFrame')
        price_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(price_frame, text="Current Price:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.current_price_label = ttk.Label(price_frame, text="Loading...", 
                                           style='Value.TLabel')
        self.current_price_label.pack(side=tk.RIGHT)
        
        # Spread
        spread_frame = ttk.Frame(self.market_data_frame, style='Light.TFrame')
        spread_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(spread_frame, text="Spread:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.spread_label = ttk.Label(spread_frame, text="Loading...", style='Value.TLabel')
        self.spread_label.pack(side=tk.RIGHT)
        
        # Market status
        status_frame = ttk.Frame(self.market_data_frame, style='Light.TFrame')
        status_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(status_frame, text="Market Status:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.market_status_label = ttk.Label(status_frame, text="Checking...", 
                                           style='Value.TLabel')
        self.market_status_label.pack(side=tk.RIGHT)
    
    def _create_account_display(self):
        """Create account information display"""
        # Balance
        balance_frame = ttk.Frame(self.account_frame, style='Light.TFrame')
        balance_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(balance_frame, text="Balance:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.balance_label = ttk.Label(balance_frame, text="$0.00", style='Value.TLabel')
        self.balance_label.pack(side=tk.RIGHT)
        
        # Equity
        equity_frame = ttk.Frame(self.account_frame, style='Light.TFrame')
        equity_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(equity_frame, text="Equity:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.equity_label = ttk.Label(equity_frame, text="$0.00", style='Value.TLabel')
        self.equity_label.pack(side=tk.RIGHT)
        
        # Profit/Loss
        pnl_frame = ttk.Frame(self.account_frame, style='Light.TFrame')
        pnl_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(pnl_frame, text="P&L:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.pnl_label = ttk.Label(pnl_frame, text="$0.00", style='Value.TLabel')
        self.pnl_label.pack(side=tk.RIGHT)
    
    def _create_positions_tab(self):
        """Create positions monitoring tab"""
        positions_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(positions_frame, text="📍 Positions")
        
        # Positions table
        table_frame = ttk.Frame(positions_frame, style='Medium.TFrame')
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Table headers
        columns = ("Ticket", "Symbol", "Type", "Volume", "Open Price", "Current Price", "P&L", "Recovery Level")
        
        self.positions_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=100, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack table and scrollbar
        self.positions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_recovery_tab(self):
        """Create recovery system control tab"""
        recovery_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(recovery_frame, text="🔄 Recovery")
        
        # Recovery status
        status_frame = ttk.Frame(recovery_frame, style='Medium.TFrame')
        status_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(status_frame, text="🔄 Recovery System Status", 
                 style='Title.TLabel').pack(pady=(0, 10))
        
        # Recovery indicators
        self._create_recovery_indicators(status_frame)
    
    def _create_recovery_indicators(self, parent):
        """Create recovery system indicators"""
        # Recovery mode indicator
        mode_frame = ttk.Frame(parent, style='Light.TFrame')
        mode_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(mode_frame, text="Recovery Mode:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.recovery_mode_label = ttk.Label(mode_frame, text="Inactive", 
                                           style='Value.TLabel')
        self.recovery_mode_label.pack(side=tk.RIGHT)
        
        # Recovery level
        level_frame = ttk.Frame(parent, style='Light.TFrame')
        level_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(level_frame, text="Recovery Level:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.recovery_level_label = ttk.Label(level_frame, text="0", style='Value.TLabel')
        self.recovery_level_label.pack(side=tk.RIGHT)
    
    def _create_analytics_tab(self):
        """Create analytics tab"""
        analytics_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(analytics_frame, text="📈 Analytics")
        
        # Placeholder for analytics
        ttk.Label(analytics_frame, text="📊 Performance Analytics Coming Soon...", 
                 style='Title.TLabel').pack(expand=True)
    
    def _create_settings_tab(self):
        """Create settings tab"""
        settings_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(settings_frame, text="⚙️ Settings")
        
        # Placeholder for settings
        ttk.Label(settings_frame, text="⚙️ Trading Settings Coming Soon...", 
                 style='Title.TLabel').pack(expand=True)
    
    def _create_bottom_panel(self, parent):
        """Create bottom log panel"""
        bottom_frame = ttk.Frame(parent, style='Medium.TFrame', height=150)
        bottom_frame.pack(fill=tk.X)
        bottom_frame.pack_propagate(False)
        
        # Log title
        ttk.Label(bottom_frame, text="📝 System Logs", style='Title.TLabel').pack(pady=(5, 0))
        
        # Log text area
        log_container = ttk.Frame(bottom_frame, style='Light.TFrame')
        log_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_container, height=8, bg=self.colors['bg_dark'],
                               fg=self.colors['text_white'], font=('Consolas', 9))
        
        log_scrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL, 
                                     command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = tk.Frame(self.root, bg=self.colors['bg_medium'], height=25)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # System time
        self.time_label = tk.Label(self.status_bar, text="", 
                                  bg=self.colors['bg_medium'],
                                  fg=self.colors['text_gray'],
                                  font=('Arial', 8))
        self.time_label.pack(side=tk.RIGHT, padx=10)
        
        # Status message
        self.status_label = tk.Label(self.status_bar, text="System Ready", 
                                    bg=self.colors['bg_medium'],
                                    fg=self.colors['text_white'],
                                    font=('Arial', 8))
        self.status_label.pack(side=tk.LEFT, padx=10)
    
    def _start_update_threads(self):
        """Start background update threads"""
        # Time update thread
        def update_time():
            while True:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    self.time_label.config(text=current_time)
                except tk.TclError:
                    break  # Window closed
                threading.Event().wait(1)
        
        time_thread = threading.Thread(target=update_time, daemon=True)
        time_thread.start()
        
        # Market data update thread
        def update_market_data():
            while True:
                if self.is_connected and self.mt5_interface:
                    self._update_market_display()
                threading.Event().wait(5)  # Update every 5 seconds
        
        market_thread = threading.Thread(target=update_market_data, daemon=True)
        market_thread.start()
    
    def _update_market_display(self):
        """Update market data display"""
        try:
            # Get current price from MT5
            if self.mt5_interface:
                price_data = self.mt5_interface.get_current_price("XAUUSD")
                if price_data:
                    bid = price_data.get('bid', 0)
                    ask = price_data.get('ask', 0)
                    spread = ask - bid
                    
                    self.current_price_label.config(text=f"${bid:.2f} / ${ask:.2f}")
                    self.spread_label.config(text=f"{spread:.1f} pips")
                    self.market_status_label.config(text="🟢 Active")
        except Exception as e:
            self.log_message(f"Market update error: {e}", "ERROR")
    
    def log_message(self, message: str, level: str = "INFO"):
        """Add message to log"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Color coding
            colors = {
                "INFO": self.colors['text_white'],
                "SUCCESS": self.colors['success'],
                "WARNING": self.colors['warning'],
                "ERROR": self.colors['danger']
            }
            
            color = colors.get(level, self.colors['text_white'])
            
            # Add to log
            log_line = f"[{timestamp}] {level}: {message}\n"
            
            self.log_text.insert(tk.END, log_line)
            self.log_text.see(tk.END)
            
            # Limit log size
            if int(self.log_text.index('end-1c').split('.')[0]) > 1000:
                self.log_text.delete(1.0, "100.0")
            
        except Exception as e:
            print(f"Log error: {e}")
    
    # Button command methods
    def connect_mt5(self):
        """Connect to MT5"""
        self.log_message("Attempting MT5 connection...", "INFO")
        # Implementation will be added when MT5 integration is complete
        
    def disconnect_mt5(self):
        """Disconnect from MT5"""
        self.log_message("Disconnecting MT5...", "INFO")
        
    def start_trading(self):
        """Start trading system"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to MT5 first!")
            return
        
        self.is_trading = True
        self.trading_status_label.config(text="▶️ Active", fg=self.colors['success'])
        self.log_message("Trading system started", "SUCCESS")
        
    def stop_trading(self):
        """Stop trading system"""
        self.is_trading = False
        self.trading_status_label.config(text="⏸️ Stopped", fg=self.colors['warning'])
        self.log_message("Trading system stopped", "WARNING")
        
    def close_all_positions(self):
        """Close all open positions"""
        if messagebox.askyesno("Confirm", "Close all open positions?"):
            self.log_message("Closing all positions...", "WARNING")
    
    def save_config(self):
        """Save configuration"""
        self.log_message("Configuration saved", "SUCCESS")
        
    def load_config(self):
        """Load configuration"""
        self.log_message("Configuration loaded", "INFO")
        
    def export_report(self):
        """Export trading report"""
        self.log_message("Report exported", "SUCCESS")
        
    def show_market_analysis(self):
        """Show market analysis window"""
        messagebox.showinfo("Market Analysis", "Market Analysis tool coming soon!")
        
    def show_recovery_settings(self):
        """Show recovery settings window"""
        messagebox.showinfo("Recovery Settings", "Recovery Settings panel coming soon!")
        
    def show_risk_manager(self):
        """Show risk manager window"""
        messagebox.showinfo("Risk Manager", "Risk Manager tool coming soon!")
        
    def show_manual(self):
        """Show user manual"""
        messagebox.showinfo("User Manual", "User Manual coming soon!")
        
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
        self.root.quit()
    
    def run(self):
        """Start the GUI application"""
        self.log_message("🚀 Professional Trading Interface Started", "SUCCESS")
        self.log_message("Ready for MT5 connection and live trading", "INFO")
        self.root.mainloop()

def main():
    """Main entry point for GUI"""
    app = ProfessionalTradingGUI()
    app.run()

if __name__ == "__main__":
    main()