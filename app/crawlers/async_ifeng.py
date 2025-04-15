#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 凤凰财经异步爬虫
使用aiohttp库实现异步爬取，提高效率
"""

import os
import re
import sys
import time
import random
import asyncio
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from app.crawlers.async_crawler import AsyncCrawler
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html, extract_keywords
from app.utils.ad_filter import AdFilter

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('凤凰财经_异步')

class AsyncIfengCrawler(AsyncCrawler):
    """凤凰财经异步爬虫，用于高效爬取凤凰财经的财经新闻"""
    
    # 新闻分类URL
    CATEGORY_URLS = {
        '首页': 'https://finance.ifeng.com/',
        '股票': 'https://finance.ifeng.com/stock/',
        '理财': 'https://finance.ifeng.com/money/',
        '宏观': 'https://finance.ifeng.com/macro/',
        '国际': 'https://finance.ifeng.com/world/',
        '公司': 'https://finance.ifeng.com/company/',
    }
    
    # 选择器
    CONTENT_SELECTOR = 'div.main_content, div.text, article.article-main'
    TITLE_SELECTOR = 'h1.headline-title, h1.yc-title, h1.topic-title, h1.o-tit'
    TIME_SELECTOR = 'span.ss01, span.time, .ar-time'
    AUTHOR_SELECTOR = 'span.ss03, p.source, .ar-from'
    
    # 常用的浏览器用户代理
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    ]
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, 
                 max_concurrency=5, timeout=30, **kwargs):
        """
        初始化凤凰财经异步爬虫
        
        Args:
            db_manager: 数据库管理器对象
            db_path: 数据库路径，如果为None则使用默认路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
            max_concurrency: 最大并发请求数
            timeout: 请求超时时间（秒）
            **kwargs: 其他参数
        """
        self.source = "凤凰财经"
        super().__init__(
            db_manager=db_manager, 
            db_path=db_path, 
            use_proxy=use_proxy, 
            use_source_db=use_source_db,
            max_concurrency=max_concurrency,
            timeout=timeout,
            **kwargs
        )
        
        # 广告过滤器
        self.ad_filter = AdFilter(source_name=self.source)
        
        logger.info(f"凤凰财经异步爬虫初始化完成，数据库路径: {self.db_path}")
    
    def get_headers(self):
        """获取HTTP请求头"""
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://finance.ifeng.com/',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
    
    async def _crawl_implementation(self, days, max_news, start_date, **kwargs):
        """
        异步爬取实现
        
        Args:
            days: 爬取的天数范围
            max_news: 最多爬取的新闻数量
            start_date: 开始日期
            **kwargs: 其他参数
        """
        category = kwargs.get('category', None)
        
        # 先尝试从首页获取新闻
        if category is None or category == '首页':
            try:
                logger.info("尝试从首页获取新闻")
                home_url = self.CATEGORY_URLS['首页']
                await self._process_category_page(home_url, '首页', max_news, start_date)
            except Exception as e:
                logger.error(f"从首页获取新闻失败: {str(e)}")
        
        # 爬取指定分类或所有分类的新闻
        categories = [category] if category else self.CATEGORY_URLS.keys()
        for cat in categories:
            if cat not in self.CATEGORY_URLS:
                logger.warning(f"未知分类: {cat}")
                continue
                
            # 跳过已经处理过的首页
            if cat == '首页' and (category is None or category == '首页'):
                continue
                
            try:
                logger.info(f"爬取分类: {cat}")
                url = self.CATEGORY_URLS[cat]
                await self._process_category_page(url, cat, max_news, start_date)
            except Exception as e:
                logger.error(f"爬取分类 {cat} 失败: {str(e)}")
    
    async def _process_category_page(self, url, category, max_news, start_date):
        """
        处理分类页面
        
        Args:
            url: 分类页面URL
            category: 分类名称
            max_news: 最大爬取新闻数量
            start_date: 开始日期
        """
        try:
            logger.info(f"爬取分类页面: {url}, 分类: {category}")
            
            # 获取页面内容
            html = await self.async_fetch_page(url)
            if not html:
                logger.warning(f"获取分类页面失败: {url}")
                return
            
            # 提取新闻链接
            news_links = self._extract_news_links(html)
            logger.info(f"从分类 {category} 提取到 {len(news_links)} 个新闻链接")
            
            # 对链接进行去重和过滤
            news_links = list(set(news_links))
            valid_links = [link for link in news_links if self._is_valid_news_url(link)]
            logger.info(f"分类 {category} 有效链接数量: {len(valid_links)}")
            
            # 限制爬取的链接数量
            remaining = max_news - len(self.news_data)
            if remaining <= 0:
                return
            
            links_to_crawl = valid_links[:remaining]
            
            # 并发爬取新闻详情
            tasks = []
            for link in links_to_crawl:
                tasks.append(self._crawl_news_detail(link, category, start_date))
            
            # 等待所有任务完成
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"处理分类页面出错: {url}, 分类: {category}, 错误: {str(e)}")
    
    def _extract_news_links(self, html):
        """
        从HTML中提取新闻链接
        
        Args:
            html: HTML内容
            
        Returns:
            list: 新闻链接列表
        """
        if not html:
            return []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            links = []
            
            # 提取所有链接
            for a in soup.find_all('a', href=True):
                href = a.get('href', '').strip()
                
                # 忽略空链接或JavaScript链接
                if not href or href.startswith('javascript:') or href == '#':
                    continue
                
                # 转换相对URL为绝对URL
                if not href.startswith('http'):
                    if href.startswith('//'):
                        href = 'https:' + href
                    else:
                        # 解析当前页面的基础URL
                        base_url = 'https://finance.ifeng.com'
                        href = urljoin(base_url, href)
                
                links.append(href)
            
            return links
        except Exception as e:
            logger.error(f"提取新闻链接失败: {str(e)}")
            return []
    
    def _is_valid_news_url(self, url):
        """
        判断URL是否为有效的新闻链接
        
        Args:
            url: 链接URL
            
        Returns:
            bool: 是否为有效的新闻链接
        """
        # 检查URL是否为空
        if not url:
            return False
            
        # 检查URL是否为广告
        if self.ad_filter.is_ad_url(url):
            logger.info(f"过滤广告URL：{url}")
            return False
            
        # 凤凰财经新闻URL通常包含以下特征
        patterns = [
            r'https?://finance\.ifeng\.com/\w/\d+/\d+_\d+\.shtml',
            r'https?://finance\.ifeng\.com/c/\w+',
            r'https?://finance\.ifeng\.com/a/\d+/\d+_\d+\.shtml',
        ]
        
        for pattern in patterns:
            if re.match(pattern, url):
                return True
        
        return False
    
    async def _crawl_news_detail(self, url, category, start_date):
        """
        异步爬取新闻详情
        
        Args:
            url: 新闻URL
            category: 新闻分类
            start_date: 开始日期
            
        Returns:
            dict: 新闻详情
        """
        try:
            logger.info(f"爬取新闻详情: {url}")
            
            # 获取页面内容
            html = await self.async_fetch_page(url)
            if not html:
                logger.warning(f"获取新闻详情失败: {url}")
                return None
            
            # 解析新闻详情
            news_data = self._parse_news_detail(html, url, category)
            
            if not news_data:
                logger.warning(f"解析新闻详情失败: {url}")
                return None
            
            # 检查新闻日期是否在指定范围内
            try:
                pub_time = news_data.get('pub_time', '')
                if pub_time:
                    news_date = datetime.strptime(pub_time.split(' ')[0], '%Y-%m-%d')
                    if news_date < start_date:
                        logger.info(f"新闻日期 {news_date} 早于起始日期 {start_date}，跳过")
                        return None
            except Exception as e:
                logger.warning(f"解析新闻日期失败: {pub_time}, 错误: {str(e)}")
            
            # 保存新闻数据
            self.news_data.append(news_data)
            
            # 保存到数据库
            self.save_news(news_data)
            
            logger.info(f"爬取新闻成功: {news_data.get('title', '未知标题')}")
            return news_data
            
        except Exception as e:
            logger.error(f"爬取新闻详情失败: {url}, 错误: {str(e)}")
            return None
    
    def _parse_news_detail(self, html, url, category):
        """
        解析新闻详情
        
        Args:
            html: HTML内容
            url: 新闻URL
            category: 新闻分类
            
        Returns:
            dict: 新闻详情
        """
        if not html:
            return None
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取标题
            title_elem = soup.select_one(self.TITLE_SELECTOR)
            if not title_elem:
                # 尝试其他可能的标题选择器
                title_elem = soup.find('h1')
                if not title_elem:
                    logger.warning(f"未找到标题：{url}")
                    return None
            
            title = title_elem.text.strip()
            if not title:
                logger.warning(f"标题为空：{url}")
                return None
            
            # 提取发布时间
            pub_time = self._extract_pub_time(soup)
            
            # 提取作者
            author = self._extract_author(soup)
            
            # 提取内容
            content_elem = soup.select_one(self.CONTENT_SELECTOR)
            if not content_elem:
                logger.warning(f"未找到内容：{url}")
                return None
            
            # 清理内容
            # 删除广告、推荐阅读等不需要的元素
            for selector in ['.advertise', '.recommand', '.share', '.bottom-share', '.adv', '.c-relate-news']:
                for elem in content_elem.select(selector):
                    elem.decompose()
            
            # 清理HTML标签，获取纯文本内容
            content = clean_html(str(content_elem))
            
            # 如果内容太短，可能是特殊页面
            if len(content) < 100:
                logger.warning(f"内容太短，可能是特殊页面: {url}")
                # 尝试查找更多内容
                more_content_elem = soup.select_one('.mainContent, .article-main-content, .all-txt')
                if more_content_elem:
                    more_content = clean_html(str(more_content_elem))
                    if len(more_content) > len(content):
                        content = more_content
            
            # 如果内容仍然太短，可能是特殊页面
            if len(content) < 100:
                logger.warning(f"内容仍然太短，可能是特殊页面: {url}")
                # 尝试查找iframe
                iframes = soup.find_all('iframe')
                if iframes:
                    iframe_srcs = [iframe.get('src', '') for iframe in iframes]
                    logger.info(f"页面包含iframe: {iframe_srcs}")
                    content = f"[此页面可能包含嵌入内容] {content}"
            
            # 提取图片
            images = []
            for img in content_elem.find_all('img'):
                img_url = img.get('src', '')
                if img_url:
                    # 确保是完整的URL
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif not img_url.startswith('http'):
                        img_url = urljoin('https://finance.ifeng.com', img_url)
                    
                    images.append(img_url)
            
            # 提取关键词
            keywords = extract_keywords(title + ' ' + content)
            
            # 提取相关股票
            related_stocks = self._extract_related_stocks(soup)
            
            # 生成新闻ID
            news_id = self._generate_news_id(url, title)
            
            # 构建新闻数据
            news_data = {
                'id': news_id,
                'title': title,
                'content': content,
                'pub_time': pub_time,
                'author': author,
                'source': self.source,
                'url': url,
                'category': category,
                'keywords': ','.join(keywords) if keywords else '',
                'images': ','.join(images) if images else '',
                'related_stocks': ','.join(related_stocks) if related_stocks else '',
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return news_data
            
        except Exception as e:
            logger.error(f"解析新闻详情失败: {url}, 错误: {str(e)}")
            return None
    
    def _extract_pub_time(self, soup):
        """
        提取发布时间
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: 发布时间
        """
        try:
            time_tag = soup.select_one(self.TIME_SELECTOR)
            if not time_tag:
                return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            time_text = time_tag.text.strip()
            
            # 使用正则表达式提取时间
            time_pattern = r'(\d{4})年(\d{2})月(\d{2})日\s+(\d{2}):(\d{2})'
            match = re.search(time_pattern, time_text)
            if match:
                year, month, day, hour, minute = match.groups()
                return f"{year}-{month}-{day} {hour}:{minute}:00"
            
            # 尝试其他时间格式
            time_pattern2 = r'(\d{4})[/-](\d{2})[/-](\d{2})\s+(\d{2}):(\d{2})'
            match = re.search(time_pattern2, time_text)
            if match:
                year, month, day, hour, minute = match.groups()
                return f"{year}-{month}-{day} {hour}:{minute}:00"
            
            # 如果没有匹配到时间，使用当前时间
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.warning(f"提取发布时间失败：{str(e)}")
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _extract_author(self, soup):
        """
        提取作者
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: 作者
        """
        try:
            author_tag = soup.select_one(self.AUTHOR_SELECTOR)
            if not author_tag:
                return "凤凰财经"
            
            author_text = author_tag.text.strip()
            
            # 使用正则表达式提取来源
            source_pattern = r'来源：(.*)'
            match = re.search(source_pattern, author_text)
            if match:
                return match.group(1).strip()
            
            return author_text or "凤凰财经"
        except Exception as e:
            logger.warning(f"提取作者失败：{str(e)}")
            return "凤凰财经"
    
    def _extract_related_stocks(self, soup):
        """
        提取相关股票
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            list: 相关股票列表
        """
        related_stocks = []
        
        try:
            # 查找股票代码正则表达式
            stock_patterns = [
                r'(\d{6})\.SH',  # 上海证券交易所
                r'(\d{6})\.SZ',  # 深圳证券交易所
                r'(\d{6})\.SHE',
                r'(\d{6})\.SZE',
                r'(\d{6})\(沪\)',
                r'(\d{6})\(深\)',
                r'股票(\d{6})',
                r'个股(\d{6})'
            ]
            
            # 在整个页面中搜索股票代码
            text = soup.get_text()
            for pattern in stock_patterns:
                matches = re.findall(pattern, text)
                related_stocks.extend(matches)
            
            # 从特定标签中查找
            stock_tags = soup.select('.stock-code, .stock_code, .stockCode, .hq_code')
            for tag in stock_tags:
                text = tag.text
                code_match = re.search(r'(\d{6})', text)
                if code_match:
                    related_stocks.append(code_match.group(1))
            
            # 去重
            related_stocks = list(set(related_stocks))
            
        except Exception as e:
            logger.warning(f"提取相关股票失败: {str(e)}")
        
        return related_stocks
    
    def _generate_news_id(self, url, title):
        """
        生成新闻唯一ID
        
        Args:
            url: 新闻URL
            title: 新闻标题
            
        Returns:
            str: 新闻唯一ID
        """
        # 尝试从URL中提取ID
        id_match = re.search(r'/(\w+/\d+/\d+_\d+)\.shtml', url)
        if id_match:
            return f"ifeng_{id_match.group(1).replace('/', '_')}"
        
        # 使用URL和标题的组合生成哈希值
        unique_string = f"{url}_{title}_{self.source}"
        return f"ifeng_{hashlib.md5(unique_string.encode('utf-8')).hexdigest()}"
    
    def _fallback_sync_crawl(self, days, max_news, **kwargs):
        """
        同步爬取回退方案
        
        Args:
            days: 爬取的天数范围
            max_news: 最多爬取的新闻数量
            **kwargs: 其他参数
            
        Returns:
            list: 爬取的新闻列表
        """
        from app.crawlers.ifeng import IfengCrawler
        
        logger.info("回退到同步爬取方式...")
        
        # 创建同步爬虫实例
        sync_crawler = IfengCrawler(
            db_manager=self.db_manager, 
            db_path=self.db_path, 
            use_proxy=self.use_proxy, 
            use_source_db=True
        )
        
        # 执行同步爬取
        category = kwargs.get('category', None)
        return sync_crawler.crawl(days=days, max_news=max_news)


if __name__ == "__main__":
    # 测试异步爬虫
    crawler = AsyncIfengCrawler(use_source_db=True)
    news_list = crawler.crawl(days=1, max_news=10)
    print(f"爬取到 {len(news_list)} 条新闻")
    for news in news_list[:3]:  # 打印前3条新闻
        print(f"标题: {news['title']}")
        print(f"日期: {news['pub_time']}")
        print(f"URL: {news['url']}")
        print("-" * 50) 