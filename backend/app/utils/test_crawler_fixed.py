#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志测试工具 - 用于测试东方财富爬虫日志输出
"""

import os
import sys
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.utils.logger import get_crawler_logger
from backend.app.db.SQLiteManager import SQLiteManager
from backend.app.crawlers.eastmoney import EastMoneyCrawler

def test_logger():
    """测试爬虫日志记录器"""
    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs', '东方财富')
    os.makedirs(log_dir, exist_ok=True)
    
    # 获取东方财富日志记录器
    logger = get_crawler_logger('东方财富')
    logger.info("=== 开始测试东方财富爬虫日志 ===")
    
    # 创建SQLiteManager
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'db', 'test_eastmoney.db')
    sqlite_manager = SQLiteManager(db_path)
    
    # 创建东方财富爬虫实例
    crawler = EastMoneyCrawler(db_manager=sqlite_manager, db_path=db_path)
    logger.info("爬虫实例创建成功")
    
    # 测试爬虫方法调用
    logger.info("测试爬虫方法...")
    
    # 测试URL访问
    url = "https://finance.eastmoney.com/"
    logger.info(f"测试访问URL: {url}")
    accessible = crawler._check_url_accessibility(url)
    logger.info(f"URL可访问性: {accessible}")
    
    # 测试提取链接
    logger.info("测试提取新闻链接...")
    try:
        links = crawler.extract_news_links(url)
        logger.info(f"成功提取 {len(links)} 个链接")
        if links:
            logger.info(f"第一个链接: {links[0]}")
    except Exception as e:
        logger.error(f"提取链接失败: {str(e)}")
    
    # 测试爬取单篇文章
    if 'links' in locals() and links:
        test_url = links[0]
        logger.info(f"测试爬取单篇文章: {test_url}")
        try:
            article = crawler.crawl_news_detail(test_url, "财经")
            if article:
                logger.info(f"成功爬取文章: {article.get('title')}")
                logger.info(f"内容长度: {len(article.get('content', ''))}")
            else:
                logger.warning("未能成功爬取文章")
        except Exception as e:
            logger.error(f"爬取文章失败: {str(e)}")
    
    logger.info("=== 东方财富爬虫日志测试完成 ===")

def main():
    """主函数"""
    print("=== 东方财富爬虫日志测试 ===")
    
    # 测试日志记录
    test_logger()
    
    # 检查日志文件
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs', '东方财富')
    today = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(log_dir, f"东方财富_{today}.log")
    
    if os.path.exists(log_file):
        print(f"日志文件已创建: {log_file}")
        print(f"文件大小: {os.path.getsize(log_file)} 字节")
        
        # 显示日志文件的最后几行
        print("\n最近的日志内容:")
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-10:]:
                print(line.strip())
    else:
        print(f"日志文件不存在: {log_file}")
    
    print("测试完成")

if __name__ == "__main__":
    main() 