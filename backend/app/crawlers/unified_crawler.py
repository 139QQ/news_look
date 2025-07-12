#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 统一爬虫引擎
使用策略模式和组件组合实现的统一爬虫引擎
"""

import os
import sys
import time
import random
import asyncio
import logging
import aiohttp
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple, Union
from urllib.parse import urlparse

from backend.app.utils.logger import get_logger
from backend.app.utils.database import DatabaseManager
from backend.app.crawlers.strategies import BaseCrawlerStrategy, get_strategy
from backend.app.utils.text_cleaner import clean_html, decode_html_entities, decode_unicode_escape

logger = get_logger('unified_crawler')

class UnifiedCrawler:
    """
    统一爬虫引擎，使用策略模式和组件组合实现
    支持同步和异步爬取，自动根据环境选择最佳方式
    """
    
    def __init__(self, source: str, db_path: str = None, db_manager=None, 
                 use_proxy: bool = False, async_mode: bool = True,
                 max_workers: int = 5, max_concurrency: int = 10,
                 timeout: int = 30, **kwargs):
        """
        初始化统一爬虫引擎
        
        Args:
            source: 新闻来源名称
            db_path: 数据库路径
            db_manager: 数据库管理器对象
            use_proxy: 是否使用代理
            async_mode: 是否使用异步模式
            max_workers: 最大工作线程数（线程池大小）
            max_concurrency: 最大并发请求数（异步模式）
            timeout: 请求超时时间（秒）
            **kwargs: 其他参数
        """
        self.source = source
        self.db_path = db_path
        self.use_proxy = use_proxy
        self.async_mode = async_mode
        self.max_workers = max_workers
        self.max_concurrency = max_concurrency
        self.timeout = timeout
        
        # 记录已处理的URL
        self.processed_urls = set()
        
        # 统计信息
        self.stats = {
            "start_time": None,
            "end_time": None,
            "total_urls": 0,
            "processed_urls": 0,
            "success_urls": 0,
            "failed_urls": 0,
            "articles_count": 0,
            "avg_process_time": 0,
            "total_process_time": 0,
        }
        
        # 加载爬虫策略
        self._init_strategy()
        
        # 初始化数据库
        self._init_database(db_manager)
        
        # 初始化HTTP会话
        self._init_session()
        
        # 初始化请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 记录配置
        logger.info(f"统一爬虫引擎初始化完成: 源={source}, 异步模式={async_mode}, 最大线程={max_workers}, 最大并发={max_concurrency}")
        
    def _init_strategy(self):
        """初始化爬虫策略"""
        # 获取对应的策略类
        strategy_class = get_strategy(self.source)
        if not strategy_class:
            raise ValueError(f"未找到源 '{self.source}' 对应的爬虫策略")
            
        # 实例化策略
        self.strategy = strategy_class(self.source)
        
    def _init_database(self, db_manager):
        """初始化数据库连接"""
        if db_manager:
            # 使用提供的数据库管理器
            self.db_manager = db_manager
        else:
            # 创建新的数据库管理器
            self.db_manager = DatabaseManager()
            
        # 如果提供了数据库路径，确保目录存在
        if self.db_path:
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                
            # 连接到数据库
            self.conn = self.db_manager.get_connection(self.db_path)
            # 确保表结构存在
            self.db_manager.init_db(self.conn)
        else:
            self.conn = None
            
    def _init_session(self):
        """初始化HTTP会话"""
        if not self.async_mode:
            # 同步会话
            self.session = requests.Session()
            self.session.headers.update(self.headers)
        else:
            # 异步会话将在需要时创建
            self.session = None
            self.semaphore = None
            
    async def _get_async_session(self):
        """获取异步会话"""
        if self.session is None or getattr(self.session, 'closed', False):
            # 创建新的异步会话
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
            
        if self.semaphore is None:
            # 创建并发控制信号量
            self.semaphore = asyncio.Semaphore(self.max_concurrency)
            
        return self.session
        
    async def _close_async_session(self):
        """关闭异步会话"""
        if self.session and not getattr(self.session, 'closed', True):
            await self.session.close()
            self.session = None
            
    def crawl(self, days: int = 1, max_news: int = None, 
             category: str = None, check_status: bool = True) -> List[Dict[str, Any]]:
        """
        爬取新闻的主方法
        
        Args:
            days: 爬取最近几天的新闻
            max_news: 最大爬取新闻数量，None表示不限制
            category: 要爬取的特定分类
            check_status: 是否检查网站状态
            
        Returns:
            list: 爬取的新闻列表
        """
        # 重置爬虫统计信息
        self._reset_stats()
        
        # 清空处理过的URL
        self.processed_urls.clear()
        
        # 开始计时
        self.stats["start_time"] = datetime.now()
        
        logger.info(f"开始爬取 {self.source} 的新闻，爬取天数: {days}" + 
                   (f", 分类: {category}" if category else ""))
        
        # 根据是否使用异步模式选择不同的爬取方法
        if self.async_mode:
            # 使用异步模式爬取
            news_data = asyncio.run(self._async_crawl(days, max_news, category, check_status))
        else:
            # 使用同步模式爬取
            news_data = self._sync_crawl(days, max_news, category, check_status)
            
        # 结束计时
        self.stats["end_time"] = datetime.now()
        
        # 计算统计信息
        self.stats["elapsed_time"] = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        if self.stats["elapsed_time"] > 0:
            self.stats["urls_per_second"] = self.stats["processed_urls"] / self.stats["elapsed_time"]
            
        logger.info(f"{self.source} 爬取完成，统计信息: {self.stats}")
        
        return news_data
        
    def _sync_crawl(self, days: int, max_news: Optional[int], 
                   category: Optional[str], check_status: bool) -> List[Dict[str, Any]]:
        """同步爬取实现"""
        # 获取列表页URL
        list_urls = self.strategy.get_list_urls(category, days)
        self.stats["total_urls"] = len(list_urls)
        
        # 计算起始日期
        start_date = self.strategy.get_start_date(days)
        
        # 存储爬取的新闻
        news_data = []
        
        # 使用线程池并行处理列表页
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 创建列表页爬取任务
            list_futures = {
                executor.submit(self._process_list_page, url, start_date): url
                for url in list_urls
            }
            
            # 收集所有文章链接
            article_infos = []
            for future in as_completed(list_futures):
                url = list_futures[future]
                try:
                    # 获取列表页的文章信息
                    page_article_infos = future.result()
                    article_infos.extend(page_article_infos)
                except Exception as e:
                    logger.error(f"处理列表页 {url} 失败: {str(e)}")
                    
        # 限制最大新闻数量
        if max_news and len(article_infos) > max_news:
            article_infos = article_infos[:max_news]
            
        # 使用线程池并行处理文章详情页
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 创建详情页爬取任务
            detail_futures = {
                executor.submit(self._process_detail_page, info): info['url']
                for info in article_infos
            }
            
            # 收集所有文章数据
            for future in as_completed(detail_futures):
                url = detail_futures[future]
                try:
                    # 获取文章详情
                    article = future.result()
                    if article:
                        news_data.append(article)
                        # 保存到数据库
                        if self.conn:
                            self._save_article(article)
                except Exception as e:
                    logger.error(f"处理详情页 {url} 失败: {str(e)}")
                    
        self.stats["articles_count"] = len(news_data)
        return news_data
        
    async def _async_crawl(self, days: int, max_news: Optional[int], 
                         category: Optional[str], check_status: bool) -> List[Dict[str, Any]]:
        """异步爬取实现"""
        # 获取列表页URL
        list_urls = self.strategy.get_list_urls(category, days)
        self.stats["total_urls"] = len(list_urls)
        
        # 计算起始日期
        start_date = self.strategy.get_start_date(days)
        
        # 存储爬取的新闻
        news_data = []
        
        try:
            # 获取异步会话
            session = await self._get_async_session()
            
            # 并发爬取列表页
            list_tasks = [
                self._async_process_list_page(url, start_date, session)
                for url in list_urls
            ]
            
            # 等待所有列表页任务完成
            list_results = await asyncio.gather(*list_tasks, return_exceptions=True)
            
            # 收集所有文章链接
            article_infos = []
            for result in list_results:
                if isinstance(result, Exception):
                    logger.error(f"处理列表页异常: {str(result)}")
                    continue
                article_infos.extend(result)
                
            # 限制最大新闻数量
            if max_news and len(article_infos) > max_news:
                article_infos = article_infos[:max_news]
                
            # 并发爬取详情页
            detail_tasks = [
                self._async_process_detail_page(info, session)
                for info in article_infos
            ]
            
            # 等待所有详情页任务完成
            detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)
            
            # 收集所有文章数据
            for result in detail_results:
                if isinstance(result, Exception):
                    logger.error(f"处理详情页异常: {str(result)}")
                    continue
                    
                if result:
                    news_data.append(result)
                    # 保存到数据库
                    if self.conn:
                        self._save_article(result)
                        
        finally:
            # 关闭异步会话
            await self._close_async_session()
            
        self.stats["articles_count"] = len(news_data)
        return news_data
        
    def _process_list_page(self, url: str, start_date: datetime) -> List[Dict[str, Any]]:
        """处理列表页，提取文章链接和基本信息"""
        try:
            # 获取列表页内容
            html = self._fetch_page(url)
            if not html:
                return []
                
            # 解析列表页
            articles = self.strategy.parse_list_page(html, url)
            
            # 过滤日期范围外的文章
            filtered_articles = []
            for article in articles:
                article_url = article['url']
                
                # 只处理未处理过的URL
                if article_url in self.processed_urls:
                    continue
                    
                # 检查URL是否应该爬取
                if not self.strategy.should_crawl_url(article_url):
                    continue
                    
                # 检查日期范围
                if not self.strategy.is_url_in_date_range(article_url, start_date):
                    continue
                    
                # 标记为已处理
                self.processed_urls.add(article_url)
                filtered_articles.append(article)
                
            logger.debug(f"列表页 {url} 提取到 {len(filtered_articles)}/{len(articles)} 篇文章")
            return filtered_articles
            
        except Exception as e:
            logger.error(f"处理列表页 {url} 异常: {str(e)}")
            return []
            
    async def _async_process_list_page(self, url: str, start_date: datetime, 
                                     session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """异步处理列表页，提取文章链接和基本信息"""
        try:
            # 获取列表页内容
            html = await self._async_fetch_page(url, session)
            if not html:
                return []
                
            # 解析列表页
            articles = self.strategy.parse_list_page(html, url)
            
            # 过滤日期范围外的文章
            filtered_articles = []
            for article in articles:
                article_url = article['url']
                
                # 只处理未处理过的URL（使用异步锁保护）
                if article_url in self.processed_urls:
                    continue
                    
                # 检查URL是否应该爬取
                if not self.strategy.should_crawl_url(article_url):
                    continue
                    
                # 检查日期范围
                if not self.strategy.is_url_in_date_range(article_url, start_date):
                    continue
                    
                # 标记为已处理
                self.processed_urls.add(article_url)
                filtered_articles.append(article)
                
            logger.debug(f"列表页 {url} 提取到 {len(filtered_articles)}/{len(articles)} 篇文章")
            return filtered_articles
            
        except Exception as e:
            logger.error(f"处理列表页 {url} 异常: {str(e)}")
            return []
            
    def _process_detail_page(self, basic_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理详情页，提取文章完整内容"""
        url = basic_info['url']
        try:
            # 获取详情页内容
            html = self._fetch_page(url)
            if not html:
                return None
                
            # 解析详情页
            article = self.strategy.parse_detail_page(html, url, basic_info)
            
            # 处理结果
            if article:
                # 增加来源信息
                article['source'] = self.source
                # 增加爬取时间
                if 'crawl_time' not in article:
                    article['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
            self.stats["success_urls"] += 1
            return article
            
        except Exception as e:
            logger.error(f"处理详情页 {url} 异常: {str(e)}")
            self.stats["failed_urls"] += 1
            return None
            
    async def _async_process_detail_page(self, basic_info: Dict[str, Any], 
                                       session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        """异步处理详情页，提取文章完整内容"""
        url = basic_info['url']
        try:
            # 获取详情页内容
            html = await self._async_fetch_page(url, session)
            if not html:
                return None
                
            # 解析详情页
            article = self.strategy.parse_detail_page(html, url, basic_info)
            
            # 处理结果
            if article:
                # 增加来源信息
                article['source'] = self.source
                # 增加爬取时间
                if 'crawl_time' not in article:
                    article['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
            self.stats["success_urls"] += 1
            return article
            
        except Exception as e:
            logger.error(f"处理详情页 {url} 异常: {str(e)}")
            self.stats["failed_urls"] += 1
            return None
            
    def _fetch_page(self, url: str) -> Optional[str]:
        """同步获取页面内容"""
        try:
            # 随机延迟，避免请求过快
            time.sleep(random.uniform(0.5, 1.5))
            
            # 发送请求
            response = self.session.get(url, timeout=self.timeout)
            
            # 检查状态码
            if response.status_code != 200:
                logger.warning(f"获取页面失败: {url}, 状态码: {response.status_code}")
                return None
                
            # 获取内容
            html = response.text
            
            # 特殊编码处理
            html = decode_html_entities(html)
            html = decode_unicode_escape(html)
            
            return html
            
        except Exception as e:
            logger.error(f"获取页面异常: {url}, 错误: {str(e)}")
            return None
            
    async def _async_fetch_page(self, url: str, session: aiohttp.ClientSession) -> Optional[str]:
        """异步获取页面内容"""
        try:
            # 使用信号量控制并发
            async with self.semaphore:
                # 随机延迟，避免请求过快
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # 发送请求
                async with session.get(url, timeout=self.timeout) as response:
                    # 检查状态码
                    if response.status != 200:
                        logger.warning(f"获取页面失败: {url}, 状态码: {response.status}")
                        return None
                        
                    # 获取内容
                    html = await response.text()
                    
                    # 特殊编码处理
                    html = decode_html_entities(html)
                    html = decode_unicode_escape(html)
                    
                    return html
                    
        except Exception as e:
            logger.error(f"异步获取页面异常: {url}, 错误: {str(e)}")
            return None
            
    def _save_article(self, article: Dict[str, Any]) -> bool:
        """保存文章到数据库"""
        if not self.conn:
            return False
            
        try:
            # 确保文章具有所有必需的字段
            required_fields = ['title', 'content', 'url', 'publish_time', 'source']
            for field in required_fields:
                if field not in article:
                    logger.warning(f"文章缺少必需字段: {field}, URL: {article.get('url', 'unknown')}")
                    return False
                    
            # 准备SQL语句
            sql = """
            INSERT INTO news (
                title, content, url, publish_time, crawl_time, source, 
                category, author, image_url, summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            # 执行插入
            cursor = self.conn.cursor()
            cursor.execute(sql, (
                article.get('title', ''),
                article.get('content', ''),
                article.get('url', ''),
                article.get('publish_time', ''),
                article.get('crawl_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                article.get('source', self.source),
                article.get('category', ''),
                article.get('author', ''),
                article.get('image_url', ''),
                article.get('summary', '')
            ))
            
            # 如果有相关股票，保存股票信息
            if 'related_stocks' in article and article['related_stocks']:
                self._save_related_stocks(article['url'], article['related_stocks'])
                
            # 提交事务
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"保存文章失败: {str(e)}, URL: {article.get('url', 'unknown')}")
            # 回滚事务
            self.conn.rollback()
            return False
            
    def _save_related_stocks(self, article_url: str, stocks: List[Dict[str, Any]]) -> bool:
        """保存文章相关股票信息"""
        if not self.conn:
            return False
            
        try:
            # 检查是否存在相关股票表，如果不存在则创建
            cursor = self.conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS article_stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_url TEXT,
                code TEXT,
                name TEXT,
                exchange TEXT,
                UNIQUE(article_url, code, exchange)
            )
            """)
            
            # 批量插入相关股票
            for stock in stocks:
                try:
                    cursor.execute("""
                    INSERT OR IGNORE INTO article_stocks (article_url, code, name, exchange)
                    VALUES (?, ?, ?, ?)
                    """, (
                        article_url,
                        stock.get('code', ''),
                        stock.get('name', ''),
                        stock.get('exchange', '')
                    ))
                except Exception as e:
                    logger.warning(f"保存股票信息失败: {str(e)}, URL: {article_url}, 股票: {stock}")
                    
            # 提交事务
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"保存相关股票失败: {str(e)}, URL: {article_url}")
            # 回滚事务
            self.conn.rollback()
            return False
            
    def _reset_stats(self):
        """重置爬虫统计信息"""
        self.stats = {
            "start_time": None,
            "end_time": None,
            "total_urls": 0,
            "processed_urls": 0,
            "success_urls": 0,
            "failed_urls": 0,
            "articles_count": 0,
            "avg_process_time": 0,
            "total_process_time": 0,
        }
        
    def get_stats(self) -> Dict[str, Any]:
        """获取爬虫统计信息"""
        return self.stats
        
    def close(self):
        """关闭爬虫，释放资源"""
        try:
            # 关闭数据库连接
            if self.conn:
                self.conn.close()
                self.conn = None
                
            # 关闭同步会话
            if not self.async_mode and self.session:
                self.session.close()
                self.session = None
                
            # 异步会话会在异步爬取完成后自动关闭
                
            logger.info(f"{self.source} 爬虫已关闭")
            
        except Exception as e:
            logger.error(f"关闭爬虫资源异常: {str(e)}")
            
    def __del__(self):
        """析构函数，确保资源被释放"""
        self.close() 