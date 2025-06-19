#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NewsLook 核心组件包
包含配置管理、日志系统、异常处理等核心功能
"""

from .config_manager import (
    ConfigManager,
    DatabaseConfig,
    CrawlerConfig,
    WebConfig,
    LoggingConfig,
    get_config_manager,
    get_config
)

from .logger_manager import (
    LoggerManager,
    get_logger_manager,
    get_logger,
    get_app_logger,
    get_crawler_logger,
    get_database_logger,
    get_web_logger,
    get_api_logger,
    log_performance
)

from .performance import (
    PerformanceMonitor,
    get_performance_monitor,
    monitor_performance,
    performance_timer,
    monitor_database_operation,
    monitor_crawler_operation,
    monitor_web_request,
    monitor_api_call
)

__all__ = [
    # 配置管理
    'ConfigManager',
    'DatabaseConfig', 
    'CrawlerConfig',
    'WebConfig',
    'LoggingConfig',
    'get_config_manager',
    'get_config',
    # 日志管理
    'LoggerManager',
    'get_logger_manager',
    'get_logger',
    'get_app_logger',
    'get_crawler_logger',
    'get_database_logger',
    'get_web_logger',
    'get_api_logger',
    'log_performance',
    # 性能监控
    'PerformanceMonitor',
    'get_performance_monitor',
    'monitor_performance',
    'performance_timer',
    'monitor_database_operation',
    'monitor_crawler_operation',
    'monitor_web_request',
    'monitor_api_call'
]

__version__ = '3.1.0' 