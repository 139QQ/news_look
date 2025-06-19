#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NewsLook 财经新闻爬虫系统主包
统一的模块导入和包管理
"""

# 版本信息
__version__ = '3.1.0'
__author__ = 'NewsLook Team'
__description__ = '财经新闻爬虫系统'

# 核心组件导入
from .core import (
    get_config, 
    get_config_manager,
    get_logger,
    get_app_logger,
    get_crawler_logger,
    get_database_logger,
    get_web_logger,
    get_api_logger,
    log_performance
)

# 常用工具导入
try:
    from .utils.database import NewsDatabase
except ImportError:
    # 处理循环导入的情况
    pass

# 包信息
__all__ = [
    # 配置管理
    'get_config',
    'get_config_manager',
    # 日志管理
    'get_logger',
    'get_app_logger',
    'get_crawler_logger', 
    'get_database_logger',
    'get_web_logger',
    'get_api_logger',
    'log_performance',
    # 数据库
    'NewsDatabase',
    # 元信息
    '__version__'
]
