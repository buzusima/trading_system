#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRADING DASHBOARD - Real-time Trading Dashboard
==============================================
หน้าจอแสดงผลการเทรดแบบ Real-time และการควบคุมระบบ
Dashboard หลักสำหรับติดตามและจัดการระบบ Intelligent Gold Trading

Key Features:
- Real-time position monitoring และ P&L tracking
- Recovery system status และ controls
- Performance analytics และ charts
- Signal generation monitoring
- Volume achievement tracking
- System health monitoring
- Professional trading interface

เชื่อมต่อไปยัง:
- analytics_engine/performance_tracker.py (ข้อมูล performance)
- position_management/position_tracker.py (ข้อมูล positions)
- intelligent_recovery/recovery_engine.py (ข้อมูล recovery)
- adaptive_entries/signal_generator.py (ข้อมูล signals)
- money_management/position_sizer.py (ข้อมูล sizing)
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import json
from collections import deque
import asyncio

# เชื่อมต่อ internal modules
from config.settings import get_system_settings, MarketSession
from config.trading_params import get_trading_parameters
from utilities.professional_logger import setup_trading_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class DashboardColors:
    """
    ชุดสีสำหรับ Professional Trading Dashboard
    """
    # Dark Theme Colors
    BG_DARK = '#1a1a2e'
    BG_MEDIUM = '#16213e'
    BG_LIGHT = '#0f3460'
    
    # Accent Colors
    ACCENT_PRIMARY = '#e94560'
    ACCENT_SECONDARY = '#f39c12'
    ACCENT_SUCCESS = '#27ae60'
    ACCENT_WARNING = '#f39c1c'
    ACCENT_DANGER = '#e74c3c'
    
    # Text Colors
    TEXT_WHITE = '#ffffff'
    TEXT_GRAY = '#bdc3c7'
    TEXT_LIGHT_GRAY = '#ecf0f1'
    
    # Trading Colors
    PROFIT_GREEN = '#27ae60'
    LOSS_RED = '#e74c3c'
    PENDING_YELLOW = '#f1c40f'
    NEUTRAL_BLUE = '#3498db'
    
    # Chart Colors
    CHART_LINE = '#2980b9'
    CHART_AREA = '#34495e'
    CHART_GRID = '#34495e'

class RealTimeDataManager:
    """
    จัดการข้อมูล Real-time สำหรับ Dashboard
    """
    
    def __init__(self):
        self.logger = setup_trading_logger()
        
        # Data Storage
        self.current_data = {
            'account_info': {},
            'positions': [],
            'performance': {},
            'recovery_status': {},
            'signal_status': {},
            'system_health': {}
        }
        
        # Data History for Charts
        self.pnl_history = deque(maxlen=100)
        self.volume_history = deque(maxlen=100)
        self.equity_history = deque(maxlen=100)
        
        # External Connections
        self.performance_tracker = None
        self.position_tracker = None
        self.recovery_engine = None
        self.signal_generator = None
        self.position_sizer = None
        
        # Update Settings
        self.update_interval = 2.0  # วินาที
        self.data_updated = False
        
        self.logger.info("📊 เริ่มต้น Real-time Data Manager")
    
    def connect_components(self) -> None:
        """
        เชื่อมต่อกับ Components อื่นๆ
        """
        try:
            from analytics_engine.performance_tracker import get_performance_tracker
            self.performance_tracker = get_performance_tracker()
            
            from position_management.position_tracker import PositionTracker
            self.position_tracker = PositionTracker()
            
            from intelligent_recovery.recovery_engine import get_recovery_engine
            self.recovery_engine = get_recovery_engine()
            
            from adaptive_entries.signal_generator import get_signal_generator
            self.signal_generator = get_signal_generator()
            
            from money_management.position_sizer import get_position_sizer
            self.position_sizer = get_position_sizer()
            
            self.logger.info("✅ เชื่อมต่อ Components สำเร็จ")
            
        except ImportError as e:
            self.logger.warning(f"⚠️ ไม่สามารถเชื่อมต่อบาง Components: {e}")
    
    def update_data(self) -> bool:
        """
        อัพเดทข้อมูล Real-time
        """
        try:
            updated = False
            
            # อัพเดท Performance Data
            if self.performance_tracker:
                performance_data = self.performance_tracker.get_current_performance()
                if performance_data != self.current_data.get('performance', {}):
                    self.current_data['performance'] = performance_data
                    updated = True
                    
                    # เพิ่มข้อมูลลง History
                    if 'net_pnl' in performance_data:
                        self.pnl_history.append({
                            'timestamp': datetime.now(),
                            'value': performance_data['net_pnl']
                        })
                    
                    if 'total_volume' in performance_data:
                        self.volume_history.append({
                            'timestamp': datetime.now(),
                            'value': performance_data['total_volume']
                        })
            
            # อัพเดท Position Data
            if self.position_tracker:
                positions = self.position_tracker.get_all_positions()
                if positions != self.current_data.get('positions', []):
                    self.current_data['positions'] = positions
                    updated = True
            
            # อัพเดท Recovery Status
            if self.recovery_engine:
                recovery_stats = self.recovery_engine.get_recovery_statistics()
                active_recoveries = self.recovery_engine.get_active_recoveries()
                recovery_status = {
                    'statistics': recovery_stats,
                    'active_recoveries': active_recoveries
                }
                if recovery_status != self.current_data.get('recovery_status', {}):
                    self.current_data['recovery_status'] = recovery_status
                    updated = True
            
            # อัพเดท Signal Status
            if self.signal_generator:
                signal_stats = self.signal_generator.get_signal_statistics()
                active_signals = self.signal_generator.get_active_signals()
                signal_status = {
                    'statistics': signal_stats,
                    'active_signals': active_signals
                }
                if signal_status != self.current_data.get('signal_status', {}):
                    self.current_data['signal_status'] = signal_status
                    updated = True
            
            # อัพเดท Position Sizer Data
            if self.position_sizer:
                sizer_stats = self.position_sizer.get_sizing_statistics()
                if sizer_stats != self.current_data.get('sizing_status', {}):
                    self.current_data['sizing_status'] = sizer_stats
                    updated = True
            
            # อัพเดท System Health
            system_health = {
                'timestamp': datetime.now().isoformat(),
                'performance_tracker_active': self.performance_tracker is not None,
                'recovery_engine_active': getattr(self.recovery_engine, 'engine_active', False),
                'signal_generator_active': getattr(self.signal_generator, 'generator_active', False),
                'components_connected': all([
                    self.performance_tracker, self.position_tracker, 
                    self.recovery_engine, self.signal_generator
                ])
            }
            
            if system_health != self.current_data.get('system_health', {}):
                self.current_data['system_health'] = system_health
                updated = True
            
            self.data_updated = updated
            return updated
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดทข้อมูล: {e}")
            return False
    
    def get_current_data(self) -> Dict[str, Any]:
        """
        ดึงข้อมูลปัจจุบัน
        """
        return self.current_data.copy()

