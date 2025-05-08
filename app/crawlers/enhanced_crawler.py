#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 增强型爬虫类
优化异步爬取能力，提供更精细的并发控制和性能优化
"""

import os
import time
import asyncio
import gc
import psutil
from typing import Dict, List, Any, Optional, Union, Set, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse

from app.utils.logger import get_logger
from app.crawlers.core.base_crawler import BaseCrawler
from app.crawlers.core.http_client import AsyncHttpClient
from app.crawlers.strategies import get_strategy

# 初始化日志记录器
logger = get_logger('enhanced_crawler')

class EnhancedCrawler(BaseCrawler):
    """
    增强型爬虫实现，提供以下增强功能:
    1. 更高效的域名级别并发控制
    2. 自动限速与智能重试
    3. 资源优化与内存管理
    4. 更详细的性能监控
    """

    def __init__(self, strategy=None, source: str = None, db_path: str = None, **options):
        """
        初始化增强爬虫

        Args:
            strategy: 爬虫策略实例
            source: 新闻源名称
            db_path: 数据库路径
            **options: 可选配置参数
        """
        # 确保默认参数
        self.options = self._set_enhanced_defaults(options)
        
        # 如果没有提供策略但提供了source，尝试加载对应的策略
        if not strategy and source:
            strategy_class = get_strategy(source)
            if strategy_class:
                strategy = strategy_class()
            else:
                raise ValueError(f"不支持的新闻源: {source}")
        
        # 调用父类初始化
        super().__init__(strategy=strategy, source=source, db_path=db_path, **self.options)
        
        # 增强爬虫特定属性
        self.domain_semaphores = {}  # 域名级别的并发控制
        self.domain_crawl_stats = {}  # 每个域名的爬取统计
        self.domain_delays = {}  # 每个域名的请求延迟
        self.memory_usage = []  # 内存使用跟踪
        self.request_intervals = {}  # 每个域名的请求间隔
        
        # 增强的性能监控
        self.performance_stats = {
            'start_time': None,
            'end_time': None,
            'total_requests': 0,
            'bandwidth_used': 0,  # 字节数
            'average_latency': 0,
            'latency_samples': [],
            'status_codes': {},
            'domain_stats': {},
            'memory_peak': 0,
        }
        
        logger.info(f"增强爬虫初始化完成: {self.source}")
    
    def _set_enhanced_defaults(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        设置增强爬虫的默认参数

        Args:
            options: 用户提供的配置选项

        Returns:
            Dict: 合并后的配置选项
        """
        # 增强爬虫的默认配置
        enhanced_defaults = {
            'async_mode': True,  # 默认使用异步模式
            'max_concurrency': 10,  # 总体并发数
            'domain_concurrency': 5,  # 每个域名的并发数
            'adaptive_speed': True,  # 自动调整请求速度
            'memory_limit': 500,  # MB，内存使用限制
            'intelligent_retry': True,  # 智能重试
            'max_retry_wait': 30,  # 最大重试等待时间（秒）
            'monitor_performance': True,  # 是否监控性能
            'request_timeout': 15,  # 请求超时时间
        }
        
        # 合并默认值与用户选项
        for key, value in enhanced_defaults.items():
            if key not in options:
                options[key] = value
                
        return options
    
    async def crawl_async(self, days: int = 1, max_news: int = 100, category: Optional[str] = None) -> Dict[str, Any]:
        """
        增强型异步爬取实现

        Args:
            days: 爬取最近几天的新闻
            max_news: 最大爬取文章数
            category: 新闻分类

        Returns:
            Dict: 爬取结果与统计
        """
        # 记录开始性能统计
        if self.options.get('monitor_performance', True):
            self.performance_stats['start_time'] = time.time()
            self._start_memory_monitoring()
        
        logger.info(f"增强爬虫开始异步爬取: {self.source}, 天数: {days}, 最大文章数: {max_news}")
        
        # 获取要爬取的URL
        start_time = time.time()
        self.success_count = 0
        self.failed_count = 0
        
        try:
            # 获取文章URL列表
            urls = await self._fetch_urls_async(days, category)
            
            if not urls:
                logger.warning(f"未获取到任何URL，爬取结束")
                return {
                    "success": False,
                    "message": "未找到符合条件的文章URL",
                    "stats": {
                        "total": 0,
                        "success": 0,
                        "failed": 0,
                        "time_elapsed": time.time() - start_time
                    }
                }
            
            # 限制爬取数量
            if max_news > 0 and len(urls) > max_news:
                urls = urls[:max_news]
                logger.info(f"限制爬取数量为 {max_news}")
            
            # 过滤已爬取的URL
            urls_to_crawl = [url for url in urls if url not in self.stats['crawled_urls']]
            if not urls_to_crawl:
                logger.info("所有URL都已爬取过，无需重复爬取")
                return {
                    "success": True,
                    "message": "所有文章都已爬取",
                    "articles": [],
                    "stats": {
                        "total": 0,
                        "success": 0,
                        "failed": 0,
                        "time_elapsed": time.time() - start_time
                    }
                }
            
            logger.info(f"准备爬取 {len(urls_to_crawl)} 个文章")
            
            # 创建信号量控制并发
            semaphore = asyncio.Semaphore(self.max_concurrency)
            
            # 创建爬取任务
            tasks = [self._fetch_and_process_article_async(url, semaphore) for url in urls_to_crawl]
            
            # 执行爬取任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理爬取结果
            articles = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"爬取任务异常: {str(result)}")
                    continue
                
                if result and isinstance(result, dict):
                    articles.append(result)
            
            # 记录结束性能统计
            if self.options.get('monitor_performance', True):
                self._record_end_performance()
            
            # 关闭HTTP客户端会话
            await self.close()
            
            # 返回爬取结果
            time_elapsed = time.time() - start_time
            logger.info(f"爬取完成: 成功 {self.success_count}, 失败 {self.failed_count}, 耗时 {time_elapsed:.2f}秒")
            
            return {
                "success": True,
                "message": f"成功爬取 {self.success_count} 篇文章",
                "articles": articles,
                "stats": {
                    "total": self.success_count + self.failed_count,
                    "success": self.success_count,
                    "failed": self.failed_count,
                    "time_elapsed": time_elapsed
                }
            }
                
        except Exception as e:
            logger.error(f"异步爬取过程中发生错误: {str(e)}")
            import traceback
            logger.debug(f"详细错误: {traceback.format_exc()}")
            
            # 记录结束性能统计
            if self.options.get('monitor_performance', True):
                self._record_end_performance()
            
            # 确保关闭HTTP客户端会话，即使发生错误
            try:
                await self.close()
            except Exception as close_error:
                logger.error(f"关闭HTTP客户端时出错: {str(close_error)}")
            
            return {
                "success": False,
                "message": f"爬取过程发生错误: {str(e)}",
                "stats": {
                    "total": self.success_count + self.failed_count,
                    "success": self.success_count,
                    "failed": self.failed_count,
                    "time_elapsed": time.time() - start_time
                }
            }
    
    async def _fetch_urls_async(self, days: int, category: Optional[str] = None) -> List[str]:
        """获取文章URL列表的异步方法"""
        logger.info(f"开始获取{self.source}的文章URL列表，天数: {days}, 分类: {category or '默认'}")
        
        # 获取列表页URL
        list_page_urls = self.strategy.get_list_page_urls(days, category)
        if not list_page_urls:
            logger.warning(f"未找到任何列表页URL，请检查爬虫策略配置")
            return []
        
        logger.info(f"找到 {len(list_page_urls)} 个列表页: {list_page_urls[:3]}...")
        
        # 爬取所有列表页获取文章URL
        semaphore = asyncio.Semaphore(self.max_concurrency)
        
        # 异步爬取每个列表页
        tasks = []
        for url in list_page_urls:
            tasks.append(self._fetch_list_page_async(url, semaphore))
        
        logger.info(f"创建了 {len(tasks)} 个列表页爬取任务，开始执行...")
        
        # 等待所有列表页爬取完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果，合并所有文章URL
        all_urls = []
        success_count = 0
        error_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"列表页爬取异常: {str(result)}")
                error_count += 1
                continue
                
            if isinstance(result, list):
                success_count += 1
                all_urls.extend(result)
        
        # 去重
        unique_urls = list(dict.fromkeys(all_urls))
        logger.info(f"列表页爬取完成: 成功 {success_count}，失败 {error_count}，获取到 {len(unique_urls)} 个文章URL")
        
        # 打印一些示例URL
        if unique_urls:
            logger.info(f"URL示例: {unique_urls[:3]}")
        
        return unique_urls
    
    async def _fetch_list_page_async(self, url: str, semaphore: asyncio.Semaphore) -> List[str]:
        """异步爬取单个列表页获取文章URL"""
        async with semaphore:
            try:
                # 获取列表页内容
                html = await self.http_client.fetch(url)
                
                # 解析文章URL
                article_urls = self.strategy.parse_list_page(html, url)
                logger.debug(f"从列表页 {url} 获取到 {len(article_urls)} 个文章URL")
                
                return article_urls
            except Exception as e:
                logger.error(f"爬取列表页失败: {url}, 错误: {str(e)}")
                return []
    
    def _on_crawl_complete(self, future):
        """爬取完成的回调处理"""
        try:
            results = future.result()
            
            # 计算成功和失败数
            success_count = 0
            failed_count = 0
            
            for result in results:
                if isinstance(result, Exception):
                    failed_count += 1
                    logger.error(f"爬取任务异常: {str(result)}")
                elif result:
                    success_count += 1
            
            # 记录结束性能统计
            if self.options.get('monitor_performance', True):
                self._record_end_performance()
                
            logger.info(f"异步爬取回调处理完成: 成功 {success_count}, 失败 {failed_count}")
            
        except Exception as e:
            logger.error(f"处理爬取结果回调时发生错误: {str(e)}")
            import traceback
            logger.debug(f"详细错误: {traceback.format_exc()}")
    
    async def _fetch_and_process_article_async(self, url: str, semaphore: asyncio.Semaphore) -> Optional[Dict[str, Any]]:
        """
        增强版异步获取并处理文章，增加域名级并发控制和性能监控

        Args:
            url: 文章URL
            semaphore: 全局并发控制信号量

        Returns:
            Optional[Dict]: 文章数据或None（失败时）
        """
        start_time = time.time()
        domain = urlparse(url).netloc
        
        # 确保该域名有信号量控制
        if domain not in self.domain_semaphores:
            domain_concurrency = self.options.get('domain_concurrency', 5)
            self.domain_semaphores[domain] = asyncio.Semaphore(domain_concurrency)
            self.domain_crawl_stats[domain] = {"success": 0, "failed": 0, "total_time": 0}
            self.domain_delays[domain] = 0  # 初始无延迟
        
        # 同时使用全局信号量和域名信号量
        async with semaphore, self.domain_semaphores[domain]:
            # 应用域名级别的延迟(如果有)
            delay = self.domain_delays.get(domain, 0)
            if delay > 0:
                await asyncio.sleep(delay)
            
            # 记录请求间隔
            if domain in self.request_intervals:
                last_request_time = self.request_intervals[domain]
                interval = time.time() - last_request_time
                if interval < 0.1:  # 如果间隔太短，可能是批量请求
                    if self.options.get('adaptive_speed', True):
                        # 动态增加延迟以避免请求过快
                        new_delay = self.domain_delays.get(domain, 0) + 0.1
                        self.domain_delays[domain] = min(new_delay, 1.0)  # 最多增加到1秒
            
            # 更新最后请求时间
            self.request_intervals[domain] = time.time()
            
            try:
                # 执行实际的抓取
                result = await super()._fetch_and_process_article_async(url, asyncio.Semaphore(1))
                
                # 记录性能数据
                if self.options.get('monitor_performance', True):
                    latency = time.time() - start_time
                    self.performance_stats['total_requests'] += 1
                    self.performance_stats['latency_samples'].append(latency)
                    
                    if result and isinstance(result, dict):
                        # 估算带宽使用
                        content_size = len(str(result)) * 2  # 粗略估计字节数
                        self.performance_stats['bandwidth_used'] += content_size
                        
                        # 更新域名统计
                        if domain not in self.performance_stats['domain_stats']:
                            self.performance_stats['domain_stats'][domain] = {
                                'requests': 0, 'success': 0, 'failed': 0, 'avg_latency': 0
                            }
                        
                        self.performance_stats['domain_stats'][domain]['requests'] += 1
                        self.performance_stats['domain_stats'][domain]['success'] += 1
                        
                        # 更新平均延迟
                        prev_avg = self.performance_stats['domain_stats'][domain]['avg_latency']
                        prev_count = self.performance_stats['domain_stats'][domain]['requests'] - 1
                        new_avg = (prev_avg * prev_count + latency) / self.performance_stats['domain_stats'][domain]['requests']
                        self.performance_stats['domain_stats'][domain]['avg_latency'] = new_avg
                
                # 成功请求后可以减少延迟
                if self.options.get('adaptive_speed', True) and self.domain_delays.get(domain, 0) > 0:
                    self.domain_delays[domain] = max(0, self.domain_delays[domain] - 0.05)
                
                # 更新域名统计
                self.domain_crawl_stats[domain]["success"] += 1
                self.domain_crawl_stats[domain]["total_time"] += (time.time() - start_time)
                
                return result
                
            except Exception as e:
                error_str = str(e).lower()
                logger.error(f"增强爬虫处理URL失败: {url}, 错误: {str(e)}")
                
                # 更新性能监控
                if self.options.get('monitor_performance', True):
                    self.performance_stats['total_requests'] += 1
                    
                    if domain not in self.performance_stats['domain_stats']:
                        self.performance_stats['domain_stats'][domain] = {
                            'requests': 0, 'success': 0, 'failed': 0, 'avg_latency': 0
                        }
                    
                    self.performance_stats['domain_stats'][domain]['requests'] += 1
                    self.performance_stats['domain_stats'][domain]['failed'] += 1
                
                # 智能重试逻辑
                if self.options.get('intelligent_retry', True):
                    if 'timeout' in error_str or 'connection' in error_str or 'reset' in error_str:
                        # 网络问题，增加该域名的延迟
                        new_delay = self.domain_delays.get(domain, 0) + 0.5
                        max_delay = self.options.get('max_retry_wait', 30)
                        self.domain_delays[domain] = min(new_delay, max_delay)
                        logger.warning(f"增加域名 {domain} 的请求延迟到 {self.domain_delays[domain]}秒")
                    
                    if '429' in error_str or 'too many' in error_str or 'rate limit' in error_str:
                        # 请求过多，显著增加延迟
                        self.domain_delays[domain] = min(self.domain_delays.get(domain, 0) + 2.0, 
                                                         self.options.get('max_retry_wait', 30))
                        logger.warning(f"检测到请求频率限制，大幅增加域名 {domain} 的延迟到 {self.domain_delays[domain]}秒")
                
                # 更新域名统计
                self.domain_crawl_stats[domain]["failed"] += 1
                self.domain_crawl_stats[domain]["total_time"] += (time.time() - start_time)
                
                return None
    
    def _start_memory_monitoring(self):
        """启动内存监控"""
        # 记录初始内存使用
        process = psutil.Process(os.getpid())
        self.memory_usage = [process.memory_info().rss / 1024 / 1024]  # MB
        self.performance_stats['memory_peak'] = self.memory_usage[0]
    
    def _update_memory_stats(self):
        """更新内存使用统计"""
        try:
            process = psutil.Process(os.getpid())
            current_mem = process.memory_info().rss / 1024 / 1024  # MB
            self.memory_usage.append(current_mem)
            
            # 更新峰值
            if current_mem > self.performance_stats['memory_peak']:
                self.performance_stats['memory_peak'] = current_mem
                
            # 检查是否超过内存限制
            memory_limit = self.options.get('memory_limit', 500)  # MB
            if current_mem > memory_limit:
                logger.warning(f"内存使用超过限制 ({current_mem:.1f}MB > {memory_limit}MB)，尝试释放内存")
                self._reduce_memory_usage()
        except Exception as e:
            logger.error(f"更新内存统计时出错: {str(e)}")
    
    def _reduce_memory_usage(self):
        """尝试减少内存使用"""
        # 主动触发垃圾回收
        gc.collect()
        # 清除不必要的缓存
        if hasattr(self, 'http_client') and hasattr(self.http_client, 'clear_cache'):
            self.http_client.clear_cache()
    
    def _record_end_performance(self):
        """记录爬取结束时的性能数据"""
        self.performance_stats['end_time'] = time.time()
        
        # 更新内存统计最后一次
        self._update_memory_stats()
        
        # 计算平均延迟
        if self.performance_stats['latency_samples']:
            self.performance_stats['average_latency'] = sum(self.performance_stats['latency_samples']) / len(self.performance_stats['latency_samples'])
        
        # 打印性能报告
        total_time = self.performance_stats['end_time'] - self.performance_stats['start_time']
        logger.info(f"增强爬虫性能报告:")
        logger.info(f"- 总请求数: {self.performance_stats['total_requests']}")
        logger.info(f"- 总耗时: {total_time:.2f}秒")
        logger.info(f"- 平均延迟: {self.performance_stats['average_latency']:.3f}秒")
        logger.info(f"- 估计带宽使用: {self.performance_stats['bandwidth_used']/1024/1024:.2f}MB")
        logger.info(f"- 内存峰值使用: {self.performance_stats['memory_peak']:.2f}MB")
        
        # 每个域名的统计信息
        for domain, stats in self.performance_stats['domain_stats'].items():
            if stats['requests'] > 0:
                logger.info(f"- 域名 {domain}: {stats['requests']}请求, "
                           f"{stats['success']}成功, {stats['failed']}失败, "
                           f"平均延迟{stats['avg_latency']:.3f}秒")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计数据

        Returns:
            Dict: 详细的性能统计信息
        """
        # 确保如果在爬取过程中调用，也能获取到当前状态
        if self.performance_stats['start_time'] and not self.performance_stats['end_time']:
            self.performance_stats['end_time'] = time.time()
            if self.options.get('monitor_performance', True):
                self._update_memory_stats()
            
        return {
            'duration': (self.performance_stats['end_time'] or time.time()) - 
                       (self.performance_stats['start_time'] or time.time()),
            'requests': self.performance_stats['total_requests'],
            'avg_latency': self.performance_stats['average_latency'],
            'bandwidth_mb': self.performance_stats['bandwidth_used'] / 1024 / 1024,
            'memory_peak_mb': self.performance_stats['memory_peak'],
            'memory_trend': self.memory_usage if hasattr(self, 'memory_usage') else [],
            'domain_stats': self.performance_stats['domain_stats'],
            'domain_delays': self.domain_delays
        }
    
    async def close(self):
        """
        关闭所有资源和连接
        
        在爬虫工作完成后应调用此方法以清理资源
        """
        logger.info("关闭增强爬虫资源...")
        
        # 关闭HTTP客户端
        if hasattr(self, 'http_client') and hasattr(self.http_client, 'close'):
            try:
                if asyncio.iscoroutinefunction(self.http_client.close):
                    await self.http_client.close()
                else:
                    self.http_client.close()
                logger.info("HTTP客户端会话已关闭")
            except Exception as e:
                logger.error(f"关闭HTTP客户端时出错: {str(e)}")
        
        # 清理其他资源
        self.domain_semaphores.clear()
        self.domain_delays.clear()
        self.request_intervals.clear()
        
        # 触发垃圾回收
        gc.collect()
        logger.info("增强爬虫资源已清理完毕")
    
    def crawl(self, days: int = 1, max_news: int = 100, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        同步爬取方法，兼容BaseCrawler接口
        这是一个简单的同步包装器，实际上会通过asyncio运行异步爬取方法
        
        Args:
            days: 爬取最近几天的新闻
            max_news: 最大爬取文章数
            category: 新闻分类
            
        Returns:
            List[Dict[str, Any]]: 爬取的文章列表
        """
        import asyncio
        
        logger.info(f"增强爬虫同步方法被调用，将转为执行异步爬取")
        
        # 尝试使用asyncio.run
        try:
            result = asyncio.run(self.crawl_async(days, max_news, category))
            # 确保返回格式一致
            if isinstance(result, dict) and 'articles' in result:
                return result['articles']
            return []
        except Exception as e:
            logger.error(f"增强爬虫同步爬取失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return [] 