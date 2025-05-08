#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
新浪财经爬虫模块
"""

import re
import os
import time
import json
# import sqlite3 # REMOVED
# import logging # REMOVED
import random
# import hashlib # REMOVED
import traceback
import requests # Keep for now
from datetime import datetime, timedelta
from urllib.parse import quote
import urllib.parse
from typing import Optional, Dict, List, Any # Added Dict, List, Any
from bs4 import BeautifulSoup
from bs4.element import Comment

# Use BaseCrawler and SQLiteManager from the app structure
from app.crawlers.base import BaseCrawler
# from app.db.sqlite_manager import SQLiteManager # SQLiteManager is used by BaseCrawler, not directly here

# from app.utils.proxy_manager import ProxyManager # REMOVED
# from app.utils.logger import get_crawler_logger # REMOVED

# logger = get_crawler_logger('新浪财经') # REMOVED

class SinaCrawler(BaseCrawler):
    """新浪财经爬虫，用于爬取新浪财经的财经新闻"""

    source = '新浪财经'
    
    ad_patterns: List[str] = [ # Moved to class attribute and typed
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
        'ESG': 'https://finance.sina.com.cn/esg/',
        '专栏': 'https://finance.sina.com.cn/zl/',
        '博客': 'http://blog.sina.com.cn/lm/finance/',
        '股市及时雨': 'https://finance.sina.com.cn/roll/index.d.html?cid=56589',
        '宏观研究': 'https://finance.sina.com.cn/roll/index.d.html?cid=56598',
    }
    
    STOCK_PAGE_SELECTORS: Dict[str, str] = {
        'news_links': 'div.news_list ul li a, div.m-list li a, div.f-list li a',
        'stock_indices': 'table.tb_01 tr',
        'stock_data': 'table.tb_02 tr'
    }
    
    def __init__(self, db_manager: Optional[Any] = None, db_path: Optional[str] = None, use_proxy: bool = False, **kwargs: Any):
        """
        初始化新浪财经爬虫
        
        Args:
            db_manager: 数据库管理器实例 (from BaseCrawler, typically SQLiteManager)
            db_path: 数据库路径 (used if db_manager is not provided)
            use_proxy: 是否使用代理
            **kwargs: Additional arguments for BaseCrawler
        """
        super().__init__(db_manager=db_manager, db_path=db_path, use_proxy=use_proxy, source=self.source, **kwargs)
        # self.logger is inherited from BaseCrawler
        # self.session is inherited from BaseCrawler
        # self.stats is inherited from BaseCrawler (for success_count, fail_count)
        # self.settings can be used for crawler-specific configurations if needed (replacing _init_config)

        # The `days` attribute might be set by `crawl` method, or passed via kwargs to BaseCrawler settings
        self.days: int = kwargs.get('days', 1) # Default to 1 if not passed, consistent with crawl method signature

        self.logger.info(f"新浪财经爬虫 ({self.source}) 初始化完成. DB Manager: {type(self.db_manager).__name__ if self.db_manager else 'N/A'}, DB Path used: {self.db_manager.db_path if self.db_manager else 'N/A'}") # type: ignore

    # def _init_database(self): # REMOVE - Handled by BaseCrawler
    #     ...
    
    # def _init_proxy(self): # REMOVE - Handled by BaseCrawler
    #     ...

    # def _init_config(self): # REVIEW - BaseCrawler has self.settings; specific configs can go there or be class attrs
    #     ...

    # fetch_page: Replaced with call to super().fetch_page()
    # The existing fetch_page method correctly calls super().fetch_page()
    # and uses self.logger.debug and self.logger.error. This is good.
    # No changes needed here other than ensuring all `logger` calls become `self.logger` if they aren't already.
    # The current version of SinaCrawler.fetch_page already uses self.logger.debug and self.logger.error.
    # The module-level `logger` was used elsewhere.
    
    def _crawl_category(self, category: str, base_url: str, max_pages: int):
        """
        Crawls a specific category: extracts all links (handling pagination) 
        and then processes the links.
        
        Args:
            category (str): Category name.
            base_url (str): Starting URL for the category.
            max_pages (int): Max pages to crawl for link extraction.
        """
        self.logger.info(f"开始处理分类: {category}, 起始URL: {base_url}") # type: ignore
        
        try:
            # Step 1: Extract all links for the category using the pagination method
            all_links_for_category = self._extract_links_for_category(base_url, category, max_pages)
            
            if not all_links_for_category:
                self.logger.info(f"分类 '{category}' 未提取到任何链接.") # type: ignore
                return
            # Step 2: Process the extracted links (get details, check date, save)
            self.logger.info(f"分类 '{category}': 开始处理提取到的 {len(all_links_for_category)} 个链接.")
            self._process_news_links(all_links_for_category, category) # Pass the full list

        except Exception as e:
            self.logger.error(f"处理分类 '{category}' ({base_url}) 时发生顶层错误: {e}", exc_info=True)
            # Log the error but allow the main crawl loop to continue with the next category

    def _extract_links_from_soup(self, soup: BeautifulSoup) -> List[str]:
        """
        从HTML BeautifulSoup对象中提取符合要求的新闻链接.
        """
        news_links_found: List[str] = []
        link_selectors = [
            'div.feed-card-item h2 a',
            'div.news-item h2 a',
            'ul.list_009 li a',
            'li.news-item a',
            'div.m-list li a',
            'div.news-list a',
            'div.article-list li a',
            'div.listBlk li a',
            '#listZone li a',
            'a[href*="finance.sina.com.cn/"]',
            'a[href*="tech.sina.com.cn/"]'
        ]
        processed_hrefs = set()

        try:
            for selector in link_selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if not href or not isinstance(href, str):
                        continue
                    
                    try:
                        # Use base from settings or default to finance
                        base_for_join = self.settings.get('BASE_URL', 'https://finance.sina.com.cn/') 
                        absolute_href = urllib.parse.urljoin(base_for_join, href)
                        if not absolute_href.startswith('http'):
                             continue
                    except Exception:
                        continue

                    if absolute_href in processed_hrefs:
                        continue
                    processed_hrefs.add(absolute_href)

                    exclude_patterns = ['/photo/', '/slide/', '/video.', '/live.', 'app.sina', 'comment', 'survey', 'jump.sina', 'vip.sina', 'blog.sina', 'auto.sina', 'ent.sina', 'sports.sina', 'gov.sina', 'jiaju.sina', 'leju.com', 'games.sina']
                    if any(pattern in absolute_href.lower() for pattern in exclude_patterns):
                        continue
                    
                    if self._is_news_link(absolute_href):
                         if absolute_href not in news_links_found:
                             news_links_found.append(absolute_href)
                             # self.logger.debug(f"提取到潜在新闻链接: {absolute_href} (选择器: {selector})") # Optional: too verbose?

            # Log final count for the soup object processed
            if news_links_found:
                 self.logger.debug(f"从当前页面提取到 {len(news_links_found)} 个有效新闻链接.") # type: ignore
                 
            return news_links_found
        except Exception as e:
            self.logger.error(f"提取新闻链接时出错 (_extract_links_from_soup): {str(e)}", exc_info=True) # type: ignore
            return []

    def _is_news_link(self, url: str) -> bool:
        """
        判断URL是否为有效的新浪财经或科技新闻文章链接.
        """
        if not url or not isinstance(url, str) or not url.startswith('http'):
            return False
            
        if not ('finance.sina.com.cn' in url or 'tech.sina.com.cn' in url):
            return False
            
        non_news_patterns = [
            '/photo/', '/slide/', '/video.', '/live.', '/zt_', '/corp/', '/tags/', '/focus/',
            '/quotes/', '/globalindex/', '/fund/quotes/', '/forex/quotes/', '/futures/quotes/',
            '/guide/', '/mobile/', '/app.', 'jump.sina', 'vip.sina', 'auto.sina', 'ent.sina',
            'sports.sina', 'gov.sina', 'jiaju.sina', 'leju.com', 'games.sina', 'blog.sina',
            'comment', 'survey', 'about', 'help', 'sitemap', 'rss', 'map.shtml',
            'index.d.html', 'index.shtml', '?cid=', '?fid=', '/roll/', '/otc/'
        ] + self.ad_patterns

        normalized_url = url.rstrip('/')
        # Use lower for case-insensitive matching of patterns
        url_lower = normalized_url.lower()
        if any(pattern in url_lower for pattern in non_news_patterns):
            return False
            
        news_url_patterns = [
            r"finance\.sina\.com\.cn/.+/\d{4}-\d{2}-\d{2}/doc-[a-z0-9]+\.shtml",
            r"tech\.sina\.com\.cn/.+/\d{4}-\d{2}-\d{2}/doc-[a-z0-9]+\.shtml",
            r"finance\.sina\.com\.cn/stock/.+\.shtml",
            r"finance\.sina\.com\.cn/fund/.+\.shtml",
            r"finance\.sina\.com\.cn/future/.+\.shtml",
            r"finance\.sina\.com\.cn/forex/.+\.shtml",
        ]
        for pattern in news_url_patterns:
            # Use normalized_url for regex matching (case might matter for doc-id)
            if re.search(pattern, normalized_url):
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
        提取正文内容
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 正文内容, or None if not found
        """
        try:
            content_selectors = [
                'div.article-content',
                'div.article',
                'div#artibody',
                'div.main-content',
                'div.content',
                'article'
            ]
            
            for selector in content_selectors:
                content_tag = soup.select_one(selector)
                if content_tag:
                    for script_or_style in content_tag.find_all(['script', 'style']):
                        script_or_style.decompose()
                    
                    for comment_node in content_tag.find_all(text=lambda text: isinstance(text, Comment)):
                        comment_node.extract()
                    
                    ad_like_classes = ['recommend', 'related', 'footer', 'ad', 'bottom', 'sinaads', 'adbox'] 
                    
                    for item in content_tag.find_all(True):
                        current_classes = item.get('class', [])
                        if any(ad_class in current_classes for ad_class in ad_like_classes):
                            item.decompose()
                            continue 

                    text_content = content_tag.get_text('\n').strip()
                    text_content = re.sub(r'\n{2,}', '\n', text_content) 
                    text_content = re.sub(r'\s{2,}', ' ', text_content)   
                    
                    if text_content:
                        return text_content
            
            self.logger.warning("正文内容未通过任何选择器找到.")
            return None
        except Exception as e: 
            self.logger.error(f"提取正文内容时出错: {str(e)}", exc_info=True)
            return None
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """
        提取作者/来源
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 作者/来源, or None if not reliably found or error occurs
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
                {'selector': 'p.article-editor', 'type': 'text'}
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
            
            self.logger.debug("未能从特定选择器中提取到明确的作者/来源信息.")
            return None
        except Exception as e:
            self.logger.error(f"提取作者/来源时出错: {str(e)}", exc_info=True)
            return None

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """
        从页面中提取标题
        
        Args:
            soup (BeautifulSoup): BeautifulSoup对象
        
        Returns:
            Optional[str]: 标题, or None if not found
        """
        title_text: Optional[str] = None
        
        title_selectors = [
            'h1.main-title',
            'h1.title',
            'h1.article-title',
            'h1.news_title',
            'div.main-title h1',
            'h1'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title_text = element.get_text(strip=True)
                if title_text and len(title_text) > 3:
                    if self.source and f" - {self.source}" in title_text:
                         title_text = title_text.replace(f" - {self.source}", "").strip()
                    if self.source and f"_{self.source}" in title_text:
                         title_text = title_text.replace(f"_{self.source}", "").strip()
                    if "_新浪财经_" in title_text:
                        title_text = title_text.split("_新浪财经_")[0].strip()
                    if " - 新浪财经" in title_text:
                        title_text = title_text.replace(" - 新浪财经", "").strip()

                    title_text = re.sub(r'\s+', ' ', title_text).strip()
                    if title_text and len(title_text) > 3:
                       self.logger.debug(f"提取到标题 (H-tag): {title_text}")
                       return title_text
        
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            if title_text and len(title_text) > 3:
                if self.source and f" - {self.source}" in title_text:
                     title_text = title_text.replace(f" - {self.source}", "").strip()
                if self.source and f"_{self.source}" in title_text:
                     title_text = title_text.replace(f"_{self.source}", "").strip()
                if "_新浪财经_" in title_text:
                    title_text = title_text.split("_新浪财经_")[0].strip()
                if " - 新浪财经" in title_text:
                    title_text = title_text.replace(" - 新浪财经", "").strip()
                
                title_text = re.sub(r'\s+', ' ', title_text).strip()
                if title_text and len(title_text) > 3:
                    self.logger.debug(f"提取到标题 (title-tag): {title_text}")
                    return title_text

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
                    title_text = re.sub(r'\s+', ' ', title_text).strip()
                    if title_text and len(title_text) > 3:
                        self.logger.debug(f"提取到标题 (meta-tag): {title_text}")
                        return title_text
        
        self.logger.warning("未能提取到标题.")
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
                    if field == 'pub_time' and news_item.get(field) is None: # Allow None pub_time
                        continue
                    self.logger.warning(f"SinaCrawler._save_news: 待保存的新闻缺少关键字段 '{field}'. URL: {news_item.get('url', 'N/A')}")
            return False

            return super().save_news_to_db(news_item)
            
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

    def crawl(self, days: int = 1, max_pages: int = 3, category: Optional[str] = None, **kwargs) -> None:
        """
        Main method to crawl Sina Finance news.
        Iterates through specified categories or all categories, fetching and processing links.
        
        Args:
            days (int): Crawl news published within the last N days. Updates self.days.
            max_pages (int): Max pages to process per category during link extraction.
            category (Optional[str]): Specific category name(s) to crawl (comma-separated). 
                                     If None, crawls all defined in CATEGORY_URLS.
            **kwargs: Additional arguments potentially passed to BaseCrawler.
        """
        self.days = days if isinstance(days, int) and days > 0 else 1
        
        self.logger.info(f"===== 开始新浪财经爬取任务 =====")
        self.logger.info(f"参数: days={self.days}, max_pages={max_pages}, category='{category}'")

        target_categories: Dict[str, str] = {}
        if category:
            cat_list = [c.strip() for c in category.split(',') if c.strip()]
            self.logger.info(f"指定分类: {cat_list}")
            for cat_name in cat_list:
                if cat_name in self.CATEGORY_URLS:
                    target_categories[cat_name] = self.CATEGORY_URLS[cat_name]
                else:
                    self.logger.warning(f"指定的分类 '{cat_name}' 在 CATEGORY_URLS 中未找到，将跳过.")
            if not target_categories:
                 self.logger.error("未找到任何有效的指定分类进行爬取.")
                 return 
        else:
            self.logger.info("未指定特定分类，将爬取所有预定义分类.")
            target_categories = self.CATEGORY_URLS

        self.logger.info(f"将要爬取的分类: {list(target_categories.keys())}")

        for cat_name, base_url in target_categories.items():
            self.logger.info(f"--- 开始处理分类: {cat_name} ({base_url}) ---")
            try:
                self._crawl_category(cat_name, base_url, max_pages) # Call refactored _crawl_category
            except Exception as e:
                self.logger.error(f"处理分类 '{cat_name}' 时发生意外错误: {e}", exc_info=True)
            finally:
                 self.logger.info(f"--- 分类 {cat_name} 处理完成 ---")
                 # time.sleep(self.settings.get('DELAY_BETWEEN_CATEGORIES', 1))

        self.logger.info("===== 新浪财经爬取任务全部完成 =====")

    def _find_next_page_url(self, soup: BeautifulSoup, current_url: str, current_page_num: int) -> Optional[str]:
        """
        Tries to find the URL for the next page from the current page's soup.
        Handles common pagination link texts and CSS selectors.
        
        Args:
            soup: BeautifulSoup object of the current page.
            current_url: URL of the current page (for resolving relative links).
            current_page_num: The current page number (1-based).
            
        Returns:
            Optional[str]: The absolute URL of the next page, or None if not found.
        """
        next_page_url: Optional[str] = None
        
        # Strategy 1: Look for links with specific text
        possible_texts = ['下一页', '>', '下页', f'>{current_page_num + 1}<']
        for text_pattern in possible_texts:
            try:
                pattern = re.compile(f'\\s*{re.escape(text_pattern)}\\s*', re.IGNORECASE)
                next_link = soup.find('a', string=pattern)
                if not next_link:
                     parent_tag = soup.find(lambda tag: tag.name in ['span', 'li', 'div'] and pattern.search(tag.get_text(strip=True)))
                     if parent_tag:
                          next_link = parent_tag.find('a')

                if next_link and next_link.get('href'):
                    href = next_link['href'].strip()
                    if href and href not in ['#', 'javascript:;']:
                        next_page_url = urllib.parse.urljoin(current_url, href)
                        # Ensure the resolved URL is different from the current one to prevent loops
                        if next_page_url != current_url:
                             self.logger.debug(f"通过文本 '{text_pattern}' 找到下一页链接: {next_page_url}")
                             return next_page_url
            except Exception as e:
                 self.logger.warning(f"查找文本 '{text_pattern}' 的下一页链接时出错: {e}", exc_info=False)

        # Strategy 2: Look for common pagination CSS classes/IDs
        pagination_selectors = [
            'a.pagebox_next', 'a.next', '.pagination a.next', '.page-navigator a.next',
            'a.nextpostslink', 'li.next a', '#page-nav a[rel="next"]', '.pagenav-next a',
            '.page-next a', '.next-page a'
        ]
        for selector in pagination_selectors:
             try:
                 next_link_tag = soup.select_one(selector)
                 if next_link_tag and next_link_tag.get('href'):
                      href = next_link_tag['href'].strip()
                      if href and href not in ['#', 'javascript:;']:
                           next_page_url = urllib.parse.urljoin(current_url, href)
                           if next_page_url != current_url:
                                self.logger.debug(f"通过选择器 '{selector}' 找到下一页链接: {next_page_url}")
                                return next_page_url
             except Exception as e:
                  self.logger.warning(f"查找选择器 '{selector}' 的下一页链接时出错: {e}", exc_info=False)

        # Strategy 3: Fallback URL manipulation (Commented out - unreliable)
        # ...
        
        self.logger.debug(f"未能找到明确的下一页链接 for {current_url}")
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
        Extracts news links for a specific category, handling pagination up to max_pages.
        
        Args:
            category_url (str): The starting URL for the category.
            category_name (str): The name of the category (for logging).
            max_pages (int): The maximum number of pages to crawl for this category.
            
        Returns:
            List[str]: A list of unique news article URLs found.
        """
        all_news_links: List[str] = []
        processed_page_urls = set()
        current_target_url: Optional[str] = category_url
        current_page = 1
        
        while current_page <= max_pages and current_target_url:
            if current_target_url in processed_page_urls:
                self.logger.warning(f"Pagination loop detected for {category_name}, URL: {current_target_url}. Stopping pagination.")
                break
            processed_page_urls.add(current_target_url)
            
            self.logger.info(f"正在爬取分类 '{category_name}' 第 {current_page}/{max_pages} 页: {current_target_url}")
            
            next_page_url_found: Optional[str] = None
            
            try:
                html = self.fetch_page(current_target_url)
                if not html:
                    self.logger.warning(f"获取页面失败 (分页): {current_target_url}")
                    break
                
                soup = BeautifulSoup(html, 'html.parser')
                
                page_links = self._extract_links_from_soup(soup)
                
                new_links_on_page = 0
                if page_links:
                    for link in page_links:
                        if link not in all_news_links:
                            all_news_links.append(link)
                            new_links_on_page += 1
                    self.logger.info(f"从 {category_name} 第 {current_page} 页提取到 {new_links_on_page} 个新链接 (总计: {len(all_news_links)}).")
                else:
                    self.logger.info(f"在 {category_name} 第 {current_page} 页未找到新链接.")

                next_page_url_found = self._find_next_page_url(soup, current_target_url, current_page)
                if not next_page_url_found:
                     self.logger.info(f"在第 {current_page} 页未找到下一页链接，停止分类 '{category_name}' 的分页.")
                    break
                
                current_target_url = next_page_url_found
                current_page += 1
                
                delay = random.uniform(
                    self.settings.get('PAGINATION_DELAY_MIN', 1.0), 
                    self.settings.get('PAGINATION_DELAY_MAX', 3.0)
                )
                self.logger.debug(f"分页随机延时 %.2f 秒", delay)
                time.sleep(delay)
                
            except requests.RequestException as e:
                self.logger.error(f"分页请求失败: {current_target_url}, 错误: {e}")
                break
            except Exception as e:
                self.logger.error(f"处理分页时发生未知异常: {current_target_url}, 错误: {e}", exc_info=True)
                break
        
        self.logger.info(f"分类 '{category_name}' 链接提取完成，共找到 {len(all_news_links)} 个唯一链接 (检查了 {current_page-1} 页).")
        return all_news_links

    # ... (Method _find_next_page_url should be below this)

    # ... (rest of the file will be refactored in subsequent steps) ...
