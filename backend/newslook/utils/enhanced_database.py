import sqlite3
import threading
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import queue
import os
from contextlib import contextmanager
from backend.newslook.core.database_path_manager import get_database_path_manager, discover_all_databases

logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """数据库连接池"""
    
    def __init__(self, db_path: str, pool_size: int = 10, timeout: float = 30.0):
        """
        初始化连接池
        
        Args:
            db_path: 数据库路径
            pool_size: 连接池大小
            timeout: 连接超时时间（秒）
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self.pool = queue.Queue(maxsize=pool_size)
        self.active_connections = 0
        self.lock = threading.Lock()
        self._closed = False
        
        # 预创建连接
        self._init_pool()
    
    def _init_pool(self):
        """初始化连接池"""
        try:
            for _ in range(self.pool_size):
                conn = self._create_connection()
                if conn:
                    self.pool.put(conn)
                    self.active_connections += 1
            logger.info(f"[DB] 数据库连接池初始化完成，连接数: {self.active_connections}/{self.pool_size}")
        except Exception as e:
            logger.error(f"[DB] 连接池初始化失败: {str(e)}")
    
    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """创建新的数据库连接"""
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=False,
                isolation_level=None  # 自动提交模式
            )
            
            # 设置连接参数
            conn.row_factory = sqlite3.Row
            
            # 设置性能优化参数
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB
            
            return conn
        except Exception as e:
            logger.error(f"[DB] 创建数据库连接失败: {str(e)}")
            return None
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = None
        try:
            if self._closed:
                raise Exception("连接池已关闭")
            
            # 尝试从池中获取连接
            try:
                conn = self.pool.get(timeout=5.0)  # 5秒超时
                
                # 测试连接是否有效
                conn.execute("SELECT 1")
                yield conn
                
            except queue.Empty:
                # 连接池为空，创建新连接
                logger.warning("[DB] 连接池为空，创建新连接")
                conn = self._create_connection()
                if conn:
                    yield conn
                else:
                    raise Exception("无法创建数据库连接")
            
            except sqlite3.Error as e:
                # 连接无效，重新创建
                logger.warning(f"[DB] 连接无效，重新创建: {str(e)}")
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                conn = self._create_connection()
                if conn:
                    yield conn
                else:
                    raise Exception("无法重新创建数据库连接")
                    
        except Exception as e:
            logger.error(f"[DB] 获取数据库连接失败: {str(e)}")
            raise
            
        finally:
            # 归还连接到池中
            if conn and not self._closed:
                try:
                    # 检查连接是否仍然有效
                    conn.execute("SELECT 1")
                    self.pool.put(conn, timeout=1.0)
                except:
                    # 连接已损坏，关闭它
                    try:
                        conn.close()
                    except:
                        pass
    
    def close(self):
        """关闭连接池"""
        self._closed = True
        
        # 关闭所有连接
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
                self.active_connections -= 1
            except:
                break
        
        logger.info(f"[DB] 连接池已关闭")


class EnhancedNewsDatabase:
    """增强的新闻数据库管理器"""
    
    def __init__(self, db_paths: List[str] = None, pool_size: int = 5, timeout: float = 30.0):
        """
        初始化数据库管理器
        
        Args:
            db_paths: 数据库路径列表，如果为None则自动发现
            pool_size: 每个数据库的连接池大小
            timeout: 查询超时时间（秒）
        """
        self.timeout = timeout
        self.pools: Dict[str, DatabaseConnectionPool] = {}
        
        # 如果没有指定数据库路径，自动发现
        if db_paths is None:
            db_paths = self._discover_databases()
        
        # 为每个数据库创建连接池
        for db_path in db_paths:
            if os.path.exists(db_path):
                try:
                    pool = DatabaseConnectionPool(db_path, pool_size, timeout)
                    self.pools[db_path] = pool
                    logger.info(f"[DB] 为数据库 {db_path} 创建连接池成功")
                except Exception as e:
                    logger.error(f"[DB] 为数据库 {db_path} 创建连接池失败: {str(e)}")
        
        if not self.pools:
            logger.warning("[DB] 没有找到有效的数据库文件")
    
    def _discover_databases(self) -> List[str]:
        """自动发现数据库文件"""
        # 使用统一的数据库路径管理器
        db_path_manager = get_database_path_manager()
        
        # 先尝试迁移旧数据库文件
        try:
            migrated = db_path_manager.migrate_old_databases()
            if migrated:
                logger.info(f"[DB] 成功迁移 {len(migrated)} 个数据库文件到标准位置")
        except Exception as e:
            logger.warning(f"[DB] 数据库迁移过程中出现警告: {e}")
        
        # 发现所有数据库文件
        db_paths = discover_all_databases()
        
        if db_paths:
            logger.info(f"[DB] 发现 {len(db_paths)} 个数据库文件:")
            for db_path in db_paths:
                logger.info(f"[DB]   - {db_path}")
        else:
            logger.warning("[DB] 未发现任何数据库文件")
        
        return db_paths
        
        # 以下代码保留作为备份，但现在使用上面的统一管理
        # 搜索data目录中的.db文件
        data_dir = "data"
        if os.path.exists(data_dir):
            for file in os.listdir(data_dir):
                if file.endswith('.db') and not file.endswith('.bak'):
                    db_path = os.path.join(data_dir, file)
                    abs_path = os.path.abspath(db_path)
                    if abs_path not in db_paths:
                        db_paths.append(abs_path)
                        logger.info(f"[DB] 发现数据库文件: {abs_path}")
        
        # 搜索data/db目录中的.db文件
        data_db_dir = "data/db"
        if os.path.exists(data_db_dir):
            for file in os.listdir(data_db_dir):
                if file.endswith('.db') and not file.endswith('.bak'):
                    db_path = os.path.join(data_db_dir, file)
                    abs_path = os.path.abspath(db_path)
                    if abs_path not in db_paths:
                        db_paths.append(abs_path)
                        logger.info(f"[DB] 发现数据库文件: {abs_path}")
        
        logger.info(f"[DB] 总共发现 {len(db_paths)} 个数据库文件")
        return db_paths
    
    def get_news_count(self, keyword: str = None, days: int = None, 
                      source: str = None, category: str = None) -> int:
        """
        获取新闻数量
        
        Args:
            keyword: 关键词
            days: 最近天数
            source: 来源
            category: 分类
            
        Returns:
            int: 新闻数量
        """
        total_count = 0
        counted_urls = set()
        
        for db_path, pool in self.pools.items():
            try:
                with pool.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 检查表是否存在
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                    if not cursor.fetchone():
                        continue
                    
                    # 构建查询条件
                    conditions = []
                    params = []
                    
                    if source:
                        conditions.append("source = ?")
                        params.append(source)
                    
                    if category:
                        conditions.append("category = ?")
                        params.append(category)
                    
                    if keyword:
                        conditions.append("(title LIKE ? OR content LIKE ?)")
                        params.extend([f"%{keyword}%", f"%{keyword}%"])
                    
                    if days:
                        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                        conditions.append("pub_time >= ?")
                        params.append(start_date)
                    
                    # 构建SQL
                    sql = "SELECT url FROM news"
                    if conditions:
                        sql += " WHERE " + " AND ".join(conditions)
                    
                    # 执行查询
                    cursor.execute(sql, params)
                    
                    # 统计去重后的URL
                    for row in cursor.fetchall():
                        url = row['url'] if row['url'] else f"no_url_{total_count}"
                        if url not in counted_urls:
                            counted_urls.add(url)
                            total_count += 1
                            
            except Exception as e:
                logger.error(f"[DB] 查询数据库 {db_path} 失败: {str(e)}")
        
        logger.info(f"[DB] 查询结果: 总数={total_count}, 来源={source}, 关键词={keyword}")
        return total_count
    
    def query_news(self, keyword: str = None, days: int = None, 
                  source: str = None, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        查询新闻列表
        
        Args:
            keyword: 关键词
            days: 最近天数
            source: 来源
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            List[Dict]: 新闻列表
        """
        all_news = []
        seen_urls = set()
        
        for db_path, pool in self.pools.items():
            try:
                with pool.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 检查表是否存在
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                    if not cursor.fetchone():
                        continue
                    
                    # 构建查询条件
                    conditions = []
                    params = []
                    
                    if source:
                        conditions.append("source = ?")
                        params.append(source)
                    
                    if keyword:
                        conditions.append("(title LIKE ? OR content LIKE ?)")
                        params.extend([f"%{keyword}%", f"%{keyword}%"])
                    
                    if days:
                        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                        conditions.append("pub_time >= ?")
                        params.append(start_date)
                    
                    # 构建SQL
                    sql = "SELECT * FROM news"
                    if conditions:
                        sql += " WHERE " + " AND ".join(conditions)
                    sql += " ORDER BY pub_time DESC"
                    
                    # 执行查询
                    cursor.execute(sql, params)
                    
                    # 收集新闻并去重
                    for row in cursor.fetchall():
                        news = dict(row)
                        url = news.get('url', '')
                        
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_news.append(news)
                            
            except Exception as e:
                logger.error(f"[DB] 查询数据库 {db_path} 失败: {str(e)}")
        
        # 按发布时间排序
        all_news.sort(key=lambda x: x.get('pub_time', ''), reverse=True)
        
        # 应用分页
        start_idx = offset
        end_idx = offset + limit
        result = all_news[start_idx:end_idx]
        
        logger.info(f"[DB] 查询新闻: 总数={len(all_news)}, 返回={len(result)}")
        return result
    
    def get_sources(self) -> List[str]:
        """获取所有新闻来源"""
        sources = set()
        
        for db_path, pool in self.pools.items():
            try:
                with pool.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 检查表是否存在
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                    if not cursor.fetchone():
                        continue
                    
                    cursor.execute("SELECT DISTINCT source FROM news WHERE source IS NOT NULL")
                    for row in cursor.fetchall():
                        if row['source']:
                            sources.add(row['source'])
                            
            except Exception as e:
                logger.error(f"[DB] 获取来源失败 {db_path}: {str(e)}")
        
        result = sorted(list(sources))
        logger.info(f"[DB] 获取来源: {result}")
        return result
    
    def get_news_by_id(self, news_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取新闻详情"""
        for db_path, pool in self.pools.items():
            try:
                with pool.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT * FROM news WHERE id = ?", (news_id,))
                    row = cursor.fetchone()
                    
                    if row:
                        logger.info(f"[DB] 找到新闻: {news_id}")
                        return dict(row)
                        
            except Exception as e:
                logger.error(f"[DB] 获取新闻详情失败 {db_path}: {str(e)}")
        
        logger.warning(f"[DB] 未找到新闻: {news_id}")
        return None
    
    def close(self):
        """关闭所有连接池"""
        for pool in self.pools.values():
            pool.close()
        self.pools.clear()
        logger.info("[DB] 所有数据库连接池已关闭") 