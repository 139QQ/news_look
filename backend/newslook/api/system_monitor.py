#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统监控API - 实时性能监控、阈值告警、健康检查
支持CPU/内存/队列深度监控，企业微信/邮件推送
"""

import psutil
import time
import json
import asyncio
import requests
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, current_app
from dataclasses import dataclass, asdict
import threading
import queue
from collections import deque
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3

from backend.newslook.config import get_settings
from backend.newslook.utils.logger import get_logger

# 创建蓝图
system_monitor_bp = Blueprint('system_monitor', __name__, url_prefix='/api/v1/system')

logger = get_logger(__name__)
config = get_settings()

# 监控数据存储
_metrics_history = deque(maxlen=1000)  # 保存最近1000条指标
_alert_history = deque(maxlen=500)     # 保存最近500条告警
_alert_queue = queue.Queue()

@dataclass
class SystemMetrics:
    """系统指标数据类"""
    timestamp: str
    cpu_percent: float
    memory_percent: float 
    memory_used_gb: float
    memory_total_gb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_sent_mb: float
    network_recv_mb: float
    process_count: int
    load_average: List[float]
    crawlers_running: int
    queue_depth: int
    response_time_avg: float

@dataclass
class AlertRule:
    """告警规则数据类"""
    id: str
    name: str
    metric: str
    operator: str  # >, <, >=, <=, ==
    threshold: float
    duration_seconds: int  # 持续时间阈值
    enabled: bool
    notification_channels: List[str]  # email, wechat, webhook
    
@dataclass
class Alert:
    """告警数据类"""
    id: str
    rule_id: str
    rule_name: str
    metric: str
    value: float
    threshold: float
    level: str  # info, warning, critical
    message: str
    timestamp: str
    resolved: bool = False
    resolved_timestamp: Optional[str] = None

# 默认告警规则
DEFAULT_ALERT_RULES = [
    AlertRule(
        id="cpu_high",
        name="CPU使用率过高",
        metric="cpu_percent",
        operator=">=",
        threshold=80.0,
        duration_seconds=300,  # 5分钟
        enabled=True,
        notification_channels=["email"]
    ),
    AlertRule(
        id="memory_high", 
        name="内存使用率过高",
        metric="memory_percent",
        operator=">=",
        threshold=85.0,
        duration_seconds=300,
        enabled=True,
        notification_channels=["email"]
    ),
    AlertRule(
        id="disk_full",
        name="磁盘空间不足",
        metric="disk_usage_percent", 
        operator=">=",
        threshold=90.0,
        duration_seconds=60,
        enabled=True,
        notification_channels=["email", "wechat"]
    ),
    AlertRule(
        id="queue_backlog",
        name="队列积压严重",
        metric="queue_depth",
        operator=">=", 
        threshold=1000,
        duration_seconds=120,
        enabled=True,
        notification_channels=["email"]
    )
]

# 全局变量
_alert_rules: Dict[str, AlertRule] = {rule.id: rule for rule in DEFAULT_ALERT_RULES}
_active_alerts: Dict[str, Alert] = {}

def collect_system_metrics() -> SystemMetrics:
    """收集系统指标"""
    try:
        # CPU指标
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存指标
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = round(memory.used / (1024**3), 2)
        memory_total_gb = round(memory.total / (1024**3), 2)
        
        # 磁盘指标
        disk = psutil.disk_usage('/')
        disk_usage_percent = round((disk.used / disk.total) * 100, 2)
        disk_free_gb = round(disk.free / (1024**3), 2)
        
        # 网络指标
        network = psutil.net_io_counters()
        network_sent_mb = round(network.bytes_sent / (1024**2), 2)
        network_recv_mb = round(network.bytes_recv / (1024**2), 2)
        
        # 进程指标
        process_count = len(psutil.pids())
        
        # 负载平均值
        try:
            load_average = list(psutil.getloadavg())
        except AttributeError:
            # Windows系统没有getloadavg
            load_average = [0.0, 0.0, 0.0]
        
        # 爬虫相关指标
        crawlers_running = 0
        queue_depth = 0
        response_time_avg = 0.0
        
        try:
            # 尝试获取爬虫状态
            from backend.newslook.api.crawler_control import get_crawler_manager
            manager = get_crawler_manager()
            status = manager.get_status()
            crawlers_running = len([s for s in status.values() if s.get('status') == 'running'])
            
            # 模拟队列深度和响应时间
            queue_depth = _alert_queue.qsize()
            response_time_avg = sum([m.response_time_avg for m in list(_metrics_history)[-10:]]) / min(len(_metrics_history), 10) if _metrics_history else 0
            
        except Exception as e:
            logger.warning(f"无法获取爬虫指标: {str(e)}")
        
        return SystemMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_gb=memory_used_gb,
            memory_total_gb=memory_total_gb,
            disk_usage_percent=disk_usage_percent,
            disk_free_gb=disk_free_gb,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            process_count=process_count,
            load_average=load_average,
            crawlers_running=crawlers_running,
            queue_depth=queue_depth,
            response_time_avg=response_time_avg
        )
        
    except Exception as e:
        logger.error(f"收集系统指标失败: {str(e)}")
        return SystemMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=0,
            memory_percent=0,
            memory_used_gb=0,
            memory_total_gb=0,
            disk_usage_percent=0,
            disk_free_gb=0,
            network_sent_mb=0,
            network_recv_mb=0,
            process_count=0,
            load_average=[0, 0, 0],
            crawlers_running=0,
            queue_depth=0,
            response_time_avg=0
        )

def check_alert_rules(metrics: SystemMetrics):
    """检查告警规则"""
    global _alert_rules, _active_alerts
    
    current_time = datetime.now()
    
    for rule_id, rule in _alert_rules.items():
        if not rule.enabled:
            continue
            
        try:
            # 获取指标值
            metric_value = getattr(metrics, rule.metric, 0)
            
            # 检查阈值
            should_alert = False
            if rule.operator == ">=":
                should_alert = metric_value >= rule.threshold
            elif rule.operator == ">":
                should_alert = metric_value > rule.threshold
            elif rule.operator == "<=":
                should_alert = metric_value <= rule.threshold
            elif rule.operator == "<":
                should_alert = metric_value < rule.threshold
            elif rule.operator == "==":
                should_alert = metric_value == rule.threshold
            
            alert_id = f"{rule_id}_{current_time.strftime('%Y%m%d_%H%M%S')}"
            
            if should_alert:
                # 检查是否已经有活跃告警
                active_alert = _active_alerts.get(rule_id)
                
                if not active_alert:
                    # 创建新告警
                    alert = Alert(
                        id=alert_id,
                        rule_id=rule_id,
                        rule_name=rule.name,
                        metric=rule.metric,
                        value=metric_value,
                        threshold=rule.threshold,
                        level=get_alert_level(rule.metric, metric_value, rule.threshold),
                        message=f"{rule.name}: {rule.metric}={metric_value} {rule.operator} {rule.threshold}",
                        timestamp=current_time.isoformat()
                    )
                    
                    _active_alerts[rule_id] = alert
                    _alert_history.append(alert)
                    
                    # 发送通知
                    send_alert_notifications(alert, rule)
                    
            else:
                # 检查是否需要解决告警
                active_alert = _active_alerts.get(rule_id)
                if active_alert and not active_alert.resolved:
                    active_alert.resolved = True
                    active_alert.resolved_timestamp = current_time.isoformat()
                    logger.info(f"告警已解决: {active_alert.message}")
                    
                    # 从活跃告警中移除
                    del _active_alerts[rule_id]
                    
        except Exception as e:
            logger.error(f"检查告警规则 {rule_id} 失败: {str(e)}")

def get_alert_level(metric: str, value: float, threshold: float) -> str:
    """获取告警级别"""
    if metric in ["cpu_percent", "memory_percent"]:
        if value >= 95:
            return "critical"
        elif value >= 85:
            return "warning"
        else:
            return "info"
    elif metric == "disk_usage_percent":
        if value >= 95:
            return "critical"
        elif value >= 90:
            return "warning"
        else:
            return "info"
    elif metric == "queue_depth":
        if value >= 5000:
            return "critical"
        elif value >= 1000:
            return "warning"
        else:
            return "info"
    else:
        return "info"

def send_alert_notifications(alert: Alert, rule: AlertRule):
    """发送告警通知"""
    try:
        for channel in rule.notification_channels:
            if channel == "email":
                send_email_alert(alert)
            elif channel == "wechat":
                send_wechat_alert(alert)
            elif channel == "webhook":
                send_webhook_alert(alert)
                
    except Exception as e:
        logger.error(f"发送告警通知失败: {str(e)}")

def send_email_alert(alert: Alert):
    """发送邮件告警"""
    try:
        # 从配置获取邮件设置
        email_config = getattr(config, 'email', {})
        if not email_config:
            logger.warning("邮件配置未设置，跳过邮件告警")
            return
            
        smtp_server = email_config.get('smtp_server', 'smtp.gmail.com')
        smtp_port = email_config.get('smtp_port', 587)
        username = email_config.get('username', '')
        password = email_config.get('password', '')
        recipients = email_config.get('recipients', [])
        
        if not username or not password or not recipients:
            logger.warning("邮件配置不完整，跳过邮件告警")
            return
            
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f"【NewsLook告警】{alert.rule_name}"
        
        body = f"""
        告警名称: {alert.rule_name}
        告警级别: {alert.level.upper()}
        触发时间: {alert.timestamp}
        指标名称: {alert.metric}
        当前值: {alert.value}
        阈值: {alert.threshold}
        详细信息: {alert.message}
        
        请及时处理此告警。
        
        -- NewsLook监控系统
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 发送邮件
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"邮件告警发送成功: {alert.message}")
        
    except Exception as e:
        logger.error(f"发送邮件告警失败: {str(e)}")

