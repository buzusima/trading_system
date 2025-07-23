# utilities/data_manager.py - Comprehensive Data Management System

import pandas as pd
import numpy as np
import sqlite3
import pickle
import json
import os
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
import threading
import time
import gzip
import shutil
from pathlib import Path

class DataType:
    """📊 ประเภทข้อมูล"""
    MARKET_DATA = "market_data"
    TRADES = "trades"
    POSITIONS = "positions"
    RECOVERY_LOGS = "recovery_logs"
    PERFORMANCE = "performance"
    CONFIGURATIONS = "configurations"
    ANALYTICS = "analytics"
    LOGS = "logs"

class StorageFormat:
    """💾 รูปแบบการเก็บข้อมูล"""
    SQLITE = "sqlite"
    CSV = "csv"
    JSON = "json"
    PICKLE = "pickle"
    PARQUET = "parquet"

class DataManager:
    """
    📁 Data Manager - ระบบจัดการข้อมูลแบบครอบคลุม
    
    ⚡ หน้าที่หลัก:
    - จัดเก็บข้อมูลการเทรดทุกประเภท
    - บีบอัดและจัดการข้อมูลขนาดใหญ่
    - Backup และ Recovery ข้อมูล
    - วิเคราะห์และรายงานข้อมูล
    - ปรับปรุงประสิทธิภาพฐานข้อมูล
    
    🎯 ความสามารถ:
    - SQLite สำหรับข้อมูลแบบ structured
    - File-based storage สำหรับ bulk data
    - Automatic compression และ archiving
    - Real-time data streaming และ caching
    - Data validation และ cleaning
    - Performance monitoring และ optimization
    """
    
    def __init__(self, config: Dict):
        print("📁 Initializing Data Manager...")
        
        self.config = config
        
        # Paths configuration
        self.base_path = Path(config.get('data_base_path', 'data'))
        self.db_path = self.base_path / 'trading_data.db'
        self.backup_path = self.base_path / 'backups'
        self.archive_path = self.base_path / 'archives'
        self.temp_path = self.base_path / 'temp'
        
        # Create directories
        self._create_directories()
        
        # Database settings
        self.db_connection = None
        self.connection_lock = threading.Lock()
        self.auto_commit = config.get('auto_commit', True)
        self.connection_timeout = config.get('connection_timeout', 30)
        
        # Performance settings
        self.batch_size = config.get('batch_size', 1000)
        self.compression_level = config.get('compression_level', 6)
        self.auto_vacuum = config.get('auto_vacuum', True)
        self.cache_size = config.get('cache_size', 10000)
        
        # Archive settings
        self.auto_archive_days = config.get('auto_archive_days', 30)
        self.max_db_size_mb = config.get('max_db_size_mb', 1000)
        self.compression_enabled = config.get('compression_enabled', True)
        
        # Statistics
        self.operations_count = 0
        self.total_records_stored = 0
        self.last_backup_time = None
        self.last_optimization_time = None
        
        # Initialize database
        self._initialize_database()
        
        # Start background maintenance
        self._start_maintenance_thread()
        
        print("✅ Data Manager initialized")
        print(f"   - Database: {self.db_path}")
        print(f"   - Backup Path: {self.backup_path}")
        print(f"   - Auto Archive: {self.auto_archive_days} days")
    
    def _create_directories(self):
        """สร้าง directories ที่จำเป็น"""
        try:
            directories = [
                self.base_path,
                self.backup_path,
                self.archive_path,
                self.temp_path,
                self.base_path / 'exports',
                self.base_path / 'imports',
                self.base_path / 'reports'
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
            
            print(f"📁 Created {len(directories)} directories")
            
        except Exception as e:
            print(f"❌ Directory creation error: {e}")
    
    def _initialize_database(self):
        """เริ่มต้นฐานข้อมูล"""
        try:
            with self._get_connection() as conn:
                # Create tables
                self._create_tables(conn)
                
                # Set performance optimizations
                self._optimize_database(conn)
                
                print("✅ Database initialized successfully")
                
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
    
    def _create_tables(self, conn: sqlite3.Connection):
        """สร้างตารางในฐานข้อมูล"""
        try:
            cursor = conn.cursor()
            
            # Market Data Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    open_price REAL NOT NULL,
                    high_price REAL NOT NULL,
                    low_price REAL NOT NULL,
                    close_price REAL NOT NULL,
                    volume INTEGER DEFAULT 0,
                    spread REAL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(timestamp, symbol, timeframe)
                )
            """)
            
            # Trades Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    trade_type TEXT NOT NULL,
                    volume REAL NOT NULL,
                    open_price REAL NOT NULL,
                    close_price REAL,
                    open_time DATETIME NOT NULL,
                    close_time DATETIME,
                    profit REAL DEFAULT 0,
                    commission REAL DEFAULT 0,
                    swap REAL DEFAULT 0,
                    magic_number INTEGER DEFAULT 0,
                    comment TEXT,
                    strategy TEXT,
                    session TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Positions Table (current open positions)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    position_type TEXT NOT NULL,
                    volume REAL NOT NULL,
                    open_price REAL NOT NULL,
                    current_price REAL,
                    unrealized_pnl REAL DEFAULT 0,
                    open_time DATETIME NOT NULL,
                    magic_number INTEGER DEFAULT 0,
                    comment TEXT,
                    strategy TEXT,
                    recovery_level INTEGER DEFAULT 0,
                    pair_id TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Recovery Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recovery_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    recovery_type TEXT NOT NULL,
                    original_ticket INTEGER,
                    recovery_ticket INTEGER,
                    recovery_level INTEGER,
                    original_loss REAL,
                    recovery_volume REAL,
                    success BOOLEAN,
                    final_profit REAL,
                    strategy_used TEXT,
                    reasoning TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Performance Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    gross_profit REAL DEFAULT 0,
                    gross_loss REAL DEFAULT 0,
                    net_profit REAL DEFAULT 0,
                    balance REAL DEFAULT 0,
                    equity REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    recovery_success_rate REAL DEFAULT 0,
                    volume_traded REAL DEFAULT 0,
                    strategies_used TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Analytics Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    metric_data TEXT,
                    category TEXT,
                    subcategory TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # System Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    level TEXT NOT NULL,
                    component TEXT,
                    message TEXT NOT NULL,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            self._create_indexes(cursor)
            
            conn.commit()
            print("✅ Database tables created successfully")
            
        except Exception as e:
            print(f"❌ Table creation error: {e}")
    
    def _create_indexes(self, cursor: sqlite3.Cursor):
        """สร้าง indexes สำหรับประสิทธิภาพ"""
        try:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_trades_ticket ON trades(ticket)",
                "CREATE INDEX IF NOT EXISTS idx_trades_open_time ON trades(open_time)",
                "CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy)",
                "CREATE INDEX IF NOT EXISTS idx_positions_ticket ON positions(ticket)",
                "CREATE INDEX IF NOT EXISTS idx_positions_strategy ON positions(strategy)",
                "CREATE INDEX IF NOT EXISTS idx_recovery_timestamp ON recovery_logs(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_performance_date ON performance(date)",
                "CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_analytics_metric ON analytics(metric_name)",
                "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level)"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            print(f"✅ Created {len(indexes)} database indexes")
            
        except Exception as e:
            print(f"❌ Index creation error: {e}")
    
    def _optimize_database(self, conn: sqlite3.Connection):
        """ปรับปรุงประสิทธิภาพฐานข้อมูล"""
        try:
            cursor = conn.cursor()
            
            # Performance optimizations
            optimizations = [
                "PRAGMA journal_mode = WAL",
                "PRAGMA synchronous = NORMAL",
                f"PRAGMA cache_size = {self.cache_size}",
                "PRAGMA temp_store = MEMORY",
                "PRAGMA mmap_size = 268435456",  # 256MB
                "PRAGMA optimize"
            ]
            
            if self.auto_vacuum:
                optimizations.append("PRAGMA auto_vacuum = INCREMENTAL")
            
            for pragma in optimizations:
                cursor.execute(pragma)
            
            conn.commit()
            print("✅ Database optimizations applied")
            
        except Exception as e:
            print(f"❌ Database optimization error: {e}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """ดึง database connection"""
        try:
            with self.connection_lock:
                if self.db_connection is None or self._connection_is_closed():
                    self.db_connection = sqlite3.connect(
                        str(self.db_path),
                        timeout=self.connection_timeout,
                        check_same_thread=False
                    )
                    
                    # Set row factory for dict-like access
                    self.db_connection.row_factory = sqlite3.Row
                
                return self.db_connection
                
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            raise
    
    def _connection_is_closed(self) -> bool:
        """ตรวจสอบว่า connection ปิดหรือไม่"""
        try:
            if self.db_connection is None:
                return True
            self.db_connection.execute("SELECT 1")
            return False
        except:
            return True
    
    def store_market_data(self, data: List[Dict], batch_insert: bool = True) -> bool:
        """
        📈 เก็บข้อมูลตลาด
        
        Args:
            data: รายการข้อมูลตลาด
            batch_insert: ใช้ batch insert หรือไม่
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            if not data:
                return True
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if batch_insert and len(data) > 1:
                    # Batch insert for better performance
                    insert_sql = """
                        INSERT OR REPLACE INTO market_data 
                        (timestamp, symbol, timeframe, open_price, high_price, 
                         low_price, close_price, volume, spread)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    
                    batch_data = []
                    for record in data:
                        batch_data.append((
                            record.get('timestamp'),
                            record.get('symbol', 'XAUUSD'),
                            record.get('timeframe', 'M5'),
                            record.get('open_price', 0),
                            record.get('high_price', 0),
                            record.get('low_price', 0),
                            record.get('close_price', 0),
                            record.get('volume', 0),
                            record.get('spread', 0)
                        ))
                    
                    cursor.executemany(insert_sql, batch_data)
                    
                else:
                    # Single insert
                    for record in data:
                        cursor.execute("""
                            INSERT OR REPLACE INTO market_data 
                            (timestamp, symbol, timeframe, open_price, high_price, 
                             low_price, close_price, volume, spread)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            record.get('timestamp'),
                            record.get('symbol', 'XAUUSD'),
                            record.get('timeframe', 'M5'),
                            record.get('open_price', 0),
                            record.get('high_price', 0),
                            record.get('low_price', 0),
                            record.get('close_price', 0),
                            record.get('volume', 0),
                            record.get('spread', 0)
                        ))
                
                if self.auto_commit:
                    conn.commit()
                
                self.total_records_stored += len(data)
                self.operations_count += 1
                
                print(f"✅ Stored {len(data)} market data records")
                return True
                
        except Exception as e:
            print(f"❌ Market data storage error: {e}")
            return False
    
    def store_trade(self, trade_data: Dict) -> bool:
        """
        💰 เก็บข้อมูลการเทรด
        
        Args:
            trade_data: ข้อมูลการเทรด
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO trades 
                    (ticket, symbol, trade_type, volume, open_price, close_price,
                     open_time, close_time, profit, commission, swap, magic_number,
                     comment, strategy, session)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_data.get('ticket'),
                    trade_data.get('symbol', 'XAUUSD'),
                    trade_data.get('trade_type'),
                    trade_data.get('volume'),
                    trade_data.get('open_price'),
                    trade_data.get('close_price'),
                    trade_data.get('open_time'),
                    trade_data.get('close_time'),
                    trade_data.get('profit', 0),
                    trade_data.get('commission', 0),
                    trade_data.get('swap', 0),
                    trade_data.get('magic_number', 0),
                    trade_data.get('comment', ''),
                    trade_data.get('strategy', ''),
                    trade_data.get('session', '')
                ))
                
                if self.auto_commit:
                    conn.commit()
                
                self.total_records_stored += 1
                self.operations_count += 1
                
                print(f"✅ Stored trade: {trade_data.get('ticket')}")
                return True
                
        except Exception as e:
            print(f"❌ Trade storage error: {e}")
            return False
    
    def update_position(self, position_data: Dict) -> bool:
        """
        📊 อัปเดตข้อมูล position
        
        Args:
            position_data: ข้อมูล position
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO positions 
                    (ticket, symbol, position_type, volume, open_price, current_price,
                     unrealized_pnl, open_time, magic_number, comment, strategy,
                     recovery_level, pair_id, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    position_data.get('ticket'),
                    position_data.get('symbol', 'XAUUSD'),
                    position_data.get('position_type'),
                    position_data.get('volume'),
                    position_data.get('open_price'),
                    position_data.get('current_price'),
                    position_data.get('unrealized_pnl', 0),
                    position_data.get('open_time'),
                    position_data.get('magic_number', 0),
                    position_data.get('comment', ''),
                    position_data.get('strategy', ''),
                    position_data.get('recovery_level', 0),
                    position_data.get('pair_id', ''),
                    datetime.now()
                ))
                
                if self.auto_commit:
                    conn.commit()
                
                self.operations_count += 1
                return True
                
        except Exception as e:
            print(f"❌ Position update error: {e}")
            return False
    
    def log_recovery_operation(self, recovery_data: Dict) -> bool:
        """
        🔄 บันทึก recovery operation
        
        Args:
            recovery_data: ข้อมูล recovery
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO recovery_logs 
                    (timestamp, recovery_type, original_ticket, recovery_ticket,
                     recovery_level, original_loss, recovery_volume, success,
                     final_profit, strategy_used, reasoning)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    recovery_data.get('timestamp', datetime.now()),
                    recovery_data.get('recovery_type'),
                    recovery_data.get('original_ticket'),
                    recovery_data.get('recovery_ticket'),
                    recovery_data.get('recovery_level', 0),
                    recovery_data.get('original_loss', 0),
                    recovery_data.get('recovery_volume', 0),
                    recovery_data.get('success', False),
                    recovery_data.get('final_profit', 0),
                    recovery_data.get('strategy_used', ''),
                    recovery_data.get('reasoning', '')
                ))
                
                if self.auto_commit:
                    conn.commit()
                
                self.total_records_stored += 1
                self.operations_count += 1
                
                print(f"✅ Logged recovery operation: {recovery_data.get('recovery_type')}")
                return True
                
        except Exception as e:
            print(f"❌ Recovery log error: {e}")
            return False
    
    def get_market_data(self, symbol: str = 'XAUUSD', timeframe: str = 'M5',
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None,
                       limit: Optional[int] = None) -> pd.DataFrame:
        """
        📈 ดึงข้อมูลตลาด
        
        Args:
            symbol: สัญลักษณ์
            timeframe: ช่วงเวลา
            start_time: เวลาเริ่มต้น
            end_time: เวลาสิ้นสุด
            limit: จำนวนสูงสุด
            
        Returns:
            DataFrame ของข้อมูลตลาด
        """
        try:
            with self._get_connection() as conn:
                query = """
                    SELECT timestamp, open_price as open, high_price as high,
                           low_price as low, close_price as close, volume
                    FROM market_data 
                    WHERE symbol = ? AND timeframe = ?
                """
                params = [symbol, timeframe]
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)
                
                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)
                
                query += " ORDER BY timestamp"
                
                if limit:
                    query += f" LIMIT {limit}"
                
                df = pd.read_sql_query(query, conn, params=params)
                
                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                
                print(f"📈 Retrieved {len(df)} market data records")
                return df
                
        except Exception as e:
            print(f"❌ Market data retrieval error: {e}")
            return pd.DataFrame()
    
    def get_trades_history(self, start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          strategy: Optional[str] = None) -> pd.DataFrame:
        """
        💰 ดึงประวัติการเทรด
        
        Args:
            start_date: วันที่เริ่มต้น
            end_date: วันที่สิ้นสุด
            strategy: กลยุทธ์
            
        Returns:
            DataFrame ของประวัติการเทรด
        """
        try:
            with self._get_connection() as conn:
                query = """
                    SELECT * FROM trades 
                    WHERE close_time IS NOT NULL
                """
                params = []
                
                if start_date:
                    query += " AND open_time >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND close_time <= ?"
                    params.append(end_date)
                
                if strategy:
                    query += " AND strategy = ?"
                    params.append(strategy)
                
                query += " ORDER BY close_time DESC"
                
                df = pd.read_sql_query(query, conn, params=params)
                
                print(f"💰 Retrieved {len(df)} trade records")
                return df
                
        except Exception as e:
            print(f"❌ Trades history retrieval error: {e}")
            return pd.DataFrame()
    
    def get_current_positions(self) -> pd.DataFrame:
        """📊 ดึง positions ปัจจุบัน"""
        try:
            with self._get_connection() as conn:
                query = """
                    SELECT * FROM positions 
                    ORDER BY open_time DESC
                """
                
                df = pd.read_sql_query(query, conn)
                
                print(f"📊 Retrieved {len(df)} current positions")
                return df
                
        except Exception as e:
            print(f"❌ Current positions retrieval error: {e}")
            return pd.DataFrame()
    
    def get_recovery_statistics(self, days_back: int = 30) -> Dict:
        """
        🔄 ดึงสถิติ recovery
        
        Args:
            days_back: จำนวนวันย้อนหลัง
            
        Returns:
            สถิติ recovery
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Total recovery operations
                cursor.execute("""
                    SELECT COUNT(*) as total_recoveries,
                           SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_recoveries,
                           AVG(CASE WHEN success = 1 THEN final_profit ELSE NULL END) as avg_success_profit,
                           AVG(recovery_level) as avg_recovery_level
                    FROM recovery_logs 
                    WHERE timestamp >= ?
                """, (cutoff_date,))
                
                stats = dict(cursor.fetchone())
                
                # Recovery by type
                cursor.execute("""
                    SELECT recovery_type, COUNT(*) as count,
                           AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
                    FROM recovery_logs 
                    WHERE timestamp >= ?
                    GROUP BY recovery_type
                """, (cutoff_date,))
                
                recovery_by_type = {row['recovery_type']: dict(row) for row in cursor.fetchall()}
                
                stats['recovery_by_type'] = recovery_by_type
                stats['success_rate'] = (stats['successful_recoveries'] / stats['total_recoveries'] * 100 
                                       if stats['total_recoveries'] > 0 else 0)
                
                print(f"🔄 Retrieved recovery statistics for {days_back} days")
                return stats
                
        except Exception as e:
            print(f"❌ Recovery statistics error: {e}")
            return {}
    
    def backup_database(self, backup_name: Optional[str] = None) -> bool:
        """
        💾 สำรองข้อมูลฐานข้อมูล
        
        Args:
            backup_name: ชื่อไฟล์สำรอง
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            if backup_name is None:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            
            backup_file = self.backup_path / backup_name
            
            # Copy database file
            shutil.copy2(str(self.db_path), str(backup_file))
            
            # Compress if enabled
            if self.compression_enabled:
                compressed_file = backup_file.with_suffix('.db.gz')
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb', compresslevel=self.compression_level) as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove uncompressed file
                backup_file.unlink()
                backup_file = compressed_file
            
            self.last_backup_time = datetime.now()
            
            print(f"💾 Database backed up to: {backup_file}")
            return True
            
        except Exception as e:
            print(f"❌ Database backup error: {e}")
            return False
    
    def export_data(self, data_type: str, format_type: str = StorageFormat.CSV,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> Optional[str]:
        """
        📤 ส่งออกข้อมูล
        
        Args:
            data_type: ประเภทข้อมูล
            format_type: รูปแบบไฟล์
            start_date: วันที่เริ่มต้น
            end_date: วันที่สิ้นสุด
            
        Returns:
            path ของไฟล์ที่ส่งออก
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if data_type == DataType.TRADES:
                df = self.get_trades_history(start_date, end_date)
                filename = f"trades_export_{timestamp}"
            elif data_type == DataType.MARKET_DATA:
                df = self.get_market_data(start_time=start_date, end_time=end_date)
                filename = f"market_data_export_{timestamp}"
            elif data_type == DataType.POSITIONS:
                df = self.get_current_positions()
                filename = f"positions_export_{timestamp}"
            else:
                print(f"❌ Unsupported data type: {data_type}")
                return None
            
            if df.empty:
                print("❌ No data to export")
                return None
            
            export_path = self.base_path / 'exports'
           
            if format_type == StorageFormat.CSV:
                file_path = export_path / f"{filename}.csv"
                df.to_csv(file_path, index=True)
            elif format_type == StorageFormat.JSON:
                file_path = export_path / f"{filename}.json"
                df.to_json(file_path, orient='records', date_format='iso')
            elif format_type == StorageFormat.PICKLE:
                file_path = export_path / f"{filename}.pkl"
                df.to_pickle(file_path)
            elif format_type == StorageFormat.PARQUET:
                file_path = export_path / f"{filename}.parquet"
                df.to_parquet(file_path)
            else:
                print(f"❌ Unsupported format: {format_type}")
                return None
            
            print(f"📤 Exported {len(df)} records to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            print(f"❌ Data export error: {e}")
            return None
    
    def import_data(self, file_path: str, data_type: str, format_type: str = StorageFormat.CSV) -> bool:
        """
        📥 นำเข้าข้อมูล
        
        Args:
            file_path: path ของไฟล์
            data_type: ประเภทข้อมูล
            format_type: รูปแบบไฟล์
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                return False
            
            # Read data based on format
            if format_type == StorageFormat.CSV:
                df = pd.read_csv(file_path)
            elif format_type == StorageFormat.JSON:
                df = pd.read_json(file_path)
            elif format_type == StorageFormat.PICKLE:
                df = pd.read_pickle(file_path)
            elif format_type == StorageFormat.PARQUET:
                df = pd.read_parquet(file_path)
            else:
                print(f"❌ Unsupported format: {format_type}")
                return False
            
            if df.empty:
                print("❌ No data found in file")
                return False
            
            # Import based on data type
            success = False
            if data_type == DataType.MARKET_DATA:
                # Convert DataFrame to list of dicts
                data_records = df.to_dict('records')
                success = self.store_market_data(data_records)
            elif data_type == DataType.TRADES:
                # Store each trade
                for _, row in df.iterrows():
                    self.store_trade(row.to_dict())
                success = True
            else:
                print(f"❌ Import not supported for data type: {data_type}")
                return False
            
            if success:
                print(f"📥 Imported {len(df)} records from: {file_path}")
            
            return success
            
        except Exception as e:
            print(f"❌ Data import error: {e}")
            return False
    
    def clean_old_data(self, days_to_keep: int = 90) -> bool:
        """
        🧹 ทำความสะอาดข้อมูลเก่า
        
        Args:
            days_to_keep: จำนวนวันที่ต้องการเก็บ
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Archive old data before deletion
                tables_to_clean = [
                    ('market_data', 'timestamp'),
                    ('trades', 'close_time'),
                    ('recovery_logs', 'timestamp'),
                    ('analytics', 'timestamp'),
                    ('system_logs', 'timestamp')
                ]
                
                total_deleted = 0
                
                for table, date_column in tables_to_clean:
                    # Count records to be deleted
                    cursor.execute(f"""
                        SELECT COUNT(*) as count FROM {table} 
                        WHERE {date_column} < ? AND {date_column} IS NOT NULL
                    """, (cutoff_date,))
                    
                    count = cursor.fetchone()['count']
                    
                    if count > 0:
                        # Archive to compressed file first
                        self._archive_old_data(table, date_column, cutoff_date)
                        
                        # Delete old records
                        cursor.execute(f"""
                            DELETE FROM {table} 
                            WHERE {date_column} < ? AND {date_column} IS NOT NULL
                        """, (cutoff_date,))
                        
                        total_deleted += count
                        print(f"🧹 Cleaned {count} records from {table}")
                
                # Vacuum database to reclaim space
                cursor.execute("VACUUM")
                
                conn.commit()
                
                print(f"✅ Cleaned {total_deleted} old records (older than {days_to_keep} days)")
                return True
                
        except Exception as e:
            print(f"❌ Data cleaning error: {e}")
            return False
    
    def _archive_old_data(self, table: str, date_column: str, cutoff_date: datetime):
        """เก็บข้อมูลเก่าลง archive"""
        try:
            archive_filename = f"{table}_{cutoff_date.strftime('%Y%m%d')}.csv.gz"
            archive_file = self.archive_path / archive_filename
            
            # Export old data to compressed CSV
            with self._get_connection() as conn:
                query = f"""
                    SELECT * FROM {table} 
                    WHERE {date_column} < ? AND {date_column} IS NOT NULL
                    ORDER BY {date_column}
                """
                
                df = pd.read_sql_query(query, conn, params=[cutoff_date])
                
                if not df.empty:
                    df.to_csv(archive_file, compression='gzip', index=False)
                    print(f"📦 Archived {len(df)} records from {table} to {archive_file}")
                
        except Exception as e:
            print(f"❌ Archiving error for {table}: {e}")
    
    def optimize_database(self) -> bool:
        """⚡ ปรับปรุงประสิทธิภาพฐานข้อมูล"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                print("⚡ Optimizing database...")
                
                # Update statistics
                cursor.execute("ANALYZE")
                
                # Optimize queries
                cursor.execute("PRAGMA optimize")
                
                # Incremental vacuum if enabled
                if self.auto_vacuum:
                    cursor.execute("PRAGMA incremental_vacuum")
                
                # Rebuild indexes if needed
                cursor.execute("REINDEX")
                
                conn.commit()
                
                self.last_optimization_time = datetime.now()
                
                print("✅ Database optimization completed")
                return True
                
        except Exception as e:
            print(f"❌ Database optimization error: {e}")
            return False
    
    def get_database_statistics(self) -> Dict:
        """📊 ดึงสถิติฐานข้อมูล"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Database size
                stats['database_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)
                
                # Table statistics
                tables = ['market_data', 'trades', 'positions', 'recovery_logs', 
                            'performance', 'analytics', 'system_logs']
                
                table_stats = {}
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    count = cursor.fetchone()['count']
                    table_stats[table] = count
                
                stats['table_records'] = table_stats
                stats['total_records'] = sum(table_stats.values())
                
                # Performance metrics
                stats['operations_count'] = self.operations_count
                stats['total_records_stored'] = self.total_records_stored
                stats['last_backup'] = self.last_backup_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_backup_time else "Never"
                stats['last_optimization'] = self.last_optimization_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_optimization_time else "Never"
                
                # Recent activity (last 24 hours)
                yesterday = datetime.now() - timedelta(days=1)
                
                cursor.execute("""
                    SELECT COUNT(*) as count FROM trades 
                    WHERE created_at >= ?
                """, (yesterday,))
                stats['trades_last_24h'] = cursor.fetchone()['count']
                
                cursor.execute("""
                    SELECT COUNT(*) as count FROM recovery_logs 
                    WHERE timestamp >= ?
                """, (yesterday,))
                stats['recoveries_last_24h'] = cursor.fetchone()['count']
                
                return stats
                
        except Exception as e:
            print(f"❌ Database statistics error: {e}")
            return {'error': str(e)}
    
    def _start_maintenance_thread(self):
        """เริ่ม background maintenance thread"""
        try:
            def maintenance_worker():
                while True:
                    try:
                        # Sleep for 1 hour
                        time.sleep(3600)
                        
                        # Check if database needs optimization
                        db_size_mb = self.db_path.stat().st_size / (1024 * 1024)
                        
                        if db_size_mb > self.max_db_size_mb:
                            print("🔧 Database size limit reached, running maintenance...")
                            
                            # Clean old data
                            self.clean_old_data(self.auto_archive_days)
                            
                            # Optimize database
                            self.optimize_database()
                            
                            # Create backup
                            self.backup_database()
                        
                        # Regular optimization (daily)
                        if (self.last_optimization_time is None or 
                            (datetime.now() - self.last_optimization_time).days >= 1):
                            self.optimize_database()
                        
                        # Regular backup (every 6 hours)
                        if (self.last_backup_time is None or 
                            (datetime.now() - self.last_backup_time).seconds >= 21600):
                            self.backup_database()
                            
                    except Exception as e:
                        print(f"❌ Maintenance worker error: {e}")
            
            # Start maintenance thread
            maintenance_thread = threading.Thread(target=maintenance_worker, daemon=True)
            maintenance_thread.start()
            
            print("🔧 Background maintenance thread started")
            
        except Exception as e:
            print(f"❌ Maintenance thread error: {e}")
    
    def log_system_message(self, level: str, component: str, message: str, details: Optional[str] = None):
        """
        📝 บันทึก system log
        
        Args:
            level: ระดับ (INFO, WARNING, ERROR)
            component: ส่วนประกอบที่เกิดเหตุการณ์
            message: ข้อความ
            details: รายละเอียดเพิ่มเติม
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO system_logs (timestamp, level, component, message, details)
                    VALUES (?, ?, ?, ?, ?)
                """, (datetime.now(), level, component, message, details))
                
                if self.auto_commit:
                    conn.commit()
                
        except Exception as e:
            print(f"❌ System log error: {e}")
    
    def get_system_logs(self, level: Optional[str] = None, 
                        component: Optional[str] = None,
                        hours_back: int = 24) -> List[Dict]:
        """
        📝 ดึง system logs
        
        Args:
            level: ระดับที่ต้องการ
            component: component ที่ต้องการ
            hours_back: จำนวนชั่วโมงย้อนหลัง
            
        Returns:
            รายการ logs
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            with self._get_connection() as conn:
                query = "SELECT * FROM system_logs WHERE timestamp >= ?"
                params = [cutoff_time]
                
                if level:
                    query += " AND level = ?"
                    params.append(level)
                
                if component:
                    query += " AND component = ?"
                    params.append(component)
                
                query += " ORDER BY timestamp DESC"
                
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                logs = [dict(row) for row in cursor.fetchall()]
                
                return logs
                
        except Exception as e:
            print(f"❌ System logs retrieval error: {e}")
            return []
    
    def close(self):
        """ปิด Data Manager"""
        try:
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
            
            print("✅ Data Manager closed successfully")
            
        except Exception as e:
            print(f"❌ Data Manager close error: {e}")

def main():
    """Test the Data Manager"""
    print("🧪 Testing Data Manager...")
    
    # Sample configuration
    config = {
        'data_base_path': 'test_data',
        'auto_commit': True,
        'batch_size': 1000,
        'compression_enabled': True,
        'auto_archive_days': 30,
        'max_db_size_mb': 100
    }
    
    # Initialize data manager
    data_manager = DataManager(config)
    
    # Test market data storage
    sample_market_data = [
        {
            'timestamp': datetime.now() - timedelta(minutes=10),
            'symbol': 'XAUUSD',
            'timeframe': 'M5',
            'open_price': 2000.0,
            'high_price': 2005.0,
            'low_price': 1995.0,
            'close_price': 2002.0,
            'volume': 1000,
            'spread': 0.5
        },
        {
            'timestamp': datetime.now() - timedelta(minutes=5),
            'symbol': 'XAUUSD',
            'timeframe': 'M5',
            'open_price': 2002.0,
            'high_price': 2008.0,
            'low_price': 1998.0,
            'close_price': 2005.0,
            'volume': 1200,
            'spread': 0.4
        }
    ]
    
    success = data_manager.store_market_data(sample_market_data)
    print(f"\n📈 Market data storage: {'✅ Success' if success else '❌ Failed'}")
    
    # Test trade storage
    sample_trade = {
        'ticket': 12345,
        'symbol': 'XAUUSD',
        'trade_type': 'BUY',
        'volume': 0.01,
        'open_price': 2000.0,
        'close_price': 2010.0,
        'open_time': datetime.now() - timedelta(hours=1),
        'close_time': datetime.now(),
        'profit': 10.0,
        'strategy': 'trend_following',
        'session': 'london'
    }
    
    success = data_manager.store_trade(sample_trade)
    print(f"💰 Trade storage: {'✅ Success' if success else '❌ Failed'}")
    
    # Test recovery log
    sample_recovery = {
        'recovery_type': 'martingale_smart',
        'original_ticket': 12345,
        'recovery_ticket': 12346,
        'recovery_level': 1,
        'original_loss': -15.0,
        'recovery_volume': 0.02,
        'success': True,
        'final_profit': 5.0,
        'strategy_used': 'martingale',
        'reasoning': 'Test recovery'
    }
    
    success = data_manager.log_recovery_operation(sample_recovery)
    print(f"🔄 Recovery log: {'✅ Success' if success else '❌ Failed'}")
    
    # Test data retrieval
    market_df = data_manager.get_market_data(limit=10)
    print(f"\n📊 Retrieved market data: {len(market_df)} records")
    
    trades_df = data_manager.get_trades_history()
    print(f"💰 Retrieved trades: {len(trades_df)} records")
    
    # Test statistics
    stats = data_manager.get_database_statistics()
    print(f"\n📊 Database Statistics:")
    print(f"   Database Size: {stats.get('database_size_mb', 0):.2f} MB")
    print(f"   Total Records: {stats.get('total_records', 0)}")
    print(f"   Operations Count: {stats.get('operations_count', 0)}")
    
    # Test recovery statistics
    recovery_stats = data_manager.get_recovery_statistics()
    print(f"\n🔄 Recovery Statistics:")
    print(f"   Total Recoveries: {recovery_stats.get('total_recoveries', 0)}")
    print(f"   Success Rate: {recovery_stats.get('success_rate', 0):.1f}%")
    
    # Test backup
    backup_success = data_manager.backup_database()
    print(f"\n💾 Database backup: {'✅ Success' if backup_success else '❌ Failed'}")
    
    # Clean up
    data_manager.close()
    
    print("\n✅ Data Manager test completed")

if __name__ == "__main__":
   main()