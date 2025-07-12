"""
NewsLook 后端统一错误处理工具
包含自定义异常类、错误装饰器、重试机制、错误上报等
"""

import os
import sys
import json
import time
import logging
import traceback
import functools
from typing import Dict, Any, Optional, Type, Callable, Union
from datetime import datetime
from dataclasses import dataclass, asdict

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.utils.logger import setup_logger

# 设置日志
logger = setup_logger()

# 自定义异常类
class NewsLookError(Exception):
    """NewsLook基础异常类"""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        self.timestamp = time.time()

class DatabaseError(NewsLookError):
    """数据库操作异常"""
    pass

class CrawlerError(NewsLookError):
    """爬虫相关异常"""
    pass

class NetworkError(NewsLookError):
    """网络请求异常"""
    pass

class ConfigurationError(NewsLookError):
    """配置错误异常"""
    pass

class ValidationError(NewsLookError):
    """数据验证异常"""
    pass

class DataNotFoundError(NewsLookError):
    """数据不存在异常"""
    pass

class RateLimitError(NewsLookError):
    """频率限制异常"""
    pass

class AuthenticationError(NewsLookError):
    """认证失败异常"""
    pass

class PermissionError(NewsLookError):
    """权限不足异常"""
    pass

@dataclass
class ErrorReport:
    """错误报告数据结构"""
    error_type: str
    message: str
    code: str
    stack_trace: str
    timestamp: float
    module: str
    function: str
    line_number: int
    details: Dict[str, Any]
    context: Dict[str, Any]
    severity: str  # info, warning, error, critical

class ErrorCollector:
    """错误收集器"""
    
    def __init__(self):
        self.errors = []
        self.max_errors = 1000
    
    def collect_error(self, 
                     error: Exception, 
                     context: Dict[str, Any] = None,
                     severity: str = 'error') -> str:
        """收集错误信息"""
        try:
            # 获取调用栈信息
            tb = traceback.extract_tb(error.__traceback__) if error.__traceback__ else []
            stack_trace = traceback.format_exception(type(error), error, error.__traceback__)
            
            # 获取最后一个调用点的信息
            if tb:
                last_frame = tb[-1]
                module = last_frame.filename
                function = last_frame.name
                line_number = last_frame.lineno
            else:
                module = "unknown"
                function = "unknown"
                line_number = 0
            
            # 创建错误报告
            error_report = ErrorReport(
                error_type=type(error).__name__,
                message=str(error),
                code=getattr(error, 'code', type(error).__name__),
                stack_trace=''.join(stack_trace),
                timestamp=time.time(),
                module=os.path.basename(module),
                function=function,
                line_number=line_number,
                details=getattr(error, 'details', {}),
                context=context or {},
                severity=severity
            )
            
            # 生成错误ID
            error_id = f"error_{int(error_report.timestamp)}_{len(self.errors)}"
            
            # 添加到错误列表
            self.errors.append((error_id, asdict(error_report)))
            
            # 限制错误数量
            if len(self.errors) > self.max_errors:
                self.errors = self.errors[-500:]
            
            # 记录日志
            self._log_error(error_report, error_id)
            
            return error_id
            
        except Exception as e:
            logger.error(f"收集错误信息失败: {str(e)}")
            return "error_collection_failed"
    
    def _log_error(self, error_report: ErrorReport, error_id: str):
        """记录错误日志"""
        log_extra = {
            'error_id': error_id,
            'error_type': error_report.error_type,
            'module': error_report.module,
            'function': error_report.function,
            'line_number': error_report.line_number
        }
        
        if error_report.severity == 'critical':
            logger.critical(f"[{error_id}] {error_report.message}", extra=log_extra)
        elif error_report.severity == 'error':
            logger.error(f"[{error_id}] {error_report.message}", extra=log_extra)
        elif error_report.severity == 'warning':
            logger.warning(f"[{error_id}] {error_report.message}", extra=log_extra)
        else:
            logger.info(f"[{error_id}] {error_report.message}", extra=log_extra)
    
    def get_errors(self, limit: int = 100) -> list:
        """获取错误列表"""
        return self.errors[-limit:]
    
    def get_error_by_id(self, error_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取错误信息"""
        for eid, error_data in self.errors:
            if eid == error_id:
                return error_data
        return None
    
    def clear_errors(self):
        """清空错误列表"""
        self.errors.clear()

# 全局错误收集器实例
error_collector = ErrorCollector()

def handle_exceptions(severity: str = 'error', 
                     reraise: bool = True,
                     fallback_result: Any = None,
                     context: Dict[str, Any] = None):
    """异常处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 收集错误信息
                error_context = (context or {}).copy()
                error_context.update({
                    'function': func.__name__,
                    'module': func.__module__,
                    'args': str(args)[:200],  # 限制长度
                    'kwargs': str(kwargs)[:200]
                })
                
                error_id = error_collector.collect_error(e, error_context, severity)
                
                # 是否重新抛出异常
                if reraise:
                    # 为自定义异常添加错误ID
                    if isinstance(e, NewsLookError):
                        e.details['error_id'] = error_id
                    raise e
                else:
                    return fallback_result
        return wrapper
    return decorator

def retry_on_failure(max_attempts: int = 3,
                    delay: float = 1.0,
                    backoff_factor: float = 2.0,
                    exceptions: tuple = (Exception,),
                    context: Dict[str, Any] = None):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    
                    # 最后一次尝试失败，抛出异常
                    if attempt >= max_attempts:
                        error_context = (context or {}).copy()
                        error_context.update({
                            'function': func.__name__,
                            'attempts': attempt,
                            'max_attempts': max_attempts
                        })
                        error_collector.collect_error(e, error_context, 'error')
                        raise e
                    
                    # 记录重试信息
                    logger.warning(f"函数 {func.__name__} 第 {attempt} 次尝试失败，{current_delay}秒后重试: {str(e)}")
                    
                    # 等待后重试
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
        return wrapper
    return decorator

def validate_data(schema: Dict[str, Any], data: Dict[str, Any]) -> bool:
    """数据验证函数"""
    try:
        for field, field_type in schema.items():
            if field not in data:
                raise ValidationError(f"缺少必需字段: {field}")
            
            value = data[field]
            
            # 类型检查
            if field_type == 'string' and not isinstance(value, str):
                raise ValidationError(f"字段 {field} 应为字符串类型")
            elif field_type == 'number' and not isinstance(value, (int, float)):
                raise ValidationError(f"字段 {field} 应为数字类型")
            elif field_type == 'boolean' and not isinstance(value, bool):
                raise ValidationError(f"字段 {field} 应为布尔类型")
            elif field_type == 'list' and not isinstance(value, list):
                raise ValidationError(f"字段 {field} 应为列表类型")
            elif field_type == 'dict' and not isinstance(value, dict):
                raise ValidationError(f"字段 {field} 应为字典类型")
        
        return True
        
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"数据验证失败: {str(e)}")

