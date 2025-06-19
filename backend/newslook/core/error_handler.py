#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局异常处理器
提供统一的异常处理机制和错误响应格式化
"""

import traceback
import functools
from typing import Dict, Any, Optional, Callable, Union
from datetime import datetime
from flask import Flask, request, jsonify, g
import logging

from .exceptions import NewsLookException, create_exception
from .logger_manager import get_logger


class ErrorHandler:
    """全局异常处理器"""
    
    def __init__(self, app: Flask = None):
        """初始化异常处理器"""
        self.app = app
        self.logger = get_logger('newslook', 'error_handler')
        
        # 错误统计
        self.error_stats = {
            'total_errors': 0,
            'errors_by_type': {},
            'errors_by_endpoint': {},
            'last_error_time': None
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """初始化Flask应用的异常处理"""
        self.app = app
        
        # 注册异常处理器
        app.register_error_handler(NewsLookException, self.handle_newslook_exception)
        app.register_error_handler(Exception, self.handle_generic_exception)
        app.register_error_handler(404, self.handle_not_found)
        app.register_error_handler(500, self.handle_internal_server_error)
        
        # 注册请求前后处理
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_appcontext(self.teardown_request)
    
    def before_request(self):
        """请求前处理"""
        g.request_start_time = datetime.now()
        g.request_id = self._generate_request_id()
        
        # 记录请求开始
        self.logger.info(
            "Request started",
            extra={
                'request_id': g.request_id,
                'method': request.method,
                'url': request.url,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', 'Unknown')
            }
        )
    
    def after_request(self, response):
        """请求后处理"""
        if hasattr(g, 'request_start_time'):
            duration = (datetime.now() - g.request_start_time).total_seconds()
            
            # 记录请求完成
            self.logger.info(
                "Request completed",
                extra={
                    'request_id': getattr(g, 'request_id', 'unknown'),
                    'method': request.method,
                    'url': request.url,
                    'status_code': response.status_code,
                    'duration_ms': round(duration * 1000, 2)
                }
            )
        
        return response
    
    def teardown_request(self, exception=None):
        """请求清理"""
        if exception:
            self._update_error_stats(exception)
    
    def handle_newslook_exception(self, error: NewsLookException):
        """处理NewsLook自定义异常"""
        self._log_exception(error, 'newslook_exception')
        self._update_error_stats(error)
        
        response_data = {
            'success': False,
            'error': {
                'type': error.__class__.__name__,
                'code': error.error_code,
                'message': error.message,
                'context': error.context,
                'timestamp': error.timestamp.isoformat(),
                'request_id': getattr(g, 'request_id', None)
            }
        }
        
        # 根据异常类型设置HTTP状态码
        status_code = self._get_http_status_for_exception(error)
        
        return jsonify(response_data), status_code
    
    def handle_generic_exception(self, error: Exception):
        """处理通用异常"""
        self._log_exception(error, 'generic_exception')
        self._update_error_stats(error)
        
        # 转换为NewsLookException
        newslook_error = NewsLookException(
            message=str(error),
            error_code="INTERNAL_ERROR",
            context={'original_type': error.__class__.__name__}
        )
        
        response_data = {
            'success': False,
            'error': {
                'type': 'InternalError',
                'code': 'INTERNAL_ERROR',
                'message': 'An internal error occurred',
                'request_id': getattr(g, 'request_id', None),
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # 在调试模式下提供更多信息
        if self.app and self.app.debug:
            response_data['error']['debug'] = {
                'original_message': str(error),
                'traceback': traceback.format_exc()
            }
        
        return jsonify(response_data), 500
    
    def handle_not_found(self, error):
        """处理404错误"""
        self._log_exception(error, 'not_found')
        
        response_data = {
            'success': False,
            'error': {
                'type': 'NotFound',
                'code': 'RESOURCE_NOT_FOUND',
                'message': 'The requested resource was not found',
                'request_id': getattr(g, 'request_id', None),
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return jsonify(response_data), 404
    
    def handle_internal_server_error(self, error):
        """处理500错误"""
        self._log_exception(error, 'internal_server_error')
        
        response_data = {
            'success': False,
            'error': {
                'type': 'InternalServerError',
                'code': 'INTERNAL_SERVER_ERROR',
                'message': 'Internal server error occurred',
                'request_id': getattr(g, 'request_id', None),
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return jsonify(response_data), 500
    
    def _log_exception(self, error: Exception, error_type: str):
        """记录异常日志"""
        request_id = getattr(g, 'request_id', 'unknown')
        
        log_data = {
            'request_id': request_id,
            'error_type': error_type,
            'exception_class': error.__class__.__name__,
            'message': str(error),
            'endpoint': request.endpoint if request else None,
            'method': request.method if request else None,
            'url': request.url if request else None,
            'remote_addr': request.remote_addr if request else None
        }
        
        # 添加NewsLook异常的特定信息
        if isinstance(error, NewsLookException):
            log_data.update({
                'error_code': error.error_code,
                'context': error.context
            })
        
        # 记录异常日志
        self.logger.error(
            f"Exception occurred: {error.__class__.__name__}",
            extra=log_data,
            exc_info=True
        )
    
    def _update_error_stats(self, error: Exception):
        """更新错误统计"""
        self.error_stats['total_errors'] += 1
        self.error_stats['last_error_time'] = datetime.now()
        
        # 按异常类型统计
        error_type = error.__class__.__name__
        self.error_stats['errors_by_type'][error_type] = \
            self.error_stats['errors_by_type'].get(error_type, 0) + 1
        
        # 按端点统计
        if request and request.endpoint:
            endpoint = request.endpoint
            self.error_stats['errors_by_endpoint'][endpoint] = \
                self.error_stats['errors_by_endpoint'].get(endpoint, 0) + 1
    
    def _get_http_status_for_exception(self, error: NewsLookException) -> int:
        """根据异常类型获取HTTP状态码"""
        status_mapping = {
            'VALIDATION_ERROR': 400,
            'AUTH_ERROR': 401,
            'AUTHZ_ERROR': 403,
            'RESOURCE_NOT_FOUND': 404,
            'RATE_LIMIT_ERROR': 429,
            'SERVICE_UNAVAILABLE': 503,
            'EXTERNAL_SERVICE_ERROR': 502,
            'CONFIG_ERROR': 500,
            'DATABASE_ERROR': 500,
            'DB_CONNECTION_ERROR': 503,
            'DB_QUERY_ERROR': 500,
            'CRAWLER_ERROR': 500,
            'NETWORK_ERROR': 502,
            'PARSING_ERROR': 500,
            'API_ERROR': 500,
            'BUSINESS_LOGIC_ERROR': 400
        }
        
        return status_mapping.get(error.error_code, 500)
    
    def _generate_request_id(self) -> str:
        """生成请求ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        stats = self.error_stats.copy()
        if stats['last_error_time']:
            stats['last_error_time'] = stats['last_error_time'].isoformat()
        return stats
    
    def reset_error_stats(self):
        """重置错误统计"""
        self.error_stats = {
            'total_errors': 0,
            'errors_by_type': {},
            'errors_by_endpoint': {},
            'last_error_time': None
        }


