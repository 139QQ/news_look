#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试新架构爬虫的命令行脚本
"""

import os
import sys
import argparse
import asyncio
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.crawlers.manager_new import EnhancedCrawlerManager
from backend.app.utils.logger import setup_logger

# 设置日志
log_dir = os.path.join(os.getcwd(), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'enhanced_crawler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
setup_logger(log_file=log_file)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='测试新架构爬虫')
    
    # 基本参数
    parser.add_argument('--source', '-s', type=str, help='爬虫来源，例如"东方财富"')
    parser.add_argument('--days', '-d', type=int, default=1, help='爬取最近几天的新闻')
    parser.add_argument('--max-news', '-m', type=int, help='最大爬取新闻数量')
    parser.add_argument('--db-dir', type=str, help='数据库目录路径')
    
    # 运行模式
    parser.add_argument('--async', action='store_true', help='使用异步模式')
    parser.add_argument('--daemon', action='store_true', help='后台运行模式')
    parser.add_argument('--interval', '-i', type=int, default=3600, help='爬取间隔（秒）')
    
    # 其他选项
    parser.add_argument('--proxy', action='store_true', help='使用代理')
    parser.add_argument('--output', '-o', type=str, help='输出文件路径')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    return parser.parse_args()


async def run_async(args):
    """异步运行爬虫"""
    settings = {}
    
    # 设置数据库目录
    if args.db_dir:
        settings['DB_DIR'] = args.db_dir
        
    # 设置代理
    settings['USE_PROXY'] = args.proxy
    
    # 设置异步模式
    settings['USE_ASYNC'] = True
    
    # 创建爬虫管理器
    manager = EnhancedCrawlerManager(settings)
    
    try:
        if args.daemon:
            # 守护进程模式
            print(f"启动爬虫 {args.source or '所有'} 在后台运行，间隔 {args.interval} 秒")
            
            if args.source:
                manager.start_crawler(args.source, args.interval)
            else:
                manager.start_all(args.interval)
                
            # 保持运行
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("收到中断信号，正在停止爬虫...")
                manager.stop_all()
        else:
            # 单次运行模式
            if args.source:
                print(f"开始运行爬虫: {args.source}")
                start_time = time.time()
                
                # 运行爬虫
                result = await manager.run_crawler_once_async(args.source, args.days, args.max_news)
                
                elapsed = time.time() - start_time
                print(f"爬虫运行完成，耗时 {elapsed:.2f} 秒，获取 {len(result)} 条新闻")
                
                # 如果指定了输出文件，保存结果
                if args.output and result:
                    import json
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    print(f"结果已保存到 {args.output}")
            else:
                # 运行所有爬虫
                all_results = []
                for source in manager.get_crawlers():
                    print(f"开始运行爬虫: {source}")
                    start_time = time.time()
                    
                    # 运行爬虫
                    result = await manager.run_crawler_once_async(source, args.days, args.max_news)
                    all_results.extend(result)
                    
                    elapsed = time.time() - start_time
                    print(f"爬虫 {source} 运行完成，耗时 {elapsed:.2f} 秒，获取 {len(result)} 条新闻")
                
                print(f"所有爬虫运行完成，共获取 {len(all_results)} 条新闻")
                
                # 如果指定了输出文件，保存结果
                if args.output and all_results:
                    import json
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(all_results, f, ensure_ascii=False, indent=2)
                    print(f"结果已保存到 {args.output}")
    finally:
        # 使用异步关闭方法来关闭管理器
        await manager.close_async()


def run_sync(args):
    """同步运行爬虫"""
    settings = {}
    
    # 设置数据库目录
    if args.db_dir:
        settings['DB_DIR'] = args.db_dir
        
    # 设置代理
    settings['USE_PROXY'] = args.proxy
    
    # 设置同步模式
    settings['USE_ASYNC'] = False
    
    # 创建爬虫管理器
    manager = EnhancedCrawlerManager(settings)
    
    try:
        if args.daemon:
            # 守护进程模式
            print(f"启动爬虫 {args.source or '所有'} 在后台运行，间隔 {args.interval} 秒")
            
            if args.source:
                manager.start_crawler(args.source, args.interval)
            else:
                manager.start_all(args.interval)
                
            # 保持运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("收到中断信号，正在停止爬虫...")
                manager.stop_all()
        else:
            # 单次运行模式
            if args.source:
                print(f"开始运行爬虫: {args.source}")
                start_time = time.time()
                
                # 运行爬虫
                result = manager.run_crawler_once(args.source, args.days, args.max_news)
                
                elapsed = time.time() - start_time
                print(f"爬虫运行完成，耗时 {elapsed:.2f} 秒，获取 {len(result)} 条新闻")
                
                # 如果指定了输出文件，保存结果
                if args.output and result:
                    import json
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    print(f"结果已保存到 {args.output}")
            else:
                # 运行所有爬虫
                all_results = []
                for source in manager.get_crawlers():
                    print(f"开始运行爬虫: {source}")
                    start_time = time.time()
                    
                    # 运行爬虫
                    result = manager.run_crawler_once(source, args.days, args.max_news)
                    all_results.extend(result)
                    
                    elapsed = time.time() - start_time
                    print(f"爬虫 {source} 运行完成，耗时 {elapsed:.2f} 秒，获取 {len(result)} 条新闻")
                
                print(f"所有爬虫运行完成，共获取 {len(all_results)} 条新闻")
                
                # 如果指定了输出文件，保存结果
                if args.output and all_results:
                    import json
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(all_results, f, ensure_ascii=False, indent=2)
                    print(f"结果已保存到 {args.output}")
    finally:
        # 关闭管理器
        manager.close()


def main():
    """主函数"""
    args = parse_args()
    
    # 如果使用异步模式
    if getattr(args, 'async'):
        asyncio.run(run_async(args))
    else:
        run_sync(args)


if __name__ == '__main__':
    main() 