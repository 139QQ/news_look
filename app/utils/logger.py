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

# 尝试导入配置文件
try:
    from app.config import LOG_CONFIG, BASE_DIR
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

def configure_logger(name=None, level=None, log_file=None, module=None, 
                    max_bytes=None, backup_count=None, propagate=False):
    """
    统一的日志配置函数
    
    Args:
        name: 日志记录器名称，如果为None则使用根日志记录器
        level: 日志级别，如果为None则从环境变量或配置文件获取
        log_file: 日志文件路径，如果为None则自动生成
        module: 模块名称，用于生成日志文件名
        max_bytes: 日志文件最大大小，超过后会自动滚动
        backup_count: 保留的日志文件数量
        propagate: 是否向父级日志记录器传播日志事件
        
    Returns:
        logger: 日志记录器
    """
    # 获取日志级别
    if level is None:
        level = get_log_level()
    
    # 获取日志记录器
    if name:
        logger = logging.getLogger(name)
    else:
        logger = logging.getLogger()
    
    # 防止重复配置
    if logger.handlers and getattr(logger, '_configured', False):
        return logger
    
    # 设置日志级别
    logger.setLevel(level)
    
    # 清除现有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 创建格式化器
    console_formatter = colorlog.ColoredFormatter(
        COLOR_LOG_FORMAT,
        log_colors=COLOR_DICT
    )
    file_formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 创建文件处理器
    if log_file is None:
        log_dir = get_log_dir()
        if module:
            log_file = os.path.join(log_dir, f"{module}_{datetime.now().strftime('%Y%m%d')}.log")
        else:
            log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
    
    if max_bytes is None:
        max_bytes = LOG_CONFIG.get('max_size', 10 * 1024 * 1024)  # 默认10MB
    
    if backup_count is None:
        backup_count = LOG_CONFIG.get('backup_count', 5)  # 默认5个备份
    
    # 使用RotatingFileHandler来限制日志文件大小
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # 设置是否向父级传播
    logger.propagate = propagate
    
    # 标记为已配置
    setattr(logger, '_configured', True)
    
    return logger

# 兼容旧版API
def setup_logger(name=None, level=None, module=None, max_bytes=None, backup_count=None):
    """
    设置日志记录器 (兼容旧版API)
    """
    return configure_logger(name=name, level=level, module=module, 
                            max_bytes=max_bytes, backup_count=backup_count)

def get_logger(name):
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        logging.Logger: 日志记录器
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return configure_logger(name=name)
    return logger

def get_crawler_logger(name):
    """
    获取爬虫专用日志记录器
    
    Args:
        name: 爬虫名称
    
    Returns:
        logging.Logger: 爬虫专用日志记录器
    """
    return configure_logger(
        name=f'crawler.{name}',
        module=name,
        level=get_log_level()
    )

def get_api_logger():
    """获取API专用日志记录器"""
    return configure_logger(
        name="api",
        module="api",
        level=get_log_level()
    )

def get_web_logger():
    """获取Web服务器专用日志记录器"""
    return configure_logger(
        name="web",
        module="web",
        level=get_log_level()
    )

def get_db_logger():
    """获取数据库专用日志记录器"""
    return configure_logger(
        name="database",
        module="database",
        level=get_log_level()
    )

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

# 在导入模块时初始化根日志记录器
root_logger = configure_logger(level=get_log_level()) 