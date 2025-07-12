#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一异常处理系统
定义NewsLook系统的自定义异常类层次结构
"""

import traceback
from typing import Optional, Dict, Any
from datetime import datetime


class NewsLookException(Exception):
    """NewsLook系统基础异常类"""
    
    def __init__(self, message: str, error_code: str = None, context: Dict[str, Any] = None):
        """
        初始化异常
        
        Args:
            message: 异常消息
            error_code: 错误代码
            context: 异常上下文信息
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'traceback': self.traceback
        }
    
    def __str__(self):
        context_str = f" (Context: {self.context})" if self.context else ""
        return f"[{self.error_code}] {self.message}{context_str}"


class ConfigurationError(NewsLookException):
    """配置相关异常"""
    
    def __init__(self, message: str, config_key: str = None, **kwargs):
        context = kwargs.pop('context', {})
        if config_key:
            context['config_key'] = config_key
        super().__init__(message, error_code="CONFIG_ERROR", context=context, **kwargs)


class DatabaseError(NewsLookException):
    """数据库相关异常"""
    
    def __init__(self, message: str, database_name: str = None, operation: str = None, **kwargs):
        context = kwargs.pop('context', {})
        if database_name:
            context['database_name'] = database_name
        if operation:
            context['operation'] = operation
        super().__init__(message, error_code="DATABASE_ERROR", context=context, **kwargs)


class DatabaseConnectionError(DatabaseError):
    """数据库连接异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="DB_CONNECTION_ERROR", **kwargs)


class DatabaseQueryError(DatabaseError):
    """数据库查询异常"""
    
    def __init__(self, message: str, query: str = None, **kwargs):
        context = kwargs.pop('context', {})
        if query:
            context['query'] = query
        super().__init__(message, error_code="DB_QUERY_ERROR", context=context, **kwargs)


class CrawlerError(NewsLookException):
    """爬虫相关异常"""
    
    def __init__(self, message: str, source: str = None, url: str = None, **kwargs):
        context = kwargs.pop('context', {})
        if source:
            context['source'] = source
        if url:
            context['url'] = url
        super().__init__(message, error_code="CRAWLER_ERROR", context=context, **kwargs)


class NetworkError(CrawlerError):
    """网络请求异常"""
    
    def __init__(self, message: str, status_code: int = None, **kwargs):
        context = kwargs.pop('context', {})
        if status_code:
            context['status_code'] = status_code
        super().__init__(message, error_code="NETWORK_ERROR", context=context, **kwargs)


class ParsingError(CrawlerError):
    """网页解析异常"""
    
    def __init__(self, message: str, selector: str = None, **kwargs):
        context = kwargs.pop('context', {})
        if selector:
            context['selector'] = selector
        super().__init__(message, error_code="PARSING_ERROR", context=context, **kwargs)


class RateLimitError(CrawlerError):
    """访问频率限制异常"""
    
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        context = kwargs.pop('context', {})
        if retry_after:
            context['retry_after'] = retry_after
        super().__init__(message, error_code="RATE_LIMIT_ERROR", context=context, **kwargs)


class ValidationError(NewsLookException):
    """数据验证异常"""
    
    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        context = kwargs.pop('context', {})
        if field:
            context['field'] = field
        if value is not None:
            context['value'] = str(value)
        super().__init__(message, error_code="VALIDATION_ERROR", context=context, **kwargs)


class APIError(NewsLookException):
    """API相关异常"""
    
    def __init__(self, message: str, endpoint: str = None, method: str = None, **kwargs):
        context = kwargs.pop('context', {})
        if endpoint:
            context['endpoint'] = endpoint
        if method:
            context['method'] = method
        super().__init__(message, error_code="API_ERROR", context=context, **kwargs)


class AuthenticationError(APIError):
    """认证异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="AUTH_ERROR", **kwargs)


class AuthorizationError(APIError):
    """授权异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="AUTHZ_ERROR", **kwargs)


class ResourceNotFoundError(APIError):
    """资源未找到异常"""
    
    def __init__(self, message: str, resource_type: str = None, resource_id: str = None, **kwargs):
        context = kwargs.pop('context', {})
        if resource_type:
            context['resource_type'] = resource_type
        if resource_id:
            context['resource_id'] = resource_id
        super().__init__(message, error_code="RESOURCE_NOT_FOUND", context=context, **kwargs)


class ServiceUnavailableError(NewsLookException):
    """服务不可用异常"""
    
    def __init__(self, message: str, service: str = None, **kwargs):
        context = kwargs.pop('context', {})
        if service:
            context['service'] = service
        super().__init__(message, error_code="SERVICE_UNAVAILABLE", context=context, **kwargs)


class ExternalServiceError(NewsLookException):
    """外部服务异常"""
    
    def __init__(self, message: str, service_name: str = None, response_code: int = None, **kwargs):
        context = kwargs.pop('context', {})
        if service_name:
            context['service_name'] = service_name
        if response_code:
            context['response_code'] = response_code
        super().__init__(message, error_code="EXTERNAL_SERVICE_ERROR", context=context, **kwargs)


class BusinessLogicError(NewsLookException):
    """业务逻辑异常"""
    
    def __init__(self, message: str, operation: str = None, **kwargs):
        context = kwargs.pop('context', {})
        if operation:
            context['operation'] = operation
        super().__init__(message, error_code="BUSINESS_LOGIC_ERROR", context=context, **kwargs)


# 异常映射字典，用于从错误代码创建异常
EXCEPTION_MAPPING = {
    'CONFIG_ERROR': ConfigurationError,
    'DATABASE_ERROR': DatabaseError,
    'DB_CONNECTION_ERROR': DatabaseConnectionError,
    'DB_QUERY_ERROR': DatabaseQueryError,
    'CRAWLER_ERROR': CrawlerError,
    'NETWORK_ERROR': NetworkError,
    'PARSING_ERROR': ParsingError,
    'RATE_LIMIT_ERROR': RateLimitError,
    'VALIDATION_ERROR': ValidationError,
    'API_ERROR': APIError,
    'AUTH_ERROR': AuthenticationError,
    'AUTHZ_ERROR': AuthorizationError,
    'RESOURCE_NOT_FOUND': ResourceNotFoundError,
    'SERVICE_UNAVAILABLE': ServiceUnavailableError,
    'EXTERNAL_SERVICE_ERROR': ExternalServiceError,
    'BUSINESS_LOGIC_ERROR': BusinessLogicError,
}


def create_exception(error_code: str, message: str, **kwargs) -> NewsLookException:
    """
    根据错误代码创建异常实例
    
    Args:
        error_code: 错误代码
        message: 异常消息
        **kwargs: 其他参数
    
    Returns:
        NewsLookException: 异常实例
    """
    exception_class = EXCEPTION_MAPPING.get(error_code, NewsLookException)
    return exception_class(message, **kwargs) 