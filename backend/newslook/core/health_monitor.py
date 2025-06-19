#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康检查和系统监控
提供系统状态监控、健康检查端点和关键指标收集
"""

import os
import psutil
import platform
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
import threading

from .config_manager import get_config
from .logger_manager import get_logger


@dataclass
class HealthStatus:
    """健康状态数据类"""
    service: str
    status: str  # 'healthy', 'warning', 'unhealthy'
    message: str
    details: Dict[str, Any] = None
    last_check: str = None
    
    def __post_init__(self):
        if self.last_check is None:
            self.last_check = datetime.now().isoformat()
        if self.details is None:
            self.details = {}


@dataclass
class SystemMetrics:
    """系统指标数据类"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    load_average: Optional[List[float]]
    network_io: Dict[str, int]
    disk_io: Dict[str, int]
    process_count: int
    uptime_seconds: float


class HealthMonitor:
    """健康监控器"""
    
    def __init__(self):
        """初始化健康监控器"""
        self.config = get_config()
        self.logger = get_logger('newslook', 'health_monitor')
        
        # 监控状态
        self.health_checks = {}
        self.metrics_history = []
        self.max_history = 100  # 保留最近100条记录
        
        # 系统启动时间
        self.start_time = time.time()
        
        # 监控线程
        self.monitoring_thread = None
        self.monitoring_enabled = False
        
        # 阈值配置
        self.thresholds = {
            'cpu_warning': 80.0,
            'cpu_critical': 95.0,
            'memory_warning': 85.0,
            'memory_critical': 95.0,
            'disk_warning': 85.0,
            'disk_critical': 95.0,
            'response_time_warning': 1000,  # ms
            'response_time_critical': 5000,  # ms
        }
    
    def start_monitoring(self, interval: int = 60):
        """开始监控"""
        if self.monitoring_enabled:
            return
        
        self.monitoring_enabled = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitoring_thread.start()
        self.logger.info(f"Health monitoring started with {interval}s interval")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_enabled = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        self.logger.info("Health monitoring stopped")
    
    def _monitoring_loop(self, interval: int):
        """监控循环"""
        while self.monitoring_enabled:
            try:
                # 收集系统指标
                metrics = self._collect_system_metrics()
                self._store_metrics(metrics)
                
                # 执行健康检查
                self._perform_health_checks()
                
                # 检查告警条件
                self._check_alerts(metrics)
                
                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                time.sleep(interval)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 系统负载
            load_avg = None
            if hasattr(os, 'getloadavg'):
                load_avg = list(os.getloadavg())
            
            # 网络IO
            net_io = psutil.net_io_counters()
            network_io = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
            
            # 磁盘IO
            disk_io_counters = psutil.disk_io_counters()
            disk_io = {
                'read_bytes': disk_io_counters.read_bytes,
                'write_bytes': disk_io_counters.write_bytes,
                'read_count': disk_io_counters.read_count,
                'write_count': disk_io_counters.write_count
            } if disk_io_counters else {}
            
            # 进程数量
            process_count = len(psutil.pids())
            
            # 运行时间
            uptime_seconds = time.time() - self.start_time
            
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                load_average=load_avg,
                network_io=network_io,
                disk_io=disk_io,
                process_count=process_count,
                uptime_seconds=uptime_seconds
            )
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return None
    
    def _store_metrics(self, metrics: SystemMetrics):
        """存储指标数据"""
        if not metrics:
            return
        
        self.metrics_history.append(metrics)
        
        # 保持历史记录大小
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]
    
    def _perform_health_checks(self):
        """执行健康检查"""
        checks = [
            self._check_database_health,
            self._check_filesystem_health,
            self._check_memory_health,
            self._check_cpu_health,
            self._check_process_health
        ]
        
        for check in checks:
            try:
                check()
            except Exception as e:
                self.logger.error(f"Health check error: {e}", exc_info=True)
    
    def _check_database_health(self):
        """检查数据库健康状态"""
        try:
            # 检查数据库文件存在性和可访问性
            db_path = Path('data')
            if not db_path.exists():
                self._update_health_status(
                    'database',
                    'unhealthy',
                    'Database directory not found',
                    {'path': str(db_path)}
                )
                return
            
            # 检查数据库文件
            db_files = list(db_path.glob('*.db'))
            if not db_files:
                self._update_health_status(
                    'database',
                    'warning',
                    'No database files found',
                    {'path': str(db_path)}
                )
                return
            
            # 测试数据库连接
            healthy_dbs = 0
            total_dbs = len(db_files)
            
            for db_file in db_files:
                try:
                    conn = sqlite3.connect(str(db_file), timeout=5)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master")
                    cursor.fetchone()
                    conn.close()
                    healthy_dbs += 1
                except Exception as e:
                    self.logger.warning(f"Database {db_file} health check failed: {e}")
            
            if healthy_dbs == total_dbs:
                self._update_health_status(
                    'database',
                    'healthy',
                    f'All {total_dbs} databases accessible',
                    {'healthy_count': healthy_dbs, 'total_count': total_dbs}
                )
            elif healthy_dbs > 0:
                self._update_health_status(
                    'database',
                    'warning',
                    f'{healthy_dbs}/{total_dbs} databases accessible',
                    {'healthy_count': healthy_dbs, 'total_count': total_dbs}
                )
            else:
                self._update_health_status(
                    'database',
                    'unhealthy',
                    'No databases accessible',
                    {'healthy_count': healthy_dbs, 'total_count': total_dbs}
                )
        
        except Exception as e:
            self._update_health_status(
                'database',
                'unhealthy',
                f'Database health check failed: {str(e)}',
                {'error': str(e)}
            )
    
    def _check_filesystem_health(self):
        """检查文件系统健康状态"""
        try:
            disk_usage = psutil.disk_usage('/')
            usage_percent = disk_usage.percent
            
            if usage_percent >= self.thresholds['disk_critical']:
                status = 'unhealthy'
                message = f'Disk usage critical: {usage_percent:.1f}%'
            elif usage_percent >= self.thresholds['disk_warning']:
                status = 'warning'
                message = f'Disk usage high: {usage_percent:.1f}%'
            else:
                status = 'healthy'
                message = f'Disk usage normal: {usage_percent:.1f}%'
            
            self._update_health_status(
                'filesystem',
                status,
                message,
                {
                    'usage_percent': usage_percent,
                    'free_gb': disk_usage.free / (1024**3),
                    'total_gb': disk_usage.total / (1024**3)
                }
            )
        
        except Exception as e:
            self._update_health_status(
                'filesystem',
                'unhealthy',
                f'Filesystem check failed: {str(e)}',
                {'error': str(e)}
            )
    
    def _check_memory_health(self):
        """检查内存健康状态"""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            if usage_percent >= self.thresholds['memory_critical']:
                status = 'unhealthy'
                message = f'Memory usage critical: {usage_percent:.1f}%'
            elif usage_percent >= self.thresholds['memory_warning']:
                status = 'warning'
                message = f'Memory usage high: {usage_percent:.1f}%'
            else:
                status = 'healthy'
                message = f'Memory usage normal: {usage_percent:.1f}%'
            
            self._update_health_status(
                'memory',
                status,
                message,
                {
                    'usage_percent': usage_percent,
                    'available_gb': memory.available / (1024**3),
                    'total_gb': memory.total / (1024**3)
                }
            )
        
        except Exception as e:
            self._update_health_status(
                'memory',
                'unhealthy',
                f'Memory check failed: {str(e)}',
                {'error': str(e)}
            )
    
    def _check_cpu_health(self):
        """检查CPU健康状态"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent >= self.thresholds['cpu_critical']:
                status = 'unhealthy'
                message = f'CPU usage critical: {cpu_percent:.1f}%'
            elif cpu_percent >= self.thresholds['cpu_warning']:
                status = 'warning'
                message = f'CPU usage high: {cpu_percent:.1f}%'
            else:
                status = 'healthy'
                message = f'CPU usage normal: {cpu_percent:.1f}%'
            
            # 获取CPU核心数和负载
            cpu_count = psutil.cpu_count()
            load_avg = None
            if hasattr(os, 'getloadavg'):
                load_avg = list(os.getloadavg())
            
            self._update_health_status(
                'cpu',
                status,
                message,
                {
                    'usage_percent': cpu_percent,
                    'cpu_count': cpu_count,
                    'load_average': load_avg
                }
            )
        
        except Exception as e:
            self._update_health_status(
                'cpu',
                'unhealthy',
                f'CPU check failed: {str(e)}',
                {'error': str(e)}
            )
    
    def _check_process_health(self):
        """检查进程健康状态"""
        try:
            current_process = psutil.Process()
            
            # 获取进程信息
            memory_info = current_process.memory_info()
            cpu_percent = current_process.cpu_percent()
            
            # 检查进程状态
            status = current_process.status()
            create_time = current_process.create_time()
            uptime = time.time() - create_time
            
            self._update_health_status(
                'process',
                'healthy',
                f'Process running normally for {uptime/3600:.1f} hours',
                {
                    'pid': current_process.pid,
                    'status': status,
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_info.rss / (1024**2),
                    'uptime_hours': uptime / 3600
                }
            )
        
        except Exception as e:
            self._update_health_status(
                'process',
                'unhealthy',
                f'Process check failed: {str(e)}',
                {'error': str(e)}
            )
    
    def _update_health_status(self, service: str, status: str, message: str, details: Dict[str, Any] = None):
        """更新健康状态"""
        health_status = HealthStatus(
            service=service,
            status=status,
            message=message,
            details=details or {}
        )
        
        self.health_checks[service] = health_status
        
        # 记录状态变化
        self.logger.info(
            f"Health check - {service}: {status}",
            extra={
                'service': service,
                'status': status,
                'message': message,
                'details': details
            }
        )
    
    def _check_alerts(self, metrics: SystemMetrics):
        """检查告警条件"""
        if not metrics:
            return
        
        alerts = []
        
        # CPU告警
        if metrics.cpu_percent >= self.thresholds['cpu_critical']:
            alerts.append(f"CPU usage critical: {metrics.cpu_percent:.1f}%")
        elif metrics.cpu_percent >= self.thresholds['cpu_warning']:
            alerts.append(f"CPU usage high: {metrics.cpu_percent:.1f}%")
        
        # 内存告警
        if metrics.memory_percent >= self.thresholds['memory_critical']:
            alerts.append(f"Memory usage critical: {metrics.memory_percent:.1f}%")
        elif metrics.memory_percent >= self.thresholds['memory_warning']:
            alerts.append(f"Memory usage high: {metrics.memory_percent:.1f}%")
        
        # 磁盘告警
        if metrics.disk_percent >= self.thresholds['disk_critical']:
            alerts.append(f"Disk usage critical: {metrics.disk_percent:.1f}%")
        elif metrics.disk_percent >= self.thresholds['disk_warning']:
            alerts.append(f"Disk usage high: {metrics.disk_percent:.1f}%")
        
        # 记录告警
        for alert in alerts:
            self.logger.warning(f"System alert: {alert}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        overall_status = 'healthy'
        unhealthy_services = []
        warning_services = []
        
        for service, health in self.health_checks.items():
            if health.status == 'unhealthy':
                unhealthy_services.append(service)
                overall_status = 'unhealthy'
            elif health.status == 'warning':
                warning_services.append(service)
                if overall_status == 'healthy':
                    overall_status = 'warning'
        
        return {
            'overall_status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'services': {name: asdict(health) for name, health in self.health_checks.items()},
            'summary': {
                'total_services': len(self.health_checks),
                'healthy_services': len([h for h in self.health_checks.values() if h.status == 'healthy']),
                'warning_services': len(warning_services),
                'unhealthy_services': len(unhealthy_services)
            }
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        current_metrics = self._collect_system_metrics()
        
        return {
            'current': asdict(current_metrics) if current_metrics else None,
            'history': [asdict(m) for m in self.metrics_history[-10:]],  # 最近10条记录
            'summary': self._get_metrics_summary()
        }
    
    def _get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        if not self.metrics_history:
            return {}
        
        recent_metrics = self.metrics_history[-10:]  # 最近10条记录
        
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        disk_values = [m.disk_percent for m in recent_metrics]
        
        return {
            'cpu': {
                'current': cpu_values[-1] if cpu_values else 0,
                'average': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'max': max(cpu_values) if cpu_values else 0
            },
            'memory': {
                'current': memory_values[-1] if memory_values else 0,
                'average': sum(memory_values) / len(memory_values) if memory_values else 0,
                'max': max(memory_values) if memory_values else 0
            },
            'disk': {
                'current': disk_values[-1] if disk_values else 0,
                'average': sum(disk_values) / len(disk_values) if disk_values else 0,
                'max': max(disk_values) if disk_values else 0
            },
            'uptime_hours': (time.time() - self.start_time) / 3600
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version()
            },
            'hardware': {
                'cpu_count': psutil.cpu_count(),
                'cpu_freq': dict(asdict(psutil.cpu_freq())) if psutil.cpu_freq() else None,
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'disk_total_gb': psutil.disk_usage('/').total / (1024**3)
            },
            'application': {
                'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                'uptime_seconds': time.time() - self.start_time,
                'monitoring_enabled': self.monitoring_enabled
            }
        }


# 全局健康监控器实例
_health_monitor = None

def get_health_monitor() -> HealthMonitor:
    """获取全局健康监控器实例"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor 