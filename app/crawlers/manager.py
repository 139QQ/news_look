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
from app.crawlers.netease import NeteaseCrawler
from app.crawlers.ifeng import IfengCrawler
import re

logger = get_logger(__name__)

class CrawlerManager:
    """爬虫管理器"""

    def __init__(self, settings=None):
        """
        初始化爬虫管理器
        
        Args:
            settings: 配置字典
        """
        self.settings = settings or {}
        self.crawlers = {}
        
        # 获取数据库目录
        db_dir = self.settings.get('DB_DIR', os.path.join(os.getcwd(), 'data', 'db'))
        os.makedirs(db_dir, exist_ok=True)
        
        # 导入所有爬虫类
        try:
            # 初始化所有爬虫
            ifeng_crawler = IfengCrawler()
            sina_crawler = SinaCrawler()
            tencent_crawler = TencentCrawler()
            netease_crawler = NeteaseCrawler()
            eastmoney_crawler = EastMoneyCrawler()
            
            # 设置爬虫来源
            ifeng_crawler.source = "凤凰财经"
            sina_crawler.source = "新浪财经"
            tencent_crawler.source = "腾讯财经"
            netease_crawler.source = "网易财经"
            eastmoney_crawler.source = "东方财富"
            
            # 为每个爬虫设置固定的数据库路径
            self._set_db_path(ifeng_crawler, "凤凰财经")
            self._set_db_path(sina_crawler, "新浪财经")
            self._set_db_path(tencent_crawler, "腾讯财经")
            self._set_db_path(netease_crawler, "网易财经")
            self._set_db_path(eastmoney_crawler, "东方财富")
            
            # 添加到字典
            self.crawlers["凤凰财经"] = ifeng_crawler
            self.crawlers["新浪财经"] = sina_crawler
            self.crawlers["腾讯财经"] = tencent_crawler
            self.crawlers["网易财经"] = netease_crawler
            self.crawlers["东方财富"] = eastmoney_crawler
            
            logger.info(f"已初始化 {len(self.crawlers)} 个爬虫")
            
        except ImportError as e:
            logger.error(f"导入爬虫模块失败: {str(e)}")
    
    def _set_db_path(self, crawler, source):
        """
        设置爬虫的数据库路径
        
        Args:
            crawler: 爬虫实例
            source: 爬虫来源
        """
        # 获取数据库目录
        db_dir = self.settings.get('DB_DIR', os.path.join(os.getcwd(), 'data', 'db'))
        
        # 将来源转换为文件名安全的字符串
        db_name = re.sub(r'[^\w]', '_', source.lower())
        
        # 生成固定的数据库路径
        db_path = os.path.join(db_dir, f"{db_name}.db")
        
        # 设置爬虫的数据库路径
        crawler.db_path = db_path
        
        # 如果有sqlite_manager属性，也更新它的db_path
        if hasattr(crawler, 'sqlite_manager'):
            crawler.sqlite_manager.db_path = db_path
        
        logger.info(f"设置 {source} 爬虫的数据库路径: {db_path}")

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
        thread_db = NewsDatabase(use_all_dbs=True)

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
                'name': name,
                'display_name': crawler.source,
                'status': getattr(crawler, 'status', 'unknown'),
                'last_run': getattr(crawler, 'last_run', None).strftime('%Y-%m-%d %H:%M:%S') if getattr(crawler, 'last_run', None) else None,
                'next_run': getattr(crawler, 'next_run', None).strftime('%Y-%m-%d %H:%M:%S') if getattr(crawler, 'next_run', None) else None,
                'error_count': getattr(crawler, 'error_count', 0),
                'success_count': getattr(crawler, 'success_count', 0)
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
            thread_db = NewsDatabase(use_all_dbs=True)
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
