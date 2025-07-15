#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
技术架构和性能优化脚本
实现WebSocket、缓存机制、性能监控、错误处理等功能
"""

import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import sqlite3
import redis
import asyncio

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceArchitectureOptimizer:
    """性能架构优化器"""
    
    def __init__(self, project_root: str = None):
        """初始化性能架构优化器"""
        if project_root is None:
            project_root = Path(__file__).parent.parent
        
        self.project_root = Path(project_root)
        self.backend_dir = self.project_root / 'backend'
        self.db_dir = self.project_root / 'data' / 'db'
        
        # 优化报告
        self.report = {
            'start_time': datetime.now().isoformat(),
            'optimizations': [],
            'errors': []
        }
    
    def create_websocket_server(self):
        """创建WebSocket服务器"""
        logger.info("创建WebSocket服务器...")
        
        websocket_dir = self.backend_dir / 'newslook' / 'websocket'
        websocket_dir.mkdir(parents=True, exist_ok=True)
        
        websocket_server_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebSocket服务器
实现实时数据推送和双向通信
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Set, Dict, Any
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

class WebSocketServer:
    """WebSocket服务器"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """初始化WebSocket服务器"""
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.subscriptions: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        
        # 数据库路径
        project_root = Path(__file__).parent.parent.parent.parent
        self.db_path = project_root / 'data' / 'db' / 'finance_news.db'
        
        logger.info(f"WebSocket服务器初始化完成: {self.host}:{self.port}")
    
    async def register_client(self, websocket):
        """注册客户端"""
        self.clients.add(websocket)
        logger.info(f"客户端连接: {websocket.remote_address}")
        
        # 发送欢迎消息
        await self.send_message(websocket, {
            'type': 'welcome',
            'message': 'WebSocket连接成功',
            'timestamp': datetime.now().isoformat()
        })
    
    async def unregister_client(self, websocket):
        """注销客户端"""
        self.clients.discard(websocket)
        
        # 从所有订阅中移除
        for topic, subscribers in self.subscriptions.items():
            subscribers.discard(websocket)
        
        logger.info(f"客户端断开: {websocket.remote_address}")
    
    async def send_message(self, websocket, message: Dict[str, Any]):
        """发送消息给客户端"""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            logger.warning("客户端连接已关闭")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
    
    async def broadcast_message(self, message: Dict[str, Any], topic: str = None):
        """广播消息给所有客户端或特定主题订阅者"""
        if topic and topic in self.subscriptions:
            recipients = self.subscriptions[topic]
        else:
            recipients = self.clients
        
        if recipients:
            await asyncio.gather(
                *[self.send_message(client, message) for client in recipients.copy()],
                return_exceptions=True
            )
    
    async def handle_subscription(self, websocket, data: Dict[str, Any]):
        """处理订阅请求"""
        topic = data.get('topic')
        action = data.get('action')  # subscribe 或 unsubscribe
        
        if not topic or not action:
            await self.send_message(websocket, {
                'type': 'error',
                'message': '订阅参数错误',
                'timestamp': datetime.now().isoformat()
            })
            return
        
        if action == 'subscribe':
            if topic not in self.subscriptions:
                self.subscriptions[topic] = set()
            self.subscriptions[topic].add(websocket)
            
            await self.send_message(websocket, {
                'type': 'subscribed',
                'topic': topic,
                'message': f'成功订阅主题: {topic}',
                'timestamp': datetime.now().isoformat()
            })
            
        elif action == 'unsubscribe':
            if topic in self.subscriptions:
                self.subscriptions[topic].discard(websocket)
            
            await self.send_message(websocket, {
                'type': 'unsubscribed',
                'topic': topic,
                'message': f'成功取消订阅主题: {topic}',
                'timestamp': datetime.now().isoformat()
            })
    
    async def handle_news_request(self, websocket, data: Dict[str, Any]):
        """处理新闻数据请求"""
        try:
            limit = data.get('limit', 10)
            source = data.get('source')
            
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                
                sql = "SELECT * FROM news"
                params = []
                
                if source:
                    sql += " WHERE source = ?"
                    params.append(source)
                
                sql += " ORDER BY pub_time DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                
                news_list = [dict(row) for row in rows]
                
                await self.send_message(websocket, {
                    'type': 'news_data',
                    'data': news_list,
                    'count': len(news_list),
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"处理新闻请求失败: {e}")
            await self.send_message(websocket, {
                'type': 'error',
                'message': '获取新闻数据失败',
                'timestamp': datetime.now().isoformat()
            })
    
    async def handle_crawler_status(self, websocket, data: Dict[str, Any]):
        """处理爬虫状态请求"""
        try:
            # 模拟爬虫状态数据
            crawler_status = {
                'eastmoney': {'status': 'running', 'last_update': datetime.now().isoformat()},
                'sina': {'status': 'running', 'last_update': datetime.now().isoformat()},
                'netease': {'status': 'stopped', 'last_update': datetime.now().isoformat()},
                'ifeng': {'status': 'running', 'last_update': datetime.now().isoformat()},
                'tencent': {'status': 'running', 'last_update': datetime.now().isoformat()}
            }
            
            await self.send_message(websocket, {
                'type': 'crawler_status',
                'data': crawler_status,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"处理爬虫状态请求失败: {e}")
            await self.send_message(websocket, {
                'type': 'error',
                'message': '获取爬虫状态失败',
                'timestamp': datetime.now().isoformat()
            })
    
    async def handle_message(self, websocket, message: str):
        """处理客户端消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'subscription':
                await self.handle_subscription(websocket, data)
            elif message_type == 'news_request':
                await self.handle_news_request(websocket, data)
            elif message_type == 'crawler_status':
                await self.handle_crawler_status(websocket, data)
            elif message_type == 'ping':
                await self.send_message(websocket, {
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                })
            else:
                await self.send_message(websocket, {
                    'type': 'error',
                    'message': f'未知消息类型: {message_type}',
                    'timestamp': datetime.now().isoformat()
                })
                
        except json.JSONDecodeError:
            await self.send_message(websocket, {
                'type': 'error',
                'message': '消息格式错误',
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            await self.send_message(websocket, {
                'type': 'error',
                'message': '处理消息失败',
                'timestamp': datetime.now().isoformat()
            })
    
    async def client_handler(self, websocket, path):
        """客户端处理程序"""
        await self.register_client(websocket)
        
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("客户端连接关闭")
        except Exception as e:
            logger.error(f"客户端处理错误: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def start_server(self):
        """启动WebSocket服务器"""
        logger.info(f"启动WebSocket服务器: {self.host}:{self.port}")
        
        async with websockets.serve(self.client_handler, self.host, self.port):
            await asyncio.Future()  # run forever
    
    async def broadcast_news_update(self, news_data: Dict[str, Any]):
        """广播新闻更新"""
        await self.broadcast_message({
            'type': 'news_update',
            'data': news_data,
            'timestamp': datetime.now().isoformat()
        }, topic='news_updates')
    
    async def broadcast_crawler_update(self, crawler_data: Dict[str, Any]):
        """广播爬虫状态更新"""
        await self.broadcast_message({
            'type': 'crawler_update',
            'data': crawler_data,
            'timestamp': datetime.now().isoformat()
        }, topic='crawler_updates')

def main():
    """主函数"""
    server = WebSocketServer()
    
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("WebSocket服务器停止")
    except Exception as e:
        logger.error(f"WebSocket服务器错误: {e}")

if __name__ == "__main__":
    main()
'''
        
        websocket_server_file = websocket_dir / 'server.py'
        with open(websocket_server_file, 'w', encoding='utf-8') as f:
            f.write(websocket_server_code)
        
        # 创建WebSocket客户端工具
        websocket_client_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebSocket客户端工具
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketClient:
    """WebSocket客户端"""
    
    def __init__(self, uri: str = "ws://localhost:8765"):
        """初始化WebSocket客户端"""
        self.uri = uri
        self.websocket = None
    
    async def connect(self):
        """连接到WebSocket服务器"""
        try:
            self.websocket = await websockets.connect(self.uri)
            logger.info(f"连接到WebSocket服务器: {self.uri}")
            return True
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    async def send_message(self, message: dict):
        """发送消息"""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                return False
        return False
    
    async def receive_messages(self):
        """接收消息"""
        if self.websocket:
            try:
                async for message in self.websocket:
                    data = json.loads(message)
                    logger.info(f"收到消息: {data}")
                    yield data
            except Exception as e:
                logger.error(f"接收消息失败: {e}")
    
    async def subscribe(self, topic: str):
        """订阅主题"""
        message = {
            'type': 'subscription',
            'action': 'subscribe',
            'topic': topic
        }
        return await self.send_message(message)
    
    async def request_news(self, limit: int = 10, source: str = None):
        """请求新闻数据"""
        message = {
            'type': 'news_request',
            'limit': limit,
            'source': source
        }
        return await self.send_message(message)
    
    async def request_crawler_status(self):
        """请求爬虫状态"""
        message = {
            'type': 'crawler_status'
        }
        return await self.send_message(message)
    
    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket连接已关闭")

async def test_client():
    """测试客户端"""
    client = WebSocketClient()
    
    if await client.connect():
        # 订阅新闻更新
        await client.subscribe('news_updates')
        
        # 请求新闻数据
        await client.request_news(limit=5)
        
        # 请求爬虫状态
        await client.request_crawler_status()
        
        # 接收消息
        async for message in client.receive_messages():
            print(f"收到: {message}")
            
            # 只接收几条消息后退出
            if message.get('type') == 'news_data':
                break
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_client())
'''
        
        websocket_client_file = websocket_dir / 'client.py'
        with open(websocket_client_file, 'w', encoding='utf-8') as f:
            f.write(websocket_client_code)
        
        # 创建__init__.py文件
        init_file = websocket_dir / '__init__.py'
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('from .server import WebSocketServer\nfrom .client import WebSocketClient\n')
        
        logger.info(f"WebSocket服务器创建完成: {websocket_dir}")
        return websocket_dir
    
    def create_caching_system(self):
        """创建缓存系统"""
        logger.info("创建缓存系统...")
        
        cache_dir = self.backend_dir / 'newslook' / 'cache'
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        cache_manager_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
缓存管理器
提供Redis和内存缓存支持
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List
import hashlib
import pickle

logger = logging.getLogger(__name__)

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_type: str = 'memory', redis_config: Dict = None):
        """
        初始化缓存管理器
        
        Args:
            cache_type: 缓存类型 ('memory' 或 'redis')
            redis_config: Redis配置
        """
        self.cache_type = cache_type
        self.memory_cache = {}
        self.cache_timestamps = {}
        self.redis_client = None
        
        if cache_type == 'redis':
            self._init_redis(redis_config or {})
        
        logger.info(f"缓存管理器初始化完成: {cache_type}")
    
    def _init_redis(self, config: Dict):
        """初始化Redis连接"""
        try:
            import redis
            
            self.redis_client = redis.Redis(
                host=config.get('host', 'localhost'),
                port=config.get('port', 6379),
                db=config.get('db', 0),
                password=config.get('password'),
                decode_responses=True
            )
            
            # 测试连接
            self.redis_client.ping()
            logger.info("Redis连接成功")
            
        except ImportError:
            logger.warning("Redis模块未安装，使用内存缓存")
            self.cache_type = 'memory'
        except Exception as e:
            logger.error(f"Redis连接失败: {e}，使用内存缓存")
            self.cache_type = 'memory'
    
    def _generate_key(self, namespace: str, key: str) -> str:
        """生成缓存键"""
        return f"{namespace}:{key}"
    
    def _serialize_value(self, value: Any) -> str:
        """序列化值"""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        elif isinstance(value, str):
            return value
        else:
            return pickle.dumps(value).decode('latin-1')
    
    def _deserialize_value(self, value: str) -> Any:
        """反序列化值"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            try:
                return pickle.loads(value.encode('latin-1'))
            except:
                return value
    
    def set(self, namespace: str, key: str, value: Any, expire: int = 3600):
        """设置缓存"""
        cache_key = self._generate_key(namespace, key)
        
        try:
            if self.cache_type == 'redis' and self.redis_client:
                serialized_value = self._serialize_value(value)
                self.redis_client.setex(cache_key, expire, serialized_value)
            else:
                # 内存缓存
                self.memory_cache[cache_key] = value
                self.cache_timestamps[cache_key] = time.time() + expire
            
            logger.debug(f"缓存设置成功: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False
    
    def get(self, namespace: str, key: str) -> Optional[Any]:
        """获取缓存"""
        cache_key = self._generate_key(namespace, key)
        
        try:
            if self.cache_type == 'redis' and self.redis_client:
                value = self.redis_client.get(cache_key)
                if value:
                    return self._deserialize_value(value)
            else:
                # 内存缓存
                if cache_key in self.memory_cache:
                    # 检查过期时间
                    if time.time() < self.cache_timestamps.get(cache_key, 0):
                        return self.memory_cache[cache_key]
                    else:
                        # 过期删除
                        del self.memory_cache[cache_key]
                        del self.cache_timestamps[cache_key]
            
            return None
            
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None
    
    def delete(self, namespace: str, key: str) -> bool:
        """删除缓存"""
        cache_key = self._generate_key(namespace, key)
        
        try:
            if self.cache_type == 'redis' and self.redis_client:
                return bool(self.redis_client.delete(cache_key))
            else:
                # 内存缓存
                if cache_key in self.memory_cache:
                    del self.memory_cache[cache_key]
                    del self.cache_timestamps[cache_key]
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            return False
    
    def clear_namespace(self, namespace: str) -> bool:
        """清空命名空间"""
        try:
            if self.cache_type == 'redis' and self.redis_client:
                pattern = f"{namespace}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    return bool(self.redis_client.delete(*keys))
            else:
                # 内存缓存
                keys_to_delete = [k for k in self.memory_cache.keys() if k.startswith(f"{namespace}:")]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                    if key in self.cache_timestamps:
                        del self.cache_timestamps[key]
                return len(keys_to_delete) > 0
            
            return True
            
        except Exception as e:
            logger.error(f"清空命名空间失败: {e}")
            return False
    
    def exists(self, namespace: str, key: str) -> bool:
        """检查缓存是否存在"""
        cache_key = self._generate_key(namespace, key)
        
        try:
            if self.cache_type == 'redis' and self.redis_client:
                return bool(self.redis_client.exists(cache_key))
            else:
                # 内存缓存
                if cache_key in self.memory_cache:
                    return time.time() < self.cache_timestamps.get(cache_key, 0)
            
            return False
            
        except Exception as e:
            logger.error(f"检查缓存存在性失败: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        stats = {
            'cache_type': self.cache_type,
            'total_keys': 0,
            'memory_usage': 0
        }
        
        try:
            if self.cache_type == 'redis' and self.redis_client:
                info = self.redis_client.info()
                stats['total_keys'] = info.get('db0', {}).get('keys', 0)
                stats['memory_usage'] = info.get('used_memory', 0)
            else:
                # 内存缓存
                stats['total_keys'] = len(self.memory_cache)
                stats['memory_usage'] = sum(len(str(v)) for v in self.memory_cache.values())
                
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
        
        return stats
    
    def cleanup_expired(self):
        """清理过期缓存（仅内存缓存）"""
        if self.cache_type == 'memory':
            current_time = time.time()
            expired_keys = [
                key for key, timestamp in self.cache_timestamps.items()
                if current_time >= timestamp
            ]
            
            for key in expired_keys:
                del self.memory_cache[key]
                del self.cache_timestamps[key]
            
            logger.info(f"清理过期缓存: {len(expired_keys)} 个")

# 缓存装饰器
def cache_result(namespace: str, key_func=None, expire: int = 3600):
    """缓存结果装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(namespace, cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache_manager.set(namespace, cache_key, result, expire)
            logger.debug(f"缓存设置: {cache_key}")
            
            return result
        return wrapper
    return decorator

# 全局缓存管理器实例
cache_manager = CacheManager()

# 常用缓存命名空间
CACHE_NAMESPACES = {
    'NEWS': 'news',
    'CRAWLER': 'crawler',
    'STATISTICS': 'statistics',
    'API': 'api'
}
'''
        
        cache_manager_file = cache_dir / 'cache_manager.py'
        with open(cache_manager_file, 'w', encoding='utf-8') as f:
            f.write(cache_manager_code)
        
        # 创建__init__.py文件
        init_file = cache_dir / '__init__.py'
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('from .cache_manager import CacheManager, cache_manager, cache_result, CACHE_NAMESPACES\n')
        
        logger.info(f"缓存系统创建完成: {cache_dir}")
        return cache_dir
    
    def create_performance_monitor(self):
        """创建性能监控系统"""
        logger.info("创建性能监控系统...")
        
        monitor_dir = self.backend_dir / 'newslook' / 'monitoring'
        monitor_dir.mkdir(parents=True, exist_ok=True)
        
        performance_monitor_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能监控系统
监控系统性能指标、慢查询、资源使用情况
"""

import time
import psutil
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from functools import wraps
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, db_path: str = None):
        """初始化性能监控器"""
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            db_path = project_root / 'data' / 'db' / 'performance.db'
        
        self.db_path = str(db_path)
        self.slow_query_threshold = 1000  # 慢查询阈值（毫秒）
        self.metrics = {
            'request_count': 0,
            'total_response_time': 0,
            'slow_queries': [],
            'errors': []
        }
        self.lock = threading.Lock()
        
        self._init_database()
        logger.info("性能监控器初始化完成")
    
    def _init_database(self):
        """初始化性能数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metric_type TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    details TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS slow_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    query TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    parameters TEXT,
                    stack_trace TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_usage REAL,
                    network_io TEXT
                )
            ''')
    
    def record_metric(self, metric_type: str, metric_name: str, value: float, details: str = None):
        """记录性能指标"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT INTO performance_metrics 
                        (metric_type, metric_name, value, details)
                        VALUES (?, ?, ?, ?)
                    ''', (metric_type, metric_name, value, details))
                
                logger.debug(f"记录性能指标: {metric_type}.{metric_name} = {value}")
                
            except Exception as e:
                logger.error(f"记录性能指标失败: {e}")
    
    def record_slow_query(self, query: str, execution_time: float, parameters: str = None):
        """记录慢查询"""
        if execution_time * 1000 >= self.slow_query_threshold:
            with self.lock:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute('''
                            INSERT INTO slow_queries 
                            (query, execution_time, parameters)
                            VALUES (?, ?, ?)
                        ''', (query, execution_time, parameters))
                    
                    logger.warning(f"慢查询: {execution_time:.3f}s - {query[:100]}...")
                    
                except Exception as e:
                    logger.error(f"记录慢查询失败: {e}")
    
    def record_system_metrics(self):
        """记录系统指标"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            network_info = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO system_metrics 
                    (cpu_percent, memory_percent, disk_usage, network_io)
                    VALUES (?, ?, ?, ?)
                ''', (
                    cpu_percent,
                    memory.percent,
                    disk.percent,
                    json.dumps(network_info)
                ))
            
            logger.debug(f"系统指标: CPU={cpu_percent}%, Memory={memory.percent}%, Disk={disk.percent}%")
            
        except Exception as e:
            logger.error(f"记录系统指标失败: {e}")
    
    def get_performance_summary(self, hours: int = 24) -> Dict:
        """获取性能摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 获取性能指标摘要
                metrics_cursor = conn.execute('''
                    SELECT metric_type, metric_name, 
                           AVG(value) as avg_value,
                           MIN(value) as min_value,
                           MAX(value) as max_value,
                           COUNT(*) as count
                    FROM performance_metrics
                    WHERE timestamp >= ?
                    GROUP BY metric_type, metric_name
                ''', (cutoff_time,))
                
                metrics = [dict(row) for row in metrics_cursor.fetchall()]
                
                # 获取慢查询统计
                slow_query_cursor = conn.execute('''
                    SELECT COUNT(*) as count,
                           AVG(execution_time) as avg_time,
                           MAX(execution_time) as max_time
                    FROM slow_queries
                    WHERE timestamp >= ?
                ''', (cutoff_time,))
                
                slow_query_stats = dict(slow_query_cursor.fetchone())
                
                # 获取系统指标
                system_cursor = conn.execute('''
                    SELECT AVG(cpu_percent) as avg_cpu,
                           AVG(memory_percent) as avg_memory,
                           AVG(disk_usage) as avg_disk
                    FROM system_metrics
                    WHERE timestamp >= ?
                ''', (cutoff_time,))
                
                system_stats = dict(system_cursor.fetchone())
                
                return {
                    'time_range': f'{hours}小时',
                    'metrics': metrics,
                    'slow_queries': slow_query_stats,
                    'system': system_stats,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"获取性能摘要失败: {e}")
            return {}
    
    def get_top_slow_queries(self, limit: int = 10) -> List[Dict]:
        """获取最慢的查询"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute('''
                    SELECT query, execution_time, timestamp, parameters
                    FROM slow_queries
                    ORDER BY execution_time DESC
                    LIMIT ?
                ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"获取慢查询失败: {e}")
            return []
    
    def cleanup_old_metrics(self, days: int = 7):
        """清理旧的性能指标"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 清理性能指标
                result1 = conn.execute('''
                    DELETE FROM performance_metrics
                    WHERE timestamp < ?
                ''', (cutoff_time,))
                
                # 清理慢查询
                result2 = conn.execute('''
                    DELETE FROM slow_queries
                    WHERE timestamp < ?
                ''', (cutoff_time,))
                
                # 清理系统指标
                result3 = conn.execute('''
                    DELETE FROM system_metrics
                    WHERE timestamp < ?
                ''', (cutoff_time,))
                
                total_deleted = result1.rowcount + result2.rowcount + result3.rowcount
                logger.info(f"清理旧指标: {total_deleted} 条记录")
                
        except Exception as e:
            logger.error(f"清理旧指标失败: {e}")

# 性能监控装饰器
def monitor_performance(metric_name: str = None):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # 记录成功执行时间
                execution_time = time.time() - start_time
                performance_monitor.record_metric(
                    'function_execution',
                    metric_name or func.__name__,
                    execution_time
                )
                
                return result
                
            except Exception as e:
                # 记录错误
                execution_time = time.time() - start_time
                performance_monitor.record_metric(
                    'function_error',
                    metric_name or func.__name__,
                    execution_time,
                    str(e)
                )
                raise
                
        return wrapper
    return decorator

# 数据库查询监控装饰器
def monitor_db_query(query_type: str = 'select'):
    """数据库查询监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # 记录查询时间
                execution_time = time.time() - start_time
                performance_monitor.record_metric(
                    'db_query',
                    query_type,
                    execution_time
                )
                
                # 检查是否为慢查询
                if hasattr(func, '__name__'):
                    query_info = f"{func.__name__}({query_type})"
                else:
                    query_info = f"unknown_query({query_type})"
                
                performance_monitor.record_slow_query(
                    query_info,
                    execution_time,
                    str(args)[:500] if args else None
                )
                
                return result
                
            except Exception as e:
                logger.error(f"数据库查询错误: {e}")
                raise
                
        return wrapper
    return decorator

# 全局性能监控器实例
performance_monitor = PerformanceMonitor()

# 启动系统指标收集
def start_system_monitoring(interval: int = 60):
    """启动系统监控"""
    def monitor_loop():
        while True:
            performance_monitor.record_system_metrics()
            time.sleep(interval)
    
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    logger.info(f"系统监控已启动，间隔 {interval} 秒")
'''
        
        performance_monitor_file = monitor_dir / 'performance_monitor.py'
        with open(performance_monitor_file, 'w', encoding='utf-8') as f:
            f.write(performance_monitor_code)
        
        # 创建__init__.py文件
        init_file = monitor_dir / '__init__.py'
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('from .performance_monitor import PerformanceMonitor, performance_monitor, monitor_performance, monitor_db_query, start_system_monitoring\n')
        
        logger.info(f"性能监控系统创建完成: {monitor_dir}")
        return monitor_dir
    
    def create_error_handling_system(self):
        """创建错误处理和恢复系统"""
        logger.info("创建错误处理和恢复系统...")
        
        error_handler_dir = self.backend_dir / 'newslook' / 'error_handling'
        error_handler_dir.mkdir(parents=True, exist_ok=True)
        
        error_handler_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
错误处理和恢复系统
提供统一的错误处理、重试机制和恢复策略
"""

import logging
import traceback
import time
import functools
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

class ErrorLevel(Enum):
    """错误级别"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, db_path: str = None):
        """初始化错误处理器"""
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            db_path = project_root / 'data' / 'db' / 'error_logs.db'
        
        self.db_path = str(db_path)
        self.error_callbacks: Dict[str, List[Callable]] = {}
        self.retry_config = {
            'max_attempts': 3,
            'delay': 1,
            'backoff_factor': 2
        }
        
        self._init_database()
        logger.info("错误处理器初始化完成")
    
    def _init_database(self):
        """初始化错误日志数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    stack_trace TEXT,
                    context TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution_notes TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS retry_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    function_name TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    error_message TEXT,
                    success BOOLEAN DEFAULT FALSE
                )
            ''')
    
    def log_error(self, level: ErrorLevel, error_type: str, message: str, 
                  exception: Exception = None, context: Dict = None):
        """记录错误"""
        try:
            stack_trace = None
            if exception:
                stack_trace = traceback.format_exception(
                    type(exception), exception, exception.__traceback__
                )
                stack_trace = ''.join(stack_trace)
            
            context_str = str(context) if context else None
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO error_logs 
                    (level, error_type, message, stack_trace, context)
                    VALUES (?, ?, ?, ?, ?)
                ''', (level.value, error_type, message, stack_trace, context_str))
            
            # 触发回调
            if error_type in self.error_callbacks:
                for callback in self.error_callbacks[error_type]:
                    try:
                        callback(level, error_type, message, exception, context)
                    except Exception as e:
                        logger.error(f"错误回调执行失败: {e}")
            
            logger.log(
                getattr(logging, level.value),
                f"[{error_type}] {message}"
            )
            
        except Exception as e:
            logger.error(f"记录错误失败: {e}")
    
    def register_error_callback(self, error_type: str, callback: Callable):
        """注册错误回调"""
        if error_type not in self.error_callbacks:
            self.error_callbacks[error_type] = []
        self.error_callbacks[error_type].append(callback)
    
    def get_recent_errors(self, hours: int = 24, level: ErrorLevel = None) -> List[Dict]:
        """获取最近的错误"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                sql = '''
                    SELECT * FROM error_logs 
                    WHERE timestamp >= datetime('now', '-{} hours')
                '''.format(hours)
                
                params = []
                if level:
                    sql += ' AND level = ?'
                    params.append(level.value)
                
                sql += ' ORDER BY timestamp DESC'
                
                cursor = conn.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"获取最近错误失败: {e}")
            return []
    
    def mark_error_resolved(self, error_id: int, resolution_notes: str = None):
        """标记错误已解决"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE error_logs 
                    SET resolved = TRUE, resolution_notes = ?
                    WHERE id = ?
                ''', (resolution_notes, error_id))
            
            logger.info(f"错误已标记为解决: {error_id}")
            
        except Exception as e:
            logger.error(f"标记错误解决失败: {e}")
    
    def get_error_statistics(self, days: int = 7) -> Dict:
        """获取错误统计"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 按级别统计
                level_cursor = conn.execute('''
                    SELECT level, COUNT(*) as count
                    FROM error_logs
                    WHERE timestamp >= datetime('now', '-{} days')
                    GROUP BY level
                '''.format(days))
                
                level_stats = {row['level']: row['count'] for row in level_cursor.fetchall()}
                
                # 按类型统计
                type_cursor = conn.execute('''
                    SELECT error_type, COUNT(*) as count
                    FROM error_logs
                    WHERE timestamp >= datetime('now', '-{} days')
                    GROUP BY error_type
                    ORDER BY count DESC
                '''.format(days))
                
                type_stats = [dict(row) for row in type_cursor.fetchall()]
                
                # 解决率
                resolution_cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN resolved THEN 1 ELSE 0 END) as resolved
                    FROM error_logs
                    WHERE timestamp >= datetime('now', '-{} days')
                '''.format(days))
                
                resolution_row = resolution_cursor.fetchone()
                resolution_rate = 0
                if resolution_row['total'] > 0:
                    resolution_rate = resolution_row['resolved'] / resolution_row['total']
                
                return {
                    'time_range': f'{days}天',
                    'level_distribution': level_stats,
                    'type_distribution': type_stats,
                    'resolution_rate': resolution_rate,
                    'total_errors': resolution_row['total']
                }
                
        except Exception as e:
            logger.error(f"获取错误统计失败: {e}")
            return {}

def retry_with_backoff(max_attempts: int = 3, delay: float = 1, 
                      backoff_factor: float = 2, 
                      exceptions: tuple = (Exception,)):
    """重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                attempt += 1
                
                try:
                    result = func(*args, **kwargs)
                    
                    # 记录成功的重试
                    if attempt > 1:
                        error_handler.log_retry(
                            func.__name__, attempt, max_attempts, None, True
                        )
                    
                    return result
                    
                except exceptions as e:
                    # 记录失败的重试
                    error_handler.log_retry(
                        func.__name__, attempt, max_attempts, str(e), False
                    )
                    
                    if attempt == max_attempts:
                        error_handler.log_error(
                            ErrorLevel.ERROR,
                            'retry_exhausted',
                            f"函数 {func.__name__} 重试 {max_attempts} 次后仍然失败",
                            e,
                            {'args': args, 'kwargs': kwargs}
                        )
                        raise
                    
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
                    
                    logger.warning(f"重试 {func.__name__} ({attempt}/{max_attempts}) 失败: {e}")
            
        return wrapper
    return decorator

