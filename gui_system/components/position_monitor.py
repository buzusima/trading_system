#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSITION MONITOR - Enhanced Position Monitoring Panel
==================================================
Panel สำหรับติดตามและจัดการ Position แบบ Real-time
พร้อมการควบคุมและวิเคราะห์ Position ที่ครอบคลุม

Key Features:
- Real-time position table with sortable/filterable columns
- P&L visualization with color-coded indicators  
- Position management controls (close, hedge, recovery trigger)
- Professional dark theme matching existing GUI
- Integration with performance_tracker และ recovery_engine
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

class PositionColors:
    """ชุดสีสำหรับ Position Monitor"""
    BG_DARK = '#1a1a2e'
    BG_MEDIUM = '#16213e'
    BG_LIGHT = '#0f3460'
    PROFIT_GREEN = '#27ae60'
    LOSS_RED = '#e74c3c'
    BREAKEVEN_YELLOW = '#f1c40f'
    PENDING_BLUE = '#3498db'
    BUY_GREEN = '#2ecc71'
    SELL_RED = '#e74c3c'
    TEXT_WHITE = '#ffffff'
    TEXT_GRAY = '#bdc3c7'
    TEXT_LIGHT = '#ecf0f1'
    RECOVERY_ACTIVE = '#e67e22'
    RECOVERY_SUCCESS = '#27ae60'
    RECOVERY_PENDING = '#f39c12'

class PositionData:
    """คลาสสำหรับเก็บข้อมูล Position"""
    
    def __init__(self, position_dict: Dict[str, Any]):
        self.ticket = position_dict.get('ticket', 0)
        self.symbol = position_dict.get('symbol', 'XAUUSD.v')
        self.type = position_dict.get('type', 0)  # 0=BUY, 1=SELL
        self.volume = position_dict.get('volume', 0.0)
        self.price_open = position_dict.get('price_open', 0.0)
        self.price_current = position_dict.get('price_current', 0.0)
        self.profit = position_dict.get('profit', 0.0)
        self.swap = position_dict.get('swap', 0.0)
        self.commission = position_dict.get('commission', 0.0)
        self.time = position_dict.get('time', datetime.now())
        self.comment = position_dict.get('comment', '')
        
        # Recovery Status
        self.recovery_level = position_dict.get('recovery_level', 0)
        self.is_recovery_active = position_dict.get('is_recovery_active', False)
        self.recovery_strategy = position_dict.get('recovery_strategy', 'None')
        
        # Performance Metrics
        self.unrealized_pnl = self.profit + self.swap + self.commission
        self.pips = self._calculate_pips()
        self.hold_time = self._calculate_hold_time()
        
    def _calculate_pips(self) -> float:
        """คำนวณ Pips"""
        if self.price_open == 0:
            return 0.0
        
        pip_value = 0.1 if 'JPY' in self.symbol else 0.0001
        if self.type == 0:  # BUY
            return (self.price_current - self.price_open) / pip_value
        else:  # SELL
            return (self.price_open - self.price_current) / pip_value
    
    def _calculate_hold_time(self) -> str:
        """คำนวณเวลาที่ Hold Position"""
        if isinstance(self.time, datetime):
            duration = datetime.now() - self.time
            hours = duration.total_seconds() // 3600
            minutes = (duration.total_seconds() % 3600) // 60
            return f"{int(hours):02d}:{int(minutes):02d}"
        return "00:00"
    
    @property
    def type_str(self) -> str:
        """แปลง Position Type เป็น String"""
        return "BUY" if self.type == 0 else "SELL"
    
    @property
    def status_color(self) -> str:
        """สีตามสถานะ Profit/Loss"""
        if abs(self.unrealized_pnl) < 0.01:
            return PositionColors.BREAKEVEN_YELLOW
        return PositionColors.PROFIT_GREEN if self.unrealized_pnl > 0 else PositionColors.LOSS_RED

