#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - HTTP客户端模块
提供同步和异步两种HTTP请求实现
"""

import time
import random
from typing import Dict, Optional, Any, List, Tuple, Union
from urllib.parse import urlparse, urljoin
import asyncio
from datetime import datetime
import re

import requests
import aiohttp
from fake_useragent import UserAgent
import chardet  # 添加chardet库导入用于编码检测

from backend.app.utils.logger import get_logger

# 初始化日志记录器
logger = get_logger('http_client')

class RequestStats:
    """请求统计类，用于记录请求情况"""
    
    def __init__(self):
        """初始化统计"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.request_times = []  # 请求耗时
        self.status_codes = {}  # 状态码统计
        self.errors = {}  # 错误统计
    
    def add_request(self, url: str, status_code: int, content_length: int):
        """
        添加请求记录
        
        Args:
            url: 请求URL
            status_code: 响应状态码
            content_length: 响应内容长度
        """
        self.total_requests += 1
        
        # 记录状态码
        if status_code not in self.status_codes:
            self.status_codes[status_code] = 0
        self.status_codes[status_code] += 1
        
        # 记录成功/失败
        if 200 <= status_code < 300:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
    
    def add_error(self, url: str, error_message: str):
        """
        添加错误记录
        
        Args:
            url: 请求URL
            error_message: 错误信息
        """
        self.total_requests += 1
        self.failed_requests += 1
        
        # 记录错误
        if error_message not in self.errors:
            self.errors[error_message] = 0
        self.errors[error_message] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            'status_codes': self.status_codes,
            'errors': self.errors
        }
    
    def reset(self):
        """重置统计"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.request_times = []
        self.status_codes = {}
        self.errors = {}

class BaseHttpClient:
    """HTTP客户端基类，定义公共方法和属性"""
    
    def __init__(self, use_proxy: bool = False, timeout: int = 30, max_retries: int = 3, 
                 retry_delay: int = 2, user_agent_type: str = 'random'):
        """
        初始化HTTP客户端
        
        Args:
            use_proxy: 是否使用代理
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟时间（秒）
            user_agent_type: User-Agent类型，可选值：random, chrome, firefox, safari等
        """
        self.use_proxy = use_proxy
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 初始化User-Agent生成器
        try:
            self.ua = UserAgent()
            self.user_agent_type = user_agent_type
        except Exception as e:
            logger.warning(f"初始化User-Agent失败: {str(e)}，将使用固定的User-Agent")
            self.ua = None
            self.user_agent_type = 'fallback'
        
        # 初始化统计信息
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retried_requests': 0,
            'total_time': 0,
            'domains': {}
        }
    
    def _get_user_agent(self) -> str:
        """
        获取User-Agent
        
        Returns:
            str: User-Agent字符串
        """
        if self.ua is None:
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
        try:
            if self.user_agent_type == 'random':
                return self.ua.random
            elif hasattr(self.ua, self.user_agent_type):
                return getattr(self.ua, self.user_agent_type)
            else:
                return self.ua.random
        except Exception:
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    def _get_proxy(self) -> Optional[Dict[str, str]]:
        """
        获取代理配置
        
        Returns:
            Dict[str, str] 或 None: 代理配置字典或None
        """
        if not self.use_proxy:
            return None
            
        # 代理配置示例，实际使用时应替换为真实的代理服务
        # TODO: 实现动态代理池或代理轮换机制
        proxies = {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890'
        }
        return proxies
    
    def _update_stats(self, url: str, success: bool, elapsed_time: float, retried: bool = False):
        """
        更新请求统计信息
        
        Args:
            url: 请求URL
            success: 请求是否成功
            elapsed_time: 请求耗时（秒）
            retried: 是否进行了重试
        """
        # 更新总体统计
        self.stats['total_requests'] += 1
        self.stats['total_time'] += elapsed_time
        
        if success:
            self.stats['successful_requests'] += 1
        else:
            self.stats['failed_requests'] += 1
            
        if retried:
            self.stats['retried_requests'] += 1
        
        # 更新域名统计
        domain = urlparse(url).netloc
        if domain not in self.stats['domains']:
            self.stats['domains'][domain] = {
                'requests': 0,
                'successful': 0,
                'failed': 0,
                'total_time': 0,
                'avg_time': 0
            }
            
        domain_stats = self.stats['domains'][domain]
        domain_stats['requests'] += 1
        domain_stats['total_time'] += elapsed_time
        domain_stats['avg_time'] = domain_stats['total_time'] / domain_stats['requests']
        
        if success:
            domain_stats['successful'] += 1
        else:
            domain_stats['failed'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        # 计算平均响应时间
        avg_time = 0
        if self.stats['total_requests'] > 0:
            avg_time = self.stats['total_time'] / self.stats['total_requests']
            
        # 复制统计信息并添加额外计算字段
        stats = self.stats.copy()
        stats['avg_response_time'] = avg_time
        stats['success_rate'] = (stats['successful_requests'] / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
        stats['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retried_requests': 0,
            'total_time': 0,
            'domains': {}
        }
    
    def detect_encoding(self, content: bytes) -> Optional[str]:
        """
        检测内容编码
        
        Args:
            content: 二进制内容
            
        Returns:
            Optional[str]: 检测到的编码，如果无法检测则返回None
        """
        try:
            # 先尝试从BOM检测编码
            if content.startswith(b'\xef\xbb\xbf'):
                return 'utf-8-sig'
            elif content.startswith(b'\xff\xfe') or content.startswith(b'\xfe\xff'):
                return 'utf-16'
            
            # 使用chardet检测编码
            try:
                import chardet
                result = chardet.detect(content)
                if result and result['confidence'] > 0.7:
                    return result['encoding']
            except ImportError:
                logger.warning("chardet模块未安装，无法精确检测编码")
            
            # 尝试常见中文编码
            for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                try:
                    content.decode(encoding)
                    return encoding
                except UnicodeDecodeError:
                    continue
            
            return None
        except Exception as e:
            logger.error(f"检测编码时发生错误: {str(e)}")
            return None


class SyncHttpClient(BaseHttpClient):
    """同步HTTP客户端实现"""
    
    def __init__(self, **kwargs):
        """
        初始化同步HTTP客户端
        
        Args:
            **kwargs: 传递给基类的参数
        """
        super().__init__(**kwargs)
        
        # 创建会话对象
        self.session = requests.Session()
        
        # 指标统计
        self.stats = RequestStats()
        
    def get_headers(self):
        """
        获取请求头
        
        Returns:
            Dict: 请求头字典
        """
        headers = {
            'User-Agent': self._get_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        }
        return headers
    
    def fetch(self, url: str, method: str = 'GET', params: Dict = None, 
               data: Dict = None, headers: Dict = None, cookies: Dict = None, 
               allow_redirects: bool = True, **kwargs) -> str:
        """
        发送HTTP请求并获取响应内容
        
        Args:
            url: 请求URL
            method: 请求方法，如GET、POST等
            params: URL参数
            data: 请求体数据
            headers: 请求头
            cookies: Cookie
            allow_redirects: 是否允许重定向
            **kwargs: 其他requests参数
            
        Returns:
            str: 响应内容
            
        Raises:
            Exception: 请求失败
        """
        # 准备请求头
        if headers is None:
            headers = {}
        if 'User-Agent' not in headers:
            headers['User-Agent'] = self._get_user_agent()
        
        # 针对不同网站添加特定请求头以绕过反爬机制
        if 'sina.com.cn' in url:
            # 新浪财经特定的请求头
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://finance.sina.com.cn/',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            })
        elif 'eastmoney.com' in url:
            # 东方财富特定的请求头
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://www.eastmoney.com/',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-site',
                'Upgrade-Insecure-Requests': '1'
            })
        elif 'fund.eastmoney.com' in url:
            # 东方财富基金特定的请求头
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://fund.eastmoney.com/',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-site',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache'
            })
        elif 'ifeng.com' in url:
            # 凤凰财经特定的请求头
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://finance.ifeng.com/',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            })
        elif '163.com' in url:
            # 网易财经特定的请求头
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://money.163.com/',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            })
        
        # 获取代理
        proxies = None
        if self.use_proxy:
            proxies = self._get_proxy()
        
        # 初始化统计变量
        start_time = time.time()
        retried = False
        success = False
        content = ""
        
        # 重试逻辑
        for attempt in range(self.max_retries):
            try:
                # 添加防止被识别为爬虫的措施：随机延迟
                if attempt > 0:
                    delay = self.retry_delay + random.uniform(0, 2)
                    time.sleep(delay)
                    retried = True
                    # 重试时，更换 User-Agent
                    headers['User-Agent'] = self._get_user_agent()
                    # 添加随机参数到URL，避免缓存
                    url_with_random = url
                    if '?' in url:
                        url_with_random = f"{url}&_r={random.random()}"
                    else:
                        url_with_random = f"{url}?_r={random.random()}"
                    url = url_with_random
                
                # 发送请求
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    headers=headers,
                    cookies=cookies,
                    proxies=proxies,
                    timeout=self.timeout,
                    allow_redirects=allow_redirects,
                    **kwargs
                )
                
                # 检查响应状态
                if response.status_code == 200:
                    # 尝试处理不同的编码情况
                    try:
                        # 1. 首先尝试使用响应头中的编码
                        content = response.text
                        success = True
                        break
                    except UnicodeDecodeError:
                        # 2. 如果失败，使用chardet检测编码
                        detected = chardet.detect(response.content)
                        encoding = detected['encoding']
                        logger.info(f"使用检测到的编码 {encoding} 解析内容")
                        try:
                            content = response.content.decode(encoding)
                            success = True
                            break
                        except (UnicodeDecodeError, TypeError):
                            # 3. 如果还是失败，尝试常用的中文编码
                            for enc in ['utf-8', 'gbk', 'gb18030', 'gb2312', 'big5']:
                                try:
                                    content = response.content.decode(enc)
                                    logger.info(f"使用 {enc} 编码成功解析内容")
                                    success = True
                                    break
                                except UnicodeDecodeError:
                                    continue
                            # 如果所有尝试都失败，使用ignore参数忽略错误字符
                            if not success:
                                content = response.content.decode('utf-8', errors='ignore')
                                logger.warning(f"使用UTF-8(ignore)编码解析内容，可能存在字符丢失")
                                success = True
                                break
                elif response.status_code == 403:
                    # 403 Forbidden，可能是被反爬机制拦截
                    logger.warning(f"请求被拒绝 (403)，正在切换请求策略: {url}")
                    # 添加更多欺骗性的请求头
                    headers.update({
                        'User-Agent': self._get_user_agent(),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                        'Referer': urlparse(url).scheme + '://' + urlparse(url).netloc
                    })
                    # 使用较长的延迟
                    time.sleep(self.retry_delay * 2 + random.uniform(1, 3))
                elif response.status_code == 404:
                    logger.warning(f"页面不存在 (404): {url}")
                    return None  # 对于404错误，直接返回None，不再重试
                elif response.status_code == 429:
                    # Too Many Requests
                    logger.warning(f"请求频率过高 (429)，延长等待时间: {url}")
                    time.sleep(self.retry_delay * 3 + random.uniform(2, 5))
                elif response.status_code >= 500:
                    # 服务器错误，可能是临时的
                    logger.warning(f"服务器错误 ({response.status_code}): {url}")
                    time.sleep(self.retry_delay + random.uniform(1, 3))
                elif 300 <= response.status_code < 400 and response.headers.get('location'):
                    # 处理重定向
                    redirect_url = response.headers['location']
                    logger.info(f"URL重定向: {url} -> {redirect_url}")
                    # 更新URL并再次尝试请求
                    url = redirect_url if redirect_url.startswith('http') else urljoin(url, redirect_url)
                else:
                    # 其他错误
                    logger.warning(f"HTTP错误: {response.status_code}, URL: {url}")
                    time.sleep(self.retry_delay)
            except requests.RequestException as e:
                # 捕获网络相关异常
                logger.warning(f"请求异常 (尝试 {attempt+1}/{self.max_retries}): {url}, 错误: {str(e)}")
                if attempt == self.max_retries - 1:
                    # 最后一次尝试失败
                    logger.error(f"请求失败: {url}, 错误: {str(e)}")
                    break
                time.sleep(self.retry_delay)
        
        # 更新统计信息
        elapsed_time = time.time() - start_time
        self._update_stats(url, success, elapsed_time, retried)
        
        return content
    
    def close(self):
        """关闭会话"""
        self.session.close()

    def fetch_sync(self, url: str, **kwargs) -> Optional[str]:
        """
        同步获取页面内容
        
        Args:
            url: 页面URL
            **kwargs: 请求参数
            
        Returns:
            Optional[str]: 页面内容，失败则返回None
        """
        try:
            logger.debug(f"同步获取页面: {url}")
            # 设置超时
            timeout = kwargs.pop('timeout', self.timeout)
            
            # 准备请求头
            headers = self.get_headers()
            if 'headers' in kwargs:
                headers.update(kwargs.pop('headers'))
            
            # 发送请求
            response = requests.get(
                url, 
                headers=headers,
                timeout=timeout,
                proxies=self.get_proxy() if self.use_proxy else None,
                **kwargs
            )
            
            # 处理响应
            if response.status_code == 200:
                # 检测并处理编码
                if response.encoding == 'ISO-8859-1':
                    # 尝试从响应头或内容中检测编码
                    detected_encoding = self.detect_encoding(response.content)
                    if detected_encoding:
                        response.encoding = detected_encoding
                    else:
                        # 默认使用UTF-8
                        response.encoding = 'utf-8'
                
                # 记录请求信息
                self.stats.add_request(url, response.status_code, len(response.content))
                
                return response.text
            else:
                logger.warning(f"请求失败: {url}, 状态码: {response.status_code}")
                self.stats.add_request(url, response.status_code, 0)
                return None
                
        except Exception as e:
            logger.error(f"请求异常: {url}, 错误: {str(e)}")
            self.stats.add_error(url, str(e))
            return None


class AsyncHttpClient(BaseHttpClient):
    """异步HTTP客户端，使用aiohttp库"""
    
    def __init__(self, use_proxy=False, timeout=30, **kwargs):
        """
        初始化异步HTTP客户端
        
        Args:
            use_proxy: 是否使用代理
            timeout: 超时时间（秒）
            **kwargs: 其他初始化参数
        """
        super().__init__(use_proxy, timeout, **kwargs)
        
        # aiohttp会话
        self.session = None
        self.initialized = False
        
        # 用于同步操作的requests会话
        self.sync_session = requests.Session()
        
        # 指标统计
        self.stats = RequestStats()
        
        # 初始化连接器和会话属性
        self._session = None
        self._connector = None
        
    def get_headers(self):
        """
        获取请求头
        
        Returns:
            Dict: 请求头字典
        """
        headers = {
            'User-Agent': self._get_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        }
        return headers
    
    async def _get_session(self):
        """
        获取异步会话，如果不存在则创建
        
        Returns:
            aiohttp.ClientSession: 异步会话
        """
        if self._session is None or self._session.closed:
            # 使用TCP连接器，设置连接限制
            if self._connector is None or self._connector.closed:
                self._connector = aiohttp.TCPConnector(limit=100, ssl=False)
            # 创建会话
            self._session = aiohttp.ClientSession(connector=self._connector)
        return self._session
    
    async def fetch(self, url: str, method: str = 'GET', params: Dict = None, 
                   data: Dict = None, headers: Dict = None, cookies: Dict = None, 
                   allow_redirects: bool = True, **kwargs) -> str:
        """
        异步发送HTTP请求并获取响应内容
        
        Args:
            url: 请求URL
            method: 请求方法，如GET、POST等
            params: URL参数
            data: 请求体数据
            headers: 请求头
            cookies: Cookie
            allow_redirects: 是否允许重定向
            **kwargs: 其他aiohttp参数
            
        Returns:
            str: 响应内容
            
        Raises:
            Exception: 请求失败
        """
        # 准备请求头
        if headers is None:
            headers = {}
        if 'User-Agent' not in headers:
            headers['User-Agent'] = self._get_user_agent()
        
        # 针对不同网站添加特定请求头以绕过反爬机制
        if 'sina.com.cn' in url:
            # 新浪财经特定的请求头
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://finance.sina.com.cn/',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            })
        elif 'eastmoney.com' in url:
            # 东方财富特定的请求头
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://www.eastmoney.com/',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-site',
                'Upgrade-Insecure-Requests': '1'
            })
        elif 'fund.eastmoney.com' in url:
            # 东方财富基金特定的请求头
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://fund.eastmoney.com/',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-site',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache'
            })
        elif 'ifeng.com' in url:
            # 凤凰财经特定的请求头
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://finance.ifeng.com/',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            })
        elif '163.com' in url:
            # 网易财经特定的请求头
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://money.163.com/',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            })
        
        # 获取代理
        proxy = None
        if self.use_proxy:
            proxies = self._get_proxy()
            if proxies and proxies.get('http'):
                proxy = proxies['http']
        
        # 获取会话
        session = await self._get_session()
        
        # 初始化统计变量
        start_time = time.time()
        retried = False
        success = False
        content = ""
        
        # 重试逻辑
        for attempt in range(self.max_retries):
            try:
                # 添加防止被识别为爬虫的措施：随机延迟
                if attempt > 0:
                    delay = self.retry_delay + random.uniform(0, 2)
                    await asyncio.sleep(delay)
                    retried = True
                    # 重试时，更换 User-Agent
                    headers['User-Agent'] = self._get_user_agent()
                    # 添加随机参数到URL，避免缓存
                    url_with_random = url
                    if '?' in url:
                        url_with_random = f"{url}&_r={random.random()}"
                    else:
                        url_with_random = f"{url}?_r={random.random()}"
                    url = url_with_random
                
                # 设置超时
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                # 发送请求
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    headers=headers,
                    cookies=cookies,
                    proxy=proxy,
                    timeout=timeout,
                    allow_redirects=allow_redirects,
                    **kwargs
                ) as response:
                    # 检查响应状态
                    if response.status == 200:
                        # 尝试处理不同的编码情况
                        try:
                            # 获取并确认响应编码
                            content_type = response.headers.get('Content-Type', '')
                            # 首先尝试使用响应的文本方法
                            content = await response.text()
                            success = True
                            break
                        except UnicodeDecodeError:
                            # 如果解码失败，读取字节内容并进行编码检测
                            content_bytes = await response.read()
                            detected = chardet.detect(content_bytes)
                            encoding = detected['encoding']
                            logger.info(f"使用检测到的编码 {encoding} 解析异步响应内容")
                            
                            try:
                                content = content_bytes.decode(encoding)
                                success = True
                                break
                            except (UnicodeDecodeError, TypeError):
                                # 尝试常用的中文编码
                                for enc in ['utf-8', 'gbk', 'gb18030', 'gb2312', 'big5']:
                                    try:
                                        content = content_bytes.decode(enc)
                                        logger.info(f"使用 {enc} 编码成功解析异步响应内容")
                                        success = True
                                        break
                                    except UnicodeDecodeError:
                                        continue
                                
                                # 如果所有尝试都失败，使用ignore参数
                                if not success:
                                    content = content_bytes.decode('utf-8', errors='ignore')
                                    logger.warning(f"使用UTF-8(ignore)编码解析异步响应内容，可能存在字符丢失")
                                    success = True
                                    break
                    elif response.status == 403:
                        # 403 Forbidden，可能是被反爬机制拦截
                        logger.warning(f"请求被拒绝 (403)，正在切换请求策略: {url}")
                        # 添加更多欺骗性的请求头
                        headers.update({
                            'User-Agent': self._get_user_agent(),
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                            'Cache-Control': 'no-cache',
                            'Pragma': 'no-cache',
                            'Referer': urlparse(url).scheme + '://' + urlparse(url).netloc
                        })
                        # 使用较长的延迟
                        await asyncio.sleep(self.retry_delay * 2 + random.uniform(1, 3))
                    elif response.status == 404:
                        logger.warning(f"页面不存在 (404): {url}")
                        return None  # 对于404错误，直接返回None，不再重试
                    elif response.status == 429:
                        # Too Many Requests
                        logger.warning(f"请求频率过高 (429)，延长等待时间: {url}")
                        await asyncio.sleep(self.retry_delay * 3 + random.uniform(2, 5))
                    elif response.status >= 500:
                        # 服务器错误，可能是临时的
                        logger.warning(f"服务器错误 ({response.status}): {url}")
                        await asyncio.sleep(self.retry_delay + random.uniform(1, 3))
                    elif 300 <= response.status < 400 and response.headers.get('location'):
                        # 处理重定向
                        redirect_url = response.headers['location']
                        logger.info(f"URL重定向: {url} -> {redirect_url}")
                        # 更新URL并再次尝试请求
                        url = redirect_url if redirect_url.startswith('http') else urljoin(url, redirect_url)
                    else:
                        # 其他错误
                        logger.warning(f"HTTP错误: {response.status}, URL: {url}")
                        await asyncio.sleep(self.retry_delay)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                # 捕获网络相关异常
                logger.warning(f"请求异常 (尝试 {attempt+1}/{self.max_retries}): {url}, 错误: {str(e)}")
                if attempt == self.max_retries - 1:
                    # 最后一次尝试失败
                    logger.error(f"请求失败: {url}, 错误: {str(e)}")
                    break
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                # 其他未预期的异常
                logger.error(f"未预期的异常: {url}, 错误: {str(e)}")
                if attempt == self.max_retries - 1:
                    break
                await asyncio.sleep(self.retry_delay)
        
        # 更新统计信息
        elapsed_time = time.time() - start_time
        self._update_stats(url, success, elapsed_time, retried)
        
        if not success:
            raise Exception(f"请求失败，已重试 {self.max_retries} 次: {url}")
            
        return content
    
    async def fetch_all(self, urls: List[str], **kwargs) -> List[Tuple[str, str]]:
        """
        并发获取多个URL的内容
        
        Args:
            urls: URL列表
            **kwargs: 其他参数，传递给fetch方法
            
        Returns:
            List[Tuple[str, str]]: (url, content)元组列表
        """
        tasks = []
        for url in urls:
            tasks.append(self.fetch(url, **kwargs))
        
        # 使用gather并发执行所有请求
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        url_contents = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"并发请求 {urls[i]} 失败: {str(result)}")
                url_contents.append((urls[i], ""))
            else:
                url_contents.append((urls[i], result))
        
        return url_contents
    
    async def close(self):
        """关闭异步会话"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        
        if self._connector and not self._connector.closed:
            await self._connector.close()
            self._connector = None

    def fetch_sync(self, url: str, **kwargs) -> Optional[str]:
        """
        同步获取页面内容 (与SyncHttpClient的实现相同)
        
        Args:
            url: 页面URL
            **kwargs: 请求参数
            
        Returns:
            Optional[str]: 页面内容，失败则返回None
        """
        try:
            logger.debug(f"同步获取页面: {url}")
            # 设置超时
            timeout = kwargs.pop('timeout', self.timeout)
            
            # 准备请求头
            headers = self.get_headers()
            if 'headers' in kwargs:
                headers.update(kwargs.pop('headers'))
            
            # 使用同步会话发送请求
            response = self.sync_session.get(
                url, 
                headers=headers,
                timeout=timeout,
                proxies=self._get_proxy() if self.use_proxy else None,
                **kwargs
            )
            
            # 处理响应
            if response.status_code == 200:
                # 检测并处理编码
                if response.encoding == 'ISO-8859-1':
                    # 尝试从响应头或内容中检测编码
                    detected_encoding = self.detect_encoding(response.content)
                    if detected_encoding:
                        response.encoding = detected_encoding
                    else:
                        # 默认使用UTF-8
                        response.encoding = 'utf-8'
                
                # 记录请求信息
                self.stats.add_request(url, response.status_code, len(response.content))
                
                return response.text
            else:
                logger.warning(f"请求失败: {url}, 状态码: {response.status_code}")
                self.stats.add_request(url, response.status_code, 0)
                return None
                
        except Exception as e:
            logger.error(f"请求异常: {url}, 错误: {str(e)}")
            self.stats.add_error(url, str(e))
            return None 