#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 监控器组件
负责监控爬虫运行状态
"""

import os
import time
import json
import logging
import threading
import datetime
from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod

from backend.app.utils.logger import get_crawler_logger

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('monitors')

class BaseMonitor(ABC):
    """监控器基类，定义监控器的接口"""
    
    @abstractmethod
    def start(self):
        """开始监控"""
        pass
    
    @abstractmethod
    def stop(self):
        """停止监控"""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict:
        """获取监控状态"""
        pass


class PerformanceMonitor(BaseMonitor):
    """性能监控器，监控爬虫性能数据"""
    
    def __init__(self, name: str, log_dir: Optional[str] = None, 
                 interval: float = 60.0, max_records: int = 1000):
        """
        初始化性能监控器
        
        Args:
            name: 监控器名称
            log_dir: 日志目录
            interval: 监控间隔（秒）
            max_records: 最大记录数
        """
        self.name = name
        self.interval = interval
        self.max_records = max_records
        self.running = False
        self.thread = None
        
        # 监控数据
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0.0,
            'total_items_processed': 0,
            'items_saved': 0,
            'items_filtered': 0,
            'memory_usage': 0,
            'cpu_usage': 0,
            'request_rate': 0.0,  # 每秒请求数
            'throughput': 0.0,    # 每秒处理项目数
        }
        
        # 时间序列数据
        self.time_series = []
        
        # 设置日志路径
        if log_dir:
            self.log_dir = log_dir
        else:
            self.log_dir = os.path.join('logs', 'performance', self.name)
        
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, f"{self.name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        logger.info(f"性能监控器初始化成功: {self.name}, 间隔: {self.interval}秒, 日志: {self.log_file}")
        
    def start(self):
        """开始监控"""
        if self.running:
            logger.warning(f"监控器 {self.name} 已经在运行")
            return
            
        self.running = True
        self.stats['start_time'] = datetime.datetime.now().isoformat()
        
        # 启动监控线程
        self.thread = threading.Thread(target=self._monitor_task, daemon=True)
        self.thread.start()
        
        logger.info(f"监控器 {self.name} 已启动")
    
    def stop(self):
        """停止监控"""
        if not self.running:
            logger.warning(f"监控器 {self.name} 已经停止")
            return
            
        self.running = False
        self.stats['end_time'] = datetime.datetime.now().isoformat()
        
        # 等待线程结束
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        # 保存最终报告
        self._save_report()
        
        logger.info(f"监控器 {self.name} 已停止")
    
    def get_status(self) -> Dict:
        """
        获取监控状态
        
        Returns:
            Dict: 当前监控状态
        """
        # 计算运行时间
        if self.stats['start_time']:
            start_time = datetime.datetime.fromisoformat(self.stats['start_time'])
            current_time = datetime.datetime.now()
            runtime = (current_time - start_time).total_seconds()
        else:
            runtime = 0
        
        # 计算请求率和吞吐量
        if runtime > 0:
            self.stats['request_rate'] = self.stats['total_requests'] / runtime
            self.stats['throughput'] = self.stats['total_items_processed'] / runtime
        
        # 获取内存和CPU使用情况
        try:
            import psutil
            process = psutil.Process(os.getpid())
            self.stats['memory_usage'] = process.memory_info().rss / 1024 / 1024  # MB
            self.stats['cpu_usage'] = process.cpu_percent(interval=0.1)
        except (ImportError, Exception) as e:
            logger.debug(f"获取系统资源使用情况失败: {str(e)}")
        
        # 返回当前状态
        status = self.stats.copy()
        status['running'] = self.running
        
        # 添加最近的时间序列数据点(最多10个)
        if self.time_series:
            status['recent_data'] = self.time_series[-10:]
        
        return status
    
    def update_stats(self, new_stats: Dict):
        """
        更新监控数据
        
        Args:
            new_stats: 新的统计数据
        """
        # 更新累计值
        for key in ['total_requests', 'successful_requests', 'failed_requests', 
                   'total_items_processed', 'items_saved', 'items_filtered']:
            if key in new_stats:
                self.stats[key] += new_stats[key]
        
        # 更新平均响应时间（加权平均）
        if 'response_time' in new_stats and 'successful_requests' in new_stats and new_stats['successful_requests'] > 0:
            total_success = self.stats['successful_requests']
            old_avg = self.stats['avg_response_time']
            new_success = new_stats['successful_requests']
            new_avg = new_stats['response_time']
            
            if total_success > 0:
                self.stats['avg_response_time'] = ((total_success - new_success) * old_avg + new_success * new_avg) / total_success
        
        # 添加时间戳
        timestamp = datetime.datetime.now().isoformat()
        data_point = {
            'timestamp': timestamp,
            **self.get_status()
        }
        
        # 添加到时间序列
        self.time_series.append(data_point)
        
        # 限制时间序列大小
        if len(self.time_series) > self.max_records:
            self.time_series = self.time_series[-self.max_records:]
    
    def _monitor_task(self):
        """监控任务，定期收集和保存性能数据"""
        last_save_time = time.time()
        
        while self.running:
            try:
                # 获取当前状态
                status = self.get_status()
                
                # 记录到时间序列
                timestamp = datetime.datetime.now().isoformat()
                data_point = {
                    'timestamp': timestamp,
                    **status
                }
                self.time_series.append(data_point)
                
                # 限制时间序列大小
                if len(self.time_series) > self.max_records:
                    self.time_series = self.time_series[-self.max_records:]
                
                # 定期保存报告
                current_time = time.time()
                if current_time - last_save_time >= 300:  # 每5分钟保存一次
                    self._save_report()
                    last_save_time = current_time
                
                # 暂停指定间隔
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"监控任务出错: {str(e)}")
                time.sleep(self.interval)
    
    def _save_report(self):
        """保存监控报告"""
        try:
            # 准备报告数据
            report = {
                'stats': self.stats,
                'time_series': self.time_series
            }
            
            # 写入JSON文件
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"监控报告已保存: {self.log_file}")
            
        except Exception as e:
            logger.error(f"保存监控报告失败: {str(e)}")


class StatusMonitor(BaseMonitor):
    """状态监控器，监控爬虫状态和警报"""
    
    def __init__(self, name: str, alert_callbacks: Optional[List[Callable]] = None):
        """
        初始化状态监控器
        
        Args:
            name: 监控器名称
            alert_callbacks: 警报回调函数列表
        """
        self.name = name
        self.alert_callbacks = alert_callbacks or []
        self.running = False
        self.thread = None
        
        # 爬虫状态
        self.status = {
            'state': 'stopped',  # 'stopped', 'running', 'paused', 'error'
            'last_activity': None,
            'last_error': None,
            'error_count': 0,
            'warnings': [],
            'messages': []
        }
        
        logger.info(f"状态监控器初始化成功: {self.name}")
    
    def start(self):
        """开始监控"""
        if self.running:
            logger.warning(f"状态监控器 {self.name} 已经在运行")
            return
            
        self.running = True
        self.status['state'] = 'running'
        self.status['last_activity'] = datetime.datetime.now().isoformat()
        
        # 启动监控线程
        self.thread = threading.Thread(target=self._monitor_task, daemon=True)
        self.thread.start()
        
        logger.info(f"状态监控器 {self.name} 已启动")
    
    def stop(self):
        """停止监控"""
        if not self.running:
            logger.warning(f"状态监控器 {self.name} 已经停止")
            return
            
        self.running = False
        self.status['state'] = 'stopped'
        
        # 等待线程结束
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info(f"状态监控器 {self.name} 已停止")
    
    def get_status(self) -> Dict:
        """
        获取监控状态
        
        Returns:
            Dict: 当前状态
        """
        return self.status.copy()
    
    def update_activity(self):
        """更新活动时间"""
        self.status['last_activity'] = datetime.datetime.now().isoformat()
    
    def record_error(self, error: str):
        """
        记录错误
        
        Args:
            error: 错误信息
        """
        timestamp = datetime.datetime.now().isoformat()
        self.status['last_error'] = {'time': timestamp, 'message': error}
        self.status['error_count'] += 1
        
        # 如果错误过多，更新状态为error
        if self.status['error_count'] >= 10 and self.status['state'] != 'error':
            self.status['state'] = 'error'
            self._send_alert(f"爬虫 {self.name} 连续出现 {self.status['error_count']} 个错误，已标记为错误状态")
    
    def record_warning(self, warning: str):
        """
        记录警告
        
        Args:
            warning: 警告信息
        """
        timestamp = datetime.datetime.now().isoformat()
        self.status['warnings'].append({'time': timestamp, 'message': warning})
        
        # 限制警告数量
        if len(self.status['warnings']) > 50:
            self.status['warnings'] = self.status['warnings'][-50:]
    
    def record_message(self, message: str):
        """
        记录消息
        
        Args:
            message: 消息内容
        """
        timestamp = datetime.datetime.now().isoformat()
        self.status['messages'].append({'time': timestamp, 'message': message})
        
        # 限制消息数量
        if len(self.status['messages']) > 100:
            self.status['messages'] = self.status['messages'][-100:]
    
    def _monitor_task(self):
        """监控任务，检查状态和发送警报"""
        while self.running:
            try:
                # 检查最后活动时间
                if self.status['last_activity']:
                    last_activity = datetime.datetime.fromisoformat(self.status['last_activity'])
                    current_time = datetime.datetime.now()
                    inactive_duration = (current_time - last_activity).total_seconds()
                    
                    # 如果5分钟没有活动，发送警告
                    if inactive_duration > 300 and self.status['state'] == 'running':
                        warning = f"爬虫 {self.name} 已经 {int(inactive_duration)} 秒没有活动"
                        self.record_warning(warning)
                        logger.warning(warning)
                        
                        # 如果15分钟没有活动，视为错误
                        if inactive_duration > 900:
                            error = f"爬虫 {self.name} 已经 {int(inactive_duration)} 秒没有活动，可能已经卡住"
                            self.record_error(error)
                            self._send_alert(error)
                
                # 暂停一会儿
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"状态监控任务出错: {str(e)}")
                time.sleep(30)
    
    def _send_alert(self, message: str):
        """
        发送警报
        
        Args:
            message: 警报消息
        """
        # 记录警报
        logger.warning(f"警报: {message}")
        
        # 调用警报回调
        for callback in self.alert_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"调用警报回调失败: {str(e)}")


class ResourceMonitor(BaseMonitor):
    """资源监控器，监控系统资源使用情况"""
    
    def __init__(self, name: str, interval: float = 60.0, 
                 alert_threshold: Dict[str, float] = None):
        """
        初始化资源监控器
        
        Args:
            name: 监控器名称
            interval: 监控间隔（秒）
            alert_threshold: 警报阈值
        """
        self.name = name
        self.interval = interval
        self.running = False
        self.thread = None
        
        # 默认警报阈值
        self.alert_threshold = {
            'cpu': 90.0,  # CPU使用率超过90%
            'memory': 85.0,  # 内存使用率超过85%
            'disk': 90.0  # 磁盘使用率超过90%
        }
        
        # 更新自定义阈值
        if alert_threshold:
            self.alert_threshold.update(alert_threshold)
        
        # 监控数据
        self.resources = {
            'cpu_usage': 0.0,
            'memory_usage': 0.0,
            'memory_percent': 0.0,
            'disk_usage': 0.0,
            'disk_percent': 0.0,
            'process_count': 0,
            'thread_count': 0,
            'network_io': {'sent_bytes': 0, 'recv_bytes': 0},
            'io_counters': {'read_bytes': 0, 'write_bytes': 0}
        }
        
        # 时间序列数据
        self.time_series = []
        
        logger.info(f"资源监控器初始化成功: {self.name}, 间隔: {self.interval}秒")
        
        # 检查psutil可用性
        try:
            import psutil
            self.psutil_available = True
        except ImportError:
            logger.warning("psutil模块不可用，资源监控功能受限")
            self.psutil_available = False
    
    def start(self):
        """开始监控"""
        if self.running:
            logger.warning(f"资源监控器 {self.name} 已经在运行")
            return
            
        self.running = True
        
        # 启动监控线程
        self.thread = threading.Thread(target=self._monitor_task, daemon=True)
        self.thread.start()
        
        logger.info(f"资源监控器 {self.name} 已启动")
    
    def stop(self):
        """停止监控"""
        if not self.running:
            logger.warning(f"资源监控器 {self.name} 已经停止")
            return
            
        self.running = False
        
        # 等待线程结束
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info(f"资源监控器 {self.name} 已停止")
    
    def get_status(self) -> Dict:
        """
        获取监控状态
        
        Returns:
            Dict: 当前资源使用情况
        """
        # 如果psutil可用，获取最新的资源使用情况
        if self.psutil_available:
            try:
                self._update_resources()
            except Exception as e:
                logger.error(f"更新资源信息失败: {str(e)}")
        
        # 返回当前状态
        status = {
            'resources': self.resources,
            'running': self.running,
            'alert_threshold': self.alert_threshold
        }
        
        # 添加最近的时间序列数据点(最多10个)
        if self.time_series:
            status['recent_data'] = self.time_series[-10:]
        
        return status
    
    def _update_resources(self):
        """更新资源使用情况"""
        if not self.psutil_available:
            return
            
        try:
            import psutil
            
            # 获取当前进程
            process = psutil.Process(os.getpid())
            
            # 更新CPU使用率
            self.resources['cpu_usage'] = psutil.cpu_percent(interval=0.1)
            
            # 更新内存使用情况
            memory = psutil.virtual_memory()
            self.resources['memory_usage'] = memory.used / 1024 / 1024  # MB
            self.resources['memory_percent'] = memory.percent
            
            # 更新磁盘使用情况
            disk = psutil.disk_usage('/')
            self.resources['disk_usage'] = disk.used / 1024 / 1024 / 1024  # GB
            self.resources['disk_percent'] = disk.percent
            
            # 更新进程和线程数量
            self.resources['process_count'] = len(psutil.pids())
            self.resources['thread_count'] = len(process.threads())
            
            # 更新网络IO
            net_io = psutil.net_io_counters()
            self.resources['network_io'] = {
                'sent_bytes': net_io.bytes_sent,
                'recv_bytes': net_io.bytes_recv
            }
            
            # 更新IO计数器
            io_counters = psutil.disk_io_counters()
            self.resources['io_counters'] = {
                'read_bytes': io_counters.read_bytes,
                'write_bytes': io_counters.write_bytes
            }
            
        except Exception as e:
            logger.error(f"获取资源使用情况失败: {str(e)}")
    
    def _monitor_task(self):
        """监控任务，定期收集和检查资源使用情况"""
        while self.running:
            try:
                # 更新资源使用情况
                self._update_resources()
                
                # 检查资源使用是否超过阈值
                self._check_thresholds()
                
                # 记录到时间序列
                timestamp = datetime.datetime.now().isoformat()
                data_point = {
                    'timestamp': timestamp,
                    **self.resources
                }
                self.time_series.append(data_point)
                
                # 限制时间序列大小
                if len(self.time_series) > 100:
                    self.time_series = self.time_series[-100:]
                
                # 暂停指定间隔
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"资源监控任务出错: {str(e)}")
                time.sleep(self.interval)
    
    def _check_thresholds(self):
        """检查资源使用是否超过阈值"""
        # 检查CPU使用率
        if self.resources['cpu_usage'] > self.alert_threshold['cpu']:
            logger.warning(f"CPU使用率过高: {self.resources['cpu_usage']}% > {self.alert_threshold['cpu']}%")
        
        # 检查内存使用率
        if self.resources['memory_percent'] > self.alert_threshold['memory']:
            logger.warning(f"内存使用率过高: {self.resources['memory_percent']}% > {self.alert_threshold['memory']}%")
        
        # 检查磁盘使用率
        if self.resources['disk_percent'] > self.alert_threshold['disk']:
            logger.warning(f"磁盘使用率过高: {self.resources['disk_percent']}% > {self.alert_threshold['disk']}%")


def create_monitor(monitor_type: str = 'performance', **kwargs) -> BaseMonitor:
    """
    创建监控器工厂函数
    
    Args:
        monitor_type: 监控器类型（'performance', 'status', 'resource'）
        **kwargs: 其他参数
        
    Returns:
        BaseMonitor: 监控器实例
    """
    if monitor_type == 'status':
        return StatusMonitor(**kwargs)
    elif monitor_type == 'resource':
        return ResourceMonitor(**kwargs)
    else:
        return PerformanceMonitor(**kwargs) 