#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 优化的网易财经爬虫
基于OptimizedCrawler，提供更高效的网易财经新闻爬取
"""

import re
import time
import random
import hashlib
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json
import urllib.parse
from urllib.parse import urlparse, parse_qs
import requests
import os
import logging
import traceback

from app.crawlers.optimized_crawler import OptimizedCrawler
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html, extract_keywords
from app.utils.ad_filter import AdFilter
from app.utils.image_detector import ImageDetector

# 设置日志记录器，确保日志输出到log文件夹
logger = get_crawler_logger('netease')

# 添加常用用户代理列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

class OptimizedNeteaseCrawler(OptimizedCrawler):
    """优化的网易财经爬虫，提供更高效的网易财经新闻爬取"""
    
    # 新闻分类URL - 更新为当前可访问的URL
    CATEGORY_URLS = {
        '财经': 'https://money.163.com/finance/',
        '股票': 'https://money.163.com/stock/',
        '理财': 'https://money.163.com/licai/',
        '基金': 'https://money.163.com/fund/',
        # 宏观和国际分类URL已失效，暂时注释掉
        # '宏观': 'https://money.163.com/macro/',
        # '国际': 'https://money.163.com/world/',
    }
    
    # API URL模板 - 注意：目前这些API可能已经不可用，需要更新
    API_URL_TEMPLATES = {
        # 使用当前首页中的新闻接口（如果有的话）
        # 'finance': 'https://money.163.com/special/00251LR5/news_json.js?callback=data_callback',
    }
    
    # 新闻列表正则表达式
    NEWS_LIST_REGEX = r'data_callback\((.*?)\);'
    
    # 文章内容选择器 - 更新为当前页面的选择器
    CONTENT_SELECTOR = 'div.post_body, div.post_text, div.article-content'
    
    # 文章标题选择器
    TITLE_SELECTOR = 'h1.post_title, h1.title, h1.article-title'
    
    # 文章时间选择器
    TIME_SELECTOR = 'div.post_time_source, div.time-source, div.publish-time'
    
    # 文章来源选择器
    SOURCE_SELECTOR = 'div.post_time_source a, div.time-source a, div.source-name'
    
    # 文章作者选择器
    AUTHOR_SELECTOR = 'div.post_time_source span, div.author, div.byline'
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, 
                max_workers=3, timeout=30, enable_async=False, **kwargs):
        """
        初始化优化的网易财经爬虫
        
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
        # 设置来源名称
        self.source = "网易财经"
        
        # 配置详细日志
        self._setup_logger()
        
        # 初始化父类
        super().__init__(db_manager=db_manager, db_path=db_path, use_proxy=use_proxy, 
                        use_source_db=use_source_db, max_workers=max_workers, 
                        timeout=timeout, enable_async=enable_async, **kwargs)
        
        # 初始化广告过滤器
        self.ad_filter = AdFilter(source_name=self.source)
        
        # 初始化图像识别器
        self.image_detector = ImageDetector(cache_dir='./image_cache')
        
        # 设置网易财经特有的请求头
        self.headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Referer': 'https://money.163.com/',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 获取并记录数据库路径
        if self.db_manager and hasattr(self.db_manager, 'main_db_path'):
            self.db_path = self.db_manager.main_db_path
        elif not self.db_path and db_path:
            self.db_path = db_path
            
        logger.info(f"优化的网易财经爬虫初始化完成，数据库路径: {self.db_path if self.db_path else '未指定'}")
        
        self.home_url = "https://money.163.com/"
        self.base_url = "https://money.163.com"
        # 添加默认请求头
        self.default_headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Referer": "https://www.163.com/"
        }

    def _setup_logger(self):
        """配置详细的日志系统"""
        global logger
        
        # 使用统一的爬虫日志记录器
        logger = get_crawler_logger('netease')
        logger.info("优化版网易财经爬虫日志系统初始化完成")
        
        # 记录数据库路径信息
        if hasattr(self, 'db_path'):
            logger.info(f"数据库路径: {self.db_path}")
        
        # 打印日志信息
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', '网易财经')
        today = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(log_dir, f'netease_{today}.log')
        logger.info(f"日志文件路径: {log_file}")

    def crawl(self, days=1, max_news=50, check_status=True, category=None):
        """
        爬取网易财经的财经新闻
        
        Args:
            days: 爬取最近几天的新闻
            max_news: 最大新闻数量
            check_status: 是否检查网站状态
            category: 要爬取的特定分类，如财经、股票等
            
        Returns:
            list: 爬取的新闻列表
        """
        # 调用父类方法初始化爬取状态
        super().crawl(days, max_news, check_status, category)
        
        # 清空新闻数据
        self.news_data = []
        
        # 重置广告过滤计数
        self.ad_filter.reset_filter_count()
        self.image_detector.reset_ad_count()
        
        # 计算开始日期
        start_date = datetime.now() - timedelta(days=days)
        
        # 尝试从首页获取最新新闻
        logger.info("开始从网易财经首页获取最新新闻")
        try:
            home_url = "https://money.163.com/"
            html = self.fetch_page(home_url)
            if html:
                news_links = self._extract_news_links_from_home(html)
                logger.info(f"从首页提取到新闻链接数量: {len(news_links)}")
                
                # 批量处理新闻链接
                home_news = self._batch_process_news_links(news_links, "财经")
                self.news_data.extend(home_news)
                
                # 如果已经达到最大新闻数量，则提前返回
                if max_news and len(self.news_data) >= max_news:
                    logger.info(f"已达到最大新闻数量 {max_news}，提前结束爬取")
                    return self.news_data[:max_news]
        except Exception as e:
            logger.error(f"从首页爬取新闻失败: {str(e)}")
        
        # 爬取各分类页面
        logger.info("开始爬取网易财经各分类页面")
        try:
            if category:
                if category in self.CATEGORY_URLS:
                    logger.info(f"开始爬取分类: {category}, URL: {self.CATEGORY_URLS[category]}")
                    
                    # 获取分类页面
                    html = self.fetch_page(self.CATEGORY_URLS[category])
                    if not html:
                        logger.warning(f"获取分类页面失败: {category}")
                        return self.news_data
                    
                    # 提取新闻链接
                    news_links = self._extract_news_links(html)
                    logger.info(f"从分类 {category} 提取到 {len(news_links)} 条新闻链接")
                    
                    # 批量处理新闻链接
                    category_news = self._batch_process_news_links(news_links, category)
                    self.news_data.extend(category_news)
                    
                    # 如果已经达到最大新闻数量，则提前返回
                    if max_news and len(self.news_data) >= max_news:
                        logger.info(f"已达到最大新闻数量 {max_news}，提前结束爬取")
                        return self.news_data[:max_news]
                else:
                    logger.warning(f"未找到分类: {category}")
                    return self.news_data
            else:
                for category, url in self.CATEGORY_URLS.items():
                    logger.info(f"开始爬取分类: {category}, URL: {url}")
                    
                    # 获取分类页面
                    html = self.fetch_page(url)
                    if not html:
                        logger.warning(f"获取分类页面失败: {category}")
                        continue
                    
                    # 提取新闻链接
                    news_links = self._extract_news_links(html)
                    logger.info(f"从分类 {category} 提取到 {len(news_links)} 条新闻链接")
                    
                    # 批量处理新闻链接
                    category_news = self._batch_process_news_links(news_links, category)
                    self.news_data.extend(category_news)
                    
                    # 如果已经达到最大新闻数量，则提前返回
                    if max_news and len(self.news_data) >= max_news:
                        logger.info(f"已达到最大新闻数量 {max_news}，提前结束爬取")
                        return self.news_data[:max_news]
                    
                    # 随机休眠，避免请求过快
                    time.sleep(2 + random.random())
        except Exception as e:
            logger.error(f"爬取分类页面失败: {str(e)}")
        
        # 更新爬虫统计信息
        self.crawl_stats["end_time"] = datetime.now()
        self.crawl_stats["elapsed_time"] = (self.crawl_stats["end_time"] - self.crawl_stats["start_time"]).total_seconds()
        if self.crawl_stats["elapsed_time"] > 0:
            self.crawl_stats["urls_per_second"] = self.crawl_stats["processed_urls"] / self.crawl_stats["elapsed_time"]
        
        # 记录爬取结果
        logger.info(f"网易财经爬取完成，获取新闻: {len(self.news_data)} 条")
        logger.info(f"过滤广告: {self.ad_filter.get_filter_count()} 条，过滤广告图片: {self.image_detector.get_ad_count()} 张")
        logger.info(f"爬取统计: {json.dumps(self.crawl_stats, default=str)}")
        
        # 如果有最大新闻数量限制，则返回指定数量的新闻
        if max_news:
            return self.news_data[:max_news]
        
        return self.news_data
    
    def _api_type_to_category(self, api_type):
        """将API类型转换为分类名称"""
        mapping = {
            'finance': '财经',
            'stock': '股票',
            'macro': '宏观',
            'fund': '基金'
        }
        return mapping.get(api_type, '财经')
    
    def _parse_api_data(self, api_data):
        """
        解析API数据
        
        Args:
            api_data: API返回的数据
            
        Returns:
            list: 解析后的新闻项列表
        """
        try:
            # 使用正则表达式提取JSON数据
            match = re.search(self.NEWS_LIST_REGEX, api_data)
            if not match:
                logger.warning("未找到API数据")
                return []
            
            # 提取JSON字符串
            json_str = match.group(1)
            
            # 解析JSON
            news_items = json.loads(json_str)
            
            return news_items
        except Exception as e:
            logger.error(f"解析API数据失败: {str(e)}")
            return []
    
    def _extract_news_links_from_home(self, html):
        """
        从首页提取新闻链接
        
        Args:
            html: 首页HTML内容
            
        Returns:
            list: 新闻链接列表
        """
        news_links = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找所有可能的新闻链接
            for a_tag in soup.find_all('a', href=True):
                link = a_tag['href']
                
                # 判断是否为有效的新闻链接
                if self._is_valid_news_url(link):
                    # 处理相对URL
                    if link.startswith('/'):
                        link = f"https://money.163.com{link}"
                    elif not link.startswith('http'):
                        continue
                    
                    # 检查是否为广告链接
                    if self.ad_filter.is_ad_url(link):
                        continue
                    
                    # 添加到链接列表
                    if link not in news_links:
                        news_links.append(link)
            
            logger.debug(f"从首页提取到 {len(news_links)} 个有效新闻链接")
        except Exception as e:
            logger.error(f"从首页提取新闻链接失败: {str(e)}")
        
        return news_links
    
    def _extract_news_links(self, html):
        """
        从HTML中提取新闻链接
        
        Args:
            html: HTML内容
            
        Returns:
            list: 新闻链接列表
        """
        news_links = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找所有可能的新闻链接
            for a_tag in soup.find_all('a', href=True):
                link = a_tag['href']
                
                # 判断是否为有效的新闻链接
                if self._is_valid_news_url(link):
                    # 处理相对URL
                    if link.startswith('/'):
                        link = f"https://money.163.com{link}"
                    elif not link.startswith('http'):
                        continue
                    
                    # 检查是否为广告链接
                    if self.ad_filter.is_ad_url(link):
                        continue
                    
                    # 添加到链接列表
                    if link not in news_links:
                        news_links.append(link)
            
            logger.debug(f"提取到 {len(news_links)} 个有效新闻链接")
        except Exception as e:
            logger.error(f"提取新闻链接失败: {str(e)}")
        
        return news_links
    
    def _is_valid_news_url(self, url):
        """
        判断URL是否为有效的新闻链接
        
        Args:
            url: URL
            
        Returns:
            bool: 是否为有效的新闻链接
        """
        if not url:
            return False
        
        # 常见的网易新闻URL模式（同时支持绝对和相对URL）
        patterns = [
            # 常规网易财经文章格式
            r'https?://money\.163\.com/\d+/\d+/\d+/\w+\.html',
            r'//money\.163\.com/\d+/\d+/\d+/\w+\.html',
            
            # article路径格式
            r'https?://money\.163\.com/article/\w+\.html',
            r'//money\.163\.com/article/\w+\.html',
            
            # www域名下的财经文章
            r'https?://www\.163\.com/money/article/\w+\.html',
            r'//www\.163\.com/money/article/\w+\.html',
            
            # 新闻中心下的财经文章
            r'https?://news\.163\.com/\d+/\d+/\d+/\w+\.html',
            r'//news\.163\.com/\d+/\d+/\d+/\w+\.html',
            
            # 可能的其他财经文章格式
            r'https?://(.*?)\.163\.com/.*/\d{4}/\d{2}/\d{2}(/\d{2}/\d{2})?/\w+\.html',
        ]
        
        # 如果URL匹配任一模式，则为有效
        for pattern in patterns:
            if re.search(pattern, url):
                return True
        
        return False
    
    def fetch_page(self, url):
        """
        获取页面内容
        
        Args:
            url: 要获取的URL
            
        Returns:
            str: 页面内容
        """
        # 每次请求随机选择一个用户代理
        headers = self.default_headers.copy()
        headers["User-Agent"] = random.choice(USER_AGENTS)
        
        # 添加随机延迟，模拟人类行为
        time.sleep(random.uniform(1, 3))
        
        try:
            response = self.optimizer.fetch_with_retry(url, self.source, headers=headers)
            if response and response.status_code == 200:
                return response.text
            return None
        except Exception as e:
            logger.error(f"获取页面异常: {url}, 错误: {str(e)}")
            return None

    def _extract_keywords(self, content):
        """
        提取关键词
        
        Args:
            content: 要提取关键词的内容
            
        Returns:
            list: 关键词列表
        """
        try:
            return extract_keywords(content)
        except Exception as e:
            logger.error(f"提取关键词失败: {str(e)}")
            return []
            
    def _get_current_time(self):
        """
        获取当前时间
        
        Returns:
            str: 当前时间字符串，格式为 YYYY-MM-DD HH:MM:SS
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
    def _crawl_news_detail(self, url, category=None):
        """
        爬取新闻详情
        
        Args:
            url: 新闻详情页URL
            category: 新闻分类，默认为None
            
        Returns:
            dict: 新闻数据字典，包含标题、发布时间、作者、内容等
        """
        try:
            # 随机延迟，模拟人类行为
            time.sleep(random.uniform(1, 3))
            
            # 设置随机用户代理
            headers = self.default_headers.copy()
            headers["User-Agent"] = random.choice(USER_AGENTS)
            
            # 直接使用requests获取页面，绕过优化器
            try:
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code != 200:
                    logger.warning(f"获取新闻页面失败，状态码: {response.status_code}, URL: {url}")
                    return None
                html_content = response.text
            except Exception as e:
                logger.error(f"请求页面异常: {url}, 错误: {str(e)}")
                return None
                
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取标题
            title = None
            title_selectors = ['h1.post_title', 'h1.title', '.article-header h1', 'h1']
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.text.strip()
                    logger.debug(f"提取到标题 (使用选择器 {selector}): {title}")
                    break
            
            if not title:
                logger.warning(f"提取标题失败: {url}")
                return None
                
            # 提取发布时间
            pub_time = None
            time_selectors = ['.post_info time', '.post_time_source', '.date', '.time']
            for selector in time_selectors:
                time_elem = soup.select_one(selector)
                if time_elem:
                    pub_time = time_elem.text.strip()
                    # 处理可能的额外文本
                    pub_time = re.sub(r'(来源|举报|举报?|：|:|\s+)', ' ', pub_time).strip()
                    logger.debug(f"提取到发布时间 (使用选择器 {selector}): {pub_time}")
                    break
            
            # 如果未找到发布时间，使用当前时间
            if not pub_time:
                pub_time = self._get_current_time()
                logger.debug(f"使用当前时间作为发布时间: {pub_time}")
            
            # 提取作者
            author = None
            author_selectors = ['.post_author', '.author', '.source', '.pb-source-wrap']
            for selector in author_selectors:
                author_elem = soup.select_one(selector)
                if author_elem:
                    author = author_elem.text.strip()
                    # 处理可能的额外文本
                    author = re.sub(r'(本文来源[：:]|作者[：:]|来源[：:]|责任编辑[：:])', '', author).strip()
                    logger.debug(f"提取到作者 (使用选择器 {selector}): {author}")
                    break
            
            if not author:
                author = "网易财经"
                logger.debug(f"使用默认作者: {author}")
            
            # 提取内容
            content_html = ''
            content_selectors = ['#content', '.post_body', '.post_text', '.article-content', 'article']
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    logger.debug(f"找到内容元素，使用选择器: {selector}")
                    
                    # 删除不需要的元素
                    for selector in ['.post_btns', '.post_topshare', '.post_end', '.post_function', '.post_function_wrap', 'script', 'style']:
                        for elem in content_elem.select(selector):
                            elem.decompose()
                    
                    content_html = str(content_elem)
                    break
            
            if not content_html:
                # 尝试查找主要段落
                paragraphs = soup.find_all('p')
                if len(paragraphs) > 3:  # 至少有几个段落才可能是文章
                    content_html = '<div class="extracted-content">'
                    for p in paragraphs:
                        # 过滤太短的段落
                        if len(p.get_text(strip=True)) > 10:
                            content_html += str(p)
                    content_html += '</div>'
                    logger.debug(f"从段落中提取内容，找到 {len(paragraphs)} 个段落")
            
            if not content_html:
                logger.warning(f"无法找到内容元素: {url}")
                return None
            
            # 清理HTML，提取纯文本
            content_text = clean_html(content_html)
            
            if not content_text or len(content_text) < 50:  # 允许较短的内容但要有基本长度
                logger.warning(f"内容过短或为空: {url}, 长度: {len(content_text) if content_text else 0}")
                if not content_text:
                    return None
            
            # 提取图片
            images = []
            soup_content = BeautifulSoup(content_html, 'html.parser')
            for img in soup_content.find_all('img', src=True):
                src = img.get('src')
                if src:
                    # 确保是绝对URL
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif not src.startswith(('http://', 'https://')):
                        continue
                    
                    images.append(src)
            
            logger.debug(f"提取到 {len(images)} 张图片")
            
            # 提取关键词
            keywords = self._extract_keywords(title + ' ' + content_text if content_text else title)
            
            # 生成唯一ID
            import hashlib
            news_id = hashlib.md5(url.encode('utf-8')).hexdigest()
            
            # 构建新闻数据
            news_data = {
                'id': news_id,
                'url': url,
                'title': title,
                'pub_time': pub_time,
                'author': author,
                'content': content_text,  # 使用content_text作为content字段
                'content_html': content_html,  # 保留原字段，但不会保存到数据库
                'content_text': content_text,  # 保留原字段，但不会保存到数据库
                'keywords': ','.join(keywords) if keywords else '',
                'images': json.dumps(images),
                'crawl_time': self._get_current_time(),
                'category': category,
                'source': self.source
            }
            
            # 调试日志
            logger.info(f"成功提取新闻: {title}, URL: {url}")
            
            # 保存新闻到数据库
            if self.db_manager:
                db_path = self.db_manager.main_db_path if hasattr(self.db_manager, 'main_db_path') else self.db_path
                logger.info(f"尝试保存新闻到数据库，路径: {db_path}")
                
                try:
                    # 移除不需要保存到数据库的字段
                    save_data = news_data.copy()
                    if 'content_html' in save_data:
                        del save_data['content_html']
                    if 'content_text' in save_data:
                        del save_data['content_text']
                    
                    # 确保content字段存在
                    if 'content' not in save_data or not save_data['content']:
                        save_data['content'] = save_data.get('content_text', '')
                    
                    # 保存到数据库
                    result = self.db_manager.save_news(save_data)
                    
                    if result:
                        logger.info(f"成功保存新闻到数据库: {title}")
                    else:
                        # 尝试检查是否已存在
                        try:
                            conn = self.db_manager.get_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT id FROM news WHERE id = ?", (news_data['id'],))
                            exists = cursor.fetchone()
                            if exists:
                                logger.info(f"新闻已存在于数据库中: {title}")
                            else:
                                logger.error(f"新闻不存在于数据库且保存失败: {title}")
                            conn.close()
                        except Exception as db_err:
                            logger.error(f"检查新闻存在性时出错: {str(db_err)}")
                except Exception as save_err:
                    logger.error(f"保存新闻到数据库时出错: {str(save_err)}")
            else:
                logger.warning(f"数据库管理器未初始化，无法保存新闻: {title}")
            
            return news_data
            
        except Exception as e:
            logger.error(f"爬取新闻详情异常: {url}, 错误: {str(e)}")
            logger.error(traceback.format_exc())
            return None
            
    def _extract_publish_time(self, soup):
        """
        从HTML中提取发布时间
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: 发布时间
        """
        try:
            # 尝试从meta标签中提取
            pub_time_tag = soup.find('meta', attrs={'property': 'article:published_time'})
            if pub_time_tag and pub_time_tag.get('content'):
                pub_time = pub_time_tag.get('content')
                # 处理ISO格式时间
                if 'T' in pub_time:
                    try:
                        dt = datetime.fromisoformat(pub_time.replace('Z', '+00:00'))
                        return dt.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        pass
                return pub_time
            
            # 尝试从time标签中提取
            time_tag = soup.find('time')
            if time_tag and time_tag.get('datetime'):
                return time_tag.get('datetime')
            
            # 尝试从特定class中提取
            for selector in ['.post_time_source', '.time-source', '.publish-time', '.date']:
                time_elem = soup.select_one(selector)
                if time_elem:
                    time_text = time_elem.text.strip()
                    # 清理时间文本
                    time_text = re.sub(r'(来源|举报|举报?|：|:|\s+)', ' ', time_text).strip()
                    # 提取时间模式
                    date_match = re.search(r'(\d{4}[-年/]\d{1,2}[-月/]\d{1,2}日?\s*\d{1,2}:\d{1,2}(:\d{1,2})?)', time_text)
                    if date_match:
                        return date_match.group(1).replace('年', '-').replace('月', '-').replace('日', '')
                    
                    # 尝试其他时间格式
                    date_match = re.search(r'(\d{4}[-年/]\d{1,2}[-月/]\d{1,2}日?)', time_text)
                    if date_match:
                        date_str = date_match.group(1).replace('年', '-').replace('月', '-').replace('日', '')
                        return f"{date_str} 00:00:00"
            
            # 如果都没找到，返回当前时间
            return self._get_current_time()
        except Exception as e:
            logger.error(f"提取发布时间失败: {str(e)}")
            return self._get_current_time()
            
    def _batch_process_news_links(self, news_links, category):
        """
        批量处理新闻链接
        
        Args:
            news_links: 新闻链接列表
            category: 新闻分类
            
        Returns:
            list: 处理后的新闻数据列表
        """
        news_data_list = []
        
        for url in news_links:
            try:
                # 更新爬虫统计信息
                self.crawl_stats["processed_urls"] += 1
                
                # 爬取新闻详情
                news_data = self._crawl_news_detail(url, category)
                if news_data:
                    news_data_list.append(news_data)
                    self.crawl_stats["success_urls"] += 1
                    
                    # 保存到数据库
                    if self.db_manager:
                        db_path = self.db_manager.main_db_path if hasattr(self.db_manager, 'main_db_path') else self.db_path
                        logger.info(f"尝试保存新闻到数据库，路径: {db_path}")
                        
                        try:
                            # 移除不需要保存到数据库的字段
                            save_data = news_data.copy()
                            if 'content_html' in save_data:
                                del save_data['content_html']
                            if 'content_text' in save_data:
                                del save_data['content_text']
                            
                            # 确保content字段存在
                            if 'content' not in save_data or not save_data['content']:
                                save_data['content'] = save_data.get('content_text', '')
                            
                            # 保存新闻
                            result = self.db_manager.save_news(save_data)
                            if result:
                                logger.info(f"成功保存新闻到数据库: {news_data['title']}")
                            else:
                                # 尝试检查是否已存在
                                try:
                                    conn = self.db_manager.get_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT id FROM news WHERE id = ?", (news_data['id'],))
                                    exists = cursor.fetchone()
                                    if exists:
                                        logger.info(f"新闻已存在于数据库中: {news_data['title']}")
                                    else:
                                        logger.error(f"新闻不存在于数据库且保存失败: {news_data['title']}")
                                    conn.close()
                                except Exception as db_err:
                                    logger.error(f"检查新闻存在性时出错: {str(db_err)}")
                        except Exception as save_err:
                            logger.error(f"保存新闻到数据库时出错: {str(save_err)}")
                else:
                    self.crawl_stats["failed_urls"] += 1
                
                # 随机休眠，避免请求过快
                time.sleep(1 + random.random())
            except Exception as e:
                logger.error(f"处理新闻链接失败: {url}, 错误: {str(e)}")
                self.crawl_stats["failed_urls"] += 1
        
        return news_data_list