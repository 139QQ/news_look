"""
NewsLook 后端监控API
处理前端监控数据、健康检查、性能监控等
"""

import os
import sys
import json
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from flask import Blueprint, request, jsonify, current_app
from functools import wraps

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.utils.logger import setup_logger

# 设置日志
logger = setup_logger()

# 创建蓝图
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')

# 监控数据存储（生产环境建议使用Redis或数据库）
monitoring_data = {
    'events': [],
    'errors': [],
    'performance': [],
    'health_checks': [],
    'alerts': []
}

# 系统指标缓存
system_metrics_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 30  # 30秒缓存
}

@dataclass
class HealthStatus:
    """健康状态数据类"""
    status: str
    timestamp: float
    uptime: float
    memory_usage: float
    cpu_usage: float
    disk_usage: float
    database_status: str
    api_response_time: float
    version: str
    environment: str

@dataclass
class ErrorReport:
    """错误报告数据类"""
    error_type: str
    message: str
    stack: Optional[str]
    timestamp: float
    url: str
    user_agent: str
    session_id: str
    context: Dict[str, Any]

@dataclass
class PerformanceMetric:
    """性能指标数据类"""
    name: str
    value: float
    timestamp: float
    url: str
    metadata: Dict[str, Any]

def require_api_key(f):
    """API密钥验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        expected_key = current_app.config.get('MONITORING_API_KEY')
        
        # 开发环境跳过验证
        if current_app.config.get('DEBUG', False):
            return f(*args, **kwargs)
            
        if not expected_key or api_key != expected_key:
            return jsonify({'error': 'Invalid API key'}), 401
            
        return f(*args, **kwargs)
    return decorated_function

def get_system_metrics() -> Dict[str, Any]:
    """获取系统指标"""
    current_time = time.time()
    
    # 检查缓存
    if (system_metrics_cache['data'] and 
        current_time - system_metrics_cache['timestamp'] < system_metrics_cache['ttl']):
        return system_metrics_cache['data']
    
    try:
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 磁盘使用率
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        # 网络统计
        network = psutil.net_io_counters()
        
        # 进程信息
        process = psutil.Process()
        process_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        metrics = {
            'cpu': {
                'usage_percent': cpu_percent,
                'count': psutil.cpu_count(),
                'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            },
            'memory': {
                'total': memory.total,
                'used': memory.used,
                'available': memory.available,
                'percent': memory_percent,
                'process_memory_mb': process_memory
            },
            'disk': {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk_percent
            },
            'network': {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            },
            'timestamp': current_time
        }
        
        # 更新缓存
        system_metrics_cache['data'] = metrics
        system_metrics_cache['timestamp'] = current_time
        
        return metrics
        
    except Exception as e:
        logger.error(f"获取系统指标失败: {str(e)}")
        return {
            'error': str(e),
            'timestamp': current_time
        }

def check_database_health() -> Dict[str, Any]:
    """检查数据库健康状态"""
    try:
        # 这里可以添加数据库连接测试
        # 示例：测试主数据库连接
        import sqlite3
        from backend.newslook.core.config_manager import ConfigManager
        
        config = ConfigManager()
        db_path = config.get('database.main_db', 'data/db/finance_news.db')
        
        start_time = time.time()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        response_time = (time.time() - start_time) * 1000  # 毫秒
        
        return {
            'status': 'healthy',
            'response_time_ms': response_time,
            'table_count': table_count,
            'database_path': db_path
        }
        
    except Exception as e:
        logger.error(f"数据库健康检查失败: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'response_time_ms': -1
        }

@monitoring_bp.route('/health', methods=['GET'])
def health_check():
    """系统健康检查端点"""
    try:
        level = request.args.get('level', 'basic')
        start_time = time.time()
        
        # 基础健康信息
        health_data = {
            'status': 'healthy',
            'timestamp': time.time(),
            'uptime': time.time() - current_app.config.get('START_TIME', time.time()),
            'version': current_app.config.get('VERSION', '3.1.0'),
            'environment': current_app.config.get('ENV', 'development')
        }
        
        if level in ['detailed', 'full']:
            # 详细健康信息
            system_metrics = get_system_metrics()
            db_health = check_database_health()
            
            health_data.update({
                'system_metrics': system_metrics,
                'database': db_health,
                'response_time_ms': (time.time() - start_time) * 1000
            })
            
            # 检查健康阈值
            if system_metrics.get('cpu', {}).get('usage_percent', 0) > 90:
                health_data['status'] = 'warning'
                health_data['warnings'] = health_data.get('warnings', [])
                health_data['warnings'].append('High CPU usage')
                
            if system_metrics.get('memory', {}).get('percent', 0) > 90:
                health_data['status'] = 'critical'
                health_data['alerts'] = health_data.get('alerts', [])
                health_data['alerts'].append('High memory usage')
                
            if db_health.get('status') == 'unhealthy':
                health_data['status'] = 'critical'
                health_data['alerts'] = health_data.get('alerts', [])
                health_data['alerts'].append('Database unhealthy')
        
        # 存储健康检查记录
        health_record = HealthStatus(
            status=health_data['status'],
            timestamp=health_data['timestamp'],
            uptime=health_data['uptime'],
            memory_usage=system_metrics.get('memory', {}).get('percent', 0) if level != 'basic' else 0,
            cpu_usage=system_metrics.get('cpu', {}).get('usage_percent', 0) if level != 'basic' else 0,
            disk_usage=system_metrics.get('disk', {}).get('percent', 0) if level != 'basic' else 0,
            database_status=db_health.get('status', 'unknown') if level != 'basic' else 'unknown',
            api_response_time=(time.time() - start_time) * 1000,
            version=health_data['version'],
            environment=health_data['environment']
        )
        
        monitoring_data['health_checks'].append(asdict(health_record))
        
        # 限制存储数量
        if len(monitoring_data['health_checks']) > 1000:
            monitoring_data['health_checks'] = monitoring_data['health_checks'][-500:]
        
        return jsonify(health_data)
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': time.time()
        }), 500

@monitoring_bp.route('/events', methods=['POST'])
def receive_events():
    """接收前端监控事件"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        events = data.get('events', [])
        environment = data.get('environment', 'unknown')
        user_agent = data.get('userAgent', 'unknown')
        timestamp = data.get('timestamp', time.time())
        
        processed_events = []
        
        for event in events:
            event_type = event.get('type')
            event_data = event.get('data')
            event_timestamp = event.get('timestamp', timestamp)
            session_id = event.get('sessionId', 'unknown')
            
            # 处理不同类型的事件
            if event_type == 'error':
                error_report = ErrorReport(
                    error_type=event_data.get('type', 'unknown'),
                    message=event_data.get('message', ''),
                    stack=event_data.get('stack'),
                    timestamp=event_timestamp,
                    url=event_data.get('url', ''),
                    user_agent=user_agent,
                    session_id=session_id,
                    context={
                        'environment': environment,
                        'filename': event_data.get('filename'),
                        'lineno': event_data.get('lineno'),
                        'colno': event_data.get('colno')
                    }
                )
                monitoring_data['errors'].append(asdict(error_report))
                logger.error(f"前端错误: {error_report.message}", extra={
                    'type': error_report.error_type,
                    'url': error_report.url,
                    'session_id': session_id
                })
                
            elif event_type == 'performance':
                perf_metric = PerformanceMetric(
                    name=event_data.get('name', 'unknown'),
                    value=event_data.get('value', 0),
                    timestamp=event_timestamp,
                    url=event_data.get('url', ''),
                    metadata=event_data.get('metadata', {})
                )
                monitoring_data['performance'].append(asdict(perf_metric))
                
                # 检查性能阈值
                if perf_metric.name in ['page_load_time', 'api_response_time'] and perf_metric.value > 5000:
                    logger.warning(f"性能警告: {perf_metric.name} = {perf_metric.value}ms")
                    
            elif event_type == 'behavior':
                # 用户行为事件处理
                logger.debug(f"用户行为: {event_data.get('type', 'unknown')}", extra={
                    'session_id': session_id,
                    'url': event_data.get('url')
                })
            
            processed_events.append({
                'type': event_type,
                'processed_at': time.time(),
                'session_id': session_id
            })
        
        # 限制存储数量，避免内存泄漏
        for key in ['events', 'errors', 'performance']:
            if len(monitoring_data[key]) > 10000:
                monitoring_data[key] = monitoring_data[key][-5000:]
        
        return jsonify({
            'success': True,
            'processed_events': len(processed_events),
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"处理监控事件失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """获取系统指标"""
    try:
        metrics_type = request.args.get('type', 'system')
        time_range = int(request.args.get('range', 3600))  # 默认1小时
        
        current_time = time.time()
        start_time = current_time - time_range
        
        if metrics_type == 'system':
            return jsonify(get_system_metrics())
            
        elif metrics_type == 'performance':
            # 过滤指定时间范围内的性能数据
            perf_data = [
                metric for metric in monitoring_data['performance']
                if metric['timestamp'] >= start_time
            ]
            
            # 聚合统计
            metrics_summary = {}
            for metric in perf_data:
                name = metric['name']
                if name not in metrics_summary:
                    metrics_summary[name] = {
                        'count': 0,
                        'total': 0,
                        'min': float('inf'),
                        'max': 0,
                        'avg': 0
                    }
                
                value = metric['value']
                metrics_summary[name]['count'] += 1
                metrics_summary[name]['total'] += value
                metrics_summary[name]['min'] = min(metrics_summary[name]['min'], value)
                metrics_summary[name]['max'] = max(metrics_summary[name]['max'], value)
                metrics_summary[name]['avg'] = metrics_summary[name]['total'] / metrics_summary[name]['count']
            
            return jsonify({
                'summary': metrics_summary,
                'raw_data': perf_data[-100:],  # 最近100条记录
                'time_range': time_range,
                'total_records': len(perf_data)
            })
            
        elif metrics_type == 'errors':
            # 错误统计
            error_data = [
                error for error in monitoring_data['errors']
                if error['timestamp'] >= start_time
            ]
            
            error_summary = {}
            for error in error_data:
                error_type = error['error_type']
                if error_type not in error_summary:
                    error_summary[error_type] = {
                        'count': 0,
                        'recent_message': '',
                        'first_occurred': error['timestamp'],
                        'last_occurred': error['timestamp']
                    }
                
                error_summary[error_type]['count'] += 1
                error_summary[error_type]['recent_message'] = error['message']
                error_summary[error_type]['last_occurred'] = max(
                    error_summary[error_type]['last_occurred'],
                    error['timestamp']
                )
            
            return jsonify({
                'summary': error_summary,
                'recent_errors': error_data[-50:],  # 最近50个错误
                'total_errors': len(error_data),
                'error_rate': len(error_data) / (time_range / 3600)  # 每小时错误数
            })
        
        else:
            return jsonify({'error': 'Invalid metrics type'}), 400
            
    except Exception as e:
        logger.error(f"获取指标失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/alerts', methods=['GET', 'POST'])
def manage_alerts():
    """管理告警"""
    if request.method == 'GET':
        # 获取告警列表
        active_alerts = [
            alert for alert in monitoring_data['alerts']
            if alert.get('status') == 'active'
        ]
        
        return jsonify({
            'active_alerts': active_alerts,
            'total_alerts': len(monitoring_data['alerts'])
        })
        
    elif request.method == 'POST':
        # 创建新告警
        try:
            alert_data = request.get_json()
            alert = {
                'id': f"alert_{int(time.time())}_{len(monitoring_data['alerts'])}",
                'type': alert_data.get('type', 'unknown'),
                'severity': alert_data.get('severity', 'warning'),
                'message': alert_data.get('message', ''),
                'source': alert_data.get('source', 'system'),
                'timestamp': time.time(),
                'status': 'active',
                'metadata': alert_data.get('metadata', {})
            }
            
            monitoring_data['alerts'].append(alert)
            
            # 根据严重程度记录日志
            if alert['severity'] == 'critical':
                logger.critical(f"严重告警: {alert['message']}")
            elif alert['severity'] == 'warning':
                logger.warning(f"告警: {alert['message']}")
            else:
                logger.info(f"告警: {alert['message']}")
            
            return jsonify({
                'success': True,
                'alert_id': alert['id']
            })
            
        except Exception as e:
            logger.error(f"创建告警失败: {str(e)}")
            return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/alerts/<alert_id>', methods=['PUT', 'DELETE'])
@require_api_key
def update_alert(alert_id):
    """更新或删除告警"""
    try:
        alert = next(
            (a for a in monitoring_data['alerts'] if a['id'] == alert_id),
            None
        )
        
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404
        
        if request.method == 'PUT':
            # 更新告警状态
            update_data = request.get_json()
            alert.update(update_data)
            alert['updated_at'] = time.time()
            
            return jsonify({
                'success': True,
                'alert': alert
            })
            
        elif request.method == 'DELETE':
            # 删除告警
            monitoring_data['alerts'].remove(alert)
            
            return jsonify({
                'success': True,
                'message': 'Alert deleted'
            })
            
    except Exception as e:
        logger.error(f"更新告警失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/dashboard', methods=['GET'])
def get_dashboard_data():
    """获取仪表盘数据"""
    try:
        current_time = time.time()
        one_hour_ago = current_time - 3600
        
        # 系统指标
        system_metrics = get_system_metrics()
        
        # 最近1小时的错误数
        recent_errors = [
            error for error in monitoring_data['errors']
            if error['timestamp'] >= one_hour_ago
        ]
        
        # 最近1小时的性能数据
        recent_performance = [
            metric for metric in monitoring_data['performance']
            if metric['timestamp'] >= one_hour_ago
        ]
        
        # 活跃告警
        active_alerts = [
            alert for alert in monitoring_data['alerts']
            if alert.get('status') == 'active'
        ]
        
        # 数据库健康状态
        db_health = check_database_health()
        
        dashboard_data = {
            'timestamp': current_time,
            'system': {
                'cpu_usage': system_metrics.get('cpu', {}).get('usage_percent', 0),
                'memory_usage': system_metrics.get('memory', {}).get('percent', 0),
                'disk_usage': system_metrics.get('disk', {}).get('percent', 0),
                'process_memory_mb': system_metrics.get('memory', {}).get('process_memory_mb', 0)
            },
            'database': db_health,
            'errors': {
                'total_last_hour': len(recent_errors),
                'error_rate_per_hour': len(recent_errors),
                'by_type': {}
            },
            'performance': {
                'total_metrics': len(recent_performance),
                'avg_response_time': 0,
                'slow_requests': 0
            },
            'alerts': {
                'active_count': len(active_alerts),
                'critical_count': len([a for a in active_alerts if a.get('severity') == 'critical']),
                'warning_count': len([a for a in active_alerts if a.get('severity') == 'warning'])
            }
        }
        
        # 计算错误类型分布
        for error in recent_errors:
            error_type = error['error_type']
            dashboard_data['errors']['by_type'][error_type] = \
                dashboard_data['errors']['by_type'].get(error_type, 0) + 1
        
        # 计算性能统计
        if recent_performance:
            response_times = [
                metric['value'] for metric in recent_performance
                if metric['name'] in ['api_response_time', 'page_load_time']
            ]
            if response_times:
                dashboard_data['performance']['avg_response_time'] = sum(response_times) / len(response_times)
                dashboard_data['performance']['slow_requests'] = len([rt for rt in response_times if rt > 3000])
        
        return jsonify(dashboard_data)
        
    except Exception as e:
        logger.error(f"获取仪表盘数据失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 错误处理装饰器
@monitoring_bp.errorhandler(Exception)
def handle_monitoring_error(e):
    """监控API错误处理"""
    logger.error(f"监控API错误: {str(e)}")
    return jsonify({
        'error': 'Internal server error',
        'message': str(e) if current_app.debug else 'An error occurred',
        'timestamp': time.time()
    }), 500

# 请求日志中间件
@monitoring_bp.before_request
def log_request():
    """记录API请求"""
    logger.debug(f"监控API请求: {request.method} {request.path}", extra={
        'method': request.method,
        'path': request.path,
        'remote_addr': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'unknown')
    })

@monitoring_bp.after_request
def log_response(response):
    """记录API响应"""
    logger.debug(f"监控API响应: {response.status_code}", extra={
        'status_code': response.status_code,
        'content_length': response.content_length
    })
    return response


def register_monitoring_routes(app):
    """注册监控API路由到Flask应用"""
    try:
        app.register_blueprint(monitoring_bp)
        logger.info("监控API路由已成功注册")
    except Exception as e:
        logger.error(f"注册监控API路由失败: {str(e)}")
        raise 