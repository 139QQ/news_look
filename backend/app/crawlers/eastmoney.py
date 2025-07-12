#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 东方财富网爬虫
使用requests库直接爬取，无需浏览器
整合了简化版功能
"""

import os
import re
import sys
import time
import random
import logging
import hashlib
import requests
import json
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from app.crawlers.base import BaseCrawler
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html, extract_keywords
from app.db.SQLiteManager import SQLiteManager

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('东方财富')

class EastMoneyCrawler(BaseCrawler):
    """东方财富网爬虫，用于爬取东方财富网的财经新闻"""
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, **kwargs):
        """
        初始化东方财富网爬虫
        
        Args:
            db_manager: 数据库管理器
            db_path: 数据库路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
            **kwargs: 其他参数
        """
        # 确保日志记录器已初始化
        self.logger = logger
        
        # 设置source属性，确保父类初始化能够正确设置数据库路径
        self.source = "东方财富"
        
        # 调用父类初始化方法
        super().__init__(
            db_manager=db_manager, 
            db_path=db_path, 
            use_proxy=use_proxy, 
            use_source_db=use_source_db,
            source=self.source, # Pass source to base class
            **kwargs
        )
        
        self.status = 'idle'
        self.last_run = None
        self.next_run = None
        self.error_count = 0
        self.success_count = 0
        
        # 分类URL映射
        self.category_urls = {
            '财经': [
                "https://finance.eastmoney.com/",
                "https://finance.eastmoney.com/a/cjdd.html"
            ],
            '股票': [
                "https://stock.eastmoney.com/",
                "https://stock.eastmoney.com/a/cgspl.html"
            ],
            '基金': [
                "https://fund.eastmoney.com/",
                "https://fund.eastmoney.com/news/cjjj.html"
            ],
            '债券': [
                "https://bond.eastmoney.com/",
                "https://bond.eastmoney.com/news/czqzx.html"
            ]
        }
        
        # 设置请求头
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
        ]
        
        # BaseCrawler.__init__ now handles db_manager setup.
        # Remove redundant setup here:
        # if db_manager:
        #     # ... (old logic removed) ...
        
        # Ensure self.db_manager is accessible (it should be set by super().__init__)
        db_display_path = getattr(self.db_manager, 'db_path', '未正确初始化')
        logger.info("东方财富网爬虫初始化完成，数据库路径: %s", db_display_path)
    
    def get_random_user_agent(self):
        """返回一个随机的User-Agent"""
        return random.choice(self.user_agents)
    
    def get_headers(self):
        """获取HTTP请求头"""
        return {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.eastmoney.com/'
        }
    
    def crawl(self, category=None, max_news=5, days=1, use_selenium=False):
        """
        爬取东方财富网新闻
        """
        try:
            categories_to_crawl = []
            if category:
                # Allow multiple categories separated by comma
                categories = [c.strip() for c in category.split(',') if c.strip() in self.category_urls]
                if categories:
                    categories_to_crawl = categories
                else:
                    logger.warning(f"提供的分类无效或不支持: {category}，将爬取所有分类。")
                    categories_to_crawl = list(self.category_urls.keys())
            else:
                categories_to_crawl = list(self.category_urls.keys())
            
            news_list = []
            processed_count = 0
            
            for cat in categories_to_crawl:
                if processed_count >= max_news:
                    logger.info(f"已达到最大处理数量({max_news})，停止爬取更多分类")
                    break
            
                logger.info(f"开始爬取'{cat}'分类的新闻")
                # _crawl_category now returns the count of successfully processed items in that category
                count_in_cat = self._crawl_category(cat, max_news - processed_count, days)
                processed_count += count_in_cat
            
            logger.info(f"爬取完成，共处理/尝试保存 {processed_count} 条新闻")
            # Removed the loop processing self.news_data, assuming direct DB save is primary path now.
            
            # crawl method might not return a list anymore if save_news isn't used for memory fallback
            # Returning the count might be more appropriate, or None.
            # Let's return the count for now.
            return processed_count
        
        except Exception as e:
            logger.error(f"爬取过程发生错误: {str(e)}")
            return 0 # Return 0 on error
    
    def _crawl_category(self, category, max_to_process, days):
        """
        爬取特定分类的新闻
        Args:
            category: 分类名称
            max_to_process: 此分类中最多处理的新闻数量
            days: 爬取天数
        Returns:
            int: 在此分类中成功处理/尝试保存的新闻数量
        """
        processed_count_in_cat = 0
        start_date = datetime.now() - timedelta(days=days)
        category_urls = self.get_category_url(category)
        
        if not category_urls: 
            logger.warning(f"分类'{category}'没有找到URL配置")
            return 0
            
        logger.info(f"开始爬取'{category}'分类，日期范围: {start_date.strftime('%Y-%m-%d')} 至今")
        logger.info(f"分类'{category}'的URL列表: {category_urls}")
        
        crawled_urls = set()
        if not hasattr(self, 'processed_urls'): 
            self.processed_urls = set()
        
        for list_page_url in category_urls:
            if processed_count_in_cat >= max_to_process: 
                break
            try:
                logger.info(f"正在处理分类列表页: {list_page_url}")
                
                # 获取页面内容并提取链接
                article_links = self.extract_news_links(list_page_url)
                if not article_links: 
                    logger.warning(f"从{list_page_url}没有提取到任何链接")
                    continue
                    
                logger.info(f"从 {list_page_url} 提取到 {len(article_links)} 个链接")
                time.sleep(random.uniform(1, 2))
                
                for link in article_links:
                    if processed_count_in_cat >= max_to_process: 
                        break
                    if link in crawled_urls or link in self.processed_urls: 
                        continue
                        
                    crawled_urls.add(link)
                    self.processed_urls.add(link)
                    
                    try:
                        logger.debug(f"处理新闻链接: {link}")
                        
                        # 检查URL日期过滤
                        pub_date_from_url = self._extract_date_from_url(link)
                        if pub_date_from_url and pub_date_from_url < start_date:
                            logger.debug(f"URL日期 {pub_date_from_url.strftime('%Y-%m-%d')} 早于要求，跳过: {link}")
                            continue
                            
                        # 爬取新闻详情
                        news_detail = self.crawl_news_detail(link, category)
                        
                        if news_detail:
                            logger.debug(f"成功获取新闻详情: {news_detail.get('title', 'N/A')}")
                            
                            # 进一步检查从页面提取的 pub_time (如果存在)
                            pub_time_str = news_detail.get('pub_time')
                            should_save = True
                            if pub_time_str:
                                try:
                                    pub_time_str = pub_time_str.replace('/', '-')
                                    if not re.match(r'\d{4}', pub_time_str):
                                        current_year = datetime.now().year
                                        pub_time_str = f"{current_year}-{pub_time_str}"
                                    pub_dt = datetime.strptime(pub_time_str.split(' ')[0], '%Y-%m-%d')
                                    if pub_dt < start_date:
                                        logger.debug(f"内容发布日期 {pub_time_str} 早于要求，跳过: {link}")
                                        should_save = False
                                except Exception as e:
                                    logger.warning(f"解析内容日期 {pub_time_str} 失败: {e}. 仍尝试保存。")
                            
                            if should_save:
                                # 预处理新闻数据
                                processed_news = self._preprocess_news_data(news_detail)
                                
                                # 调用基类保存方法
                                logger.debug(f"尝试保存新闻到数据库: {processed_news.get('title', 'N/A')}")
                                if super().save_news_to_db(processed_news):
                                    processed_count_in_cat += 1
                                    logger.info(f"✅ 成功保存新闻 ({processed_count_in_cat}/{max_to_process}): {processed_news.get('title', 'N/A')}")
                                else:
                                    logger.warning(f"❌ 保存新闻失败: {processed_news.get('title', 'N/A')}")
                            else:
                                logger.debug(f"跳过保存（日期不符合要求）: {news_detail.get('title', 'N/A')}")
                        else:
                            logger.warning(f"爬取新闻详情失败: {link}")
                        
                    except Exception as e:
                        logger.error(f"处理新闻链接 {link} 失败: {str(e)}")
                        import traceback
                        logger.error(f"详细错误信息: {traceback.format_exc()}")
                    
                    time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                logger.error(f"处理列表页 {list_page_url} 失败: {str(e)}")
                import traceback
                logger.error(f"详细错误信息: {traceback.format_exc()}")
        
        logger.info(f"分类'{category}'处理完成，共成功保存 {processed_count_in_cat} 条新闻")
        return processed_count_in_cat
    
    def _check_url_accessibility(self, url):
        """
        检查URL是否可访问
        
        Args:
            url: 要检查的URL
            
        Returns:
            bool: URL是否可访问
        """
        max_retries = 2  # 设置最大重试次数
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # 使用GET请求而不是HEAD请求，某些服务器可能不正确处理HEAD请求
                headers = self.get_headers()
                
                # 使用requests.get代替head请求，但设置stream=True避免下载整个内容
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=10,
                    allow_redirects=True,
                    stream=True
                )
                
                # 检查状态码
                if response.status_code == 200:
                    # 关闭连接释放资源
                    response.close()
                    return True
                elif response.status_code == 404:
                    logger.warning(f"页面不存在 (404): {url}")
                    return False
                elif response.status_code in [301, 302, 307, 308]:
                    # 处理重定向情况
                    if 'location' in response.headers:
                        redirect_url = response.headers['location']
                        # 规范化重定向URL
                        if not redirect_url.startswith(('http://', 'https://')):
                            # 相对URL，需要与原始URL的域名结合
                            from urllib.parse import urlparse, urljoin
                            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                            redirect_url = urljoin(base_url, redirect_url)
                        
                        logger.info(f"URL重定向: {url} -> {redirect_url}")
                        
                        # 检查重定向URL是否有效
                        if self.is_valid_news_url(redirect_url):
                            # 如果重定向URL有效，则返回True
                            return True
                    
                    # 重定向但没有有效的location头，或重定向URL无效
                    return False
                elif response.status_code == 403:
                    # 服务器禁止访问，但可能是临时的或需要特殊处理
                    logger.warning(f"访问被禁止 (403): {url}, 尝试更换请求头")
                    
                    # 每次重试更换User-Agent
                    headers['User-Agent'] = self.get_random_user_agent()
                    # 添加额外的header尝试绕过反爬
                    headers.update({
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                        'Referer': 'https://www.eastmoney.com/'
                    })
                    
                    # 递增重试计数
                    retry_count += 1
                    if retry_count <= max_retries:
                        # 增加等待时间
                        time.sleep(random.uniform(1, 3))
                        continue
                    else:
                        logger.warning(f"最大重试次数已用尽，URL不可访问: {url}")
                        return False
                else:
                    logger.warning(f"无法访问URL，状态码: {response.status_code}: {url}")
                    
                    # 对于5xx服务器错误，可以尝试重试
                    if response.status_code >= 500:
                        retry_count += 1
                        if retry_count <= max_retries:
                            # 增加等待时间
                            time.sleep(random.uniform(2, 5))
                            continue
                    
                    return False
                
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时: {url}")
                retry_count += 1
                if retry_count <= max_retries:
                    time.sleep(random.uniform(1, 3))
                    continue
                return False
            except requests.exceptions.ConnectionError:
                logger.warning(f"连接错误: {url}")
                retry_count += 1
                if retry_count <= max_retries:
                    time.sleep(random.uniform(2, 5))
                    continue
                return False
            except requests.RequestException as e:
                logger.warning(f"检查URL可访问性时出错: {url}, 错误: {str(e)}")
                return False
            except Exception as e:
                logger.error(f"未知错误：{str(e)}")
                return False
                
        # 如果所有重试都失败
        return False
    
    def _extract_date_from_url(self, url):
        """
        从URL中提取日期
        
        Args:
            url: 新闻URL
            
        Returns:
            datetime: 提取的日期对象，如果无法提取则返回None
        """
        # 尝试匹配URL中的日期格式
        # 格式1: /20230723/ 或类似格式
        pattern1 = r'/(\d{4})(\d{2})(\d{2})/'
        # 格式2: /202307/23/ 或类似格式
        pattern2 = r'/(\d{4})(\d{2})/(\d{2})/'
        # 格式3: /2023-07-23/ 或类似格式
        pattern3 = r'/(\d{4})-(\d{2})-(\d{2})/'
        # 格式4: 路径中包含日期，如 news_20230723
        pattern4 = r'_(\d{4})(\d{2})(\d{2})'
        
        for pattern in [pattern1, pattern2, pattern3, pattern4]:
            match = re.search(pattern, url)
            if match:
                try:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    
                    # 验证日期有效性
                    if 2000 <= year <= datetime.now().year and 1 <= month <= 12 and 1 <= day <= 31:
                        return datetime(year, month, day)
                except ValueError:
                    pass
        
        return None
    
    def extract_news_links(self, url):
        """
        从页面中提取新闻链接
        
        Args:
            url: 页面URL
            
        Returns:
            list: 新闻链接列表
        """
        try:
            # 使用带有特定headers的请求获取页面
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            
            # 确保正确的编码
            if response.encoding.lower() in ['iso-8859-1', 'unknown']:
                response.encoding = 'utf-8'
            
            logger.info(f"获取页面成功，编码: {response.encoding}，长度: {len(response.text)}")
            
            # 解析HTML并提取链接
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 使用适合东方财富网的CSS选择器提取新闻链接
            news_links = []
            
            # 主要新闻选择器 - 更新为实际可用的选择器
            selectors = [
                'ul.list li a',  # 从调试输出看，这个选择器有效
                '.news-list li a', 
                '.news-item a', 
                '.title a',
                '.news_item a', 
                '.news-body a',
                '.news-cnt h3 a', 
                '.news-tab .item>a', 
                '.slider-news-list a.news-item',
                '.list-wrap .list-item a',
                '.listContent .list-item a',
                '.text-list li a',
                'a.news-link',
                '.content-list li a',
                'h2 a',  # 标题链接
                'h3 a',  # 标题链接
                'a[href*="/a/"]',  # 包含/a/的链接（新闻文章路径）
            ]
            
            # 对于不同类型的页面使用不同的选择器
            for selector in selectors:
                try:
                    links = soup.select(selector)
                    logger.debug(f"选择器 '{selector}' 找到 {len(links)} 个链接")
                    
                    for link in links:
                        href = link.get('href')
                        if href:
                            # 规范化链接
                            full_url = self._normalize_url(href, url)
                            if full_url and self.is_valid_news_url(full_url):
                                news_links.append(full_url)
                                logger.debug(f"添加有效链接: {full_url}")
                            else:
                                logger.debug(f"跳过无效链接: {href} -> {full_url}")
                except Exception as e:
                    logger.warning(f"处理选择器 '{selector}' 时出错: {e}")
                    continue
            
            # 特殊处理股票和基金页面
            if 'stock.eastmoney.com' in url or 'fund.eastmoney.com' in url:
                # 添加针对股票和基金页面特有的选择器
                stock_fund_selectors = [
                    '.stock-news a', 
                    '.fund-news a',
                    '.article-list a',
                    '.news-panel a', 
                    '.main-list a',
                    '.important-news a'
                ]
                
                for selector in stock_fund_selectors:
                    try:
                        links = soup.select(selector)
                        for link in links:
                            href = link.get('href')
                            if href:
                                full_url = self._normalize_url(href, url)
                                if full_url and self.is_valid_news_url(full_url):
                                    news_links.append(full_url)
                    except Exception as e:
                        logger.warning(f"处理特殊选择器 '{selector}' 时出错: {e}")
                        continue
            
            # 去重
            news_links = list(dict.fromkeys(news_links))
            
            logger.info(f"从 {url} 提取到 {len(news_links)} 条有效新闻链接")
            
            # 输出前几个链接用于调试
            if news_links:
                logger.info("提取到的前5个链接:")
                for i, link in enumerate(news_links[:5]):
                    logger.info(f"  {i+1}. {link}")
            
            return news_links
            
        except Exception as e:
            logger.error(f"提取新闻链接失败: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return []
    
    def _normalize_url(self, href, base_url):
        """
        规范化URL，将相对路径转为绝对路径
        
        Args:
            href: 原始链接
            base_url: 基础URL
            
        Returns:
            str: 规范化后的URL
        """
        if not href:
            return None
            
        # 跳过JavaScript链接和锚点链接
        if href.startswith(('javascript:', '#', 'mailto:')):
            return None
        
        # 清理href中的空白字符
        href = href.strip()
        
        # 处理相对路径
        if href.startswith('//'):
            # 协议相对URL，如 //fund.eastmoney.com/a/xxx.html
            return 'https:' + href
        elif href.startswith('/'):
            # 根路径相对URL，如 /a/xxx.html
            from urllib.parse import urlparse
            parsed_base = urlparse(base_url)
            return f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
        elif not href.startswith(('http://', 'https://')):
            # 相对路径
            from urllib.parse import urljoin
            return urljoin(base_url, href)
            
        return href
    
    def is_valid_news_url(self, url):
        """
        判断URL是否是有效的新闻链接
        
        Args:
            url: URL
            
        Returns:
            bool: 是否是有效的新闻链接
        """
        # 检查是否是东方财富网的链接
        valid_domains = [
            'eastmoney.com',
            'finance.eastmoney.com',
            'stock.eastmoney.com',
            'fund.eastmoney.com',
            'bond.eastmoney.com',
            'forex.eastmoney.com',
            'money.eastmoney.com',
            'futures.eastmoney.com',
            'global.eastmoney.com',
            'tech.eastmoney.com',
            'hk.eastmoney.com',
            'data.eastmoney.com'
        ]
        
        if not any(domain in url for domain in valid_domains):
            return False
        
        # 排除无效的页面类型
        invalid_keywords = [
            'list', 'index.html', 'search', 'help', 'about', 'contact',
            'login', 'register', 'download', 'app', 'special', 'zhuanti',
            'data', 'f10', 'api', 'static', 'so.eastmoney', 'guba', 'bbs',
            'blog', 'live', 'wap'
        ]
        
        # 一些特殊的有效关键字（覆盖无效关键字检查）
        valid_overrides = [
            '/a/', '/news/', '/article/', '/content/', '/yw/', '/cj/',
            '/stock/news', '/fund/news', '/bond/news',
            '/article_', '/2023', '/2024'
        ]
        
        # 检查是否包含有效覆盖关键字
        if any(override in url for override in valid_overrides):
            return True
            
        # 检查是否包含无效关键字
        if any(keyword in url for keyword in invalid_keywords):
            return False
        
        # 检查URL是否是新闻页面（通常包含/a/、/news/等路径）
        if any(path in url for path in ['/a/', '/news/', '/article/', '/content/']):
            return True
            
        # 检查URL是否包含年份数字（通常新闻URL包含发布日期）
        if re.search(r'/20\d{2}', url):
            return True
            
        # 针对股票、基金页面的特殊检查
        if 'stock.eastmoney.com' in url and re.search(r'\.html$', url):
            return True
            
        if 'fund.eastmoney.com' in url and re.search(r'\.html$', url):
            return True
        
        return False
    
    def crawl_news_detail(self, url, category):
        """
        爬取新闻详情
        
        Args:
            url: 新闻URL
            category: 分类
            
        Returns:
            dict: 新闻详情
        """
        try:
            # 准备特定的请求头，避免反爬
            headers = self.get_headers()
            
            # 请求页面内容
            html = self.fetch_page_with_requests(url)
            
            if not html:
                logger.warning(f"获取新闻详情页失败: {url}")
                return None
            
            # 使用策略解析详情页
            # from backend.app.crawlers.strategies.eastmoney_strategy import EastMoneyStrategy
            
            # 使用策略解析新闻详情
            # strategy = EastMoneyStrategy(self.source)
            
            try:
                # 直接在这里实现解析逻辑，避免策略加载
                news_data = self._parse_news_detail(html, url, category)
                
                # 验证解析结果
                if not news_data.get('title') or news_data.get('title') in ["内容为空", "解析失败"]:
                    logger.warning(f"解析新闻 {url} 失败: 标题为空或解析失败")
                    return None
                
                return news_data
                
            except Exception as e:
                logger.error(f"使用策略解析新闻 {url} 时出错: {str(e)}，尝试使用备用解析方法")
                # 如果策略解析失败，回退到自己的解析方法
                return self._parse_news_detail(html, url, category)
                
        except Exception as e:
            logger.error(f"爬取新闻详情失败: {url}, 错误: {str(e)}")
            return None
    
    def _parse_news_detail(self, html, url, category):
        """
        解析新闻详情 (简化版，移除冗余预处理)
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        title = self.extract_title(soup)
        if not title: return None
        
        pub_time = self.extract_pub_time(soup) # Extract raw time string or None
        author = self.extract_author(soup) # Extract raw author or None
        text_content, html_content = self.extract_content(soup)
        keywords_list = self.extract_keywords(soup, text_content) # Expect list of strings
        
        # 构建只包含提取信息的新闻字典
        # 其他字段（id, source, crawl_time, sentiment, defaults）由下游处理
        news = {
            'url': url,
            'title': title,
            'content': text_content,
            'content_html': html_content,
            'pub_time': pub_time, # Pass raw extracted value
            'author': author,   # Pass raw extracted value
            'keywords': ','.join(keywords_list) if keywords_list else None, # Pass csv or None
            'category': category # Keep category from crawl context
        }
        
        logger.info(f"[_parse_news_detail] 成功提取新闻: {title}")
        return news
    
    def extract_title(self, soup):
        """
        提取新闻标题
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: 标题
        """
        # 尝试常见的标题选择器
        selectors = [
            'h1.articleTitle', 
            'h1.article-title',
            'h1.title',
            'div.article-title h1',
            'div.detail-title h1',
            'h1'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                return elements[0].get_text().strip()
        
        # 如果上述选择器都未找到，尝试使用页面标题
        if soup.title:
            title = soup.title.get_text().strip()
            # 去除网站名称
            title = re.sub(r'[-_|].*?$', '', title).strip()
            return title
        
        return None
    
    def extract_pub_time(self, soup):
        """
        提取发布时间
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: 发布时间(YYYY-MM-DD HH:MM:SS)
        """
        # 尝试常见的时间选择器
        selectors = [
            'div.time',
            'div.article-time',
            'div.article-info span.time',
            'span.time',
            'div.Info span:first-child',
            'div.infos time'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                time_text = elements[0].get_text().strip()
                
                # 尝试匹配日期时间格式
                patterns = [
                    r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(:\d{2})?)',
                    r'(\d{4}/\d{2}/\d{2}\s\d{2}:\d{2}(:\d{2})?)',
                    r'(\d{4}年\d{2}月\d{2}日\s\d{2}:\d{2}(:\d{2})?)',
                    r'(\d{4}-\d{2}-\d{2})',
                    r'(\d{4}/\d{2}/\d{2})',
                    r'(\d{4}年\d{2}月\d{2}日)'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, time_text)
                    if match:
                        date_time = match.group(1)
                        
                        # 转换格式
                        date_time = date_time.replace('/', '-').replace('年', '-').replace('月', '-').replace('日', '')
                        
                        # 如果只有日期，添加时间
                        if ' ' not in date_time:
                            date_time += ' 00:00:00'
                        # 如果没有秒，添加秒
                        elif date_time.count(':') == 1:
                            date_time += ':00'
                        
                        return date_time
        
        # 尝试从URL中提取日期
        try:
            url = None
            url_element = soup.select_one('link[rel="canonical"]')
            if url_element:
                url = url_element.get('href')
            
            if url:
                # 尝试提取日期，格式如 /20230317/ 或 /202303171430/
                match = re.search(r'/(\d{8})(\d{4})?', url)
                if match:
                    date_str = match.group(1)
                    time_str = match.group(2) if match.group(2) else '0000'
                    
                    year = date_str[:4]
                    month = date_str[4:6]
                    day = date_str[6:8]
                    
                    hour = time_str[:2] if time_str else '00'
                    minute = time_str[2:] if time_str else '00'
                    
                    return f"{year}-{month}-{day} {hour}:{minute}:00"
        except:
            pass
        
        return None
    
    def extract_author(self, soup):
        """
        提取作者/来源
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: 作者/来源
        """
        # 尝试常见的作者选择器
        selectors = [
            'div.source',
            'span.source',
            'div.author',
            'span.author',
            'div.article-meta span.time'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                author_text = elements[0].get_text().strip()
                
                # 提取"来源："后面的内容
                match = re.search(r'来源[:：](.*?)$', author_text)
                if match:
                    return match.group(1).strip()
                
                # 如果没有"来源："前缀，直接使用文本
                return author_text
        
        return None
    
    def extract_content(self, soup):
        """
        从BeautifulSoup对象中提取新闻正文内容
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            tuple: (纯文本内容, HTML内容)
        """
        try:
            # 查找文章内容容器
            content_div = None
            
            # 查找可能的内容容器
            selectors = [
                'div.txtinfos',  # 新版详情页
                'div#ContentBody',  # 老版详情页
                'div.newsContent', # 另一种详情页
                'div.Container', # 可能的容器
                'div.article-content', # 可能的容器
                'div.content', # 通用
                'div#ctrlfscont', # 东方财富网文章内容ID
                'div.Body', # 东方财富网文章正文
                'div.news-content' # 另一种可能的容器
            ]
            
            # 依次尝试各种选择器
            for selector in selectors:
                content_div = soup.select_one(selector)
                if content_div and len(content_div.text.strip()) > 100:
                    # 内容长度大于100个字符，认为是有效内容
                    break
            
            # 如果找不到特定容器，尝试其他方法找到最可能的内容区域
            if not content_div or len(content_div.text.strip()) < 100:
                # 获取页面中最长的div元素作为内容
                divs = soup.find_all('div')
                if divs:
                    divs_with_text = [(div, len(div.text.strip())) for div in divs if len(div.text.strip()) > 100]
                    if divs_with_text:
                        divs_with_text.sort(key=lambda x: x[1], reverse=True)
                        content_div = divs_with_text[0][0]
            
            if not content_div:
                logger.warning("找不到新闻内容")
                return "", ""
            
            # 移除不需要的元素
            for remove_tag in content_div.select('script, style, iframe, .advertise, .advert, .ad-content, .no-print, .related-news, .clear, #backsohucom'):
                remove_tag.decompose()
            
            # 保存原始HTML内容
            html_content = str(content_div)
            
            # 获取图片
            images = []
            for img in content_div.find_all('img'):
                if img.get('src'):
                    images.append(img['src'])
            
            # 从HTML中提取纯文本，但保留段落结构
            paragraphs = []
            for p in content_div.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5']):
                text = p.get_text().strip()
                if text and not text.isspace() and len(text) > 5:  # 忽略太短的段落
                    paragraphs.append(text)
            
            # 过滤掉广告
            clean_paragraphs = [p for p in paragraphs if not self.filter_advertisements(p)]
            
            # 将段落以换行符连接
            text_content = '\n\n'.join(clean_paragraphs)
            
            # 特殊处理：修复HTML内容中的排版问题
            # 确保每个段落有正确的标签和间距
            soup_html = BeautifulSoup(html_content, 'html.parser')
            for p_tag in soup_html.find_all(['p']):
                # 添加CSS样式确保段落间距
                p_tag['style'] = 'margin-bottom: 1em; line-height: 1.6;'
            
            # 添加响应式样式确保在移动设备上也能正常显示
            style_tag = soup.new_tag('style')
            style_tag.string = '''
            img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
            p { margin-bottom: 1em; line-height: 1.6; }
            h1, h2, h3, h4, h5 { margin: 1em 0 0.5em 0; }
            table { width: 100%; max-width: 100%; overflow-x: auto; display: block; }
            '''
            soup_html.insert(0, style_tag)
            
            # 修复后的HTML内容
            fixed_html_content = str(soup_html)
            
            return text_content, fixed_html_content
        
        except Exception as e:
            logger.error(f"提取新闻内容失败: {str(e)}")
            return "", ""
    
    def filter_advertisements(self, content):
        """
        过滤广告和无关内容
        
        Args:
            content: 原始内容文本
            
        Returns:
            bool: 是否包含广告
        """
        if not content:
            return True
            
        # 定义需要过滤的广告和无关内容模式
        ad_patterns = [
            r'打开微信[，,].*?朋友圈',
            r'扫描二维码.*?关注',
            r'东方财富.*?微信',
            r'扫一扫.*?分享',
            r'点击底部的.*?发现',
            r'使用.*?扫一扫',
            r'在东方财富看资讯.*?开户交易>>',
            r'想炒股，先开户！.*?搞定>>',
            r'全新妙想投研助理，立即体验',
            r'打开APP查看更多',
            r'更多精彩内容，请下载.*?APP',
            r'点击下载.*?APP',
            r'本文首发于.*?APP',
            r'关注微信公众号.*?',
            r'本文转自.*?仅供参考',
            r'风险提示：.*?入市有风险',
            r'免责声明：.*?据此操作',
            r'(文章来源|来源)：.*?\n',
        ]
        
        # 逐个应用过滤模式
        for pattern in ad_patterns:
            if re.search(pattern, content, re.DOTALL):
                return True
        
        return False
    
    def extract_keywords(self, soup, content=None):
        """
        提取关键词
        
        Args:
            soup: BeautifulSoup对象
            content: 内容文本
            
        Returns:
            list: 关键词列表
        """
        # 尝试从meta标签提取关键词
        meta_keywords = soup.select_one('meta[name="keywords"]')
        if meta_keywords and meta_keywords.get('content'):
            keywords_text = meta_keywords.get('content')
            if ',' in keywords_text:
                return [k.strip() for k in keywords_text.split(',') if k.strip()]
            elif '，' in keywords_text:
                return [k.strip() for k in keywords_text.split('，') if k.strip()]
        
        # 尝试从内容中提取关键词
        if content:
            try:
                import jieba
                import jieba.analyse
                # 使用TF-IDF算法提取关键词
                keywords = jieba.analyse.extract_tags(content, topK=10)
                return keywords
            except:
                pass
        
        return []
    
    def get_category_url(self, category):
        """
        获取分类URL列表
        
        Args:
            category: 分类名称
            
        Returns:
            list: 分类URL列表
        """
        # 更新后的有效分类URL映射
        valid_category_urls = {
            '财经': [
                "https://finance.eastmoney.com/",
                "https://finance.eastmoney.com/a/cjdd.html"
            ],
            '股票': [
                "https://stock.eastmoney.com/",
                "https://stock.eastmoney.com/a/cgspl.html"
            ],
            '基金': [
                "https://fund.eastmoney.com/",
                "https://fund.eastmoney.com/news/cjjj.html"
            ],
            '债券': [
                "https://bond.eastmoney.com/",
                "https://bond.eastmoney.com/news/czqzx.html"
            ]
        }
        
        # 检查分类是否存在于有效URL映射中
        if category and category in valid_category_urls:
            return valid_category_urls[category]
        
        # 如果未指定分类或找不到分类，返回所有有效分类的URL
        if not category:
            all_urls = []
            for urls in valid_category_urls.values():
                all_urls.extend(urls)
            return all_urls
        
        # 如果指定的分类不存在于有效映射中，检查原始映射
        if category and category in self.category_urls:
            # 返回原始分类URL，但可能需要验证
            logger.warning(f"分类 '{category}' 不在有效URL映射中，使用原始URL（可能需要验证）")
            return self.category_urls[category]
        
        # 如果指定的分类不存在，记录警告并返回默认财经分类
        logger.warning(f"未找到分类 '{category}'，使用默认财经分类")
        return valid_category_urls.get('财经', [])

def main():
    """测试爬虫功能"""
    from app.db.SQLiteManager import SQLiteManager
    
    # 创建数据库管理器
    db_manager = SQLiteManager('./data/news.db')
    
    # 创建爬虫实例
    crawler = EastMoneyCrawler(db_manager)
    
    # 爬取财经新闻
    crawler.crawl(category='财经', max_news=3)
    
    print("爬取完成")

if __name__ == '__main__':
    from app.utils.logger import get_crawler_logger
    logger = get_crawler_logger('东方财富')
    main()
