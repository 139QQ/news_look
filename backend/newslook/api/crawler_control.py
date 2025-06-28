#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫控制API - 实时控制、参数热更新、错误自愈
支持RESTful API规范，延迟<500ms
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, current_app
from dataclasses import dataclass, asdict
import threading
import queue
import traceback
import json
from functools import wraps

from backend.newslook.config import get_settings
from backend.newslook.utils.logger import get_logger

# 尝试导入爬虫管理器
try:
    from backend.newslook.crawlers.manager import CrawlerManager
except ImportError:
    CrawlerManager = None


# 创建蓝图
crawler_control_bp = Blueprint('crawler_control', __name__, url_prefix='/api/v1/crawlers')

logger = get_logger(__name__)
config = get_settings()

# 全局爬虫管理器实例
_crawler_manager: Optional[CrawlerManager] = None
_retry_queue = queue.Queue()
_error_history: List[Dict] = []

@dataclass
class CrawlerStatus:
    """爬虫状态数据类"""
    id: str
    name: str
    status: str  # running, stopped, error, starting, stopping
    last_run: Optional[str] = None
    last_error: Optional[str] = None
    next_retry: Optional[str] = None
    success_count: int = 0
    error_count: int = 0
    current_params: Dict = None
    performance_metrics: Dict = None


def get_crawler_manager():
    """获取爬虫管理器单例"""
    global _crawler_manager
    if _crawler_manager is None and CrawlerManager is not None:
        try:
            _crawler_manager = CrawlerManager()
        except Exception as e:
            logger.error(f"初始化爬虫管理器失败: {str(e)}")
            return None
    return _crawler_manager


