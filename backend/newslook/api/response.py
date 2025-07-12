#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一API响应格式和错误码映射
提供标准化的API响应结构：{code, data, msg}
"""

from typing import Any, Dict, Optional, Union
from flask import jsonify, Response
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """错误码枚举"""
    # 成功状态码
    SUCCESS = 0
    
    # 客户端错误 (400-499)
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    
    # 服务器错误 (500-599)
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
    
    # 业务逻辑错误 (1000-1999)
    INVALID_PARAMETER = 1000
    MISSING_PARAMETER = 1001
    PARAMETER_FORMAT_ERROR = 1002
    PARAMETER_OUT_OF_RANGE = 1003
    
    # 数据库错误 (2000-2999)
    DATABASE_ERROR = 2000
    DATABASE_CONNECTION_ERROR = 2001
    DATABASE_QUERY_ERROR = 2002
    DATABASE_TRANSACTION_ERROR = 2003
    DATA_NOT_FOUND = 2004
    DATA_ALREADY_EXISTS = 2005
    
    # 爬虫错误 (3000-3999)
    CRAWLER_ERROR = 3000
    CRAWLER_TIMEOUT = 3001
    CRAWLER_BLOCKED = 3002
    CRAWLER_PARSE_ERROR = 3003
    CRAWLER_RATE_LIMITED = 3004
    
    # 认证授权错误 (4000-4999)
    AUTH_ERROR = 4000
    AUTH_TOKEN_INVALID = 4001
    AUTH_TOKEN_EXPIRED = 4002
    AUTH_PERMISSION_DENIED = 4003
    AUTH_USER_NOT_FOUND = 4004
    
    # 配置错误 (5000-5999)
    CONFIG_ERROR = 5000
    CONFIG_INVALID = 5001
    CONFIG_MISSING = 5002
    CONFIG_RELOAD_FAILED = 5003


# 错误码到消息的映射
ERROR_MESSAGES = {
    ErrorCode.SUCCESS: "成功",
    
    # 客户端错误
    ErrorCode.BAD_REQUEST: "请求参数错误",
    ErrorCode.UNAUTHORIZED: "未授权访问",
    ErrorCode.FORBIDDEN: "禁止访问",
    ErrorCode.NOT_FOUND: "资源不存在",
    ErrorCode.METHOD_NOT_ALLOWED: "请求方法不允许",
    ErrorCode.REQUEST_TIMEOUT: "请求超时",
    ErrorCode.CONFLICT: "资源冲突",
    ErrorCode.UNPROCESSABLE_ENTITY: "请求实体无法处理",
    ErrorCode.TOO_MANY_REQUESTS: "请求过于频繁",
    
    # 服务器错误
    ErrorCode.INTERNAL_SERVER_ERROR: "内部服务器错误",
    ErrorCode.NOT_IMPLEMENTED: "功能未实现",
    ErrorCode.BAD_GATEWAY: "网关错误",
    ErrorCode.SERVICE_UNAVAILABLE: "服务不可用",
    ErrorCode.GATEWAY_TIMEOUT: "网关超时",
    
    # 业务逻辑错误
    ErrorCode.INVALID_PARAMETER: "参数无效",
    ErrorCode.MISSING_PARAMETER: "缺少必需参数",
    ErrorCode.PARAMETER_FORMAT_ERROR: "参数格式错误",
    ErrorCode.PARAMETER_OUT_OF_RANGE: "参数超出范围",
    
    # 数据库错误
    ErrorCode.DATABASE_ERROR: "数据库错误",
    ErrorCode.DATABASE_CONNECTION_ERROR: "数据库连接错误",
    ErrorCode.DATABASE_QUERY_ERROR: "数据库查询错误",
    ErrorCode.DATABASE_TRANSACTION_ERROR: "数据库事务错误",
    ErrorCode.DATA_NOT_FOUND: "数据不存在",
    ErrorCode.DATA_ALREADY_EXISTS: "数据已存在",
    
    # 爬虫错误
    ErrorCode.CRAWLER_ERROR: "爬虫错误",
    ErrorCode.CRAWLER_TIMEOUT: "爬虫超时",
    ErrorCode.CRAWLER_BLOCKED: "爬虫被阻止",
    ErrorCode.CRAWLER_PARSE_ERROR: "爬虫解析错误",
    ErrorCode.CRAWLER_RATE_LIMITED: "爬虫限流",
    
    # 认证授权错误
    ErrorCode.AUTH_ERROR: "认证错误",
    ErrorCode.AUTH_TOKEN_INVALID: "令牌无效",
    ErrorCode.AUTH_TOKEN_EXPIRED: "令牌过期",
    ErrorCode.AUTH_PERMISSION_DENIED: "权限不足",
    ErrorCode.AUTH_USER_NOT_FOUND: "用户不存在",
    
    # 配置错误
    ErrorCode.CONFIG_ERROR: "配置错误",
    ErrorCode.CONFIG_INVALID: "配置无效",
    ErrorCode.CONFIG_MISSING: "配置缺失",
    ErrorCode.CONFIG_RELOAD_FAILED: "配置重载失败"
}


class APIResponse:
    """API响应类"""
    
    def __init__(self, code: Union[ErrorCode, int], data: Any = None, msg: str = None):
        """
        初始化API响应
        
        Args:
            code: 错误码
            data: 响应数据
            msg: 响应消息
        """
        if isinstance(code, ErrorCode):
            self.code = code.value
            self.msg = msg or ERROR_MESSAGES.get(code, "未知错误")
        else:
            self.code = code
            self.msg = msg or "未知错误"
        
        self.data = data
        self.timestamp = datetime.now().isoformat()
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code,
            "data": self.data,
            "msg": self.msg,
            "timestamp": self.timestamp
        }
        
    def to_json_response(self, http_status: int = None) -> Response:
        """转换为JSON响应"""
        if http_status is None:
            # 根据错误码确定HTTP状态码
            if self.code == 0:
                http_status = 200
            elif 400 <= self.code < 500:
                http_status = self.code
            elif 500 <= self.code < 600:
                http_status = self.code
            else:
                http_status = 500 if self.code != 0 else 200
                
        return jsonify(self.to_dict()), http_status


def success_response(data: Any = None, msg: str = None) -> APIResponse:
    """成功响应"""
    return APIResponse(ErrorCode.SUCCESS, data, msg or "操作成功")


def error_response(code: Union[ErrorCode, int], msg: str = None, data: Any = None) -> APIResponse:
    """错误响应"""
    return APIResponse(code, data, msg)


def bad_request_response(msg: str = None, data: Any = None) -> APIResponse:
    """400错误响应"""
    return APIResponse(ErrorCode.BAD_REQUEST, data, msg)


def unauthorized_response(msg: str = None, data: Any = None) -> APIResponse:
    """401错误响应"""
    return APIResponse(ErrorCode.UNAUTHORIZED, data, msg)


def forbidden_response(msg: str = None, data: Any = None) -> APIResponse:
    """403错误响应"""
    return APIResponse(ErrorCode.FORBIDDEN, data, msg)


def not_found_response(msg: str = None, data: Any = None) -> APIResponse:
    """404错误响应"""
    return APIResponse(ErrorCode.NOT_FOUND, data, msg)


def internal_server_error_response(msg: str = None, data: Any = None) -> APIResponse:
    """500错误响应"""
    return APIResponse(ErrorCode.INTERNAL_SERVER_ERROR, data, msg)


def database_error_response(msg: str = None, data: Any = None) -> APIResponse:
    """数据库错误响应"""
    return APIResponse(ErrorCode.DATABASE_ERROR, data, msg)


def crawler_error_response(msg: str = None, data: Any = None) -> APIResponse:
    """爬虫错误响应"""
    return APIResponse(ErrorCode.CRAWLER_ERROR, data, msg)


def parameter_error_response(msg: str = None, data: Any = None) -> APIResponse:
    """参数错误响应"""
    return APIResponse(ErrorCode.INVALID_PARAMETER, data, msg)


class ResponseFormatter:
    """响应格式化器"""
    
    @staticmethod
    def format_pagination_response(data: list, page: int, per_page: int, total: int) -> Dict[str, Any]:
        """格式化分页响应"""
        total_pages = (total + per_page - 1) // per_page
        
        return {
            "items": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
        
    @staticmethod
    def format_list_response(data: list, total: int = None) -> Dict[str, Any]:
        """格式化列表响应"""
        if total is None:
            total = len(data)
            
        return {
            "items": data,
            "total": total
        }
        
    @staticmethod
    def format_stats_response(stats: Dict[str, Any]) -> Dict[str, Any]:
        """格式化统计响应"""
        return {
            "statistics": stats,
            "generated_at": datetime.now().isoformat()
        }
        
    @staticmethod
    def format_health_response(is_healthy: bool, details: Dict[str, Any]) -> Dict[str, Any]:
        """格式化健康检查响应"""
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "details": details,
            "check_time": datetime.now().isoformat()
        }


def handle_exception(e: Exception) -> APIResponse:
    """异常处理函数"""
    logger.error(f"API异常: {e}", exc_info=True)
    
    # 根据异常类型返回不同的错误响应
    if isinstance(e, ValueError):
        return parameter_error_response(f"参数错误: {str(e)}")
    elif isinstance(e, FileNotFoundError):
        return not_found_response(f"文件不存在: {str(e)}")
    elif isinstance(e, PermissionError):
        return forbidden_response(f"权限不足: {str(e)}")
    elif isinstance(e, TimeoutError):
        return error_response(ErrorCode.REQUEST_TIMEOUT, f"请求超时: {str(e)}")
    else:
        return internal_server_error_response(f"系统错误: {str(e)}")


def create_response_decorator(success_code: ErrorCode = ErrorCode.SUCCESS):
    """创建响应装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                # 如果函数返回的是APIResponse对象，直接返回
                if isinstance(result, APIResponse):
                    return result.to_json_response()
                
                # 如果函数返回的是元组 (data, msg)
                if isinstance(result, tuple) and len(result) == 2:
                    data, msg = result
                    return success_response(data, msg).to_json_response()
                
                # 否则将结果作为data返回
                return success_response(result).to_json_response()
                
            except Exception as e:
                return handle_exception(e).to_json_response()
                
        return wrapper
    return decorator


