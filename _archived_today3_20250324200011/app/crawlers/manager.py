#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 爬虫管理器
"""

import os
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.database import NewsDatabase
from app.crawlers.base import BaseCrawler
from app.crawlers.eastmoney import EastMoneyCrawler
from app.crawlers.sina import SinaCrawler
from app.crawlers.tencent import TencentCrawler

logger = get_logger(__name__)

class CrawlerManager:
    """爬虫管理器"""

    def __init__(self):
        """初始化爬虫管理器"""
        self.settings = get_settings()
        self.db = NewsDatabase()
        self.crawlers: Dict[str, BaseCrawler] = {}
        self.crawler_threads: Dict[str, threading.Thread] = {}
        self.stop_flags: Dict[str, threading.Event] = {}

        # 初始化爬虫
        self.init_crawlers()

    def init_crawlers(self):
        """初始化爬虫"""
        # 注册爬虫
        eastmoney_crawler = EastMoneyCrawler()
        eastmoney_crawler.source = "东方财富网"
        eastmoney_crawler.name = "eastmoney"
        
        sina_crawler = SinaCrawler()
        sina_crawler.source = "新浪财经"
        sina_crawler.name = "sina"
        
        tencent_crawler = TencentCrawler()
        tencent_crawler.source = "腾讯财经"
        tencent_crawler.name = "tencent"
        
        self.register_crawler('eastmoney', eastmoney_crawler)
        self.register_crawler('sina', sina_crawler)
        self.register_crawler('tencent', tencent_crawler)

    def register_crawler(self, name: str, crawler: BaseCrawler):
        """注册爬虫"""
        self.crawlers[name] = crawler
        self.stop_flags[name] = threading.Event()

    def get_crawlers(self) -> List[BaseCrawler]:
        """获取所有爬虫"""
        return list(self.crawlers.values())

    def get_available_crawlers(self) -> List[str]:
        """获取所有可用的爬虫名称"""
        return list(self.crawlers.keys())

    def get_crawler(self, name: str) -> Optional[BaseCrawler]:
        """获取指定爬虫"""
        return self.crawlers.get(name)

    def start_crawler(self, name: str):
        """启动指定爬虫"""
        if name not in self.crawlers:
            raise ValueError(f"爬虫 {name} 不存在")

        if name in self.crawler_threads and self.crawler_threads[name].is_alive():
            raise RuntimeError(f"爬虫 {name} 已在运行")

        # 创建停止标志
        self.stop_flags[name].clear()

        # 创建并启动线程
        thread = threading.Thread(
            target=self._crawler_worker,
            args=(name,),
            daemon=True
        )
        self.crawler_threads[name] = thread
        thread.start()

        logger.info(f"爬虫 {name} 已启动")

    def stop_crawler(self, name: str):
        """停止指定爬虫"""
        if name not in self.crawlers:
            raise ValueError(f"爬虫 {name} 不存在")

        if name not in self.crawler_threads or not self.crawler_threads[name].is_alive():
            raise RuntimeError(f"爬虫 {name} 未在运行")

        # 设置停止标志
        self.stop_flags[name].set()

        # 等待线程结束
        self.crawler_threads[name].join()

        logger.info(f"爬虫 {name} 已停止")

    def start_all(self):
        """启动所有爬虫"""
        for name in self.crawlers:
            try:
                self.start_crawler(name)
            except Exception as e:
                logger.error(f"启动爬虫 {name} 失败: {str(e)}")

    def stop_all(self):
        """停止所有爬虫"""
        for name in self.crawlers:
            try:
                self.stop_crawler(name)
            except Exception as e:
                logger.error(f"停止爬虫 {name} 失败: {str(e)}")

    def _crawler_worker(self, name: str):
        """爬虫工作线程"""
        crawler = self.crawlers[name]
        stop_flag = self.stop_flags[name]

        # 为线程创建新的数据库连接
        thread_db = NewsDatabase()

        while not stop_flag.is_set():
            try:
                # 更新爬虫状态
                crawler.status = 'running'
                crawler.last_run = datetime.now()

                # 执行爬取
                news_list = crawler.crawl()

                # 保存数据
                for news in news_list:
                    try:
                        # 确保新闻包含正确的来源
                        if 'source' not in news or not news['source']:
                            news['source'] = crawler.source
                        thread_db.add_news(news)
                    except Exception as e:
                        logger.error(f"保存新闻失败: {str(e)}")

                # 更新爬虫状态
                crawler.status = 'idle'
                crawler.next_run = datetime.now() + timedelta(minutes=self.settings['crawler_interval'])
                crawler.success_count += 1

                # 等待下一次运行
                while not stop_flag.is_set():
                    if datetime.now() >= crawler.next_run:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"爬虫 {name} 运行出错: {str(e)}")
                crawler.status = 'error'
                crawler.error_count += 1
                time.sleep(60)  # 出错后等待1分钟再重试

    def get_status(self) -> Dict:
        """获取爬虫状态"""
        status = {}
        for name, crawler in self.crawlers.items():
            status[name] = {
                'status': crawler.status,
                'last_run': crawler.last_run.strftime('%Y-%m-%d %H:%M:%S') if crawler.last_run else None,
                'next_run': crawler.next_run.strftime('%Y-%m-%d %H:%M:%S') if crawler.next_run else None,
                'error_count': crawler.error_count,
                'success_count': crawler.success_count
            }
        return status

    def close(self):
        """关闭爬虫管理器"""
        self.stop_all()
        self.db.close()

    def run_crawler(self, crawler_name: str, **params) -> int:
        """运行指定爬虫

        Args:
            crawler_name: 爬虫名称
            **params: 爬虫参数

        Returns:
            int: 获取的新闻数量
        """
        if crawler_name not in self.crawlers:
            logger.error(f"未找到爬虫: {crawler_name}")
            return 0

        crawler = self.crawlers[crawler_name]

        # 设置参数
        for key, value in params.items():
            if hasattr(crawler, key):
                setattr(crawler, key, value)

        # 运行爬虫
        try:
            logger.info(f"开始运行爬虫: {crawler_name}")
            result = crawler.crawl(**params)
            logger.info(f"爬虫 {crawler_name} 运行完成，共获取 {len(result)} 条新闻")
            
            # 创建新的数据库连接保存数据
            thread_db = NewsDatabase()
            for news in result:
                try:
                    # 确保新闻包含正确的来源
                    if 'source' not in news or not news['source']:
                        news['source'] = crawler.source
                    thread_db.add_news(news)
                except Exception as e:
                    logger.error(f"保存新闻失败: {str(e)}")
            
            # 更新爬虫状态
            crawler.success_count += 1
            return len(result)
        except Exception as e:
            logger.error(f"运行爬虫 {crawler_name} 失败: {e}")
            crawler.error_count += 1
            return 0

    def set_proxy(self, proxy_type: str, proxy_url: str):
        """设置所有爬虫的代理

        Args:
            proxy_type: 代理类型，如http, socks5
            proxy_url: 代理URL
        """
        for crawler in self.crawlers.values():
            if hasattr(crawler, 'proxy_type'):
                crawler.proxy_type = proxy_type
            if hasattr(crawler, 'proxy_url'):
                crawler.proxy_url = proxy_url
            crawler.use_proxy = True
