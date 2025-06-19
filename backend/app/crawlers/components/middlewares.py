#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 中间件组件
实现类似Django的请求处理链
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from abc import ABC, abstractmethod

from backend.app.utils.logger import get_crawler_logger

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('middlewares')

# 中间件类型定义
RequestMiddleware = Callable[[Dict], Dict]  # 处理请求的中间件
ResponseMiddleware = Callable[[Dict, Dict], Dict]  # 处理响应的中间件
ItemMiddleware = Callable[[Dict], Dict]  # 处理数据项的中间件


class MiddlewareManager:
    """中间件管理器，管理请求、响应和数据处理中间件"""
    
    def __init__(self):
        """初始化中间件管理器"""
        # 请求中间件列表
        self.request_middlewares = []
        
        # 响应中间件列表
        self.response_middlewares = []
        
        # 数据项中间件列表
        self.item_middlewares = []
        
        logger.info("中间件管理器初始化成功")
    
    def add_request_middleware(self, middleware: RequestMiddleware):
        """
        添加请求中间件
        
        Args:
            middleware: 请求中间件函数
        """
        self.request_middlewares.append(middleware)
        logger.info(f"添加请求中间件: {middleware.__name__}")
    
    def add_response_middleware(self, middleware: ResponseMiddleware):
        """
        添加响应中间件
        
        Args:
            middleware: 响应中间件函数
        """
        self.response_middlewares.append(middleware)
        logger.info(f"添加响应中间件: {middleware.__name__}")
    
    def add_item_middleware(self, middleware: ItemMiddleware):
        """
        添加数据项中间件
        
        Args:
            middleware: 数据项中间件函数
        """
        self.item_middlewares.append(middleware)
        logger.info(f"添加数据项中间件: {middleware.__name__}")
    
    def process_request(self, request: Dict) -> Dict:
        """
        处理请求
        
        Args:
            request: 请求参数
            
        Returns:
            Dict: 处理后的请求参数
        """
        for middleware in self.request_middlewares:
            try:
                request = middleware(request)
            except Exception as e:
                logger.error(f"请求中间件 {middleware.__name__} 处理失败: {str(e)}")
        
        return request
    
    def process_response(self, response: Dict, request: Dict) -> Dict:
        """
        处理响应
        
        Args:
            response: 响应结果
            request: 原始请求参数
            
        Returns:
            Dict: 处理后的响应结果
        """
        for middleware in self.response_middlewares:
            try:
                response = middleware(response, request)
            except Exception as e:
                logger.error(f"响应中间件 {middleware.__name__} 处理失败: {str(e)}")
        
        return response
    
    def process_item(self, item: Dict) -> Dict:
        """
        处理数据项
        
        Args:
            item: 数据项
            
        Returns:
            Dict: 处理后的数据项
        """
        for middleware in self.item_middlewares:
            try:
                item = middleware(item)
                # 如果中间件返回None，表示数据项被过滤掉
                if item is None:
                    return None
            except Exception as e:
                logger.error(f"数据项中间件 {middleware.__name__} 处理失败: {str(e)}")
        
        return item


# 预定义的中间件函数

def ua_rotation_middleware(request: Dict) -> Dict:
    """
    User-Agent轮换中间件
    
    Args:
        request: 请求参数
        
    Returns:
        Dict: 添加随机User-Agent后的请求参数
    """
    from backend.app.crawlers.components.requesters import SyncRequester
    
    # 创建临时请求器以使用其get_random_user_agent方法
    temp_requester = SyncRequester()
    
    # 获取随机User-Agent
    user_agent = temp_requester._get_random_user_agent()
    
    # 设置请求头
    if 'headers' not in request:
        request['headers'] = {}
    
    request['headers']['User-Agent'] = user_agent
    
    return request


