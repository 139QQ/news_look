"""
SQLite数据库优化器
实现WAL模式、连接池、锁争用缓解等紧急优化措施
"""

import sqlite3
import threading
import time
import logging
import contextlib
from typing import Dict, List, Optional, Generator
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import queue

logger = logging.getLogger(__name__)

class SQLiteConnectionPool:
    """SQLite连接池管理器"""
    
    def __init__(self, db_path: str, pool_size: int = 10, timeout: int = 30):
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool = queue.Queue(maxsize=pool_size)
        self._all_connections = []
        self._lock = threading.Lock()
        self._initialize_pool()
        
    def _initialize_pool(self):
        """初始化连接池"""
        for _ in range(self.pool_size):
            conn = self._create_optimized_connection()
            self._pool.put(conn)
            self._all_connections.append(conn)
            
    def _create_optimized_connection(self) -> sqlite3.Connection:
        """创建优化的SQLite连接"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.timeout,
            check_same_thread=False,
            isolation_level=None  # 自动提交模式
        )
        
        # 启用WAL模式和性能优化
        self._optimize_connection(conn)
        return conn
        
    def _optimize_connection(self, conn: sqlite3.Connection):
        """优化SQLite连接设置"""
        cursor = conn.cursor()
        
        # 启用WAL模式（写前日志）
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # 设置锁等待时间
        cursor.execute("PRAGMA busy_timeout=5000")
        
        # 性能优化设置
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB缓存
        cursor.execute("PRAGMA temp_store=MEMORY")   # 临时表存储在内存
        cursor.execute("PRAGMA mmap_size=268435456") # 256MB内存映射
        cursor.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全
        cursor.execute("PRAGMA wal_autocheckpoint=1000")  # WAL检查点
        
        # 启用查询优化器
        cursor.execute("PRAGMA optimize")
        
        logger.info(f"SQLite连接优化完成: {self.db_path}")
        
    @contextlib.contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """获取连接的上下文管理器"""
        try:
            conn = self._pool.get(timeout=self.timeout)
            yield conn
        except queue.Empty:
            logger.warning(f"连接池超时，创建临时连接: {self.db_path}")
            conn = self._create_optimized_connection()
            yield conn
            conn.close()
        else:
            self._pool.put(conn)
            
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for conn in self._all_connections:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"关闭连接失败: {e}")
            self._all_connections.clear()


class SQLiteOptimizer:
    """SQLite数据库优化器主类"""
    
    def __init__(self):
        self.pools: Dict[str, SQLiteConnectionPool] = {}
        self.executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="sqlite-opt")
        
    def get_or_create_pool(self, db_path: str, pool_size: int = 10) -> SQLiteConnectionPool:
        """获取或创建数据库连接池"""
        if db_path not in self.pools:
            self.pools[db_path] = SQLiteConnectionPool(db_path, pool_size)
            logger.info(f"为数据库创建连接池: {db_path}")
        return self.pools[db_path]
        
    def optimize_database_file(self, db_path: str) -> dict:
        """优化单个数据库文件"""
        start_time = time.time()
        
        try:
            # 确保数据库文件存在
            if not Path(db_path).exists():
                logger.warning(f"数据库文件不存在: {db_path}")
                return {"status": "error", "message": "数据库文件不存在"}
                
            pool = self.get_or_create_pool(db_path)
            
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # 收集优化前的状态
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA freelist_count")
                freelist_count = cursor.fetchone()[0]
                
                # 执行优化操作
                cursor.execute("VACUUM")  # 重建数据库
                cursor.execute("ANALYZE") # 更新查询计划统计
                cursor.execute("PRAGMA optimize") # 优化索引
                
                # 收集优化后的状态
                cursor.execute("PRAGMA page_count")
                new_page_count = cursor.fetchone()[0]
                
                optimization_time = time.time() - start_time
                
                result = {
                    "status": "success",
                    "db_path": db_path,
                    "optimization_time": optimization_time,
                    "before": {
                        "page_count": page_count,
                        "page_size": page_size,
                        "freelist_count": freelist_count,
                        "size_mb": (page_count * page_size) / 1024 / 1024
                    },
                    "after": {
                        "page_count": new_page_count,
                        "page_size": page_size,
                        "size_mb": (new_page_count * page_size) / 1024 / 1024
                    }
                }
                
                logger.info(f"数据库优化完成: {db_path}, 耗时: {optimization_time:.2f}s")
                return result
                
        except Exception as e:
            logger.error(f"数据库优化失败 {db_path}: {e}")
            return {"status": "error", "db_path": db_path, "message": str(e)}
            
    def optimize_all_databases(self, db_paths: List[str]) -> List[dict]:
        """并行优化多个数据库"""
        logger.info(f"开始优化 {len(db_paths)} 个数据库")
        
        # 使用线程池并行处理
        futures = []
        for db_path in db_paths:
            future = self.executor.submit(self.optimize_database_file, db_path)
            futures.append(future)
            
        results = []
        for future in futures:
            try:
                result = future.result(timeout=300)  # 5分钟超时
                results.append(result)
            except Exception as e:
                logger.error(f"优化任务失败: {e}")
                results.append({"status": "error", "message": str(e)})
                
        return results
        
    def enable_wal_mode_for_all(self, db_paths: List[str]) -> dict:
        """为所有数据库启用WAL模式"""
        results = {"success": [], "failed": []}
        
        for db_path in db_paths:
            try:
                pool = self.get_or_create_pool(db_path)
                with pool.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA journal_mode=WAL")
                    result = cursor.fetchone()[0]
                    
                    if result.upper() == 'WAL':
                        results["success"].append(db_path)
                        logger.info(f"WAL模式启用成功: {db_path}")
                    else:
                        results["failed"].append(f"{db_path}: {result}")
                        
            except Exception as e:
                results["failed"].append(f"{db_path}: {str(e)}")
                logger.error(f"WAL模式启用失败 {db_path}: {e}")
                
        return results
        
    def get_database_stats(self, db_path: str) -> dict:
        """获取数据库统计信息"""
        try:
            pool = self.get_or_create_pool(db_path)
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # 收集统计信息
                stats = {"db_path": db_path}
                
                # 基本信息
                cursor.execute("PRAGMA page_count")
                stats["page_count"] = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA page_size") 
                stats["page_size"] = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA journal_mode")
                stats["journal_mode"] = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA synchronous")
                stats["synchronous"] = cursor.fetchone()[0]
                
                # 计算大小
                stats["size_mb"] = (stats["page_count"] * stats["page_size"]) / 1024 / 1024
                
                # 表信息
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                stats["tables"] = [table[0] for table in tables]
                
                # 索引信息
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                indexes = cursor.fetchall()
                stats["indexes"] = [index[0] for index in indexes]
                
                return stats
                
        except Exception as e:
            logger.error(f"获取数据库统计失败 {db_path}: {e}")
            return {"db_path": db_path, "error": str(e)}
            
    def close_all_pools(self):
        """关闭所有连接池"""
        for db_path, pool in self.pools.items():
            try:
                pool.close_all()
                logger.info(f"连接池已关闭: {db_path}")
            except Exception as e:
                logger.error(f"关闭连接池失败 {db_path}: {e}")
                
        self.pools.clear()
        self.executor.shutdown(wait=True)


# 全局优化器实例
_optimizer = None

def get_sqlite_optimizer() -> SQLiteOptimizer:
    """获取全局SQLite优化器实例"""
    global _optimizer
    if _optimizer is None:
        _optimizer = SQLiteOptimizer()
    return _optimizer 