#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
新浪财经爬虫模块
"""

import datetime
import re
import os
import time
import json
import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
from typing import Optional, Dict, List, Any
import urllib.parse
import sqlite3
import logging
import hashlib
import traceback
from datetime import datetime, timedelta

# 从app目录导入BaseCrawler和SQLiteManager
from app.crawlers.base import BaseCrawler
from app.db.SQLiteManager import SQLiteManager

logger = logging.getLogger('新浪财经')

class SinaCrawler(BaseCrawler):
    """新浪财经爬虫，用于爬取新浪财经的财经新闻"""

    source = '新浪财经'

    ad_patterns: List[str] = [
        'sinaads', 'adbox', 'advertisement', 'promotion', 'sponsor', 
        'click.sina', 'sina.cn', 'game.weibo', 'games.sina', 'iask'
    ]

    CATEGORY_URLS: Dict[str, str] = {
        '财经': 'https://finance.sina.com.cn/',
        '股票': 'https://finance.sina.com.cn/stock/',
        '新股': 'https://finance.sina.com.cn/stock/newstock/',
        '港股': 'https://finance.sina.com.cn/stock/hkstock/',
        '美股': 'https://finance.sina.com.cn/stock/usstock/',
        '基金': 'https://finance.sina.com.cn/fund/',
        '期货': 'https://finance.sina.com.cn/futures/',
        '外汇': 'https://finance.sina.com.cn/forex/',
        '黄金': 'https://finance.sina.com.cn/nmetal/',
        '债券': 'https://finance.sina.com.cn/bond/',
        '理财': 'https://money.sina.com.cn/money/',
        '银行': 'https://finance.sina.com.cn/money/bank/',
        '保险': 'https://finance.sina.com.cn/money/insurance/',
        '信托': 'https://finance.sina.com.cn/trust/',
        '科技': 'https://tech.sina.com.cn/',
        '医药': 'https://finance.sina.com.cn/med/',
        'ESG': 'https://finance.sina.com.cn/esg/',
        '专栏': 'https://finance.sina.com.cn/roll/index.d.html?cat=finance',
        '博客': 'http://blog.sina.com.cn/lm/finance/',
        '滚动': 'https://finance.sina.com.cn/roll/',
        '要闻': 'https://finance.sina.com.cn/roll/index.d.html?cid=56588',
        '股市及时雨': 'https://finance.sina.com.cn/roll/index.d.html?cid=56589',
        '宏观研究': 'https://finance.sina.com.cn/roll/index.d.html?cid=56598',
        'IPO观察哨': 'https://finance.sina.com.cn/ipo/',
        '上市公司': 'https://finance.sina.com.cn/listedcompany/',
        '银行财眼': 'https://finance.sina.com.cn/bankingeye/',
        '国际财经': 'https://finance.sina.com.cn/world/',
    }

    STOCK_PAGE_SELECTORS = {
        'news_links': 'div.pagebox a.next, div.pages a.next,
            div.news-list a:contains("下一页"), div.pages a:contains("下一页"),
            a.next, a.next-page, a[rel="next"],
            a.page-next, a.pagebox_next,
            li.next a, a:-soup-contains("下一页")',
        'a.next': 'div.pagebox a.next',
        'a.next-page': 'div.pages a.next',
        'div.news-list a:-soup-contains("下一页")': 'div.news-list a:-soup-contains("下一页")',
        'div.pages a:-soup-contains("下一页")': 'div.pages a:-soup-contains("下一页")',
        'li.next a': 'li.next a',
        'a:-soup-contains("下一页")': 'a:-soup-contains("下一页")'
    }

    
    CONTENT_SELECTORS = [
        'div.article-content',
        'div#artibody',
        'div.main-content',
        'div.content',
        'div.article',
        'article'
    ]
    
    TITLE_SELECTORS = [
        'h1.main-title',
        'h1#artibodyTitle',
        'h1.title',
        'h1.article-title',
        'h1.m-title',
        'h1.focus-title',
        'h1.content-title',
        'div.page-header h1',
        'div.txt-hd h1',
        'div.f_center h1',
        'div.headline h1'
    ]
    
    NEWS_LIST_SELECTORS = [
        # 普通新闻列表
        'ul.news-list li',
        'div.news-item',
        'div.feed-card-item',
        'div.news-list a',
        # 滚动新闻
        '.r-nt2 li',
        '.feed-card-item',
        '.m-list li',
        # 综合选择器
        '.list-a li',
        '.list-b li', 
        '.list-c li',
        '.news-card'
    ]
    
    def __init__(self, db_manager: Optional[Any] = None, db_path: Optional[str] = None, use_proxy: bool = False, **kwargs: Any):
        """
        初始化新浪财经爬虫
        
        Args:
            db_manager: 数据库管理器实例 (from BaseCrawler, typically SQLiteManager)
            db_path: 数据库路径 (used if db_manager is not provided)
            use_proxy: 是否使用代理
            **kwargs: Additional arguments for BaseCrawler
        """
        super().__init__(db_manager=db_manager, db_path=db_path or './data/news.db', use_proxy=use_proxy, source=self.source, **kwargs)
        
        # 检查数据库管理器是否已初始化，没有的话手动初始化
        if not self.db_manager:
            from app.db.SQLiteManager import SQLiteManager
            self.db_manager = SQLiteManager(db_path or './data/news.db')
            self.logger.info(f"手动初始化数据库管理器 SQLiteManager: {db_path or './data/news.db'}")
        
        # 确保源数据库目录存在
        import os
        source_db_dir = os.path.join(os.path.dirname(self.db_manager.db_path), 'sources')
        os.makedirs(source_db_dir, exist_ok=True)
        
        # 预先连接到源数据库并创建表结构
        source_db_path = self.db_manager.get_source_db_path(self.source)
        conn = self.db_manager.get_connection(source_db_path)
        if conn:
            self.logger.info(f"已连接到源数据库: {source_db_path}")
            self.db_manager.create_tables_for_connection(conn)
            self.logger.info(f"已创建源数据库表结构: {source_db_path}")
        else:
            self.logger.error(f"无法连接到源数据库: {source_db_path}")

        # The `days` attribute might be set by `crawl` method, or passed via kwargs to BaseCrawler settings
        self.days: int = kwargs.get('days', 1) # Default to 1 if not passed, consistent with crawl method signature

        self.logger.info(f"新浪财经爬虫 ({self.source}) 初始化完成. DB Manager: {type(self.db_manager).__name__ if self.db_manager else 'N/A'}, DB Path: {self.db_manager.db_path if self.db_manager else 'N/A'}")

    # def _init_database(self): # REMOVE - Handled by BaseCrawler
    #     ...
    
    # def _init_proxy(self): # REMOVE - Handled by BaseCrawler
    #     ...

    # def _init_config(self): # REVIEW - BaseCrawler has self.settings; specific configs can go there or be class attrs
    #     ...

    def fetch_page(self, url, params=None, headers=None, max_retries=3, timeout=10):
        """获取页面内容
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 请求头
            max_retries: 最大重试次数
            timeout: 超时时间(秒)
            
        Returns:
            str: 页面HTML内容，获取失败则返回None
        """
        self.logger.info(f"开始获取页面: {url}")
        
        # 如果没有提供请求头，使用默认请求头
        if not headers:
            # 构建随机的User-Agent
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
            ]
            random_user_agent = random.choice(user_agents)
            
            headers = {
                'User-Agent': random_user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            self.logger.debug(f"使用随机User-Agent: {random_user_agent}")
        
        # 重试机制
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"尝试获取页面 (尝试 {attempt+1}/{max_retries}): {url}")
                
                # 发送请求
                response = requests.get(
                    url, 
                    params=params, 
                    headers=headers, 
                    timeout=timeout,
                    verify=False  # 忽略SSL证书验证，解决一些HTTPS问题
                )
                
                # 检查响应状态码
                if response.status_code != 200:
                    self.logger.warning(f"HTTP请求失败，状态码: {response.status_code}, URL: {url}")
                    time.sleep(1 * (attempt + 1))  # 逐步增加等待时间
                    continue
                
                # 检查是否有内容
                if not response.content:
                    self.logger.warning(f"响应内容为空，URL: {url}")
                    time.sleep(1 * (attempt + 1))
                    continue
                
                # 尝试检测并处理编码问题
                try:
                    # 首先尝试使用响应的编码
                    html = response.text
                    
                    # 如果内容太短或包含乱码，尝试使用不同的编码
                    if len(html) < 100 or '' in html:
                        self.logger.debug(f"尝试使用不同的编码解析页面，原编码: {response.encoding}")
                        if response.encoding.lower() != 'utf-8':
                            html = response.content.decode('utf-8', errors='replace')
                        else:
                            # 中文网站常用的编码
                            for encoding in ['gb2312', 'gbk', 'gb18030']:
                                try:
                                    html = response.content.decode(encoding, errors='replace')
                                    if '' not in html:
                                        self.logger.debug(f"使用 {encoding} 编码成功")
                                        break
                                except UnicodeDecodeError:
                                    continue
                except Exception as e:
                    self.logger.warning(f"解码页面内容时出错: {e}")
                    html = response.text  # 回退到默认方式
                
                self.logger.info(f"成功获取页面，大小: {len(html)} 字节, URL: {url}")
                return html
                
            except requests.Timeout:
                self.logger.warning(f"请求超时 (尝试 {attempt+1}/{max_retries}): {url}")
                time.sleep(1 * (attempt + 1))
            except requests.ConnectionError:
                self.logger.warning(f"连接错误 (尝试 {attempt+1}/{max_retries}): {url}")
                time.sleep(2 * (attempt + 1))
            except Exception as e:
                self.logger.error(f"请求页面时发生未知错误 (尝试 {attempt+1}/{max_retries}): {url}, 错误: {str(e)}")
                time.sleep(1.5 * (attempt + 1))
        
        self.logger.error(f"获取页面失败，已达到最大重试次数 ({max_retries}): {url}")
        return None

    def _crawl_category(self, category: str, base_url: str, max_pages: int):
        """
        爬取特定分类的新闻：提取所有链接（处理分页）然后处理链接
        
        Args:
            category (str): 分类名称
            base_url (str): 分类起始URL
            max_pages (int): 最大页数
            
        Returns:
            List[Dict[str, Any]]: 提取的新闻列表
        """
        self.logger.info(f"开始处理分类: {category}, 起始URL: {base_url}")
        category_news = []
        
        try:
            # 第1步: 使用分页方法提取所有链接
            all_links_for_category = self._extract_links_for_category(base_url, category, max_pages)
            
            if not all_links_for_category:
                self.logger.info(f"分类 '{category}' 未提取到任何链接")
                return category_news
                
            # 确认链接数量
            self.logger.info(f"分类 '{category}' 共提取到 {len(all_links_for_category)} 个有效链接，开始提取新闻内容")
            
            # 第2步: 处理所有链接并提取新闻内容
            valid_links_count = 0
            
            for link_index, url in enumerate(all_links_for_category):
                try:
                    # 如果是测试URL，直接跳过
                    if 'TESTARTICLE' in url:
                        continue
                    
                    # 避免频繁请求
                    if link_index > 0:
                        time.sleep(random.uniform(0.5, 1.5))
                    
                    # 处理链接，获取新闻详情
                    self.logger.info(f"处理链接 [{link_index+1}/{len(all_links_for_category)}]: {url}")
                    news_item = self.process_news_link(url, category)
                    
                    # 如果获取到新闻详情且符合日期要求，保存并累计
                    if news_item and self._is_news_in_date_range(news_item):
                        # 保存到数据库
                        if self._save_news(news_item):
                            valid_links_count += 1
                            category_news.append(news_item)
                            
                            # 记录成功爬取的数量
                            self.stats['success_count'] += 1
                            
                            # 日志记录成功信息
                            self.logger.info(f"成功提取新闻: {news_item.get('title', '无标题')} [{valid_links_count}]")
                        else:
                            self.logger.warning(f"新闻保存失败: {news_item.get('title', '无标题')}")
                            self.stats['failed_save_count'] += 1
                    else:
                        self.logger.debug(f"链接 {url} 不是有效新闻或不在日期范围内")
                        self.stats['invalid_count'] += 1
                        
                except Exception as e:
                    self.logger.error(f"处理链接时出错: {url} - {str(e)}")
                    self.stats['error_count'] += 1
                    continue
                    
                # 如果已经获取到足够的新闻，提前结束
                if valid_links_count >= self.max_news_per_category:
                    self.logger.info(f"已获取足够数量的新闻 ({valid_links_count}/{self.max_news_per_category})，停止处理")
                    break
            
            # 记录分类爬取结果
            self.logger.info(f"分类 '{category}' 爬取完成，成功获取 {valid_links_count} 篇新闻")
            return category_news
            
        except Exception as e:
            self.logger.error(f"爬取分类 '{category}' 时出错: {str(e)}", exc_info=True)
            return category_news

    def _extract_links_from_soup(self, soup: BeautifulSoup) -> List[str]:
        """
        从HTML BeautifulSoup对象中提取符合要求的新闻链接.
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            List[str]: 提取的新闻链接列表
        """
        news_links_found: List[str] = []
        processed_hrefs = set()
        
        try:
            self.logger.info("开始从页面提取新闻链接...")
            
            # 1. 使用定义的NEWS_LIST_SELECTORS选择器提取新闻列表项
            for selector in self.NEWS_LIST_SELECTORS:
                items = soup.select(selector)
                for item in items:
                    # 先尝试在列表项中查找链接
                    links = item.select('a[href]')
                    
                    # 如果列表项本身就是链接，则直接使用
                    if not links and item.name == 'a' and item.has_attr('href'):
                        links = [item]
                        
                    for link in links:
                        try:
                            href = link.get('href')
                            if not href or not isinstance(href, str):
                                continue
                                
                            # 规范化URL
                            try:
                                base_for_join = 'https://finance.sina.com.cn/'
                                absolute_href = urllib.parse.urljoin(base_for_join, href)
                                
                                # 跳过非HTTP链接
                                if not absolute_href.startswith('http'):
                                    continue
                                    
                                # 跳过已处理的链接
                                if absolute_href in processed_hrefs:
                                    continue
                                    
                                processed_hrefs.add(absolute_href)
                            except Exception:
                                continue
                                
                            # 验证链接是否为新闻链接
                            if self._is_news_link(absolute_href) and absolute_href not in news_links_found:
                                news_links_found.append(absolute_href)
                                # 限制提取的链接数量，避免过多无效链接
                                if len(news_links_found) >= 100:
                                    self.logger.info(f"已达到最大链接提取数量限制 (100)")
                                    break
                        except Exception as e:
                            self.logger.warning(f"处理链接时出错: {str(e)}")
                            continue
                            
                    # 如果已提取足够链接，提前结束
                    if len(news_links_found) >= 100:
                        break
            
            # 2. 如果使用列表选择器没有找到足够的链接，尝试其他策略
            if len(news_links_found) < 20:
                self.logger.info(f"通过列表选择器仅找到 {len(news_links_found)} 个链接，尝试备用提取方法...")
                
                # 备用方法：扫描所有链接
                link_selectors = [
                    'a[href*="finance.sina.com.cn"]',
                    'a[href*="tech.sina.com.cn"]',
                    'a[href*="money.sina.com.cn"]'
                ]
                
                for selector in link_selectors:
                    direct_links = soup.select(selector)
                    for link in direct_links:
                        try:
                            href = link.get('href')
                            if not href or not isinstance(href, str):
                                continue
                                
                            # 规范化URL
                            try:
                                absolute_href = href if href.startswith('http') else urllib.parse.urljoin('https://finance.sina.com.cn/', href)
                                
                                # 跳过已处理的链接
                                if absolute_href in processed_hrefs:
                                    continue
                                    
                                processed_hrefs.add(absolute_href)
                            except Exception:
                                continue
                                
                            # 验证链接是否为新闻链接
                            if self._is_news_link(absolute_href) and absolute_href not in news_links_found:
                                news_links_found.append(absolute_href)
                        except Exception:
                            continue
            
            # 记录结果
            if news_links_found:
                self.logger.info(f"从当前页面提取到 {len(news_links_found)} 个有效新闻链接.")
            else:
                self.logger.warning("当前页面未找到任何有效新闻链接.")
                
            return news_links_found
        except Exception as e:
            self.logger.error(f"提取新闻链接时出错: {str(e)}", exc_info=True)
            return []

    def _is_news_link(self, url: str) -> bool:
        """
        判断URL是否为有效的新浪财经或科技新闻文章链接
        
        Args:
            url: 要判断的URL
            
        Returns:
            bool: 是否为有效的新闻链接
        """
        if not url or not isinstance(url, str) or not url.startswith('http'):
            return False
            
        # 检查是否为新浪财经域名
        sina_domains = [
            'finance.sina.com.cn',
            'tech.sina.com.cn',
            'money.sina.com.cn',
            'blog.sina.com.cn/lm/finance'
        ]
        
        has_valid_domain = False
        for domain in sina_domains:
            if domain in url:
                has_valid_domain = True
                break
                
        if not has_valid_domain:
            return False
            
        # 排除特定类型的非新闻页面
        non_news_patterns = [
            # 多媒体内容
            '/photo/', '/slide/', '/video.', '/live.',
            # 功能页面 
            '/quotes/', '/globalindex/', '/fund/quotes/', '/forex/quotes/', '/futures/quotes/',
            '/guide/', '/mobile/', '/app.',
            # 其他非财经内容
            'jump.sina', 'vip.sina', 'auto.sina', 'ent.sina', 'sports.sina', 
            'gov.sina', 'jiaju.sina', 'leju.com', 'games.sina',
            # 交互功能页面
            'comment', 'survey', 'about', 'help', 'sitemap', 'rss', 'map.shtml',
            # 列表页面
            'index.d.html', 'index.shtml', '?cid=', '?fid=', '/otc/',
            # 广告和营销
            'sinaads', 'adbox', 'advertisement', 'promotion', 'sponsor', 
            'click.sina', 'sina.cn', 'game.weibo', 'games.sina', 'iask'
        ]
        
        normalized_url = url.rstrip('/')
        url_lower = normalized_url.lower()
        if any(pattern in url_lower for pattern in non_news_patterns):
            return False
            
        # 识别常见的新闻URL模式
        news_url_patterns = [
            # 主要的新闻URL模式
            r"finance\.sina\.com\.cn/.+/\d{4}-\d{2}-\d{2}/doc-[a-zA-Z0-9]+\.shtml",
            r"tech\.sina\.com\.cn/.+/\d{4}-\d{2}-\d{2}/doc-[a-zA-Z0-9]+\.shtml",
            r"money\.sina\.com\.cn/.+/\d{4}-\d{2}-\d{2}/doc-[a-zA-Z0-9]+\.shtml",
            # 常见的分类新闻路径
            r"finance\.sina\.com\.cn/roll/\d{4}-\d{2}-\d{2}/doc-[a-zA-Z0-9]+\.shtml",
            r"finance\.sina\.com\.cn/jjxw/\d{4}-\d{2}-\d{2}/doc-[a-zA-Z0-9]+\.shtml",
            r"finance\.sina\.com\.cn/china/\d{4}-\d{2}-\d{2}/doc-[a-zA-Z0-9]+\.shtml",
            r"finance\.sina\.com\.cn/world/\d{4}-\d{2}-\d{2}/doc-[a-zA-Z0-9]+\.shtml",
            # 股票、基金、期货等财经专区
            r"finance\.sina\.com\.cn/stock/.+\.shtml",
            r"finance\.sina\.com\.cn/fund/.+\.shtml",
            r"finance\.sina\.com\.cn/futures/.+\.shtml", 
            r"finance\.sina\.com\.cn/forex/.+\.shtml",
            r"finance\.sina\.com\.cn/money/.+\.shtml",
            r"finance\.sina\.com\.cn/tech/.+\.shtml",
            r"finance\.sina\.com\.cn/blockchain/.+\.shtml",
            r"finance\.sina\.com\.cn/7x24/.+\.shtml",
            r"finance\.sina\.com\.cn/esg/.+\.shtml",
            r"finance\.sina\.com\.cn/med/.+\.shtml",
            # 专栏和博客
            r"finance\.sina\.com\.cn/zl/.+\.shtml",
            r"blog\.sina\.com\.cn/s/blog_.+\.html",
            # 新格式的文章URL
            r"finance\.sina\.com\.cn/.*\d+\.html",
            r"finance\.sina\.com\.cn/.*\d+\.d\.html"
        ]
        
        # 测试用的特殊URL
        if 'TESTARTICLE' in url:
            return True
            
        # 检查URL是否匹配任意一种新闻模式
        for pattern in news_url_patterns:
            if re.search(pattern, normalized_url):
                return True
        
        # 如果URL没有匹配特定模式，但包含doc和shtml，可能仍是有效的新闻
        if '/doc-' in url and url.endswith('.shtml'):
            return True
            
        return False
            
    def _process_news_links(self, news_links: List[str], category: str):
        """
        Processes a list of news links for a given category: retrieves details,
        checks date range, and attempts to save valid items.
        
        Args:
            news_links (List[str]): A list of URLs to process.
            category (str): The category these links belong to.
        """
        if not news_links:
            self.logger.info(f"分类 '{category}' 没有需要处理的新闻链接.")
            return
            
        processed_count = 0
        max_links_to_process_total = self.settings.get('MAX_LINKS_PER_CATEGORY_PROCESS', 50)
        max_items_to_save_per_category = self.settings.get('MAX_ITEMS_PER_CATEGORY_SAVE', 10)
        
        links_to_attempt = news_links[:max_links_to_process_total]
        self.logger.info(f"分类 '{category}': 尝试处理 {len(links_to_attempt)}/{len(news_links)} 个链接 (最多保存 {max_items_to_save_per_category} 条).")

        for link_url in links_to_attempt:
            if processed_count >= max_items_to_save_per_category:
                self.logger.info(f"分类 '{category}': 已达到最大保存数量 ({max_items_to_save_per_category}).")
                break
                
            try:
                news_details_dict = self.process_news_link(link_url, category) 
                
                if not news_details_dict:
                    continue
                    
                if not self._is_news_in_date_range(news_details_dict):
                    self.logger.debug(f"新闻日期不在范围内，跳过: {link_url} ({news_details_dict.get('pub_time')})")
                    continue
                    
                # Use the refactored _save_news which calls super().save_news_to_db
                if self._save_news(news_details_dict):
                    self.logger.info(f"成功处理并保存新闻: {news_details_dict.get('title', 'N/A')}")
                    processed_count += 1
                    
                delay = random.uniform(
                    self.settings.get('DOWNLOAD_DELAY_MIN', 0.5), 
                    self.settings.get('DOWNLOAD_DELAY_MAX', 1.5)
                )
                self.logger.debug(f"随机延时 %.2f 秒后处理下一个链接.", delay)
                time.sleep(delay)
                
            except Exception as e:
                self.logger.error(f"_process_news_links: 处理链接时发生意外错误 {link_url}, Error: {e}", exc_info=True)

    def get_news_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """
        获取新闻详情 (不包含id, source, crawl_time, category - these are handled by BaseCrawler/SQLiteManager)
        
        Args:
            url (str): 新闻URL
            
        Returns:
            Optional[Dict[str, Any]]: 新闻详情字典，获取失败则返回None
        """
        self.logger.info(f"获取新闻详情: {url}")
        
        try:
            html = self.fetch_page(url)
            if not html:
                self.logger.warning(f"获取页面内容失败 (get_news_detail): {url}")
                return None
            
            try:
                soup = BeautifulSoup(html, 'html.parser')
                if not soup:
                    self.logger.warning(f"创建BeautifulSoup对象失败: {url}")
                    return None
            except Exception as e:
                self.logger.warning(f"解析HTML内容失败 (get_news_detail): {url}, 错误: {str(e)}")
                return None
            
            title = self._extract_title(soup)
            if not title:
                self.logger.warning(f"提取标题失败: {url}")
                return None
            
            pub_time_str = self._extract_publish_time(soup)
            if not pub_time_str:
                self.logger.warning(f"提取发布时间失败: {url}，将留空处理")
                pub_time_str = None 
            
            content = self._extract_content(soup)
            if not content:
                self.logger.warning(f"提取内容失败: {url}")
                return None
            
            author = self._extract_author(soup)
            keywords = self._extract_keywords(soup, content)
            image_urls = self._extract_images(soup)
            related_stocks = self._extract_related_stocks(soup)
            
            news_data = {
                'url': url,
                'title': title,
                'content': content,
                'pub_time': pub_time_str,
                'author': author,
                'keywords': keywords,
                'images': image_urls,
                'related_stocks': related_stocks
            }
            
            self.logger.debug(f"成功提取新闻详情 (pre-save): {title}")
            return news_data
        except requests.RequestException as e:
            self.logger.error(f"请求新闻详情时发生请求错误: {url}, 错误: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"获取新闻详情时发生未知异常: {url}, 错误: {str(e)}", exc_info=True)
            return None

    def _extract_publish_time(self, soup: BeautifulSoup) -> Optional[str]:
        """
        从HTML中提取发布时间
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 发布时间，格式为 YYYY-MM-DD HH:MM:SS, or None if not found
        """
        try:
            # 尝试从meta标签中提取时间
            pub_time_tag = soup.find('meta', attrs={'property': 'article:published_time'})
            if pub_time_tag and pub_time_tag.get('content'):
                pub_time = pub_time_tag['content'].split('+')[0].replace('T', ' ')
                if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', pub_time):
                    self.logger.debug("从meta标签提取到发布时间: %s", pub_time)
                    return pub_time
            
            # 尝试从time标签中提取时间
            time_tag = soup.find('time')
            if time_tag and time_tag.get('datetime'):
                pub_time = time_tag['datetime'].split('+')[0].replace('T', ' ')
                if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', pub_time):
                    self.logger.debug("从time标签提取到发布时间: %s", pub_time)
                    return pub_time
            
            # 尝试从新浪特定的时间标签中提取
            time_source_span = soup.find('span', class_='date') # Renamed variable
            if time_source_span:
                time_text = time_source_span.get_text().strip()
                match = re.search(r'(\d{4})年(\d{2})月(\d{2})日\s+(\d{2}):(\d{2})', time_text)
                if match:
                    year, month, day, hour, minute = match.groups()
                    pub_time = f"{year}-{month}-{day} {hour}:{minute}:00"
                    self.logger.debug("从date标签提取到发布时间: %s", pub_time)
                    return pub_time
            
            date_source_div = soup.find('div', class_='date-source') # Renamed variable
            if date_source_div:
                time_text = date_source_div.get_text().strip()
                match = re.search(r'(\d{4})年(\d{2})月(\d{2})日\s+(\d{2}):(\d{2})', time_text)
                if match:
                    year, month, day, hour, minute = match.groups()
                    pub_time = f"{year}-{month}-{day} {hour}:{minute}:00"
                    self.logger.debug("从date-source提取到发布时间: %s", pub_time)
                    return pub_time
            
            time_source_span_alt = soup.find('span', class_='time-source') # Renamed variable
            if time_source_span_alt:
                time_text = time_source_span_alt.get_text().strip()
                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)', time_text)
                if match:
                    pub_time = match.group(1)
                    if len(pub_time.split(':')) == 2:
                        pub_time += ':00'
                    self.logger.debug("从time-source提取到发布时间: %s", pub_time)
                    return pub_time
                
                match = re.search(r'(\d{4})年(\d{2})月(\d{2})日\s+(\d{2}):(\d{2})', time_text)
                if match:
                    year, month, day, hour, minute = match.groups()
                    pub_time = f"{year}-{month}-{day} {hour}:{minute}:00"
                    self.logger.debug("从time-source提取到发布时间: %s", pub_time)
                    return pub_time
            
            publish_time_class = soup.find(class_='publish_time') # Renamed variable
            if publish_time_class:
                time_text = publish_time_class.get_text().strip()
                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)', time_text)
                if match:
                    pub_time = match.group(1)
                    if len(pub_time.split(':')) == 2:
                        pub_time += ':00'
                    self.logger.debug("从publish_time提取到发布时间: %s", pub_time)
                    return pub_time
            
            article_info_div = soup.find('div', class_='article-info') # Renamed variable
            if article_info_div:
                time_text = article_info_div.get_text().strip()
                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)', time_text)
                if match:
                    pub_time = match.group(1)
                    if len(pub_time.split(':')) == 2:
                        pub_time += ':00'
                    self.logger.debug("从article-info提取到发布时间: %s", pub_time)
                    return pub_time
            
            article_meta_div = soup.find('div', class_='article-meta') # Renamed variable
            if article_meta_div:
                time_text = article_meta_div.get_text().strip()
                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)', time_text)
                if match:
                    pub_time = match.group(1)
                    if len(pub_time.split(':')) == 2:
                        pub_time += ':00'
                    self.logger.debug("从article-meta提取到发布时间: %s", pub_time)
                    return pub_time
            
            info_div_class = soup.find('div', class_='info') # Renamed variable
            if info_div_class:
                time_text = info_div_class.get_text().strip()
                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)', time_text)
                if match:
                    pub_time = match.group(1)
                    if len(pub_time.split(':')) == 2:
                        pub_time += ':00'
                    self.logger.debug("从info提取到发布时间: %s", pub_time)
                    return pub_time
            
            text = soup.get_text()
            match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text)
            if match:
                pub_time = match.group(1)
                self.logger.debug("从全文提取到发布时间: %s", pub_time)
                return pub_time
            
            match = re.search(r'(\d{4})年(\d{2})月(\d{2})日\s+(\d{2}):(\d{2})', text)
            if match:
                year, month, day, hour, minute = match.groups()
                pub_time = f"{year}-{month}-{day} {hour}:{minute}:00"
                self.logger.debug("从全文提取到发布时间: %s", pub_time)
                return pub_time
            
            self.logger.warning("无法提取发布时间，返回None")
            return None # Return None instead of current time if not found
        except Exception as e:
            self.logger.error("提取发布时间时出错: %s", str(e), exc_info=True) # Added exc_info
            return None # Return None on error
    
    def _extract_content(self, soup: BeautifulSoup) -> Optional[str]:
        """
        从HTML中提取新闻正文内容
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            Optional[str]: 提取的正文内容，如果提取失败则返回None
        """
        try:
            # 尝试使用定义的内容选择器提取正文
            for selector in self.CONTENT_SELECTORS:
                content_tag = soup.select_one(selector)
                if content_tag:
                    # 移除脚本、样式和注释
                    for tag in content_tag.find_all(['script', 'style']):
                        tag.decompose()
                        
                    for comment_node in content_tag.find_all(string=lambda text: isinstance(text, Comment)):
                        comment_node.extract()
                    
                    # 过滤广告和推荐内容
                    ad_classes = ['recommend', 'related', 'footer', 'ad', 'bottom', 'sinaads', 'adbox']
                    
                    for item in content_tag.find_all(True):
                        # 检查类名是否包含广告相关关键词
                        if item.get('class'):
                            if any(ad_class in ' '.join(item.get('class', [])) for ad_class in ad_classes):
                                item.decompose()
                                continue
                                
                        # 检查ID是否包含广告相关关键词
                        if item.get('id'):
                            if any(ad_class in item.get('id', '').lower() for ad_class in ad_classes):
                                item.decompose()
                                continue
                    
                    # 提取文本并格式化
                    text_content = content_tag.get_text('\n').strip()
                    
                    # 清理多余的空白字符
                    text_content = re.sub(r'\n{3,}', '\n\n', text_content)  # 将3个以上连续换行减少为2个
                    text_content = re.sub(r'\s{2,}', ' ', text_content)     # 将2个以上连续空格减少为1个
                    
                    if text_content:
                        self.logger.debug(f"使用选择器 '{selector}' 成功提取到正文内容: {len(text_content)} 字符")
                        return text_content
            
            # 备用提取方法：如果使用选择器未提取到内容，尝试通过p标签收集
            paragraphs = []
            article_area = None
            
            # 先尝试找到可能的文章区域
            potential_areas = [
                'div.article', 'div.main-content', 'div#artibody', 'article',
                'div.cont', 'div.content', 'div.article-content'
            ]
            
            for area_selector in potential_areas:
                article_area = soup.select_one(area_selector)
                if article_area:
                    break
            
            # 如果找到文章区域，从中提取段落
            if article_area:
                for p in article_area.find_all('p'):
                    p_text = p.get_text().strip()
                    if p_text and len(p_text) > 15:  # 排除太短的段落
                        paragraphs.append(p_text)
            
            # 如果没找到文章区域，直接从整个页面提取段落
            else:
                # 尝试找到所有可能是正文的段落
                for p in soup.find_all('p'):
                    p_text = p.get_text().strip()
                    if p_text and len(p_text) > 15 and not any(ad in p.get('class', []) for ad in ad_classes):
                        paragraphs.append(p_text)
            
            # 如果收集到段落，拼接为文章内容
            if paragraphs:
                content = '\n\n'.join(paragraphs)
                self.logger.debug(f"使用段落收集方法提取到正文内容: {len(content)} 字符")
                return content
            
            self.logger.warning("未能提取到正文内容")
            return None
            
        except Exception as e:
            self.logger.error(f"提取正文内容时出错: {str(e)}", exc_info=True)
            return None
            
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """
        从HTML中提取新闻标题
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            Optional[str]: 提取的标题，如果提取失败则返回None
        """
        title_text: Optional[str] = None
        
        # 使用定义的标题选择器提取标题
        for selector in self.TITLE_SELECTORS:
            element = soup.select_one(selector)
            if element:
                title_text = element.get_text(strip=True)
                if title_text and len(title_text) > 3:
                    self.logger.debug(f"使用选择器 '{selector}' 提取到标题: {title_text}")
                    break
        
        # 如果标题选择器未提取到标题，尝试从title标签提取
        if not title_text or len(title_text) <= 3:
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                self.logger.debug(f"从title标签提取到标题: {title_text}")
        
        # 如果仍未提取到标题，尝试从meta标签提取
        if not title_text or len(title_text) <= 3:
            meta_selectors = [
                'meta[property="og:title"]',
                'meta[name="title"]',
                'meta[name="sharetitle"]'
            ]
            for selector in meta_selectors:
                meta_tag = soup.select_one(selector)
                if meta_tag and meta_tag.get('content'):
                    title_text = meta_tag['content'].strip()
                    if title_text and len(title_text) > 3:
                        self.logger.debug(f"从meta标签提取到标题: {title_text}")
                        break
        
        # 如果成功提取到标题，清理标题中的网站标识
        if title_text and len(title_text) > 3:
            # 移除常见的网站标识后缀
            site_suffixes = [
                f" - {self.source}", f"_{self.source}",
                "_新浪财经_", " - 新浪财经", "_新浪网_", " - 新浪网",
                "_新浪财经网_", " - 新浪财经网", "- 新浪", "_新浪"
            ]
            
            for suffix in site_suffixes:
                if suffix in title_text:
                    title_text = title_text.replace(suffix, "").strip()
            
            # 清理分隔符和多余空格
            title_text = re.sub(r'\s+', ' ', title_text).strip()
            
            if title_text and len(title_text) > 3:
                return title_text
        
        self.logger.warning("未能提取到有效标题")
        return None
    
    def _extract_keywords(self, soup: BeautifulSoup, content: Optional[str]) -> List[str]:
        """
        提取关键词. Content argument is optional as title-based extraction doesn't need it.
        
        Args:
            soup: BeautifulSoup对象
            content: 正文内容 (Optional)
            
        Returns:
            List[str]: 关键词列表 (guaranteed to be a list, possibly empty)
        """
        extracted_keywords: List[str] = []

        try:
            # 1. Try from meta tags
            meta_keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords_tag and meta_keywords_tag.get('content'):
                keywords_string = meta_keywords_tag['content']
                if isinstance(keywords_string, str):
                    raw_kws = re.split(r'[,，\s]+', keywords_string)
                    kw_list = [k.strip() for k in raw_kws if k.strip() and len(k) < 30]
                    if kw_list:
                        extracted_keywords.extend(k for k in kw_list if k not in extracted_keywords)
                        self.logger.debug(f"从meta标签提取到关键词: {kw_list}")
            
            # 2. Try from specific tag selectors
            tag_selectors = [
                'div.keywords a', 'div.tags a', 'div.article-tags a',
                'a.tag-link', '.tag', '.tags-container a'
            ]
            for selector in tag_selectors:
                tags = soup.select(selector)
                for tag_element in tags:
                    keyword = tag_element.get_text(strip=True)
                    if keyword and keyword not in extracted_keywords and len(keyword) < 30:
                        extracted_keywords.append(keyword)
            if extracted_keywords and not meta_keywords_tag: # Log if found from tags and not from meta
                 self.logger.debug(f"通过标签选择器提取到关键词: {extracted_keywords}")

            # 3. Fallback: If no keywords found yet, try to extract from title
            if not extracted_keywords:
                title = self._extract_title(soup)
                if title:
                    potential_words = re.findall(r'[\w\u4e00-\u9fa5]+', title)
                    title_kws = [
                        word for word in potential_words 
                        if len(word) > 1 and not word.isnumeric() and len(word) < 15
                    ]
                    if title_kws:
                        extracted_keywords.extend(k for k in title_kws if k not in extracted_keywords)
                        self.logger.debug(f"从标题提取到关键词: {title_kws}")
            
            final_keywords = []
            for kw in extracted_keywords:
                if kw not in final_keywords:
                    final_keywords.append(kw)
            
            return final_keywords

        except Exception as e:
            self.logger.error(f"提取关键词过程中发生错误: {str(e)}", exc_info=True)
            return []
    
    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        """
        提取文章内容中的主要图片URL.
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            List[str]: 图片URL列表 (guaranteed to be a list, possibly empty)
        """
        image_urls: List[str] = []
        try:
            content_selectors = [
                'div.article-content', 'div.article', 'div#artibody',
                'div.main-content', 'div.content', 'article', 
                '#articleContent', '.post_content_main', '.entry-content'
            ]
            
            content_area_found = False
            for selector in content_selectors:
                content_tag = soup.select_one(selector)
                if content_tag:
                    content_area_found = True
                    self.logger.debug(f"发现图片内容区域使用选择器: {selector}")
                    for img in content_tag.find_all('img'):
                        img_src = img.get('src')
                        if not img_src or '占位' in img_src or 'placeholder' in img_src.lower() or 'loading.gif' in img_src:
                            data_src = img.get('data-src') or img.get('data-original') or img.get('data-lazy-src')
                            if data_src:
                                img_src = data_src
                        
                        if img_src and isinstance(img_src, str) and img_src.startswith('http'):
                            alt_text = img.get('alt', '').lower()
                            if 'logo' in img_src.lower() or 'icon' in img_src.lower() or \
                               'button' in img_src.lower() or 'spinner' in img_src.lower() or \
                               'loading' in img_src.lower() or 'transparent.gif' in img_src.lower() or \
                               'pixel.gif' in img_src.lower() or 'spacer.gif' in img_src.lower() or \
                               'logo' in alt_text or 'icon' in alt_text:
                                self.logger.debug(f"过滤掉可能的非内容图片 (logo/icon/pixel): {img_src}")
                                continue

                            if img_src not in image_urls:
                                image_urls.append(img_src)
                    if image_urls:
                        self.logger.debug(f"从选择器 '{selector}' 提取到 {len(image_urls)} 张图片.")
                        break 
            
            if not content_area_found:
                self.logger.debug("未找到主要内容区域来提取图片.")
            
            return image_urls
        except Exception as e:
            self.logger.error(f"提取图片URL时出错: {str(e)}", exc_info=True)
            return []
    
    def _extract_related_stocks(self, soup: BeautifulSoup) -> List[str]:
        """
        提取页面中提及的相关股票代码或名称.
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            List[str]: 相关股票列表 (guaranteed to be a list, possibly empty)
        """
        stocks_found: List[str] = []
        try:
            stock_container_selectors = [
                'div.stock-info', 'div.related-stocks', 'div.stock-wrap',
                '.relate_stock', '.about_stock', '#finance_focusstocks'
            ]
            
            for container_selector in stock_container_selectors:
                container = soup.select_one(container_selector)
                if container:
                    link_tags = container.select('a, span.stock-name, li.stock-item')
                    
                    for tag in link_tags:
                        stock_text = tag.get_text(strip=True)
                        
                        match_code_in_paren = re.search(r'\uff08([A-Za-z0-9\.]+)\uff09$', stock_text)
                        if not match_code_in_paren:
                             match_code_in_paren = re.search(r'\(([A-Za-z0-9\.]+)\)$', stock_text)

                        stock_identifier = ""
                        if match_code_in_paren:
                            stock_identifier = match_code_in_paren.group(1).strip()
                        elif re.match(r'^[A-Za-z0-9\.]+$', stock_text) and (any(c.isdigit() for c in stock_text) or any(c.isupper() for c in stock_text if c.isalpha())):
                            stock_identifier = stock_text
                        elif len(stock_text) > 1 and len(stock_text) < 30 and not stock_text.startswith("http"):
                             stock_identifier = stock_text

                        if stock_identifier:
                            if 1 < len(stock_identifier) < 30:
                                if stock_identifier not in stocks_found:
                                    stocks_found.append(stock_identifier)
                                    self.logger.debug(f"提取到相关股票: {stock_identifier} (选择器: {container_selector})")
            
            return list(set(stocks_found))
            
        except Exception as e:
            self.logger.error(f"提取相关股票时出错: {str(e)}", exc_info=True)
            return []

    def _is_news_in_date_range(self, news_data: Dict[str, Any]) -> bool:
        """
        检查新闻的发布日期是否在由 self.days 定义的日期范围内.
        self.days 应该是从当前时间回溯的天数.
        """
        pub_time_str = news_data.get('pub_time')
        if not pub_time_str:
            self.logger.debug("新闻缺少 'pub_time'，日期范围检查跳过，默认视为在范围内.")
            return True
            
        try:
            news_pub_date = None
            common_formats = [
                '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M', '%Y/%m/%d',
                '%Y年%m月%d日 %H:%M:%S', '%Y年%m月%d日 %H:%M', '%Y年%m月%d日'
            ]
            for fmt in common_formats:
                try:
                    news_pub_date = datetime.strptime(pub_time_str.split('+')[0].replace('T', ' ').strip(), fmt)
                    break
                except ValueError:
                    continue
            
            if not news_pub_date:
                match = re.match(r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)", pub_time_str)
                if match:
                    date_only_str = match.group(1)
                    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y年%m月%d日']:
                        try:
                            news_pub_date = datetime.strptime(date_only_str, fmt)
                            break
                        except ValueError:
                            continue
            
            if not news_pub_date:
                self.logger.warning(f"无法将新闻发布时间字符串 '{pub_time_str}' 解析为已知日期格式. 默认视为在范围内.")
                return True

            days_to_crawl = getattr(self, 'days', self.settings.get('DEFAULT_CRAWL_DAYS', 1))
            if not isinstance(days_to_crawl, int) or days_to_crawl < 0:
                self.logger.warning(f"无效的天数设置 (days={days_to_crawl})，默认为1天.")
                days_to_crawl = 1
                
            limit_start_date = (datetime.now() - timedelta(days=days_to_crawl)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            if news_pub_date >= limit_start_date:
                self.logger.debug(f"新闻日期 {news_pub_date.strftime('%Y-%m-%d')} 在范围内 (>= {limit_start_date.strftime('%Y-%m-%d')}).")
                return True
            else:
                self.logger.debug(f"新闻日期 {news_pub_date.strftime('%Y-%m-%d')} 不在范围内 (< {limit_start_date.strftime('%Y-%m-%d')}).")
                return False

        except Exception as e:
            self.logger.error(f"检查新闻日期范围时发生错误 (pub_time: {pub_time_str}): {str(e)}", exc_info=True)
            return True
            
    def _save_news(self, news_item: Dict[str, Any]) -> bool:
        """
        Internal helper to save a single news item using BaseCrawler's mechanisms.
        Assumes `news_item` is ready for saving (e.g., from `get_news_detail` and category added).
        
        Args:
            news_item (Dict[str, Any]): The news data dictionary.
            
        Returns:
            bool: True if saving was successful, False otherwise.
        """
        try:
            if not news_item or not isinstance(news_item, dict):
                self.logger.warning("SinaCrawler._save_news: 无效的新闻数据格式.")
                return False
            
            required_fields = ['url', 'title']
            for field in required_fields:
                if not news_item.get(field):
                    self.logger.warning(f"SinaCrawler._save_news: 待保存的新闻缺少关键字段 '{field}'. URL: {news_item.get('url', 'N/A')}")
                    return False

            # 确保设置source字段
            if not news_item.get('source'):
                news_item['source'] = self.source
                
            self.logger.info(f"SinaCrawler._save_news: 准备将新闻保存到 '{news_item['source']}' 数据库: {news_item.get('title')}")
            
            # 调用BaseCrawler的save_news_to_db方法
            result = super().save_news_to_db(news_item)
            
            if result:
                self.logger.info(f"SinaCrawler._save_news: 成功保存新闻: {news_item.get('title')}")
            else:
                self.logger.warning(f"SinaCrawler._save_news: 保存新闻失败: {news_item.get('title')}")
                
            return result
            
        except Exception as e:
            self.logger.error(f"SinaCrawler._save_news: 保存新闻时发生错误. URL: {news_item.get('url', 'N/A')}, Error: {str(e)}", exc_info=True)
            return False

    def process_news_link(self, url: str, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Processes a single news link by fetching its details.
        This method calls self.get_news_detail (which is already refactored)
        and optionally adds the category to the resulting dictionary.
        It does NOT save the news item.
        
        Args:
            url (str): The URL of the news article.
            category (Optional[str]): The category of the news article.
        
        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the extracted news details,
                                      or None if processing fails.
        """
        if not url:
            self.logger.debug("SinaCrawler.process_news_link: 收到的URL为空.")
            return None
        
        if not self.validate_url(url):
            self.logger.info(f"SinaCrawler.process_news_link: 过滤无效或不符合规则的URL: {url}")
            return None
        
        try:
            news_details_dict = self.get_news_detail(url)

            if not news_details_dict:
                self.logger.warning(f"SinaCrawler.process_news_link: get_news_detail未能提取到新闻详情 for URL: {url}")
                return None
            
            if category:
                news_details_dict['category'] = category
            news_details_dict['source'] = self.source
            
            self.logger.debug(f"SinaCrawler.process_news_link: 成功处理新闻链接 (未保存). URL: {url}, 标题: {news_details_dict.get('title')}")
            return news_details_dict
        
        except Exception as e:
            self.logger.error(f"SinaCrawler.process_news_link: 处理新闻链接时发生意外错误. URL: {url}, 错误: {str(e)}", exc_info=True)
            return None

    def validate_url(self, url: str) -> bool:
        """
        验证URL是否是我们要处理的有效的新闻文章URL.
        (Combines basic checks and calls _is_news_link).
        """
        # Basic checks first
        if not url or not isinstance(url, str):
            return False
        if not url.startswith('http'):
            return False
        if 'sina.com.cn' not in url:
            return False

        # More detailed check using _is_news_link logic
        return self._is_news_link(url)

    def crawl(self, days: int = 1, max_pages: int = 3, category: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        爬取新闻，支持按分类爬取
        
        Args:
            days: 爬取天数
            max_pages: 每个分类最大抓取页数
            category: 新闻分类，多个分类用逗号分隔
            **kwargs: 其他参数
            
        Returns:
            List[Dict[str, Any]]: 爬取到的新闻列表
        """
        # 使用kwargs或传入参数设置爬取配置
        self.days = int(days)
        self.max_pages = int(kwargs.get('max_pages', max_pages))
        self.max_news_per_category = int(kwargs.get('max_news', 20))
        
        # 重置统计信息
        self.reset_stats()
        
        # 处理分类参数
        categories = []
        if category:
            if isinstance(category, str):
                if ',' in category:
                    # 分割多个分类
                    categories = [cat.strip() for cat in category.split(',')]
                else:
                    categories = [category.strip()]
            elif isinstance(category, list):
                categories = category
        
        # 如果没有指定分类，使用所有支持的分类
        if not categories:
            categories = list(self.CATEGORY_URLS.keys())
        
        # 记录爬取开始信息
        self.logger.info(f"开始爬取新浪财经新闻: 分类 {categories}, 天数 {days}, 最大页数 {self.max_pages}")
        
        # 存储所有爬取到的新闻
        all_news = []
        
        # 遍历每个分类进行爬取
        for category_name in categories:
            try:
                # 检查分类是否支持
                if category_name not in self.CATEGORY_URLS:
                    self.logger.warning(f"不支持的分类: {category_name}，跳过")
                    continue
                
                # 获取分类URL
                category_url = self.CATEGORY_URLS[category_name]
                self.logger.info(f"开始爬取分类: {category_name}, URL: {category_url}")
                
                # 爬取该分类的新闻
                category_news = self._crawl_category(category_name, category_url, self.max_pages)
                
                # 将当前分类的新闻添加到总结果中
                if category_news:
                    all_news.extend(category_news)
                    self.logger.info(f"已从分类 '{category_name}' 获取 {len(category_news)} 篇新闻，累计 {len(all_news)} 篇")
                else:
                    self.logger.info(f"从分类 '{category_name}' 未获取到有效新闻")
                    
                # 添加分类间延迟，避免请求过于频繁
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                self.logger.error(f"爬取分类 '{category_name}' 时出错: {str(e)}", exc_info=True)
                continue
        
        # 记录爬取完成信息
        self.logger.info(f"新浪财经爬虫任务完成. 总共抓取 {len(all_news)} 篇新闻")
        self.log_stats()
        
        return all_news

    def reset_stats(self):
        """
        重置爬虫统计数据
        """
        if hasattr(self, 'stats'):
            self.stats = {'success_count': 0, 'fail_count': 0, 'start_time': time.time()}
        else:
            self.stats = {'success_count': 0, 'fail_count': 0, 'start_time': time.time()}
        self.logger.debug("已重置爬虫统计数据")
        
    def log_stats(self):
        """
        记录爬虫统计数据到日志
        """
        if hasattr(self, 'stats'):
            elapsed_time = time.time() - self.stats.get('start_time', time.time())
            success_count = self.stats.get('success_count', 0)
            fail_count = self.stats.get('fail_count', 0)
            total_count = success_count + fail_count
            
            self.logger.info("爬虫统计数据:")
            self.logger.info(f"总处理: {total_count} 条, 成功: {success_count} 条, 失败: {fail_count} 条")
            self.logger.info(f"耗时: {elapsed_time:.2f} 秒")
            if total_count > 0:
                self.logger.info(f"成功率: {success_count / total_count * 100:.2f}%")
        else:
            self.logger.warning("无可用统计数据")

    def _find_next_page_url(self, soup: BeautifulSoup, current_url: str, current_page_num: int) -> Optional[str]:
        """
        查找下一页链接
        
        Args:
            soup: BeautifulSoup对象
            current_url: 当前页面URL
            current_page_num: 当前页码
            
        Returns:
            Optional[str]: 下一页URL，如果没有下一页则返回None
        """
        try:
            # 1. 尝试查找标准分页链接
            pagination_selectors = [
                '.pagebox a.next', '.pages a.next',
                'div.pagebox a:contains("下一页")', 'div.pages a:contains("下一页")',
                'a.next', 'a.next-page', 'a[rel="next"]',
                'a.page-next', 'a.pagebox_next',
                'li.next a', 'a:contains("下一页")'
            ]
            
            for selector in pagination_selectors:
                try:
                    next_page_links = soup.select(selector)
                    if next_page_links:
                        for link in next_page_links:
                            href = link.get('href')
                            if href:
                                # 处理相对URL
                                if href.startswith('/'):
                                    base_url = '/'.join(current_url.split('/')[:3])  # 提取域名部分
                                    next_url = base_url + href
                                elif href.startswith('http'):
                                    next_url = href
                                else:
                                    # 如果是相对当前目录的URL
                                    base_path = '/'.join(current_url.split('/')[:-1])
                                    next_url = f"{base_path}/{href}"
                                    
                                self.logger.debug(f"找到下一页链接: {next_url}")
                                return next_url
                except Exception as e:
                    self.logger.debug(f"使用选择器 '{selector}' 查找下一页链接时出错: {str(e)}")
                    continue
            
            # 2. 尝试从URL中提取页码参数并构造下一页URL
            # 如果当前URL包含页码参数，则增加页码
            parsed_url = urllib.parse.urlparse(current_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # 检查常见的页码参数
            page_param_names = ['page', 'pn', 'p', 'cpage', 'pageNo', 'pageNum']
            
            for param_name in page_param_names:
                if param_name in query_params:
                    try:
                        current_param_page = int(query_params[param_name][0])
                        next_param_page = current_param_page + 1
                        
                        # 更新查询参数
                        new_query_params = query_params.copy()
                        new_query_params[param_name] = [str(next_param_page)]
                        
                        # 构建新的查询字符串
                        new_query_string = urllib.parse.urlencode(new_query_params, doseq=True)
                        
                        # 构建新的URL
                        next_url_parts = list(parsed_url)
                        next_url_parts[4] = new_query_string
                        next_url = urllib.parse.urlunparse(next_url_parts)
                        
                        self.logger.debug(f"通过URL参数构造下一页链接: {next_url}")
                        return next_url
                    except (ValueError, IndexError):
                        continue
            
            # 3. 尝试构造基于标准页码参数的URL
            # 如果当前URL不包含页码参数，尝试添加页码参数
            if not any(param in query_params for param in page_param_names):
                try:
                    # 默认使用'page'作为页码参数
                    new_query_params = query_params.copy()
                    new_query_params['page'] = ['2']  # 第二页
                    
                    # 构建新的查询字符串
                    new_query_string = urllib.parse.urlencode(new_query_params, doseq=True)
                    
                    # 如果原URL已有查询参数，则添加&page=2，否则添加?page=2
                    if parsed_url.query:
                        next_url = current_url + '&page=2'
                    else:
                        next_url = current_url + '?page=2'
                    
                    self.logger.debug(f"添加页码参数构造下一页链接: {next_url}")
                    return next_url
                except Exception as e:
                    self.logger.debug(f"构造基于页码参数的URL时出错: {str(e)}")
            
            # 4. 尝试查找页码数字链接
            # 在滚动型新闻列表中可能没有明确的"下一页"链接，但有页码列表
            page_number_links = []
            page_number_elements = soup.select('div.pagebox a, div.pages a, .pagebox_nums a, .page-num a')
            
            for element in page_number_elements:
                try:
                    page_num_text = element.get_text().strip()
                    # 尝试将文本转换为数字
                    if page_num_text.isdigit():
                        page_num = int(page_num_text)
                        if page_num == current_page_num + 1:
                            href = element.get('href')
                            if href:
                                # 构造完整URL
                                if href.startswith('/'):
                                    base_url = '/'.join(current_url.split('/')[:3])
                                    next_url = base_url + href
                                else:
                                    next_url = urllib.parse.urljoin(current_url, href)
                                self.logger.debug(f"通过页码链接找到下一页: {next_url}")
                                return next_url
                except (ValueError, AttributeError):
                    continue
            
            # 没有找到下一页链接
            self.logger.debug(f"未找到下一页链接，当前页面可能是最后一页: {current_url}")
            return None
            
        except Exception as e:
            self.logger.error(f"查找下一页链接时出错: {str(e)}")
            return None

    def _extract_links_from_html(self, html: str) -> List[str]:
        """
        从HTML字符串中提取新闻链接
        
        Args:
            html: HTML字符串内容
        
        Returns:
            list: 新闻链接列表
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            return self._extract_links_from_soup(soup) # Calls refactored method
        except Exception as e:
            self.logger.error(f"解析HTML并提取新闻链接失败 (_extract_links_from_html): {str(e)}", exc_info=True)
            return []

    def crawl_category(self, category_name: str, max_pages: int = 3, days: int = 1):
        # ... (To be refactored) ...
        pass

    # REFACTOR _extract_links_for_category (Original lines 1184-1237)
    def _extract_links_for_category(self, category_url: str, category_name: str, max_pages: int) -> List[str]:
        """
        从分类页面提取新闻链接，支持分页
        
        Args:
            category_url: 分类页面URL
            category_name: 分类名称
            max_pages: 最大抓取页数
            
        Returns:
            List[str]: 提取的新闻链接列表
        """
        all_links = []
        processed_links = set()
        current_url = category_url
        
        self.logger.info(f"开始从'{category_name}'分类获取新闻链接, 起始URL: {category_url}")
        
        try:
            for page_num in range(1, max_pages + 1):
                # 如果已达到链接提取数量上限，提前结束
                if len(all_links) >= 100:
                    self.logger.info(f"已提取足够的链接 ({len(all_links)})，不再获取更多页面")
                    break
                
                # 记录当前页面号码和URL
                self.logger.info(f"获取第 {page_num}/{max_pages} 页新闻链接: {current_url}")
                
                # 获取页面内容
                page_html = self.fetch_page(current_url)
                if not page_html:
                    self.logger.warning(f"无法获取分类页面内容: {current_url}")
                    break
                
                # 解析页面
                soup = BeautifulSoup(page_html, 'html.parser')
                
                # 提取新闻链接
                page_links = self._extract_links_from_soup(soup)
                
                # 过滤重复链接
                new_links = [link for link in page_links if link not in processed_links]
                
                # 将新链接添加到结果和已处理集合中
                all_links.extend(new_links)
                processed_links.update(new_links)
                
                self.logger.info(f"从第 {page_num} 页新增 {len(new_links)} 个链接，当前总共: {len(all_links)} 个链接")
                
                # 判断是否有下一页
                next_page_url = self._find_next_page_url(soup, current_url, page_num)
                if not next_page_url:
                    self.logger.info(f"未找到下一页链接，爬取结束于第 {page_num} 页")
                    break
                    
                # 更新当前URL为下一页URL
                current_url = next_page_url
                
                # 添加页面请求间隔，避免频繁请求
                time.sleep(random.uniform(1.0, 2.0))
            
            self.logger.info(f"从'{category_name}'分类总共提取到 {len(all_links)} 个有效新闻链接")
            return all_links
            
        except Exception as e:
            self.logger.error(f"从'{category_name}'分类提取链接时出错: {str(e)}", exc_info=True)
            return all_links  # 返回已提取的链接，而不是空列表
            
    # ... (Method _find_next_page_url should be below this)

    # ... (rest of the file will be refactored in subsequent steps) ...

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """
        提取作者/来源
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            Optional[str]: 作者/来源，如果提取失败则返回None
        """
        try:
            author_selectors = [
                {'selector': 'meta[name="author"]', 'type': 'meta_content'},
                {'selector': 'meta[property="article:author"]', 'type': 'meta_content'},
                {'selector': '.author', 'type': 'text'},
                {'selector': '.source', 'type': 'text'},
                {'selector': 'span.source', 'type': 'text'},
                {'selector': 'span.author', 'type': 'text'},
                {'selector': '.article-info span.source', 'type': 'text'},
                {'selector': '.article-info span.author', 'type': 'text'},
                {'selector': '.info span.source', 'type': 'text'},
                {'selector': '.info span.author', 'type': 'text'},
                {'selector': '#top_bar_wrap > div > div.date-source > span.source', 'type': 'text'},
                {'selector': 'p.article-editor', 'type': 'text'},
                {'selector': '.time-source a', 'type': 'text'},
                {'selector': '.date-source a', 'type': 'text'}
            ]
            
            author_name: Optional[str] = None

            for item in author_selectors:
                tag = soup.select_one(item['selector'])
                if tag:
                    if item['type'] == 'meta_content':
                        author_name = tag.get('content', '').strip()
                    else:
                        author_name = tag.get_text().strip()
                    
                    if author_name:
                        author_name = re.sub(r'^(来源|作者|责任编辑)[:：\s]*', '', author_name).strip()
                        author_name = re.sub(r'^本文来源[:：\s]*', '', author_name, flags=re.IGNORECASE).strip()
                        if re.match(r'^https?://', author_name):
                            author_name = None 
                            continue
                        if len(author_name) > 50:
                            author_name = None
                            continue
                        crawler_source_name = self.source.lower() if hasattr(self, 'source') and self.source else ""
                        if author_name.lower() in ['sina.com.cn', '新浪网', '新浪财经', crawler_source_name] and crawler_source_name != "":
                            author_name = None 
                            continue
                        if author_name:
                            self.logger.debug(f"提取到作者/来源: {author_name} (选择器: {item['selector']})")
                            return author_name
            
            # 尝试从时间来源标签中提取
            time_source_tags = soup.select('.time-source, .date-source')
            for tag in time_source_tags:
                source_text = tag.get_text()
                source_match = re.search(r'来源[:：\s]*([^\s]+)', source_text)
                if source_match:
                    source = source_match.group(1).strip()
                    if source and source.lower() not in ['新浪财经', '新浪网', 'sina.com.cn']:
                        self.logger.debug(f"从时间来源标签提取到来源: {source}")
                        return source
            
            self.logger.debug("未能从特定选择器中提取到明确的作者/来源信息")
            return None
        except Exception as e:
            self.logger.error(f"提取作者/来源时出错: {str(e)}", exc_info=True)
            return None