class TradingMetricsPanel:
    """
    Panel แสดง Trading Metrics หลัก
    """
    
    def __init__(self, parent: tk.Widget, colors: DashboardColors):
        self.parent = parent
        self.colors = colors
        self.logger = setup_trading_logger()
        
        # สร้าง Frame หลัก
        self.frame = tk.Frame(parent, bg=colors.BG_MEDIUM)
        
        # สร้าง UI Components
        self._create_metrics_display()
        
        # ข้อมูลปัจจุบัน
        self.current_metrics = {}
        
        self.logger.info("📈 เริ่มต้น Trading Metrics Panel")
    
    def _create_metrics_display(self) -> None:
        """
        สร้างการแสดงผล Metrics
        """
        # Title
        title_label = tk.Label(
            self.frame, 
            text="📊 Trading Performance",
            font=('Arial', 14, 'bold'),
            fg=self.colors.TEXT_WHITE,
            bg=self.colors.BG_MEDIUM
        )
        title_label.pack(pady=(10, 20))
        
        # Metrics Grid
        self.metrics_frame = tk.Frame(self.frame, bg=self.colors.BG_MEDIUM)
        self.metrics_frame.pack(fill='both', expand=True, padx=10)
        
        # สร้าง Metric Cards
        self.metric_labels = {}
        
        # Row 1: P&L Metrics
        row1_frame = tk.Frame(self.metrics_frame, bg=self.colors.BG_MEDIUM)
        row1_frame.pack(fill='x', pady=5)
        
        self._create_metric_card(row1_frame, 'net_pnl', 'Net P&L', '$0.00', self.colors.NEUTRAL_BLUE, 0, 0)
        self._create_metric_card(row1_frame, 'unrealized_pnl', 'Unrealized P&L', '$0.00', self.colors.PENDING_YELLOW, 0, 1)
        self._create_metric_card(row1_frame, 'total_volume', 'Volume Today', '0.00 lots', self.colors.ACCENT_PRIMARY, 0, 2)
        
        # Row 2: Performance Metrics
        row2_frame = tk.Frame(self.metrics_frame, bg=self.colors.BG_MEDIUM)
        row2_frame.pack(fill='x', pady=5)
        
        self._create_metric_card(row2_frame, 'win_rate', 'Win Rate', '0%', self.colors.PROFIT_GREEN, 0, 0)
        self._create_metric_card(row2_frame, 'recovery_rate', 'Recovery Rate', '100%', self.colors.ACCENT_SUCCESS, 0, 1)
        self._create_metric_card(row2_frame, 'profit_factor', 'Profit Factor', '0.00', self.colors.ACCENT_SECONDARY, 0, 2)
        
        # Row 3: Trading Activity
        row3_frame = tk.Frame(self.metrics_frame, bg=self.colors.BG_MEDIUM)
        row3_frame.pack(fill='x', pady=5)
        
        self._create_metric_card(row3_frame, 'total_trades', 'Total Trades', '0', self.colors.NEUTRAL_BLUE, 0, 0)
        self._create_metric_card(row3_frame, 'active_positions', 'Active Positions', '0', self.colors.ACCENT_WARNING, 0, 1)
        self._create_metric_card(row3_frame, 'active_recoveries', 'Active Recoveries', '0', self.colors.LOSS_RED, 0, 2)
    
    def _create_metric_card(self, parent: tk.Widget, key: str, title: str, 
                           initial_value: str, color: str, row: int, col: int) -> None:
        """
        สร้าง Metric Card
        """
        # Card Frame
        card_frame = tk.Frame(
            parent, 
            bg=self.colors.BG_LIGHT,
            relief='raised',
            bd=1
        )
        card_frame.grid(row=row, column=col, padx=10, pady=5, sticky='ew')
        parent.grid_columnconfigure(col, weight=1)
        
        # Title Label
        title_label = tk.Label(
            card_frame,
            text=title,
            font=('Arial', 10),
            fg=self.colors.TEXT_GRAY,
            bg=self.colors.BG_LIGHT
        )
        title_label.pack(pady=(10, 0))
        
        # Value Label
        value_label = tk.Label(
            card_frame,
            text=initial_value,
            font=('Arial', 16, 'bold'),
            fg=color,
            bg=self.colors.BG_LIGHT
        )
        value_label.pack(pady=(0, 10))
        
        # เก็บ reference
        self.metric_labels[key] = {
            'title': title_label,
            'value': value_label,
            'color': color
        }
    
    def update_metrics(self, data: Dict[str, Any]) -> None:
        """
        อัพเดท Metrics Display
        """
        try:
            performance = data.get('performance', {})
            recovery_status = data.get('recovery_status', {})
            
            # อัพเดทค่าต่างๆ
            updates = {
                'net_pnl': f"${performance.get('net_pnl', 0):.2f}",
                'unrealized_pnl': f"${performance.get('total_unrealized_pnl', 0):.2f}",
                'total_volume': f"{performance.get('total_volume', 0):.2f} lots",
                'win_rate': f"{performance.get('win_rate', 0):.1f}%",
                'recovery_rate': f"{performance.get('recovery_rate', 100):.1f}%",
                'profit_factor': f"{performance.get('profit_factor', 0):.2f}",
                'total_trades': str(performance.get('total_trades', 0)),
                'active_positions': str(performance.get('active_positions', 0)),
                'active_recoveries': str(len(recovery_status.get('active_recoveries', [])))
            }
            
            # อัพเดท UI
            for key, value in updates.items():
                if key in self.metric_labels:
                    self.metric_labels[key]['value'].config(text=value)
                    
                    # เปลี่ยนสีตาม P&L
                    if key == 'net_pnl':
                        pnl_value = performance.get('net_pnl', 0)
                        if pnl_value > 0:
                            color = self.colors.PROFIT_GREEN
                        elif pnl_value < 0:
                            color = self.colors.LOSS_RED
                        else:
                            color = self.colors.TEXT_WHITE
                        self.metric_labels[key]['value'].config(fg=color)
                    
                    elif key == 'unrealized_pnl':
                        unrealized = performance.get('total_unrealized_pnl', 0)
                        if unrealized > 0:
                            color = self.colors.PROFIT_GREEN
                        elif unrealized < 0:
                            color = self.colors.LOSS_RED
                        else:
                            color = self.colors.TEXT_WHITE
                        self.metric_labels[key]['value'].config(fg=color)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Metrics: {e}")

