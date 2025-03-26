#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 配置管理模块

提供统一的配置管理功能，支持从配置文件、环境变量和命令行参数读取配置。
"""

import os
import sys
import configparser
import argparse
from typing import Dict, Any, Optional, Union
import logging

# 移动logging导入位置，确保在系统环境初始化完成之后再导入
# 这里暂时不导入get_logger，稍后处理

class ConfigManager:
    """配置管理类，负责读取和管理所有配置项"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，如果为None，则按默认位置寻找
        """
        self.config = configparser.ConfigParser()
        self.config_loaded = False
        self.config_file = config_file or self._find_config_file()
        
        # 创建一个临时的日志记录器
        self.logger = logging.getLogger("config")
        
        # 加载配置
        self.load_config()
        
        # 命令行参数
        self.args = None
        
        # 环境变量前缀
        self.env_prefix = "NEWSLOOK_"
        
    def _find_config_file(self) -> str:
        """
        查找配置文件，按优先级依次寻找:
        1. 当前目录下的 config.ini
        2. 项目根目录下的 config.ini
        3. /etc/newslook/config.ini (Linux/Unix系统)
        4. %APPDATA%/NewsLook/config.ini (Windows系统)
        
        Returns:
            str: 找到的配置文件路径，如果未找到则使用默认路径
        """
        # 可能的配置文件位置
        possible_locations = [
            "./config.ini",
            "../config.ini",
        ]
        
        # 添加系统特定位置
        if sys.platform.startswith('win'):
            app_data = os.environ.get('APPDATA', '')
            if app_data:
                possible_locations.append(os.path.join(app_data, "NewsLook", "config.ini"))
        else:
            possible_locations.append("/etc/newslook/config.ini")
        
        # 按优先级检查文件是否存在
        for location in possible_locations:
            if os.path.isfile(location):
                print(f"找到配置文件: {location}")
                return location
        
        # 没有找到，返回默认位置
        default_location = "./config.ini"
        print(f"未找到配置文件，将使用默认位置: {default_location}")
        return default_location
    
    def load_config(self) -> bool:
        """
        加载配置文件
        
        Returns:
            bool: 是否成功加载
        """
        try:
            if os.path.isfile(self.config_file):
                self.config.read(self.config_file, encoding='utf-8')
                self.config_loaded = True
                print(f"成功加载配置文件: {self.config_file}")
                return True
            else:
                print(f"配置文件不存在: {self.config_file}")
                return False
        except Exception as e:
            print(f"加载配置文件出错: {str(e)}")
            return False
    
    def parse_args(self, args=None):
        """
        解析命令行参数
        
        Args:
            args: 命令行参数列表，默认为None使用sys.argv
        """
        parser = argparse.ArgumentParser(description="NewsLook 财经新闻爬虫系统")
        
        # 通用参数
        parser.add_argument("--config", help="配置文件路径")
        parser.add_argument("--db-dir", help="数据库目录路径")
        parser.add_argument("--log-level", help="日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL")
        
        # 子命令
        subparsers = parser.add_subparsers(dest="command", help="运行命令")
        
        # 爬虫命令
        crawler_parser = subparsers.add_parser("crawler", help="爬虫模式")
        crawler_parser.add_argument("--source", help="指定爬取的新闻来源")
        crawler_parser.add_argument("--days", type=int, default=1, help="爬取最近几天的新闻")
        
        # 调度器命令
        scheduler_parser = subparsers.add_parser("scheduler", help="调度器模式")
        scheduler_parser.add_argument("--interval", type=int, default=3600, help="调度间隔(秒)")
        
        # Web应用命令
        web_parser = subparsers.add_parser("web", help="Web应用模式")
        web_parser.add_argument("--host", default="0.0.0.0", help="Web服务器地址")
        web_parser.add_argument("--port", type=int, default=8000, help="Web服务器端口")
        web_parser.add_argument("--debug", action="store_true", help="是否启用调试模式")
        
        # 解析参数
        self.args = parser.parse_args(args)
        
        # 如果指定了配置文件，重新加载
        if self.args.config:
            self.config_file = self.args.config
            self.load_config()
        
        return self.args
    
    def get(self, section: str, option: str, fallback: Any = None) -> Any:
        """
        获取配置项，优先级: 命令行参数 > 环境变量 > 配置文件 > 默认值
        
        Args:
            section: 配置节
            option: 配置项
            fallback: 默认值
            
        Returns:
            配置值
        """
        # 1. 检查命令行参数
        cmd_value = self._get_from_args(section, option)
        if cmd_value is not None:
            return cmd_value
        
        # 2. 检查环境变量
        env_value = self._get_from_env(section, option)
        if env_value is not None:
            return env_value
        
        # 3. 检查配置文件
        if self.config_loaded and section in self.config and option in self.config[section]:
            return self.config[section][option]
        
        # 4. 返回默认值
        return fallback
    
    def _get_from_args(self, section: str, option: str) -> Optional[str]:
        """从命令行参数获取配置"""
        if not self.args:
            return None
        
        # 转换格式: section.option -> section_option 
        arg_name = f"{section}_{option}".lower().replace('-', '_')
        
        # 特殊情况处理
        if section.lower() == "database" and option.lower() == "db_dir" and hasattr(self.args, "db_dir"):
            return self.args.db_dir
        elif section.lower() == "web" and option.lower() == "host" and hasattr(self.args, "host"):
            return self.args.host
        elif section.lower() == "web" and option.lower() == "port" and hasattr(self.args, "port"):
            return str(self.args.port)
        
        # 常规检查
        if hasattr(self.args, arg_name):
            value = getattr(self.args, arg_name)
            if value is not None:
                return str(value)
        
        return None
    
    def _get_from_env(self, section: str, option: str) -> Optional[str]:
        """从环境变量获取配置"""
        # 转换格式: NEWSLOOK_SECTION_OPTION
        env_name = f"{self.env_prefix}{section}_{option}".upper()
        return os.environ.get(env_name)
    
    def get_int(self, section: str, option: str, fallback: Optional[int] = None) -> Optional[int]:
        """获取整数类型配置"""
        value = self.get(section, option, fallback)
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            self.logger.warning(f"配置项 {section}.{option} 值 '{value}' 不是有效的整数，使用默认值 {fallback}")
            return fallback
    
    def get_float(self, section: str, option: str, fallback: Optional[float] = None) -> Optional[float]:
        """获取浮点数类型配置"""
        value = self.get(section, option, fallback)
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            self.logger.warning(f"配置项 {section}.{option} 值 '{value}' 不是有效的浮点数，使用默认值 {fallback}")
            return fallback
    
    def get_bool(self, section: str, option: str, fallback: Optional[bool] = None) -> Optional[bool]:
        """获取布尔类型配置"""
        value = self.get(section, option, fallback)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'y', 'on')
        return bool(value)
    
    def get_list(self, section: str, option: str, fallback: Optional[list] = None, delimiter: str = ',') -> Optional[list]:
        """获取列表类型配置（以指定分隔符分隔的字符串）"""
        value = self.get(section, option)
        if value is None:
            return fallback or []
        if isinstance(value, str):
            return [item.strip() for item in value.split(delimiter)]
        if isinstance(value, list):
            return value
        self.logger.warning(f"配置项 {section}.{option} 值 '{value}' 无法转换为列表，使用默认值 {fallback}")
        return fallback or []
    
    def get_db_dir(self) -> str:
        """获取数据库目录路径"""
        db_dir = self.get("Database", "DB_DIR", "data/db")
        # 确保目录存在
        os.makedirs(db_dir, exist_ok=True)
        return db_dir
    
    def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """获取所有配置项"""
        settings = {}
        for section in self.config.sections():
            settings[section] = {}
            for option in self.config[section]:
                settings[section][option] = self.get(section, option)
        return settings
    
    def create_default_config(self) -> bool:
        """创建默认配置文件（如果不存在）"""
        if os.path.exists(self.config_file):
            self.logger.info(f"配置文件已存在: {self.config_file}")
            return False
        
        try:
            # 创建配置对象
            config = configparser.ConfigParser()
            
            # 数据库配置
            config["Database"] = {
                "DB_DIR": "data/db",
                "BACKUP_DIR": "data/db/backup"
            }
            
            # 爬虫配置
            config["Crawler"] = {
                "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "REQUEST_TIMEOUT": "30",
                "MAX_RETRIES": "3",
                "DEFAULT_ENCODING": "utf-8"
            }
            
            # Web应用配置
            config["Web"] = {
                "HOST": "0.0.0.0",
                "PORT": "8000",
                "DEBUG": "False",
                "SECRET_KEY": "newslook_secret_key_change_this_in_production"
            }
            
            # 日志配置
            config["Logging"] = {
                "LOG_LEVEL": "INFO",
                "LOG_FILE": "logs/newslook.log",
                "ROTATE_LOGS": "True",
                "MAX_LOG_SIZE": "10485760",  # 10MB
                "BACKUP_COUNT": "5"
            }
            
            # 创建目录（如果不存在）
            os.makedirs(os.path.dirname(os.path.abspath(self.config_file)), exist_ok=True)
            
            # 写入配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            
            self.logger.info(f"已创建默认配置文件: {self.config_file}")
            
            # 重新加载配置
            self.load_config()
            
            return True
        except Exception as e:
            self.logger.error(f"创建默认配置文件失败: {str(e)}")
            return False

    def update_settings(self, key, value):
        """更新配置项"""
        for section in self.config.sections():
            for option in self.config[section]:
                if option.upper() == key.upper():
                    self.config[section][option] = str(value)
                    return True
        
        # 如果找不到匹配的配置项，可以添加到默认节
        if 'DEFAULT' not in self.config:
            self.config['DEFAULT'] = {}
        self.config['DEFAULT'][key] = str(value)
        return True


# 创建全局配置管理器实例
config_manager = ConfigManager()

# 导出常用函数，方便其他模块使用
def get_config(section: str, option: str, fallback: Any = None) -> Any:
    """获取配置项"""
    return config_manager.get(section, option, fallback)

def get_db_dir() -> str:
    """获取数据库目录"""
    return config_manager.get_db_dir()

def parse_args(args=None):
    """解析命令行参数"""
    return config_manager.parse_args(args)

def get_all_settings() -> Dict[str, Dict[str, Any]]:
    """获取所有配置项"""
    return config_manager.get_all_settings()

def create_default_config() -> bool:
    """创建默认配置文件"""
    return config_manager.create_default_config()

def get_settings():
    """获取所有配置设置"""
    settings = config_manager.get_all_settings() or {}
    
    # 确保DB_DIR设置存在且是绝对路径
    if 'DB_DIR' not in settings or not settings['DB_DIR']:
        # 优先使用环境变量
        if 'DB_DIR' in os.environ and os.environ['DB_DIR']:
            db_dir = os.environ['DB_DIR']
        else:
            # 默认使用项目根目录下的data/db目录
            db_dir = os.path.join(os.getcwd(), 'data', 'db')
        
        # 确保是绝对路径
        if not os.path.isabs(db_dir):
            db_dir = os.path.join(os.getcwd(), db_dir)
            
        settings['DB_DIR'] = db_dir
        logger.info(f"使用数据库目录: {db_dir}")
        
        # 确保目录存在
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"创建数据库目录: {db_dir}")
    
    return settings

# 在所有代码加载完毕后，再初始化日志系统，避免循环导入问题
try:
    from newslook.utils.logger import get_logger
    # 更新日志记录器为正确的日志器
    logger = get_logger("config")
    
    # 更新ConfigManager实例的logger
    config_manager.logger = logger
except ImportError:
    logger = logging.getLogger("config")
    logger.warning("无法导入newslook.utils.logger，使用基本日志记录器")
except Exception as e:
    logger = logging.getLogger("config")
    logger.error(f"初始化日志记录器时出错: {str(e)}") 