def referer_middleware(request: Dict) -> Dict:
    """
    Referer中间件，添加Referer头
    
    Args:
        request: 请求参数
        
    Returns:
        Dict: 添加Referer后的请求参数
    """
    # 设置请求头
    if 'headers' not in request:
        request['headers'] = {}
    
    # 如果没有指定Referer，且有URL
    if 'Referer' not in request['headers'] and 'url' in request:
        url = request['url']
        
        # 生成合理的Referer
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        referer = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        
        request['headers']['Referer'] = referer
    
    return request


def rate_limiting_middleware(request: Dict) -> Dict:
    """
    速率限制中间件，避免请求过于频繁
    
    Args:
        request: 请求参数
        
    Returns:
        Dict: 处理后的请求参数
    """
    # 记录上次请求时间的字典
    if not hasattr(rate_limiting_middleware, 'last_request_time'):
        rate_limiting_middleware.last_request_time = {}
    
    # 获取域名
    from urllib.parse import urlparse
    
    if 'url' in request:
        parsed_url = urlparse(request['url'])
        domain = parsed_url.netloc
        
        # 检查上次请求时间
        current_time = time.time()
        if domain in rate_limiting_middleware.last_request_time:
            last_time = rate_limiting_middleware.last_request_time[domain]
            elapsed = current_time - last_time
            
            # 如果间隔太短，需要等待
            min_interval = request.get('min_interval', 1.0)  # 默认最小间隔1秒
            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                logger.debug(f"速率限制: 等待 {wait_time:.2f} 秒后请求 {domain}")
                time.sleep(wait_time)
        
        # 更新上次请求时间
        rate_limiting_middleware.last_request_time[domain] = time.time()
    
    return request


def request_logging_middleware(request: Dict) -> Dict:
    """
    请求日志中间件
    
    Args:
        request: 请求参数
        
    Returns:
        Dict: 处理后的请求参数
    """
    if 'url' in request:
        logger.info(f"发送请求: {request['url']}")
    
    return request


def response_logging_middleware(response: Dict, request: Dict) -> Dict:
    """
    响应日志中间件
    
    Args:
        response: 响应结果
        request: 原始请求参数
        
    Returns:
        Dict: 处理后的响应结果
    """
    if 'url' in request and 'status_code' in response:
        logger.info(f"收到响应: {request['url']}, 状态码: {response['status_code']}")
    
    return response


def error_retry_middleware(response: Dict, request: Dict) -> Dict:
    """
    错误重试中间件
    
    Args:
        response: 响应结果
        request: 原始请求参数
        
    Returns:
        Dict: 处理后的响应结果
    """
    # 如果状态码表示错误
    if 'status_code' in response and response['status_code'] >= 400:
        # 获取已重试次数
        retry_count = request.get('retry_count', 0)
        max_retries = request.get('max_retries', 3)
        
        if retry_count < max_retries:
            logger.warning(f"请求失败，状态码: {response['status_code']}，将进行第 {retry_count + 1} 次重试")
            
            # 更新请求参数
            request['retry_count'] = retry_count + 1
            
            # 设置退避时间
            backoff_time = 2 ** retry_count  # 指数退避
            logger.debug(f"等待 {backoff_time} 秒后重试")
            time.sleep(backoff_time)
            
            # 重新发送请求
            from backend.app.crawlers.components.requesters import SyncRequester
            requester = SyncRequester()
            
            try:
                url = request.get('url')
                params = request.get('params')
                headers = request.get('headers')
                timeout = request.get('timeout')
                
                content = requester.fetch(url, params, headers, timeout, max_retries=1)
                
                if content:
                    response['content'] = content
                    response['status_code'] = 200
                    logger.info(f"重试成功: {url}")
            except Exception as e:
                logger.error(f"重试失败: {str(e)}")
    
    return response


