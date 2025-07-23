#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RECOVERY PANEL - Advanced Recovery Control Panel
==============================================
Panel สำหรับควบคุมและติดตามระบบ Recovery แบบขั้นสูง
พร้อมการจัดการและวิเคราะห์ Recovery Strategy ที่ครอบคลุม

Key Features:
- Recovery strategy selector with visual previews
- Real-time recovery progress monitoring
- Manual recovery intervention controls
- Recovery performance analytics and charts
- Emergency recovery controls
- Integration with recovery_engine และ strategies
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
import json
from collections import deque, defaultdict
import queue
from decimal import Decimal, ROUND_HALF_UP

# เชื่อมต่อ internal modules
from config.settings import get_system_settings
from config.trading_params import get_trading_parameters
from utilities.professional_logger import setup_component_logger
from utilities.error_handler import handle_trading_errors, ErrorCategory, ErrorSeverity

class RecoveryColors:
    """ชุดสีสำหรับ Recovery Panel"""
    BG_DARK = '#1a1a2e'
    BG_MEDIUM = '#16213e'
    BG_LIGHT = '#0f3460'
    
    # Recovery Status Colors
    RECOVERY_ACTIVE = '#e67e22'
    RECOVERY_SUCCESS = '#27ae60'
    RECOVERY_FAILED = '#e74c3c'
    RECOVERY_PENDING = '#f39c12'
    RECOVERY_PAUSED = '#95a5a6'
    
    # Strategy Colors
    MARTINGALE_COLOR = '#3498db'
    GRID_COLOR = '#9b59b6'
    HEDGING_COLOR = '#1abc9c'
    AVERAGING_COLOR = '#f39c12'
    CORRELATION_COLOR = '#e91e63'
    
    # Text Colors
    TEXT_WHITE = '#ffffff'
    TEXT_GRAY = '#bdc3c7'
    TEXT_LIGHT = '#ecf0f1'
    
    # Alert Colors
    ALERT_SUCCESS = '#27ae60'
    ALERT_WARNING = '#f39c12'
    ALERT_DANGER = '#e74c3c'

class RecoveryStrategy:
    """คลาสสำหรับเก็บข้อมูล Recovery Strategy"""
    
    def __init__(self, strategy_dict: Dict[str, Any]):
        self.name = strategy_dict.get('name', 'Unknown')
        self.description = strategy_dict.get('description', '')
        self.success_rate = strategy_dict.get('success_rate', 0.0)
        self.avg_recovery_time = strategy_dict.get('avg_recovery_time', 0)
        self.max_drawdown = strategy_dict.get('max_drawdown', 0.0)
        self.recommended_market = strategy_dict.get('recommended_market', 'All')
        self.risk_level = strategy_dict.get('risk_level', 'Medium')
        self.parameters = strategy_dict.get('parameters', {})
        self.is_active = strategy_dict.get('is_active', False)
        self.color = strategy_dict.get('color', RecoveryColors.BG_LIGHT)

class RecoverySession:
    """คลาสสำหรับเก็บข้อมูล Recovery Session"""
    
    def __init__(self, session_dict: Dict[str, Any]):
        self.session_id = session_dict.get('session_id', '')
        self.position_ticket = session_dict.get('position_ticket', 0)
        self.strategy_name = session_dict.get('strategy_name', '')
        self.start_time = session_dict.get('start_time', datetime.now())
        self.status = session_dict.get('status', 'PENDING')
        self.current_level = session_dict.get('current_level', 0)
        self.max_level = session_dict.get('max_level', 10)
        self.total_volume = session_dict.get('total_volume', 0.0)
        self.unrealized_pnl = session_dict.get('unrealized_pnl', 0.0)
        self.recovery_orders = session_dict.get('recovery_orders', [])
        
    @property
    def progress_percentage(self) -> float:
        """คำนวณ Progress เป็น Percentage"""
        if self.max_level == 0:
            return 0.0
        return min((self.current_level / self.max_level) * 100, 100.0)
    
    @property
    def status_color(self) -> str:
        """สีตามสถานะ Recovery"""
        status_colors = {
            'PENDING': RecoveryColors.RECOVERY_PENDING,
            'ACTIVE': RecoveryColors.RECOVERY_ACTIVE,
            'SUCCESS': RecoveryColors.RECOVERY_SUCCESS,
            'FAILED': RecoveryColors.RECOVERY_FAILED,
            'PAUSED': RecoveryColors.RECOVERY_PAUSED
        }
        return status_colors.get(self.status, RecoveryColors.TEXT_GRAY)