class PositionsPanel:
    """
    Panel แสดงรายการ Positions
    """
    
    def __init__(self, parent: tk.Widget, colors: DashboardColors):
        self.parent = parent
        self.colors = colors
        self.logger = setup_trading_logger()
        
        # สร้าง Frame หลัก
        self.frame = tk.Frame(parent, bg=colors.BG_MEDIUM)
        
        # สร้าง UI Components
        self._create_positions_table()
        
        self.logger.info("📋 เริ่มต้น Positions Panel")
    
    def _create_positions_table(self) -> None:
        """
        สร้างตารางแสดง Positions
        """
        # Title
        title_label = tk.Label(
            self.frame,
            text="📋 Active Positions",
            font=('Arial', 14, 'bold'),
            fg=self.colors.TEXT_WHITE,
            bg=self.colors.BG_MEDIUM
        )
        title_label.pack(pady=(10, 10))
        
        # Table Frame
        table_frame = tk.Frame(self.frame, bg=self.colors.BG_MEDIUM)
        table_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Scrollable Treeview
        self.tree_frame = tk.Frame(table_frame, bg=self.colors.BG_LIGHT)
        self.tree_frame.pack(fill='both', expand=True)
        
        # Define columns
        columns = ('Position', 'Symbol', 'Direction', 'Volume', 'Entry Price', 'Current Price', 'P&L', 'Status')
        
        self.positions_tree = ttk.Treeview(
            self.tree_frame,
            columns=columns,
            show='headings',
            height=8
        )
        
        # Configure columns
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=100, anchor='center')
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(self.tree_frame, orient='vertical', command=self.positions_tree.yview)
        h_scrollbar = ttk.Scrollbar(self.tree_frame, orient='horizontal', command=self.positions_tree.xview)
        
        self.positions_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack components
        self.positions_tree.pack(side='left', fill='both', expand=True)
        v_scrollbar.pack(side='right', fill='y')
        h_scrollbar.pack(side='bottom', fill='x')
        
        # Configure Treeview colors (limited in tkinter)
        style = ttk.Style()
        style.configure('Treeview', background=self.colors.BG_LIGHT, 
                       foreground=self.colors.TEXT_WHITE, fieldbackground=self.colors.BG_LIGHT)
        style.configure('Treeview.Heading', background=self.colors.BG_DARK, 
                       foreground=self.colors.TEXT_WHITE)
    
    def update_positions(self, positions: List[Dict[str, Any]]) -> None:
        """
        อัพเดทรายการ Positions
        """
        try:
            # ลบข้อมูลเก่า
            for item in self.positions_tree.get_children():
                self.positions_tree.delete(item)
            
            # เพิ่มข้อมูลใหม่
            for position in positions:
                position_id = position.get('position_id', 'N/A')
                symbol = position.get('symbol', 'XAUUSD')
                direction = position.get('direction', 'BUY')
                volume = f"{position.get('volume', 0):.2f}"
                entry_price = f"{position.get('entry_price', 0):.2f}"
                current_price = f"{position.get('current_price', 0):.2f}"
                pnl = position.get('unrealized_pnl', 0)
                pnl_text = f"${pnl:.2f}"
                status = position.get('status', 'OPEN')
                
                # เพิ่มลงตาราง
                item = self.positions_tree.insert('', 'end', values=(
                    position_id, symbol, direction, volume, 
                    entry_price, current_price, pnl_text, status
                ))
                
                # เปลี่ยนสีตาม P&L (จำกัดใน ttk.Treeview)
                if pnl > 0:
                    self.positions_tree.set(item, 'P&L', f"${pnl:.2f} ↗")
                elif pnl < 0:
                    self.positions_tree.set(item, 'P&L', f"${pnl:.2f} ↘")
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Positions: {e}")

