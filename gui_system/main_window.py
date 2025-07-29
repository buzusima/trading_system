#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAIN WINDOW - หน้าต่างหลักของระบบ (COMPLETE)
===========================================
GUI หลักของ Intelligent Gold Trading System
ฉบับสมบูรณ์แบบที่มีฟีเจอร์ครบถ้วน

🎯 ฟีเจอร์หลัก:
- Real-time Trading Dashboard
- System Status Monitoring
- Component Control Panel
- Performance Analytics Display
- Position Management Interface
- Recovery System Controls
- Professional Dark Theme
- Multi-tab Interface
- Real-time Updates
- Error Handling & Logging
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import json
from collections import defaultdict, deque
import queue
import sys
from pathlib import Path

# Safe imports
try:
    from utilities.professional_logger import setup_component_logger
except ImportError:
    import logging
    def setup_component_logger(name):
        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

class DashboardColors:
    """
    Professional Trading Dashboard Color Scheme
    Dark theme optimized for long trading sessions
    """
    # Background Colors
    BG_DARK = '#1a1a2e'
    BG_MEDIUM = '#16213e'
    BG_LIGHT = '#0f3460'
    BG_CARD = '#252545'
    
    # Accent Colors
    PRIMARY = '#e94560'
    SECONDARY = '#f39c12'
    SUCCESS = '#27ae60'
    WARNING = '#f39c1c'
    DANGER = '#e74c3c'
    INFO = '#3498db'
    
    # Text Colors
    TEXT_WHITE = '#ffffff'
    TEXT_GRAY = '#bdc3c7'
    TEXT_LIGHT = '#ecf0f1'
    TEXT_MUTED = '#95a5a6'
    
    # Trading Colors
    PROFIT = '#27ae60'
    LOSS = '#e74c3c'
    PENDING = '#f1c40f'
    NEUTRAL = '#3498db'
    
    # Chart Colors
    CHART_LINE = '#2980b9'
    CHART_AREA = '#34495e'
    CHART_GRID = '#2c3e50'
    
    # Component Status Colors
    RUNNING = '#27ae60'
    STOPPED = '#e74c3c'
    ERROR = '#e67e22'
    LOADING = '#f39c12'

