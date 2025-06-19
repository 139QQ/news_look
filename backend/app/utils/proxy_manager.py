#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
代理管理模块 - 用于管理和使用HTTP代理
"""

import os
import time
import random
import logging
import requests
from threading import Lock

logger = logging.getLogger(__name__)

class ProxyManager:
    """代理管理器，用于获取、验证和管理HTTP代理"""
    
    def __init__(self, proxy_file=None, max_proxies=20, check_interval=3600):
        """
        初始化代理管理器
        
        Args:
            proxy_file (str): 代理列表文件路径，每行一个代理，格式为 ip:port
            max_proxies (int): 最大代理数量
            check_interval (int): 代理检查间隔（秒）
        """
        self.proxy_file = proxy_file
        self.max_proxies = max_proxies
        self.check_interval = check_interval
        self.proxies = []
        self.last_check_time = 0
        self.lock = Lock()
        
        # 初始化代理列表
        self._init_proxies()
    
    def _init_proxies(self):
        """初始化代理列表"""
        # 如果指定了代理文件，从文件加载代理
        if self.proxy_file and os.path.exists(self.proxy_file):
            try:
                with open(self.proxy_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        proxy = line.strip()
                        if proxy and self._is_valid_proxy_format(proxy):
                            self.proxies.append({
                                'http': f'http://{proxy}',
                                'https': f'https://{proxy}',
                                'last_used': 0,
                                'fail_count': 0
                            })
                logger.info("从文件加载了 %d 个代理", len(self.proxies))
            except (IOError, OSError) as e:
                logger.error("从文件加载代理失败: %s", str(e))
    
    def _is_valid_proxy_format(self, proxy):
        """检查代理格式是否有效"""
        import re
        # 简单的IP:PORT格式检查
        pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$'
        return bool(re.match(pattern, proxy))
    
    def _check_proxy(self, proxy):
        """
        检查代理是否可用
        
        Args:
            proxy (dict): 代理配置
            
        Returns:
            bool: 代理是否可用
        """
        test_url = 'http://www.baidu.com'
        try:
            response = requests.get(
                test_url, 
                proxies=proxy, 
                timeout=5,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            return response.status_code == 200
        except (requests.RequestException, ConnectionError, TimeoutError) as e:
            logger.debug("代理检查失败: %s, 错误: %s", proxy['http'], str(e))
            return False
    
    def _refresh_proxies(self):
        """刷新代理列表，移除不可用的代理"""
        with self.lock:
            # 检查是否需要刷新
            current_time = time.time()
            if current_time - self.last_check_time < self.check_interval:
                return
            
            # 更新检查时间
            self.last_check_time = current_time
            
            # 检查现有代理
            valid_proxies = []
            for proxy in self.proxies:
                if self._check_proxy(proxy):
                    valid_proxies.append(proxy)
            
            # 更新代理列表
            self.proxies = valid_proxies
            logger.info("代理检查完成，有效代理数量: %d", len(self.proxies))
    
    def get_proxy(self):
        """
        获取一个可用的代理
        
        Returns:
            dict: 代理配置，如果没有可用代理则返回None
        """
        # 如果没有代理，返回None
        if not self.proxies:
            return None
        
        with self.lock:
            # 随机选择一个代理
            proxy = random.choice(self.proxies)
            # 更新最后使用时间
            proxy['last_used'] = time.time()
            return proxy
    
    def report_proxy_failure(self, proxy):
        """
        报告代理失败
        
        Args:
            proxy (dict): 失败的代理
        """
        with self.lock:
            for p in self.proxies:
                if p['http'] == proxy['http']:
                    p['fail_count'] += 1
                    # 如果失败次数过多，移除该代理
                    if p['fail_count'] >= 3:
                        self.proxies.remove(p)
                        logger.info("移除失效代理: %s", p['http'])
                    break
    
    def add_proxy(self, proxy_str):
        """
        添加新代理
        
        Args:
            proxy_str (str): 代理字符串，格式为 ip:port
            
        Returns:
            bool: 是否添加成功
        """
        if not self._is_valid_proxy_format(proxy_str):
            return False
        
        with self.lock:
            # 检查是否已存在
            proxy_http = f'http://{proxy_str}'
            for p in self.proxies:
                if p['http'] == proxy_http:
                    return False
            
            # 添加新代理
            new_proxy = {
                'http': proxy_http,
                'https': f'https://{proxy_str}',
                'last_used': 0,
                'fail_count': 0
            }
            
            # 检查代理是否可用
            if self._check_proxy(new_proxy):
                self.proxies.append(new_proxy)
                logger.info("添加新代理: %s", proxy_http)
                return True
            
            return False
