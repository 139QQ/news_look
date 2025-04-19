#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 日志工具
"""

import os
import logging
import logging.handlers
import colorlog
from datetime import datetime
import traceback

# 全局日志器缓存，用于防止重复配置
_logger_cache = {}

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
    except Exception as e:
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

# 日志格式 - 统一标准格式
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
    return hasattr(logger, '_configured') and getattr(logger, '_configured', False)

def configure_logger(name, level=None, log_file=None, module=None, 
                   max_bytes=10*1024*1024, backup_count=5, propagate=True):
    """
    配置日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径
        module: 模块名
        max_bytes: 日志文件最大字节数
        backup_count: 备份文件数量
        propagate: 是否传播日志事件
    
    Returns:
        logger: 配置好的日志器
    """
    global _logger_cache
    
    # 生成唯一的logger_id
    logger_id = f"{name}_{module or ''}"
    
    # 如果已经配置过该日志器，直接返回
    if logger_id in _logger_cache:
        return _logger_cache[logger_id]
    
    # 获取日志级别
    if level is None:
        level = logging.INFO if not LOG_LEVEL else getattr(logging, LOG_LEVEL, logging.INFO)
    
    # 获取日志文件路径
    if log_file is None:
        log_file = LOG_FILE
    
    # 创建日志目录
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 获取或创建日志器
    logger = logging.getLogger(name)
    
    # 检查是否已有相同的处理器，如果有则移除
    existing_handlers = []
    for handler in logger.handlers:
        # 检查是否为文件处理器并且指向相同文件
        if isinstance(handler, logging.handlers.RotatingFileHandler) and hasattr(handler, 'baseFilename'):
            if os.path.abspath(handler.baseFilename) == os.path.abspath(log_file):
                existing_handlers.append(handler)
        # 检查是否为控制台处理器
        elif isinstance(handler, logging.StreamHandler) and handler.stream.name in ('<stdout>', '<stderr>'):
            existing_handlers.append(handler)
    
    # 移除已存在的处理器
    for handler in existing_handlers:
        logger.removeHandler(handler)
    
    # 设置日志级别
    logger.setLevel(level)
    
    # 设置日志传播
    logger.propagate = propagate
    
    # 创建处理器
    # 添加文件处理器
    if log_file:
        # 根据模块名修改日志文件名
        if module:
            log_basename = os.path.basename(log_file)
            log_dirname = os.path.dirname(log_file)
            module_log_file = os.path.join(log_dirname, f"{module}_{log_basename}")
        else:
            module_log_file = log_file
        
        file_handler = logging.handlers.RotatingFileHandler(
            module_log_file, 
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        # 确保使用统一的日志格式
        file_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
        logger.addHandler(file_handler)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    # 确保使用统一的彩色日志格式
    console_handler.setFormatter(colorlog.ColoredFormatter(
        COLOR_LOG_FORMAT,
        log_colors=COLOR_DICT
    ))
    logger.addHandler(console_handler)
    
    # 缓存已配置的日志器
    _logger_cache[logger_id] = logger
    
    return logger

def get_logger(name):
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        logging.Logger: 日志记录器
    """
    # 检查缓存
    if name in _logger_cache:
        return _logger_cache[name]
    
    logger = logging.getLogger(name)
    if not is_logger_configured(logger):
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
    global _logger_cache
    cache_key = f'crawler.{name}'
    if cache_key in _logger_cache:
        return _logger_cache[cache_key]
    
    # 先获取logger对象
    logger = logging.getLogger(cache_key)
    
    # 如果已有处理器，先清空，避免添加重复的处理器导致日志重复输出
    if logger.handlers:
        logger.handlers = []
    
    # 确保日志目录存在
    try:
        from app.config import get_settings
        settings = get_settings()
        log_dir = settings.LOG_DIR
    except (ImportError, AttributeError):
        # 使用默认日志目录
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
    
    # 创建爬虫专用日志目录
    crawler_log_dir = os.path.join(log_dir, name)
    os.makedirs(crawler_log_dir, exist_ok=True)
    
    # 构建日志文件路径 - 使用统一的日期格式 YYYYMMDD
    today = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(crawler_log_dir, f"{name}_{today}.log")
    
    # 设置日志级别
    level = get_log_level()
    logger.setLevel(level)
    
    # 防止日志传播导致重复
    logger.propagate = False
    
    # 添加文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=LOG_CONFIG.get('max_size', 10 * 1024 * 1024),
        backupCount=LOG_CONFIG.get('backup_count', 5),
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = colorlog.ColoredFormatter(
        COLOR_LOG_FORMAT,
        log_colors=COLOR_DICT
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 标记为已配置
    setattr(logger, '_configured', True)
    
    # 缓存已配置的日志器
    _logger_cache[cache_key] = logger
    
    # 记录初始化信息
    logger.info(f"爬虫日志记录器 '{name}' 已初始化，日志文件: {log_file}")
    
    return logger

def get_api_logger():
    """获取API专用日志记录器"""
    if 'api' in _logger_cache:
        return _logger_cache['api']
    
    return configure_logger(
        name="api",
        module="api",
        level=get_log_level(),
        propagate=False
    )

def get_web_logger():
    """获取Web服务器专用日志记录器"""
    if 'web' in _logger_cache:
        return _logger_cache['web']
    
    return configure_logger(
        name="web",
        module="web",
        level=get_log_level(),
        propagate=False
    )

def get_db_logger():
    """获取数据库专用日志记录器"""
    if 'database' in _logger_cache:
        return _logger_cache['database']
    
    return configure_logger(
        name="database",
        module="database",
        level=get_log_level(),
        propagate=False
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