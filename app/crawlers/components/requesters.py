#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 请求器组件
负责处理HTTP请求，支持同步和异步模式
"""

import time
import random
import logging
import requests
import aiohttp
import asyncio
from typing import Dict, Optional, Any, Union, List, Tuple
from abc import ABC, abstractmethod
from fake_useragent import UserAgent

from app.utils.logger import get_crawler_logger

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('requesters')

class BaseRequester(ABC):
    """请求器基类，定义请求器的接口"""
    
    @abstractmethod
    def fetch(self, url: str, params: Optional[Dict] = None, 
              headers: Optional[Dict] = None, timeout: Optional[int] = None, 
              max_retries: int = 3) -> Optional[str]:
        """获取页面内容"""
        pass
    
    @abstractmethod
    def fetch_json(self, url: str, params: Optional[Dict] = None, 
                  headers: Optional[Dict] = None, timeout: Optional[int] = None,
                  max_retries: int = 3) -> Optional[Dict]:
        """获取JSON内容"""
        pass
    
    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """获取HTTP请求头"""
        pass
    
    @abstractmethod
    def set_proxy(self, proxy_url: str) -> None:
        """设置代理"""
        pass


class SyncRequester(BaseRequester):
    """同步请求器，使用requests库处理HTTP请求"""
    
    def __init__(self, use_proxy: bool = False, proxy_url: Optional[str] = None, 
                 timeout: int = 30, random_delay: bool = True):
        """
        初始化同步请求器
        
        Args:
            use_proxy: 是否使用代理
            proxy_url: 代理URL
            timeout: 默认超时时间（秒）
            random_delay: 是否随机延迟请求
        """
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self.timeout = timeout
        self.random_delay = random_delay
        self.proxies = self._set_proxies(proxy_url) if use_proxy and proxy_url else None
        
        # 尝试初始化UserAgent
        try:
            self.ua = UserAgent()
        except Exception as e:
            logger.warning(f"初始化UserAgent失败: {str(e)}，将使用默认User-Agent")
            self.ua = None
            
        # 请求统计
        self.request_stats = {
            "total": 0,
            "success": 0,
            "failure": 0,
            "avg_response_time": 0,
            "total_response_time": 0
        }
    
    def fetch(self, url: str, params: Optional[Dict] = None, 
              headers: Optional[Dict] = None, timeout: Optional[int] = None, 
              max_retries: int = 3) -> Optional[str]:
        """
        获取页面内容
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 自定义请求头
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            
        Returns:
            str: 页面内容或None
        """
        if not url:
            return None
            
        # 设置超时
        if timeout is None:
            timeout = self.timeout
            
        # 合并请求头
        merged_headers = self.get_headers()
        if headers:
            merged_headers.update(headers)
            
        # 添加随机延迟
        if self.random_delay:
            self._random_sleep()
            
        # 更新请求统计
        self.request_stats["total"] += 1
        start_time = time.time()
        
        # 尝试请求
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=merged_headers,
                    proxies=self.proxies,
                    timeout=timeout
                )
                
                # 检查响应状态
                if response.status_code != 200:
                    logger.warning(f"请求失败: {url}, 状态码: {response.status_code}, 重试 {attempt+1}/{max_retries}")
                    if attempt < max_retries - 1:
                        time.sleep(2 * (attempt + 1))  # 指数退避
                        continue
                    self.request_stats["failure"] += 1
                    return None
                
                # 更新统计信息
                end_time = time.time()
                request_time = end_time - start_time
                self.request_stats["success"] += 1
                self.request_stats["total_response_time"] += request_time
                self.request_stats["avg_response_time"] = (
                    self.request_stats["total_response_time"] / self.request_stats["success"]
                )
                
                # 尝试检测并修正编码
                content = self._handle_encoding(response)
                return content
                
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常: {url}, 错误: {str(e)}, 重试 {attempt+1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))  # 指数退避
                    continue
                self.request_stats["failure"] += 1
                return None
        
        return None
    
    def fetch_json(self, url: str, params: Optional[Dict] = None, 
                  headers: Optional[Dict] = None, timeout: Optional[int] = None,
                  max_retries: int = 3) -> Optional[Dict]:
        """
        获取JSON内容
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 自定义请求头
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            
        Returns:
            Dict: JSON响应或None
        """
        # 设置默认的JSON请求头
        json_headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
        }
        
        # 合并请求头
        if headers:
            json_headers.update(headers)
            
        # 发起请求
        content = self.fetch(url, params, json_headers, timeout, max_retries)
        if not content:
            return None
            
        # 尝试解析JSON
        try:
            return requests.utils.json_loads(content)
        except ValueError as e:
            logger.error(f"JSON解析失败: {url}, 错误: {str(e)}")
            return None
    
    def get_headers(self) -> Dict[str, str]:
        """获取随机的HTTP请求头"""
        user_agent = self._get_random_user_agent()
        return {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
    
    def set_proxy(self, proxy_url: str) -> None:
        """
        设置代理
        
        Args:
            proxy_url: 代理URL (例如: http://user:pass@10.10.1.10:3128/)
        """
        self.proxy_url = proxy_url
        self.proxies = self._set_proxies(proxy_url)
        self.use_proxy = bool(self.proxies)
        
        if self.use_proxy:
            logger.info(f"代理已设置: {proxy_url}")
        else:
            logger.warning("代理设置失败")
    
    def _set_proxies(self, proxy_url: str) -> Dict[str, str]:
        """
        根据代理URL设置proxies字典
        
        Args:
            proxy_url: 代理URL
            
        Returns:
            Dict: 代理配置字典
        """
        if not proxy_url:
            return {}
            
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def _random_sleep(self, min_seconds: float = 0.5, max_seconds: float = 2.0) -> None:
        """
        随机休眠，避免频繁请求
        
        Args:
            min_seconds: 最小休眠时间（秒）
            max_seconds: 最大休眠时间（秒）
        """
        sleep_time = random.uniform(min_seconds, max_seconds)
        time.sleep(sleep_time)
    
    def _get_random_user_agent(self) -> str:
        """
        获取随机User-Agent
        
        Returns:
            str: User-Agent字符串
        """
        # 如果有fake_useragent，使用它
        if self.ua:
            try:
                return self.ua.random
            except Exception:
                pass
        
        # 否则使用预定义的User-Agent列表
        user_agents = [
            # Chrome最新版本UA
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Edge最新版本UA
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            # Firefox最新版本UA
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
            # Safari最新版本UA
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        ]
        return random.choice(user_agents)
    
    def _handle_encoding(self, response: requests.Response) -> str:
        """
        处理响应编码
        
        Args:
            response: requests响应对象
            
        Returns:
            str: 解码后的响应内容
        """
        # 尝试从响应头获取编码
        content_type = response.headers.get('Content-Type', '')
        if 'charset=' in content_type:
            encoding = content_type.split('charset=')[-1].split(';')[0].strip()
            try:
                return response.content.decode(encoding, errors='replace')
            except (LookupError, UnicodeDecodeError):
                pass
        
        # 尝试使用response.encoding
        if response.encoding:
            try:
                return response.content.decode(response.encoding, errors='replace')
            except (LookupError, UnicodeDecodeError):
                pass
        
        # 尝试使用apparent_encoding
        if response.apparent_encoding:
            try:
                return response.content.decode(response.apparent_encoding, errors='replace')
            except (LookupError, UnicodeDecodeError):
                pass
        
        # 常见的中文编码
        for encoding in ['utf-8', 'gb2312', 'gbk', 'gb18030']:
            try:
                return response.content.decode(encoding, errors='replace')
            except (LookupError, UnicodeDecodeError):
                continue
        
        # 最后尝试使用默认编码，并忽略错误
        return response.text


class AsyncRequester(BaseRequester):
    """异步请求器，使用aiohttp库处理HTTP请求"""
    
    def __init__(self, use_proxy: bool = False, proxy_url: Optional[str] = None, 
                 timeout: int = 30, max_concurrency: int = 5, random_delay: bool = True):
        """
        初始化异步请求器
        
        Args:
            use_proxy: 是否使用代理
            proxy_url: 代理URL
            timeout: 默认超时时间（秒）
            max_concurrency: 最大并发请求数
            random_delay: 是否随机延迟请求
        """
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self.timeout = timeout
        self.max_concurrency = max_concurrency
        self.random_delay = random_delay
        self.session = None
        self.semaphore = None
        
        # 尝试初始化UserAgent
        try:
            self.ua = UserAgent()
        except Exception as e:
            logger.warning(f"初始化UserAgent失败: {str(e)}，将使用默认User-Agent")
            self.ua = None
            
        # 请求统计
        self.request_stats = {
            "total": 0,
            "success": 0,
            "failure": 0,
            "avg_response_time": 0,
            "total_response_time": 0
        }
    
    def fetch(self, url: str, params: Optional[Dict] = None, 
              headers: Optional[Dict] = None, timeout: Optional[int] = None, 
              max_retries: int = 3) -> Optional[str]:
        """
        同步获取页面内容（该方法是为了兼容性而提供的）
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 自定义请求头
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            
        Returns:
            str: 页面内容或None
        """
        # 创建一个事件循环并运行异步fetch
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.async_fetch(url, params, headers, timeout, max_retries)
            )
        finally:
            loop.close()
    
    def fetch_json(self, url: str, params: Optional[Dict] = None, 
                  headers: Optional[Dict] = None, timeout: Optional[int] = None,
                  max_retries: int = 3) -> Optional[Dict]:
        """
        同步获取JSON内容（该方法是为了兼容性而提供的）
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 自定义请求头
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            
        Returns:
            Dict: JSON响应或None
        """
        # 创建一个事件循环并运行异步fetch_json
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.async_fetch_json(url, params, headers, timeout, max_retries)
            )
        finally:
            loop.close()
    
    async def async_fetch(self, url: str, params: Optional[Dict] = None, 
                         headers: Optional[Dict] = None, timeout: Optional[int] = None,
                         max_retries: int = 3) -> Optional[str]:
        """
        异步获取页面内容
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 自定义请求头
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            
        Returns:
            str: 页面内容或None
        """
        if not url:
            return None
            
        # 初始化会话
        await self._init_session()
        
        # 设置超时
        if timeout is None:
            timeout = self.timeout
            
        # 合并请求头
        merged_headers = self.get_headers()
        if headers:
            merged_headers.update(headers)
            
        # 限制并发
        async with self.semaphore:
            # 添加随机延迟
            if self.random_delay:
                await self._async_random_sleep()
                
            # 更新请求统计
            self.request_stats["total"] += 1
            start_time = time.time()
            
            # 尝试请求
            for attempt in range(max_retries):
                try:
                    # 设置代理
                    proxy = self.proxy_url if self.use_proxy else None
                    
                    async with self.session.get(
                        url,
                        params=params,
                        headers=merged_headers,
                        proxy=proxy,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        # 检查响应状态
                        if response.status != 200:
                            logger.warning(f"请求失败: {url}, 状态码: {response.status}, 重试 {attempt+1}/{max_retries}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2 * (attempt + 1))  # 指数退避
                                continue
                            self.request_stats["failure"] += 1
                            return None
                        
                        # 更新统计信息
                        end_time = time.time()
                        request_time = end_time - start_time
                        self.request_stats["success"] += 1
                        self.request_stats["total_response_time"] += request_time
                        self.request_stats["avg_response_time"] = (
                            self.request_stats["total_response_time"] / self.request_stats["success"]
                        )
                        
                        # 获取响应内容
                        content = await response.text(errors='replace')
                        return content
                        
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.error(f"请求异常: {url}, 错误: {str(e)}, 重试 {attempt+1}/{max_retries}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 * (attempt + 1))  # 指数退避
                        continue
                    self.request_stats["failure"] += 1
                    return None
            
            return None
    
    async def async_fetch_json(self, url: str, params: Optional[Dict] = None, 
                              headers: Optional[Dict] = None, timeout: Optional[int] = None,
                              max_retries: int = 3) -> Optional[Dict]:
        """
        异步获取JSON内容
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 自定义请求头
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            
        Returns:
            Dict: JSON响应或None
        """
        # 设置默认的JSON请求头
        json_headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
        }
        
        # 合并请求头
        if headers:
            json_headers.update(headers)
            
        # 发起请求
        content = await self.async_fetch(url, params, json_headers, timeout, max_retries)
        if not content:
            return None
            
        # 尝试解析JSON
        try:
            import json
            return json.loads(content)
        except ValueError as e:
            logger.error(f"JSON解析失败: {url}, 错误: {str(e)}")
            return None
    
    def get_headers(self) -> Dict[str, str]:
        """获取随机的HTTP请求头"""
        user_agent = self._get_random_user_agent()
        return {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
    
    def set_proxy(self, proxy_url: str) -> None:
        """
        设置代理
        
        Args:
            proxy_url: 代理URL (例如: http://user:pass@10.10.1.10:3128/)
        """
        self.proxy_url = proxy_url
        self.use_proxy = bool(proxy_url)
        
        # 重置会话，让新的代理设置生效
        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())
            self.session = None
        
        if self.use_proxy:
            logger.info(f"代理已设置: {proxy_url}")
        else:
            logger.warning("代理已清除")
    
    async def _init_session(self) -> None:
        """初始化异步会话"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(headers=self.get_headers(), timeout=timeout)
        
        if self.semaphore is None:
            self.semaphore = asyncio.Semaphore(self.max_concurrency)
    
    async def close(self) -> None:
        """关闭异步会话"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            logger.debug("异步会话已关闭")
    
    def __del__(self) -> None:
        """析构函数，确保会话被关闭"""
        if self.session and not self.session.closed:
            # 创建一个事件循环来关闭会话
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
            except RuntimeError:
                # 如果没有运行中的事件循环
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.close())
                    loop.close()
                except Exception as e:
                    logger.error(f"关闭异步会话时出错: {str(e)}")
    
    async def _async_random_sleep(self, min_seconds: float = 0.5, max_seconds: float = 2.0) -> None:
        """
        异步随机休眠，避免频繁请求
        
        Args:
            min_seconds: 最小休眠时间（秒）
            max_seconds: 最大休眠时间（秒）
        """
        sleep_time = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(sleep_time)
    
    def _get_random_user_agent(self) -> str:
        """
        获取随机User-Agent
        
        Returns:
            str: User-Agent字符串
        """
        # 如果有fake_useragent，使用它
        if self.ua:
            try:
                return self.ua.random
            except Exception:
                pass
        
        # 否则使用预定义的User-Agent列表
        user_agents = [
            # Chrome最新版本UA
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Edge最新版本UA
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            # Firefox最新版本UA
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
            # Safari最新版本UA
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        ]
        return random.choice(user_agents)


def create_requester(async_mode: bool = False, **kwargs) -> BaseRequester:
    """
    创建请求器工厂函数
    
    Args:
        async_mode: 是否创建异步请求器
        **kwargs: 其他参数
        
    Returns:
        BaseRequester: 请求器实例
    """
    if async_mode:
        return AsyncRequester(**kwargs)
    else:
        return SyncRequester(**kwargs) 