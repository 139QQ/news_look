#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
优化后的爬虫架构设计示例
展示统一的基类架构、配置管理和错误处理方案
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Protocol, Union
from datetime import datetime
import asyncio
import aiohttp
import logging
from functools import wraps
from pathlib import Path
import yaml


# =============================================================================
# 1. 配置管理系统
# =============================================================================

@dataclass
class HttpConfig:
    """HTTP客户端配置"""
    timeout: int = 30
    max_retries: int = 3
    user_agent: str = "NewsLook-Crawler/1.0"
    headers: Dict[str, str] = field(default_factory=dict)
    proxy: Optional[str] = None
    ssl_verify: bool = True


@dataclass
class CrawlerConfig:
    """爬虫配置"""
    name: str
    source: str
    base_url: str
    concurrency: int = 10
    rate_limit: float = 1.0  # 请求间隔秒数
    http: HttpConfig = field(default_factory=HttpConfig)
    selectors: Dict[str, Dict[str, str]] = field(default_factory=dict)
    categories: List[str] = field(default_factory=list)
    enabled: bool = True


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Union[str, Path] = "configs/crawlers"):
        self.config_dir = Path(config_dir)
        self.configs: Dict[str, CrawlerConfig] = {}
        self._load_all_configs()
    
    def _load_all_configs(self) -> None:
        """加载所有配置文件"""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for config_file in self.config_dir.glob("*.yml"):
            try:
                config = self._load_config_file(config_file)
                self.configs[config.name] = config
            except Exception as e:
                logging.error(f"加载配置文件失败 {config_file}: {e}")
    
    def _load_config_file(self, config_file: Path) -> CrawlerConfig:
        """加载单个配置文件"""
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 处理嵌套配置
        http_config = HttpConfig(**data.get('http', {}))
        
        return CrawlerConfig(
            name=data['name'],
            source=data['source'],
            base_url=data['base_url'],
            concurrency=data.get('concurrency', 10),
            rate_limit=data.get('rate_limit', 1.0),
            http=http_config,
            selectors=data.get('selectors', {}),
            categories=data.get('categories', []),
            enabled=data.get('enabled', True)
        )
    
    def get_config(self, crawler_name: str) -> Optional[CrawlerConfig]:
        """获取指定爬虫的配置"""
        return self.configs.get(crawler_name)
    
    def get_all_configs(self) -> Dict[str, CrawlerConfig]:
        """获取所有爬虫配置"""
        return self.configs.copy()


# =============================================================================
# 2. 异常处理系统
# =============================================================================

class CrawlerException(Exception):
    """爬虫异常基类"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        super().__init__(message)
        self.error_code = error_code or "CRAWLER_ERROR"
        self.details = details or {}
        self.timestamp = datetime.now()


class NetworkException(CrawlerException):
    """网络相关异常"""
    
    def __init__(self, message: str, status_code: int = None, url: str = None):
        super().__init__(message, "NETWORK_ERROR", {
            'status_code': status_code,
            'url': url
        })


class ParseException(CrawlerException):
    """解析相关异常"""
    
    def __init__(self, message: str, selector: str = None, page_url: str = None):
        super().__init__(message, "PARSE_ERROR", {
            'selector': selector,
            'page_url': page_url
        })


def handle_crawler_errors(func):
    """爬虫错误处理装饰器"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except CrawlerException:
            raise  # 重新抛出已知异常
        except asyncio.TimeoutError as e:
            raise NetworkException(f"请求超时: {e}")
        except (aiohttp.ClientError, aiohttp.ServerConnectionError) as e:
            raise NetworkException(f"网络错误: {e}")
        except Exception as e:
            logging.error(f"未知错误在 {func.__name__}: {e}", exc_info=True)
            raise CrawlerException(f"执行失败: {e}")
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CrawlerException:
            raise
        except Exception as e:
            logging.error(f"未知错误在 {func.__name__}: {e}", exc_info=True)
            raise CrawlerException(f"执行失败: {e}")
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


# =============================================================================
# 3. HTTP客户端抽象
# =============================================================================

class HttpClient(Protocol):
    """HTTP客户端协议"""
    
    async def fetch(self, url: str, **kwargs) -> str:
        """获取页面内容"""
        ...
    
    async def close(self) -> None:
        """关闭客户端"""
        ...


