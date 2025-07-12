#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态持久化管理器 - 第二优先级指令实现
实现SQLite→Redis→PostgreSQL三级存储架构
"""

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
import traceback

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import psycopg2
    import psycopg2.extras
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

from backend.newslook.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class StateRecord:
    """状态记录数据类"""
    key: str
    value: Any
    timestamp: datetime
    ttl: Optional[int] = None  # 生存时间（秒）
    metadata: Dict[str, Any] = None
    level: str = 'sqlite'  # 存储级别：sqlite, redis, postgresql

class StatePersistenceManager:
    """
    状态持久化管理器
    
    三级存储架构：
    1. SQLite - 本地快速存储（L1缓存）
    2. Redis - 内存高速缓存（L2缓存）
    3. PostgreSQL - 持久化存储（L3存储）
    
    特性：
    - 自动数据同步
    - 故障转移
    - 性能监控
    - 数据一致性保证
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化状态持久化管理器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 初始化存储连接
        self.sqlite_db = None
        self.redis_client = None
        self.postgresql_conn = None
        
        # 连接状态
        self.sqlite_connected = False
        self.redis_connected = False
        self.postgresql_connected = False
        
        # 同步相关
        self.sync_thread = None
        self.sync_interval = self.config.get('sync_interval', 30)  # 秒
        self.is_syncing = False
        
        # 性能统计
        self.stats = {
            'sqlite_ops': 0,
            'redis_ops': 0,
            'postgresql_ops': 0,
            'sync_cycles': 0,
            'failed_syncs': 0,
            'last_sync': None
        }
        
        # 初始化连接
        self._init_connections()
        
        # 启动同步线程
        self._start_sync_thread()
        
        logger.info("状态持久化管理器初始化完成")
    
    def _init_connections(self):
        """初始化所有存储连接"""
        # 初始化SQLite
        self._init_sqlite()
        
        # 初始化Redis（如果可用）
        if REDIS_AVAILABLE:
            self._init_redis()
        
        # 初始化PostgreSQL（如果可用）
        if POSTGRESQL_AVAILABLE:
            self._init_postgresql()
    
    def _init_sqlite(self):
        """初始化SQLite连接"""
        try:
            sqlite_path = self.config.get('sqlite_path', 'data/state.db')
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.sqlite_db = sqlite3.connect(sqlite_path, check_same_thread=False)
            self.sqlite_db.row_factory = sqlite3.Row
            
            # 创建状态表
            cursor = self.sqlite_db.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state_records (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ttl INTEGER,
                    metadata TEXT,
                    level TEXT DEFAULT 'sqlite',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON state_records(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_level ON state_records(level)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ttl ON state_records(ttl)")
            
            self.sqlite_db.commit()
            self.sqlite_connected = True
            
            logger.info(f"SQLite连接初始化成功: {sqlite_path}")
            
        except Exception as e:
            logger.error(f"SQLite初始化失败: {str(e)}")
            self.sqlite_connected = False
    
    def _init_redis(self):
        """初始化Redis连接"""
        try:
            redis_config = self.config.get('redis', {})
            
            self.redis_client = redis.Redis(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                db=redis_config.get('db', 0),
                password=redis_config.get('password'),
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # 测试连接
            self.redis_client.ping()
            self.redis_connected = True
            
            logger.info("Redis连接初始化成功")
            
        except Exception as e:
            logger.warning(f"Redis连接失败: {str(e)}")
            self.redis_connected = False
    
    def _init_postgresql(self):
        """初始化PostgreSQL连接"""
        try:
            pg_config = self.config.get('postgresql', {})
            
            if not pg_config:
                logger.info("PostgreSQL配置未设置，跳过初始化")
                return
            
            self.postgresql_conn = psycopg2.connect(
                host=pg_config.get('host', 'localhost'),
                port=pg_config.get('port', 5432),
                database=pg_config.get('database', 'newslook'),
                user=pg_config.get('user', 'postgres'),
                password=pg_config.get('password', ''),
                connect_timeout=10
            )
            
            # 创建状态表
            cursor = self.postgresql_conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state_records (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    ttl INTEGER,
                    metadata JSONB,
                    level VARCHAR(50) DEFAULT 'postgresql',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_state_timestamp ON state_records(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_state_level ON state_records(level)")
            
            self.postgresql_conn.commit()
            self.postgresql_connected = True
            
            logger.info("PostgreSQL连接初始化成功")
            
        except Exception as e:
            logger.warning(f"PostgreSQL连接失败: {str(e)}")
            self.postgresql_connected = False
    
    def set_state(self, key: str, value: Any, ttl: Optional[int] = None, level: str = 'auto') -> bool:
        """
        设置状态值
        
        Args:
            key: 状态键
            value: 状态值
            ttl: 生存时间（秒）
            level: 存储级别（auto, sqlite, redis, postgresql）
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 确定存储级别
            if level == 'auto':
                level = self._determine_storage_level(key, value, ttl)
            
            # 序列化值
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            
            # 创建状态记录
            record = StateRecord(
                key=key,
                value=serialized_value,
                timestamp=datetime.now(),
                ttl=ttl,
                metadata={'size': len(serialized_value)},
                level=level
            )
            
            # 根据级别存储
            success = False
            
            if level == 'postgresql' and self.postgresql_connected:
                success = self._set_postgresql(record)
                if success:
                    self.stats['postgresql_ops'] += 1
            
            if (level in ['redis', 'auto'] or not success) and self.redis_connected:
                success = self._set_redis(record)
                if success:
                    self.stats['redis_ops'] += 1
            
            if (level in ['sqlite', 'auto'] or not success) and self.sqlite_connected:
                success = self._set_sqlite(record)
                if success:
                    self.stats['sqlite_ops'] += 1
            
            if success:
                logger.debug(f"状态设置成功: {key} -> {level}")
            else:
                logger.error(f"状态设置失败: {key}")
            
            return success
            
        except Exception as e:
            logger.error(f"设置状态失败 {key}: {str(e)}")
            return False
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """
        获取状态值
        
        Args:
            key: 状态键
            default: 默认值
            
        Returns:
            Any: 状态值
        """
        try:
            # 按优先级顺序查找：Redis > SQLite > PostgreSQL
            
            # 尝试从Redis获取
            if self.redis_connected:
                value = self._get_redis(key)
                if value is not None:
                    return self._deserialize_value(value)
            
            # 尝试从SQLite获取
            if self.sqlite_connected:
                record = self._get_sqlite(key)
                if record:
                    # 检查TTL
                    if self._is_record_valid(record):
                        # 如果Redis可用，将值同步到Redis
                        if self.redis_connected:
                            self._sync_to_redis(record)
                        return self._deserialize_value(record['value'])
                    else:
                        # 过期数据，删除
                        self._delete_sqlite(key)
            
            # 尝试从PostgreSQL获取
            if self.postgresql_connected:
                record = self._get_postgresql(key)
                if record:
                    if self._is_record_valid(record):
                        # 同步到更高级缓存
                        if self.redis_connected:
                            self._sync_to_redis(record)
                        if self.sqlite_connected:
                            self._sync_to_sqlite(record)
                        return self._deserialize_value(record['value'])
                    else:
                        self._delete_postgresql(key)
            
            return default
            
        except Exception as e:
            logger.error(f"获取状态失败 {key}: {str(e)}")
            return default
    
    def delete_state(self, key: str) -> bool:
        """
        删除状态值
        
        Args:
            key: 状态键
            
        Returns:
            bool: 操作是否成功
        """
        try:
            success = True
            
            # 从所有存储中删除
            if self.redis_connected:
                try:
                    self.redis_client.delete(key)
                except Exception as e:
                    logger.error(f"Redis删除失败: {str(e)}")
                    success = False
            
            if self.sqlite_connected:
                success = self._delete_sqlite(key) and success
            
            if self.postgresql_connected:
                success = self._delete_postgresql(key) and success
            
            logger.debug(f"状态删除: {key} -> {'成功' if success else '失败'}")
            return success
            
        except Exception as e:
            logger.error(f"删除状态失败 {key}: {str(e)}")
            return False
    
    def _determine_storage_level(self, key: str, value: Any, ttl: Optional[int]) -> str:
        """确定存储级别"""
        # 临时数据（TTL < 1小时）-> Redis
        if ttl and ttl < 3600:
            return 'redis'
        
        # 大数据（> 1MB）-> PostgreSQL
        serialized = json.dumps(value) if not isinstance(value, str) else value
        if len(serialized) > 1024 * 1024:
            return 'postgresql'
        
        # 频繁访问的键 -> Redis
        if any(pattern in key for pattern in ['cache:', 'temp:', 'session:']):
            return 'redis'
        
        # 配置和元数据 -> PostgreSQL
        if any(pattern in key for pattern in ['config:', 'meta:', 'schema:']):
            return 'postgresql'
        
        # 默认使用SQLite
        return 'sqlite'
    
    def _set_sqlite(self, record: StateRecord) -> bool:
        """在SQLite中设置状态"""
        try:
            cursor = self.sqlite_db.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO state_records 
                (key, value, timestamp, ttl, metadata, level, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record.key,
                record.value,
                record.timestamp.isoformat(),
                record.ttl,
                json.dumps(record.metadata) if record.metadata else None,
                record.level,
                datetime.now().isoformat()
            ))
            self.sqlite_db.commit()
            return True
        except Exception as e:
            logger.error(f"SQLite设置失败: {str(e)}")
            return False
    
    def _get_sqlite(self, key: str) -> Optional[Dict]:
        """从SQLite获取状态"""
        try:
            cursor = self.sqlite_db.cursor()
            cursor.execute("SELECT * FROM state_records WHERE key = ?", (key,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"SQLite获取失败: {str(e)}")
            return None
    
    def _delete_sqlite(self, key: str) -> bool:
        """从SQLite删除状态"""
        try:
            cursor = self.sqlite_db.cursor()
            cursor.execute("DELETE FROM state_records WHERE key = ?", (key,))
            self.sqlite_db.commit()
            return True
        except Exception as e:
            logger.error(f"SQLite删除失败: {str(e)}")
            return False
    
    def _set_redis(self, record: StateRecord) -> bool:
        """在Redis中设置状态"""
        try:
            if record.ttl:
                self.redis_client.setex(record.key, record.ttl, record.value)
            else:
                self.redis_client.set(record.key, record.value)
            return True
        except Exception as e:
            logger.error(f"Redis设置失败: {str(e)}")
            return False
    
    def _get_redis(self, key: str) -> Optional[str]:
        """从Redis获取状态"""
        try:
            return self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis获取失败: {str(e)}")
            return None
    
    def _set_postgresql(self, record: StateRecord) -> bool:
        """在PostgreSQL中设置状态"""
        try:
            cursor = self.postgresql_conn.cursor()
            cursor.execute("""
                INSERT INTO state_records 
                (key, value, timestamp, ttl, metadata, level, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                timestamp = EXCLUDED.timestamp,
                ttl = EXCLUDED.ttl,
                metadata = EXCLUDED.metadata,
                level = EXCLUDED.level,
                updated_at = EXCLUDED.updated_at
            """, (
                record.key,
                record.value,
                record.timestamp,
                record.ttl,
                json.dumps(record.metadata) if record.metadata else None,
                record.level,
                datetime.now()
            ))
            self.postgresql_conn.commit()
            return True
        except Exception as e:
            logger.error(f"PostgreSQL设置失败: {str(e)}")
            # 尝试重新连接
            self._reconnect_postgresql()
            return False
    
    def _get_postgresql(self, key: str) -> Optional[Dict]:
        """从PostgreSQL获取状态"""
        try:
            cursor = self.postgresql_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT * FROM state_records WHERE key = %s", (key,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"PostgreSQL获取失败: {str(e)}")
            return None
    
    def _delete_postgresql(self, key: str) -> bool:
        """从PostgreSQL删除状态"""
        try:
            cursor = self.postgresql_conn.cursor()
            cursor.execute("DELETE FROM state_records WHERE key = %s", (key,))
            self.postgresql_conn.commit()
            return True
        except Exception as e:
            logger.error(f"PostgreSQL删除失败: {str(e)}")
            return False
    
    def _is_record_valid(self, record: Dict) -> bool:
        """检查记录是否有效（未过期）"""
        if not record.get('ttl'):
            return True
        
        timestamp_str = record.get('timestamp', '')
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str)
        else:
            timestamp = timestamp_str
        
        ttl = record['ttl']
        expiry_time = timestamp + timedelta(seconds=ttl)
        
        return datetime.now() < expiry_time
    
    def _deserialize_value(self, value: str) -> Any:
        """反序列化值"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    def _sync_to_redis(self, record: Dict):
        """同步数据到Redis"""
        try:
            if self.redis_connected:
                key = record['key']
                value = record['value']
                ttl = record.get('ttl')
                
                if ttl:
                    self.redis_client.setex(key, ttl, value)
                else:
                    self.redis_client.set(key, value)
        except Exception as e:
            logger.error(f"同步到Redis失败: {str(e)}")
    
    def _sync_to_sqlite(self, record: Dict):
        """同步数据到SQLite"""
        try:
            if self.sqlite_connected:
                cursor = self.sqlite_db.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO state_records 
                    (key, value, timestamp, ttl, metadata, level, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    record['key'],
                    record['value'],
                    record['timestamp'],
                    record.get('ttl'),
                    record.get('metadata'),
                    record.get('level', 'sqlite'),
                    datetime.now().isoformat()
                ))
                self.sqlite_db.commit()
        except Exception as e:
            logger.error(f"同步到SQLite失败: {str(e)}")
    
    def _start_sync_thread(self):
        """启动同步线程"""
        if self.sync_interval > 0:
            self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
            self.sync_thread.start()
            logger.info(f"同步线程已启动，间隔: {self.sync_interval}秒")
    
    def _sync_loop(self):
        """同步循环"""
        while True:
            try:
                time.sleep(self.sync_interval)
                
                if not self.is_syncing:
                    self.is_syncing = True
                    self._perform_sync()
                    self.is_syncing = False
                    
            except Exception as e:
                logger.error(f"同步循环出错: {str(e)}")
                self.stats['failed_syncs'] += 1
                self.is_syncing = False
                time.sleep(self.sync_interval)
    
    def _perform_sync(self):
        """执行同步操作"""
        try:
            logger.debug("开始执行数据同步")
            
            # 清理过期数据
            self._cleanup_expired_data()
            
            # SQLite -> PostgreSQL 同步
            if self.sqlite_connected and self.postgresql_connected:
                self._sync_sqlite_to_postgresql()
            
            # Redis -> SQLite 同步（持久化热数据）
            if self.redis_connected and self.sqlite_connected:
                self._sync_redis_to_sqlite()
            
            self.stats['sync_cycles'] += 1
            self.stats['last_sync'] = datetime.now().isoformat()
            
            logger.debug("数据同步完成")
            
        except Exception as e:
            logger.error(f"同步操作失败: {str(e)}")
            self.stats['failed_syncs'] += 1
    
    def _cleanup_expired_data(self):
        """清理过期数据"""
        try:
            current_time = datetime.now()
            
            # 清理SQLite过期数据
            if self.sqlite_connected:
                cursor = self.sqlite_db.cursor()
                cursor.execute("""
                    DELETE FROM state_records 
                    WHERE ttl IS NOT NULL 
                    AND datetime(timestamp, '+' || ttl || ' seconds') < ?
                """, (current_time.isoformat(),))
                deleted_sqlite = cursor.rowcount
                self.sqlite_db.commit()
                
                if deleted_sqlite > 0:
                    logger.debug(f"清理SQLite过期数据: {deleted_sqlite}条")
            
            # 清理PostgreSQL过期数据
            if self.postgresql_connected:
                cursor = self.postgresql_conn.cursor()
                cursor.execute("""
                    DELETE FROM state_records 
                    WHERE ttl IS NOT NULL 
                    AND timestamp + INTERVAL '1 second' * ttl < %s
                """, (current_time,))
                deleted_pg = cursor.rowcount
                self.postgresql_conn.commit()
                
                if deleted_pg > 0:
                    logger.debug(f"清理PostgreSQL过期数据: {deleted_pg}条")
                    
        except Exception as e:
            logger.error(f"清理过期数据失败: {str(e)}")
    
    def _sync_sqlite_to_postgresql(self):
        """SQLite同步到PostgreSQL"""
        try:
            # 获取需要同步的数据（最近1小时的修改）
            cursor = self.sqlite_db.cursor()
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            cursor.execute("""
                SELECT * FROM state_records 
                WHERE updated_at > ? AND level IN ('postgresql', 'auto')
                LIMIT 100
            """, (one_hour_ago,))
            
            rows = cursor.fetchall()
            
            if rows:
                pg_cursor = self.postgresql_conn.cursor()
                for row in rows:
                    try:
                        pg_cursor.execute("""
                            INSERT INTO state_records 
                            (key, value, timestamp, ttl, metadata, level, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (key) DO UPDATE SET
                            value = EXCLUDED.value,
                            timestamp = EXCLUDED.timestamp,
                            updated_at = EXCLUDED.updated_at
                        """, (
                            row['key'], row['value'], 
                            datetime.fromisoformat(row['timestamp']),
                            row['ttl'], row['metadata'], 
                            row['level'], datetime.now()
                        ))
                    except Exception as e:
                        logger.error(f"同步单条记录失败 {row['key']}: {str(e)}")
                
                self.postgresql_conn.commit()
                logger.debug(f"SQLite->PostgreSQL同步: {len(rows)}条记录")
                
        except Exception as e:
            logger.error(f"SQLite到PostgreSQL同步失败: {str(e)}")
    
    def _sync_redis_to_sqlite(self):
        """Redis热数据同步到SQLite"""
        # Redis数据通常是临时的，这里主要是为了数据恢复
        # 实际实现会根据具体需求调整
        pass
    
    def _reconnect_postgresql(self):
        """重新连接PostgreSQL"""
        try:
            if self.postgresql_conn:
                self.postgresql_conn.close()
            self._init_postgresql()
        except Exception as e:
            logger.error(f"PostgreSQL重连失败: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'connections': {
                'sqlite': self.sqlite_connected,
                'redis': self.redis_connected,
                'postgresql': self.postgresql_connected
            },
            'operations': self.stats.copy(),
            'sync_status': {
                'is_syncing': self.is_syncing,
                'interval': self.sync_interval,
                'last_sync': self.stats.get('last_sync')
            }
        }
    
    def close(self):
        """关闭所有连接"""
        if self.sqlite_db:
            self.sqlite_db.close()
        
        if self.redis_client:
            self.redis_client.close()
        
        if self.postgresql_conn:
            self.postgresql_conn.close()
        
        logger.info("状态持久化管理器已关闭")

# 全局状态持久化管理器实例
_state_manager: Optional[StatePersistenceManager] = None

def get_state_manager() -> StatePersistenceManager:
    """获取全局状态持久化管理器实例"""
    global _state_manager
    if _state_manager is None:
        # 从配置获取设置
        config = {
            'sqlite_path': 'data/state.db',
            'sync_interval': 60,  # 60秒同步一次
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 1
            },
            'postgresql': {
                # PostgreSQL配置留空，仅在明确配置时启用
            }
        }
        _state_manager = StatePersistenceManager(config)
    return _state_manager

def set_state(key: str, value: Any, ttl: Optional[int] = None, level: str = 'auto') -> bool:
    """便捷函数：设置状态"""
    return get_state_manager().set_state(key, value, ttl, level)

def get_state(key: str, default: Any = None) -> Any:
    """便捷函数：获取状态"""
    return get_state_manager().get_state(key, default)

def delete_state(key: str) -> bool:
    """便捷函数：删除状态"""
    return get_state_manager().delete_state(key) 