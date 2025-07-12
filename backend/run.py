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

# 移除策略和工厂导入，避免加载时间开销
from app.utils.logger import get_logger, configure_logger, fix_duplicate_logging
from app.tasks.scheduler import SchedulerManager

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
else:
    logger.info("=== NewsLook 财经新闻爬虫系统启动 ===")
    logger.info(f"运行路径: {CWD}")
    logger.info(f"Python版本: {sys.version}")

# 添加直接的爬虫映射，替代策略映射
CRAWLER_MAP = {
    'sina': 'app.crawlers.sina',
    'eastmoney': 'app.crawlers.eastmoney', 
    'netease': 'app.crawlers.sites.netease',
    'ifeng': 'app.crawlers.ifeng'
}

# 爬虫显示名称映射
CRAWLER_DISPLAY_MAP = {
    'sina': '新浪财经',
    'eastmoney': '东方财富',
    'netease': '网易财经', 
    'ifeng': '凤凰财经'
}

# 直接导入函数，避免策略加载
def import_crawler_directly(crawler_key: str, db_path: str, **kwargs):
    """
    直接导入指定的爬虫模块和类
    
    Args:
        crawler_key: 爬虫键值（如sina, eastmoney等）
        db_path: 数据库路径
        **kwargs: 其他参数
        
    Returns:
        爬虫实例或None
    """
    try:
        if crawler_key == 'sina':
            from app.crawlers.sina import SinaCrawler
            return SinaCrawler(db_path=db_path, **kwargs)
        elif crawler_key == 'eastmoney':
            from app.crawlers.eastmoney import EastMoneyCrawler
            return EastMoneyCrawler(db_path=db_path, **kwargs)
        elif crawler_key == 'netease':
            from app.crawlers.sites.netease import NeteaseCrawler
            return NeteaseCrawler(db_path=db_path, **kwargs)
        elif crawler_key == 'ifeng':
            from app.crawlers.ifeng import IfengCrawler
            return IfengCrawler(db_path=db_path, **kwargs)
        else:
            logger.error(f"不支持的爬虫: {crawler_key}")
            return None
    except ImportError as e:
        logger.error(f"导入爬虫失败 {crawler_key}: {e}")
        return None
    except Exception as e:
        logger.error(f"创建爬虫实例失败 {crawler_key}: {e}")
        return None

