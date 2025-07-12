#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket集成模块
为NewsLook系统提供实时状态推送、日志流和双向通信功能
"""

import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque

try:
    from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False

from backend.newslook.utils.logger import get_logger
from backend.newslook.utils.database import NewsDatabase

logger = get_logger(__name__)

class WebSocketManager:
    """WebSocket管理器"""
    
    def __init__(self, app=None):
        self.app = app
        self.socketio = None
        self.clients = {}  # 客户端信息
        self.rooms = defaultdict(set)  # 房间管理
        self.message_history = deque(maxlen=100)  # 消息历史
        self.heartbeat_interval = 30  # 心跳间隔（秒）
        self.heartbeat_thread = None
        self.is_running = False
        
        # 状态缓存
        self.crawler_status_cache = {}
        self.system_status_cache = {}
        self.last_status_update = 0
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化Flask应用"""
        if not SOCKETIO_AVAILABLE:
            logger.warning("Flask-SocketIO不可用，WebSocket功能将被禁用")
            return
        
        self.app = app
        self.socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            async_mode='threading',
            ping_timeout=60,
            ping_interval=25,
            logger=False,
            engineio_logger=False
        )
        
        self._register_events()
        self._start_heartbeat_thread()
        
        logger.info("WebSocket集成初始化完成")
    
    def _register_events(self):
        """注册WebSocket事件"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """客户端连接处理"""
            client_id = self._get_client_id()
            self.clients[client_id] = {
                'connected_at': datetime.now(),
                'last_ping': time.time(),
                'rooms': set(),
                'user_agent': self._get_user_agent()
            }
            
            logger.info(f"客户端连接: {client_id}")
            
            # 发送欢迎消息
            emit('connected', {
                'client_id': client_id,
                'timestamp': datetime.now().isoformat(),
                'server_time': time.time(),
                'available_rooms': list(self.rooms.keys())
            })
            
            # 发送当前状态
            self._send_current_status(client_id)
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """客户端断开处理"""
            client_id = self._get_client_id()
            
            # 从所有房间移除
            if client_id in self.clients:
                for room in self.clients[client_id]['rooms']:
                    self.rooms[room].discard(client_id)
                del self.clients[client_id]
            
            logger.info(f"客户端断开: {client_id}")
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            """加入房间"""
            room_name = data.get('room')
            if not room_name:
                emit('error', {'message': '房间名称不能为空'})
                return
            
            client_id = self._get_client_id()
            
            join_room(room_name)
            self.rooms[room_name].add(client_id)
            
            if client_id in self.clients:
                self.clients[client_id]['rooms'].add(room_name)
            
            emit('room_joined', {
                'room': room_name,
                'timestamp': datetime.now().isoformat(),
                'member_count': len(self.rooms[room_name])
            })
            
            logger.info(f"客户端 {client_id} 加入房间: {room_name}")
        
        @self.socketio.on('leave_room')
        def handle_leave_room(data):
            """离开房间"""
            room_name = data.get('room')
            if not room_name:
                return
            
            client_id = self._get_client_id()
            
            leave_room(room_name)
            self.rooms[room_name].discard(client_id)
            
            if client_id in self.clients:
                self.clients[client_id]['rooms'].discard(room_name)
            
            emit('room_left', {
                'room': room_name,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"客户端 {client_id} 离开房间: {room_name}")
        
        @self.socketio.on('ping')
        def handle_ping(data):
            """处理ping消息"""
            client_id = self._get_client_id()
            
            if client_id in self.clients:
                self.clients[client_id]['last_ping'] = time.time()
            
            emit('pong', {
                'timestamp': datetime.now().isoformat(),
                'server_time': time.time()
            })
        
        @self.socketio.on('get_crawler_status')
        def handle_get_crawler_status():
            """获取爬虫状态"""
            try:
                status = self._get_crawler_status()
                emit('crawler_status', status)
            except Exception as e:
                logger.error(f"获取爬虫状态失败: {e}")
                emit('error', {'message': '获取爬虫状态失败'})
        
        @self.socketio.on('get_system_status')
        def handle_get_system_status():
            """获取系统状态"""
            try:
                status = self._get_system_status()
                emit('system_status', status)
            except Exception as e:
                logger.error(f"获取系统状态失败: {e}")
                emit('error', {'message': '获取系统状态失败'})
    
    def _get_client_id(self):
        """获取客户端ID"""
        from flask import request
        return request.sid
    
    def _get_user_agent(self):
        """获取用户代理"""
        from flask import request
        return request.headers.get('User-Agent', 'Unknown')
    
    def _start_heartbeat_thread(self):
        """启动心跳线程"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return
        
        self.is_running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        
        logger.info("心跳线程已启动")
    
    def _heartbeat_loop(self):
        """心跳循环"""
        while self.is_running:
            try:
                current_time = time.time()
                
                # 检查离线客户端
                offline_clients = []
                for client_id, client_info in self.clients.items():
                    if current_time - client_info['last_ping'] > self.heartbeat_interval * 2:
                        offline_clients.append(client_id)
                
                # 移除离线客户端
                for client_id in offline_clients:
                    self._remove_client(client_id)
                
                # 发送心跳
                if self.socketio:
                    self.socketio.emit('heartbeat', {
                        'timestamp': datetime.now().isoformat(),
                        'server_time': current_time,
                        'active_clients': len(self.clients)
                    })
                
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"心跳循环错误: {e}")
                time.sleep(5)
    
    def _remove_client(self, client_id):
        """移除客户端"""
        if client_id in self.clients:
            # 从所有房间移除
            for room in self.clients[client_id]['rooms']:
                self.rooms[room].discard(client_id)
            del self.clients[client_id]
            
            logger.info(f"移除离线客户端: {client_id}")
    
    def _send_current_status(self, client_id):
        """发送当前状态给指定客户端"""
        try:
            crawler_status = self._get_crawler_status()
            system_status = self._get_system_status()
            
            if self.socketio:
                self.socketio.emit('current_status', {
                    'crawler_status': crawler_status,
                    'system_status': system_status,
                    'timestamp': datetime.now().isoformat()
                }, room=client_id)
                
        except Exception as e:
            logger.error(f"发送当前状态失败: {e}")
    
    def _get_crawler_status(self):
        """获取爬虫状态"""
        try:
            # 如果有缓存且不超过30秒，使用缓存
            current_time = time.time()
            if (self.crawler_status_cache and 
                current_time - self.last_status_update < 30):
                return self.crawler_status_cache
            
            # 从爬虫管理器获取状态
            if hasattr(self.app, 'crawler_manager') and self.app.crawler_manager:
                status = self.app.crawler_manager.get_status()
            else:
                status = {'error': '爬虫管理器不可用'}
            
            self.crawler_status_cache = status
            self.last_status_update = current_time
            return status
            
        except Exception as e:
            logger.error(f"获取爬虫状态失败: {e}")
            return {'error': str(e)}
    
    def _get_system_status(self):
        """获取系统状态"""
        try:
            import psutil
            
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'uptime': time.time() - psutil.boot_time(),
                'active_connections': len(self.clients),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {'error': str(e)}
    
    def broadcast_crawler_status(self, crawler_name, status, message=None):
        """广播爬虫状态变化"""
        if not self.socketio:
            return
        
        data = {
            'crawler_name': crawler_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        # 更新缓存
        if 'crawlers' not in self.crawler_status_cache:
            self.crawler_status_cache['crawlers'] = {}
        self.crawler_status_cache['crawlers'][crawler_name] = data
        
        # 广播状态变化
        self.socketio.emit('crawler_status_changed', data)
        
        # 发送到爬虫状态房间
        self.socketio.emit('crawler_update', data, room='crawler_status')
        
        logger.info(f"广播爬虫状态变化: {crawler_name} -> {status}")
    
    def broadcast_log_message(self, level, message, source=None):
        """广播日志消息"""
        if not self.socketio:
            return
        
        data = {
            'level': level,
            'message': message,
            'source': source or 'system',
            'timestamp': datetime.now().isoformat()
        }
        
        # 添加到历史记录
        self.message_history.append(data)
        
        # 广播到日志房间
        self.socketio.emit('log_message', data, room='logs')
        
        # 如果是错误级别，也广播到主房间
        if level in ['ERROR', 'CRITICAL']:
            self.socketio.emit('error_log', data)
    
    def broadcast_system_alert(self, alert_type, message, severity='warning'):
        """广播系统告警"""
        if not self.socketio:
            return
        
        data = {
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        }
        
        self.socketio.emit('system_alert', data)
        logger.warning(f"系统告警: {alert_type} - {message}")
    
    def get_stats(self):
        """获取WebSocket统计信息"""
        return {
            'active_clients': len(self.clients),
            'rooms': {room: len(members) for room, members in self.rooms.items()},
            'message_history_count': len(self.message_history),
            'uptime': time.time() - (self.clients.get(min(self.clients.keys(), default=''), {}).get('connected_at', datetime.now())).timestamp() if self.clients else 0
        }
    
    def shutdown(self):
        """关闭WebSocket管理器"""
        self.is_running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        
        logger.info("WebSocket管理器已关闭")

# 全局实例
_websocket_manager = None

def get_websocket_manager():
    """获取WebSocket管理器实例"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager

def init_websocket(app):
    """初始化WebSocket支持"""
    if not SOCKETIO_AVAILABLE:
        logger.warning("Flask-SocketIO不可用，跳过WebSocket初始化")
        return None
    
    ws_manager = get_websocket_manager()
    ws_manager.init_app(app)
    
    # 将WebSocket管理器添加到应用上下文
    app.websocket_manager = ws_manager
    
    return ws_manager.socketio 