class StatusIndicator(tk.Frame):
    """Status Indicator Widget"""
    
    def __init__(self, parent, label_text="Status", **kwargs):
        super().__init__(parent, bg=DashboardColors.BG_MEDIUM, **kwargs)
        
        self.label = tk.Label(
            self,
            text=label_text,
            font=("Arial", 10),
            fg=DashboardColors.TEXT_GRAY,
            bg=DashboardColors.BG_MEDIUM
        )
        self.label.pack(side=tk.LEFT, padx=5)
        
        self.status_circle = tk.Label(
            self,
            text="●",
            font=("Arial", 12),
            fg=DashboardColors.TEXT_MUTED,
            bg=DashboardColors.BG_MEDIUM
        )
        self.status_circle.pack(side=tk.LEFT, padx=2)
        
        self.status_text = tk.Label(
            self,
            text="Unknown",
            font=("Arial", 10, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        )
        self.status_text.pack(side=tk.LEFT, padx=5)
    
    def update_status(self, status: str, color: str = None):
        """Update status display"""
        self.status_text.config(text=status)
        
        if color:
            self.status_circle.config(fg=color)
        else:
            # Auto color based on status
            status_colors = {
                'RUNNING': DashboardColors.RUNNING,
                'HEALTHY': DashboardColors.SUCCESS,
                'STOPPED': DashboardColors.STOPPED,
                'ERROR': DashboardColors.ERROR,
                'LOADING': DashboardColors.WARNING,
                'READY': DashboardColors.INFO
            }
            self.status_circle.config(fg=status_colors.get(status.upper(), DashboardColors.TEXT_MUTED))

class MetricCard(tk.Frame):
    """Metric Display Card"""
    
    def __init__(self, parent, title="Metric", value="0", unit="", **kwargs):
        super().__init__(parent, bg=DashboardColors.BG_CARD, relief=tk.RAISED, bd=1, **kwargs)
        
        # Title
        self.title_label = tk.Label(
            self,
            text=title,
            font=("Arial", 10),
            fg=DashboardColors.TEXT_GRAY,
            bg=DashboardColors.BG_CARD
        )
        self.title_label.pack(pady=(10, 2))
        
        # Value
        self.value_label = tk.Label(
            self,
            text=value,
            font=("Arial", 18, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_CARD
        )
        self.value_label.pack()
        
        # Unit
        if unit:
            self.unit_label = tk.Label(
                self,
                text=unit,
                font=("Arial", 9),
                fg=DashboardColors.TEXT_MUTED,
                bg=DashboardColors.BG_CARD
            )
            self.unit_label.pack(pady=(0, 10))
    
    def update_value(self, value: str, color: str = None):
        """Update metric value"""
        self.value_label.config(text=value)
        if color:
            self.value_label.config(fg=color)

class LogPanel(tk.Frame):
    """Professional Log Display Panel"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=DashboardColors.BG_MEDIUM, **kwargs)
        
        # Header
        header_frame = tk.Frame(self, bg=DashboardColors.BG_MEDIUM)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(
            header_frame,
            text="📋 System Logs",
            font=("Arial", 12, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        ).pack(side=tk.LEFT)
        
        # Control buttons
        control_frame = tk.Frame(header_frame, bg=DashboardColors.BG_MEDIUM)
        control_frame.pack(side=tk.RIGHT)
        
        self.clear_btn = tk.Button(
            control_frame,
            text="Clear",
            command=self.clear_logs,
            bg=DashboardColors.WARNING,
            fg=DashboardColors.TEXT_WHITE,
            font=("Arial", 9),
            width=8
        )
        self.clear_btn.pack(side=tk.RIGHT, padx=2)
        
        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_cb = tk.Checkbutton(
            control_frame,
            text="Auto Scroll",
            variable=self.auto_scroll_var,
            fg=DashboardColors.TEXT_GRAY,
            bg=DashboardColors.BG_MEDIUM,
            selectcolor=DashboardColors.BG_LIGHT,
            font=("Arial", 9)
        )
        self.auto_scroll_cb.pack(side=tk.RIGHT, padx=5)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(
            self,
            height=12,
            width=80,
            bg=DashboardColors.BG_DARK,
            fg=DashboardColors.TEXT_WHITE,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        # Configure text tags for different log levels
        self.log_text.tag_configure("INFO", foreground=DashboardColors.TEXT_WHITE)
        self.log_text.tag_configure("WARNING", foreground=DashboardColors.WARNING)
        self.log_text.tag_configure("ERROR", foreground=DashboardColors.DANGER)
        self.log_text.tag_configure("SUCCESS", foreground=DashboardColors.SUCCESS)
        self.log_text.tag_configure("TIMESTAMP", foreground=DashboardColors.TEXT_MUTED)
        
        # Log buffer
        self.log_buffer = deque(maxlen=1000)
    
    def add_log(self, message: str, level: str = "INFO"):
        """Add log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        self.log_buffer.append(log_entry)
        
        # Update text widget
        self.log_text.config(state=tk.NORMAL)
        
        # Insert timestamp
        self.log_text.insert(tk.END, f"[{timestamp}] ", "TIMESTAMP")
        
        # Insert message with appropriate color
        self.log_text.insert(tk.END, f"{message}\n", level.upper())
        
        # Auto scroll if enabled
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        
        self.log_text.config(state=tk.DISABLED)
    
    def clear_logs(self):
        """Clear all logs"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log_buffer.clear()

class ComponentPanel(tk.Frame):
    """Component Status Panel"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=DashboardColors.BG_MEDIUM, **kwargs)
        
        # Header
        header_frame = tk.Frame(self, bg=DashboardColors.BG_MEDIUM)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            header_frame,
            text="⚙️ System Components",
            font=("Arial", 12, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        ).pack(side=tk.LEFT)
        
        # Components list
        self.components_frame = tk.Frame(self, bg=DashboardColors.BG_MEDIUM)
        self.components_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Component status indicators
        self.component_indicators = {}
        
        # Create component indicators
        components = [
            'market_analyzer', 'signal_generator', 'recovery_engine',
            'position_tracker', 'order_executor', 'performance_tracker'
        ]
        
        for i, component in enumerate(components):
            row = i // 2
            col = i % 2
            
            component_frame = tk.Frame(
                self.components_frame,
                bg=DashboardColors.BG_CARD,
                relief=tk.RAISED,
                bd=1
            )
            component_frame.grid(row=row, column=col, padx=5, pady=3, sticky="ew")
            
            # Component name
            name_label = tk.Label(
                component_frame,
                text=component.replace('_', ' ').title(),
                font=("Arial", 10, "bold"),
                fg=DashboardColors.TEXT_WHITE,
                bg=DashboardColors.BG_CARD
            )
            name_label.pack(side=tk.LEFT, padx=10, pady=5)
            
            # Status indicator
            status_indicator = StatusIndicator(component_frame, "")
            status_indicator.pack(side=tk.RIGHT, padx=10, pady=5)
            
            self.component_indicators[component] = status_indicator
        
        # Configure grid weights
        self.components_frame.grid_columnconfigure(0, weight=1)
        self.components_frame.grid_columnconfigure(1, weight=1)
    
    def update_component_status(self, component: str, status: str, health: str = ""):
        """Update component status"""
        if component in self.component_indicators:
            display_status = health if health else status
            self.component_indicators[component].update_status(display_status)

class TradingControlPanel(tk.Frame):
    """Trading Control Panel"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=DashboardColors.BG_MEDIUM, **kwargs)
        
        # Header
        header_frame = tk.Frame(self, bg=DashboardColors.BG_MEDIUM)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            header_frame,
            text="🎯 Trading Controls",
            font=("Arial", 12, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        ).pack()
        
        # Control buttons
        button_frame = tk.Frame(self, bg=DashboardColors.BG_MEDIUM)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Start/Stop buttons
        self.start_btn = tk.Button(
            button_frame,
            text="🚀 Start Trading",
            font=("Arial", 12, "bold"),
            bg=DashboardColors.SUCCESS,
            fg=DashboardColors.TEXT_WHITE,
            width=15,
            height=2
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(
            button_frame,
            text="🛑 Stop Trading",
            font=("Arial", 12, "bold"),
            bg=DashboardColors.DANGER,
            fg=DashboardColors.TEXT_WHITE,
            width=15,
            height=2,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Emergency stop
        self.emergency_btn = tk.Button(
            button_frame,
            text="🚨 EMERGENCY",
            font=("Arial", 12, "bold"),
            bg=DashboardColors.DANGER,
            fg=DashboardColors.TEXT_WHITE,
            width=15,
            height=2
        )
        self.emergency_btn.pack(side=tk.RIGHT, padx=5)
        
        # Status and controls
        status_frame = tk.Frame(self, bg=DashboardColors.BG_MEDIUM)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # System status
        self.system_status = StatusIndicator(status_frame, "System Status")
        self.system_status.pack(side=tk.LEFT, padx=10)
        
        # Trading status
        self.trading_status = StatusIndicator(status_frame, "Trading Status")
        self.trading_status.pack(side=tk.LEFT, padx=10)
        
        # Auto trading toggle
        self.auto_trading_var = tk.BooleanVar()
        self.auto_trading_cb = tk.Checkbutton(
            status_frame,
            text="Auto Trading",
            variable=self.auto_trading_var,
            font=("Arial", 10),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM,
            selectcolor=DashboardColors.BG_LIGHT
        )
        self.auto_trading_cb.pack(side=tk.RIGHT, padx=10)

class PerformancePanel(tk.Frame):
    """Performance Metrics Panel"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=DashboardColors.BG_MEDIUM, **kwargs)
        
        # Header
        header_frame = tk.Frame(self, bg=DashboardColors.BG_MEDIUM)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            header_frame,
            text="📊 Performance Metrics",
            font=("Arial", 12, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        ).pack()
        
        # Metrics grid
        metrics_frame = tk.Frame(self, bg=DashboardColors.BG_MEDIUM)
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create metric cards
        self.metric_cards = {}
        
        metrics = [
            ('Signals Today', '0', 'signals'),
            ('Success Rate', '0%', 'rate'),
            ('Open Positions', '0', 'positions'),
            ('Total Profit', '$0.00', 'profit'),
            ('Volume Today', '0.00', 'lots'),
            ('Recovery Ops', '0', 'operations')
        ]
        
        for i, (title, value, unit) in enumerate(metrics):
            row = i // 3
            col = i % 3
            
            card = MetricCard(metrics_frame, title=title, value=value, unit=unit)
            card.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            
            self.metric_cards[title.lower().replace(' ', '_')] = card
        
        # Configure grid weights
        for i in range(3):
            metrics_frame.grid_columnconfigure(i, weight=1)
    
    def update_metrics(self, metrics_data: Dict[str, Any]):
        """Update performance metrics"""
        try:
            # Signals
            if 'signals' in metrics_data:
                signals = metrics_data['signals']
                self.metric_cards['signals_today'].update_value(str(signals.get('generated_today', 0)))
                
                success_rate = signals.get('success_rate', 0.0)
                color = DashboardColors.SUCCESS if success_rate > 60 else DashboardColors.WARNING if success_rate > 30 else DashboardColors.DANGER
                self.metric_cards['success_rate'].update_value(f"{success_rate:.1f}%", color)
            
            # Positions
            if 'positions' in metrics_data:
                positions = metrics_data['positions']
                self.metric_cards['open_positions'].update_value(str(positions.get('open_count', 0)))
                
                profit = positions.get('total_profit', 0.0)
                color = DashboardColors.SUCCESS if profit > 0 else DashboardColors.DANGER if profit < 0 else DashboardColors.TEXT_WHITE
                self.metric_cards['total_profit'].update_value(f"${profit:.2f}", color)
                
                volume = positions.get('open_volume', 0.0)
                self.metric_cards['volume_today'].update_value(f"{volume:.2f}")
            
            # Recovery
            if 'recovery' in metrics_data:
                recovery = metrics_data['recovery']
                self.metric_cards['recovery_ops'].update_value(str(recovery.get('recovery_operations', 0)))
        
        except Exception as e:
            print(f"❌ Error updating metrics: {e}")

class TradingSystemGUI:
    """🖥️ Main Trading System GUI - ฉบับสมบูรณ์"""
    
    def __init__(self, settings=None, logger=None, trading_system=None):
        """Initialize GUI"""
        self.settings = settings
        self.logger = logger or setup_component_logger("TradingSystemGUI")
        self.trading_system = trading_system
        
        # GUI State
        self.gui_active = False
        self.update_thread = None
        self.update_interval = 1000  # ms
        
        # Data buffers
        self.last_system_status = {}
        self.message_queue = queue.Queue()
        
        # Create main window
        self.root = tk.Tk()
        self._setup_main_window()
        
        # Create GUI components
        self._create_gui_components()
        
        # Bind events
        self._bind_events()
        
        # Start update loop
        self._start_update_loop()
        
        self.logger.info("🖥️ เริ่มต้น Trading System GUI")
    
    def _setup_main_window(self):
        """Setup main window properties"""
        self.root.title("🚀 Intelligent Gold Trading System v2.0")
        self.root.geometry("1400x900")
        self.root.configure(bg=DashboardColors.BG_DARK)
        self.root.resizable(True, True)
        
        # Window icon (if available)
        try:
            # You can add icon file here
            pass
        except:
            pass
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1400 // 2)
        y = (self.root.winfo_screenheight() // 2) - (900 // 2)
        self.root.geometry(f"1400x900+{x}+{y}")
    
    def _create_gui_components(self):
        """Create all GUI components"""
        # Main title
        title_frame = tk.Frame(self.root, bg=DashboardColors.BG_DARK)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            title_frame,
            text="🚀 INTELLIGENT GOLD TRADING SYSTEM",
            font=("Arial", 20, "bold"),
            fg=DashboardColors.PRIMARY,
            bg=DashboardColors.BG_DARK
        ).pack()
        
        tk.Label(
            title_frame,
            text="Professional Automated Gold Trading Platform",
            font=("Arial", 12),
            fg=DashboardColors.TEXT_GRAY,
            bg=DashboardColors.BG_DARK
        ).pack()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Configure notebook style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background=DashboardColors.BG_DARK)
        style.configure('TNotebook.Tab', background=DashboardColors.BG_MEDIUM, foreground=DashboardColors.TEXT_WHITE)
        
        # Create tabs
        self._create_dashboard_tab()
        self._create_control_tab()
        self._create_performance_tab()
        self._create_logs_tab()
        self._create_settings_tab()
        
        # Status bar
        self._create_status_bar()
    
    def _create_dashboard_tab(self):
        """Create main dashboard tab"""
        dashboard_frame = tk.Frame(self.notebook, bg=DashboardColors.BG_DARK)
        self.notebook.add(dashboard_frame, text="📊 Dashboard")
        
        # Top section - System Overview
        top_frame = tk.Frame(dashboard_frame, bg=DashboardColors.BG_DARK)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # System status panel
        system_panel = tk.Frame(top_frame, bg=DashboardColors.BG_MEDIUM, relief=tk.RAISED, bd=2)
        system_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        tk.Label(
            system_panel,
            text="🖥️ System Overview",
            font=("Arial", 14, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        ).pack(pady=10)
        
        # System info
        self.system_info_frame = tk.Frame(system_panel, bg=DashboardColors.BG_MEDIUM)
        self.system_info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # System status labels
        self.system_labels = {}
        info_items = [
            ('System State', 'INITIALIZING'),
            ('Uptime', '00:00:00'),
            ('Components', '0/6'),
            ('Health', 'UNKNOWN')
        ]
        
        for item, default_value in info_items:
            row_frame = tk.Frame(self.system_info_frame, bg=DashboardColors.BG_MEDIUM)
            row_frame.pack(fill=tk.X, pady=2)
            
            tk.Label(
                row_frame,
                text=f"{item}:",
                font=("Arial", 10),
                fg=DashboardColors.TEXT_GRAY,
                bg=DashboardColors.BG_MEDIUM,
                width=12,
                anchor='w'
            ).pack(side=tk.LEFT)
            
            label = tk.Label(
                row_frame,
                text=default_value,
                font=("Arial", 10, "bold"),
                fg=DashboardColors.TEXT_WHITE,
                bg=DashboardColors.BG_MEDIUM,
                anchor='w'
            )
            label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            self.system_labels[item.lower().replace(' ', '_')] = label
        
        # Middle section - Components and Performance
        middle_frame = tk.Frame(dashboard_frame, bg=DashboardColors.BG_DARK)
        middle_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Components panel
        self.component_panel = ComponentPanel(middle_frame)
        self.component_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Performance panel
        self.performance_panel = PerformancePanel(middle_frame)
        self.performance_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # Bottom section - Quick logs
        bottom_frame = tk.Frame(dashboard_frame, bg=DashboardColors.BG_DARK)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Quick log panel
        self.quick_log_panel = LogPanel(bottom_frame)
        self.quick_log_panel.pack(fill=tk.X, pady=5)
        
        # Limit quick log height
        self.quick_log_panel.log_text.config(height=6)
    
    def _create_control_tab(self):
        """Create control tab"""
        control_frame = tk.Frame(self.notebook, bg=DashboardColors.BG_DARK)
        self.notebook.add(control_frame, text="🎮 Controls")
        
        # Trading control panel
        self.trading_control = TradingControlPanel(control_frame)
        self.trading_control.pack(fill=tk.X, padx=10, pady=10)
        
        # Component controls
        component_control_frame = tk.Frame(control_frame, bg=DashboardColors.BG_MEDIUM, relief=tk.RAISED, bd=2)
        component_control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            component_control_frame,
            text="⚙️ Component Controls",
            font=("Arial", 12, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        ).pack(pady=10)
        
        # Individual component restart buttons
        button_frame = tk.Frame(component_control_frame, bg=DashboardColors.BG_MEDIUM)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        components = [
            'market_analyzer', 'signal_generator', 'recovery_engine',
            'position_tracker', 'order_executor', 'performance_tracker'
        ]
        
        self.component_buttons = {}
        for i, component in enumerate(components):
            btn = tk.Button(
                button_frame,
                text=f"Restart {component.replace('_', ' ').title()}",
                font=("Arial", 9),
                bg=DashboardColors.WARNING,
                fg=DashboardColors.TEXT_WHITE,
                width=20,
                command=lambda c=component: self._restart_component(c)
            )
            btn.grid(row=i//3, column=i%3, padx=5, pady=5)
            self.component_buttons[component] = btn
        
        # Configure grid
        for i in range(3):
            button_frame.grid_columnconfigure(i, weight=1)
        
        # System controls
        system_control_frame = tk.Frame(control_frame, bg=DashboardColors.BG_MEDIUM, relief=tk.RAISED, bd=2)
        system_control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            system_control_frame,
            text="🔧 System Controls",
            font=("Arial", 12, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        ).pack(pady=10)
        
        system_btn_frame = tk.Frame(system_control_frame, bg=DashboardColors.BG_MEDIUM)
        system_btn_frame.pack(pady=10)
        
        # System control buttons
        tk.Button(
            system_btn_frame,
            text="🔄 Reset System",
            font=("Arial", 10),
            bg=DashboardColors.WARNING,
            fg=DashboardColors.TEXT_WHITE,
            width=15,
            command=self._reset_system
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            system_btn_frame,
            text="🛑 Force Close Positions",
            font=("Arial", 10),
            bg=DashboardColors.DANGER,
            fg=DashboardColors.TEXT_WHITE,
            width=20,
            command=self._force_close_positions
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            system_btn_frame,
            text="📁 Export Logs",
            font=("Arial", 10),
            bg=DashboardColors.INFO,
            fg=DashboardColors.TEXT_WHITE,
            width=15,
            command=self._export_logs
        ).pack(side=tk.LEFT, padx=5)

   
    def _create_performance_tab(self):
        """Create performance analysis tab"""
        perf_frame = tk.Frame(self.notebook, bg=DashboardColors.BG_DARK)
        self.notebook.add(perf_frame, text="📈 Performance")
        
        # Performance summary
        summary_frame = tk.Frame(perf_frame, bg=DashboardColors.BG_MEDIUM, relief=tk.RAISED, bd=2)
        summary_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            summary_frame,
            text="📊 Performance Summary",
            font=("Arial", 14, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        ).pack(pady=10)
        
        # Detailed metrics
        self.detailed_metrics_frame = tk.Frame(summary_frame, bg=DashboardColors.BG_MEDIUM)
        self.detailed_metrics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create scrollable text for detailed performance
        self.performance_text = scrolledtext.ScrolledText(
            self.detailed_metrics_frame,
            height=20,
            width=80,
            bg=DashboardColors.BG_DARK,
            fg=DashboardColors.TEXT_WHITE,
            font=("Consolas", 10),
            wrap=tk.WORD
        )
        self.performance_text.pack(fill=tk.BOTH, expand=True)
        
        # Strategy performance breakdown
        strategy_frame = tk.Frame(perf_frame, bg=DashboardColors.BG_MEDIUM, relief=tk.RAISED, bd=2)
        strategy_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            strategy_frame,
            text="🎯 Strategy Performance",
            font=("Arial", 14, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        ).pack(pady=10)
        
        self.strategy_text = scrolledtext.ScrolledText(
            strategy_frame,
            height=10,
            width=80,
            bg=DashboardColors.BG_DARK,
            fg=DashboardColors.TEXT_WHITE,
            font=("Consolas", 10),
            wrap=tk.WORD
        )
        self.strategy_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def _create_logs_tab(self):
        """Create detailed logs tab"""
        logs_frame = tk.Frame(self.notebook, bg=DashboardColors.BG_DARK)
        self.notebook.add(logs_frame, text="📋 Logs")
        
        # Full log panel
        self.full_log_panel = LogPanel(logs_frame)
        self.full_log_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Log controls
        control_frame = tk.Frame(logs_frame, bg=DashboardColors.BG_DARK)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Log level filter
        tk.Label(
            control_frame,
            text="Log Level:",
            font=("Arial", 10),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_DARK
        ).pack(side=tk.LEFT, padx=5)
        
        self.log_level_var = tk.StringVar(value="INFO")
        log_level_combo = ttk.Combobox(
            control_frame,
            textvariable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            width=10,
            state="readonly"
        )
        log_level_combo.pack(side=tk.LEFT, padx=5)
        
        # Search functionality
        tk.Label(
            control_frame,
            text="Search:",
            font=("Arial", 10),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_DARK
        ).pack(side=tk.LEFT, padx=(20, 5))
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(
            control_frame,
            textvariable=self.search_var,
            width=20,
            bg=DashboardColors.BG_LIGHT,
            fg=DashboardColors.TEXT_WHITE
        )
        search_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            control_frame,
            text="Search",
            font=("Arial", 9),
            bg=DashboardColors.INFO,
            fg=DashboardColors.TEXT_WHITE,
            command=self._search_logs
        ).pack(side=tk.LEFT, padx=5)
    
    def _create_settings_tab(self):
        """Create settings tab"""
        settings_frame = tk.Frame(self.notebook, bg=DashboardColors.BG_DARK)
        self.notebook.add(settings_frame, text="⚙️ Settings")
        
        # General settings
        general_frame = tk.Frame(settings_frame, bg=DashboardColors.BG_MEDIUM, relief=tk.RAISED, bd=2)
        general_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            general_frame,
            text="⚙️ General Settings",
            font=("Arial", 14, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        ).pack(pady=10)
        
        # Settings controls
        settings_grid = tk.Frame(general_frame, bg=DashboardColors.BG_MEDIUM)
        settings_grid.pack(fill=tk.X, padx=20, pady=10)
        
        # Update interval
        tk.Label(
            settings_grid,
            text="Update Interval (ms):",
            font=("Arial", 10),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        ).grid(row=0, column=0, sticky='w', pady=5)
        
        self.update_interval_var = tk.StringVar(value=str(self.update_interval))
        tk.Entry(
            settings_grid,
            textvariable=self.update_interval_var,
            width=10,
            bg=DashboardColors.BG_LIGHT,
            fg=DashboardColors.TEXT_WHITE
        ).grid(row=0, column=1, padx=10, pady=5)
        
        # Auto scroll logs
        self.auto_scroll_setting = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings_grid,
            text="Auto-scroll logs",
            variable=self.auto_scroll_setting,
            font=("Arial", 10),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM,
            selectcolor=DashboardColors.BG_LIGHT
        ).grid(row=1, column=0, columnspan=2, sticky='w', pady=5)
        
        # Sound notifications
        self.sound_notifications = tk.BooleanVar(value=False)
        tk.Checkbutton(
            settings_grid,
            text="Sound notifications",
            variable=self.sound_notifications,
            font=("Arial", 10),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM,
            selectcolor=DashboardColors.BG_LIGHT
        ).grid(row=2, column=0, columnspan=2, sticky='w', pady=5)
        
        # Apply button
        tk.Button(
            general_frame,
            text="Apply Settings",
            font=("Arial", 10),
            bg=DashboardColors.SUCCESS,
            fg=DashboardColors.TEXT_WHITE,
            command=self._apply_settings
        ).pack(pady=10)
        
        # Trading parameters
        trading_frame = tk.Frame(settings_frame, bg=DashboardColors.BG_MEDIUM, relief=tk.RAISED, bd=2)
        trading_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            trading_frame,
            text="📊 Trading Parameters",
            font=("Arial", 14, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        ).pack(pady=10)
        
        # Trading parameters display
        self.trading_params_text = scrolledtext.ScrolledText(
            trading_frame,
            height=15,
            width=80,
            bg=DashboardColors.BG_DARK,
            fg=DashboardColors.TEXT_WHITE,
            font=("Consolas", 10),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.trading_params_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = tk.Frame(self.root, bg=DashboardColors.BG_MEDIUM, relief=tk.SUNKEN, bd=1)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Status items
        self.status_time = tk.Label(
            self.status_bar,
            text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            font=("Arial", 9),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        )
        self.status_time.pack(side=tk.RIGHT, padx=10)
        
        self.status_message = tk.Label(
            self.status_bar,
            text="System Initializing...",
            font=("Arial", 9),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        )
        self.status_message.pack(side=tk.LEFT, padx=10)
        
        # Connection status
        self.connection_status = StatusIndicator(self.status_bar, "Connection")
        self.connection_status.pack(side=tk.LEFT, padx=20)
    
    def _bind_events(self):
        """Bind GUI events"""
        # Window close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Trading control events
        self.trading_control.start_btn.config(command=self._start_trading)
        self.trading_control.stop_btn.config(command=self._stop_trading)
        self.trading_control.emergency_btn.config(command=self._emergency_stop)
        self.trading_control.auto_trading_var.trace('w', self._on_auto_trading_change)
        
        # Keyboard shortcuts
        self.root.bind('<F1>', lambda e: self._show_help())
        self.root.bind('<F5>', lambda e: self._refresh_all())
        self.root.bind('<Control-s>', lambda e: self._export_logs())
        self.root.bind('<Control-r>', lambda e: self._reset_system())
        self.root.bind('<Escape>', lambda e: self._emergency_stop())
    
    def _start_update_loop(self):
        """Start GUI update loop"""
        self.gui_active = True
        self._schedule_update()
        self.logger.info("🔄 เริ่ม GUI update loop")
    
    def _schedule_update(self):
        """Schedule next GUI update"""
        if self.gui_active:
            self._update_gui()
            self.root.after(self.update_interval, self._schedule_update)
    
    def _update_gui(self):
        """Update GUI components"""
        try:
            # Update status bar time
            self.status_time.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            # Update system status if trading system is available
            if self.trading_system:
                self._update_system_status()
                self._update_performance_displays()
                self._process_message_queue()
            else:
                self.status_message.config(text="Trading System not connected")
                self.connection_status.update_status("DISCONNECTED", DashboardColors.DANGER)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน GUI update: {e}")
    
    def _update_system_status(self):
        """Update system status display"""
        try:
            system_status = self.trading_system.get_system_status()
            
            # Update system labels
            self.system_labels['system_state'].config(text=system_status.get('system_state', 'UNKNOWN'))
            self.system_labels['uptime'].config(text=system_status.get('uptime_formatted', '00:00:00'))
            self.system_labels['components'].config(
                text=f"{system_status.get('components_running', 0)}/{system_status.get('total_components', 0)}"
            )
            
            # System health
            health = self.trading_system.get_system_health()
            health_color = {
                'HEALTHY': DashboardColors.SUCCESS,
                'READY': DashboardColors.INFO,
                'ERROR': DashboardColors.DANGER,
                'INITIALIZING': DashboardColors.WARNING
            }.get(health, DashboardColors.TEXT_WHITE)
            
            self.system_labels['health'].config(text=health, fg=health_color)
            
            # Update component status
            components_status = system_status.get('components_status', {})
            for component, status_info in components_status.items():
                self.component_panel.update_component_status(
                    component,
                    status_info.get('status', 'UNKNOWN'),
                    status_info.get('health', '')
                )
            
            # Update trading control status
            self.trading_control.system_status.update_status(system_status.get('system_state', 'UNKNOWN'))
            
            trading_status = "ACTIVE" if system_status.get('trading_active', False) else "STOPPED"
            self.trading_control.trading_status.update_status(trading_status)
            
            # Update button states
            if system_status.get('trading_active', False):
                self.trading_control.start_btn.config(state=tk.DISABLED)
                self.trading_control.stop_btn.config(state=tk.NORMAL)
            else:
                self.trading_control.start_btn.config(state=tk.NORMAL if system_status.get('system_state') == 'READY' else tk.DISABLED)
                self.trading_control.stop_btn.config(state=tk.DISABLED)
            
            # Update connection status
            self.connection_status.update_status("CONNECTED", DashboardColors.SUCCESS)
            self.status_message.config(text=f"System: {health} | Trading: {trading_status}")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดทสถานะระบบ: {e}")
            self.connection_status.update_status("ERROR", DashboardColors.DANGER)
            self.status_message.config(text="Error updating status")
    
    def _update_performance_displays(self):
        """Update performance displays"""
        try:
            system_status = self.trading_system.get_system_status()
            performance_summary = system_status.get('performance_summary', {})
            
            # Update performance panel
            self.performance_panel.update_metrics(performance_summary)
            
            # Update detailed performance text
            detailed_performance = self.trading_system.get_detailed_performance()
            self._update_performance_text(detailed_performance)
            
            # Update trading parameters display
            self._update_trading_params_display()
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท performance: {e}")
    
    def _update_performance_text(self, detailed_performance: Dict[str, Any]):
        """Update detailed performance text"""
        try:
            self.performance_text.delete(1.0, tk.END)
            
            # Format performance data
            if detailed_performance:
                self.performance_text.insert(tk.END, "=== DETAILED PERFORMANCE ===\n\n")
                
                # Signal strategies
                if 'signal_strategies' in detailed_performance:
                    self.performance_text.insert(tk.END, "📊 Signal Strategies Performance:\n")
                    strategies = detailed_performance['signal_strategies']
                    for strategy, data in strategies.items():
                        self.performance_text.insert(tk.END, 
                            f"  {strategy}:\n"
                            f"    Generated: {data.get('signals_generated', 0)}\n"
                            f"    Executed: {data.get('signals_executed', 0)}\n"
                            f"    Success Rate: {data.get('success_rate_percent', 0)}%\n"
                            f"    Avg Confidence: {data.get('average_confidence', 0):.3f}\n\n"
                        )
                
                # Session analysis
                if 'session_analysis' in detailed_performance:
                    self.performance_text.insert(tk.END, "🕐 Session Analysis:\n")
                    sessions = detailed_performance['session_analysis']
                    for session, data in sessions.items():
                        self.performance_text.insert(tk.END,
                            f"  {session}:\n"
                            f"    Signals: {data.get('signals_generated', 0)}\n"
                            f"    Avg Confidence: {data.get('average_confidence', 0):.3f}\n"
                            f"    Most Used Strategy: {data.get('most_used_strategy', 'None')}\n\n"
                        )
            else:
                self.performance_text.insert(tk.END, "No detailed performance data available.")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท performance text: {e}")
    
    def _update_trading_params_display(self):
        """Update trading parameters display"""
        try:
            self.trading_params_text.config(state=tk.NORMAL)
            self.trading_params_text.delete(1.0, tk.END)
            
            if self.settings:
                self.trading_params_text.insert(tk.END, "=== TRADING PARAMETERS ===\n\n")
                
                # Basic settings
                self.trading_params_text.insert(tk.END, "📊 Basic Settings:\n")
                self.trading_params_text.insert(tk.END, f"  Symbol: {getattr(self.settings, 'symbol', 'XAUUSD')}\n")
                self.trading_params_text.insert(tk.END, f"  Trading Mode: {getattr(self.settings, 'trading_mode', 'LIVE')}\n")
                self.trading_params_text.insert(tk.END, f"  High Frequency: {getattr(self.settings, 'high_frequency_mode', True)}\n\n")
                
                # Volume targets
                self.trading_params_text.insert(tk.END, "🎯 Volume Targets:\n")
                self.trading_params_text.insert(tk.END, f"  Daily Min: {getattr(self.settings, 'daily_volume_target_min', 50)} lots\n")
                self.trading_params_text.insert(tk.END, f"  Daily Max: {getattr(self.settings, 'daily_volume_target_max', 100)} lots\n\n")
                
                # Risk management
                self.trading_params_text.insert(tk.END, "⚠️ Risk Management:\n")
                self.trading_params_text.insert(tk.END, f"  Use Stop Loss: {getattr(self.settings, 'use_stop_loss', False)}\n")
                self.trading_params_text.insert(tk.END, f"  Recovery Mandatory: {getattr(self.settings, 'recovery_mandatory', True)}\n")
            
            self.trading_params_text.config(state=tk.DISABLED)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท trading params: {e}")
    
    def _process_message_queue(self):
        """Process messages from trading system"""
        try:
            while not self.message_queue.empty():
                try:
                    message_data = self.message_queue.get_nowait()
                    message = message_data.get('message', '')
                    level = message_data.get('level', 'INFO')
                    
                    # Add to both log panels
                    self.quick_log_panel.add_log(message, level)
                    self.full_log_panel.add_log(message, level)
                    
                except queue.Empty:
                    break
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการประมวลผล message queue: {e}")
    
    # Event Handlers
    def _start_trading(self):
        """Start trading button handler"""
        try:
            if not self.trading_system:
                messagebox.showerror("Error", "Trading system not connected!")
                return
            
            if not self.trading_system.is_system_ready():
                messagebox.showwarning("Warning", "System is not ready for trading!")
                return
            
            # Confirm start
            if messagebox.askyesno("Confirm", "Start automated trading?\n\nThis will begin live trading with real money."):
                self.log_message("🚀 กำลังเริ่มระบบการเทรด...", "INFO")
                
                # Start in separate thread to avoid blocking GUI
                threading.Thread(
                    target=self._start_trading_worker,
                    daemon=True
                ).start()
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเริ่มการเทรด: {e}")
            messagebox.showerror("Error", f"Failed to start trading: {e}")
    
    def _start_trading_worker(self):
        """Worker thread for starting trading"""
        try:
            success = self.trading_system.start_trading()
            
            if success:
                self.log_message("✅ เริ่มการเทรดสำเร็จ", "SUCCESS")
                
                # Enable auto trading if checkbox is checked
                if self.trading_control.auto_trading_var.get():
                    self.trading_system.enable_auto_trading()
                    self.log_message("🤖 เปิดใช้งาน Auto Trading", "INFO")
            else:
                self.log_message("❌ ไม่สามารถเริ่มการเทรดได้", "ERROR")
                
        except Exception as e:
            self.log_message(f"💥 ข้อผิดพลาดในการเริ่มการเทรด: {e}", "ERROR")
    
    def _stop_trading(self):
        """Stop trading button handler"""
        try:
            if not self.trading_system:
                return
            
            if messagebox.askyesno("Confirm", "Stop automated trading?"):
                self.log_message("🛑 กำลังหยุดระบบการเทรด...", "INFO")
                
                threading.Thread(
                    target=self._stop_trading_worker,
                    daemon=True
                ).start()
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการหยุดการเทรด: {e}")
    
    def _stop_trading_worker(self):
        """Worker thread for stopping trading"""
        try:
            self.trading_system.stop_trading()
            self.log_message("✅ หยุดการเทรดสำเร็จ", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"💥 ข้อผิดพลาดในการหยุดการเทรด: {e}", "ERROR")
    
    def _emergency_stop(self):
        """Emergency stop button handler"""
        try:
            if not self.trading_system:
                return
            
            if messagebox.askyesno("EMERGENCY STOP", 
                                    "🚨 EMERGENCY STOP 🚨\n\n"
                                    "This will immediately:\n"
                                    "• Stop all trading\n"
                                    "• Close all positions\n" 
                                    "• Shutdown system\n\n"
                                    "Are you sure?"):
                
                self.log_message("🚨 EMERGENCY STOP - กำลังหยุดระบบฉุกเฉิน!", "ERROR")
                
                threading.Thread(
                    target=self._emergency_stop_worker,
                    daemon=True
                ).start()
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Emergency Stop: {e}")
    
    def _emergency_stop_worker(self):
        """Worker thread for emergency stop"""
        try:
            self.trading_system.emergency_stop()
            self.log_message("🚨 Emergency Stop เสร็จสิ้น", "ERROR")
            
        except Exception as e:
            self.log_message(f"💥 ข้อผิดพลาดใน Emergency Stop: {e}", "ERROR")
    
    def _on_auto_trading_change(self, *args):
        """Auto trading checkbox change handler"""
        try:
            if not self.trading_system:
                return
            
            if self.trading_control.auto_trading_var.get():
                self.trading_system.enable_auto_trading()
                self.log_message("🤖 เปิดใช้งาน Auto Trading", "INFO")
            else:
                self.trading_system.disable_auto_trading()
                self.log_message("⏸️ ปิดใช้งาน Auto Trading", "INFO")
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเปลี่ยน Auto Trading: {e}")
    
    def _restart_component(self, component_name: str):
        """Restart component button handler"""
        try:
            if not self.trading_system:
                messagebox.showerror("Error", "Trading system not connected!")
                return
            
            if messagebox.askyesno("Confirm", f"Restart {component_name.replace('_', ' ').title()}?"):
                self.log_message(f"🔄 กำลังรีสตาร์ท {component_name}...", "INFO")
                
                threading.Thread(
                    target=lambda: self._restart_component_worker(component_name),
                    daemon=True
                ).start()
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการรีสตาร์ท component: {e}")
    
    def _restart_component_worker(self, component_name: str):
        """Worker thread for restarting component"""
        try:
            success = self.trading_system.restart_component(component_name)
            
            if success:
                self.log_message(f"✅ รีสตาร์ท {component_name} สำเร็จ", "SUCCESS")
            else:
                self.log_message(f"❌ รีสตาร์ท {component_name} ล้มเหลว", "ERROR")
                
        except Exception as e:
            self.log_message(f"💥 ข้อผิดพลาดในการรีสตาร์ท {component_name}: {e}", "ERROR")
    
    def _reset_system(self):
        """Reset system button handler"""
        try:
            if not self.trading_system:
                return
            
            if messagebox.askyesno("Confirm", 
                                    "Reset entire system?\n\n"
                                    "This will stop all trading and reset all components."):
                
                self.log_message("🔄 กำลังรีเซ็ตระบบ...", "WARNING")
                
                threading.Thread(
                    target=self._reset_system_worker,
                    daemon=True
                ).start()
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการรีเซ็ตระบบ: {e}")
    
    def _reset_system_worker(self):
        """Worker thread for resetting system"""
        try:
            self.trading_system.reset_system()
            self.log_message("✅ รีเซ็ตระบบเสร็จสิ้น", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"💥 ข้อผิดพลาดในการรีเซ็ตระบบ: {e}", "ERROR")
    
    def _force_close_positions(self):
        """Force close all positions"""
        try:
            if not self.trading_system:
                return
            
            if messagebox.askyesno("Confirm",
                                    "Force close ALL positions?\n\n"
                                    "This will immediately close all open positions."):
                
                self.log_message("🛑 กำลังปิด positions ทั้งหมด...", "WARNING")
                
                threading.Thread(
                    target=self._force_close_positions_worker,
                    daemon=True
                ).start()
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการปิด positions: {e}")
    
    def _force_close_positions_worker(self):
        """Worker thread for force closing positions"""
        try:
            self.trading_system.force_close_all_positions()
            self.log_message("✅ ปิด positions ทั้งหมดเสร็จสิ้น", "SUCCESS")
        
        except Exception as e:
            self.log_message(f"💥 ข้อผิดพลาดในการปิด positions: {e}", "ERROR")
    
    def _export_logs(self):
        """Export system logs"""
        try:
            if not self.trading_system:
                messagebox.showerror("Error", "Trading system not connected!")
                return
            
            self.log_message("📁 กำลังส่งออก system logs...", "INFO")
            
            threading.Thread(
                target=self._export_logs_worker,
                daemon=True
            ).start()
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการส่งออก logs: {e}")
    
    def _export_logs_worker(self):
        """Worker thread for exporting logs"""
        try:
            filename = self.trading_system.export_system_logs()
            
            if filename:
                self.log_message(f"✅ ส่งออก logs เสร็จสิ้น: {filename}", "SUCCESS")
                messagebox.showinfo("Export Complete", f"Logs exported to: {filename}")
            else:
                self.log_message("❌ ไม่สามารถส่งออก logs ได้", "ERROR")
                
        except Exception as e:
            self.log_message(f"💥 ข้อผิดพลาดในการส่งออก logs: {e}", "ERROR")
    
    def _search_logs(self):
        """Search logs functionality"""
        try:
            search_term = self.search_var.get().strip()
            
            if not search_term:
                messagebox.showwarning("Warning", "Please enter search term")
                return
            
            # Search in log buffer
            found_logs = []
            for log_entry in self.full_log_panel.log_buffer:
                if search_term.lower() in log_entry.lower():
                    found_logs.append(log_entry)
            
            # Display results in a new window
            if found_logs:
                self._show_search_results(search_term, found_logs)
            else:
                messagebox.showinfo("Search Results", f"No logs found containing: {search_term}")
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการค้นหา logs: {e}")
    
    def _show_search_results(self, search_term: str, results: List[str]):
        """Show search results in new window"""
        try:
            # Create search results window
            results_window = tk.Toplevel(self.root)
            results_window.title(f"Search Results: {search_term}")
            results_window.geometry("800x600")
            results_window.configure(bg=DashboardColors.BG_DARK)
            
            # Title
            tk.Label(
                results_window,
                text=f"Search Results for: '{search_term}' ({len(results)} matches)",
                font=("Arial", 12, "bold"),
                fg=DashboardColors.TEXT_WHITE,
                bg=DashboardColors.BG_DARK
            ).pack(pady=10)
            
            # Results text
            results_text = scrolledtext.ScrolledText(
                results_window,
                bg=DashboardColors.BG_DARK,
                fg=DashboardColors.TEXT_WHITE,
                font=("Consolas", 10),
                wrap=tk.WORD
            )
            results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Add results
            for result in results:
                results_text.insert(tk.END, result + "\n")
            
            # Close button
            tk.Button(
                results_window,
                text="Close",
                font=("Arial", 10),
                bg=DashboardColors.DANGER,
                fg=DashboardColors.TEXT_WHITE,
                command=results_window.destroy
            ).pack(pady=10)
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการแสดงผลการค้นหา: {e}")
    
    def _apply_settings(self):
        """Apply settings changes"""
        try:
            # Update interval
            try:
                new_interval = int(self.update_interval_var.get())
                if 100 <= new_interval <= 10000:  # 100ms to 10s
                    self.update_interval = new_interval
                    self.log_message(f"⚙️ อัพเดท update interval: {new_interval}ms", "INFO")
                else:
                    messagebox.showwarning("Warning", "Update interval must be between 100-10000ms")
                    return
            except ValueError:
                messagebox.showerror("Error", "Invalid update interval value")
                return
            
            # Auto scroll setting
            self.quick_log_panel.auto_scroll_var.set(self.auto_scroll_setting.get())
            self.full_log_panel.auto_scroll_var.set(self.auto_scroll_setting.get())
            
            self.log_message("✅ การตั้งค่าถูกนำไปใช้แล้ว", "SUCCESS")
            messagebox.showinfo("Settings", "Settings applied successfully!")
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการนำไปใช้การตั้งค่า: {e}")
            messagebox.showerror("Error", f"Failed to apply settings: {e}")
   
    def _show_help(self):
        """Show help dialog"""
        help_text = """
🚀 INTELLIGENT GOLD TRADING SYSTEM - HELP

📊 Dashboard Tab:
- Real-time system overview
- Component status monitoring  
- Performance metrics
- Quick logs

🎮 Controls Tab:
- Start/Stop trading controls
- Component restart buttons
- System controls
- Emergency stop

📈 Performance Tab:
- Detailed performance analysis
- Strategy breakdowns
- Session analysis

📋 Logs Tab:
- Complete system logs
- Search functionality
- Log level filtering

⚙️ Settings Tab:
- GUI preferences
- Trading parameters

🔧 Keyboard Shortcuts:
- F1: Show this help
- F5: Refresh all displays
- Ctrl+S: Export logs
- Ctrl+R: Reset system
- Escape: Emergency stop

⚠️ Important Notes:
- This system trades with REAL MONEY
- Always monitor positions carefully
- Use Emergency Stop if needed
- Recovery system handles losses
- No stop losses by design
        """
       
        # Create help window
        help_window = tk.Toplevel(self.root)
        help_window.title("Help - Intelligent Gold Trading System")
        help_window.geometry("600x700")
        help_window.configure(bg=DashboardColors.BG_DARK)
        
        # Help text
        help_display = scrolledtext.ScrolledText(
            help_window,
            bg=DashboardColors.BG_DARK,
            fg=DashboardColors.TEXT_WHITE,
            font=("Consolas", 10),
            wrap=tk.WORD
        )
        help_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        help_display.insert(tk.END, help_text)
        help_display.config(state=tk.DISABLED)
        
        # Close button
        tk.Button(
            help_window,
            text="Close",
            font=("Arial", 10),
            bg=DashboardColors.INFO,
            fg=DashboardColors.TEXT_WHITE,
            command=help_window.destroy
        ).pack(pady=10)
    
    def _refresh_all(self):
        """Refresh all displays"""
        try:
            self.log_message("🔄 รีเฟรชหน้าจอทั้งหมด...", "INFO")
            # Force immediate update
            self._update_gui()
            self.log_message("✅ รีเฟรชเสร็จสิ้น", "SUCCESS")
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการรีเฟรช: {e}")
    
    def _on_closing(self):
        """Handle window closing"""
        try:
            if messagebox.askokcancel("Quit", "Do you want to quit the trading system?"):
                self.log_message("🛑 กำลังปิดระบบ...", "INFO")
                
                # Stop GUI updates
                self.gui_active = False
                
                # Stop trading if active
                if self.trading_system and self.trading_system.is_trading_active():
                    if messagebox.askyesno("Confirm", "Trading is active. Stop trading before closing?"):
                        self.trading_system.stop_trading()
                        time.sleep(2)  # Wait for trading to stop
                
                # Close window
                self.root.quit()
                self.root.destroy()
        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการปิดหน้าต่าง: {e}")
            self.root.quit()
            self.root.destroy()
    
    # Public Methods
    def log_message(self, message: str, level: str = "INFO"):
        """Public method to add log message"""
        try:
            # Add to message queue for processing in GUI thread
            self.message_queue.put({
                'message': message,
                'level': level
            })
            
            # Also log to logger
            if self.logger:
                if level == "ERROR":
                    self.logger.error(message)
                elif level == "WARNING":
                    self.logger.warning(message)
                elif level == "SUCCESS":
                    self.logger.info(message)
                else:
                    self.logger.info(message)
        
        except Exception as e:
            print(f"❌ Error logging message: {e}")
    
    def update_system_reference(self, trading_system):
        """Update trading system reference"""
        self.trading_system = trading_system
        self.log_message("🔗 เชื่อมต่อ Trading System", "SUCCESS")
    
    def run(self):
        """Run the GUI main loop"""
        try:
            self.log_message("🖥️ เริ่มต้นระบบ GUI", "INFO")
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน GUI main loop: {e}")
        finally:
            self.gui_active = False
            self.log_message("🛑 ปิดระบบ GUI", "INFO")

# ===============================
# UTILITY FUNCTIONS
# ===============================

def create_trading_gui(settings=None, logger=None, trading_system=None) -> TradingSystemGUI:
    """Create and return GUI instance"""
    return TradingSystemGUI(settings, logger, trading_system)

def test_gui():
    """Test GUI without trading system"""
    print("🧪 ทดสอบ GUI...")
    
    # Create GUI
    gui = TradingSystemGUI()
    
    # Add some test logs
    gui.log_message("🧪 ทดสอบระบบ GUI", "INFO")
    gui.log_message("⚠️ ข้อความเตือนทดสอบ", "WARNING")
    gui.log_message("❌ ข้อผิดพลาดทดสอบ", "ERROR")
    gui.log_message("✅ ข้อความสำเร็จทดสอบ", "SUCCESS")
    
    # Run GUI
    gui.run()

if __name__ == "__main__":
    test_gui()
    
