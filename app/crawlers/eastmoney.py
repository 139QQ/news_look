#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 东方财富网爬虫
使用requests库直接爬取，无需浏览器
"""

import os
import re
import sys
import time
import random
import logging
import hashlib
import requests
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from app.crawlers.base import BaseCrawler
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html, extract_keywords
from app.db.sqlite_manager import SQLiteManager

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('eastmoney')

class EastMoneyCrawler(BaseCrawler):
    """东方财富网爬虫，用于爬取东方财富网的财经新闻"""
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False):
        """
        初始化东方财富网爬虫
        
        Args:
            db_manager: 数据库管理器对象
            db_path: 数据库路径，如果为None则使用默认路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
        """
        # 基本属性
        self.source = "东方财富网"
        self.name = "eastmoney"
        
        # 调用父类的初始化方法
        super().__init__(db_manager=db_manager, db_path=db_path, use_proxy=use_proxy, use_source_db=use_source_db)
        
        self.status = 'idle'
        self.last_run = None
        self.next_run = None
        self.error_count = 0
        self.success_count = 0
        
        # 设置请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 分类URL映射
        self.category_urls = {
            '财经': ['https://finance.eastmoney.com/'],
            '股票': ['https://stock.eastmoney.com/'],
            '基金': ['https://fund.eastmoney.com/'],
            '债券': ['https://bond.eastmoney.com/'],
        }
        
        # 初始化数据列表
        self.news_data = []
        
        # 随机User-Agent
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        ]
        
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
        
        logger.info(f"东方财富网爬虫初始化完成，数据库路径: {self.db_path}")
    
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
        
        Args:
            category: 要爬取的新闻分类，如'财经'，'股票'等
            max_news: 最大爬取新闻数量
            days: 爬取多少天内的新闻
            use_selenium: 是否使用Selenium爬取，默认False使用requests
            
        Returns:
            list: 爬取到的新闻列表
        """
        # selenium参数在简化版中被忽略，为了保持接口兼容而保留
        try:
            # 确定要爬取的分类
            categories_to_crawl = []
            if category:
                if category in self.category_urls:
                    categories_to_crawl = [category]
                else:
                    logger.warning(f"未知分类: {category}，将使用默认分类'财经'")
                    categories_to_crawl = ['财经']
            else:
                # 默认爬取所有分类
                categories_to_crawl = list(self.category_urls.keys())
            
            # 爬取结果
            news_list = []
            
            # 爬取每个分类
            for cat in categories_to_crawl:
                logger.info(f"开始爬取'{cat}'分类的新闻")
                cat_news = self._crawl_category(cat, max_news, days)
                news_list.extend(cat_news)
                
                # 如果已达到最大数量，停止爬取
                if len(news_list) >= max_news:
                    logger.info(f"已达到最大爬取数量({max_news})，停止爬取")
                    break
            
            logger.info(f"爬取完成，共获取{len(news_list)}条新闻")
            
            # 爬取结束后，确保数据被保存到数据库
            if hasattr(self, 'news_data') and self.news_data:
                saved_count = 0
                for news in self.news_data:
                    if self.save_news_to_db(news):
                        saved_count += 1
                
                logger.info(f"成功保存 {saved_count}/{len(self.news_data)} 条新闻到数据库")
            
            return news_list
        
        except Exception as e:
            logger.error(f"爬取过程发生错误: {str(e)}")
            return []
    
    def _crawl_category(self, category, max_news, days):
        """
        爬取特定分类的新闻
        
        Args:
            category: 分类名称
            max_news: 最大爬取数量
            days: 爬取天数
            
        Returns:
            list: 该分类下爬取到的新闻列表
        """
        news_list = []
        
        # 获取该分类的URL列表
        urls = self.category_urls.get(category, [])
        if not urls:
            logger.warning(f"分类'{category}'没有对应的URL")
            return []
        
        # 爬取每个URL
        for url in urls:
            # 如果已达到最大数量，停止爬取
            if len(news_list) >= max_news:
                break
            
            try:
                # 获取新闻链接
                logger.info(f"从 {url} 提取新闻链接")
                news_links = self.extract_news_links(url)
                
                # 随机排序链接，增加多样性
                random.shuffle(news_links)
                
                # 爬取每个新闻详情
                for link in news_links:
                    # 如果已达到最大数量，停止爬取
                    if len(news_list) >= max_news:
                        break
                    
                    # 爬取新闻详情
                    news = self.crawl_news_detail(link, category)
                    
                    # 如果成功爬取，检查日期并添加到结果列表
                    if news:
                        try:
                            # 解析发布时间
                            pub_time = datetime.strptime(news['pub_time'], '%Y-%m-%d %H:%M:%S')
                            
                            # 计算日期范围
                            date_limit = datetime.now() - timedelta(days=days)
                            
                            # 检查日期是否在范围内
                            if pub_time >= date_limit:
                                # 保存到结果列表
                                news_list.append(news)
                                
                                # 保存到数据库
                                try:
                                    self.save_news_to_db(news)
                                    logger.info(f"已将新闻保存到数据库: {news['title']}")
                                except Exception as e:
                                    logger.error(f"保存新闻到数据库失败: {news['title']}, 错误: {str(e)}")
                                
                                # 如果达到最大新闻数，跳出循环
                                if len(news_list) >= max_news:
                                    break
                            else:
                                logger.info(f"新闻发布日期 {pub_time} 不在范围内，跳过")
                        
                        except Exception as e:
                            logger.warning(f"处理新闻日期失败: {str(e)}")
                        
                        # 随机延迟，避免请求过于频繁
                        time.sleep(random.uniform(1, 3))
            
            except Exception as e:
                logger.error(f"从 {url} 提取新闻链接失败: {str(e)}")
        
        logger.info(f"分类'{category}'爬取完成，共获取{len(news_list)}条新闻")
        return news_list
    
    def extract_news_links(self, url):
        """
        从页面中提取新闻链接
        
        Args:
            url: 页面URL
            
        Returns:
            list: 新闻链接列表
        """
        try:
            # 发送请求
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            response.encoding = 'utf-8'  # 确保编码正确
            
            # 检查响应状态
            if response.status_code != 200:
                logger.warning(f"请求失败，状态码: {response.status_code}")
                return []
            
            # 解析HTML并提取链接
            return self._parse_html_for_links(response.text, url)
            
        except Exception as e:
            logger.error(f"提取新闻链接失败: {str(e)}")
            return []
    
    def _parse_html_for_links(self, html, base_url):
        """
        解析HTML提取链接
        
        Args:
            html: HTML内容
            base_url: 基础URL用于相对链接转绝对链接
            
        Returns:
            list: 新闻链接列表
        """
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # 提取所有链接
        links = soup.find_all('a', href=True)
        
        # 过滤有效的新闻链接
        news_links = []
        for link in links:
            href = link.get('href')
            
            # 确保链接不为空
            if not href:
                continue
            
            # 规范化链接
            if href.startswith('//'):
                href = 'https:' + href
            elif not href.startswith(('http://', 'https://')):
                href = urljoin(base_url, href)
            
            # 检查是否是有效的新闻链接
            if self.is_valid_news_url(href):
                # 确保链接不重复
                if href not in news_links:
                    news_links.append(href)
        
        logger.info(f"从 {base_url} 提取到 {len(news_links)} 条有效新闻链接")
        return news_links
    
    def is_valid_news_url(self, url):
        """
        判断URL是否是有效的新闻链接
        
        Args:
            url: URL
            
        Returns:
            bool: 是否是有效的新闻链接
        """
        # 检查是否是东方财富网的链接
        if not any(domain in url for domain in [
            'eastmoney.com',
            'finance.eastmoney.com',
            'stock.eastmoney.com',
            'fund.eastmoney.com',
            'bond.eastmoney.com'
        ]):
            return False
        
        # 排除非新闻页面
        if any(keyword in url for keyword in [
            'list', 'index.html', 'search', 'help', 'about', 'contact',
            'login', 'register', 'download', 'app'
        ]):
            return False
        
        # 检查URL是否包含年份数字（通常新闻URL包含发布日期）
        if not re.search(r'/20\d{2}', url):
            return False
        
        # 检查URL是否是新闻页面（通常包含/a/、/news/等路径）
        if not any(path in url for path in ['/a/', '/news/', '/article/', '/content/']):
            return False
        
        return True
    
    def crawl_news_detail(self, url, category):
        """
        爬取新闻详情
        
        Args:
            url: 新闻URL
            category: 新闻分类
            
        Returns:
            dict: 新闻详情
        """
        try:
            # 发送请求
            logger.info(f"爬取新闻详情: {url}")
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            response.encoding = 'utf-8'  # 确保编码正确
            
            # 检查响应状态
            if response.status_code != 200:
                logger.warning(f"请求失败，状态码: {response.status_code}")
                return None
            
            # 解析新闻详情
            return self._parse_news_detail(response.text, url, category)
            
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
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # 提取标题
        title = self.extract_title(soup)
        if not title:
            logger.warning(f"未能提取到标题: {url}")
            return None
        
        # 提取发布时间
        pub_time = self.extract_pub_time(soup)
        if not pub_time:
            # 如果无法提取时间，使用当前时间
            pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.warning(f"未能提取到发布时间，使用当前时间: {pub_time}")
        
        # 提取作者
        author = self.extract_author(soup)
        if not author:
            author = "东方财富网"
        
        # 提取内容
        content = self.extract_content(soup)
        if not content or len(content) < 100:  # 内容太短可能是提取失败
            logger.warning(f"未能提取到有效内容: {url}")
            return None
        
        # 提取关键词
        keywords = self.extract_keywords(soup, content)
        
        # 生成新闻ID
        news_id = hashlib.md5(url.encode('utf-8')).hexdigest()
        
        # 构建新闻对象
        news = {
            'id': news_id,
            'url': url,
            'title': title,
            'content': content,
            'pub_time': pub_time,
            'author': author,
            'keywords': ','.join(keywords) if keywords else '',
            'sentiment': '中性',  # 默认情感
            'category': category,
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': self.source
        }
        
        logger.info(f"成功爬取新闻: {title}")
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
            'div.article-meta span:nth-child(2)'
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
        提取新闻内容
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: 新闻内容
        """
        # 尝试常见的内容选择器
        selectors = [
            'div.article-content',
            'div.contentbox',
            'div.detail-content',
            'div#ContentBody',
            'div.Body',
            'div.content',
            'article'
        ]
        
        content = None
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                content_element = elements[0]
                
                # 移除不需要的元素
                for tag in content_element.select('script, style, iframe, .share, .related, .advertisement, .recommend, .footer, .copyright, .statement'):
                    tag.decompose()
                
                # 提取段落文本
                paragraphs = content_element.select('p')
                
                # 如果找到段落，组合段落内容
                if paragraphs:
                    content = '\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                    if content:
                        break
                
                # 如果没有找到段落，直接使用内容元素的文本
                content = content_element.get_text().strip()
                break
        
        # 如果常规方法失败，尝试提取所有段落
        if not content:
            paragraphs = soup.select('p')
            valid_paragraphs = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20]
            
            if valid_paragraphs:
                content = '\n'.join(valid_paragraphs)
        
        # 如果没有提取到内容，返回None
        if not content:
            return None
            
        # 过滤广告和无关内容
        filtered_content = self.filter_advertisements(content)
        return filtered_content
    
    def filter_advertisements(self, content):
        """
        过滤广告和无关内容
        
        Args:
            content: 原始内容文本
            
        Returns:
            str: 过滤后的内容
        """
        if not content:
            return content
            
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
        filtered_content = content
        for pattern in ad_patterns:
            filtered_content = re.sub(pattern, '', filtered_content, flags=re.DOTALL)
        
        # 移除空行和多余的空格
        lines = filtered_content.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        filtered_content = '\n'.join(cleaned_lines)
        
        # 移除重复的分隔线
        filtered_content = re.sub(r'[-_=]{3,}', '', filtered_content)
        
        # 移除过短的行（可能是残留的广告片段）
        lines = filtered_content.split('\n')
        content_lines = [line for line in lines if len(line) > 5 or re.search(r'\d{4}-\d{2}-\d{2}', line)]
        filtered_content = '\n'.join(content_lines)
        
        return filtered_content
    
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
        获取分类页面URL
        
        Args:
            category: 分类名称
            
        Returns:
            str: 分类页面URL
        """
        # 定义各个分类对应的URL
        category_urls = {
            'stock': 'https://finance.eastmoney.com/a/cgnjj.html',
            'finance': 'https://finance.eastmoney.com/a/czqyw.html',
            'global': 'https://finance.eastmoney.com/a/cgjjj.html',
            'forex': 'https://finance.eastmoney.com/a/chgjj.html',
            'bond': 'https://finance.eastmoney.com/a/czqzx.html'
        }
        
        # 如果分类不存在，使用默认分类
        if category not in category_urls:
            logger.warning(f"未找到分类 {category} 的URL，使用默认财经分类")
            return category_urls['finance']
        
        return category_urls[category]
    
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
            logger.error(f"保存新闻到数据库失败: {news.get('title', '未知标题')}, 错误: {str(e)}")
            return False

def main():
    """测试爬虫功能"""
    from app.db.sqlite_manager import SQLiteManager
    
    # 创建数据库管理器
    db_manager = SQLiteManager('./data/news.db')
    
    # 创建爬虫实例
    crawler = EastMoneyCrawler(db_manager)
    
    # 爬取财经新闻
    crawler.crawl(category='财经', max_news=3)
    
    print("爬取完成")

if __name__ == '__main__':
    main()
