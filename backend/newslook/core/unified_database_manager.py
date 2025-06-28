#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一数据库管理器 - 解决路径不一致、连接泄漏、保存验证问题
核心修复：
1. 强制路径统一：所有模块使用统一数据库路径
2. 连接池化管理：自动连接回收和复用
3. 事务增强：防锁竞争和失败回滚
4. 保存验证：插入后立即校验
5. 错误熔断：自动重试和告警机制
"""

import os
import sqlite3
import logging
import time
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Generator
import hashlib
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """数据库配置"""
    base_dir: Path
    main_db_path: Path
    sources_dir: Path
    backups_dir: Path
    connection_timeout: int = 10
    max_retry_attempts: int = 3
    retry_backoff_factor: float = 0.2

class DataIntegrityError(Exception):
    """数据完整性错误"""
    pass

class DatabaseConnectionPool:
    """数据库连接池"""
    
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self._connections = []
        self._used_connections = set()
        self._lock = threading.Lock()
        
    def get_connection(self) -> sqlite3.Connection:
        """获取连接"""
        with self._lock:
            # 尝试重用现有连接
            for conn in self._connections[:]:
                if conn not in self._used_connections:
                    try:
                        # 测试连接是否有效
                        conn.execute("SELECT 1").fetchone()
                        self._used_connections.add(conn)
                        return conn
                    except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                        # 连接已失效，移除
                        self._connections.remove(conn)
                        try:
                            conn.close()
                        except:
                            pass
            
            # 创建新连接
            if len(self._connections) < self.max_connections:
                conn = sqlite3.connect(
                    self.db_path, 
                    check_same_thread=False, 
                    timeout=10
                )
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA synchronous = NORMAL")
                conn.row_factory = sqlite3.Row
                
                self._connections.append(conn)
                self._used_connections.add(conn)
                return conn
            
            raise Exception(f"连接池已满，无法创建新连接到 {self.db_path}")
    
    def release_connection(self, conn: sqlite3.Connection):
        """释放连接"""
        with self._lock:
            if conn in self._used_connections:
                self._used_connections.remove(conn)
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except:
                    pass
            self._connections.clear()
            self._used_connections.clear()

class UnifiedDatabaseManager:
    """统一数据库管理器"""
    
    def __init__(self):
        """初始化统一数据库管理器"""
        self._setup_paths()
        self._connection_pools: Dict[str, DatabaseConnectionPool] = {}
        self._lock = threading.Lock()
        self._setup_tables()
        
        logger.info(f"统一数据库管理器初始化完成，主数据库：{self.config.main_db_path}")
    
    def _setup_paths(self):
        """设置统一数据库路径"""
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent.parent
        
        # 强制统一路径配置
        base_dir = project_root / 'data' / 'db'
        main_db_path = base_dir / 'finance_news.db'
        sources_dir = base_dir / 'sources'
        backups_dir = base_dir / 'backups'
        
        # 确保目录存在
        base_dir.mkdir(parents=True, exist_ok=True)
        sources_dir.mkdir(exist_ok=True)
        backups_dir.mkdir(exist_ok=True)
        
        self.config = DatabaseConfig(
            base_dir=base_dir,
            main_db_path=main_db_path,
            sources_dir=sources_dir,
            backups_dir=backups_dir
        )
        
        logger.info(f"数据库路径统一化完成：{base_dir}")
    
    def get_unified_db_path(self) -> str:
        """获取统一主数据库路径"""
        return str(self.config.main_db_path)
    
    def get_source_db_path(self, source_name: str) -> str:
        """获取数据源数据库路径"""
        normalized_name = self._normalize_source_name(source_name)
        return str(self.config.sources_dir / f"{normalized_name}.db")
    
    def _normalize_source_name(self, source_name: str) -> str:
        """标准化数据源名称"""
        name_map = {
            '新浪财经': 'sina',
            '东方财富': 'eastmoney', 
            '网易财经': 'netease',
            '凤凰财经': 'ifeng',
            '腾讯财经': 'tencent',
            'sina': 'sina',
            'eastmoney': 'eastmoney',
            'netease': 'netease',
            'ifeng': 'ifeng',
            'tencent': 'tencent'
        }
        return name_map.get(source_name, source_name.lower().replace(' ', '_'))
    
    def _get_connection_pool(self, db_path: str) -> DatabaseConnectionPool:
        """获取连接池"""
        with self._lock:
            if db_path not in self._connection_pools:
                self._connection_pools[db_path] = DatabaseConnectionPool(db_path)
            return self._connection_pools[db_path]
    
    @contextmanager
    def get_connection(self, db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
        """上下文管理器方式获取数据库连接"""
        target_path = db_path or str(self.config.main_db_path)
        pool = self._get_connection_pool(target_path)
        conn = None
        
        try:
            conn = pool.get_connection()
            # 开始事务，防止锁竞争
            conn.execute("BEGIN IMMEDIATE")
            yield conn
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                    logger.warning(f"事务回滚: {e}")
                except:
                    pass
            raise
        else:
            if conn:
                try:
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logger.error(f"提交事务失败，已回滚: {e}")
                    raise
        finally:
            if conn:
                pool.release_connection(conn)
    
    def _setup_tables(self):
        """设置数据库表结构"""
        with self.get_connection() as conn:
            self._create_tables(conn)
    
    def _create_tables(self, conn: sqlite3.Connection):
        """创建数据库表"""
        cursor = conn.cursor()
        
        # 创建新闻表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_html TEXT,
                pub_time DATETIME NOT NULL,
                author TEXT,
                source TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                keywords TEXT,
                images TEXT,
                related_stocks TEXT,
                sentiment REAL,
                classification TEXT,
                category TEXT DEFAULT '财经',
                crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                summary TEXT,
                status INTEGER DEFAULT 0,
                
                CONSTRAINT news_url_unique UNIQUE (url)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_source_time ON news(source, pub_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_category ON news(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_pub_time ON news(pub_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_url ON news(url)')
        
        logger.info("数据库表结构初始化完成")
    
    def safe_execute_with_retry(self, operation_func, *args, **kwargs) -> bool:
        """带重试机制的安全执行"""
        for attempt in range(self.config.max_retry_attempts):
            try:
                return operation_func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < self.config.max_retry_attempts - 1:
                    wait_time = self.config.retry_backoff_factor * (2 ** attempt)
                    logger.warning(f"数据库锁定，等待 {wait_time}s 后重试 (尝试 {attempt + 1}/{self.config.max_retry_attempts})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"数据库操作失败: {e}")
                    return False
            except Exception as e:
                logger.error(f"操作执行失败: {e}", exc_info=True)
                return False
        
        logger.error(f"操作在 {self.config.max_retry_attempts} 次重试后仍然失败")
        return False
    
    def save_news(self, news_data: Dict[str, Any], to_source_db: bool = True) -> bool:
        """
        保存新闻数据
        
        Args:
            news_data: 新闻数据
            to_source_db: 是否保存到源数据库
            
        Returns:
            bool: 是否保存成功
        """
        return self.safe_execute_with_retry(self._save_news_impl, news_data, to_source_db)
    
    def _save_news_impl(self, news_data: Dict[str, Any], to_source_db: bool) -> bool:
        """保存新闻实现"""
        # 预处理数据
        processed_data = self._preprocess_news_data(news_data)
        if not processed_data:
            return False
        
        # 确定目标数据库
        if to_source_db and processed_data.get('source'):
            db_path = self.get_source_db_path(processed_data['source'])
        else:
            db_path = str(self.config.main_db_path)
        
        # 确保源数据库表结构存在
        if to_source_db:
            self._ensure_source_db_tables(db_path)
        
        try:
            with self.get_connection(db_path) as conn:
                cursor = conn.cursor()
                
                # 插入或替换新闻
                cursor.execute('''
                    INSERT OR REPLACE INTO news (
                        id, title, content, content_html, pub_time, author, 
                        source, url, keywords, images, related_stocks, 
                        sentiment, classification, category, summary, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    processed_data['id'],
                    processed_data['title'],
                    processed_data.get('content', ''),
                    processed_data.get('content_html', ''),
                    processed_data.get('pub_time'),
                    processed_data.get('author'),
                    processed_data.get('source', ''),
                    processed_data['url'],
                    json.dumps(processed_data.get('keywords', []), ensure_ascii=False),
                    json.dumps(processed_data.get('images', []), ensure_ascii=False),
                    json.dumps(processed_data.get('related_stocks', []), ensure_ascii=False),
                    processed_data.get('sentiment'),
                    processed_data.get('classification'),
                    processed_data.get('category', '财经'),
                    processed_data.get('summary'),
                    processed_data.get('status', 0)
                ))
                
                # 保存验证：插入后立即校验
                if not self._verify_save(conn, processed_data['id']):
                    raise DataIntegrityError(f"保存验证失败: {processed_data['id']}")
                
                logger.info(f"✅ 保存验证通过: {processed_data['title'][:50]}... -> {db_path}")
                return True
                
        except Exception as e:
            logger.error(f"❌ 保存失败: {e}, 标题: {processed_data.get('title', 'Unknown')}", exc_info=True)
            return False
    
    def _verify_save(self, conn: sqlite3.Connection, news_id: str) -> bool:
        """验证保存操作"""
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM news WHERE id = ?", (news_id,))
            count = cursor.fetchone()[0]
            verified = count > 0
            
            if verified:
                logger.debug(f"保存验证成功: {news_id}")
            else:
                logger.error(f"保存验证失败: {news_id}")
                
            return verified
        except Exception as e:
            logger.error(f"保存验证异常: {e}")
            return False
    
    def _preprocess_news_data(self, news_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """预处理新闻数据"""
        try:
            if not news_data.get('title') or not news_data.get('url'):
                logger.warning("新闻数据缺少必要字段 (title/url)")
                return None
            
            # 生成ID
            news_id = news_data.get('id')
            if not news_id:
                content_for_id = f"{news_data['title']}{news_data['url']}"
                news_id = hashlib.md5(content_for_id.encode('utf-8')).hexdigest()
            
            processed_data = news_data.copy()
            processed_data['id'] = news_id
            
            # 处理时间格式
            if 'pub_time' in processed_data and processed_data['pub_time']:
                if isinstance(processed_data['pub_time'], str):
                    try:
                        processed_data['pub_time'] = datetime.fromisoformat(processed_data['pub_time'].replace('Z', '+00:00'))
                    except:
                        processed_data['pub_time'] = datetime.now()
                elif not isinstance(processed_data['pub_time'], datetime):
                    processed_data['pub_time'] = datetime.now()
            else:
                processed_data['pub_time'] = datetime.now()
            
            return processed_data
            
        except Exception as e:
            logger.error(f"预处理新闻数据失败: {e}", exc_info=True)
            return None
    
    def _ensure_source_db_tables(self, db_path: str):
        """确保源数据库表结构存在"""
        try:
            with self.get_connection(db_path) as conn:
                self._create_tables(conn)
        except Exception as e:
            logger.error(f"创建源数据库表结构失败 {db_path}: {e}")
    
    def query_news(self, source: Optional[str] = None, limit: int = 100, 
                   days: Optional[int] = None, use_all_sources: bool = False) -> List[Dict[str, Any]]:
        """查询新闻"""
        try:
            if use_all_sources:
                return self._query_all_sources(limit, days)
            
            db_path = self.get_source_db_path(source) if source else str(self.config.main_db_path)
            
            with self.get_connection(db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM news"
                params = []
                
                if days:
                    query += " WHERE pub_time >= datetime('now', ?, 'localtime')"
                    params.append(f'-{days} days')
                
                query += " ORDER BY pub_time DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                results = []
                
                for row in cursor.fetchall():
                    news_item = dict(row)
                    # 反序列化JSON字段
                    for json_field in ['keywords', 'images', 'related_stocks']:
                        if news_item.get(json_field):
                            try:
                                news_item[json_field] = json.loads(news_item[json_field])
                            except:
                                news_item[json_field] = []
                    results.append(news_item)
                
                return results
                
        except Exception as e:
            logger.error(f"查询新闻失败: {e}", exc_info=True)
            return []
    
    def _query_all_sources(self, limit: int, days: Optional[int]) -> List[Dict[str, Any]]:
        """查询所有数据源"""
        all_news = []
        
        # 查询主数据库
        all_news.extend(self.query_news(None, limit, days, False))
        
        # 查询所有源数据库
        if self.config.sources_dir.exists():
            for db_file in self.config.sources_dir.glob('*.db'):
                source_name = db_file.stem
                try:
                    source_news = self.query_news(source_name, limit, days, False)
                    all_news.extend(source_news)
                except Exception as e:
                    logger.warning(f"查询源数据库 {source_name} 失败: {e}")
        
        # 按时间排序并限制数量
        all_news.sort(key=lambda x: x.get('pub_time', ''), reverse=True)
        return all_news[:limit]
    
    def migrate_database_files(self) -> Dict[str, List[str]]:
        """迁移旧位置的数据库文件到统一位置"""
        report = {
            'migrated': [],
            'skipped': [],
            'errors': []
        }
        
        # 检查data根目录下的数据库文件
        data_root = self.config.base_dir.parent
        
        for db_file in data_root.glob('*.db'):
            if db_file.parent == data_root:  # 只处理直接在data目录下的文件
                target_path = self.config.base_dir / db_file.name
                
                try:
                    if not target_path.exists() or db_file.stat().st_mtime > target_path.stat().st_mtime:
                        import shutil
                        shutil.copy2(str(db_file), str(target_path))
                        report['migrated'].append(f"{db_file} -> {target_path}")
                        logger.info(f"迁移数据库文件: {db_file.name}")
                    else:
                        report['skipped'].append(f"{db_file} (目标文件已存在且更新)")
                        
                except Exception as e:
                    report['errors'].append(f"{db_file}: {e}")
                    logger.error(f"迁移数据库文件失败 {db_file}: {e}")
        
        if report['migrated']:
            logger.info(f"成功迁移 {len(report['migrated'])} 个数据库文件到统一位置")
        
        return report
    
    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {
            'main_db': {},
            'source_dbs': {},
            'total_news': 0
        }
        
        # 主数据库统计
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM news")
                main_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT source) FROM news")
                main_sources = cursor.fetchone()[0]
                
                stats['main_db'] = {
                    'path': str(self.config.main_db_path),
                    'count': main_count,
                    'sources': main_sources
                }
                stats['total_news'] += main_count
                
        except Exception as e:
            logger.error(f"获取主数据库统计失败: {e}")
        
        # 源数据库统计
        for db_file in self.config.sources_dir.glob('*.db'):
            source_name = db_file.stem
            try:
                with self.get_connection(str(db_file)) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM news")
                    count = cursor.fetchone()[0]
                    
                    stats['source_dbs'][source_name] = {
                        'path': str(db_file),
                        'count': count
                    }
                    stats['total_news'] += count
                    
            except Exception as e:
                logger.error(f"获取源数据库统计失败 {source_name}: {e}")
        
        return stats
    
    def close_all_connections(self):
        """关闭所有连接池"""
        with self._lock:
            for pool in self._connection_pools.values():
                pool.close_all()
            self._connection_pools.clear()
        
        logger.info("所有数据库连接已关闭")


# 全局实例
_unified_db_manager = None

def get_unified_database_manager() -> UnifiedDatabaseManager:
    """获取统一数据库管理器实例（单例）"""
    global _unified_db_manager
    if _unified_db_manager is None:
        _unified_db_manager = UnifiedDatabaseManager()
    return _unified_db_manager