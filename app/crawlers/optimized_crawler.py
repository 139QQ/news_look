#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 优化的爬虫基类
基于CrawlerOptimizer工具，提供更高效的爬虫实现
"""

import os
import sys
import time
import random
from datetime import datetime, timedelta
import json
import asyncio
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.crawlers.base import BaseCrawler
from app.utils.crawler_optimizer import CrawlerOptimizer
from app.utils.logger import get_logger
from app.utils.text_cleaner import clean_html, extract_keywords
from app.utils.database import DatabaseManager

# 设置日志记录器
logger = get_logger('optimized_crawler')

class OptimizedCrawler(BaseCrawler):
    """优化的爬虫基类，提供更高效的网页获取、并行处理和异常处理能力"""
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, 
                max_workers=5, timeout=30, enable_async=False, **kwargs):
        """
        初始化优化的爬虫基类
        
        Args:
            db_manager: 数据库管理器对象
            db_path: 数据库路径，如果为None则使用默认路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
            max_workers: 最大工作线程数
            timeout: 请求超时时间（秒）
            enable_async: 是否启用异步模式
            **kwargs: 其他参数
        """
        # 确保子类在调用super().__init__之前设置了source属性
        super().__init__(db_manager=db_manager, db_path=db_path, use_proxy=use_proxy, 
                        use_source_db=use_source_db, **kwargs)
        
        # 初始化优化器
        self.optimizer = CrawlerOptimizer(max_workers=max_workers, timeout=timeout, enable_async=enable_async)
        
        # 爬虫性能跟踪
        self.crawl_stats = {
            "start_time": None,
            "end_time": None,
            "total_urls": 0,
            "processed_urls": 0,
            "success_urls": 0,
            "failed_urls": 0,
            "news_count": 0,
            "filtered_count": 0,
            "error_count": 0,
            "avg_process_time": 0,
            "total_process_time": 0,
        }
        
        # 用于存储已处理的URL
        self.processed_urls = set()
        
        # 用于存储新闻数据的队列
        self.news_queue = Queue()
        
        # 为大型爬取任务创建保存线程
        self.save_thread = None
        self.save_thread_running = False
        
        # 设置每个网站特定的处理能力
        self.site_capacity = {
            "网易财经": {
                "parallel_requests": 3,  # 并行请求数
                "list_page_size": 30,    # 列表页面大小
                "article_batch_size": 5, # 文章批处理大小
                "page_load_wait": 1.0,   # 页面加载等待时间
            },
            "新浪财经": {
                "parallel_requests": 2,
                "list_page_size": 20,
                "article_batch_size": 3,
                "page_load_wait": 1.5,
            },
            "凤凰财经": {
                "parallel_requests": 2,
                "list_page_size": 25,
                "article_batch_size": 4,
                "page_load_wait": 1.2,
            },
        }
        
        logger.info(f"优化爬虫初始化完成: {self.source}, 最大工作线程: {max_workers}, 超时: {timeout}秒")
    
    def __del__(self):
        """析构函数，清理资源"""
        try:
            if hasattr(self, 'optimizer'):
                self.optimizer.close()
                
            if hasattr(self, 'save_thread_running') and self.save_thread_running:
                self.save_thread_running = False
                if self.save_thread:
                    self.save_thread.join(timeout=5)
                    
            super().__del__()
        except Exception as e:
            logger.error(f"清理资源时出错: {str(e)}")
    
    def fetch_page(self, url, params=None, headers=None, max_retries=None, timeout=None):
        """
        使用优化器获取页面内容
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 自定义请求头
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
            
        Returns:
            页面内容或None
        """
        response = self.optimizer.fetch_with_retry(
            url=url,
            site_name=self.source,
            params=params,
            headers=headers,
            max_retries=max_retries,
            timeout=timeout
        )
        
        if response:
            return response.text
        return None
    
    def parallel_fetch_pages(self, urls, **kwargs):
        """
        并行获取多个页面
        
        Args:
            urls: URL列表
            **kwargs: 其他请求参数
            
        Returns:
            dict: {url: content} 字典
        """
        responses = self.optimizer.parallel_fetch(urls, self.source, **kwargs)
        
        results = {}
        for url, response in responses.items():
            if response:
                results[url] = response.text
            else:
                results[url] = None
        
        return results
    
    def async_fetch_pages(self, urls, **kwargs):
        """
        异步获取多个页面
        
        Args:
            urls: URL列表
            **kwargs: 其他请求参数
            
        Returns:
            dict: {url: content} 字典
        """
        loop = asyncio.get_event_loop()
        responses = loop.run_until_complete(
            self.optimizer.async_fetch_all(urls, self.source, **kwargs)
        )
        
        results = {}
        for url, response in responses.items():
            if response:
                results[url] = response.get('text')
            else:
                results[url] = None
        
        return results
    
    def start_save_thread(self):
        """启动数据保存线程"""
        if self.save_thread and self.save_thread.is_alive():
            return
        
        self.save_thread_running = True
        self.save_thread = threading.Thread(target=self._save_worker)
        self.save_thread.daemon = True
        self.save_thread.start()
        logger.info("数据保存线程已启动")
    
    def _save_worker(self):
        """数据保存工作线程"""
        while self.save_thread_running:
            try:
                # 从队列获取数据，最多等待1秒
                news_data = self.news_queue.get(timeout=1)
                
                # 保存到数据库
                if news_data:
                    try:
                        self.save_news(news_data)
                        self.crawl_stats["news_count"] += 1
                        logger.debug(f"保存新闻成功: {news_data.get('title', '未知标题')}")
                    except Exception as e:
                        self.crawl_stats["error_count"] += 1
                        logger.error(f"保存新闻失败: {str(e)}")
                
                # 标记任务完成
                self.news_queue.task_done()
            except Exception as e:
                if not isinstance(e, Exception):  # 忽略队列超时异常
                    logger.error(f"数据保存线程异常: {str(e)}")
                time.sleep(0.1)  # 避免空队列时CPU占用过高
    
    def stop_save_thread(self):
        """停止数据保存线程"""
        if self.save_thread and self.save_thread.is_alive():
            self.save_thread_running = False
            # 等待队列清空
            self.news_queue.join()
            # 等待线程结束
            self.save_thread.join(timeout=5)
            logger.info("数据保存线程已停止")
    
    def batch_process_news_links(self, news_links, category):
        """
        批量处理新闻链接
        
        Args:
            news_links: 新闻链接列表
            category: 新闻分类
            
        Returns:
            list: 爬取的新闻列表
        """
        if not news_links:
            return []
        
        news_results = []
        processed = 0
        total = len(news_links)
        
        self.crawl_stats["total_urls"] += total
        
        # 获取网站特定的批处理大小
        site_config = self.site_capacity.get(self.source, self.site_capacity["网易财经"])
        batch_size = site_config["article_batch_size"]
        
        # 启动保存线程
        self.start_save_thread()
        
        # 分批处理
        for i in range(0, total, batch_size):
            batch_links = news_links[i:i+batch_size]
            
            # 记录处理开始时间
            batch_start_time = time.time()
            
            # 并行获取内容
            contents = self.parallel_fetch_pages(batch_links)
            
            for url, content in contents.items():
                self.crawl_stats["processed_urls"] += 1
                
                if url in self.processed_urls:
                    logger.debug(f"跳过已处理的URL: {url}")
                    continue
                
                # 标记URL为已处理
                self.processed_urls.add(url)
                
                # 处理内容
                if content:
                    try:
                        news_data = self.crawl_news_detail(url, category)
                        if news_data:
                            # 将数据添加到队列中，由保存线程处理
                            self.news_queue.put(news_data)
                            news_results.append(news_data)
                            self.crawl_stats["success_urls"] += 1
                    except Exception as e:
                        self.crawl_stats["failed_urls"] += 1
                        self.crawl_stats["error_count"] += 1
                        logger.error(f"处理新闻详情失败, URL: {url}, 错误: {str(e)}")
                else:
                    self.crawl_stats["failed_urls"] += 1
            
            # 计算批处理耗时
            batch_end_time = time.time()
            batch_time = batch_end_time - batch_start_time
            self.crawl_stats["total_process_time"] += batch_time
            
            # 更新平均处理时间
            processed += len(batch_links)
            self.crawl_stats["avg_process_time"] = self.crawl_stats["total_process_time"] / max(processed, 1)
            
            # 记录进度
            progress = (processed / total) * 100
            logger.info(f"批处理进度: {processed}/{total} ({progress:.1f}%), 平均处理时间: {self.crawl_stats['avg_process_time']:.2f}秒/URL")
            
            # 随机休眠，避免过快请求
            if i + batch_size < total:
                sleep_time = site_config["page_load_wait"] * (0.8 + 0.4 * random.random())
                time.sleep(sleep_time)
        
        # 等待队列中的数据保存完成
        self.news_queue.join()
        
        return news_results
    
    def check_website_status(self):
        """
        检查目标网站状态
        
        Returns:
            bool: 网站是否可访问
        """
        status = self.optimizer.check_network_status({self.source: self.get_base_url()})
        site_status = status.get(self.source, {})
        
        if site_status.get("status") == "可访问":
            logger.info(f"网站 {self.source} 可正常访问，响应时间: {site_status.get('response_time', 0):.2f}秒")
            return True
        else:
            logger.warning(f"网站 {self.source} 访问异常: {site_status}")
            return False
    
    def get_base_url(self):
        """
        获取网站基础URL
        
        Returns:
            str: 网站基础URL
        """
        # 根据来源返回相应的基础URL
        if self.source == "网易财经":
            return "https://money.163.com/"
        elif self.source == "新浪财经":
            return "https://finance.sina.com.cn/"
        elif self.source == "凤凰财经":
            return "https://finance.ifeng.com/"
        else:
            # 默认返回空字符串
            return ""
    
    def crawl(self, days=1, max_news=None, check_status=True):
        """
        爬取新闻的主方法
        
        Args:
            days: 爬取最近几天的新闻
            max_news: 最大新闻数量，None表示不限制
            check_status: 是否检查网站状态
            
        Returns:
            list: 爬取的新闻列表
        """
        # 重置爬虫统计信息
        self.reset_crawl_stats()
        
        # 清空处理过的URL
        self.processed_urls.clear()
        
        # 开始计时
        self.crawl_stats["start_time"] = datetime.now()
        
        logger.info(f"开始爬取 {self.source} 的财经新闻，爬取天数: {days}")
        
        # 如果需要，检查网站状态
        if check_status and not self.check_website_status():
            logger.error(f"网站 {self.source} 无法访问，爬取中止")
            return []
        
        # 实际爬取逻辑需要由子类实现
        news_data = []
        
        # 结束计时
        self.crawl_stats["end_time"] = datetime.now()
        
        # 计算统计信息
        self.crawl_stats["elapsed_time"] = (self.crawl_stats["end_time"] - self.crawl_stats["start_time"]).total_seconds()
        if self.crawl_stats["elapsed_time"] > 0:
            self.crawl_stats["urls_per_second"] = self.crawl_stats["processed_urls"] / self.crawl_stats["elapsed_time"]
        
        # 记录爬取结果
        logger.info(f"{self.source} 爬取完成，统计信息: {json.dumps(self.crawl_stats, default=str)}")
        
        return news_data
    
    def reset_crawl_stats(self):
        """重置爬虫统计信息"""
        self.crawl_stats = {
            "start_time": None,
            "end_time": None,
            "elapsed_time": 0,
            "total_urls": 0,
            "processed_urls": 0,
            "success_urls": 0,
            "failed_urls": 0,
            "news_count": 0,
            "filtered_count": 0,
            "error_count": 0,
            "avg_process_time": 0,
            "total_process_time": 0,
            "urls_per_second": 0,
        }
    
    def get_crawl_stats(self):
        """
        获取爬虫统计信息
        
        Returns:
            dict: 爬虫统计信息
        """
        return self.crawl_stats
    
    def get_optimizer_stats(self):
        """
        获取优化器统计信息
        
        Returns:
            dict: 优化器统计信息
        """
        return self.optimizer.get_stats() 