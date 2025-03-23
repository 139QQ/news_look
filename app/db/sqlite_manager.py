#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SQLite数据库管理模块
"""

import os
import sqlite3
import logging
from datetime import datetime

class SQLiteManager:
    """SQLite数据库管理类"""
    
    def __init__(self, db_path):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        
        # 确保数据库目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # 创建数据库连接
        self.conn = self.connect()
        
        # 创建表
        self.create_tables()
    
    def connect(self):
        """
        连接到数据库
        
        Returns:
            sqlite3.Connection: 数据库连接
        """
        try:
            conn = sqlite3.connect(self.db_path)
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys = ON")
            # 设置行工厂，返回字典
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logging.error(f"连接数据库失败: {str(e)}")
            raise
    
    def create_tables(self):
        """创建数据库表"""
        try:
            cursor = self.conn.cursor()
            
            # 创建新闻表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    content_html TEXT,
                    pub_time TEXT,
                    author TEXT,
                    source TEXT,
                    url TEXT UNIQUE,
                    keywords TEXT,
                    images TEXT,
                    related_stocks TEXT,
                    sentiment TEXT,
                    classification TEXT,
                    category TEXT,
                    crawl_time TEXT
                )
            ''')
            
            # 创建关键词表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE,
                    count INTEGER DEFAULT 1,
                    last_updated TEXT
                )
            ''')
            
            # 创建新闻-关键词关系表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_keywords (
                    news_id TEXT,
                    keyword_id INTEGER,
                    PRIMARY KEY (news_id, keyword_id),
                    FOREIGN KEY (news_id) REFERENCES news(id) ON DELETE CASCADE,
                    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
                )
            ''')
            
            # 创建股票表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stocks (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    count INTEGER DEFAULT 1,
                    last_updated TEXT
                )
            ''')
            
            # 创建新闻-股票关系表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_stocks (
                    news_id TEXT,
                    stock_code TEXT,
                    PRIMARY KEY (news_id, stock_code),
                    FOREIGN KEY (news_id) REFERENCES news(id) ON DELETE CASCADE,
                    FOREIGN KEY (stock_code) REFERENCES stocks(code) ON DELETE CASCADE
                )
            ''')
            
            self.conn.commit()
            logging.debug("数据库表创建成功")
            
            # 检查并升级表结构
            self.upgrade_tables()
        except sqlite3.Error as e:
            logging.error(f"创建数据库表失败: {str(e)}")
            self.conn.rollback()
            raise
    
    def upgrade_tables(self):
        """升级数据库表结构，添加缺失的列"""
        try:
            cursor = self.conn.cursor()
            
            # 获取news表的列信息
            cursor.execute("PRAGMA table_info(news)")
            columns = {row[1]: row for row in cursor.fetchall()}
            
            # 检查是否缺少content_html列
            if 'content_html' not in columns:
                logging.info("升级数据库：添加content_html列到news表")
                cursor.execute("ALTER TABLE news ADD COLUMN content_html TEXT")
            
            # 检查是否缺少classification列
            if 'classification' not in columns:
                logging.info("升级数据库：添加classification列到news表")
                cursor.execute("ALTER TABLE news ADD COLUMN classification TEXT")
            
            self.conn.commit()
            logging.debug("数据库表升级完成")
        except sqlite3.Error as e:
            logging.error(f"升级数据库表失败: {str(e)}")
            self.conn.rollback()
    
    def save_news(self, news_data):
        """
        保存新闻数据
        
        Args:
            news_data: 新闻数据字典
            
        Returns:
            bool: 是否保存成功
        """
        try:
            cursor = self.conn.cursor()
            
            # 检查新闻是否已存在
            cursor.execute("SELECT id FROM news WHERE id = ?", (news_data['id'],))
            if cursor.fetchone():
                logging.debug(f"新闻已存在: {news_data['title']}")
                return False
            
            # 处理关键词（如果有）
            keywords_str = ""
            if 'keywords' in news_data and news_data['keywords']:
                if isinstance(news_data['keywords'], list):
                    keywords_str = ",".join(news_data['keywords'])
                else:
                    keywords_str = str(news_data['keywords'])
            
            # 处理图片（如果有）
            images_str = ""
            if 'images' in news_data and news_data['images']:
                if isinstance(news_data['images'], list):
                    images_str = ",".join(news_data['images'])
                else:
                    images_str = str(news_data['images'])
            
            # 处理相关股票（如果有）
            related_stocks_str = ""
            if 'related_stocks' in news_data and news_data['related_stocks']:
                if isinstance(news_data['related_stocks'], list):
                    related_stocks_str = ",".join(news_data['related_stocks'])
                else:
                    related_stocks_str = str(news_data['related_stocks'])
            
            # 设置爬取时间
            crawl_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 插入新闻数据
            cursor.execute("""
                INSERT INTO news (
                    id, title, content, pub_time, author, source, url, 
                    keywords, images, related_stocks, sentiment, category, crawl_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                news_data['id'], news_data['title'], news_data.get('content', ''), 
                news_data.get('pub_time', ''), news_data.get('author', ''), 
                news_data.get('source', ''), news_data.get('url', ''), keywords_str, 
                images_str, related_stocks_str, news_data.get('sentiment', ''), 
                news_data.get('category', ''), crawl_time
            ))
            
            # 处理关键词
            if 'keywords' in news_data and news_data['keywords']:
                keywords = news_data['keywords']
                if isinstance(keywords, str):
                    keywords = keywords.split(',')
                
                for keyword in keywords:
                    keyword = keyword.strip()
                    if not keyword:
                        continue
                    
                    # 检查关键词是否已存在
                    cursor.execute("SELECT id, count FROM keywords WHERE keyword = ?", (keyword,))
                    row = cursor.fetchone()
                    
                    if row:
                        # 更新已存在的关键词
                        keyword_id = row[0]
                        count = row[1] + 1
                        cursor.execute(
                            "UPDATE keywords SET count = ?, last_updated = ? WHERE id = ?", 
                            (count, crawl_time, keyword_id)
                        )
                    else:
                        # 插入新关键词
                        cursor.execute(
                            "INSERT INTO keywords (keyword, last_updated) VALUES (?, ?)", 
                            (keyword, crawl_time)
                        )
                        keyword_id = cursor.lastrowid
                    
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
                        count = row[1] + 1
                        cursor.execute(
                            "UPDATE stocks SET count = ?, last_updated = ? WHERE code = ?", 
                            (count, crawl_time, code)
                        )
                    else:
                        # 插入新股票
                        cursor.execute(
                            "INSERT INTO stocks (code, name, last_updated) VALUES (?, ?, ?)", 
                            (code, name, crawl_time)
                        )
                    
                    # 插入新闻-股票关系
                    cursor.execute(
                        "INSERT OR IGNORE INTO news_stocks (news_id, stock_code) VALUES (?, ?)", 
                        (news_data['id'], code)
                    )
            
            self.conn.commit()
            logging.info(f"新闻保存成功: {news_data['title']}")
            return True
        except sqlite3.Error as e:
            logging.error(f"保存新闻失败: {str(e)}")
            self.conn.rollback()
            return False
    
    # 添加insert_news方法作为save_news的别名，兼容爬虫接口
    def insert_news(self, news_data):
        """
        插入新闻数据（save_news的别名）
        
        Args:
            news_data: 新闻数据字典
            
        Returns:
            bool: 是否保存成功
        """
        return self.save_news(news_data)
    
    def get_news(self, news_id):
        """
        获取指定ID的新闻
        
        Args:
            news_id: 新闻ID
            
        Returns:
            dict: 新闻数据
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM news WHERE id = ?", (news_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # 将行转换为字典
            news = dict(row)
            
            # 获取关键词
            cursor.execute("""
                SELECT k.keyword FROM keywords k
                JOIN news_keywords nk ON k.id = nk.keyword_id
                WHERE nk.news_id = ?
            """, (news_id,))
            keywords = [row[0] for row in cursor.fetchall()]
            news['keywords'] = keywords
            
            # 获取相关股票
            cursor.execute("""
                SELECT s.code, s.name FROM stocks s
                JOIN news_stocks ns ON s.code = ns.stock_code
                WHERE ns.news_id = ?
            """, (news_id,))
            stocks = [f"{row[0]}:{row[1]}" for row in cursor.fetchall()]
            news['related_stocks'] = stocks
            
            return news
        
        except sqlite3.Error as e:
            logging.error(f"获取新闻失败: {news_id}, 错误: {str(e)}")
            return None
    
    def get_news_list(self, limit=100, offset=0, category=None, start_date=None, end_date=None):
        """
        获取新闻列表
        
        Args:
            limit: 限制条数
            offset: 偏移量
            category: 分类
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            list: 新闻列表
        """
        try:
            cursor = self.conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if category:
                conditions.append("classification = ?")
                params.append(category)
            
            if start_date:
                conditions.append("pub_time >= ?")
                params.append(start_date)
            
            if end_date:
                conditions.append("pub_time <= ?")
                params.append(end_date)
            
            # 构建SQL语句
            sql = "SELECT * FROM news"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            
            sql += " ORDER BY pub_time DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            # 执行查询
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # 将行转换为字典列表
            news_list = []
            for row in rows:
                news = dict(row)
                
                # 处理关键词
                if news['keywords']:
                    news['keywords'] = news['keywords'].split(',')
                else:
                    news['keywords'] = []
                
                # 处理图片
                if news['images']:
                    news['images'] = news['images'].split(',')
                else:
                    news['images'] = []
                
                # 处理相关股票
                if news['related_stocks']:
                    news['related_stocks'] = news['related_stocks'].split(',')
                else:
                    news['related_stocks'] = []
                
                news_list.append(news)
            
            return news_list
        
        except sqlite3.Error as e:
            logging.error(f"获取新闻列表失败: 错误: {str(e)}")
            return []
    
    def get_news_count(self, category=None, start_date=None, end_date=None):
        """
        获取新闻数量
        
        Args:
            category: 分类
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            int: 新闻数量
        """
        try:
            cursor = self.conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if category:
                conditions.append("classification = ?")
                params.append(category)
            
            if start_date:
                conditions.append("pub_time >= ?")
                params.append(start_date)
            
            if end_date:
                conditions.append("pub_time <= ?")
                params.append(end_date)
            
            # 构建SQL语句
            sql = "SELECT COUNT(*) FROM news"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            
            # 执行查询
            cursor.execute(sql, params)
            count = cursor.fetchone()[0]
            
            return count
        
        except sqlite3.Error as e:
            logging.error(f"获取新闻数量失败: 错误: {str(e)}")
            return 0
    
    def delete_news(self, news_id):
        """
        删除指定ID的新闻
        
        Args:
            news_id: 新闻ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM news WHERE id = ?", (news_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        
        except sqlite3.Error as e:
            logging.error(f"删除新闻失败: {news_id}, 错误: {str(e)}")
            self.conn.rollback()
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __del__(self):
        """析构函数，关闭数据库连接"""
        self.close() 