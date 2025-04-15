#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 主入口脚本

用法:
    python run.py crawler [--source SOURCE] [--days DAYS]
    python run.py scheduler [--interval INTERVAL]
    python run.py web [--host HOST] [--port PORT] [--debug]
    python run.py --help

选项:
    --help          显示帮助信息
    --config        指定配置文件路径
    --db-dir        指定数据库目录
    --log-level     指定日志级别

爬虫模式:
    --source        指定新闻来源（不指定则爬取所有来源）
    --days          爬取最近几天的新闻（默认为1天）
    --category      指定要爬取的特定分类（如：财经、股票、基金等）

调度器模式:
    --interval      调度间隔，单位为秒（默认3600秒）

Web应用模式:
    --host          Web服务器地址（默认0.0.0.0）
    --port          Web服务器端口（默认8000）
    --debug         启用调试模式
"""

import os
import sys
import time
import json
import logging
import logging.handlers
import argparse
import traceback
import configparser
import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import sqlite3
import warnings
import signal

# 添加当前目录到模块搜索路径
sys.path.insert(0, os.path.abspath('.'))

# 确保创建日志目录
os.makedirs("logs", exist_ok=True)

# 禁用第三方库日志
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("chardet").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# 创建全局logger对象
logger = logging.getLogger("run")

# 导入应用创建函数
from app import create_app

# 全局配置管理器
from app.utils.config import Config
config_manager = Config()

# 全局配置
def init_config():
    """初始化配置"""
    # 检查是否存在配置文件
    config_file = "./config.ini"
    config_loaded = False
    
    # 尝试加载配置文件
    if os.path.exists(config_file):
        try:
            config_manager.load_config()
            config_loaded = True
            logger.info("成功加载配置文件: %s", config_file)
        except Exception as e:
            logger.error("加载配置文件出错: %s", str(e))
    
    # 如果未加载配置文件，使用默认配置
    if not config_loaded:
        logger.info("未找到配置文件，使用默认配置")
    
    return config_manager.settings

def init_logging(args):
    """初始化日志设置"""
    # 检查是否已经初始化过日志
    if hasattr(init_logging, 'initialized') and init_logging.initialized:
        return logging.getLogger().level
        
    # 获取日志级别
    log_level_str = args.log_level if hasattr(args, 'log_level') else 'INFO'
    log_level = getattr(logging, log_level_str)
    
    # 创建主日志目录
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    try:
        os.makedirs(log_dir, exist_ok=True)
        print(f"主日志目录已创建: {log_dir}")
    except Exception as e:
        print(f"创建主日志目录失败: {str(e)}")
        log_dir = os.path.abspath('./logs')
        try:
            os.makedirs(log_dir, exist_ok=True)
            print(f"使用备用主日志目录: {log_dir}")
        except Exception as e2:
            print(f"创建备用主日志目录也失败: {str(e2)}")
            log_dir = os.getcwd()
            print(f"将使用当前工作目录: {log_dir}")
    
    # 使用日期创建日志文件名
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除已有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 重置所有已知的日志记录器，避免重复输出
    for logger_name in logging.root.manager.loggerDict:
        logger_obj = logging.getLogger(logger_name)
        for handler in logger_obj.handlers[:]:
            logger_obj.removeHandler(handler)
        # 确保子记录器使用父记录器的处理器
        logger_obj.propagate = True
    
    # 创建主日志文件处理器
    main_log_file = os.path.join(log_dir, f'finance_news_crawler_{current_date}.log')
    try:
        # 确保日志文件可写
        with open(main_log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n--- 日志开始于 {datetime.datetime.now()} ---\n")
            
        file_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
        ))
        root_logger.addHandler(file_handler)
        print(f"主日志文件处理器创建成功: {main_log_file}")
    except Exception as e:
        print(f"创建主日志文件处理器失败: {str(e)}")
    
    # 为每个爬虫源创建单独的日志文件夹和处理器
    crawler_sources = ['netease', 'ifeng', 'sina', 'eastmoney', 'cnstock']
    if hasattr(args, 'source') and args.source and args.source != 'all':
        crawler_sources = [args.source]
    
    for source in crawler_sources:
        try:
            # 创建爬虫源特定的日志目录
            source_log_dir = os.path.join(log_dir, source)
            os.makedirs(source_log_dir, exist_ok=True)
            
            # 创建爬虫源特定的日志文件
            source_log_file = os.path.join(source_log_dir, f'{source}_{current_date}.log')
            
            # 确保日志文件可写
            with open(source_log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n--- {source} 爬虫日志开始于 {datetime.datetime.now()} ---\n")
            
            # 创建爬虫源特定的日志处理器
            source_handler = logging.handlers.RotatingFileHandler(
                source_log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            source_handler.setLevel(log_level)
            source_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
            ))
            
            # 创建爬虫源特定的过滤器，只处理该爬虫的日志
            class SourceFilter(logging.Filter):
                def filter(self, record):
                    return record.name.endswith(source)
            
            source_filter = SourceFilter()
            source_handler.addFilter(source_filter)
            
            # 添加到根日志记录器
            root_logger.addHandler(source_handler)
            print(f"{source} 爬虫日志处理器创建成功: {source_log_file}")
        except Exception as e:
            print(f"为 {source} 创建日志处理器失败: {str(e)}")
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 尝试使用彩色日志
    try:
        import colorlog
        console_handler.setFormatter(colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        ))
    except ImportError:
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
        ))
    
    root_logger.addHandler(console_handler)
    
    # 设置特定模块的日志级别
    if hasattr(args, 'verbose') and args.verbose:
        logging.getLogger('app.crawlers').setLevel(logging.DEBUG)
    
    logger.info("设置日志级别: %s", log_level_str)
    logger.info("日志文件路径: %s", log_dir)
    
    # 标记日志已初始化
    init_logging.initialized = True
    
    return log_level

# 处理命令行参数
def parse_args():
    """解析命令行参数"""
    # 创建解析器
    parser = argparse.ArgumentParser(description='NewsLook 财经新闻爬虫系统')
    
    # 添加子命令
    subparsers = parser.add_subparsers(dest='mode', help='运行模式')
    
    # 爬虫模式
    crawler_parser = subparsers.add_parser('crawler', help='爬虫模式')
    crawler_parser.add_argument('--source', help='指定新闻来源（不指定则爬取所有来源）')
    crawler_parser.add_argument('--days', type=int, default=1, help='爬取最近几天的新闻（默认为1天）')
    crawler_parser.add_argument('--max-pages', type=int, default=3, help='每个分类最多爬取的页数（默认为3页）')
    crawler_parser.add_argument('--category', help='指定要爬取的特定分类（如：财经、股票、基金等）')
    crawler_parser.add_argument('--use-proxy', action='store_true', help='是否使用代理')
    crawler_parser.add_argument('--db-dir', help='数据库目录路径')
    crawler_parser.add_argument('--verbose', action='store_true', help='输出详细日志')
    crawler_parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='日志级别')
    crawler_parser.add_argument('--use-optimized', action='store_true', help='使用优化模式（多线程）')
    crawler_parser.add_argument('--max-news', type=int, default=50, help='每个源最多爬取的新闻数量（默认为50条）')
    
    # 调度器模式
    scheduler_parser = subparsers.add_parser('scheduler', help='调度器模式')
    scheduler_parser.add_argument('--interval', type=int, default=60, help='轮询间隔（分钟）')
    scheduler_parser.add_argument('--days', type=int, default=1, help='爬取最近几天的新闻（默认为1天）')
    scheduler_parser.add_argument('--max-pages', type=int, default=3, help='每个分类最多爬取的页数（默认为3页）')
    scheduler_parser.add_argument('--use-proxy', action='store_true', help='是否使用代理')
    scheduler_parser.add_argument('--db-dir', help='数据库目录路径')
    scheduler_parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='日志级别')
    scheduler_parser.add_argument('--use-optimized', action='store_true', help='使用优化模式（多线程）')
    scheduler_parser.add_argument('--max-news', type=int, default=50, help='每个源最多爬取的新闻数量（默认为50条）')
    
    # Web应用模式
    web_parser = subparsers.add_parser('web', help='Web应用模式')
    web_parser.add_argument('--host', default='0.0.0.0', help='监听地址（默认为0.0.0.0）')
    web_parser.add_argument('--port', type=int, default=8080, help='监听端口（默认为8080）')
    web_parser.add_argument('--debug', action='store_true', help='调试模式')
    web_parser.add_argument('--db-dir', help='数据库目录路径')
    web_parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='日志级别')
    
    # 解析参数
    args = parser.parse_args()
    
    # 如果没有指定模式，默认使用web模式
    if not args.mode:
        args.mode = 'web'
    
    return args

# 爬虫模式处理函数
def run_crawler(args):
    """运行爬虫模式"""
    try:
        # 初始化配置
        settings = init_config()
        
        # 清理旧日志文件
        if hasattr(args, 'clean_logs') and args.clean_logs:
            from app.utils.log_cleaner import LogCleaner
            # 这里出现了错误，因为LogCleaner类的构造函数不接受max_logs和retention_days参数
            # 需要查看LogCleaner类的定义，使用正确的参数名称
            # 可能应该使用max_files和days参数
            # 这里的问题是LogCleaner类的构造函数参数名称可能不正确
            # 根据注释，应该使用max_files和days参数，而不是max_logs和retention_days
            cleaner = LogCleaner(
                log_dir='logs',
                max_files=settings.get('max_logs', 10),
                days=settings.get('log_retention_days', 7)
            )
            time_cleaned, space_cleaned = cleaner.run_cleanup()
            logger.info("日志清理完成: 删除了 %d 个过期日志文件, 释放了 %.2f MB 空间", time_cleaned, space_cleaned)
        
        # 获取爬虫源
        source = args.source.lower() if hasattr(args, 'source') and args.source else None
        
        # 获取爬取天数和最大页数
        days = int(args.days) if hasattr(args, 'days') else 1
        max_pages = int(args.max_pages) if hasattr(args, 'max_pages') else 3
        
        # 获取分类
        category = args.category if hasattr(args, 'category') else None
        
        # 获取最大新闻数量
        max_news = int(args.max_news) if hasattr(args, 'max_news') else 50
        
        # 是否使用优化版爬虫
        use_optimized = hasattr(args, 'use_optimized') and args.use_optimized
        
        # 是否使用代理
        use_proxy = hasattr(args, 'use_proxy') and args.use_proxy
        
        # 打印爬虫配置信息
        logger.info("="*50)
        logger.info("爬虫配置信息:")
        logger.info("爬虫源: %s", source)
        logger.info("爬取天数: %d", days)
        logger.info("最大页数: %d", max_pages)
        logger.info("最大新闻数: %d", max_news)
        logger.info("分类: %s", category)
        logger.info("使用优化版: %s", use_optimized)
        logger.info("使用代理: %s", use_proxy)
        logger.info("详细模式: %s", args.verbose if hasattr(args, 'verbose') else False)
        logger.info("="*50)
        
        # 爬虫映射表
        crawler_map = {
            'sina': {
                'name': '新浪财经',
                'module': 'app.crawlers.sina',
                'class': 'SinaCrawler',
                'optimized_module': 'app.crawlers.optimized_sina',
                'optimized_class': 'OptimizedSinaCrawler'
            },
            '新浪财经': {
                'name': '新浪财经',
                'module': 'app.crawlers.sina',
                'class': 'SinaCrawler',
                'optimized_module': 'app.crawlers.optimized_sina',
                'optimized_class': 'OptimizedSinaCrawler'
            },
            '新浪': {
                'name': '新浪财经',
                'module': 'app.crawlers.sina',
                'class': 'SinaCrawler',
                'optimized_module': 'app.crawlers.optimized_sina',
                'optimized_class': 'OptimizedSinaCrawler'
            },
            'netease': {
                'name': '网易财经',
                'module': 'app.crawlers.netease',
                'class': 'NeteaseCrawler',
                'optimized_module': 'app.crawlers.optimized_netease',
                'optimized_class': 'OptimizedNeteaseCrawler'
            },
            '网易财经': {
                'name': '网易财经',
                'module': 'app.crawlers.netease',
                'class': 'NeteaseCrawler',
                'optimized_module': 'app.crawlers.optimized_netease',
                'optimized_class': 'OptimizedNeteaseCrawler'
            },
            '网易': {
                'name': '网易财经',
                'module': 'app.crawlers.netease',
                'class': 'NeteaseCrawler',
                'optimized_module': 'app.crawlers.optimized_netease',
                'optimized_class': 'OptimizedNeteaseCrawler'
            },
            'ifeng': {
                'name': '凤凰财经',
                'module': 'app.crawlers.ifeng',
                'class': 'IfengCrawler',
                'optimized_module': 'app.crawlers.ifeng',  # 已优化
                'optimized_class': 'IfengCrawler'
            },
            '凤凰财经': {
                'name': '凤凰财经',
                'module': 'app.crawlers.ifeng',
                'class': 'IfengCrawler',
                'optimized_module': 'app.crawlers.ifeng',  # 已优化
                'optimized_class': 'IfengCrawler'
            },
            '凤凰': {
                'name': '凤凰财经',
                'module': 'app.crawlers.ifeng',
                'class': 'IfengCrawler',
                'optimized_module': 'app.crawlers.ifeng',  # 已优化
                'optimized_class': 'IfengCrawler'
            },
            'eastmoney': {
                'name': '东方财富',
                'module': 'app.crawlers.eastmoney',
                'class': 'EastMoneyCrawler',
                'optimized_module': 'app.crawlers.eastmoney_simple',
                'optimized_class': 'EastmoneySimpleCrawler'
            },
            '东方财富': {
                'name': '东方财富',
                'module': 'app.crawlers.eastmoney',
                'class': 'EastMoneyCrawler',
                'optimized_module': 'app.crawlers.eastmoney_simple',
                'optimized_class': 'EastmoneySimpleCrawler'
            },
            '东财': {
                'name': '东方财富',
                'module': 'app.crawlers.eastmoney',
                'class': 'EastMoneyCrawler',
                'optimized_module': 'app.crawlers.eastmoney_simple',
                'optimized_class': 'EastmoneySimpleCrawler'
            }
        }
        
        # 如果是运行所有爬虫
        if source == 'all':
            logger.info("运行所有爬虫")
            
            # 获取所有唯一的爬虫名称
            unique_crawlers = set()
            for key, value in crawler_map.items():
                unique_crawlers.add(value['name'])
            
            # 运行每个爬虫
            for crawler_name in unique_crawlers:
                for key, value in crawler_map.items():
                    if value['name'] == crawler_name:
                        crawler_info = value
                        break
                
                logger.info(f"运行 {crawler_info['name']} 爬虫")
                try:
                    run_single_crawler(
                        crawler_info,
                        use_optimized,
                        days,
                        max_news,
                        max_pages,
                        category,
                        use_proxy
                    )
                except Exception as e:
                    logger.error(f"{crawler_info['name']} 爬虫运行出错: {str(e)}")
                    logger.error(traceback.format_exc())
                    # 继续运行下一个爬虫
                    continue
            
            logger.info("所有爬虫运行完成")
            return 0
        
        # 运行单个爬虫
        elif source in crawler_map:
            crawler_info = crawler_map[source]
            logger.info(f"运行 {crawler_info['name']} 爬虫")
            
            try:
                run_single_crawler(
                    crawler_info,
                    use_optimized,
                    days,
                    max_news,
                    max_pages,
                    category,
                    use_proxy
                )
                logger.info(f"{crawler_info['name']} 爬虫运行完成")
                return 0
            except Exception as e:
                logger.error(f"{crawler_info['name']} 爬虫运行出错: {str(e)}")
                logger.error(traceback.format_exc())
                return 1
        else:
            logger.error(f"未知的爬虫源: {source}")
            logger.info("可用的爬虫源包括:")
            unique_sources = set()
            for key, value in crawler_map.items():
                if key == value['name'].lower() or key == value['name']:
                    unique_sources.add(key)
            
            for source_name in sorted(unique_sources):
                logger.info(f"- {source_name}")
            
            return 1
        
    except ImportError as e:
        logger.error("导入爬虫模块失败: %s", str(e))
        return 1
    except ValueError as e:
        logger.error("参数错误: %s", str(e))
        return 1
    except Exception as e:
        logger.error("爬虫运行出错: %s", str(e))
        logger.error(traceback.format_exc())
        return 1

def run_single_crawler(crawler_info, use_optimized, days, max_news, max_pages, category, use_proxy):
    """运行单个爬虫"""
    # 选择模块和类
    if use_optimized:
        module_name = crawler_info['optimized_module']
        class_name = crawler_info['optimized_class']
        logger.info(f"使用优化版 {crawler_info['name']} 爬虫")
    else:
        module_name = crawler_info['module']
        class_name = crawler_info['class']
        logger.info(f"使用标准版 {crawler_info['name']} 爬虫")
    
    # 导入模块
    logger.info(f"正在导入 {crawler_info['name']} 爬虫模块...")
    print(f"正在导入 {crawler_info['name']} 爬虫模块...")
    
    try:
        module = __import__(module_name, fromlist=[class_name])
        crawler_class = getattr(module, class_name)
        
        logger.info(f"{crawler_info['name']} 爬虫模块导入成功")
        print(f"{crawler_info['name']} 爬虫模块导入成功")
        
        # 初始化爬虫
        logger.info("正在初始化爬虫...")
        print("正在初始化爬虫...")
        
        # 获取配置中的数据库目录
        from app.config import get_settings
        settings = get_settings()
        db_dir = settings.get('DB_DIR')
        
        # 确保数据库目录存在
        import os
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"创建数据库目录: {db_dir}")
        
        # 设置数据库路径
        db_path = os.path.join(db_dir, f"{crawler_info['name']}.db")
        logger.info(f"使用数据库路径: {db_path}")
        
        # 检查爬虫类的初始化参数
        import inspect
        init_sig = inspect.signature(crawler_class.__init__)
        init_params = init_sig.parameters
        
        # 准备初始化参数
        init_args = {}
        
        # 检查不同爬虫类支持的参数
        if 'config' in init_params:
            # 新浪爬虫使用config参数
            init_args['config'] = {
                'db_path': db_path,
                'use_proxy': use_proxy,
                'use_source_db': True
            }
        else:
            # 其他爬虫直接使用参数
            if 'db_path' in init_params:
                init_args['db_path'] = db_path
            if 'use_source_db' in init_params:
                init_args['use_source_db'] = True
            if 'use_proxy' in init_params:
                init_args['use_proxy'] = use_proxy
        
        # 创建爬虫实例
        crawler = crawler_class(**init_args)
        
        logger.info("爬虫初始化成功")
        print("爬虫初始化成功")
        
        # 开始爬取
        logger.info(f"开始爬取，天数: {days}, 最大新闻数: {max_news}, 最大页数: {max_pages}, 分类: {category}")
        print(f"开始爬取，天数: {days}, 最大新闻数: {max_news}, 最大页数: {max_pages}, 分类: {category}")
        
        # 根据爬虫类型调用不同的爬取方法
        if hasattr(crawler, 'crawl'):
            # 检查crawl方法的参数
            import inspect
            sig = inspect.signature(crawler.crawl)
            params = sig.parameters
            
            # 准备参数
            crawl_args = {}
            if 'days' in params:
                crawl_args['days'] = days
            if 'max_news' in params:
                crawl_args['max_news'] = max_news
            if 'max_pages' in params:
                crawl_args['max_pages'] = max_pages
            if 'category' in params:
                crawl_args['category'] = category
            
            # 调用爬取方法
            crawler.crawl(**crawl_args)
        else:
            logger.error(f"{crawler_info['name']} 爬虫没有 crawl 方法")
            raise AttributeError(f"{crawler_info['name']} 爬虫没有 crawl 方法")
        
        logger.info("爬取完成")
        print("爬取完成")
        
    except ImportError as e:
        logger.error(f"导入 {crawler_info['name']} 爬虫模块失败: {str(e)}")
        print(f"导入 {crawler_info['name']} 爬虫模块失败: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"{crawler_info['name']} 爬虫运行出错: {str(e)}")
        print(f"{crawler_info['name']} 爬虫运行出错: {str(e)}")
        logger.error(traceback.format_exc())
        print(traceback.format_exc())
        raise

def run_scheduler(args):
    """运行调度器模式"""
    # 初始化配置
    settings = init_config()
    
    # 导入调度器模块
    try:
        logger.info("导入调度器模块...")
        import time
        import threading
        from app.crawlers.sina import SinaCrawler
        logger.info("成功导入调度器模块")
    except ImportError as e:
        logger.error("导入调度器模块失败: %s", str(e))
        sys.exit(1)
    
    # 创建爬虫实例
    try:
        crawler = SinaCrawler()
        logger.info("爬虫初始化成功")
    except Exception as e:
        logger.error("初始化爬虫失败: %s", str(e))
        traceback.print_exc()
        sys.exit(1)
    
    # 定义爬虫任务
    def crawl_task():
        logger.info("开始定时爬取任务")
        try:
            crawler.crawl(days=1)
            logger.info("定时爬取任务完成")
        except Exception as e:
            logger.error("定时爬取任务失败: %s", str(e))
            traceback.print_exc()
    
    # 定义调度器
    def scheduler():
        logger.info("调度器已启动，间隔: %d 秒", args.interval)
        while True:
            crawl_task()
            logger.info("等待下一次调度，间隔: %d 秒", args.interval)
            time.sleep(args.interval)
    
    # 启动调度器
    try:
        scheduler_thread = threading.Thread(target=scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        logger.info("调度器已在后台运行，按 Ctrl+C 停止")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到停止信号，调度器已停止")
    except ImportError as e:
        logger.error("导入模块失败: %s", str(e))
    except ValueError as e:
        logger.error("参数错误: %s", str(e))
    except Exception as e:
        logger.error("调度器运行出错: %s", str(e))
        traceback.print_exc()

def run_web(args):
    """运行Web应用模式"""
    # 导入必要的模块
    import os
    
    # 初始化配置
    settings = init_config()
    
    # 确保数据库目录存在
    db_dir = settings.get('DB_DIR')
    if not db_dir:
        db_dir = os.path.join(os.path.abspath('.'), 'data', 'db')
        settings['DB_DIR'] = db_dir
        logger.warning(f"DB_DIR未设置，使用默认路径: {db_dir}")
    
    # 确保目录存在
    os.makedirs(db_dir, exist_ok=True)
    logger.info(f"使用数据库目录: {db_dir}")
    
    # 设置环境变量，确保其他模块能够访问
    os.environ['DB_DIR'] = db_dir
    
    # 导入数据库模块
    try:
        from app.utils.database import NewsDatabase
        
        # 尝试多个可能的数据库路径
        db = None
        possible_db_paths = [
            os.path.join(db_dir, 'finance_news.db'),
            os.path.join(db_dir, '网易财经.db'),
            os.path.join(db_dir, '新浪财经.db'),
            os.path.join(db_dir, '东方财富.db'),
            os.path.join(os.path.abspath('.'), 'data', 'db', 'finance_news.db'),
            os.path.join(os.path.abspath('.'), 'db', 'finance_news.db')
        ]
        
        for db_path in possible_db_paths:
            if os.path.exists(db_path):
                logger.info(f"找到数据库文件: {db_path}")
                try:
                    db = NewsDatabase(db_path=db_path)
                    logger.info(f"成功连接到数据库: {db_path}")
                    break
                except Exception as e:
                    logger.error(f"连接数据库 {db_path} 失败: {str(e)}")
        
        if db is None:
            logger.warning("未找到有效的数据库文件，将尝试使用默认路径")
            db = NewsDatabase()
            logger.info(f"使用默认数据库路径: {db.db_path}")
            
    except ImportError as e:
        logger.error(f"导入数据库模块失败: {str(e)}")
        db = None
    except Exception as e:
        logger.error(f"数据库连接初始化失败: {str(e)}")
        traceback.print_exc()
        db = None
    
    # 创建Flask应用
    try:
        logger.info("使用create_app函数创建Flask应用...")
        app = create_app()
        
        # 设置密钥，用于session和flash消息
        app.secret_key = 'newslook_secret_key'  # 在生产环境中应使用更安全的密钥
        
        # 增强错误处理
        app.config['TRAP_HTTP_EXCEPTIONS'] = True
        app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = True
        
        # 如果设置了调试模式，启用更多调试功能
        if getattr(args, 'debug', False):
            app.config['EXPLAIN_TEMPLATE_LOADING'] = True
            app.config['TEMPLATES_AUTO_RELOAD'] = True
        
        # 把数据库实例保存到应用上下文中
        if db:
            app.db = db
            
        # 启动Web服务器
        port = getattr(args, 'port', 8080)
        debug = getattr(args, 'debug', False)
        logger.info(f"启动Web服务器，端口: {port}, 调试模式: {debug}")
        app.run(host='0.0.0.0', port=port, debug=debug)
    except Exception as e:
        logger.error(f"运行Web应用失败: {str(e)}")
        traceback.print_exc()

def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_args()
        
        # 初始化日志
        init_logging(args)
        
        # 记录运行模式
        logger.info("运行模式: %s", args.mode)
        
        # 根据模式运行相应的功能
        if args.mode == 'crawler':
            run_crawler(args)
        elif args.mode == 'scheduler':
            run_scheduler(args)
        elif args.mode == 'web':
            run_web(args)
        else:
            logger.error("未知的运行模式: %s", args.mode)
            sys.exit(1)
            
    except Exception as e:
        logger.error("程序运行出错: %s", str(e))
        traceback.print_exc()
        sys.exit(1)

# 程序入口
if __name__ == "__main__":
    main() 