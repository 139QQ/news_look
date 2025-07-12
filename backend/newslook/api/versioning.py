#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API版本路由系统
支持/v1/和/v2/版本隔离，提供向后兼容性
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, Callable, Optional
from functools import wraps
import logging
from datetime import datetime

from .response import success_response, error_response, ErrorCode

logger = logging.getLogger(__name__)


class APIVersion:
    """API版本类"""
    
    def __init__(self, version: str, description: str = None, deprecated: bool = False):
        self.version = version
        self.description = description or f"API版本 {version}"
        self.deprecated = deprecated
        self.endpoints = {}
        
    def __str__(self):
        return f"API v{self.version}"


class VersionManager:
    """版本管理器"""
    
    def __init__(self):
        self.versions: Dict[str, APIVersion] = {}
        self.current_version = None
        self.default_version = None
        
    def register_version(self, version: str, description: str = None, 
                        deprecated: bool = False, is_default: bool = False) -> APIVersion:
        """注册API版本"""
        api_version = APIVersion(version, description, deprecated)
        self.versions[version] = api_version
        
        if is_default or not self.default_version:
            self.default_version = version
            
        if not self.current_version:
            self.current_version = version
            
        logger.info(f"注册API版本: {api_version}")
        return api_version
        
    def get_version(self, version: str) -> Optional[APIVersion]:
        """获取API版本"""
        return self.versions.get(version)
        
    def get_available_versions(self) -> Dict[str, Dict[str, Any]]:
        """获取可用版本列表"""
        return {
            version: {
                'version': api_version.version,
                'description': api_version.description,
                'deprecated': api_version.deprecated,
                'is_current': version == self.current_version,
                'is_default': version == self.default_version
            }
            for version, api_version in self.versions.items()
        }
        
    def set_current_version(self, version: str):
        """设置当前版本"""
        if version in self.versions:
            self.current_version = version
            logger.info(f"当前API版本设置为: {version}")
        else:
            raise ValueError(f"版本 {version} 不存在")


# 全局版本管理器
version_manager = VersionManager()


def create_versioned_blueprint(version: str, name: str, url_prefix: str = None) -> Blueprint:
    """创建版本化蓝图"""
    if url_prefix is None:
        url_prefix = f'/v{version}'
        
    bp = Blueprint(f'{name}_v{version}', __name__, url_prefix=url_prefix)
    
    # 添加版本信息路由
    @bp.route('/info', methods=['GET'])
    def version_info():
        """版本信息"""
        api_version = version_manager.get_version(version)
        if not api_version:
            return error_response(ErrorCode.NOT_FOUND, "版本不存在").to_json_response()
            
        return success_response({
            'version': api_version.version,
            'description': api_version.description,
            'deprecated': api_version.deprecated,
            'endpoints': list(api_version.endpoints.keys()),
            'server_time': datetime.now().isoformat()
        }).to_json_response()
    
    return bp


def version_required(supported_versions: list):
    """版本要求装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从URL路径中提取版本号
            version = extract_version_from_request()
            
            if not version:
                version = version_manager.default_version
                
            if version not in supported_versions:
                return error_response(
                    ErrorCode.BAD_REQUEST, 
                    f"不支持的API版本: {version}, 支持的版本: {', '.join(supported_versions)}"
                ).to_json_response()
                
            # 检查版本是否已弃用
            api_version = version_manager.get_version(version)
            if api_version and api_version.deprecated:
                logger.warning(f"使用了已弃用的API版本: {version}")
                
            # 将版本信息传递给函数
            kwargs['api_version'] = version
            return func(*args, **kwargs)
            
        return wrapper
    return decorator


def extract_version_from_request() -> Optional[str]:
    """从请求中提取版本号"""
    # 从URL路径提取版本号
    path = request.path
    if path.startswith('/v'):
        parts = path.split('/')
        if len(parts) > 1:
            version_part = parts[1]
            if version_part.startswith('v'):
                return version_part[1:]
                
    # 从请求头提取版本号
    version_header = request.headers.get('API-Version')
    if version_header:
        return version_header
        
    # 从查询参数提取版本号
    version_param = request.args.get('version')
    if version_param:
        return version_param
        
    return None


def deprecated_endpoint(since_version: str, remove_version: str = None, 
                       alternative: str = None):
    """标记端点为已弃用"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 添加弃用警告头
            response = func(*args, **kwargs)
            
            # 如果是Flask响应对象，添加警告头
            if hasattr(response, 'headers'):
                response.headers['Warning'] = f'299 - "Deprecated since version {since_version}"'
                if remove_version:
                    response.headers['Sunset'] = f'API version {remove_version}'
                if alternative:
                    response.headers['Link'] = f'<{alternative}>; rel="successor-version"'
                    
            logger.warning(f"使用了已弃用的端点: {request.endpoint}")
            return response
            
        return wrapper
    return decorator


