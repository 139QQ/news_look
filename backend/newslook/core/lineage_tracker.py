#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 数据谱系自动追踪器
通过装饰器自动记录数据操作的血缘关系
"""

import functools
import inspect
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
import logging
import asyncio

from .data_lineage_manager import get_lineage_manager, LineageType

logger = logging.getLogger(__name__)

class LineageTracker:
    """数据谱系追踪器"""
    
    def __init__(self):
        self.lineage_manager = get_lineage_manager()
        self.tracking_enabled = True
    
    def enable_tracking(self):
        """启用追踪"""
        self.tracking_enabled = True
        logger.info("数据谱系追踪已启用")
    
    def disable_tracking(self):
        """禁用追踪"""
        self.tracking_enabled = False
        logger.info("数据谱系追踪已禁用")
    
    def track_crawler_operation(self, 
                               source_name: str,
                               source_url: str = None,
                               target_table: str = "news_data",
                               field_mapping: Dict[str, str] = None):
        """
        爬虫操作追踪装饰器
        
        Args:
            source_name: 数据源名称
            source_url: 源URL
            target_table: 目标表名
            field_mapping: 字段映射关系
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.tracking_enabled:
                    return await func(*args, **kwargs)
                
                # 获取函数参数
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                # 动态获取source_url（如果没有提供）
                actual_source_url = source_url or bound_args.arguments.get('url', 'unknown')
                
                # 获取默认字段映射（如果没有提供）
                actual_field_mapping = field_mapping or {
                    'title': 'title',
                    'content': 'content', 
                    'pub_time': 'pub_time',
                    'url': 'url'
                }
                
                try:
                    # 执行原函数
                    result = await func(*args, **kwargs)
                    
                    # 记录血缘关系
                    await self.lineage_manager.record_crawler_lineage(
                        source_name=source_name,
                        source_url=actual_source_url,
                        target_table=target_table,
                        field_mapping=actual_field_mapping,
                        crawler_type=func.__name__
                    )
                    
                    logger.debug(f"已记录爬虫血缘: {source_name} → {target_table}")
                    return result
                    
                except Exception as e:
                    logger.error(f"爬虫血缘追踪失败: {str(e)}")
                    # 不影响原函数执行
                    return await func(*args, **kwargs)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.tracking_enabled:
                    return func(*args, **kwargs)
                
                # 同步版本，使用asyncio.run执行异步追踪
                try:
                    result = func(*args, **kwargs)
                    
                    # 在后台记录血缘
                    asyncio.create_task(self._record_sync_crawler_lineage(
                        source_name, source_url, target_table, field_mapping, func.__name__
                    ))
                    
                    return result
                except Exception as e:
                    logger.error(f"同步爬虫血缘追踪失败: {str(e)}")
                    return func(*args, **kwargs)
            
            # 根据函数类型返回对应的包装器
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    async def _record_sync_crawler_lineage(self, source_name, source_url, target_table, field_mapping, crawler_type):
        """后台记录同步爬虫血缘"""
        try:
            actual_field_mapping = field_mapping or {
                'title': 'title',
                'content': 'content',
                'pub_time': 'pub_time',
                'url': 'url'
            }
            
            await self.lineage_manager.record_crawler_lineage(
                source_name=source_name,
                source_url=source_url or 'unknown',
                target_table=target_table,
                field_mapping=actual_field_mapping,
                crawler_type=crawler_type
            )
        except Exception as e:
            logger.error(f"后台血缘记录失败: {str(e)}")
    
    def track_api_access(self, 
                        endpoint: str = None,
                        source_table: str = "news_data",
                        query_fields: List[str] = None):
        """
        API访问追踪装饰器
        
        Args:
            endpoint: API端点（自动检测）
            source_table: 数据源表
            query_fields: 查询字段列表
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.tracking_enabled:
                    return await func(*args, **kwargs)
                
                try:
                    # 获取请求信息
                    request = kwargs.get('request') or (args[0] if args and hasattr(args[0], 'url') else None)
                    
                    actual_endpoint = endpoint or (getattr(request, 'url', str(func.__name__)) if request else func.__name__)
                    actual_query_fields = query_fields or ['title', 'content', 'pub_time']
                    
                    client_info = {}
                    if request:
                        client_info = {
                            'client_ip': getattr(request, 'client', {}).get('host', 'unknown'),
                            'user_agent': getattr(request, 'headers', {}).get('user-agent', 'unknown'),
                            'method': getattr(request, 'method', 'GET')
                        }
                    
                    # 执行原函数
                    result = await func(*args, **kwargs)
                    
                    # 记录API访问血缘
                    await self.lineage_manager.record_api_access_lineage(
                        api_endpoint=actual_endpoint,
                        source_table=source_table,
                        query_fields=actual_query_fields,
                        client_info=client_info
                    )
                    
                    logger.debug(f"已记录API访问血缘: {actual_endpoint}")
                    return result
                    
                except Exception as e:
                    logger.error(f"API血缘追踪失败: {str(e)}")
                    return await func(*args, **kwargs)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.tracking_enabled:
                    return func(*args, **kwargs)
                
                try:
                    result = func(*args, **kwargs)
                    
                    # 在后台记录API访问血缘
                    asyncio.create_task(self._record_sync_api_lineage(
                        endpoint or func.__name__, source_table, query_fields or ['title', 'content']
                    ))
                    
                    return result
                except Exception as e:
                    logger.error(f"同步API血缘追踪失败: {str(e)}")
                    return func(*args, **kwargs)
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    async def _record_sync_api_lineage(self, endpoint, source_table, query_fields):
        """后台记录同步API血缘"""
        try:
            await self.lineage_manager.record_api_access_lineage(
                api_endpoint=endpoint,
                source_table=source_table,
                query_fields=query_fields,
                client_info={'source': 'sync_tracking'}
            )
        except Exception as e:
            logger.error(f"后台API血缘记录失败: {str(e)}")
    
    def track_data_transformation(self,
                                source_table: str,
                                target_table: str,
                                transformation_type: str = "数据处理",
                                field_mappings: List[Dict[str, str]] = None):
        """
        数据转换追踪装饰器
        
        Args:
            source_table: 源表
            target_table: 目标表
            transformation_type: 转换类型
            field_mappings: 字段映射列表
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.tracking_enabled:
                    return await func(*args, **kwargs)
                
                try:
                    # 执行原函数
                    result = await func(*args, **kwargs)
                    
                    # 获取默认字段映射
                    actual_field_mappings = field_mappings or [
                        {"source_field": "raw_data", "target_field": "processed_data", "transform_logic": "数据清洗"}
                    ]
                    
                    # 记录转换血缘
                    await self.lineage_manager.record_transformation_lineage(
                        source_table=source_table,
                        target_table=target_table,
                        transformation_type=transformation_type,
                        transformation_rule=f"函数: {func.__name__}",
                        field_mappings=actual_field_mappings
                    )
                    
                    logger.debug(f"已记录数据转换血缘: {source_table} → {target_table}")
                    return result
                    
                except Exception as e:
                    logger.error(f"数据转换血缘追踪失败: {str(e)}")
                    return await func(*args, **kwargs)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.tracking_enabled:
                    return func(*args, **kwargs)
                
                try:
                    result = func(*args, **kwargs)
                    
                    # 在后台记录转换血缘
                    asyncio.create_task(self._record_sync_transformation_lineage(
                        source_table, target_table, transformation_type, field_mappings, func.__name__
                    ))
                    
                    return result
                except Exception as e:
                    logger.error(f"同步转换血缘追踪失败: {str(e)}")
                    return func(*args, **kwargs)
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    async def _record_sync_transformation_lineage(self, source_table, target_table, transformation_type, field_mappings, func_name):
        """后台记录同步转换血缘"""
        try:
            actual_field_mappings = field_mappings or [
                {"source_field": "raw_data", "target_field": "processed_data", "transform_logic": "数据清洗"}
            ]
            
            await self.lineage_manager.record_transformation_lineage(
                source_table=source_table,
                target_table=target_table,
                transformation_type=transformation_type,
                transformation_rule=f"函数: {func_name}",
                field_mappings=actual_field_mappings
            )
        except Exception as e:
            logger.error(f"后台转换血缘记录失败: {str(e)}")


