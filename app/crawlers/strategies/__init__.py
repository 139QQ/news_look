#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 爬虫策略包
提供不同网站的爬虫策略实现
"""

import os
import sys
import importlib
from typing import Dict, Type
from app.utils.logger import get_logger
from app.crawlers.strategies.base_strategy import BaseCrawlerStrategy

# 获取日志记录器
logger = get_logger('crawlers.strategies')

# 策略映射
STRATEGY_MAP: Dict[str, Type[BaseCrawlerStrategy]] = {}

def load_strategy(module_name: str, class_name: str, source_name: str) -> None:
    """加载单个策略"""
    try:
        module = importlib.import_module(f"app.crawlers.strategies.{module_name}")
        strategy_class = getattr(module, class_name)
        STRATEGY_MAP[source_name] = strategy_class
        logger.info(f"成功加载策略: {source_name} -> {class_name}")
    except ImportError as e:
        logger.error(f"导入策略失败 {source_name}: {str(e)}")
    except Exception as e:
        logger.error(f"加载策略失败 {source_name}: {str(e)}")

# 加载所有策略
load_strategy('sina_strategy', 'SinaStrategy', '新浪财经')
load_strategy('eastmoney_strategy', 'EastMoneyStrategy', '东方财富')
load_strategy('netease_strategy', 'NeteaseStrategy', '网易财经')
load_strategy('ifeng_strategy', 'IfengStrategy', '凤凰财经')

# 记录加载结果
logger.info(f"已加载 {len(STRATEGY_MAP)} 个爬虫策略: {', '.join(STRATEGY_MAP.keys())}")

def get_strategy(source_name: str) -> Type[BaseCrawlerStrategy]:
    """
    根据来源名称获取对应的爬虫策略
    
    Args:
        source_name: 来源名称
        
    Returns:
        Type[BaseCrawlerStrategy]: 对应的爬虫策略类
    """
    strategy_class = STRATEGY_MAP.get(source_name)
    if not strategy_class:
        logger.error(f"未找到 {source_name} 的爬虫策略")
        return None
    return strategy_class

def list_supported_sources() -> list:
    """
    获取所有支持的新闻源列表
    
    Returns:
        list: 支持的新闻源名称列表
    """
    return list(STRATEGY_MAP.keys())

__all__ = [
    'BaseCrawlerStrategy',
    'get_strategy',
    'list_supported_sources',
    'STRATEGY_MAP'
] 