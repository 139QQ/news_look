#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook爬虫系统使用示例
演示如何使用基础爬虫和增强爬虫爬取新闻数据
"""

import os
import time
import json
import argparse
from typing import Dict, List, Any
from datetime import datetime

from backend.app.crawlers.factory import CrawlerFactory
from backend.app.utils.logger import get_logger

# 初始化日志记录器
logger = get_logger('spider_example')

def run_sync_spider(source: str, days: int = 1, max_news: int = 10, category: str = None):
    """
    运行同步模式的爬虫
    
    Args:
        source: 数据源名称
        days: 爬取天数
        max_news: 最大爬取数量
        category: 新闻分类
    """
    print(f"\n===== 同步爬虫示例: {source} =====")
    print(f"爬取天数: {days}, 最大新闻数: {max_news}, 分类: {category or '默认'}")
    
    # 创建输出目录
    os.makedirs('data/spider_example', exist_ok=True)
    
    # 创建工厂
    factory = CrawlerFactory()
    
    # 创建爬虫
    db_path = f'data/spider_example/{source}_sync.db'
    options = {
        'async_mode': False,  # 同步模式
        'max_concurrency': 1,
        'timeout': 30
    }
    
    crawler = factory.create_crawler(source, db_path, options)
    
    # 爬取新闻
    print("\n> 开始同步爬取...")
    start_time = time.time()
    articles = crawler.crawl(days=days, max_news=max_news, category=category)
    elapsed_time = time.time() - start_time
    
    print(f"爬取完成，耗时: {elapsed_time:.2f}秒，获取 {len(articles)} 篇文章")
    
    # 显示爬取结果
    if articles:
        print("\n> 爬取结果预览:")
        for i, article in enumerate(articles[:3], 1):
            print(f"\n文章 {i}:")
            print(f"标题: {article.get('title', '无标题')}")
            print(f"发布时间: {article.get('pub_time', '未知')}")
            print(f"URL: {article.get('url', '无URL')}")
            print(f"分类: {article.get('category', '未分类')}")
    else:
        print("\n未爬取到任何文章")
    
    # 保存结果到JSON文件
    if articles:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path = f'data/spider_example/{source}_sync_{timestamp}.json'
        
        # 转换集合为列表以便JSON序列化
        for article in articles:
            for key, value in article.items():
                if isinstance(value, set):
                    article[key] = list(value)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        
        print(f"\n> 爬取结果已保存到: {json_path}")

def run_async_spider(source: str, days: int = 1, max_news: int = 10, category: str = None, enhanced: bool = False):
    """
    运行异步模式的爬虫
    
    Args:
        source: 数据源名称
        days: 爬取天数
        max_news: 最大爬取数量
        category: 新闻分类
        enhanced: 是否使用增强爬虫
    """
    crawler_type = "增强型异步爬虫" if enhanced else "基础异步爬虫"
    print(f"\n===== {crawler_type}示例: {source} =====")
    print(f"爬取天数: {days}, 最大新闻数: {max_news}, 分类: {category or '默认'}")
    
    # 创建输出目录
    os.makedirs('data/spider_example', exist_ok=True)
    
    # 创建工厂
    factory = CrawlerFactory()
    
    # 创建爬虫
    suffix = "enhanced" if enhanced else "async"
    db_path = f'data/spider_example/{source}_{suffix}.db'
    
    options = {
        'async_mode': True,
        'max_concurrency': 5,
        'timeout': 30
    }
    
    if enhanced:
        crawler = factory.create_enhanced_crawler(source, db_path, options)
    else:
        crawler = factory.create_crawler(source, db_path, options)
    
    # 爬取新闻
    print(f"\n> 开始{crawler_type}爬取...")
    start_time = time.time()
    result = crawler.crawl(days=days, max_news=max_news, category=category)
    elapsed_time = time.time() - start_time
    
    # 检查结果
    if isinstance(result, dict) and 'articles' in result:
        articles = result['articles']
        stats = result.get('stats', {})
        success = result.get('success', False)
        
        status = "成功" if success else "失败"
        print(f"爬取{status}，耗时: {elapsed_time:.2f}秒，获取 {len(articles)} 篇文章")
        print(f"总URL数: {stats.get('total', 0)}, 成功: {stats.get('success', 0)}, 失败: {stats.get('failed', 0)}")
        
        # 显示爬取结果
        if articles:
            print("\n> 爬取结果预览:")
            for i, article in enumerate(articles[:3], 1):
                print(f"\n文章 {i}:")
                print(f"标题: {article.get('title', '无标题')}")
                print(f"发布时间: {article.get('pub_time', '未知')}")
                print(f"URL: {article.get('url', '无URL')}")
                print(f"分类: {article.get('category', '未分类')}")
                
            # 保存结果到JSON文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_path = f'data/spider_example/{source}_{suffix}_{timestamp}.json'
            
            # 转换集合为列表以便JSON序列化
            for article in articles:
                for key, value in article.items():
                    if isinstance(value, set):
                        article[key] = list(value)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            
            print(f"\n> 爬取结果已保存到: {json_path}")
        else:
            print("\n未爬取到任何文章")
    else:
        print(f"爬取返回的结果格式不正确: {result}")

def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description="NewsLook爬虫系统使用示例")
    parser.add_argument("--mode", type=str, default="all", 
                      choices=["sync", "async", "enhanced", "all"],
                      help="爬虫模式: sync(同步), async(异步), enhanced(增强), all(所有)")
    parser.add_argument("--source", type=str, default="东方财富",
                      help="要爬取的数据源")
    parser.add_argument("--days", type=int, default=1,
                      help="爬取天数")
    parser.add_argument("--max-news", type=int, default=10,
                      help="最大爬取数量")
    parser.add_argument("--category", type=str, default=None,
                      help="爬取的新闻分类")
    
    args = parser.parse_args()
    
    # 打印支持的来源
    factory = CrawlerFactory()
    supported_sources = factory.get_supported_sources()
    print(f"支持的新闻源: {', '.join(supported_sources)}")
    
    if args.source not in supported_sources:
        print(f"错误: 不支持的来源 '{args.source}'")
        return
    
    # 根据模式运行不同的爬虫
    if args.mode in ["sync", "all"]:
        run_sync_spider(args.source, args.days, args.max_news, args.category)
    
    if args.mode in ["async", "all"]:
        run_async_spider(args.source, args.days, args.max_news, args.category)
    
    if args.mode in ["enhanced", "all"]:
        run_async_spider(args.source, args.days, args.max_news, args.category, enhanced=True)

if __name__ == "__main__":
    main() 