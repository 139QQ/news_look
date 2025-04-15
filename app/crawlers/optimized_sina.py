#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 优化版新浪财经爬虫
"""

import os  # 用于处理文件路径
import re  # 用于正则表达式匹配
import sys  # 用于系统相关操作
import time  # 用于时间延迟
import hashlib  # 用于生成新闻ID
import random  # 用于随机延迟
import json  # 用于解析JSON数据
import asyncio
import aiohttp
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

import logging
from app.crawlers.base import BaseCrawler
from app.utils.text_cleaner import clean_html, extract_keywords, decode_html_entities, decode_unicode_escape, decode_url_encoded
from app.db.sqlite_manager import SQLiteManager
from app.utils.logger import get_crawler_logger

# 配置日志
logger = logging.getLogger(__name__)

class OptimizedSinaCrawler(BaseCrawler):
    """优化版新浪财经爬虫"""
    
    # 新闻分类URL - 更新为最新的分类URL
    CATEGORY_URLS = {
        '股票': 'https://finance.sina.com.cn/stock/',  # 更新为股票主页
        '公司': 'https://finance.sina.com.cn/roll/index.d.html?cid=57526&page={}',
        '产业': 'https://finance.sina.com.cn/roll/index.d.html?cid=57522&page={}',
        '宏观': 'https://finance.sina.com.cn/roll/index.d.html?cid=57524&page={}',
        '国际': 'https://finance.sina.com.cn/roll/index.d.html?cid=56590&page={}',
        '科技': 'https://finance.sina.com.cn/tech/index.shtml',
        '区块链': 'https://finance.sina.com.cn/blockchain/',
        '基金': 'https://finance.sina.com.cn/fund/',  # 新增基金频道
        '期货': 'https://finance.sina.com.cn/futuremarket/',  # 新增期货频道
    }
    
    # 内容选择器 - 更新为最新的选择器
    CONTENT_SELECTORS = [
        'div.article-content-left',
        'div.article-content',
        'div#artibody',
        'div.article',
        'div.main-content',
    ]
    
    # 时间选择器 - 更新为最新的选择器
    TIME_SELECTORS = [
        'span.date',
        'div.date-source span.date',
        'div.date-source span:first-child',
        'span.time-source',
        'div.titer span.time',
    ]
    
    # 作者选择器 - 更新为最新的选择器
    AUTHOR_SELECTORS = [
        'span.source',
        'div.date-source span.source',
        'div.date-source a.source',
        'span.time-source span.source',
        'div.titer span.source',
    ]
    
    # 标题选择器 - 更新为最新的选择器
    TITLE_SELECTORS = [
        'h1.main-title',
        'h1.title',
        'h1#artibodyTitle',
        'div.headline h1',
    ]
    
    def __init__(self, db_path=None, db_manager=None, use_proxy=False, use_source_db=False, 
                 max_workers=3, timeout=30, enable_async=False, **kwargs):
        """
        初始化优化版新浪财经爬虫
        
        Args:
            db_path: 数据库路径，如果为None则使用默认路径
            db_manager: 数据库管理器对象
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
            max_workers: 最大工作线程数
            timeout: 请求超时时间（秒）
            enable_async: 是否启用异步模式
            **kwargs: 其他参数
        """
        # 设置来源名称
        self.source = "新浪财经"
        
        # 保存数据库管理器
        self.db_manager = db_manager
        self.db_path = db_path
        
        # 配置详细日志
        self._setup_logger()
        
        # 初始化父类
        super().__init__(db_path=db_path, db_manager=db_manager, use_proxy=use_proxy, 
                         use_source_db=use_source_db, max_workers=max_workers, 
                         timeout=timeout, enable_async=enable_async, **kwargs)
        
        # 新浪财经特有的请求头 - 更新为最新的请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://finance.sina.com.cn/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
        }
        
        # 初始化线程池
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # 初始化异步会话
        self.session = None
        
        logger.info("优化版新浪财经爬虫初始化完成，数据库路径: %s", self.db_path or "未指定")
    
    async def _init_session(self):
        """初始化异步会话"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
        return self.session
    
    async def _close_session(self):
        """关闭异步会话"""
        if self.session is not None:
            await self.session.close()
            self.session = None
    
    def fetch_page(self, url, params=None, headers=None, max_retries=None, timeout=None):
        """
        重写获取页面内容方法，处理新浪财经特有的编码问题
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 自定义请求头
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
            
        Returns:
            页面内容或None
        """
        # 调用父类的fetch_page方法获取响应
        response = super().fetch_page(url, params, headers, max_retries, timeout)
        
        if response is None:
            return None
        
        # 解决新浪财经的编码问题
        try:
            # 尝试检测编码
            if response.encoding == 'ISO-8859-1':
                # 对于误判为ISO-8859-1的页面，先尝试utf-8
                try:
                    content = response.content.decode('utf-8')
                except UnicodeDecodeError:
                    # 如果utf-8解码失败，尝试GBK
                    try:
                        content = response.content.decode('gbk')
                    except UnicodeDecodeError:
                        # 如果GBK也失败，使用gb18030（超集）
                        content = response.content.decode('gb18030')
            else:
                # 使用响应的编码
                content = response.text
            
            # 应用额外的解码处理
            content = decode_html_entities(content)
            content = decode_unicode_escape(content)
            content = decode_url_encoded(content)
            
            return content
        except Exception as e:
            logger.error("处理页面编码时出错: %s, 错误: %s", url, str(e))
            return response.text  # 出错时返回原始文本
    
    async def async_fetch_page(self, url, params=None, headers=None, max_retries=3, timeout=30):
        """
        异步获取页面内容
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 自定义请求头
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
            
        Returns:
            页面内容或None
        """
        if not url:
            return None
        
        # 初始化会话
        session = await self._init_session()
        
        # 合并请求头
        merged_headers = self.headers.copy()
        if headers:
            merged_headers.update(headers)
        
        # 设置重试次数
        retries = max_retries if max_retries is not None else 3
        
        # 添加随机延迟，避免被反爬
        await asyncio.sleep(random.uniform(1, 3))
        
        for attempt in range(retries):
            try:
                async with session.get(url, params=params, headers=merged_headers, timeout=timeout) as response:
                    if response.status != 200:
                        logger.warning("请求失败: %s, 状态码: %s, 重试 %s/%s", url, response.status, attempt+1, retries)
                        if attempt < retries - 1:
                            await asyncio.sleep(random.uniform(2, 5))  # 随机延迟
                            continue
                        return None
                    
                    # 获取响应内容
                    content = await response.text(errors='replace')
                    
                    # 应用额外的解码处理
                    content = decode_html_entities(content)
                    content = decode_unicode_escape(content)
                    content = decode_url_encoded(content)
                    
                    return content
            except asyncio.TimeoutError:
                logger.warning("请求超时: %s, 重试 %s/%s", url, attempt+1, retries)
                if attempt < retries - 1:
                    await asyncio.sleep(random.uniform(2, 5))  # 随机延迟
            except Exception as e:
                logger.error("请求出错: %s, 错误: %s, 重试 %s/%s", url, str(e), attempt+1, retries)
                if attempt < retries - 1:
                    await asyncio.sleep(random.uniform(2, 5))  # 随机延迟
        
        return None
    
    def crawl(self, days=1, max_pages=3, max_news=50, category=None):
        """
        爬取新浪财经的新闻
        
        Args:
            days: 爬取的天数范围，默认为1天
            max_pages: 每个分类最多爬取的页数，默认为3页
            max_news: 最多爬取的新闻数量，默认为50条
            category: 指定爬取的分类，如果为None则爬取所有分类
            
        Returns:
            list: 爬取的新闻列表
        """
        logger.info("开始爬取%s新闻，天数范围: %s天，每个分类最多爬取: %s页，最多爬取: %s条新闻，分类: %s", 
                   self.source, days, max_pages, max_news, category if category else "全部")
        
        # 清空新闻数据列表
        self.news_data = []
        
        # 计算开始日期
        start_date = datetime.now() - timedelta(days=days)
        
        # 使用异步方式爬取
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self._crawl_async(days, max_pages, start_date, max_news, category))
        except Exception as e:
            logger.error("异步爬取失败: %s", str(e))
            # 如果异步爬取失败，回退到同步爬取
            self._crawl_sync(days, max_pages, start_date, max_news, category)
        finally:
            # 确保关闭异步会话
            try:
                loop.run_until_complete(self._close_session())
            except Exception as e:
                logger.error("关闭异步会话失败: %s", str(e))
        
        # 爬取结束后，确保数据被保存到数据库
        if hasattr(self, 'news_data') and self.news_data:
            saved_count = 0
            for news in self.news_data:
                if self.save_news_to_db(news):
                    saved_count += 1
            
            logger.info("成功保存 %s/%s 条新闻到数据库", saved_count, len(self.news_data))
        
        logger.info("爬取完成，共爬取新闻 %s 条", len(self.news_data))
        
        # 如果设置了max_news限制，确保返回的新闻不超过该数量
        if max_news and len(self.news_data) > max_news:
            return self.news_data[:max_news]
        return self.news_data
    
    async def _crawl_async(self, days, max_pages, start_date, max_news, category):
        """
        异步爬取新闻
        
        Args:
            days: 爬取的天数范围
            max_pages: 每个分类最多爬取的页数
            start_date: 开始日期
            max_news: 最多爬取的新闻数量
            category: 指定爬取的分类
        """
        logger.info("使用异步方式爬取新闻")
        
        # 创建异步会话
        self.session = aiohttp.ClientSession(headers=self.headers)
        
        try:
            # 爬取分类页面
            logger.info("从网页获取新闻")
            
            # 爬取每个分类的新闻
            tasks = []
            for cat in self.CATEGORY_URLS:
                if category and cat != category:
                    continue
                
                url_template = self.CATEGORY_URLS[cat]
                # 只处理带有分页参数的URL
                if '{}' in url_template:
                    for page in range(1, max_pages + 1):
                        url = url_template.format(page)
                        tasks.append(self._crawl_category_page_async(url, cat, start_date, max_news))
                else:
                    # 对于没有分页参数的URL，直接爬取
                    tasks.append(self._crawl_category_page_async(url_template, cat, start_date, max_news))
            
            # 等待所有任务完成
            await asyncio.gather(*tasks)
            
            logger.info("网页获取的新闻数量: %s条", len(self.news_data))
        except Exception as e:
            logger.error("从网页获取新闻失败: %s", str(e))
            raise
    
    async def _crawl_category_page_async(self, url, category, start_date, max_news=None):
        """
        异步爬取分类页面
        
        Args:
            url: 分类页面URL
            category: 分类
            start_date: 开始日期
            max_news: 最多爬取的新闻数量
        """
        try:
            logger.info("爬取分类页面: %s, 分类: %s", url, category)
            
            # 检查是否已达到最大新闻数量限制
            if max_news and len(self.news_data) >= max_news:
                logger.info("已达到最大新闻数量限制 %s，停止爬取", max_news)
                return
            
            # 获取页面内容
            html = await self.async_fetch_page(url)
            if not html:
                logger.warning("获取分类页面失败: %s", url)
                return
            
            # 解析页面，提取新闻链接
            news_links = self.extract_news_links(html, category)
            logger.info("提取到新闻链接数量: %s", len(news_links))
            
            # 计算剩余可爬取的新闻数量
            remaining = max_news - len(self.news_data) if max_news else len(news_links)
            if remaining <= 0:
                return
                
            # 限制爬取的链接数量
            news_links = news_links[:remaining]
            
            # 异步爬取每个新闻详情
            tasks = []
            for news_link in news_links:
                tasks.append(self._crawl_news_detail_async(news_link, category, start_date))
            
            # 等待所有任务完成
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error("爬取分类页面失败: %s, 分类: %s, 错误: %s", url, category, str(e))
    
    async def _crawl_news_detail_async(self, url, category, start_date):
        """
        异步爬取新闻详情
        
        Args:
            url: 新闻URL
            category: 分类
            start_date: 开始日期
        """
        # 跳过已爬取的URL
        if url in self.crawled_urls:
            return
        
        # 添加到已爬取集合
        self.crawled_urls.add(url)
        
        # 爬取新闻详情
        html = await self.async_fetch_page(url)
        if not html:
            return
        
        try:
            # 解析新闻详情
            news_data = self.parse_news_detail(html, url, category)
            if not news_data:
                logger.warning("解析新闻详情失败: %s", url)
                return
            
            # 检查发布时间是否在范围内
            if 'pub_time' in news_data and news_data['pub_time']:
                try:
                    pub_time = datetime.strptime(news_data['pub_time'], '%Y-%m-%d %H:%M:%S')
                    if pub_time < start_date:
                        return
                except (ValueError, TypeError):
                    # 如果日期解析失败，仍然保留该新闻
                    pass
            
            # 添加到新闻列表
            self.news_data.append(news_data)
            
            # 保存到数据库
            if self.save_news_to_db(news_data):
                logger.info("成功爬取新浪新闻: %s", news_data.get('title', url))
        except Exception as e:
            logger.error("爬取新闻详情失败: %s, 错误: %s", url, str(e))
    
    def _crawl_sync(self, days, max_pages, start_date, max_news, category):
        """
        同步爬取新闻（作为异步爬取的备选方案）
        
        Args:
            days: 爬取的天数范围
            max_pages: 每个分类最多爬取的页数
            start_date: 开始日期
            max_news: 最多爬取的新闻数量
            category: 指定爬取的分类
        """
        logger.info("使用同步方式爬取新闻")
        
        # 尝试从首页获取新闻
        try:
            # 如果指定了分类，则跳过首页爬取
            if category:
                logger.info("已指定分类 %s，跳过首页爬取", category)
            else:
                logger.info("尝试从首页获取新闻")
                # 获取首页内容
                html = self.fetch_page(self.INDEX_URL)
                if html:
                    # 解析首页，提取新闻链接
                    news_links = self.extract_news_links_from_home(html, "首页")
                    logger.info("从首页提取到新闻链接数量: %s", len(news_links))
                    
                    # 计算剩余可爬取的新闻数量
                    remaining = max_news - len(self.news_data) if max_news else len(news_links)
                    if remaining > 0:
                        # 限制爬取的链接数量
                        news_links = news_links[:remaining]
                        
                        # 爬取每个新闻详情
                        for news_link in news_links:
                            self.random_sleep(1, 3)
                            
                            # 爬取新闻详情
                            news_data = self.crawl_news_detail(news_link, "首页")
                            if not news_data:
                                continue
                            
                            # 检查新闻日期是否在指定范围内
                            try:
                                news_date = datetime.strptime(news_data['pub_time'].split(' ')[0], '%Y-%m-%d')
                                if news_date < start_date:
                                    logger.debug("新闻日期 %s 早于开始日期 %s，跳过", news_date, start_date)
                                    continue
                            except Exception as e:
                                logger.warning("解析新闻日期失败: %s, 错误: %s", news_data['pub_time'], str(e))
                            
                            # 保存新闻数据
                            self.save_news_to_db(news_data)
                            self.news_data.append(news_data)
                            logger.info("成功爬取新浪新闻: %s", news_data['title'])
                            
                            # 检查是否已达到最大新闻数量限制
                            if max_news and len(self.news_data) >= max_news:
                                logger.info("已达到最大新闻数量限制 %s，停止爬取", max_news)
                                return
        except Exception as e:
            logger.error("从首页获取新闻失败: %s", str(e))
        
        # 如果从首页获取的新闻不足，再尝试从分类页获取
        if max_news is None or len(self.news_data) < max_news:
            # 爬取每个分类的新闻
            for cat in self.CATEGORY_URLS:
                if category and cat != category:
                    continue
                
                logger.info("爬取分类: %s", cat)
                
                # 处理带有分页参数的URL
                if '{}' in self.CATEGORY_URLS[cat]:
                    # 爬取前max_pages页
                    for page in range(1, max_pages + 1):
                        url = self.CATEGORY_URLS[cat].format(page)
                        logger.info("爬取页面: %s", url)
                        
                        # 获取页面内容
                        html = self.fetch_page(url)
                        if not html:
                            logger.warning("获取分类页面失败: %s", url)
                            continue
                        
                        # 解析页面，提取新闻链接
                        news_links = self.extract_news_links(html, cat)
                        logger.info("提取到新闻链接数量: %s", len(news_links))
                        
                        # 计算剩余可爬取的新闻数量
                        remaining = max_news - len(self.news_data) if max_news else len(news_links)
                        if remaining <= 0:
                            return
                            
                        # 限制爬取的链接数量
                        news_links = news_links[:remaining]
                        
                        # 爬取每个新闻详情
                        for news_link in news_links:
                            self.random_sleep(1, 3)
                            
                            # 爬取新闻详情
                            news_data = self.crawl_news_detail(news_link, cat)
                            if not news_data:
                                continue
                            
                            # 检查新闻日期是否在指定范围内
                            try:
                                news_date = datetime.strptime(news_data['pub_time'].split(' ')[0], '%Y-%m-%d')
                                if news_date < start_date:
                                    logger.debug("新闻日期 %s 早于开始日期 %s，跳过", news_date, start_date)
                                    continue
                            except Exception as e:
                                logger.warning("解析新闻日期失败: %s, 错误: %s", news_data['pub_time'], str(e))
                            
                            # 保存新闻数据
                            self.save_news_to_db(news_data)
                            self.news_data.append(news_data)
                            logger.info("成功爬取新浪新闻: %s", news_data['title'])
                            
                            # 检查是否已达到最大新闻数量限制
                            if max_news and len(self.news_data) >= max_news:
                                logger.info("已达到最大新闻数量限制 %s，停止爬取", max_news)
                                return
                        
                        # 随机休眠，避免请求过于频繁
                        self.random_sleep(2, 5)
                else:
                    # 对于没有分页参数的URL，直接爬取
                    url = self.CATEGORY_URLS[cat]
                    logger.info("爬取页面: %s", url)
                    
                    # 获取页面内容
                    html = self.fetch_page(url)
                    if not html:
                        logger.warning("获取分类页面失败: %s", url)
                        continue
                    
                    # 解析页面，提取新闻链接
                    news_links = self.extract_news_links(html, cat)
                    logger.info("提取到新闻链接数量: %s", len(news_links))
                    
                    # 计算剩余可爬取的新闻数量
                    remaining = max_news - len(self.news_data) if max_news else len(news_links)
                    if remaining <= 0:
                        return
                        
                    # 限制爬取的链接数量
                    news_links = news_links[:remaining]
                    
                    # 爬取每个新闻详情
                    for news_link in news_links:
                        self.random_sleep(1, 3)
                        
                        # 爬取新闻详情
                        news_data = self.crawl_news_detail(news_link, cat)
                        if not news_data:
                            continue
                        
                        # 检查新闻日期是否在指定范围内
                        try:
                            news_date = datetime.strptime(news_data['pub_time'].split(' ')[0], '%Y-%m-%d')
                            if news_date < start_date:
                                logger.debug("新闻日期 %s 早于开始日期 %s，跳过", news_date, start_date)
                                continue
                        except Exception as e:
                            logger.warning("解析新闻日期失败: %s, 错误: %s", news_data['pub_time'], str(e))
                        
                        # 保存新闻数据
                        self.save_news_to_db(news_data)
                        self.news_data.append(news_data)
                        logger.info("成功爬取新浪新闻: %s", news_data['title'])
                        
                        # 检查是否已达到最大新闻数量限制
                        if max_news and len(self.news_data) >= max_news:
                            logger.info("已达到最大新闻数量限制 %s，停止爬取", max_news)
                            return
                    
                    # 随机休眠，避免请求过于频繁
                    self.random_sleep(2, 5)
    
    def extract_news_links(self, html, category):
        """
        从页面中提取新闻链接
        
        Args:
            html: 页面内容
            category: 新闻分类
        
        Returns:
            list: 新闻链接列表
        """
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        # 提取所有链接
        for a in soup.find_all('a', href=True):
            url = a['href']
            
            # 处理相对URL
            if not url.startswith('http'):
                if url.startswith('//'):
                    url = 'https:' + url
                else:
                    url = urljoin('https://finance.sina.com.cn', url)
            
            # 验证URL
            if self.validate_url(url):
                links.append(url)
        
        # 移除重复链接
        links = list(set(links))
        
        logger.info("提取到新闻链接数量: %s", len(links))
        return links
    
    def extract_news_links_from_home(self, html, category):
        """
        从首页提取新闻链接
        
        Args:
            html: 页面内容
            category: 新闻分类
        
        Returns:
            list: 新闻链接列表
        """
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        # 提取所有链接
        for a in soup.find_all('a', href=True):
            url = a['href']
            
            # 处理相对URL
            if not url.startswith('http'):
                if url.startswith('//'):
                    url = 'https:' + url
                else:
                    url = urljoin('https://finance.sina.com.cn', url)
            
            # 验证URL
            if self.validate_url(url):
                links.append(url)
        
        # 移除重复链接
        links = list(set(links))
        
        logger.info("提取到新闻链接数量: %s", len(links))
        return links
    
    def validate_url(self, url):
        """
        验证URL是否有效
        
        Args:
            url: URL
        
        Returns:
            bool: 是否有效
        """
        if not url:
            return False
        
        # 检查URL格式
        if not url.startswith('http'):
            return False
        
        # 检查是否是新浪网站
        if 'sina.com.cn' not in url:
            return False
        
        # 过滤非新闻页面
        if any(pattern in url for pattern in [
            '/live/', '/zhibo/', '/video/', '/vr/', '/zhuanlan/', 
            '/ask/', '/search/', '/tags/', '/keyword/', '/zt_', '/special/',
            'photo.sina.com.cn', 'blog.sina.com.cn', 'vip.stock.finance.sina.com.cn',
            'bbs.sina.com.cn', 'club.sina.com.cn', 'comment', 'tousu', 'survey'
        ]):
            return False
        
        # 过滤特定的非新闻URL
        if url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.css', '.js', '.xml')):
            return False
        
        return True
    
    def parse_news_detail(self, html, url, category):
        """
        解析新闻详情
        
        Args:
            html: 页面内容
            url: 新闻URL
            category: 新闻分类
        
        Returns:
            dict: 新闻数据
        """
        if not html:
            return None
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 获取标题
            title = self.extract_title(soup)
            if not title:
                logger.warning("无法找到标题: %s", url)
                return None
            
            # 获取正文内容
            content_html = ""
            content_tag = None
            
            # 尝试不同的内容选择器
            for selector in self.CONTENT_SELECTORS:
                content_tag = soup.select_one(selector)
                if content_tag:
                    break
            
            if not content_tag:
                logger.warning("未找到正文: %s", url)
                return None
            
            # 清理内容
            for script in content_tag.find_all('script'):
                script.decompose()
            for style in content_tag.find_all('style'):
                style.decompose()
            
            # 移除广告和无关元素
            for div in content_tag.find_all('div', class_=lambda c: c and ('recommend' in str(c).lower() or 'footer' in str(c).lower() or 'ad' in str(c).lower() or 'bottom' in str(c).lower())):
                div.decompose()
            
            # 保存处理后的HTML
            content_html = str(content_tag)
            content = content_tag.get_text('\n').strip()
            
            # 确保内容没有乱码
            content = decode_html_entities(content)
            content = decode_unicode_escape(content)
            content = decode_url_encoded(content)
            
            # 提取发布时间
            pub_time = self.extract_pub_time(soup)
            if not pub_time:
                pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 提取作者/来源
            author = self.extract_author(soup)
            
            # 提取图片
            image_urls = []
            image_content_soup = BeautifulSoup(content_html, 'html.parser')
            for img in image_content_soup.find_all('img'):
                img_url = img.get('src')
                if img_url and img_url.startswith('http'):
                    image_urls.append(img_url)
            
            # 提取关键词
            keywords = extract_keywords(content)
            
            # 提取相关股票
            related_stocks = self.extract_related_stocks(soup)
            
            # 生成新闻ID
            news_id = self.generate_news_id(url, title)
            
            # 构建新闻数据
            news_data = {
                'id': news_id,
                'title': title,
                'content': content,
                'content_html': content_html,
                'pub_time': pub_time,
                'source': self.source,
                'author': author,
                'category': category,
                'url': url,
                'keywords': ','.join(keywords) if keywords else '',
                'images': ','.join(image_urls),
                'related_stocks': ','.join(related_stocks) if related_stocks else '',
                'sentiment': 0,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 分析情感
            if content and hasattr(self, 'sentiment_analyzer'):
                try:
                    sentiment = self.sentiment_analyzer.analyze(title, content)
                    news_data['sentiment'] = sentiment
                except Exception as e:
                    logger.error("情感分析失败: %s", str(e))
            
            return news_data
        except Exception as e:
            logger.error("解析新闻详情失败: %s, 错误: %s", url, str(e))
            return None
    
    def crawl_news_detail(self, url, category=None):
        """
        爬取新闻详情
        
        Args:
            url: 新闻URL
            category: 新闻分类
        
        Returns:
            dict: 新闻数据
        """
        if not url or not self.is_valid_news_url(url):
            return None
        
        # 检查是否为广告URL
        if not self.validate_url(url):
            logger.info("过滤无效URL: %s", url)
            return None
        
        try:
            response = self.fetch_page(url)
            if not response:
                logger.warning("无法获取页面内容: %s", url)
                return None
            
            # 解析新闻详情
            return self.parse_news_detail(response, url, category)
        except Exception as e:
            logger.error("爬取新闻详情失败: %s, 错误: %s", url, str(e))
            return None
    
    def extract_title(self, soup):
        """
        提取标题
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 标题
        """
        try:
            # 尝试使用不同的标题选择器
            for selector in self.TITLE_SELECTORS:
                title_tag = soup.select_one(selector)
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    if title:
                        return title
            
            # 尝试使用meta标签提取标题
            meta_tag = soup.select_one('meta[property="og:title"]')
            if meta_tag and 'content' in meta_tag.attrs:
                return meta_tag['content']
            
            # 尝试使用title标签提取标题
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                if '_' in title:
                    return title.split('_')[0].strip()
                if '-' in title:
                    return title.split('-')[0].strip()
                return title
            
            return None
        except Exception as e:
            logger.warning("提取标题失败: %s", str(e))
            return None
    
    def extract_pub_time(self, soup):
        """
        提取发布时间
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 发布时间
        """
        try:
            # 尝试使用不同的时间选择器
            for selector in self.TIME_SELECTORS:
                time_tag = soup.select_one(selector)
                if time_tag:
                    time_text = time_tag.text.strip()
                    
                    # 使用正则表达式提取时间
                    # 匹配格式: 2023年03月28日 12:34 或 2023-03-28 12:34:56
                    time_patterns = [
                        r'(\d{4})年(\d{2})月(\d{2})日\s*(\d{2}):(\d{2})',  # 中文日期格式
                        r'(\d{4})-(\d{2})-(\d{2})\s*(\d{2}):(\d{2}):(\d{2})',  # 标准日期时间格式
                        r'(\d{4})-(\d{2})-(\d{2})\s*(\d{2}):(\d{2})',  # 标准日期时间格式（无秒）
                    ]
                    
                    for pattern in time_patterns:
                        match = re.search(pattern, time_text)
                        if match:
                            groups = match.groups()
                            if len(groups) == 5:  # 中文格式或无秒格式
                                return f"{groups[0]}-{groups[1]}-{groups[2]} {groups[3]}:{groups[4]}:00"
                            elif len(groups) == 6:  # 标准格式
                                return f"{groups[0]}-{groups[1]}-{groups[2]} {groups[3]}:{groups[4]}:{groups[5]}"
            
            # 尝试从meta标签获取时间
            meta_tag = soup.select_one('meta[property="article:published_time"]')
            if meta_tag and 'content' in meta_tag.attrs:
                pub_time = meta_tag['content']
                # 转换为标准格式
                try:
                    dt = datetime.fromisoformat(pub_time.replace('Z', '+00:00'))
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass
            
            # 如果无法提取时间，返回当前时间
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.warning("提取发布时间失败: %s", str(e))
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def extract_author(self, soup):
        """
        提取作者
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 作者
        """
        try:
            # 尝试使用不同的作者选择器
            for selector in self.AUTHOR_SELECTORS:
                author_tag = soup.select_one(selector)
                if author_tag:
                    author_text = author_tag.text.strip()
                    
                    # 使用正则表达式提取作者
                    author_patterns = [
                        r'来源[：:]\s*(.*?)$',  # 匹配"来源："后面的内容
                        r'作者[：:]\s*(.*?)$',  # 匹配"作者："后面的内容
                    ]
                    
                    for pattern in author_patterns:
                        match = re.search(pattern, author_text)
                        if match:
                            return match.group(1).strip()
                    
                    return author_text
            
            # 如果无法提取作者，返回默认值
            return "新浪财经"
        except Exception as e:
            logger.warning("提取作者失败: %s", str(e))
            return "新浪财经"
    
    def extract_related_stocks(self, soup):
        """
        提取相关股票
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            list: 相关股票列表
        """
        related_stocks = []
        try:
            # 查找相关股票标签
            stock_selectors = [
                'div.stock-info a',  # 传统股票信息
                'div.related-stock a',  # 相关股票
                'div.stock-wrap a',  # 股票包装
                'a[href*="finance.sina.com.cn/realstock/company"]',  # 股票链接
            ]
            
            for selector in stock_selectors:
                stock_tags = soup.select(selector)
                for stock_tag in stock_tags:
                    stock_text = stock_tag.text.strip()
                    if stock_text and '(' in stock_text and ')' in stock_text:
                        # 提取股票代码和名称
                        match = re.search(r'(.*?)\((.*?)\)', stock_text)
                        if match:
                            stock_name = match.group(1).strip()
                            stock_code = match.group(2).strip()
                            related_stocks.append(f"{stock_name}({stock_code})")
        except Exception as e:
            logger.warning("提取相关股票失败: %s", str(e))
        
        return related_stocks
    
    def generate_news_id(self, url, title):
        """
        生成新闻ID
        
        Args:
            url: 新闻URL
            title: 新闻标题
        
        Returns:
            str: 新闻ID
        """
        # 使用URL和标题生成唯一ID
        text = url + title
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def save_news_to_db(self, news_data):
        """
        保存新闻到数据库
        
        Args:
            news_data: 新闻数据字典
            
        Returns:
            bool: 是否保存成功
        """
        try:
            if not news_data:
                return False
                
            # 确保数据库管理器已初始化
            if not hasattr(self, 'db_manager') or not self.db_manager:
                logger.error("数据库管理器未初始化")
                return False
                
            # 检查新闻数据是否包含必要字段
            required_fields = ['id', 'title', 'url', 'pub_time', 'content']
            for field in required_fields:
                if field not in news_data:
                    logger.warning("新闻数据缺少必要字段: %s", field)
                    return False
            
            # 确保content字段有值
            if not news_data.get('content'):
                logger.warning("新闻内容为空: %s", news_data.get('title', '未知标题'))
                return False
                
            # 保存到数据库
            result = self.db_manager.save_news(news_data)
            if result:
                logger.info("成功保存新闻到数据库: %s", news_data['title'])
                return True
            else:
                logger.warning("保存新闻到数据库失败: %s", news_data['title'])
                return False
        except Exception as e:
            logger.error("保存新闻到数据库时发生错误: %s, 错误: %s", 
                        news_data.get('title', '未知标题'), str(e))
            return False
    
    def _setup_logger(self):
        """配置详细的日志系统"""
        global logger
        
        # 使用统一的爬虫日志记录器
        logger = get_crawler_logger('sina')
        logger.info("优化版新浪财经爬虫日志系统初始化完成")
        
        # 记录数据库路径信息
        if hasattr(self, 'db_path'):
            logger.info(f"数据库路径: {self.db_path}")
        elif hasattr(self, 'db_manager') and self.db_manager and hasattr(self.db_manager, 'main_db_path'):
            self.db_path = self.db_manager.main_db_path
            logger.info(f"数据库路径(从db_manager获取): {self.db_path}")
        
        # 打印日志信息
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', '新浪财经')
        today = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(log_dir, f'sina_{today}.log')
        logger.info(f"日志文件路径: {log_file}")
    
    def __del__(self):
        """析构函数，关闭资源"""
        # 关闭异步会话
        if hasattr(self, 'session') and self.session:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._close_session())
                else:
                    loop.run_until_complete(self._close_session())
            except Exception as e:
                logger.error("关闭异步会话失败: %s", str(e))
        
        # 关闭线程池
        if hasattr(self, 'executor') and self.executor:
            self.executor.shutdown(wait=False)
        
        # 调用父类析构函数
        super().__del__()

    def extract_content(self, soup):
        """
        优化后的内容提取方法，处理不同页面结构
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 提取的正文内容
        """
        # 尝试多种常见的内容选择器
        selectors = [
            '.article',  # 常见文章容器
            '.articalContent',  # 另一种文章容器
            '.main-content',  # 主内容区域
            '.article-content',  # 文章内容
            '.content',  # 通用内容
            '#artibody',  # 文章正文
            '.article-body',  # 文章主体
            '.article-main',  # 文章主区域
            '.article-detail',  # 文章详情
        ]
        
        for selector in selectors:
            content = soup.select_one(selector)
            if content:
                # 清理不需要的元素
                for elem in content(['script', 'style', 'iframe', 'noscript', 'aside', 'footer']):
                    elem.decompose()
                return content.get_text(separator='\n', strip=True)
        
        # 如果通过选择器找不到，尝试通用方法
        return self.extract_content_generic(soup)

    def extract_content_generic(self, soup):
        """
        通用内容提取方法，作为最后的手段
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 提取的正文内容
        """
        # 获取所有文本内容
        text = soup.get_text(separator='\n', strip=True)
        
        # 过滤掉不需要的文本
        lines = [line for line in text.splitlines() 
                if len(line.strip()) > 20  # 过滤短行
                and not any(x in line for x in ['版权', '声明', '相关阅读'])  # 过滤版权信息
                and not line.startswith(('http', 'www'))]  # 过滤URL
        
        return '\n'.join(lines)

if __name__ == "__main__":
    # 测试爬虫
    try:
        crawler = OptimizedSinaCrawler(use_proxy=False, use_source_db=True)
        news_list = crawler.crawl(days=1, max_pages=2)
        print(f"爬取到新闻数量: {len(news_list)}")
    except Exception as e:
        import traceback
        print(f"测试爬虫时出错: {str(e)}")
        print(traceback.format_exc())