def safe_database_operation(operation: Callable, 
                          connection_getter: Callable = None,
                          max_retries: int = 3,
                          context: Dict[str, Any] = None) -> Any:
    """安全的数据库操作包装器"""
    @retry_on_failure(max_attempts=max_retries, exceptions=(DatabaseError,), context=context)
    @handle_exceptions(severity='error', context=context)
    def _safe_operation():
        try:
            # 如果提供了连接获取器，使用它获取连接
            if connection_getter:
                with connection_getter() as conn:
                    return operation(conn)
            else:
                return operation()
        except Exception as e:
            # 将数据库相关异常转换为自定义异常
            raise DatabaseError(f"数据库操作失败: {str(e)}", details={'original_error': str(e)})
    
    return _safe_operation()

def safe_network_request(request_func: Callable,
                        max_retries: int = 3,
                        timeout: float = 30.0,
                        context: Dict[str, Any] = None) -> Any:
    """安全的网络请求包装器"""
    @retry_on_failure(
        max_attempts=max_retries, 
        delay=2.0,
        exceptions=(NetworkError,), 
        context=context
    )
    @handle_exceptions(severity='warning', context=context)
    def _safe_request():
        try:
            return request_func()
        except Exception as e:
            # 检查是否为网络相关错误
            if any(keyword in str(e).lower() for keyword in 
                   ['connection', 'timeout', 'network', 'unreachable', 'dns']):
                raise NetworkError(f"网络请求失败: {str(e)}", details={'original_error': str(e)})
            else:
                raise e
    
    return _safe_request()

