#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 升级版爬虫管理器
支持新的统一爬虫架构
"""

import os
import time
import threading
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
from concurrent.futures import ThreadPoolExecutor

from app.config import get_settings
from app.utils.logger import get_logger

# 初始化日志记录器
logger = get_logger(__name__)

class EnhancedCrawlerManager:
    """
    升级版爬虫管理器，支持新的统一爬虫架构
    """

    def __init__(self, settings=None):
        """
        初始化爬虫管理器
        
        Args:
            settings: 配置字典，可覆盖默认配置
        """
        # 首先从app.config获取设置，然后用传入的settings更新它（如果有）
        config_settings = get_settings()
        self.settings = {}
        
        # 确保将config_settings中的设置复制到self.settings字典中
        if hasattr(config_settings, 'settings'):
            for key, value in config_settings.settings.items():
                self.settings[key] = value
        else:
            # 如果config_settings是字典，直接复制
            self.settings = config_settings.copy()
            
        # 如果传入了settings，更新self.settings
        if settings:
            self.settings.update(settings)
        
        # 获取数据库目录
        db_dir = self.settings.get('DB_DIR')
        if not db_dir:
            # 如果在设置中没有找到DB_DIR，使用默认值
            db_dir = os.path.join(os.getcwd(), 'data', 'db')
            
        # 确保目录存在
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"爬虫管理器使用数据库目录: {db_dir}")
        
        # 将DB_DIR保存回设置
        self.settings['DB_DIR'] = db_dir
        
        # 初始化爬虫容器
        self.crawlers = {}
        self.crawler_tasks = {}
        self.stop_flags = {}
        
        # 初始化爬虫配置选项
        self.use_proxy = self.settings.get('USE_PROXY', False)
        self.use_async = self.settings.get('USE_ASYNC', True)
        
        # 加载爬虫
        self._load_crawlers()
        
    def _load_crawlers(self):
        """加载所有爬虫"""
        try:
            # 首先尝试导入新架构的爬虫类
            self._load_new_crawlers()
            
            # 如果新架构爬虫加载失败，尝试加载旧架构爬虫
            if not self.crawlers:
                logger.warning("未能加载新架构爬虫，尝试加载旧架构爬虫")
                self._load_legacy_crawlers()
                
            logger.info(f"已加载 {len(self.crawlers)} 个爬虫")
        except Exception as e:
            logger.error(f"加载爬虫失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _load_new_crawlers(self):
        """加载新架构的爬虫"""
        try:
            # 尝试导入新架构的东方财富爬虫
            from app.crawlers.eastmoney_new import EastMoneyCrawler
            
            # 配置数据库路径
            db_path = os.path.join(self.settings['DB_DIR'], "东方财富.db")
            
            # 创建爬虫实例
            options = {
                'async_mode': self.use_async,
                'use_proxy': self.use_proxy,
                'max_concurrency': self.settings.get('max_concurrency', 10)
            }
            
            self.crawlers["东方财富"] = EastMoneyCrawler(db_path, **options)
            logger.info("成功加载新架构的东方财富爬虫")
            
            # 随着项目进展，添加更多新架构爬虫的加载逻辑
            # 例如:
            # from app.crawlers.sina_new import SinaCrawler
            # self.crawlers["新浪财经"] = SinaCrawler(...)
            
        except ImportError as e:
            logger.warning(f"导入新架构爬虫失败: {str(e)}")
    
    def _load_legacy_crawlers(self):
        """加载旧架构的爬虫（向后兼容）"""
        try:
            # 导入旧架构的爬虫类
            from app.crawlers.eastmoney import EastMoneyCrawler
            from app.crawlers.sina import SinaCrawler
            from app.crawlers.netease import NeteaseCrawler
            from app.crawlers.ifeng import IfengCrawler
            
            # 创建爬虫实例
            self.crawlers["东方财富"] = EastMoneyCrawler()
            self.crawlers["新浪财经"] = SinaCrawler()
            self.crawlers["网易财经"] = NeteaseCrawler()
            self.crawlers["凤凰财经"] = IfengCrawler()
            
            # 设置数据库路径
            for name, crawler in self.crawlers.items():
                if hasattr(crawler, 'db_path'):
                    crawler.db_path = os.path.join(self.settings['DB_DIR'], f"{name}.db")
                    
            logger.info("成功加载旧架构爬虫")
        except ImportError as e:
            logger.warning(f"导入旧架构爬虫失败: {str(e)}")
    
    def get_crawlers(self) -> List[str]:
        """
        获取所有可用的爬虫名称
        
        Returns:
            List[str]: 爬虫名称列表
        """
        return list(self.crawlers.keys())
    
    def get_crawler(self, name: str):
        """
        获取指定名称的爬虫
        
        Args:
            name: 爬虫名称
            
        Returns:
            爬虫实例
        """
        return self.crawlers.get(name)
    
    def start_crawler(self, name: str, interval: int = 3600):
        """
        启动指定爬虫
        
        Args:
            name: 爬虫名称
            interval: 爬取间隔（秒）
        """
        if name not in self.crawlers:
            raise ValueError(f"爬虫 {name} 不存在")
            
        if name in self.crawler_tasks and not self.crawler_tasks[name].done():
            logger.warning(f"爬虫 {name} a已在运行中")
            return
            
        # 创建停止标志
        self.stop_flags[name] = threading.Event()
        
        # 创建爬虫任务
        if self.use_async:
            task = asyncio.create_task(self._crawler_async_worker(name, interval))
        else:
            # 使用线程执行同步爬虫
            executor = ThreadPoolExecutor(max_workers=1)
            loop = asyncio.get_event_loop()
            task = loop.run_in_executor(
                executor, 
                self._crawler_sync_worker, 
                name, 
                interval
            )
            
        self.crawler_tasks[name] = task
        logger.info(f"爬虫 {name} 已启动")
    
    def stop_crawler(self, name: str):
        """
        停止指定爬虫
        
        Args:
            name: 爬虫名称
        """
        if name not in self.crawlers:
            raise ValueError(f"爬虫 {name} 不存在")
            
        if name not in self.crawler_tasks or self.crawler_tasks[name].done():
            logger.warning(f"爬虫 {name} 未在运行")
            return
            
        # 设置停止标志
        self.stop_flags[name].set()
        
        # 等待任务完成
        try:
            # 取消任务
            self.crawler_tasks[name].cancel()
            logger.info(f"爬虫 {name} 已停止")
        except Exception as e:
            logger.error(f"停止爬虫 {name} 时出错: {str(e)}")
    
    def start_all(self, interval: int = 3600):
        """
        启动所有爬虫
        
        Args:
            interval: 爬取间隔（秒）
        """
        for name in self.crawlers:
            try:
                self.start_crawler(name, interval)
            except Exception as e:
                logger.error(f"启动爬虫 {name} 失败: {str(e)}")
    
    def stop_all(self):
        """停止所有爬虫"""
        for name in list(self.crawler_tasks.keys()):
            try:
                self.stop_crawler(name)
            except Exception as e:
                logger.error(f"停止爬虫 {name} 失败: {str(e)}")
    
    async def _crawler_async_worker(self, name: str, interval: int):
        """
        异步爬虫工作器
        
        Args:
            name: 爬虫名称
            interval: 爬取间隔（秒）
        """
        crawler = self.crawlers[name]
        stop_flag = self.stop_flags[name]
        
        while not stop_flag.is_set():
            try:
                logger.info(f"开始运行爬虫: {name}")
                start_time = time.time()
                
                # 检查爬虫是否支持异步模式
                if hasattr(crawler, 'crawl') and asyncio.iscoroutinefunction(crawler.crawl):
                    # 异步爬取
                    result = await crawler.crawl(days=1)
                else:
                    # 同步爬取（在线程池中执行）
                    loop = asyncio.get_event_loop()
                    with ThreadPoolExecutor() as executor:
                        result = await loop.run_in_executor(
                            executor,
                            crawler.crawl,
                            1  # days
                        )
                
                elapsed = time.time() - start_time
                logger.info(f"爬虫 {name} 运行完成，耗时 {elapsed:.2f} 秒，获取 {len(result)} 条新闻")
                
                # 等待下一次运行
                for _ in range(interval):
                    if stop_flag.is_set():
                        break
                    await asyncio.sleep(1)
                    
            except asyncio.CancelledError:
                logger.info(f"爬虫 {name} 任务被取消")
                break
            except Exception as e:
                logger.error(f"爬虫 {name} 运行出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
                # 错误后等待一段时间再重试
                await asyncio.sleep(60)
    
    def _crawler_sync_worker(self, name: str, interval: int):
        """
        同步爬虫工作器
        
        Args:
            name: 爬虫名称
            interval: 爬取间隔（秒）
        """
        crawler = self.crawlers[name]
        stop_flag = self.stop_flags[name]
        
        while not stop_flag.is_set():
            try:
                logger.info(f"开始运行爬虫: {name}")
                start_time = time.time()
                
                # 执行爬取
                result = crawler.crawl(days=1)
                
                elapsed = time.time() - start_time
                logger.info(f"爬虫 {name} 运行完成，耗时 {elapsed:.2f} 秒，获取 {len(result)} 条新闻")
                
                # 等待下一次运行
                for _ in range(interval):
                    if stop_flag.is_set():
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"爬虫 {name} 运行出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
                # 错误后等待一段时间再重试
                time.sleep(60)
    
    def run_crawler_once(self, name: str, days: int = 1, max_news: int = None) -> List[Dict[str, Any]]:
        """
        运行指定爬虫一次
        
        Args:
            name: 爬虫名称
            days: 爬取天数
            max_news: 最大新闻数量
            
        Returns:
            List[Dict[str, Any]]: 爬取的新闻列表
        """
        if name not in self.crawlers:
            raise ValueError(f"爬虫 {name} 不存在")
            
        crawler = self.crawlers[name]
        
        try:
            logger.info(f"开始运行爬虫: {name}")
            start_time = time.time()
            
            # 执行爬取
            result = crawler.crawl(days=days, max_news=max_news)
            
            elapsed = time.time() - start_time
            logger.info(f"爬虫 {name} 运行完成，耗时 {elapsed:.2f} 秒，获取 {len(result)} 条新闻")
            
            return result
        except Exception as e:
            logger.error(f"运行爬虫 {name} 失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def run_crawler_once_async(self, name: str, days: int = 1, max_news: int = None) -> List[Dict[str, Any]]:
        """
        异步运行指定爬虫一次
        
        Args:
            name: 爬虫名称
            days: 爬取天数
            max_news: 最大新闻数量
            
        Returns:
            List[Dict[str, Any]]: 爬取的新闻列表
        """
        if name not in self.crawlers:
            raise ValueError(f"爬虫 {name} 不存在")
            
        crawler = self.crawlers[name]
        
        try:
            logger.info(f"开始异步运行爬虫: {name}")
            start_time = time.time()
            
            # 检查爬虫是否支持异步模式
            if hasattr(crawler, 'crawl') and asyncio.iscoroutinefunction(crawler.crawl):
                # 异步爬取
                result = await crawler.crawl(days=days, max_news=max_news)
            else:
                # 同步爬取（在线程池中执行）
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(
                        executor,
                        crawler.crawl,
                        days,
                        max_news
                    )
            
            elapsed = time.time() - start_time
            logger.info(f"爬虫 {name} 异步运行完成，耗时 {elapsed:.2f} 秒，获取 {len(result)} 条新闻")
            
            return result
        except Exception as e:
            logger.error(f"异步运行爬虫 {name} 失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有爬虫的状态
        
        Returns:
            Dict[str, Dict[str, Any]]: 爬虫状态字典
        """
        status = {}
        
        for name, crawler in self.crawlers.items():
            # 检查爬虫是否在运行
            is_running = name in self.crawler_tasks and not self.crawler_tasks[name].done()
            
            # 获取爬虫的统计信息
            stats = {}
            if hasattr(crawler, 'get_stats'):
                try:
                    stats = crawler.get_stats()
                except Exception as e:
                    logger.error(f"获取爬虫 {name} 统计信息失败: {str(e)}")
            
            # 组装状态信息
            status[name] = {
                'name': name,
                'running': is_running,
                'type': crawler.__class__.__name__,
                'stats': stats
            }
            
        return status
    
    def close(self):
        """关闭管理器，释放资源"""
        # 停止所有爬虫
        self.stop_all()
        
        # 关闭爬虫资源
        for name, crawler in self.crawlers.items():
            if hasattr(crawler, 'close'):
                try:
                    # 检查close方法是否是协程方法
                    if asyncio.iscoroutinefunction(crawler.close):
                        # 使用事件循环创建一个新的任务执行关闭操作
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # 如果已有事件循环在运行，创建任务并等待其完成
                                future = asyncio.ensure_future(crawler.close())
                                # 等待任务完成，但设置超时避免无限等待
                                try:
                                    loop.run_until_complete(asyncio.wait_for(future, timeout=10))
                                except asyncio.TimeoutError:
                                    logger.warning(f"关闭爬虫 {name} 资源超时")
                            else:
                                # 如果没有事件循环在运行，创建一个新的循环
                                loop.run_until_complete(crawler.close())
                        except RuntimeError as e:
                            # 可能由于运行在不同线程或事件循环已关闭导致错误
                            logger.warning(f"尝试关闭爬虫 {name} 资源时遇到运行时错误: {str(e)}")
                            # 创建一个新的事件循环来关闭资源
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                new_loop.run_until_complete(crawler.close())
                            except Exception as inner_e:
                                logger.error(f"使用新事件循环关闭爬虫 {name} 资源失败: {str(inner_e)}")
                            finally:
                                new_loop.close()
                    else:
                        # 如果是同步方法，直接调用
                        crawler.close()
                    logger.info(f"爬虫 {name} 资源已关闭")
                except Exception as e:
                    logger.error(f"关闭爬虫 {name} 资源失败: {str(e)}")
                    
        logger.info("爬虫管理器已关闭")

    async def close_async(self):
        """异步关闭管理器，释放资源"""
        # 停止所有爬虫
        self.stop_all()
        
        # 关闭爬虫资源
        for name, crawler in self.crawlers.items():
            if hasattr(crawler, 'close'):
                try:
                    # 检查close方法是否是协程方法
                    if asyncio.iscoroutinefunction(crawler.close):
                        # 直接等待异步关闭方法
                        await crawler.close()
                    else:
                        # 如果是同步方法，直接调用
                        crawler.close()
                    logger.info(f"爬虫 {name} 资源已关闭")
                except Exception as e:
                    logger.error(f"关闭爬虫 {name} 资源失败: {str(e)}")
                    
        logger.info("爬虫管理器已异步关闭") 