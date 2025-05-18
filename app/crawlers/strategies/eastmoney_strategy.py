#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 东方财富网站爬虫策略
实现东方财富网站特定的爬取规则
"""

import re
import json
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from app.crawlers.strategies.base_strategy import BaseCrawlerStrategy
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html, clean_text

# 初始化日志记录器 - 使用爬虫专用日志记录器
logger = get_crawler_logger('eastmoney')

class EastMoneyStrategy(BaseCrawlerStrategy):
    """东方财富网站爬虫策略"""
    
    def __init__(self, source: str):
        """
        初始化策略
        
        Args:
            source: 数据源名称
        """
        super().__init__(source)
        
        # 设置东方财富的分类映射
        self.categories = {
            '财经': 'https://finance.eastmoney.com/',
            '股票': 'https://stock.eastmoney.com/',
            '基金': 'https://fund.eastmoney.com/',
            '债券': 'https://bond.eastmoney.com/'
        }
        
        # 基础URL
        self.base_url = 'https://www.eastmoney.com'
        self.finance_base_url = 'https://finance.eastmoney.com'
        
        # 列表页URL模板
        self.list_page_templates = {
            '财经': [
                'https://finance.eastmoney.com/a/cywjh_{}.html',       # 要闻精华
                'https://finance.eastmoney.com/a/czqyw_{}.html',       # 证券要闻
                'https://finance.eastmoney.com/yaowen.html'            # 焦点 - 有效链接
            ],
            '股票': [
                'https://stock.eastmoney.com/a/cgsxw_{}.html',         # 股市新闻
                'http://finance.eastmoney.com/news/cgspl.html'         # 股市评论 - 有效链接
            ],
            '基金': [
                'https://fund.eastmoney.com/a/cjjdt_{}.html',          # 基金动态 
                'https://fund.eastmoney.com/a/cjjgd_{}.html',          # 基金观点
                'https://fund.eastmoney.com/news/cjjyj.html'           # 基金研究首页 - 有效链接
            ]
        }
        
        logger.info(f"东方财富爬虫策略初始化完成")
    
    def get_list_page_urls(self, days: int = 1, category: Optional[str] = None) -> List[str]:
        """
        获取列表页URL
        
        Args:
            days: 爬取最近几天的新闻
            category: 新闻分类
            
        Returns:
            List[str]: 列表页URL列表
        """
        # 生成列表页URL
        list_urls = []
        
        # 根据天数决定页数，每天平均10条新闻，一页通常有20条，所以pages = days/2 向上取整
        page_count = max(1, (days + 1) // 2)  
        max_pages = min(5, page_count)  # 限制最大页数为5，避免爬取过多
        
        # 确定要爬取的分类
        if category and category in self.categories:
            categories_to_crawl = [category]
        else:
            # 默认只爬取财经、股票和基金分类
            categories_to_crawl = ['财经', '股票', '基金']
        
        # 添加分类首页 - 确保首页可访问
        for cat in categories_to_crawl:
            if cat in self.categories:
                list_urls.append(self.categories[cat])
        
        # 更新列表页URL模板 - 使用实际可访问的URL格式
        working_templates = {
            '财经': [
                'https://finance.eastmoney.com/a/cywjh_{}.html',  # 要闻精华
                'https://finance.eastmoney.com/a/czqyw_{}.html',  # 证券要闻
                'https://finance.eastmoney.com/yaowen.html' # 焦点 - 有效链接
            ],
            '股票': [
                'https://stock.eastmoney.com/a/cgsxw_{}.html',    # 股市新闻
                'http://finance.eastmoney.com/news/cgspl.html'  # 股市评论 - 有效链接
            ],
            '基金': [
                'https://fund.eastmoney.com/a/cjjdt_{}.html',     # 基金动态 
                'https://fund.eastmoney.com/a/cjjgd_{}.html',     # 基金观点
            ]
        }
        
        # 添加分类列表页
        for cat in categories_to_crawl:
            if cat in working_templates:
                templates = working_templates[cat]
                # 添加多个模板的多个页码，确保抓取足够多的内容
                for template in templates:
                    if '{}' in template:  # 只有包含格式化占位符的模板才需要替换页码
                        for i in range(1, max_pages + 1):
                            list_urls.append(template.format(i))
                    else:  # 对于不包含格式化占位符的URL，直接添加
                        list_urls.append(template)
        
        # 添加首页
        if 'https://www.eastmoney.com/' not in list_urls:
            list_urls.append('https://www.eastmoney.com/')

        # 添加特定页面，确保能获取重要内容
        special_urls = [
            'https://www.1234567.com.cn/',                             # 基金资讯首页
            'https://fund.eastmoney.com/news/cjjyj.html',              # 基金研究首页
            'https://fund.eastmoney.com/data/fundranking.html',        # 基金排行
            'https://fund.eastmoney.com/data/fundrating.html',         # 基金评级
            'https://fund.eastmoney.com/dingtou/syph_yndt.html',       # 基金定投
            'https://fund.eastmoney.com/data/xinfund.html',            # 新发基金
            'http://finance.eastmoney.com/a/ccjdd.html',               # 财经导读 - 有效链接
            'https://finance.eastmoney.com/yaowen.html'                # 焦点
        ]
        for url in special_urls:
            if url not in list_urls:
                list_urls.append(url)
            
        # 去重
        list_urls = list(dict.fromkeys(list_urls))
        
        logger.info(f"生成 {len(list_urls)} 个列表页URL，分类: {category or '默认'}")
        
        return list_urls
    
    def parse_list_page(self, html: str, url: str) -> List[str]:
        """
        解析列表页，获取文章URL列表
        
        Args:
            html: 列表页HTML内容
            url: 列表页URL
            
        Returns:
            List[str]: 文章URL列表
        """
        if not html:
            logger.warning(f"列表页内容为空: {url}")
            return []
            
        article_urls = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # 主页模式
        if url in ['https://www.eastmoney.com/', 'https://finance.eastmoney.com/'] or url in self.categories.values():
            # 提取新闻列表
            news_selectors = [
                '.news-list li a', 
                '.focus-list li a',
                '.title a',
                '.news-item a',
                '.news_item a',
                '.news-body a',
                '.news-cnt h3 a', 
                '.news-tab .item>a', 
                '.slider-news-list a.news-item'
            ]
            
            for selector in news_selectors:
                items = soup.select(selector)
                for item in items:
                    href = item.get('href')
                    if href and self._is_valid_link(href):
                        full_url = self._normalize_url(href, url)
                        if full_url and full_url not in article_urls:
                            article_urls.append(full_url)
        
        # 列表页模式
        else:
            # 提取新闻项
            news_selectors = [
                '.news-item a', 
                '.news-list li a', 
                '.title a',
                '.news_item a', 
                '.list-wrap .list-item a',
                '.listContent .list-item a',
                'ul.list li a'
            ]
            
            for selector in news_selectors:
                items = soup.select(selector)
                for item in items:
                    href = item.get('href')
                    if href and self._is_valid_link(href):
                        full_url = self._normalize_url(href, url)
                        if full_url and full_url not in article_urls:
                            article_urls.append(full_url)
        
        # 过滤有效的URL
        filtered_urls = self._filter_valid_urls(article_urls)
        
        logger.info(f"从列表页 {url} 解析出 {len(filtered_urls)} 个有效文章URL")
        
        return filtered_urls
    
    def _is_valid_link(self, href: str) -> bool:
        """判断链接是否有效"""
        # 排除空链接、JavaScript链接和锚点链接
        if not href or href.startswith(('javascript:', '#')):
            return False
        return True
    
    def _normalize_url(self, href: str, base_url: str) -> str:
        """规范化URL"""
        if href.startswith('//'):
            return 'https:' + href
        elif not href.startswith(('http://', 'https://')):
            return urljoin(base_url, href)
        return href
    
    def _filter_valid_urls(self, urls: List[str]) -> List[str]:
        """过滤有效的新闻URL"""
        valid_domains = [
            'eastmoney.com', 
            'finance.eastmoney.com', 
            'stock.eastmoney.com',
            'fund.eastmoney.com', 
            'bond.eastmoney.com',
            'money.eastmoney.com',
            'forex.eastmoney.com',
            'futures.eastmoney.com',
            'global.eastmoney.com',
            'data.eastmoney.com',
            'hk.eastmoney.com',
            'tech.eastmoney.com',
            'video.eastmoney.com'  # 添加视频域名
        ]
        
        invalid_keywords = [
            'list', 'index.html', 'search', 'help', 'about', 'contact',
            'login', 'register', 'download', 'app', 'special', 'quote',
            'data', 'f10', 'api', 'static', 'so.eastmoney', 'guba', 'bbs',
            'blog', 'live', 'wap', 'zhuanti', 'trade', 'default.html',  # 添加更多无效关键词
            'mobile', 'column', 'home', 'main', 'banner', 'redirect'
        ]
        
        # 特定类型的有效URL关键词
        valid_overrides = [
            '/a/', '/news/', '/article/', '/content/', '/yw/', '/cj/',
            '/stock/news', '/fund/news', '/bond/news',
            '/article_', '/2023', '/2024',
            '/ccjdd',    # 财经导读有效
            '/cgspl',    # 股市评论有效
            'yaowen'     # 要闻有效
        ]
        
        filtered = []
        
        for url in urls:
            # 验证URL格式
            if not url or not isinstance(url, str):
                continue
                
            # 规范化URL - 移除URL中的空格和无效字符
            url = url.strip()
            
            # 尝试修复常见的URL问题
            if url.startswith('//'):
                url = 'https:' + url
            
            # 解析URL
            try:
                parsed = urlparse(url)
                # 检查是否包含有效的协议和域名
                if not parsed.scheme or not parsed.netloc:
                    continue
            except Exception:
                # URL格式无效
                continue
            
            # 检查域名
            if not any(domain in parsed.netloc for domain in valid_domains):
                continue
                
            # 特殊处理：直接通过有效关键词进行判断
            if any(override in url for override in valid_overrides):
                if url not in filtered:
                    filtered.append(url)
                continue
                
            # 检查URL是否是广告、登录等常见的非内容页面
            if any(keyword in url.lower() for keyword in invalid_keywords):
                continue
            
            # 检查是否是新闻URL
            # 优先检查URL模式
            patterns = [
                r'https?://finance\.eastmoney\.com/a/\d+\w*\.html',
                r'https?://finance\.eastmoney\.com/news/\d+,\d+\.html',
                r'https?://stock\.eastmoney\.com/a/\d+\w*\.html',
                r'https?://fund\.eastmoney\.com/a/\d+\w*\.html',
                r'https?://bond\.eastmoney\.com/a/\d+\w*\.html',
                r'https?://forex\.eastmoney\.com/a/\d+\w*\.html',
                r'https?://finance\.eastmoney\.com/news/\w+,\w+\.html',
                r'https?://stock\.eastmoney\.com/news/\w+,\w+\.html',
                r'https?://fund\.eastmoney\.com/news/\d+,\d+\.html',     # 基金新闻
                r'https?://hk\.eastmoney\.com/a/\d+\w*\.html',           # 港股新闻
                r'https?://video\.eastmoney\.com/a/\d+\w*\.html',        # 视频新闻
                r'https?://stock\.eastmoney\.com/a/\d+\.html'            # 股票新闻
            ]
            
            is_valid = False
            for pattern in patterns:
                if re.match(pattern, url):
                    is_valid = True
                    break
                    
            if not is_valid:
                # 检查URL是否包含日期或特定路径
                has_date = re.search(r'/20\d{2}', url)
                has_news_path = any(path in url for path in ['/a/', '/news/', '/article/', '/content/'])
                
                # 对于没有明显标识但以.html结尾的URL，检查URL结构
                if url.endswith('.html'):
                    # 提取路径，查看是否有新闻特征
                    path_parts = parsed.path.split('/')
                    
                    # 如果路径短且没有明显新闻特征，可能不是新闻页面
                    if len(path_parts) <= 2 and not has_date and not has_news_path:
                        # 对于首页和分类首页，检查是否包含"news"或"新闻"
                        if any(term in url for term in ['news', 'a/', '新闻']):
                            is_valid = True
                        else:
                            continue
                    else:
                        # 较长路径的.html文件，更可能是新闻
                        is_valid = True
                else:
                    # 不以.html结尾的URL，除非有明确的新闻路径标识，否则跳过
                    continue
            
            # 确保URL未重复
            if url not in filtered:
                filtered.append(url)
                
        logger.info(f"过滤前URL数量: {len(urls)}，过滤后: {len(filtered)}")
        return filtered
    
    def parse_detail_page(self, html: str, url: str) -> Dict[str, Any]:
        """
        解析详情页，获取文章内容
        
        Args:
            html: 详情页HTML内容
            url: 详情页URL
            
        Returns:
            Dict[str, Any]: 文章内容字典
        """
        if not html:
            logger.warning(f"详情页内容为空: {url}")
            # 改为返回最小可用数据，而不是抛出异常
            return {
                'id': hashlib.md5(url.encode('utf-8')).hexdigest(),
                'title': "内容为空",
                'content': "",
                'content_html': "",
                'pub_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'author': "",
                'source': self.source,
                'url': url,
                'keywords': "",
                'images': None,
                'related_stocks': None,
                'category': '财经',  # 默认分类
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        try:
            logger.info(f"开始解析详情页: {url}")
            soup = BeautifulSoup(html, 'html.parser')
            
            # 解析标题 - 添加更多选择器以提高成功率
            title_selectors = [
                '.newsContent .title', 
                '.detail-title',
                'h1', 
                '.article-title', 
                '.title',
                '.news_title',
                '.article h1',
                '.main-content h1',
                '.content-title'
            ]
            
            title = ""
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.text.strip()
                    logger.debug(f"使用选择器 '{selector}' 找到标题: {title}")
                    break
                    
            if not title:
                # 如果所有选择器都失败，尝试使用页面标题
                if soup.title:
                    title = soup.title.text.strip()
                    # 清理标题中的网站名称
                    title = re.sub(r'[-_|].*?$', '', title).strip()
                    logger.debug(f"使用页面标题作为替代: {title}")
                else:
                    title = "未知标题"
                    logger.warning(f"无法提取标题: {url}")
            
            # 解析内容 - 使用更多选择器并尝试多种方法
            content_selectors = [
                '.article-content', 
                '.newsContent .body', 
                '.ContentBody',
                '.content',
                '#content', 
                '.article', 
                '.detail-body', 
                '.main-text',
                '.news-body',
                '.text',
                '.article-text',
                '.text-body',
                '.txtinfos',
                '.article-cont',
                '.news-content',
                '#artibody',
                '.ctn-text',
                '.Container',
                '#ctrlfscont',
                '.Body'
            ]
            
            content_elem = None
            content_html = ""
            content = ""
            
            # 尝试多个选择器查找内容
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem and len(content_elem.text.strip()) > 100:  # 确保内容足够长
                    # 移除不需要的元素，如广告、分享按钮等
                    for remove_sel in ['script', 'style', 'iframe', '.advertise', '.advert', '.ad-content', '.share', '.related-news']:
                        for el in content_elem.select(remove_sel):
                            el.decompose()
                    
                    content_html = str(content_elem)
                    content = clean_html(content_html)
                    logger.debug(f"使用选择器 '{selector}' 找到内容 (长度: {len(content)})")
                    break
            
            # 如果所有选择器都失败，尝试找最长的div作为内容
            if not content or len(content) < 100:
                logger.warning(f"使用常规选择器无法提取内容，尝试备用方法: {url}")
                divs = soup.find_all('div')
                max_len = 0
                max_div = None
                
                for div in divs:
                    div_text = div.text.strip()
                    if len(div_text) > 200 and len(div_text) > max_len:
                        # 排除页面布局div
                        parent_classes = div.parent.get('class', [])
                        if not any(cls in ['header', 'footer', 'nav', 'sidebar', 'menu', 'navigation'] for cls in parent_classes):
                            max_len = len(div_text)
                            max_div = div
                
                if max_div:
                    # 移除不需要的元素
                    for remove_sel in ['script', 'style', 'iframe', '.advertise', '.advert', '.ad-content', '.share', '.related-news']:
                        for el in max_div.select(remove_sel):
                            el.decompose()
                            
                    content_html = str(max_div)
                    content = clean_html(content_html)
                    logger.debug(f"使用最长div作为内容 (长度: {len(content)})")
            
            # 解析发布时间 - 添加更多解析方法
            pub_time_selectors = [
                '.time', 
                '.date', 
                '.publish-time',
                '.news-time',
                '.article-info .time',
                '.article-info time',
                '.date-source',
                '.info span:first-child',
                '.article-meta span:first-child',
                '.news-info .date'
            ]
            
            pub_time = ""
            
            # 尝试多个选择器提取时间
            for selector in pub_time_selectors:
                pub_time_elem = soup.select_one(selector)
                if pub_time_elem:
                    pub_time_text = pub_time_elem.text.strip()
                    # 尝试提取日期时间格式
                    time_patterns = [
                        r'(\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2}(:\d{1,2})?)',
                        r'(\d{4}/\d{1,2}/\d{1,2}\s\d{1,2}:\d{1,2}(:\d{1,2})?)',
                        r'(\d{4}年\d{1,2}月\d{1,2}日\s\d{1,2}:\d{1,2}(:\d{1,2})?)',
                        r'(\d{4}-\d{1,2}-\d{1,2})',
                        r'(\d{4}/\d{1,2}/\d{1,2})',
                        r'(\d{4}年\d{1,2}月\d{1,2}日)'
                    ]
                    
                    for pattern in time_patterns:
                        match = re.search(pattern, pub_time_text)
                        if match:
                            pub_time = match.group(1)
                            # 标准化时间格式
                            pub_time = re.sub(r'年|月', '-', pub_time)
                            pub_time = re.sub(r'日', ' ', pub_time)
                            pub_time = re.sub(r'^\s+|\s+$', '', pub_time)
                            
                            # 处理只有日期没有时间的情况
                            if re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', pub_time):
                                pub_time += ' 00:00:00'
                            elif re.match(r'^\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}$', pub_time):
                                pub_time += ':00'
                                
                            logger.debug(f"使用选择器 '{selector}' 找到时间: {pub_time}")
                            break
                    
                    if pub_time:
                        break
            
            # 如果无法从页面提取时间，尝试从URL中提取
            if not pub_time:
                # 尝试从URL中提取日期
                url_date_patterns = [
                    r'/(\d{4})(\d{2})(\d{2})/',  # /20240421/
                    r'/(\d{4})-(\d{2})-(\d{2})/', # /2024-04-21/
                    r'/(\d{4})(\d{2})/(\d{2})/',  # /202404/21/
                    r'_(\d{4})(\d{2})(\d{2})'     # _20240421
                ]
                
                for pattern in url_date_patterns:
                    match = re.search(pattern, url)
                    if match:
                        year, month, day = match.groups()
                        pub_time = f"{year}-{month}-{day} 00:00:00"
                        logger.debug(f"从URL中提取到日期: {pub_time}")
                        break
            
            # 如果仍然无法提取时间，使用当前时间
            if not pub_time:
                pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.warning(f"无法提取发布时间，使用当前时间: {pub_time}")
            
            # 解析作者/来源
            author_selectors = [
                '.author', 
                '.source',
                '.article-source',
                '.news-info .source',
                '.article-info .source',
                '.date-source span:last-child',
                '.info .source',
                'span.source',
                'span.author',
                '.editor'
            ]
            
            author = ""
            for selector in author_selectors:
                author_elem = soup.select_one(selector)
                if author_elem:
                    author_text = author_elem.text.strip()
                    # 提取"来源："后面的内容
                    source_match = re.search(r'来源[:：]\s*(.+?)(?:\s|$)', author_text)
                    if source_match:
                        author = source_match.group(1).strip()
                    else:
                        author = author_text
                    
                    logger.debug(f"使用选择器 '{selector}' 找到作者/来源: {author}")
                    break
            
            if not author:
                author = "东方财富"
            
            # 解析图片 - 主要检查文章内容中的图片，而不是页面上的所有图片
            images = []
            
            # 如果有内容元素，从中提取图片
            if content_elem:
                img_elems = content_elem.select('img')
                for img in img_elems:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        # 过滤广告图片和图标
                        if any(kw in src.lower() for kw in ['ad', 'banner', 'logo', 'icon']):
                            continue
                            
                        # 规范化URL
                        if not src.startswith(('http://', 'https://')):
                            src = urljoin(url, src)
                        
                        if src not in images:
                            images.append(src)
            
            # 解析关键词
            keywords = []
            
            # 首先检查meta标签中的关键词
            meta_keywords = soup.select_one('meta[name="keywords"]')
            if meta_keywords and meta_keywords.get('content'):
                keywords_text = meta_keywords.get('content')
                if ',' in keywords_text:
                    keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
                elif '，' in keywords_text:
                    keywords = [kw.strip() for kw in keywords_text.split('，') if kw.strip()]
                else:
                    keywords = [keywords_text.strip()]
                    
                logger.debug(f"从meta标签提取到关键词: {keywords}")
            
            # 如果meta中没有关键词，尝试从页面中提取
            if not keywords:
                keyword_elems = soup.select('.keywords a, .article-keywords a, .tags a')
                for kw in keyword_elems:
                    keyword = kw.text.strip()
                    if keyword and keyword not in keywords:
                        keywords.append(keyword)
                
                if keywords:
                    logger.debug(f"从页面元素提取到关键词: {keywords}")
            
            # 解析相关股票
            related_stocks = []
            stock_selectors = [
                '.stock-info a', 
                '.related-stock a',
                '.stock-container a',
                '.stock a',
                '.stockcontent a'
            ]
            
            for selector in stock_selectors:
                stock_elems = soup.select(selector)
                for stock in stock_elems:
                    stock_code = stock.get('data-code') or ""
                    stock_name = stock.text.strip()
                    
                    # 尝试从文本中提取股票代码
                    if not stock_code and stock_name:
                        code_match = re.search(r'(\d{6})', stock_name)
                        if code_match:
                            stock_code = code_match.group(1)
                            stock_name = re.sub(r'\(\d{6}\)', '', stock_name).strip()
                    
                    if (stock_code or stock_name) and not any(s.get('code') == stock_code for s in related_stocks):
                        related_stocks.append({
                            'code': stock_code,
                            'name': stock_name
                        })
            
            logger.info(f"成功解析详情页: {url}, 标题: {title}, 内容长度: {len(content)}")
            
            # 构建文章数据
            article = {
                'id': hashlib.md5(url.encode('utf-8')).hexdigest(),
                'title': title,
                'content': content,
                'content_html': content_html,
                'pub_time': pub_time,
                'author': author,
                'source': self.source,
                'url': url,
                'keywords': ','.join(keywords),
                'images': json.dumps(images, ensure_ascii=False) if images else None,
                'related_stocks': json.dumps(related_stocks, ensure_ascii=False) if related_stocks else None,
                'category': self._determine_category(url, title, content),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return article
            
        except Exception as e:
            logger.error(f"解析详情页失败: {url}, 错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 返回最小可用数据而不是抛出异常，确保爬虫可以继续
            return {
                'id': hashlib.md5(url.encode('utf-8')).hexdigest(),
                'title': "解析失败",
                'content': f"解析错误: {str(e)}",
                'content_html': "",
                'pub_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'author': "",
                'source': self.source,
                'url': url,
                'keywords': "",
                'images': None,
                'related_stocks': None,
                'category': self._determine_category(url, "", ""),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def _determine_category(self, url: str, title: str, content: str) -> str:
        """
        根据URL和内容确定新闻分类
        
        Args:
            url: 文章URL
            title: 文章标题
            content: 文章内容
            
        Returns:
            str: 分类名称
        """
        # 从URL中尝试确定分类
        for category, category_url in self.categories.items():
            if category_url in url:
                return category
                
        # 从路径中尝试确定分类
        path = urlparse(url).path
        if '/stock/' in path or '/gupiao/' in path:
            return '股票'
        elif '/fund/' in path or '/jijin/' in path:
            return '基金'
        elif '/bond/' in path or '/zhaiquan/' in path:
            return '债券'
        elif '/money/' in path or '/licai/' in path:
            return '理财'
        
        # 根据标题和内容关键词判断
        keyword_mapping = {
            '股票': ['股票', '大盘', 'A股', '个股', '上证', '深证', '创业板', '港股', '美股'],
            '基金': ['基金', 'ETF', '指数基金', '公募基金', '私募基金', '基金经理'],
            '期货': ['期货', '期指', '原油', '商品期货'],
            '债券': ['债券', '国债', '公司债', '可转债', '利率债'],
            '理财': ['理财', '存款', '贷款', '保险', '银行', '储蓄', '资管'],
            '房产': ['房产', '楼市', '房价', '地产', '开发商', '二手房', '一手房'],
            '科技': ['科技', '互联网', '人工智能', '5G', '云计算', '大数据', '区块链']
        }
        
        for category, keywords in keyword_mapping.items():
            for keyword in keywords:
                if keyword in title or keyword in content[:500]:  # 只检查内容前500字符
                    return category
        
        # 默认分类
        return '财经' 