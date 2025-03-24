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
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from app.config import get_settings
from app.utils.logger import get_logger

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
    publish_time = Column(DateTime)
    crawl_time = Column(DateTime, default=datetime.now)
    keywords = Column(Text)  # JSON格式存储关键词列表

class NewsDatabase:
    """新闻数据库工具类"""
    
    def __init__(self):
        """初始化数据库连接"""
        settings = get_settings()
        
        # 确保DB_DIR存在
        db_dir = settings.get('DB_DIR', os.path.join(os.getcwd(), 'data', 'db'))
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        if settings.get('db_type', 'sqlite') == 'sqlite':
            db_path = os.path.join(db_dir, 'news.db')
            self.engine = create_engine(f'sqlite:///{db_path}')
        else:
            db_user = settings.get('db_user', '')
            db_password = settings.get('db_password', '')
            db_host = settings.get('db_host', 'localhost')
            db_port = settings.get('db_port', 3306)
            db_name = settings.get('db_name', 'news')
            db_type = settings.get('db_type', 'mysql')
            db_url = f"{db_type}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            self.engine = create_engine(db_url)
        
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
                    elif 'sina.com' in url:
                        source = '新浪财经'
                    elif 'finance.qq.com' in url:
                        source = '腾讯财经'
                
            # 创建新闻对象
            news = News(
                title=news_data['title'],
                content=news_data['content'],
                url=news_data['url'],
                source=source,
                category=news_data.get('category', '财经'),
                publish_time=pub_time,
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
        """查询新闻"""
        query = self.session.query(News)
        
        if keyword:
            query = query.filter(News.title.like(f'%{keyword}%'))
        
        if days:
            start_time = datetime.now() - timedelta(days=days)
            query = query.filter(News.publish_time >= start_time)
        
        if source:
            query = query.filter(News.source == source)
        
        query = query.order_by(News.publish_time.desc())
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def get_news_count(self, keyword=None, days=None, source=None, start_date=None, end_date=None):
        """获取新闻数量"""
        query = self.session.query(News)
        
        if keyword:
            query = query.filter(News.title.like(f'%{keyword}%'))
        
        if days:
            start_time = datetime.now() - timedelta(days=days)
            query = query.filter(News.publish_time >= start_time)
        
        if source:
            query = query.filter(News.source == source)
        
        if start_date:
            query = query.filter(News.publish_time >= start_date)
        
        if end_date:
            query = query.filter(News.publish_time < end_date)
        
        return query.count()
    
    def get_sources(self):
        """获取新闻来源统计"""
        result = self.session.query(
            News.source,
            func.count(News.id).label('count')
        ).group_by(News.source).all()
        
        return [{'name': row[0], 'count': row[1]} for row in result]
    
    def get_keywords(self, limit=50):
        """获取热门关键词"""
        # 从所有新闻中提取关键词并统计
        all_keywords = {}
        news_list = self.session.query(News.keywords).all()
        
        for news in news_list:
            if news[0]:
                keywords = json.loads(news[0])
                for keyword in keywords:
                    all_keywords[keyword] = all_keywords.get(keyword, 0) + 1
        
        # 按出现次数排序
        sorted_keywords = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)
        return [{'word': word, 'count': count} for word, count in sorted_keywords[:limit]]
    
    def get_categories(self):
        """获取新闻分类统计"""
        result = self.session.query(
            News.category,
            func.count(News.id).label('count')
        ).group_by(News.category).all()
        
        # 计算每个分类的趋势（与前一天相比的变化）
        categories = []
        for row in result:
            category = row[0]
            count = row[1]
            
            # 获取昨天的数据
            yesterday = datetime.now() - timedelta(days=1)
            yesterday_count = self.session.query(News).filter(
                News.category == category,
                News.publish_time >= yesterday,
                News.publish_time < datetime.now()
            ).count()
            
            # 计算趋势
            trend = count - yesterday_count
            
            categories.append({
                'name': category,
                'count': count,
                'trend': trend
            })
        
        return categories
    
    def get_news_by_id(self, news_id):
        """根据ID获取新闻"""
        return self.session.query(News).filter(News.id == news_id).first()
    
    def update_news(self, news_id, news_data):
        """更新新闻"""
        try:
            news = self.get_news_by_id(news_id)
            if news:
                for key, value in news_data.items():
                    setattr(news, key, value)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            raise e
    
    def delete_news(self, news_id):
        """删除新闻"""
        try:
            news = self.get_news_by_id(news_id)
            if news:
                self.session.delete(news)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            raise e
    
    def close(self):
        """关闭数据库连接"""
        self.session.close()

class DatabaseManager:
    """数据库管理器，提供数据库连接和初始化功能"""
    
    def __init__(self, db_dir='db'):
        """
        初始化数据库管理器
        
        Args:
            db_dir: 数据库目录
        """
        self.db_dir = db_dir
        
        # 确保数据库目录存在
        os.makedirs(db_dir, exist_ok=True)
        
        # 主数据库路径
        self.main_db_path = os.path.join(db_dir, 'finance_news.db')
    
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
        # 创建新闻表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                pub_time TEXT NOT NULL,
                author TEXT,
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                keywords TEXT,
                sentiment REAL,
                crawl_time TEXT NOT NULL,
                category TEXT,
                images TEXT,
                related_stocks TEXT
            )
        ''')
        
        # 创建索引
        conn.execute('CREATE INDEX IF NOT EXISTS idx_news_source ON news (source)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_news_pub_time ON news (pub_time)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_news_category ON news (category)')
        
        # 提交事务
        conn.commit()
        
        logger.debug("数据库初始化完成")
    
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