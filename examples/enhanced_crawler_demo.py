#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强型爬虫示例脚本
演示如何使用增强型异步爬虫以及与标准爬虫的性能对比
"""

import os
import time
import argparse
import matplotlib.pyplot as plt
from typing import Dict, List, Any
from datetime import datetime

from app.crawlers.factory import CrawlerFactory
from app.utils.logger import get_logger

# 初始化日志记录器
logger = get_logger('enhanced_demo')

def run_performance_comparison(source: str, days: int = 1, max_news: int = 20):
    """
    运行性能对比测试
    
    Args:
        source: 数据源名称
        days: 爬取天数
        max_news: 最大爬取数量
    """
    print(f"\n===== 性能对比测试: {source} =====")
    print(f"爬取天数: {days}, 最大新闻数: {max_news}")
    
    # 创建测试目录
    os.makedirs('data/enhanced_demo', exist_ok=True)
    
    # 创建工厂
    factory = CrawlerFactory()
    
    # 测试标准爬虫
    standard_db = f'data/enhanced_demo/{source}_standard.db'
    standard_options = {
        'async_mode': True,
        'max_concurrency': 5,
        'timeout': 30
    }
    
    standard_crawler = factory.create_crawler(source, standard_db, standard_options)
    
    print("\n> 运行标准爬虫...")
    standard_start = time.time()
    standard_articles = standard_crawler.crawl(days=days, max_news=max_news)
    standard_time = time.time() - standard_start
    
    print(f"标准爬虫完成，耗时: {standard_time:.2f}秒，获取 {len(standard_articles)} 篇文章")
    
    # 测试增强型爬虫
    enhanced_db = f'data/enhanced_demo/{source}_enhanced.db'
    enhanced_options = {
        'concurrency_per_domain': 5,
        'domain_delay': 0.2,
        'chunk_size': 10
    }
    
    enhanced_crawler = factory.create_enhanced_crawler(source, enhanced_db, enhanced_options)
    
    print("\n> 运行增强型爬虫...")
    enhanced_start = time.time()
    enhanced_articles = enhanced_crawler.crawl(days=days, max_news=max_news)
    enhanced_time = time.time() - enhanced_start
    
    print(f"增强型爬虫完成，耗时: {enhanced_time:.2f}秒，获取 {len(enhanced_articles)} 篇文章")
    
    # 计算性能提升
    if standard_time > 0:
        improvement = (standard_time - enhanced_time) / standard_time * 100
        print(f"\n> 性能提升: {improvement:.2f}%")
    else:
        print("\n> 无法计算性能提升 (标准爬虫耗时为0)")
    
    # 绘制对比图表
    labels = ['标准爬虫', '增强型爬虫']
    times = [standard_time, enhanced_time]
    counts = [len(standard_articles), len(enhanced_articles)]
    
    plt.figure(figsize=(12, 5))
    
    # 时间对比
    plt.subplot(1, 2, 1)
    plt.bar(labels, times, color=['blue', 'green'])
    plt.title('爬取耗时对比 (秒)')
    plt.ylabel('耗时 (秒)')
    
    # 文章数量对比
    plt.subplot(1, 2, 2)
    plt.bar(labels, counts, color=['blue', 'green'])
    plt.title('文章数量对比')
    plt.ylabel('文章数量')
    
    # 保存图表
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    chart_path = f'data/enhanced_demo/{source}_comparison_{timestamp}.png'
    plt.tight_layout()
    plt.savefig(chart_path)
    
    print(f"\n> 对比图表已保存到: {chart_path}")


def enhanced_crawler_example(source: str):
    """
    增强型爬虫使用示例
    
    Args:
        source: 数据源名称
    """
    print(f"\n===== 增强型爬虫示例: {source} =====")
    
    # 创建目录
    os.makedirs('data/enhanced_demo', exist_ok=True)
    
    # 创建工厂
    factory = CrawlerFactory()
    
    # 创建增强型爬虫，配置高级选项
    db_path = f'data/enhanced_demo/{source}_example.db'
    options = {
        'concurrency_per_domain': 5,     # 每个域名最大并发请求数
        'domain_delay': 0.5,             # 同域名请求之间的延迟(秒)
        'chunk_size': 10,                # 分批处理的大小
        'timeout': 30                    # 请求超时时间(秒)
    }
    
    crawler = factory.create_enhanced_crawler(source, db_path, options)
    
    # 爬取新闻
    print("\n> 开始爬取...")
    start_time = time.time()
    articles = crawler.crawl(days=1, max_news=10)
    elapsed_time = time.time() - start_time
    
    print(f"爬取完成，耗时: {elapsed_time:.2f}秒，获取 {len(articles)} 篇文章")
    
    # 显示爬取结果
    print("\n> 爬取结果预览:")
    for i, article in enumerate(articles[:3], 1):
        print(f"\n文章 {i}:")
        print(f"标题: {article.get('title', '无标题')}")
        print(f"发布时间: {article.get('pub_time', '未知')}")
        print(f"URL: {article.get('url', '无URL')}")
        print(f"分类: {article.get('category', '未分类')}")
        if 'content' in article:
            content = article['content']
            preview = content[:100] + '...' if len(content) > 100 else content
            print(f"内容预览: {preview}")
    
    # 显示爬虫统计信息
    stats = crawler.get_stats()
    print("\n> 爬虫统计信息:")
    print(f"爬取次数: {stats.get('crawl_count', 0)}")
    print(f"成功数量: {stats.get('success_count', 0)}")
    print(f"失败数量: {stats.get('failed_count', 0)}")
    print(f"总耗时: {stats.get('total_time', 0):.2f}秒")


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description="增强型爬虫演示")
    parser.add_argument("--mode", type=str, default="example", 
                      choices=["example", "test", "both"],
                      help="演示模式: example(使用示例), test(性能测试), both(两者)")
    parser.add_argument("--source", type=str, default="东方财富",
                      help="要爬取的数据源")
    parser.add_argument("--days", type=int, default=1,
                      help="爬取天数")
    parser.add_argument("--max-news", type=int, default=20,
                      help="最大爬取数量")
    
    args = parser.parse_args()
    
    if args.mode in ["example", "both"]:
        enhanced_crawler_example(args.source)
    
    if args.mode in ["test", "both"]:
        run_performance_comparison(args.source, args.days, args.max_news)


if __name__ == "__main__":
    main() 