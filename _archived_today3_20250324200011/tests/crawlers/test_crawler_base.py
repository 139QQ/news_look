#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 爬虫测试脚本
用于测试爬虫模块的功能
"""

import os
import sys
import time
from datetime import datetime

from app.crawlers import get_crawler, get_all_crawlers, get_crawler_sources
from app.utils.logger import setup_logger, get_logger

# 设置日志记录器
logger = get_logger('crawler_tester')

def test_crawler_sources():
    """测试获取爬虫来源"""
    print("\n===== 测试获取爬虫来源 =====")
    sources = get_crawler_sources()
    print(f"支持的爬虫来源: {', '.join(sources)}")
    assert len(sources) > 0, "爬虫来源列表为空"
    print("测试通过: 成功获取爬虫来源")

def test_get_crawler():
    """测试获取爬虫实例"""
    print("\n===== 测试获取爬虫实例 =====")
    sources = get_crawler_sources()
    
    for source in sources:
        print(f"测试获取爬虫: {source}")
        crawler = get_crawler(source, use_source_db=True)
        assert crawler is not None, f"获取爬虫实例失败: {source}"
        print(f"爬虫类型: {type(crawler).__name__}")
        print(f"爬虫来源: {crawler.source}")
        print(f"数据库路径: {crawler.db_path}")
    
    print("测试通过: 成功获取所有爬虫实例")

def test_get_all_crawlers():
    """测试获取所有爬虫实例"""
    print("\n===== 测试获取所有爬虫实例 =====")
    crawlers = get_all_crawlers(use_source_db=True)
    assert len(crawlers) > 0, "爬虫实例列表为空"
    
    for crawler in crawlers:
        print(f"爬虫类型: {type(crawler).__name__}")
        print(f"爬虫来源: {crawler.source}")
        print(f"数据库路径: {crawler.db_path}")
    
    print("测试通过: 成功获取所有爬虫实例")

def test_fetch_page():
    """测试获取页面内容"""
    print("\n===== 测试获取页面内容 =====")
    sources = get_crawler_sources()
    
    test_urls = {
        'eastmoney': 'https://finance.eastmoney.com/',
        'sina': 'https://finance.sina.com.cn/'
    }
    
    for source in sources:
        if source not in test_urls:
            continue
            
        print(f"测试获取页面: {source}")
        crawler = get_crawler(source)
        url = test_urls[source]
        
        print(f"获取页面: {url}")
        html = crawler.fetch_page(url)
        
        assert html is not None, f"获取页面失败: {url}"
        assert len(html) > 1000, f"页面内容过短: {len(html)}"
        
        print(f"页面内容长度: {len(html)}")
    
    print("测试通过: 成功获取页面内容")

def test_crawl_single_news():
    """测试爬取单条新闻"""
    print("\n===== 测试爬取单条新闻 =====")
    
    test_urls = {
        'eastmoney': 'https://finance.eastmoney.com/a/202503162023397539.html',
        'sina': 'https://finance.sina.com.cn/jjxw/2025-03-16/doc-inaepkfn2345678.shtml'
    }
    
    for source, url in test_urls.items():
        try:
            print(f"测试爬取新闻: {source}")
            crawler = get_crawler(source, use_source_db=True)
            
            if hasattr(crawler, 'crawl_news_detail'):
                print(f"爬取新闻: {url}")
                news_data = crawler.crawl_news_detail(url, '测试')
                
                if news_data:
                    print(f"新闻标题: {news_data['title']}")
                    print(f"新闻作者: {news_data['author']}")
                    print(f"发布时间: {news_data['pub_time']}")
                    print(f"内容长度: {len(news_data['content'])}")
                    print(f"情感分析: {news_data['sentiment']}")
                else:
                    print(f"爬取新闻失败: {url}")
            else:
                print(f"爬虫 {source} 不支持爬取单条新闻")
        except Exception as e:
            print(f"测试爬取新闻异常: {str(e)}")

def test_mini_crawl():
    """测试小规模爬取"""
    print("\n===== 测试小规模爬取 =====")
    sources = get_crawler_sources()
    
    for source in sources:
        try:
            print(f"测试爬取: {source}")
            crawler = get_crawler(source, use_source_db=True)
            
            # 记录开始时间
            start_time = time.time()
            
            # 设置爬取参数，只爬取最近1天的新闻，最多爬取5条
            crawler.max_news_count = 5  # 如果爬虫类支持此属性
            news_list = crawler.crawl(days=1)
            
            # 记录结束时间
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            print(f"爬取完成，共爬取新闻: {len(news_list)} 条，耗时: {elapsed_time:.2f} 秒")
            
            # 打印爬取的新闻标题
            for i, news in enumerate(news_list[:5]):
                print(f"{i+1}. {news['title']}")
        except Exception as e:
            print(f"测试爬取异常: {str(e)}")

def main():
    """主函数"""
    # 设置日志
    setup_logger()
    
    print("===== 开始测试爬虫模块 =====")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试获取爬虫来源
    test_crawler_sources()
    
    # 测试获取爬虫实例
    test_get_crawler()
    
    # 测试获取所有爬虫实例
    test_get_all_crawlers()
    
    # 测试获取页面内容
    test_fetch_page()
    
    # 测试爬取单条新闻
    test_crawl_single_news()
    
    # 测试小规模爬取
    test_mini_crawl()
    
    print("\n===== 爬虫模块测试完成 =====")
    return 0

if __name__ == "__main__":
    sys.exit(main())
