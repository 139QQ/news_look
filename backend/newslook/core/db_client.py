#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据库客户端
提供统一的数据库操作接口、连接池管理和健康检查功能
"""

import sqlite3
import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
import json
import time
from threading import Lock
from pathlib import Path
try:
    import aiosqlite
except ImportError:
    aiosqlite = None

logger = logging.getLogger(__name__)


@dataclass
class DBConfig:
    """数据库配置"""
    db_path: str
    pool_size: int = 10
    timeout: int = 30
    enable_wal: bool = True
    cache_size: int = 10000
    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"
    

@dataclass
class HealthStatus:
    """健康状态"""
    is_healthy: bool
    response_time_ms: float
    connection_count: int
    last_check: datetime
    error_message: Optional[str] = None


class ConnectionPool:
    """连接池管理"""
    
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self.connections = []
        self.busy_connections = set()
        self.lock = Lock()
        self._setup_database()
    
    def _setup_database(self):
        """设置数据库"""
        # 确保数据库目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库连接
        with sqlite3.connect(self.db_path) as conn:
            # 启用WAL模式
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        with self.lock:
            if self.connections:
                conn = self.connections.pop()
            else:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
            
            self.busy_connections.add(conn)
        
        try:
            yield conn
        finally:
            with self.lock:
                self.busy_connections.remove(conn)
                if len(self.connections) < self.max_connections:
                    self.connections.append(conn)
                else:
                    conn.close()
    
    def close_all(self):
        """关闭所有连接"""
        with self.lock:
            for conn in self.connections:
                conn.close()
            self.connections.clear()
            
            for conn in self.busy_connections:
                conn.close()
            self.busy_connections.clear()
    
    def get_status(self) -> Dict[str, Any]:
        """获取连接池状态"""
        with self.lock:
            return {
                "total_connections": len(self.connections) + len(self.busy_connections),
                "available_connections": len(self.connections),
                "busy_connections": len(self.busy_connections),
                "max_connections": self.max_connections,
                "utilization_rate": len(self.busy_connections) / self.max_connections * 100
            }


class DBClient:
    """统一数据库客户端"""
    
    def __init__(self, config: DBConfig):
        self.config = config
        self.pool = ConnectionPool(config.db_path, config.pool_size)
        self.health_status = HealthStatus(
            is_healthy=False,
            response_time_ms=0,
            connection_count=0,
            last_check=datetime.now()
        )
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger(f"DBClient-{Path(self.config.db_path).stem}")
        self.logger.setLevel(logging.INFO)
    
    def _monitor_operation(self, operation_name: str, func):
        """监控数据库操作"""
        start_time = time.time()
        try:
            result = func()
            
            # 更新健康状态
            self.health_status.is_healthy = True
            self.health_status.response_time_ms = (time.time() - start_time) * 1000
            self.health_status.connection_count = len(self.pool.connections)
            self.health_status.last_check = datetime.now()
            self.health_status.error_message = None
            
            return result
        except Exception as e:
            # 记录错误
            self.health_status.is_healthy = False
            self.health_status.error_message = str(e)
            self.health_status.last_check = datetime.now()
            self.logger.error(f"数据库操作失败[{operation_name}]: {e}")
            raise
    
    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """执行SQL查询"""
        def _execute():
            params_safe = params or {}
            
            with self.pool.get_connection() as conn:
                try:
                    cursor = conn.execute(query, params_safe)
                    if query.strip().upper().startswith('SELECT'):
                        return [dict(row) for row in cursor.fetchall()]
                    else:
                        conn.commit()
                        return [{"rows_affected": cursor.rowcount}]
                except Exception as e:
                    conn.rollback()
                    raise
        
        return self._monitor_operation("execute", _execute)
    
    def execute_many(self, query: str, params_list: List[Dict[str, Any]]) -> int:
        """批量执行SQL"""
        def _execute_many():
            with self.pool.get_connection() as conn:
                try:
                    cursor = conn.cursor()
                    cursor.executemany(query, params_list)
                    conn.commit()
                    return cursor.rowcount
                except Exception as e:
                    conn.rollback()
                    raise
        
        return self._monitor_operation("execute_many", _execute_many)
    
    def transaction(self, queries: List[Dict[str, Any]]) -> List[Any]:
        """事务执行"""
        def _transaction():
            with self.pool.get_connection() as conn:
                try:
                    results = []
                    for query_info in queries:
                        query = query_info['query']
                        params = query_info.get('params', {})
                        
                        cursor = conn.execute(query, params)
                        if query.strip().upper().startswith('SELECT'):
                            results.append([dict(row) for row in cursor.fetchall()])
                        else:
                            results.append({"rows_affected": cursor.rowcount})
                    
                    conn.commit()
                    return results
                except Exception as e:
                    conn.rollback()
                    raise
        
        return self._monitor_operation("transaction", _transaction)
    
    def get_health_status(self) -> HealthStatus:
        """获取健康状态"""
        return self.health_status
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        pool_status = self.pool.get_status()
        return {
            "db_path": self.config.db_path,
            "pool_config": {
                "max_connections": self.config.pool_size,
                "timeout": self.config.timeout
            },
            "pool_status": pool_status,
            "health_status": {
                "is_healthy": self.health_status.is_healthy,
                "response_time_ms": self.health_status.response_time_ms,
                "last_check": self.health_status.last_check.isoformat(),
                "error_message": self.health_status.error_message
            }
        }
    
    def close(self):
        """关闭客户端"""
        self.pool.close_all()
        self.logger.info("数据库客户端已关闭")


class AsyncDBClient:
    """异步数据库客户端"""
    
    def __init__(self, config: DBConfig):
        self.config = config
        self.connections = []
        self.max_connections = config.pool_size
        self.lock = asyncio.Lock()
        self.health_status = HealthStatus(
            is_healthy=False,
            response_time_ms=0,
            connection_count=0,
            last_check=datetime.now()
        )
    
    async def _setup_database(self):
        """设置数据库"""
        Path(self.config.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        async with aiosqlite.connect(self.config.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            await db.execute("PRAGMA cache_size=10000")
            await db.execute("PRAGMA foreign_keys=ON")
            await db.commit()
    
    @asynccontextmanager
    async def get_connection(self):
        """获取异步连接"""
        async with self.lock:
            if self.connections:
                conn = self.connections.pop()
            else:
                conn = await aiosqlite.connect(self.config.db_path)
                conn.row_factory = aiosqlite.Row
        
        try:
            yield conn
        finally:
            async with self.lock:
                if len(self.connections) < self.max_connections:
                    self.connections.append(conn)
                else:
                    await conn.close()
    
    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """异步执行SQL查询"""
        start_time = time.time()
        params = params or {}
        
        try:
            async with self.get_connection() as conn:
                if query.strip().upper().startswith('SELECT'):
                    cursor = await conn.execute(query, params)
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
                else:
                    await conn.execute(query, params)
                    await conn.commit()
                    return [{"rows_affected": conn.total_changes}]
        except Exception as e:
            self.health_status.is_healthy = False
            self.health_status.error_message = str(e)
            raise
        finally:
            # 更新健康状态
            self.health_status.response_time_ms = (time.time() - start_time) * 1000
            self.health_status.last_check = datetime.now()
    
    async def close(self):
        """关闭所有连接"""
        async with self.lock:
            for conn in self.connections:
                await conn.close()
            self.connections.clear()


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.clients: Dict[str, DBClient] = {}
        self.async_clients: Dict[str, AsyncDBClient] = {}
    
    def register_database(self, name: str, config: DBConfig) -> DBClient:
        """注册数据库"""
        client = DBClient(config)
        self.clients[name] = client
        return client
    
    def register_async_database(self, name: str, config: DBConfig) -> AsyncDBClient:
        """注册异步数据库"""
        client = AsyncDBClient(config)
        self.async_clients[name] = client
        return client
    
    def get_client(self, name: str) -> Optional[DBClient]:
        """获取数据库客户端"""
        return self.clients.get(name)
    
    def get_async_client(self, name: str) -> Optional[AsyncDBClient]:
        """获取异步数据库客户端"""
        return self.async_clients.get(name)
    
    def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有数据库的健康状态"""
        status = {}
        
        for name, client in self.clients.items():
            status[name] = client.get_connection_stats()
        
        return status
    
    def close_all(self):
        """关闭所有数据库连接"""
        for client in self.clients.values():
            client.close()
        
        for client in self.async_clients.values():
            asyncio.create_task(client.close())


# 全局数据库管理器
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器"""
    return db_manager 