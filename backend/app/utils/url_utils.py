#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
URL处理工具模块
"""

import re
import logging
from urllib.parse import urlparse, parse_qs, urljoin, urlunparse

logger = logging.getLogger(__name__)

def normalize_url(url):
    """
    规范化URL，去除查询参数、片段标识符等
    
    Args:
        url (str): 需要规范化的URL
        
    Returns:
        str: 规范化后的URL
    """
    if not url:
        return ""
    
    try:
        # 解析URL
        parsed = urlparse(url)
        
        # 重构URL，去除查询参数和片段标识符
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            '',  # 去除params
            '',  # 去除query
            ''   # 去除fragment
        ))
        
        # 确保URL以/结尾（如果是目录）
        if not parsed.path or parsed.path.endswith('/'):
            if not normalized.endswith('/'):
                normalized += '/'
        
        return normalized
    except (ValueError, TypeError) as e:
        logger.error("规范化URL失败: %s, 错误: %s", url, str(e))
        return url

def extract_domain(url):
    """
    从URL中提取域名
    
    Args:
        url (str): URL字符串
        
    Returns:
        str: 域名
    """
    if not url:
        return ""
    
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except (ValueError, TypeError) as e:
        logger.error("提取域名失败: %s, 错误: %s", url, str(e))
        return ""

def is_valid_url(url):
    """
    检查URL是否有效
    
    Args:
        url (str): 需要检查的URL
        
    Returns:
        bool: URL是否有效
    """
    if not url:
        return False
    
    # URL格式正则表达式
    pattern = re.compile(
        r'^(?:http|https)://'  # http:// 或 https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # 域名
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP地址
        r'(?::\d+)?'  # 可选端口
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return bool(pattern.match(url))

def get_url_params(url):
    """
    获取URL中的查询参数
    
    Args:
        url (str): URL字符串
        
    Returns:
        dict: 查询参数字典
    """
    if not url:
        return {}
    
    try:
        parsed = urlparse(url)
        return parse_qs(parsed.query)
    except (ValueError, TypeError) as e:
        logger.error("获取URL参数失败: %s, 错误: %s", url, str(e))
        return {}

def join_url(base, path):
    """
    连接基础URL和路径
    
    Args:
        base (str): 基础URL
        path (str): 相对路径
        
    Returns:
        str: 完整URL
    """
    if not base or not path:
        return base or path
    
    try:
        return urljoin(base, path)
    except (ValueError, TypeError) as e:
        logger.error("连接URL失败: %s, %s, 错误: %s", base, path, str(e))
        return path if path.startswith(('http://', 'https://')) else base