def handle_errors(error_type: str = None, level: ErrorLevel = ErrorLevel.ERROR):
    """错误处理装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.log_error(
                    level,
                    error_type or func.__name__,
                    f"函数 {func.__name__} 执行失败: {str(e)}",
                    e,
                    {'args': args, 'kwargs': kwargs}
                )
                raise
        return wrapper
    return decorator

# 添加重试日志记录方法
def log_retry(self, function_name: str, attempt: int, max_attempts: int, 
              error_message: str, success: bool):
    """记录重试日志"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO retry_logs 
                (function_name, attempt_number, max_attempts, error_message, success)
                VALUES (?, ?, ?, ?, ?)
            ''', (function_name, attempt, max_attempts, error_message, success))
    except Exception as e:
        logger.error(f"记录重试日志失败: {e}")

# 给ErrorHandler类添加方法
ErrorHandler.log_retry = log_retry

# 全局错误处理器实例
error_handler = ErrorHandler()

# 预定义错误回调
def database_error_callback(level, error_type, message, exception, context):
    """数据库错误回调"""
    if 'database' in error_type.lower():
        logger.critical(f"数据库错误: {message}")
        # 这里可以添加数据库恢复逻辑

def crawler_error_callback(level, error_type, message, exception, context):
    """爬虫错误回调"""
    if 'crawler' in error_type.lower():
        logger.warning(f"爬虫错误: {message}")
        # 这里可以添加爬虫重启逻辑

# 注册默认回调
error_handler.register_error_callback('database_error', database_error_callback)
error_handler.register_error_callback('crawler_error', crawler_error_callback)
'''
        
        error_handler_file = error_handler_dir / 'error_handler.py'
        with open(error_handler_file, 'w', encoding='utf-8') as f:
            f.write(error_handler_code)
        
        # 创建__init__.py文件
        init_file = error_handler_dir / '__init__.py'
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('from .error_handler import ErrorHandler, ErrorLevel, error_handler, retry_with_backoff, handle_errors\n')
        
        logger.info(f"错误处理系统创建完成: {error_handler_dir}")
        return error_handler_dir
    
    def generate_optimization_report(self) -> Path:
        """生成优化报告"""
        self.report['end_time'] = datetime.now().isoformat()
        
        report_file = self.project_root / f"performance_optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"生成优化报告: {report_file}")
        return report_file
    
    def run_full_optimization(self) -> Path:
        """运行完整的性能架构优化"""
        logger.info("开始技术架构和性能优化...")
        
        try:
            # 1. 创建WebSocket服务器
            websocket_server = self.create_websocket_server()
            self.report['optimizations'].append({
                'action': 'create_websocket_server',
                'directory': str(websocket_server)
            })
            
            # 2. 创建缓存系统
            cache_system = self.create_caching_system()
            self.report['optimizations'].append({
                'action': 'create_caching_system',
                'directory': str(cache_system)
            })
            
            # 3. 创建性能监控系统
            performance_monitor = self.create_performance_monitor()
            self.report['optimizations'].append({
                'action': 'create_performance_monitor',
                'directory': str(performance_monitor)
            })
            
            # 4. 创建错误处理系统
            error_handler = self.create_error_handling_system()
            self.report['optimizations'].append({
                'action': 'create_error_handling_system',
                'directory': str(error_handler)
            })
            
            # 5. 生成报告
            report_file = self.generate_optimization_report()
            
            logger.info("技术架构和性能优化完成!")
            return report_file
            
        except Exception as e:
            logger.error(f"优化过程中出错: {e}")
            self.report['errors'].append(str(e))
            return self.generate_optimization_report()

def main():
    """主函数"""
    optimizer = PerformanceArchitectureOptimizer()
    report_file = optimizer.run_full_optimization()
    
    print(f"\n技术架构和性能优化完成! 报告文件: {report_file}")

if __name__ == "__main__":
    main() 