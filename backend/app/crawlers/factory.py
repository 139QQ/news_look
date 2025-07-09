#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 爬虫工厂模块
负责创建和管理不同网站的爬虫实例
"""

import os
import json
import yaml
import logging
import sys
import importlib
import inspect
from typing import Dict, List, Any, Optional, Type
import asyncio
from pybloom_live import BloomFilter
import aiohttp
import time
from prometheus_client import Counter, Histogram
from dataclasses import dataclass, field, asdict

from app.utils.logger import get_logger
from app.crawlers.base import BaseCrawler
from app.utils.database import NewsDatabase
from app.config import get_settings

logger = get_logger('crawler_factory')

class URLManager:
    def __init__(self):
        self.visited_urls = BloomFilter(capacity=100000, error_rate=0.001)
        self.pending_urls = asyncio.Queue()
        self.failed_urls = set()
        
    async def add_url(self, url: str):
        if not self.is_visited(url):
            await self.pending_urls.put(url)
            
    def is_visited(self, url: str) -> bool:
        return url in self.visited_urls
        
    def mark_visited(self, url: str):
        self.visited_urls.add(url)

class ProxyPool:
    def __init__(self, max_size=100):
        self.proxies = []
        self.max_size = max_size
        self.lock = asyncio.Lock()
        self.proxy_scores = {}  # 代理评分系统

    async def get_proxy(self):
        """获取一个可用的代理"""
        async with self.lock:
            # 选择评分最高的可用代理
            valid_proxies = [p for p in self.proxies if self.proxy_scores[p] > 0]
            if valid_proxies:
                return max(valid_proxies, key=lambda x: self.proxy_scores[x])
            # 如果没有可用代理,返回None
            return None

    async def report_proxy_status(self, proxy, success: bool):
        """报告代理使用状态,更新评分"""
        if success:
            self.proxy_scores[proxy] = self.proxy_scores.get(proxy, 0) + 1
        else:
            self.proxy_scores[proxy] = self.proxy_scores.get(proxy, 0) - 1
            if self.proxy_scores[proxy] <= 0:
                # 移除无效代理
                if proxy in self.proxies:
                    self.proxies.remove(proxy)
                if proxy in self.proxy_scores:
                    del self.proxy_scores[proxy]

class ResourceManager:
    def __init__(self):
        self.session_pool = aiohttp.ClientSession()
        self.connection_pool = asyncio.Semaphore(100)
        self.proxy_pool = ProxyPool()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
        
    async def cleanup(self):
        await self.session_pool.close()

class CrawlerMetrics:
    def __init__(self):
        self.metrics = {
            'requests': Counter('crawler_requests_total', 'Total number of crawler requests'),
            'success': Counter('crawler_success_total', 'Total number of successful requests'),
            'failures': Counter('crawler_failures_total', 'Total number of failed requests'),
            'retry_count': Counter('crawler_retry_total', 'Total number of retry attempts'),
            'response_times': Histogram('crawler_response_time_seconds', 'Response time in seconds'),
            'content_lengths': Histogram('crawler_content_length_bytes', 'Response content length in bytes'),
            'status_codes': Counter('crawler_status_codes_total', 'Total requests by status code'),
            'error_types': Counter('crawler_error_types_total', 'Total errors by type')
        }
    
    async def record_request(self, url: str, start_time: float, status: int, 
                           content_length: int, error: Optional[Exception] = None):
        duration = time.time() - start_time
        self.metrics['response_times'].observe(duration)
        self.metrics['content_lengths'].observe(content_length)
        self.metrics['status_codes'].labels(status=status).inc()
        
        if error:
            self.metrics['error_types'].labels(type=type(error).__name__).inc()

@dataclass
class CrawlerConfig:
    max_retries: int = 3
    timeout: int = 30
    batch_size: int = 20
    max_concurrency: int = 10
    user_agent_rotation: bool = True
    proxy_enabled: bool = False
    save_failed_pages: bool = True
    retry_codes: List[int] = field(default_factory=lambda: [500, 502, 503, 504])
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class CrawlerFactory:
    """爬虫工厂类，负责创建各种爬虫实例"""
    
    def __init__(self):
        """初始化爬虫工厂"""
        self.settings = get_settings()
        self.crawlers_path = os.path.join(os.path.dirname(__file__), 'sites')
        self.crawler_classes = {}  # 缓存爬虫类
        self.crawler_instances = {}  # 缓存爬虫实例
        self.config_cache = {}  # 添加配置缓存字典
        self.config_dir = os.path.join(os.path.dirname(__file__), 'configs')  # 添加配置目录路径
        
        # 添加直接的爬虫映射，替代策略映射
        self.crawler_mapping = {
            'sina': 'app.crawlers.sina',
            'eastmoney': 'app.crawlers.eastmoney',
            'netease': 'app.crawlers.sites.netease', 
            'ifeng': 'app.crawlers.ifeng'
        }
        
        # 扫描并加载爬虫类
        self._scan_crawlers()
    
    def _scan_crawlers(self):
        """扫描并加载所有爬虫类"""
        # 确保爬虫目录存在
        if not os.path.exists(self.crawlers_path):
            logger.warning(f"爬虫目录不存在: {self.crawlers_path}")
            return
            
        # 确保爬虫目录可导入
        crawler_package = 'app.crawlers.sites'
        
        # 扫描爬虫目录中的所有.py文件
        for filename in os.listdir(self.crawlers_path):
            if filename.endswith('.py') and filename != '__init__.py':
                crawler_name = filename[:-3]  # 去掉.py后缀
                try:
                    # 动态导入模块
                    module_name = f"{crawler_package}.{crawler_name}"
                    module = importlib.import_module(module_name)
                    
                    # 查找模块中的爬虫类（BaseCrawler的子类）
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseCrawler) and 
                            obj != BaseCrawler and
                            hasattr(obj, 'source')):
                            # 缓存爬虫类
                            self.crawler_classes[crawler_name] = obj
                            logger.info(f"已加载爬虫类: {crawler_name} -> {obj.__name__}")
                            break
                except ImportError as e:
                    logger.error(f"导入爬虫模块失败 {crawler_name}: {e}")
                except Exception as e:
                    logger.error(f"加载爬虫类失败 {crawler_name}: {e}")
    
    def get_crawler_class(self, crawler_name: str) -> Optional[Type[BaseCrawler]]:
        """
        获取指定爬虫的类
        
        Args:
            crawler_name: 爬虫名称
            
        Returns:
            Type[BaseCrawler]: 爬虫类，如果不存在则返回None
        """
        # 如果已缓存，直接返回
        if crawler_name in self.crawler_classes:
            return self.crawler_classes[crawler_name]
            
        # 尝试动态加载
        try:
            module_name = f"app.crawlers.sites.{crawler_name}"
            module = importlib.import_module(module_name)
            
            # 查找模块中的爬虫类
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseCrawler) and 
                    obj != BaseCrawler and
                    getattr(obj, 'source', None) == crawler_name):
                    # 缓存并返回
                    self.crawler_classes[crawler_name] = obj
                    logger.info(f"已加载爬虫类: {crawler_name} -> {obj.__name__}")
                    return obj
                    
            logger.error(f"未在模块 {module_name} 中找到爬虫类")
            return None
            
        except ImportError:
            logger.error(f"导入爬虫模块失败: {crawler_name}")
            return None
        except Exception as e:
            logger.error(f"加载爬虫类失败 {crawler_name}: {e}")
            return None
    
    def create_crawler(self, crawler_name: str, **kwargs) -> Optional[BaseCrawler]:
        """
        创建指定爬虫的实例
        
        Args:
            crawler_name: 爬虫名称
            **kwargs: 传递给爬虫构造函数的参数
            
        Returns:
            BaseCrawler: 爬虫实例，如果创建失败则返回None
        """
        try:
            # 使用直接导入方式创建爬虫，避免策略加载
            crawler_class = self._import_crawler_directly(crawler_name)
            if not crawler_class:
                logger.error(f"未找到爬虫类: {crawler_name}")
                return None
            
            # 创建爬虫实例
            crawler = crawler_class(**kwargs)
            logger.info(f"成功创建爬虫实例: {crawler_name}")
            return crawler
        
        except Exception as e:
            logger.error(f"创建爬虫实例失败 {crawler_name}: {e}")
            return None
    
    def reload_crawler(self, crawler_name: str) -> bool:
        """
        重新加载指定爬虫的类
        
        Args:
            crawler_name: 爬虫名称
            
        Returns:
            bool: 重新加载是否成功
        """
        try:
            # 清除缓存
            if crawler_name in self.crawler_classes:
                del self.crawler_classes[crawler_name]
            if crawler_name in self.crawler_instances:
                del self.crawler_instances[crawler_name]
                
            # 重新加载模块
            module_name = f"app.crawlers.sites.{crawler_name}"
            if module_name in sys.modules:
                # 重新加载模块
                module = importlib.reload(sys.modules[module_name])
            else:
                # 首次加载模块
                module = importlib.import_module(module_name)
                
            # 查找爬虫类
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseCrawler) and 
                    obj != BaseCrawler and
                    getattr(obj, 'source', None) == crawler_name):
                    # 缓存爬虫类
                    self.crawler_classes[crawler_name] = obj
                    logger.info(f"已重新加载爬虫类: {crawler_name} -> {obj.__name__}")
                    return True
                    
            logger.error(f"重新加载后未找到爬虫类: {crawler_name}")
            return False
            
        except Exception as e:
            logger.error(f"重新加载爬虫类失败 {crawler_name}: {e}")
            return False
    
    def create_enhanced_crawler(self, source: str, db_path: str = None, options: Dict[str, Any] = None) -> Optional[BaseCrawler]:
        """
        创建增强型爬虫实例
        
        Args:
            source: 新闻源名称
            db_path: 数据库路径
            options: 爬虫选项
            
        Returns:
            Optional[BaseCrawler]: 爬虫实例，如果创建失败则返回None
        """
        try:
            # 暂时禁用增强爬虫，避免策略依赖
            logger.warning(f"增强爬虫暂时禁用以避免策略加载，将创建普通爬虫: {source}")
            
            # 创建普通爬虫实例作为替代
            crawler = self.create_crawler(source, db_path=db_path, **(options or {}))
            if not crawler:
                logger.error(f"创建普通爬虫失败: {source}")
                return None
                
            logger.info(f"成功创建普通爬虫(代替增强型): {source}")
            return crawler
            
        except Exception as e:
            logger.error(f"创建增强型爬虫失败 {source}: {str(e)}")
            return None
    
    def create_all_crawlers(self, db_dir: str = None, options: Dict[str, Any] = None) -> Dict[str, BaseCrawler]:
        """
        创建所有支持的爬虫实例
        
        Args:
            db_dir: 数据库目录，如果为None则使用默认目录
            options: 通用爬虫选项
            
        Returns:
            Dict[str, BaseCrawler]: {源名称: 爬虫实例}
        """
        # 如果指定了db_dir，更新实例的db_dir
        if db_dir:
            self.db_dir = db_dir
            self.sources_dir = os.path.join(db_dir, 'sources')
            self.main_db_path = os.path.join(db_dir, 'finance_news.db')
            
            # 确保目录存在
            for dir_path in [db_dir, self.sources_dir]:
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
        
        crawlers = {}
        
        # 使用爬虫映射而不是策略映射
        for source in self.crawler_mapping.keys():
            try:
                # 创建爬虫实例，使用默认专用数据库路径
                crawler = self.create_crawler(source, **(options or {}))
                if crawler:
                    crawlers[source] = crawler
                    logger.info(f"已创建 {source} 爬虫实例")
                else:
                    logger.warning(f"创建 {source} 爬虫实例失败")
            except Exception as e:
                logger.error(f"创建 {source} 爬虫实例失败: {str(e)}")
        
        return crawlers
    
    def create_all_enhanced_crawlers(self, db_dir: str = None, options: Dict[str, Any] = None) -> Dict[str, BaseCrawler]:
        """
        创建所有支持的增强型爬虫实例
        
        Args:
            db_dir: 数据库目录
            options: 通用爬虫选项
            
        Returns:
            Dict[str, BaseCrawler]: {源名称: 爬虫实例}
        """
        # 确保选项字典存在
        if options is None:
            options = {}
        
        # 强制使用增强型爬虫
        options['use_enhanced'] = True
        
        # 调用通用创建方法
        return self.create_all_crawlers(db_dir, options)
    
    def get_supported_sources(self) -> List[str]:
        """
        获取所有支持的爬虫源名称
        
        Returns:
            List[str]: 支持的源名称列表
        """
        return sorted(list(self.crawler_mapping.keys()))
    
    def register_source(self, source_name: str, crawler_class) -> None:
        """
        注册新的爬虫源
        
        Args:
            source_name: 源名称
            crawler_class: 爬虫类
        """
        if source_name in self.crawler_mapping:
            logger.warning(f"源 '{source_name}' 已存在，将被覆盖")
            
        self.crawler_mapping[source_name] = crawler_class
        logger.info(f"已注册新源: {source_name}")
    
    def register_source_from_config(self, source_name: str, config: Dict[str, Any]) -> None:
        """
        从配置字典注册新的爬虫源
        
        Args:
            source_name: 源名称
            config: 配置字典
        """
        # 这里可以实现基于配置动态创建策略类
        # 当前简单实现，只保存配置
        self.save_config(source_name, config)
        logger.info(f"已保存 {source_name} 的配置")
        
    def _get_source_config(self, source: str) -> Dict[str, Any]:
        """
        获取指定源的配置
        
        Args:
            source: 源名称
            
        Returns:
            Dict[str, Any]: 源配置
        """
        # 检查缓存
        if source in self.config_cache:
            return self.config_cache[source]
        
        # 尝试加载配置文件
        config = None
        
        # 尝试JSON配置
        json_path = os.path.join(self.config_dir, f"{source}.json")
        if os.path.exists(json_path):
            config = self._load_config(json_path)
        
        # 尝试YAML配置
        if config is None:
            yaml_path = os.path.join(self.config_dir, f"{source}.yaml")
            if os.path.exists(yaml_path):
                config = self._load_config(yaml_path)
        
        # 尝试YML配置
        if config is None:
            yml_path = os.path.join(self.config_dir, f"{source}.yml")
            if os.path.exists(yml_path):
                config = self._load_config(yml_path)
        
        # 如果无法加载配置，使用默认配置
        if config is None:
            logger.warning(f"未找到 {source} 的配置文件，使用默认配置")
            config = self._get_default_config()
        
        # 缓存配置
        self.config_cache[source] = config
        
        return config
    
    def _load_config(self, config_path: str) -> Optional[Dict[str, Any]]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Optional[Dict[str, Any]]: 配置字典，加载失败则返回None
        """
        try:
            logger.debug(f"尝试加载配置文件: {config_path}")
            
            # 根据文件扩展名选择加载方式
            if config_path.endswith('.json'):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            elif config_path.endswith('.yaml') or config_path.endswith('.yml'):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            else:
                logger.error(f"不支持的配置文件格式: {config_path}")
                return None
            
            logger.debug(f"配置文件加载成功: {config_path}")
            return config
        except Exception as e:
            logger.error(f"加载配置文件 {config_path} 失败: {str(e)}")
            return None
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置
        
        Returns:
            Dict[str, Any]: 默认配置
                """
        # 从环境变量获取配置值
        from app.config import get_settings
        settings = get_settings()
        
        # 构建默认配置
        default_config = {
            'use_enhanced': False,
            'async_mode': True,
            'use_proxy': False,
            'timeout': 30,
            'max_workers': 5,
            'max_concurrency': 10,
            'DB_DIR': settings.get('DB_DIR', os.path.join('data', 'db')),
            'sync_to_main': True  # 默认同步到主数据库
        }
        
        return default_config
    
    def save_config(self, source: str, config: Dict[str, Any], format: str = 'json') -> bool:
        """
        保存配置到文件
        
        Args:
            source: 源名称
            config: 配置字典
            format: 文件格式，支持json/yaml
            
        Returns:
            bool: 是否保存成功
        """
        # 确保配置目录存在
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)
        
        # 确定文件路径
        if format.lower() == 'json':
            config_path = os.path.join(self.config_dir, f"{source}.json")
        elif format.lower() in ['yaml', 'yml']:
            config_path = os.path.join(self.config_dir, f"{source}.yaml")
        else:
            logger.error(f"不支持的配置文件格式: {format}")
            return False
        
        try:
            # 保存配置
            if format.lower() == 'json':
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
            else:
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            # 更新缓存
            self.config_cache[source] = config
            
            logger.info(f"配置已保存到文件: {config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件 {config_path} 失败: {str(e)}")
            return False
    
    def get_crawler_list(self) -> List[Dict[str, Any]]:
        """
        获取所有可用爬虫的简要信息列表
        
        Returns:
            List[Dict[str, Any]]: 爬虫信息列表
        """
        result = []
        
        # 确保所有爬虫都已扫描
        self._scan_crawlers()
        
        for source, crawler_class in self.crawler_classes.items():
            info = {
                'source': source,
                'name': crawler_class.__name__,
                'module': crawler_class.__module__,
                'description': crawler_class.__doc__ or "无描述"
            }
            result.append(info)
            
        return result
    
    def get_crawler_info(self, source: str) -> Optional[Dict[str, Any]]:
        """
        获取指定爬虫的详细信息
        
        Args:
            source: 爬虫源名称
            
        Returns:
            Dict[str, Any]: 爬虫详细信息
        """
        # 获取或创建爬虫实例
        crawler = self.crawler_instances.get(source)
        if not crawler:
            crawler = self.create_crawler(source)
            
        if not crawler:
            return None
            
        try:
            # 获取爬虫信息
            return crawler.get_info()
        except Exception as e:
            logger.error(f"获取爬虫信息失败: {source}, 错误: {str(e)}")
            return {
                'source': source,
                'error': str(e),
                'crawler_type': crawler.__class__.__name__
            }
    
    def get_all_crawler_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有爬虫的详细信息
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有爬虫的详细信息
        """
        result = {}
        
        # 确保所有爬虫都已扫描
        self._scan_crawlers()
        
        for source in self.crawler_classes.keys():
            info = self.get_crawler_info(source)
            if info:
                result[source] = info
                
        return result

    def _import_crawler_directly(self, crawler_key: str):
        """
        直接导入爬虫类
        
        Args:
            crawler_key: 爬虫键值
            
        Returns:
            爬虫类或None
        """
        try:
            if crawler_key == 'sina':
                from app.crawlers.sina import SinaCrawler
                return SinaCrawler
            elif crawler_key == 'eastmoney':
                from app.crawlers.eastmoney import EastMoneyCrawler
                return EastMoneyCrawler
            elif crawler_key == 'netease':
                from app.crawlers.sites.netease import NeteaseCrawler
                return NeteaseCrawler
            elif crawler_key == 'ifeng':
                from app.crawlers.ifeng import IfengCrawler
                return IfengCrawler
            else:
                logger.error(f"不支持的爬虫: {crawler_key}")
                return None
        except ImportError as e:
            logger.error(f"导入爬虫失败 {crawler_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"创建爬虫类失败 {crawler_key}: {e}")
            return None