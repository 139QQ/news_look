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

调度器模式:
    --interval      调度间隔，单位为秒（默认3600秒）

Web应用模式:
    --host          Web服务器地址（默认0.0.0.0）
    --port          Web服务器端口（默认8000）
    --debug         启用调试模式
"""

import os
import sys
import logging

# 确保创建日志目录
os.makedirs("logs", exist_ok=True)

# 禁用所有默认处理器
if not hasattr(logging.root, '_initialized'):
    # 移除所有默认处理器
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # 禁用第三方库日志
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("chardet").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    
    # 设置Flask的日志级别为WARNING，减少路由日志输出
    logging.getLogger("flask").setLevel(logging.WARNING)
    
    # 标记root logger已初始化
    logging.root._initialized = True

# 使用定制日志模块前必须先禁用默认日志
from newslook.config import config_manager, create_default_config
from newslook.utils.logger import get_logger, configure_logger

# 创建全局logger对象，确保在函数前定义以避免未定义错误
logger = get_logger("run")

# 全局配置
def init_config():
    # 检查是否存在配置文件
    config_file = "./config.ini"
    config_loaded = False
    
    # 尝试加载配置文件
    if os.path.exists(config_file):
        try:
            # 修正：不传递多余的参数
            config_manager.load_config(config_file)
            config_loaded = True
        except Exception as e:
            print(f"加载配置文件出错: {e}")
    
    # 如果未加载配置文件，使用默认配置
    if not config_loaded:
        print("未找到配置文件，使用默认配置")
        create_default_config()
    
    # 初始化日志记录器 - 确保只调用一次
    configure_logger()
    
    return config_manager.get_all_settings()

# 处理命令行参数
def parse_args():
    """解析命令行参数"""
    import argparse
    
    # 创建解析器
    parser = argparse.ArgumentParser(description='NewsLook 财经新闻爬虫系统')
    
    # 添加子命令
    subparsers = parser.add_subparsers(dest='mode', help='运行模式')
    
    # 爬虫模式
    crawler_parser = subparsers.add_parser('crawler', help='爬虫模式')
    crawler_parser.add_argument('--source', '-s', help='指定新闻来源')
    crawler_parser.add_argument('--days', '-d', type=int, default=1, help='爬取最近几天的新闻')
    
    # 调度器模式
    scheduler_parser = subparsers.add_parser('scheduler', help='调度器模式')
    scheduler_parser.add_argument('--interval', '-i', type=int, default=3600, help='调度间隔（秒）')
    
    # Web应用模式
    web_parser = subparsers.add_parser('web', help='Web应用模式')
    web_parser.add_argument('--host', default='0.0.0.0', help='Web服务器地址')
    web_parser.add_argument('--port', '-p', type=int, default=8000, help='Web服务器端口')
    web_parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    # 全局选项
    parser.add_argument('--config', '-c', help='指定配置文件路径')
    parser.add_argument('--db-dir', help='指定数据库目录')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='设置日志级别')
    
    # 解析参数
    args = parser.parse_args()
    
    # 检查是否指定了模式
    if not args.mode:
        parser.print_help()
        sys.exit(1)
    
    return args

# 爬虫模式处理函数
def run_crawler(args):
    """运行爬虫模式"""
    # 初始化配置
    settings = init_config()
    
    # 如果指定了数据库目录，覆盖配置
    if args.db_dir:
        logger.info(f"使用指定的数据库目录: {args.db_dir}")
        settings['DB_DIR'] = args.db_dir
        config_manager.update_settings('DB_DIR', args.db_dir)
        os.environ['DB_DIR'] = args.db_dir
    
    # 导入爬虫模块
    try:
        from newslook.crawlers.manager import CrawlerManager
    except ImportError:
        logger.error("无法导入爬虫模块。请检查是否安装了所有依赖。")
        sys.exit(1)
    
    # 创建爬虫管理器
    crawler_manager = CrawlerManager(settings)
    
    # 获取爬虫列表
    # 修正：CrawlerManager没有get_crawler_list方法，使用正确的方法或属性
    try:
        # 尝试使用get_crawlers方法
        crawler_list = crawler_manager.get_crawlers()
    except AttributeError:
        # 如果get_crawlers不存在，尝试使用crawlers属性
        try:
            crawler_list = crawler_manager.crawlers
        except AttributeError:
            # 如果crawlers属性不存在，尝试使用其它可能的属性或方法
            try:
                # 可能有类似的方法
                crawler_list = crawler_manager.list_crawlers()
            except AttributeError:
                # 如果所有尝试都失败，记录错误并退出
                logger.error("无法获取爬虫列表，CrawlerManager类没有正确的方法或属性")
                sys.exit(1)
    
    if not crawler_list:
        logger.error("未找到可用的爬虫")
        sys.exit(1)
    
    # 如果指定了特定来源，过滤爬虫列表
    if args.source:
        filtered_crawlers = [c for c in crawler_list if c.source.lower() == args.source.lower()]
        if not filtered_crawlers:
            logger.error(f"未找到来源名称为 '{args.source}' 的爬虫")
            logger.info(f"可用的爬虫来源: {', '.join([c.source for c in crawler_list])}")
            sys.exit(1)
        crawler_list = filtered_crawlers
    
    # 运行爬虫
    for crawler in crawler_list:
        logger.info(f"开始爬取 {crawler.source} 的新闻")
        try:
            crawler.crawl(days=args.days)
        except Exception as e:
            logger.error(f"爬取 {crawler.source} 失败: {e}")
    
    logger.info("爬虫运行完成")

# 调度器模式处理函数
def run_scheduler(args):
    """运行调度器模式"""
    # 初始化配置
    settings = init_config()
    
    # 如果指定了数据库目录，覆盖配置
    if args.db_dir:
        logger.info(f"使用指定的数据库目录: {args.db_dir}")
        settings['DB_DIR'] = args.db_dir
        config_manager.update_settings('DB_DIR', args.db_dir)
        os.environ['DB_DIR'] = args.db_dir
    
    # 导入调度器模块
    try:
        from newslook.scheduler import Scheduler
    except ImportError:
        logger.error("无法导入调度器模块。请检查是否安装了所有依赖。")
        sys.exit(1)
    
    # 创建并运行调度器
    logger.info(f"启动调度器，间隔: {args.interval} 秒")
    scheduler = Scheduler(interval=args.interval)
    scheduler.start()

# Web应用模式处理函数
def run_web(args):
    """运行Web应用模式"""
    # 初始化配置
    settings = init_config()
    
    # 设置调试模式
    if args.debug:
        settings['debug'] = True
    
    # 如果指定了数据库目录，覆盖配置
    if args.db_dir:
        settings['DB_DIR'] = args.db_dir
        logger.info(f"设置环境变量DB_DIR: {args.db_dir}")
        os.environ['DB_DIR'] = args.db_dir
    else:
        # 确保配置了DB_DIR
        db_dir = settings.get('DB_DIR')
        if db_dir:
            logger.info(f"设置环境变量DB_DIR: {db_dir}")
            os.environ['DB_DIR'] = db_dir
    
    # 导入Web应用模块
    try:
        from newslook.web import create_app
    except ImportError:
        logger.error("无法导入Web应用模块。请检查是否安装了所有依赖。")
        sys.exit(1)
    
    # 创建并运行Web应用
    logger.info(f"Web应用模式启动: host={args.host}, port={args.port}, debug={args.debug}")
    app = create_app(settings)
    app.run(host=args.host, port=args.port, debug=args.debug)

# 主函数
def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 处理全局选项
    if args.config:
        # 如果指定了配置文件路径，加载配置
        config_file = args.config
        if os.path.exists(config_file):
            try:
                config_manager.load_config(config_file)
            except Exception as e:
                logger.error(f"加载配置文件 {config_file} 出错: {e}")
                sys.exit(1)
        else:
            logger.error(f"配置文件 {config_file} 不存在")
            sys.exit(1)
    
    # 根据模式执行对应的处理函数
    try:
        if args.mode == 'crawler':
            logger.info("运行模式: crawler")
            run_crawler(args)
        elif args.mode == 'scheduler':
            logger.info("运行模式: scheduler")
            run_scheduler(args)
        elif args.mode == 'web':
            logger.info("运行模式: web")
            run_web(args)
    except Exception as e:
        import traceback
        logger.error(f"程序运行出错: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)

# 程序入口
if __name__ == "__main__":
    main() 