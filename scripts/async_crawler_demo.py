#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
异步爬虫示例和性能比较脚本
用于演示异步爬虫的使用方法和对比性能差异
"""

import os
import sys
import time
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.crawlers import get_crawler, get_crawler_sources, has_async_support
from app.utils.logger import get_crawler_logger

# 设置日志
logger = get_crawler_logger('async_demo')

def run_performance_test(source, max_news=20, days=1, use_source_db=True):
    """
    对指定来源的同步和异步爬虫进行性能测试
    
    Args:
        source: 爬虫来源名称
        max_news: 最大爬取新闻数量
        days: 爬取的天数范围 
        use_source_db: 是否使用来源专用数据库
        
    Returns:
        dict: 性能测试结果
    """
    if not has_async_support(source):
        logger.warning(f"{source} 不支持异步爬取，跳过性能测试")
        return None
    
    results = {
        'source': source,
        'max_news': max_news,
        'days': days,
        'sync_time': None,
        'async_time': None,
        'speedup': None,
        'sync_count': 0,
        'async_count': 0
    }
    
    # 测试同步爬虫
    logger.info(f"开始测试 {source} 同步爬虫...")
    sync_crawler = get_crawler(source, use_async=False, use_source_db=use_source_db)
    
    sync_start = time.time()
    sync_news = sync_crawler.crawl(days=days, max_news=max_news)
    sync_end = time.time()
    
    sync_time = sync_end - sync_start
    results['sync_time'] = sync_time
    results['sync_count'] = len(sync_news) if sync_news else 0
    
    logger.info(f"同步爬虫测试完成，用时 {sync_time:.2f} 秒，获取新闻 {results['sync_count']} 条")
    
    # 测试异步爬虫
    logger.info(f"开始测试 {source} 异步爬虫...")
    async_crawler = get_crawler(source, use_async=True, use_source_db=use_source_db)
    
    async_start = time.time()
    async_news = async_crawler.crawl(days=days, max_news=max_news)
    async_end = time.time()
    
    async_time = async_end - async_start
    results['async_time'] = async_time
    results['async_count'] = len(async_news) if async_news else 0
    
    logger.info(f"异步爬虫测试完成，用时 {async_time:.2f} 秒，获取新闻 {results['async_count']} 条")
    
    # 计算加速比
    if sync_time > 0:
        results['speedup'] = sync_time / async_time
        logger.info(f"异步爬虫较同步爬虫提速 {results['speedup']:.2f} 倍")
    
    return results

def plot_performance_results(results):
    """
    绘制性能测试结果图表
    
    Args:
        results: 性能测试结果列表
    """
    if not results:
        logger.warning("没有性能测试结果可供绘制")
        return
    
    # 转换结果为DataFrame
    df = pd.DataFrame(results)
    
    # 创建图表
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 绘制执行时间对比
    df.plot(x='source', y=['sync_time', 'async_time'], kind='bar', ax=ax1, 
            color=['blue', 'green'], alpha=0.7)
    ax1.set_title('同步 vs 异步爬虫执行时间对比')
    ax1.set_ylabel('执行时间 (秒)')
    ax1.set_xlabel('爬虫来源')
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    
    for i, v in enumerate(df['sync_time']):
        ax1.text(i-0.1, v+0.5, f"{v:.1f}s", color='blue', fontweight='bold')
    
    for i, v in enumerate(df['async_time']):
        ax1.text(i+0.1, v+0.5, f"{v:.1f}s", color='green', fontweight='bold')
    
    # 绘制加速比
    df.plot(x='source', y='speedup', kind='bar', ax=ax2, color='red', alpha=0.7)
    ax2.set_title('异步爬虫加速比')
    ax2.set_ylabel('加速比 (倍)')
    ax2.set_xlabel('爬虫来源')
    ax2.axhline(y=1, color='gray', linestyle='--')
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    
    for i, v in enumerate(df['speedup']):
        ax2.text(i, v+0.1, f"{v:.2f}x", color='red', fontweight='bold', ha='center')
    
    plt.tight_layout()
    
    # 保存图表
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'crawler_performance_{timestamp}.png')
    plt.savefig(output_path)
    logger.info(f"性能测试结果图表已保存至: {output_path}")
    
    # 显示图表（如果在交互环境中运行）
    plt.show()

def save_performance_results(results):
    """
    保存性能测试结果为CSV文件
    
    Args:
        results: 性能测试结果列表
    """
    if not results:
        logger.warning("没有性能测试结果可供保存")
        return
    
    # 转换结果为DataFrame
    df = pd.DataFrame(results)
    
    # 保存为CSV文件
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'crawler_performance_{timestamp}.csv')
    df.to_csv(output_path, index=False)
    logger.info(f"性能测试结果已保存至: {output_path}")

def run_demo():
    """
    运行异步爬虫演示
    """
    logger.info("开始异步爬虫性能演示")
    
    # 获取支持异步的爬虫来源
    async_sources = [source for source in get_crawler_sources() if has_async_support(source)]
    
    if not async_sources:
        logger.error("没有找到支持异步的爬虫")
        return
    
    logger.info(f"支持异步的爬虫来源: {', '.join(async_sources)}")
    
    # 运行每个爬虫来源的性能测试
    results = []
    for source in async_sources:
        logger.info(f"=========== 测试 {source} ===========")
        result = run_performance_test(source, max_news=20, days=1)
        if result:
            results.append(result)
    
    # 保存和绘制结果
    if results:
        save_performance_results(results)
        try:
            plot_performance_results(results)
        except Exception as e:
            logger.error(f"绘制性能测试结果图表失败: {str(e)}")
    
    logger.info("异步爬虫性能演示完成")

def demo_specific_crawler(source, max_news=20, days=1, use_async=True):
    """
    演示特定爬虫的用法
    
    Args:
        source: 爬虫来源名称
        max_news: 最大爬取新闻数量
        days: 爬取的天数范围
        use_async: 是否使用异步爬虫
    """
    if use_async and not has_async_support(source):
        logger.warning(f"{source} 不支持异步爬取，将使用同步爬虫")
        use_async = False
    
    crawler_type = "异步" if use_async else "同步"
    logger.info(f"开始使用{crawler_type}爬虫爬取 {source} 新闻...")
    
    crawler = get_crawler(source, use_async=use_async, use_source_db=True)
    
    start_time = time.time()
    news_list = crawler.crawl(days=days, max_news=max_news)
    end_time = time.time()
    
    logger.info(f"爬取完成，用时 {end_time - start_time:.2f} 秒，获取新闻 {len(news_list) if news_list else 0} 条")
    
    # 打印前5条新闻的标题和发布时间
    if news_list:
        logger.info("前5条新闻:")
        for i, news in enumerate(news_list[:5], 1):
            logger.info(f"{i}. {news['title']} ({news['pub_time']})")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="异步爬虫示例和性能比较")
    parser.add_argument("--mode", type=str, choices=["demo", "test", "specific"], default="demo",
                       help="运行模式：demo-完整演示, test-性能测试, specific-特定爬虫")
    parser.add_argument("--source", type=str, help="爬虫来源名称")
    parser.add_argument("--max_news", type=int, default=20, help="最大爬取新闻数量")
    parser.add_argument("--days", type=int, default=1, help="爬取的天数范围")
    parser.add_argument("--sync", action="store_true", help="使用同步爬虫（默认使用异步）")
    
    args = parser.parse_args()
    
    if args.mode == "demo":
        run_demo()
    elif args.mode == "test":
        if not args.source:
            logger.error("请指定爬虫来源名称")
            sys.exit(1)
        result = run_performance_test(args.source, args.max_news, args.days)
        if result:
            save_performance_results([result])
            try:
                plot_performance_results([result])
            except Exception as e:
                logger.error(f"绘制性能测试结果图表失败: {str(e)}")
    elif args.mode == "specific":
        if not args.source:
            logger.error("请指定爬虫来源名称")
            sys.exit(1)
        demo_specific_crawler(args.source, args.max_news, args.days, not args.sync) 