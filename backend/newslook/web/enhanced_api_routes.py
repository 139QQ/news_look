#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的API路由
提供实时状态接口、改进的错误处理和WebSocket通信支持
"""

import json
import time
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import wraps

from flask import Blueprint, request, jsonify, current_app
from backend.newslook.utils.logger import get_logger
from backend.newslook.utils.database import NewsDatabase

logger = get_logger(__name__)

# 创建增强API蓝图
enhanced_api_bp = Blueprint('enhanced_api', __name__, url_prefix='/api/v2')

def handle_api_error(f):
    """API错误处理装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"API错误 {f.__name__}: {str(e)}", exc_info=True)
            
            # 广播错误信息到WebSocket
            if hasattr(current_app, 'websocket_manager') and current_app.websocket_manager:
                current_app.websocket_manager.broadcast_system_alert(
                    'api_error',
                    f"API错误: {str(e)}",
                    'error'
                )
            
            # 返回结构化的错误响应
            error_response = {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat(),
                'endpoint': request.endpoint,
                'method': request.method
            }
            
            # 根据错误类型返回不同的HTTP状态码
            if isinstance(e, ValueError):
                return jsonify(error_response), 400
            elif isinstance(e, FileNotFoundError):
                return jsonify(error_response), 404
            elif isinstance(e, PermissionError):
                return jsonify(error_response), 403
            else:
                return jsonify(error_response), 500
    
    return decorated_function