def setup_argparser():
    """设置命令行参数解析器"""
    parser = argparse.ArgumentParser(description='NewsLook 财经新闻爬虫系统')
    subparsers = parser.add_subparsers(dest='mode', help='运行模式')
    
    # 爬虫模式 - 修改为英文键值
    crawler_parser = subparsers.add_parser('crawler', help='爬虫模式')
    crawler_parser.add_argument('-s', '--source', type=str, choices=list(CRAWLER_MAP.keys()), help='指定新闻源 (sina|eastmoney|netease|ifeng)')
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
    
    # 数据库管理模式
    db_parser = subparsers.add_parser('db', help='数据库管理模式')
    db_subparsers = db_parser.add_subparsers(dest='db_action', help='数据库操作')
    
    # 数据库整理命令
    organize_parser = db_subparsers.add_parser('organize', help='整理和规范化数据库文件')
    organize_parser.add_argument('--auto', action='store_true', help='自动执行，不询问确认')
    organize_parser.add_argument('--dry-run', action='store_true', help='模拟运行，只显示将要执行的操作')
    
    # 数据库备份命令
    backup_parser = db_subparsers.add_parser('backup', help='备份数据库文件')
    backup_parser.add_argument('-s', '--source', type=str, help='指定要备份的数据源')
    backup_parser.add_argument('-a', '--all', action='store_true', help='备份所有数据库')
    
    # 数据库统计命令
    stats_parser = db_subparsers.add_parser('stats', help='显示数据库统计信息')
    stats_parser.add_argument('-s', '--source', type=str, help='指定要查看的数据源')
    stats_parser.add_argument('-a', '--all', action='store_true', default=True, help='查看所有数据库统计 (默认)')
    stats_parser.add_argument('--format', type=str, choices=['table', 'json', 'csv'], default='table', help='输出格式')
    
    # 数据库清理命令
    clean_parser = db_subparsers.add_parser('clean', help='清理数据库')
    clean_parser.add_argument('--days', type=int, default=30, help='清理多少天前的数据 (默认: 30)')
    clean_parser.add_argument('--source', type=str, help='指定要清理的数据源')
    clean_parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际删除')
    
    # 数据库导出命令
    export_parser = db_subparsers.add_parser('export', help='导出数据库数据')
    export_parser.add_argument('-s', '--source', type=str, required=True, help='指定要导出的数据源')
    export_parser.add_argument('-o', '--output', type=str, help='输出文件路径')
    export_parser.add_argument('--format', type=str, choices=['json', 'csv', 'xlsx'], default='json', help='导出格式')
    export_parser.add_argument('--limit', type=int, help='限制导出数量')
    export_parser.add_argument('--days', type=int, help='限制导出天数')
    
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
    # 如果是列出支持的新闻源
    if args.list:
        logger.info("支持的新闻源:")
        for key, display in CRAWLER_DISPLAY_MAP.items():
            logger.info(f"- {key} ({display})")
        return
    
    # 确保数据库目录存在 - 修复默认路径
    db_dir = args.db_dir or os.path.join(CWD, 'data')
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"已创建数据库目录: {db_dir}")
    
    # 确保数据库路径是绝对路径
    db_dir = os.path.abspath(db_dir)
    logger.info(f"使用数据库目录: {db_dir}")
        
    # 准备爬虫参数
    crawler_options = {
        'use_proxy': args.proxy,
        'timeout': args.timeout,
    }
    
    # 爬取所有支持的新闻源
    if args.all:
        logger.info("将爬取所有支持的新闻源")
        
        for crawler_key in CRAWLER_MAP.keys():
            try:
                display_name = CRAWLER_DISPLAY_MAP.get(crawler_key, crawler_key)
                logger.info(f"开始爬取: {display_name}")
                
                # 准备数据库路径
                db_path = os.path.join(db_dir, f"{crawler_key}.db")
                
                # 直接导入爬虫
                crawler = import_crawler_directly(crawler_key, db_path, **crawler_options)
                if not crawler:
                    logger.error(f"创建爬虫失败: {display_name}")
                    continue
                
                # 分割分类字符串
                categories = args.category.split(',') if args.category else None
                
                # 执行爬取
                result = crawler.crawl(days=args.days, max_news=args.max, category=categories)
                logger.info(f"爬取完成 ({display_name})，结果: {result}")
                
            except Exception as e:
                logger.error(f"爬取 {display_name} 失败: {str(e)}")
                logger.debug(traceback.format_exc())
    
    elif args.source:
        try:
            display_name = CRAWLER_DISPLAY_MAP.get(args.source, args.source)
            logger.info(f"将爬取新闻源: {display_name}")
            
            # 准备数据库路径
            db_path = os.path.join(db_dir, f"{args.source}.db")
            logger.info(f"数据库路径: {db_path}")
            
            # 直接导入爬虫
            crawler = import_crawler_directly(args.source, db_path, **crawler_options)
            if not crawler:
                logger.error(f"创建爬虫失败: {display_name}")
                return
                
            # 分割分类字符串
            categories = args.category.split(',') if args.category else None
            
            # 执行爬取
            logger.info(f"开始爬取: {display_name}")
            result = crawler.crawl(days=args.days, max_news=args.max, category=categories)
            logger.info(f"爬取完成: {result}")
            
        except Exception as e:
            logger.error(f"爬取 {display_name} 失败: {str(e)}")
            logger.error(traceback.format_exc())
    else:
        logger.error("请使用 -s/--source 指定新闻源或使用 -a/--all 爬取所有支持的新闻源")
        logger.info(f"支持的新闻源: {list(CRAWLER_MAP.keys())}")

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
        
        # 设置默认数据库目录 - 修复路径
        db_dir = args.db_dir if hasattr(args, 'db_dir') and args.db_dir else os.path.join(CWD, 'data')
        
        # 确保数据库目录存在
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
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
            
        # 启动前记录数据库配置信息
        logger.info(f"Web应用数据库目录: {db_dir}")
        db_files = [f for f in os.listdir(db_dir) if f.endswith('.db')] if os.path.exists(db_dir) else []
        logger.info(f"发现数据库文件: {db_files}")
            
        # 启动Web服务器
        logger.info(f"启动Web服务器: {args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=args.debug)
        
        return 0
    except Exception as e:
        logger.error(f"Web应用启动失败: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

def run_db_mode(args):
    """运行数据库管理模式"""
    try:
        from app.db.database_manager import DatabaseManager
        
        # 初始化数据库管理器
        manager = DatabaseManager(CWD)
        
        if args.db_action == 'organize':
            return handle_db_organize(manager, args)
        elif args.db_action == 'backup':
            return handle_db_backup(manager, args)
        elif args.db_action == 'stats':
            return handle_db_stats(manager, args)
        elif args.db_action == 'clean':
            return handle_db_clean(manager, args)
        elif args.db_action == 'export':
            return handle_db_export(manager, args)
        else:
            logger.error("请指定数据库操作: organize|backup|stats|clean|export")
            return 1
            
    except Exception as e:
        logger.error(f"数据库管理失败: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

def handle_db_organize(manager, args):
    """处理数据库整理"""
    logger.info("开始整理数据库文件...")
    
    if args.dry_run:
        logger.info("模拟运行模式，不会实际移动文件")
        # TODO: 实现dry-run逻辑
        return 0
    
    if not args.auto:
        try:
            confirm = input("确认要整理数据库文件吗? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                logger.info("用户取消操作")
                return 0
        except KeyboardInterrupt:
            logger.info("用户中断操作")
            return 0
    
    # 执行整理
    results = manager.normalize_database_files()
    
    # 显示结果
    logger.info("整理完成!")
    logger.info(f"移动文件: {len(results['moved_files'])}")
    logger.info(f"备份文件: {len(results['backup_files'])}")
    logger.info(f"错误: {len(results['errors'])}")
    
    if results['errors']:
        logger.error("错误详情:")
        for error in results['errors']:
            logger.error(f"  {error}")
    
    return 0

def handle_db_backup(manager, args):
    """处理数据库备份"""
    logger.info("开始备份数据库...")
    
    try:
        if args.all:
            backup_files = manager.create_backup()
            logger.info(f"备份完成，共备份 {len(backup_files)} 个文件:")
            for file_path in backup_files:
                logger.info(f"  {file_path}")
        elif args.source:
            if args.source not in CRAWLER_MAP:
                logger.error(f"不支持的数据源: {args.source}")
                return 1
            backup_files = manager.create_backup(args.source)
            if backup_files:
                logger.info(f"备份完成: {backup_files[0]}")
            else:
                logger.warning(f"没有找到 {args.source} 的数据库文件")
        else:
            logger.error("请指定 --source 或使用 --all")
            return 1
        
        return 0
    except Exception as e:
        logger.error(f"备份失败: {e}")
        return 1

def handle_db_stats(manager, args):
    """处理数据库统计"""
    logger.info("获取数据库统计信息...")
    
    try:
        stats = manager.get_database_stats()
        
        if args.format == 'json':
            import json
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        elif args.format == 'csv':
            print("source,path,exists,records,size_mb,latest_crawl")
            for source, info in stats.items():
                if args.source and source != args.source:
                    continue
                records = info.get('records', 0)
                size_mb = info.get('size_mb', 0)
                latest = info.get('latest_crawl', '')
                print(f"{source},{info['path']},{info['exists']},{records},{size_mb},{latest}")
        else:  # table format
            print("\n数据库统计信息:")
            print("-" * 80)
            print(f"{'数据源':<12} {'记录数':<10} {'大小(MB)':<12} {'最新爬取时间':<20} {'状态'}")
            print("-" * 80)
            
            for source, info in stats.items():
                if args.source and source != args.source:
                    continue
                    
                if info['exists'] and 'records' in info:
                    status = "✅ 正常"
                    records = info['records']
                    size_mb = info['size_mb']
                    latest = info.get('latest_crawl', '未知')[:19]
                else:
                    status = "❌ 不存在" if not info['exists'] else "⚠️ 错误"
                    records = 0
                    size_mb = 0
                    latest = ""
                
                print(f"{source:<12} {records:<10} {size_mb:<12.2f} {latest:<20} {status}")
        
        return 0
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return 1

def handle_db_clean(manager, args):
    """处理数据库清理"""
    logger.info(f"清理 {args.days} 天前的数据...")
    
    if args.dry_run:
        logger.info("模拟运行模式，不会实际删除数据")
    
    # TODO: 实现数据库清理逻辑
    logger.warning("数据库清理功能尚未实现")
    return 0

def handle_db_export(manager, args):
    """处理数据库导出"""
    logger.info(f"导出 {args.source} 数据库...")
    
    if args.source not in CRAWLER_MAP:
        logger.error(f"不支持的数据源: {args.source}")
        return 1
    
    # TODO: 实现数据库导出逻辑
    logger.warning("数据库导出功能尚未实现")
    return 0

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
    elif args.mode == 'db':
        return run_db_mode(args)
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