#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REAL TRADING GUI - เชื่อมต่อระบบเทรดจริง
======================================
GUI ที่เชื่อมต่อกับ Real Trading System และสามารถเทรดได้จริง
ไม่มี Mock หรือ Simulation
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

# Core imports
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

# Import ระบบจริง
try:
    from core_system.trading_system import RealTradingSystem
    from mt5_integration.order_executor import get_smart_order_executor
    from position_management.position_tracker import get_enhanced_position_tracker
    from market_intelligence.market_analyzer import MarketAnalyzer
    REAL_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ไม่สามารถโหลดระบบจริง: {e}")
    REAL_SYSTEM_AVAILABLE = False

class DashboardColors:
    """ธีมสี"""
    BG_DARK = '#1a1a2e'
    BG_MEDIUM = '#16213e'
    BG_LIGHT = '#0f3460'
    PRIMARY = '#e94560'
    SUCCESS = '#27ae60'
    WARNING = '#f39c1c'
    DANGER = '#e74c3c'
    INFO = '#3498db'
    TEXT_WHITE = '#ffffff'
    TEXT_GRAY = '#bdc3c7'

class RealTradingGUI:
    """🚀 Real Trading GUI - เชื่อมต่อระบบจริง"""
    
    def __init__(self):
        # เช็คว่าระบบพร้อมหรือไม่
        if not MT5_AVAILABLE:
            messagebox.showerror("Error", "❌ MetaTrader5 module ไม่พร้อมใช้งาน")
            return
        
        if not REAL_SYSTEM_AVAILABLE:
            messagebox.showerror("Error", "❌ Real Trading System ไม่พร้อมใช้งาน")
            return
        
        # สร้าง Real Trading System
        try:
            self.trading_system = RealTradingSystem()
            self.system_initialized = self.trading_system.initialize_system()
        except Exception as e:
            messagebox.showerror("Error", f"❌ ไม่สามารถเริ่มต้นระบบ: {e}")
            return
        
        if not self.system_initialized:
            messagebox.showerror("Error", "❌ ระบบไม่สามารถเริ่มต้นได้")
            return
        
        # GUI State
        self.gui_active = True
        self.update_interval = 1000
        
        # Data
        self.account_info = None
        self.positions = []
        self.system_stats = {}
        
        # Create GUI
        self.root = tk.Tk()
        self._setup_window()
        self._create_components()
        self._start_updates()
        
        # เชื่อมต่อข้อมูลจริง
        self._connect_real_system()
        
        print("🚀 Real Trading GUI เริ่มต้นสำเร็จ")
    
    def _setup_window(self):
        """Setup หน้าต่างหลัก"""
        self.root.title("🚀 Real Intelligent Gold Trading System")
        self.root.geometry("1400x900")
        self.root.configure(bg=DashboardColors.BG_DARK)
        
        # Center window
        x = (self.root.winfo_screenwidth() // 2) - 700
        y = (self.root.winfo_screenheight() // 2) - 450
        self.root.geometry(f"1400x900+{x}+{y}")
    
    def _create_components(self):
        """สร้าง GUI Components"""
        
        # Header with system status
        header_frame = tk.Frame(self.root, bg=DashboardColors.BG_DARK, height=80)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        header_frame.pack_propagate(False)
        
        # Title
        tk.Label(
            header_frame,
            text="🚀 REAL INTELLIGENT GOLD TRADING SYSTEM",
            font=("Arial", 18, "bold"),
            fg=DashboardColors.PRIMARY,
            bg=DashboardColors.BG_DARK
        ).pack(pady=5)
        
        # System status
        self.system_status_label = tk.Label(
            header_frame,
            text="🔄 Initializing...",
            font=("Arial", 12),
            fg=DashboardColors.WARNING,
            bg=DashboardColors.BG_DARK
        )
        self.system_status_label.pack()
        
        # Main content
        main_frame = tk.Frame(self.root, bg=DashboardColors.BG_DARK)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left panel - Controls
        left_frame = tk.Frame(main_frame, bg=DashboardColors.BG_MEDIUM, width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)
        
        self._create_control_panel(left_frame)
        self._create_account_panel(left_frame)
        self._create_stats_panel(left_frame)
        
        # Right panel - Monitoring
        right_frame = tk.Frame(main_frame, bg=DashboardColors.BG_MEDIUM)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self._create_monitoring_panel(right_frame)
        
        # Status bar
        self.status_bar = tk.Frame(self.root, bg=DashboardColors.BG_LIGHT, height=30)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(
            self.status_bar,
            text="🔄 System Ready",
            font=("Arial", 10),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_LIGHT
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.time_label = tk.Label(
            self.status_bar,
            text="",
            font=("Arial", 10),
            fg=DashboardColors.TEXT_GRAY,
            bg=DashboardColors.BG_LIGHT
        )
        self.time_label.pack(side=tk.RIGHT, padx=10, pady=5)
    
    def _create_control_panel(self, parent):
        """สร้าง Control Panel"""
        control_frame = tk.LabelFrame(
            parent,
            text="🎯 Trading Controls",
            font=("Arial", 12, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        )
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Start Trading Button
        self.start_btn = tk.Button(
            control_frame,
            text="🚀 START LIVE TRADING",
            font=("Arial", 14, "bold"),
            bg=DashboardColors.SUCCESS,
            fg=DashboardColors.TEXT_WHITE,
            height=2,
            command=self.start_trading
        )
        self.start_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Stop Trading Button
        self.stop_btn = tk.Button(
            control_frame,
            text="🛑 STOP TRADING",
            font=("Arial", 14, "bold"),
            bg=DashboardColors.DANGER,
            fg=DashboardColors.TEXT_WHITE,
            height=2,
            state=tk.DISABLED,
            command=self.stop_trading
        )
        self.stop_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Emergency Stop
        emergency_btn = tk.Button(
            control_frame,
            text="🚨 EMERGENCY STOP",
            font=("Arial", 12, "bold"),
            bg=DashboardColors.DANGER,
            fg=DashboardColors.TEXT_WHITE,
            command=self.emergency_stop
        )
        emergency_btn.pack(fill=tk.X, padx=10, pady=5)
    
    def _create_account_panel(self, parent):
        """สร้าง Account Panel"""
        account_frame = tk.LabelFrame(
            parent,
            text="💰 Account Information",
            font=("Arial", 12, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        )
        account_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Account labels
        self.account_labels = {}
        account_items = [
            ('Login', '---'),
            ('Server', '---'),
            ('Company', '---'),
            ('Balance', '$0.00'),
            ('Equity', '$0.00'),
            ('Free Margin', '$0.00'),
            ('Margin Level', '0%')
        ]
        
        for label, default_value in account_items:
            row_frame = tk.Frame(account_frame, bg=DashboardColors.BG_MEDIUM)
            row_frame.pack(fill=tk.X, padx=5, pady=2)
            
            tk.Label(
                row_frame,
                text=f"{label}:",
                font=("Arial", 10),
                fg=DashboardColors.TEXT_GRAY,
                bg=DashboardColors.BG_MEDIUM,
                width=12,
                anchor="w"
            ).pack(side=tk.LEFT)
            
            value_label = tk.Label(
                row_frame,
                text=default_value,
                font=("Arial", 10, "bold"),
                fg=DashboardColors.TEXT_WHITE,
                bg=DashboardColors.BG_MEDIUM,
                anchor="w"
            )
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            self.account_labels[label.lower().replace(' ', '_')] = value_label
    
    def _create_stats_panel(self, parent):
        """สร้าง Statistics Panel"""
        stats_frame = tk.LabelFrame(
            parent,
            text="📊 Trading Statistics",
            font=("Arial", 12, "bold"),
            fg=DashboardColors.TEXT_WHITE,
            bg=DashboardColors.BG_MEDIUM
        )
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Stats labels
        self.stats_labels = {}
        stats_items = [
            ('Open Positions', '0'),
            ('Total Volume', '0.00'),
            ('Today P&L', '$0.00'),
            ('Success Rate', '0%'),
            ('Recovery Active', 'No')
        ]
        
        for label, default_value in stats_items:
            row_frame = tk.Frame(stats_frame, bg=DashboardColors.BG_MEDIUM)
            row_frame.pack(fill=tk.X, padx=5, pady=2)
            
            tk.Label(
                row_frame,
                text=f"{label}:",
                font=("Arial", 10),
                fg=DashboardColors.TEXT_GRAY,
                bg=DashboardColors.BG_MEDIUM,
                width=12,
                anchor="w"
            ).pack(side=tk.LEFT)
            
            value_label = tk.Label(
                row_frame,
                text=default_value,
                font=("Arial", 10, "bold"),
                fg=DashboardColors.TEXT_WHITE,
                bg=DashboardColors.BG_MEDIUM,
                anchor="w"
            )
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            self.stats_labels[label.lower().replace(' ', '_')] = value_label
    
    def _create_monitoring_panel(self, parent):
        """สร้าง Monitoring Panel"""
        # Create notebook for tabs
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Positions tab
        positions_frame = tk.Frame(notebook, bg=DashboardColors.BG_DARK)
        notebook.add(positions_frame, text="📈 Positions")
        
        # Positions tree
        columns = ('Ticket', 'Symbol', 'Type', 'Volume', 'Open Price', 'Current Price', 'P&L')
        self.positions_tree = ttk.Treeview(positions_frame, columns=columns, show='headings')
        
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=100)
        
        # Scrollbar for positions
        pos_scrollbar = ttk.Scrollbar(positions_frame, orient=tk.VERTICAL, command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=pos_scrollbar.set)
        
        self.positions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pos_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Logs tab
        logs_frame = tk.Frame(notebook, bg=DashboardColors.BG_DARK)
        notebook.add(logs_frame, text="📝 Logs")
        
        # Log text widget
        self.log_text = scrolledtext.ScrolledText(
            logs_frame,
            font=("Consolas", 10),
            bg=DashboardColors.BG_DARK,
            fg=DashboardColors.TEXT_WHITE,
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _connect_real_system(self):
        """เชื่อมต่อกับระบบจริง"""
        try:
            # Get initial account info
            self._update_account_info()
            
            # Log initial status
            self.add_log("🚀 Real Trading System connected")
            self.add_log(f"✅ Components loaded: {len(self.trading_system.components)}")
            
            # Update system status
            if self.trading_system.system_state.value == "READY":
                self.system_status_label.config(
                    text="✅ System Ready - Live Trading Available",
                    fg=DashboardColors.SUCCESS
                )
            else:
                self.system_status_label.config(
                    text=f"⚠️ System State: {self.trading_system.system_state.value}",
                    fg=DashboardColors.WARNING
                )
            
        except Exception as e:
            self.add_log(f"❌ Connection error: {e}")
            self.system_status_label.config(text="❌ Connection Failed", fg=DashboardColors.DANGER)
    
    def _start_updates(self):
        """เริ่มการอัพเดท GUI"""
        self._update_gui()
    
    def _update_gui(self):
        """อัพเดท GUI แบบ Real-time"""
        if self.gui_active:
            try:
                # Update time
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.time_label.config(text=current_time)
                
                # Update account info
                self._update_account_info()
                
                # Update positions
                self._update_positions()
                
                # Update statistics
                self._update_statistics()
                
            except Exception as e:
                self.add_log(f"❌ GUI update error: {e}")
            
            # Schedule next update
            self.root.after(self.update_interval, self._update_gui)
    
    def _update_account_info(self):
        """อัพเดทข้อมูลบัญชี"""
        try:
            if not mt5.account_info():
                return
            
            account = mt5.account_info()
            
            # Update account labels
            self.account_labels['login'].config(text=str(account.login))
            self.account_labels['server'].config(text=account.server)
            self.account_labels['company'].config(text=account.company)
            self.account_labels['balance'].config(text=f"${account.balance:,.2f}")
            self.account_labels['equity'].config(text=f"${account.equity:,.2f}")
            self.account_labels['free_margin'].config(text=f"${account.margin_free:,.2f}")
            
            if account.margin > 0:
                margin_level = (account.equity / account.margin) * 100
                self.account_labels['margin_level'].config(text=f"{margin_level:.1f}%")
            
        except Exception as e:
            self.add_log(f"❌ Account update error: {e}")
    
    def _update_positions(self):
        """อัพเดท Positions"""
        try:
            # Get positions from MT5
            positions = mt5.positions_get()
            
            # Clear existing items
            for item in self.positions_tree.get_children():
                self.positions_tree.delete(item)
            
            if positions:
                for pos in positions:
                    # Get current price
                    tick = mt5.symbol_info_tick(pos.symbol)
                    current_price = tick.bid if pos.type == 1 else tick.ask if tick else pos.price_open
                    
                    # Calculate P&L
                    if pos.type == 0:  # BUY
                        pnl = (current_price - pos.price_open) * pos.volume * 100
                    else:  # SELL
                        pnl = (pos.price_open - current_price) * pos.volume * 100
                    
                    # Add to tree
                    self.positions_tree.insert('', 'end', values=(
                        pos.ticket,
                        pos.symbol,
                        'BUY' if pos.type == 0 else 'SELL',
                        f"{pos.volume:.2f}",
                        f"{pos.price_open:.2f}",
                        f"{current_price:.2f}",
                        f"${pnl:.2f}"
                    ))
            
        except Exception as e:
            self.add_log(f"❌ Positions update error: {e}")
    
    def _update_statistics(self):
        """อัพเดทสถิติ"""
        try:
            positions = mt5.positions_get()
            
            # Count positions
            open_positions = len(positions) if positions else 0
            self.stats_labels['open_positions'].config(text=str(open_positions))
            
            # Calculate total volume
            total_volume = sum(pos.volume for pos in positions) if positions else 0
            self.stats_labels['total_volume'].config(text=f"{total_volume:.2f}")
            
            # Calculate total P&L
            total_pnl = 0
            if positions:
                for pos in positions:
                    tick = mt5.symbol_info_tick(pos.symbol)
                    if tick:
                        current_price = tick.bid if pos.type == 1 else tick.ask
                        if pos.type == 0:  # BUY
                            pnl = (current_price - pos.price_open) * pos.volume * 100
                        else:  # SELL
                            pnl = (pos.price_open - current_price) * pos.volume * 100
                        total_pnl += pnl
            
            # Update P&L with color
            pnl_color = DashboardColors.SUCCESS if total_pnl >= 0 else DashboardColors.DANGER
            self.stats_labels['today_p&l'].config(text=f"${total_pnl:.2f}", fg=pnl_color)
            
            # Check if recovery is active
            recovery_active = "Yes" if self.trading_system.trading_active else "No"
            self.stats_labels['recovery_active'].config(text=recovery_active)
            
        except Exception as e:
            self.add_log(f"❌ Statistics update error: {e}")
    
    def start_trading(self):
        """เริ่มการเทรดจริง"""
        try:
            # Confirm with user
            result = messagebox.askyesno(
                "⚠️ LIVE TRADING CONFIRMATION",
                "🚨 คุณกำลังจะเริ่มการเทรดด้วยเงินจริง!\n\n"
                "ระบบจะทำการเทรด XAUUSD แบบอัตโนมัติ\n"
                "พร้อมระบบ Recovery ที่ไม่ใช้ Stop Loss\n\n"
                "⚠️ การเทรดมีความเสี่ยง\n"
                "ต้องการดำเนินการต่อหรือไม่?"
            )
            
            if not result:
                return
            
            # Start real trading system
            if self.trading_system.start_trading():
                self.add_log("🚀 Live Trading Started!")
                self.add_log("💰 System is now trading with real money")
                
                # Update UI
                self.start_btn.config(state=tk.DISABLED)
                self.stop_btn.config(state=tk.NORMAL)
                self.status_label.config(text="🟢 Live Trading Active")
                self.system_status_label.config(
                    text="🚀 LIVE TRADING ACTIVE",
                    fg=DashboardColors.SUCCESS
                )
                
                messagebox.showinfo("Started", "🚀 Live Trading เริ่มแล้ว!")
            else:
                messagebox.showerror("Error", "❌ ไม่สามารถเริ่มการเทรดได้")
                
        except Exception as e:
            self.add_log(f"❌ Start trading error: {e}")
            messagebox.showerror("Error", f"❌ ข้อผิดพลาด: {e}")
    
    def stop_trading(self):
        """หยุดการเทรด"""
        try:
            result = messagebox.askyesno(
                "Confirm Stop",
                "🛑 หยุดการเทรด?\n\nระบบจะหยุดสร้าง position ใหม่\nแต่ position ที่มีอยู่จะยังคงเปิดอยู่"
            )
            
            if result:
                if self.trading_system.stop_trading():
                    self.add_log("🛑 Trading Stopped")
                    
                    # Update UI
                    self.start_btn.config(state=tk.NORMAL)
                    self.stop_btn.config(state=tk.DISABLED)
                    self.status_label.config(text="🔴 Trading Stopped")
                    self.system_status_label.config(
                        text="🛑 Trading Stopped - System Ready",
                        fg=DashboardColors.WARNING
                    )
                    
                    messagebox.showinfo("Stopped", "🛑 หยุดการเทรดแล้ว")
                
        except Exception as e:
            self.add_log(f"❌ Stop trading error: {e}")
            messagebox.showerror("Error", f"❌ ข้อผิดพลาด: {e}")
    
    def emergency_stop(self):
        """หยุดฉุกเฉิน"""
        try:
            result = messagebox.askyesno(
                "🚨 EMERGENCY STOP",
                "🚨 EMERGENCY STOP\n\n"
                "จะหยุดการเทรดทันทีและปิดตำแหน่งทั้งหมด\n"
                "⚠️ การดำเนินการนี้ไม่สามารถย้อนกลับได้\n\n"
                "ต้องการดำเนินการหรือไม่?"
            )
            
            if result:
                # Close all positions
                positions = mt5.positions_get()
                if positions:
                    for pos in positions:
                        # Create close request
                        request = {
                            "action": mt5.TRADE_ACTION_DEAL,
                            "symbol": pos.symbol,
                            "volume": pos.volume,
                            "type": mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY,
                            "position": pos.ticket,
                            "deviation": 10,
                            "magic": 0,
                            "comment": "EMERGENCY STOP",
                            "type_time": mt5.ORDER_TIME_GTC,
                            "type_filling": mt5.ORDER_FILLING_IOC,
                        }
                        
                        # Send close order
                        result = mt5.order_send(request)
                        if result.retcode == mt5.TRADE_RETCODE_DONE:
                            self.add_log(f"✅ Closed position {pos.ticket}")
                        else:
                            self.add_log(f"❌ Failed to close position {pos.ticket}: {result.comment}")
                
                # Stop trading system
                self.trading_system.stop_trading()
                
                self.add_log("🚨 EMERGENCY STOP EXECUTED")
                
                # Update UI
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
                self.status_label.config(text="🚨 Emergency Stop")
                self.system_status_label.config(
                    text="🚨 EMERGENCY STOP",
                    fg=DashboardColors.DANGER
                )
                
                messagebox.showwarning("Emergency Stop", "🚨 Emergency Stop executed")
                
        except Exception as e:
            self.add_log(f"❌ Emergency stop error: {e}")
            messagebox.showerror("Error", f"❌ ข้อผิดพลาด: {e}")
    
    def add_log(self, message):
        """เพิ่มข้อความ log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        
        # Keep only last 1000 lines
        lines = self.log_text.get(1.0, tk.END).split('\n')
        if len(lines) > 1000:
            self.log_text.delete(1.0, f"{len(lines)-1000}.0")
    
    def run(self):
        """รัน GUI"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
            self.root.mainloop()
        except Exception as e:
            print(f"❌ GUI error: {e}")
        finally:
            self.gui_active = False
    
    def _on_closing(self):
        """จัดการการปิดหน้าต่าง"""
        try:
            if self.trading_system.trading_active:
                result = messagebox.askyesno(
                    "Confirm",
                    "การเทรดกำลังทำงานอยู่\nต้องการหยุดการเทรดและปิดโปรแกรม?"
                )
                if result:
                    self.trading_system.stop_trading()
                    time.sleep(2)  # Wait for system to stop
                else:
                    return
            
            self.gui_active = False
            mt5.shutdown()
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            self.root.quit()
            self.root.destroy()

# Factory function
def create_real_trading_gui():
    """สร้าง Real Trading GUI"""
    return RealTradingGUI()

if __name__ == "__main__":
    try:
        gui = RealTradingGUI()
        if hasattr(gui, 'root'):
            gui.run()
    except Exception as e:
        print(f"❌ Failed to start GUI: {e}")
        messagebox.showerror("Error", f"❌ ไม่สามารถเริ่ม GUI: {e}")