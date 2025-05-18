#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 爬虫异步接口组件
实现统一的异步/同步双模式接口
"""

import asyncio
import inspect
import logging
import functools
from typing import Dict, List, Any, Optional, Callable, Union, Tuple, TypeVar, Awaitable

from app.utils.logger import get_crawler_logger

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('async_interface')

# 定义类型变量
T = TypeVar('T')

class AsyncCrawlerInterface:
    """爬虫异步接口，提供统一的同步/异步操作接口"""
    
    def __init__(self, name: str, async_mode: bool = False):
        """
        初始化爬虫异步接口
        
        Args:
            name: 爬虫名称
            async_mode: 是否使用异步模式
        """
        self.name = name
        self.async_mode = async_mode
        self.loop = None
        
        logger.info(f"爬虫异步接口初始化成功: {name}, {'异步' if async_mode else '同步'}模式")
    
    def __enter__(self):
        """上下文管理器入口方法"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出方法"""
        self.close()
        return False  # 不处理异常
    
    def close(self):
        """关闭资源"""
        if self.loop and self.async_mode:
            try:
                if hasattr(self, '_close_coro') and inspect.iscoroutinefunction(self._close_coro):
                    if self.loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(self._close_coro(), self.loop)
                        future.result()
                    else:
                        self.loop.run_until_complete(self._close_coro())
            except Exception as e:
                logger.error(f"关闭异步资源失败: {str(e)}")
    
    def set_close_callback(self, close_coro: Callable[[], Awaitable[None]]):
        """
        设置关闭回调协程
        
        Args:
            close_coro: 关闭资源的协程函数
        """
        self._close_coro = close_coro
    
    def run_sync(self, coro_or_func: Union[Callable[..., T], Callable[..., Awaitable[T]]], *args, **kwargs) -> T:
        """
        运行协程或函数（同步模式）
        
        Args:
            coro_or_func: 协程函数或普通函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
        """
        if not self.async_mode:
            # 同步模式下直接调用函数
            if inspect.iscoroutinefunction(coro_or_func):
                raise TypeError("同步模式下不能直接调用协程函数")
            return coro_or_func(*args, **kwargs)
        else:
            # 异步模式下，但需要同步执行
            if inspect.iscoroutinefunction(coro_or_func):
                # 创建新的事件循环来运行协程
                if self.loop is None:
                    self.loop = asyncio.new_event_loop()
                
                if self.loop.is_running():
                    # 如果事件循环已经运行，使用run_coroutine_threadsafe
                    future = asyncio.run_coroutine_threadsafe(coro_or_func(*args, **kwargs), self.loop)
                    return future.result()
                else:
                    # 否则直接运行
                    return self.loop.run_until_complete(coro_or_func(*args, **kwargs))
            else:
                # 普通函数直接调用
                return coro_or_func(*args, **kwargs)
    
    async def run_async(self, coro_or_func: Union[Callable[..., T], Callable[..., Awaitable[T]]], *args, **kwargs) -> T:
        """
        运行协程或函数（异步模式）
        
        Args:
            coro_or_func: 协程函数或普通函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Awaitable[Any]: 函数执行结果
        """
        if not self.async_mode:
            # 同步模式下，但使用异步调用
            if inspect.iscoroutinefunction(coro_or_func):
                # 如果是协程函数，设置一个事件循环来运行
                if self.loop is None:
                    self.loop = asyncio.get_event_loop()
                
                # 直接等待协程
                return await coro_or_func(*args, **kwargs)
            else:
                # 如果是普通函数，使用run_in_executor
                if self.loop is None:
                    self.loop = asyncio.get_event_loop()
                
                return await self.loop.run_in_executor(None, functools.partial(coro_or_func, *args, **kwargs))
        else:
            # 异步模式下
            if inspect.iscoroutinefunction(coro_or_func):
                # 直接等待协程
                return await coro_or_func(*args, **kwargs)
            else:
                # 如果是普通函数，使用run_in_executor
                if self.loop is None:
                    self.loop = asyncio.get_event_loop()
                
                return await self.loop.run_in_executor(None, functools.partial(coro_or_func, *args, **kwargs))
    
    def ensure_future(self, coro: Awaitable[T]) -> 'asyncio.Future[T]':
        """
        确保协程在事件循环中运行
        
        Args:
            coro: 协程对象
            
        Returns:
            asyncio.Future: 代表协程的Future对象
        """
        if not self.async_mode:
            raise RuntimeError("同步模式下不能使用ensure_future")
        
        if self.loop is None:
            self.loop = asyncio.get_event_loop()
        
        return asyncio.ensure_future(coro, loop=self.loop)
    
    def wrap_sync(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        包装同步函数，根据运行模式返回适当的包装后函数
        
        Args:
            func: 同步函数
            
        Returns:
            Callable: 包装后的函数
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.run_sync(func, *args, **kwargs)
        
        return wrapper
    
    def wrap_async(self, coro_func: Callable[..., Awaitable[T]]) -> Union[Callable[..., T], Callable[..., Awaitable[T]]]:
        """
        包装异步函数，根据运行模式返回适当的包装后函数
        
        Args:
            coro_func: 协程函数
            
        Returns:
            Callable: 包装后的函数
        """
        if self.async_mode:
            # 异步模式下返回原协程函数
            return coro_func
        else:
            # 同步模式下返回同步包装器
            @functools.wraps(coro_func)
            def wrapper(*args, **kwargs):
                return self.run_sync(coro_func, *args, **kwargs)
            
            return wrapper
    
    def adapt_method(self, instance: Any, method_name: str) -> Callable:
        """
        适配实例方法，根据当前模式返回同步或异步版本
        
        Args:
            instance: 实例对象
            method_name: 方法名称
            
        Returns:
            Callable: 适配后的方法
        """
        method = getattr(instance, method_name)
        
        if inspect.iscoroutinefunction(method):
            if self.async_mode:
                # 异步模式下返回原协程方法
                return method
            else:
                # 同步模式下返回同步包装器
                @functools.wraps(method)
                def sync_wrapper(*args, **kwargs):
                    return self.run_sync(method, *args, **kwargs)
                
                return sync_wrapper
        else:
            if self.async_mode:
                # 异步模式下返回异步包装器
                @functools.wraps(method)
                async def async_wrapper(*args, **kwargs):
                    return await self.run_async(method, *args, **kwargs)
                
                return async_wrapper
            else:
                # 同步模式下返回原方法
                return method
    
    @staticmethod
    def is_async_function(func: Callable) -> bool:
        """
        检查是否为异步函数
        
        Args:
            func: 函数对象
            
        Returns:
            bool: 是否为异步函数
        """
        return inspect.iscoroutinefunction(func)


def create_interface(name: str, async_mode: bool = False) -> AsyncCrawlerInterface:
    """
    创建爬虫异步接口
    
    Args:
        name: 爬虫名称
        async_mode: 是否使用异步模式
        
    Returns:
        AsyncCrawlerInterface: 爬虫异步接口实例
    """
    return AsyncCrawlerInterface(name, async_mode) 