class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self.error_callbacks = {}
    
    def register_error_callback(self, error_type: Type[Exception], callback: Callable):
        """注册错误回调函数"""
        self.error_callbacks[error_type] = callback
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> str:
        """处理错误"""
        error_id = error_collector.collect_error(error, context)
        
        # 执行注册的回调函数
        error_type = type(error)
        if error_type in self.error_callbacks:
            try:
                self.error_callbacks[error_type](error, error_id, context)
            except Exception as callback_error:
                logger.error(f"错误回调函数执行失败: {str(callback_error)}")
        
        return error_id
    
    def create_error_response(self, error: Exception, include_details: bool = False) -> Dict[str, Any]:
        """创建错误响应"""
        error_id = self.handle_error(error)
        
        response = {
            'success': False,
            'error': {
                'type': type(error).__name__,
                'message': str(error),
                'code': getattr(error, 'code', type(error).__name__),
                'error_id': error_id,
                'timestamp': time.time()
            }
        }
        
        # 开发环境或明确要求时包含详细信息
        if include_details and isinstance(error, NewsLookError):
            response['error']['details'] = error.details
        
        return response

# 全局错误处理器实例
error_handler = ErrorHandler()

def flask_error_handler(error: Exception):
    """Flask错误处理函数"""
    from flask import current_app, jsonify
    
    # 判断是否为开发环境
    include_details = current_app.config.get('DEBUG', False)
    
    # 创建错误响应
    response_data = error_handler.create_error_response(error, include_details)
    
    # 根据错误类型确定HTTP状态码
    status_code = 500
    if isinstance(error, (ValidationError, ValueError)):
        status_code = 400
    elif isinstance(error, (AuthenticationError,)):
        status_code = 401
    elif isinstance(error, (PermissionError,)):
        status_code = 403
    elif isinstance(error, (DataNotFoundError,)):
        status_code = 404
    elif isinstance(error, (RateLimitError,)):
        status_code = 429
    
    return jsonify(response_data), status_code

# 常用的错误处理装饰器预设
database_error_handler = handle_exceptions(
    severity='error',
    context={'category': 'database'}
)

network_error_handler = handle_exceptions(
    severity='warning',
    context={'category': 'network'}
)

crawler_error_handler = handle_exceptions(
    severity='warning',
    reraise=False,
    fallback_result=None,
    context={'category': 'crawler'}
)

critical_error_handler = handle_exceptions(
    severity='critical',
    context={'category': 'critical'}
)

# 工具函数
def create_error_context(module: str, 
                        operation: str, 
                        additional_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """创建错误上下文"""
    context = {
        'module': module,
        'operation': operation,
        'timestamp': time.time()
    }
    
    if additional_info:
        context.update(additional_info)
    
    return context

def log_and_raise(error_class: Type[NewsLookError], 
                 message: str, 
                 details: Dict[str, Any] = None,
                 context: Dict[str, Any] = None):
    """记录并抛出错误"""
    error = error_class(message, details=details)
    error_handler.handle_error(error, context)
    raise error

# 初始化函数
def init_error_handling(app):
    """初始化Flask应用的错误处理"""
    # 注册全局错误处理器
    @app.errorhandler(NewsLookError)
    def handle_newslook_error(error):
        return flask_error_handler(error)
    
    @app.errorhandler(Exception)
    def handle_general_error(error):
        return flask_error_handler(error)
    
    # 注册错误回调示例
    def database_error_callback(error, error_id, context):
        """数据库错误回调"""
        logger.critical(f"数据库错误需要关注 [{error_id}]: {str(error)}")
        # 这里可以添加告警、通知等逻辑
    
    error_handler.register_error_callback(DatabaseError, database_error_callback)
    
    logger.info("错误处理系统初始化完成")

# 导出主要接口
__all__ = [
    'NewsLookError', 'DatabaseError', 'CrawlerError', 'NetworkError',
    'ConfigurationError', 'ValidationError', 'DataNotFoundError',
    'RateLimitError', 'AuthenticationError', 'PermissionError',
    'handle_exceptions', 'retry_on_failure', 'validate_data',
    'safe_database_operation', 'safe_network_request',
    'error_handler', 'error_collector', 'init_error_handling',
    'create_error_context', 'log_and_raise',
    'database_error_handler', 'network_error_handler',
    'crawler_error_handler', 'critical_error_handler'
] 