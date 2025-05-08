#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 凤凰财经爬虫
"""

import os
import re
import time
import random
import urllib.parse
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import traceback

import requests
from bs4 import BeautifulSoup
import hashlib
import json
import logging
import chardet

# 修复导入路径
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.db_manager import DatabaseManager
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html_content, extract_keywords, decode_html_entities, decode_unicode_escape, decode_url_encoded
from app.crawlers.base import BaseCrawler
from app.utils.ad_filter import AdFilter  # 导入广告过滤器模块
from app.utils.image_detector import ImageDetector  # 导入图像识别模块

# 确保日志目录存在
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs', '凤凰财经')
os.makedirs(log_dir, exist_ok=True)

# 使用专门的爬虫日志记录器，并配置文件输出
today = datetime.now().strftime('%Y%m%d')
log_file = os.path.join(log_dir, f"凤凰财经_{today}.log")

# 创建自定义的日志记录器
logger = logging.getLogger('ifeng_crawler')
logger.setLevel(logging.INFO)

# 添加控制台输出
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s'))
logger.addHandler(console_handler)

# 添加文件输出
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s'))
logger.addHandler(file_handler)

# 避免日志重复
logger.propagate = False

class IfengCrawler(BaseCrawler):
    """凤凰财经爬虫，用于爬取凤凰财经的财经新闻"""
    
    # 来源名称
    source = "凤凰财经"
    
    # 新闻分类URL
    CATEGORY_URLS = {
        '财经': 'https://finance.ifeng.com/',
        '股票': 'https://finance.ifeng.com/stock/',
        '绿色发展': 'https://finance.ifeng.com/greenfinance/',
        '中国深度财经': 'https://finance.ifeng.com/deepfinance/',
        '上市公司': 'https://finance.ifeng.com/listedcompany/',
        '银行财眼': 'https://finance.ifeng.com/bankingeye/',
        '国际财经': 'https://finance.ifeng.com/world/',
        'IPO观察哨': 'https://finance.ifeng.com/ipo/',
    }
    
    # API URL模板 - 凤凰财经的API接口
    API_URL_TEMPLATE = "https://api.3g.ifeng.com/ipadtestdoc?gv=5.8.5&os=ios&uid={uid}&aid={aid}&id={id}&pageSize={page_size}"
    
    # 内容选择器 - 更新以适应各种网页结构
    CONTENT_SELECTOR = 'div.main_content, div.text_area, div.article-main, div.text-3w2e3DBc, div.main-content-section, div.js-video-content, div.content, div.article_content, article.article-main-content, div.detailArticle-content, div#artical_real, div.yc-artical, div.art_content, div.article-cont, div.news-content, div.news_txt, div.c-article-content, div#main_content, div.hqy-ArticleInfo-article, div.article-main-inner, div.article__content, div.c-article-body'
    
    # 时间选择器
    TIME_SELECTOR = 'span.ss01, span.date, div.time, p.time, span.time, span.date-source, span.ss01, time.time'
    
    # 作者选择器
    AUTHOR_SELECTOR = 'span.ss03, span.source, div.source, p.source, span.author, span.ss03, span.source-name'
    
    # 标题选择器
    TITLE_SELECTOR = 'h1.title, h1.headline-title, div.headline-title, h1.news-title-h1, h1.yc-title, h1.c-article-title, h1.news_title'
    
    # 更新User-Agent为更现代的浏览器标识
    USER_AGENTS = [
        # Chrome最新版本UA
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        
        # Edge最新版本UA
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        
        # Firefox最新版本UA
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/118.0",
        
        # Safari最新版本UA
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    ]
    
    # 浏览器默认请求头
    DEFAULT_HEADERS = {
        'User-Agent': None,  # 将在请求时随机选择
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Referer': 'https://www.ifeng.com/'
    }
    
    # 新凤凰财经API端点
    NEW_API_ENDPOINT = "https://finance.ifeng.com/mapi/getfeeds"
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, **kwargs):
        """
        初始化凤凰财经爬虫
        
        Args:
            db_manager: 数据库管理器
            db_path: 数据库路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用源数据库
        """
        # self.source 已在类级别定义
        super().__init__(db_manager, db_path, use_proxy, use_source_db, source=self.source, **kwargs)
        
        # 设置 spécifique 的 logger
        self.logger = logger # 使用模块顶层定义的logger
        
        # 初始化特定于IfengCrawler的组件
        self.ad_filter = AdFilter(source_name=self.source) 
        self.image_detector = ImageDetector(cache_dir='./image_cache')
        
        # 编码修复功能的标志 (如果IfengCrawler有特殊处理，否则可考虑移至BaseCrawler或TextCleaner)
        self.encoding_fix_enabled = True 
        self.logger.info("已启用编码修复功能，自动处理中文乱码问题")
        
        # BaseCrawler.__init__ 会处理 self.db_manager 的初始化
        # 此处不再需要 IfengCrawler 特定的 SQLiteManager 初始化逻辑
        
        self.logger.info(f"凤凰财经爬虫 {self.source} 初始化完成，将使用数据库: {self.db_manager.db_path if self.db_manager else '未指定'}")
    
    def crawl(self, days=1, max_news=10):
        """
        爬取凤凰财经新闻
        
        Args:
            days: 爬取的天数范围，默认为1天
            max_news: 最大爬取新闻数量，默认为10条
            
        Returns:
            list: 爬取的新闻数据列表
        """
        crawled_news_items = [] # 用于收集实际爬取并尝试保存的新闻项
        
        start_date = datetime.now() - timedelta(days=days)
        self.logger.info(f"开始爬取凤凰财经新闻 ({self.source})，爬取天数: {days}, 最大新闻数: {max_news}")
        
        # SQLiteManager 的初始化会负责创建表，此处的显式调用可能不再必要
        # self._ensure_db_ready() 
        
        # 优先处理API（如果适用且高效）
        # TODO: 如果有API爬取逻辑，可以在这里实现

        # 网页爬取逻辑
        page_urls_to_crawl = []
        page_urls_to_crawl.append(("https://finance.ifeng.com/", "首页"))
        for category, url in self.CATEGORY_URLS.items():
            page_urls_to_crawl.append((url, category))

        for page_url, category_name in page_urls_to_crawl:
            if len(crawled_news_items) >= max_news:
                self.logger.info(f"已达到最大新闻数量 {max_news} 条，停止爬取更多分类页面。")
                break
            
            self.logger.info(f"开始处理页面: {page_url} (分类: {category_name})")
            try:
                time.sleep(random.uniform(1, 3)) # 礼貌性延迟
                news_links = self.get_news_links(page_url, category_name)
                if not news_links:
                    self.logger.warning(f"在页面 {page_url} 未找到新闻链接。")
                    continue
                
                self.logger.info(f"页面 {page_url} 找到 {len(news_links)} 个潜在新闻链接。")
                
                for link_url in news_links:
                    if len(crawled_news_items) >= max_news:
                        self.logger.info(f"已达到最大新闻数量 {max_news} 条，停止处理更多新闻链接。")
                        break
                    
                    self.logger.debug(f"准备处理新闻链接: {link_url}")
                    try:
                        time.sleep(random.uniform(0.5, 1.5)) # 处理单个新闻前的延迟
                        news_detail = self.get_news_detail(link_url, category_name)
                        
                        if not news_detail:
                            self.logger.warning(f"无法获取新闻详情或内容无效: {link_url}")
                            continue
                        
                        # 日期检查 (确保 pub_time 是存在的并且是有效格式)
                        if 'pub_time' not in news_detail or not news_detail['pub_time']:
                            self.logger.warning(f"新闻详情缺少 pub_time: {link_url}, 标题: {news_detail.get('title')}")
                            # 可以选择跳过，或者让后续的SQLiteManager预处理设置默认时间
                            # 此处选择信任后续处理，但记录警告

                        try:
                            # 如果pub_time存在，则进行日期范围检查
                            if news_detail.get('pub_time'):
                                news_date = datetime.strptime(news_detail['pub_time'], '%Y-%m-%d %H:%M:%S')
                                if news_date < start_date:
                                    self.logger.info(f"新闻日期 {news_detail['pub_time']} 早于起始日期 {start_date.strftime('%Y-%m-%d %H:%M:%S')}，跳过: {news_detail.get('title')}")
                                    continue
                        except ValueError as ve:
                            self.logger.warning(f"日期格式错误 for pub_time '{news_detail.get('pub_time')}': {ve}. 新闻: {news_detail.get('title')}. 将尝试由后续流程处理。")
                            # 不跳过，让SQLiteManager尝试处理或设置默认值

                        # 调用基类的保存方法，它会处理预处理和数据库交互
                        if super().save_news_to_db(news_detail): # 或者 self.save_news_to_db(news_detail)
                            crawled_news_items.append(news_detail)
                            self.logger.info(f"成功处理并尝试保存新闻: {news_detail.get('title')}")
                        else:
                            self.logger.warning(f"基类 save_news_to_db未能成功处理/保存新闻: {news_detail.get('title')}, URL: {link_url}")
                            # 此处可以根据需要添加更多错误处理或重试逻辑

                    except Exception as e_inner:
                        self.logger.error(f"处理单个新闻链接 {link_url} 时出错: {str(e_inner)}")
                        self.logger.error(traceback.format_exc())
                        continue # 继续处理下一个链接
            
            except Exception as e_outer:
                self.logger.error(f"处理页面 {page_url} (分类: {category_name}) 时出错: {str(e_outer)}")
                self.logger.error(traceback.format_exc())
                continue # 继续处理下一个分类页面
        
        self.logger.info(f"凤凰财经新闻爬取完成，共尝试处理/保存 {len(crawled_news_items)} 条新闻。")
        return crawled_news_items
    
    def get_news_links(self, url, category):
        """
        获取分类页面的新闻链接
        
        Args:
            url (str): 分类页面URL
            category (str): 分类名称
            
        Returns:
            list: 新闻链接列表
        """
        try:
            # 请求分类页面
            headers = {'User-Agent': random.choice(self.USER_AGENTS)}
            
            # 创建新会话，避免连接被重置问题
            session = requests.Session()
            
            # 禁用SSL验证，避免某些证书问题
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass

            try:
                # 使用新创建的session对象，而不是self.session
                response = session.get(
                    url, 
                    headers=headers, 
                    timeout=15,
                    verify=False  # 禁用SSL验证 
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.error(f"请求分类页面失败: {str(e)}, URL: {url}")
                # 重试一次
                time.sleep(random.uniform(2, 5))
                try:
                    # 使用新创建的session对象进行重试
                    response = session.get(
                        url,
                        headers=headers,
                        timeout=20,  # 增加超时时间
                        verify=False
                    )
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    logger.error(f"第二次请求分类页面失败: {str(e)}, URL: {url}")
                    return []
            
            # 检测并处理编码
            if hasattr(self, '_handle_encoding'):
                html_content = self._handle_encoding(response)
            else:
                # 尝试自动检测编码
                encoding = self.detect_encoding(response.content) if hasattr(self, 'detect_encoding') else 'utf-8'
                html_content = response.content.decode(encoding, errors='ignore')
            
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取新闻链接
            news_links = []
            
            # 1. 从普通链接获取
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                
                # 确保链接是完整的URL
                if href.startswith('//'):
                    href = 'https:' + href
                elif not href.startswith('http'):
                    # 相对路径转绝对路径
                    if href.startswith('/'):
                        base_url = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(url))
                        href = base_url + href
                    else:
                        continue  # 跳过不完整的链接
                
                # 过滤非新闻链接
                if self.is_valid_news_url(href):
                    news_links.append(href)
            
            # 2. 特别处理首页上的特色栏目（如"操盘热点"、"IPO观察哨"等）
            hot_sections = [
                'Trading Hotspots', 'Hot List', 'Financial News', 
                'IPO观察哨', '操盘热点', '热榜', '财经要闻', '全球快报'
            ]
            
            for section in hot_sections:
                # 查找可能表示栏目的元素
                section_headers = soup.find_all(['h2', 'h3', 'div', 'span', 'a'], 
                                               string=lambda s: s and section in s)
                
                for header in section_headers:
                    # 查找栏目的父容器
                    container = header
                    for _ in range(3):  # 向上查找最多3层
                        if container.parent:
                            container = container.parent
                        else:
                            break
                    
                    # 从容器中提取链接
                    if container:
                        for link in container.find_all('a', href=True):
                            href = link['href']
                            
                            # 格式化URL
                            if href.startswith('//'):
                                href = 'https:' + href
                            elif not href.startswith('http'):
                                if href.startswith('/'):
                                    base_url = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(url))
                                    href = base_url + href
                                else:
                                    continue
                            
                            if self.is_valid_news_url(href):
                                news_links.append(href)
            
            # 3. 爬取"中国深度财经"、"IPO观察哨"等特色栏目
            if category in ['中国深度财经', 'IPO观察哨', '上市公司', '绿色发展']:
                # 查找文章卡片和列表项
                article_cards = soup.find_all(['div', 'li'], class_=lambda c: c and any(
                    term in str(c).lower() for term in ['card', 'article', 'news-item', 'list-item']))
                
                for card in article_cards:
                    links = card.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        
                        # 格式化URL
                        if href.startswith('//'):
                            href = 'https:' + href
                        elif not href.startswith('http'):
                            if href.startswith('/'):
                                base_url = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(url))
                                href = base_url + href
                            else:
                                continue
                        
                        if self.is_valid_news_url(href):
                            news_links.append(href)
            
            # 去重
            news_links = list(set(news_links))
            
            logger.info("分类 %s 找到 %d 条新闻链接", category, len(news_links))
            return news_links
        except requests.exceptions.RequestException as e:
            logger.error("请求分类页面出错：%s，错误：%s", url, str(e))
            return []
        except Exception as e:
            logger.error("处理分类页面出错：%s，错误：%s", url, str(e))
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def detect_encoding(self, content):
        """
        检测内容的编码格式
        
        Args:
            content: 二进制内容
            
        Returns:
            str: 检测到的编码
        """
        try:
            # 使用chardet检测编码
            result = chardet.detect(content)
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0)
            
            logger.debug("检测到编码: %s, 置信度: %.2f", encoding, confidence)
            
            # 如果置信度较低，使用常见中文编码尝试解码
            if confidence < 0.7:
                encodings = ['utf-8', 'gbk', 'gb18030', 'big5']
                for enc in encodings:
                    try:
                        content.decode(enc)
                        logger.info("低置信度情况下成功使用 %s 解码", enc)
                        return enc
                    except UnicodeDecodeError:
                        continue
            
            return encoding or 'utf-8'
        except Exception as e:
            logger.warning("编码检测失败: %s", str(e))
            return 'utf-8'
    
    def _handle_encoding(self, response):
        """
        处理响应的编码问题，确保返回UTF-8字符串
        
        Args:
            response: requests 响应对象
            
        Returns:
            str: 处理后的文本内容 (UTF-8)
        """
        content_bytes = response.content
        apparent_encoding = response.apparent_encoding
        final_encoding = None
        decoded_text = None

        try:
            # 1. 使用统一的 _detect_encoding 方法获取最佳猜测编码
            # 注意：这个方法现在在后面定义（约 L975）
            # 它内部包含了 meta tag, apparent_encoding, 强制规则, 尝试解码列表, 默认utf-8 的逻辑
            detected_encoding = self._detect_encoding(content_bytes)
            final_encoding = detected_encoding # 以检测结果为准
            
            # 2. 尝试使用检测到的编码进行解码
            try:
                decoded_text = content_bytes.decode(final_encoding)
                logger.debug(f"使用检测/推断出的编码 '{final_encoding}' 成功解码.")
            except UnicodeDecodeError:
                logger.warning(f"使用检测/推断出的编码 '{final_encoding}' 解码失败. 将回退到 utf-8 (ignore errors).")
                final_encoding = 'utf-8' # 更新最终使用的编码记录
                decoded_text = content_bytes.decode(final_encoding, errors='ignore')
            except Exception as decode_err: # 其他可能的解码错误
                logger.error(f"使用编码 '{final_encoding}' 解码时发生未知错误: {decode_err}. 将回退到 utf-8 (ignore errors).")
                final_encoding = 'utf-8'
                decoded_text = content_bytes.decode(final_encoding, errors='ignore')

            # 3. （可选）进行文本清理
            # decoded_text = self.clean_text(decoded_text) # 如果需要在这里进行清理
            
            return decoded_text

        except Exception as e:
            logger.error(f"处理编码时发生意外错误: {str(e)}. 返回 utf-8 (ignore errors) 解码结果。")
            # 最终回退
            return content_bytes.decode('utf-8', errors='ignore')
    
    def clean_text(self, text):
        """
        清理文本，处理特殊字符和乱码
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""
        
        # 确保输入是字符串
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                return ""
        
        # 处理潜在的乱码
        try:
            # 如果文本看起来是乱码，尝试检测并修复
            if any(ord(c) > 127 for c in text[:20]) and any(c in text[:30] for c in 'äåæçèéêëìíîï'):
                # 可能是latin1误编码的utf-8
                try:
                    text = text.encode('latin1').decode('utf-8')
                except UnicodeError:
                    pass
        except Exception:
            pass
        
        # 应用多种解码处理
        text = decode_html_entities(text)
        text = decode_unicode_escape(text)
        text = decode_url_encoded(text)
        
        # 替换常见问题字符
        text = text.replace('\xa0', ' ')  # 替换不间断空格
        text = text.replace('\u3000', ' ')  # 替换全角空格
        
        # 处理多余空白
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
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
        self.logger.debug(f"[IfengCrawler.fetch_page] Calling super().fetch_page() for URL: {url}")
        try:
            return super().fetch_page(url, params=params, headers=headers, max_retries=max_retries, timeout=timeout)
        except Exception as e:
            self.logger.error(f"[IfengCrawler.fetch_page] Error calling super().fetch_page() for {url}: {e}", exc_info=True)
            return None
    
    def get_news_detail(self, url, category=None, retry=0):
        """获取新闻详情并处理"""
        if retry > 3:
            logger.error(f"获取新闻详情失败，已重试{retry}次，放弃: {url}")
            return None

        try:
            logger.info(f"获取新闻详情: {url}, 分类: {category or '未知'}")
            
            # 更健壮的请求处理
            try:
                # 禁用SSL验证，避免某些证书问题
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                # 创建自定义请求头
                headers = {
                    'User-Agent': random.choice(self.USER_AGENTS),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Referer': 'https://finance.ifeng.com/',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0'
                }
                
                # 创建新会话避免之前的连接问题
                session = requests.Session()
                response = session.get(
                    url, 
                    headers=headers, 
                    timeout=30,
                    verify=False,  # 禁用SSL验证
                    stream=False   # 不使用流式传输
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求异常 (尝试 {retry+1}/3): {str(e)}, URL: {url}")
                if retry < 3:
                    # 指数退避策略
                    sleep_time = (2 ** retry) + random.uniform(0, 1)
                    logger.info(f"等待 {sleep_time:.2f} 秒后重试...")
                    time.sleep(sleep_time)
                    return self.get_news_detail(url, category, retry + 1)
                return None
            
            # 使用编码修复功能处理响应
            if hasattr(self, 'encoding_fix_enabled') and self.encoding_fix_enabled:
                html = self._handle_encoding(response)
            else:
                html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 获取标题 - 扩展标题获取方法
            title_elem = None
            for selector in ['.news-title', '.hl', 'h1', 'title', 'h1.title', 'h1.headline-title', 'h1.news-title-h1']:
                title_elem = soup.select_one(selector)
                if title_elem:
                    break
                
            title = title_elem.text.strip() if title_elem else ""
            
            # 移除标题中的网站名称（如"_凤凰网"）
            title = re.sub(r'_凤凰网$', '', title)
            title = re.sub(r'_.*?网$', '', title)
            title = re.sub(r'\s*\|\s*IPO观察哨$', '', title)
            
            # 使用编码修复功能处理标题
            if hasattr(self, 'encoding_fix_enabled') and self.encoding_fix_enabled and title:
                try:
                    title = self.clean_text(title)
                    logger.info(f"标题编码修复成功: {title}")
                except Exception as e:
                    logger.error(f"标题编码修复失败: {str(e)}")
            
            # 获取内容 - 使用多种可能的内容选择器
            content = None
            content_selectors = [
                'div.main-content', 'div.article-content', 'div.news-content', 
                'div.content', 'article', '.story', '#main_content',
                '.news-body', '.article_body'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # 过滤掉不需要的元素
                    for tag in content_elem.select('script, style, .advertisement, .ad, .recommend, .related, .footer, .copyright'):
                        tag.decompose()
                    
                    # 提取内容HTML
                    content = str(content_elem)
                    break
                
            if not content:
                # 最后的尝试：使用p标签
                paragraphs = soup.select('p')
                if paragraphs:
                    content = ''.join(str(p) for p in paragraphs)
            
            # 提取发布时间
            pub_time = self.extract_pub_time(soup)
            
            # 提取作者
            author = self.extract_author(soup)
            
            # 提取分类
            category = None
            category_patterns = [
                '.category', '.channel', '.belong', '.article-channel',
                '.breadcrumb a', '.nav-wrap a', '.site-nav a'
            ]
            
            for pattern in category_patterns:
                category_elems = soup.select(pattern)
                if category_elems:
                    # 使用最后一个面包屑或导航项作为分类
                    category = category_elems[-1].get_text().strip()
                    break
                
            if not category:
                # 默认分类
                category = "财经"
            
            # 构建新闻数据
            news_data = {
                'url': url,
                'title': title,
                'content': content,
                'pub_time': pub_time,
                'author': author,
                'category': category,
                'sentiment': None,  # SQLiteManager._preprocess_news_data 会处理默认值
            }
            
            return news_data
            
        except Exception as e:
            logger.error(f"获取新闻详情异常: {str(e)}, URL: {url}")
            import traceback
            logger.error(traceback.format_exc())
            if retry < 3:
                # 指数退避策略
                sleep_time = (2 ** retry) + random.uniform(0, 1)
                logger.info(f"等待 {sleep_time:.2f} 秒后重试...")
                time.sleep(sleep_time)
                return self.get_news_detail(url, category, retry + 1)
            return None
    
    def extract_pub_time(self, soup):
        """
        提取发布时间
        
        Args:
            soup (BeautifulSoup): 解析后的HTML
            
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
            
            # 如果没有匹配到时间，使用当前时间
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.warning("提取发布时间失败：%s", str(e))
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def extract_author(self, soup):
        """
        提取作者
        
        Args:
            soup (BeautifulSoup): 解析后的HTML
            
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
            logger.warning("提取作者失败：%s", str(e))
            return "凤凰财经"
    
    def extract_related_stocks(self, soup):
        """
        提取相关股票
        
        Args:
            soup (BeautifulSoup): 解析后的HTML
            
        Returns:
            list: 相关股票列表
        """
        try:
            # 尝试从页面提取相关股票信息
            stock_tags = soup.select('a.stock')
            related_stocks = []
            for stock_tag in stock_tags:
                stock_code = stock_tag.text.strip()
                if stock_code:
                    related_stocks.append(stock_code)
            
            return related_stocks
        except Exception as e:
            logger.warning("提取相关股票失败：%s", str(e))
            return []
    
    def is_valid_news_url(self, url):
        """
        判断URL是否为有效的新闻链接
        
        Args:
            url (str): 链接URL
            
        Returns:
            bool: 是否为有效的新闻链接
        """
        # 检查URL是否为空
        if not url:
            return False
            
        # 检查URL是否为广告
        if self.ad_filter.is_ad_url(url):
            logger.info("过滤广告URL：%s", url)
            return False
            
        # 凤凰财经新闻URL模式
        patterns = [
            r'https?://finance\.ifeng\.com/\w/\d+/\d+_\d+\.shtml',
            r'https?://finance\.ifeng\.com/c/[a-zA-Z0-9]+',  # 新版文章URL模式 /c/8eJNY7hopdJ
            r'https?://finance\.ifeng\.com/a/\d+/\d+_\d+\.shtml',
            r'https?://finance\.ifeng\.com/[a-z]+/[a-z0-9]+/detail_\d+_\d+\.shtml',
            r'https?://finance\.ifeng\.com/[a-z]+/[a-z0-9]+/[a-zA-Z0-9]+',
        ]
        
        for pattern in patterns:
            if re.match(pattern, url):
                return True
                
        # 2024年新增：检查是否包含关键词路径
        key_paths = ['/c/', '/deepfinance/', '/stock/', '/ipo/', '/listedcompany/', '/greenfinance/']
        for path in key_paths:
            if path in url and 'finance.ifeng.com' in url:
                return True
        
        return False

    def _process_news_content(self, content, news_id=None, url=None):
        """
        处理新闻内容，提取图片、优化格式
        
        Args:
            content: HTML内容
            news_id: 新闻ID，用于图片保存
            url: 原始URL，用于处理相对路径
            
        Returns:
            处理后的内容和提取的图片列表
        """
        if not content:
            return content, []
        
        try:
            # 解析HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # 清理不需要的元素
            for selector in [
                'script', 'style', '.ad', '.advertisement', '.recommend', '.footer',
                '.copyright', '.tool-bar', '.share-bar', 'iframe', 'ins', 
                'link', 'meta', 'noscript', 'object', 'embed', '.comment'
            ]:
                for element in soup.select(selector):
                    element.decompose()
            
            # 提取图片
            images = []
            processed_urls = set()  # 用于去重
            
            # 1. 查找所有常规图片标签
            img_tags = soup.select('img')
            self.logger.info(f"在内容中找到 {len(img_tags)} 个图片标签")
            
            for img in img_tags:
                # 尝试不同属性获取图片URL
                img_url = None
                
                # 检查各种可能的图片属性
                for attr in ['src', 'data-src', 'data-original', 'data-original-src', 'data-lazy-src', 'data-lazysrc', 'data-lazyload']:
                    if img.get(attr):
                        img_url = img.get(attr)
                        if img_url and img_url.strip():
                            break
                
                # 如果没有找到图片URL，跳过
                if not img_url or not img_url.strip():
                    continue
                
                img_url = img_url.strip()
                
                # 处理相对URL
                if not img_url.startswith(('http://', 'https://')):
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif url:
                        base_url = '/'.join(url.split('/')[:3])  # http(s)://domain.com
                        if img_url.startswith('/'):
                            img_url = base_url + img_url
                        else:
                            img_url = base_url + '/' + img_url
                    else:
                        continue
                
                # 过滤小图标、广告等无用图片
                skip_patterns = ['logo', 'icon', 'avatar', 'ad', 'banner', '.gif', '.svg', 'pixel.', 'blank.', 
                                'stat', 'tracker', 'analytics', '1x1', 'spacer', 'transparent']
                if any(pattern in img_url.lower() for pattern in skip_patterns):
                    self.logger.debug(f"跳过无用图片: {img_url}")
                    continue
                
                # 去重
                if img_url in processed_urls:
                    continue
                processed_urls.add(img_url)
                
                # 处理alt文本
                alt = img.get('alt', '').strip()
                if not alt and img.get('title'):
                    alt = img.get('title').strip()
                
                # 如果alt为空，尝试从周围文本提取描述
                if not alt:
                    parent = img.parent
                    if parent:
                        parent_text = parent.get_text().strip()
                        if parent_text:
                            alt = parent_text[:50] + ('...' if len(parent_text) > 50 else '')
                
                # 保存图片信息
                images.append({
                    'url': img_url,
                    'alt': alt or '凤凰财经图片',
                    'original_url': img_url
                })
                
                # 优化图片标签
                img['loading'] = 'lazy'
                img['src'] = img_url  # 统一使用找到的URL
                img_classes = img.get('class', [])
                if isinstance(img_classes, str):
                    img_classes = [img_classes]
                if 'img-fluid' not in img_classes:
                    img_classes.append('img-fluid')
                if 'rounded' not in img_classes:
                    img_classes.append('rounded')
                img['class'] = ' '.join(img_classes)
                img['alt'] = alt or '凤凰财经图片'
                
                # 添加错误处理
                img['onerror'] = "this.onerror=null; this.src='/static/img/image-error.jpg'; this.alt='图片加载失败';"
            
            # 2. 查找背景图片样式
            for element in soup.select('[style*="background"]'):
                style = element.get('style', '')
                # 使用正则表达式提取背景图片URL
                bg_match = re.search(r'background(-image)?:\s*url\([\'"]?([^\'")]+)[\'"]?\)', style)
                if bg_match:
                    bg_url = bg_match.group(2).strip()
                    
                    # 处理相对URL
                    if not bg_url.startswith(('http://', 'https://')):
                        if bg_url.startswith('//'):
                            bg_url = 'https:' + bg_url
                        elif url:
                            base_url = '/'.join(url.split('/')[:3])
                            if bg_url.startswith('/'):
                                bg_url = base_url + bg_url
                            else:
                                bg_url = base_url + '/' + bg_url
                        else:
                            continue
                    
                    # 过滤和去重
                    if any(pattern in bg_url.lower() for pattern in skip_patterns) or bg_url in processed_urls:
                        continue
                    
                    processed_urls.add(bg_url)
                    
                    # 提取alt文本
                    alt = element.get('alt', '') or element.get('title', '')
                    if not alt:
                        alt = element.get_text().strip()[:50]
                    
                    # 保存图片信息
                    images.append({
                        'url': bg_url,
                        'alt': alt or '凤凰财经背景图片',
                        'original_url': bg_url
                    })
            
            # 3. 查找JSON数据中的图片URL
            for script in soup.find_all('script'):
                script_text = script.string
                if not script_text:
                    continue
                
                # 尝试查找常见的图片JSON格式
                img_patterns = [
                    r'"imageUrl"\s*:\s*"([^"]+)"',
                    r'"coverImage"\s*:\s*"([^"]+)"',
                    r'"image"\s*:\s*"([^"]+)"',
                    r'"img"\s*:\s*"([^"]+)"',
                    r'"pic"\s*:\s*"([^"]+)"'
                ]
                
                for pattern in img_patterns:
                    for match in re.finditer(pattern, script_text):
                        json_img_url = match.group(1).strip()
                        
                        # 处理相对URL
                        if not json_img_url.startswith(('http://', 'https://')):
                            if json_img_url.startswith('//'):
                                json_img_url = 'https:' + json_img_url
                            elif url:
                                base_url = '/'.join(url.split('/')[:3])
                                if json_img_url.startswith('/'):
                                    json_img_url = base_url + json_img_url
                                else:
                                    json_img_url = base_url + '/' + json_img_url
                            else:
                                continue
                        
                        # 过滤和去重
                        if any(pattern in json_img_url.lower() for pattern in skip_patterns) or json_img_url in processed_urls:
                            continue
                        
                        processed_urls.add(json_img_url)
                        
                        # 保存图片信息
                        images.append({
                            'url': json_img_url,
                            'alt': '凤凰财经文章图片',
                            'original_url': json_img_url
                        })
            
            # 4. 检查meta标签中的图片
            og_image = soup.select_one('meta[property="og:image"]')
            if og_image and og_image.get('content'):
                og_img_url = og_image.get('content').strip()
                
                # 处理相对URL
                if not og_img_url.startswith(('http://', 'https://')):
                    if og_img_url.startswith('//'):
                        og_img_url = 'https:' + og_img_url
                    elif url:
                        base_url = '/'.join(url.split('/')[:3])
                        if og_img_url.startswith('/'):
                            og_img_url = base_url + og_img_url
                        else:
                            og_img_url = base_url + '/' + og_img_url
                
                # 只有URL开始于http时才添加
                if og_img_url.startswith(('http://', 'https://')) and og_img_url not in processed_urls:
                    processed_urls.add(og_img_url)
                    
                    # 获取可能的描述
                    og_title = soup.select_one('meta[property="og:title"]')
                    og_desc = soup.select_one('meta[property="og:description"]')
                    alt_text = ''
                    
                    if og_title and og_title.get('content'):
                        alt_text = og_title.get('content')
                    elif og_desc and og_desc.get('content'):
                        alt_text = og_desc.get('content')
                    
                    # 保存图片信息
                    images.append({
                        'url': og_img_url,
                        'alt': alt_text or '凤凰财经封面图片',
                        'original_url': og_img_url
                    })
            
            # 处理链接
            for a in soup.select('a'):
                href = a.get('href', '')
                if href:
                    a['target'] = '_blank'
                    a['rel'] = 'noopener noreferrer'
                    
                    # 如果是相对链接，转换为绝对链接
                    if not href.startswith(('http://', 'https://', '#', 'mailto:', 'tel:')) and url:
                        base_url = '/'.join(url.split('/')[:3])
                        if href.startswith('/'):
                            a['href'] = base_url + href
                        else:
                            a['href'] = base_url + '/' + href
            
            # 优化段落和标题
            for p in soup.select('p'):
                if not p.get('class'):
                    p['class'] = 'article-paragraph'
            
            for h in soup.select('h1, h2, h3, h4, h5, h6'):
                if not h.get('class'):
                    h['class'] = f'article-heading article-{h.name}'
            
            # 返回处理后的内容和图片列表
            self.logger.info(f"成功提取 {len(images)} 个有效图片")
            return str(soup), images
            
        except Exception as e:
            self.logger.error(f"处理新闻内容失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return content, []

if __name__ == "__main__":
    # 测试爬虫
    crawler = IfengCrawler(use_proxy=False, use_source_db=True)
    news_list = crawler.crawl(days=1, max_news=5)
    print(f"爬取到新闻数量：{len(news_list)}")
    for news in news_list:
        print(f"标题：{news['title']}")
        print(f"发布时间：{news['pub_time']}")
        print(f"来源：{news['source']}")
        print("-" * 50) 