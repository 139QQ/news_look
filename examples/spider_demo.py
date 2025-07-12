#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 爬虫示例脚本 - 演示如何使用同步和异步方式抓取新闻数据
本脚本展示了如何使用NewsLook爬虫系统中的爬虫组件进行新闻抓取，
并将结果保存到SQLite数据库和JSON文件中。
"""

import os
import sys
import time
import json
import argparse
import logging
import asyncio
from datetime import datetime

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

# 导入爬虫相关模块
from backend.app.crawlers.factory import CrawlerFactory
from backend.app.crawlers.strategies import STRATEGY_MAP
from backend.app.utils.logger import get_logger

# 设置日志
logger = get_logger('SpiderDemo')

def setup_output_dir():
    """设置输出目录"""
    output_dir = os.path.join(root_dir, 'data', 'spider_example')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"已创建输出目录: {output_dir}")
    return output_dir

def save_results_to_json(results, filename):
    """将结果保存到JSON文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"结果已保存到: {filename}")

def run_sync_spider(source, days=1, max_news=50, category=None):
    """
    运行同步爬虫示例
    
    参数:
        source (str): 新闻源名称
        days (int): 爬取天数
        max_news (int): 最大新闻数量
        category (list): 要爬取的分类列表
    """
    logger.info(f"开始同步爬取 {source} 的新闻，天数: {days}, 最大数量: {max_news}")
    
    # 创建输出目录
    output_dir = setup_output_dir()
    
    # 设置数据库路径
    db_path = os.path.join(output_dir, f"{source}_sync.db")
    
    # 创建爬虫工厂
    factory = CrawlerFactory()
    
    # 创建爬虫
    crawler = factory.create_crawler(source, db_path, {'async_mode': False})
    
    if not crawler:
        logger.error(f"不支持的新闻源: {source}")
        logger.info(f"支持的新闻源: {', '.join(STRATEGY_MAP.keys())}")
        return None
    
    # 开始计时
    start_time = time.time()
    
    try:
        # 执行爬取操作
        results = crawler.crawl(days=days, max_news=max_news, category=category)
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        # 准备结果
        summary = {
            "source": source,
            "mode": "同步",
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_time": f"{elapsed_time:.2f}秒",
            "articles_count": len(results),
            "articles": results
        }
        
        # 保存结果到JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(output_dir, f"{source}_sync_{timestamp}.json")
        save_results_to_json(summary, json_path)
        
        logger.info(f"同步爬取完成! 获取到 {len(results)} 篇文章，耗时 {elapsed_time:.2f} 秒")
        
        return summary
    
    except Exception as e:
        logger.error(f"同步爬取失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def run_async_spider(source, days=1, max_news=50, category=None, enhanced=False):
    """
    运行异步爬虫示例
    
    参数:
        source (str): 新闻源名称
        days (int): 爬取天数
        max_news (int): 最大新闻数量
        category (list): 要爬取的分类列表
        enhanced (bool): 是否使用增强型爬虫
    """
    suffix = "enhanced" if enhanced else "async"
    logger.info(f"开始{suffix}爬取 {source} 的新闻，天数: {days}, 最大数量: {max_news}")
    
    # 创建输出目录
    output_dir = setup_output_dir()
    
    # 设置数据库路径
    db_path = os.path.join(output_dir, f"{source}_{suffix}.db")
    
    # 创建爬虫工厂
    factory = CrawlerFactory()
    
    # 创建爬虫
    if enhanced:
        crawler = factory.create_enhanced_crawler(source, db_path, {
            'async_mode': True,
            'concurrency': 15,
            'domain_concurrency': 8,
            'domain_delay': 0.5
        })
    else:
        crawler = factory.create_crawler(source, db_path, {'async_mode': True})
    
    if not crawler:
        logger.error(f"不支持的新闻源: {source}")
        logger.info(f"支持的新闻源: {', '.join(STRATEGY_MAP.keys())}")
        return None
    
    # 开始计时
    start_time = time.time()
    
    try:
        # 执行爬取操作
        results = await crawler.crawl_async(days=days, max_news=max_news, category=category)
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        # 准备结果
        summary = {
            "source": source,
            "mode": "增强型异步" if enhanced else "异步",
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_time": f"{elapsed_time:.2f}秒",
            "articles_count": results.get('success', 0),
            "failed_count": results.get('failed', 0),
            "message": results.get('message', '')
        }
        
        # 保存结果到JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(output_dir, f"{source}_{suffix}_{timestamp}.json")
        save_results_to_json(summary, json_path)
        
        logger.info(f"{suffix}爬取完成! 成功: {results.get('success', 0)}, 失败: {results.get('failed', 0)}, 耗时: {elapsed_time:.2f} 秒")
        
        return summary
    
    except Exception as e:
        logger.error(f"{suffix}爬取失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def main():
    """主函数，处理命令行参数并执行爬虫操作"""
    parser = argparse.ArgumentParser(description='NewsLook 爬虫示例脚本')
    parser.add_argument('--mode', type=str, choices=['sync', 'async', 'enhanced', 'all'], default='all',
                        help='爬取模式: sync=同步, async=异步, enhanced=增强型, all=全部 (默认: all)')
    parser.add_argument('--source', type=str, default='新浪财经',
                        help=f'新闻源 (默认: 新浪财经), 支持: {", ".join(STRATEGY_MAP.keys())}')
    parser.add_argument('--days', type=int, default=1, 
                        help='爬取天数 (默认: 1)')
    parser.add_argument('--max', type=int, default=20, 
                        help='每个源最大爬取新闻数量 (默认: 20)')
    parser.add_argument('--category', type=str, 
                        help='要爬取的分类，多个分类用逗号分隔')
    
    args = parser.parse_args()
    
    # 检查新闻源是否支持
    if args.source not in STRATEGY_MAP:
        logger.error(f"不支持的新闻源: {args.source}")
        logger.info(f"支持的新闻源: {', '.join(STRATEGY_MAP.keys())}")
        return 1
    
    # 处理分类参数
    categories = args.category.split(',') if args.category else None
    
    # 根据模式运行不同的爬虫
    results = {}
    
    if args.mode in ['sync', 'all']:
        results['sync'] = run_sync_spider(args.source, args.days, args.max, categories)
        
    if args.mode in ['async', 'all']:
        # 使用asyncio.run运行异步爬虫
        try:
            results['async'] = asyncio.run(run_async_spider(args.source, args.days, args.max, categories))
        except RuntimeError as e:
            logger.warning(f"asyncio.run失败: {str(e)}，使用传统方法")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results['async'] = loop.run_until_complete(
                    run_async_spider(args.source, args.days, args.max, categories)
                )
            finally:
                loop.close()
    
    if args.mode in ['enhanced', 'all']:
        # 使用asyncio.run运行增强型异步爬虫
        try:
            results['enhanced'] = asyncio.run(
                run_async_spider(args.source, args.days, args.max, categories, enhanced=True)
            )
        except RuntimeError as e:
            logger.warning(f"asyncio.run失败: {str(e)}，使用传统方法")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results['enhanced'] = loop.run_until_complete(
                    run_async_spider(args.source, args.days, args.max, categories, enhanced=True)
                )
            finally:
                loop.close()
    
    # 输出结果比较
    if args.mode == 'all':
        logger.info("===== 爬虫性能比较 =====")
        for mode, result in results.items():
            if result:
                mode_name = {
                    'sync': '同步',
                    'async': '异步',
                    'enhanced': '增强型'
                }.get(mode, mode)
                
                if mode == 'sync':
                    logger.info(f"{mode_name}爬虫: 获取到 {result.get('articles_count', 0)} 篇文章，"
                              f"耗时 {result.get('elapsed_time', '未知')}")
                else:
                    logger.info(f"{mode_name}爬虫: 成功: {result.get('articles_count', 0)}, "
                              f"失败: {result.get('failed_count', 0)}, "
                              f"耗时: {result.get('elapsed_time', '未知')}")
    
    return 0

if __name__ == '__main__':
    try:
        logger.info("===== NewsLook 爬虫示例脚本启动 =====")
        exit_code = main()
        logger.info("===== 爬虫示例脚本运行结束 =====")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("用户中断，程序退出")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序异常: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1) 