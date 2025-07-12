#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康监控系统测试
"""

import pytest
import sys
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.newslook.core.health_monitor import (
    HealthMonitor, HealthStatus, SystemMetrics, get_health_monitor
)


class TestHealthStatus:
    """健康状态数据类测试"""
    
    def test_health_status_creation(self):
        """测试健康状态创建"""
        status = HealthStatus(
            service="test_service",
            status="healthy",
            message="服务正常",
            details={"uptime": 3600}
        )
        
        assert status.service == "test_service"
        assert status.status == "healthy"
        assert status.message == "服务正常"
        assert status.details["uptime"] == 3600
        assert status.last_check is not None
    
    def test_health_status_defaults(self):
        """测试健康状态默认值"""
        status = HealthStatus(
            service="test_service",
            status="healthy",
            message="服务正常"
        )
        
        assert status.details == {}
        assert status.last_check is not None


class TestSystemMetrics:
    """系统指标数据类测试"""
    
    def test_system_metrics_creation(self):
        """测试系统指标创建"""
        metrics = SystemMetrics(
            timestamp="2024-01-01T00:00:00",
            cpu_percent=50.0,
            memory_percent=60.0,
            disk_percent=70.0,
            load_average=[1.0, 1.5, 2.0],
            network_io={"bytes_sent": 1000, "bytes_recv": 2000},
            disk_io={"read_bytes": 500, "write_bytes": 300},
            process_count=100,
            uptime_seconds=3600.0
        )
        
        assert metrics.cpu_percent == 50.0
        assert metrics.memory_percent == 60.0
        assert metrics.disk_percent == 70.0
        assert metrics.load_average == [1.0, 1.5, 2.0]
        assert metrics.network_io["bytes_sent"] == 1000
        assert metrics.disk_io["read_bytes"] == 500
        assert metrics.process_count == 100
        assert metrics.uptime_seconds == 3600.0


class TestHealthMonitor:
    """健康监控器测试"""
    
    def setup_method(self):
        """设置测试方法"""
        self.monitor = HealthMonitor()
    
    def teardown_method(self):
        """清理测试方法"""
        if self.monitor.monitoring_enabled:
            self.monitor.stop_monitoring()
    
    def test_monitor_initialization(self):
        """测试监控器初始化"""
        assert self.monitor.health_checks == {}
        assert self.monitor.metrics_history == []
        assert self.monitor.monitoring_enabled == False
        assert self.monitor.start_time is not None
        assert 'cpu_warning' in self.monitor.thresholds
    
    def test_start_stop_monitoring(self):
        """测试启动和停止监控"""
        # 启动监控
        self.monitor.start_monitoring(1)  # 1秒间隔
        assert self.monitor.monitoring_enabled == True
        assert self.monitor.monitoring_thread is not None
        
        # 等待一段时间让监控运行
        time.sleep(0.5)
        
        # 停止监控
        self.monitor.stop_monitoring()
        assert self.monitor.monitoring_enabled == False
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    @patch('psutil.disk_io_counters')
    @patch('psutil.pids')
    def test_collect_system_metrics(self, mock_pids, mock_disk_io, mock_net_io, 
                                   mock_disk, mock_memory, mock_cpu):
        """测试系统指标收集"""
        # Mock系统调用
        mock_cpu.return_value = 50.0
        
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 60.0
        mock_memory.return_value = mock_memory_obj
        
        mock_disk_obj = Mock()
        mock_disk_obj.percent = 70.0
        mock_disk.return_value = mock_disk_obj
        
        mock_net_obj = Mock()
        mock_net_obj.bytes_sent = 1000
        mock_net_obj.bytes_recv = 2000
        mock_net_obj.packets_sent = 10
        mock_net_obj.packets_recv = 20
        mock_net_io.return_value = mock_net_obj
        
        mock_disk_io_obj = Mock()
        mock_disk_io_obj.read_bytes = 500
        mock_disk_io_obj.write_bytes = 300
        mock_disk_io_obj.read_count = 5
        mock_disk_io_obj.write_count = 3
        mock_disk_io.return_value = mock_disk_io_obj
        
        mock_pids.return_value = [1, 2, 3, 4, 5]  # 5个进程
        
        # 收集指标
        metrics = self.monitor._collect_system_metrics()
        
        assert metrics is not None
        assert metrics.cpu_percent == 50.0
        assert metrics.memory_percent == 60.0
        assert metrics.disk_percent == 70.0
        assert metrics.network_io['bytes_sent'] == 1000
        assert metrics.disk_io['read_bytes'] == 500
        assert metrics.process_count == 5
    
    def test_store_metrics(self):
        """测试指标存储"""
        # 创建测试指标
        metrics = SystemMetrics(
            timestamp="2024-01-01T00:00:00",
            cpu_percent=50.0,
            memory_percent=60.0,
            disk_percent=70.0,
            load_average=None,
            network_io={},
            disk_io={},
            process_count=100,
            uptime_seconds=3600.0
        )
        
        # 存储指标
        self.monitor._store_metrics(metrics)
        
        assert len(self.monitor.metrics_history) == 1
        assert self.monitor.metrics_history[0] == metrics
        
        # 测试历史记录限制
        original_max = self.monitor.max_history
        self.monitor.max_history = 2
        
        # 添加更多指标
        for i in range(3):
            self.monitor._store_metrics(metrics)
        
        assert len(self.monitor.metrics_history) <= 2
        self.monitor.max_history = original_max
    
    def test_update_health_status(self):
        """测试健康状态更新"""
        service = "test_service"
        status = "healthy"
        message = "服务正常"
        details = {"uptime": 3600}
        
        self.monitor._update_health_status(service, status, message, details)
        
        assert service in self.monitor.health_checks
        health_status = self.monitor.health_checks[service]
        assert health_status.service == service
        assert health_status.status == status
        assert health_status.message == message
        assert health_status.details == details
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.glob')
    @patch('sqlite3.connect')
    def test_check_database_health(self, mock_connect, mock_glob, mock_exists):
        """测试数据库健康检查"""
        # Mock数据库检查
        mock_exists.return_value = True
        mock_glob.return_value = [Path('test1.db'), Path('test2.db')]
        
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (5,)
        mock_connect.return_value = mock_conn
        
        # 执行检查
        self.monitor._check_database_health()
        
        # 验证结果
        assert 'database' in self.monitor.health_checks
        health_status = self.monitor.health_checks['database']
        assert health_status.status == 'healthy'
        assert 'All 2 databases accessible' in health_status.message
    
    @patch('psutil.disk_usage')
    def test_check_filesystem_health(self, mock_disk_usage):
        """测试文件系统健康检查"""
        # Mock磁盘使用情况
        mock_usage = Mock()
        mock_usage.percent = 75.0  # 低于警告阈值
        mock_usage.free = 100 * (1024**3)  # 100GB
        mock_usage.total = 400 * (1024**3)  # 400GB
        mock_disk_usage.return_value = mock_usage
        
        # 执行检查
        self.monitor._check_filesystem_health()
        
        # 验证结果
        assert 'filesystem' in self.monitor.health_checks
        health_status = self.monitor.health_checks['filesystem']
        assert health_status.status == 'healthy'
        assert '75.0%' in health_status.message
        assert health_status.details['usage_percent'] == 75.0
    
    def test_get_health_status(self):
        """测试获取健康状态"""
        # 添加一些健康检查
        self.monitor._update_health_status('service1', 'healthy', 'OK')
        self.monitor._update_health_status('service2', 'warning', 'Warning')
        self.monitor._update_health_status('service3', 'unhealthy', 'Error')
        
        # 获取状态
        status = self.monitor.get_health_status()
        
        assert status['overall_status'] == 'unhealthy'  # 有不健康的服务
        assert status['summary']['total_services'] == 3
        assert status['summary']['healthy_services'] == 1
        assert status['summary']['warning_services'] == 1
        assert status['summary']['unhealthy_services'] == 1
        assert 'timestamp' in status
        assert 'services' in status
    
    def test_get_system_metrics(self):
        """测试获取系统指标"""
        # 添加一些历史指标
        for i in range(5):
            metrics = SystemMetrics(
                timestamp=f"2024-01-01T{i:02d}:00:00",
                cpu_percent=float(i * 10),
                memory_percent=float(i * 15),
                disk_percent=50.0,
                load_average=None,
                network_io={},
                disk_io={},
                process_count=100,
                uptime_seconds=3600.0
            )
            self.monitor._store_metrics(metrics)
        
        # 获取指标
        with patch.object(self.monitor, '_collect_system_metrics') as mock_collect:
            mock_collect.return_value = SystemMetrics(
                timestamp="2024-01-01T05:00:00",
                cpu_percent=50.0,
                memory_percent=75.0,
                disk_percent=50.0,
                load_average=None,
                network_io={},
                disk_io={},
                process_count=100,
                uptime_seconds=3600.0
            )
            
            metrics = self.monitor.get_system_metrics()
        
        assert 'current' in metrics
        assert 'history' in metrics
        assert 'summary' in metrics
        assert metrics['current']['cpu_percent'] == 50.0
        assert len(metrics['history']) <= 10  # 最多10条历史记录
    
    def test_get_system_info(self):
        """测试获取系统信息"""
        with patch('platform.system', return_value='Linux'), \
             patch('platform.release', return_value='5.4.0'), \
             patch('psutil.cpu_count', return_value=8):
            
            info = self.monitor.get_system_info()
            
            assert 'platform' in info
            assert 'hardware' in info
            assert 'application' in info
            assert info['platform']['system'] == 'Linux'
            assert info['platform']['release'] == '5.4.0'
            assert info['hardware']['cpu_count'] == 8


class TestGlobalHealthMonitor:
    """全局健康监控器测试"""
    
    def test_get_health_monitor_singleton(self):
        """测试获取健康监控器单例"""
        monitor1 = get_health_monitor()
        monitor2 = get_health_monitor()
        
        assert monitor1 is monitor2  # 应该是同一个实例
        assert isinstance(monitor1, HealthMonitor)


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 