def send_wechat_alert(alert: Alert):
    """发送企业微信告警"""
    try:
        # 从配置获取企业微信设置
        wechat_config = getattr(config, 'wechat', {})
        webhook_url = wechat_config.get('webhook_url', '')
        
        if not webhook_url:
            logger.warning("企业微信配置未设置，跳过微信告警")
            return
            
        # 构造消息
        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"""# NewsLook系统告警
                
**告警名称**: {alert.rule_name}
**告警级别**: <font color="{'red' if alert.level == 'critical' else 'orange' if alert.level == 'warning' else 'blue'}">{alert.level.upper()}</font>
**触发时间**: {alert.timestamp}
**指标名称**: {alert.metric}
**当前值**: {alert.value}
**阈值**: {alert.threshold}

请及时处理此告警。
                """
            }
        }
        
        # 发送请求
        response = requests.post(
            webhook_url,
            json=message,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"企业微信告警发送成功: {alert.message}")
        else:
            logger.error(f"企业微信告警发送失败: {response.text}")
            
    except Exception as e:
        logger.error(f"发送企业微信告警失败: {str(e)}")

def send_webhook_alert(alert: Alert):
    """发送Webhook告警"""
    try:
        # 从配置获取Webhook设置
        webhook_config = getattr(config, 'webhook', {})
        webhook_url = webhook_config.get('url', '')
        
        if not webhook_url:
            logger.warning("Webhook配置未设置，跳过Webhook告警")
            return
            
        # 构造消息
        payload = {
            "alert": asdict(alert),
            "timestamp": datetime.now().isoformat(),
            "source": "NewsLook"
        }
        
        # 发送请求
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Webhook告警发送成功: {alert.message}")
        else:
            logger.error(f"Webhook告警发送失败: {response.text}")
            
    except Exception as e:
        logger.error(f"发送Webhook告警失败: {str(e)}")

