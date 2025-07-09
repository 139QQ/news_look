#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SQLite数据库管理模块
"""

import os
import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import hashlib
import shutil

logger = logging.getLogger(__name__)

class SQLiteManager:
    """SQLite数据库管理类"""
    
    def __init__(self, db_path: str):
        """
        初始化数据库管理器 - 🔧 强制路径统一化
        
        Args:
            db_path: 数据库路径
        """
        # 🔧 修复：强制使用统一路径管理器
        from backend.newslook.core.database_path_manager import get_database_path_manager
        
        path_manager = get_database_path_manager()
        # 强制使用统一路径，忽略传入的db_path
        self.db_path = path_manager.get_main_db_path()
        self.base_dir = str(path_manager.db_dir)
        # 🔧 修复：不再使用sources分离目录
        self.backups_dir = str(path_manager.backup_dir)
        
        # 只创建backups目录，不再创建sources分离目录
        os.makedirs(self.backups_dir, exist_ok=True)
        
        logger.info(f"🔧 SQLiteManager强制使用统一路径: {self.db_path}")
        
        # Main connection
        self.conn: Optional[sqlite3.Connection] = None 
        # Dictionary to hold connections to source-specific DBs
        self.source_connections: Dict[str, sqlite3.Connection] = {} 
        
        # Establish main connection and create tables on init
        self._connect() # Establishes self.conn
        if self.conn:
            self.create_tables(self.conn) # Create tables for main connection
        else:
            logger.error(f"Failed to establish main DB connection on init to {self.db_path}. Tables not created.")

    def __enter__(self):
        """上下文管理器入口方法"""
        if not self.conn:
            self._connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出方法"""
        self.close_all_connections()
        return False  # 不处理异常
    
    def _connect(self, db_file: Optional[str] = None) -> Optional[sqlite3.Connection]:
        """
        连接到数据库
        
        Returns:
            sqlite3.Connection: 数据库连接
        """
        target_db_path = db_file if db_file else self.db_path
        is_main_connection = (target_db_path == self.db_path)

        # Avoid reconnecting if already connected (for the main connection)
        if is_main_connection and self.conn:
            # Basic check if connection is still alive (optional)
            try:
                 self.conn.execute("SELECT 1").fetchone()
                 # logger.debug(f"Main connection to {target_db_path} is active.")
                 return self.conn
            except (sqlite3.ProgrammingError, sqlite3.OperationalError) as e:
                 logger.warning(f"Main connection seems closed ({e}). Reconnecting...")
                 self.conn = None # Force reconnect

        try:
            db_dir = os.path.dirname(target_db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                logger.info(f"Created directory for DB: {db_dir}")
            
            logger.debug(f"Attempting to connect to: {target_db_path}")
            conn = sqlite3.connect(target_db_path, check_same_thread=False, timeout=10)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.row_factory = sqlite3.Row
            logger.info(f"Successfully connected to: {target_db_path}")
            
            if is_main_connection:
                self.conn = conn # Store the main connection
            
            return conn
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database {target_db_path}: {e}", exc_info=True)
            if is_main_connection:
                self.conn = None # Ensure main conn is None if connect failed
            return None

    def get_connection(self, db_path: Optional[str] = None) -> Optional[sqlite3.Connection]:
        """Gets or creates a connection. Manages main and source connections."""
        target_db_path = os.path.abspath(db_path) if db_path else self.db_path
        is_main = (target_db_path == self.db_path)
        source_name = None
        # 🔧 修复：移除sources_dir依赖，统一使用主数据库
        if not is_main:
             source_name = os.path.splitext(os.path.basename(target_db_path))[0]

        # 1. Check main connection cache
        if is_main and self.conn:
            try: # Quick check if alive
                self.conn.execute("SELECT 1")
                return self.conn
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                 logger.warning("Main connection cache was stale. Reconnecting...")
                 self.conn = None # Clear stale connection

        # 2. Check source connection cache
        if source_name and source_name in self.source_connections:
             cached_conn = self.source_connections[source_name]
             try: # Quick check if alive
                  cached_conn.execute("SELECT 1")
                  return cached_conn
             except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                  logger.warning(f"Source connection cache for '{source_name}' was stale. Reconnecting...")
                  self.source_connections.pop(source_name, None)
                  # Proceed to connect
        
        # 3. Establish new connection if not cached or stale
        new_conn = self._connect(db_file=target_db_path)
        if new_conn:
            # Ensure tables exist for the new connection
            self.create_tables_for_connection(new_conn)
            # Store in the appropriate cache
            if is_main:
                self.conn = new_conn
            elif source_name:
                self.source_connections[source_name] = new_conn
            else: # Should not happen if path is absolute, but handle anyway
                 logger.warning(f"Connection established to {target_db_path}, but couldn't determine if main or source.")
        return new_conn
    
    def create_tables(self, conn: sqlite3.Connection) -> None:
        """创建必要的数据库表"""
        try:
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
            
            conn.commit()
            logger.info("数据库表初始化完成")
            
        except sqlite3.Error as e:
            logger.error(f"创建数据库表失败: {str(e)}")
            raise
    
    def create_tables_for_connection(self, conn: sqlite3.Connection) -> None:
        """
        For a given database connection, create all necessary table structures
        (news, keywords, news_keywords, stocks, news_stocks).
        Typically used for source-specific databases.
        
        Args:
            conn: sqlite3.Connection object
        """
        cursor = None  # Initialize cursor to None
        try:
            cursor = conn.cursor()
            db_name_for_log = conn.db_name if hasattr(conn, 'db_name') else 'unknown_db'
            
            # 1. Create news Table (identical to create_tables())
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    content_html TEXT,
                    pub_time DATETIME,
                    author TEXT,
                    source TEXT,
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
            logger.info(f"Ensured 'news' table exists on connection to {db_name_for_log}.")

            # 2. Create keywords Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logger.info(f"Ensured 'keywords' table exists on connection to {db_name_for_log}.")

            # 3. Create news_keywords Junction Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_keywords (
                    news_id TEXT NOT NULL,
                    keyword_id INTEGER NOT NULL,
                    relevance REAL, 
                    PRIMARY KEY (news_id, keyword_id),
                    FOREIGN KEY (news_id) REFERENCES news (id) ON DELETE CASCADE,
                    FOREIGN KEY (keyword_id) REFERENCES keywords (id) ON DELETE CASCADE
                )
            ''')
            logger.info(f"Ensured 'news_keywords' table exists on connection to {db_name_for_log}.")
            
            # 4. Create stocks Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT UNIQUE NOT NULL, -- e.g., "600519.SH" or "00700.HK"
                    stock_name TEXT,             -- e.g., "贵州茅台" or "腾讯控股"
                    market TEXT,                 -- e.g., "SH", "SZ", "HK", "US"
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logger.info(f"Ensured 'stocks' table exists on connection to {db_name_for_log}.")
            
            # 5. Create news_stocks Junction Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_stocks (
                    news_id TEXT NOT NULL,
                    stock_id INTEGER NOT NULL,
                    relevance REAL, 
                    PRIMARY KEY (news_id, stock_id),
                    FOREIGN KEY (news_id) REFERENCES news (id) ON DELETE CASCADE,
                    FOREIGN KEY (stock_id) REFERENCES stocks (id) ON DELETE CASCADE
                )
            ''')
            logger.info(f"Ensured 'news_stocks' table exists on connection to {db_name_for_log}.")

            # Apply table structure upgrades after creation
            self._upgrade_news_table_if_needed(cursor) 
            self._upgrade_keywords_table_if_needed(cursor)
            self._upgrade_stocks_table_if_needed(cursor)
            # Note: Junction tables (news_keywords, news_stocks) rarely need schema changes 
            # unless foreign keys or primary keys structure changes, which is less common.
            
            conn.commit()
            logger.info(f"Successfully created/verified all table structures on connection to {db_name_for_log}.")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to create tables on connection to {db_name_for_log}: {e}")
            if conn:
                conn.rollback()
        finally:
            if cursor:
                cursor.close()
    
    def _upgrade_news_table_if_needed(self, cursor: sqlite3.Cursor) -> None:
        """
        检查并升级 news 表结构，添加缺失的列
        
        Args:
            cursor: 数据库游标
        """
        try:
            # 获取news表的列信息
            cursor.execute("PRAGMA table_info(news)")
            columns = {row[1]: row for row in cursor.fetchall()}
            
            # 定义期望的列及其添加语句
            # (字段名, SQL类型, 默认值 - 如果有的话)
            expected_news_columns = {
                'content_html': "TEXT",
                'classification': "TEXT",
                'summary': "TEXT",
                'status': "INTEGER DEFAULT 0",
                # 'crawl_time' should exist due to table definition, but check anyway
                'crawl_time': "DATETIME DEFAULT CURRENT_TIMESTAMP", 
                # 'category' should exist due to table definition
                'category': "TEXT DEFAULT '财经'",
                 # 'sentiment' should exist
                'sentiment': "REAL",
                 # 'author' should exist
                'author': "TEXT",
                 # 'source' should exist
                'source': "TEXT", # Ensure this is NOT NULL if required by application logic elsewhere
                 # 'url' should exist and be unique
                'url': "TEXT UNIQUE NOT NULL",
                 # 'keywords' should exist
                'keywords': "TEXT",
                 # 'images' should exist
                'images': "TEXT",
                 # 'related_stocks' should exist
                'related_stocks': "TEXT"
            }

            for col_name, col_type_with_default in expected_news_columns.items():
                if col_name not in columns:
                    logger.info(f"升级 'news' 表: 添加列 '{col_name}'")
                    cursor.execute(f"ALTER TABLE news ADD COLUMN {col_name} {col_type_with_default}")
            
            # 确保关键的 NOT NULL 约束仍然存在或被正确设置（如果ALTER TABLE不能直接修改）
            # 对于 SQLite, ALTER TABLE 不能直接添加 NOT NULL约束到现有列而不提供默认值
            # 通常在CREATE TABLE时定义。如果需要修改，可能需要更复杂的数据迁移。
            # 这里主要关注添加缺失列。

            # self.conn.commit() # Commit should be handled by the calling method (e.g., create_tables_for_connection)
            logger.debug(f"'news' 表结构检查/升级完成 (cursor: {cursor})")
        except sqlite3.Error as e:
            logger.error(f"升级 'news' 表失败: {str(e)}")
            # self.conn.rollback() # Rollback should be handled by the calling method

    def _upgrade_keywords_table_if_needed(self, cursor: sqlite3.Cursor) -> None:
        """Checks and upgrades the keywords table schema if necessary."""
        try:
            cursor.execute("PRAGMA table_info(keywords)")
            columns = {row[1]: row for row in cursor.fetchall()}
            
            # Example: Ensure 'frequency' column exists (it should from CREATE TABLE)
            if 'frequency' not in columns:
                logger.info("升级 'keywords' 表: 添加列 'frequency' INTEGER DEFAULT 1")
                cursor.execute("ALTER TABLE keywords ADD COLUMN frequency INTEGER DEFAULT 1")

            # Example: Ensure 'last_updated' column exists
            if 'last_updated' not in columns:
                logger.info("升级 'keywords' 表: 添加列 'last_updated' DATETIME DEFAULT CURRENT_TIMESTAMP")
                cursor.execute("ALTER TABLE keywords ADD COLUMN last_updated DATETIME DEFAULT CURRENT_TIMESTAMP")
            
            # Add other checks for keywords table if needed in the future
            logger.debug(f"'keywords' 表结构检查/升级完成 (cursor: {cursor})")
        except sqlite3.Error as e:
            logger.error(f"升级 'keywords' 表失败: {str(e)}")

    def _upgrade_stocks_table_if_needed(self, cursor: sqlite3.Cursor) -> None:
        """Checks and upgrades the stocks table schema if necessary."""
        try:
            cursor.execute("PRAGMA table_info(stocks)")
            columns = {row[1]: row for row in cursor.fetchall()}

            # Example: Ensure 'stock_code' is UNIQUE NOT NULL (defined in CREATE TABLE)
            # Example: Ensure 'market' column exists
            if 'market' not in columns:
                logger.info("升级 'stocks' 表: 添加列 'market' TEXT")
                cursor.execute("ALTER TABLE stocks ADD COLUMN market TEXT")
            
            if 'last_updated' not in columns:
                logger.info("升级 'stocks' 表: 添加列 'last_updated' DATETIME DEFAULT CURRENT_TIMESTAMP")
                cursor.execute("ALTER TABLE stocks ADD COLUMN last_updated DATETIME DEFAULT CURRENT_TIMESTAMP")

            # Add other checks for stocks table if needed in the future
            logger.debug(f"'stocks' 表结构检查/升级完成 (cursor: {cursor})")
        except sqlite3.Error as e:
            logger.error(f"升级 'stocks' 表失败: {str(e)}")

    def save_news(self, news_data: Dict[str, Any], use_source_db: bool = False) -> bool:
        """
        保存新闻数据到数据库
        
        Args:
            news_data: 新闻数据字典
            use_source_db: 是否使用来源数据库
            
        Returns:
            bool: 是否保存成功
        """
        target_conn: Optional[sqlite3.Connection] = None
        source_name_for_conn_management: Optional[str] = None

        if use_source_db:
            source = news_data.get('source')
            if not source:
                logger.error("save_news: Cannot use source DB if 'source' is not in news_data.")
                return False
            source_db_path = self.get_source_db_path(source)
            target_conn = self.get_connection(db_path=source_db_path)
            source_name_for_conn_management = source
        else:
            target_conn = self.get_connection() # Gets self.conn or establishes it
        
        if not target_conn:
            logger.error(f"save_news: Failed to get a database connection. News not saved: {news_data.get('title')}")
            return False
        
        try:
            # preprocessed_item = self._preprocess_news_data(news_data, for_source_db=use_source_db)
            # The above line was from a previous state. _preprocess_news_data should be robust.
            preprocessed_item = self._preprocess_news_data(news_data) # Assuming one preprocess fits all for now
            if not preprocessed_item.get('id'):
                 logger.error(f"News item ID missing after preprocessing. Cannot save. Title: {news_data.get('title')}")
                 return False

            self.insert_news(preprocessed_item, target_conn) # insert_news takes the connection
            return True
        except Exception as e:
            logger.error(f"save_news: Error saving news '{news_data.get('title')}': {e}", exc_info=True)
            return False
        finally:
            if use_source_db and target_conn and target_conn != self.conn:
                # Close if it was a source-specific connection different from the main one
                self.close_connection(conn=target_conn, source_name=source_name_for_conn_management)
    
    def _preprocess_news_data(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        预处理新闻数据
        
        Args:
            news_data: 原始新闻数据
            
        Returns:
            Dict[str, Any]: 处理后的新闻数据
        """
        # 创建副本以避免修改原始数据
        processed = news_data.copy()
        
        # 1. 确保id存在，如果不存在则根据url生成
        if 'id' not in processed or not processed['id']:
            if 'url' in processed and processed['url']:
                processed['id'] = hashlib.md5(processed['url'].encode('utf-8')).hexdigest()
                logger.debug(f"[preprocess] 新闻ID缺失, 根据URL生成ID: {processed['id']} for URL: {processed['url']}")
            else:
                # 如果连URL都没有，则无法生成ID，后续的必需字段检查会处理这个问题
                logger.warning("[preprocess] 新闻ID和URL均缺失, 无法生成ID.")

        # 2. 确保时间字段格式正确或有默认值
        if 'pub_time' not in processed or not processed['pub_time']:
            # 尝试从其他常见时间字段获取，如果都没有则设为当前时间
            # (此部分可根据实际数据源的字段名进一步扩展)
            processed['pub_time'] = processed.get('publish_time', processed.get('time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        if 'crawl_time' not in processed or not processed['crawl_time']:
            processed['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 3. 处理可能的JSON字段 (keywords, images, related_stocks)
        for field in ['images', 'related_stocks', 'keywords']:
            if field in processed and isinstance(processed[field], (list, dict)):
                try:
                    processed[field] = json.dumps(processed[field], ensure_ascii=False)
                except TypeError as e:
                    logger.warning(f"[preprocess] JSON序列化失败 for field {field}: {e}. 值: {processed[field]}. 将设置为空字符串.")
                    processed[field] = ""
            elif field in processed and processed[field] is None: # 如果显式传入None，转为空字符串或保持None，根据数据库定义
                 processed[field] = "" # 或者 None，取决于表结构是否允许NULL

        # 4. 处理情感值 (sentiment)
        if 'sentiment' in processed:
            if isinstance(processed['sentiment'], str):
                sentiment_map = {
                    '积极': 1.0,
                    '中性': 0.0,
                    '消极': -1.0
                }
                # 如果字符串不在map中，也默认为中性0.0
                processed['sentiment'] = sentiment_map.get(processed['sentiment'], 0.0) 
            elif not isinstance(processed['sentiment'], (float, int)):
                 logger.warning(f"[preprocess] 无效的情感值类型: {processed['sentiment']}. 将设置为0.0")
                 processed['sentiment'] = 0.0 # 如果类型不对，也默认为0.0
        
        # 5. 设置其他字段的默认值 (包括新字段 summary, status)
        # 注意: author 和 source 通常由爬虫本身根据来源设定，这里可以作为最终的保障
        defaults = {
            'author': processed.get('source', '未知'), # 如果爬虫没给author，尝试使用source
            'source': processed.get('source', '未知来源'), # 万一连source都没有
            'category': '财经',
            'classification': '', # 默认为空字符串
            'content_html': '',   # 默认为空字符串
            'keywords': '',       # 如果之前未处理或处理失败，默认为空字符串
            'images': '',         # 同上
            'related_stocks': '', # 同上
            'summary': '',        # 新字段，默认为空字符串
            'status': 0,          # 新字段，默认为0
            'sentiment': 0.0      # 如果上面处理后 sentiment 仍不存在，则默认为0.0
        }
        
        for field, default_value in defaults.items():
            if field not in processed or processed[field] is None: # 检查 None 或不存在
                processed[field] = default_value
        
        # 确保 title, content, url, source, pub_time 不为 None (后续 save_news 中有更严格的检查)
        # 但这里可以提前将 None 转为空字符串，避免某些数据库操作对 None 的问题
        for critical_field in ['title', 'content', 'url', 'source', 'pub_time']:
            if critical_field in processed and processed[critical_field] is None:
                logger.warning(f"[preprocess] 关键字段 {critical_field} 为 None, 将转换为空字符串.")
                processed[critical_field] = ""

        logger.debug(f"[preprocess] 数据预处理完成: {processed.get('title')}")
        return processed
    
    def save_to_source_db(self, news_data):
        """
        🔧 修复：保存到统一数据库目录，移除sources分离
        
        Args:
            news_data: 新闻数据字典
            
        Returns:
            bool: 是否保存成功
        """
        if 'source' not in news_data or not news_data['source']:
            logger.warning(f"保存失败: 新闻数据缺少source字段, 标题: {news_data.get('title', 'Unknown')}")
            return False
        
        # 🔧 修复：使用统一路径管理器获取数据库路径
        from backend.newslook.core.database_path_manager import get_database_path_manager
        
        path_manager = get_database_path_manager()
        original_source = news_data['source']
        
        # 直接使用主数据库，实现路径统一化
        source_db_path = path_manager.get_main_db_path()
        
        logger.info(f"🔧 强制使用统一数据库路径: {source_db_path}")
        
        try:
            # 🔧 修复：使用统一数据库管理器进行保存验证
            from backend.newslook.core.unified_database_manager import get_unified_database_manager
            
            unified_manager = get_unified_database_manager()
            success = unified_manager.save_news(news_data, to_source_db=False)
            
            if success:
                logger.info(f"✅ 保存验证通过: {news_data.get('title', 'Unknown')[:50]}...")
            else:
                logger.warning(f"❌ 保存失败: {news_data.get('title', 'Unknown')[:50]}...")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 保存到统一数据库时发生错误: {str(e)}, 标题: {news_data.get('title', 'Unknown')}")
            return False
    
    def backup_database(self, source=None):
        """
        备份数据库
        
        Args:
            source: 要备份的来源名称，如果为None则备份主数据库
            
        Returns:
            str: 备份文件路径
        """
        # 🔧 修复：统一使用主数据库路径
        db_path = self.db_path
        
        # 生成备份文件名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        backup_filename = f"{source or 'main'}_{timestamp}.db.bak"
        backup_path = os.path.join(self.backups_dir, backup_filename)
        
        try:
            # 关闭连接以确保数据已写入磁盘
            if db_path in self.source_connections:
                self.source_connections[db_path].close()
                del self.source_connections[db_path]
            
            # 复制数据库文件
            shutil.copy2(db_path, backup_path)
            logger.info(f"成功备份数据库 {db_path} 到 {backup_path}")
            
            # 重新连接
            if db_path == self.db_path:
                self.conn = self._connect()
                self.source_connections[db_path] = self.conn
            
            return backup_path
        except Exception as e:
            logger.error(f"备份数据库失败: {str(e)}")
            return None
    
    def restore_database(self, backup_path, target_source=None):
        """
        从备份恢复数据库
        
        Args:
            backup_path: 备份文件路径
            target_source: 目标来源名称，如果为None则恢复到主数据库
            
        Returns:
            bool: 是否恢复成功
        """
        # 🔧 修复：统一使用主数据库路径
        target_db_path = self.db_path
        
        try:
            # 关闭连接
            if target_db_path in self.source_connections:
                self.source_connections[target_db_path].close()
                del self.source_connections[target_db_path]
            
            # 复制备份文件到目标位置
            shutil.copy2(backup_path, target_db_path)
            logger.info(f"成功从备份 {backup_path} 恢复数据库 {target_db_path}")
            
            # 重新连接
            if target_db_path == self.db_path:
                self.conn = self._connect()
                self.source_connections[target_db_path] = self.conn
            
            return True
        except Exception as e:
            logger.error(f"恢复数据库失败: {str(e)}")
            return False
    
    def list_backups(self, source=None):
        """
        列出备份文件
        
        Args:
            source: 来源名称，如果为None则列出所有备份
            
        Returns:
            list: 备份信息列表，每项包含 {path, timestamp, source, size}
        """
        import glob
        
        # 查找所有备份文件
        backup_pattern = os.path.join(self.backups_dir, '*.db.bak')
        backup_files = glob.glob(backup_pattern)
        
        # 解析备份信息
        backups = []
        for path in backup_files:
            filename = os.path.basename(path)
            parts = filename.split('_')
            
            if len(parts) >= 2:
                backup_source = parts[0]
                
                # 如果指定了来源，只返回匹配的备份
                if source and backup_source != source:
                    continue
                
                # 解析时间戳
                timestamp_str = parts[1].split('.')[0]
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                    size = os.path.getsize(path)
                    
                    backups.append({
                        'path': path,
                        'timestamp': timestamp,
                        'source': backup_source,
                        'size': size
                    })
                except ValueError:
                    logger.warning(f"无法解析备份时间戳: {filename}")
        
        # 按时间戳排序，最新的在前
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        return backups
    
    def sync_to_main_db(self, source):
        """
        将指定来源的数据同步到主数据库
        
        Args:
            source: 来源名称
            
        Returns:
            int: 同步的新闻数量
        """
        # 🔧 修复：同步功能已废弃，统一数据库不需要同步
        logger.info(f"🔧 同步功能已废弃: 所有数据已统一存储在主数据库")
        return 0
        
        # 🔧 修复：同步功能的实现已移除，因为统一数据库不需要同步
    
    def get_available_sources(self):
        """
        🔧 修复：获取统一数据库中的数据源
        
        Returns:
            list: 数据源列表
        """
        # 🔧 修复：从主数据库查询所有数据源
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT source FROM news WHERE source IS NOT NULL AND source != ''")
            sources = [row[0] for row in cursor.fetchall()]
            return sorted(sources)
        except Exception as e:
            logger.error(f"获取数据源失败: {e}")
            return []
    
    def close(self):
        """关闭数据库连接"""
        for path, conn in list(self.source_connections.items()):
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"关闭数据库连接失败: {str(e)}")
        
        # 清空连接字典
        self.source_connections = {}
        self.conn = None
    
    def __del__(self):
        """Ensure connections are closed when the manager is garbage collected."""
        logger.debug("SQLiteManager __del__ called. Attempting to close all connections.")
        self.close_all_connections()

    def insert_news(self, news_data, conn):
        """
        向数据库插入或替换新闻数据 (使用特定连接)
        
        Args:
            news_data: 新闻数据字典
            conn: 数据库连接
            
        Returns:
            bool: 是否成功插入或替换
        """
        processed_news_data = None # Define outside try
        try:
            cursor = conn.cursor()
            
            # 预处理数据
            processed_news_data = self._preprocess_news_data(news_data.copy())

            logger.debug(f"[insert_news] Attempting INSERT OR REPLACE for ID: {processed_news_data.get('id')}")
            # logger.debug(f"[insert_news] Data Dict: {processed_news_data}") # Optional: Log full dict

            # 准备数据元组 (ensure order matches VALUES clause)
            data_tuple = (
                processed_news_data.get('id', ''),
                processed_news_data.get('title', ''),
                processed_news_data.get('content', ''),
                processed_news_data.get('content_html', ''), 
                processed_news_data.get('pub_time', ''),
                processed_news_data.get('author', ''),
                processed_news_data.get('source', ''),
                processed_news_data.get('url', ''),
                processed_news_data.get('keywords', ''), # Expects JSON string here if preprocessing worked
                processed_news_data.get('images', ''), # Expects JSON string
                processed_news_data.get('related_stocks', ''), # Expects JSON string
                processed_news_data.get('sentiment', 0.0),
                processed_news_data.get('classification', ''),
                processed_news_data.get('category', '财经'), 
                processed_news_data.get('crawl_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                processed_news_data.get('summary', ''),
                processed_news_data.get('status', 0)
            )
            
            # Log the tuple right before execution
            logger.debug(f"[insert_news] Executing INSERT OR REPLACE with tuple: {data_tuple}")
            
            # 执行插入或替换
            cursor.execute('''
                INSERT OR REPLACE INTO news (
                    id, title, content, content_html, pub_time, author, source,
                    url, keywords, images, related_stocks, sentiment,
                    classification, category, crawl_time, summary, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data_tuple)
            
            conn.commit()
            logger.info(f"[insert_news] Successfully inserted/replaced news ID: {processed_news_data.get('id')}, Title: {processed_news_data.get('title')[:30]}...")
            return True
            
        except sqlite3.Error as e:
            db_file_path_for_log = "Unknown DB"
            try: db_file_path_for_log = conn.execute('PRAGMA database_list;').fetchone()[2]
            except Exception: pass
            logger.error(f"[insert_news] SQLite Error during INSERT/REPLACE ({db_file_path_for_log}): {e}. Title: {processed_news_data.get('title', 'N/A') if processed_news_data else news_data.get('title', 'N/A')}", exc_info=True) # Add exc_info
            try: conn.rollback()
            except Exception as rb_err: logger.error(f"Rollback failed: {rb_err}")
            return False
        except Exception as e: # Catch other potential errors (e.g., in preprocessing)
             db_file_path_for_log = "Unknown DB"
             try: db_file_path_for_log = conn.execute('PRAGMA database_list;').fetchone()[2]
             except Exception: pass
             logger.error(f"[insert_news] Unexpected Error during insert/replace ({db_file_path_for_log}): {e}. Title: {processed_news_data.get('title', 'N/A') if processed_news_data else news_data.get('title', 'N/A')}", exc_info=True)
             try: conn.rollback()
             except Exception as rb_err: logger.error(f"Rollback failed: {rb_err}")
             return False

    def query_news(self, page=1, per_page=20, category=None, source=None, 
                   keyword=None, sort_by='pub_time', order='desc', days=None,
                   start_date=None, end_date=None, limit=None):
        """
        查询新闻数据
        
        Args:
            page: 页码，从1开始
            per_page: 每页数量
            category: 分类过滤
            source: 来源过滤
            keyword: 关键词过滤
            sort_by: 排序字段
            order: 排序方式，'asc'为升序，'desc'为降序
            days: 最近几天的数据，如果为None则不限制
            start_date: 开始日期，格式为'YYYY-MM-DD'
            end_date: 结束日期，格式为'YYYY-MM-DD'
            limit: 限制返回的结果数量
            
        Returns:
            list: 新闻数据列表
        """
        try:
            # 构建SQL查询
            query = "SELECT * FROM news WHERE 1=1"
            params = []
            
            # 添加过滤条件
            if category:
                query += " AND category = ?"
                params.append(category)
                
            if source:
                query += " AND source = ?"
                params.append(source)
                
            if keyword:
                query += " AND (title LIKE ? OR content LIKE ? OR keywords LIKE ?)"
                keyword_param = f"%{keyword}%"
                params.extend([keyword_param, keyword_param, keyword_param])
            
            # 处理日期条件
            if start_date and end_date:
                query += " AND pub_time BETWEEN ? AND ?"
                params.append(f"{start_date} 00:00:00")
                params.append(f"{end_date} 23:59:59")
            elif days:
                # 计算日期范围
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                query += " AND pub_time >= ?"
                params.append(start_date.strftime('%Y-%m-%d 00:00:00'))
            
            # 添加排序
            valid_sort_fields = ['id', 'title', 'pub_time', 'source', 'category', 'crawl_time']
            if sort_by in valid_sort_fields:
                order_dir = "DESC" if order.lower() == 'desc' else "ASC"
                query += f" ORDER BY {sort_by} {order_dir}"
            else:
                query += " ORDER BY pub_time DESC"  # 默认排序
            
            # 应用分页
            if limit:
                # 如果直接指定了limit
                query += f" LIMIT {int(limit)}"
            else:
                # 使用分页参数
                offset = (page - 1) * per_page
                query += f" LIMIT {int(per_page)} OFFSET {int(offset)}"
            
            # 执行查询
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # 转换为字典列表
            result = []
            for row in rows:
                news_dict = dict(row)
                result.append(news_dict)
                
            return result
            
        except sqlite3.Error as e:
            logger.error(f"查询新闻失败: {str(e)}")
            return []
    
    def get_news_count(self, category=None, source=None, keyword=None, days=None, 
                      start_date=None, end_date=None):
        """
        获取符合条件的新闻数量
        
        Args:
            category: 分类过滤
            source: 来源过滤
            keyword: 关键词过滤
            days: 最近几天的数据，如果为None则不限制
            start_date: 开始日期，格式为'YYYY-MM-DD'
            end_date: 结束日期，格式为'YYYY-MM-DD'
            
        Returns:
            int: 新闻数量
        """
        try:
            # 构建SQL查询
            query = "SELECT COUNT(*) as count FROM news WHERE 1=1"
            params = []
            
            # 添加过滤条件
            if category:
                query += " AND category = ?"
                params.append(category)
                
            if source:
                query += " AND source = ?"
                params.append(source)
                
            if keyword:
                query += " AND (title LIKE ? OR content LIKE ? OR keywords LIKE ?)"
                keyword_param = f"%{keyword}%"
                params.extend([keyword_param, keyword_param, keyword_param])
            
            # 处理日期条件
            if start_date and end_date:
                query += " AND pub_time BETWEEN ? AND ?"
                params.append(f"{start_date} 00:00:00")
                params.append(f"{end_date} 23:59:59")
            elif days:
                # 计算日期范围
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                query += " AND pub_time >= ?"
                params.append(start_date.strftime('%Y-%m-%d 00:00:00'))
            
            # 执行查询
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            return row['count'] if row else 0
            
        except sqlite3.Error as e:
            logger.error(f"获取新闻数量失败: {str(e)}")
            return 0
    
    def get_sources(self):
        """
        获取所有新闻来源
        
        Returns:
            list: 来源列表
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT source FROM news WHERE source IS NOT NULL AND source != ''")
            sources = [row['source'] for row in cursor.fetchall()]
            return sources
        except sqlite3.Error as e:
            logger.error(f"获取新闻来源失败: {str(e)}")
            return []
    
    def get_categories(self):
        """
        获取所有新闻分类
        
        Returns:
            list: 分类列表
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM news WHERE category IS NOT NULL AND category != ''")
            categories = [row['category'] for row in cursor.fetchall()]
            return categories
        except sqlite3.Error as e:
            logger.error(f"获取新闻分类失败: {str(e)}")
            return []
    
    def get_news_by_id(self, news_id: str, source: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过ID获取新闻，可以指定来源数据库"""
        db_to_query = self.get_source_db_path(source) if source else self.db_path
        conn = self.get_connection(db_path=db_to_query)
        if not conn:
            logger.error(f"get_news_by_id: Failed to get connection for news_id '{news_id}' (source: {source}).")
            return None
        
        news_item = None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM news WHERE id = ?", (news_id,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                news_item = dict(zip(columns, row))
                # Deserialize JSON fields if necessary (handled by _deserialize_news_item)
                news_item = self._deserialize_news_item(news_item)
        except sqlite3.Error as e:
            logger.error(f"获取新闻失败 (ID: {news_id}, Source: {source}): {e}", exc_info=True)
        finally:
            if source and conn != self.conn: # Close if it was a source-specific, potentially temporary connection
                self.close_connection(conn=conn, source_name=source)
        return news_item

    def get_source_db_path(self, source_name: str) -> str:
        """🔧 修复：返回统一数据库路径"""
        # 🔧 修复：所有数据源都使用统一的主数据库
        return self.db_path

    def execute_query(self, query, params=None):
        """
        执行SQL查询
        
        Args:
            query: SQL查询字符串
            params: 查询参数
            
        Returns:
            bool: 是否成功执行
        """
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"执行SQL查询失败: {str(e)}")
            self.conn.rollback()
            return False

    def get_news(self, source: Optional[str] = None, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取新闻列表
        
        Args:
            source: 新闻来源
            days: 最近几天的新闻
            
        Returns:
            List[Dict[str, Any]]: 新闻列表
        """
        try:
            cursor = self.conn.cursor()
            
            query = "SELECT * FROM news"
            params = []
            
            conditions = []
            if source:
                conditions.append("source = ?")
                params.append(source)
            
            if days:
                conditions.append("pub_time >= datetime('now', ?, 'localtime')")
                params.append(f'-{days} days')
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY pub_time DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"获取新闻失败: {str(e)}")
            return []

    def close_connection(self, conn: Optional[sqlite3.Connection] = None, source_name: Optional[str] = None):
        """Closes a specific database connection or the main connection if conn is None and source_name is None."""
        conn_to_close: Optional[sqlite3.Connection] = None
        description = "unknown connection"

        if source_name and source_name in self.source_connections:
            conn_to_close = self.source_connections.pop(source_name, None)
            description = f"source DB '{source_name}'"
        elif conn: # Explicit connection object passed
            conn_to_close = conn
            if conn == self.conn:
                description = "main DB (explicitly passed)"
                self.conn = None # Clear attribute if it was the main connection
            else:
                # Check if it was a known source connection passed directly
                for src, c_obj in list(self.source_connections.items()):
                    if c_obj == conn:
                        description = f"source DB '{src}' (explicitly passed)"
                        self.source_connections.pop(src, None)
                        break
        elif self.conn: # Default to the main connection if no other specifier
            conn_to_close = self.conn
            self.conn = None # Clear the main connection attribute
            description = "main DB (default)"
        
        if conn_to_close:
            try:
                conn_to_close.close()
                logger.info(f"SQLiteManager: Database connection closed for {description}.")
            except Exception as e:
                logger.error(f"SQLiteManager: Error closing database connection for {description}: {e}")

    def close_all_connections(self):
        """Closes all managed database connections (main and all source connections)."""
        logger.info("SQLiteManager: Closing all managed database connections.")
        # Close all source connections 
        source_keys = list(self.source_connections.keys())
        logger.debug(f"Closing {len(source_keys)} source connections...")
        for source_name in source_keys:
            conn_obj = self.source_connections.pop(source_name, None)
            if conn_obj:
                try:
                    conn_obj.close()
                    logger.info(f"SQLiteManager: Closed connection for source DB '{source_name}'.")
                except Exception as e:
                    logger.error(f"SQLiteManager: Error closing connection for source DB '{source_name}': {e}")
        self.source_connections.clear()
        
        # Close the main connection if it's active
        if self.conn:
            logger.debug("Closing main connection...")
            try:
                self.conn.close()
                logger.info("SQLiteManager: Closed main database connection (self.conn).")
                self.conn = None # Explicitly set to None after closing
            except Exception as e:
                logger.error(f"SQLiteManager: Error closing main database connection (self.conn): {e}")
        else:
            logger.debug("SQLiteManager: Main connection (self.conn) was not active or already closed.")
        logger.info("SQLiteManager: All database connection closing attempts finished.") 

    def _deserialize_news_item(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to deserialize JSON string fields in a news item dictionary."""
        # Ensure json is imported at the top of the file: import json
        if not news_item: return news_item
        json_fields = ['tags', 'images', 'videos', 'related_stocks', 'keywords'] 
        for field in json_fields:
            if field in news_item and isinstance(news_item[field], str):
                try:
                    loaded_json = json.loads(news_item[field])
                    news_item[field] = loaded_json if isinstance(loaded_json, list) else [loaded_json]
                except json.JSONDecodeError as e:
                    logger.warning(f"_deserialize_news_item: Failed to decode JSON for field '{field}' in news ID {news_item.get('id')}. Value: \"{news_item[field][:100]}...\". Error: {e}")
                    news_item[field] = []
            elif field in news_item and news_item[field] is None:
                 news_item[field] = []
            elif field not in news_item:
                 news_item[field] = []
        return news_item 
