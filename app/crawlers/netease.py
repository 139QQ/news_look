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
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html, extract_keywords
from app.db.sqlite_manager import SQLiteManager
from app.utils.ad_filter import AdFilter  # 导入广告过滤器模块
from app.utils.image_detector import ImageDetector  # 导入图像识别模块

# 使用专门的爬虫日志记录器
crawler_logger = logging.getLogger('crawler.netease')

class NeteaseCrawler(BaseCrawler):
    """网易财经爬虫，用于爬取网易财经的财经新闻"""
    
    # 新闻分类URL
    CATEGORY_URLS = {
        '财经': 'https://money.163.com/',
        '股票': 'https://money.163.com/stock/',
        '理财': 'https://money.163.com/licai/',
        '基金': 'https://money.163.com/fund/',
        '热点': 'https://money.163.com/special/00252G50/macro.html',
        '商业': 'https://biz.163.com/'
    }
    
    # API接口
    API_URLS = {
        '股票': 'https://money.163.com/special/00259BVP/news_json.js',
        '理财': 'https://money.163.com/special/00259BVP/licai_json.js',
        '基金': 'https://money.163.com/special/00259BVP/fund_json.js'
    }
    
    # 内容选择器 - 更新为支持多种可能的选择器
    CONTENT_SELECTORS = [
        'div.post_body',
        'div.post_text',
        'div#endText',
        'div.post-content',
        'div.content'
    ]
    
    # 时间选择器 - 更新为支持多种可能的选择器
    TIME_SELECTORS = [
        'div.post_time_source',
        'div.post_info',
        'div.time',
        'span.time',
        'div.post-time'
    ]
    
    # 作者选择器
    AUTHOR_SELECTORS = [
        'div.post_time_source span',
        'div.post_info span',
        'span.source',
        'a.source'
    ]
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, **kwargs):
        """
        初始化网易财经爬虫
        
        Args:
            db_manager: 数据库管理器对象
            db_path: 数据库路径，如果为None则使用默认路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
        """
        self.source = "网易财经"
        super().__init__(db_manager=db_manager, db_path=db_path, use_proxy=use_proxy, use_source_db=use_source_db, **kwargs)
        
        # 初始化广告过滤器
        self.ad_filter = AdFilter(source_name=self.source)
        # 初始化图像检测器
        self.image_detector = ImageDetector(cache_dir='./image_cache')
        
        # 初始化requests会话
        self.session = requests.Session()
        self.session.headers.update(self.get_browser_headers())
        
        # 设置专用日志
        self.setup_logger()
        
        # 如果提供了db_manager并且不是SQLiteManager类型，创建SQLiteManager
        if db_manager and not isinstance(db_manager, SQLiteManager):
            if hasattr(db_manager, 'db_path'):
                self.sqlite_manager = SQLiteManager(db_manager.db_path)
            else:
                # 使用传入的db_path或默认路径
                self.sqlite_manager = SQLiteManager(db_path or self.db_path)
        elif not db_manager:
            # 如果没有提供db_manager，创建SQLiteManager
            self.sqlite_manager = SQLiteManager(self.db_path)
        else:
            # 否则使用提供的db_manager
            self.sqlite_manager = db_manager
        
        self.proxy_manager = None
        
        crawler_logger.info(f"网易财经爬虫初始化完成，数据库路径: {self.db_path}")
        print(f"网易财经爬虫初始化完成，数据库路径: {self.db_path}")
    
    def setup_logger(self):
        """设置专用的爬虫日志记录器"""
        global crawler_logger
        
        # 使用统一的爬虫日志记录器功能
        crawler_logger = get_crawler_logger('netease')
        crawler_logger.info("网易财经爬虫日志系统初始化完成")
        
        # 记录数据库路径信息
        if hasattr(self, 'db_path'):
            crawler_logger.info(f"数据库路径: {self.db_path}")
        
        # 打印日志信息
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs', '网易财经')
        current_date = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(log_dir, f'netease_{current_date}.log')
        print(f"网易财经爬虫日志将输出到: {log_file}")
    
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
    
    def fetch_page(self, url, retry=3, retry_interval=2):
        """
        获取页面内容
        
        Args:
            url: 页面URL
            retry: 重试次数
            retry_interval: 重试间隔时间（秒）
            
        Returns:
            str: 页面内容
        """
        crawler_logger.info(f"尝试获取页面: {url}")
        print(f"尝试获取页面: {url}")
        
        for attempt in range(retry):
            try:
                # 使用会话发送请求
                headers = self.get_browser_headers()
                response = self.session.get(url, headers=headers, timeout=15)
                
                # 检查响应状态
                if response.status_code == 200:
                    # 检查是否有反爬措施
                    if "验证码" in response.text or "人机验证" in response.text or len(response.text) < 1000:
                        crawler_logger.warning(f"检测到反爬虫措施，尝试更换User-Agent和延迟重试")
                        print(f"检测到反爬虫措施，尝试更换User-Agent和延迟重试")
                        # 更换User-Agent
                        time.sleep(random.uniform(3, 5))
                        continue
                    
                    crawler_logger.info(f"成功获取页面: {url}")
                    print(f"成功获取页面: {url}")
                    return response.text
                else:
                    crawler_logger.warning(f"获取页面失败，状态码: {response.status_code}，尝试重试 {attempt+1}/{retry}")
                    print(f"获取页面失败，状态码: {response.status_code}，尝试重试 {attempt+1}/{retry}")
            except requests.exceptions.Timeout:
                crawler_logger.warning(f"请求超时，尝试重试 {attempt+1}/{retry}")
                print(f"请求超时，尝试重试 {attempt+1}/{retry}")
            except requests.exceptions.ConnectionError:
                crawler_logger.warning(f"连接错误，尝试重试 {attempt+1}/{retry}")
                print(f"连接错误，尝试重试 {attempt+1}/{retry}")
            except Exception as e:
                crawler_logger.error(f"获取页面时发生错误: {str(e)}，尝试重试 {attempt+1}/{retry}")
                print(f"获取页面时发生错误: {str(e)}，尝试重试 {attempt+1}/{retry}")
            
            # 等待一段时间后重试
            time.sleep(retry_interval)
        
        crawler_logger.error(f"获取页面失败，已达到最大重试次数: {retry}")
        print(f"获取页面失败，已达到最大重试次数: {retry}")
        return None
    
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
            crawler_logger.warning("首页HTML内容为空，无法提取新闻链接")
            print("首页HTML内容为空，无法提取新闻链接")
            return []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            news_links = []
            
            # 提取所有可能的新闻链接
            for link in soup.find_all('a', href=True):
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
                    # if '/article/' in href and not self.ad_filter.is_ad(href, link.text):
                    news_links.append(href)
            
            crawler_logger.info(f"从首页提取到 {len(news_links)} 个新闻链接")
            print(f"从首页提取到 {len(news_links)} 个新闻链接")
            return news_links
        except Exception as e:
            crawler_logger.error(f"从首页提取新闻链接失败: {str(e)}")
            print(f"从首页提取新闻链接失败: {str(e)}")
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
            crawler_logger.warning(f"分类 {category} 页面HTML内容为空，无法提取新闻链接")
            print(f"分类 {category} 页面HTML内容为空，无法提取新闻链接")
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
            
            crawler_logger.info(f"从分类 {category} 页面提取到 {len(news_links)} 个新闻链接")
            print(f"从分类 {category} 页面提取到 {len(news_links)} 个新闻链接")
            return news_links
        except Exception as e:
            crawler_logger.error(f"从分类 {category} 页面提取新闻链接失败: {str(e)}")
            print(f"从分类 {category} 页面提取新闻链接失败: {str(e)}")
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
        crawler_logger.info(f"开始提取新闻详情: {url}")
        print(f"开始提取新闻详情: {url}")
        
        # 获取页面内容
        html = self.fetch_page(url)
        if not html:
            crawler_logger.warning(f"获取新闻页面失败: {url}")
            print(f"获取新闻页面失败: {url}")
            return None
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取标题
            title_elem = soup.select_one('.post_title')
            if not title_elem:
                crawler_logger.warning(f"未找到标题元素: {url}")
                print(f"未找到标题元素: {url}")
                return None
            
            title = title_elem.text.strip()
            
            # 提取发布时间
            time_elem = soup.select_one('.post_time')
            if not time_elem:
                crawler_logger.warning(f"未找到时间元素: {url}")
                print(f"未找到时间元素: {url}")
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
                crawler_logger.warning(f"未找到内容元素: {url}")
                print(f"未找到内容元素: {url}")
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
                'id': self.generate_news_id(url, title),
                'title': title,
                'url': url,
                'pub_time': pub_time,
                'author': author,
                'content': content,
                'images': images,
                'category': category,
                'source': self.source
            }
            
            crawler_logger.info(f"成功提取新闻详情: {title}")
            print(f"成功提取新闻详情: {title}")
            return news_data
        except Exception as e:
            crawler_logger.error(f"提取新闻详情失败: {url}, 错误: {str(e)}")
            print(f"提取新闻详情失败: {url}, 错误: {str(e)}")
            return None
    
    def generate_news_id(self, url, title):
        """
        生成新闻唯一ID
        
        Args:
            url: 新闻URL
            title: 新闻标题
            
        Returns:
            str: 新闻唯一ID
        """
        import hashlib
        
        # 从URL中提取文章ID
        try:
            # 网易新闻URL格式通常为 https://www.163.com/xxx/article/ABCDEFGH.html
            # 尝试提取ABCDEFGH部分作为ID
            if '/article/' in url:
                article_id = url.split('/article/')[1].split('.')[0]
                # 如果ID包含额外路径，只取ID部分
                if '/' in article_id:
                    article_id = article_id.split('/')[-1]
                return article_id
        except Exception as e:
            crawler_logger.warning(f"从URL提取文章ID失败: {e}")
        
        # 如果无法从URL提取ID，则使用URL和标题的组合生成哈希
        unique_string = f"{url}_{title}_{self.source}"
        return hashlib.md5(unique_string.encode('utf-8')).hexdigest()
    
    def crawl(self, days=1, max_news=10):
        """
        爬取网易财经新闻
        
        Args:
            days: 爬取的天数
            max_news: 最大爬取新闻数量
            
        Returns:
            list: 爬取的新闻列表
        """
        crawler_logger.info(f"开始爬取网易财经新闻，爬取天数: {days}")
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
            crawler_logger.info("尝试从首页获取新闻")
            home_url = "https://money.163.com/"
            print(f"\n[1] 正在获取首页: {home_url}")
            
            try:
                response = self.session.get(home_url, headers=self.get_browser_headers(), timeout=15)
                if response.status_code == 200:
                    html = response.text
                    news_links = self.extract_news_links_from_home(html, "财经")
                    crawler_logger.info(f"从首页提取到新闻链接数量: {len(news_links)}")
                    print(f"从首页提取到新闻链接数量: {len(news_links)}")
                    
                    # 爬取每个新闻详情
                    for i, news_link in enumerate(news_links):
                        if len(self.news_data) >= max_news:
                            break
                            
                        print(f"\n[1.{i+1}] 爬取新闻: {news_link}")
                        if news_link in self.crawled_urls:
                            crawler_logger.info(f"新闻 {news_link} 已经爬取过，跳过")
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
                                crawler_logger.debug(f"新闻日期 {news_date} 早于开始日期 {start_date}，跳过")
                                print(f"  - 新闻日期 {news_date} 早于开始日期 {start_date}，跳过")
                                continue
                        except Exception as e:
                            crawler_logger.warning(f"解析新闻日期失败: {news_data['pub_time']}, 错误: {str(e)}")
                            print(f"  - 解析新闻日期失败: {news_data['pub_time']}, 错误: {str(e)}")
                        
                        # 保存新闻数据
                        save_result = self.save_news_to_db(news_data)
                        self.news_data.append(news_data)
                        print(f"  - 标题: {news_data['title']}")
                        print(f"  - 发布时间: {news_data['pub_time']}")
                        print(f"  - 保存结果: {'成功' if save_result else '失败'}")
                else:
                    crawler_logger.warning(f"首页请求失败，状态码: {response.status_code}")
                    print(f"首页请求失败，状态码: {response.status_code}")
            except requests.exceptions.Timeout:
                crawler_logger.warning("首页请求超时，将继续尝试分类页面")
                print("首页请求超时，将继续尝试分类页面")
            except requests.exceptions.ConnectionError:
                crawler_logger.warning("首页连接错误，将继续尝试分类页面")
                print("首页连接错误，将继续尝试分类页面")
            except Exception as e:
                crawler_logger.error(f"从首页爬取新闻失败: {str(e)}")
                print(f"从首页爬取新闻失败: {str(e)}")
        except Exception as e:
            crawler_logger.error(f"从首页爬取新闻失败: {str(e)}")
            print(f"从首页爬取新闻失败: {str(e)}")
        
        # 爬取各个分类的新闻
        category_index = 2
        for category, url in self.CATEGORY_URLS.items():
            try:
                crawler_logger.info(f"开始爬取分类: {category}, URL: {url}")
                print(f"\n[{category_index}] 开始爬取分类: {category}, URL: {url}")
                category_index += 1
                
                # 对于特定分类，使用API接口获取数据
                if category in self.API_URLS:
                    api_url = self.API_URLS[category]
                    crawler_logger.info(f"使用API接口获取数据: {api_url}")
                    print(f"使用API接口获取数据: {api_url}")
                    
                    news_links = self.fetch_news_from_api(api_url, category)
                    if news_links:
                        crawler_logger.info(f"从API获取到 {len(news_links)} 条新闻链接")
                        print(f"从API获取到 {len(news_links)} 条新闻链接")
                    else:
                        # 如果API获取失败，尝试从页面提取
                        crawler_logger.info(f"API获取失败，尝试从页面提取")
                        print(f"API获取失败，尝试从页面提取")
                        
                        try:
                            response = self.session.get(url, headers=self.get_browser_headers(), timeout=15)
                            if response.status_code == 200:
                                html = response.text
                                news_links = self.extract_news_links(html, category)
                                crawler_logger.info(f"从页面提取到 {len(news_links)} 条新闻链接")
                                print(f"从页面提取到 {len(news_links)} 条新闻链接")
                            else:
                                crawler_logger.warning(f"请求分类页面失败，状态码: {response.status_code}")
                                print(f"请求分类页面失败，状态码: {response.status_code}")
                                continue
                        except requests.exceptions.Timeout:
                            crawler_logger.warning(f"分类 {category} 请求超时，跳过")
                            print(f"分类 {category} 请求超时，跳过")
                            continue
                        except requests.exceptions.ConnectionError:
                            crawler_logger.warning(f"分类 {category} 连接错误，跳过")
                            print(f"分类 {category} 连接错误，跳过")
                            continue
                        except Exception as e:
                            crawler_logger.error(f"请求分类 {category} 页面失败: {str(e)}")
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
                                crawler_logger.warning(f"检测到反爬虫措施，尝试更换User-Agent和IP")
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
                                    crawler_logger.warning(f"重试请求失败，状态码: {response.status_code}")
                                    print(f"重试请求失败，状态码: {response.status_code}")
                                    continue
                            
                            news_links = self.extract_news_links(html, category)
                            crawler_logger.info(f"分类 '{category}' 找到 {len(news_links)} 个潜在新闻项")
                            print(f"分类 '{category}' 找到 {len(news_links)} 个潜在新闻项")
                        else:
                            crawler_logger.warning(f"请求分类页面失败，状态码: {response.status_code}")
                            print(f"请求分类页面失败，状态码: {response.status_code}")
                            continue
                    except requests.exceptions.Timeout:
                        crawler_logger.warning(f"分类 {category} 请求超时，跳过")
                        print(f"分类 {category} 请求超时，跳过")
                        continue
                    except requests.exceptions.ConnectionError:
                        crawler_logger.warning(f"分类 {category} 连接错误，跳过")
                        print(f"分类 {category} 连接错误，跳过")
                        continue
                    except Exception as e:
                        crawler_logger.error(f"请求分类 {category} 页面失败: {str(e)}")
                        print(f"请求分类 {category} 页面失败: {str(e)}")
                        continue
                
                # 爬取每个新闻详情
                for i, news_link in enumerate(news_links):
                    if len(self.news_data) >= max_news:
                        break
                    
                    print(f"\n[{category_index-1}.{i+1}] 爬取新闻: {news_link}")
                    if news_link in self.crawled_urls:
                        crawler_logger.info(f"新闻 {news_link} 已经爬取过，跳过")
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
                            crawler_logger.debug(f"新闻日期 {news_date} 早于开始日期 {start_date}，跳过")
                            print(f"  - 新闻日期 {news_date} 早于开始日期 {start_date}，跳过")
                            continue
                    except Exception as e:
                        crawler_logger.warning(f"解析新闻日期失败: {news_data['pub_time']}")
                        print(f"  - 解析新闻日期失败: {news_data['pub_time']}")
                    
                    # 保存新闻数据
                    save_result = self.save_news_to_db(news_data)
                    self.news_data.append(news_data)
                    print(f"  - 标题: {news_data['title']}")
                    print(f"  - 发布时间: {news_data['pub_time']}")
                    print(f"  - 保存结果: {'成功' if save_result else '失败'}")
                    
                # 如果已经获取足够数量的新闻，停止爬取
                if len(self.news_data) >= max_news:
                    crawler_logger.info(f"已经爬取 {len(self.news_data)} 条新闻，达到最大数量 {max_news}")
                    print(f"\n已经爬取 {len(self.news_data)} 条新闻，达到最大数量 {max_news}")
                    break
                
                # 随机休眠，避免被反爬
                sleep_time = random.uniform(1, 3)
                print(f"休眠 {sleep_time:.2f} 秒...")
                time.sleep(sleep_time)
            except Exception as e:
                crawler_logger.error(f"爬取分类 '{category}' 失败: {str(e)}")
                print(f"爬取分类 '{category}' 失败: {str(e)}")
        
        crawler_logger.info(f"网易财经爬取完成，共爬取新闻: {len(self.news_data)} 条，过滤广告: {self.ad_filter.get_filter_count()} 条")
        print(f"\n===== 网易财经爬取完成 =====")
        print(f"共爬取新闻: {len(self.news_data)} 条")
        print(f"过滤广告: {self.ad_filter.get_filter_count()} 条")
        print("=" * 40)
        return self.news_data
    
    def save_news_to_db(self, news):
        """
        保存新闻到数据库
        
        Args:
            news: 新闻数据
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保新闻数据有ID字段
            if 'id' not in news:
                if 'url' in news and 'title' in news:
                    news['id'] = self.generate_news_id(news['url'], news['title'])
                else:
                    # 如果没有URL或标题，使用时间戳作为ID
                    news['id'] = f"netease_{int(time.time())}_{random.randint(1000, 9999)}"
                    crawler_logger.warning(f"使用随机ID: {news['id']}")
            
            if hasattr(self, 'sqlite_manager') and self.sqlite_manager:
                return self.sqlite_manager.save_news(news)
            return super().save_news(news)
        except Exception as e:
            crawler_logger.error(f"保存新闻到数据库失败: {str(e)}")
            return False
    
    def is_valid_news_url(self, url):
        """
        判断URL是否为有效的新闻链接
        
        Args:
            url: 链接URL
        
        Returns:
            bool: 是否为有效的新闻链接
        """
        if not url:
            return False
            
        # 检查URL是否为广告 - 已移除广告过滤
        # if self.ad_filter.is_ad_url(url):
        #     crawler_logger.info(f"过滤广告URL: {url}")
        #     return False
            
        # 网易财经新闻URL通常包含以下特征
        patterns = [
            r'https?://money\.163\.com/\d+/\d+/\d+/\w+\.html',
            r'https?://money\.163\.com/\w+/\d+/\d+/\d+/\w+\.html',
            r'https?://www\.163\.com/money/article/\w+\.html',
            r'https?://www\.163\.com/dy/article/\w+\.html',  # 新增网易号文章
            r'https?://biz\.163\.com/\d+/\d+/\d+/\w+\.html',
            r'https?://biz\.163\.com/article/\w+\.html'
        ]
        
        for pattern in patterns:
            if re.match(pattern, url):
                return True
        
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
                                if self.is_valid_news_url(url):
                                    news_links.append(url)
                    except json.JSONDecodeError:
                        crawler_logger.warning(f"解析JSON数据失败: {json_str[:100]}...")
                else:
                    # 尝试直接从响应中提取URL
                    urls = re.findall(r'https?://[^\s\'"]+\.html', content)
                    for url in urls:
                        if self.is_valid_news_url(url):
                            news_links.append(url)
            else:
                crawler_logger.warning(f"API请求失败，状态码: {response.status_code}")
        except Exception as e:
            crawler_logger.error(f"从API获取新闻数据失败: {str(e)}")
        
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