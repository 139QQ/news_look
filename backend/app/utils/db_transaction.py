#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库事务和并发控制工具
提供更健壮的数据库操作支持，包括事务管理、重试机制和并发控制
"""

import os
import time
import random
import sqlite3
import logging
import threading
from functools import wraps
from contextlib import contextmanager
from datetime import datetime

# 获取日志记录器
logger = logging.getLogger("db_transaction")

# 数据库锁字典，用于控制多线程/进程访问
DB_LOCKS = {}
LOCKS_LOCK = threading.RLock()  # 控制对DB_LOCKS本身的访问

def get_db_lock(db_path):
    """
    获取特定数据库的锁
    
    Args:
        db_path: 数据库路径
        
    Returns:
        threading.RLock: 数据库锁
    """
    with LOCKS_LOCK:
        if db_path not in DB_LOCKS:
            DB_LOCKS[db_path] = threading.RLock()
        return DB_LOCKS[db_path]

@contextmanager
def db_transaction(db_path, isolation_level="IMMEDIATE", max_retries=3, retry_delay=0.5):
    """
    数据库事务上下文管理器
    
    Args:
        db_path: 数据库路径
        isolation_level: 事务隔离级别
        max_retries: 最大重试次数
        retry_delay: 重试延迟时间
        
    Yields:
        tuple: (connection, cursor) 数据库连接和游标
    """
    db_lock = get_db_lock(db_path)
    
    # 确保数据库目录存在
    try:
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"创建数据库目录失败: {str(e)}")
    
    conn = None
    attempts = 0
    
    with db_lock:  # 获取数据库锁
        while attempts < max_retries:
            try:
                conn = sqlite3.connect(db_path, isolation_level=isolation_level, timeout=20)
                conn.row_factory = sqlite3.Row  # 使用Row工厂，返回类字典对象
                cursor = conn.cursor()
                
                # 启用外键约束
                cursor.execute("PRAGMA foreign_keys = ON")
                
                # 执行一些性能优化设置
                cursor.execute("PRAGMA journal_mode = WAL")  # 启用WAL模式
                cursor.execute("PRAGMA synchronous = NORMAL")  # 设置同步模式为NORMAL
                cursor.execute("PRAGMA cache_size = 10000")  # 增加缓存大小
                cursor.execute("PRAGMA temp_store = MEMORY")  # 临时表存储在内存中
                
                yield conn, cursor
                
                # 如果没有异常发生，则提交事务
                conn.commit()
                break  # 成功执行，跳出循环
                
            except sqlite3.OperationalError as e:
                # 处理数据库锁或忙碌错误
                if any(err in str(e).lower() for err in ['database is locked', 'busy']):
                    attempts += 1
                    if attempts < max_retries:
                        # 随机延迟，避免多个线程同时重试
                        jitter = random.uniform(0, 0.5)
                        wait_time = retry_delay * (2 ** (attempts - 1)) + jitter
                        logger.warning(f"数据库忙，等待 {wait_time:.2f} 秒后重试 ({attempts}/{max_retries})")
                        time.sleep(wait_time)
                        if conn:
                            try:
                                conn.close()
                            except:
                                pass
                            conn = None
                    else:
                        logger.error(f"数据库忙，重试次数超过最大值: {str(e)}")
                        if conn:
                            try:
                                conn.rollback()
                            except:
                                pass
                        raise
                else:
                    # 其他操作错误
                    logger.error(f"数据库操作错误: {str(e)}")
                    if conn:
                        try:
                            conn.rollback()
                        except:
                            pass
                    raise
                
            except Exception as e:
                # 处理其他异常
                logger.error(f"数据库事务异常: {str(e)}")
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                raise
            
            finally:
                # 在最终尝试后，如果连接仍然存在，则关闭它
                if attempts == max_retries and conn:
                    try:
                        conn.close()
                    except:
                        pass
        
        # 确保连接被关闭
        if conn:
            try:
                conn.close()
            except:
                pass

def with_db_transaction(db_path=None, isolation_level="IMMEDIATE", max_retries=3):
    """
    数据库事务装饰器
    
    Args:
        db_path: 数据库路径，如果为None则从第一个参数中获取
        isolation_level: 事务隔离级别
        max_retries: 最大重试次数
        
    Returns:
        function: 装饰器函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 确定数据库路径
            actual_db_path = db_path
            if actual_db_path is None:
                # 如果没有提供db_path，尝试从参数中获取
                # 首先检查self.db_path
                if args and hasattr(args[0], 'db_path') and args[0].db_path:
                    actual_db_path = args[0].db_path
                # 然后检查kwargs['db_path']
                elif 'db_path' in kwargs:
                    actual_db_path = kwargs['db_path']
                else:
                    raise ValueError("未能确定数据库路径，请提供db_path参数")
            
            with db_transaction(actual_db_path, isolation_level, max_retries) as (conn, cursor):
                # 将连接和游标添加到kwargs
                kwargs['conn'] = conn
                kwargs['cursor'] = cursor
                return func(*args, **kwargs)
        return wrapper
    return decorator

