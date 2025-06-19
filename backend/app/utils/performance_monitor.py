#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能监控工具
收集和分析爬虫性能数据，提供实时监控和历史统计分析
"""

import os
import time
import json
import logging
import sqlite3
import threading
import psutil
import platform
from datetime import datetime, timedelta
from contextlib import contextmanager

# 获取日志记录器
logger = logging.getLogger("performance_monitor")

# 性能数据库路径
DEFAULT_PERF_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                 'data', 'performance.db')

# 全局统计数据，用于实时监控
GLOBAL_STATS = {
    'active_crawlers': {},  # 当前活动的爬虫
    'start_time': time.time(),  # 系统启动时间
    'last_reset': time.time(),  # 最后重置时间
    'total_requests': 0,  # 总请求数
    'total_news': 0,  # 总新闻数
    'request_success': 0,  # 成功请求数
    'request_failure': 0,  # 失败请求数
    'db_operations': 0,  # 数据库操作数
    'db_success': 0,  # 数据库操作成功数
    'db_failure': 0,  # 数据库操作失败数
    'peak_memory': 0,  # 峰值内存使用
    'peak_cpu': 0,  # 峰值CPU使用
}

# 统计数据锁
STATS_LOCK = threading.RLock()

class PerformanceMonitor:
    """性能监控类，用于收集和分析爬虫性能数据"""
    
    def __init__(self, db_path=None):
        """
        初始化性能监控器
        
        Args:
            db_path: 性能数据库路径，如果为None则使用默认路径
        """
        self.db_path = db_path or DEFAULT_PERF_DB_PATH
        self.init_db()
        
        # 系统信息
        self.system_info = {
            'os': platform.system(),
            'platform': platform.platform(),
            'cpu_count': psutil.cpu_count(logical=True),
            'physical_cpu': psutil.cpu_count(logical=False),
            'memory_total': psutil.virtual_memory().total,
            'python_version': platform.python_version(),
        }
        
        # 当前进程信息
        self.process = psutil.Process()
    
    def init_db(self):
        """初始化性能数据库"""
        # 确保数据库目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # 创建数据库表
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # 创建统计数据总表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                crawler_type TEXT,
                source TEXT,
                task_id TEXT,
                requests INTEGER,
                success INTEGER,
                failure INTEGER,
                avg_response_time REAL,
                news_count INTEGER,
                db_operations INTEGER,
                db_success INTEGER,
                db_failure INTEGER,
                memory_usage REAL,
                cpu_usage REAL,
                duration REAL,
                status TEXT,
                error_msg TEXT
            )
            ''')
            
            # 创建请求详情表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS request_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                url TEXT,
                method TEXT,
                status_code INTEGER,
                duration REAL,
                size INTEGER,
                timestamp TEXT,
                success INTEGER,
                error_msg TEXT
            )
            ''')
            
            # 创建资源使用表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS resource_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                task_id TEXT,
                crawler_type TEXT,
                cpu_percent REAL,
                memory_percent REAL,
                memory_used INTEGER,
                io_read_count INTEGER,
                io_write_count INTEGER,
                io_read_bytes INTEGER,
                io_write_bytes INTEGER,
                thread_count INTEGER
            )
            ''')
            
            conn.commit()
        finally:
            conn.close()
    
    @contextmanager
    def track_task(self, task_name, crawler_type=None, source=None):
        """
        追踪爬虫任务性能
        
        Args:
            task_name: 任务名称
            crawler_type: 爬虫类型
            source: 爬虫来源
            
        Yields:
            dict: 性能追踪字典
        """
        task_id = f"{task_name}_{int(time.time())}"
        
        # 初始化任务统计
        stats = {
            'task_id': task_id,
            'crawler_type': crawler_type,
            'source': source,
            'start_time': time.time(),
            'requests': 0,
            'success': 0,
            'failure': 0,
            'news_count': 0,
            'db_operations': 0,
            'db_success': 0,
            'db_failure': 0,
            'response_times': [],
            'status': 'running',
            'error_msg': None
        }
        
        # 添加到活动爬虫
        with STATS_LOCK:
            GLOBAL_STATS['active_crawlers'][task_id] = {
                'name': task_name,
                'type': crawler_type,
                'source': source,
                'start_time': stats['start_time'],
                'stats': stats
            }
        
        # 启动资源监控线程
        stop_monitor = threading.Event()
        monitor_thread = threading.Thread(
            target=self._monitor_resources,
            args=(task_id, crawler_type, stop_monitor),
            daemon=True
        )
        monitor_thread.start()
        
        try:
            yield stats
            stats['status'] = 'completed'
        except Exception as e:
            stats['status'] = 'failed'
            stats['error_msg'] = str(e)
            raise
        finally:
            # 计算统计信息
            stats['end_time'] = time.time()
            stats['duration'] = stats['end_time'] - stats['start_time']
            stats['avg_response_time'] = (
                sum(stats['response_times']) / len(stats['response_times']) 
                if stats['response_times'] else 0
            )
            
            # 停止资源监控
            stop_monitor.set()
            monitor_thread.join(timeout=1)
            
            # 保存性能数据
            self.save_performance_stats(stats)
            
            # 从活动爬虫中移除
            with STATS_LOCK:
                if task_id in GLOBAL_STATS['active_crawlers']:
                    del GLOBAL_STATS['active_crawlers'][task_id]
    
    def _monitor_resources(self, task_id, crawler_type, stop_event, interval=2):
        """
        监控资源使用情况
        
        Args:
            task_id: 任务ID
            crawler_type: 爬虫类型
            stop_event: 停止事件
            interval: 监控间隔（秒）
        """
        while not stop_event.is_set():
            try:
                # 获取进程信息
                cpu_percent = self.process.cpu_percent(interval=0.1)
                memory_info = self.process.memory_info()
                memory_percent = self.process.memory_percent()
                io_counters = self.process.io_counters()
                thread_count = len(self.process.threads())
                
                # 更新全局统计
                with STATS_LOCK:
                    GLOBAL_STATS['peak_memory'] = max(GLOBAL_STATS['peak_memory'], memory_percent)
                    GLOBAL_STATS['peak_cpu'] = max(GLOBAL_STATS['peak_cpu'], cpu_percent)
                
                # 保存资源使用情况
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                    INSERT INTO resource_usage (
                        timestamp, task_id, crawler_type, cpu_percent, memory_percent,
                        memory_used, io_read_count, io_write_count, io_read_bytes,
                        io_write_bytes, thread_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        task_id,
                        crawler_type,
                        cpu_percent,
                        memory_percent,
                        memory_info.rss,
                        io_counters.read_count,
                        io_counters.write_count,
                        io_counters.read_bytes,
                        io_counters.write_bytes,
                        thread_count
                    ))
                    conn.commit()
            
            except Exception as e:
                logger.error(f"监控资源使用出错: {str(e)}")
            
            # 等待下一个间隔或停止信号
            stop_event.wait(interval)
    
    def track_request(self, task_id, url, method='GET', status_code=None, duration=None, 
                     size=None, success=True, error_msg=None):
        """
        记录请求详情
        
        Args:
            task_id: 任务ID
            url: 请求URL
            method: 请求方法
            status_code: 状态码
            duration: 请求耗时
            size: 响应大小
            success: 是否成功
            error_msg: 错误信息
        """
        try:
            # 更新全局统计
            with STATS_LOCK:
                GLOBAL_STATS['total_requests'] += 1
                if success:
                    GLOBAL_STATS['request_success'] += 1
                else:
                    GLOBAL_STATS['request_failure'] += 1
            
            # 更新任务统计
            if task_id in GLOBAL_STATS['active_crawlers']:
                stats = GLOBAL_STATS['active_crawlers'][task_id]['stats']
                stats['requests'] += 1
                if success:
                    stats['success'] += 1
                    if duration:
                        stats['response_times'].append(duration)
                else:
                    stats['failure'] += 1
            
            # 保存请求详情
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO request_details (
                    task_id, url, method, status_code, duration, 
                    size, timestamp, success, error_msg
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_id, 
                    url, 
                    method, 
                    status_code, 
                    duration, 
                    size, 
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    1 if success else 0,
                    error_msg
                ))
                conn.commit()
        
        except Exception as e:
            logger.error(f"记录请求详情出错: {str(e)}")
    
    def track_db_operation(self, task_id, operation_type, success=True, error_msg=None):
        """
        记录数据库操作
        
        Args:
            task_id: 任务ID
            operation_type: 操作类型
            success: 是否成功
            error_msg: 错误信息
        """
        try:
            # 更新全局统计
            with STATS_LOCK:
                GLOBAL_STATS['db_operations'] += 1
                if success:
                    GLOBAL_STATS['db_success'] += 1
                else:
                    GLOBAL_STATS['db_failure'] += 1
            
            # 更新任务统计
            if task_id in GLOBAL_STATS['active_crawlers']:
                stats = GLOBAL_STATS['active_crawlers'][task_id]['stats']
                stats['db_operations'] += 1
                if success:
                    stats['db_success'] += 1
                else:
                    stats['db_failure'] += 1
        
        except Exception as e:
            logger.error(f"记录数据库操作出错: {str(e)}")
    
    def track_news_saved(self, task_id, count=1):
        """
        记录保存的新闻数量
        
        Args:
            task_id: 任务ID
            count: 新闻数量
        """
        try:
            # 更新全局统计
            with STATS_LOCK:
                GLOBAL_STATS['total_news'] += count
            
            # 更新任务统计
            if task_id in GLOBAL_STATS['active_crawlers']:
                stats = GLOBAL_STATS['active_crawlers'][task_id]['stats']
                stats['news_count'] += count
        
        except Exception as e:
            logger.error(f"记录保存的新闻数量出错: {str(e)}")
    
    def save_performance_stats(self, stats):
        """
        保存性能统计数据
        
        Args:
            stats: 性能统计字典
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO performance_stats (
                    timestamp, crawler_type, source, task_id, requests, 
                    success, failure, avg_response_time, news_count, 
                    db_operations, db_success, db_failure, memory_usage, 
                    cpu_usage, duration, status, error_msg
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    stats.get('crawler_type'),
                    stats.get('source'),
                    stats.get('task_id'),
                    stats.get('requests', 0),
                    stats.get('success', 0),
                    stats.get('failure', 0),
                    stats.get('avg_response_time', 0),
                    stats.get('news_count', 0),
                    stats.get('db_operations', 0),
                    stats.get('db_success', 0),
                    stats.get('db_failure', 0),
                    GLOBAL_STATS.get('peak_memory', 0),
                    GLOBAL_STATS.get('peak_cpu', 0),
                    stats.get('duration', 0),
                    stats.get('status', 'unknown'),
                    stats.get('error_msg')
                ))
                conn.commit()
        
        except Exception as e:
            logger.error(f"保存性能统计数据出错: {str(e)}")
    
    def get_active_crawlers(self):
        """获取当前活动的爬虫"""
        with STATS_LOCK:
            return {k: v.copy() for k, v in GLOBAL_STATS['active_crawlers'].items()}
    
    def get_global_stats(self):
        """获取全局统计数据"""
        with STATS_LOCK:
            stats = GLOBAL_STATS.copy()
            stats['uptime'] = time.time() - stats['start_time']
            stats['active_count'] = len(stats['active_crawlers'])
            return stats
    
    def get_performance_history(self, days=7, crawler_type=None, source=None):
        """
        获取历史性能数据
        
        Args:
            days: 天数
            crawler_type: 爬虫类型
            source: 来源
            
        Returns:
            list: 性能数据列表
        """
        try:
            # 构建查询条件
            query = '''
            SELECT * FROM performance_stats 
            WHERE timestamp >= ?
            '''
            params = [(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')]
            
            if crawler_type:
                query += ' AND crawler_type = ?'
                params.append(crawler_type)
            
            if source:
                query += ' AND source = ?'
                params.append(source)
            
            query += ' ORDER BY timestamp DESC'
            
            # 执行查询
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        
        except Exception as e:
            logger.error(f"获取历史性能数据出错: {str(e)}")
            return []
    
    def get_performance_summary(self, days=7):
        """
        获取性能摘要
        
        Args:
            days: 天数
            
        Returns:
            dict: 性能摘要
        """
        try:
            # 计算开始日期
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            
            # 总体统计
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 总任务数
                cursor.execute('SELECT COUNT(*) as count FROM performance_stats WHERE timestamp >= ?', (start_date,))
                total_tasks = cursor.fetchone()['count']
                
                # 总请求数
                cursor.execute('SELECT SUM(requests) as total, SUM(success) as success, SUM(failure) as failure FROM performance_stats WHERE timestamp >= ?', (start_date,))
                row = cursor.fetchone()
                total_requests = row['total'] or 0
                success_requests = row['success'] or 0
                failure_requests = row['failure'] or 0
                
                # 总新闻数
                cursor.execute('SELECT SUM(news_count) as count FROM performance_stats WHERE timestamp >= ?', (start_date,))
                total_news = cursor.fetchone()['count'] or 0
                
                # 平均响应时间
                cursor.execute('SELECT AVG(avg_response_time) as avg_time FROM performance_stats WHERE timestamp >= ? AND avg_response_time > 0', (start_date,))
                avg_response_time = cursor.fetchone()['avg_time'] or 0
                
                # 成功率
                success_rate = success_requests / total_requests * 100 if total_requests > 0 else 0
                
                # 按爬虫类型分组
                cursor.execute('''
                SELECT crawler_type, COUNT(*) as task_count, SUM(news_count) as news_count, AVG(duration) as avg_duration 
                FROM performance_stats 
                WHERE timestamp >= ? 
                GROUP BY crawler_type
                ''', (start_date,))
                crawler_stats = [dict(row) for row in cursor.fetchall()]
                
                # 按来源分组
                cursor.execute('''
                SELECT source, COUNT(*) as task_count, SUM(news_count) as news_count, AVG(duration) as avg_duration 
                FROM performance_stats 
                WHERE timestamp >= ? 
                GROUP BY source
                ''', (start_date,))
                source_stats = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'period_days': days,
                    'total_tasks': total_tasks,
                    'total_requests': total_requests,
                    'success_requests': success_requests,
                    'failure_requests': failure_requests,
                    'success_rate': success_rate,
                    'total_news': total_news,
                    'avg_response_time': avg_response_time,
                    'crawler_stats': crawler_stats,
                    'source_stats': source_stats
                }
        
        except Exception as e:
            logger.error(f"获取性能摘要出错: {str(e)}")
            return {
                'period_days': days,
                'error': str(e)
            }
    
    def get_daily_stats(self, days=30):
        """
        获取每日统计数据
        
        Args:
            days: 天数
            
        Returns:
            list: 每日统计数据
        """
        try:
            # 计算开始日期
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # 查询每日统计
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT 
                    substr(timestamp, 1, 10) as date,
                    COUNT(*) as task_count,
                    SUM(requests) as total_requests,
                    SUM(success) as success_requests,
                    SUM(failure) as failure_requests,
                    SUM(news_count) as news_count,
                    AVG(avg_response_time) as avg_response_time,
                    AVG(duration) as avg_duration
                FROM performance_stats
                WHERE substr(timestamp, 1, 10) >= ?
                GROUP BY substr(timestamp, 1, 10)
                ORDER BY date
                ''', (start_date,))
                
                return [dict(row) for row in cursor.fetchall()]
        
        except Exception as e:
            logger.error(f"获取每日统计数据出错: {str(e)}")
            return []
    
    def reset_stats(self):
        """重置全局统计数据"""
        with STATS_LOCK:
            GLOBAL_STATS['last_reset'] = time.time()
            GLOBAL_STATS['total_requests'] = 0
            GLOBAL_STATS['total_news'] = 0
            GLOBAL_STATS['request_success'] = 0
            GLOBAL_STATS['request_failure'] = 0
            GLOBAL_STATS['db_operations'] = 0
            GLOBAL_STATS['db_success'] = 0
            GLOBAL_STATS['db_failure'] = 0
            GLOBAL_STATS['peak_memory'] = 0
            GLOBAL_STATS['peak_cpu'] = 0

# 创建全局性能监控实例
performance_monitor = PerformanceMonitor()

@contextmanager
def monitor_crawler(name, crawler_type=None, source=None):
    """
    爬虫性能监控上下文管理器
    
    Args:
        name: 爬虫名称
        crawler_type: 爬虫类型
        source: 爬虫来源
        
    Yields:
        dict: 性能追踪字典
    """
    with performance_monitor.track_task(name, crawler_type, source) as stats:
        yield stats

def track_request(task_id, url, **kwargs):
    """记录请求"""
    performance_monitor.track_request(task_id, url, **kwargs)

def track_db_operation(task_id, operation_type, **kwargs):
    """记录数据库操作"""
    performance_monitor.track_db_operation(task_id, operation_type, **kwargs)

def track_news_saved(task_id, count=1):
    """记录保存的新闻"""
    performance_monitor.track_news_saved(task_id, count)

def get_active_crawlers():
    """获取活动爬虫"""
    return performance_monitor.get_active_crawlers()

def get_global_stats():
    """获取全局统计"""
    return performance_monitor.get_global_stats()

def get_performance_summary(days=7):
    """获取性能摘要"""
    return performance_monitor.get_performance_summary(days)

def get_performance_history(days=7, **kwargs):
    """获取性能历史"""
    return performance_monitor.get_performance_history(days, **kwargs)

def get_daily_stats(days=30):
    """获取每日统计"""
    return performance_monitor.get_daily_stats(days)

def reset_stats():
    """重置统计"""
    performance_monitor.reset_stats() 