#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 日志工具
"""

import os
import sys
import logging
import logging.handlers
import colorlog
from datetime import datetime
import traceback
import importlib.util
import time
from logging.handlers import RotatingFileHandler

# 全局日志初始化：移除所有root handler，防止重复日志
if not hasattr(logging.root, '_initialized'):
    # 移除所有默认处理器
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # 禁用第三方库日志
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("chardet").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    
    # 标记root logger已初始化
    logging.root._initialized = True

# 设置最大日志文件大小和备份数量
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

class DuplicateFilter:
    """
    过滤重复日志的过滤器
    在短时间内出现相同内容的日志只记录一次
    """
    def __init__(self):
        self.msgs = {}
        self.patterns = [
            "爬虫管理器使用数据库目录",
            "初始化数据库连接",
            "找到主数据库",
            "找到来源",
            "数据库文件:",
            "连接到现有数据库",
            "初始化爬虫",
            "爬虫初始化完成",
            "已完成爬虫来源属性验证和统一格式化",
            "爬虫管理器初始化完成",
            "已初始化",
            "设置环境变量DB_DIR",
            "使用来源专用数据库"
        ]
        self.timeout = 5  # 5秒内相同日志只显示一次

    def filter(self, record):
        # 检查日志消息是否包含需要过滤的模式
        msg = record.getMessage()
        for pattern in self.patterns:
            if pattern in msg:
                # 创建消息标识
                now = time.time()
                key = f"{record.levelname}:{pattern}"
                
                # 检查是否在短时间内已经记录了类似消息
                if key in self.msgs:
                    if now - self.msgs[key] < self.timeout:
                        return False  # 不记录这条消息
                
                # 更新最后记录时间
                self.msgs[key] = now
                return True
                
        return True  # 不匹配任何过滤模式的消息都记录

# 全局日志器缓存，用于防止重复配置
_logger_cache = {}

# 尝试导入配置文件
try:
    from backend.app.config import LOG_CONFIG, BASE_DIR
except ImportError:
    # 默认日志配置
    LOG_CONFIG = {
        'level': logging.INFO,
        'format': '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        'file': 'logs/finance_news_crawler.log',
        'max_size': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5
    }
    # 尝试获取BASE_DIR
    try:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    except:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 从环境变量或配置文件获取日志级别
LOG_LEVEL = os.environ.get('LOG_LEVEL', '').upper()
if not LOG_LEVEL:
    LOG_LEVEL = 'INFO'

# 从环境变量或配置文件获取日志文件路径
LOG_FILE = os.environ.get('LOG_FILE', '')
if not LOG_FILE:
    LOG_FILE = LOG_CONFIG.get('file', 'logs/finance_news_crawler.log')
    if not os.path.isabs(LOG_FILE):
        LOG_FILE = os.path.join(BASE_DIR, LOG_FILE)

# 日志格式
DEFAULT_LOG_FORMAT = '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
COLOR_LOG_FORMAT = '%(log_color)s%(asctime)s [%(levelname)s] [%(name)s] %(message)s'

# 颜色映射
COLOR_DICT = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}

# 从环境变量获取日志级别
def get_log_level():
    """从环境变量获取日志级别"""
    log_level_str = os.environ.get('LOG_LEVEL', '').upper()
    if log_level_str == 'DEBUG':
        return logging.DEBUG
    elif log_level_str == 'INFO':
        return logging.INFO
    elif log_level_str == 'WARNING':
        return logging.WARNING
    elif log_level_str == 'ERROR':
        return logging.ERROR
    elif log_level_str == 'CRITICAL':
        return logging.CRITICAL
    else:
        return LOG_CONFIG.get('level', logging.INFO)

def get_log_dir():
    """获取日志目录"""
    log_dir = os.environ.get('LOG_DIR')
    if not log_dir:
        log_dir = os.path.join(BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def is_logger_configured(logger):
    """检查日志记录器是否已经配置过"""
    return hasattr(logger, '_configured') and logger._configured

def get_logger(name):
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        logging.Logger: 日志记录器
    """
    # 检查缓存
    global _logger_cache
    if name in _logger_cache:
        return _logger_cache[name]
    
    # 获取或创建日志器
    logger = logging.getLogger(name)
    
    # 如果已有处理器但未被正确配置，清除处理器
    if logger.handlers and not hasattr(logger, '_configured'):
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # 如果未配置，进行配置
    if not hasattr(logger, '_configured') or not logger._configured:
        # 使用新的统一配置函数
        configure_logger()
        # 标记为已配置
        logger._configured = True
    
    _logger_cache[name] = logger
    return logger