def performance_monitor(f):
    """性能监控装饰器 - 确保API响应时间<500ms"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        try:
            result = f(*args, **kwargs)
            response_time = (time.time() - start_time) * 1000
            
            # 记录响应时间
            if response_time > 500:
                logger.warning(f"API {f.__name__} 响应时间超标: {response_time:.2f}ms")
            
            # 添加性能头
            if isinstance(result, tuple):
                response, status_code = result
                if isinstance(response, dict):
                    response['_performance'] = {
                        'response_time_ms': round(response_time, 2),
                        'timestamp': datetime.now().isoformat()
                    }
                return response, status_code
            else:
                if isinstance(result, dict):
                    result['_performance'] = {
                        'response_time_ms': round(response_time, 2),
                        'timestamp': datetime.now().isoformat()
                    }
                return result
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"API {f.__name__} 执行异常: {str(e)}, 响应时间: {response_time:.2f}ms")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                '_performance': {
                    'response_time_ms': round(response_time, 2),
                    'error': True
                }
            }, 500
    
    return decorated_function


def error_recovery_handler(crawler_id: str, error: Exception):
    """错误自愈处理器"""
    global _error_history, _retry_queue
    
    error_info = {
        'crawler_id': crawler_id,
        'error': str(error),
        'traceback': traceback.format_exc(),
        'timestamp': datetime.now().isoformat(),
        'retry_count': 0
    }
    
    # 记录错误历史
    _error_history.append(error_info)
    if len(_error_history) > 1000:  # 保持最近1000条错误记录
        _error_history.pop(0)
    
    # 添加到重试队列
    _retry_queue.put(error_info)
    
    logger.error(f"爬虫 {crawler_id} 发生错误，已添加到重试队列: {str(error)}")


def retry_worker():
    """重试队列处理工作者"""
    global _retry_queue
    
    while True:
        try:
            if not _retry_queue.empty():
                error_info = _retry_queue.get(timeout=5)
                crawler_id = error_info['crawler_id']
                retry_count = error_info['retry_count']
                
                # 指数退避算法
                wait_time = min(2 ** retry_count, 300)  # 最大等待5分钟
                time.sleep(wait_time)
                
                if retry_count < 3:  # 最多重试3次
                    try:
                        manager = get_crawler_manager()
                        if crawler_id in manager.crawlers:
                            # 尝试重新启动爬虫
                            manager.start_crawler(crawler_id)
                            logger.info(f"成功重启爬虫 {crawler_id}，第 {retry_count + 1} 次重试")
                        else:
                            logger.warning(f"爬虫 {crawler_id} 不存在，无法重试")
                            
                    except Exception as e:
                        # 重试失败，重新加入队列
                        error_info['retry_count'] = retry_count + 1
                        _retry_queue.put(error_info)
                        logger.warning(f"爬虫 {crawler_id} 重试失败，第 {retry_count + 1} 次: {str(e)}")
                else:
                    logger.error(f"爬虫 {crawler_id} 重试次数已达上限，停止重试")
            else:
                time.sleep(1)
                
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"重试队列处理异常: {str(e)}")
            time.sleep(5)


# 启动重试工作者线程
retry_thread = threading.Thread(target=retry_worker, daemon=True)
retry_thread.start()

@crawler_control_bp.route('', methods=['GET'])
@performance_monitor
def list_crawlers():
    """获取所有爬虫列表"""
    try:
        manager = get_crawler_manager()
        crawlers = []
        
        for name, crawler in manager.crawlers.items():
            status = get_crawler_status(name, crawler)
            crawlers.append(asdict(status))
        
        return {
            'success': True,
            'data': crawlers,
            'total': len(crawlers),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取爬虫列表失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500


@crawler_control_bp.route('/<crawler_id>', methods=['GET'])
@performance_monitor
def get_crawler_detail(crawler_id: str):
    """获取单个爬虫详情"""
    try:
        manager = get_crawler_manager()
        
        if crawler_id not in manager.crawlers:
            return {'error': f'爬虫 {crawler_id} 不存在', 'success': False}, 404
        
        crawler = manager.crawlers[crawler_id]
        status = get_crawler_status(crawler_id, crawler)
        
        return {
            'success': True,
            'data': asdict(status),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取爬虫详情失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500


@crawler_control_bp.route('/<crawler_id>/toggle', methods=['POST'])
@performance_monitor
def toggle_crawler(crawler_id: str):
    """实时启停爬虫 - 核心功能"""
    try:
        manager = get_crawler_manager()
        
        if crawler_id not in manager.crawlers:
            return {'error': f'爬虫 {crawler_id} 不存在', 'success': False}, 404
        
        # 获取当前状态
        current_status = manager.get_status().get(crawler_id, {}).get('status', 'stopped')
        
        try:
            if current_status == 'running':
                # 停止爬虫
                manager.stop_crawler(crawler_id)
                new_status = 'stopped'
                action = 'stopped'
            else:
                # 启动爬虫
                manager.start_crawler(crawler_id)
                new_status = 'running' 
                action = 'started'
            
            # 获取更新后的状态
            crawler = manager.crawlers[crawler_id]
            status = get_crawler_status(crawler_id, crawler)
            status.status = new_status
            
            return {
                'success': True,
                'action': action,
                'data': asdict(status),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            # 错误自愈
            error_recovery_handler(crawler_id, e)
            raise e
        
    except Exception as e:
        logger.error(f"切换爬虫状态失败: {str(e)}")
        return {
            'error': str(e), 
            'success': False,
            'crawler_id': crawler_id,
            'timestamp': datetime.now().isoformat()
        }, 500


@crawler_control_bp.route('/<crawler_id>/params', methods=['PATCH'])
@performance_monitor
def update_crawler_params(crawler_id: str):
    """参数热更新 - 不重启爬虫的情况下更新参数"""
    try:
        manager = get_crawler_manager()
        
        if crawler_id not in manager.crawlers:
            return {'error': f'爬虫 {crawler_id} 不存在', 'success': False}, 404
        
        # 获取更新参数
        params = request.get_json() or {}
        if not params:
            return {'error': '未提供更新参数', 'success': False}, 400
        
        crawler = manager.crawlers[crawler_id]
        old_params = {}
        updated_params = {}
        
        # 支持的热更新参数
        hotswap_params = {
            'delay': 'crawler_delay',
            'timeout': 'timeout', 
            'concurrent': 'max_concurrent',
            'user_agent': 'user_agent',
            'headers': 'headers',
            'proxy': 'proxy_config'
        }
        
        for param_key, param_value in params.items():
            if param_key in hotswap_params:
                attr_name = hotswap_params[param_key]
                
                # 保存旧值
                if hasattr(crawler, attr_name):
                    old_params[param_key] = getattr(crawler, attr_name)
                
                # 设置新值
                if hasattr(crawler, attr_name):
                    setattr(crawler, attr_name, param_value)
                    updated_params[param_key] = param_value
                    logger.info(f"爬虫 {crawler_id} 参数 {param_key} 已更新: {param_value}")
        
        if not updated_params:
            return {'error': '没有可更新的参数', 'success': False}, 400
        
        # 获取更新后的状态
        status = get_crawler_status(crawler_id, crawler)
        
        return {
            'success': True,
            'updated_params': updated_params,
            'old_params': old_params,
            'data': asdict(status),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"更新爬虫参数失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500


@crawler_control_bp.route('/<crawler_id>/status', methods=['GET'])
@performance_monitor  
def get_crawler_status_api(crawler_id: str):
    """获取爬虫实时状态"""
    try:
        manager = get_crawler_manager()
        
        if crawler_id not in manager.crawlers:
            return {'error': f'爬虫 {crawler_id} 不存在', 'success': False}, 404
        
        crawler = manager.crawlers[crawler_id]
        status = get_crawler_status(crawler_id, crawler)
        
        return {
            'success': True,
            'data': asdict(status),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取爬虫状态失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500


@crawler_control_bp.route('/batch/toggle', methods=['POST'])
@performance_monitor
def batch_toggle_crawlers():
    """批量切换爬虫状态"""
    try:
        data = request.get_json() or {}
        crawler_ids = data.get('crawler_ids', [])
        action = data.get('action', 'toggle')  # toggle, start, stop
        
        if not crawler_ids:
            return {'error': '未指定爬虫ID列表', 'success': False}, 400
        
        manager = get_crawler_manager()
        results = []
        
        for crawler_id in crawler_ids:
            if crawler_id not in manager.crawlers:
                results.append({
                    'crawler_id': crawler_id,
                    'success': False,
                    'error': f'爬虫 {crawler_id} 不存在'
                })
                continue
            
            try:
                current_status = manager.get_status().get(crawler_id, {}).get('status', 'stopped')
                
                if action == 'start' or (action == 'toggle' and current_status != 'running'):
                    manager.start_crawler(crawler_id)
                    new_status = 'running'
                    performed_action = 'started'
                elif action == 'stop' or (action == 'toggle' and current_status == 'running'):
                    manager.stop_crawler(crawler_id)
                    new_status = 'stopped'
                    performed_action = 'stopped'
                else:
                    new_status = current_status
                    performed_action = 'no_change'
                
                results.append({
                    'crawler_id': crawler_id,
                    'success': True,
                    'action': performed_action,
                    'status': new_status
                })
                
            except Exception as e:
                error_recovery_handler(crawler_id, e)
                results.append({
                    'crawler_id': crawler_id,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'success': True,
            'results': results,
            'total': len(crawler_ids),
            'successful': len([r for r in results if r['success']]),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"批量操作爬虫失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500


@crawler_control_bp.route('/errors', methods=['GET'])
@performance_monitor
def get_error_history():
    """获取错误历史和重试队列状态"""
    try:
        global _error_history, _retry_queue
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # 过滤参数
        crawler_id = request.args.get('crawler_id')
        
        # 过滤错误历史
        filtered_errors = _error_history
        if crawler_id:
            filtered_errors = [e for e in _error_history if e['crawler_id'] == crawler_id]
        
        # 分页
        start = (page - 1) * per_page
        end = start + per_page
        paged_errors = filtered_errors[start:end]
        
        return {
            'success': True,
            'data': {
                'errors': paged_errors,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': len(filtered_errors),
                    'pages': (len(filtered_errors) + per_page - 1) // per_page
                },
                'retry_queue_size': _retry_queue.qsize(),
                'total_errors': len(_error_history)
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取错误历史失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500


def get_crawler_status(crawler_id: str, crawler) -> CrawlerStatus:
    """获取爬虫状态信息"""
    try:
        manager = get_crawler_manager()
        manager_status = manager.get_status()
        
        crawler_info = manager_status.get(crawler_id, {})
        
        # 获取最近的错误信息
        recent_errors = [e for e in _error_history if e['crawler_id'] == crawler_id]
        last_error = recent_errors[-1]['error'] if recent_errors else None
        
        # 计算下次重试时间
        next_retry = None
        if last_error:
            last_error_time = datetime.fromisoformat(recent_errors[-1]['timestamp'].replace('Z', ''))
            retry_count = recent_errors[-1].get('retry_count', 0)
            wait_time = min(2 ** retry_count, 300)
            next_retry = (last_error_time + timedelta(seconds=wait_time)).isoformat()
        
        # 构建性能指标
        performance_metrics = {
            'avg_response_time': getattr(crawler, 'avg_response_time', 0),
            'success_rate': getattr(crawler, 'success_rate', 0),
            'items_per_minute': getattr(crawler, 'items_per_minute', 0),
            'last_performance_check': datetime.now().isoformat()
        }
        
        # 获取当前参数
        current_params = {
            'delay': getattr(crawler, 'crawler_delay', getattr(crawler, 'delay', 1)),
            'timeout': getattr(crawler, 'timeout', 30),
            'concurrent': getattr(crawler, 'max_concurrent', 1),
            'user_agent': getattr(crawler, 'user_agent', ''),
        }
        
        return CrawlerStatus(
            id=crawler_id,
            name=crawler_info.get('name', crawler_id),
            status=crawler_info.get('status', 'stopped'),
            last_run=crawler_info.get('last_run'),
            last_error=last_error,
            next_retry=next_retry,
            success_count=crawler_info.get('success_count', 0),
            error_count=len([e for e in _error_history if e['crawler_id'] == crawler_id]),
            current_params=current_params,
            performance_metrics=performance_metrics
        )
        
    except Exception as e:
        logger.error(f"获取爬虫状态失败: {str(e)}")
        return CrawlerStatus(
            id=crawler_id,
            name=crawler_id,
            status='error',
            last_error=str(e),
            current_params={},
            performance_metrics={}
        )


# 注册蓝图的函数
def register_crawler_control_routes(app):
    """注册爬虫控制路由"""
    app.register_blueprint(crawler_control_bp)
    logger.info("爬虫控制API路由已注册") 