#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化版东方财富网爬虫启动脚本
"""

import os
import sys
import argparse
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# 导入简化版爬虫
from app.crawlers.eastmoney_simple import EastMoneySimpleCrawler

def setup_logging(log_level=logging.INFO, log_file=None):
    """设置日志配置"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
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
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
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
    
    # 调整第三方库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='简化版东方财富网爬虫')
    parser.add_argument('--output', type=str, default='news.json', help='输出文件名')
    parser.add_argument('--db-path', type=str, default='./data/news.db', help='数据库路径')
    parser.add_argument('--output-dir', type=str, default='./data/output', help='输出目录路径')
    parser.add_argument('--category', type=str, default='财经', help='新闻分类')
    parser.add_argument('--debug', action='store_true', help='是否开启调试模式')
    parser.add_argument('--log-dir', type=str, default='./logs', help='日志存储目录')
    parser.add_argument('--days', type=int, default=3, help='爬取几天内的新闻')
    parser.add_argument('--max-news', type=int, default=10, help='最多爬取的新闻数量')
    return parser.parse_args()

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 设置日志级别
    log_level = logging.DEBUG if args.debug else logging.INFO
    
    # 设置日志文件路径：logs/eastmoney_simple/eastmoney_simple_YYYYMMDD.log
    crawler_name = "eastmoney_simple"
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
    
    # 检查输出目录是否存在
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        logging.info(f"创建输出目录: {args.output_dir}")
    
    try:
        # 初始化数据库管理器
        db_manager = None
        try:
            # 如果有数据库管理模块，导入并初始化
            from app.db.sqlite_manager import SQLiteManager
            db_manager = SQLiteManager(args.db_path)
            logging.info(f"数据库路径: {args.db_path}")
        except ImportError:
            logging.warning("未找到数据库管理模块，将不保存数据到数据库")
        
        # 创建爬虫实例
        crawler = EastMoneySimpleCrawler(db_manager=db_manager)
        
        # 爬取结果
        all_news = []
        
        # 爬取每个分类
        for category in args.category:
            logging.info(f"开始爬取 {category} 分类的新闻")
            
            # 爬取新闻
            news_list = crawler.crawl(
                category=category,
                max_news=args.max_news,
                days=args.days
            )
            
            # 添加到总结果
            all_news.extend(news_list)
            
            logging.info(f"成功爬取 {category} 分类的 {len(news_list)} 条新闻")
            
            # 将新闻内容保存到文件
            if news_list:
                output_file = os.path.join(args.output_dir, f"{category}_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt")
                with open(output_file, 'w', encoding='utf-8') as f:
                    for i, news in enumerate(news_list):
                        f.write(f"新闻 {i+1}:\n")
                        f.write(f"标题: {news['title']}\n")
                        f.write(f"URL: {news['url']}\n")
                        f.write(f"发布时间: {news['pub_time']}\n")
                        f.write(f"来源: {news['author']}\n")
                        f.write(f"关键词: {news['keywords']}\n")
                        f.write(f"内容:\n{news['content']}\n")
                        f.write("-" * 80 + "\n\n")
                
                logging.info(f"已将 {category} 分类的新闻保存到文件: {output_file}")
        
        # 打印爬取结果
        if all_news:
            logging.info(f"爬取完成，共获取 {len(all_news)} 条新闻")
            
            # 打印前几条新闻的标题
            for i, news in enumerate(all_news[:min(5, len(all_news))]):
                logging.info(f"新闻 {i+1}: {news['title']}")
        else:
            logging.warning("未爬取到任何新闻")
        
    except Exception as e:
        logging.error(f"爬虫运行失败: {str(e)}")
        logging.exception(e)

if __name__ == "__main__":
    main() 