class RecoveryControlPanel:
    """🎛️ Main Recovery Control Panel"""
    
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.logger = setup_component_logger("RecoveryPanel")
        self.colors = RecoveryColors()
        
        # Settings
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Data
        self.available_strategies = []
        self.active_sessions = []
        self.selected_strategy = None
        
        # Data Update Threading
        self.update_active = False
        self.update_thread = None
        self.data_queue = queue.Queue()
        
        # Create main frame
        self.main_frame = tk.Frame(parent, bg=self.colors.BG_DARK)
        self.main_frame.pack(fill='both', expand=True)
        
        # Create UI components
        self._create_header_panel()
        self._create_strategy_selector()
        self._create_active_sessions_panel()
        self._create_control_buttons()
        
        # Load initial data
        self._load_recovery_strategies()
        self.start_real_time_updates()
        
        self.logger.info("🔄 เริ่มต้น Recovery Control Panel")
    
    def _create_header_panel(self) -> None:
        """สร้าง Header Panel"""
        header_frame = tk.Frame(self.main_frame, bg=self.colors.BG_MEDIUM, height=80)
        header_frame.pack(fill='x', padx=10, pady=(10, 5))
        header_frame.pack_propagate(False)
        
        # Title and Status
        title_frame = tk.Frame(header_frame, bg=self.colors.BG_MEDIUM)
        title_frame.pack(side='left', fill='y')
        
        tk.Label(
            title_frame, text="🔄 Recovery Control Center", 
            font=('Segoe UI', 18, 'bold'), fg=self.colors.TEXT_WHITE, bg=self.colors.BG_MEDIUM
        ).pack(anchor='w')
        
        self.status_label = tk.Label(
            title_frame, text="🟢 Recovery system online", 
            font=('Segoe UI', 10), fg=self.colors.RECOVERY_SUCCESS, bg=self.colors.BG_MEDIUM
        )
        self.status_label.pack(anchor='w')
        
        # Recovery Stats
        stats_frame = tk.Frame(header_frame, bg=self.colors.BG_MEDIUM)
        stats_frame.pack(side='right', fill='y', padx=20)
        
        self.recovery_stats = {}
        stat_items = [
            ('active_sessions', 'Active Sessions:', '0'),
            ('success_rate', 'Success Rate:', '0%'),
            ('total_recovered', 'Total Recovered:', '$0.00'),
            ('avg_time', 'Avg Recovery Time:', '0m')
        ]
        
        for i, (key, label, default) in enumerate(stat_items):
            stat_container = tk.Frame(stats_frame, bg=self.colors.BG_MEDIUM)
            stat_container.grid(row=i//2, column=i%2, padx=10, pady=2, sticky='w')
            
            tk.Label(
                stat_container, text=label, font=('Segoe UI', 9),
                fg=self.colors.TEXT_GRAY, bg=self.colors.BG_MEDIUM
            ).pack(side='left')
            
            self.recovery_stats[key] = tk.Label(
                stat_container, text=default, font=('Segoe UI', 9, 'bold'),
                fg=self.colors.TEXT_WHITE, bg=self.colors.BG_MEDIUM
            )
            self.recovery_stats[key].pack(side='left', padx=(5, 0))
    
    def _create_strategy_selector(self) -> None:
        """สร้าง Strategy Selector Panel"""
        strategy_frame = tk.LabelFrame(
            self.main_frame, text="📋 Recovery Strategies", 
            font=('Segoe UI', 12, 'bold'), fg=self.colors.TEXT_WHITE, 
            bg=self.colors.BG_MEDIUM, bd=2, relief='raised'
        )
        strategy_frame.pack(fill='x', padx=10, pady=5)
        
        # Strategy List
        list_frame = tk.Frame(strategy_frame, bg=self.colors.BG_MEDIUM)
        list_frame.pack(fill='x', padx=10, pady=10)
        
        # Treeview for strategies
        columns = ('name', 'success_rate', 'avg_time', 'risk_level', 'market', 'status')
        self.strategy_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=6)
        
        # Configure columns
        column_config = {
            'name': {'width': 150, 'text': 'Strategy Name'},
            'success_rate': {'width': 100, 'text': 'Success Rate'},
            'avg_time': {'width': 100, 'text': 'Avg Time'},
            'risk_level': {'width': 80, 'text': 'Risk Level'},
            'market': {'width': 100, 'text': 'Best Market'},
            'status': {'width': 80, 'text': 'Status'}
        }
        
        for col, config in column_config.items():
            self.strategy_tree.heading(col, text=config['text'])
            self.strategy_tree.column(col, width=config['width'], anchor='center')
        
        # Scrollbar
        strategy_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.strategy_tree.yview)
        self.strategy_tree.configure(yscrollcommand=strategy_scrollbar.set)
        
        self.strategy_tree.pack(side='left', fill='both', expand=True)
        strategy_scrollbar.pack(side='right', fill='y')
        
        # Bind selection event
        self.strategy_tree.bind('<<TreeviewSelect>>', self._on_strategy_select)
        
        # Strategy Details Panel
        details_frame = tk.Frame(strategy_frame, bg=self.colors.BG_LIGHT)
        details_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        self.strategy_details_label = tk.Label(
            details_frame, text="Select a strategy to view details", 
            font=('Segoe UI', 10), fg=self.colors.TEXT_GRAY, bg=self.colors.BG_LIGHT,
            wraplength=800, justify='left'
        )
        self.strategy_details_label.pack(padx=10, pady=10)
    
    def _create_active_sessions_panel(self) -> None:
        """สร้าง Active Sessions Panel"""
        sessions_frame = tk.LabelFrame(
            self.main_frame, text="🔄 Active Recovery Sessions", 
            font=('Segoe UI', 12, 'bold'), fg=self.colors.TEXT_WHITE, 
            bg=self.colors.BG_MEDIUM, bd=2, relief='raised'
        )
        sessions_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Sessions Table
        table_frame = tk.Frame(sessions_frame, bg=self.colors.BG_MEDIUM)
        table_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Treeview for active sessions
        session_columns = (
            'session_id', 'position', 'strategy', 'status', 'level', 
            'progress', 'volume', 'pnl', 'time_elapsed'
        )
        self.sessions_tree = ttk.Treeview(table_frame, columns=session_columns, show='headings', height=8)
        
        # Configure columns
        session_column_config = {
            'session_id': {'width': 100, 'text': 'Session ID'},
            'position': {'width': 100, 'text': 'Position'},
            'strategy': {'width': 120, 'text': 'Strategy'},
            'status': {'width': 80, 'text': 'Status'},
            'level': {'width': 60, 'text': 'Level'},
            'progress': {'width': 80, 'text': 'Progress'},
            'volume': {'width': 80, 'text': 'Volume'},
            'pnl': {'width': 100, 'text': 'P&L'},
            'time_elapsed': {'width': 100, 'text': 'Time Elapsed'}
        }
        
        for col, config in session_column_config.items():
            self.sessions_tree.heading(col, text=config['text'])
            self.sessions_tree.column(col, width=config['width'], anchor='center')
        
        # Scrollbars
        sessions_v_scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.sessions_tree.yview)
        sessions_h_scrollbar = ttk.Scrollbar(table_frame, orient='horizontal', command=self.sessions_tree.xview)
        
        self.sessions_tree.configure(
            yscrollcommand=sessions_v_scrollbar.set, 
            xscrollcommand=sessions_h_scrollbar.set
        )
        
        # Pack sessions tree and scrollbars
        self.sessions_tree.grid(row=0, column=0, sticky='nsew')
        sessions_v_scrollbar.grid(row=0, column=1, sticky='ns')
        sessions_h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Bind events
        self.sessions_tree.bind('<Double-1>', self._on_session_double_click)
        self.sessions_tree.bind('<Button-3>', self._show_session_context_menu)
    
    def _create_control_buttons(self) -> None:
        """สร้าง Control Buttons"""
        control_frame = tk.Frame(self.main_frame, bg=self.colors.BG_MEDIUM, height=80)
        control_frame.pack(fill='x', padx=10, pady=(5, 10))
        control_frame.pack_propagate(False)
        
        # Recovery Actions
        left_controls = tk.Frame(control_frame, bg=self.colors.BG_MEDIUM)
        left_controls.pack(side='left', fill='y', padx=10)
        
        tk.Label(
            left_controls, text="Recovery Actions:", font=('Segoe UI', 10, 'bold'),
            fg=self.colors.TEXT_WHITE, bg=self.colors.BG_MEDIUM
        ).pack(anchor='w')
        
        button_frame = tk.Frame(left_controls, bg=self.colors.BG_MEDIUM)
        button_frame.pack(fill='x', pady=(5, 0))
        
        action_buttons = [
            ("🚀 Start Recovery", self._start_manual_recovery, self.colors.RECOVERY_ACTIVE),
            ("⏸️ Pause All", self._pause_all_recovery, self.colors.RECOVERY_PAUSED),
            ("⏹️ Stop All", self._stop_all_recovery, self.colors.RECOVERY_FAILED),
            ("🔄 Resume All", self._resume_all_recovery, self.colors.RECOVERY_SUCCESS)
        ]
        
        for i, (text, command, color) in enumerate(action_buttons):
            btn = tk.Button(
                button_frame, text=text, font=('Segoe UI', 9),
                bg=color, fg=self.colors.TEXT_WHITE,
                command=command, cursor='hand2', width=15
            )
            btn.grid(row=i//2, column=i%2, padx=5, pady=2, sticky='w')
        
        # Emergency Controls
        right_controls = tk.Frame(control_frame, bg=self.colors.BG_MEDIUM)
        right_controls.pack(side='right', fill='y', padx=10)
        
        tk.Label(
            right_controls, text="Emergency Controls:", font=('Segoe UI', 10, 'bold'),
            fg=self.colors.TEXT_WHITE, bg=self.colors.BG_MEDIUM
        ).pack(anchor='w')
        
        emergency_frame = tk.Frame(right_controls, bg=self.colors.BG_MEDIUM)
        emergency_frame.pack(fill='x', pady=(5, 0))
        
        emergency_buttons = [
            ("🚨 Emergency Stop", self._emergency_stop_all, self.colors.ALERT_DANGER),
            ("🛡️ Force Hedge All", self._force_hedge_all, self.colors.ALERT_WARNING),
            ("💊 Auto Recovery", self._enable_auto_recovery, self.colors.ALERT_SUCCESS)
        ]
        
        for i, (text, command, color) in enumerate(emergency_buttons):
            btn = tk.Button(
                emergency_frame, text=text, font=('Segoe UI', 9),
                bg=color, fg=self.colors.TEXT_WHITE,
                command=command, cursor='hand2', width=15
            )
            btn.grid(row=i//3, column=i%3, padx=5, pady=2, sticky='w')
    
    def _load_recovery_strategies(self) -> None:
        """โหลด Recovery Strategies"""
        try:
            # TODO: เชื่อมต่อกับ Recovery Engine
            # Sample strategies for testing
            sample_strategies = [
                {
                    'name': 'Smart Martingale',
                    'description': 'Adaptive Martingale with market condition analysis',
                    'success_rate': 92.5,
                    'avg_recovery_time': 15,
                    'max_drawdown': 12.3,
                    'recommended_market': 'Ranging',
                    'risk_level': 'Medium',
                    'parameters': {'multiplier': 2.0, 'max_levels': 5},
                    'is_active': True,
                    'color': self.colors.MARTINGALE_COLOR
                },
                {
                    'name': 'Dynamic Grid',
                    'description': 'Intelligent grid trading with trend alignment',
                    'success_rate': 88.7,
                    'avg_recovery_time': 22,
                    'max_drawdown': 8.9,
                    'recommended_market': 'Trending',
                    'risk_level': 'Low',
                    'parameters': {'grid_size': 10, 'max_orders': 8},
                    'is_active': True,
                    'color': self.colors.GRID_COLOR
                },
                {
                    'name': 'Advanced Hedging',
                    'description': 'Smart hedging with correlation analysis',
                    'success_rate': 95.2,
                    'avg_recovery_time': 8,
                    'max_drawdown': 5.4,
                    'recommended_market': 'Volatile',
                    'risk_level': 'High',
                    'parameters': {'hedge_ratio': 0.8, 'correlation_threshold': 0.7},
                    'is_active': False,
                    'color': self.colors.HEDGING_COLOR
                }
            ]
            
            self.available_strategies = [RecoveryStrategy(strategy) for strategy in sample_strategies]
            self._update_strategy_display()
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการโหลด Recovery Strategies: {e}")
    
    def _update_strategy_display(self) -> None:
        """อัพเดทการแสดงผล Strategies"""
        try:
            # Clear existing items
            for item in self.strategy_tree.get_children():
                self.strategy_tree.delete(item)
            
            # Populate strategies
            for strategy in self.available_strategies:
                values = (
                    strategy.name,
                    f"{strategy.success_rate:.1f}%",
                    f"{strategy.avg_recovery_time}m",
                    strategy.risk_level,
                    strategy.recommended_market,
                    "🟢 Active" if strategy.is_active else "🔴 Inactive"
                )
                
                item = self.strategy_tree.insert('', 'end', values=values)
                
                # Color coding
                if strategy.is_active:
                    self.strategy_tree.item(item, tags=('active',))
                else:
                    self.strategy_tree.item(item, tags=('inactive',))
            
            # Configure row colors
            self.strategy_tree.tag_configure('active', background='#1e4d3a', foreground=self.colors.RECOVERY_SUCCESS)
            self.strategy_tree.tag_configure('inactive', background='#4d1e1e', foreground=self.colors.RECOVERY_FAILED)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Strategy Display: {e}")
    
    def start_real_time_updates(self) -> None:
        """เริ่ม Real-time Updates"""
        if not self.update_active:
            self.update_active = True
            self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()
            self.logger.info("🔄 เริ่ม Real-time Recovery Updates")
    
    def _update_loop(self) -> None:
        """Main Update Loop"""
        while self.update_active:
            try:
                # Fetch recovery session data
                session_data = self._fetch_recovery_sessions()
                self.data_queue.put(('sessions', session_data))
                self.main_frame.after_idle(self._process_data_queue)
                
                time.sleep(2)  # Update every 2 seconds
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Recovery Update Loop: {e}")
                time.sleep(1)
    
    def _fetch_recovery_sessions(self) -> List[Dict[str, Any]]:
        """ดึงข้อมูล Recovery Sessions"""
        try:
            # TODO: เชื่อมต่อกับ Recovery Engine
            # Sample data for testing
            return [
                {
                    'session_id': 'REC_001',
                    'position_ticket': 123456789,
                    'strategy_name': 'Smart Martingale',
                    'start_time': datetime.now() - timedelta(minutes=5),
                    'status': 'ACTIVE',
                    'current_level': 2,
                    'max_level': 5,
                    'total_volume': 0.3,
                    'unrealized_pnl': -45.50,
                    'recovery_orders': ['REC_001_1', 'REC_001_2']
                }
            ]
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Recovery Sessions: {e}")
            return []
    
    def _process_data_queue(self) -> None:
        """ประมวลผล Data Queue"""
        try:
            while not self.data_queue.empty():
                data_type, data = self.data_queue.get_nowait()
                if data_type == 'sessions':
                    self._update_sessions_display(data)
        except queue.Empty:
            pass
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการประมวลผล Recovery Data Queue: {e}")
    
    def _update_sessions_display(self, sessions_data: List[Dict[str, Any]]) -> None:
        """อัพเดทการแสดงผล Recovery Sessions"""
        try:
            # Clear existing items
            for item in self.sessions_tree.get_children():
                self.sessions_tree.delete(item)
            
            # Convert to RecoverySession objects
            self.active_sessions = [RecoverySession(session_dict) for session_dict in sessions_data]
            
            # Populate sessions
            for session in self.active_sessions:
                time_elapsed = datetime.now() - session.start_time
                elapsed_str = f"{time_elapsed.total_seconds() // 60:.0f}m"
                
                values = (
                    session.session_id,
                    str(session.position_ticket),
                    session.strategy_name,
                    session.status,
                    f"{session.current_level}/{session.max_level}",
                    f"{session.progress_percentage:.1f}%",
                    f"{session.total_volume:.2f}",
                    f"${session.unrealized_pnl:.2f}",
                    elapsed_str
                )
                
                item = self.sessions_tree.insert('', 'end', values=values)
                
                # Color coding based on status
                status_tag = session.status.lower()
                self.sessions_tree.item(item, tags=(status_tag,))
            
            # Configure status colors
            self.sessions_tree.tag_configure('active', background='#4d3319', foreground=self.colors.RECOVERY_ACTIVE)
            self.sessions_tree.tag_configure('success', background='#1e4d3a', foreground=self.colors.RECOVERY_SUCCESS)
            self.sessions_tree.tag_configure('failed', background='#4d1e1e', foreground=self.colors.RECOVERY_FAILED)
            self.sessions_tree.tag_configure('pending', background='#4d4d1e', foreground=self.colors.RECOVERY_PENDING)
            self.sessions_tree.tag_configure('paused', background='#3a3a3a', foreground=self.colors.RECOVERY_PAUSED)
            
            # Update stats
            self._update_recovery_stats(sessions_data)
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Sessions Display: {e}")
    
    def _update_recovery_stats(self, sessions_data: List[Dict[str, Any]]) -> None:
        """อัพเดท Recovery Statistics"""
        try:
            active_count = len([s for s in sessions_data if s.get('status') == 'ACTIVE'])
            
            # TODO: Calculate real statistics from historical data
            self.recovery_stats['active_sessions'].config(text=str(active_count))
            self.recovery_stats['success_rate'].config(text="92.5%")
            self.recovery_stats['total_recovered'].config(text="$1,250.00")
            self.recovery_stats['avg_time'].config(text="15m")
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Recovery Stats: {e}")
    
    # Event Handlers
    def _on_strategy_select(self, event) -> None:
        """จัดการการเลือก Strategy"""
        selection = self.strategy_tree.selection()
        if selection:
            item = selection[0]
            strategy_name = self.strategy_tree.item(item, 'values')[0]
            
            # Find strategy object
            self.selected_strategy = next(
                (s for s in self.available_strategies if s.name == strategy_name), None
            )
            
            if self.selected_strategy:
                self._update_strategy_details()
    
    def _update_strategy_details(self) -> None:
        """อัพเดทรายละเอียด Strategy"""
        if self.selected_strategy:
            details_text = (
                f"📋 {self.selected_strategy.name}\n\n"
                f"📝 Description: {self.selected_strategy.description}\n"
                f"📊 Success Rate: {self.selected_strategy.success_rate:.1f}%\n"
                f"⏱️ Average Recovery Time: {self.selected_strategy.avg_recovery_time} minutes\n"
                f"📉 Max Drawdown: {self.selected_strategy.max_drawdown:.1f}%\n"
                f"🎯 Recommended Market: {self.selected_strategy.recommended_market}\n"
                f"⚠️ Risk Level: {self.selected_strategy.risk_level}\n"
                f"🔧 Parameters: {json.dumps(self.selected_strategy.parameters, indent=2)}"
            )
            self.strategy_details_label.config(text=details_text)
    
    def _on_session_double_click(self, event) -> None:
        """จัดการ Double Click บน Recovery Session"""
        selection = self.sessions_tree.selection()
        if selection:
            item = selection[0]
            session_id = self.sessions_tree.item(item, 'values')[0]
            messagebox.showinfo("Session Details", f"Recovery session {session_id} details (Feature coming soon)")
    
    def _show_session_context_menu(self, event) -> None:
        """แสดง Context Menu สำหรับ Session"""
        selection = self.sessions_tree.selection()
        if not selection:
            return
        
        context_menu = tk.Menu(self.sessions_tree, tearoff=0, bg=self.colors.BG_DARK, 
                              fg=self.colors.TEXT_WHITE, font=('Segoe UI', 9))
        
        context_menu.add_command(label="⏹️ Stop Session", command=self._stop_selected_session)
        context_menu.add_command(label="🔄 Resume Session", command=self._resume_selected_session)
        context_menu.add_separator()
        context_menu.add_command(label="📈 View Chart", command=self._view_session_chart)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    # Control Methods
    def _start_manual_recovery(self) -> None:
        """เริ่ม Manual Recovery"""
        if not self.selected_strategy:
            messagebox.showwarning("No Strategy", "Please select a recovery strategy first")
            return
        
        if messagebox.askyesno("Confirm Recovery", 
                              f"Start manual recovery using {self.selected_strategy.name}?"):
            try:
                # TODO: เชื่อมต่อกับ Recovery Engine
                self.logger.info(f"🚀 เริ่ม Manual Recovery ด้วย {self.selected_strategy.name}")
                messagebox.showinfo("Success", f"Manual recovery started with {self.selected_strategy.name}")
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดในการเริ่ม Manual Recovery: {e}")
                messagebox.showerror("Error", f"Failed to start recovery: {e}")
    
    def _pause_all_recovery(self) -> None:
        """หยุด Recovery ทั้งหมดชั่วคราว"""
        if messagebox.askyesno("Confirm Pause", "Pause ALL active recovery sessions?"):
            try:
                # TODO: เชื่อมต่อกับ Recovery Engine
                self.logger.warning("⏸️ หยุด Recovery ทั้งหมดชั่วคราว")
                messagebox.showinfo("Success", "All recovery sessions paused")
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดในการหยุด Recovery: {e}")
                messagebox.showerror("Error", f"Failed to pause recovery: {e}")
    
    def _stop_all_recovery(self) -> None:
        """หยุด Recovery ทั้งหมดถาวร"""
        if messagebox.askyesno("Confirm Stop", 
                              "⚠️ STOP ALL recovery sessions? This action cannot be undone!"):
            try:
                # TODO: เชื่อมต่อกับ Recovery Engine
                self.logger.warning("⏹️ หยุด Recovery ทั้งหมดถาวร")
                messagebox.showinfo("Success", "All recovery sessions stopped")
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดในการหยุด Recovery ถาวร: {e}")
                messagebox.showerror("Error", f"Failed to stop recovery: {e}")
    
    def _resume_all_recovery(self) -> None:
        """เริ่ม Recovery ที่หยุดไว้ใหม่"""
        if messagebox.askyesno("Confirm Resume", "Resume ALL paused recovery sessions?"):
            try:
                # TODO: เชื่อมต่อกับ Recovery Engine
                self.logger.info("🔄 เริ่ม Recovery ที่หยุดไว้ใหม่")
                messagebox.showinfo("Success", "All paused recovery sessions resumed")
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดในการเริ่ม Recovery ใหม่: {e}")
                messagebox.showerror("Error", f"Failed to resume recovery: {e}")
    
    def _emergency_stop_all(self) -> None:
        """Emergency Stop ทั้งหมด"""
        if messagebox.askyesno("EMERGENCY STOP", 
                              "🚨 EMERGENCY STOP ALL recovery and trading activities?\n\n"
                              "This will immediately stop:\n"
                              "• All recovery sessions\n"
                              "• All pending orders\n"
                              "• All automated trading\n\n"
                              "This action CANNOT be undone!"):
            try:
                # TODO: เชื่อมต่อกับ Emergency System
                self.logger.critical("🚨 EMERGENCY STOP ALL - ระบบหยุดฉุกเฉิน")
                messagebox.showinfo("EMERGENCY STOP", "🚨 All systems stopped!")
                
                # Update status
                self.status_label.config(
                    text="🚨 EMERGENCY STOP ACTIVATED",
                    fg=self.colors.RECOVERY_FAILED
                )
                
            except Exception as e:
                self.logger.critical(f"💥 ข้อผิดพลาดใน Emergency Stop: {e}")
                messagebox.showerror("CRITICAL ERROR", f"Emergency stop failed: {e}")
    
    def _force_hedge_all(self) -> None:
        """Force Hedge ทั้งหมด"""
        if messagebox.askyesno("Confirm Force Hedge", 
                              "🛡️ Force hedge ALL positions?\n\n"
                              "This will create opposite positions for all active trades."):
            try:
                # TODO: เชื่อมต่อกับ Hedging System
                self.logger.warning("🛡️ Force Hedge ทั้งหมด")
                messagebox.showinfo("Success", "Force hedge applied to all positions")
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Force Hedge: {e}")
                messagebox.showerror("Error", f"Failed to force hedge: {e}")
    
    def _enable_auto_recovery(self) -> None:
        """เปิดใช้ Auto Recovery"""
        if messagebox.askyesno("Confirm Auto Recovery", 
                              "💊 Enable automatic recovery for ALL future losing positions?"):
            try:
                # TODO: เชื่อมต่อกับ Auto Recovery System
                self.logger.info("💊 เปิดใช้ Auto Recovery")
                messagebox.showinfo("Success", "Auto recovery enabled")
                
                # Update status
                self.status_label.config(
                    text="🟢 Auto recovery enabled",
                    fg=self.colors.RECOVERY_SUCCESS
                )
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดในการเปิด Auto Recovery: {e}")
                messagebox.showerror("Error", f"Failed to enable auto recovery: {e}")
    
    # Session Management Methods
    def _view_session_details(self) -> None:
        """ดูรายละเอียด Session ที่เลือก"""
        selection = self.sessions_tree.selection()
        if selection:
            item = selection[0]
            session_id = self.sessions_tree.item(item, 'values')[0]
            messagebox.showinfo("Session Details", f"Session {session_id} details (Feature coming soon)")
    
    def _pause_selected_session(self) -> None:
        """หยุด Session ที่เลือกชั่วคราว"""
        selection = self.sessions_tree.selection()
        if selection:
            item = selection[0]
            session_id = self.sessions_tree.item(item, 'values')[0]
            
            if messagebox.askyesno("Confirm Pause", f"Pause recovery session {session_id}?"):
                try:
                    # TODO: เชื่อมต่อกับ Recovery Engine
                    self.logger.info(f"⏸️ หยุด Recovery Session {session_id}")
                    messagebox.showinfo("Success", f"Session {session_id} paused")
                except Exception as e:
                    self.logger.error(f"❌ ข้อผิดพลาดในการหยุด Session {session_id}: {e}")
                    messagebox.showerror("Error", f"Failed to pause session: {e}")
    
    def _stop_selected_session(self) -> None:
        """หยุด Session ที่เลือกถาวร"""
        selection = self.sessions_tree.selection()
        if selection:
            item = selection[0]
            session_id = self.sessions_tree.item(item, 'values')[0]
            
            if messagebox.askyesno("Confirm Stop", 
                                  f"⚠️ STOP recovery session {session_id}?\n\n"
                                  "This action cannot be undone!"):
                try:
                    # TODO: เชื่อมต่อกับ Recovery Engine
                    self.logger.warning(f"⏹️ หยุด Recovery Session {session_id} ถาวร")
                    messagebox.showinfo("Success", f"Session {session_id} stopped")
                except Exception as e:
                    self.logger.error(f"❌ ข้อผิดพลาดในการหยุด Session {session_id}: {e}")
                    messagebox.showerror("Error", f"Failed to stop session: {e}")
    
    def _resume_selected_session(self) -> None:
        """เริ่ม Session ที่หยุดไว้ใหม่"""
        selection = self.sessions_tree.selection()
        if selection:
            item = selection[0]
            session_id = self.sessions_tree.item(item, 'values')[0]
            
            if messagebox.askyesno("Confirm Resume", f"Resume recovery session {session_id}?"):
                try:
                    # TODO: เชื่อมต่อกับ Recovery Engine
                    self.logger.info(f"🔄 เริ่ม Recovery Session {session_id} ใหม่")
                    messagebox.showinfo("Success", f"Session {session_id} resumed")
                except Exception as e:
                    self.logger.error(f"❌ ข้อผิดพลาดในการเริ่ม Session {session_id} ใหม่: {e}")
                    messagebox.showerror("Error", f"Failed to resume session: {e}")
    
    def _view_session_chart(self) -> None:
        """ดู Chart ของ Session"""
        selection = self.sessions_tree.selection()
        if selection:
            item = selection[0]
            session_id = self.sessions_tree.item(item, 'values')[0]
            messagebox.showinfo("Session Chart", f"Chart for session {session_id} (Feature coming soon)")
    
    def cleanup(self) -> None:
        """ทำความสะอาดเมื่อปิด Panel"""
        self.update_active = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1)
        self.logger.info("🧹 ทำความสะอาด Recovery Control Panel")


# Test Function
def demo_recovery_panel():
    """Demo function สำหรับทดสอบ Recovery Panel"""
    root = tk.Tk()
    root.title("Recovery Panel Demo")
    root.geometry("1400x900")
    root.configure(bg='#1a1a2e')
    
    panel = RecoveryControlPanel(root)
    
    def on_closing():
        panel.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    demo_recovery_panel()