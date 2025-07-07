#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版爬虫控制API - 第二优先级指令实现
集成心跳检测、状态持久化、实时日志流
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, current_app
from dataclasses import dataclass, asdict
import threading
import json

from backend.newslook.config import get_settings
from backend.newslook.utils.logger import get_logger
from backend.newslook.core.heartbeat_monitor import get_heartbeat_monitor, ping_crawler_heartbeat
from backend.newslook.core.state_persistence import get_state_manager
from backend.newslook.core.realtime_log_stream import get_realtime_log_stream

# 创建蓝图
enhanced_crawler_bp = Blueprint('enhanced_crawler', __name__, url_prefix='/api/v2/crawlers')

logger = get_logger(__name__)
config = get_settings()

# 全局组件
heartbeat_monitor = None
state_manager = None
log_stream = None

def init_enhanced_crawler_system():
    """初始化增强爬虫系统"""
    global heartbeat_monitor, state_manager, log_stream
    
    try:
        # 初始化心跳监控
        heartbeat_monitor = get_heartbeat_monitor()
        heartbeat_monitor.start()
        
        # 初始化状态持久化
        state_manager = get_state_manager()
        
        # 初始化实时日志流
        log_stream = get_realtime_log_stream()
        
        # 添加心跳告警回调
        heartbeat_monitor.add_alert_callback(_heartbeat_alert_callback)
        
        logger.info("增强爬虫系统初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"增强爬虫系统初始化失败: {str(e)}")
        return False

def _heartbeat_alert_callback(crawler_id: str, old_status: str, new_status: str, time_since_last: float):
    """心跳告警回调"""
    try:
        alert_data = {
            'type': 'heartbeat_alert',
            'crawler_id': crawler_id,
            'old_status': old_status,
            'new_status': new_status,
            'time_since_last': time_since_last,
            'timestamp': datetime.now().isoformat()
        }
        
        # 保存告警到状态存储
        state_manager.set_state(
            f"alert:heartbeat:{crawler_id}:{int(time.time())}", 
            alert_data, 
            ttl=86400  # 24小时
        )
        
        # 发送到实时日志流
        if log_stream:
            message = f"爬虫心跳告警: {crawler_id} {old_status}→{new_status} (无响应{time_since_last:.1f}s)"
            log_stream.send_manual_log(message, 'WARNING', 'heartbeat', 'system')
        
        logger.warning(f"心跳告警: {crawler_id} {old_status}→{new_status}")
        
    except Exception as e:
        logger.error(f"处理心跳告警失败: {str(e)}")

@dataclass
class EnhancedCrawlerStatus:
    """增强爬虫状态"""
    id: str
    name: str
    status: str
    heartbeat_status: str
    last_heartbeat: Optional[str] = None
    performance_metrics: Dict[str, Any] = None
    persistence_level: str = 'sqlite'
    log_stream_room: str = 'general'

@enhanced_crawler_bp.route('/status', methods=['GET'])
def get_enhanced_status():
    """获取增强爬虫状态"""
    try:
        # 获取基础爬虫状态
        from backend.newslook.crawlers.manager import CrawlerManager
        crawler_manager = CrawlerManager()
        basic_status = crawler_manager.get_status()
        
        # 获取心跳状态
        heartbeat_status = heartbeat_monitor.get_status() if heartbeat_monitor else {}
        
        # 组合增强状态
        enhanced_crawlers = []
        for crawler_id, crawler_info in basic_status.items():
            heartbeat_info = heartbeat_status.get('heartbeats', {}).get(crawler_id, {})
            
            enhanced_status = EnhancedCrawlerStatus(
                id=crawler_id,
                name=crawler_info.get('display_name', crawler_id),
                status=crawler_info.get('status', 'unknown'),
                heartbeat_status=heartbeat_info.get('status', 'unknown'),
                last_heartbeat=heartbeat_info.get('last_heartbeat'),
                performance_metrics={
                    'response_time_ms': heartbeat_info.get('response_time_ms', 0),
                    'total_heartbeats': heartbeat_info.get('total_heartbeats', 0),
                    'uptime_seconds': heartbeat_info.get('uptime_seconds', 0)
                },
                persistence_level='redis' if heartbeat_info.get('consecutive_failures', 0) == 0 else 'sqlite',
                log_stream_room=f'crawler_{crawler_id}'
            )
            
            enhanced_crawlers.append(asdict(enhanced_status))
        
        return {
            'success': True,
            'data': enhanced_crawlers,
            'heartbeat_summary': heartbeat_status.get('summary', {}),
            'system_health': {
                'heartbeat_monitor': heartbeat_monitor is not None and heartbeat_monitor.is_running,
                'state_persistence': state_manager is not None,
                'log_streaming': log_stream is not None
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取增强状态失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@enhanced_crawler_bp.route('/<crawler_id>/heartbeat', methods=['POST'])
def update_heartbeat(crawler_id: str):
    """更新爬虫心跳"""
    try:
        data = request.get_json() or {}
        response_time_ms = data.get('response_time_ms')
        metadata = data.get('metadata', {})
        
        # 注册/更新心跳
        if heartbeat_monitor:
            if crawler_id not in heartbeat_monitor.heartbeats:
                heartbeat_monitor.register_crawler(crawler_id, metadata)
            
            # 发送心跳
            ping_crawler_heartbeat(crawler_id, response_time_ms)
            
            # 保存状态到持久化存储
            if state_manager:
                state_data = {
                    'crawler_id': crawler_id,
                    'last_ping': datetime.now().isoformat(),
                    'response_time_ms': response_time_ms,
                    'metadata': metadata
                }
                state_manager.set_state(f"crawler:heartbeat:{crawler_id}", state_data, ttl=300)
        
        return {
            'success': True,
            'message': f'心跳更新成功: {crawler_id}',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"更新心跳失败 {crawler_id}: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@enhanced_crawler_bp.route('/<crawler_id>/performance', methods=['GET'])
def get_performance_metrics(crawler_id: str):
    """获取爬虫性能指标"""
    try:
        # 从心跳监控获取指标
        heartbeat_data = heartbeat_monitor.get_status(crawler_id) if heartbeat_monitor else {}
        
        # 从状态存储获取历史数据
        historical_data = []
        if state_manager:
            for i in range(24):  # 最近24小时
                hour_ago = datetime.now() - timedelta(hours=i)
                key = f"crawler:metrics:{crawler_id}:{hour_ago.strftime('%Y%m%d%H')}"
                hour_data = state_manager.get_state(key)
                if hour_data:
                    historical_data.append(hour_data)
        
        return {
            'success': True,
            'crawler_id': crawler_id,
            'current_metrics': heartbeat_data,
            'historical_metrics': historical_data,
            'performance_summary': {
                'avg_response_time': sum(h.get('response_time_ms', 0) for h in historical_data) / max(len(historical_data), 1),
                'availability_percentage': len([h for h in historical_data if h.get('status') == 'healthy']) / max(len(historical_data), 1) * 100,
                'total_uptime_hours': sum(h.get('uptime_seconds', 0) for h in historical_data) / 3600
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取性能指标失败 {crawler_id}: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@enhanced_crawler_bp.route('/<crawler_id>/logs/stream', methods=['GET'])
def get_log_stream_info(crawler_id: str):
    """获取爬虫日志流信息"""
    try:
        room_name = f'crawler_{crawler_id}'
        
        # 获取日志历史
        log_history = []
        if log_stream:
            log_history = log_stream._get_log_history(room_name, 50)
        
        return {
            'success': True,
            'crawler_id': crawler_id,
            'log_stream_room': room_name,
            'websocket_endpoint': '/socket.io',
            'recent_logs': log_history,
            'log_stats': {
                'total_logs': len(log_history),
                'log_levels': {
                    'INFO': len([l for l in log_history if l.get('level') == 'INFO']),
                    'WARNING': len([l for l in log_history if l.get('level') == 'WARNING']),
                    'ERROR': len([l for l in log_history if l.get('level') == 'ERROR'])
                }
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取日志流信息失败 {crawler_id}: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@enhanced_crawler_bp.route('/system/health', methods=['GET'])
def get_system_health():
    """获取系统健康状态"""
    try:
        # 心跳监控健康状态
        heartbeat_health = {
            'running': heartbeat_monitor.is_running if heartbeat_monitor else False,
            'monitored_crawlers': len(heartbeat_monitor.heartbeats) if heartbeat_monitor else 0,
            'healthy_crawlers': 0,
            'critical_crawlers': 0
        }
        
        if heartbeat_monitor:
            for status in heartbeat_monitor.heartbeats.values():
                if status.status == 'healthy':
                    heartbeat_health['healthy_crawlers'] += 1
                elif status.status in ['critical', 'dead']:
                    heartbeat_health['critical_crawlers'] += 1
        
        # 状态持久化健康状态
        persistence_health = state_manager.get_stats() if state_manager else {'connections': {}, 'operations': {}}
        
        # 日志流健康状态
        log_stream_health = {
            'active': log_stream is not None,
            'watching': log_stream.is_watching if log_stream else False,
            'connected_clients': len(log_stream.connected_clients) if log_stream else 0
        }
        
        return {
            'success': True,
            'system_health': {
                'overall_status': 'healthy',  # 简化版本
                'heartbeat_monitor': heartbeat_health,
                'state_persistence': persistence_health,
                'log_streaming': log_stream_health
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取系统健康状态失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@enhanced_crawler_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """获取系统告警"""
    try:
        alerts = []
        
        if state_manager:
            # 获取最近的告警（简化实现）
            for i in range(1440):  # 最近24小时（每分钟检查）
                minute_ago = datetime.now() - timedelta(minutes=i)
                timestamp = int(minute_ago.timestamp())
                
                # 查找该分钟的告警
                pattern_key = f"alert:heartbeat:*:{timestamp}"
                # 注意：这里需要实现模式匹配，简化版本只检查几个
                for crawler_id in ['eastmoney', 'sina', 'netease', 'ifeng', 'tencent', 'caijing']:
                    alert_key = f"alert:heartbeat:{crawler_id}:{timestamp}"
                    alert_data = state_manager.get_state(alert_key)
                    if alert_data:
                        alerts.append(alert_data)
                
                if len(alerts) >= 20:  # 最多返回20个告警
                    break
        
        return {
            'success': True,
            'alerts': alerts,
            'alert_summary': {
                'total': len(alerts),
                'critical': len([a for a in alerts if a.get('new_status') == 'critical']),
                'warning': len([a for a in alerts if a.get('new_status') == 'warning'])
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取告警失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@enhanced_crawler_bp.route('/metrics/export', methods=['GET'])
def export_metrics():
    """导出系统指标（Prometheus格式）"""
    try:
        metrics = []
        
        # 心跳指标
        if heartbeat_monitor:
            for crawler_id, status in heartbeat_monitor.heartbeats.items():
                metrics.append(f'crawler_heartbeat_total{{crawler="{crawler_id}"}} {status.total_heartbeats}')
                metrics.append(f'crawler_uptime_seconds{{crawler="{crawler_id}"}} {status.uptime_seconds}')
                metrics.append(f'crawler_response_time_ms{{crawler="{crawler_id}"}} {status.response_time_ms}')
                
                # 状态转换为数值
                status_value = {'healthy': 1, 'warning': 0.5, 'critical': 0.2, 'dead': 0}.get(status.status, 0)
                metrics.append(f'crawler_health_status{{crawler="{crawler_id}"}} {status_value}')
        
        # 系统指标
        if state_manager:
            stats = state_manager.get_stats()
            metrics.append(f'state_sqlite_operations_total {stats.get("operations", {}).get("sqlite_ops", 0)}')
            metrics.append(f'state_redis_operations_total {stats.get("operations", {}).get("redis_ops", 0)}')
        
        # 返回Prometheus格式
        return '\n'.join(metrics) + '\n', 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
    except Exception as e:
        logger.error(f"导出指标失败: {str(e)}")
        return f'# ERROR: {str(e)}\n', 500, {'Content-Type': 'text/plain; charset=utf-8'}

def register_enhanced_crawler_routes(app):
    """注册增强爬虫控制路由"""
    try:
        # 初始化增强系统
        init_enhanced_crawler_system()
        
        # 注册蓝图
        app.register_blueprint(enhanced_crawler_bp)
        
        logger.info("✅ 增强爬虫控制API已注册")
        return True
        
    except Exception as e:
        logger.error(f"❌ 增强爬虫控制API注册失败: {str(e)}")
        return False 