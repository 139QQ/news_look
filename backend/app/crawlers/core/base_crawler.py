#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 基础爬虫类
提供统一的爬虫框架，支持同步和异步操作
"""

import os
import time
import asyncio
from typing import Dict, List, Any, Optional, Union, Set
from datetime import datetime, timedelta
import traceback

from backend.app.utils.logger import get_logger, fix_duplicate_logging
from backend.app.crawlers.core.http_client import SyncHttpClient, AsyncHttpClient
from backend.app.crawlers.core.data_processor import DataProcessor
from backend.app.crawlers.strategies.base_strategy import BaseCrawlerStrategy

# 初始化日志记录器
logger = get_logger('base_crawler')

class BaseCrawler:
    """基础爬虫类，实现通用爬取流程"""
    
    def __init__(self, strategy: Optional[BaseCrawlerStrategy] = None, source: str = None, db_path: str = None, **options):
        """
        初始化爬虫
        
        Args:
            strategy: 爬虫策略实例，如果提供则优先使用
            source: 数据源名称
            db_path: 数据库路径
            **options: 配置选项，可包含：
                - async_mode: 是否使用异步模式，默认True
                - max_concurrency: 最大并发请求数，默认10
                - batch_size: 数据批处理大小，默认20
                - timeout: 请求超时时间（秒），默认30
                - max_retries: 最大重试次数，默认3
                - use_proxy: 是否使用代理，默认False
        """
        # 设置爬虫策略
        self.strategy = strategy
        if not self.strategy and source:
            self.strategy = self._create_strategy()
        if not self.strategy:
            raise ValueError("必须提供爬虫策略或有效的数据源名称")
            
        # 设置基本属性
        self.source = source or self.strategy.source
        self.db_path = db_path
        
        # 处理配置选项
        self.async_mode = options.get('async_mode', True)
        self.max_concurrency = options.get('max_concurrency', 10)
        self.batch_size = options.get('batch_size', 20)
        self.timeout = options.get('timeout', 30)
        self.max_retries = options.get('max_retries', 3)
        self.use_proxy = options.get('use_proxy', False)
        
        # 创建HTTP客户端
        if self.async_mode:
            self.http_client = AsyncHttpClient(
                timeout=self.timeout,
                max_retries=self.max_retries,
                use_proxy=self.use_proxy
            )
        else:
            self.http_client = SyncHttpClient(
                timeout=self.timeout,
                max_retries=self.max_retries,
                use_proxy=self.use_proxy
            )
        
        # 创建数据处理器
        if self.db_path:
            self.data_processor = DataProcessor(
                db_path=self.db_path,
                batch_size=self.batch_size
            )
        
        # 初始化统计信息
        self.stats = {
            'crawl_count': 0,
            'success_count': 0,
            'failed_count': 0,
            'total_time': 0,
            'last_crawl_time': None,
            'crawled_urls': set(),
            'failed_urls': set()
        }
        
        # 初始化成功和失败计数
        self.success_count = 0
        self.failed_count = 0
        
        # 确保日志配置正确
        fix_duplicate_logging()
        
        logger.info(f"{self.source} 爬虫初始化完成，使用{'异步' if self.async_mode else '同步'}模式")
    
    def _create_strategy(self) -> BaseCrawlerStrategy:
        """
        创建爬取策略实例，子类需重写此方法
        
        Returns:
            BaseCrawlerStrategy: 爬取策略实例
        """
        from backend.app.crawlers.strategies import get_strategy
        
        # 获取策略类
        strategy_class = get_strategy(self.source)
        if not strategy_class:
            raise ValueError(f"未找到源 '{self.source}' 对应的爬虫策略")
            
        # 创建策略实例
        return strategy_class(self.source)
    
    def crawl(self, days: int = 1, max_news: int = 100, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        爬取指定天数、数量的新闻
        
        Args:
            days: 爬取最近几天的新闻
            max_news: 最大爬取数量
            category: 新闻分类，如None表示所有分类
            
        Returns:
            List[Dict[str, Any]]: 新闻列表
        """
        logger = get_logger(f"crawler.{self.source}")
        logger.info(f"开始爬取{self.source}的新闻，天数: {days}, 最大数量: {max_news}, 分类: {category}")
        
        # 检查爬虫策略是否存在
        if not hasattr(self, 'strategy') or self.strategy is None:
            logger.error(f"未找到爬虫策略，请先初始化爬虫")
            return []
        
        # 获取要爬取的URL列表
        try:
            # 获取列表页URL
            list_page_urls = self.strategy.get_list_page_urls(days, category)
            if not list_page_urls:
                logger.warning(f"未找到任何列表页URL")
                return []
                
            logger.info(f"获取到 {len(list_page_urls)} 个列表页URL")
            
            # 爬取每个列表页，获取文章URL
            all_article_urls = []
            for url in list_page_urls:
                try:
                    html = self.http_client.fetch_sync(url)
                    if not html:
                        logger.warning(f"获取列表页内容失败: {url}")
                        continue
                        
                    article_urls = self.strategy.parse_list_page(html, url)
                    if article_urls:
                        all_article_urls.extend(article_urls)
                        logger.info(f"从列表页 {url} 获取到 {len(article_urls)} 个文章URL")
                    else:
                        logger.warning(f"从列表页 {url} 未获取到任何文章URL")
                except Exception as e:
                    logger.error(f"爬取列表页 {url} 出错: {str(e)}")
            
            # 去重
            unique_article_urls = list(dict.fromkeys(all_article_urls))
            logger.info(f"去重后共有 {len(unique_article_urls)} 个文章URL")
            
            # 限制爬取数量
            if max_news > 0 and len(unique_article_urls) > max_news:
                unique_article_urls = unique_article_urls[:max_news]
                logger.info(f"限制爬取数量为 {max_news}")
            
            # 爬取每篇文章的详细内容
            news_list = []
            for url in unique_article_urls:
                try:
                    html = self.http_client.fetch_sync(url)
                    if not html:
                        logger.warning(f"获取文章内容失败: {url}")
                        continue
                        
                    article_data = self.strategy.parse_detail_page(html, url)
                    if article_data:
                        # 确保所有必要字段都存在
                        if 'source' not in article_data or not article_data['source']:
                            article_data['source'] = self.source
                            
                        if 'crawl_time' not in article_data:
                            article_data['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            
                        # 保存到数据库
                        self.save_news_to_db(article_data)
                        
                        # 添加到结果列表
                        news_list.append(article_data)
                        logger.info(f"成功爬取文章: {article_data.get('title', url)}")
                    else:
                        logger.warning(f"解析文章内容失败: {url}")
                except Exception as e:
                    logger.error(f"爬取文章 {url} 出错: {str(e)}")
            
            logger.info(f"成功爬取 {len(news_list)} 篇文章")
            return news_list
            
        except Exception as e:
            logger.error(f"爬取过程中发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def crawl_sync(self, days: int = 1, max_news: Optional[int] = None, 
                  category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        同步模式爬取新闻
        
        Args:
            days: 爬取最近几天的新闻
            max_news: 最大爬取数量，为None则不限制
            category: 新闻分类，为None则使用默认分类
            
        Returns:
            List[Dict[str, Any]]: 爬取的新闻列表
        """
        start_time = time.time()
        logger.info(f"开始同步爬取 {self.source} 新闻，天数: {days}, 最大数量: {max_news or '不限'}, 分类: {category or '所有'}")
        
        # 获取要爬取的URL列表
        urls = self._get_urls_to_crawl(days, category)
        if not urls:
            logger.warning(f"未找到需要爬取的URL，请检查爬取策略是否正确配置")
            return []
        
        logger.info(f"找到 {len(urls)} 个待爬取URL")
        
        # 限制爬取数量
        if max_news and len(urls) > max_news:
            urls = urls[:max_news]
            logger.info(f"由于max_news限制，实际将爬取 {len(urls)} 个URL")
        
        # 爬取结果列表
        results = []
        crawled_count = 0
        failed_count = 0
        
        # 爬取每个URL
        for url in urls:
            try:
                # 检查是否已爬取过
                if url in self.stats['crawled_urls']:
                    logger.debug(f"跳过已爬取的URL: {url}")
                    continue
                
                # 获取页面内容
                html = self.http_client.fetch(url)
                
                # 解析文章详情
                article = self.strategy.parse_detail_page(html, url)
                
                # 确保来源正确
                article['source'] = self.source
                
                # 预处理文章
                article = self.preprocess_article(article)
                
                # 保存到数据库
                self.data_processor.save(article)
                
                # 添加到结果列表
                results.append(article)
                
                # 更新统计信息
                self.stats['crawled_urls'].add(url)
                crawled_count += 1
                
                logger.debug(f"成功爬取: {url}")
                
            except Exception as e:
                logger.error(f"爬取失败: {url}, 错误: {str(e)}")
                self.stats['failed_urls'].add(url)
                failed_count += 1
        
        # 刷新数据处理器缓存
        self.data_processor.flush()
        
        # 更新统计信息
        elapsed_time = time.time() - start_time
        self.stats['crawl_count'] += 1
        self.stats['success_count'] += crawled_count
        self.stats['failed_count'] += failed_count
        self.stats['total_time'] += elapsed_time
        self.stats['last_crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info(f"同步爬取完成，成功: {crawled_count}, 失败: {failed_count}, 耗时: {elapsed_time:.2f}秒")
        
        return results
    
    async def crawl_async(self, days: int = 1, max_news: int = 100, category: Optional[str] = None) -> Dict[str, Any]:
        """
        异步爬取文章

        Args:
            days: 爬取最近几天的新闻
            max_news: 最大爬取文章数
            category: 新闻分类

        Returns:
            Dict: 包含爬取结果的字典
        """
        start_time = time.time()
        logger.info(f"开始异步爬取 {self.source}，天数：{days}，最大数量：{max_news}，分类：{category or '默认'}")

        # 重置状态计数器
        self.success_count = 0
        self.failed_count = 0
        
        # 检查是否在现有事件循环中运行
        try:
            existing_loop = asyncio.get_running_loop()
            is_nested_loop = True
            logger.debug("检测到现有事件循环，在当前循环中执行爬取任务")
        except RuntimeError:
            is_nested_loop = False
            logger.debug("未检测到事件循环，将创建新的事件循环")

        try:
            # 获取要爬取的URL
            urls_to_crawl = self._get_urls_to_crawl(days, category)
            
            # 如果URL列表为空，可能是因为在嵌套循环模式下异步获取结果尚未返回
            if not urls_to_crawl and is_nested_loop and hasattr(self, '_current_loop_result'):
                urls_to_crawl = self._current_loop_result
                delattr(self, '_current_loop_result')
                logger.debug(f"从现有事件循环中获取到 {len(urls_to_crawl)} 个URL")
                
            if not urls_to_crawl:
                logger.warning(f"没有找到符合条件的文章URL（{self.source}，天数：{days}，分类：{category or '默认'}）")
                return {
                    "success": False,
                    "message": "未找到符合条件的文章",
                    "articles": [],
                    "stats": {
                        "total": 0,
                        "success": 0,
                        "failed": 0,
                        "time_elapsed": time.time() - start_time
                    }
                }

            # 限制爬取数量
            if max_news > 0 and len(urls_to_crawl) > max_news:
                logger.info(f"限制爬取数量：{len(urls_to_crawl)} -> {max_news}")
                urls_to_crawl = urls_to_crawl[:max_news]

            # 创建信号量控制并发
            semaphore = asyncio.Semaphore(self.max_concurrency)
            
            # 准备爬取任务
            fetch_tasks = []
            for url in urls_to_crawl:
                if url not in self.stats['crawled_urls']:
                    task = self._fetch_and_process_article_async(url, semaphore)
                    fetch_tasks.append(task)
                else:
                    logger.debug(f"跳过已爬取的URL: {url}")

            if not fetch_tasks:
                logger.info(f"所有URL都已爬取过，无需重复爬取")
                return {
                    "success": True,
                    "message": "所有URL都已爬取过",
                    "articles": [],
                    "stats": {
                        "total": 0,
                        "success": 0,
                        "failed": 0,
                        "time_elapsed": time.time() - start_time
                    }
                }

            logger.info(f"准备爬取 {len(fetch_tasks)} 个URL，并发数：{self.max_concurrency}")
                
            # 执行爬取任务
            if is_nested_loop:
                # 在现有事件循环中运行，返回future对象供外部管理
                gather_future = asyncio.gather(*fetch_tasks, return_exceptions=True)
                
                # 包装结果，让调用者知道这是一个需要等待的future
                return {
                    "pending_future": gather_future,
                    "message": f"异步任务已启动，正在爬取 {len(fetch_tasks)} 个URL",
                    "meta": {
                        "source": self.source,
                        "days": days,
                        "max_news": max_news,
                        "category": category,
                        "start_time": start_time,
                        "url_count": len(fetch_tasks)
                    }
                }
            else:
                # 创建新的事件循环并执行任务
                results = []
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    results = loop.run_until_complete(asyncio.gather(*fetch_tasks, return_exceptions=True))
                finally:
                    loop.close()
                    
                # 处理结果
                return self._process_crawl_results(results, start_time)
            
        except Exception as e:
            logger.error(f"异步爬取过程中发生错误: {str(e)}")
            logger.debug(f"详细错误: {traceback.format_exc()}")
            
            return {
                "success": False,
                "message": f"爬取过程发生错误: {str(e)}",
                "articles": [],
                "stats": {
                    "total": self.success_count + self.failed_count,
                    "success": self.success_count,
                    "failed": self.failed_count,
                    "time_elapsed": time.time() - start_time
                }
            }

    async def _fetch_and_process_article_async(self, url: str, semaphore: asyncio.Semaphore) -> Optional[Dict[str, Any]]:
        """
        异步获取并处理单篇文章
        
        Args:
            url: 文章URL
            semaphore: 并发控制信号量
            
        Returns:
            Optional[Dict[str, Any]]: 处理后的文章数据，失败则返回None
        """
        async with semaphore:
            try:
                # 获取文章页面内容
                html = await self.http_client.fetch(url)
                
                # 解析文章详情
                article = self.strategy.parse_detail_page(html, url)
                
                # 确保来源正确
                article['source'] = self.source
                
                # 预处理文章
                article = self.preprocess_article(article)
                
                # 保存到数据库
                await asyncio.to_thread(self.data_processor.save, article)
                
                # 更新统计信息
                self.stats['crawled_urls'].add(url)
                
                # 确保属性存在再递增
                if hasattr(self, 'success_count'):
                    self.success_count += 1
                else:
                    # 如果属性不存在，初始化它
                    self.success_count = 1
                    logger.warning("success_count属性不存在，已初始化为1")
                
                logger.debug(f"成功爬取: {url}")
                return article
                
            except Exception as e:
                logger.error(f"爬取失败: {url}, 错误: {str(e)}")
                self.stats['failed_urls'].add(url)
                
                # 确保属性存在再递增
                if hasattr(self, 'failed_count'):
                    self.failed_count += 1
                else:
                    # 如果属性不存在，初始化它
                    self.failed_count = 1
                    logger.warning("failed_count属性不存在，已初始化为1")
                
                # 记录详细错误
                logger.debug(f"详细错误: {traceback.format_exc()}")
                return None
    
    def _process_crawl_results(self, results: List[Any], start_time: float) -> Dict[str, Any]:
        """
        处理爬取结果并生成统计信息
        
        Args:
            results: 爬取任务的结果列表
            start_time: 爬取开始时间
            
        Returns:
            Dict[str, Any]: 包含爬取结果和统计信息的字典
        """
        articles = []
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"爬取任务异常: {str(result)}")
                continue
                
            if result and isinstance(result, dict):
                articles.append(result)
        
        # 刷新数据处理器缓存
        self.data_processor.flush()
        
        # 计算总耗时
        time_elapsed = time.time() - start_time
        
        # 更新统计信息
        self.stats['crawl_count'] += 1
        self.stats['total_time'] += time_elapsed
        self.stats['last_crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 确保成功和失败计数属性存在
        if not hasattr(self, 'success_count'):
            self.success_count = 0
            logger.warning("success_count属性不存在，已初始化为0")
            
        if not hasattr(self, 'failed_count'):
            self.failed_count = 0
            logger.warning("failed_count属性不存在，已初始化为0")
        
        total_crawled = self.success_count + self.failed_count
        
        logger.info(f"异步爬取完成，成功: {self.success_count}，失败: {self.failed_count}，总耗时: {time_elapsed:.2f}秒")
        
        return {
            "success": True,
            "message": f"成功爬取 {self.success_count} 篇文章",
            "articles": articles,
            "stats": {
                "total": total_crawled,
                "success": self.success_count,
                "failed": self.failed_count,
                "time_elapsed": time_elapsed
            }
        }
    
    def _get_urls_to_crawl(self, days: int, category: Optional[str] = None) -> List[str]:
        """
        获取需要爬取的URL列表
        
        Args:
            days: 爬取最近几天的新闻
            category: 新闻分类，为None则使用默认分类
            
        Returns:
            List[str]: 需要爬取的URL列表
        """
        try:
            # 获取列表页URL
            list_page_urls = self.strategy.get_list_page_urls(days, category)
            if not list_page_urls:
                logger.warning(f"未找到任何列表页URL（天数：{days}，分类：{category or '默认'}）")
                return []
            
            logger.info(f"找到 {len(list_page_urls)} 个列表页，准备提取文章URL")
            
            # 异步获取所有文章URL
            try:
                # 检查是否有事件循环在运行
                try:
                    loop = asyncio.get_running_loop()
                    # 如果有事件循环在运行，使用ensure_future
                    future = asyncio.ensure_future(
                        self._fetch_list_pages_async(list_page_urls)
                    )
                    # 获取已有事件循环的结果
                    article_urls = []
                    if hasattr(self, '_current_loop_result'):
                        # 如果已经有之前的结果，先清理
                        delattr(self, '_current_loop_result')
                    
                    # 设置回调来存储结果
                    def save_result(fut):
                        self._current_loop_result = fut.result()
                    
                    future.add_done_callback(save_result)
                    logger.info("在现有事件循环中请求文章URL，结果将异步返回")
                    
                    # 返回一个空列表，实际结果将在回调中处理
                    return []
                    
                except RuntimeError:
                    # 没有事件循环运行，创建一个新的
                    logger.debug("创建新的事件循环来获取文章URL")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        article_urls = loop.run_until_complete(
                            self._fetch_list_pages_async(list_page_urls)
                        )
                    finally:
                        loop.close()
            except Exception as e:
                logger.error(f"异步获取文章URL失败: {str(e)}")
                logger.debug(f"详细错误: {traceback.format_exc()}")
                # 回退到同步方式获取
                logger.info("回退到同步方式获取文章URL")
                article_urls = self._fetch_list_pages_sync(list_page_urls)
            
            if not isinstance(article_urls, list):
                logger.warning(f"获取到的文章URL类型不正确: {type(article_urls)}，已转换为空列表")
                article_urls = []
                
            logger.info(f"从列表页中提取到 {len(article_urls)} 个文章URL")
            return article_urls
            
        except Exception as e:
            logger.error(f"获取待爬取URL时发生错误: {str(e)}")
            logger.debug(f"详细错误: {traceback.format_exc()}")
            return []
    
    def _fetch_list_pages_sync(self, list_urls: List[str]) -> List[str]:
        """
        同步爬取列表页
        
        Args:
            list_urls: 列表页URL列表
            
        Returns:
            List[str]: 文章URL列表
        """
        all_article_urls = []
        
        for list_url in list_urls:
            try:
                # 获取列表页内容
                html = self.http_client.fetch(list_url)
                
                # 解析文章链接
                article_urls = self.strategy.parse_list_page(html, list_url)
                all_article_urls.extend(article_urls)
                
                logger.debug(f"从列表页 {list_url} 获取到 {len(article_urls)} 个文章URL")
                
            except Exception as e:
                logger.error(f"爬取列表页失败: {list_url}, 错误: {str(e)}")
        
        # 去重
        return list(dict.fromkeys(all_article_urls))
    
    async def _fetch_list_pages_async(self, list_urls: List[str]) -> List[str]:
        """
        异步爬取列表页
        
        Args:
            list_urls: 列表页URL列表
            
        Returns:
            List[str]: 文章URL列表
        """
        all_article_urls = []
        
        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(self.max_concurrency)
        
        async def fetch_list_page(url):
            """爬取并解析单个列表页"""
            async with semaphore:
                try:
                    # 获取列表页内容
                    html = await self.http_client.fetch(url)
                    
                    # 解析文章链接
                    article_urls = self.strategy.parse_list_page(html, url)
                    
                    logger.debug(f"从列表页 {url} 获取到 {len(article_urls)} 个文章URL")
                    
                    return article_urls
                    
                except Exception as e:
                    logger.error(f"爬取列表页失败: {url}, 错误: {str(e)}")
                    return []
        
        # 创建爬取任务
        tasks = [fetch_list_page(url) for url in list_urls]
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks)
        
        # 合并结果
        for urls in results:
            all_article_urls.extend(urls)
        
        # 去重
        return list(dict.fromkeys(all_article_urls))
    
    def preprocess_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        预处理文章数据，可在子类中重写以添加特定处理
        
        Args:
            article: 文章数据字典
            
        Returns:
            Dict[str, Any]: 处理后的文章数据
        """
        # 确保ID存在
        if 'id' not in article or not article['id']:
            if 'url' in article and article['url']:
                import hashlib
                article['id'] = hashlib.md5(article['url'].encode('utf-8')).hexdigest()
        
        # 确保来源字段正确
        article['source'] = self.source
        
        # 确保爬取时间存在
        if 'crawl_time' not in article:
            article['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        return article
    
    def save_news_to_db(self, article_data: Dict[str, Any]) -> bool:
        """
        保存新闻到数据库
        
        Args:
            article_data: 文章数据
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 使用数据处理器保存文章
            self.data_processor.save(article_data)
            logger.debug(f"成功保存新闻到数据库: {article_data.get('title', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"保存新闻到数据库失败: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取爬虫统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        # 基本统计信息
        stats = {
            'source': self.source,
            'mode': 'async' if self.async_mode else 'sync',
            'crawl_count': self.stats['crawl_count'],
            'success_count': self.stats['success_count'],
            'failed_count': self.stats['failed_count'],
            'total_time': self.stats['total_time'],
            'last_crawl_time': self.stats['last_crawl_time'],
            'crawled_urls_count': len(self.stats['crawled_urls']),
            'failed_urls_count': len(self.stats['failed_urls'])
        }
        
        # 添加HTTP客户端统计
        http_stats = self.http_client.get_stats()
        stats['http'] = http_stats
        
        # 添加数据处理器统计
        data_stats = self.data_processor.get_stats()
        stats['data'] = data_stats
        
        return stats
    
    def close(self):
        """关闭资源"""
        # 关闭数据处理器
        if self.data_processor:
            self.data_processor.close()
        
        # 关闭HTTP客户端
        if self.http_client:
            if self.async_mode and isinstance(self.http_client, AsyncHttpClient):
                # 异步关闭需要使用事件循环
                try:
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(self.http_client.close())
                except Exception as e:
                    logger.error(f"关闭异步HTTP客户端失败: {str(e)}")
            else:
                # 同步关闭
                self.http_client.close() 