class AsyncHttpClient:
    """异步HTTP客户端实现"""
    
    def __init__(self, config: HttpConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(10)  # 并发限制
    
    async def __aenter__(self):
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _ensure_session(self):
        """确保session存在"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            headers = {
                'User-Agent': self.config.user_agent,
                **self.config.headers
            }
            
            connector = aiohttp.TCPConnector(
                ssl=self.config.ssl_verify,
                limit=100,
                limit_per_host=20
            )
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=connector
            )
    
    @handle_crawler_errors
    async def fetch(self, url: str, **kwargs) -> str:
        """获取页面内容"""
        async with self._semaphore:
            await self._ensure_session()
            
            async with self.session.get(url, **kwargs) as response:
                if response.status >= 400:
                    raise NetworkException(
                        f"HTTP错误 {response.status}",
                        status_code=response.status,
                        url=url
                    )
                
                content = await response.text()
                return content
    
    async def close(self):
        """关闭客户端"""
        if self.session and not self.session.closed:
            await self.session.close()


# =============================================================================
# 4. 解析器抽象
# =============================================================================

class Parser(Protocol):
    """解析器协议"""
    
    def parse_list_page(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """解析列表页"""
        ...
    
    def parse_detail_page(self, html: str, url: str) -> Dict[str, Any]:
        """解析详情页"""
        ...


class SelectorParser:
    """基于CSS选择器的解析器"""
    
    def __init__(self, selectors: Dict[str, Dict[str, str]]):
        self.selectors = selectors
        try:
            from bs4 import BeautifulSoup
            self.BeautifulSoup = BeautifulSoup
        except ImportError:
            raise ImportError("需要安装 beautifulsoup4")
    
    @handle_crawler_errors
    def parse_list_page(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """解析列表页"""
        soup = self.BeautifulSoup(html, 'html.parser')
        list_selectors = self.selectors.get('list_page', {})
        
        news_links_selector = list_selectors.get('news_links')
        if not news_links_selector:
            raise ParseException("缺少新闻链接选择器", selector="news_links")
        
        links = soup.select(news_links_selector)
        results = []
        
        for link in links:
            href = link.get('href')
            if href:
                if href.startswith('/'):
                    href = base_url.rstrip('/') + href
                elif not href.startswith('http'):
                    href = f"{base_url.rstrip('/')}/{href}"
                
                results.append({
                    'url': href,
                    'title': link.get_text(strip=True),
                })
        
        return results
    
    @handle_crawler_errors
    def parse_detail_page(self, html: str, url: str) -> Dict[str, Any]:
        """解析详情页"""
        soup = self.BeautifulSoup(html, 'html.parser')
        detail_selectors = self.selectors.get('detail_page', {})
        
        result = {'url': url}
        
        # 解析各个字段
        for field, selector in detail_selectors.items():
            elements = soup.select(selector)
            if elements:
                if field == 'content':
                    # 内容字段可能包含多个段落
                    result[field] = '\n'.join(elem.get_text(strip=True) for elem in elements)
                else:
                    result[field] = elements[0].get_text(strip=True)
            else:
                result[field] = None
        
        return result


# =============================================================================
# 5. 统一爬虫基类
# =============================================================================

class UnifiedCrawler(ABC):
    """统一的爬虫基类"""
    
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.logger = logging.getLogger(f"crawler.{config.name}")
        self.http_client = AsyncHttpClient(config.http)
        self.parser = SelectorParser(config.selectors)
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'articles_parsed': 0,
            'start_time': None,
            'end_time': None,
        }
    
    async def __aenter__(self):
        await self.http_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.__aexit__(exc_type, exc_val, exc_tb)
    
    @handle_crawler_errors
    async def crawl(self, days: int = 1, max_articles: int = 100, 
                   categories: List[str] = None) -> List[Dict[str, Any]]:
        """执行爬取任务"""
        self.stats['start_time'] = datetime.now()
        
        try:
            # 获取文章列表
            article_links = await self._get_article_links(categories or self.config.categories)
            
            # 限制文章数量
            if max_articles:
                article_links = article_links[:max_articles]
            
            # 并发爬取文章详情
            articles = await self._fetch_articles_concurrently(article_links)
            
            self.stats['articles_parsed'] = len(articles)
            return articles
        
        finally:
            self.stats['end_time'] = datetime.now()
            self._log_stats()
    
    async def _get_article_links(self, categories: List[str]) -> List[Dict[str, Any]]:
        """获取文章链接列表"""
        all_links = []
        
        for category in categories:
            try:
                category_url = await self._build_category_url(category)
                html = await self.http_client.fetch(category_url)
                self.stats['total_requests'] += 1
                self.stats['successful_requests'] += 1
                
                links = self.parser.parse_list_page(html, self.config.base_url)
                all_links.extend(links)
                
            except Exception as e:
                self.stats['failed_requests'] += 1
                self.logger.error(f"获取分类 {category} 失败: {e}")
        
        return all_links
    
    async def _fetch_articles_concurrently(self, article_links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """并发爬取文章详情"""
        semaphore = asyncio.Semaphore(self.config.concurrency)
        
        async def fetch_article(link_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            async with semaphore:
                try:
                    # 限流
                    await asyncio.sleep(self.config.rate_limit)
                    
                    html = await self.http_client.fetch(link_info['url'])
                    self.stats['total_requests'] += 1
                    self.stats['successful_requests'] += 1
                    
                    article = self.parser.parse_detail_page(html, link_info['url'])
                    article['source'] = self.config.source
                    
                    return self._post_process_article(article)
                
                except Exception as e:
                    self.stats['failed_requests'] += 1
                    self.logger.error(f"爬取文章失败 {link_info['url']}: {e}")
                    return None
        
        tasks = [fetch_article(link) for link in article_links]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤掉None和异常
        articles = [result for result in results 
                   if result is not None and not isinstance(result, Exception)]
        
        return articles
    
    def _post_process_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """后处理文章数据"""
        # 添加时间戳
        article['crawled_at'] = datetime.now().isoformat()
        
        # 生成唯一ID
        import hashlib
        url_hash = hashlib.md5(article['url'].encode('utf-8')).hexdigest()
        article['id'] = url_hash
        
        # 清理文本
        if article.get('content'):
            article['content'] = self._clean_text(article['content'])
        
        return article
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余的空白字符
        import re
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _log_stats(self):
        """记录统计信息"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        success_rate = (self.stats['successful_requests'] / 
                       max(self.stats['total_requests'], 1)) * 100
        
        self.logger.info(
            f"爬取完成 - 耗时: {duration:.2f}s, "
            f"总请求: {self.stats['total_requests']}, "
            f"成功率: {success_rate:.1f}%, "
            f"文章数: {self.stats['articles_parsed']}"
        )
    
    @abstractmethod
    async def _build_category_url(self, category: str) -> str:
        """构建分类URL - 子类需要实现"""
        pass


