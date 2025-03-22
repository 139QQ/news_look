#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 爬虫包初始化文件
"""

try:
    from app.crawlers.base import BaseCrawler
    from app.crawlers.eastmoney import EastMoneyCrawler
    from app.crawlers.sina import SinaCrawler
    from app.crawlers.tencent import TencentCrawler
    from app.crawlers.netease import NeteaseCrawler
    from app.crawlers.ifeng import IfengCrawler
except ImportError as e:
    print(f"导入爬虫模块失败: {str(e)}")

# 可用的爬虫类映射
CRAWLER_CLASSES = {
    "东方财富": EastMoneyCrawler,
    "新浪财经": SinaCrawler,
    "腾讯财经": TencentCrawler,
    "网易财经": NeteaseCrawler,
    "凤凰财经": IfengCrawler,
}

def get_crawler(source, db_manager=None, use_proxy=False, use_source_db=False, db_path=None):
    """
    获取指定来源的爬虫实例
    
    Args:
        source: 爬虫来源名称
        db_manager: 数据库管理器对象
        use_proxy: 是否使用代理
        use_source_db: 是否使用来源专用数据库
        db_path: 数据库路径，如果为None则使用默认路径
    
    Returns:
        BaseCrawler: 爬虫实例
    
    Raises:
        ValueError: 如果指定的来源不存在
    """
    if source not in CRAWLER_CLASSES:
        raise ValueError(f"不支持的爬虫来源: {source}，可用来源: {', '.join(CRAWLER_CLASSES.keys())}")
    
    crawler_class = CRAWLER_CLASSES[source]
    return crawler_class(db_manager=db_manager, use_proxy=use_proxy, use_source_db=use_source_db, db_path=db_path)

def get_all_crawlers(db_manager=None, use_proxy=False, use_source_db=False, db_path=None):
    """
    获取所有爬虫实例
    
    Args:
        db_manager: 数据库管理器对象
        use_proxy: 是否使用代理
        use_source_db: 是否使用来源专用数据库
        db_path: 数据库路径，如果为None则使用默认路径
    
    Returns:
        list: 爬虫实例列表
    """
    crawlers = []
    for source in CRAWLER_CLASSES:
        try:
            crawler = get_crawler(source, db_manager, use_proxy, use_source_db, db_path)
            crawlers.append(crawler)
        except Exception as e:
            print(f"初始化爬虫 {source} 失败: {str(e)}")
    
    return crawlers

def get_crawler_sources():
    """
    获取所有支持的爬虫来源
    
    Returns:
        list: 爬虫来源列表
    """
    return list(CRAWLER_CLASSES.keys())
