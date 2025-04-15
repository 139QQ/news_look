#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 异步爬虫基类
提供异步爬取功能，通过aiohttp高效执行并发请求
"""

import os
import sys
import time
import random
import asyncio
import logging
import aiohttp
from datetime import datetime, timedelta
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html, extract_keywords, decode_html_entities, decode_unicode_escape, decode_url_encoded
from app.utils.db_transaction import TransactionalDBManager, create_db_manager, DEFAULT_TABLE_SCHEMAS
from app.utils.performance_monitor import monitor_crawler, track_request, track_db_operation, track_news_saved

# 异步爬虫日志记录器
logger = get_crawler_logger('async_crawler')

class AsyncCrawler(BaseCrawler):
    """异步爬虫基类，提供异步爬取能力"""
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, 
                 max_concurrency=5, timeout=30, **kwargs):
        """
        初始化异步爬虫基类
        
        Args:
            db_manager: 数据库管理器对象
            db_path: 数据库路径，如果为None则使用默认路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
            max_concurrency: 最大并发请求数
            timeout: 请求超时时间（秒）
            **kwargs: 其他参数
        """
        super().__init__(db_manager=db_manager, db_path=db_path, use_proxy=use_proxy, 
                        use_source_db=use_source_db, **kwargs)
        
        # 异步特有属性
        self.max_concurrency = max_concurrency
        self.timeout = timeout
        self.session = None  # 异步会话，在运行时初始化
        self.semaphore = None  # 并发控制器，在运行时初始化
        
        # 请求统计
        self.request_stats = {
            "total": 0,
            "success": 0,
            "failure": 0,
            "start_time": None,
            "end_time": None,
            "avg_response_time": 0,
            "total_response_time": 0
        }
        
        # 初始化事务数据库管理器
        if db_path and not hasattr(self, 'db_transaction_manager'):
            try:
                self.db_transaction_manager = create_db_manager(db_path)
                logger.info(f"事务数据库管理器初始化成功: {db_path}")
            except Exception as e:
                logger.error(f"初始化事务数据库管理器失败: {str(e)}")
                self.db_transaction_manager = None
        
        logger.info(f"异步爬虫初始化完成: {self.source}, 最大并发数: {max_concurrency}, 超时: {timeout}秒")
    
    async def _init_session(self):
        """初始化异步会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self.get_headers(),
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        
        # 初始化并发控制器
        if self.semaphore is None:
            self.semaphore = asyncio.Semaphore(self.max_concurrency)
        
        return self.session
    
    async def _close_session(self):
        """关闭异步会话"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            logger.debug("异步会话已关闭")
    
    def get_headers(self):
        """获取请求头"""
        # 默认使用基类的get_random_user_agent方法，子类可以覆盖
        user_agent = self.get_random_user_agent()
        return {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
    
    async def async_fetch_page(self, url, params=None, headers=None, max_retries=3, timeout=None):
        """
        异步获取页面内容
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 自定义请求头
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
            
        Returns:
            str: 页面内容或None
        """
        if not url:
            return None
        
        # 初始化会话
        session = await self._init_session()
        
        # 合并请求头
        merged_headers = self.get_headers()
        if headers:
            merged_headers.update(headers)
        
        # 设置超时
        if timeout is None:
            timeout = self.timeout
        
        async with self.semaphore:  # 使用信号量控制并发
            self.request_stats["total"] += 1
            start_time = time.time()
            
            for attempt in range(max_retries):
                try:
                    # 添加随机延迟，避免被反爬
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    
                    async with session.get(
                        url, 
                        params=params, 
                        headers=merged_headers,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        if response.status != 200:
                            logger.warning(f"请求失败: {url}, 状态码: {response.status}, 重试 {attempt+1}/{max_retries}")
                            
                            # 记录请求统计
                            track_request(
                                self.task_id, 
                                url=url, 
                                status_code=response.status, 
                                duration=time.time() - start_time, 
                                success=False
                            )
                            
                            if attempt < max_retries - 1:
                                await asyncio.sleep(random.uniform(2, 5))  # 随机延迟
                                continue
                            self.request_stats["failure"] += 1
                            return None
                        
                        # 获取响应内容
                        content = await response.text(errors='replace')
                        content_size = len(content)
                        
                        # 应用额外的解码处理
                        content = decode_html_entities(content)
                        content = decode_unicode_escape(content)
                        content = decode_url_encoded(content)
                        
                        # 更新统计
                        self.request_stats["success"] += 1
                        end_time = time.time()
                        request_time = end_time - start_time
                        self.request_stats["total_response_time"] += request_time
                        self.request_stats["avg_response_time"] = (
                            self.request_stats["total_response_time"] / self.request_stats["success"]
                        )
                        
                        # 记录请求统计
                        track_request(
                            self.task_id, 
                            url=url, 
                            method='GET', 
                            status_code=response.status, 
                            duration=request_time, 
                            size=content_size, 
                            success=True
                        )
                        
                        return content
                except asyncio.TimeoutError:
                    logger.warning(f"请求超时: {url}, 重试 {attempt+1}/{max_retries}")
                    
                    # 记录请求统计
                    track_request(
                        self.task_id, 
                        url=url, 
                        duration=time.time() - start_time, 
                        success=False, 
                        error_msg="Timeout"
                    )
                    
                    if attempt < max_retries - 1:
                        await asyncio.sleep(random.uniform(2, 5))  # 随机延迟
                except Exception as e:
                    logger.error(f"请求出错: {url}, 错误: {str(e)}, 重试 {attempt+1}/{max_retries}")
                    
                    # 记录请求统计
                    track_request(
                        self.task_id, 
                        url=url, 
                        duration=time.time() - start_time, 
                        success=False, 
                        error_msg=str(e)
                    )
                    
                    if attempt < max_retries - 1:
                        await asyncio.sleep(random.uniform(2, 5))  # 随机延迟
            
            self.request_stats["failure"] += 1
            return None
    
    async def async_batch_fetch(self, urls, **kwargs):
        """
        批量异步获取多个页面
        
        Args:
            urls: URL列表
            **kwargs: 其他请求参数
            
        Returns:
            dict: {url: content} 字典
        """
        if not urls:
            return {}
        
        tasks = []
        for url in urls:
            tasks.append(self.async_fetch_page(url, **kwargs))
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks)
        
        # 将结果映射回URL
        return {url: content for url, content in zip(urls, results) if content is not None}
    
    async def crawl_async(self, days=1, max_news=50, **kwargs):
        """
        异步爬取新闻
        
        Args:
            days: 爬取的天数范围
            max_news: 最多爬取的新闻数量
            **kwargs: 其他参数，如分类等
            
        Returns:
            list: 爬取的新闻列表
        """
        # 使用性能监控
        task_name = f"{self.__class__.__name__}_{int(time.time())}"
        with monitor_crawler(task_name, crawler_type=self.__class__.__name__, source=self.source) as performance_stats:
            # 保存任务ID用于后续跟踪
            self.task_id = performance_stats['task_id']
            
            # 重置请求统计
            self.request_stats = {
                "total": 0,
                "success": 0,
                "failure": 0,
                "start_time": time.time(),
                "end_time": None,
                "avg_response_time": 0,
                "total_response_time": 0
            }
            
            # 清空新闻数据列表
            self.news_data = []
            
            # 计算开始日期
            start_date = datetime.now() - timedelta(days=days)
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            logger.info(f"开始异步爬取 {self.source} 新闻，天数范围: {days}天，最多爬取: {max_news}条新闻")
            
            try:
                # 初始化会话
                await self._init_session()
                
                # 执行具体爬取逻辑（由子类实现）
                await self._crawl_implementation(days, max_news, start_date, performance_stats=performance_stats, **kwargs)
                
                logger.info(f"异步爬取完成，共爬取新闻 {len(self.news_data)} 条")
            finally:
                # 更新统计
                self.request_stats["end_time"] = time.time()
                
                # 关闭会话
                await self._close_session()
                
                # 输出统计信息
                elapsed = self.request_stats["end_time"] - self.request_stats["start_time"]
                logger.info(f"爬取统计 - 总请求: {self.request_stats['total']}, "
                            f"成功: {self.request_stats['success']}, "
                            f"失败: {self.request_stats['failure']}, "
                            f"平均响应时间: {self.request_stats['avg_response_time']:.2f}秒, "
                            f"总用时: {elapsed:.2f}秒")
            
            # 如果设置了max_news限制，确保返回的新闻不超过该数量
            if max_news and len(self.news_data) > max_news:
                return self.news_data[:max_news]
            return self.news_data
    
    async def _crawl_implementation(self, days, max_news, start_date, performance_stats, **kwargs):
        """
        爬取实现（由子类重写）
        
        Args:
            days: 爬取的天数范围
            max_news: 最多爬取的新闻数量
            start_date: 开始日期
            performance_stats: 性能统计对象
            **kwargs: 其他参数
        """
        raise NotImplementedError("子类必须实现_crawl_implementation方法")
    
    def crawl(self, days=1, max_news=50, **kwargs):
        """
        同步入口点，使用事件循环运行异步爬取
        
        Args:
            days: 爬取的天数范围
            max_news: 最多爬取的新闻数量
            **kwargs: 其他参数
            
        Returns:
            list: 爬取的新闻列表
        """
        loop = asyncio.get_event_loop()
        try:
            return loop.run_until_complete(self.crawl_async(days, max_news, **kwargs))
        except Exception as e:
            logger.error(f"异步爬取失败: {str(e)}")
            # 如果异步爬取失败，回退到同步爬取（如果子类实现了）
            logger.info("回退到同步爬取...")
            return self._fallback_sync_crawl(days, max_news, **kwargs)
    
    def _fallback_sync_crawl(self, days, max_news, **kwargs):
        """
        同步爬取回退方案（由子类实现）
        
        Args:
            days: 爬取的天数范围
            max_news: 最多爬取的新闻数量
            **kwargs: 其他参数
            
        Returns:
            list: 爬取的新闻列表
        """
        logger.warning("同步爬取回退方案未实现")
        return []
        
    def save_news(self, news_data, batch_mode=False):
        """
        保存新闻数据（使用事务进行数据库操作）
        
        Args:
            news_data: 新闻数据字典
            batch_mode: 是否为批量模式，批量模式下失败不会报错，便于批量操作
            
        Returns:
            bool: 是否成功添加
        """
        try:
            # 检查必要字段
            required_fields = ['id', 'title', 'content', 'pub_time', 'source', 'url']
            for field in required_fields:
                if field not in news_data:
                    logger.warning(f"新闻数据缺少必要字段: {field}")
                    return False
            
            # 确保所有必要字段都有值
            if 'author' not in news_data or not news_data['author']:
                news_data['author'] = self.source
                
            if 'sentiment' not in news_data or not news_data['sentiment']:
                news_data['sentiment'] = '中性'
                
            if 'crawl_time' not in news_data:
                news_data['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
            if 'keywords' not in news_data:
                news_data['keywords'] = ''
                
            if 'category' not in news_data:
                news_data['category'] = '财经'
                
            if 'images' not in news_data:
                news_data['images'] = ''
                
            if 'related_stocks' not in news_data:
                news_data['related_stocks'] = ''
            
            # 记录数据库操作开始
            operation_type = 'save_news'
            
            # 使用事务数据库保存
            if hasattr(self, 'db_transaction_manager') and self.db_transaction_manager:
                try:
                    result = self.db_transaction_manager.save_news(news_data)
                    
                    # 跟踪数据库操作
                    if hasattr(self, 'task_id'):
                        track_db_operation(self.task_id, operation_type, success=result)
                        if result:
                            track_news_saved(self.task_id, 1)
                    
                    if result:
                        logger.info(f"新闻已保存到数据库(事务): {news_data['title']}")
                        return True
                except Exception as e:
                    logger.error(f"使用事务管理器保存新闻失败: {str(e)}")
                    
                    # 跟踪数据库操作失败
                    if hasattr(self, 'task_id'):
                        track_db_operation(self.task_id, operation_type, success=False, error_msg=str(e))
                    
                    if not batch_mode:
                        raise
            
            # 如果没有事务管理器或保存失败，回退到原始保存方法
            result = super().save_news(news_data)
            
            # 跟踪数据库操作
            if hasattr(self, 'task_id'):
                track_db_operation(self.task_id, 'fallback_save_news', success=result)
                if result:
                    track_news_saved(self.task_id, 1)
            
            return result
            
        except Exception as e:
            logger.error(f"保存新闻失败: {str(e)}")
            if 'title' in news_data:
                logger.error(f"标题: {news_data['title']}")
            
            # 跟踪数据库操作失败
            if hasattr(self, 'task_id'):
                track_db_operation(self.task_id, operation_type, success=False, error_msg=str(e))
            
            if not batch_mode:
                raise
            return False
    
    def batch_save_news(self, news_list):
        """
        批量保存新闻数据
        
        Args:
            news_list: 新闻数据列表
            
        Returns:
            int: 成功保存的新闻数量
        """
        if not news_list:
            return 0
            
        saved_count = 0
        
        # 如果有事务数据库管理器，使用其批量保存功能
        if hasattr(self, 'db_transaction_manager') and self.db_transaction_manager:
            try:
                start_time = time.time()
                saved_count = self.db_transaction_manager.batch_save_news(news_list)
                end_time = time.time()
                
                # 跟踪数据库操作
                if hasattr(self, 'task_id'):
                    track_db_operation(
                        self.task_id, 
                        'batch_save_news', 
                        success=True
                    )
                    track_news_saved(self.task_id, saved_count)
                
                logger.info(f"批量保存新闻完成，成功: {saved_count}/{len(news_list)}, 耗时: {end_time - start_time:.2f}秒")
                return saved_count
            except Exception as e:
                logger.error(f"批量保存新闻失败: {str(e)}，将改用单条保存")
                
                # 跟踪数据库操作失败
                if hasattr(self, 'task_id'):
                    track_db_operation(
                        self.task_id, 
                        'batch_save_news', 
                        success=False, 
                        error_msg=str(e)
                    )
        
        # 如果没有事务管理器或批量保存失败，使用单条保存
        for news_data in news_list:
            try:
                if self.save_news(news_data, batch_mode=True):
                    saved_count += 1
            except Exception as e:
                logger.error(f"保存新闻失败: {news_data.get('title', '未知标题')}, 错误: {str(e)}")
        
        logger.info(f"逐条保存新闻完成，成功: {saved_count}/{len(news_list)}")
        return saved_count 