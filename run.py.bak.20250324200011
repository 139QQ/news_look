#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 主程序入口
支持多种运行模式：爬虫模式、调度模式、Web应用模式
"""

import os
import sys
import argparse
import logging
import importlib
import glob
from pathlib import Path

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from app.utils.logger import configure_logger, get_logger
from app.web import create_app
from app.crawlers.manager import CrawlerManager

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='财经新闻爬虫系统')

    # 子命令解析器
    subparsers = parser.add_subparsers(dest='mode', help='运行模式')

    # 爬虫模式
    crawler_parser = subparsers.add_parser('crawler', help='爬虫模式')
    crawler_parser.add_argument('-s', '--source', default='all', help='爬虫来源，默认全部')
    crawler_parser.add_argument('-d', '--days', type=int, default=1, help='爬取天数，默认1天')
    crawler_parser.add_argument('-p', '--use-proxy', action='store_true', help='使用代理')
    crawler_parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='日志级别')
    crawler_parser.add_argument('--log-dir', default='./logs', help='日志目录')
    crawler_parser.add_argument('--db-dir', default=None, help='数据库目录，如不指定则自动检测')
    crawler_parser.add_argument('--max-news', type=int, default=10, help='每类最多新闻数')
    crawler_parser.add_argument('--categories', nargs='+', default=['财经', '股票'], help='新闻分类')
    crawler_parser.add_argument('--debug', action='store_true', help='调试模式')

    # 调度模式
    scheduler_parser = subparsers.add_parser('scheduler', help='调度模式')
    scheduler_parser.add_argument('--daemon', action='store_true', help='守护进程模式')
    scheduler_parser.add_argument('--config', help='配置文件路径')
    scheduler_parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='日志级别')
    scheduler_parser.add_argument('--log-dir', default='./logs', help='日志目录')
    scheduler_parser.add_argument('--db-dir', default=None, help='数据库目录，如不指定则自动检测')
    scheduler_parser.add_argument('--command', choices=['start', 'list'], default='start', help='调度器命令')

    # Web应用模式
    web_parser = subparsers.add_parser('web', help='Web应用模式')
    web_parser.add_argument('--host', default='0.0.0.0', help='监听主机')
    web_parser.add_argument('--port', type=int, default=5000, help='监听端口')
    web_parser.add_argument('--debug', action='store_true', help='调试模式')
    web_parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='日志级别')
    web_parser.add_argument('--log-dir', default='./logs', help='日志目录')
    web_parser.add_argument('--db-dir', default=None, help='数据库目录，如不指定则自动检测')
    web_parser.add_argument('--with-crawler', action='store_true', help='初始化爬虫管理器')

    return parser.parse_args()

def find_db_dir():
    """查找数据库目录，按优先级顺序尝试多个可能的位置"""
    # 可能的数据库目录列表，按优先级排序
    possible_dirs = [
        os.path.join(project_root, 'data', 'db'),  # ./data/db
        os.path.join(project_root, 'db'),          # ./db
        os.path.join(os.getcwd(), 'data', 'db'),   # 当前工作目录/data/db
        os.path.join(os.getcwd(), 'db')            # 当前工作目录/db
    ]
    
    # 首先找含有数据库文件的目录
    for db_dir in possible_dirs:
        if os.path.exists(db_dir):
            db_files = glob.glob(os.path.join(db_dir, '*.db'))
            if db_files:
                return os.path.abspath(db_dir)
    
    # 如果没有找到含数据库文件的目录，则返回第一个存在的目录
    for db_dir in possible_dirs:
        if os.path.exists(db_dir):
            return os.path.abspath(db_dir)
    
    # 如果所有目录都不存在，则创建并返回默认目录
    default_dir = os.path.join(project_root, 'data', 'db')
    os.makedirs(default_dir, exist_ok=True)
    return os.path.abspath(default_dir)

def run_crawler_mode(args):
    """运行爬虫模式"""
    # 设置环境变量
    os.environ['LOG_LEVEL'] = args.log_level
    os.environ['LOG_DIR'] = os.path.abspath(args.log_dir)
    
    # 设置数据库目录
    if args.db_dir:
        db_dir = os.path.abspath(args.db_dir)
    else:
        db_dir = find_db_dir()
    os.environ['DB_DIR'] = db_dir
    
    print(f"使用数据库目录: {db_dir}")

    # 动态导入模块
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app.crawlers.manager import CrawlerManager

    # 初始化爬虫管理器
    manager = CrawlerManager()

    # 根据参数配置爬虫
    if args.source == 'all':
        crawler_list = manager.get_available_crawlers()
    else:
        crawler_list = [args.source]

    # 运行爬虫
    for crawler_name in crawler_list:
        # 设置参数
        params = {
            'days': args.days,
            'use_proxy': args.use_proxy,
            'max_news': args.max_news,
            'categories': args.categories
        }

        # 运行爬虫
        print(f"开始运行爬虫: {crawler_name}")
        try:
            result = manager.run_crawler(crawler_name, **params)
            print(f"爬虫 {crawler_name} 运行完成，共获取 {result} 条数据")
        except Exception as e:
            print(f"爬虫 {crawler_name} 运行出错: {e}")

def run_scheduler_mode(args):
    """运行调度器模式"""
    # 设置环境变量
    os.environ['LOG_LEVEL'] = args.log_level
    os.environ['LOG_DIR'] = os.path.abspath(args.log_dir)
    
    # 设置数据库目录
    if args.db_dir:
        db_dir = os.path.abspath(args.db_dir)
    else:
        db_dir = find_db_dir()
    os.environ['DB_DIR'] = db_dir
    
    print(f"使用数据库目录: {db_dir}")

    # 动态导入模块
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app.scheduler import Scheduler

    # 初始化调度器
    scheduler = Scheduler(daemon=args.daemon)

    # 根据命令执行操作
    if args.command == 'start':
        scheduler.start()
    elif args.command == 'list':
        scheduler.list_tasks()
    else:
        print("错误：未知的调度器命令")

def run_web_mode(args):
    """运行Web应用模式"""
    # 设置环境变量
    os.environ['LOG_LEVEL'] = args.log_level
    os.environ['LOG_DIR'] = os.path.abspath(args.log_dir)
    
    # 设置数据库目录
    if args.db_dir:
        db_dir = os.path.abspath(args.db_dir)
    else:
        db_dir = find_db_dir()
    os.environ['DB_DIR'] = db_dir
    
    print(f"使用数据库目录: {db_dir}")

    # 检查必要的目录
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # 动态导入模块
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app.web import create_app
    
    # 创建Flask应用
    app_config = {
        'DEBUG': args.debug,
        'DB_DIR': db_dir
    }
    
    # 如果需要初始化爬虫管理器
    if args.with_crawler:
        from app.crawlers.manager import CrawlerManager
        crawler_manager = CrawlerManager()
        app_config['CRAWLER_MANAGER'] = crawler_manager

    # 创建Flask应用
    app = create_app(app_config)

    # 运行Web应用
    app.run(host=args.host, port=args.port)

def main():
    """主函数"""
    # 创建必要的目录
    for directory in ['logs']:
        os.makedirs(directory, exist_ok=True)
        print(f"创建目录: {directory}")

    # 设置默认环境变量
    os.environ['LOG_LEVEL'] = os.environ.get('LOG_LEVEL', 'INFO')
    os.environ['LOG_DIR'] = os.environ.get('LOG_DIR', os.path.join(os.getcwd(), 'logs'))
    
    # 查找并设置数据库目录
    db_dir = find_db_dir()
    os.environ['DB_DIR'] = os.environ.get('DB_DIR', db_dir)
    
    print(f"环境变量设置完成:")
    print(f"LOG_LEVEL: {os.environ['LOG_LEVEL']}")
    print(f"LOG_DIR: {os.environ['LOG_DIR']}")
    print(f"DB_DIR: {os.environ['DB_DIR']}")

    # 解析命令行参数
    args = parse_args()

    # 如果未指定模式，默认使用Web模式
    if not args.mode:
        print("未指定运行模式，默认使用Web应用模式")
        # 创建默认的Web模式参数
        web_args = argparse.Namespace(
            host='0.0.0.0',
            port=5000,
            debug=True,
            log_level='INFO',
            log_dir='./logs',
            db_dir=None,
            with_crawler=True  # 确保默认启用爬虫管理器
        )
        run_web_mode(web_args)
    # 根据指定的模式运行
    elif args.mode == 'crawler':
        print("启动爬虫模式...")
        run_crawler_mode(args)
    elif args.mode == 'scheduler':
        print("启动调度器模式...")
        run_scheduler_mode(args)
    else:  # web模式
        print("启动Web应用模式...")
        run_web_mode(args)

if __name__ == '__main__':
    main()
