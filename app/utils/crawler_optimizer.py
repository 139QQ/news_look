#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 爬虫优化工具
用于优化爬虫性能、稳定性和抗干扰能力
"""

import time
import random
import socket
import logging
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import aiohttp
from fake_useragent import UserAgent
import chardet

from app.utils.logger import get_logger

# 设置日志记录器
logger = get_logger('crawler_optimizer')

class CrawlerOptimizer:
    """爬虫优化工具类，提供各种优化爬虫性能和稳定性的方法"""
    
    def __init__(self, max_workers=5, timeout=30, enable_async=False):
        """
        初始化爬虫优化器
        
        Args:
            max_workers: 最大工作线程数
            timeout: 请求超时时间（秒）
            enable_async: 是否启用异步模式
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.enable_async = enable_async
        self.session = self._create_optimized_session()
        self.async_session = None
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 网站特定的参数
        self.site_configs = {
            "网易财经": {
                "rate_limit": 2.0,  # 每秒请求数限制
                "retry_delay": [1, 3, 5],  # 重试延迟（秒）
                "max_retries": 3,  # 最大重试次数
                "encoding": "utf-8",  # 默认编码
                "connection_timeout": 10,  # 连接超时（秒）
                "read_timeout": 30,  # 读取超时（秒）
                "success_rate_threshold": 0.8,  # 成功率阈值
                "slow_down_threshold": 0.5,  # 减速阈值
            },
            "新浪财经": {
                "rate_limit": 1.5,
                "retry_delay": [2, 4, 8],
                "max_retries": 4,
                "encoding": "gb18030",  # 新浪常用编码
                "connection_timeout": 15,
                "read_timeout": 40,
                "success_rate_threshold": 0.7,
                "slow_down_threshold": 0.4,
            },
            "凤凰财经": {
                "rate_limit": 1.8,
                "retry_delay": [1, 3, 6],
                "max_retries": 3,
                "encoding": "utf-8",
                "connection_timeout": 12,
                "read_timeout": 35,
                "success_rate_threshold": 0.75,
                "slow_down_threshold": 0.45,
            }
        }
        
        # 状态跟踪
        self.request_stats = {site: {"success": 0, "failure": 0, "last_request_time": 0} 
                             for site in self.site_configs}
        
        # 智能用户代理
        try:
            self.ua = UserAgent()
            self.user_agents = None
        except Exception as e:
            logger.warning(f"初始化UserAgent失败: {str(e)}")
            self.ua = None
            self.user_agents = self._get_fallback_user_agents()
        
        logger.info(f"爬虫优化器初始化完成，最大线程数: {max_workers}, 超时时间: {timeout}秒")
    
    def _get_fallback_user_agents(self):
        """获取备用User-Agent列表"""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.254"
        ]
    
    def _create_optimized_session(self):
        """创建优化的请求会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        # 配置适配器
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get_random_user_agent(self):
        """获取随机User-Agent"""
        if self.ua:
            try:
                return self.ua.random
            except Exception:
                pass
        
        if self.user_agents:
            return random.choice(self.user_agents)
        
        # 默认User-Agent
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    def get_site_specific_headers(self, site_name):
        """获取特定网站的请求头"""
        headers = {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
        
        # 网站特定的请求头
        if site_name == "网易财经":
            headers.update({
                "Referer": "https://money.163.com/",
                "Cache-Control": "max-age=0",
                "Accept-Encoding": "gzip, deflate, br",
            })
        elif site_name == "新浪财经":
            headers.update({
                "Referer": "https://finance.sina.com.cn/",
                "Cache-Control": "max-age=0",
                "Accept-Encoding": "gzip, deflate, br",
            })
        elif site_name == "凤凰财经":
            headers.update({
                "Referer": "https://finance.ifeng.com/",
                "Cache-Control": "max-age=0",
                "Accept-Encoding": "gzip, deflate, br",
            })
        
        return headers
    
    def fetch_with_retry(self, url, site_name, method="GET", max_retries=None, **kwargs):
        """
        使用重试机制获取页面
        
        Args:
            url: 页面URL
            site_name: 网站名称，用于获取网站特定的配置
            method: 请求方法，默认为GET
            max_retries: 最大重试次数，如果为None则使用网站配置
            **kwargs: 其他requests参数
            
        Returns:
            requests.Response对象或None
        """
        site_config = self.site_configs.get(site_name, self.site_configs["网易财经"])
        max_retries = max_retries if max_retries is not None else site_config["max_retries"]
        retry_delays = site_config["retry_delay"]
        
        headers = kwargs.pop("headers", self.get_site_specific_headers(site_name))
        timeout = kwargs.pop("timeout", (site_config["connection_timeout"], site_config["read_timeout"]))
        
        # 检查请求频率限制
        self._respect_rate_limit(site_name)
        
        # 更新请求时间
        self.request_stats[site_name]["last_request_time"] = time.time()
        
        for retry in range(max_retries + 1):
            try:
                logger.debug(f"请求URL: {url}, 网站: {site_name}, 尝试次数: {retry+1}/{max_retries+1}")
                
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    timeout=timeout,
                    **kwargs
                )
                
                # 根据状态码判断是否成功
                if response.status_code < 400:
                    # 更新成功计数
                    self.request_stats[site_name]["success"] += 1
                    
                    # 检测和转换编码
                    response = self._handle_encoding(response, site_config["encoding"])
                    
                    return response
                else:
                    logger.warning(f"请求失败, URL: {url}, 状态码: {response.status_code}")
            except (requests.RequestException, socket.timeout, ConnectionError) as e:
                logger.warning(f"请求异常, URL: {url}, 异常: {type(e).__name__}, 信息: {str(e)}")
            
            # 更新失败计数
            self.request_stats[site_name]["failure"] += 1
            
            # 如果不是最后一次尝试，则等待重试
            if retry < max_retries:
                delay = retry_delays[min(retry, len(retry_delays) - 1)]
                # 增加随机抖动
                delay = delay * (0.8 + 0.4 * random.random())
                logger.debug(f"等待 {delay:.2f} 秒后重试...")
                time.sleep(delay)
            else:
                logger.error(f"达到最大重试次数, URL: {url}")
        
        return None
    
    def _respect_rate_limit(self, site_name):
        """遵守请求频率限制"""
        site_config = self.site_configs.get(site_name, self.site_configs["网易财经"])
        stats = self.request_stats[site_name]
        
        rate_limit = site_config["rate_limit"]
        
        # 计算成功率
        total_requests = stats["success"] + stats["failure"]
        success_rate = stats["success"] / max(total_requests, 1)
        
        # 根据成功率调整速率限制
        if success_rate < site_config["slow_down_threshold"]:
            # 降低速率，增加等待时间
            adjusted_rate = rate_limit * 0.5
            logger.warning(f"成功率低 ({success_rate:.2f}), 降低请求速率: {adjusted_rate:.2f} 请求/秒")
        elif success_rate < site_config["success_rate_threshold"]:
            # 轻微降低速率
            adjusted_rate = rate_limit * 0.8
            logger.info(f"成功率中等 ({success_rate:.2f}), 调整请求速率: {adjusted_rate:.2f} 请求/秒")
        else:
            # 保持正常速率
            adjusted_rate = rate_limit
        
        # 计算距离上次请求的时间间隔
        time_since_last = time.time() - stats["last_request_time"]
        required_interval = 1.0 / adjusted_rate
        
        # 如果间隔不足，则等待
        if time_since_last < required_interval:
            wait_time = required_interval - time_since_last
            time.sleep(wait_time)
    
    def _handle_encoding(self, response, default_encoding):
        """处理响应编码"""
        try:
            # 检测编码
            if response.encoding == 'ISO-8859-1':
                # 如果响应没有指定编码或指定了不太可能的编码，则尝试更好的猜测
                encoding_detect = chardet.detect(response.content)
                detected_encoding = encoding_detect['encoding']
                
                if detected_encoding and detected_encoding.lower() != 'iso-8859-1':
                    response.encoding = detected_encoding
                else:
                    # 如果检测失败或再次得到ISO-8859-1，使用默认编码
                    response.encoding = default_encoding
            
            # 如果编码仍然是ISO-8859-1，强制使用默认编码
            if response.encoding == 'ISO-8859-1':
                response.encoding = default_encoding
                
            return response
        except Exception as e:
            logger.error(f"处理响应编码时出错: {str(e)}")
            return response
    
    def parallel_fetch(self, urls, site_name, **kwargs):
        """
        并行获取多个URL
        
        Args:
            urls: URL列表
            site_name: 网站名称
            **kwargs: 其他请求参数
            
        Returns:
            dict: {url: response} 字典
        """
        results = {}
        futures = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            for url in urls:
                future = executor.submit(self.fetch_with_retry, url, site_name, **kwargs)
                futures[future] = url
            
            # 获取结果
            for future in as_completed(futures):
                url = futures[future]
                try:
                    response = future.result()
                    results[url] = response
                except Exception as e:
                    logger.error(f"并行获取URL时出错: {url}, 异常: {str(e)}")
                    results[url] = None
        
        return results
    
    async def _async_fetch(self, url, site_name, **kwargs):
        """异步获取单个URL"""
        site_config = self.site_configs.get(site_name, self.site_configs["网易财经"])
        headers = kwargs.pop("headers", self.get_site_specific_headers(site_name))
        timeout = kwargs.pop("timeout", site_config["connection_timeout"] + site_config["read_timeout"])
        
        max_retries = site_config["max_retries"]
        retry_delays = site_config["retry_delay"]
        
        for retry in range(max_retries + 1):
            try:
                # 遵守速率限制
                self._respect_rate_limit(site_name)
                
                # 更新请求时间
                self.request_stats[site_name]["last_request_time"] = time.time()
                
                if self.async_session is None:
                    self.async_session = aiohttp.ClientSession()
                
                async with self.async_session.get(url, headers=headers, timeout=timeout, **kwargs) as response:
                    if response.status < 400:
                        # 更新成功计数
                        self.request_stats[site_name]["success"] += 1
                        
                        # 读取响应内容
                        content = await response.read()
                        
                        # 尝试检测编码
                        encoding_detect = chardet.detect(content)
                        encoding = encoding_detect['encoding'] or site_config["encoding"]
                        
                        # 返回文本内容和响应对象
                        return {
                            'text': content.decode(encoding, errors='replace'),
                            'status': response.status,
                            'url': str(response.url),
                            'headers': dict(response.headers)
                        }
                    else:
                        logger.warning(f"异步请求失败, URL: {url}, 状态码: {response.status}")
            except Exception as e:
                logger.warning(f"异步请求异常, URL: {url}, 异常: {type(e).__name__}, 信息: {str(e)}")
            
            # 更新失败计数
            self.request_stats[site_name]["failure"] += 1
            
            # 如果不是最后一次尝试，则等待重试
            if retry < max_retries:
                delay = retry_delays[min(retry, len(retry_delays) - 1)]
                # 增加随机抖动
                delay = delay * (0.8 + 0.4 * random.random())
                logger.debug(f"等待 {delay:.2f} 秒后重试...")
                await asyncio.sleep(delay)
        
        return None
    
    async def async_fetch_all(self, urls, site_name, **kwargs):
        """
        异步获取多个URL
        
        Args:
            urls: URL列表
            site_name: 网站名称
            **kwargs: 其他请求参数
            
        Returns:
            dict: {url: response_dict} 字典
        """
        tasks = []
        for url in urls:
            task = asyncio.ensure_future(self._async_fetch(url, site_name, **kwargs))
            tasks.append((url, task))
        
        results = {}
        for url, task in tasks:
            try:
                result = await task
                results[url] = result
            except Exception as e:
                logger.error(f"异步获取多个URL时出错: {url}, 异常: {str(e)}")
                results[url] = None
        
        return results
    
    def check_network_status(self, test_urls=None):
        """
        检查网络状态
        
        Args:
            test_urls: 测试URL列表，默认为各网站的首页
            
        Returns:
            dict: 网络状态信息
        """
        if test_urls is None:
            test_urls = {
                "网易财经": "https://money.163.com/",
                "新浪财经": "https://finance.sina.com.cn/",
                "凤凰财经": "https://finance.ifeng.com/"
            }
        
        results = {}
        for site_name, url in test_urls.items():
            try:
                start_time = time.time()
                response = self.fetch_with_retry(url, site_name, max_retries=1)
                elapsed = time.time() - start_time
                
                if response and response.status_code < 400:
                    results[site_name] = {
                        "status": "可访问",
                        "response_time": elapsed,
                        "status_code": response.status_code,
                    }
                else:
                    results[site_name] = {
                        "status": "不可访问",
                        "response_time": elapsed,
                        "status_code": response.status_code if response else None,
                    }
            except Exception as e:
                results[site_name] = {
                    "status": "错误",
                    "error": str(e),
                }
        
        return results
    
    def get_stats(self):
        """获取爬虫统计信息"""
        stats = {}
        for site_name, site_stats in self.request_stats.items():
            total = site_stats["success"] + site_stats["failure"]
            success_rate = site_stats["success"] / max(total, 1)
            
            stats[site_name] = {
                "total_requests": total,
                "success": site_stats["success"],
                "failure": site_stats["failure"],
                "success_rate": success_rate,
            }
        
        return stats
    
    def close(self):
        """关闭会话和连接池"""
        try:
            self.session.close()
            self.executor.shutdown(wait=False)
            
            # 关闭异步会话
            if self.async_session:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self.async_session.close())
                else:
                    loop.run_until_complete(self.async_session.close())
            
            logger.info("爬虫优化器资源已释放")
        except Exception as e:
            logger.error(f"关闭爬虫优化器资源时出错: {str(e)}") 