class APICompatibilityLayer:
    """API兼容性层"""
    
    def __init__(self):
        self.transformers = {}
        
    def register_transformer(self, from_version: str, to_version: str, 
                           transformer: Callable):
        """注册数据转换器"""
        key = f"{from_version}->{to_version}"
        self.transformers[key] = transformer
        logger.info(f"注册API转换器: {key}")
        
    def transform_request(self, data: Dict[str, Any], from_version: str, 
                         to_version: str) -> Dict[str, Any]:
        """转换请求数据"""
        key = f"{from_version}->{to_version}"
        transformer = self.transformers.get(key)
        
        if transformer:
            return transformer(data)
        return data
        
    def transform_response(self, data: Dict[str, Any], from_version: str, 
                          to_version: str) -> Dict[str, Any]:
        """转换响应数据"""
        key = f"{from_version}->{to_version}"
        transformer = self.transformers.get(key)
        
        if transformer:
            return transformer(data)
        return data


# 全局兼容性层
compatibility_layer = APICompatibilityLayer()


def setup_version_compatibility():
    """设置版本兼容性转换器"""
    
    # v1 到 v2 的请求转换
    def v1_to_v2_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """v1到v2请求数据转换"""
        # 示例转换规则
        if 'page_size' in data:
            data['per_page'] = data.pop('page_size')
            
        if 'search' in data:
            data['query'] = data.pop('search')
            
        return data
    
    # v2 到 v1 的响应转换
    def v2_to_v1_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """v2到v1响应数据转换"""
        # 示例转换规则
        if isinstance(data, dict):
            if 'per_page' in data:
                data['page_size'] = data.pop('per_page')
                
            if 'query' in data:
                data['search'] = data.pop('query')
                
        return data
    
    compatibility_layer.register_transformer('1', '2', v1_to_v2_request)
    compatibility_layer.register_transformer('2', '1', v2_to_v1_response)


def create_version_middleware():
    """创建版本中间件"""
    def middleware(app):
        @app.before_request
        def before_request():
            # 记录API版本使用情况
            version = extract_version_from_request()
            if version:
                api_version = version_manager.get_version(version)
                if api_version and api_version.deprecated:
                    logger.warning(
                        f"客户端使用已弃用的API版本: {version}, "
                        f"客户端: {request.headers.get('User-Agent', 'Unknown')}"
                    )
                    
        return app
    return middleware


def init_api_versioning(app):
    """初始化API版本系统"""
    
    # 注册API版本
    version_manager.register_version(
        '1', 
        'NewsLook API v1 - 基础版本', 
        deprecated=False, 
        is_default=True
    )
    
    version_manager.register_version(
        '2', 
        'NewsLook API v2 - 增强版本', 
        deprecated=False
    )
    
    # 设置兼容性转换器
    setup_version_compatibility()
    
    # 创建版本信息蓝图
    version_bp = Blueprint('versions', __name__, url_prefix='/api')
    
    @version_bp.route('/versions', methods=['GET'])
    def list_versions():
        """列出所有API版本"""
        versions = version_manager.get_available_versions()
        return success_response(versions, "API版本列表").to_json_response()
    
    @version_bp.route('/version/current', methods=['GET'])
    def current_version():
        """获取当前API版本"""
        current = version_manager.current_version
        api_version = version_manager.get_version(current)
        
        return success_response({
            'current_version': current,
            'description': api_version.description if api_version else None,
            'deprecated': api_version.deprecated if api_version else False
        }, "当前API版本").to_json_response()
    
    # 注册蓝图
    app.register_blueprint(version_bp)
    
    # 应用中间件
    middleware = create_version_middleware()
    middleware(app)
    
    logger.info("API版本系统初始化完成")


# V1和V2蓝图工厂函数
def create_v1_blueprint(name: str) -> Blueprint:
    """创建V1版本蓝图"""
    return create_versioned_blueprint('1', name, '/v1')


def create_v2_blueprint(name: str) -> Blueprint:
    """创建V2版本蓝图"""
    return create_versioned_blueprint('2', name, '/v2')


# 版本兼容性装饰器
def cross_version_compatible(supported_versions: list, 
                           default_behavior_version: str = '2'):
    """跨版本兼容装饰器"""
    def decorator(func):
        @wraps(func)
        @version_required(supported_versions)
        def wrapper(*args, **kwargs):
            api_version = kwargs.get('api_version', default_behavior_version)
            
            # 处理请求数据转换
            if request.is_json:
                data = request.get_json()
                if api_version != default_behavior_version:
                    data = compatibility_layer.transform_request(
                        data, api_version, default_behavior_version
                    )
                request._cached_json = (data, data)
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 处理响应数据转换
            if hasattr(result, 'get_json') and api_version != default_behavior_version:
                response_data = result.get_json()
                if response_data and 'data' in response_data:
                    response_data['data'] = compatibility_layer.transform_response(
                        response_data['data'], default_behavior_version, api_version
                    )
                    result.data = jsonify(response_data).data
            
            return result
            
        return wrapper
    return decorator 