# 常用装饰器
api_response = create_response_decorator()


def validate_json_request(required_fields: list = None):
    """验证JSON请求装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            from flask import request
            
            # 检查Content-Type
            if not request.is_json:
                return bad_request_response("Content-Type必须是application/json").to_json_response()
            
            # 检查必需字段
            if required_fields:
                json_data = request.get_json()
                if not json_data:
                    return bad_request_response("请求体不能为空").to_json_response()
                
                missing_fields = []
                for field in required_fields:
                    if field not in json_data or json_data[field] is None:
                        missing_fields.append(field)
                
                if missing_fields:
                    return bad_request_response(
                        f"缺少必需字段: {', '.join(missing_fields)}"
                    ).to_json_response()
            
            return func(*args, **kwargs)
            
        return wrapper
    return decorator


def validate_query_params(required_params: list = None, optional_params: dict = None):
    """验证查询参数装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            from flask import request
            
            # 检查必需参数
            if required_params:
                missing_params = []
                for param in required_params:
                    if param not in request.args:
                        missing_params.append(param)
                
                if missing_params:
                    return bad_request_response(
                        f"缺少必需参数: {', '.join(missing_params)}"
                    ).to_json_response()
            
            # 检查可选参数的默认值
            if optional_params:
                for param, default_value in optional_params.items():
                    if param not in request.args:
                        request.args = request.args.copy()
                        request.args[param] = default_value
            
            return func(*args, **kwargs)
            
        return wrapper
    return decorator 