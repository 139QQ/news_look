#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 网易财经爬虫
"""

import os
import re
import sys
import time
import json
import random
import hashlib
import logging
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from app.crawlers.base import BaseCrawler
from app.utils.logger import get_crawler_logger, configure_logger
from app.utils.text_cleaner import clean_html, extract_keywords
from app.db.sqlite_manager import SQLiteManager
from app.utils.ad_filter import AdFilter  # 导入广告过滤器模块
from app.utils.image_detector import ImageDetector  # 导入图像识别模块

# 初始化日志记录器
logger = get_crawler_logger('netease')

class NeteaseCrawler(BaseCrawler):
    """网易财经爬虫，用于爬取网易财经的财经新闻"""
    
    # 新闻分类URL - 仅保留财经核心版块
    CATEGORY_URLS = {
        '财经': 'https://money.163.com/',
        '股票': 'https://money.163.com/stock/',
        '基金': 'https://money.163.com/fund/',
        '期货': 'https://money.163.com/futures/',
        '外汇': 'https://money.163.com/forex/'
    }
    
    # API接口
    API_URLS = {
        '股票': 'https://money.163.com/special/00259BVP/news_json.js',
        '理财': 'https://money.163.com/special/00259BVP/licai_json.js',
        '基金': 'https://money.163.com/special/00259BVP/fund_json.js'
    }
    
    # 内容选择器 - 保留主要选择器
    CONTENT_SELECTORS = [
        'div.post_body',
        'div#endText'
    ]
    
    # 时间选择器 - 保留主要选择器
    TIME_SELECTORS = [
        'div.post_time_source',
        'div.post_info'
    ]
    
    # 作者选择器 - 保留主要选择器
    AUTHOR_SELECTORS = [
        'div.post_time_source span',
        'span.source'
    ]
    
    # URL过滤规则
    FILTER_PATTERNS = [
        r'/api/',           # API接口
        r'\?.*=',          # 带有动态参数的URL
        r'/login',         # 登录相关
        r'/register',      # 注册相关
        r'/mobile',        # 移动端
        r'/app',           # 应用相关
        r'/service',       # 内部服务
        r'/admin',         # 管理后台
        r'/manage',        # 管理相关
        r'/download',      # 下载相关
        r'/special',       # 专题页面
        r'/ent',          # 娱乐
        r'/sports',       # 体育
        r'/tech',         # 科技
        r'/auto',         # 汽车
        r'/war',          # 军事
        r'/dy',           # 订阅
        r'/sdk',          # SDK相关
        r'/oauth'         # 认证相关
    ]
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, **kwargs):
        """
        初始化网易财经爬虫
        
        Args:
            db_manager: 数据库管理器对象
            db_path: 数据库路径 (BaseCrawler handles default)
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库 (BaseCrawler handles interpretation)
            **kwargs: Additional arguments for BaseCrawler
        """
        self.source = "网易财经" # Define source before calling super
        
        # Initialize BaseCrawler first
        # Pass source, db_manager, db_path, use_proxy etc.
        super().__init__(
            db_manager=db_manager,
            db_path=db_path, # Let BaseCrawler handle defaulting if None
            use_proxy=use_proxy,
            use_source_db=use_source_db,
            source=self.source, # Pass the source
            **kwargs
        )
        
        # Initialize Netease-specific components
        self.ad_filter = AdFilter(source_name=self.source)
        self.image_detector = ImageDetector(cache_dir='./image_cache') # Consider making cache_dir configurable
        
        # Use BaseCrawler's session, potentially configuring it if needed
        # self.session = requests.Session() # REMOVE - Use super().session
        # Configure BaseCrawler's session headers if necessary
        self.session.headers.update(self.get_browser_headers())
        
        # Setup Netease-specific logger (optional, if more control needed than BaseCrawler's logger)
        # self.setup_logger() # Review if BaseCrawler logger is sufficient
        # Use BaseCrawler's logger by default, or assign the specific one if needed
        self.logger = logger # Assign module-level logger to instance logger

        # Remove redundant db manager setup - rely on self.db_manager from BaseCrawler
        # if not isinstance(self.db_manager, SQLiteManager):
        #     self.sqlite_manager = SQLiteManager(self.db_path)
        # else:
        #     self.sqlite_manager = self.db_manager
        
        # self.proxy_manager = None # BaseCrawler initializes proxy_manager if use_proxy=True
        
        self.logger.info(f"网易财经爬虫 ({self.source}) 初始化完成. DB Manager: {type(self.db_manager).__name__}, DB Path from Manager: {getattr(self.db_manager, 'db_path', 'N/A')}")
    
    def get_browser_headers(self):
        """获取模拟浏览器的请求头"""
        return {
            'User-Agent': self.get_random_ua(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://money.163.com/'
        }
    
    def get_random_ua(self):
        """获取随机User-Agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
        ]
        return random.choice(user_agents)
    
    def fetch_page(self, url, params=None, headers=None, max_retries=None, timeout=None):
        """
        获取页面内容 (使用BaseCrawler的实现)
        
        Args:
            url (str): 页面URL
            params (Optional[Dict]): 请求参数.
            headers (Optional[Dict]): 请求头 (如果为None，将使用BaseCrawler的默认头).
            max_retries (Optional[int]): 最大重试次数 (如果为None，使用BaseCrawler默认).
            timeout (Optional[int]): 超时时间 (如果为None，使用BaseCrawler默认).
            
        Returns:
            Optional[str]: 页面内容 (UTF-8)，获取失败则返回None
        """
        self.logger.debug(f"[NeteaseCrawler.fetch_page] Calling super().fetch_page() for URL: {url}")
        try:
            return super().fetch_page(url, params=params, headers=headers, max_retries=max_retries, timeout=timeout)
            except Exception as e:
            self.logger.error(f"[NeteaseCrawler.fetch_page] Error calling super().fetch_page() for {url}: {e}", exc_info=True)
        return None
    
    def is_valid_url(self, url):
        """
        检查URL是否有效
        
        Args:
            url: 要检查的URL
            
        Returns:
            bool: URL是否有效
        """
        if not url:
            return False
            
        # 检查是否是网易财经的URL
        if not url.startswith(('http://money.163.com', 'https://money.163.com')):
            return False
            
        # 检查是否包含需要过滤的模式
        for pattern in self.FILTER_PATTERNS:
            if re.search(pattern, url):
                return False
                
        # 检查是否是新闻文章URL
        if not re.search(r'/\d{2}/\d{4}/', url):  # 新闻URL通常包含日期格式
            return False
            
        return True

    def extract_news_links_from_home(self, html, category):
        """
        从首页提取新闻链接
        
        Args:
            html: 首页HTML内容
            category: 新闻分类
            
        Returns:
            list: 新闻链接列表
        """
        if not html:
            self.logger.warning("首页HTML内容为空，无法提取新闻链接")
            return []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            news_links = []
            
            # 提取所有可能的新闻链接
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                
                # 过滤无效链接
                if not href or not isinstance(href, str):
                    continue
                
                # 确保是完整的URL
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    href = 'https://money.163.com' + href
                
                # 检查URL是否有效
                if self.is_valid_url(href):
                    news_links.append(href)
            
            # 去重
            news_links = list(set(news_links))
            
            self.logger.info(f"从{category}分类首页提取到{len(news_links)}个有效新闻链接")
            return news_links
            
        except Exception as e:
            self.logger.error(f"提取新闻链接时发生错误: {str(e)}")
            return []
    
    def extract_news_links(self, html, category):
        """
        从分类页面提取新闻链接
        
        Args:
            html: 分类页面HTML内容
            category: 新闻分类
            
        Returns:
            list: 新闻链接列表
        """
        if not html:
            self.logger.warning(f"分类 {category} 页面HTML内容为空，无法提取新闻链接")
            return []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            news_links = []
            
            # 根据不同分类使用不同的选择器
            if category == '财经':
                # 财经分类页面的新闻链接通常在特定区域
                news_containers = soup.select('.news_article, .list_item, .news-item, .news_item')
                if not news_containers:
                    # 如果没有找到特定容器，尝试查找所有链接
                    news_containers = soup.find_all('a', href=True)
            else:
                # 其他分类页面的通用选择器
                news_containers = soup.select('.list_item, .news-item, .item, article')
                if not news_containers:
                    # 如果没有找到特定容器，尝试查找所有链接
                    news_containers = soup.find_all('a', href=True)
            
            # 从容器中提取链接
            for container in news_containers:
                # 如果容器本身是链接
                if container.name == 'a' and container.has_attr('href'):
                    href = container.get('href', '')
                else:
                    # 否则在容器中查找链接
                    link = container.find('a', href=True)
                    if not link:
                        continue
                    href = link.get('href', '')
                
                # 过滤链接
                if not href or not isinstance(href, str):
                    continue
                
                # 确保是完整的URL
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    href = 'https://money.163.com' + href
                
                # 检查是否是新闻链接
                if '/article/' in href:
                    # 移除广告过滤
                    # if '/article/' in href and not self.ad_filter.is_ad(href, container.text):
                    news_links.append(href)
            
            self.logger.info(f"从分类 {category} 页面提取到 {len(news_links)} 个新闻链接")
            return news_links
        except Exception as e:
            self.logger.error(f"从分类 {category} 页面提取新闻链接失败: {str(e)}")
            return []
    
    def extract_news_detail(self, url, category):
        """
        提取新闻详情
        
        Args:
            url: 新闻URL
            category: 新闻分类
            
        Returns:
            dict: 新闻详情
        """
        self.logger.info(f"开始提取新闻详情: {url}")
        
        # 获取页面内容
        html = self.fetch_page(url)
        if not html:
            self.logger.warning(f"获取新闻页面失败: {url}")
            return None
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取标题
            title_elem = soup.select_one('.post_title')
            if not title_elem:
                self.logger.warning(f"未找到标题元素: {url}")
                return None
            
            title = title_elem.text.strip()
            
            # 提取发布时间
            time_elem = soup.select_one('.post_time')
            if not time_elem:
                self.logger.warning(f"未找到时间元素: {url}")
                pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                pub_time = time_elem.text.strip()
                # 尝试规范化时间格式
                try:
                    if len(pub_time) <= 10:  # 只有日期
                        pub_time = f"{pub_time} 00:00:00"
                except:
                    pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 提取作者
            source_elem = soup.select_one('.post_source')
            if source_elem:
                author = source_elem.text.strip()
            else:
                author = "网易财经"
            
            # 提取内容
            content_elem = soup.select_one('#content')
            if not content_elem:
                self.logger.warning(f"未找到内容元素: {url}")
                return None
            
            # 移除内容中的广告
            for ad in content_elem.select('.gg200x300'):
                ad.decompose()
            
            # 获取所有段落
            paragraphs = content_elem.select('p')
            content = '\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])
            
            # 提取图片
            images = []
            for img in content_elem.select('img'):
                img_url = img.get('src', '')
                if img_url:
                    # 确保是完整的URL
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    
                    # 不再过滤广告图片，保留所有图片
                    # if not self.image_detector.is_ad_image(img_url):
                    #    images.append(img_url)
                    images.append(img_url)
            
            # 构建新闻数据
            news_data = {
                # 'id': self.generate_news_id(url, title), # Let SQLiteManager handle ID
                'url': url,
                'title': title,
                'pub_time': pub_time,
                'content': content,
                'source': self.source,
                'author': author,
                'category': category,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.logger.info(f"成功提取新闻详情: {title}")
            return news_data
        except Exception as e:
            self.logger.error(f"提取新闻详情失败: {url}, 错误: {str(e)}")
            return None
    
    def crawl(self, days=1, max_news=10):
        """
        爬取网易财经新闻
        
        Args:
            days: 爬取的天数
            max_news: 最大爬取新闻数量
            
        Returns:
            list: 爬取的新闻列表
        """
        self.logger.info(f"开始爬取网易财经新闻，爬取天数: {days}")
        print(f"\n===== 开始爬取网易财经新闻 =====")
        print(f"爬取天数: {days}, 最大新闻数: {max_news}")
        print(f"日志文件: {os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs', '网易财经', f'网易财经_{datetime.now().strftime('%Y-%m-%d')}.log')}")
        print("=" * 40)
        
        # 清空新闻数据列表
        self.news_data = []
        self.crawled_urls = set()  # 用于记录已爬取的URL，避免重复爬取
        
        # 设置爬取的开始日期
        start_date = datetime.now() - timedelta(days=days)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 设置广告过滤器 - 已禁用URL广告过滤
        # self.ad_filter.load_rules()
        
        # 尝试直接从首页获取新闻
        try:
            self.logger.info("尝试从首页获取新闻")
            home_url = "https://money.163.com/"
            print(f"\n[1] 正在获取首页: {home_url}")
            
            try:
                response = self.session.get(home_url, headers=self.get_browser_headers(), timeout=15)
                if response.status_code == 200:
                    html = response.text
                    news_links = self.extract_news_links_from_home(html, "财经")
                    self.logger.info(f"从首页提取到新闻链接数量: {len(news_links)}")
                    print(f"从首页提取到新闻链接数量: {len(news_links)}")
                    
                    # 爬取每个新闻详情
                    for i, news_link in enumerate(news_links):
                        if len(self.news_data) >= max_news:
                            break
                            
                        print(f"\n[1.{i+1}] 爬取新闻: {news_link}")
                        if news_link in self.crawled_urls:
                            self.logger.info(f"新闻 {news_link} 已经爬取过，跳过")
                            print(f"新闻 {news_link} 已经爬取过，跳过")
                            continue
                        self.crawled_urls.add(news_link)
                        news_data = self.extract_news_detail(news_link, "财经")
                        if not news_data:
                            print(f"  - 提取失败，跳过")
                            continue
                            
                        # 检查新闻日期是否在爬取范围内
                        try:
                            news_date = datetime.strptime(news_data['pub_time'].split(' ')[0], '%Y-%m-%d')
                            if news_date < start_date:
                                self.logger.debug(f"新闻日期 {news_date} 早于开始日期 {start_date}，跳过")
                                print(f"  - 新闻日期 {news_date} 早于开始日期 {start_date}，跳过")
                                continue
                        except Exception as e:
                            self.logger.warning(f"解析新闻日期失败: {news_data['pub_time']}, 错误: {str(e)}")
                            print(f"  - 解析新闻日期失败: {news_data['pub_time']}, 错误: {str(e)}")
                        
                        # 保存新闻数据 - Modified to use BaseCrawler's saving mechanism
                        # BaseCrawler.save_news_to_db calls SQLiteManager.save_to_source_db
                        if news_data:
                            news_data['source'] = self.source # Ensure source is in news_data
                            if 'category' not in news_data or not news_data['category']:
                                news_data['category'] = category # Add category if missing
                            
                            # Call the method from BaseCrawler (which handles db_manager)
                            save_result = super().save_news_to_db(news_data)
                            
                            if save_result:
                                self.news_data.append(news_data) # Optionally, still collect successfully saved items
                                self.crawled_urls.add(news_link) # Add to crawled_urls only if save was successful
                            
                            print(f"  - 标题: {news_data.get('title', 'N/A')}")
                            print(f"  - 发布时间: {news_data.get('pub_time', 'N/A')}")
                        print(f"  - 保存结果: {'成功' if save_result else '失败'}")
                        else:
                            print(f"  - 提取新闻数据失败，无法保存")
                            save_result = False # Ensure save_result is defined
                else:
                    self.logger.warning(f"首页请求失败，状态码: {response.status_code}")
                    print(f"首页请求失败，状态码: {response.status_code}")
            except requests.exceptions.Timeout:
                self.logger.warning("首页请求超时，将继续尝试分类页面")
                print("首页请求超时，将继续尝试分类页面")
            except requests.exceptions.ConnectionError:
                self.logger.warning("首页连接错误，将继续尝试分类页面")
                print("首页连接错误，将继续尝试分类页面")
            except Exception as e:
                self.logger.error(f"从首页爬取新闻失败: {str(e)}")
                print(f"从首页爬取新闻失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"从首页爬取新闻失败: {str(e)}")
            print(f"从首页爬取新闻失败: {str(e)}")
        
        # 爬取各个分类的新闻
        category_index = 2
        for category, url in self.CATEGORY_URLS.items():
            try:
                self.logger.info(f"开始爬取分类: {category}, URL: {url}")
                print(f"\n[{category_index}] 开始爬取分类: {category}, URL: {url}")
                category_index += 1
                
                # 对于特定分类，使用API接口获取数据
                if category in self.API_URLS:
                    api_url = self.API_URLS[category]
                    self.logger.info(f"使用API接口获取数据: {api_url}")
                    print(f"使用API接口获取数据: {api_url}")
                    
                    news_links = self.fetch_news_from_api(api_url, category)
                    if news_links:
                        self.logger.info(f"从API获取到 {len(news_links)} 条新闻链接")
                        print(f"从API获取到 {len(news_links)} 条新闻链接")
                    else:
                        # 如果API获取失败，尝试从页面提取
                        self.logger.info(f"API获取失败，尝试从页面提取")
                        print(f"API获取失败，尝试从页面提取")
                        
                        try:
                            response = self.session.get(url, headers=self.get_browser_headers(), timeout=15)
                            if response.status_code == 200:
                                html = response.text
                                news_links = self.extract_news_links(html, category)
                                self.logger.info(f"从页面提取到 {len(news_links)} 条新闻链接")
                                print(f"从页面提取到 {len(news_links)} 条新闻链接")
                            else:
                                self.logger.warning(f"请求分类页面失败，状态码: {response.status_code}")
                                print(f"请求分类页面失败，状态码: {response.status_code}")
                                continue
                        except requests.exceptions.Timeout:
                            self.logger.warning(f"分类 {category} 请求超时，跳过")
                            print(f"分类 {category} 请求超时，跳过")
                            continue
                        except requests.exceptions.ConnectionError:
                            self.logger.warning(f"分类 {category} 连接错误，跳过")
                            print(f"分类 {category} 连接错误，跳过")
                            continue
                        except Exception as e:
                            self.logger.error(f"请求分类 {category} 页面失败: {str(e)}")
                            print(f"请求分类 {category} 页面失败: {str(e)}")
                            continue
                else:
                    # 普通页面提取
                    try:
                        response = self.session.get(url, headers=self.get_browser_headers(), timeout=15)
                        if response.status_code == 200:
                            html = response.text
                            
                            # 检查是否有反爬虫措施
                            if "验证码" in html or "人机验证" in html or len(html) < 1000:
                                self.logger.warning(f"检测到反爬虫措施，尝试更换User-Agent和IP")
                                print(f"检测到反爬虫措施，尝试更换User-Agent和IP")
                                # 更换User-Agent
                                self.headers['User-Agent'] = self.get_random_ua()
                                # 如果使用代理，尝试更换代理
                                if self.use_proxy and hasattr(self, 'proxy_manager'):
                                    self.proxy_manager.rotate_proxy()
                                
                                # 重试请求
                                time.sleep(2)
                                response = self.session.get(url, headers=self.get_browser_headers(), timeout=15)
                                if response.status_code == 200:
                                    html = response.text
                                else:
                                    self.logger.warning(f"重试请求失败，状态码: {response.status_code}")
                                    print(f"重试请求失败，状态码: {response.status_code}")
                                    continue
                            
                            news_links = self.extract_news_links(html, category)
                            self.logger.info(f"分类 '{category}' 找到 {len(news_links)} 个潜在新闻项")
                            print(f"分类 '{category}' 找到 {len(news_links)} 个潜在新闻项")
                        else:
                            self.logger.warning(f"请求分类页面失败，状态码: {response.status_code}")
                            print(f"请求分类页面失败，状态码: {response.status_code}")
                            continue
                    except requests.exceptions.Timeout:
                        self.logger.warning(f"分类 {category} 请求超时，跳过")
                        print(f"分类 {category} 请求超时，跳过")
                        continue
                    except requests.exceptions.ConnectionError:
                        self.logger.warning(f"分类 {category} 连接错误，跳过")
                        print(f"分类 {category} 连接错误，跳过")
                        continue
                    except Exception as e:
                        self.logger.error(f"请求分类 {category} 页面失败: {str(e)}")
                        print(f"请求分类 {category} 页面失败: {str(e)}")
                        continue
                
                # 爬取每个新闻详情
                for i, news_link in enumerate(news_links):
                    if len(self.news_data) >= max_news:
                        break
                    
                    print(f"\n[{category_index-1}.{i+1}] 爬取新闻: {news_link}")
                    if news_link in self.crawled_urls:
                        self.logger.info(f"新闻 {news_link} 已经爬取过，跳过")
                        print(f"新闻 {news_link} 已经爬取过，跳过")
                        continue
                    self.crawled_urls.add(news_link)
                    news_data = self.extract_news_detail(news_link, category)
                    if not news_data:
                        print(f"  - 提取失败，跳过")
                        continue
                        
                    # 检查新闻日期是否在爬取范围内
                    try:
                        news_date = datetime.strptime(news_data['pub_time'].split(' ')[0], '%Y-%m-%d')
                        if news_date < start_date:
                            self.logger.debug(f"新闻日期 {news_date} 早于开始日期 {start_date}，跳过")
                            print(f"  - 新闻日期 {news_date} 早于开始日期 {start_date}，跳过")
                            continue
                    except Exception as e:
                        self.logger.warning(f"解析新闻日期失败: {news_data['pub_time']}")
                        print(f"  - 解析新闻日期失败: {news_data['pub_time']}")
                    
                    # 保存新闻数据 - Modified to use BaseCrawler's saving mechanism
                    # BaseCrawler.save_news_to_db calls SQLiteManager.save_to_source_db
                    if news_data:
                        news_data['source'] = self.source # Ensure source is in news_data
                        if 'category' not in news_data or not news_data['category']:
                            news_data['category'] = category # Add category if missing
                        
                        # Call the method from BaseCrawler (which handles db_manager)
                        save_result = super().save_news_to_db(news_data)
                        
                        if save_result:
                            self.news_data.append(news_data) # Optionally, still collect successfully saved items
                            self.crawled_urls.add(news_link) # Add to crawled_urls only if save was successful
                        
                        print(f"  - 标题: {news_data.get('title', 'N/A')}")
                        print(f"  - 发布时间: {news_data.get('pub_time', 'N/A')}")
                    print(f"  - 保存结果: {'成功' if save_result else '失败'}")
                    else:
                        print(f"  - 提取新闻数据失败，无法保存")
                        save_result = False # Ensure save_result is defined
                    
                # 如果已经获取足够数量的新闻，停止爬取
                if len(self.news_data) >= max_news:
                    self.logger.info(f"已经爬取 {len(self.news_data)} 条新闻，达到最大数量 {max_news}")
                    print(f"\n已经爬取 {len(self.news_data)} 条新闻，达到最大数量 {max_news}")
                    break
                
                # 随机休眠，避免被反爬
                sleep_time = random.uniform(1, 3)
                print(f"休眠 {sleep_time:.2f} 秒...")
                time.sleep(sleep_time)
            except Exception as e:
                self.logger.error(f"爬取分类 '{category}' 失败: {str(e)}")
                print(f"爬取分类 '{category}' 失败: {str(e)}")
        
        self.logger.info(f"网易财经爬取完成，共爬取新闻: {len(self.news_data)} 条，过滤广告: {self.ad_filter.get_filter_count()} 条")
        print(f"\n===== 网易财经爬取完成 =====")
        print(f"共爬取新闻: {len(self.news_data)} 条")
        print(f"过滤广告: {self.ad_filter.get_filter_count()} 条")
        print("=" * 40)
        return self.news_data
    
    def save_news_to_db(self, news):
        """
        保存新闻到数据库
        
        Args:
            news: 新闻数据字典
            
        Returns:
            bool: 是否保存成功
        """
        try:
            if not news.get('title'):
                self.logger.warning("新闻标题为空，跳过保存")
                return False
                
            if not news.get('content'):
                self.logger.warning("新闻内容为空，跳过保存")
                return False
                
            if not news.get('url'):
                self.logger.warning("新闻URL为空，跳过保存")
                return False
            
            # 确保必要字段存在
            news['source'] = self.source
            if 'pub_time' not in news:
                news['pub_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return self.sqlite_manager.save_news(news)
            
        except Exception as e:
            self.logger.error(f"保存新闻到数据库失败: {str(e)}")
            return False
    
    def fetch_news_from_api(self, api_url, category):
        """
        从API接口获取新闻数据
        
        Args:
            api_url: API接口URL
            category: 新闻分类
            
        Returns:
            list: 新闻链接列表
        """
        news_links = []
        try:
            # 使用更完整的浏览器标识
            headers = self.get_browser_headers()
            
            # 添加Referer头，避免被识别为爬虫
            headers['Referer'] = self.CATEGORY_URLS.get(category, 'https://money.163.com/')
            
            response = self.session.get(api_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # 处理JavaScript格式的响应
                content = response.text
                
                # 提取JSON数据
                if 'var data=' in content:
                    json_str = content.split('var data=')[1].strip().rstrip(';')
                    try:
                        data = json.loads(json_str)
                        # 提取新闻链接
                        for item in data:
                            if 'docurl' in item:
                                url = item['docurl']
                                if self.is_valid_url(url):
                                    news_links.append(url)
                    except json.JSONDecodeError:
                        self.logger.warning(f"解析JSON数据失败: {json_str[:100]}...")
                else:
                    # 尝试直接从响应中提取URL
                    urls = re.findall(r'https?://[^\s\'"]+\.html', content)
                    for url in urls:
                        if self.is_valid_url(url):
                            news_links.append(url)
            else:
                self.logger.warning(f"API请求失败，状态码: {response.status_code}")
        except Exception as e:
            self.logger.error(f"从API获取新闻数据失败: {str(e)}")
        
        # 去重
        return list(set(news_links))


if __name__ == "__main__":
    # 测试爬虫
    crawler = NeteaseCrawler(use_proxy=False, use_source_db=True)
    news_list = crawler.crawl(days=1, max_news=5)
    print(f"爬取到新闻数量: {len(news_list)}")
    for news in news_list:
        print(f"标题: {news['title']}")
        print(f"发布时间: {news['pub_time']}")
        print(f"来源: {news['source']}")
        print("-" * 50) 