def get_crawler_logger(name):
    """
    获取爬虫专用日志记录器
    
    Args:
        name: 爬虫名称
    
    Returns:
        logging.Logger: 爬虫专用日志记录器
    """
    cache_key = f'crawler.{name}'
    if cache_key in _logger_cache:
        return _logger_cache[cache_key]
    
    # 使用统一配置函数配置根日志器
    configure_logger()
    
    # 获取爬虫专用日志器
    logger = logging.getLogger(f"crawler.{name}")
    logger._configured = True
    _logger_cache[cache_key] = logger
    
    return logger

def get_api_logger():
    """获取API专用日志记录器"""
    if 'api' in _logger_cache:
        return _logger_cache['api']
    
    # 使用统一配置函数配置根日志器
    configure_logger()
    
    # 获取API专用日志器
    logger = logging.getLogger("api")
    logger._configured = True
    _logger_cache['api'] = logger
    
    return logger

def get_web_logger():
    """获取Web服务器专用日志记录器"""
    if 'web' in _logger_cache:
        return _logger_cache['web']
    
    # 使用统一配置函数配置根日志器
    configure_logger()
    
    # 获取Web专用日志器
    logger = logging.getLogger("web")
    logger._configured = True
    _logger_cache['web'] = logger
    
    return logger

def get_db_logger():
    """获取数据库专用日志记录器"""
    if 'database' in _logger_cache:
        return _logger_cache['database']
    
    # 使用统一配置函数配置根日志器
    configure_logger()
    
    # 获取数据库专用日志器
    logger = logging.getLogger("database")
    logger._configured = True
    _logger_cache['database'] = logger
    
    return logger

def log_exception(logger, e, message="发生异常"):
    """
    记录异常信息
    
    Args:
        logger: 日志记录器
        e: 异常对象
        message: 异常消息前缀
    """
    logger.error(f"{message}: {str(e)}")
    logger.error(traceback.format_exc())

# 简化的日志函数
def log_info(message, logger_name='finance_news'):
    """记录信息"""
    get_logger(logger_name).info(message)

def log_warning(message, logger_name='finance_news'):
    """记录警告"""
    get_logger(logger_name).warning(message)

def log_error(message, logger_name='finance_news'):
    """记录错误"""
    get_logger(logger_name).error(message)

def log_debug(message, logger_name='finance_news'):
    """记录调试信息"""
    get_logger(logger_name).debug(message)

def log_critical(message, logger_name='finance_news'):
    """记录严重错误"""
    get_logger(logger_name).critical(message)

def configure_logger(level=None, log_dir='logs', config=None):
    """
    配置日志记录器 - 统一的日志配置函数
    
    Args:
        level: 日志级别，默认为None（使用配置中的值）
        log_dir: 日志目录，默认为'logs'
        config: 配置字典，默认为None
    """
    # 如果根日志器已经配置过，直接返回
    if hasattr(logging.root, '_configured') and logging.root._configured:
        return logging.root
        
    if config is None:
        # 尝试导入配置
        try:
            from backend.newslook.config import get_settings
            config = get_settings()
        except:
            config = {}
    
    # 获取日志级别
    if level is None:
        level = config.get('LOG_LEVEL', 'INFO')
    
    # 转换日志级别字符串为常量
    level = getattr(logging, level.upper()) if isinstance(level, str) else level
    
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 移除所有现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加重复过滤器
    duplicate_filter = DuplicateFilter()
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', 
                                         datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(duplicate_filter)
    root_logger.addHandler(console_handler)
    
    # 添加文件处理器（按日期）
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                                       datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(duplicate_filter)
    root_logger.addHandler(file_handler)
    
    # 添加错误日志处理器
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s\n'
                                        'File "%(pathname)s", line %(lineno)d\n',
                                        datefmt='%Y-%m-%d %H:%M:%S')
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)
    
    # 禁用第三方库日志
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("chardet").setLevel(logging.WARNING)
    
    # 设置特定的logger级别
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("flask").setLevel(logging.WARNING)
    
    # 标记为已初始化
    root_logger._configured = True
    
    return root_logger 