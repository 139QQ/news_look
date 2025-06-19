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
from backend.app.config import get_settings
from backend.app.utils.logger import get_logger
from backend.app.utils.database import NewsDatabase
from backend.newslook.crawlers.base import BaseCrawler
from backend.newslook.crawlers.eastmoney import EastMoneyCrawler
from backend.newslook.crawlers.eastmoney_simple import EastMoneySimpleCrawler
from backend.newslook.crawlers.sina import SinaCrawler
from backend.newslook.crawlers.tencent import TencentCrawler
from backend.newslook.crawlers.netease import NeteaseCrawler
from backend.newslook.crawlers.ifeng import IfengCrawler
from backend.newslook.core.database_path_manager import get_database_path_manager
import re
import sqlite3

logger = get_logger(__name__)

class CrawlerManager:
    """爬虫管理器"""

    def __init__(self, settings=None):
        """
        初始化爬虫管理器
        
        Args:
            settings: 配置字典
        """
        # 首先从app.config获取设置，然后用传入的settings更新它（如果有）
        config_settings = get_settings()
        self.settings = {} 
        # 确保将config_settings中的设置复制到self.settings字典中
        if hasattr(config_settings, 'settings'):
            # 如果是配置对象
            for key, value in config_settings.settings.items():
                self.settings[key] = value
        else:
            # 如果是字典
            self.settings.update(config_settings)
            
        # 如果传入了settings，更新self.settings
        if settings:
            self.settings.update(settings)
            
        self.crawlers = {}
        
        # 使用统一的数据库路径管理器
        self.db_path_manager = get_database_path_manager()
        db_dir = str(self.db_path_manager.db_dir)
        self.settings['DB_DIR'] = db_dir
        
        # 确保目录存在
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"爬虫管理器使用统一数据库目录: {db_dir}")
        
        # 初始化线程相关属性
        self.crawler_threads = {}
        self.stop_flags = {}
        
        # 初始化数据库连接
        try:
            # 尝试使用传入的db_path连接数据库
            self.db = NewsDatabase()
        except Exception as e:
            logger.error(f"连接数据库失败: {str(e)}")
            self.db = None
            
        # 导入所有爬虫类
        try:
            # 初始化所有爬虫
            self._init_crawlers()
            
            # 添加到字典
            self.crawlers["东方财富"] = self.eastmoney_crawler
            self.crawlers["东方财富简版"] = self.eastmoney_simple_crawler
            self.crawlers["新浪财经"] = self.sina_crawler
            self.crawlers["腾讯财经"] = self.tencent_crawler
            self.crawlers["网易财经"] = self.netease_crawler
            self.crawlers["凤凰财经"] = self.ifeng_crawler
            
            # 初始化stop_flags
            for name in self.crawlers.keys():
                self.stop_flags[name] = threading.Event()
            
            logger.info(f"已初始化 {len(self.crawlers)} 个爬虫")
            
        except ImportError as e:
            logger.error(f"导入爬虫模块失败: {str(e)}")
    
    def _init_crawlers(self):
        """初始化所有爬虫实例"""
        try:
            # 导入统一数据库路径配置
            from backend.newslook.config import get_unified_db_path
            
            # 获取统一的数据库路径
            unified_db_path = get_unified_db_path()
            
            # 初始化各个爬虫，使用统一的数据库路径
            self.eastmoney_crawler = EastMoneyCrawler(
                use_proxy=self.settings.get('USE_PROXY', False),
                use_source_db=False,  # 统一使用主数据库
                db_path=unified_db_path
            )
            self._set_unified_db_path(self.eastmoney_crawler, "东方财富")
            
            self.eastmoney_simple_crawler = EastMoneySimpleCrawler(
                use_proxy=self.settings.get('USE_PROXY', False),
                use_source_db=False,  # 统一使用主数据库
                db_path=unified_db_path
            )
            # 修正东方财富简版爬虫的source属性，与主爬虫保持一致
            if hasattr(self.eastmoney_simple_crawler, 'source') and self.eastmoney_simple_crawler.source != "东方财富":
                self.eastmoney_simple_crawler.source = "东方财富"
                logger.info(f"已修正东方财富简版爬虫的source属性为'东方财富'")
            self._set_unified_db_path(self.eastmoney_simple_crawler, "东方财富")
            
            self.sina_crawler = SinaCrawler(
                use_proxy=self.settings.get('USE_PROXY', False),
                use_source_db=False,  # 统一使用主数据库
                db_path=unified_db_path
            )
            self._set_unified_db_path(self.sina_crawler, "新浪财经")
            
            self.tencent_crawler = TencentCrawler(
                use_proxy=self.settings.get('USE_PROXY', False),
                use_source_db=False,  # 统一使用主数据库
                db_path=unified_db_path
            )
            self._set_unified_db_path(self.tencent_crawler, "腾讯财经")
            
            self.netease_crawler = NeteaseCrawler(
                use_proxy=self.settings.get('USE_PROXY', False),
                use_source_db=False,  # 统一使用主数据库
                db_path=unified_db_path
            )
            self._set_unified_db_path(self.netease_crawler, "网易财经")
            
            self.ifeng_crawler = IfengCrawler(
                use_proxy=self.settings.get('USE_PROXY', False),
                use_source_db=False,  # 统一使用主数据库
                db_path=unified_db_path
            )
            self._set_unified_db_path(self.ifeng_crawler, "凤凰财经")
            
            # 确保每个爬虫的source属性正确设置
            self._verify_sources()
            
            # 打印初始化信息
            logger.info("爬虫管理器初始化完成，可用爬虫:")
            logger.info(f"- 东方财富 (EastmoneyCrawler): {unified_db_path}")
            logger.info(f"- 东方财富简版 (EastMoneySimpleCrawler): {unified_db_path}")
            logger.info(f"- 新浪财经 (SinaCrawler): {unified_db_path}")
            logger.info(f"- 腾讯财经 (TencentCrawler): {unified_db_path}")
            logger.info(f"- 网易财经 (NeteaseCrawler): {unified_db_path}")
            logger.info(f"- 凤凰财经 (IfengCrawler): {unified_db_path}")
            logger.info(f"所有爬虫统一使用数据库: {unified_db_path}")
            
        except Exception as e:
            logger.error(f"初始化爬虫失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def _set_unified_db_path(self, crawler, source_name):
        """
        设置爬虫的统一数据库路径
        
        Args:
            crawler: 爬虫实例
            source_name: 来源名称
        """
        # 确保source属性被正确设置
        if hasattr(crawler, 'source') and crawler.source == "未知来源":
            crawler.source = source_name
            logger.warning(f"爬虫 {crawler.__class__.__name__} 的source属性未设置，已设置为 {source_name}")
        
        # 获取统一的数据库路径
        from backend.newslook.config import get_unified_db_path
        unified_db_path = get_unified_db_path()
        
        if hasattr(crawler, 'db_path'):
            crawler.db_path = unified_db_path
            logger.info(f"设置爬虫 {crawler.__class__.__name__} 统一数据库路径: {unified_db_path}")
        
        # 如果数据库不存在，则创建数据库结构
        if not os.path.exists(unified_db_path):
            logger.info(f"统一数据库 {unified_db_path} 不存在，将创建")
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(unified_db_path), exist_ok=True)
                
                conn = sqlite3.connect(unified_db_path)
                cursor = conn.cursor()
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    content TEXT,
                    url TEXT UNIQUE,
                    publish_time TEXT,
                    crawl_time TEXT,
                    source TEXT,
                    category TEXT,
                    image_url TEXT,
                    sentiment REAL,
                    summary TEXT
                )
                ''')
                conn.commit()
                conn.close()
                logger.info(f"成功创建统一数据库 {unified_db_path}")
            except Exception as e:
                logger.error(f"创建统一数据库 {unified_db_path} 失败: {str(e)}")
    
    # 保留旧方法以兼容性，但已标记为废弃
    def _set_db_path(self, crawler, source_name):
        """
        [已废弃] 设置爬虫的数据库路径，请使用 _set_unified_db_path
        """
        logger.warning("_set_db_path 方法已废弃，请使用 _set_unified_db_path")
        self._set_unified_db_path(crawler, source_name)
    
    def _verify_sources(self):
        """验证所有爬虫的source属性是否正确设置，并统一来源名称格式"""
        crawlers = {
            'eastmoney_crawler': ('东方财富', self.eastmoney_crawler),
            'eastmoney_simple_crawler': ('东方财富', self.eastmoney_simple_crawler),
            'sina_crawler': ('新浪财经', self.sina_crawler),
            'tencent_crawler': ('腾讯财经', self.tencent_crawler),
            'netease_crawler': ('网易财经', self.netease_crawler),
            'ifeng_crawler': ('凤凰财经', self.ifeng_crawler)
        }
        
        for name, (expected_source, crawler) in crawlers.items():
            if hasattr(crawler, 'source'):
                current_source = crawler.source
                # 标准化来源名称，处理常见变体
                if current_source.endswith('网') and current_source != expected_source:
                    # 例如："东方财富网" -> "东方财富"
                    crawler.source = expected_source
                    logger.info(f"已统一爬虫 {name} 的source属性从 '{current_source}' 改为 '{expected_source}'")
                elif current_source != expected_source:
                    logger.warning(f"爬虫 {name} 的source属性为 '{current_source}'，与预期的 '{expected_source}' 不符，已修正")
                    crawler.source = expected_source
            else:
                logger.error(f"爬虫 {name} 没有source属性")
                # 尝试设置source属性
                try:
                    crawler.source = expected_source
                    logger.info(f"已为爬虫 {name} 设置source属性为 '{expected_source}'")
                except Exception as e:
                    logger.error(f"为爬虫 {name} 设置source属性失败: {str(e)}")
                    
        logger.info("已完成爬虫来源属性验证和统一格式化")

    def get_crawlers(self) -> List[BaseCrawler]:
        """获取所有爬虫"""
        return list(self.crawlers.values())
    
    def get_all_crawlers(self) -> Dict[str, type]:
        """获取所有爬虫类型映射"""
        return {
            'eastmoney': EastMoneyCrawler,
            'eastmoney_simple': EastMoneySimpleCrawler,
            'sina': SinaCrawler,
            'tencent': TencentCrawler,
            'netease': NeteaseCrawler,
            'ifeng': IfengCrawler
        }

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

        # 运行爬虫
        try:
            logger.info(f"开始运行爬虫: {crawler_name}")
            
            # 提取days参数
            days = params.get('days', 1)
            
            # 只传递days参数给爬虫的crawl方法
            result = crawler.crawl(days=days)
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
            import traceback
            logger.error(traceback.format_exc())
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