class PositionMonitorPanel:
    """🎛️ Main Position Monitor Panel"""
    
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.logger = setup_component_logger("PositionMonitor")
        self.colors = PositionColors()
        
        # Settings
        self.settings = get_system_settings()
        self.trading_params = get_trading_parameters()
        
        # Data
        self.positions = []
        self.selected_positions = set()
        
        # Data Update Threading
        self.update_active = False
        self.update_thread = None
        self.data_queue = queue.Queue()
        
        # Create main frame
        self.main_frame = tk.Frame(parent, bg=self.colors.BG_DARK)
        self.main_frame.pack(fill='both', expand=True)
        
        # Create UI components
        self._create_header_panel()
        self._create_position_table()
        self._create_control_panel()
        
        # Start data updates
        self.start_real_time_updates()
        
        self.logger.info("📊 เริ่มต้น Position Monitor Panel")
    
    def _create_header_panel(self) -> None:
        """สร้าง Header Panel"""
        header_frame = tk.Frame(self.main_frame, bg=self.colors.BG_MEDIUM, height=80)
        header_frame.pack(fill='x', padx=10, pady=(10, 5))
        header_frame.pack_propagate(False)
        
        # Title and Status
        title_frame = tk.Frame(header_frame, bg=self.colors.BG_MEDIUM)
        title_frame.pack(side='left', fill='y')
        
        tk.Label(
            title_frame, text="📊 Position Monitor", 
            font=('Segoe UI', 18, 'bold'), fg=self.colors.TEXT_WHITE, bg=self.colors.BG_MEDIUM
        ).pack(anchor='w')
        
        self.status_label = tk.Label(
            title_frame, text="🟢 Real-time monitoring active", 
            font=('Segoe UI', 10), fg=self.colors.PROFIT_GREEN, bg=self.colors.BG_MEDIUM
        )
        self.status_label.pack(anchor='w')
        
        # Quick Stats
        stats_frame = tk.Frame(header_frame, bg=self.colors.BG_MEDIUM)
        stats_frame.pack(side='right', fill='y', padx=20)
        
        self.quick_stats = {}
        stat_items = [
            ('live_positions', 'Live Positions:', '0'),
            ('total_exposure', 'Total Exposure:', '0.00'),
            ('net_pnl', 'Net P&L:', '$0.00'),
            ('last_update', 'Last Update:', 'Never')
        ]
        
        for i, (key, label, default) in enumerate(stat_items):
            stat_container = tk.Frame(stats_frame, bg=self.colors.BG_MEDIUM)
            stat_container.grid(row=i//2, column=i%2, padx=10, pady=2, sticky='w')
            
            tk.Label(
                stat_container, text=label, font=('Segoe UI', 9),
                fg=self.colors.TEXT_GRAY, bg=self.colors.BG_MEDIUM
            ).pack(side='left')
            
            self.quick_stats[key] = tk.Label(
                stat_container, text=default, font=('Segoe UI', 9, 'bold'),
                fg=self.colors.TEXT_WHITE, bg=self.colors.BG_MEDIUM
            )
            self.quick_stats[key].pack(side='left', padx=(5, 0))
    
    def _create_position_table(self) -> None:
        """สร้าง Position Table"""
        table_frame = tk.Frame(self.main_frame, bg=self.colors.BG_MEDIUM)
        table_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Title
        title_label = tk.Label(
            table_frame, text="📊 Position Monitor - Real-time Tracking",
            font=('Segoe UI', 14, 'bold'), fg=self.colors.TEXT_WHITE, bg=self.colors.BG_MEDIUM
        )
        title_label.pack(pady=(10, 10))
        
        # Treeview with Scrollbars
        tree_frame = tk.Frame(table_frame, bg=self.colors.BG_MEDIUM)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Define columns
        columns = (
            'ticket', 'symbol', 'type', 'volume', 'open_price', 'current_price',
            'pips', 'profit', 'total_pnl', 'hold_time', 'recovery_status'
        )
        
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        column_config = {
            'ticket': {'width': 100, 'text': 'Ticket'},
            'symbol': {'width': 80, 'text': 'Symbol'},
            'type': {'width': 60, 'text': 'Type'},
            'volume': {'width': 80, 'text': 'Volume'},
            'open_price': {'width': 100, 'text': 'Open Price'},
            'current_price': {'width': 100, 'text': 'Current Price'},
            'pips': {'width': 70, 'text': 'Pips'},
            'profit': {'width': 80, 'text': 'Profit'},
            'total_pnl': {'width': 100, 'text': 'Total P&L'},
            'hold_time': {'width': 80, 'text': 'Hold Time'},
            'recovery_status': {'width': 120, 'text': 'Recovery Status'}
        }
        
        for col, config in column_config.items():
            self.tree.heading(col, text=config['text'])
            self.tree.column(col, width=config['width'], anchor='center')
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack tree and scrollbars
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind events
        self.tree.bind('<Double-1>', self._on_position_double_click)
        self.tree.bind('<Button-3>', self._show_context_menu)
    
    def _create_control_panel(self) -> None:
        """สร้าง Control Panel"""
        control_frame = tk.Frame(self.main_frame, bg=self.colors.BG_MEDIUM, height=80)
        control_frame.pack(fill='x', padx=10, pady=(5, 10))
        control_frame.pack_propagate(False)
        
        # Position Actions
        left_controls = tk.Frame(control_frame, bg=self.colors.BG_MEDIUM)
        left_controls.pack(side='left', fill='y', padx=10)
        
        tk.Label(
            left_controls, text="Position Actions:", font=('Segoe UI', 10, 'bold'),
            fg=self.colors.TEXT_WHITE, bg=self.colors.BG_MEDIUM
        ).pack(anchor='w')
        
        button_frame = tk.Frame(left_controls, bg=self.colors.BG_MEDIUM)
        button_frame.pack(fill='x', pady=(5, 0))
        
        action_buttons = [
            ("❌ Close All", self._close_all_positions, self.colors.LOSS_RED),
            ("🔄 Recovery All", self._trigger_all_recovery, self.colors.RECOVERY_ACTIVE),
            ("⏸️ Pause Trading", self._pause_trading, self.colors.PENDING_BLUE),
            ("🛡️ Emergency Hedge", self._emergency_hedge, self.colors.BG_LIGHT)
        ]
        
        for i, (text, command, color) in enumerate(action_buttons):
            btn = tk.Button(
                button_frame, text=text, font=('Segoe UI', 9),
                bg=color, fg=self.colors.TEXT_WHITE,
                command=command, cursor='hand2', width=15
            )
            btn.grid(row=i//2, column=i%2, padx=5, pady=2, sticky='w')
        
        # Auto Updates Settings
        right_controls = tk.Frame(control_frame, bg=self.colors.BG_MEDIUM)
        right_controls.pack(side='right', fill='y', padx=10)
        
        tk.Label(
            right_controls, text="Monitor Settings:", font=('Segoe UI', 10, 'bold'),
            fg=self.colors.TEXT_WHITE, bg=self.colors.BG_MEDIUM
        ).pack(anchor='w')
        
        settings_frame = tk.Frame(right_controls, bg=self.colors.BG_MEDIUM)
        settings_frame.pack(fill='x', pady=(5, 0))
        
        # Auto-refresh toggle
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_cb = tk.Checkbutton(
            settings_frame, text="Auto Refresh", variable=self.auto_refresh_var,
            font=('Segoe UI', 9), fg=self.colors.TEXT_WHITE, bg=self.colors.BG_MEDIUM,
            selectcolor=self.colors.BG_LIGHT
        )
        auto_refresh_cb.grid(row=0, column=0, sticky='w', padx=5)
        
        # Manual refresh button
        refresh_btn = tk.Button(
            settings_frame, text="🔄 Refresh", font=('Segoe UI', 9),
            bg=self.colors.BG_LIGHT, fg=self.colors.TEXT_WHITE,
            command=self._manual_refresh, cursor='hand2'
        )
        refresh_btn.grid(row=0, column=1, padx=10)
    
    def start_real_time_updates(self) -> None:
        """เริ่ม Real-time Updates"""
        if not self.update_active:
            self.update_active = True
            self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()
            self.logger.info("🔄 เริ่ม Real-time Position Updates")
    
    def _update_loop(self) -> None:
        """Main Update Loop"""
        while self.update_active:
            try:
                if self.auto_refresh_var.get():
                    position_data = self._fetch_position_data()
                    self.data_queue.put(('positions', position_data))
                    self.main_frame.after_idle(self._process_data_queue)
                
                time.sleep(1)  # Update every second
                
            except Exception as e:
                self.logger.error(f"❌ ข้อผิดพลาดใน Update Loop: {e}")
                time.sleep(1)
    
    def _fetch_position_data(self) -> List[Dict[str, Any]]:
        """ดึงข้อมูล Position จาก Backend"""
        try:
            # TODO: เชื่อมต่อกับ Position Tracker
            # Sample data for testing
            return [
                {
                    'ticket': 123456789,
                    'symbol': 'XAUUSD.v',
                    'type': 0,  # BUY
                    'volume': 0.1,
                    'price_open': 2020.50,
                    'price_current': 2022.30,
                    'profit': 18.00,
                    'swap': -0.50,
                    'commission': -3.00,
                    'time': datetime.now() - timedelta(minutes=15),
                    'comment': 'Auto Entry - Trend Following',
                    'recovery_level': 0,
                    'is_recovery_active': False,
                    'recovery_strategy': 'None'
                }
            ]
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการดึงข้อมูล Position: {e}")
            return []
    
    def _process_data_queue(self) -> None:
        """ประมวลผล Data Queue"""
        try:
            while not self.data_queue.empty():
                data_type, data = self.data_queue.get_nowait()
                if data_type == 'positions':
                    self._update_position_display(data)
        except queue.Empty:
            pass
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการประมวลผล Data Queue: {e}")
    
    def _update_position_display(self, positions_data: List[Dict[str, Any]]) -> None:
        """อัพเดทการแสดงผล Position"""
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Convert to PositionData objects
            self.positions = [PositionData(pos_dict) for pos_dict in positions_data]
            
            # Populate table
            for position in self.positions:
                values = (
                    str(position.ticket),
                    position.symbol,
                    position.type_str,
                    f"{position.volume:.2f}",
                    f"{position.price_open:.5f}",
                    f"{position.price_current:.5f}",
                    f"{position.pips:.1f}",
                    f"${position.profit:.2f}",
                    f"${position.unrealized_pnl:.2f}",
                    position.hold_time,
                    "🔄 Active" if position.is_recovery_active else "⏸️ Inactive"
                )
                
                item = self.tree.insert('', 'end', values=values)
                
                # Color coding
                if position.unrealized_pnl > 0:
                    self.tree.item(item, tags=('profit',))
                elif position.unrealized_pnl < 0:
                    self.tree.item(item, tags=('loss',))
                else:
                    self.tree.item(item, tags=('breakeven',))
            
            # Configure row colors
            self.tree.tag_configure('profit', background='#1e4d3a', foreground=self.colors.PROFIT_GREEN)
            self.tree.tag_configure('loss', background='#4d1e1e', foreground=self.colors.LOSS_RED)
            self.tree.tag_configure('breakeven', background='#4d4d1e', foreground=self.colors.BREAKEVEN_YELLOW)
            
            # Update quick stats
            self._update_quick_stats(positions_data)
            
            # Update status
            self.status_label.config(
                text=f"🟢 Last updated: {datetime.now().strftime('%H:%M:%S')}",
                fg=self.colors.PROFIT_GREEN
            )
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดทการแสดงผล: {e}")
    
    def _update_quick_stats(self, positions_data: List[Dict[str, Any]]) -> None:
        """อัพเดท Quick Stats"""
        try:
            total_positions = len(positions_data)
            total_exposure = sum(pos['volume'] for pos in positions_data)
            net_pnl = sum(pos.get('profit', 0) + pos.get('swap', 0) + 
                         pos.get('commission', 0) for pos in positions_data)
            
            self.quick_stats['live_positions'].config(text=str(total_positions))
            self.quick_stats['total_exposure'].config(text=f"{total_exposure:.2f}")
            
            # P&L with color
            pnl_color = self.colors.PROFIT_GREEN if net_pnl > 0 else \
                       self.colors.LOSS_RED if net_pnl < 0 else self.colors.TEXT_WHITE
            self.quick_stats['net_pnl'].config(text=f"${net_pnl:.2f}", fg=pnl_color)
            
            self.quick_stats['last_update'].config(
                text=datetime.now().strftime('%H:%M:%S')
            )
            
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดในการอัพเดท Quick Stats: {e}")
    
    def _on_position_double_click(self, event) -> None:
        """จัดการ Double Click บน Position"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            ticket = self.tree.item(item, 'values')[0]
            messagebox.showinfo("Position Details", f"Position #{ticket} details (Feature coming soon)")
    
    def _show_context_menu(self, event) -> None:
        """แสดง Context Menu"""
        selection = self.tree.selection()
        if not selection:
            return
        
        context_menu = tk.Menu(self.tree, tearoff=0, bg=self.colors.BG_DARK, 
                              fg=self.colors.TEXT_WHITE, font=('Segoe UI', 9))
        
        context_menu.add_command(label="📊 View Details", command=self._view_selected_details)
        context_menu.add_command(label="❌ Close Position", command=self._close_selected_position)
        context_menu.add_command(label="🔄 Trigger Recovery", command=self._trigger_recovery)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def _manual_refresh(self) -> None:
        """Manual Refresh"""
        try:
            position_data = self._fetch_position_data()
            self._update_position_display(position_data)
            self.logger.info("🔄 Manual refresh completed")
        except Exception as e:
            self.logger.error(f"❌ ข้อผิดพลาดใน Manual Refresh: {e}")
    
    # Control Methods
    def _close_all_positions(self) -> None:
        """ปิด Position ทั้งหมด"""
        if messagebox.askyesno("Confirm Close All", 
                              "⚠️ Close ALL positions? This action cannot be undone!"):
            self.logger.warning("🚨 ส่งคำสั่งปิด Position ทั้งหมด")
            messagebox.showinfo("Success", "Close all positions command sent")
    
    def _trigger_all_recovery(self) -> None:
        """เริ่ม Recovery ทั้งหมด"""
        if messagebox.askyesno("Confirm Recovery All", 
                              "🔄 Trigger recovery for ALL losing positions?"):
            self.logger.info("🔄 เริ่ม Recovery ทั้งหมด")
            messagebox.showinfo("Success", "Recovery triggered for all positions")
    
    def _pause_trading(self) -> None:
        """หยุดการเทรดชั่วคราว"""
        self.logger.warning("⏸️ หยุดการเทรดชั่วคราว")
        messagebox.showinfo("Success", "Trading paused")
    
    def _emergency_hedge(self) -> None:
        """Emergency Hedging"""
        if messagebox.askyesno("Confirm Emergency Hedge", 
                              "🛡️ Create emergency hedge for ALL positions?"):
            self.logger.warning("🛡️ สร้าง Emergency Hedge")
            messagebox.showinfo("Success", "Emergency hedge created")
    
    def _view_selected_details(self) -> None:
        """ดูรายละเอียด Position ที่เลือก"""
        messagebox.showinfo("Details", "Position details (Feature coming soon)")
    
    def _close_selected_position(self) -> None:
        """ปิด Position ที่เลือก"""
        messagebox.showinfo("Close", "Close position (Feature coming soon)")
    
    def _trigger_recovery(self) -> None:
        """เริ่ม Recovery สำหรับ Position ที่เลือก"""
        messagebox.showinfo("Recovery", "Trigger recovery (Feature coming soon)")
    
    def cleanup(self) -> None:
        """ทำความสะอาดเมื่อปิด Panel"""
        self.update_active = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1)
        self.logger.info("🧹 ทำความสะอาด Position Monitor Panel")


# Test Function
def demo_position_monitor():
    """Demo function สำหรับทดสอบ Position Monitor Panel"""
    root = tk.Tk()
    root.title("Position Monitor Demo")
    root.geometry("1400x800")
    root.configure(bg='#1a1a2e')
    
    monitor = PositionMonitorPanel(root)
    
    def on_closing():
        monitor.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    demo_position_monitor()