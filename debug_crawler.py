#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试脚本 - 直接测试新浪财经爬虫
"""

import os
import sys
import logging
import traceback

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("debug_crawler.log")
    ]
)

logger = logging.getLogger("debug_crawler")

def main():
    """主函数"""
    logger.info("开始测试新浪财经爬虫")
    
    try:
        # 导入爬虫
        logger.info("导入SinaCrawler...")
        from app.crawlers.sina import SinaCrawler
        logger.info("成功导入SinaCrawler")
        
        # 创建爬虫实例
        logger.info("初始化爬虫...")
        crawler = SinaCrawler()
        logger.info("爬虫初始化成功")
        
        # 获取股票页面URL
        stock_url = crawler.CATEGORY_URLS.get('股票')
        if not stock_url:
            logger.error("找不到股票分类URL")
            return
        
        logger.info("股票页面URL: %s", stock_url)
        
        # 获取页面内容
        logger.info("获取页面内容...")
        html = crawler.fetch_page(stock_url)
        if not html:
            logger.error("获取页面内容失败")
            return
        
        logger.info("成功获取页面内容，长度: %d 字符", len(html))
        
        # 提取新闻链接
        logger.info("提取新闻链接...")
        links = crawler.extract_news_links(html, "股票")
        logger.info("提取到 %d 个新闻链接", len(links))
        
        if not links:
            logger.warning("没有提取到新闻链接")
            return
        
        # 爬取第一条新闻
        first_link = links[0]
        logger.info("爬取第一条新闻: %s", first_link)
        
        news_data = crawler.crawl_news_detail(first_link, "股票")
        if not news_data:
            logger.error("爬取新闻失败")
            return
        
        # 打印新闻信息
        logger.info("新闻标题: %s", news_data.get('title', '无标题'))
        logger.info("发布时间: %s", news_data.get('pub_time', '未知'))
        logger.info("内容长度: %d 字符", len(news_data.get('content', '')))
        logger.info("关键词: %s", ', '.join(news_data.get('keywords', [])))
        
        logger.info("测试完成")
        
    except Exception as e:
        logger.error("测试过程中出错: %s", str(e))
        traceback.print_exc()

if __name__ == "__main__":
    main()
