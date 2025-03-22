#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试东方财富网爬虫
"""

import os
import sys

# 获取当前文件所在目录（项目根目录）
project_root = os.path.abspath(os.path.dirname(__file__))

# 将项目根目录添加到Python路径
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入爬虫
from app.crawlers.eastmoney import EastmoneyCrawler

def main():
    # 初始化爬虫
    crawler = EastmoneyCrawler(use_proxy=False, use_source_db=True)
    print("爬虫初始化成功，开始爬取...")
    
    # 爬取新闻
    news_list = crawler.crawl(days=1, max_news_per_category=5, retry_count=2)
    print(f"爬取到新闻数量: {len(news_list)}")
    
    # 打印前5条新闻的标题
    for i, news in enumerate(news_list[:5]):
        print(f"{i+1}. {news['title']}")

if __name__ == "__main__":
    main() 