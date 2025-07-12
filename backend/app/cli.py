#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫 - 命令行工具
提供命令行接口运行爬虫
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta

from backend.app.utils.logger import configure_logger
from backend.app.crawlers.factory import CrawlerFactory
from backend.app.crawlers.strategies import STRATEGY_MAP

def setup_logger():
    """设置日志记录器"""
    logger = configure_logger(
        name="cli",
        level=logging.INFO,
        log_file="logs/cli.log"
    )
    return logger

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='财经新闻爬虫命令行工具')
    
    # 设置子命令
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 添加爬取命令
    crawl_parser = subparsers.add_parser('crawl', help='爬取新闻')
    crawl_parser.add_argument('-s', '--source', type=str, required=False,
                             help='新闻源，支持: ' + ', '.join(STRATEGY_MAP.keys()))
    crawl_parser.add_argument('-a', '--all', action='store_true',
                             help='爬取所有支持的新闻源')
    crawl_parser.add_argument('-d', '--days', type=int, default=1,
                             help='爬取天数 (默认: 1)')
    crawl_parser.add_argument('-m', '--max', type=int, default=100,
                             help='每个源最大爬取新闻数量 (默认: 100)')
    crawl_parser.add_argument('-c', '--category', type=str,
                             help='指定爬取分类，多个分类用逗号分隔')
    crawl_parser.add_argument('--db-dir', type=str, default='data',
                             help='数据库目录 (默认: data)')
    crawl_parser.add_argument('--async', dest='async_mode', action='store_true',
                             help='使用异步模式 (默认)')
    crawl_parser.add_argument('--sync', dest='async_mode', action='store_false',
                             help='使用同步模式')
    crawl_parser.add_argument('--config-dir', type=str,
                             help='配置文件目录')
    crawl_parser.add_argument('--proxy', action='store_true',
                             help='使用代理')
    crawl_parser.add_argument('--workers', type=int, default=5,
                             help='工作线程数 (默认: 5)')
    crawl_parser.add_argument('--timeout', type=int, default=30,
                             help='请求超时时间，单位秒 (默认: 30)')
    crawl_parser.set_defaults(async_mode=True)
    
    # 添加列表命令
    list_parser = subparsers.add_parser('list', help='列出支持的新闻源')
    
    # 添加版本命令
    version_parser = subparsers.add_parser('version', help='显示版本信息')
    
    return parser.parse_args()

def run_crawl(args):
    """运行爬取命令"""
    # 初始化工厂
    factory = CrawlerFactory(config_dir=args.config_dir)
    
    # 确保数据库目录存在
    if not os.path.exists(args.db_dir):
        os.makedirs(args.db_dir, exist_ok=True)
        logging.info(f"已创建数据库目录: {args.db_dir}")
    
    # 准备爬取参数
    options = {
        'use_proxy': args.proxy,
        'async_mode': args.async_mode,
        'max_workers': args.workers,
        'timeout': args.timeout
    }
    
    # 准备分类列表
    categories = None
    if args.category:
        categories = [c.strip() for c in args.category.split(',')]
    
    # 爬取所有源
    if args.all:
        logging.info(f"开始爬取所有新闻源，天数: {args.days}, 最大数量: {args.max}")
        crawlers = factory.create_all_crawlers(db_dir=args.db_dir)
        
        for source, crawler in crawlers.items():
            try:
                logging.info(f"开始爬取 {source}...")
                crawler.crawl(days=args.days, max_news=args.max, category=args.category)
                logging.info(f"爬取 {source} 完成")
            except Exception as e:
                logging.error(f"爬取 {source} 失败: {str(e)}")
        
        logging.info("所有爬取任务完成")
        return
    
    # 爬取单个源
    if not args.source:
        logging.error("必须指定 --source 或 --all")
        return
    
    try:
        # 构建数据库路径
        db_path = os.path.join(args.db_dir, f"{args.source}.db")
        
        # 创建并运行爬虫
        crawler = factory.create_crawler(args.source, db_path, options)
        crawler.crawl(days=args.days, max_news=args.max, category=args.category)
        
        logging.info(f"爬取 {args.source} 完成")
        
    except Exception as e:
        logging.error(f"爬取失败: {str(e)}")

def run_list():
    """显示支持的新闻源"""
    print("支持的新闻源列表:")
    for source in sorted(STRATEGY_MAP.keys()):
        print(f"  - {source}")

def run_version():
    """显示版本信息"""
    version = "0.1.0"  # 版本号
    print(f"财经新闻爬虫 v{version}")
    print("作者: 您的名字")
    print("许可证: MIT")

def main():
    """主函数"""
    # 设置日志
    setup_logger()
    
    # 解析参数
    args = parse_args()
    
    # 执行命令
    if args.command == 'crawl':
        run_crawl(args)
    elif args.command == 'list':
        run_list()
    elif args.command == 'version':
        run_version()
    else:
        print("请指定命令。使用 -h 或 --help 查看帮助。")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 