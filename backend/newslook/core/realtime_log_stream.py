#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时日志流系统 - 第二优先级指令实现
WebSocket实时推送日志功能
"""

import asyncio
import threading
import time
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
import queue
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
from backend.newslook.utils.logger import get_logger

logger = get_logger(__name__)

class LogFileWatcher(FileSystemEventHandler):
    """日志文件监视器"""
    
    def __init__(self, log_stream_manager):
        self.log_stream_manager = log_stream_manager
        self.file_positions = {}  # 记录文件读取位置
        
    def on_modified(self, event):
        """文件修改时触发"""
        if event.is_directory:
            return
        
        if event.src_path.endswith('.log'):
            self._read_new_lines(event.src_path)
    
    def _read_new_lines(self, file_path):
        """读取文件新增行"""
        try:
            # 获取当前文件大小
            current_size = os.path.getsize(file_path)
            last_position = self.file_positions.get(file_path, 0)
            
            if current_size > last_position:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                    self.file_positions[file_path] = f.tell()
                    
                    # 处理新行
                    for line in new_lines:
                        line = line.strip()
                        if line:
                            self.log_stream_manager.broadcast_log_line(line, file_path)
                            
        except Exception as e:
            logger.error(f"读取日志文件失败 {file_path}: {str(e)}")

class RealTimeLogStream:
    """
    实时日志流管理器
    
    功能特性：
    1. WebSocket实时推送日志
    2. 日志文件监控
    3. 多房间支持（按爬虫分类）
    4. 日志过滤和格式化
    5. 历史日志回放
    """
    
    def __init__(self, app: Flask = None, log_dir: str = "logs"):
        """
        初始化实时日志流
        
        Args:
            app: Flask应用实例
            log_dir: 日志目录路径
        """
        self.app = app
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # WebSocket相关
        self.socketio = None
        self.connected_clients: Set[str] = set()
        self.room_subscribers: Dict[str, Set[str]] = {}
        
        # 日志监控相关
        self.observer = Observer()
        self.file_watcher = LogFileWatcher(self)
        self.is_watching = False
        
        # 日志缓存和过滤
        self.log_buffer: queue.Queue = queue.Queue(maxsize=1000)
        self.log_filters: Dict[str, Any] = {}
        
        # 性能统计
        self.stats = {
            'total_logs_sent': 0,
            'active_connections': 0,
            'start_time': datetime.now(),
            'bytes_transmitted': 0
        }
        
        if app:
            self.init_app(app)
        
        logger.info(f"实时日志流初始化完成 - 监控目录: {self.log_dir}")
    
    def init_app(self, app: Flask):
        """初始化Flask应用"""
        self.app = app
        self.socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
        
        # 注册WebSocket事件处理器
        self._register_socketio_events()
        
        # 启动日志文件监控
        self.start_watching()
        
        logger.info("实时日志流WebSocket服务已启动")
    
    def _register_socketio_events(self):
        """注册WebSocket事件处理器"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """客户端连接事件"""
            client_id = self._get_client_id()
            self.connected_clients.add(client_id)
            self.stats['active_connections'] = len(self.connected_clients)
            
            logger.info(f"客户端连接: {client_id}")
            
            # 发送连接确认和基本信息
            emit('log_stream_ready', {
                'status': 'connected',
                'client_id': client_id,
                'timestamp': datetime.now().isoformat(),
                'available_rooms': self._get_available_rooms(),
                'stats': self._get_public_stats()
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """客户端断开事件"""
            client_id = self._get_client_id()
            self.connected_clients.discard(client_id)
            self.stats['active_connections'] = len(self.connected_clients)
            
            # 从所有房间移除
            for room_name in self.room_subscribers:
                self.room_subscribers[room_name].discard(client_id)
            
            logger.info(f"客户端断开: {client_id}")
        
        @self.socketio.on('join_log_room')
        def handle_join_room(data):
            """加入日志房间"""
            room_name = data.get('room', 'general')
            client_id = self._get_client_id()
            
            # 加入房间
            join_room(room_name)
            
            if room_name not in self.room_subscribers:
                self.room_subscribers[room_name] = set()
            self.room_subscribers[room_name].add(client_id)
            
            logger.info(f"客户端 {client_id} 加入房间: {room_name}")
            
            # 发送历史日志
            self._send_recent_logs(room_name, client_id)
            
            emit('room_joined', {
                'room': room_name,
                'timestamp': datetime.now().isoformat(),
                'subscriber_count': len(self.room_subscribers[room_name])
            })
        
        @self.socketio.on('leave_log_room')
        def handle_leave_room(data):
            """离开日志房间"""
            room_name = data.get('room', 'general')
            client_id = self._get_client_id()
            
            # 离开房间
            leave_room(room_name)
            
            if room_name in self.room_subscribers:
                self.room_subscribers[room_name].discard(client_id)
            
            logger.info(f"客户端 {client_id} 离开房间: {room_name}")
            
            emit('room_left', {
                'room': room_name,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.socketio.on('set_log_filter')
        def handle_set_filter(data):
            """设置日志过滤器"""
            client_id = self._get_client_id()
            filter_config = data.get('filter', {})
            
            self.log_filters[client_id] = filter_config
            
            logger.info(f"客户端 {client_id} 设置日志过滤器: {filter_config}")
            
            emit('filter_set', {
                'filter': filter_config,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.socketio.on('get_log_history')
        def handle_get_history(data):
            """获取历史日志"""
            room_name = data.get('room', 'general')
            lines = data.get('lines', 100)
            
            history = self._get_log_history(room_name, lines)
            
            emit('log_history', {
                'room': room_name,
                'logs': history,
                'count': len(history),
                'timestamp': datetime.now().isoformat()
            })
    
    def _get_client_id(self):
        """获取客户端ID"""
        from flask import request
        return f"{request.sid}_{int(time.time())}"
    
    def start_watching(self):
        """开始监控日志文件"""
        if self.is_watching:
            logger.warning("日志文件监控已在运行")
            return
        
        # 监控日志目录
        self.observer.schedule(self.file_watcher, str(self.log_dir), recursive=True)
        self.observer.start()
        self.is_watching = True
        
        logger.info(f"开始监控日志目录: {self.log_dir}")
    
    def stop_watching(self):
        """停止监控日志文件"""
        if not self.is_watching:
            return
        
        self.observer.stop()
        self.observer.join()
        self.is_watching = False
        
        logger.info("停止监控日志文件")
    
    def broadcast_log_line(self, log_line: str, file_path: str = None):
        """
        广播日志行到WebSocket客户端
        
        Args:
            log_line: 日志内容
            file_path: 日志文件路径
        """
        if not self.socketio:
            return
        
        # 解析日志行
        parsed_log = self._parse_log_line(log_line, file_path)
        
        # 确定房间
        room_name = self._determine_room(parsed_log)
        
        # 广播到指定房间
        self.socketio.emit('new_log', parsed_log, room=room_name)
        
        # 更新统计
        self.stats['total_logs_sent'] += 1
        self.stats['bytes_transmitted'] += len(log_line.encode('utf-8'))
        
        # 缓存日志
        try:
            self.log_buffer.put_nowait({
                'log': parsed_log,
                'room': room_name,
                'timestamp': datetime.now().isoformat()
            })
        except queue.Full:
            # 缓存满时，移除最旧的日志
            try:
                self.log_buffer.get_nowait()
                self.log_buffer.put_nowait({
                    'log': parsed_log,
                    'room': room_name,
                    'timestamp': datetime.now().isoformat()
                })
            except queue.Empty:
                pass
    
    def _parse_log_line(self, log_line: str, file_path: str = None) -> Dict[str, Any]:
        """
        解析日志行
        
        Args:
            log_line: 日志内容
            file_path: 文件路径
            
        Returns:
            Dict: 解析后的日志数据
        """
        # 基本日志结构
        parsed = {
            'raw_message': log_line,
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'source': 'unknown',
            'module': 'unknown',
            'message': log_line
        }
        
        # 从文件路径推断来源
        if file_path:
            file_name = os.path.basename(file_path)
            parsed['source'] = file_name.replace('.log', '')
            
            # 从路径推断模块
            path_parts = Path(file_path).parts
            if len(path_parts) > 1:
                parsed['module'] = path_parts[-2]  # 倒数第二个路径部分
        
        # 尝试解析标准日志格式
        # 格式：2024-01-15 10:30:25,123 [INFO] [module] message
        try:
            import re
            pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-?\s*\[?(\w+)\]?\s*(?:\[([^\]]+)\])?\s*-?\s*(.*)'
            match = re.match(pattern, log_line)
            
            if match:
                timestamp_str, level, module, message = match.groups()
                parsed['timestamp'] = timestamp_str
                parsed['level'] = level.upper() if level else 'INFO'
                if module:
                    parsed['module'] = module
                parsed['message'] = message.strip() if message else log_line
            
        except Exception as e:
            logger.debug(f"日志解析失败: {str(e)}")
        
        return parsed
    
    def _determine_room(self, parsed_log: Dict[str, Any]) -> str:
        """确定日志应该发送到哪个房间"""
        source = parsed_log.get('source', 'unknown')
        module = parsed_log.get('module', 'unknown')
        
        # 爬虫日志
        if 'crawler' in source or 'crawler' in module:
            return f"crawler_{source}"
        
        # API日志
        if 'api' in source or 'api' in module:
            return 'api'
        
        # Web日志
        if 'web' in source or 'flask' in module:
            return 'web'
        
        # 系统日志
        if 'system' in source or 'monitor' in module:
            return 'system'
        
        # 默认房间
        return 'general'
    
    def _get_available_rooms(self) -> List[str]:
        """获取可用的房间列表"""
        rooms = ['general', 'api', 'web', 'system']
        
        # 添加爬虫房间
        for file_path in self.log_dir.glob("**/*.log"):
            if 'crawler' in file_path.name:
                crawler_name = file_path.stem.split('_')[0]
                room_name = f"crawler_{crawler_name}"
                if room_name not in rooms:
                    rooms.append(room_name)
        
        return sorted(rooms)
    
    def _send_recent_logs(self, room_name: str, client_id: str):
        """发送最近的日志给新加入的客户端"""
        try:
            recent_logs = []
            
            # 从缓存中获取该房间的最近日志
            temp_queue = queue.Queue()
            while not self.log_buffer.empty():
                try:
                    item = self.log_buffer.get_nowait()
                    temp_queue.put(item)
                    
                    if item['room'] == room_name:
                        recent_logs.append(item['log'])
                        
                except queue.Empty:
                    break
            
            # 恢复缓存
            while not temp_queue.empty():
                try:
                    self.log_buffer.put_nowait(temp_queue.get_nowait())
                except queue.Full:
                    break
            
            # 发送最近的日志（最多50条）
            if recent_logs:
                recent_logs = recent_logs[-50:]  # 最近50条
                self.socketio.emit('recent_logs', {
                    'room': room_name,
                    'logs': recent_logs,
                    'count': len(recent_logs)
                }, room=client_id)
                
        except Exception as e:
            logger.error(f"发送最近日志失败: {str(e)}")
    
    def _get_log_history(self, room_name: str, lines: int = 100) -> List[Dict[str, Any]]:
        """获取日志历史"""
        history = []
        
        try:
            # 根据房间名确定日志文件
            log_files = []
            
            if room_name.startswith('crawler_'):
                crawler_name = room_name.replace('crawler_', '')
                log_files = list(self.log_dir.glob(f"**/*{crawler_name}*.log"))
            elif room_name == 'api':
                log_files = list(self.log_dir.glob("**/api*.log"))
            elif room_name == 'web':
                log_files = list(self.log_dir.glob("**/web*.log"))
            else:
                log_files = list(self.log_dir.glob("**/*.log"))
            
            # 读取最新的日志文件
            for log_file in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        file_lines = f.readlines()
                        
                    # 处理最近的行
                    for line in file_lines[-lines:]:
                        line = line.strip()
                        if line:
                            parsed = self._parse_log_line(line, str(log_file))
                            history.append(parsed)
                            
                    if len(history) >= lines:
                        break
                        
                except Exception as e:
                    logger.error(f"读取日志文件失败 {log_file}: {str(e)}")
            
        except Exception as e:
            logger.error(f"获取日志历史失败: {str(e)}")
        
        return history[-lines:]  # 返回最近的N条
    
    def _get_public_stats(self) -> Dict[str, Any]:
        """获取公开统计信息"""
        uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return {
            'active_connections': self.stats['active_connections'],
            'total_logs_sent': self.stats['total_logs_sent'],
            'uptime_seconds': uptime,
            'mb_transmitted': round(self.stats['bytes_transmitted'] / 1024 / 1024, 2),
            'avg_logs_per_minute': round(self.stats['total_logs_sent'] / (uptime / 60), 2) if uptime > 0 else 0
        }
    
    def send_manual_log(self, message: str, level: str = 'INFO', source: str = 'system', room: str = 'general'):
        """
        手动发送日志消息
        
        Args:
            message: 日志消息
            level: 日志级别
            source: 日志来源
            room: 目标房间
        """
        if not self.socketio:
            return
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': level.upper(),
            'source': source,
            'module': source,
            'message': message,
            'raw_message': f"[{level.upper()}] {message}"
        }
        
        self.socketio.emit('new_log', log_data, room=room)
        logger.info(f"手动发送日志到房间 {room}: {message}")

# 全局实时日志流实例
_realtime_log_stream: Optional[RealTimeLogStream] = None

def get_realtime_log_stream() -> RealTimeLogStream:
    """获取全局实时日志流实例"""
    global _realtime_log_stream
    if _realtime_log_stream is None:
        _realtime_log_stream = RealTimeLogStream()
    return _realtime_log_stream

def init_realtime_logs(app: Flask, log_dir: str = "logs"):
    """初始化实时日志流"""
    global _realtime_log_stream
    _realtime_log_stream = RealTimeLogStream(app, log_dir)
    return _realtime_log_stream 