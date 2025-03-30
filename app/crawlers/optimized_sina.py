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
import asyncio
import aiohttp
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

import logging
from urllib.parse import urlparse
from app.crawlers.base import BaseCrawler
from app.utils.text_cleaner import clean_html, extract_keywords, decode_html_entities, decode_unicode_escape, decode_url_encoded
from app.db.sqlite_manager import SQLiteManager
from app.utils.ad_filter import AdFilter
from app.utils.image_detector import ImageDetector

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
    
    # 新浪财经API URL - 使用新浪财经的API获取最新新闻
    API_URL = "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid={lid}&k=&num=50&page={page}"
    
    # 分类与API参数映射
    CATEGORY_API_MAP = {
        '财经': '2516',
        '股票': '2517',
        '公司': '2518',
        '产业': '2519',
        '宏观': '2520',
        '国际': '2521',
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
    
    # 广告URL特征 - 更新为最新的广告特征
    AD_URL_PATTERNS = [
        'download', 
        'app',
        'promotion',
        'activity',
        'zhuanti',
        'special',
        'advert',
        'subscribe',
        'vip',
        'client',
        'special',
        'topic',
        'hot',
        'apk',
        'store.sina.com.cn',
        'game',
        'sinaapp',
        'sax',
        'sina.cn',
        'sinaimg.cn/ad',
        'sinajs.cn',
        'beacon',
        'analytics',
        'tracking',
        'click.sina',
        'sax.sina',
        'weibo.com/login',
        'passport.weibo',
        'sina.com.cn/sso',
    ]
    
    # 广告内容关键词 - 更新为最新的广告关键词
    AD_CONTENT_KEYWORDS = [
        '下载APP',
        '新浪财经APP',
        '新浪新闻APP',
        '扫描下载',
        '立即下载',
        '下载新浪',
        '扫码下载',
        '专属福利',
        '点击下载',
        '安装新浪',
        '新浪新闻客户端',
        '独家活动',
        '活动详情',
        '注册即送',
        '点击安装',
        '官方下载',
        'APP专享',
        '扫一扫下载',
        '新人专享',
        '首次下载',
        '关注微博',
        '关注微信',
        '扫描二维码',
        '添加微信',
        '点击关注',
        '一键关注',
        '立即关注',
        '关注公众号',
        '添加客服',
        '联系客服',
    ]
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, **kwargs):
        """
        初始化优化版新浪财经爬虫
        
        Args:
            db_manager: 数据库管理器对象
            db_path: 数据库路径，如果为None则使用默认路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
        """
        self.source = "新浪财经"
        self.name = "optimized_sina"  # 添加name属性
        self.status = "idle"  # 添加爬虫状态属性
        self.last_run = None  # 添加上次运行时间属性
        self.next_run = None  # 添加下次运行时间属性
        self.error_count = 0  # 添加错误计数属性
        self.success_count = 0  # 添加成功计数属性
        self.news_data = []  # 存储爬取的新闻数据
        
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
        
        # 初始化父类
        super().__init__(db_manager, db_path, use_proxy, use_source_db, **kwargs)
        
        # 初始化广告过滤器
        self.ad_filter = AdFilter(source_name=self.source)
        self.image_detector = ImageDetector(cache_dir='./image_cache')
        
        # 如果提供了db_manager并且不是SQLiteManager类型，创建SQLiteManager
        if db_manager and not isinstance(db_manager, SQLiteManager):
            if hasattr(db_manager, 'db_path'):
                self.sqlite_manager = SQLiteManager(db_manager.db_path)
            else:
                # 使用传入的db_path或默认路径
                self.sqlite_manager = SQLiteManager(db_path or self.db_path)
        elif not db_manager:
            # 如果没有提供db_manager，创建SQLiteManager
            self.sqlite_manager = SQLiteManager(db_path or self.db_path)
        else:
            # 否则使用提供的db_manager
            self.sqlite_manager = db_manager
        
        # 初始化线程池
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # 初始化异步会话
        self.session = None
        
        logger.info("优化版新浪财经爬虫初始化完成，数据库路径: %s", self.db_path)
    
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
    
    def crawl(self, days=1, max_pages=3):
        """
        爬取新浪财经的新闻
        
        Args:
            days: 爬取的天数范围，默认为1天
            max_pages: 每个分类最多爬取的页数，默认为3页
            
        Returns:
            list: 爬取的新闻列表
        """
        logger.info("开始爬取%s新闻，天数范围: %s天，每个分类最多爬取: %s页", self.source, days, max_pages)
        
        # 重置过滤计数
        self.ad_filter.reset_filter_count()
        self.image_detector.reset_ad_count()
        
        # 清空新闻数据列表
        self.news_data = []
        
        # 计算开始日期
        start_date = datetime.now() - timedelta(days=days)
        
        # 使用异步方式爬取
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self._crawl_async(days, max_pages, start_date))
        except Exception as e:
            logger.error("异步爬取失败: %s", str(e))
            # 如果异步爬取失败，回退到同步爬取
            self._crawl_sync(days, max_pages, start_date)
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
        
        logger.info("爬取完成，共爬取新闻 %s 条，过滤广告 %s 条，过滤广告图片 %s 张", 
                   len(self.news_data), self.ad_filter.get_filter_count(), self.image_detector.get_ad_count())
        return self.news_data
    
    async def _crawl_async(self, days, max_pages, start_date):
        """
        异步爬取新闻
        
        Args:
            days: 爬取的天数范围
            max_pages: 每个分类最多爬取的页数
            start_date: 开始日期
        """
        logger.info("使用异步方式爬取新闻")
        
        # 首先尝试使用API获取新闻
        try:
            logger.info("尝试使用API获取新闻")
            await self._crawl_from_api_async(max_pages, start_date)
        except Exception as e:
            logger.error("使用API获取新闻失败: %s", str(e))
        
        # 如果API获取的新闻不足，再尝试从网页获取
        if len(self.news_data) < 50:
            logger.info("API获取的新闻数量不足(%s条)，尝试从网页获取", len(self.news_data))
            
            # 从首页获取新闻
            try:
                logger.info("尝试从首页获取新闻")
                home_url = "https://finance.sina.com.cn/"
                html = await self.async_fetch_page(home_url)
                if html:
                    news_links = self.extract_news_links_from_home(html, "财经")
                    logger.info("从首页提取到新闻链接数量: %s", len(news_links))
                    
                    # 异步爬取每个新闻详情
                    tasks = []
                    for news_link in news_links:
                        tasks.append(self._crawl_news_detail_async(news_link, "财经", start_date))
                    
                    # 等待所有任务完成
                    await asyncio.gather(*tasks)
            except Exception as e:
                logger.error("从首页获取新闻失败: %s", str(e))
            
            # 如果从首页获取的新闻仍然不足，再尝试从分类页获取
            if len(self.news_data) < 50:
                logger.info("从首页获取的新闻数量不足(%s条)，尝试从分类页获取", len(self.news_data))
                
                # 爬取每个分类的新闻
                tasks = []
                for category, url_template in self.CATEGORY_URLS.items():
                    # 只处理带有分页参数的URL
                    if '{}' in url_template:
                        for page in range(1, max_pages + 1):
                            url = url_template.format(page)
                            tasks.append(self._crawl_category_page_async(url, category, start_date))
                    else:
                        # 对于没有分页参数的URL，直接爬取
                        tasks.append(self._crawl_category_page_async(url_template, category, start_date))
                
                # 等待所有任务完成
                await asyncio.gather(*tasks)
    
    async def _crawl_from_api_async(self, max_pages, start_date):
        """
        从API异步爬取新闻
        
        Args:
            max_pages: 最大页数
            start_date: 开始日期
        """
        tasks = []
        for category, lid in self.CATEGORY_API_MAP.items():
            for page in range(1, max_pages + 1):
                url = self.API_URL.format(lid=lid, page=page)
                tasks.append(self._crawl_api_page_async(url, category, start_date))
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
    
    async def _crawl_api_page_async(self, url, category, start_date):
        """
        异步爬取API页面
        
        Args:
            url: API URL
            category: 分类
            start_date: 开始日期
        """
        try:
            # 获取API响应
            html = await self.async_fetch_page(url)
            if not html:
                logger.warning("获取API页面失败: %s", url)
                return
            
            # 解析JSON响应
            try:
                data = json.loads(html)
                if data.get('result', {}).get('status', {}).get('code') != 0:
                    logger.warning("API返回错误: %s", data)
                    return
                
                # 提取新闻列表
                news_list = data.get('result', {}).get('data', [])
                logger.info("从API获取到新闻数量: %s", len(news_list))
                
                # 处理每条新闻
                tasks = []
                for news_item in news_list:
                    # 提取新闻URL
                    news_url = news_item.get('url')
                    if not news_url or not self.validate_url(news_url):
                        continue
                    
                    # 提取发布时间
                    pub_time_str = news_item.get('ctime')
                    if pub_time_str:
                        try:
                            pub_time = datetime.fromtimestamp(int(pub_time_str))
                            if pub_time < start_date:
                                logger.debug("新闻日期 %s 早于开始日期 %s，跳过", pub_time, start_date)
                                continue
                        except Exception as e:
                            logger.warning("解析API新闻日期失败: %s, 错误: %s", pub_time_str, str(e))
                    
                    # 异步爬取新闻详情
                    tasks.append(self._crawl_news_detail_async(news_url, category, start_date))
                
                # 等待所有任务完成
                await asyncio.gather(*tasks)
            except json.JSONDecodeError as e:
                logger.error("解析API响应失败: %s, 错误: %s", url, str(e))
        except Exception as e:
            logger.error("爬取API页面失败: %s, 错误: %s", url, str(e))
    
    async def _crawl_category_page_async(self, url, category, start_date):
        """
        异步爬取分类页面
        
        Args:
            url: 分类页面URL
            category: 分类
            start_date: 开始日期
        """
        try:
            logger.info("爬取分类页面: %s, 分类: %s", url, category)
            
            # 获取页面内容
            html = await self.async_fetch_page(url)
            if not html:
                logger.warning("获取分类页面失败: %s", url)
                return
            
            # 解析页面，提取新闻链接
            news_links = self.extract_news_links(html, category)
            logger.info("从分类页面提取到新闻链接数量: %s", len(news_links))
            
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
        try:
            # 验证URL
            if not url or not self.validate_url(url):
                return
            
            # 获取页面内容
            html = await self.async_fetch_page(url)
            if not html:
                logger.warning("获取新闻详情失败: %s", url)
                return
            
            # 解析新闻详情
            news_data = self.parse_news_detail(html, url, category)
            if not news_data:
                logger.warning("解析新闻详情失败: %s", url)
                return
            
            # 检查新闻日期是否在指定范围内
            try:
                news_date = datetime.strptime(news_data['pub_time'].split(' ')[0], '%Y-%m-%d')
                if news_date < start_date:
                    logger.debug("新闻日期 %s 早于开始日期 %s，跳过", news_date, start_date)
                    return
            except Exception as e:
                logger.warning("解析新闻日期失败: %s, 错误: %s", news_data['pub_time'], str(e))
            
            # 保存新闻数据
            self.save_news_to_db(news_data)
            self.news_data.append(news_data)
            self.success_count += 1
            logger.info("成功爬取新浪新闻: %s", news_data['title'])
        except Exception as e:
            logger.error("爬取新闻详情失败: %s, 错误: %s", url, str(e))
    
    def _crawl_sync(self, days, max_pages, start_date):
        """
        同步爬取新闻（作为异步爬取的备选方案）
        
        Args:
            days: 爬取的天数范围
            max_pages: 每个分类最多爬取的页数
            start_date: 开始日期
        """
        logger.info("使用同步方式爬取新闻")
        
        # 尝试从首页获取新闻
        try:
            logger.info("尝试从首页获取新闻")
            home_url = "https://finance.sina.com.cn/"
            html = self.fetch_page(home_url)
            if html:
                news_links = self.extract_news_links_from_home(html, "财经")
                logger.info("从首页提取到新闻链接数量: %s", len(news_links))
                
                # 爬取每个新闻详情
                for news_link in news_links:
                    # 随机休眠，避免被反爬
                    self.random_sleep(1, 3)
                    
                    # 爬取新闻详情
                    news_data = self.crawl_news_detail(news_link, "财经")
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
                    self.success_count += 1
                    logger.info("成功爬取新浪新闻: %s", news_data['title'])
        except Exception as e:
            logger.error("从首页获取新闻失败: %s", str(e))
        
        # 如果从首页获取的新闻不足，再尝试从分类页获取
        if len(self.news_data) < 10:
            # 爬取每个分类的新闻
            for category, url_template in self.CATEGORY_URLS.items():
                logger.info("爬取分类: %s", category)
                
                # 处理带有分页参数的URL
                if '{}' in url_template:
                    # 爬取前max_pages页
                    for page in range(1, max_pages + 1):
                        url = url_template.format(page)
                        logger.info("爬取页面: %s", url)
                        
                        # 获取页面内容
                        html = self.fetch_page(url)
                        if not html:
                            logger.warning("获取页面失败: %s", url)
                            continue
                        
                        # 解析页面，提取新闻链接
                        news_links = self.extract_news_links(html, category)
                        logger.info("提取到新闻链接数量: %s", len(news_links))
                        
                        # 爬取每个新闻详情
                        for news_link in news_links:
                            # 随机休眠，避免被反爬
                            self.random_sleep(1, 3)
                            
                            # 爬取新闻详情
                            news_data = self.crawl_news_detail(news_link, category)
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
                            self.success_count += 1
                            logger.info("成功爬取新浪新闻: %s", news_data['title'])
                        
                        # 随机休眠，避免被反爬
                        self.random_sleep(2, 5)
                else:
                    # 对于没有分页参数的URL，直接爬取
                    url = url_template
                    logger.info("爬取页面: %s", url)
                    
                    # 获取页面内容
                    html = self.fetch_page(url)
                    if not html:
                        logger.warning("获取页面失败: %s", url)
                        continue
                    
                    # 解析页面，提取新闻链接
                    news_links = self.extract_news_links(html, category)
                    logger.info("提取到新闻链接数量: %s", len(news_links))
                    
                    # 爬取每个新闻详情
                    for news_link in news_links:
                        # 随机休眠，避免被反爬
                        self.random_sleep(1, 3)
                        
                        # 爬取新闻详情
                        news_data = self.crawl_news_detail(news_link, category)
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
                        self.success_count += 1
                        logger.info("成功爬取新浪新闻: %s", news_data['title'])
                    
                    # 随机休眠，避免被反爬
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
        news_links = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找新闻列表 - 更新选择器以适应最新的页面结构
            selectors = [
                'ul.list_009 li a',  # 传统新闻列表
                'div.feed-card-item h2 a',  # 新版新闻卡片
                'div.news-item h2 a',  # 另一种新闻卡片
                'li.news-item a',  # 简化新闻列表
                'div.m-list li a',  # 移动版列表
                'ul.list-a li a',  # 另一种列表样式
                'div.news-list a',  # 通用新闻列表
                'a[href*="finance.sina.com.cn"]',  # 通用链接选择器
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link_tag in links:
                    link = link_tag.get('href')
                    if not link:
                        continue
                    
                    # 验证链接
                    if not self.validate_url(link):
                        continue
                    
                    # 添加到链接列表，避免重复
                    if link not in news_links:
                        news_links.append(link)
        except Exception as e:
            logger.error("提取新闻链接失败: %s, 错误: %s", category, str(e))
        
        return news_links

    def extract_news_links_from_home(self, html, category):
        """
        从首页提取新闻链接
        
        Args:
            html: 页面内容
            category: 新闻分类
        
        Returns:
            list: 新闻链接列表
        """
        news_links = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找新闻链接 - 更新选择器以适应最新的首页结构
            selectors = [
                'a[href*="finance.sina.com.cn"]',  # 通用链接选择器
                'div.fin_tabs div.tab-content a',  # 财经标签页内容
                'div.m-list li a',  # 移动版列表
                'div.news-list a',  # 通用新闻列表
                'div.feed-card a',  # 新版卡片
                'div.slide-item a',  # 轮播图
                'div.top-news a',  # 头条新闻
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link_tag in links:
                    link = link_tag.get('href')
                    if not link:
                        continue
                    
                    # 验证链接，确保是新闻页面而不是分类页面
                    if not self.validate_url(link):
                        continue
                    
                    # 确保链接包含数字（新闻ID），过滤掉分类页面
                    if not any(c.isdigit() for c in link):
                        continue
                    
                    # 添加到链接列表，避免重复
                    if link not in news_links:
                        news_links.append(link)
        except Exception as e:
            logger.error("从首页提取新闻链接失败: %s, 错误: %s", category, str(e))
        
        return news_links
    
    def validate_url(self, url):
        """
        验证URL是否有效
        
        Args:
            url: URL
        
        Returns:
            bool: 是否有效
        """
        # 检查URL是否为空
        if not url:
            return False
        
        # 检查URL是否为绝对URL
        if not url.startswith('http'):
            return False
        
        # 检查URL是否为新浪财经的URL
        if 'sina.com.cn' not in url:
            return False
            
        # 检查URL是否是广告
        for pattern in self.AD_URL_PATTERNS:
            if pattern in url:
                logger.info("过滤广告URL: %s", url)
                return False
        
        return True
    
    def is_valid_news_url(self, url):
        """
        检查是否为有效的新闻URL
        
        Args:
            url: URL
        
        Returns:
            bool: 是否有效
        """
        if not self.validate_url(url):
            return False
        
        # 检查URL是否包含新闻ID（通常包含数字）
        if not any(c.isdigit() for c in url):
            return False
        
        # 检查URL是否包含常见的新闻路径
        news_paths = ['/doc-', '/article_', '/news_', '/s_', '/a_']
        if not any(path in url for path in news_paths):
            # 如果不包含常见路径，检查是否包含日期格式（如/2023-03-28/）
            if not re.search(r'/\d{4}-\d{2}-\d{2}/', url):
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
            
            # 检查内容是否为广告
            if self.ad_filter.is_ad_content(content, title=title, category=category):
                logger.info("过滤广告内容: %s, URL: %s", title, url)
                return None
            
            # 提取发布时间
            pub_time = self.extract_pub_time(soup)
            if not pub_time:
                pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 提取作者/来源
            author = self.extract_author(soup)
            
            # 提取图片并检测广告图片
            image_urls = []
            ad_images_removed = False
            image_content_soup = BeautifulSoup(content_html, 'html.parser')
            
            for img in image_content_soup.find_all('img'):
                img_url = img.get('src')
                if img_url and img_url.startswith('http'):
                    if self.image_detector.is_ad_image(img_url, context={'category': category}):
                        logger.info("过滤广告图片: %s", img_url)
                        img.decompose()  # 从HTML中移除广告图片
                        ad_images_removed = True
                    else:
                        image_urls.append(img_url)
            
            # 如果移除了广告图片，更新内容HTML和纯文本
            if ad_images_removed:
                content_html = str(image_content_soup)
                content = image_content_soup.get_text('\n').strip()
            
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
    
    def save_news_to_db(self, news):
        """
        保存新闻到数据库
        
        Args:
            news: 新闻数据字典
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 如果有sqlite_manager属性则使用它保存
            if hasattr(self, 'sqlite_manager') and self.sqlite_manager:
                return self.sqlite_manager.save_news(news)
            
            # 否则使用父类的save_news方法保存到内存中
            return super().save_news(news)
        except Exception as e:
            logger.error("保存新闻到数据库失败: %s, 错误: %s", news.get('title', '未知标题'), str(e))
            return False
    
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
    crawler = OptimizedSinaCrawler(use_proxy=False, use_source_db=True)
    news_list = crawler.crawl(days=1, max_pages=2)
    print(f"爬取到新闻数量: {len(news_list)}")
from app.crawlers.optimized_sina import OptimizedSinaCrawler

crawler = OptimizedSinaCrawler(use_proxy=False, use_source_db=True)
news_list = crawler.crawl(days=1, max_pages=2)
print(f"爬取到新闻数量: {len(news_list)}")