def content_type_middleware(response: Dict, request: Dict) -> Dict:
    """
    内容类型中间件，根据Content-Type处理响应
    
    Args:
        response: 响应结果
        request: 原始请求参数
        
    Returns:
        Dict: 处理后的响应结果
    """
    # 检查Content-Type
    content_type = response.get('headers', {}).get('Content-Type', '')
    
    # 如果是JSON
    if 'application/json' in content_type and 'content' in response:
        try:
            import json
            response['json'] = json.loads(response['content'])
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
    
    # 如果是XML
    elif ('application/xml' in content_type or 'text/xml' in content_type) and 'content' in response:
        try:
            from bs4 import BeautifulSoup
            response['xml'] = BeautifulSoup(response['content'], 'xml')
        except Exception as e:
            logger.error(f"XML解析失败: {str(e)}")
    
    # 如果是HTML
    elif 'text/html' in content_type and 'content' in response:
        try:
            from bs4 import BeautifulSoup
            response['html'] = BeautifulSoup(response['content'], 'html.parser')
        except Exception as e:
            logger.error(f"HTML解析失败: {str(e)}")
    
    return response


def ads_filter_middleware(item: Dict) -> Optional[Dict]:
    """
    广告过滤中间件，过滤掉广告内容
    
    Args:
        item: 数据项
        
    Returns:
        Optional[Dict]: 处理后的数据项，如果是广告则返回None
    """
    # 广告关键词
    ad_keywords = [
        '广告', '推广', 'AD', '赞助', '特惠', '活动', '下载APP', '打开APP',
        '立即下载', '立即注册', '点击查看', '点击下载', '点击注册'
    ]
    
    # 检查标题
    if 'title' in item:
        title = item['title']
        for keyword in ad_keywords:
            if keyword in title:
                logger.info(f"过滤广告: {title}")
                return None
    
    # 检查内容
    if 'content' in item:
        content = item['content']
        
        # 检查内容长度是否过短
        if len(content) < 100:
            # 如果内容过短，进一步检查是否包含广告关键词
            for keyword in ad_keywords:
                if keyword in content:
                    logger.info(f"过滤短广告内容: {item.get('title', '')}")
                    return None
    
    # 检查URL
    if 'url' in item:
        url = item['url'].lower()
        
        # 检查URL是否包含广告相关路径
        ad_paths = ['ad', 'ads', 'advertisement', 'promotion', 'sponsored']
        for path in ad_paths:
            if f'/{path}/' in url or f'/{path}?' in url:
                logger.info(f"过滤广告URL: {url}")
                return None
    
    return item


def duplicate_filter_middleware(item: Dict) -> Optional[Dict]:
    """
    去重中间件，过滤掉重复内容
    
    Args:
        item: 数据项
        
    Returns:
        Optional[Dict]: 处理后的数据项，如果是重复项则返回None
    """
    # 记录已处理的项目ID
    if not hasattr(duplicate_filter_middleware, 'processed_ids'):
        duplicate_filter_middleware.processed_ids = set()
    
    # 生成ID
    item_id = None
    
    # 如果有ID字段
    if 'id' in item:
        item_id = item['id']
    # 如果有URL字段
    elif 'url' in item:
        import hashlib
        item_id = hashlib.md5(item['url'].encode('utf-8')).hexdigest()
    # 如果有标题字段
    elif 'title' in item:
        import hashlib
        item_id = hashlib.md5(item['title'].encode('utf-8')).hexdigest()
    
    # 检查是否已处理
    if item_id and item_id in duplicate_filter_middleware.processed_ids:
        logger.debug(f"过滤重复项: {item.get('title', '')}")
        return None
    
    # 记录ID
    if item_id:
        duplicate_filter_middleware.processed_ids.add(item_id)
    
    return item