class TransactionalDBManager:
    """支持事务和并发控制的数据库管理器"""
    
    def __init__(self, db_path, table_schemas=None):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库路径
            table_schemas: 表结构定义字典，键为表名，值为创建表的SQL语句
        """
        self.db_path = db_path
        self.table_schemas = table_schemas or {}
        
        # 初始化数据库，确保表结构存在
        self.init_db()
    
    def init_db(self):
        """初始化数据库，创建必要的表"""
        try:
            with db_transaction(self.db_path) as (conn, cursor):
                # 创建表
                for table_name, schema in self.table_schemas.items():
                    try:
                        cursor.execute(schema)
                    except sqlite3.Error as e:
                        logger.error(f"创建表 {table_name} 失败: {str(e)}")
                        raise
                        
                logger.debug(f"数据库 {self.db_path} 初始化成功")
        except Exception as e:
            logger.error(f"初始化数据库失败: {str(e)}")
            raise
    
    @with_db_transaction()
    def save_news(self, news_data, conn=None, cursor=None):
        """
        保存新闻数据到数据库
        
        Args:
            news_data: 新闻数据字典
            conn: 数据库连接（由装饰器提供）
            cursor: 数据库游标（由装饰器提供）
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保必要字段存在
            required_fields = ['id', 'title', 'content', 'pub_time', 'source', 'url']
            for field in required_fields:
                if field not in news_data:
                    logger.warning(f"新闻数据缺少必要字段: {field}")
                    return False
            
            # 检查新闻是否已存在
            cursor.execute("SELECT id FROM news WHERE id = ?", (news_data['id'],))
            if cursor.fetchone():
                logger.debug(f"新闻已存在: {news_data['title']}")
                return True
            
            # 构建INSERT语句
            fields = [
                'id', 'title', 'content', 'pub_time', 'author', 'source', 'url', 
                'keywords', 'images', 'related_stocks', 'sentiment', 'category', 'crawl_time'
            ]
            
            # 准备数据
            values = []
            for field in fields:
                if field in news_data:
                    # 如果是列表类型，转换为逗号分隔的字符串
                    if isinstance(news_data[field], list):
                        values.append(','.join(news_data[field]))
                    else:
                        values.append(news_data[field])
                else:
                    # 对于缺失的字段设置默认值
                    if field == 'crawl_time':
                        values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    elif field == 'sentiment':
                        values.append('中性')
                    else:
                        values.append('')
            
            # 执行INSERT语句
            placeholders = ', '.join(['?' for _ in fields])
            sql = f"INSERT INTO news ({', '.join(fields)}) VALUES ({placeholders})"
            cursor.execute(sql, values)
            
            # 处理关键词
            if 'keywords' in news_data and news_data['keywords']:
                keywords = news_data['keywords']
                if isinstance(keywords, str):
                    keywords = keywords.split(',')
                
                for keyword in keywords:
                    if not keyword:
                        continue
                    
                    # 检查关键词是否已存在
                    cursor.execute("SELECT id, count FROM keywords WHERE keyword = ?", (keyword,))
                    row = cursor.fetchone()
                    
                    if row:
                        # 更新已存在的关键词
                        keyword_id = row['id']
                        count = row['count'] + 1
                        cursor.execute(
                            "UPDATE keywords SET count = ?, last_updated = ? WHERE id = ?", 
                            (count, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), keyword_id)
                        )
                    else:
                        # 插入新关键词
                        cursor.execute(
                            "INSERT INTO keywords (keyword, last_updated) VALUES (?, ?)", 
                            (keyword, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                        )
                        cursor.execute("SELECT last_insert_rowid()")
                        keyword_id = cursor.fetchone()[0]
                    
                    # 插入新闻-关键词关系
                    cursor.execute(
                        "INSERT OR IGNORE INTO news_keywords (news_id, keyword_id) VALUES (?, ?)", 
                        (news_data['id'], keyword_id)
                    )
            
            # 处理相关股票
            if 'related_stocks' in news_data and news_data['related_stocks']:
                stocks = news_data['related_stocks']
                if isinstance(stocks, str):
                    stocks = stocks.split(',')
                
                for stock in stocks:
                    if not stock:
                        continue
                    
                    # 解析股票代码和名称
                    parts = stock.split(':')
                    if len(parts) == 2:
                        code, name = parts
                    else:
                        code = stock
                        name = stock
                    
                    # 检查股票是否已存在
                    cursor.execute("SELECT code, count FROM stocks WHERE code = ?", (code,))
                    row = cursor.fetchone()
                    
                    if row:
                        # 更新已存在的股票
                        count = 1 if row['count'] is None else row['count'] + 1
                        cursor.execute(
                            "UPDATE stocks SET count = ?, last_updated = ? WHERE code = ?", 
                            (count, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), code)
                        )
                    else:
                        # 插入新股票
                        cursor.execute(
                            "INSERT INTO stocks (code, name, last_updated) VALUES (?, ?, ?)", 
                            (code, name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                        )
                    
                    # 插入新闻-股票关系
                    cursor.execute(
                        "INSERT OR IGNORE INTO news_stocks (news_id, stock_code) VALUES (?, ?)", 
                        (news_data['id'], code)
                    )
            
            logger.info(f"新闻保存成功: {news_data['title']}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"保存新闻失败: {str(e)}")
            raise
    
    @with_db_transaction()
    def batch_save_news(self, news_list, conn=None, cursor=None):
        """
        批量保存新闻数据到数据库
        
        Args:
            news_list: 新闻数据列表
            conn: 数据库连接（由装饰器提供）
            cursor: 数据库游标（由装饰器提供）
            
        Returns:
            int: 成功保存的新闻数量
        """
        saved_count = 0
        for news_data in news_list:
            try:
                if self.save_news(news_data, conn=conn, cursor=cursor):
                    saved_count += 1
            except Exception as e:
                logger.error(f"保存新闻失败: {news_data.get('title', 'unknown')}, 错误: {str(e)}")
        
        return saved_count
    
    @contextmanager
    def get_transaction(self, isolation_level="IMMEDIATE", max_retries=3):
        """获取数据库事务上下文"""
        with db_transaction(self.db_path, isolation_level, max_retries) as (conn, cursor):
            yield conn, cursor
    
    def execute_with_retry(self, sql, params=None, max_retries=3, retry_delay=0.5):
        """
        执行SQL语句，支持重试
        
        Args:
            sql: SQL语句
            params: SQL参数
            max_retries: 最大重试次数
            retry_delay: 重试延迟时间
            
        Returns:
            cursor: 数据库游标
        """
        with self.get_transaction(max_retries=max_retries) as (conn, cursor):
            cursor.execute(sql, params or ())
            return cursor
    
    def get_news_count(self):
        """
        获取数据库中的新闻数量
        
        Returns:
            int: 新闻数量
        """
        try:
            cursor = self.execute_with_retry("SELECT COUNT(*) FROM news")
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"获取新闻数量失败: {str(e)}")
            return 0

# 默认表结构定义
DEFAULT_TABLE_SCHEMAS = {
    'news': '''
        CREATE TABLE IF NOT EXISTS news (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            pub_time TEXT,
            author TEXT,
            source TEXT,
            url TEXT UNIQUE,
            keywords TEXT,
            images TEXT,
            related_stocks TEXT,
            sentiment TEXT,
            category TEXT,
            crawl_time TEXT,
            classification TEXT
        )
    ''',
    'keywords': '''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE,
            count INTEGER DEFAULT 1,
            last_updated TEXT
        )
    ''',
    'news_keywords': '''
        CREATE TABLE IF NOT EXISTS news_keywords (
            news_id TEXT,
            keyword_id INTEGER,
            PRIMARY KEY (news_id, keyword_id),
            FOREIGN KEY (news_id) REFERENCES news(id) ON DELETE CASCADE,
            FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
        )
    ''',
    'stocks': '''
        CREATE TABLE IF NOT EXISTS stocks (
            code TEXT PRIMARY KEY,
            name TEXT,
            count INTEGER DEFAULT 1,
            last_updated TEXT
        )
    ''',
    'news_stocks': '''
        CREATE TABLE IF NOT EXISTS news_stocks (
            news_id TEXT,
            stock_code TEXT,
            PRIMARY KEY (news_id, stock_code),
            FOREIGN KEY (news_id) REFERENCES news(id) ON DELETE CASCADE,
            FOREIGN KEY (stock_code) REFERENCES stocks(code) ON DELETE CASCADE
        )
    '''
}

# 创建默认的事务数据库管理器
def create_db_manager(db_path, table_schemas=None):
    """
    创建事务数据库管理器
    
    Args:
        db_path: 数据库路径
        table_schemas: 表结构定义，如果为None则使用默认表结构
        
    Returns:
        TransactionalDBManager: 数据库管理器实例
    """
    if table_schemas is None:
        table_schemas = DEFAULT_TABLE_SCHEMAS
    return TransactionalDBManager(db_path, table_schemas) 