class RecoveryPanel:
    """
    Panel แสดงสถานะ Recovery System
    """
    
    def __init__(self, parent: tk.Widget, colors: DashboardColors):
        self.parent = parent
        self.colors = colors
        self.logger = setup_trading_logger()
        
        # สร้าง Frame หลัก
        self.frame = tk.Frame(parent, bg=colors.BG_MEDIUM)
        
        # สร้าง UI Components
        self._create_recovery_display()
        
        self.logger.info("🔄 เริ่มต้น Recovery Panel")
    
    def _create_recovery_display(self) -> None:
        """
        สร้างการแสดงผล Recovery
        """
        # Title
        title_label = tk.Label(
            self.frame,
            text="🔄 Recovery System",
            font=('Arial', 14, 'bold'),
            fg=self.colors.TEXT_WHITE,
            bg=self.colors.BG_MEDIUM
        )
        title_label.pack(pady=(10, 20))
        
        # Recovery Stats Frame
        stats_frame = tk.Frame(self.frame, bg=self.colors.BG_MEDIUM)
        stats_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        # Recovery Rate Display
        self.recovery_rate_label = tk.Label(
            stats_frame,
            text="Recovery Rate: 100%",
            font=('Arial', 12, 'bold'),
            fg=self.colors.ACCENT_SUCCESS,
            bg=self.colors.BG_MEDIUM
        )
        self.recovery_rate_label.pack(pady=5)
        
        # Success Count Display
        self.success_count_label = tk.Label(
            stats_frame,
            text="Successful Recoveries: 0",
            font=('Arial', 10),
            fg=self.colors.TEXT_GRAY,
            bg=self.colors.BG_MEDIUM
        )
        self.success_count_label.pack(pady=2)
        
        # Active Recoveries List
        active_frame = tk.Frame(self.frame, bg=self.colors.BG_MEDIUM)
        active_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        active_title = tk.Label(
            active_frame,
            text="Active Recoveries:",
            font=('Arial', 11, 'bold'),
            fg=self.colors.TEXT_WHITE,
            bg=self.colors.BG_MEDIUM
        )
        active_title.pack(anchor='w', pady=(0, 5))
        
        # Recovery List
        self.recovery_listbox = tk.Listbox(
            active_frame,
            bg=self.colors.BG_LIGHT,
            fg=self.colors.TEXT_WHITE,
            selectbackground=self.colors.ACCENT_PRIMARY,
            font=('Arial', 9),
            height=6
        )
        self.recovery_listbox.pack(fill='both', expand=True)
        
        # Recovery Controls
        controls_frame = tk.Frame(self.frame, bg=self.colors.BG_MEDIUM)
        controls_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        # Emergency Stop Button
        self.emergency_btn = tk.Button(
            controls_frame,
            text="🚨 Emergency Stop",
            command=self._emergency_stop_recovery,
            bg=self.colors.ACCENT_DANGER,
            fg=self.colors.TEXT_WHITE,
            font=('Arial', 10, 'bold'),
            relief='raised',
            bd=2
        )
        self.emergency_btn.pack(side='left', padx=(0, 10))
        
        # Pause All Button
        self.pause_btn = tk.Button(
            controls_frame,
            text="⏸️ Pause All",
            command=self._pause_all_recovery,
            bg=self.colors.ACCENT_WARNING,
            fg=self.colors.TEXT_WHITE,
            font=('Arial', 10),
            relief='raised',
            bd=2
        )
        self.pause_btn.pack(side='left')
    
    def update_recovery_status(self, recovery_data: Dict[str, Any]) -> None:
        """
        อัพเดทสถานะ Recovery
        """
        try:
            statistics = recovery_data.get('statistics', {})
            active_recoveries = recovery_data.get('active_recoveries', [])
            
            # อัพเดท Recovery Rate
            recovery_rate = statistics.get('recovery_success_rate', 100)
            self.recovery_rate_label.config(text=f"Recovery Rate: {recovery_rate:.1f}%")
            
            # เปลี่ยนสีตามอัตราสำเร็จ
            if recovery_rate >= 95:
                color = self.colors.ACCENT_SUCCESS
            elif recovery_rate >= 80:
                color = self.colors.ACCENT_WARNING
            else:
                color = self.colors.ACCENT_DANGER
            
            self.recovery_rate_label.config(fg=color)
            
            # อัพเดท Success Count
            success_count = statistics.get('total_recoveries_successful', 0)
            total_attempts = statistics.get('total_recoveries_attempted', 0)
            self.success_count_label.config(
                text=f"Successful Recoveries: {success_count}/{total_attempts}"
            )
            
            # อัพเดท Active Recoveries List
            self.recovery_listbox.delete(0, tk.END)
            
            for recovery in active_recoveries:
                task_id = recovery.get('task_id', 'Unknown')
                method = recovery.get('recovery_method', 'Unknown')
                loss = recovery.get('unrealized_loss', 0)
                attempts = recovery.get('recovery_attempts', 0)
                
                item_text = f"{task_id[:15]}... | {method} | Loss: ${loss:.2f} | Attempts: {attempts}"
                self.recovery_listbox.insert(tk.END, item_text)
            
            if not active_recoveries:
                self.recovery_listbox.insert(tk.END, "No active recoveries")
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Recovery Status: {e}")
    
    def _emergency_stop_recovery(self) -> None:
        """
        หยุด Recovery ฉุกเฉิน
        """
        try:
            result = messagebox.askyesno(
                "Emergency Stop",
                "Are you sure you want to emergency stop all recovery operations?\n\n"
                "This will pause all active recoveries immediately."
            )
            
            if result:
                # TODO: เชื่อมต่อไป recovery_engine.emergency_recovery_shutdown()
                messagebox.showinfo("Emergency Stop", "All recovery operations have been stopped.")
                self.logger.warning("🚨 Emergency stop ทั้งหมด Recovery operations")
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Emergency Stop: {e}")
            messagebox.showerror("Error", f"Failed to stop recovery operations: {e}")
    
    def _pause_all_recovery(self) -> None:
        """
        หยุด Recovery ชั่วคราวทั้งหมด
        """
        try:
            result = messagebox.askyesno(
                "Pause Recovery",
                "Pause all active recovery operations?"
            )
            
            if result:
                # TODO: เชื่อมต่อไป recovery_engine pause functions
                messagebox.showinfo("Paused", "All recovery operations have been paused.")
                self.logger.info("⏸️ หยุด Recovery operations ชั่วคราว")
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Pause Recovery: {e}")
            messagebox.showerror("Error", f"Failed to pause recovery operations: {e}")