# =============================================================================
# 6. 具体爬虫实现示例
# =============================================================================

class EastMoneyCrawler(UnifiedCrawler):
    """东方财富爬虫示例实现"""
    
    async def _build_category_url(self, category: str) -> str:
        """构建东方财富分类URL"""
        category_mapping = {
            '财经': 'finance',
            '股票': 'stock',
            '基金': 'fund',
            '债券': 'bond'
        }
        
        category_path = category_mapping.get(category, 'finance')
        return f"{self.config.base_url.rstrip('/')}/{category_path}/"


# =============================================================================
# 7. 工厂类
# =============================================================================

class CrawlerFactory:
    """爬虫工厂"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self._crawler_classes = {
            '东方财富': EastMoneyCrawler,
            # 其他爬虫类...
        }
    
    def create_crawler(self, crawler_name: str) -> Optional[UnifiedCrawler]:
        """创建爬虫实例"""
        config = self.config_manager.get_config(crawler_name)
        if not config:
            return None
        
        crawler_class = self._crawler_classes.get(crawler_name)
        if not crawler_class:
            return None
        
        return crawler_class(config)
    
    def create_all_crawlers(self) -> Dict[str, UnifiedCrawler]:
        """创建所有爬虫实例"""
        crawlers = {}
        for name in self.config_manager.get_all_configs():
            crawler = self.create_crawler(name)
            if crawler:
                crawlers[name] = crawler
        return crawlers


# =============================================================================
# 8. 使用示例
# =============================================================================

async def main():
    """使用示例"""
    # 初始化配置管理器
    config_manager = ConfigManager()
    
    # 创建工厂
    factory = CrawlerFactory(config_manager)
    
    # 创建东方财富爬虫
    async with factory.create_crawler('东方财富') as crawler:
        if crawler:
            articles = await crawler.crawl(days=1, max_articles=50, categories=['财经', '股票'])
            print(f"爬取到 {len(articles)} 篇文章")
            
            for article in articles[:3]:  # 显示前3篇
                print(f"标题: {article.get('title')}")
                print(f"URL: {article.get('url')}")
                print("-" * 50)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 