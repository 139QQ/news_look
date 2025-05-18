#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 财经新闻爬虫系统 - 统一入口脚本
支持三种运行模式：爬虫模式、调度器模式和Web应用模式
"""

import os
import sys
import time
import argparse
import logging
import traceback
from datetime import datetime
import asyncio

# 设置当前工作目录为脚本所在目录
CWD = os.path.dirname(os.path.abspath(__file__))
os.chdir(CWD)

# 添加调试选项
DEBUG_MODE = True

# 添加强制同步模式
FORCE_SYNC_MODE = False

# 添加爬虫工厂支持
from app.crawlers.factory import CrawlerFactory
from app.crawlers.strategies import STRATEGY_MAP
from app.utils.logger import get_logger, configure_logger, fix_duplicate_logging
from app.tasks.scheduler import SchedulerManager

# 直接导入增强爬虫，确保该类被正确加载
from app.crawlers.enhanced_crawler import EnhancedCrawler

# 设置工作目录为脚本所在目录，确保相对路径正确
CWD = os.path.dirname(os.path.abspath(__file__))
os.chdir(CWD)

# 确保日志目录存在
os.makedirs("logs", exist_ok=True)

# 配置根日志器
configure_logger(name="root", level=logging.INFO)

# 修复日志重复输出问题
fix_duplicate_logging()

# 获取logger
logger = get_logger('NewsLook')

# 如果是调试模式，输出一些系统信息
if DEBUG_MODE:
    logger.info("=== NewsLook 财经新闻爬虫系统 (调试模式) ===")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"系统路径: {sys.path}")
    logger.info(f"增强爬虫类: {EnhancedCrawler}")
else:
    logger.info("=== NewsLook 财经新闻爬虫系统启动 ===")
    logger.info(f"运行路径: {CWD}")
    logger.info(f"Python版本: {sys.version}")

def setup_argparser():
    """设置命令行参数解析器"""
    parser = argparse.ArgumentParser(description='NewsLook 财经新闻爬虫系统')
    subparsers = parser.add_subparsers(dest='mode', help='运行模式')
    
    # 爬虫模式
    crawler_parser = subparsers.add_parser('crawler', help='爬虫模式')
    crawler_parser.add_argument('-s', '--source', type=str, choices=STRATEGY_MAP.keys(), help='指定新闻源')
    crawler_parser.add_argument('-a', '--all', action='store_true', help='爬取所有支持的新闻源')
    crawler_parser.add_argument('-d', '--days', type=int, default=1, help='爬取天数 (默认: 1)')
    crawler_parser.add_argument('-m', '--max', type=int, default=100, help='每个源最大爬取新闻数量 (默认: 100)')
    crawler_parser.add_argument('-c', '--category', type=str, help='指定爬取分类，多个分类用逗号分隔')
    crawler_parser.add_argument('--db-dir', type=str, default='data', help='数据库目录 (默认: data)')
    crawler_parser.add_argument('--async', dest='async_mode', action='store_true', default=True, help='使用异步模式 (默认)')
    crawler_parser.add_argument('--sync', dest='async_mode', action='store_false', help='使用同步模式')
    crawler_parser.add_argument('--config-dir', type=str, help='配置文件目录')
    crawler_parser.add_argument('--proxy', action='store_true', help='使用代理')
    crawler_parser.add_argument('--workers', type=int, default=5, help='工作线程数 (默认: 5)')
    crawler_parser.add_argument('--timeout', type=int, default=30, help='请求超时时间，单位秒 (默认: 30)')
    crawler_parser.add_argument('--enhanced', action='store_true', help='使用增强型爬虫')
    crawler_parser.add_argument('--concurrency', type=int, default=10, help='最大并发请求数 (默认: 10)')
    crawler_parser.add_argument('--domain-concurrency', type=int, default=5, help='每个域名的最大并发请求数 (默认: 5)')
    crawler_parser.add_argument('--domain-delay', type=float, default=0, help='同域名请求间的延迟(秒) (默认: 0)')
    crawler_parser.add_argument('--list', action='store_true', help='列出支持的新闻源')
    
    # 调度器模式
    scheduler_parser = subparsers.add_parser('scheduler', help='调度器模式')
    scheduler_parser.add_argument('-c', '--config', type=str, default='app/config/scheduler.json', help='调度配置文件路径')
    scheduler_parser.add_argument('-i', '--interval', type=int, default=60, help='调度间隔（分钟）')
    scheduler_parser.add_argument('-l', '--log-dir', type=str, default='logs', help='日志目录')
    scheduler_parser.add_argument('-d', '--daemon', action='store_true', help='作为守护进程运行')
    
    # Web应用模式
    web_parser = subparsers.add_parser('web', help='Web应用模式')
    web_parser.add_argument('-H', '--host', type=str, default='127.0.0.1', help='监听主机')
    web_parser.add_argument('-p', '--port', type=int, default=5000, help='监听端口')
    web_parser.add_argument('-d', '--debug', action='store_true', help='调试模式')
    web_parser.add_argument('--db-dir', type=str, help='数据库目录')
    web_parser.add_argument('--log-file', type=str, default='logs/webserver.log', help='日志文件')
    
    return parser

def run_crawler_mode(args):
    """运行爬虫模式"""
    # 创建爬虫工厂
    factory = CrawlerFactory()
    
    # 如果是列出支持的新闻源
    if args.list:
        sources = factory.get_supported_sources()
        logger.info(f"支持的新闻源:")
        for source in sources:
            logger.info(f"- {source}")
        return
    
    # 确保数据库目录存在
    db_dir = args.db_dir or os.path.join(CWD, 'data', 'db')
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"已创建数据库目录: {db_dir}")
    
    # 确保数据库路径是绝对路径
    db_dir = os.path.abspath(db_dir)
    logger.info(f"使用数据库目录: {db_dir}")
        
    # 准备爬虫参数
    crawler_options = {
        'async_mode': args.async_mode,
        'use_proxy': args.proxy,
        'request_timeout': args.timeout,
        'max_concurrency': args.concurrency,
        'domain_concurrency': args.domain_concurrency,
        'domain_delay': args.domain_delay,
        'adaptive_speed': True,
        'intelligent_retry': True,
        'monitor_performance': True
    }
    
    # 添加调试信息 
    logger.info(f"爬虫选项: {crawler_options}")
    if args.enhanced:
        logger.info("使用增强型爬虫模式")
    
    # 根据用户指定的新闻源创建爬虫
    if args.all:
        # 爬取所有支持的新闻源
        crawlers = factory.create_all_crawlers(db_dir, crawler_options)
        logger.info(f"将爬取所有支持的新闻源: {', '.join(STRATEGY_MAP.keys())}")
        
        for source, crawler in crawlers.items():
            try:
                # 分割分类字符串
                categories = args.category.split(',') if args.category else None
                
                # 使用异步或同步方法爬取
                if args.async_mode and hasattr(crawler.http_client, 'session'):
                    # 使用正确的异步调用方法
                    try:
                        # Python 3.7+推荐使用asyncio.run
                        crawl_result = asyncio.run(
                            crawler.crawl_async(days=args.days, max_news=args.max, category=categories)
                        )
                    except RuntimeError as e:
                        # 在某些环境下，如果已有事件循环，asyncio.run会失败
                        # 这时候回退到传统方法
                        logger.warning(f"使用asyncio.run失败: {str(e)}，回退到传统方法")
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            crawl_result = loop.run_until_complete(
                                crawler.crawl_async(days=args.days, max_news=args.max, category=categories)
                            )
                        finally:
                            loop.close()
                    
                    logger.info(f"爬取结果 ({source}): {crawl_result.get('message', '')}")
                else:
                    # 使用同步方法
                    crawl_result = crawler.crawl(days=args.days, max_news=args.max, category=categories)
                    logger.info(f"同步爬取完成 ({source})，获取到 {len(crawl_result)} 篇文章")
            except Exception as e:
                logger.error(f"爬取 {source} 失败: {str(e)}")
                logger.debug(traceback.format_exc())
    elif args.source:
        try:
            # 准备数据库路径
            db_path = os.path.join(db_dir, f"{args.source}.db")
            logger.info(f"数据库路径: {db_path}")
            
            # 特殊处理东方财富
            if args.source == '东方财富':
                logger.info("使用直接导入的东方财富爬虫")
                try:
                    from app.crawlers.eastmoney import EastMoneyCrawler
                    crawler = EastMoneyCrawler(db_path=db_path, use_proxy=args.proxy)
                    
                    # 爬取新闻
                    news_list = crawler.crawl(days=args.days, max_news=args.max)
                    logger.info(f"成功爬取 {len(news_list) if news_list else 0} 条新闻")
                    return
                except Exception as e:
                    logger.error(f"使用东方财富爬虫失败: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # 特殊处理新浪财经
            elif args.source == '新浪财经':
                logger.info("使用直接导入的新浪财经爬虫")
                try:
                    from app.crawlers.sina import SinaCrawler
                    crawler = SinaCrawler(db_path=db_path, use_proxy=args.proxy)
                    
                    # 爬取新闻
                    categories = args.category.split(',') if args.category else None
                    news_list = crawler.crawl(days=args.days, max_pages=args.max, category=categories)
                    logger.info(f"成功爬取新浪财经新闻，获取到 {len(news_list)} 篇文章")
                    return
                except Exception as e:
                    logger.error(f"使用新浪财经爬虫失败: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # 特殊处理网易财经
            elif args.source == '网易财经':
                logger.info("使用直接导入的网易财经爬虫")
                try:
                    from app.crawlers.netease import NeteaseCrawler
                    crawler = NeteaseCrawler(db_path=db_path, use_proxy=args.proxy)
                    
                    # 爬取新闻
                    crawler.crawl(days=args.days, max_news=args.max)
                    logger.info(f"成功爬取网易财经新闻")
                    return
                except Exception as e:
                    logger.error(f"使用网易财经爬虫失败: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # 特殊处理凤凰财经
            elif args.source == '凤凰财经':
                logger.info("使用直接导入的凤凰财经爬虫")
                try:
                    from app.crawlers.ifeng import IfengCrawler
                    crawler = IfengCrawler(db_path=db_path, use_proxy=args.proxy)
                    
                    # 爬取新闻，不向crawl传递category参数
                    crawler.crawl(days=args.days, max_news=args.max)
                    logger.info(f"成功爬取凤凰财经新闻")
                    return
                except Exception as e:
                    logger.error(f"使用凤凰财经爬虫失败: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # 确定是否使用增强型爬虫
            crawler_options['use_enhanced'] = args.enhanced
            
            # 爬取指定的新闻源
            if args.enhanced:
                logger.info(f"正在创建增强型爬虫: {args.source}")
                crawler = factory.create_enhanced_crawler(args.source, db_path, crawler_options)
                logger.info(f"使用增强型爬虫爬取: {args.source}")
                logger.info(f"爬虫类型: {type(crawler).__name__}")
                logger.info(f"爬虫属性: {dir(crawler)}")
            else:
                logger.info(f"正在创建标准爬虫: {args.source}")
                crawler = factory.create_crawler(args.source, db_path=db_path, **crawler_options)
                logger.info(f"爬虫类型: {type(crawler).__name__}")
            
            if not crawler:
                logger.error(f"不支持的新闻源: {args.source}")
                logger.info(f"支持的新闻源: {', '.join(STRATEGY_MAP.keys())}")
                return
                
            logger.info(f"将爬取新闻源: {args.source}")
            
            # 分割分类字符串
            categories = args.category.split(',') if args.category else None
            
            # 使用正确的方法爬取
            if args.enhanced or (args.async_mode and hasattr(crawler.http_client, 'session')):
                # 添加调试信息
                logger.info(f"准备使用异步方法爬取，爬虫类: {type(crawler).__name__}")
                if hasattr(crawler, 'crawl_async'):
                    logger.info("爬虫支持异步爬取方法")
                    
                    # 使用现代化的asyncio.run方法运行异步代码
                    try:
                        # Python 3.7+推荐使用asyncio.run
                        logger.info("开始使用asyncio.run执行异步爬取")
                        crawl_result = asyncio.run(
                            crawler.crawl_async(days=args.days, max_news=args.max, category=categories)
                        )
                        logger.info("异步爬取完成")
                    except RuntimeError as e:
                        # 在某些环境下，如果已有事件循环，asyncio.run会失败
                        # 这时候回退到传统方法
                        logger.warning(f"使用asyncio.run失败: {str(e)}，回退到传统方法")
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            logger.info("使用传统事件循环方法执行异步爬取")
                            crawl_result = loop.run_until_complete(
                                crawler.crawl_async(days=args.days, max_news=args.max, category=categories)
                            )
                            logger.info("异步爬取完成")
                        finally:
                            loop.close()
                    except Exception as e:
                        logger.error(f"异步爬取时发生错误: {str(e)}")
                        logger.error(traceback.format_exc())
                        # 尝试使用同步方法作为备选
                        logger.info("尝试使用同步方法作为备选")
                        crawl_result = crawler.crawl(days=args.days, max_news=args.max, category=categories)
                            
                    logger.info(f"爬取结果: {crawl_result.get('message', '')}")
                else:
                    logger.error("爬虫不支持异步爬取方法，回退到同步爬取")
                    crawl_result = crawler.crawl(days=args.days, max_news=args.max, category=categories)
                    logger.info(f"同步爬取完成，获取到 {len(crawl_result) if isinstance(crawl_result, list) else 0} 篇文章")
            else:
                # 使用同步方法
                logger.info(f"准备使用同步方法爬取，爬虫类: {type(crawler).__name__}")
                if hasattr(crawler, 'crawl'):
                    logger.info("爬虫支持同步爬取方法")
                else:
                    logger.error("爬虫不支持同步爬取方法")
                
                crawl_result = crawler.crawl(days=args.days, max_news=args.max, category=categories)
                logger.info(f"同步爬取完成，获取到 {len(crawl_result)} 篇文章")
        except Exception as e:
            logger.error(f"爬取 {args.source} 失败: {str(e)}")
            logger.error(traceback.format_exc())
    else:
        logger.error("请使用 -s/--source 指定新闻源或使用 -a/--all 爬取所有支持的新闻源")

def run_scheduler_mode(args):
    """运行调度器模式"""
    try:
        # 创建日志目录
        if not os.path.exists(args.log_dir):
            os.makedirs(args.log_dir, exist_ok=True)
        
        # 准备配置
        config = None
        if args.config and os.path.exists(args.config):
            import json
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        # 初始化调度器
        scheduler = SchedulerManager(config=config)
        
        # 启动调度器
        if args.daemon:
            logger.info("作为守护进程启动调度器")
            try:
                import daemon
                with daemon.DaemonContext():
                    # 使用start_scheduler函数替代start方法
                    from app.tasks.scheduler import start_scheduler
                    scheduler_obj = start_scheduler(config_path=args.config)
                    # 保持主线程运行
                    while True:
                        time.sleep(60)
            except ImportError:
                logger.error("daemon模块未安装，无法以守护进程模式运行")
                logger.info("请使用pip install python-daemon安装所需模块")
                from app.tasks.scheduler import start_scheduler
                start_scheduler(config_path=args.config)
                # 保持主线程运行
                while True:
                    time.sleep(60)
        else:
            logger.info("启动调度器")
            from app.tasks.scheduler import start_scheduler
            start_scheduler(config_path=args.config)
            # 保持主线程运行
            while True:
                time.sleep(60)
            
        return 0
    except Exception as e:
        logger.error(f"调度器启动失败: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

def run_web_mode(args):
    """运行Web应用模式"""
    try:
        from app.web import create_app
        
        # 设置默认数据库目录
        db_dir = args.db_dir if hasattr(args, 'db_dir') and args.db_dir else os.path.join(CWD, 'data', 'db')
        
        # 设置环境变量
        os.environ['DB_DIR'] = db_dir
        
        # 创建日志目录
        log_dir = os.path.dirname(args.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 配置Web应用的日志
        web_logger = logging.getLogger('web')
        web_logger.setLevel(logging.INFO)
        
        # 文件处理器
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s'))
        web_logger.addHandler(file_handler)
        
        # 尝试初始化爬虫管理器
        crawler_manager = None
        try:
            from app.crawlers.manager import CrawlerManager
            crawler_manager = CrawlerManager()
            logger.info("已成功初始化爬虫管理器")
        except Exception as e:
            logger.warning(f"初始化爬虫管理器失败: {e}")
        
        # 配置Web应用
        web_config = {
            'DB_DIR': db_dir,  # 使用处理过的db_dir
            'CRAWLER_MANAGER': crawler_manager,
            'DEBUG': args.debug,
            'secret_key': os.environ.get('SECRET_KEY', os.urandom(24).hex())
        }
        
        # 创建Flask应用
        app = create_app(web_config)
        
        # 指定模板目录
        template_folder = os.path.join(CWD, 'app', 'web', 'templates')
        if os.path.exists(template_folder):
            app.template_folder = template_folder
            logging.info(f"设置模板目录为: {template_folder}")
        
        # 开启调试模式
        if args.debug:
            app.debug = True
            
        # 启动Web服务器
        logger.info(f"启动Web服务器: {args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=args.debug)
        
        return 0
    except Exception as e:
        logger.error(f"Web应用启动失败: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

def parse_crawler_args(parser):
    """解析爬虫模式的命令行参数"""
    crawler_group = parser.add_argument_group('爬虫参数')
    source_group = crawler_group.add_mutually_exclusive_group()
    source_group.add_argument('-s', '--source', type=str, help='要爬取的新闻源')
    source_group.add_argument('-a', '--all', action='store_true', help='爬取所有支持的新闻源')
    crawler_group.add_argument('-d', '--days', type=int, default=1, help='爬取最近几天的新闻')
    crawler_group.add_argument('-m', '--max', type=int, help='每个源最多爬取的新闻数量')
    crawler_group.add_argument('-c', '--category', type=str, help='要爬取的新闻分类')
    crawler_group.add_argument('--proxy', action='store_true', help='是否使用代理')
    crawler_group.add_argument('--async-mode', action='store_true', help='是否使用异步模式')
    crawler_group.add_argument('--enhanced', action='store_true', help='是否使用增强型异步爬虫')
    crawler_group.add_argument('--concurrency', type=int, default=10, help='最大并发请求数')
    crawler_group.add_argument('--domain-concurrency', type=int, default=5, help='每个域名的最大并发请求数')
    crawler_group.add_argument('--domain-delay', type=float, default=0, help='同域名请求间的延迟(秒)')
    crawler_group.add_argument('--list', action='store_true', help='列出支持的新闻源')
    return crawler_group

def main():
    """主函数"""
    # 解析命令行参数
    parser = setup_argparser()
    args = parser.parse_args()
    
    # 打印完整的命令行参数
    logger.info(f"命令行参数: {vars(args)}")
    
    # 根据运行模式选择相应的处理函数
    if args.mode == 'crawler':
        return run_crawler_mode(args)
    elif args.mode == 'scheduler':
        return run_scheduler_mode(args)
    elif args.mode == 'web':
        return run_web_mode(args)
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    try:
        # 记录启动信息
        logger.info("=== NewsLook 财经新闻爬虫系统启动 ===")
        logger.info(f"运行路径: {os.path.abspath('.')}")
        logger.info(f"Python版本: {sys.version}")
        
        # 运行主程序
        start_time = time.time()
        exit_code = main()
        elapsed_time = time.time() - start_time
        
        # 记录结束信息
        logger.info(f"程序运行结束，耗时: {elapsed_time:.2f}秒，退出代码: {exit_code}")
        
        # 退出
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("用户中断，程序退出")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序异常: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)