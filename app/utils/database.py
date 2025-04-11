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
from app.config import get_settings
from app.utils.logger import get_logger
import uuid

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
    
    def __init__(self, db_path=None, use_all_dbs=False):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库路径，如果为None则使用默认路径
            use_all_dbs: 是否使用所有找到的数据库文件
        """
        settings = get_settings()
        
        # 确保DB_DIR存在且为绝对路径
        self.db_dir = settings.get('DB_DIR')
        if not os.path.isabs(self.db_dir):
            self.db_dir = os.path.join(os.getcwd(), self.db_dir)
            
        logger.info(f"初始化数据库连接，数据库目录: {self.db_dir}")
        
        if not os.path.exists(self.db_dir):
            logger.info(f"数据库目录不存在，创建目录: {self.db_dir}")
            os.makedirs(self.db_dir, exist_ok=True)
            
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
        
        # 查找所有.db文件
        db_files = glob.glob(os.path.join(self.db_dir, '*.db'))
        
        # 构建来源到数据库的映射
        for db_file in db_files:
            file_name = os.path.basename(db_file)
            source_name = os.path.splitext(file_name)[0]
            
            # 如果不是finance_news.db，则认为是来源专用数据库
            if file_name != 'finance_news.db' and file_name != 'main_news.db':
                self.source_db_map[source_name] = db_file
                logger.info(f"找到来源 '{source_name}' 的专用数据库: {db_file}")
        
        if use_all_dbs:
            # 使用所有数据库文件，包括来源专用数据库
            self.all_db_paths = db_files
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
    
    def add_news(self, news_data):
        """添加新闻"""
        try:
            # 检查新闻是否已存在
            existing_news = self.session.query(News).filter(News.url == news_data['url']).first()
            if existing_news:
                logger.debug(f"新闻已存在: {news_data['title']}")
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
            
            # 确保source不为空
            source = news_data.get('source', '未知来源')
            if not source or source == '未知来源':
                # 尝试从URL中推断来源
                if 'url' in news_data:
                    url = news_data['url']
                    if 'eastmoney.com' in url:
                        source = '东方财富网'
                    elif 'sina.com' in url or 'sina.cn' in url:
                        source = '新浪财经'
                    elif 'qq.com' in url or 'finance.qq.com' in url or 'news.qq.com' in url:
                        source = '腾讯财经'
                    elif '163.com' in url or 'money.163.com' in url:
                        source = '网易财经'
                    elif 'ifeng.com' in url:
                        source = '凤凰财经'
                    elif 'jrj.com' in url:
                        source = '金融界'
                    elif 'cs.com.cn' in url:
                        source = '中国证券网'
                    elif 'hexun.com' in url:
                        source = '和讯网'
                    elif 'cnstock.com' in url:
                        source = '中证网'
                    elif 'xinhuanet.com' in url:
                        source = '新华网'
                    elif 'people.com.cn' in url:
                        source = '人民网'
                    elif 'cctv.com' in url:
                        source = 'CCTV'
                    elif 'stcn.com' in url:
                        source = '证券时报网'
                    elif '21jingji.com' in url:
                        source = '21世纪经济报道'
                    elif 'caixin.com' in url:
                        source = '财新网'
                
            # 创建新闻对象
            news = News(
                title=news_data['title'],
                content=news_data['content'],
                url=news_data['url'],
                source=source,
                category=news_data.get('category', '财经'),
                pub_time=pub_time,
                crawl_time=crawl_time,
                keywords=keywords
            )
            
            self.session.add(news)
            self.session.commit()
            logger.info(f"新闻添加成功: {news_data['title']}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"添加新闻失败: {str(e)}")
            if 'title' in news_data:
                logger.error(f"标题: {news_data['title']}")
            return False
    
    def query_news(self, keyword=None, days=None, source=None, limit=10, offset=0):
        """
        根据条件查询新闻
        
        Args:
            keyword: 搜索关键词（可选）
            days: 最近几天的新闻（可选）
            source: 新闻来源（可选）
            limit: 返回结果数量限制
            offset: 分页偏移量
            
        Returns:
            list: 新闻列表
        """
        results = []
        
        try:
            # 确定要查询的数据库
            db_paths = []
            
            # 如果指定了来源，优先使用对应的专用数据库
            if source and source in self.source_db_map:
                source_db = self.source_db_map[source]
                if os.path.exists(source_db):
                    db_paths.append(source_db)
                    logger.info(f"使用来源 '{source}' 的专用数据库: {source_db}")
                else:
                    logger.warning(f"找不到来源 '{source}' 的专用数据库，回退到默认数据库")
                    db_paths = self.all_db_paths
            else:
                # 如果未指定来源或找不到对应专用数据库，则查询所有数据库
                db_paths = self.all_db_paths
                logger.info(f"未指定来源或找不到专用数据库，使用所有数据库: {db_paths}")
                
            # 检查数据库文件是否存在
            valid_db_paths = []
            for db_path in db_paths:
                if os.path.exists(db_path):
                    valid_db_paths.append(db_path)
                else:
                    logger.warning(f"数据库文件不存在: {db_path}")
            
            if not valid_db_paths:
                logger.error(f"没有找到有效的数据库文件")
                return []
            
            # 记录已处理的新闻URL，避免重复
            processed_urls = set()
                
            # 遍历数据库文件查询
            for db_path in valid_db_paths:
                try:
                    # 尝试从数据库文件名中提取来源
                    db_source = os.path.basename(db_path).replace('.db', '')
                    logger.info(f"从数据库 {db_path} 中查询新闻，来源: {db_source}")
                    
                    # 连接数据库
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cur = conn.cursor()
                    
                    # 构建查询条件
                    conditions = []
                    params = []
                    
                    if source:
                        conditions.append("source = ?")
                        params.append(source)
                    
                    if keyword:
                        # 从标题和内容中搜索
                        conditions.append("(title LIKE ? OR content LIKE ?)")
                        params.extend([f'%{keyword}%', f'%{keyword}%'])
                    
                    if days:
                        # 计算日期范围
                        days_ago = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                        conditions.append("pub_time >= ?")
                        params.append(days_ago)
                    
                    # 构建SQL查询
                    query = "SELECT * FROM news"
                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)
                    
                    # 添加排序和分页
                    # 注意：这里不添加LIMIT和OFFSET，因为我们需要合并结果后再分页
                    query += " ORDER BY pub_time DESC"
                    
                    logger.info(f"执行查询: {query} 参数: {params}")
                    
                    # 执行查询
                    try:
                        cur.execute(query, params)
                        rows = cur.fetchall()
                        logger.info(f"从 {db_path} 数据库查询到 {len(rows)} 条新闻")
                        
                        for row in rows:
                            news = dict(row)
                            
                            # 检查URL是否已处理，避免重复
                            if 'url' in news and news['url'] in processed_urls:
                                continue
                                
                            # 添加到已处理URL集合
                            if 'url' in news:
                                processed_urls.add(news['url'])
                            
                            # 处理关键词字段
                            if 'keywords' in news and news['keywords']:
                                try:
                                    news['keywords'] = json.loads(news['keywords'])
                                except json.JSONDecodeError:
                                    news['keywords'] = []
                            else:
                                news['keywords'] = []
                            
                            # 处理图片字段
                            if 'images' in news and news['images']:
                                try:
                                    news['images'] = json.loads(news['images'])
                                except json.JSONDecodeError:
                                    news['images'] = []
                            else:
                                news['images'] = []
                                
                            # 检查必需字段
                            required_fields = ['id', 'title', 'content', 'url', 'pub_time', 'source']
                            for field in required_fields:
                                if field not in news or not news[field]:
                                    if field == 'source':
                                        news['source'] = db_source or '未知来源'
                                    elif field == 'id':
                                        news['id'] = str(uuid.uuid4())
                                    elif field == 'pub_time':
                                        news['pub_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    
                            results.append(news)
                    except sqlite3.OperationalError as e:
                        logger.error(f"执行查询失败: {str(e)}")
                        # 可能是表不存在，尝试创建表
                        if "no such table" in str(e).lower():
                            logger.warning(f"数据库 {db_path} 中表不存在，尝试创建表")
                            try:
                                self._create_tables(conn)
                                logger.info(f"成功创建表结构")
                            except Exception as create_err:
                                logger.error(f"创建表失败: {str(create_err)}")
                    
                    conn.close()
                except Exception as db_error:
                    logger.error(f"处理数据库 {db_path} 时出错: {str(db_error)}")
            
            # 按发布时间排序合并后的结果
            results.sort(key=lambda x: x.get('pub_time', ''), reverse=True)
            
            # 应用分页
            return results[offset:offset+limit]
            
        except Exception as e:
            logger.error(f"查询新闻失败: {str(e)}")
            
        return results
    
    def _create_tables(self, conn):
        """创建数据库表结构"""
        cur = conn.cursor()
        # 创建新闻表
        cur.execute('''
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
        cur.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE,
                count INTEGER DEFAULT 1,
                last_updated TEXT
            )
        ''')
        
        # 创建新闻-关键词关系表
        cur.execute('''
            CREATE TABLE IF NOT EXISTS news_keywords (
                news_id TEXT,
                keyword_id INTEGER,
                PRIMARY KEY (news_id, keyword_id),
                FOREIGN KEY (news_id) REFERENCES news(id) ON DELETE CASCADE,
                FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
    
    def get_news_count(self, keyword=None, days=None, source=None):
        """
        获取新闻数量
        
        Args:
            keyword: 搜索关键词（可选）
            days: 最近几天的新闻（可选）
            source: 新闻来源（可选）
            
        Returns:
            int: 符合条件的新闻总数
        """
        total_count = 0
        
        try:
            # 确定要查询的数据库
            db_paths = []
            
            # 如果指定了来源，优先使用对应的专用数据库
            if source and source in self.source_db_map:
                source_db = self.source_db_map[source]
                if os.path.exists(source_db):
                    db_paths.append(source_db)
                    logger.info(f"计数使用来源 '{source}' 的专用数据库: {source_db}")
                else:
                    logger.warning(f"计数找不到来源 '{source}' 的专用数据库，回退到默认数据库")
                    db_paths = self.all_db_paths
            else:
                # 如果未指定来源或找不到对应专用数据库，则查询所有数据库
                db_paths = self.all_db_paths
                logger.info(f"计数未指定来源或找不到专用数据库，使用所有数据库: {db_paths}")
            
            # 检查数据库文件是否存在
            valid_db_paths = []
            for db_path in db_paths:
                if os.path.exists(db_path):
                    valid_db_paths.append(db_path)
                else:
                    logger.warning(f"数据库文件不存在: {db_path}")
            
            if not valid_db_paths:
                logger.error(f"没有找到有效的数据库文件")
                return 0
            
            # 记录已统计的URL，避免重复计数
            counted_urls = set()
            
            # 尝试从所有数据库查询
            for db_path in valid_db_paths:
                try:
                    # 尝试从数据库文件名中提取来源
                    db_source = os.path.basename(db_path).replace('.db', '')
                    logger.info(f"从数据库 {db_path} 中计数，来源: {db_source}")
                    
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # 判断news表是否存在
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                    if not cursor.fetchone():
                        # 表不存在，创建表结构
                        logger.warning(f"数据库 {db_path} 中news表不存在，尝试创建表")
                        try:
                            self._create_tables(conn)
                            logger.info(f"成功创建表结构")
                        except Exception as create_err:
                            logger.error(f"创建表失败: {str(create_err)}")
                            conn.close()
                            continue
                    
                    # 如果是计数URL去重，需要先获取所有URL
                    if source or keyword or days:
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
                            start_time = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                            conditions.append("pub_time >= ?")
                            params.append(start_time)
                        
                        # 先获取所有匹配的URL进行去重
                        sql = "SELECT url FROM news"
                        if conditions:
                            sql += " WHERE " + " AND ".join(conditions)
                        
                        cursor.execute(sql, params)
                        for url_row in cursor.fetchall():
                            url = url_row[0]
                            if url and url not in counted_urls:
                                counted_urls.add(url)
                                total_count += 1
                    else:
                        # 如果没有筛选条件，直接计数（但仍需去重）
                        cursor.execute("SELECT url FROM news")
                        for url_row in cursor.fetchall():
                            url = url_row[0]
                            if url and url not in counted_urls:
                                counted_urls.add(url)
                                total_count += 1
                    
                    conn.close()
                except Exception as e:
                    logger.error(f"查询数据库 {db_path} 计数失败: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            logger.info(f"查询结果: 共 {total_count} 条符合条件的新闻")
        except Exception as e:
            logger.error(f"获取新闻数量失败: {str(e)}")
        
        return total_count
    
    def get_sources(self):
        """获取所有新闻来源"""
        sources = set()
        
        try:
            # 检查数据库文件是否存在
            valid_db_paths = []
            for db_path in self.all_db_paths:
                if os.path.exists(db_path):
                    valid_db_paths.append(db_path)
                else:
                    logger.warning(f"数据库文件不存在: {db_path}")
            
            if not valid_db_paths:
                logger.error(f"没有找到有效的数据库文件")
                return []
            
            # 尝试从所有数据库查询
            for db_path in valid_db_paths:
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # 判断news表是否存在
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                    if not cursor.fetchone():
                        # 表不存在，跳过此数据库
                        logger.warning(f"数据库 {db_path} 中news表不存在，跳过")
                        conn.close()
                        continue
                    
                    cursor.execute("SELECT DISTINCT source FROM news")
                    for row in cursor.fetchall():
                        if row[0]:  # 排除空值
                            sources.add(row[0])
                    
                    # 从文件名中提取来源名称
                    source_from_filename = os.path.splitext(os.path.basename(db_path))[0]
                    # 如果不是主数据库，添加到来源列表
                    if source_from_filename not in ['finance_news', 'main_news']:
                        sources.add(source_from_filename)
                    
                    conn.close()
                except Exception as e:
                    logger.error(f"查询数据库 {db_path} 来源失败: {str(e)}")
            
            # 优先使用专用数据库名称作为来源
            for source_name in self.source_db_map.keys():
                if source_name not in ['finance_news', 'main_news']:
                    sources.add(source_name)
        except Exception as e:
            logger.error(f"获取新闻来源失败: {str(e)}")
        
        return sorted(list(sources))
    
    def get_categories(self):
        """获取所有分类"""
        categories = set()
        
        try:
            # 检查数据库文件是否存在
            valid_db_paths = []
            for db_path in self.all_db_paths:
                if os.path.exists(db_path):
                    valid_db_paths.append(db_path)
                else:
                    logger.warning(f"数据库文件不存在: {db_path}")
            
            if not valid_db_paths:
                logger.error(f"没有找到有效的数据库文件")
                return []
            
            # 尝试从所有数据库查询
            for db_path in valid_db_paths:
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # 判断news表是否存在
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                    if not cursor.fetchone():
                        # 表不存在，跳过此数据库
                        logger.warning(f"数据库 {db_path} 中news表不存在，跳过")
                        conn.close()
                        continue
                    
                    cursor.execute("SELECT DISTINCT category FROM news")
                    for row in cursor.fetchall():
                        if row[0]:  # 排除空值
                            categories.add(row[0])
                    
                    conn.close()
                except Exception as e:
                    logger.error(f"查询数据库 {db_path} 分类失败: {str(e)}")
        except Exception as e:
            logger.error(f"获取新闻分类失败: {str(e)}")
        
        return sorted(list(categories))
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'session'):
            self.session.close()

    def get_news_by_id(self, news_id):
        """根据ID获取新闻详情
        
        Args:
            news_id: 新闻ID
            
        Returns:
            dict: 新闻数据，如果未找到则返回None
        """
        try:
            # 确定要查询的数据库列表
            db_paths = self.all_db_paths
            
            # 检查数据库文件是否存在
            valid_db_paths = []
            for db_path in db_paths:
                if os.path.exists(db_path):
                    valid_db_paths.append(db_path)
                else:
                    logger.warning(f"数据库文件不存在: {db_path}")
            
            if not valid_db_paths:
                logger.error(f"没有找到有效的数据库文件")
                return None
            
            # 尝试从所有数据库查询
            for db_path in valid_db_paths:
                try:
                    # 尝试从数据库文件名中提取来源
                    db_source = os.path.basename(db_path).replace('.db', '')
                    logger.debug(f"在数据库 {db_path} 中查询新闻ID: {news_id}")
                    
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # 判断news表是否存在
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                    if not cursor.fetchone():
                        # 表不存在，跳过此数据库
                        logger.warning(f"数据库 {db_path} 中news表不存在，跳过")
                        conn.close()
                        continue
                    
                    # 查询指定ID的新闻
                    cursor.execute("SELECT * FROM news WHERE id = ?", (news_id,))
                    row = cursor.fetchone()
                    
                    if row:
                        # 转换为字典
                        news = {}
                        for i, column in enumerate(cursor.description):
                            news[column[0]] = row[i]
                        
                        # 处理JSON字段
                        try:
                            if 'keywords' in news and news['keywords']:
                                news['keywords'] = json.loads(news['keywords'])
                            if 'images' in news and news['images']:
                                news['images'] = json.loads(news['images'])
                            if 'related_stocks' in news and news['related_stocks']:
                                news['related_stocks'] = json.loads(news['related_stocks'])
                        except json.JSONDecodeError:
                            # 如果JSON解析失败，保持原始字符串
                            pass
                        
                        conn.close()
                        logger.info(f"在数据库 {db_path} 中找到新闻ID: {news_id}")
                        return news  # 找到后立即返回
                    
                    conn.close()
                except Exception as e:
                    logger.error(f"查询新闻详情失败: {str(e)}")
            
            logger.warning(f"在所有数据库中未找到新闻ID: {news_id}")
            return None  # 所有数据库都未找到，返回None
        except Exception as e:
            logger.error(f"获取新闻详情失败: {str(e)}")
            return None

    def update_unknown_sources(self):
        """
        更新数据库中所有未知来源的新闻，根据URL推断正确的数据源
        
        Returns:
            int: 更新的记录数量
        """
        try:
            logger.info("开始更新未知来源的新闻数据...")
            
            # 查询所有未知来源的新闻
            unknown_news = self.session.query(News).filter(
                (News.source == '未知来源') | 
                (News.source == '') | 
                (News.source == None)
            ).all()
            
            if not unknown_news:
                logger.info("没有找到未知来源的新闻")
                return 0
                
            updated_count = 0
            
            for news in unknown_news:
                if not news.url:
                    continue
                    
                url = news.url.lower()
                new_source = None
                
                # 根据URL推断来源
                if 'eastmoney.com' in url:
                    new_source = '东方财富网'
                elif 'sina.com' in url or 'sina.cn' in url:
                    new_source = '新浪财经'
                elif 'qq.com' in url or 'finance.qq.com' in url or 'news.qq.com' in url:
                    new_source = '腾讯财经'
                elif '163.com' in url or 'money.163.com' in url:
                    new_source = '网易财经'
                elif 'ifeng.com' in url:
                    new_source = '凤凰财经'
                elif 'jrj.com' in url:
                    new_source = '金融界'
                elif 'cs.com.cn' in url:
                    new_source = '中国证券网'
                elif 'hexun.com' in url:
                    new_source = '和讯网'
                elif 'cnstock.com' in url:
                    new_source = '中证网'
                elif 'xinhuanet.com' in url:
                    new_source = '新华网'
                elif 'people.com.cn' in url:
                    new_source = '人民网'
                elif 'cctv.com' in url:
                    new_source = 'CCTV'
                elif 'stcn.com' in url:
                    new_source = '证券时报网'
                elif '21jingji.com' in url:
                    new_source = '21世纪经济报道'
                elif 'caixin.com' in url:
                    new_source = '财新网'
                
                if new_source:
                    news.source = new_source
                    updated_count += 1
            
            if updated_count > 0:
                self.session.commit()
                logger.info(f"成功更新 {updated_count} 条未知来源的新闻")
            
            return updated_count
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"更新未知来源失败: {str(e)}")
            return 0

class DatabaseManager:
    """数据库管理器，提供数据库连接和初始化功能"""
    
    def __init__(self, db_dir='db'):
        """
        初始化数据库管理器
        
        Args:
            db_dir: 数据库目录或数据库文件路径
        """
        # 检查db_dir是否是一个文件路径（以.db结尾）
        if db_dir.endswith('.db'):
            # 如果是文件路径，分离目录和文件名
            self.db_dir = os.path.dirname(db_dir)
            self.main_db_path = db_dir
        else:
            # 如果是目录路径，使用默认文件名
            self.db_dir = db_dir
            self.main_db_path = os.path.join(db_dir, 'finance_news.db')
        
        # 确保数据库目录存在
        if self.db_dir and not os.path.exists(self.db_dir):
            try:
                os.makedirs(self.db_dir, exist_ok=True)
                logger.info(f"创建数据库目录: {self.db_dir}")
            except Exception as e:
                logger.error(f"创建数据库目录失败: {self.db_dir}, 错误: {str(e)}")
                # 尝试使用当前目录
                self.db_dir = os.path.join(os.getcwd(), 'data', 'db')
                if not os.path.exists(self.db_dir):
                    os.makedirs(self.db_dir, exist_ok=True)
                self.main_db_path = os.path.join(self.db_dir, 'finance_news.db')
                logger.info(f"使用备用数据库目录: {self.db_dir}")
    
    def get_connection(self, db_path=None):
        """
        获取数据库连接
        
        Args:
            db_path: 数据库路径，如果为None则使用主数据库
        
        Returns:
            sqlite3.Connection: 数据库连接
        """
        if db_path is None:
            db_path = self.main_db_path
        
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        
        # 启用外键约束
        conn.execute('PRAGMA foreign_keys = ON')
        
        # 设置行工厂，返回字典
        conn.row_factory = sqlite3.Row
        
        logger.debug(f"已连接到数据库: {db_path}")
        return conn
    
    def init_db(self, conn):
        """
        初始化数据库，创建表
        
        Args:
            conn: 数据库连接
        """
        try:
            cursor = conn.cursor()
            
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
                    url TEXT,
                    keywords TEXT,
                    sentiment REAL,
                    crawl_time TEXT,
                    category TEXT,
                    images TEXT,
                    related_stocks TEXT
                )
            ''')
            
            # 提交事务
            conn.commit()
            
            logger.debug("已初始化数据库表")
            
        except Exception as e:
            logger.error(f"初始化数据库失败: {str(e)}")
            conn.rollback()
            raise
    
    def save_news(self, news_data, conn=None, db_path=None):
        """
        保存新闻数据到数据库
        
        Args:
            news_data: 新闻数据字典
            conn: 数据库连接，如果为None则创建新连接
            db_path: 数据库路径，如果为None则使用默认路径
            
        Returns:
            bool: 是否保存成功
        """
        # 如果没有提供数据库路径，使用当前对象的db_path属性（如果存在）
        if db_path is None:
            if hasattr(self, 'db_path') and self.db_path:
                db_path = self.db_path
            else:
                db_path = self.main_db_path
        
        logger.debug(f"使用数据库路径保存新闻: {db_path}")
        
        # 如果没有提供连接，创建新连接
        close_conn = False
        if conn is None:
            conn = self.get_connection(db_path)
            close_conn = True
            
            # 确保数据库已初始化
            try:
                self.init_db(conn)
            except Exception as e:
                logger.error(f"初始化数据库失败: {str(e)}")
        
        try:
            cursor = conn.cursor()
            
            # 检查新闻ID是否已存在
            cursor.execute("SELECT id FROM news WHERE id = ?", (news_data['id'],))
            if cursor.fetchone():
                logger.debug(f"新闻已存在: {news_data.get('title', 'unknown')}")
                return False
            
            # 确保所有字段都存在
            fields = ['id', 'title', 'content', 'pub_time', 'author', 'source', 'url', 
                      'keywords', 'sentiment', 'crawl_time', 'category', 'images', 'related_stocks']
            
            news_dict = {}
            for field in fields:
                if field in news_data:
                    # 如果是列表类型，转换为逗号分隔的字符串
                    if isinstance(news_data[field], list):
                        news_dict[field] = ','.join(news_data[field])
                    else:
                        news_dict[field] = news_data[field]
                else:
                    # 对于缺失的字段设置默认值
                    if field == 'crawl_time':
                        news_dict[field] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    elif field == 'sentiment':
                        news_dict[field] = 0.5
                    else:
                        news_dict[field] = ''
            
            # 构建INSERT语句
            fields_str = ', '.join(fields)
            placeholders = ', '.join(['?' for _ in fields])
            sql = f"INSERT INTO news ({fields_str}) VALUES ({placeholders})"
            
            # 执行INSERT语句
            cursor.execute(sql, tuple(news_dict[field] for field in fields))
            
            # 提交事务
            conn.commit()
            
            logger.debug(f"成功保存新闻: {news_dict.get('title', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"保存新闻失败: {str(e)}")
            conn.rollback()
            return False
            
        finally:
            # 如果我们创建了连接，则关闭它
            if close_conn:
                conn.close()
    
    def merge_db(self, source_db_path, target_db_path=None):
        """
        合并数据库，将源数据库的数据合并到目标数据库
        
        Args:
            source_db_path: 源数据库路径
            target_db_path: 目标数据库路径，如果为None则使用主数据库
        
        Returns:
            int: 合并的新闻数量
        """
        if target_db_path is None:
            target_db_path = self.main_db_path
        
        # 连接源数据库和目标数据库
        source_conn = self.get_connection(source_db_path)
        target_conn = self.get_connection(target_db_path)
        
        try:
            # 获取源数据库中的所有新闻
            source_cursor = source_conn.cursor()
            source_cursor.execute('SELECT * FROM news')
            news_list = source_cursor.fetchall()
            
            # 获取目标数据库中的所有新闻ID
            target_cursor = target_conn.cursor()
            target_cursor.execute('SELECT id FROM news')
            existing_ids = set(row[0] for row in target_cursor.fetchall())
            
            # 合并新闻
            merged_count = 0
            for news in news_list:
                # 如果新闻ID已存在，则跳过
                if news['id'] in existing_ids:
                    continue
                
                # 插入新闻
                target_conn.execute('''
                    INSERT INTO news (
                        id, title, content, pub_time, author, source, url, 
                        keywords, sentiment, crawl_time, category, images, related_stocks
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    news['id'], news['title'], news['content'], news['pub_time'], 
                    news['author'], news['source'], news['url'], news['keywords'], 
                    news['sentiment'], news['crawl_time'], news['category'], 
                    news['images'], news['related_stocks']
                ))
                
                merged_count += 1
            
            # 提交事务
            target_conn.commit()
            
            logger.info(f"数据库合并完成，合并 {merged_count} 条新闻")
            return merged_count
            
        except Exception as e:
            logger.error("数据库合并失败", e)
            return 0
        finally:
            source_conn.close()
            target_conn.close()
    
    def backup_db(self, db_path=None, backup_dir='backup'):
        """
        备份数据库
        
        Args:
            db_path: 数据库路径，如果为None则使用主数据库
            backup_dir: 备份目录
        
        Returns:
            str: 备份文件路径
        """
        if db_path is None:
            db_path = self.main_db_path
        
        # 确保备份目录存在
        os.makedirs(backup_dir, exist_ok=True)
        
        # 生成备份文件名
        db_name = os.path.basename(db_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'{db_name}_{timestamp}.bak')
        
        try:
            # 复制数据库文件
            shutil.copy2(db_path, backup_file)
            
            logger.info(f"数据库备份完成: {backup_file}")
            return backup_file
            
        except Exception as e:
            logger.error(f"数据库备份失败: {db_path}", e)
            return None
    
    def restore_db(self, backup_file, db_path=None):
        """
        恢复数据库
        
        Args:
            backup_file: 备份文件路径
            db_path: 数据库路径，如果为None则使用主数据库
        
        Returns:
            bool: 是否恢复成功
        """
        if db_path is None:
            db_path = self.main_db_path
        
        try:
            # 复制备份文件到数据库文件
            shutil.copy2(backup_file, db_path)
            
            logger.info(f"数据库恢复完成: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"数据库恢复失败: {backup_file} -> {db_path}", e)
            return False
    
    def export_data(self, db_path=None, output_file=None, format='json'):
        """
        导出数据
        
        Args:
            db_path: 数据库路径，如果为None则使用主数据库
            output_file: 输出文件路径，如果为None则使用默认路径
            format: 导出格式，支持json和csv
        
        Returns:
            str: 输出文件路径
        """
        if db_path is None:
            db_path = self.main_db_path
        
        if output_file is None:
            # 生成输出文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = 'data'
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f'export_{timestamp}.{format}')
        
        # 连接数据库
        conn = self.get_connection(db_path)
        
        try:
            # 获取所有新闻
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM news')
            news_list = cursor.fetchall()
            
            # 将查询结果转换为字典列表
            columns = [column[0] for column in cursor.description]
            data = []
            for row in news_list:
                news_dict = dict(zip(columns, row))
                data.append(news_dict)
            
            # 导出数据
            if format == 'json':
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            elif format == 'csv':
                import csv
                with open(output_file, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=columns)
                    writer.writeheader()
                    writer.writerows(data)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
            
            logger.info(f"数据导出完成: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"数据导出失败: {db_path} -> {output_file}", e)
            return None
        finally:
            conn.close()
    
    def import_data(self, input_file, db_path=None, format='json'):
        """
        导入数据
        
        Args:
            input_file: 输入文件路径
            db_path: 数据库路径，如果为None则使用主数据库
            format: 导入格式，支持json和csv
        
        Returns:
            int: 导入的新闻数量
        """
        if db_path is None:
            db_path = self.main_db_path
        
        # 连接数据库
        conn = self.get_connection(db_path)
        
        try:
            # 初始化数据库
            self.init_db(conn)
            
            # 获取已存在的新闻ID
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM news')
            existing_ids = set(row[0] for row in cursor.fetchall())
            
            # 导入数据
            data = []
            if format == 'json':
                with open(input_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            elif format == 'csv':
                import csv
                with open(input_file, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.DictReader(f)
                    data = list(reader)
            else:
                raise ValueError(f"不支持的导入格式: {format}")
            
            # 插入新闻
            imported_count = 0
            for news in data:
                # 如果新闻ID已存在，则跳过
                if news['id'] in existing_ids:
                    continue
                
                # 插入新闻
                conn.execute('''
                    INSERT INTO news (
                        id, title, content, pub_time, author, source, url, 
                        keywords, sentiment, crawl_time, category, images, related_stocks
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    news['id'], news['title'], news['content'], news['pub_time'], 
                    news['author'], news['source'], news['url'], news['keywords'], 
                    news['sentiment'], news['crawl_time'], news['category'], 
                    news['images'], news['related_stocks']
                ))
                
                imported_count += 1
            
            # 提交事务
            conn.commit()
            
            logger.info(f"数据导入完成，导入 {imported_count} 条新闻")
            return imported_count
            
        except Exception as e:
            logger.error(f"数据导入失败: {input_file} -> {db_path}", e)
            return 0
        finally:
            conn.close()
    
    def get_db_stats(self, db_path=None):
        """
        获取数据库统计信息
        
        Args:
            db_path: 数据库路径，如果为None则使用主数据库
        
        Returns:
            dict: 数据库统计信息
        """
        if db_path is None:
            db_path = self.main_db_path
        
        # 连接数据库
        conn = self.get_connection(db_path)
        
        try:
            # 获取统计信息
            cursor = conn.cursor()
            
            # 总新闻数
            cursor.execute('SELECT COUNT(*) FROM news')
            total_news = cursor.fetchone()[0]
            
            # 来源统计
            cursor.execute('SELECT source, COUNT(*) FROM news GROUP BY source')
            sources = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 分类统计
            cursor.execute('SELECT category, COUNT(*) FROM news GROUP BY category')
            categories = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 日期范围
            cursor.execute('SELECT MIN(pub_time), MAX(pub_time) FROM news')
            date_range = cursor.fetchone()
            
            # 文件大小
            file_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
            
            # 统计信息
            stats = {
                'db_path': db_path,
                'total_news': total_news,
                'sources': sources,
                'categories': categories,
                'date_range': {
                    'min': date_range[0],
                    'max': date_range[1]
                },
                'file_size': round(file_size, 2)  # MB
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取数据库统计信息失败: {db_path}", e)
            return None
        finally:
            conn.close()
    
    def list_databases(self):
        """
        列出所有数据库
        
        Returns:
            list: 数据库列表
        """
        try:
            # 获取数据库目录中的所有数据库文件
            db_files = []
            for file in os.listdir(self.db_dir):
                if file.endswith('.db'):
                    db_files.append(os.path.join(self.db_dir, file))
            
            return db_files
            
        except Exception as e:
            logger.error("列出数据库失败", e)
            return []
    
    def vacuum_db(self, db_path=None):
        """
        压缩数据库
        
        Args:
            db_path: 数据库路径，如果为None则使用主数据库
        
        Returns:
            bool: 是否压缩成功
        """
        if db_path is None:
            db_path = self.main_db_path
        
        # 连接数据库
        conn = self.get_connection(db_path)
        
        try:
            # 压缩数据库
            conn.execute('VACUUM')
            
            logger.info(f"数据库压缩完成: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"数据库压缩失败: {db_path}", e)
            return False
        finally:
            conn.close()
    
    def delete_news(self, news_id, db_path=None):
        """
        删除新闻
        
        Args:
            news_id: 新闻ID
            db_path: 数据库路径，如果为None则使用主数据库
        
        Returns:
            bool: 是否删除成功
        """
        if db_path is None:
            db_path = self.main_db_path
        
        # 连接数据库
        conn = self.get_connection(db_path)
        
        try:
            # 删除新闻
            cursor = conn.cursor()
            cursor.execute('DELETE FROM news WHERE id = ?', (news_id,))
            
            # 提交事务
            conn.commit()
            
            # 检查是否删除成功
            if cursor.rowcount > 0:
                logger.info(f"删除新闻成功: {news_id}")
                return True
            else:
                logger.warning(f"删除新闻失败，新闻不存在: {news_id}")
                return False
            
        except Exception as e:
            logger.error(f"删除新闻失败: {news_id}", e)
            return False
        finally:
            conn.close()
    
    def search_news(self, keyword, db_path=None):
        """
        搜索新闻
        
        Args:
            keyword: 关键词
            db_path: 数据库路径，如果为None则使用主数据库
        
        Returns:
            list: 新闻列表
        """
        if db_path is None:
            db_path = self.main_db_path
        
        # 连接数据库
        conn = self.get_connection(db_path)
        
        try:
            # 搜索新闻
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM news 
                WHERE title LIKE ? OR content LIKE ? OR keywords LIKE ? 
                ORDER BY pub_time DESC
            ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
            
            # 获取搜索结果
            news_list = cursor.fetchall()
            
            # 将查询结果转换为字典列表
            columns = [column[0] for column in cursor.description]
            result = []
            for row in news_list:
                news_dict = dict(zip(columns, row))
                result.append(news_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"搜索新闻失败: {keyword}", e)
            return []
        finally:
            conn.close()
    
    def close_connection(self, conn):
        """
        关闭数据库连接
        
        Args:
            conn: 数据库连接
        """
        if conn:
            conn.close()
            logger.debug("数据库连接已关闭") 