def sentiment_analysis_middleware(item: Dict) -> Dict:
    """
    情感分析中间件，添加情感分析结果
    
    Args:
        item: 数据项
        
    Returns:
        Dict: 添加情感分析结果后的数据项
    """
    # 如果已有情感分析结果，跳过
    if 'sentiment' in item:
        return item
    
    # 检查是否有内容
    if 'content' not in item or not item['content']:
        return item
    
    try:
        # 尝试导入情感分析器
        from backend.app.utils.sentiment_analyzer import SentimentAnalyzer
        
        # 创建情感分析器
        analyzer = SentimentAnalyzer()
        
        # 分析情感
        content = item['content']
        sentiment = analyzer.analyze(content)
        
        # 添加情感分析结果
        item['sentiment'] = sentiment
        
        logger.debug(f"完成情感分析: {item.get('title', '')}, 情感得分: {sentiment}")
        
    except ImportError:
        logger.warning("情感分析模块不可用")
    except Exception as e:
        logger.error(f"情感分析失败: {str(e)}")
    
    return item


def keyword_extraction_middleware(item: Dict) -> Dict:
    """
    关键词提取中间件，提取内容关键词
    
    Args:
        item: 数据项
        
    Returns:
        Dict: 添加关键词后的数据项
    """
    # 如果已有关键词，跳过
    if 'keywords' in item and item['keywords']:
        return item
    
    # 检查是否有内容
    if 'content' not in item or not item['content']:
        return item
    
    try:
        # 导入关键词提取函数
        from backend.app.utils.text_cleaner import extract_keywords
        
        # 提取关键词
        content = item['content']
        keywords = extract_keywords(content)
        
        # 添加关键词
        item['keywords'] = keywords
        
        logger.debug(f"提取关键词: {item.get('title', '')}, 关键词: {keywords}")
        
    except ImportError:
        logger.warning("关键词提取模块不可用")
    except Exception as e:
        logger.error(f"关键词提取失败: {str(e)}")
    
    return item


def summary_middleware(item: Dict) -> Dict:
    """
    摘要生成中间件，生成内容摘要
    
    Args:
        item: 数据项
        
    Returns:
        Dict: 添加摘要后的数据项
    """
    # 如果已有摘要，跳过
    if 'summary' in item and item['summary']:
        return item
    
    # 检查是否有内容
    if 'content' not in item or not item['content']:
        return item
    
    try:
        # 尝试导入摘要生成器
        from backend.app.utils.summarizer import Summarizer
        
        # 创建摘要生成器
        summarizer = Summarizer()
        
        # 生成摘要
        content = item['content']
        summary = summarizer.summarize(content)
        
        # 添加摘要
        item['summary'] = summary
        
        logger.debug(f"生成摘要: {item.get('title', '')}")
        
    except ImportError:
        # 如果摘要生成器不可用，使用简单方法生成摘要
        content = item['content']
        
        # 简单摘要：取内容的前200个字符
        simple_summary = content[:200].strip()
        if len(content) > 200:
            simple_summary += '...'
        
        item['summary'] = simple_summary
        
        logger.debug(f"生成简单摘要: {item.get('title', '')}")
    except Exception as e:
        logger.error(f"生成摘要失败: {str(e)}")
    
    return item


def create_middleware_manager() -> MiddlewareManager:
    """
    创建中间件管理器并添加常用中间件
    
    Returns:
        MiddlewareManager: 初始化好的中间件管理器
    """
    manager = MiddlewareManager()
    
    # 添加请求中间件
    manager.add_request_middleware(ua_rotation_middleware)
    manager.add_request_middleware(referer_middleware)
    manager.add_request_middleware(rate_limiting_middleware)
    manager.add_request_middleware(request_logging_middleware)
    
    # 添加响应中间件
    manager.add_response_middleware(response_logging_middleware)
    manager.add_response_middleware(error_retry_middleware)
    manager.add_response_middleware(content_type_middleware)
    
    # 添加数据项中间件
    manager.add_item_middleware(ads_filter_middleware)
    manager.add_item_middleware(duplicate_filter_middleware)
    manager.add_item_middleware(sentiment_analysis_middleware)
    manager.add_item_middleware(keyword_extraction_middleware)
    manager.add_item_middleware(summary_middleware)
    
    return manager 