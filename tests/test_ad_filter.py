#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试新浪财经爬虫的广告过滤功能
"""

import os
import sys
import time
import logging
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 导入相关模块
from app.crawlers.sina import SinaCrawler
from app.utils.database import NewsDatabase
from app.utils.logger import configure_logger

# 设置日志
logger = configure_logger(name="ad_filter_test", module="ad_filter")

def test_url_filter():
    """测试URL过滤功能"""
    logger.info("=== 测试URL过滤功能 ===")
    
    # 设置数据库路径
    db_dir = os.path.join('data', 'db')
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, '新浪财经.db')
    
    # 初始化爬虫，确保设置正确的数据库路径和来源
    crawler = SinaCrawler(db_path=db_path, use_source_db=True)
    logger.info(f"爬虫初始化完成，数据库路径：{crawler.db_path}，来源：{crawler.source}")
    
    # 初始化广告计数器
    crawler.ad_filtered_count = 0
    
    # 测试URL列表 - 包含正常新闻URL和广告URL
    test_urls = [
        # 正常新闻URL
        "https://finance.sina.com.cn/china/gncj/2023-03-23/doc-imynivrm1428696.shtml",
        "https://finance.sina.com.cn/roll/2023-03-23/doc-imynivrm1432109.shtml",
        # 广告URL
        "https://finance.sina.com.cn/focus/app/sfa_download_new.shtml",
        "https://k.sina.com.cn/download_app.html",
        "https://finance.sina.com.cn/app/download.shtml",
        "https://finance.sina.com.cn/promotion/activity.html"
    ]
    
    # 测试URL验证
    for url in test_urls:
        valid = crawler.validate_url(url)
        logger.info(f"URL: {url} - {'有效' if valid else '无效(广告)'}")
    
    logger.info(f"广告过滤统计: {crawler.ad_filtered_count}")
    
def test_content_filter():
    """测试内容过滤功能"""
    logger.info("\n=== 测试内容过滤功能 ===")
    
    # 设置数据库路径
    db_dir = os.path.join('data', 'db')
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, '新浪财经.db')
    
    # 初始化爬虫，确保设置正确的数据库路径和来源
    crawler = SinaCrawler(db_path=db_path, use_source_db=True)
    logger.info(f"爬虫初始化完成，数据库路径：{crawler.db_path}，来源：{crawler.source}")
    
    # 初始化广告计数器
    crawler.ad_filtered_count = 0
    
    # 测试内容
    test_contents = [
        # 正常新闻内容
        "中国经济持续向好，多项指标显示经济复苏势头强劲，专家预计全年GDP增长有望实现预期目标。",
        # 广告内容
        "新浪财经APP全新升级，扫码下载即可体验，首次下载还可获得专属福利。",
        "点击下载新浪财经客户端，享有更多资讯内容，更快获取市场动态。",
        "扫一扫下载APP，轻松获取第一手财经资讯，让您把握投资良机。"
    ]
    
    # 测试内容过滤
    for content in test_contents:
        is_ad = crawler.is_ad_content(content)
        logger.info(f"内容: {content[:30]}... - {'广告' if is_ad else '非广告'}")
    
def test_crawl_specific_urls():
    """测试爬取特定URL"""
    logger.info("\n=== 测试爬取特定URL ===")
    
    # 设置数据库路径
    db_dir = os.path.join('data', 'db')
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, '新浪财经.db')
    
    # 初始化爬虫，确保设置正确的数据库路径和来源
    crawler = SinaCrawler(db_path=db_path, use_source_db=True)
    logger.info(f"爬虫初始化完成，数据库路径：{crawler.db_path}，来源：{crawler.source}")
    
    # 重置广告过滤计数
    crawler.ad_filtered_count = 0
    
    # 测试URL列表 - 包含正常新闻URL和广告URL
    test_urls = [
        # 正常新闻URL (可能需要更新为有效的URL)
        "https://finance.sina.com.cn/china/gncj/2023-03-23/doc-imynivrm1428696.shtml",
        "https://finance.sina.com.cn/roll/2023-03-23/doc-imynivrm1432109.shtml",
        # 广告URL - 新浪财经APP下载页
        "https://finance.sina.com.cn/focus/app/sfa_download_new.shtml"
    ]
    
    # 爬取测试URL
    for url in test_urls:
        logger.info(f"尝试爬取URL: {url}")
        news_data = crawler.crawl_news_detail(url, "测试")
        if news_data:
            logger.info(f"成功爬取: {news_data['title'][:30]}...")
            logger.info(f"新闻来源: {news_data['source']}")
        else:
            logger.info(f"爬取失败或已过滤")
    
    logger.info(f"爬取完成，广告过滤统计: {crawler.ad_filtered_count}")

def main():
    """主函数"""
    logger.info("开始测试新浪财经爬虫的广告过滤功能")
    
    # 确保数据库目录存在
    db_dir = os.path.join('data', 'db')
    os.makedirs(db_dir, exist_ok=True)
    
    # 测试URL过滤
    test_url_filter()
    
    # 测试内容过滤
    test_content_filter()
    
    # 测试爬取特定URL
    test_crawl_specific_urls()
    
    logger.info("广告过滤测试完成")

if __name__ == "__main__":
    main() 