def validate_request_data(required_fields=None, optional_fields=None):
    """请求数据验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # 获取请求数据
                if request.is_json:
                    data = request.get_json()
                else:
                    data = request.form.to_dict()
                
                # 验证必需字段
                if required_fields:
                    missing_fields = []
                    for field in required_fields:
                        if field not in data or data[field] is None:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        return jsonify({
                            'success': False,
                            'error': f'缺少必需字段: {", ".join(missing_fields)}',
                            'missing_fields': missing_fields,
                            'timestamp': datetime.now().isoformat()
                        }), 400
                
                # 添加验证后的数据到kwargs
                kwargs['validated_data'] = data
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"请求验证失败: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': '请求数据验证失败',
                    'details': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 400
        
        return decorated_function
    return decorator

@enhanced_api_bp.route('/health', methods=['GET'])
@handle_api_error
def health_check():
    """健康检查接口"""
    try:
        # 检查数据库连接
        db = current_app.db
        db_status = "healthy"
        try:
            # 简单的数据库查询测试
            db.execute_query("SELECT 1")
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # 检查爬虫管理器
        crawler_status = "healthy"
        if hasattr(current_app, 'crawler_manager') and current_app.crawler_manager:
            try:
                status = current_app.crawler_manager.get_all_status()
                crawler_status = "healthy" if status else "no_data"
            except Exception as e:
                crawler_status = f"error: {str(e)}"
        else:
            crawler_status = "unavailable"
        
        # 检查WebSocket
        websocket_status = "healthy" if hasattr(current_app, 'websocket_manager') else "unavailable"
        
        health_data = {
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'uptime': time.time(),
            'components': {
                'database': db_status,
                'crawler_manager': crawler_status,
                'websocket': websocket_status
            },
            'version': '2.0.0'
        }
        
        return jsonify(health_data)
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@enhanced_api_bp.route('/status/crawler', methods=['GET'])
@handle_api_error
def get_crawler_status():
    """获取爬虫状态"""
    if not hasattr(current_app, 'crawler_manager') or not current_app.crawler_manager:
        return jsonify({
            'success': False,
            'error': '爬虫管理器不可用',
            'timestamp': datetime.now().isoformat()
        }), 503
    
    try:
        status = current_app.crawler_manager.get_all_status()
        
        # 增强状态信息
        enhanced_status = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'crawlers': status,
            'summary': {
                'total': len(status) if status else 0,
                'running': sum(1 for s in status.values() if s.get('status') == 'running') if status else 0,
                'stopped': sum(1 for s in status.values() if s.get('status') == 'stopped') if status else 0,
                'error': sum(1 for s in status.values() if s.get('status') == 'error') if status else 0
            }
        }
        
        return jsonify(enhanced_status)
        
    except Exception as e:
        logger.error(f"获取爬虫状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@enhanced_api_bp.route('/status/system', methods=['GET'])
@handle_api_error
def get_system_status():
    """获取系统状态"""
    try:
        import psutil
        
        # 获取系统资源信息
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 获取进程信息
        current_process = psutil.Process()
        process_info = {
            'pid': current_process.pid,
            'memory_mb': current_process.memory_info().rss / 1024 / 1024,
            'cpu_percent': current_process.cpu_percent(),
            'create_time': current_process.create_time(),
            'num_threads': current_process.num_threads()
        }
        
        # 获取WebSocket统计
        websocket_stats = {}
        if hasattr(current_app, 'websocket_manager') and current_app.websocket_manager:
            websocket_stats = current_app.websocket_manager.get_stats()
        
        system_status = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_percent': cpu_percent,
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                },
                'load_average': list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else []
            },
            'process': process_info,
            'websocket': websocket_stats
        }
        
        return jsonify(system_status)
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@enhanced_api_bp.route('/crawler/<crawler_name>/start', methods=['POST'])
@handle_api_error
@validate_request_data(optional_fields=['config'])
def start_crawler(crawler_name, validated_data):
    """启动指定爬虫"""
    if not hasattr(current_app, 'crawler_manager') or not current_app.crawler_manager:
        return jsonify({
            'success': False,
            'error': '爬虫管理器不可用',
            'timestamp': datetime.now().isoformat()
        }), 503
    
    try:
        config = validated_data.get('config', {})
        
        # 启动爬虫
        result = current_app.crawler_manager.start_crawler(crawler_name, config)
        
        # 广播状态变化
        if hasattr(current_app, 'websocket_manager') and current_app.websocket_manager:
            current_app.websocket_manager.broadcast_crawler_status(
                crawler_name,
                'starting',
                f'爬虫 {crawler_name} 正在启动'
            )
        
        return jsonify({
            'success': True,
            'message': f'爬虫 {crawler_name} 启动成功',
            'crawler_name': crawler_name,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"启动爬虫失败: {str(e)}")
        
        # 广播错误信息
        if hasattr(current_app, 'websocket_manager') and current_app.websocket_manager:
            current_app.websocket_manager.broadcast_crawler_status(
                crawler_name,
                'error',
                f'爬虫 {crawler_name} 启动失败: {str(e)}'
            )
        
        return jsonify({
            'success': False,
            'error': str(e),
            'crawler_name': crawler_name,
            'timestamp': datetime.now().isoformat()
        }), 500

@enhanced_api_bp.route('/crawler/<crawler_name>/stop', methods=['POST'])
@handle_api_error
def stop_crawler(crawler_name):
    """停止指定爬虫"""
    if not hasattr(current_app, 'crawler_manager') or not current_app.crawler_manager:
        return jsonify({
            'success': False,
            'error': '爬虫管理器不可用',
            'timestamp': datetime.now().isoformat()
        }), 503
    
    try:
        # 停止爬虫
        result = current_app.crawler_manager.stop_crawler(crawler_name)
        
        # 广播状态变化
        if hasattr(current_app, 'websocket_manager') and current_app.websocket_manager:
            current_app.websocket_manager.broadcast_crawler_status(
                crawler_name,
                'stopping',
                f'爬虫 {crawler_name} 正在停止'
            )
        
        return jsonify({
            'success': True,
            'message': f'爬虫 {crawler_name} 停止成功',
            'crawler_name': crawler_name,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"停止爬虫失败: {str(e)}")
        
        # 广播错误信息
        if hasattr(current_app, 'websocket_manager') and current_app.websocket_manager:
            current_app.websocket_manager.broadcast_crawler_status(
                crawler_name,
                'error',
                f'爬虫 {crawler_name} 停止失败: {str(e)}'
            )
        
        return jsonify({
            'success': False,
            'error': str(e),
            'crawler_name': crawler_name,
            'timestamp': datetime.now().isoformat()
        }), 500

@enhanced_api_bp.route('/crawler/batch/start', methods=['POST'])
@handle_api_error
@validate_request_data(required_fields=['crawlers'])
def start_batch_crawlers(validated_data):
    """批量启动爬虫"""
    if not hasattr(current_app, 'crawler_manager') or not current_app.crawler_manager:
        return jsonify({
            'success': False,
            'error': '爬虫管理器不可用',
            'timestamp': datetime.now().isoformat()
        }), 503
    
    crawler_names = validated_data['crawlers']
    
    if not isinstance(crawler_names, list):
        return jsonify({
            'success': False,
            'error': '爬虫名称必须是数组',
            'timestamp': datetime.now().isoformat()
        }), 400
    
    results = {}
    errors = {}
    
    for crawler_name in crawler_names:
        try:
            result = current_app.crawler_manager.start_crawler(crawler_name)
            results[crawler_name] = result
            
            # 广播状态变化
            if hasattr(current_app, 'websocket_manager') and current_app.websocket_manager:
                current_app.websocket_manager.broadcast_crawler_status(
                    crawler_name,
                    'starting',
                    f'爬虫 {crawler_name} 正在启动'
                )
                
        except Exception as e:
            errors[crawler_name] = str(e)
            logger.error(f"启动爬虫 {crawler_name} 失败: {str(e)}")
            
            # 广播错误信息
            if hasattr(current_app, 'websocket_manager') and current_app.websocket_manager:
                current_app.websocket_manager.broadcast_crawler_status(
                    crawler_name,
                    'error',
                    f'爬虫 {crawler_name} 启动失败: {str(e)}'
                )
    
    return jsonify({
        'success': len(errors) == 0,
        'message': f'批量启动完成，成功: {len(results)}，失败: {len(errors)}',
        'results': results,
        'errors': errors,
        'timestamp': datetime.now().isoformat()
    })

@enhanced_api_bp.route('/crawler/batch/stop', methods=['POST'])
@handle_api_error
@validate_request_data(required_fields=['crawlers'])
def stop_batch_crawlers(validated_data):
    """批量停止爬虫"""
    if not hasattr(current_app, 'crawler_manager') or not current_app.crawler_manager:
        return jsonify({
            'success': False,
            'error': '爬虫管理器不可用',
            'timestamp': datetime.now().isoformat()
        }), 503
    
    crawler_names = validated_data['crawlers']
    
    if not isinstance(crawler_names, list):
        return jsonify({
            'success': False,
            'error': '爬虫名称必须是数组',
            'timestamp': datetime.now().isoformat()
        }), 400
    
    results = {}
    errors = {}
    
    for crawler_name in crawler_names:
        try:
            result = current_app.crawler_manager.stop_crawler(crawler_name)
            results[crawler_name] = result
            
            # 广播状态变化
            if hasattr(current_app, 'websocket_manager') and current_app.websocket_manager:
                current_app.websocket_manager.broadcast_crawler_status(
                    crawler_name,
                    'stopping',
                    f'爬虫 {crawler_name} 正在停止'
                )
                
        except Exception as e:
            errors[crawler_name] = str(e)
            logger.error(f"停止爬虫 {crawler_name} 失败: {str(e)}")
            
            # 广播错误信息
            if hasattr(current_app, 'websocket_manager') and current_app.websocket_manager:
                current_app.websocket_manager.broadcast_crawler_status(
                    crawler_name,
                    'error',
                    f'爬虫 {crawler_name} 停止失败: {str(e)}'
                )
    
    return jsonify({
        'success': len(errors) == 0,
        'message': f'批量停止完成，成功: {len(results)}，失败: {len(errors)}',
        'results': results,
        'errors': errors,
        'timestamp': datetime.now().isoformat()
    })

@enhanced_api_bp.route('/logs/recent', methods=['GET'])
@handle_api_error
def get_recent_logs():
    """获取最近的日志"""
    try:
        # 获取查询参数
        lines = request.args.get('lines', 100, type=int)
        level = request.args.get('level', 'INFO')
        source = request.args.get('source', None)
        
        # 限制返回的日志条数
        lines = min(lines, 1000)
        
        # 这里应该从日志文件或日志存储中获取数据
        # 目前返回模拟数据
        logs = []
        
        # 如果有WebSocket管理器，获取消息历史
        if hasattr(current_app, 'websocket_manager') and current_app.websocket_manager:
            message_history = list(current_app.websocket_manager.message_history)
            for msg in message_history[-lines:]:
                if not level or msg.get('level') == level:
                    if not source or msg.get('source') == source:
                        logs.append(msg)
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs),
            'filters': {
                'lines': lines,
                'level': level,
                'source': source
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取日志失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@enhanced_api_bp.route('/websocket/stats', methods=['GET'])
@handle_api_error
def get_websocket_stats():
    """获取WebSocket统计信息"""
    if not hasattr(current_app, 'websocket_manager') or not current_app.websocket_manager:
        return jsonify({
            'success': False,
            'error': 'WebSocket管理器不可用',
            'timestamp': datetime.now().isoformat()
        }), 503
    
    try:
        stats = current_app.websocket_manager.get_stats()
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取WebSocket统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def register_enhanced_api_routes(app):
    """注册增强API路由"""
    app.register_blueprint(enhanced_api_bp)
    logger.info("增强API路由已注册") 