# 全局追踪器实例
_tracker_instance = None

def get_lineage_tracker() -> LineageTracker:
    """获取数据谱系追踪器单例"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = LineageTracker()
    return _tracker_instance

# 便捷装饰器函数
def track_crawler(source_name: str, 
                 source_url: str = None,
                 target_table: str = "news_data",
                 field_mapping: Dict[str, str] = None):
    """爬虫追踪装饰器"""
    return get_lineage_tracker().track_crawler_operation(
        source_name=source_name,
        source_url=source_url,
        target_table=target_table,
        field_mapping=field_mapping
    )

def track_api(endpoint: str = None,
             source_table: str = "news_data", 
             query_fields: List[str] = None):
    """API追踪装饰器"""
    return get_lineage_tracker().track_api_access(
        endpoint=endpoint,
        source_table=source_table,
        query_fields=query_fields
    )

def track_transformation(source_table: str,
                        target_table: str,
                        transformation_type: str = "数据处理",
                        field_mappings: List[Dict[str, str]] = None):
    """数据转换追踪装饰器"""
    return get_lineage_tracker().track_data_transformation(
        source_table=source_table,
        target_table=target_table,
        transformation_type=transformation_type,
        field_mappings=field_mappings
    )

# 上下文管理器
class LineageContext:
    """数据谱系追踪上下文管理器"""
    
    def __init__(self, operation_type: str, metadata: Dict[str, Any] = None):
        self.operation_type = operation_type
        self.metadata = metadata or {}
        self.tracker = get_lineage_tracker()
        self.start_time = None
    
    async def __aenter__(self):
        self.start_time = datetime.now()
        logger.debug(f"开始数据谱系追踪: {self.operation_type}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            logger.debug(f"数据谱系追踪完成: {self.operation_type}, 耗时: {duration:.2f}s")
        else:
            logger.error(f"数据谱系追踪异常: {self.operation_type}, 错误: {exc_val}")
        
        return False  # 不抑制异常 