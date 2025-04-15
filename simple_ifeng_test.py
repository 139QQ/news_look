#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
凤凰财经爬虫简单测试脚本
"""

import os
import sys
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# 添加当前目录到模块搜索路径
sys.path.insert(0, os.path.abspath('.'))

def main():
    try:
        # 导入凤凰财经爬虫
        from app.crawlers.ifeng import IfengCrawler
        
        print("="*50)
        print("开始测试凤凰财经爬虫")
        print("="*50)
        
        # 初始化爬虫
        print("初始化爬虫...")
        crawler = IfengCrawler()
        print(f"爬虫初始化成功")
        
        # 测试获取新闻链接
        category = '财经'
        url = 'https://finance.ifeng.com/'
        print(f"测试获取新闻链接: {category}, {url}")
        news_links = crawler.get_news_links(url, category)
        print(f"获取到 {len(news_links)} 条新闻链接")
        
        if news_links:
            # 测试获取新闻详情
            test_url = news_links[0]
            print(f"测试获取新闻详情: {test_url}")
            news = crawler.get_news_detail(test_url, category)
            if news:
                print("获取新闻详情成功:")
                print(f"标题: {news['title']}")
                print(f"发布时间: {news['pub_time']}")
                print(f"作者: {news['author']}")
                print(f"内容长度: {len(news['content'])}")
            else:
                print("获取新闻详情失败")
        
        print("="*50)
        return True
    except Exception as e:
        import traceback
        print(f"测试失败: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
