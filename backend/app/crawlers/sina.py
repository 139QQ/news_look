#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 新浪财经爬虫
采用与东方财富爬虫相同的架构，使用requests库直接爬取，无需浏览器
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
from backend.app.crawlers.base import BaseCrawler
from backend.app.utils.logger import get_crawler_logger
from backend.app.utils.text_cleaner import clean_html, extract_keywords
from backend.app.db.SQLiteManager import SQLiteManager

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('新浪财经')

class SinaCrawler(BaseCrawler):
    """新浪财经爬虫，用于爬取新浪财经的新闻"""
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, **kwargs):
        """
        初始化新浪财经爬虫
        
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
        self.source = "新浪财经"
        
        # 调用父类初始化方法
        super().__init__(
            db_manager=db_manager, 
            db_path=db_path, 
            use_proxy=use_proxy, 
            use_source_db=use_source_db,
            source=self.source,
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
                "https://finance.sina.com.cn/",
                "https://finance.sina.com.cn/china/",
                "https://finance.sina.com.cn/world/"
            ],
            '股票': [
                "https://finance.sina.com.cn/stock/",
                "https://finance.sina.com.cn/realstock/company/",
                "https://finance.sina.com.cn/stock/marketresearch/"
            ],
            '基金': [
                "https://finance.sina.com.cn/fund/",
                "https://finance.sina.com.cn/fund/fundnews/"
            ],
            '期货': [
                "https://finance.sina.com.cn/futuremarket/",
                "https://finance.sina.com.cn/money/future/"
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
        
        db_display_path = getattr(self.db_manager, 'db_path', '未正确初始化')
        logger.info("新浪财经爬虫初始化完成，数据库路径: %s", db_display_path)
    
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
            'Referer': 'https://finance.sina.com.cn/'
        }
    
    def crawl(self, category=None, max_news=5, days=1, use_selenium=False):
        """
        爬取新浪财经新闻
        
        Args:
            category: 分类（可选）
            max_news: 最大新闻数量
            days: 爬取天数
            use_selenium: 是否使用Selenium（忽略此参数）
            
        Returns:
            int: 成功处理的新闻数量
        """
        try:
            categories_to_crawl = []
            if category:
                # 支持逗号分隔的多个分类
                categories = [c.strip() for c in category.split(',') if c.strip() in self.category_urls]
                if categories:
                    categories_to_crawl = categories
                else:
                    logger.warning(f"提供的分类无效或不支持: {category}，将爬取所有分类。")
                    categories_to_crawl = list(self.category_urls.keys())
            else:
                categories_to_crawl = list(self.category_urls.keys())
            
            processed_count = 0
            
            for cat in categories_to_crawl:
                if processed_count >= max_news:
                    logger.info(f"已达到最大处理数量({max_news})，停止爬取更多分类")
                    break
            
                logger.info(f"开始爬取'{cat}'分类的新闻")
                count_in_cat = self._crawl_category(cat, max_news - processed_count, days)
                processed_count += count_in_cat
            
            logger.info(f"爬取完成，共处理 {processed_count} 条新闻")
            return processed_count
        
        except Exception as e:
            logger.error(f"爬取过程发生错误: {str(e)}")
            return 0
    
    def _crawl_category(self, category, max_to_process, days):
        """
        爬取特定分类的新闻
        
        Args:
            category: 分类名称
            max_to_process: 此分类中最多处理的新闻数量
            days: 爬取天数
            
        Returns:
            int: 在此分类中成功处理的新闻数量
        """
        processed_count_in_cat = 0
        start_date = datetime.now() - timedelta(days=days)
        category_urls = self.get_category_url(category)
        
        if not category_urls:
            return 0
            
        logger.info(f"开始爬取'{category}'分类，日期范围: {start_date.strftime('%Y-%m-%d')} 至今")
        
        crawled_urls = set()
        if not hasattr(self, 'processed_urls'):
            self.processed_urls = set()
        
        for list_page_url in category_urls:
            if processed_count_in_cat >= max_to_process:
                break
                
            try:
                logger.info(f"正在处理分类列表页: {list_page_url}")
                article_links = self.extract_news_links(list_page_url)
                
                if not article_links:
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
                        # 检查链接日期
                        pub_date_from_url = self._extract_date_from_url(link)
                        if pub_date_from_url and pub_date_from_url < start_date:
                            logger.debug(f"URL日期 {pub_date_from_url.strftime('%Y-%m-%d')} 早于要求，跳过: {link}")
                            continue
                            
                        news_detail = self.crawl_news_detail(link, category)
                        
                        if news_detail:
                            # 进一步检查从页面提取的 pub_time
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
                                # 调用基类保存方法
                                if super().save_news_to_db(news_detail):
                                    processed_count_in_cat += 1
                                else:
                                    logger.warning(f"基类save_news_to_db未能保存新闻: {news_detail.get('title')}")
                        else:
                            logger.warning(f"爬取新闻详情失败: {link}")
                        
                    except Exception as e:
                        logger.error(f"处理新闻链接 {link} 失败: {str(e)}")
                    
                    time.sleep(random.uniform(0.5, 1.5))
                        
            except Exception as e:
                logger.error(f"处理列表页 {list_page_url} 失败: {str(e)}")
        
        logger.info(f"分类'{category}'处理完成，共尝试保存 {processed_count_in_cat} 条新闻")
        return processed_count_in_cat
    
    def _extract_date_from_url(self, url):
        """
        从URL中提取日期
        
        Args:
            url: 新闻URL
            
        Returns:
            datetime: 提取的日期对象，如果无法提取则返回None
        """
        # 新浪财经的URL日期格式
        patterns = [
            r'/(\d{4})-(\d{2})-(\d{2})/',   # /2023-07-23/
            r'/(\d{4})(\d{2})(\d{2})/',     # /20230723/
            r'/(\d{4})(\d{2})/(\d{2})/',    # /202307/23/
            r'_(\d{4})(\d{2})(\d{2})',      # _20230723
            r'(\d{4})/(\d{2})-(\d{2})'      # 2023/07-23
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    
                    if 2000 <= year <= datetime.now().year and 1 <= month <= 12 and 1 <= day <= 31:
                        return datetime(year, month, day)
                except ValueError:
                    pass
        
        return None
    
    def get_category_url(self, category):
        """获取分类URL列表"""
        return self.category_urls.get(category, [])
    
    def extract_news_links(self, url):
        """
        从列表页提取新闻链接
        
        Args:
            url: 列表页URL
            
        Returns:
            list: 新闻链接列表
        """
        try:
            html = self.fetch_page_with_requests(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            links = []
            
            # 新浪财经常见的新闻链接选择器
            selectors = [
                'a[href*="finance.sina.com.cn"]',
                '.news-item a',
                '.news-list a',
                '.articleList a',
                '.feed-card-title a',
                '.article-list a',
                '.list-item a'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get('href')
                    if href:
                        # 规范化URL
                        href = self.normalize_url(href, url)
                        if self.is_valid_news_url(href):
                            links.append(href)
            
            # 去重并限制数量
            unique_links = list(set(links))[:50]
            
            logger.info(f"从 {url} 提取到 {len(unique_links)} 个有效新闻链接")
            return unique_links
            
        except Exception as e:
            logger.error(f"提取新闻链接失败 {url}: {str(e)}")
            return []
    
    def normalize_url(self, href, base_url):
        """
        规范化URL
        
        Args:
            href: 原始链接
            base_url: 基础URL
            
        Returns:
            str: 规范化后的URL
        """
        # 处理相对路径
        if href.startswith('//'):
            return 'https:' + href
        elif not href.startswith(('http://', 'https://')):
            return urljoin(base_url, href)
            
        return href
    
    def is_valid_news_url(self, url):
        """
        判断是否为有效的新闻URL
        
        Args:
            url: 待验证的URL
            
        Returns:
            bool: 是否为有效的新闻URL
        """
        if not url:
            return False
        
        try:
            # 必须是新浪财经相关域名
            valid_domains = [
                'finance.sina.com.cn',
                'news.sina.com.cn',
                'sina.com.cn'
            ]
            
            # 检查域名
            if not any(domain in url for domain in valid_domains):
                return False
            
            # 新闻文章URL特征
            valid_patterns = [
                r'/doc-\w+\.shtml',           # 新浪新闻文档格式
                r'/\d{4}-\d{2}-\d{2}/doc-',   # 带日期的文档
                r'\.shtml$',                  # 以shtml结尾
                r'\.html$'                    # 以html结尾
            ]
            
            # 检查是否匹配新闻URL模式
            has_valid_pattern = any(re.search(pattern, url) for pattern in valid_patterns)
            
            # 排除的URL类型
            invalid_patterns = [
                r'/index\.s?html',           # 首页
                r'/list\.s?html',            # 列表页
                r'/\w+/$',                   # 目录页
                r'javascript:',              # JS链接
                r'#',                        # 锚点链接
                r'\?.*page=',                # 分页链接
                r'/api/',                    # API接口
                r'/login',                   # 登录页
                r'/register'                 # 注册页
            ]
            
            # 检查是否包含无效模式
            has_invalid_pattern = any(re.search(pattern, url) for pattern in invalid_patterns)
            
            # 最终判断
            is_valid = has_valid_pattern and not has_invalid_pattern
            
            if is_valid:
                logger.debug(f"有效新闻URL: {url}")
            else:
                logger.debug(f"无效URL (模式不匹配): {url}")
                
            return is_valid
            
        except Exception as e:
            logger.warning(f"验证URL时出错 {url}: {e}")
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
            html = self.fetch_page_with_requests(url)
            if not html:
                logger.warning(f"获取新闻详情页失败: {url}")
                return None
            
            # 解析新闻详情
            return self._parse_news_detail(html, url, category)
                
        except Exception as e:
            logger.error(f"爬取新闻详情失败: {url}, 错误: {str(e)}")
            return None
    
    def _parse_news_detail(self, html, url, category):
        """
        解析新闻详情页面
        
        Args:
            html: 页面HTML内容
            url: 新闻URL
            category: 新闻分类
            
        Returns:
            dict: 新闻数据字典，包含标题、内容、发布时间等信息
        """
        try:
            if not html or len(html.strip()) < 100:
                logger.warning(f"页面内容太短或为空: {url}")
                return None
                
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取标题
            title = self.extract_title(soup)
            if not title or len(title.strip()) < 5:
                logger.warning(f"无法提取有效标题: {url}")
                return None
            
            # 提取内容
            content, html_content = self.extract_content(soup)
            if not content or len(content.strip()) < 50:
                logger.warning(f"无法提取有效内容或内容太短: {url}, 内容长度: {len(content) if content else 0}")
                return None
            
            # 提取发布时间
            pub_time = self.extract_pub_time(soup)
            
            # 提取作者
            author = self.extract_author(soup)
            
            # 提取关键词
            keywords = self.extract_keywords(soup, content)
            
            # 构建新闻数据
            news_data = {
                'id': self.generate_news_id(url, title),
                'title': title.strip(),
                'content': content.strip(),
                'content_html': html_content,
                'pub_time': pub_time,
                'author': author,
                'source': self.source,
                'url': url,
                'category': category,
                'keywords': ','.join(keywords) if keywords else '',
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 验证数据完整性
            if not news_data['title'] or not news_data['content']:
                logger.warning(f"新闻数据不完整: {url}")
                return None
            
            logger.info(f"成功解析新闻: {title[:50]}...")
            return news_data
            
        except Exception as e:
            logger.error(f"解析新闻详情失败 {url}: {str(e)}")
            return None
    
    def extract_title(self, soup):
        """
        提取新闻标题
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: 新闻标题
        """
        # 更新的新浪财经标题选择器
        selectors = [
            'h1.main-title',      # 新浪财经主标题
            'h1.article-title',   # 文章标题
            '.article-header h1', # 文章头部标题
            '.title h1',          # 标题容器中的h1
            'h1',                 # 通用h1
            '.headline',          # 头条
            '.news-title',        # 新闻标题
            'title'               # 页面标题作为备选
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    title = elements[0].get_text().strip()
                    if title:
                        # 清理标题 - 去除网站名称和特殊字符
                        title = re.sub(r'[-_|].*?新浪.*?$', '', title).strip()
                        title = re.sub(r'[-_|].*?财经.*?$', '', title).strip()
                        title = re.sub(r'\s*_\s*新浪网$', '', title).strip()
                        
                        # 去除前后的特殊字符
                        title = title.strip('_-|:：')
                        
                        # 检查标题有效性
                        if title and len(title) > 5 and not title.isdigit():
                            logger.debug(f"成功提取标题: {title}")
                            return title
                        
            except Exception as e:
                logger.debug(f"使用选择器 {selector} 提取标题失败: {e}")
                continue
        
        # 如果所有选择器都失败，从URL提取标题信息
        try:
            if soup.title:
                title = soup.title.get_text().strip()
                if title:
                    # 清理页面标题
                    title = re.sub(r'[-_|].*?新浪.*?$', '', title).strip()
                    title = re.sub(r'\s*_\s*新浪网$', '', title).strip()
                    title = title.strip('_-|:：')
                    
                    if title and len(title) > 5:
                        return title
        except Exception as e:
            logger.debug(f"从页面title提取标题失败: {e}")
        
        return None
    
    def extract_pub_time(self, soup):
        """
        提取发布时间
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: 发布时间
        """
        selectors = [
            '.article-time',
            '.time',
            '.pub-time',
            '.date',
            '.article-info .time',
            '.publish-time'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                time_text = elements[0].get_text().strip()
                if time_text:
                    # 清理时间文本
                    time_text = re.sub(r'发布时间[:：]?', '', time_text).strip()
                    return time_text
        
        # 尝试从meta标签获取
        meta_time = soup.find('meta', {'name': 'publishdate'})
        if meta_time and meta_time.get('content'):
            return meta_time['content']
        
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def extract_author(self, soup):
        """
        提取作者
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: 作者
        """
        selectors = [
            '.author',
            '.article-author',
            '.by-author',
            '.writer',
            '.article-info .author'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                author = elements[0].get_text().strip()
                if author:
                    # 清理作者信息
                    author = re.sub(r'作者[:：]?', '', author).strip()
                    return author
        
        return '新浪财经'
    
    def generate_news_id(self, url, title):
        """
        生成新闻ID
        
        Args:
            url: 新闻URL
            title: 新闻标题
            
        Returns:
            str: 生成的新闻ID
        """
        import hashlib
        content = f"{url}_{title}_{self.source}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def extract_content(self, soup):
        """
        提取新闻内容
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            tuple: (文本内容, HTML内容)
        """
        # 移除不需要的标签
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        
        # 更新的新浪财经内容选择器，基于真实网站结构
        selectors = [
            '#artibody',          # 新浪财经文章主体
            '.article-content',   # 通用文章内容
            '.article-body',      # 文章正文
            '.content',           # 通用内容
            '.detail-content',    # 详情内容
            '.article',           # 文章容器
            '.news-content',      # 新闻内容
            'div[class*="content"]'  # 包含content的div
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    content_element = elements[0]
                    
                    # 移除广告和无关内容
                    for ad in content_element.select('.ad, .advertisement, .app-download, .related-news, .share, .comment'):
                        ad.decompose()
                    
                    # 提取所有段落文本
                    paragraphs = content_element.find_all(['p', 'div'])
                    content_parts = []
                    
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:  # 过滤太短的文本
                            content_parts.append(text)
                    
                    if content_parts:
                        text_content = '\n\n'.join(content_parts)
                        html_content = str(content_element)
                        
                        # 最终检查内容长度
                        if len(text_content.strip()) > 100:
                            return text_content, html_content
                        
            except Exception as e:
                logger.debug(f"使用选择器 {selector} 提取内容失败: {e}")
                continue
        
        # 如果以上选择器都失败，尝试提取页面主要文本
        try:
            # 移除明显的导航和广告区域
            for tag in soup(['nav', 'header', 'footer', 'aside', '.nav', '.header', '.footer', '.sidebar']):
                if tag:
                    tag.decompose()
            
            # 查找包含最多文本的div
            divs = soup.find_all('div')
            best_div = None
            max_text_length = 0
            
            for div in divs:
                text = div.get_text(strip=True)
                if len(text) > max_text_length and len(text) > 200:
                    max_text_length = len(text)
                    best_div = div
            
            if best_div:
                text_content = best_div.get_text(strip=True)
                if len(text_content) > 100:
                    return text_content, str(best_div)
                    
        except Exception as e:
            logger.debug(f"备用内容提取方法失败: {e}")
        
        return None, None
    
    def extract_keywords(self, soup, content):
        """
        提取关键词
        
        Args:
            soup: BeautifulSoup对象
            content: 文本内容
            
        Returns:
            list: 关键词列表
        """
        keywords = []
        
        # 从meta标签获取关键词
        meta_keywords = soup.find('meta', {'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            meta_kw = meta_keywords['content'].split(',')
            keywords.extend([kw.strip() for kw in meta_kw if kw.strip()])
        
        # 从内容中提取关键词
        if content:
            extracted_kw = extract_keywords(content)
            if extracted_kw:
                keywords.extend(extracted_kw)
        
        # 去重并限制数量
        unique_keywords = list(set(keywords))[:10]
        return unique_keywords
    
    def fetch_page_with_requests(self, url, max_retries=3):
        """
        使用requests获取页面内容
        
        Args:
            url: 页面URL
            max_retries: 最大重试次数
            
        Returns:
            str: 页面HTML内容
        """
        for attempt in range(max_retries):
            try:
                headers = self.get_headers()
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=30,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # 改进编码处理
                # 首先尝试从响应头获取编码
                content_type = response.headers.get('content-type', '').lower()
                if 'charset=' in content_type:
                    charset = content_type.split('charset=')[1].split(';')[0].strip()
                    response.encoding = charset
                else:
                    # 尝试从响应内容检测编码
                    if response.content:
                        import chardet
                        detected = chardet.detect(response.content[:1024])
                        if detected and detected['encoding']:
                            response.encoding = detected['encoding']
                        else:
                            # 默认使用UTF-8
                            response.encoding = 'utf-8'
                
                # 如果仍然是ISO-8859-1，强制使用UTF-8
                if response.encoding and response.encoding.lower() in ['iso-8859-1', 'latin-1']:
                    response.encoding = 'utf-8'
                
                return response.text
                
            except Exception as e:
                logger.warning(f"获取页面失败 (尝试 {attempt + 1}/{max_retries}): {url}, 错误: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(2, 5))
                else:
                    logger.error(f"获取页面最终失败: {url}")
                    return None
        
        return None 