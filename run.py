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
import logging
import logging.handlers
import traceback
import argparse
import configparser
from datetime import datetime

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
    # 获取日志级别
    log_level_str = args.log_level if hasattr(args, 'log_level') else 'INFO'
    log_level = getattr(logging, log_level_str)
    
    # 创建日志目录
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 日志文件路径
    log_file = os.path.join(log_dir, 'finance_news_crawler.log')
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除已有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
    ))
    root_logger.addHandler(file_handler)
    
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
    logger.info("日志文件路径: %s", log_file)
    
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
    crawler_parser.add_argument('--db-dir', help='指定数据库目录')
    crawler_parser.add_argument('--use-proxy', action='store_true', help='是否使用代理')
    crawler_parser.add_argument('--verbose', action='store_true', help='显示详细日志信息')
    crawler_parser.add_argument('--log-retention-days', type=int, default=30, help='日志保留天数（默认为30天）')
    crawler_parser.add_argument('--clean-logs', action='store_true', help='清理过期日志文件')
    crawler_parser.add_argument('--optimized', action='store_true', help='是否使用优化版爬虫')
    crawler_parser.add_argument('--max-news', type=int, default=50, help='最大新闻数量（默认为50条）')
    
    # 调度器模式
    scheduler_parser = subparsers.add_parser('scheduler', help='调度器模式')
    scheduler_parser.add_argument('--interval', type=int, default=3600, help='调度间隔，单位为秒（默认3600秒）')
    
    # Web应用模式
    web_parser = subparsers.add_parser('web', help='Web应用模式')
    web_parser.add_argument('--host', default='0.0.0.0', help='Web服务器地址（默认0.0.0.0）')
    web_parser.add_argument('--port', type=int, default=8000, help='Web服务器端口（默认8000）')
    web_parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    # 全局参数
    parser.add_argument('--config', help='指定配置文件路径')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                        default='INFO', help='指定日志级别')
    
    # 解析参数
    args = parser.parse_args()
    
    # 如果没有指定模式，显示帮助信息
    if not args.mode:
        parser.print_help()
        sys.exit(0)
    
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
            cleaner = LogCleaner(
                log_dir='logs',
                max_logs=settings.get('max_logs', 10),
                retention_days=settings.get('log_retention_days', 7)
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
        
        # 打印爬虫配置信息
        logger.info("="*50)
        logger.info("爬虫配置信息:")
        logger.info("爬虫源: %s", source)
        logger.info("爬取天数: %d", days)
        logger.info("最大页数: %d", max_pages)
        logger.info("分类: %s", category)
        logger.info("详细模式: %s", args.verbose if hasattr(args, 'verbose') else False)
        logger.info("="*50)
        
        # 根据源选择爬虫
        if source == 'all':
            # 运行所有爬虫
            logger.info("运行所有爬虫")
            # 实现所有爬虫的运行逻辑
        elif source == 'sina' or source == '新浪财经' or source == '新浪':
            # 运行新浪爬虫
            logger.info("运行新浪爬虫")
            try:
                print("正在导入新浪爬虫模块...")
                from app.crawlers.sina import SinaCrawler
                print("新浪爬虫模块导入成功")
                
                print("正在初始化爬虫...")
                crawler = SinaCrawler()
                print("爬虫初始化成功")
                
                print(f"开始爬取，天数: {days}, 最大页数: {max_pages}, 分类: {category}")
                crawler.crawl(days=days, max_pages=max_pages, category=category)
                print("爬取完成")
            except Exception as e:
                print(f"爬虫运行出错: {str(e)}")
                logger.error("爬虫运行出错: %s", str(e))
                import traceback
                print(traceback.format_exc())
                logger.error(traceback.format_exc())
                return 1
        elif source == 'netease':
            # 运行网易爬虫
            logger.info("运行网易爬虫")
            try:
                print("正在导入网易爬虫模块...")
                # 判断是否使用优化版爬虫
                use_optimized = hasattr(args, 'optimized') and args.optimized
                
                if use_optimized:
                    from app.crawlers.optimized_netease import OptimizedNeteaseCrawler
                    print("优化版网易爬虫模块导入成功")
                    
                    print("正在初始化优化版爬虫...")
                    from app.utils.database import DatabaseManager
                    from app.config import get_settings
                    
                    # 获取配置中的数据库目录
                    settings = get_settings()
                    db_dir = settings.DB_DIR
                    print(f"使用数据库目录: {db_dir}")
                    
                    # 确保数据库目录存在
                    import os
                    if not os.path.exists(db_dir):
                        os.makedirs(db_dir, exist_ok=True)
                        print(f"创建数据库目录: {db_dir}")
                    
                    # 创建数据库管理器
                    db_manager = DatabaseManager(db_dir=db_dir)
                    
                    # 初始化爬虫，传入数据库管理器
                    crawler = OptimizedNeteaseCrawler(db_manager=db_manager)
                    print("优化版爬虫初始化成功")
                else:
                    from app.crawlers.netease import NeteaseCrawler
                    print("网易爬虫模块导入成功")
                    
                    print("正在初始化爬虫...")
                    crawler = NeteaseCrawler()
                    print("爬虫初始化成功")
                
                # 获取最大新闻数量
                max_news = int(args.max_news) if hasattr(args, 'max_news') else 50
                
                print(f"开始爬取，天数: {days}, 最大新闻数: {max_news}, 分类: {category}")
                crawler.crawl(days=days, max_news=max_news, category=category)
                print("爬取完成")
            except Exception as e:
                print(f"爬虫运行出错: {str(e)}")
                logger.error("爬虫运行出错: %s", str(e))
                import traceback
                print(traceback.format_exc())
                logger.error(traceback.format_exc())
                return 1
        elif source == 'tencent' or source == '腾讯财经' or source == '腾讯':
            # 运行腾讯爬虫
            logger.info("运行腾讯爬虫")
            try:
                print("正在导入腾讯爬虫模块...")
                from app.crawlers.tencent import TencentCrawler
                print("腾讯爬虫模块导入成功")
                
                print("正在初始化爬虫...")
                crawler = TencentCrawler()
                print("爬虫初始化成功")
                
                # 获取最大新闻数量
                max_news = int(args.max_news) if hasattr(args, 'max_news') else 50
                
                print(f"开始爬取，天数: {days}, 最大新闻数: {max_news}")
                crawler.crawl(days=days, max_pages=max_news)
                print("爬取完成")
            except Exception as e:
                print(f"爬虫运行出错: {str(e)}")
                logger.error("爬虫运行出错: %s", str(e))
                import traceback
                print(traceback.format_exc())
                logger.error(traceback.format_exc())
                return 1
        elif source == 'ifeng':
            # 运行凤凰爬虫
            logger.info("运行凤凰爬虫")
            try:
                print("正在导入凤凰财经爬虫模块...")
                from app.crawlers.ifeng import IfengCrawler
                print("凤凰财经爬虫模块导入成功")
                
                print("正在初始化爬虫...")
                crawler = IfengCrawler()
                print("爬虫初始化成功")
                
                # 获取最大新闻数量
                max_news = int(args.max_news) if hasattr(args, 'max_news') else 50
                
                print(f"开始爬取，天数: {days}, 最大新闻数: {max_news}")
                crawler.crawl(days=days, max_news=max_news)
                print("爬取完成")
            except Exception as e:
                print(f"爬虫运行出错: {str(e)}")
                logger.error("爬虫运行出错: %s", str(e))
                import traceback
                print(traceback.format_exc())
                logger.error(traceback.format_exc())
                return 1
        elif source == 'eastmoney':
            # 运行东方财富爬虫
            logger.info("运行东方财富爬虫")
            # 实现东方财富爬虫的运行逻辑
        else:
            logger.error("未知的爬虫源: %s", source)
            sys.exit(1)
        
        logger.info("爬虫运行完成")
        return 0
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
    # 初始化配置
    settings = init_config()
    
    # 导入Web应用模块
    try:
        logger.info("导入Web应用模块...")
        from flask import Flask, render_template, request, jsonify
        logger.info("成功导入Web应用模块")
    except ImportError as e:
        logger.error("导入Web应用模块失败: %s", str(e))
        logger.error("请安装Flask: pip install flask")
        sys.exit(1)
    
    # 创建Flask应用
    app = Flask(__name__, 
                template_folder=os.path.join('app', 'templates'),
                static_folder=os.path.join('app', 'static'))
    
    # 导入爬虫模块
    try:
        from app.crawlers.sina import SinaCrawler
        crawler = SinaCrawler()
        logger.info("爬虫初始化成功")
    except Exception as e:
        logger.error("初始化爬虫失败: %s", str(e))
        traceback.print_exc()
    
    # 定义路由
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/api/crawl', methods=['POST'])
    def api_crawl():
        try:
            days = int(request.form.get('days', 1))
            crawler.crawl(days=days)
            return jsonify({'status': 'success', 'message': '成功爬取最近 %d 天的新闻' % days})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    
    # 启动Web服务器
    logger.info("启动Web服务器，地址: %s, 端口: %d", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug)

def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_args()
        
        # 初始化日志
        init_logging(args)
        
        # 加载配置文件
        if args.config:
            config_file = args.config
            if os.path.exists(config_file):
                try:
                    config_manager.load_config()
                    logger.info("加载配置文件: %s", config_file)
                except Exception as e:
                    logger.error("加载配置文件 %s 出错: %s", config_file, str(e))
                    sys.exit(1)
            else:
                logger.error("配置文件不存在: %s", config_file)
                sys.exit(1)
        
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