def metrics_collector_worker():
    """指标收集工作者"""
    global _metrics_history
    
    while True:
        try:
            # 收集系统指标
            metrics = collect_system_metrics()
            _metrics_history.append(metrics)
            
            # 检查告警规则
            check_alert_rules(metrics)
            
            # 等待下一次收集(30秒)
            time.sleep(30)
            
        except Exception as e:
            logger.error(f"指标收集异常: {str(e)}")
            time.sleep(30)

# 启动指标收集线程
metrics_thread = threading.Thread(target=metrics_collector_worker, daemon=True)
metrics_thread.start()

# API 路由
@system_monitor_bp.route('/metrics', methods=['GET'])
def get_current_metrics():
    """获取当前系统指标"""
    try:
        metrics = collect_system_metrics()
        return {
            'success': True,
            'data': asdict(metrics),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取系统指标失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@system_monitor_bp.route('/metrics/history', methods=['GET'])
def get_metrics_history():
    """获取历史指标数据"""
    try:
        # 分页参数
        limit = min(request.args.get('limit', 100, type=int), 1000)
        offset = request.args.get('offset', 0, type=int)
        
        # 时间范围参数
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        # 获取历史数据
        history_list = list(_metrics_history)
        
        # 时间过滤
        if start_time or end_time:
            filtered_history = []
            for metrics in history_list:
                metrics_time = datetime.fromisoformat(metrics.timestamp.replace('Z', ''))
                
                if start_time:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', ''))
                    if metrics_time < start_dt:
                        continue
                        
                if end_time:
                    end_dt = datetime.fromisoformat(end_time.replace('Z', ''))
                    if metrics_time > end_dt:
                        continue
                        
                filtered_history.append(metrics)
            history_list = filtered_history
        
        # 分页
        total = len(history_list)
        paged_history = history_list[offset:offset + limit]
        
        return {
            'success': True,
            'data': [asdict(m) for m in paged_history],
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取历史指标失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@system_monitor_bp.route('/health', methods=['GET'])
def health_check():
    """完整健康检查"""
    try:
        level = request.args.get('level', 'basic')
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        # 基础检查
        health_status['checks']['api'] = {'status': 'healthy', 'message': 'API服务正常'}
        
        if level == 'full':
            # 完整健康检查
            try:
                # 系统资源检查
                metrics = collect_system_metrics()
                
                # CPU检查
                if metrics.cpu_percent > 90:
                    health_status['checks']['cpu'] = {'status': 'warning', 'value': metrics.cpu_percent, 'message': 'CPU使用率过高'}
                else:
                    health_status['checks']['cpu'] = {'status': 'healthy', 'value': metrics.cpu_percent}
                
                # 内存检查
                if metrics.memory_percent > 90:
                    health_status['checks']['memory'] = {'status': 'warning', 'value': metrics.memory_percent, 'message': '内存使用率过高'}
                else:
                    health_status['checks']['memory'] = {'status': 'healthy', 'value': metrics.memory_percent}
                
                # 磁盘检查
                if metrics.disk_usage_percent > 90:
                    health_status['checks']['disk'] = {'status': 'critical', 'value': metrics.disk_usage_percent, 'message': '磁盘空间不足'}
                elif metrics.disk_usage_percent > 80:
                    health_status['checks']['disk'] = {'status': 'warning', 'value': metrics.disk_usage_percent, 'message': '磁盘空间紧张'}
                else:
                    health_status['checks']['disk'] = {'status': 'healthy', 'value': metrics.disk_usage_percent}
                
                # 数据库检查
                try:
                    from backend.newslook.config import get_unified_db_path
                    db_path = get_unified_db_path()
                    conn = sqlite3.connect(db_path, timeout=5)
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    conn.close()
                    health_status['checks']['database'] = {'status': 'healthy', 'message': '数据库连接正常'}
                except Exception as e:
                    health_status['checks']['database'] = {'status': 'critical', 'message': f'数据库连接失败: {str(e)}'}
                
                # 爬虫状态检查
                try:
                    from backend.newslook.api.crawler_control import get_crawler_manager
                    manager = get_crawler_manager()
                    crawler_status = manager.get_status()
                    health_status['checks']['crawlers'] = {
                        'status': 'healthy',
                        'running': len([s for s in crawler_status.values() if s.get('status') == 'running']),
                        'total': len(crawler_status)
                    }
                except Exception as e:
                    health_status['checks']['crawlers'] = {'status': 'warning', 'message': f'爬虫状态检查失败: {str(e)}'}
                
            except Exception as e:
                health_status['checks']['system'] = {'status': 'error', 'message': f'系统检查失败: {str(e)}'}
        
        # 确定整体状态
        check_statuses = [check.get('status', 'unknown') for check in health_status['checks'].values()]
        if 'critical' in check_statuses:
            health_status['status'] = 'critical'
        elif 'warning' in check_statuses:
            health_status['status'] = 'warning'
        elif 'error' in check_statuses:
            health_status['status'] = 'error'
        else:
            health_status['status'] = 'healthy'
        
        return health_status
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }, 500

@system_monitor_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """获取告警列表"""
    try:
        # 查询参数
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        level = request.args.get('level')  # info, warning, critical
        limit = min(request.args.get('limit', 50, type=int), 500)
        
        # 获取告警列表
        alerts = list(_alert_history)
        
        # 过滤
        if active_only:
            alerts = [a for a in alerts if not a.resolved]
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        # 按时间排序(最新的在前)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        # 限制数量
        alerts = alerts[:limit]
        
        return {
            'success': True,
            'data': [asdict(a) for a in alerts],
            'total': len(alerts),
            'active_count': len([a for a in _alert_history if not a.resolved]),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取告警列表失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@system_monitor_bp.route('/alerts/rules', methods=['GET'])
def get_alert_rules():
    """获取告警规则"""
    try:
        return {
            'success': True,
            'data': [asdict(rule) for rule in _alert_rules.values()],
            'total': len(_alert_rules),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取告警规则失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@system_monitor_bp.route('/alerts/rules', methods=['POST'])
def create_alert_rule():
    """创建告警规则"""
    try:
        data = request.get_json() or {}
        
        # 验证必需字段
        required_fields = ['id', 'name', 'metric', 'operator', 'threshold']
        for field in required_fields:
            if field not in data:
                return {'error': f'缺少必需字段: {field}', 'success': False}, 400
        
        # 创建规则
        rule = AlertRule(
            id=data['id'],
            name=data['name'],
            metric=data['metric'],
            operator=data['operator'],
            threshold=float(data['threshold']),
            duration_seconds=data.get('duration_seconds', 300),
            enabled=data.get('enabled', True),
            notification_channels=data.get('notification_channels', ['email'])
        )
        
        # 检查ID是否已存在
        if rule.id in _alert_rules:
            return {'error': f'告警规则ID {rule.id} 已存在', 'success': False}, 400
        
        # 保存规则
        _alert_rules[rule.id] = rule
        
        return {
            'success': True,
            'data': asdict(rule),
            'message': f'告警规则 {rule.name} 创建成功',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"创建告警规则失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@system_monitor_bp.route('/alerts/rules/<rule_id>', methods=['PUT'])
def update_alert_rule(rule_id: str):
    """更新告警规则"""
    try:
        if rule_id not in _alert_rules:
            return {'error': f'告警规则 {rule_id} 不存在', 'success': False}, 404
        
        data = request.get_json() or {}
        rule = _alert_rules[rule_id]
        
        # 更新字段
        if 'name' in data:
            rule.name = data['name']
        if 'metric' in data:
            rule.metric = data['metric']
        if 'operator' in data:
            rule.operator = data['operator']
        if 'threshold' in data:
            rule.threshold = float(data['threshold'])
        if 'duration_seconds' in data:
            rule.duration_seconds = int(data['duration_seconds'])
        if 'enabled' in data:
            rule.enabled = bool(data['enabled'])
        if 'notification_channels' in data:
            rule.notification_channels = data['notification_channels']
        
        return {
            'success': True,
            'data': asdict(rule),
            'message': f'告警规则 {rule.name} 更新成功',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"更新告警规则失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@system_monitor_bp.route('/alerts/rules/<rule_id>', methods=['DELETE'])
def delete_alert_rule(rule_id: str):
    """删除告警规则"""
    try:
        if rule_id not in _alert_rules:
            return {'error': f'告警规则 {rule_id} 不存在', 'success': False}, 404
        
        rule = _alert_rules[rule_id]
        del _alert_rules[rule_id]
        
        # 如果有活跃告警，也要清除
        if rule_id in _active_alerts:
            del _active_alerts[rule_id]
        
        return {
            'success': True,
            'message': f'告警规则 {rule.name} 删除成功',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"删除告警规则失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

# 注册蓝图的函数
def register_system_monitor_routes(app):
    """注册系统监控路由"""
    app.register_blueprint(system_monitor_bp)
    logger.info("系统监控API路由已注册") 