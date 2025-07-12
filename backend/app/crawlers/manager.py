#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 爬虫管理器
"""

import os
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union, Tuple
from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.database import NewsDatabase
from app.crawlers.base import BaseCrawler
from app.crawlers.factory import CrawlerFactory
import re
import sqlite3

logger = get_logger(__name__)

class CrawlerManager:
    """爬虫管理器，负责管理所有爬虫"""
    
    def __init__(self):
        """初始化爬虫管理器"""
        self.settings = get_settings()
        self.factory = CrawlerFactory()
        self.crawlers_path = os.path.join(os.path.dirname(__file__), 'sites')
        self.crawlers_cache = {}  # 缓存已创建的爬虫实例
        self.db = NewsDatabase()  # 主数据库连接
        
        # 初始化爬虫目录
        self._init_crawlers_dir()
    
    def _init_crawlers_dir(self):
        """初始化爬虫目录"""
        # 确保爬虫目录存在
        if not os.path.exists(self.crawlers_path):
            logger.info(f"创建爬虫目录: {self.crawlers_path}")
            os.makedirs(self.crawlers_path, exist_ok=True)
        
        # 确保__init__.py存在
        init_file = os.path.join(self.crawlers_path, '__init__.py')
        if not os.path.exists(init_file):
            logger.info(f"创建爬虫包初始化文件: {init_file}")
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write('# -*- coding: utf-8 -*-\n')
                f.write('"""爬虫实现目录"""\n')
    
    def get_available_crawlers(self) -> List[str]:
        """
        获取所有可用的爬虫列表
        
        Returns:
            List[str]: 爬虫名称列表
        """
        crawlers = []
        
        # 扫描爬虫目录
        for filename in os.listdir(self.crawlers_path):
            if filename.endswith('.py') and filename != '__init__.py':
                crawler_name = filename[:-3]  # 去掉.py后缀
                crawlers.append(crawler_name)
        
        return crawlers
    
    def get_crawler_info(self, crawler_name: str) -> Dict[str, Any]:
        """
        获取指定爬虫的信息
        
        Args:
            crawler_name: 爬虫名称
            
        Returns:
            Dict: 爬虫信息字典
        """
        # 尝试创建爬虫实例
        try:
            crawler = self.factory.create_crawler(crawler_name)
            if not crawler:
                return {
                    'name': crawler_name,
                    'status': 'error',
                    'message': '爬虫创建失败'
                }
            
            # 获取爬虫信息
            info = {
                'name': crawler_name,
                'source': crawler.source,
                'class': crawler.__class__.__name__,
                'description': crawler.__doc__ or '无描述',
                'status': 'available',
                'capabilities': getattr(crawler, 'capabilities', {}),
                'config': getattr(crawler, 'config', {})
            }
            
            # 获取爬虫统计信息
            source_db = NewsDatabase(source=crawler_name)
            today_count = source_db.get_news_count(days=1, source=crawler_name)
            week_count = source_db.get_news_count(days=7, source=crawler_name)
            month_count = source_db.get_news_count(days=30, source=crawler_name)
            total_count = source_db.get_news_count(source=crawler_name)
            source_db.close()
            
            info['statistics'] = {
                'today': today_count,
                'week': week_count,
                'month': month_count,
                'total': total_count
            }
            
            return info
            
        except Exception as e:
            logger.error(f"获取爬虫信息失败 {crawler_name}: {e}")
            return {
                'name': crawler_name,
                'status': 'error',
                'message': str(e)
            }
    
    def get_all_crawler_info(self) -> List[Dict[str, Any]]:
        """
        获取所有爬虫的信息
        
        Returns:
            List[Dict]: 爬虫信息列表
        """
        crawler_list = []
        
        # 获取所有可用爬虫
        available_crawlers = self.get_available_crawlers()
        
        # 获取每个爬虫的信息
        for crawler_name in available_crawlers:
            info = self.get_crawler_info(crawler_name)
            crawler_list.append(info)
        
        return crawler_list
    
    def run_crawler(self, crawler_name: str, days: float = 7.0, 
                   force_update: bool = False, 
                   use_dedicated_db: bool = True,
                   sync_to_main: bool = True) -> int:
        """
        运行指定的爬虫
        
        Args:
            crawler_name: 爬虫名称
            days: 爬取过去几天的新闻
            force_update: 是否强制更新已存在的新闻
            use_dedicated_db: 是否使用爬虫专用数据库
            sync_to_main: 是否同步数据到主数据库
            
        Returns:
            int: 成功爬取的新闻数量
        """
        # 获取缓存中的爬虫，如果没有则创建新的
        if crawler_name in self.crawlers_cache:
            crawler = self.crawlers_cache[crawler_name]
        else:
            # 如果使用专用数据库，则传入对应数据库路径
            db_path = None
            if use_dedicated_db:
                db = NewsDatabase(source=crawler_name)
                db_path = db.db_path
                db.close()
            
            # 创建爬虫实例
            crawler = self.factory.create_crawler(
                crawler_name, 
                db_path=db_path
            )
            
            # 缓存爬虫实例
            self.crawlers_cache[crawler_name] = crawler
        
        if not crawler:
            logger.error(f"爬虫 {crawler_name} 创建失败")
            return 0
        
        try:
            # 运行爬虫
            logger.info(f"开始运行爬虫: {crawler_name}, 爬取时间范围: {days}天")
            count = crawler.crawl(days=days, force_update=force_update)
            logger.info(f"爬虫 {crawler_name} 运行完成，获取 {count} 条新闻")
            
            # 如果使用专用数据库且需要同步到主数据库
            if use_dedicated_db and sync_to_main and count > 0:
                self._sync_to_main_db(crawler_name)
            
            return count
        except Exception as e:
            logger.error(f"爬虫 {crawler_name} 运行失败: {e}")
            return 0
    
    def _sync_to_main_db(self, source: str) -> int:
        """
        将源数据库的数据同步到主数据库
        
        Args:
            source: 数据源名称
            
        Returns:
            int: 同步的记录数
        """
        # 创建源数据库连接
        source_db = NewsDatabase(source=source)
        main_db = self.db
        sync_count = 0
        
        try:
            # 获取源数据库中的数据
            news_list = source_db.query_news(source=source, limit=1000)
            if not news_list:
                logger.info(f"数据源 {source} 没有需要同步的数据")
                return 0
            
            logger.info(f"开始同步数据源 {source} 到主数据库，共 {len(news_list)} 条记录")
            
            # 添加到主数据库
            for news in news_list:
                try:
                    # 检查主数据库是否已存在该新闻
                    conn = main_db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1 FROM news WHERE url = ?", (news['url'],))
                    exists = cursor.fetchone() is not None
                    conn.close()
                    
                    if not exists:
                        # 使用直接的SQL语句保存新闻
                        conn = main_db.get_connection()
                        cursor = conn.cursor()
                        
                        # 获取表字段
                        cursor.execute("PRAGMA table_info(news)")
                        columns = [row[1] for row in cursor.fetchall()]
                        
                        # 过滤新闻数据，只保留表中存在的字段
                        filtered_data = {k: v for k, v in news.items() if k in columns}
                        
                        # 构建SQL语句
                        fields = ', '.join(filtered_data.keys())
                        placeholders = ', '.join(['?' for _ in filtered_data])
                        values = list(filtered_data.values())
                        
                        cursor.execute(f"INSERT INTO news ({fields}) VALUES ({placeholders})", values)
                        conn.commit()
                        conn.close()
                        
                        sync_count += 1
                except Exception as e:
                    logger.error(f"同步记录失败 {news.get('id', '')}: {e}")
            
            logger.info(f"数据源 {source} 同步完成，共同步 {sync_count} 条记录")
            return sync_count
            
        except Exception as e:
            logger.error(f"同步数据源 {source} 失败: {e}")
            return 0
        finally:
            # 关闭源数据库连接
            source_db.close()
    
    def sync_all_to_main(self) -> Dict[str, int]:
        """
        将所有数据源的数据同步到主数据库
        
        Returns:
            Dict[str, int]: 每个数据源同步的记录数
        """
        result = {}
        
        # 获取所有数据源
        sources = self.db.get_available_sources()
        logger.info(f"开始同步所有数据源到主数据库，共 {len(sources)} 个数据源")
        
        # 同步每个数据源
        for source in sources:
            try:
                count = self._sync_to_main_db(source)
                result[source] = count
            except Exception as e:
                logger.error(f"同步数据源 {source} 失败: {e}")
                result[source] = 0
        
        logger.info(f"所有数据源同步完成，结果: {result}")
        return result
    
    def close(self):
        """关闭爬虫管理器，清理资源"""
        # 关闭所有爬虫实例
        for crawler_name, crawler in self.crawlers_cache.items():
            try:
                crawler.close()
            except Exception as e:
                logger.error(f"关闭爬虫 {crawler_name} 失败: {e}")
        
        # 清空爬虫缓存
        self.crawlers_cache.clear()
        
        # 关闭数据库连接
        self.db.close()
        
        logger.info("爬虫管理器已关闭")
