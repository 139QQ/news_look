#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 爬虫统一入口
支持多种爬虫类型，通过参数指定要运行的爬虫
"""

import os
import sys
import argparse
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
import re

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from app.utils.logger import configure_logger, get_logger
from app.crawlers import get_crawler, get_all_crawlers, get_crawler_sources

def setup_logging(log_level, log_dir, source=None):
    """设置日志配置"""
    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)
    
    # 设置日志格式和级别
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    console_handler.setLevel(numeric_level)
    root_logger.addHandler(console_handler)
    
    # 设置爬虫日志
    sources = [source] if source else get_crawler_sources()
    for crawler_name in sources:
        # 创建爬虫日志目录和处理器
        crawler_log_dir = os.path.join(log_dir, crawler_name.lower())
        os.makedirs(crawler_log_dir, exist_ok=True)
        
        log_file = os.path.join(crawler_log_dir, f"{crawler_name.lower()}_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(log_format))
        file_handler.setLevel(numeric_level)
        
        # 配置爬虫日志记录器
        logger = logging.getLogger(crawler_name.lower())
        logger.setLevel(numeric_level)
        logger.handlers.clear()
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.propagate = False
    
    # 设置第三方库日志级别
    for lib in ['urllib3', 'selenium', 'chardet', 'requests']:
        logging.getLogger(lib).setLevel(logging.WARNING)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='财经新闻爬虫统一入口')
    
    # 基本参数
    parser.add_argument('-s', '--source', help='爬虫来源，不指定则爬取所有来源')
    parser.add_argument('-d', '--days', type=int, default=1, help='爬取天数，默认1天')
    parser.add_argument('-p', '--use-proxy', action='store_true', help='使用代理')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='日志级别')
    parser.add_argument('--log-dir', default='./logs', help='日志目录')
    
    # 爬虫参数
    parser.add_argument('--max-news', type=int, default=10, help='每类最多新闻数')
    parser.add_argument('--categories', nargs='+', default=['财经', '股票'], help='新闻分类')
    parser.add_argument('--delay', type=float, default=3.0, help='请求间隔时间(秒)')
    parser.add_argument('--timeout', type=int, default=30, help='请求超时时间(秒)')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    return parser.parse_args()

def run_crawler(source, days, use_proxy, **kwargs):
    """运行爬虫"""
    start_time = datetime.now()
    logger = get_logger(source.lower() if source else 'crawler')
    
    try:
        if source:
            # 提取db_path参数
            db_path = kwargs.get('db_path')
            
            # 运行单个爬虫，传递db_path参数
            crawler = get_crawler(source, use_proxy=use_proxy, use_source_db=False, db_path=db_path)
            logger.info(f"开始运行 {source} 爬虫，爬取最近 {days} 天的新闻")
            
            # 确保数据库表已创建
            if hasattr(crawler, 'db_manager') and hasattr(crawler.db_manager, 'init_db'):
                try:
                    if hasattr(crawler, 'conn'):
                        crawler.db_manager.init_db(crawler.conn)
                        logger.info("数据库表初始化完成")
                    else:
                        logger.warning("爬虫没有数据库连接")
                except Exception as e:
                    logger.error(f"初始化数据库表失败: {str(e)}")
            
            # 设置爬虫参数
            for key, value in kwargs.items():
                if hasattr(crawler, key):
                    setattr(crawler, key, value)
            
            # 简化：只传递days参数给所有爬虫
            news_data = crawler.crawl(days=days)
            logger.info(f"{source} 爬虫运行完成，共爬取 {len(news_data)} 条新闻")
            
            # 确保新闻数据保存到数据库
            if news_data and hasattr(crawler, 'db_manager') and hasattr(crawler.db_manager, 'save_news'):
                saved_count = 0
                for news in news_data:
                    try:
                        if crawler.db_manager.save_news(news):
                            saved_count += 1
                    except Exception as e:
                        logger.error(f"保存新闻到数据库失败: {news.get('title', '未知标题')}, 错误: {str(e)}")
                
                logger.info(f"成功保存 {saved_count} 条新闻到数据库: {crawler.db_path}")
            
            # 保存数据库连接
            if hasattr(crawler, 'conn') and crawler.conn:
                try:
                    crawler.conn.commit()
                    logger.info(f"已提交数据库事务")
                except Exception as e:
                    logger.error(f"提交数据库事务失败: {str(e)}")
            
        else:
            # 提取db_path参数
            db_path = kwargs.get('db_path')
            
            # 运行所有爬虫
            crawlers = get_all_crawlers(use_proxy=use_proxy, db_path=db_path)
            logger.info(f"开始运行所有爬虫，共 {len(crawlers)} 个，爬取最近 {days} 天的新闻")
            
            total_news = 0
            for crawler in crawlers:
                crawler_source = crawler.source
                try:
                    # 设置爬虫参数
                    for key, value in kwargs.items():
                        if hasattr(crawler, key):
                            setattr(crawler, key, value)
                    
                    # 简化：只传递days参数给所有爬虫
                    crawler_logger = get_logger(crawler_source.lower())
                    crawler_logger.info(f"开始运行 {crawler_source} 爬虫")
                    news_data = crawler.crawl(days=days)
                    crawler_logger.info(f"{crawler_source} 爬虫运行完成，共爬取 {len(news_data)} 条新闻")
                    total_news += len(news_data)
                    
                    # 确保新闻数据保存到数据库
                    if news_data and hasattr(crawler, 'db_manager') and hasattr(crawler.db_manager, 'save_news'):
                        saved_count = 0
                        for news in news_data:
                            try:
                                if crawler.db_manager.save_news(news):
                                    saved_count += 1
                            except Exception as e:
                                logger.error(f"保存新闻到数据库失败: {news.get('title', '未知标题')}, 错误: {str(e)}")
                        
                        logger.info(f"成功保存 {saved_count} 条新闻到数据库: {crawler.db_path}")
                    
                    # 保存数据库连接
                    if hasattr(crawler, 'conn') and crawler.conn:
                        try:
                            crawler.conn.commit()
                            logger.info(f"已提交数据库事务")
                        except Exception as e:
                            logger.error(f"提交数据库事务失败: {str(e)}")
                    
                    # 随机延迟，避免频繁请求
                    time.sleep(random.uniform(1, kwargs.get('delay', 3)))
                    
                except Exception as e:
                    crawler_logger = get_logger(crawler_source.lower())
                    crawler_logger.error(f"运行 {crawler_source} 爬虫失败: {e}")
                    crawler_logger.exception(e)
            
            logger.info(f"所有爬虫运行完成，共爬取 {total_news} 条新闻")
    
    except Exception as e:
        logger.error(f"爬虫运行异常: {e}")
        logger.exception(e)
    
    # 计算运行时间
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"爬虫运行总耗时: {duration:.2f} 秒")

def generate_db_path(source=None, db_dir=None):
    """生成数据库路径"""
    # 如果没有提供数据库目录，使用默认目录
    if db_dir is None:
        db_dir = os.path.join(os.getcwd(), 'data', 'db')
    
    # 确保数据库目录存在
    os.makedirs(db_dir, exist_ok=True)
    
    # 根据来源生成数据库文件名
    if source:
        # 将来源转换为文件名安全的字符串
        source_name = re.sub(r'[^\w]', '_', source.lower())
        db_filename = f"{source_name}.db"
    else:
        # 使用固定的文件名
        db_filename = "finance_news.db"
    
    # 生成数据库路径
    db_path = os.path.join(db_dir, db_filename)
    
    return db_path

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 如果开启调试模式，设置日志级别为DEBUG
    if args.debug and args.log_level != 'DEBUG':
        args.log_level = 'DEBUG'
    
    # 确保必要的目录存在
    os.makedirs('data/db', exist_ok=True)
    os.makedirs('data/output', exist_ok=True)
    
    # 使用新的函数生成固定的数据库路径
    absolute_db_path = os.path.abspath(generate_db_path(args.source, os.path.join(os.getcwd(), 'data', 'db')))
    
    # 设置环境变量
    db_dir = os.path.dirname(absolute_db_path)
    os.environ['DB_DIR'] = db_dir
    os.environ['LOG_LEVEL'] = args.log_level
    os.environ['LOG_DIR'] = os.path.abspath(args.log_dir)
    os.environ['DB_PATH'] = absolute_db_path
    
    print(f"当前工作目录: {os.getcwd()}")
    print(f"设置新的数据库文件: {absolute_db_path}")
    print(f"设置的环境变量DB_DIR: {os.environ['DB_DIR']}")
    
    # 设置日志
    setup_logging(args.log_level, args.log_dir, args.source)
    
    # 构建爬虫参数
    crawler_kwargs = {
        'max_news': args.max_news,
        'categories': args.categories,
        'delay': args.delay,
        'timeout': args.timeout,
        'db_path': absolute_db_path  # 添加数据库路径参数
    }
    
    # 运行爬虫
    run_crawler(args.source, args.days, args.use_proxy, **crawler_kwargs)
    
    # 爬取完成后检查数据库文件是否存在
    if os.path.exists(absolute_db_path):
        print(f"数据库文件已成功创建: {absolute_db_path}")
        print(f"文件大小: {os.path.getsize(absolute_db_path)} 字节")
    else:
        print(f"警告: 数据库文件未找到: {absolute_db_path}")
        
        # 搜索可能的数据库文件
        db_files = []
        for root, dirs, files in os.walk(os.getcwd()):
            for file in files:
                if file.endswith('.db') and f'_{current_time}' in file:
                    db_files.append(os.path.join(root, file))
        
        if db_files:
            print(f"找到可能的数据库文件:")
            for db_file in db_files:
                print(f"  - {db_file} ({os.path.getsize(db_file)} 字节)")
        else:
            print("未找到任何可能的数据库文件")

if __name__ == '__main__':
    main()
