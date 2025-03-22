import logging
import os
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import traceback

# 尝试导入colorama以支持彩色日志
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLOR_SUPPORT = True
except ImportError:
    COLOR_SUPPORT = False

# 日志级别颜色映射
LOG_COLORS = {
    'DEBUG': '\033[36m',     # 青色
    'INFO': '\033[32m',      # 绿色
    'WARNING': '\033[33m',   # 黄色
    'ERROR': '\033[31m',     # 红色
    'CRITICAL': '\033[35m',  # 紫色
    'RESET': '\033[0m'       # 重置
}

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    def format(self, record):
        """格式化日志记录"""
        # 保存原始的levelname
        levelname = record.levelname
        
        if COLOR_SUPPORT:
            # 根据日志级别设置颜色
            if record.levelno >= logging.CRITICAL:
                color = Fore.MAGENTA
            elif record.levelno >= logging.ERROR:
                color = Fore.RED
            elif record.levelno >= logging.WARNING:
                color = Fore.YELLOW
            elif record.levelno >= logging.INFO:
                color = Fore.GREEN
            else:
                color = Fore.CYAN
                
            # 设置彩色的levelname
            record.levelname = f"{color}{levelname}{Style.RESET_ALL}"
        
        # 调用原始的format方法
        result = super().format(record)
        
        # 恢复原始的levelname
        record.levelname = levelname
        
        return result

def get_log_dir():
    """获取日志目录"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def setup_logger(name=None, level=logging.INFO, module=None, max_bytes=10*1024*1024, backup_count=5):
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称，如果为None则使用root记录器
        level: 日志级别
        module: 模块名称，用于分类日志文件
        max_bytes: 单个日志文件最大字节数，默认10MB
        backup_count: 备份文件数量，默认5个
        
    Returns:
        logger: 配置好的日志记录器
    """
    # 创建日志目录
    log_dir = get_log_dir()
    
    # 设置日志文件名
    if module:
        # 按模块分类日志文件
        module_dir = os.path.join(log_dir, module)
        os.makedirs(module_dir, exist_ok=True)
        log_file = os.path.join(module_dir, f'{module}_{datetime.now().strftime("%Y%m%d")}.log')
    else:
        # 默认日志文件
        log_file = os.path.join(log_dir, f'crawler_{datetime.now().strftime("%Y%m%d")}.log')
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 清除已有的处理器
    if logger.handlers:
        logger.handlers.clear()
    
    # 创建文件处理器（使用RotatingFileHandler实现日志轮转）
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=max_bytes, 
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # 设置日志格式
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # 控制台使用彩色格式
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    file_handler.setFormatter(detailed_formatter)
    console_handler.setFormatter(console_formatter)
    
    # 添加处理器到记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def setup_daily_logger(name=None, level=logging.INFO, module=None):
    """
    设置按天轮转的日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        module: 模块名称
        
    Returns:
        logger: 配置好的日志记录器
    """
    # 创建日志目录
    log_dir = get_log_dir()
    
    # 设置日志文件名
    if module:
        # 按模块分类日志文件
        module_dir = os.path.join(log_dir, module)
        os.makedirs(module_dir, exist_ok=True)
        log_file = os.path.join(module_dir, f'{module}.log')
    else:
        # 默认日志文件
        log_file = os.path.join(log_dir, 'crawler.log')
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 清除已有的处理器
    if logger.handlers:
        logger.handlers.clear()
    
    # 创建文件处理器（使用TimedRotatingFileHandler实现按天轮转）
    file_handler = TimedRotatingFileHandler(
        log_file, 
        when='midnight',
        interval=1,
        backupCount=30,  # 保留30天的日志
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.suffix = "%Y%m%d"  # 日志文件后缀格式
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # 设置日志格式
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # 控制台使用彩色格式
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    file_handler.setFormatter(detailed_formatter)
    console_handler.setFormatter(console_formatter)
    
    # 添加处理器到记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
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

def get_crawler_logger(crawler_name):
    """
    获取爬虫专用日志记录器
    
    Args:
        crawler_name: 爬虫名称
        
    Returns:
        logger: 爬虫专用日志记录器
    """
    return setup_logger(
        name=f"crawler.{crawler_name}",
        module="crawlers",
        level=logging.INFO
    )

def get_api_logger():
    """获取API专用日志记录器"""
    return setup_logger(
        name="api",
        module="api",
        level=logging.INFO
    )

def get_web_logger():
    """获取Web服务器专用日志记录器"""
    return setup_logger(
        name="web",
        module="web",
        level=logging.INFO
    )

def get_db_logger():
    """获取数据库专用日志记录器"""
    return setup_logger(
        name="database",
        module="database",
        level=logging.INFO
    ) 