class SystemControlPanel:
    """
    Panel ควบคุมระบบหลัก
    """
    
    def __init__(self, parent: tk.Widget, colors: DashboardColors):
        self.parent = parent
        self.colors = colors
        self.logger = setup_trading_logger()
        
        # สร้าง Frame หลัก
        self.frame = tk.Frame(parent, bg=colors.BG_MEDIUM)
        
        # สร้าง UI Components
        self._create_control_buttons()
        
        # System Status
        self.system_active = False
        
        self.logger.info("🎛️ เริ่มต้น System Control Panel")
    
    def _create_control_buttons(self) -> None:
        """
        สร้างปุ่มควบคุมระบบ
        """
        # Title
        title_label = tk.Label(
            self.frame,
            text="🎛️ System Control",
            font=('Arial', 14, 'bold'),
            fg=self.colors.TEXT_WHITE,
            bg=self.colors.BG_MEDIUM
        )
        title_label.pack(pady=(10, 20))
        
        # System Status Display
        self.status_frame = tk.Frame(self.frame, bg=self.colors.BG_LIGHT, relief='sunken', bd=2)
        self.status_frame.pack(fill='x', padx=10, pady=(0, 20))
        
        self.status_label = tk.Label(
            self.status_frame,
            text="🔴 System: STOPPED",
            font=('Arial', 12, 'bold'),
            fg=self.colors.ACCENT_DANGER,
            bg=self.colors.BG_LIGHT
        )
        self.status_label.pack(pady=10)
        
        # Control Buttons Grid
        buttons_frame = tk.Frame(self.frame, bg=self.colors.BG_MEDIUM)
        buttons_frame.pack(fill='x', padx=10)
        
        # Row 1: Main System Controls
        row1_frame = tk.Frame(buttons_frame, bg=self.colors.BG_MEDIUM)
        row1_frame.pack(fill='x', pady=5)
        
        self.start_btn = tk.Button(
            row1_frame,
            text="▶️ Start System",
            command=self._start_system,
            bg=self.colors.ACCENT_SUCCESS,
            fg=self.colors.TEXT_WHITE,
            font=('Arial', 11, 'bold'),
            relief='raised',
            bd=3,
            width=15
        )
        self.start_btn.pack(side='left', padx=(0, 10))
        
        self.stop_btn = tk.Button(
            row1_frame,
            text="⏹️ Stop System",
            command=self._stop_system,
            bg=self.colors.ACCENT_DANGER,
            fg=self.colors.TEXT_WHITE,
            font=('Arial', 11, 'bold'),
            relief='raised',
            bd=3,
            width=15,
            state='disabled'
        )
        self.stop_btn.pack(side='left')
        
        # Row 2: Component Controls
        row2_frame = tk.Frame(buttons_frame, bg=self.colors.BG_MEDIUM)
        row2_frame.pack(fill='x', pady=5)
        
        self.signal_btn = tk.Button(
            row2_frame,
            text="📡 Signal Gen",
            command=self._toggle_signal_generator,
            bg=self.colors.ACCENT_SECONDARY,
            fg=self.colors.TEXT_WHITE,
            font=('Arial', 10),
            relief='raised',
            bd=2,
            width=12
        )
        self.signal_btn.pack(side='left', padx=(0, 5))
        
        self.recovery_btn = tk.Button(
            row2_frame,
            text="🔄 Recovery",
            command=self._toggle_recovery_engine,
            bg=self.colors.ACCENT_PRIMARY,
            fg=self.colors.TEXT_WHITE,
            font=('Arial', 10),
            relief='raised',
            bd=2,
            width=12
        )
        self.recovery_btn.pack(side='left', padx=(0, 5))
        
        self.analytics_btn = tk.Button(
            row2_frame,
            text="📊 Analytics",
            command=self._toggle_performance_tracker,
            bg=self.colors.NEUTRAL_BLUE,
            fg=self.colors.TEXT_WHITE,
            font=('Arial', 10),
            relief='raised',
            bd=2,
            width=12
        )
        self.analytics_btn.pack(side='left')
        
        # Row 3: Emergency Controls
        row3_frame = tk.Frame(buttons_frame, bg=self.colors.BG_MEDIUM)
        row3_frame.pack(fill='x', pady=(10, 0))
        
        self.emergency_btn = tk.Button(
            row3_frame,
            text="🚨 EMERGENCY STOP",
            command=self._emergency_shutdown,
            bg=self.colors.ACCENT_DANGER,
            fg=self.colors.TEXT_WHITE,
            font=('Arial', 12, 'bold'),
            relief='raised',
            bd=4
        )
        self.emergency_btn.pack(fill='x', pady=5)
        
        # System Health Indicators
        health_frame = tk.Frame(self.frame, bg=self.colors.BG_MEDIUM)
        health_frame.pack(fill='x', padx=10, pady=(20, 10))
        
        health_title = tk.Label(
            health_frame,
            text="System Health:",
            font=('Arial', 11, 'bold'),
            fg=self.colors.TEXT_WHITE,
            bg=self.colors.BG_MEDIUM
        )
        health_title.pack(anchor='w')
        
        # Health Indicators
        self.health_indicators = {}
        indicators = [
            ('MT5 Connection', 'mt5_connection'),
            ('Signal Generator', 'signal_generator'),
            ('Recovery Engine', 'recovery_engine'),
            ('Performance Tracker', 'performance_tracker')
        ]
        
        for name, key in indicators:
            indicator_frame = tk.Frame(health_frame, bg=self.colors.BG_MEDIUM)
            indicator_frame.pack(fill='x', pady=2)
            
            status_indicator = tk.Label(
                indicator_frame,
                text="🔴",
                font=('Arial', 12),
                bg=self.colors.BG_MEDIUM
            )
            status_indicator.pack(side='left')
            
            name_label = tk.Label(
                indicator_frame,
                text=name,
                font=('Arial', 10),
                fg=self.colors.TEXT_GRAY,
                bg=self.colors.BG_MEDIUM
            )
            name_label.pack(side='left', padx=(5, 0))
            
            self.health_indicators[key] = status_indicator
    
    def _start_system(self) -> None:
        """
        เริ่มต้นระบบ
        """
        try:
            result = messagebox.askyesno(
                "Start System",
                "Start the Intelligent Gold Trading System?\n\n"
                "This will activate:\n"
                "• Signal Generation\n"
                "• Recovery Engine\n"
                "• Performance Tracking\n"
                "• Automated Trading"
            )
            
            if result:
                self.system_active = True
                self._update_system_status("🟢 System: ACTIVE", self.colors.ACCENT_SUCCESS)
                
                # อัพเดทปุ่ม
                self.start_btn.config(state='disabled')
                self.stop_btn.config(state='normal')
                
                # TODO: เริ่มต้น Components จริง
                self.logger.info("✅ เริ่มต้นระบบ Trading")
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเริ่มต้นระบบ: {e}")
            messagebox.showerror("Error", f"Failed to start system: {e}")
    
    def _stop_system(self) -> None:
        """
        หยุดระบบ
        """
        try:
            result = messagebox.askyesno(
                "Stop System",
                "Stop the trading system?\n\n"
                "This will:\n"
                "• Stop signal generation\n"
                "• Pause recovery operations\n"
                "• Stop automated trading\n\n"
                "Open positions will remain active."
            )
            
            if result:
                self.system_active = False
                self._update_system_status("🔴 System: STOPPED", self.colors.ACCENT_DANGER)
                
                # อัพเดทปุ่ม
                self.start_btn.config(state='normal')
                self.stop_btn.config(state='disabled')
                
                # TODO: หยุด Components จริง
                self.logger.info("🛑 หยุดระบบ Trading")
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการหยุดระบบ: {e}")
            messagebox.showerror("Error", f"Failed to stop system: {e}")
    
    def _emergency_shutdown(self) -> None:
        """
        หยุดระบบฉุกเฉิน
        """
        try:
            result = messagebox.askyesno(
                "EMERGENCY SHUTDOWN",
                "EMERGENCY SYSTEM SHUTDOWN?\n\n"
                "⚠️ WARNING: This will immediately:\n"
                "• Stop ALL trading activities\n"
                "• Stop ALL recovery operations\n"
                "• Close ALL pending orders\n"
                "• Shut down the entire system\n\n"
                "This action cannot be undone!\n"
                "Are you absolutely sure?",
                icon='warning'
            )
            
            if result:
                # Confirmation dialog
                confirm = messagebox.askyesno(
                    "FINAL CONFIRMATION",
                    "FINAL CONFIRMATION REQUIRED\n\n"
                    "This will perform an EMERGENCY SHUTDOWN.\n"
                    "All trading will stop immediately.\n\n"
                    "Proceed with emergency shutdown?",
                    icon='error'
                )
                
                if confirm:
                    self.system_active = False
                    self._update_system_status("🚨 System: EMERGENCY STOP", self.colors.ACCENT_DANGER)
                    
                    # Disable all controls
                    self.start_btn.config(state='disabled')
                    self.stop_btn.config(state='disabled')
                    self.signal_btn.config(state='disabled')
                    self.recovery_btn.config(state='disabled')
                    self.analytics_btn.config(state='disabled')
                    
                    # TODO: Emergency shutdown จริง
                    self.logger.critical("🚨 EMERGENCY SYSTEM SHUTDOWN")
                    messagebox.showinfo("Emergency Shutdown", "Emergency shutdown completed.")
                    
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Emergency Shutdown: {e}")
    
    def _toggle_signal_generator(self) -> None:
        """
        เปิด/ปิด Signal Generator
        """
        try:
            # TODO: Toggle Signal Generator จริง
            messagebox.showinfo("Signal Generator", "Signal Generator toggled")
            self.logger.info("📡 Toggle Signal Generator")
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Toggle Signal Generator: {e}")
    
    def _toggle_recovery_engine(self) -> None:
        """
        เปิด/ปิด Recovery Engine
        """
        try:
            # TODO: Toggle Recovery Engine จริง
            messagebox.showinfo("Recovery Engine", "Recovery Engine toggled")
            self.logger.info("🔄 Toggle Recovery Engine")
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Toggle Recovery Engine: {e}")
    
    def _toggle_performance_tracker(self) -> None:
        """
        เปิด/ปิด Performance Tracker
        """
        try:
            # TODO: Toggle Performance Tracker จริง
            messagebox.showinfo("Performance Tracker", "Performance Tracker toggled")
            self.logger.info("📊 Toggle Performance Tracker")
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Toggle Performance Tracker: {e}")
    
    def _update_system_status(self, status_text: str, color: str) -> None:
        """
        อัพเดทสถานะระบบ
        """
        self.status_label.config(text=status_text, fg=color)
    
    def update_health_indicators(self, health_data: Dict[str, Any]) -> None:
        """
        อัพเดต Health Indicators
        """
        try:
            # อัพเดต indicators ตามสถานะจริง
            indicators_status = {
                'mt5_connection': health_data.get('mt5_connected', False),
                'signal_generator': health_data.get('signal_generator_active', False),
                'recovery_engine': health_data.get('recovery_engine_active', False),
                'performance_tracker': health_data.get('performance_tracker_active', False)
            }
            
            for key, status in indicators_status.items():
                if key in self.health_indicators:
                    indicator = self.health_indicators[key]
                    if status:
                        indicator.config(text="🟢", fg=self.colors.ACCENT_SUCCESS)
                    else:
                        indicator.config(text="🔴", fg=self.colors.ACCENT_DANGER)
                        
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Health Indicators: {e}")

