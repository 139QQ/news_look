#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置管理器
支持YAML配置文件和环境变量覆盖
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = "sqlite"
    db_dir: str = "data/db"
    main_db: str = "data/db/finance_news.db"
    pool_size: int = 10
    timeout: int = 30
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    backup_retention_days: int = 30
    sources: Dict[str, str] = None

@dataclass
class CrawlerConfig:
    """爬虫配置"""
    concurrent: int = 5
    delay: float = 1.0
    timeout: int = 30
    retry_attempts: int = 3
    user_agents: list = None
    headers: Dict[str, str] = None

@dataclass
class WebConfig:
    """Web服务配置"""
    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = True
    secret_key: str = "newslook-dev-secret-key"
    cors_enabled: bool = True
    cors_origins: list = None
    rate_limiting_enabled: bool = True
    rate_limit_per_minute: int = 60

@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    console_enabled: bool = True
    file_enabled: bool = True
    file_path: str = "data/logs"
    max_size_mb: int = 10
    backup_count: int = 5

class ConfigManager:
    """统一配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认使用configs/app.yaml
        """
        self.logger = logging.getLogger(__name__)
        
        # 确定配置文件路径
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            self.config_path = project_root / "configs" / "app.yaml"
        else:
            self.config_path = Path(config_path)
            
        # 加载配置
        self._config = self._load_config()
        
        # 创建配置对象
        self._database_config = None
        self._crawler_config = None
        self._web_config = None
        self._logging_config = None
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                self.logger.warning(f"配置文件不存在: {self.config_path}")
                return self._get_default_config()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            self.logger.info(f"成功加载配置文件: {self.config_path}")
            return self._apply_env_overrides(config)
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'app': {
                'name': 'NewsLook',
                'version': '3.1',
                'description': '财经新闻爬虫系统'
            },
            'database': {
                'type': 'sqlite',
                'db_dir': 'data/db',
                'main_db': 'data/db/finance_news.db',
                'pool_size': 10,
                'timeout': 30,
                'backup': {
                    'enabled': True,
                    'interval_hours': 24,
                    'retention_days': 30
                },
                'sources': {
                    'eastmoney': 'eastmoney.db',
                    'sina': 'sina.db',
                    'netease': 'netease.db',
                    'ifeng': 'ifeng.db',
                    'tencent': 'tencent.db'
                }
            },
            'crawler': {
                'concurrent': 5,
                'delay': 1,
                'timeout': 30,
                'retry_attempts': 3,
                'user_agents': [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                ],
                'headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive'
                }
            },
            'web': {
                'host': '127.0.0.1',
                'port': 5000,
                'debug': True,
                'secret_key': 'newslook-dev-secret-key',
                'cors': {
                    'enabled': True,
                    'origins': ['http://localhost:3000']
                },
                'rate_limiting': {
                    'enabled': True,
                    'requests_per_minute': 60
                }
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                'handlers': {
                    'console': {
                        'enabled': True,
                        'level': 'INFO'
                    },
                    'file': {
                        'enabled': True,
                        'level': 'DEBUG',
                        'path': 'data/logs',
                        'max_size_mb': 10,
                        'backup_count': 5
                    }
                }
            },
            'features': {
                'scheduler': True,
                'api': True,
                'web_interface': True,
                'monitoring': True
            }
        }
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用环境变量覆盖"""
        # 常见的环境变量映射
        env_mappings = {
            'NEWSLOOK_DEBUG': ('web', 'debug'),
            'NEWSLOOK_HOST': ('web', 'host'),
            'NEWSLOOK_PORT': ('web', 'port'),
            'NEWSLOOK_DB_DIR': ('database', 'db_dir'),
            'NEWSLOOK_LOG_LEVEL': ('logging', 'level'),
            'NEWSLOOK_CRAWLER_CONCURRENT': ('crawler', 'concurrent'),
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # 类型转换
                if key in ['debug']:
                    value = value.lower() in ('true', '1', 'yes')
                elif key in ['port', 'concurrent', 'pool_size', 'timeout']:
                    value = int(value)
                elif key in ['delay']:
                    value = float(value)
                
                # 设置值
                if section in config:
                    config[section][key] = value
                
                self.logger.info(f"环境变量覆盖: {env_var} -> {section}.{key} = {value}")
        
        return config
    
    @property
    def database(self) -> DatabaseConfig:
        """获取数据库配置"""
        if self._database_config is None:
            db_config = self._config.get('database', {})
            backup_config = db_config.get('backup', {})
            
            self._database_config = DatabaseConfig(
                type=db_config.get('type', 'sqlite'),
                db_dir=db_config.get('db_dir', 'data/db'),
                main_db=db_config.get('main_db', 'data/db/finance_news.db'),
                pool_size=db_config.get('pool_size', 10),
                timeout=db_config.get('timeout', 30),
                backup_enabled=backup_config.get('enabled', True),
                backup_interval_hours=backup_config.get('interval_hours', 24),
                backup_retention_days=backup_config.get('retention_days', 30),
                sources=db_config.get('sources', {})
            )
        
        return self._database_config
    
    @property
    def crawler(self) -> CrawlerConfig:
        """获取爬虫配置"""
        if self._crawler_config is None:
            crawler_config = self._config.get('crawler', {})
            
            self._crawler_config = CrawlerConfig(
                concurrent=crawler_config.get('concurrent', 5),
                delay=crawler_config.get('delay', 1.0),
                timeout=crawler_config.get('timeout', 30),
                retry_attempts=crawler_config.get('retry_attempts', 3),
                user_agents=crawler_config.get('user_agents', []),
                headers=crawler_config.get('headers', {})
            )
        
        return self._crawler_config
    
    @property
    def web(self) -> WebConfig:
        """获取Web配置"""
        if self._web_config is None:
            web_config = self._config.get('web', {})
            cors_config = web_config.get('cors', {})
            rate_limit_config = web_config.get('rate_limiting', {})
            
            self._web_config = WebConfig(
                host=web_config.get('host', '127.0.0.1'),
                port=web_config.get('port', 5000),
                debug=web_config.get('debug', True),
                secret_key=web_config.get('secret_key', 'newslook-dev-secret-key'),
                cors_enabled=cors_config.get('enabled', True),
                cors_origins=cors_config.get('origins', []),
                rate_limiting_enabled=rate_limit_config.get('enabled', True),
                rate_limit_per_minute=rate_limit_config.get('requests_per_minute', 60)
            )
        
        return self._web_config
    
    @property
    def logging(self) -> LoggingConfig:
        """获取日志配置"""
        if self._logging_config is None:
            log_config = self._config.get('logging', {})
            file_config = log_config.get('handlers', {}).get('file', {})
            
            self._logging_config = LoggingConfig(
                level=log_config.get('level', 'INFO'),
                format=log_config.get('format', '%(asctime)s [%(levelname)s] %(message)s'),
                console_enabled=log_config.get('handlers', {}).get('console', {}).get('enabled', True),
                file_enabled=file_config.get('enabled', True),
                file_path=file_config.get('path', 'data/logs'),
                max_size_mb=file_config.get('max_size_mb', 10),
                backup_count=file_config.get('backup_count', 5)
            )
        
        return self._logging_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点分割的键路径"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_app_info(self) -> Dict[str, str]:
        """获取应用信息"""
        app_config = self._config.get('app', {})
        return {
            'name': app_config.get('name', 'NewsLook'),
            'version': app_config.get('version', '3.1'),
            'description': app_config.get('description', '财经新闻爬虫系统')
        }
    
    def is_feature_enabled(self, feature: str) -> bool:
        """检查功能是否启用"""
        return self._config.get('features', {}).get(feature, False)
    
    def reload(self):
        """重新加载配置"""
        self._config = self._load_config()
        self._database_config = None
        self._crawler_config = None
        self._web_config = None
        self._logging_config = None
        self.logger.info("配置已重新加载")

# 全局配置管理器实例
_config_manager = None

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_config() -> ConfigManager:
    """获取配置管理器的简化别名"""
    return get_config_manager() 