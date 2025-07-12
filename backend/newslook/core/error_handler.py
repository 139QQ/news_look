#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准化错误处理系统
实现结构化错误响应和全面日志记录
"""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from functools import wraps
import json

logger = logging.getLogger(__name__)

@dataclass
class ErrorResponse:
    """标准化错误响应结构"""
    error_id: str
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = None
    request_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON格式"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

class ErrorHandler:
    """标准化错误处理器"""
    
    def __init__(self):
        self.error_history: List[ErrorResponse] = []
        self.max_history = 100
        
    def create_error_response(self, 
                            error_type: str, 
                            message: str, 
                            details: Optional[Dict[str, Any]] = None,
                            request_id: Optional[str] = None) -> ErrorResponse:
        """创建标准化错误响应"""
        error_id = str(uuid.uuid4())
        
        error_response = ErrorResponse(
            error_id=error_id,
            error_type=error_type,
            message=message,
            details=details,
            request_id=request_id
        )
        
        # 记录错误到历史
        self.error_history.append(error_response)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        
        # 记录日志
        logger.error(f"[{error_id}] {error_type}: {message}", extra={
            'error_id': error_id,
            'error_type': error_type,
            'details': details,
            'request_id': request_id
        })
        
        return error_response
    
    def handle_database_error(self, error: Exception, context: str = "") -> ErrorResponse:
        """处理数据库错误"""
        details = {
            'context': context,
            'error_class': error.__class__.__name__,
            'traceback': traceback.format_exc()
        }
        
        return self.create_error_response(
            error_type="DATABASE_ERROR",
            message=f"数据库操作失败: {str(error)}",
            details=details
        )
    
    def handle_crawler_error(self, error: Exception, source: str = "") -> ErrorResponse:
        """处理爬虫错误"""
        details = {
            'source': source,
            'error_class': error.__class__.__name__,
            'traceback': traceback.format_exc()
        }
        
        return self.create_error_response(
            error_type="CRAWLER_ERROR",
            message=f"爬虫操作失败: {str(error)}",
            details=details
        )
    
    def handle_config_error(self, error: Exception, config_key: str = "") -> ErrorResponse:
        """处理配置错误"""
        details = {
            'config_key': config_key,
            'error_class': error.__class__.__name__,
            'traceback': traceback.format_exc()
        }
        
        return self.create_error_response(
            error_type="CONFIG_ERROR",
            message=f"配置错误: {str(error)}",
            details=details
        )
    
    def handle_validation_error(self, message: str, validation_errors: List[str]) -> ErrorResponse:
        """处理验证错误"""
        details = {
            'validation_errors': validation_errors
        }
        
        return self.create_error_response(
            error_type="VALIDATION_ERROR",
            message=message,
            details=details
        )
    
    def get_error_history(self) -> List[Dict[str, Any]]:
        """获取错误历史"""
        return [error.to_dict() for error in self.error_history]

# 全局错误处理器实例
_error_handler = None

def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器实例"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler

def handle_errors(error_type: str = "GENERAL_ERROR"):
    """错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()
                error_response = error_handler.create_error_response(
                    error_type=error_type,
                    message=f"函数 {func.__name__} 执行失败: {str(e)}",
                    details={
                        'function': func.__name__,
                        'args': str(args),
                        'kwargs': str(kwargs),
                        'traceback': traceback.format_exc()
                    }
                )
                return {"error": error_response.to_dict()}, 500
        return wrapper
    return decorator

def create_api_error_response(error: Exception, 
                            error_type: str = "API_ERROR",
                            request_id: Optional[str] = None) -> tuple:
    """创建API错误响应"""
    error_handler = get_error_handler()
    error_response = error_handler.create_error_response(
        error_type=error_type,
        message=str(error),
        details={
            'error_class': error.__class__.__name__,
            'traceback': traceback.format_exc()
        },
        request_id=request_id
    )
    
    return {"error": error_response.to_dict()}, 500

# 自动重试装饰器
def auto_retry(max_attempts: int = 3, backoff_factor: float = 2.0):
    """自动重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        import time
                        wait_time = backoff_factor ** attempt
                        logger.warning(f"重试 {func.__name__} (尝试 {attempt + 1}/{max_attempts}), 等待 {wait_time}s")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"重试失败 {func.__name__} 在 {max_attempts} 次尝试后")
            
            # 如果所有重试都失败，抛出最后一个异常
            raise last_error
        return wrapper
    return decorator

def init_error_handler(app=None):
    """初始化错误处理器"""
    error_handler = get_error_handler()
    
    if app is not None:
        # Flask应用错误处理
        @app.errorhandler(404)
        def handle_404(error):
            error_response = error_handler.create_error_response(
                error_type="NOT_FOUND",
                message="请求的资源不存在",
                details={"path": str(error), "method": "GET"}
            )
            return {"error": error_response.to_dict()}, 404
        
        @app.errorhandler(500)
        def handle_500(error):
            error_response = error_handler.create_error_response(
                error_type="INTERNAL_SERVER_ERROR",
                message="服务器内部错误",
                details={"error": str(error)}
            )
            return {"error": error_response.to_dict()}, 500
        
        @app.errorhandler(Exception)
        def handle_general_exception(error):
            error_response = error_handler.create_error_response(
                error_type="GENERAL_ERROR",
                message="未捕获的异常",
                details={
                    "error_class": error.__class__.__name__,
                    "error_message": str(error),
                    "traceback": traceback.format_exc()
                }
            )
            return {"error": error_response.to_dict()}, 500
    
    logger.info("错误处理器初始化完成")
    return error_handler 