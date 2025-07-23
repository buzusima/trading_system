# utilities/configuration_manager.py - Advanced Configuration Management System

import json
import yaml
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import threading
import time
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

class ConfigType(Enum):
    """⚙️ ประเภทการตั้งค่า"""
    SYSTEM = "system"                   # การตั้งค่าระบบ
    TRADING = "trading"                 # การตั้งค่าการเทรด
    RECOVERY = "recovery"               # การตั้งค่า recovery
    RISK = "risk"                       # การตั้งค่าความเสี่ยง
    SESSION = "session"                 # การตั้งค่า session
    STRATEGY = "strategy"               # การตั้งค่ากลยุทธ์
    USER = "user"                       # การตั้งค่าผู้ใช้

class ConfigSource(Enum):
    """📂 แหล่งที่มาของการตั้งค่า"""
    FILE = "file"                       # จากไฟล์
    DATABASE = "database"               # จากฐานข้อมูล
    ENVIRONMENT = "environment"         # จาก environment variables
    DEFAULT = "default"                 # ค่าเริ่มต้น
    RUNTIME = "runtime"                 # กำหนดขณะทำงาน

@dataclass
class ConfigEntry:
    """📝 รายการการตั้งค่า"""
    key: str
    value: Any
    config_type: ConfigType
    source: ConfigSource
    description: str = ""
    validation_rule: str = ""
    last_modified: datetime = None
    is_encrypted: bool = False
    requires_restart: bool = False

