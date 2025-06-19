#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 数据库工具
"""

import os
import sys
import sqlite3
import json
import shutil
import glob
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from backend.app.config import get_settings
from backend.app.utils.logger import get_logger
import uuid
from typing import Dict, List, Any

# 设置日志记录器
logger = get_logger('database')

Base = declarative_base()

class News(Base):
    """新闻模型"""
    __tablename__ = 'news'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    url = Column(String(1000), unique=True)
    source = Column(String(100))
    category = Column(String(100))
    pub_time = Column(DateTime)
    crawl_time = Column(DateTime, default=datetime.now)
    keywords = Column(Text)  # JSON格式存储关键词列表

class NewsDatabase:
    """新闻数据库工具类"""
    
    def __init__(self, db_path=None, use_all_dbs=False, source=None):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库路径，如果为None则使用默认路径
            use_all_dbs: 是否使用所有找到的数据库文件
            source: 指定数据来源，用于筛选特定来源的数据库
        """
        settings = get_settings()
        
        # 确保DB_DIR存在且为绝对路径
        self.db_dir = settings.get('DB_DIR')
        if not self.db_dir:
            # 如果DB_DIR未设置，使用默认路径
            self.db_dir = os.path.join(os.getcwd(), 'data', 'db')
            logger.warning(f"DB_DIR未设置，使用默认路径: {self.db_dir}")
            
        # 转换为绝对路径
        if not os.path.isabs(self.db_dir):
            self.db_dir = os.path.join(os.getcwd(), self.db_dir)
            
        # 创建数据库子目录
        self.sources_dir = os.path.join(self.db_dir, 'sources')
        self.backups_dir = os.path.join(self.db_dir, 'backups')
        
        # 确保数据库目录存在
        for dir_path in [self.db_dir, self.sources_dir, self.backups_dir]:
            if not os.path.exists(dir_path):
                logger.info(f"数据库目录不存在，创建目录: {dir_path}")
                os.makedirs(dir_path, exist_ok=True)
            
        # 如果指定了db_path，直接使用
        if db_path:
            # 如果是相对路径，转换为绝对路径
            if not os.path.isabs(db_path):
                db_path = os.path.join(self.db_dir, db_path)
            self.db_path = db_path
            logger.info(f"使用指定的数据库路径: {self.db_path}")
        else:
            # 默认使用finance_news.db作为主数据库
            self.db_path = os.path.join(self.db_dir, 'finance_news.db')
            
            # 查找finance_news.db（主数据库）
            if os.path.exists(self.db_path):
                logger.info(f"找到主数据库: {self.db_path}")
            else:
                # 查找任何.db文件
                db_files = glob.glob(os.path.join(self.db_dir, '*.db'))
                if db_files:
                    # 使用修改时间最新的数据库
                    newest_db = max(db_files, key=os.path.getmtime)
                    self.db_path = newest_db
                    logger.info(f"使用最新的数据库: {self.db_path}")
                else:
                    logger.warning(f"未找到任何数据库文件，将创建新数据库: {self.db_path}")
        
        logger.info(f"初始化数据库连接: {self.db_path}")
        
        # 收集所有要查询的数据库
        self.all_db_paths = []
        
        # 收集来源专用数据库映射
        self.source_db_map = {}
        
        # 查找所有来源数据库文件
        source_db_files = glob.glob(os.path.join(self.sources_dir, '*.db'))
        if not source_db_files:  # 如果sources目录为空，则查找主目录中的数据库
            source_db_files = glob.glob(os.path.join(self.db_dir, '*.db'))
            
        # 构建来源到数据库的映射
        for db_file in source_db_files:
            file_name = os.path.basename(db_file)
            source_name = os.path.splitext(file_name)[0]
            
            # 如果不是finance_news.db，则认为是来源专用数据库
            if file_name != 'finance_news.db' and file_name != 'main_news.db':
                self.source_db_map[source_name] = db_file
                logger.info(f"找到来源 '{source_name}' 的专用数据库: {db_file}")
        
        # 根据指定的source参数选择数据库
        if source and source in self.source_db_map:
            # 如果指定了来源并且找到了对应的数据库
            self.all_db_paths = [self.source_db_map[source]]
            logger.info(f"使用来源 '{source}' 的专用数据库: {self.all_db_paths[0]}")
        elif use_all_dbs:
            # 使用所有数据库文件，包括来源专用数据库
            self.all_db_paths = [self.db_path]  # 首先添加主数据库
            # 添加所有来源数据库
            for source_db in self.source_db_map.values():
                if source_db not in self.all_db_paths:
                    self.all_db_paths.append(source_db)
            logger.info(f"找到 {len(self.all_db_paths)} 个数据库文件")
            
            # 如果没有找到数据库文件，使用默认数据库
            if not self.all_db_paths:
                self.all_db_paths = [self.db_path]
        else:
            self.all_db_paths = [self.db_path]
            
        # 列出所有将要使用的数据库文件
        for db_path in self.all_db_paths:
            if os.path.exists(db_path):
                file_size = os.path.getsize(db_path) / 1024
                logger.info(f"数据库文件: {db_path} ({file_size:.1f} KB)")
            else:
                logger.warning(f"数据库文件不存在: {db_path}")
        
        # 存储指定的来源
        self.selected_source = source
        
        # 线程安全：不在初始化时创建长期连接，而是每次需要时创建
        self.engine = None
        self.session = None
        self._init_session()
        
        # 存储多数据库连接
        self.engines = {}
        self.sessions = {}
    
    def _init_session(self):
        """初始化数据库会话"""
        settings = get_settings()
        if settings.get('db_type', 'sqlite') == 'sqlite':
            self.engine = create_engine(f'sqlite:///{self.db_path}')
        else:
            db_user = settings.get('db_user', '')
            db_password = settings.get('db_password', '')
            db_host = settings.get('db_host', 'localhost')
            db_port = settings.get('db_port', 3306)
            db_name = settings.get('db_name', 'news')
            db_type = settings.get('db_type', 'mysql')
            db_url = f"{db_type}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            self.engine = create_engine(db_url)
        
        # 创建表（如果不存在）
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # 初始化多数据库连接
        for db_path in self.all_db_paths:
            if db_path != self.db_path and db_path not in self.engines:
                self.engines[db_path] = create_engine(f'sqlite:///{db_path}')
                Base.metadata.create_all(self.engines[db_path])
                Session = sessionmaker(bind=self.engines[db_path])
                self.sessions[db_path] = Session()
    
    def __enter__(self):
        """上下文管理器入口"""
        if self.session is None or self.engine is None:
            self._init_session()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
        return False  # 返回False表示不处理异常
    
    def close(self):
        """关闭数据库连接"""
        try:
            if self.session:
                self.session.close()
                
            # 关闭所有会话
            for session in self.sessions.values():
                if session:
                    session.close()
                    
            # 清空会话和引擎缓存
            self.sessions = {}
            self.engines = {}
            
            logger.debug("已关闭所有数据库连接")
        except Exception as e:
            logger.error(f"关闭数据库连接时出错: {str(e)}")
    
    def add_news(self, news_data):
        """
        添加新闻到数据库
        
        Args:
            news_data: 新闻数据字典
            
        Returns:
            bool: 是否成功添加
        """
        # 确定目标数据库路径
        target_db_path = self.db_path
        
        # 如果新闻有来源信息，也保存到对应的来源数据库
        if 'source' in news_data and news_data['source'] in self.source_db_map:
            source_db_path = self.source_db_map[news_data['source']]
            # 先保存到来源数据库
            self._add_news_to_db(news_data, source_db_path)
            
        # 始终保存到主数据库
        return self._add_news_to_db(news_data, target_db_path)
    
    def _add_news_to_db(self, news_data, db_path):
        """
        将新闻添加到指定的数据库
        
        Args:
            news_data: 新闻数据字典
            db_path: 数据库路径
            
        Returns:
            bool: 是否成功添加
        """
        try:
            # 获取对应的会话
            if db_path == self.db_path:
                session = self.session
            else:
                if db_path not in self.sessions:
                    self.engines[db_path] = create_engine(f'sqlite:///{db_path}')
                    Base.metadata.create_all(self.engines[db_path])
                    Session = sessionmaker(bind=self.engines[db_path])
                    self.sessions[db_path] = Session()
                session = self.sessions[db_path]
            
            # 检查新闻是否已存在
            existing_news = session.query(News).filter(News.url == news_data['url']).first()
            if existing_news:
                logger.debug(f"新闻已存在于数据库 {db_path}: {news_data['title']}")
                return False
                
            # 处理日期时间
            if 'pub_time' in news_data:
                pub_time_str = news_data['pub_time']
                try:
                    pub_time = datetime.strptime(pub_time_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # 尝试其他可能的日期格式
                    try:
                        pub_time = datetime.strptime(pub_time_str, '%Y-%m-%d')
                    except ValueError:
                        pub_time = datetime.now()
            else:
                pub_time = datetime.now()
                
            # 处理爬取时间
            if 'crawl_time' in news_data:
                try:
                    crawl_time = datetime.strptime(news_data['crawl_time'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    crawl_time = datetime.now()
            else:
                crawl_time = datetime.now()
                
            # 处理关键词
            if 'keywords' in news_data and news_data['keywords']:
                if isinstance(news_data['keywords'], list):
                    keywords = json.dumps(news_data['keywords'])
                else:
                    # 如果是逗号分隔的字符串，转换为列表
                    keywords = json.dumps(news_data['keywords'].split(','))
            else:
                keywords = json.dumps([])
                
            # 创建新闻对象
            news = News(
                title=news_data['title'],
                content=news_data.get('content', ''),
                url=news_data['url'],
                source=news_data.get('source', '未知来源'),
                category=news_data.get('category', '未分类'),
                pub_time=pub_time,
                crawl_time=crawl_time,
                keywords=keywords
            )
            
            # 添加到数据库
            session.add(news)
            session.commit()
            logger.info(f"成功添加新闻到数据库 {db_path}: {news_data['title']}")
            return True
        
        except Exception as e:
            logger.error(f"添加新闻到数据库 {db_path} 失败: {str(e)}")
            if 'session' in locals():
                session.rollback()
            return False
    
    def get_available_sources(self):
        """
        获取所有可用的数据源
        
        Returns:
            list: 数据源列表
        """
        return list(self.source_db_map.keys())
    
    def backup_database(self, source=None):
        """
        备份数据库
        
        Args:
            source: 要备份的数据源，如果为None则备份主数据库
            
        Returns:
            str: 备份文件路径
        """
        # 确定要备份的数据库路径
        if source and source in self.source_db_map:
            db_path = self.source_db_map[source]
        else:
            db_path = self.db_path
            
        # 生成备份文件名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        source_name = source or 'main'
        backup_filename = f"{source_name}_{timestamp}.db.bak"
        backup_path = os.path.join(self.backups_dir, backup_filename)
        
        # 执行备份
        try:
            shutil.copy2(db_path, backup_path)
            logger.info(f"成功备份数据库 {db_path} 到 {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"备份数据库 {db_path} 失败: {str(e)}")
            return None
    
    def restore_database(self, backup_path, source=None):
        """
        从备份恢复数据库
        
        Args:
            backup_path: 备份文件路径
            source: 要恢复的数据源，如果为None则恢复到主数据库
            
        Returns:
            bool: 是否成功恢复
        """
        # 确定要恢复的目标数据库路径
        if source and source in self.source_db_map:
            target_db_path = self.source_db_map[source]
        else:
            target_db_path = self.db_path
            
        # 确保备份文件存在
        if not os.path.exists(backup_path):
            logger.error(f"备份文件不存在: {backup_path}")
            return False
            
        # 执行恢复
        try:
            # 关闭相关的数据库连接
            if target_db_path == self.db_path:
                if self.session:
                    self.session.close()
            elif target_db_path in self.sessions:
                self.sessions[target_db_path].close()
                del self.sessions[target_db_path]
                del self.engines[target_db_path]
                
            # 复制备份文件到目标位置
            shutil.copy2(backup_path, target_db_path)
            logger.info(f"成功恢复数据库 {target_db_path} 从备份 {backup_path}")
            
            # 重新初始化会话
            self._init_session()
            return True
        except Exception as e:
            logger.error(f"恢复数据库 {target_db_path} 失败: {str(e)}")
            return False
    
    def get_backups(self, source=None):
        """
        获取指定来源的所有备份文件
        
        Args:
            source: 数据源名称，如果为None则获取所有备份
            
        Returns:
            list: 备份文件信息列表，每项包含 {path, timestamp, size}
        """
        # 查找所有备份文件
        backup_files = glob.glob(os.path.join(self.backups_dir, '*.db.bak'))
        
        # 筛选特定来源的备份
        filtered_backups = []
        for backup_file in backup_files:
            file_name = os.path.basename(backup_file)
            
            # 解析文件名
            if source:
                # 检查文件名是否以指定来源开头
                if file_name.startswith(f"{source}_"):
                    # 获取备份信息
                    timestamp_str = file_name.split('_')[1].split('.')[0]
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                        size = os.path.getsize(backup_file)
                        filtered_backups.append({
                            'path': backup_file,
                            'timestamp': timestamp,
                            'size': size,
                            'source': source
                        })
                    except ValueError:
                        logger.warning(f"无法解析备份文件的时间戳: {file_name}")
            else:
                # 所有备份
                parts = file_name.split('_')
                if len(parts) >= 2:
                    source_name = parts[0]
                    timestamp_str = parts[1].split('.')[0]
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                        size = os.path.getsize(backup_file)
                        filtered_backups.append({
                            'path': backup_file,
                            'timestamp': timestamp,
                            'size': size,
                            'source': source_name
                        })
                    except ValueError:
                        logger.warning(f"无法解析备份文件的时间戳: {file_name}")
        
        # 按时间戳排序，最新的在前
        filtered_backups.sort(key=lambda x: x['timestamp'], reverse=True)
        return filtered_backups
    
    def sync_to_main_db(self, source):
        """
        将指定来源的数据同步到主数据库
        
        Args:
            source: 数据源名称
            
        Returns:
            int: 同步的新闻数量
        """
        if source not in self.source_db_map:
            logger.error(f"未找到来源 '{source}' 的数据库")
            return 0
            
        source_db_path = self.source_db_map[source]
        
        try:
            # 获取来源数据库的会话
            if source_db_path not in self.sessions:
                self.engines[source_db_path] = create_engine(f'sqlite:///{source_db_path}')
                Base.metadata.create_all(self.engines[source_db_path])
                Session = sessionmaker(bind=self.engines[source_db_path])
                self.sessions[source_db_path] = Session()
                
            source_session = self.sessions[source_db_path]
            
            # 查询来源数据库中的所有新闻
            news_items = source_session.query(News).all()
            sync_count = 0
            
            # 遍历新闻并添加到主数据库
            for news in news_items:
                # 检查主数据库中是否已存在该新闻
                if not self.session.query(News).filter(News.url == news.url).first():
                    # 创建新闻数据字典
                    news_data = {
                        'title': news.title,
                        'content': news.content,
                        'url': news.url,
                        'source': news.source,
                        'category': news.category,
                        'pub_time': news.pub_time.strftime('%Y-%m-%d %H:%M:%S') if news.pub_time else None,
                        'crawl_time': news.crawl_time.strftime('%Y-%m-%d %H:%M:%S') if news.crawl_time else None,
                        'keywords': json.loads(news.keywords) if news.keywords else []
                    }
                    
                    # 添加到主数据库
                    news_obj = News(
                        title=news_data['title'],
                        content=news_data['content'],
                        url=news_data['url'],
                        source=news_data['source'],
                        category=news_data['category'],
                        pub_time=news.pub_time,
                        crawl_time=news.crawl_time,
                        keywords=news.keywords
                    )
                    
                    self.session.add(news_obj)
                    sync_count += 1
            
            # 提交更改
            if sync_count > 0:
                self.session.commit()
                logger.info(f"成功从 '{source}' 同步 {sync_count} 条新闻到主数据库")
            else:
                logger.info(f"没有新闻需要从 '{source}' 同步到主数据库")
                
            return sync_count
            
        except Exception as e:
            logger.error(f"同步数据库失败: {str(e)}")
            if hasattr(self, 'session') and self.session:
                self.session.rollback()
            return 0

    # 确保其余方法兼容新的多数据库结构... 
    
    def get_sources(self):
        """
        获取所有新闻来源
        
        Returns:
            list: 来源列表
        """
        # 集合用于去重
        sources = set()
        
        try:
            # 从所有数据库收集来源
            for db_path in self.all_db_paths:
                try:
                    # 直接使用SQLite连接查询
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT DISTINCT source FROM news WHERE source IS NOT NULL AND source != ''")
                    for row in cursor.fetchall():
                        sources.add(row['source'])
                    conn.close()
                except Exception as e:
                    logger.error(f"从数据库 {db_path} 获取来源失败: {str(e)}")
            
            # 返回排序后的列表
            return sorted(list(sources))
        except Exception as e:
            logger.error(f"获取新闻来源失败: {str(e)}")
            return []
    
    def get_news_count(self, keyword=None, days=None, source=None, category=None, start_date=None, end_date=None):
        """
        获取符合条件的新闻数量
        
        Args:
            keyword: 关键词过滤
            days: 最近几天的数据
            source: 来源过滤
            category: 分类过滤
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            int: 新闻数量
        """
        total = 0
        
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
            
            # 从所有数据库获取数量
            for db_path in self.all_db_paths:
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    count = cursor.fetchone()[0]
                    total += count
                    conn.close()
                except Exception as e:
                    logger.error(f"从数据库 {db_path} 获取新闻数量失败: {str(e)}")
            
            return total
            
        except Exception as e:
            logger.error(f"获取新闻数量失败: {str(e)}")
            return 0
    
    def get_categories(self):
        """
        获取所有新闻分类
        
        Returns:
            list: 分类列表
        """
        # 集合用于去重
        categories = set()
        
        try:
            # 从所有数据库收集分类
            for db_path in self.all_db_paths:
                try:
                    # 直接使用SQLite连接查询
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT DISTINCT category FROM news WHERE category IS NOT NULL AND category != ''")
                    for row in cursor.fetchall():
                        categories.add(row['category'])
                    conn.close()
                except Exception as e:
                    logger.error(f"从数据库 {db_path} 获取分类失败: {str(e)}")
            
            # 返回排序后的列表
            return sorted(list(categories))
        except Exception as e:
            logger.error(f"获取新闻分类失败: {str(e)}")
            return []
    
    def get_connection(self, db_path=None):
        """
        获取sqlite3数据库连接
        
        Args:
            db_path: 数据库路径，如果为None则使用当前对象的db_path
            
        Returns:
            sqlite3.Connection: 数据库连接
        """
        if db_path is None:
            db_path = self.db_path
            
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 创建连接
        conn = sqlite3.connect(db_path)
        
        # 启用外键约束
        conn.execute("PRAGMA foreign_keys = ON")
        
        # 设置返回行为字典
        conn.row_factory = sqlite3.Row
        
        return conn

class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def connect(self):
        """创建数据库连接"""
        return sqlite3.connect(self.db_path)
        
    def execute(self, sql: str, params: tuple = None) -> Any:
        """执行SQL语句"""
        with self.connect() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            conn.commit()
            return cursor.fetchall()