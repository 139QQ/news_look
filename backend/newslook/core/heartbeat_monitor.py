#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心跳检测监控器 - 第二优先级指令实现
实现 while active: ping_control_channel() 机制
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
import json
import sqlite3
from pathlib import Path

from backend.newslook.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class HeartbeatStatus:
    """心跳状态数据类"""
    crawler_id: str
    last_heartbeat: datetime
    status: str  # 'healthy', 'warning', 'critical', 'dead'
    response_time_ms: float = 0.0
    consecutive_failures: int = 0
    total_heartbeats: int = 0
    uptime_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class HeartbeatMonitor:
    """
    心跳检测监控器
    
    功能特性：
    1. 实时心跳检测
    2. 状态持久化存储
    3. 异常告警机制
    4. 性能指标统计
    """
    
    def __init__(self, check_interval: int = 30, timeout_threshold: int = 120):
        """
        初始化心跳监控器
        
        Args:
            check_interval: 检查间隔（秒）
            timeout_threshold: 超时阈值（秒）
        """
        self.check_interval = check_interval
        self.timeout_threshold = timeout_threshold
        self.is_running = False
        self.monitor_thread = None
        
        # 心跳状态存储
        self.heartbeats: Dict[str, HeartbeatStatus] = {}
        self.alert_callbacks: List[Callable] = []
        
        # 持久化存储
        self.db_path = Path("data/heartbeat.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        logger.info(f"心跳监控器初始化完成 - 检查间隔: {check_interval}s, 超时阈值: {timeout_threshold}s")
    
    def _init_database(self):
        """初始化心跳数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS heartbeats (
                        crawler_id TEXT PRIMARY KEY,
                        last_heartbeat TEXT NOT NULL,
                        status TEXT NOT NULL,
                        response_time_ms REAL DEFAULT 0.0,
                        consecutive_failures INTEGER DEFAULT 0,
                        total_heartbeats INTEGER DEFAULT 0,
                        uptime_seconds REAL DEFAULT 0.0,
                        metadata TEXT DEFAULT '{}',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS heartbeat_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        crawler_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        status TEXT NOT NULL,
                        response_time_ms REAL DEFAULT 0.0,
                        metadata TEXT DEFAULT '{}'
                    )
                """)
                
                conn.commit()
                logger.info("心跳数据库初始化完成")
                
        except Exception as e:
            logger.error(f"初始化心跳数据库失败: {str(e)}")
    
    def start(self):
        """启动心跳监控"""
        if self.is_running:
            logger.warning("心跳监控器已经在运行")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("心跳监控器已启动")
    
    def stop(self):
        """停止心跳监控"""
        if not self.is_running:
            logger.warning("心跳监控器已经停止")
            return
        
        self.is_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        logger.info("心跳监控器已停止")
    
    def register_crawler(self, crawler_id: str, metadata: Dict[str, Any] = None):
        """
        注册爬虫到心跳监控
        
        Args:
            crawler_id: 爬虫ID
            metadata: 元数据
        """
        if metadata is None:
            metadata = {}
        
        status = HeartbeatStatus(
            crawler_id=crawler_id,
            last_heartbeat=datetime.now(),
            status='healthy',
            metadata=metadata
        )
        
        self.heartbeats[crawler_id] = status
        self._persist_heartbeat(status)
        
        logger.info(f"爬虫 {crawler_id} 已注册到心跳监控")
    
    def ping_control_channel(self, crawler_id: str, response_time_ms: float = None):
        """
        心跳检测核心方法 - 实现 while active: ping_control_channel()
        
        Args:
            crawler_id: 爬虫ID
            response_time_ms: 响应时间（毫秒）
        """
        if crawler_id not in self.heartbeats:
            logger.warning(f"收到未注册爬虫的心跳: {crawler_id}")
            self.register_crawler(crawler_id)
        
        status = self.heartbeats[crawler_id]
        current_time = datetime.now()
        
        # 更新心跳信息
        status.last_heartbeat = current_time
        status.total_heartbeats += 1
        status.consecutive_failures = 0  # 重置失败计数
        
        # 更新响应时间
        if response_time_ms is not None:
            status.response_time_ms = response_time_ms
        
        # 计算运行时间
        if hasattr(status, 'start_time'):
            status.uptime_seconds = (current_time - status.start_time).total_seconds()
        else:
            status.start_time = current_time
            status.uptime_seconds = 0
        
        # 确定状态
        if response_time_ms and response_time_ms > 5000:  # 响应时间超过5秒
            status.status = 'warning'
        else:
            status.status = 'healthy'
        
        # 持久化保存
        self._persist_heartbeat(status)
        self._save_history(status)
        
        logger.debug(f"心跳更新: {crawler_id} - 状态: {status.status}, 响应时间: {response_time_ms}ms")
    
    def _monitor_loop(self):
        """心跳监控主循环"""
        logger.info("心跳监控循环启动")
        
        while self.is_running:
            try:
                self._check_all_heartbeats()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"心跳监控循环出错: {str(e)}")
                time.sleep(self.check_interval)
        
        logger.info("心跳监控循环结束")
    
    def _check_all_heartbeats(self):
        """检查所有爬虫心跳状态"""
        current_time = datetime.now()
        
        for crawler_id, status in self.heartbeats.items():
            time_since_last = (current_time - status.last_heartbeat).total_seconds()
            
            # 判断状态
            if time_since_last > self.timeout_threshold * 2:  # 2倍超时 = 死亡
                new_status = 'dead'
                status.consecutive_failures += 1
            elif time_since_last > self.timeout_threshold:  # 1倍超时 = 危险
                new_status = 'critical'
                status.consecutive_failures += 1
            elif time_since_last > self.timeout_threshold * 0.5:  # 0.5倍超时 = 警告
                new_status = 'warning'
            else:
                new_status = 'healthy'
                status.consecutive_failures = 0
            
            # 状态变化时触发告警
            if status.status != new_status:
                old_status = status.status
                status.status = new_status
                self._trigger_alert(crawler_id, old_status, new_status, time_since_last)
                
                # 持久化保存状态变化
                self._persist_heartbeat(status)
    
    def _trigger_alert(self, crawler_id: str, old_status: str, new_status: str, time_since_last: float):
        """触发状态变化告警"""
        alert_message = f"爬虫 {crawler_id} 状态变化: {old_status} → {new_status} (无心跳时间: {time_since_last:.1f}s)"
        
        # 记录日志
        if new_status in ['critical', 'dead']:
            logger.error(alert_message)
        elif new_status == 'warning':
            logger.warning(alert_message)
        else:
            logger.info(alert_message)
        
        # 调用告警回调
        for callback in self.alert_callbacks:
            try:
                callback(crawler_id, old_status, new_status, time_since_last)
            except Exception as e:
                logger.error(f"告警回调执行失败: {str(e)}")
    
    def _persist_heartbeat(self, status: HeartbeatStatus):
        """持久化心跳状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO heartbeats 
                    (crawler_id, last_heartbeat, status, response_time_ms, consecutive_failures, 
                     total_heartbeats, uptime_seconds, metadata, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    status.crawler_id,
                    status.last_heartbeat.isoformat(),
                    status.status,
                    status.response_time_ms,
                    status.consecutive_failures,
                    status.total_heartbeats,
                    status.uptime_seconds,
                    json.dumps(status.metadata),
                    datetime.now().isoformat()
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"持久化心跳状态失败: {str(e)}")
    
    def _save_history(self, status: HeartbeatStatus):
        """保存心跳历史记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO heartbeat_history 
                    (crawler_id, timestamp, status, response_time_ms, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    status.crawler_id,
                    datetime.now().isoformat(),
                    status.status,
                    status.response_time_ms,
                    json.dumps(status.metadata)
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"保存心跳历史失败: {str(e)}")
    
    def get_status(self, crawler_id: str = None) -> Dict[str, Any]:
        """
        获取心跳状态
        
        Args:
            crawler_id: 指定爬虫ID，None表示获取所有
            
        Returns:
            Dict: 心跳状态信息
        """
        if crawler_id:
            if crawler_id in self.heartbeats:
                status = self.heartbeats[crawler_id]
                return {
                    'crawler_id': status.crawler_id,
                    'last_heartbeat': status.last_heartbeat.isoformat(),
                    'status': status.status,
                    'response_time_ms': status.response_time_ms,
                    'consecutive_failures': status.consecutive_failures,
                    'total_heartbeats': status.total_heartbeats,
                    'uptime_seconds': status.uptime_seconds,
                    'metadata': status.metadata
                }
            else:
                return {'error': f'爬虫 {crawler_id} 未注册'}
        else:
            # 返回所有爬虫状态
            all_status = {}
            for cid, status in self.heartbeats.items():
                all_status[cid] = {
                    'crawler_id': status.crawler_id,
                    'last_heartbeat': status.last_heartbeat.isoformat(),
                    'status': status.status,
                    'response_time_ms': status.response_time_ms,
                    'consecutive_failures': status.consecutive_failures,
                    'total_heartbeats': status.total_heartbeats,
                    'uptime_seconds': status.uptime_seconds,
                    'metadata': status.metadata
                }
            
            return {
                'heartbeats': all_status,
                'summary': {
                    'total': len(all_status),
                    'healthy': len([s for s in all_status.values() if s['status'] == 'healthy']),
                    'warning': len([s for s in all_status.values() if s['status'] == 'warning']),
                    'critical': len([s for s in all_status.values() if s['status'] == 'critical']),
                    'dead': len([s for s in all_status.values() if s['status'] == 'dead'])
                }
            }
    
    def add_alert_callback(self, callback: Callable):
        """添加告警回调函数"""
        self.alert_callbacks.append(callback)
        logger.info("添加告警回调函数成功")
    
    def load_persisted_data(self):
        """从数据库加载持久化数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM heartbeats")
                rows = cursor.fetchall()
                
                for row in rows:
                    (crawler_id, last_heartbeat_str, status, response_time_ms, 
                     consecutive_failures, total_heartbeats, uptime_seconds, 
                     metadata_str, created_at, updated_at) = row
                    
                    # 重构 HeartbeatStatus 对象
                    self.heartbeats[crawler_id] = HeartbeatStatus(
                        crawler_id=crawler_id,
                        last_heartbeat=datetime.fromisoformat(last_heartbeat_str),
                        status=status,
                        response_time_ms=response_time_ms,
                        consecutive_failures=consecutive_failures,
                        total_heartbeats=total_heartbeats,
                        uptime_seconds=uptime_seconds,
                        metadata=json.loads(metadata_str) if metadata_str else {}
                    )
                
                logger.info(f"从数据库加载了 {len(rows)} 个爬虫的心跳数据")
                
        except Exception as e:
            logger.error(f"加载持久化心跳数据失败: {str(e)}")

# 全局心跳监控器实例
_heartbeat_monitor: Optional[HeartbeatMonitor] = None

def get_heartbeat_monitor() -> HeartbeatMonitor:
    """获取全局心跳监控器实例"""
    global _heartbeat_monitor
    if _heartbeat_monitor is None:
        _heartbeat_monitor = HeartbeatMonitor()
        _heartbeat_monitor.load_persisted_data()
    return _heartbeat_monitor

def ping_crawler_heartbeat(crawler_id: str, response_time_ms: float = None):
    """便捷的心跳检测函数"""
    monitor = get_heartbeat_monitor()
    monitor.ping_control_channel(crawler_id, response_time_ms) 