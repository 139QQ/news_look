#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志管理器
基于新配置管理器的结构化日志系统
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json

from .config_manager import get_config

class JsonFormatter(logging.Formatter):
    """JSON格式化器 - 输出结构化日志"""
    
    def __init__(self, include_extra_fields=True):
        super().__init__()
        self.include_extra_fields = include_extra_fields
    
    def format(self, record):
        """格式化日志记录为JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if self.include_extra_fields and hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                              'pathname', 'filename', 'module', 'lineno', 
                              'funcName', 'created', 'msecs', 'relativeCreated', 
                              'thread', 'threadName', 'processName', 'process',
                              'exc_info', 'exc_text', 'stack_info']:
                    log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False)

class ColoredFormatter(logging.Formatter):
    """彩色控制台格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m'       # 重置
    }
    
    def format(self, record):
        """格式化带颜色的日志"""
        # 获取原始格式化结果
        log_message = super().format(record)
        
        # 添加颜色
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        return f"{color}{log_message}{reset}"

class LoggerManager:
    """统一日志管理器"""
    
    def __init__(self):
        """初始化日志管理器"""
        self.config = get_config()
        self.log_config = self.config.logging
        self.loggers = {}
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志系统"""
        # 确保日志目录存在
        log_dir = Path(self.log_config.file_path)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置根日志级别
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_config.level.upper()))
        
        # 清除现有的处理器
        root_logger.handlers.clear()
        
        # 设置日志格式
        console_format = self.log_config.format
        file_format = self.log_config.format
        
        # 创建控制台处理器
        if self.log_config.console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.log_config.level.upper()))
            
            # 使用彩色格式化器
            console_formatter = ColoredFormatter(console_format)
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # 创建文件处理器
        if self.log_config.file_enabled:
            # 主日志文件
            main_log_file = log_dir / "newslook.log"
            file_handler = logging.handlers.RotatingFileHandler(
                main_log_file,
                maxBytes=self.log_config.max_size_mb * 1024 * 1024,
                backupCount=self.log_config.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            
            # 使用普通格式化器
            file_formatter = logging.Formatter(file_format)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            
            # JSON格式日志文件（用于日志分析）
            json_log_file = log_dir / "newslook.json"
            json_handler = logging.handlers.RotatingFileHandler(
                json_log_file,
                maxBytes=self.log_config.max_size_mb * 1024 * 1024,
                backupCount=self.log_config.backup_count,
                encoding='utf-8'
            )
            json_handler.setLevel(logging.INFO)
            json_formatter = JsonFormatter()
            json_handler.setFormatter(json_formatter)
            root_logger.addHandler(json_handler)
    
    def get_logger(self, name: str, module: str = None) -> logging.Logger:
        """获取模块专用的日志记录器"""
        # 构建完整的日志器名称
        if module:
            full_name = f"{name}.{module}"
        else:
            full_name = name
        
        # 如果已存在，直接返回
        if full_name in self.loggers:
            return self.loggers[full_name]
        
        # 创建新的日志记录器
        logger = logging.getLogger(full_name)
        
        # 设置日志级别
        logger.setLevel(getattr(logging, self.log_config.level.upper()))
        
        # 添加模块专用的文件处理器（如果配置了）
        if self.log_config.file_enabled and module:
            self._setup_module_handler(logger, module)
        
        self.loggers[full_name] = logger
        return logger
    
    def _setup_module_handler(self, logger: logging.Logger, module: str):
        """为特定模块设置专用的日志处理器"""
        log_dir = Path(self.log_config.file_path)
        
        # 模块专用日志文件
        module_log_file = log_dir / f"{module}.log"
        module_handler = logging.handlers.RotatingFileHandler(
            module_log_file,
            maxBytes=self.log_config.max_size_mb * 1024 * 1024,
            backupCount=self.log_config.backup_count,
            encoding='utf-8'
        )
        module_handler.setLevel(logging.DEBUG)
        
        # 使用带模块标识的格式
        module_format = f"%(asctime)s [{module.upper()}] [%(levelname)s] %(message)s"
        module_formatter = logging.Formatter(module_format)
        module_handler.setFormatter(module_formatter)
        
        logger.addHandler(module_handler)
    
    def setup_performance_logging(self):
        """设置性能监控日志"""
        perf_logger = self.get_logger('performance', 'perf')
        
        log_dir = Path(self.log_config.file_path)
        perf_log_file = log_dir / "performance.log"
        
        # 性能日志处理器
        perf_handler = logging.handlers.RotatingFileHandler(
            perf_log_file,
            maxBytes=self.log_config.max_size_mb * 1024 * 1024,
            backupCount=self.log_config.backup_count,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        
        # JSON格式用于性能分析
        perf_formatter = JsonFormatter()
        perf_handler.setFormatter(perf_formatter)
        perf_logger.addHandler(perf_handler)
        
        return perf_logger
    
    def log_performance(self, operation: str, duration: float, **kwargs):
        """记录性能指标"""
        perf_logger = self.get_logger('performance', 'perf')
        
        perf_data = {
            'operation': operation,
            'duration_ms': round(duration * 1000, 2),
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        perf_logger.info("Performance metric", extra=perf_data)
    
    def create_context_logger(self, base_logger: logging.Logger, **context):
        """创建带上下文的日志记录器"""
        class ContextAdapter(logging.LoggerAdapter):
            def process(self, msg, kwargs):
                # 添加上下文信息到额外字段
                if 'extra' not in kwargs:
                    kwargs['extra'] = {}
                kwargs['extra'].update(context)
                return msg, kwargs
        
        return ContextAdapter(base_logger, context)
    
    def get_app_logger(self) -> logging.Logger:
        """获取应用主日志记录器"""
        return self.get_logger('newslook', 'app')
    
    def get_crawler_logger(self, source: str = None) -> logging.Logger:
        """获取爬虫日志记录器"""
        if source:
            return self.get_logger('newslook.crawler', f'crawler.{source}')
        return self.get_logger('newslook.crawler', 'crawler')
    
    def get_database_logger(self) -> logging.Logger:
        """获取数据库日志记录器"""
        return self.get_logger('newslook.database', 'database')
    
    def get_web_logger(self) -> logging.Logger:
        """获取Web日志记录器"""
        return self.get_logger('newslook.web', 'web')
    
    def get_api_logger(self) -> logging.Logger:
        """获取API日志记录器"""
        return self.get_logger('newslook.api', 'api')
    
    def shutdown(self):
        """关闭日志系统"""
        # 刷新所有处理器
        for handler in logging.getLogger().handlers:
            handler.flush()
            handler.close()
        
        # 关闭所有日志记录器
        logging.shutdown()

# 全局日志管理器实例
_logger_manager = None

def get_logger_manager() -> LoggerManager:
    """获取全局日志管理器实例"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    return _logger_manager

def get_logger(name: str = 'newslook', module: str = None) -> logging.Logger:
    """获取日志记录器的便捷函数"""
    return get_logger_manager().get_logger(name, module)

def get_app_logger() -> logging.Logger:
    """获取应用日志记录器"""
    return get_logger_manager().get_app_logger()

def get_crawler_logger(source: str = None) -> logging.Logger:
    """获取爬虫日志记录器"""
    return get_logger_manager().get_crawler_logger(source)

def get_database_logger() -> logging.Logger:
    """获取数据库日志记录器"""
    return get_logger_manager().get_database_logger()

def get_web_logger() -> logging.Logger:
    """获取Web日志记录器"""
    return get_logger_manager().get_web_logger()

def get_api_logger() -> logging.Logger:
    """获取API日志记录器"""
    return get_logger_manager().get_api_logger()

def log_performance(operation: str, duration: float, **kwargs):
    """记录性能指标的便捷函数"""
    get_logger_manager().log_performance(operation, duration, **kwargs)