class ConfigurationManager:
    """
    ⚙️ Configuration Manager - ระบบจัดการการตั้งค่าขั้นสูง
    
    ⚡ หน้าที่หลัก:
    - จัดการการตั้งค่าทุกประเภทของระบบ
    - โหลดและบันทึกการตั้งค่าจากหลายแหล่ง
    - Validation และ Type checking
    - Hot reload การตั้งค่าขณะทำงาน
    - Backup และ Version control
    - Template และ Profile management
    
    🎯 ความสามารถ:
    - JSON/YAML configuration files
    - Environment variables integration
    - Real-time configuration updates
    - Configuration templates
    - User profiles และ strategy presets
    - Secure sensitive data handling
    - Configuration validation
    - Automatic backups
    """
    
    def __init__(self, config_dir: str = "config"):
        print("⚙️ Initializing Configuration Manager...")
        
        # Paths
        self.config_dir = Path(config_dir)
        self.profiles_dir = self.config_dir / "profiles"
        self.templates_dir = self.config_dir / "templates"
        self.backups_dir = self.config_dir / "backups"
        
        # Create directories
        self._create_directories()
        
        # Configuration storage
        self.configurations = {}  # config_type -> Dict[key, ConfigEntry]
        self.watchers = {}       # file_path -> last_modified_time
        self.change_callbacks = []  # List of callback functions
        
        # Current profile and template
        self.current_profile = "default"
        self.active_template = None
        
        # Validation rules
        self.validation_rules = {}
        self._setup_validation_rules()
        
        # File monitoring
        self.file_watch_enabled = True
        self.watch_interval = 5  # seconds
        
        # Security
        self.encryption_key = self._generate_encryption_key()
        
        # Thread safety
        self.config_lock = threading.Lock()
        
        # Initialize default configurations
        self._initialize_default_configs()
        
        # Load existing configurations
        self._load_all_configurations()
        
        # Start file monitoring
        if self.file_watch_enabled:
            self._start_file_watcher()
        
        print("✅ Configuration Manager initialized")
        print(f"   - Config Directory: {self.config_dir}")
        print(f"   - Current Profile: {self.current_profile}")
        print(f"   - Configurations Loaded: {sum(len(configs) for configs in self.configurations.values())}")
    
    def _create_directories(self):
        """สร้าง directories ที่จำเป็น"""
        try:
            directories = [
                self.config_dir,
                self.profiles_dir,
                self.templates_dir,
                self.backups_dir
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
            
            print(f"📁 Created configuration directories")
            
        except Exception as e:
            print(f"❌ Directory creation error: {e}")
    
    def _initialize_default_configs(self):
        """เริ่มต้นการตั้งค่าเริ่มต้น"""
        try:
            # System Configuration
            system_defaults = {
                'debug_mode': ConfigEntry(
                    key='debug_mode',
                    value=False,
                    config_type=ConfigType.SYSTEM,
                    source=ConfigSource.DEFAULT,
                    description='Enable debug logging',
                    validation_rule='boolean'
                ),
                'log_level': ConfigEntry(
                    key='log_level',
                    value='INFO',
                    config_type=ConfigType.SYSTEM,
                    source=ConfigSource.DEFAULT,
                    description='System log level',
                    validation_rule='string:DEBUG,INFO,WARNING,ERROR'
                ),
                'max_threads': ConfigEntry(
                    key='max_threads',
                    value=4,
                    config_type=ConfigType.SYSTEM,
                    source=ConfigSource.DEFAULT,
                    description='Maximum number of threads',
                    validation_rule='int:1,20'
                )
            }
            
            # Trading Configuration
            trading_defaults = {
                'symbol': ConfigEntry(
                    key='symbol',
                    value='XAUUSD',
                    config_type=ConfigType.TRADING,
                    source=ConfigSource.DEFAULT,
                    description='Trading symbol',
                    validation_rule='string'
                ),
                'base_lot_size': ConfigEntry(
                    key='base_lot_size',
                    value=0.01,
                    config_type=ConfigType.TRADING,
                    source=ConfigSource.DEFAULT,
                    description='Base lot size for trading',
                    validation_rule='float:0.001,10.0'
                ),
                'max_positions': ConfigEntry(
                    key='max_positions',
                    value=10,
                    config_type=ConfigType.TRADING,
                    source=ConfigSource.DEFAULT,
                    description='Maximum open positions',
                    validation_rule='int:1,50'
                ),
                'enable_recovery': ConfigEntry(
                    key='enable_recovery',
                    value=True,
                    config_type=ConfigType.TRADING,
                    source=ConfigSource.DEFAULT,
                    description='Enable recovery trading',
                    validation_rule='boolean'
                )
            }
            
            # Recovery Configuration
            recovery_defaults = {
                'recovery_threshold': ConfigEntry(
                    key='recovery_threshold',
                    value=-20.0,
                    config_type=ConfigType.RECOVERY,
                    source=ConfigSource.DEFAULT,
                    description='Loss threshold to trigger recovery (USD)',
                    validation_rule='float:-1000.0,0.0'
                ),
                'max_recovery_levels': ConfigEntry(
                    key='max_recovery_levels',
                    value=5,
                    config_type=ConfigType.RECOVERY,
                    source=ConfigSource.DEFAULT,
                    description='Maximum recovery levels',
                    validation_rule='int:1,10'
                ),
                'recovery_multiplier': ConfigEntry(
                    key='recovery_multiplier',
                    value=1.8,
                    config_type=ConfigType.RECOVERY,
                    source=ConfigSource.DEFAULT,
                    description='Volume multiplier for recovery',
                    validation_rule='float:1.1,5.0'
                )
            }
            
            # Risk Configuration
            risk_defaults = {
                'max_daily_loss': ConfigEntry(
                    key='max_daily_loss',
                    value=500.0,
                    config_type=ConfigType.RISK,
                    source=ConfigSource.DEFAULT,
                    description='Maximum daily loss (USD)',
                    validation_rule='float:0.0,10000.0'
                ),
                'max_total_exposure': ConfigEntry(
                    key='max_total_exposure',
                    value=5.0,
                    config_type=ConfigType.RISK,
                    source=ConfigSource.DEFAULT,
                    description='Maximum total exposure (lots)',
                    validation_rule='float:0.1,50.0'
                ),
                'risk_per_trade': ConfigEntry(
                    key='risk_per_trade',
                    value=1.0,
                    config_type=ConfigType.RISK,
                    source=ConfigSource.DEFAULT,
                    description='Risk per trade (%)',
                    validation_rule='float:0.1,10.0'
                )
            }
            
            # Session Configuration
            session_defaults = {
                'timezone': ConfigEntry(
                    key='timezone',
                    value='Asia/Bangkok',
                    config_type=ConfigType.SESSION,
                    source=ConfigSource.DEFAULT,
                    description='Local timezone',
                    validation_rule='string'
                ),
                'trading_sessions': ConfigEntry(
                    key='trading_sessions',
                    value=['asian', 'london', 'ny'],
                    config_type=ConfigType.SESSION,
                    source=ConfigSource.DEFAULT,
                    description='Active trading sessions',
                    validation_rule='list'
                )
            }
            
            # Store defaults
            self.configurations = {
                ConfigType.SYSTEM: system_defaults,
                ConfigType.TRADING: trading_defaults,
                ConfigType.RECOVERY: recovery_defaults,
                ConfigType.RISK: risk_defaults,
                ConfigType.SESSION: session_defaults,
                ConfigType.STRATEGY: {},
                ConfigType.USER: {}
            }
            
            print("✅ Default configurations initialized")
            
        except Exception as e:
            print(f"❌ Default config initialization error: {e}")
    
    def _setup_validation_rules(self):
        """ตั้งค่า validation rules"""
        self.validation_rules = {
            'boolean': lambda x: isinstance(x, bool),
            'int': lambda x, min_val=None, max_val=None: (
                isinstance(x, int) and
                (min_val is None or x >= min_val) and
                (max_val is None or x <= max_val)
            ),
            'float': lambda x, min_val=None, max_val=None: (
                isinstance(x, (int, float)) and
                (min_val is None or x >= min_val) and
                (max_val is None or x <= max_val)
            ),
            'string': lambda x, *allowed_values: (
                isinstance(x, str) and
                (not allowed_values or x in allowed_values)
            ),
            'list': lambda x: isinstance(x, list),
            'dict': lambda x: isinstance(x, dict)
        }
    
    def _generate_encryption_key(self) -> str:
        """สร้าง encryption key"""
        try:
            # In production, this should be loaded from secure storage
            key_file = self.config_dir / '.encryption_key'
            
            if key_file.exists():
                with open(key_file, 'r') as f:
                    return f.read().strip()
            else:
                # Generate new key
                import secrets
                key = secrets.token_hex(32)
                
                with open(key_file, 'w') as f:
                    f.write(key)
                
                # Hide the key file
                if os.name == 'nt':  # Windows
                    os.system(f'attrib +h "{key_file}"')
                
                return key
                
        except Exception as e:
            print(f"❌ Encryption key generation error: {e}")
            return "default_key_change_in_production"
    
    def get_config(self, key: str, config_type: ConfigType = None, default: Any = None) -> Any:
        """
        📝 ดึงค่าการตั้งค่า
        
        Args:
            key: คีย์การตั้งค่า
            config_type: ประเภทการตั้งค่า
            default: ค่าเริ่มต้นถ้าไม่พบ
            
        Returns:
            ค่าการตั้งค่า
        """
        try:
            with self.config_lock:
                # Search in specific config type first
                if config_type and config_type in self.configurations:
                    if key in self.configurations[config_type]:
                        return self.configurations[config_type][key].value
                
                # Search across all config types
                for configs in self.configurations.values():
                    if key in configs:
                        return configs[key].value
                
                return default
                
        except Exception as e:
            print(f"❌ Config get error for {key}: {e}")
            return default
    
    def set_config(self, key: str, value: Any, config_type: ConfigType,
                  description: str = "", validation_rule: str = "",
                  source: ConfigSource = ConfigSource.RUNTIME,
                  save_to_file: bool = True) -> bool:
        """
        ✏️ ตั้งค่าการตั้งค่า
        
        Args:
            key: คีย์การตั้งค่า
            value: ค่าใหม่
            config_type: ประเภทการตั้งค่า
            description: คำอธิบาย
            validation_rule: กฎการตรวจสอบ
            source: แหล่งที่มา
            save_to_file: บันทึกลงไฟล์หรือไม่
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            # Validate value
            if validation_rule and not self._validate_value(value, validation_rule):
                print(f"❌ Validation failed for {key}: {value}")
                return False
            
            with self.config_lock:
                # Get existing entry or create new one
                if config_type in self.configurations and key in self.configurations[config_type]:
                    entry = self.configurations[config_type][key]
                    old_value = entry.value
                    entry.value = value
                    entry.last_modified = datetime.now()
                    entry.source = source
                else:
                    entry = ConfigEntry(
                        key=key,
                        value=value,
                        config_type=config_type,
                        source=source,
                        description=description,
                        validation_rule=validation_rule,
                        last_modified=datetime.now()
                    )
                    
                    if config_type not in self.configurations:
                        self.configurations[config_type] = {}
                    
                    self.configurations[config_type][key] = entry
                    old_value = None
                
                # Save to file if requested
                if save_to_file:
                    self._save_config_type(config_type)
                
                # Notify callbacks
                self._notify_config_change(key, old_value, value, config_type)
                
                print(f"✅ Config set: {key} = {value}")
                return True
                
        except Exception as e:
            print(f"❌ Config set error for {key}: {e}")
            return False
    
    def _validate_value(self, value: Any, validation_rule: str) -> bool:
        """ตรวจสอบความถูกต้องของค่า"""
        try:
            if not validation_rule:
                return True
            
            # Parse validation rule
            if ':' in validation_rule:
                rule_type, rule_params = validation_rule.split(':', 1)
                params = rule_params.split(',')
                
                if rule_type in ['int', 'float']:
                    min_val = float(params[0]) if params[0] else None
                    max_val = float(params[1]) if len(params) > 1 and params[1] else None
                    return self.validation_rules[rule_type](value, min_val, max_val)
                elif rule_type == 'string':
                    allowed_values = params if params[0] else []
                    return self.validation_rules[rule_type](value, *allowed_values)
            else:
                rule_type = validation_rule
                if rule_type in self.validation_rules:
                    return self.validation_rules[rule_type](value)
            
            return True
            
        except Exception as e:
            print(f"❌ Validation error: {e}")
            return False
    
    def _notify_config_change(self, key: str, old_value: Any, new_value: Any, config_type: ConfigType):
        """แจ้งเตือนการเปลี่ยนแปลงการตั้งค่า"""
        try:
            for callback in self.change_callbacks:
                try:
                    callback(key, old_value, new_value, config_type)
                except Exception as e:
                    print(f"❌ Config change callback error: {e}")
                    
        except Exception as e:
            print(f"❌ Config change notification error: {e}")
    
    def register_change_callback(self, callback_func):
        """ลงทะเบียน callback สำหรับการเปลี่ยนแปลงการตั้งค่า"""
        try:
            self.change_callbacks.append(callback_func)
            print(f"✅ Registered config change callback")
            
        except Exception as e:
            print(f"❌ Callback registration error: {e}")
    
    def load_from_file(self, file_path: str, config_type: ConfigType = None) -> bool:
        """
        📂 โหลดการตั้งค่าจากไฟล์
        
        Args:
            file_path: path ของไฟล์
            config_type: ประเภทการตั้งค่า
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                print(f"❌ Config file not found: {file_path}")
                return False
            
            # Determine file format
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            elif file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                print(f"❌ Unsupported config file format: {file_path.suffix}")
                return False
            
            if not data:
                return True
            
            # Auto-detect config type from filename if not specified
            if config_type is None:
                filename = file_path.stem.lower()
                for ct in ConfigType:
                    if ct.value in filename:
                        config_type = ct
                        break
                else:
                    config_type = ConfigType.SYSTEM  # default
            
            # Load configurations
            success_count = 0
            for key, value in data.items():
                if isinstance(value, dict) and 'value' in value:
                    # Full ConfigEntry format
                    entry_data = value
                    success = self.set_config(
                        key=key,
                        value=entry_data.get('value'),
                        config_type=config_type,
                        description=entry_data.get('description', ''),
                        validation_rule=entry_data.get('validation_rule', ''),
                        source=ConfigSource.FILE,
                        save_to_file=False
                    )
                else:
                    # Simple key-value format
                    success = self.set_config(
                        key=key,
                        value=value,
                        config_type=config_type,
                        source=ConfigSource.FILE,
                        save_to_file=False
                    )
                
                if success:
                    success_count += 1
            
            # Add to watchers
            self.watchers[str(file_path)] = file_path.stat().st_mtime
            
            print(f"✅ Loaded {success_count} configurations from {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Config file load error: {e}")
            return False
    
    def save_to_file(self, file_path: str, config_type: ConfigType, format_type: str = 'yaml') -> bool:
        """
        💾 บันทึกการตั้งค่าลงไฟล์
        
        Args:
            file_path: path ของไฟล์
            config_type: ประเภทการตั้งค่า
            format_type: รูปแบบไฟล์ (yaml/json)
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            if config_type not in self.configurations:
                print(f"❌ No configurations found for type: {config_type}")
                return False
            
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data
            data = {}
            for key, entry in self.configurations[config_type].items():
                data[key] = {
                    'value': entry.value,
                    'description': entry.description,
                    'validation_rule': entry.validation_rule,
                    'last_modified': entry.last_modified.isoformat() if entry.last_modified else None,
                    'source': entry.source.value
                }
            
            # Save based on format
            if format_type.lower() == 'yaml':
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            elif format_type.lower() == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                print(f"❌ Unsupported format: {format_type}")
                return False
            
            print(f"✅ Saved {len(data)} configurations to {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Config file save error: {e}")
            return False
    
    def _save_config_type(self, config_type: ConfigType):
        """บันทึกการตั้งค่าประเภทหนึ่งลงไฟล์"""
        try:
            filename = f"{config_type.value}_config.yaml"
            file_path = self.config_dir / filename
            self.save_to_file(str(file_path), config_type)
            
        except Exception as e:
            print(f"❌ Config type save error: {e}")
    
    def _load_all_configurations(self):
        """โหลดการตั้งค่าทั้งหมดจากไฟล์"""
        try:
            # Load main config files
            for config_type in ConfigType:
                filename = f"{config_type.value}_config.yaml"
                file_path = self.config_dir / filename
                
                if file_path.exists():
                    self.load_from_file(str(file_path), config_type)
            
            # Load current profile
            self._load_profile(self.current_profile)
            
            print("✅ All configurations loaded")
            
        except Exception as e:
            print(f"❌ Load all configurations error: {e}")
    
    def create_profile(self, profile_name: str, description: str = "") -> bool:
        """
        👤 สร้าง profile ใหม่
        
        Args:
            profile_name: ชื่อ profile
            description: คำอธิบาย
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            profile_file = self.profiles_dir / f"{profile_name}.yaml"
            
            if profile_file.exists():
                print(f"❌ Profile already exists: {profile_name}")
                return False
            
            # Create profile with current configurations
            profile_data = {
                'profile_info': {
                    'name': profile_name,
                    'description': description,
                    'created_at': datetime.now().isoformat(),
                    'version': '1.0'
                },
                'configurations': {}
            }
            
            # Copy current configurations
            for config_type, configs in self.configurations.items():
                if configs:  # Only save non-empty config types
                    profile_data['configurations'][config_type.value] = {}
                    for key, entry in configs.items():
                        profile_data['configurations'][config_type.value][key] = entry.value
            
            # Save profile
            with open(profile_file, 'w', encoding='utf-8') as f:
                yaml.dump(profile_data, f, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ Created profile: {profile_name}")
            return True
            
        except Exception as e:
            print(f"❌ Profile creation error: {e}")
            return False
    
    def load_profile(self, profile_name: str) -> bool:
        """
        👤 โหลด profile
        
        Args:
            profile_name: ชื่อ profile
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            return self._load_profile(profile_name)
            
        except Exception as e:
            print(f"❌ Profile load error: {e}")
            return False
    
    def _load_profile(self, profile_name: str) -> bool:
        """โหลด profile (internal)"""
        try:
            profile_file = self.profiles_dir / f"{profile_name}.yaml"
            
            if not profile_file.exists():
                if profile_name != "default":
                    print(f"❌ Profile not found: {profile_name}")
                return False
            
            with open(profile_file, 'r', encoding='utf-8') as f:
                profile_data = yaml.safe_load(f)
            
            if 'configurations' not in profile_data:
                print(f"❌ Invalid profile format: {profile_name}")
                return False
            
            # Load configurations from profile
            success_count = 0
            for config_type_name, configs in profile_data['configurations'].items():
                try:
                    config_type = ConfigType(config_type_name)
                    for key, value in configs.items():
                        success = self.set_config(
                            key=key,
                            value=value,
                            config_type=config_type,
                            source=ConfigSource.FILE,
                            save_to_file=False
                        )
                        if success:
                            success_count += 1
                except ValueError:
                    print(f"❌ Unknown config type in profile: {config_type_name}")
            
            self.current_profile = profile_name
            print(f"✅ Loaded profile '{profile_name}' with {success_count} configurations")
            return True
            
        except Exception as e:
            print(f"❌ Profile load error: {e}")
            return False
    
    def get_profiles(self) -> List[Dict]:
        """📋 ดึงรายการ profiles"""
        try:
            profiles = []
            
            for profile_file in self.profiles_dir.glob("*.yaml"):
                try:
                    with open(profile_file, 'r', encoding='utf-8') as f:
                        profile_data = yaml.safe_load(f)
                    
                    profile_info = profile_data.get('profile_info', {})
                    profile_info['filename'] = profile_file.name
                    profile_info['file_size'] = profile_file.stat().st_size
                    profile_info['modified_at'] = datetime.fromtimestamp(
                        profile_file.stat().st_mtime
                    ).isoformat()
                    
                    profiles.append(profile_info)
                    
                except Exception as e:
                    print(f"❌ Error reading profile {profile_file}: {e}")
            
            return profiles
            
        except Exception as e:
            print(f"❌ Get profiles error: {e}")
            return []
    
    def backup_configurations(self, backup_name: Optional[str] = None) -> bool:
        """
        💾 สำรองการตั้งค่า
        
        Args:
            backup_name: ชื่อไฟล์สำรอง
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            if backup_name is None:
                backup_name = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_dir = self.backups_dir / backup_name
            backup_dir.mkdir(exist_ok=True)
            
            # Backup all config files
            config_files_backed = 0
            for config_file in self.config_dir.glob("*_config.yaml"):
                shutil.copy2(config_file, backup_dir)
                config_files_backed += 1
            
            # Backup profiles
            profiles_dir_backup = backup_dir / "profiles"
            if self.profiles_dir.exists():
                shutil.copytree(self.profiles_dir, profiles_dir_backup, dirs_exist_ok=True)
            
            # Create backup info
            backup_info = {
                'backup_name': backup_name,
                'created_at': datetime.now().isoformat(),
                'config_files_count': config_files_backed,
                'profiles_count': len(list(self.profiles_dir.glob("*.yaml"))),
                'current_profile': self.current_profile
            }
            
            with open(backup_dir / "backup_info.yaml", 'w') as f:
                yaml.dump(backup_info, f, default_flow_style=False)
            
            print(f"✅ Configuration backup created: {backup_name}")
            return True
            
        except Exception as e:
            print(f"❌ Configuration backup error: {e}")
            return False
   
    def restore_configurations(self, backup_name: str) -> bool:
        """
        📥 กู้คืนการตั้งค่า
        
        Args:
            backup_name: ชื่อไฟล์สำรอง
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            backup_dir = self.backups_dir / backup_name
            
            if not backup_dir.exists():
                print(f"❌ Backup not found: {backup_name}")
                return False
            
            # Read backup info
            backup_info_file = backup_dir / "backup_info.yaml"
            if backup_info_file.exists():
                with open(backup_info_file, 'r') as f:
                    backup_info = yaml.safe_load(f)
                print(f"📥 Restoring backup from {backup_info.get('created_at', 'unknown')}")
            
            # Restore config files
            restored_count = 0
            for backup_file in backup_dir.glob("*_config.yaml"):
                target_file = self.config_dir / backup_file.name
                shutil.copy2(backup_file, target_file)
                restored_count += 1
            
            # Restore profiles
            profiles_backup = backup_dir / "profiles"
            if profiles_backup.exists():
                if self.profiles_dir.exists():
                    shutil.rmtree(self.profiles_dir)
                shutil.copytree(profiles_backup, self.profiles_dir)
            
            # Reload configurations
            self._load_all_configurations()
            
            print(f"✅ Restored {restored_count} configuration files from backup: {backup_name}")
            return True
            
        except Exception as e:
            print(f"❌ Configuration restore error: {e}")
            return False
    
    def _start_file_watcher(self):
        """เริ่ม file watcher thread"""
        try:
            def watch_files():
                while self.file_watch_enabled:
                    try:
                        changes_detected = False
                        
                        # Check config files
                        for config_file in self.config_dir.glob("*_config.yaml"):
                            file_path = str(config_file)
                            current_mtime = config_file.stat().st_mtime
                            
                            if file_path in self.watchers:
                                if current_mtime > self.watchers[file_path]:
                                    print(f"🔄 Config file changed: {config_file.name}")
                                    
                                    # Determine config type from filename
                                    config_type_name = config_file.stem.replace('_config', '')
                                    try:
                                        config_type = ConfigType(config_type_name)
                                        self.load_from_file(file_path, config_type)
                                        changes_detected = True
                                    except ValueError:
                                        print(f"❌ Unknown config type: {config_type_name}")
                            
                            self.watchers[file_path] = current_mtime
                        
                        # Check profile files
                        for profile_file in self.profiles_dir.glob("*.yaml"):
                            file_path = str(profile_file)
                            current_mtime = profile_file.stat().st_mtime
                            
                            if file_path in self.watchers:
                                if current_mtime > self.watchers[file_path]:
                                    print(f"🔄 Profile file changed: {profile_file.name}")
                                    
                                    # Reload if it's the current profile
                                    profile_name = profile_file.stem
                                    if profile_name == self.current_profile:
                                        self._load_profile(profile_name)
                                        changes_detected = True
                            
                            self.watchers[file_path] = current_mtime
                        
                        if changes_detected:
                            print("🔄 Configuration hot-reload completed")
                        
                        time.sleep(self.watch_interval)
                        
                    except Exception as e:
                        print(f"❌ File watcher error: {e}")
                        time.sleep(self.watch_interval)
            
            watcher_thread = threading.Thread(target=watch_files, daemon=True)
            watcher_thread.start()
            
            print("👁️ File watcher started")
            
        except Exception as e:
            print(f"❌ File watcher start error: {e}")
    
    def get_all_configurations(self) -> Dict:
        """📋 ดึงการตั้งค่าทั้งหมด"""
        try:
            all_configs = {}
            
            with self.config_lock:
                for config_type, configs in self.configurations.items():
                    all_configs[config_type.value] = {}
                    for key, entry in configs.items():
                        all_configs[config_type.value][key] = {
                            'value': entry.value,
                            'description': entry.description,
                            'source': entry.source.value,
                            'last_modified': entry.last_modified.isoformat() if entry.last_modified else None,
                            'validation_rule': entry.validation_rule
                        }
            
            return all_configs
            
        except Exception as e:
            print(f"❌ Get all configurations error: {e}")
            return {}
    
    def export_configuration(self, output_file: str, config_types: Optional[List[ConfigType]] = None) -> bool:
        """
        📤 ส่งออกการตั้งค่า
        
        Args:
            output_file: ไฟล์ที่จะส่งออก
            config_types: ประเภทการตั้งค่าที่ต้องการส่งออก
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            if config_types is None:
                config_types = list(ConfigType)
            
            export_data = {
                'export_info': {
                    'created_at': datetime.now().isoformat(),
                    'profile': self.current_profile,
                    'config_types': [ct.value for ct in config_types]
                },
                'configurations': {}
            }
            
            # Export selected config types
            total_exported = 0
            for config_type in config_types:
                if config_type in self.configurations:
                    export_data['configurations'][config_type.value] = {}
                    for key, entry in self.configurations[config_type].items():
                        export_data['configurations'][config_type.value][key] = {
                            'value': entry.value,
                            'description': entry.description,
                            'validation_rule': entry.validation_rule
                        }
                        total_exported += 1
            
            # Save export file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if output_path.suffix.lower() in ['.yaml', '.yml']:
                with open(output_path, 'w', encoding='utf-8') as f:
                    yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Exported {total_exported} configurations to {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Configuration export error: {e}")
            return False
    
    def import_configuration(self, input_file: str, merge: bool = True) -> bool:
        """
        📥 นำเข้าการตั้งค่า
        
        Args:
            input_file: ไฟล์ที่จะนำเข้า
            merge: ผสานกับการตั้งค่าปัจจุบันหรือไม่
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            input_path = Path(input_file)
            
            if not input_path.exists():
                print(f"❌ Import file not found: {input_file}")
                return False
            
            # Read import file
            if input_path.suffix.lower() in ['.yaml', '.yml']:
                with open(input_path, 'r', encoding='utf-8') as f:
                    import_data = yaml.safe_load(f)
            else:
                with open(input_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
            
            if 'configurations' not in import_data:
                print(f"❌ Invalid import file format")
                return False
            
            # Clear existing configurations if not merging
            if not merge:
                self.configurations = {ct: {} for ct in ConfigType}
            
            # Import configurations
            total_imported = 0
            for config_type_name, configs in import_data['configurations'].items():
                try:
                    config_type = ConfigType(config_type_name)
                    for key, config_data in configs.items():
                        if isinstance(config_data, dict) and 'value' in config_data:
                            value = config_data['value']
                            description = config_data.get('description', '')
                            validation_rule = config_data.get('validation_rule', '')
                        else:
                            value = config_data
                            description = ''
                            validation_rule = ''
                        
                        success = self.set_config(
                            key=key,
                            value=value,
                            config_type=config_type,
                            description=description,
                            validation_rule=validation_rule,
                            source=ConfigSource.FILE,
                            save_to_file=False
                        )
                        
                        if success:
                            total_imported += 1
                            
                except ValueError:
                    print(f"❌ Unknown config type in import: {config_type_name}")
            
            # Save imported configurations
            for config_type in ConfigType:
                if config_type in self.configurations and self.configurations[config_type]:
                    self._save_config_type(config_type)
            
            print(f"✅ Imported {total_imported} configurations from {input_file}")
            return True
            
        except Exception as e:
            print(f"❌ Configuration import error: {e}")
            return False
    
    def validate_all_configurations(self) -> Dict:
        """
        ✅ ตรวจสอบการตั้งค่าทั้งหมด
        
        Returns:
            ผลการตรวจสอบ
        """
        try:
            validation_results = {
                'total_configs': 0,
                'valid_configs': 0,
                'invalid_configs': 0,
                'errors': []
            }
            
            with self.config_lock:
                for config_type, configs in self.configurations.items():
                    for key, entry in configs.items():
                        validation_results['total_configs'] += 1
                        
                        if entry.validation_rule:
                            is_valid = self._validate_value(entry.value, entry.validation_rule)
                            if is_valid:
                                validation_results['valid_configs'] += 1
                            else:
                                validation_results['invalid_configs'] += 1
                                validation_results['errors'].append({
                                    'config_type': config_type.value,
                                    'key': key,
                                    'value': entry.value,
                                    'validation_rule': entry.validation_rule,
                                    'error': 'Validation failed'
                                })
                        else:
                            validation_results['valid_configs'] += 1
            
            validation_results['success_rate'] = (
                validation_results['valid_configs'] / validation_results['total_configs'] * 100
                if validation_results['total_configs'] > 0 else 100
            )
            
            print(f"✅ Configuration validation completed")
            print(f"   Total: {validation_results['total_configs']}")
            print(f"   Valid: {validation_results['valid_configs']}")
            print(f"   Invalid: {validation_results['invalid_configs']}")
            print(f"   Success Rate: {validation_results['success_rate']:.1f}%")
            
            return validation_results
            
        except Exception as e:
            print(f"❌ Configuration validation error: {e}")
            return {'error': str(e)}
    
    def get_configuration_summary(self) -> Dict:
        """📊 ดึงสรุปการตั้งค่า"""
        try:
            summary = {
                'profile': self.current_profile,
                'total_configurations': 0,
                'config_types': {},
                'recent_changes': [],
                'file_watchers': len(self.watchers),
                'backup_count': len(list(self.backups_dir.glob('*'))),
                'profiles_count': len(list(self.profiles_dir.glob('*.yaml')))
            }
            
            # Count configurations by type
            recent_cutoff = datetime.now() - timedelta(hours=24)
            
            with self.config_lock:
                for config_type, configs in self.configurations.items():
                    count = len(configs)
                    summary['total_configurations'] += count
                    summary['config_types'][config_type.value] = count
                    
                    # Recent changes
                    for key, entry in configs.items():
                        if entry.last_modified and entry.last_modified > recent_cutoff:
                            summary['recent_changes'].append({
                                'key': key,
                                'config_type': config_type.value,
                                'modified_at': entry.last_modified.isoformat(),
                                'source': entry.source.value
                            })
            
            # Sort recent changes by time
            summary['recent_changes'].sort(
                key=lambda x: x['modified_at'], reverse=True
            )
            summary['recent_changes'] = summary['recent_changes'][:10]  # Last 10
            
            return summary
            
        except Exception as e:
            print(f"❌ Configuration summary error: {e}")
            return {'error': str(e)}
    
    def reset_to_defaults(self, config_type: ConfigType = None) -> bool:
        """
        🔄 รีเซ็ตเป็นค่าเริ่มต้น
        
        Args:
            config_type: ประเภทการตั้งค่าที่ต้องการรีเซ็ต (หรือทั้งหมด)
            
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            if config_type is None:
                # Reset all configurations
                self._initialize_default_configs()
                
                # Save all config types
                for ct in ConfigType:
                    self._save_config_type(ct)
                
                print("✅ All configurations reset to defaults")
            else:
                # Reset specific config type
                if config_type in self.configurations:
                    # Get default values for this type
                    temp_manager = ConfigurationManager.__new__(ConfigurationManager)
                    temp_manager.configurations = {}
                    temp_manager._initialize_default_configs()
                    
                    if config_type in temp_manager.configurations:
                        self.configurations[config_type] = temp_manager.configurations[config_type]
                        self._save_config_type(config_type)
                        
                        print(f"✅ {config_type.value} configurations reset to defaults")
                    else:
                        self.configurations[config_type] = {}
                        print(f"✅ {config_type.value} configurations cleared")
                else:
                    print(f"❌ Config type not found: {config_type}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Reset to defaults error: {e}")
            return False
    
    def stop_file_watcher(self):
        """หยุด file watcher"""
        self.file_watch_enabled = False
        print("👁️ File watcher stopped")
    
    def close(self):
        """ปิด Configuration Manager"""
        try:
            self.stop_file_watcher()
            
            # Save any pending changes
            for config_type in ConfigType:
                if config_type in self.configurations and self.configurations[config_type]:
                    self._save_config_type(config_type)
            
            print("✅ Configuration Manager closed successfully")
            
        except Exception as e:
            print(f"❌ Configuration Manager close error: {e}")

def main():
    """Test the Configuration Manager"""
    print("🧪 Testing Configuration Manager...")
    
    # Initialize configuration manager
    config_manager = ConfigurationManager("test_config")
    
    # Test basic get/set operations
    print(f"\n📝 Testing basic operations...")
    
    # Get default values
    debug_mode = config_manager.get_config('debug_mode')
    print(f"   Debug mode (default): {debug_mode}")
    
    base_lot = config_manager.get_config('base_lot_size')
    print(f"   Base lot size (default): {base_lot}")
    
    # Set new values
    success = config_manager.set_config(
        'custom_setting', 
        42, 
        ConfigType.USER, 
        description='Test custom setting'
    )
    print(f"   Set custom setting: {'✅ Success' if success else '❌ Failed'}")
    
    # Test validation
    success = config_manager.set_config(
        'invalid_lot_size', 
        -1.0, 
        ConfigType.TRADING, 
        validation_rule='float:0.001,10.0'
    )
    print(f"   Set invalid lot size: {'❌ Correctly rejected' if not success else '✅ Incorrectly accepted'}")
    
    # Test profile creation
    print(f"\n👤 Testing profile management...")
    
    success = config_manager.create_profile('test_profile', 'Test profile for demo')
    print(f"   Create profile: {'✅ Success' if success else '❌ Failed'}")
    
    profiles = config_manager.get_profiles()
    print(f"   Available profiles: {len(profiles)}")
    for profile in profiles:
        print(f"     - {profile.get('name', 'Unknown')}: {profile.get('description', 'No description')}")
    
    # Test export/import
    print(f"\n📤 Testing export/import...")
    
    export_file = "test_config_export.yaml"
    success = config_manager.export_configuration(export_file, [ConfigType.SYSTEM, ConfigType.TRADING])
    print(f"   Export configuration: {'✅ Success' if success else '❌ Failed'}")
    
    # Test backup
    print(f"\n💾 Testing backup...")
    
    success = config_manager.backup_configurations("test_backup")
    print(f"   Create backup: {'✅ Success' if success else '❌ Failed'}")
    
    # Test validation
    print(f"\n✅ Testing validation...")
    
    validation_results = config_manager.validate_all_configurations()
    print(f"   Validation results:")
    print(f"     Total configs: {validation_results.get('total_configs', 0)}")
    print(f"     Valid configs: {validation_results.get('valid_configs', 0)}")
    print(f"     Success rate: {validation_results.get('success_rate', 0):.1f}%")
    
    # Test summary
    print(f"\n📊 Testing summary...")
    
    summary = config_manager.get_configuration_summary()
    print(f"   Configuration summary:")
    print(f"     Profile: {summary.get('profile', 'Unknown')}")
    print(f"     Total configurations: {summary.get('total_configurations', 0)}")
    print(f"     Recent changes: {len(summary.get('recent_changes', []))}")
    
    # Register a change callback
    def config_change_callback(key, old_value, new_value, config_type):
        print(f"   🔄 Config changed: {key} = {old_value} -> {new_value} ({config_type.value})")
    
    config_manager.register_change_callback(config_change_callback)
    
    # Test callback
    config_manager.set_config('test_callback', 'test_value', ConfigType.USER)
    
    # Clean up
    config_manager.close()
    
    print("\n✅ Configuration Manager test completed")

if __name__ == "__main__":
   main()