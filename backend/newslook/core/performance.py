#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控工具
提供性能监控装饰器和工具函数
"""

import time
import functools
from typing import Any, Callable, Dict, Optional
from contextlib import contextmanager

from .logger_manager import log_performance, get_logger

class PerformanceMonitor:
    """性能监控类"""
    
    def __init__(self):
        self.logger = get_logger('performance', 'monitor')
    
    def monitor(self, operation_name: str = None, **kwargs):
        """性能监控装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **func_kwargs):
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                start_time = time.time()
                
                try:
                    result = func(*args, **func_kwargs)
                    duration = time.time() - start_time
                    
                    # 记录成功的操作
                    log_performance(
                        operation=op_name,
                        duration=duration,
                        status='success',
                        **kwargs
                    )
                    
                    self.logger.debug(f"操作 {op_name} 完成，耗时: {duration*1000:.2f}ms")
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    
                    # 记录失败的操作
                    log_performance(
                        operation=op_name,
                        duration=duration,
                        status='error',
                        error=str(e),
                        error_type=type(e).__name__,
                        **kwargs
                    )
                    
                    self.logger.error(f"操作 {op_name} 失败，耗时: {duration*1000:.2f}ms, 错误: {e}")
                    raise
            
            return wrapper
        return decorator
    
    @contextmanager
    def timer(self, operation: str, **kwargs):
        """上下文管理器形式的性能监控"""
        start_time = time.time()
        try:
            yield
            duration = time.time() - start_time
            log_performance(
                operation=operation,
                duration=duration,
                status='success',
                **kwargs
            )
            self.logger.debug(f"操作 {operation} 完成，耗时: {duration*1000:.2f}ms")
            
        except Exception as e:
            duration = time.time() - start_time
            log_performance(
                operation=operation,
                duration=duration,
                status='error',
                error=str(e),
                error_type=type(e).__name__,
                **kwargs
            )
            self.logger.error(f"操作 {operation} 失败，耗时: {duration*1000:.2f}ms, 错误: {e}")
            raise

# 全局性能监控实例
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控实例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

def monitor_performance(operation_name: str = None, **kwargs):
    """性能监控装饰器"""
    return get_performance_monitor().monitor(operation_name, **kwargs)

def performance_timer(operation: str, **kwargs):
    """性能计时上下文管理器"""
    return get_performance_monitor().timer(operation, **kwargs)

# 常用的性能监控装饰器
def monitor_database_operation(operation_name: str = None):
    """数据库操作性能监控装饰器"""
    return monitor_performance(operation_name, category='database')

def monitor_crawler_operation(source: str = None, operation_name: str = None):
    """爬虫操作性能监控装饰器"""
    kwargs = {'category': 'crawler'}
    if source:
        kwargs['source'] = source
    return monitor_performance(operation_name, **kwargs)

def monitor_web_request(endpoint: str = None):
    """Web请求性能监控装饰器"""
    kwargs = {'category': 'web'}
    if endpoint:
        kwargs['endpoint'] = endpoint
    return monitor_performance(endpoint, **kwargs)

def monitor_api_call(api_name: str = None):
    """API调用性能监控装饰器"""
    kwargs = {'category': 'api'}
    return monitor_performance(api_name, **kwargs) 