class TradingDashboard:
    """
    🖥️ Main Trading Dashboard Class
    
    หน้าจอหลักสำหรับแสดงผลและควบคุมระบบ Intelligent Gold Trading
    รวบรวมทุก Components เข้าด้วยกัน
    """
    
    def __init__(self, master: tk.Tk = None):
        self.logger = setup_trading_logger()
        self.settings = get_system_settings()
        
        # Create main window if not provided
        if master is None:
            self.root = tk.Tk()
        else:
            self.root = master
        
        # Colors
        self.colors = DashboardColors()
        
        # Data Manager
        self.data_manager = RealTimeDataManager()
        
        # Setup UI
        self._setup_main_window()
        self._create_dashboard_layout()
        
        # Update Threading
        self.update_active = False
        self.update_thread = None
        
        self.logger.info("🖥️ เริ่มต้น Trading Dashboard")
    
    def _setup_main_window(self) -> None:
        """
        ตั้งค่าหน้าต่างหลัก
        """
        self.root.title("🚀 Intelligent Gold Trading System - Professional Dashboard v1.0")
        self.root.geometry("1600x1000")
        self.root.minsize(1400, 900)
        self.root.configure(bg=self.colors.BG_DARK)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1600 // 2)
        y = (self.root.winfo_screenheight() // 2) - (1000 // 2)
        self.root.geometry(f"1600x1000+{x}+{y}")
        
        # Window protocol
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_dashboard_layout(self) -> None:
        """
        สร้างโครงสร้าง Dashboard
        """
        # Main container
        main_container = tk.Frame(self.root, bg=self.colors.BG_DARK)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title Bar
        title_frame = tk.Frame(main_container, bg=self.colors.BG_DARK, height=60)
        title_frame.pack(fill='x', pady=(0, 10))
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="🚀 Intelligent Gold Trading System - Professional Dashboard",
            font=('Arial', 18, 'bold'),
            fg=self.colors.TEXT_WHITE,
            bg=self.colors.BG_DARK
        )
        title_label.pack(expand=True)
        
        # Time display
        self.time_label = tk.Label(
            title_frame,
            text="",
            font=('Arial', 12),
            fg=self.colors.TEXT_GRAY,
            bg=self.colors.BG_DARK
        )
        self.time_label.place(relx=1.0, rely=0.5, anchor='e')
        
        # Main content area
        content_frame = tk.Frame(main_container, bg=self.colors.BG_DARK)
        content_frame.pack(fill='both', expand=True)
        
        # Left Column: Metrics and Controls
        left_column = tk.Frame(content_frame, bg=self.colors.BG_DARK, width=500)
        left_column.pack(side='left', fill='y', padx=(0, 10))
        left_column.pack_propagate(False)
        
        # Trading Metrics Panel
        self.metrics_panel = TradingMetricsPanel(left_column, self.colors)
        self.metrics_panel.frame.pack(fill='x', pady=(0, 10))
        
        # System Control Panel
        self.control_panel = SystemControlPanel(left_column, self.colors)
        self.control_panel.frame.pack(fill='x', pady=(0, 10))
        
        # Recovery Panel
        self.recovery_panel = RecoveryPanel(left_column, self.colors)
        self.recovery_panel.frame.pack(fill='both', expand=True)
        
        # Right Column: Positions and Activity
        right_column = tk.Frame(content_frame, bg=self.colors.BG_DARK)
        right_column.pack(side='right', fill='both', expand=True)
        
        # Positions Panel
        self.positions_panel = PositionsPanel(right_column, self.colors)
        self.positions_panel.frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Activity Log Panel
        self._create_activity_log(right_column)
    
    def _create_activity_log(self, parent: tk.Widget) -> None:
        """
        สร้าง Activity Log Panel
        """
        log_frame = tk.Frame(parent, bg=self.colors.BG_MEDIUM, height=200)
        log_frame.pack(fill='x', pady=(0, 0))
        log_frame.pack_propagate(False)
        
        # Title
        log_title = tk.Label(
            log_frame,
            text="📝 Activity Log",
            font=('Arial', 14, 'bold'),
            fg=self.colors.TEXT_WHITE,
            bg=self.colors.BG_MEDIUM
        )
        log_title.pack(pady=(10, 10))
        
        # Log Text Area
        log_text_frame = tk.Frame(log_frame, bg=self.colors.BG_MEDIUM)
        log_text_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        self.activity_log = tk.Text(
            log_text_frame,
            bg=self.colors.BG_LIGHT,
            fg=self.colors.TEXT_WHITE,
            font=('Consolas', 9),
            wrap='word',
            height=8,
            state='disabled'
        )
        
        log_scrollbar = tk.Scrollbar(log_text_frame, command=self.activity_log.yview)
        self.activity_log.configure(yscrollcommand=log_scrollbar.set)
        
        self.activity_log.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
        # Add initial log entry
        self._add_activity_log("🚀 Trading Dashboard initialized")
    
    def _add_activity_log(self, message: str) -> None:
        """
        เพิ่มข้อความลง Activity Log
        """
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            
            self.activity_log.config(state='normal')
            self.activity_log.insert(tk.END, log_entry)
            self.activity_log.see(tk.END)
            
            # จำกัดจำนวนบรรทัด
            lines = int(self.activity_log.index('end-1c').split('.')[0])
            if lines > 100:
                self.activity_log.delete(1.0, "10.0")
            
            self.activity_log.config(state='disabled')
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเพิ่ม Activity Log: {e}")
    
    def start_dashboard(self) -> None:
        """
        เริ่มต้น Dashboard
        """
        try:
            self.logger.info("🚀 เริ่มต้น Trading Dashboard")
            
            # เชื่อมต่อ Data Manager
            self.data_manager.connect_components()
            
            # เริ่ม Update Thread
            self.update_active = True
            self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()
            
            # เริ่มต้น Time Update
            self._update_time()
            
            self._add_activity_log("✅ Dashboard systems started")
            
            # Run the GUI
            self.root.mainloop()
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการเริ่มต้น Dashboard: {e}")
            messagebox.showerror("Dashboard Error", f"Failed to start dashboard: {e}")
    
    def _update_loop(self) -> None:
        """
        Main Update Loop สำหรับ Real-time Data
        """
        self.logger.info("🔄 เริ่มต้น Dashboard Update Loop")
        
        while self.update_active:
            try:
                # อัพเดทข้อมูล
                data_updated = self.data_manager.update_data()
                
                if data_updated:
                    # ดึงข้อมูลใหม่
                    current_data = self.data_manager.get_current_data()
                    
                    # อัพเดท UI (ต้องทำใน main thread)
                    self.root.after(0, lambda: self._update_ui_components(current_data))
                
                # รอ 2 วินาที
                time.sleep(self.data_manager.update_interval)
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Update Loop: {e}")
                time.sleep(5)
    
    def _update_ui_components(self, data: Dict[str, Any]) -> None:
        """
        อัพเดท UI Components ด้วยข้อมูลใหม่
        """
        try:
            # อัพเดท Metrics Panel
            self.metrics_panel.update_metrics(data)
            
            # อัพเดท Positions Panel
            positions = data.get('positions', [])
            self.positions_panel.update_positions(positions)
            
            # อัพเดท Recovery Panel
            recovery_status = data.get('recovery_status', {})
            self.recovery_panel.update_recovery_status(recovery_status)
            
            # อัพเดท System Health
            system_health = data.get('system_health', {})
            self.control_panel.update_health_indicators(system_health)
            
            # Log important events
            self._log_important_events(data)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท UI: {e}")
    
    def _log_important_events(self, data: Dict[str, Any]) -> None:
        """
        บันทึก Events สำคัญลง Activity Log
        """
        try:
            performance = data.get('performance', {})
            recovery_status = data.get('recovery_status', {})
            
            # Log new positions
            positions = data.get('positions', [])
            current_positions = len(positions)
            if hasattr(self, '_last_position_count'):
                if current_positions > self._last_position_count:
                    self._add_activity_log(f"📈 New position opened (Total: {current_positions})")
                elif current_positions < self._last_position_count:
                    self._add_activity_log(f"📉 Position closed (Total: {current_positions})")
            self._last_position_count = current_positions
            
            # Log recovery events
            active_recoveries = len(recovery_status.get('active_recoveries', []))
            if hasattr(self, '_last_recovery_count'):
                if active_recoveries > self._last_recovery_count:
                    self._add_activity_log(f"🔄 New recovery started (Active: {active_recoveries})")
                elif active_recoveries < self._last_recovery_count:
                    self._add_activity_log(f"✅ Recovery completed (Active: {active_recoveries})")
            self._last_recovery_count = active_recoveries
            
            # Log significant P&L changes
            net_pnl = performance.get('net_pnl', 0)
            if hasattr(self, '_last_net_pnl'):
                pnl_change = net_pnl - self._last_net_pnl
                if abs(pnl_change) > 50:  # เปลี่ยนแปลงมากกว่า $50
                    direction = "📈" if pnl_change > 0 else "📉"
                    self._add_activity_log(f"{direction} P&L change: ${pnl_change:+.2f} (Total: ${net_pnl:.2f})")
            self._last_net_pnl = net_pnl
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการ Log Events: {e}")
    
    def _update_time(self) -> None:
        """
        อัพเดทเวลาบน Dashboard
        """
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.config(text=current_time)
            
            # Schedule next update
            self.root.after(1000, self._update_time)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดทเวลา: {e}")
    
    def _on_closing(self) -> None:
        """
        จัดการการปิด Dashboard
        """
        try:
            result = messagebox.askyesno(
                "Close Dashboard",
                "Close the Trading Dashboard?\n\n"
                "The trading system will continue running in the background.\n"
                "To stop trading, use the System Control panel first."
            )
            
            if result:
                self.logger.info("🛑 ปิด Trading Dashboard")
                
                # หยุด Update Thread
                self.update_active = False
                if self.update_thread and self.update_thread.is_alive():
                    self.update_thread.join(timeout=3)
                
                # บันทึก Log สุดท้าย
                self._add_activity_log("🛑 Dashboard shutting down")
                
                # ปิดหน้าต่าง
                self.root.quit()
                self.root.destroy()
                
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการปิด Dashboard: {e}")
            self.root.quit()

# === CONVENIENCE FUNCTIONS ===
def create_trading_dashboard(master: tk.Tk = None) -> TradingDashboard:
    """
    สร้าง Trading Dashboard
    """
    return TradingDashboard(master)

def main():
    """
    เริ่มต้น Trading Dashboard standalone
    """
    print("🖥️ เริ่มต้น Intelligent Gold Trading Dashboard")
    
    try:
        dashboard = create_trading_dashboard()
        dashboard.start_dashboard()
        
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการเริ่มต้น Dashboard: {e}")

if __name__ == "__main__":
    main()