def handle_exceptions(func: Callable) -> Callable:
    """
    异常处理装饰器
    用于装饰函数，自动处理异常并转换为NewsLook异常
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NewsLookException:
            # NewsLook异常直接抛出
            raise
        except Exception as e:
            # 转换为NewsLook异常
            logger = get_logger('newslook', 'decorator')
            logger.error(f"Exception in {func.__name__}: {str(e)}", exc_info=True)
            
            # 创建NewsLook异常
            newslook_error = NewsLookException(
                message=f"Error in {func.__name__}: {str(e)}",
                error_code="FUNCTION_ERROR",
                context={
                    'function': func.__name__,
                    'original_type': e.__class__.__name__,
                    'args': str(args) if args else None,
                    'kwargs': str(kwargs) if kwargs else None
                }
            )
            raise newslook_error
    
    return wrapper


def handle_database_exceptions(func: Callable) -> Callable:
    """
    数据库异常处理装饰器
    专门处理数据库相关异常
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = get_logger('newslook', 'database')
            logger.error(f"Database error in {func.__name__}: {str(e)}", exc_info=True)
            
            # 根据异常类型创建相应的数据库异常
            if 'connection' in str(e).lower():
                from .exceptions import DatabaseConnectionError
                raise DatabaseConnectionError(
                    message=f"Database connection error in {func.__name__}: {str(e)}",
                    context={'function': func.__name__}
                )
            else:
                from .exceptions import DatabaseError
                raise DatabaseError(
                    message=f"Database error in {func.__name__}: {str(e)}",
                    operation=func.__name__,
                    context={'original_error': str(e)}
                )
    
    return wrapper


def handle_crawler_exceptions(source: str = None):
    """
    爬虫异常处理装饰器
    专门处理爬虫相关异常
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = get_logger('newslook', f'crawler.{source}' if source else 'crawler')
                logger.error(f"Crawler error in {func.__name__}: {str(e)}", exc_info=True)
                
                # 根据异常类型创建相应的爬虫异常
                error_message = str(e).lower()
                
                if 'network' in error_message or 'connection' in error_message:
                    from .exceptions import NetworkError
                    raise NetworkError(
                        message=f"Network error in {func.__name__}: {str(e)}",
                        source=source,
                        context={'function': func.__name__}
                    )
                elif 'parse' in error_message or 'selector' in error_message:
                    from .exceptions import ParsingError
                    raise ParsingError(
                        message=f"Parsing error in {func.__name__}: {str(e)}",
                        source=source,
                        context={'function': func.__name__}
                    )
                elif 'rate limit' in error_message or '429' in error_message:
                    from .exceptions import RateLimitError
                    raise RateLimitError(
                        message=f"Rate limit error in {func.__name__}: {str(e)}",
                        source=source,
                        context={'function': func.__name__}
                    )
                else:
                    from .exceptions import CrawlerError
                    raise CrawlerError(
                        message=f"Crawler error in {func.__name__}: {str(e)}",
                        source=source,
                        context={'function': func.__name__, 'original_error': str(e)}
                    )
        
        return wrapper
    
    return decorator


# 全局错误处理器实例
_error_handler = None

def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器实例"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def init_error_handler(app: Flask) -> ErrorHandler:
    """初始化应用的错误处理器"""
    error_handler = get_error_handler()
    error_handler.init_app(app)
    return error_handler 