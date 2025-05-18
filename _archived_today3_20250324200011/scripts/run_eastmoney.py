#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
东方财富网爬虫启动脚本
"""

import os
import sys
import logging
import argparse
import traceback
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging.handlers

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# 设置日志配置
def setup_logging(log_level=logging.INFO, log_file=None):
    """设置日志配置"""
    # 简洁的日志格式，只包含时间、级别和消息
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # 创建日志处理器
    handlers = []
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 使用RotatingFileHandler限制日志文件大小
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,          # 保留5个备份
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        format=log_format
    )
    
    # 调整第三方库的日志级别，减少冗余输出
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('chardet').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # 设置自定义过滤器，过滤掉包含新闻详细内容的日志
    class NewsContentFilter(logging.Filter):
        def filter(self, record):
            # 如果日志消息包含大段新闻内容，则不显示完整内容
            if '条新闻' in record.getMessage() and len(record.getMessage()) > 500:
                # 找到最后一个右方括号的位置，通常是新闻列表的结束
                idx = record.getMessage().rfind('] 条新闻')
                if idx > 0:
                    # 保留消息开头和结尾，省略中间的新闻内容
                    prefix = record.getMessage()[:record.getMessage().find('[') + 1]
                    suffix = record.getMessage()[idx:]
                    record.msg = f"{prefix}...{suffix}"
            return True
    
    # 为根日志记录器添加过滤器
    root_logger = logging.getLogger()
    root_logger.addFilter(NewsContentFilter())

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='东方财富网爬虫')
    parser.add_argument('--days', type=int, default=3, help='爬取几天内的新闻，默认3天')
    parser.add_argument('--max-news', type=int, default=10, help='每个分类最多爬取多少条新闻，默认10条')
    parser.add_argument('--use-proxy', action='store_true', help='是否使用代理')
    parser.add_argument('--db-path', type=str, default='./data/news.db', help='数据库路径')
    parser.add_argument('--categories', nargs='+', default=['财经', '股票'], help='要爬取的新闻分类，默认为财经和股票')
    parser.add_argument('--delay', type=float, default=5.0, help='请求间隔时间(秒)，默认5秒')
    parser.add_argument('--max-retries', type=int, default=3, help='最大重试次数，默认3次')
    parser.add_argument('--timeout', type=int, default=30, help='请求超时时间(秒)，默认30秒')
    parser.add_argument('--use-selenium', action='store_true', help='是否使用Selenium')
    parser.add_argument('--debug', action='store_true', help='是否开启调试模式')
    parser.add_argument('--log-dir', type=str, default='./logs', help='日志存储目录')
    parser.add_argument('--output-dir', type=str, default='./data/output', help='输出文件目录')
    return parser.parse_args()

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 设置日志级别
    log_level = logging.DEBUG if args.debug else logging.INFO
    
    # 生成日志文件路径：logs/eastmoney/eastmoney_YYYYMMDD.log
    crawler_name = "eastmoney"
    crawler_log_dir = os.path.join(args.log_dir, crawler_name)
    if not os.path.exists(crawler_log_dir):
        os.makedirs(crawler_log_dir)
    
    log_filename = f"{crawler_name}_{datetime.now().strftime('%Y%m%d')}.log"
    log_file = os.path.join(crawler_log_dir, log_filename)
    
    # 设置日志配置
    setup_logging(log_level=log_level, log_file=log_file)
    
    # 记录启动信息
    logging.info(f"项目根目录: {project_root}")
    logging.info(f"启动参数: {args}")
    
    # 检查数据库目录是否存在
    db_dir = os.path.dirname(args.db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        logging.info(f"创建数据库目录: {db_dir}")
    
    # 检查输出目录是否存在
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        logging.info(f"创建输出目录: {args.output_dir}")
    
    try:
        # 导入爬虫模块
        try:
            from app.crawlers.eastmoney import EastMoneyCrawler
            from app.db.SQLiteManager import SQLiteManager
            logging.info("成功导入爬虫模块")
        except ImportError as e:
            logging.error(f"导入爬虫模块失败: {str(e)}")
            logging.error("请确保项目结构正确，并且已安装所有依赖")
            return
        
        # 创建数据库管理器
        db_manager = SQLiteManager(args.db_path)
        logging.info(f"数据库路径: {args.db_path}")
        
        # 创建爬虫实例
        crawler = EastMoneyCrawler(db_manager)
        
        # 设置爬虫参数
        crawler.use_proxy = args.use_proxy
        
        # 设置反爬参数
        if hasattr(crawler, 'delay'):
            crawler.delay = args.delay
        
        if hasattr(crawler, 'max_retries'):
            crawler.max_retries = args.max_retries
        
        if hasattr(crawler, 'timeout'):
            crawler.timeout = args.timeout
        
        # 设置是否使用Selenium
        crawler.use_selenium = args.use_selenium
        
        # 计算开始日期
        start_date = datetime.now() - timedelta(days=args.days)
        start_date_str = start_date.strftime('%Y-%m-%d')
        
        # 开始爬取
        logging.info(f"开始爬取 {args.categories} 分类的新闻，从 {start_date_str} 开始，每个分类最多爬取 {args.max_news} 条")
        
        # 爬取每个分类的新闻
        for category in args.categories:
            try:
                logging.info(f"开始爬取 {category} 分类的新闻")
                
                # 随机延迟，避免频繁请求
                sleep_time = random.uniform(1, 3)
                logging.debug(f"随机延迟 {sleep_time:.2f} 秒")
                time.sleep(sleep_time)
                
                # 爬取该分类的新闻
                news_count = crawler.crawl(
                    category=category,
                    days=args.days,
                    max_news=args.max_news
                )
                
                logging.info(f"成功爬取 {category} 分类的 {news_count} 条新闻")
            except Exception as e:
                logging.error(f"爬取 {category} 分类的新闻失败: {str(e)}")
                logging.exception(e)
        
        logging.info("爬取完成")
        
    except Exception as e:
        logging.error(f"爬虫运行失败: {str(e)}")
        logging.exception(e)

if __name__ == "__main__":
    main() 