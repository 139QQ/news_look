#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 优化爬虫测试脚本
用于测试优化后的网易财经、新浪财经和凤凰财经爬虫
"""

import os
import sys
import time
import json
import traceback
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.crawlers.optimized_netease import OptimizedNeteaseCrawler
from app.utils.logger import configure_logger, get_logger
from app.utils.crawler_optimizer import CrawlerOptimizer

# 配置日志
logger = configure_logger(name='test_optimized_crawlers', level='DEBUG')

def test_network_status():
    """测试网络状态"""
    print("\n===== 测试网络状态 =====")
    try:
        optimizer = CrawlerOptimizer(max_workers=3, timeout=30)
        print("初始化CrawlerOptimizer成功")
        
        print("开始检测网络状态...")
        status = optimizer.check_network_status()
        
        print(f"网络状态检测结果:")
        for site, info in status.items():
            status_str = info.get('status')
            response_time = info.get('response_time', 0)
            status_code = info.get('status_code', 'N/A')
            
            print(f"  - {site}: {status_str}, 响应时间: {response_time:.2f}秒, 状态码: {status_code}")
        
        # 清理资源
        optimizer.close()
    except Exception as e:
        print(f"测试网络状态时出错: {str(e)}")
        traceback.print_exc()

def test_optimized_netease():
    """测试优化的网易财经爬虫"""
    print("\n===== 测试优化的网易财经爬虫 =====")
    
    # 创建临时测试数据库路径
    test_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'test_optimized.db')
    os.makedirs(os.path.dirname(test_db_path), exist_ok=True)
    print(f"临时数据库路径: {test_db_path}")
    
    crawler = None
    try:
        # 创建爬虫实例
        print("创建OptimizedNeteaseCrawler实例...")
        crawler = OptimizedNeteaseCrawler(
            db_path=test_db_path,
            use_source_db=True,
            max_workers=3,
            timeout=30,
            enable_async=False
        )
        print("爬虫实例创建成功")
        
        # 测试链接验证逻辑
        print("\n测试URL验证逻辑:")
        test_urls = [
            "https://money.163.com/23/0521/13/I6T8A77B00259DLP.html",  # 标准网易财经URL
            "https://money.163.com/article/I6T8A77B00259DLP.html",     # 另一种格式
            "https://www.163.com/money/article/I6T8A77B00259DLP.html", # www域名
            "http://money.163.com/23/0521/13/I6T8A77B00259DLP.html",   # http协议
            "//money.163.com/23/0521/13/I6T8A77B00259DLP.html",        # 相对协议
            "https://money.163.com/special/app/download.html",         # 广告URL
            "https://other.163.com/23/0521/13/I6T8A77B00259DLP.html",  # 非财经域名
        ]
        
        for url in test_urls:
            is_valid = crawler.is_valid_news_url(url)
            print(f"  URL: {url}")
            print(f"  有效: {is_valid}")
            print()
        
        # 记录开始时间
        start_time = time.time()
        
        # 先检查网站状态
        print("\n检查网易财经网站状态...")
        site_accessible = crawler.check_website_status()
        print(f"网站状态: {'可访问' if site_accessible else '不可访问'}")
        
        if not site_accessible:
            print("网站不可访问，跳过爬取测试")
            return
        
        # 获取主页
        print("\n获取网易财经首页...")
        home_url = "https://money.163.com/"
        html = crawler.fetch_page(home_url)
        if html:
            print(f"成功获取首页，内容长度: {len(html)} 字节")
            
            # 提取链接
            print("从首页提取新闻链接...")
            news_links = crawler.extract_news_links_from_home(html)
            print(f"从首页提取到 {len(news_links)} 个新闻链接")
            
            if news_links:
                print("前10个链接:")
                for i, link in enumerate(news_links[:10]):
                    print(f"  {i+1}. {link}")
            else:
                print("警告: 未从首页提取到新闻链接")
        else:
            print("警告: 无法获取网易财经首页")
        
        # 爬取最近1天的最多3条新闻
        print("\n开始爬取网易财经新闻...")
        news_list = crawler.crawl(days=1, max_news=3)
        
        # 记录结束时间
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 输出结果
        print(f"\n爬取完成，共爬取 {len(news_list)} 条新闻，耗时: {elapsed_time:.2f} 秒")
        
        # 输出爬取的新闻标题
        if news_list:
            print("\n爬取的新闻:")
            for i, news in enumerate(news_list):
                print(f"  {i+1}. {news['title']} | {news['pub_time']} | {news['url']}")
        else:
            print("警告: 未爬取到任何新闻")
        
        # 获取并输出爬虫统计信息
        stats = crawler.get_crawl_stats()
        
        print("\n爬虫统计信息:")
        print(f"  - 总URL数: {stats['total_urls']}")
        print(f"  - 成功URL数: {stats['success_urls']}")
        print(f"  - 失败URL数: {stats['failed_urls']}")
        print(f"  - 过滤URL数: {stats['filtered_count']}")
        print(f"  - 错误数: {stats['error_count']}")
        print(f"  - 平均处理时间: {stats['avg_process_time']:.2f} 秒/URL")
        print(f"  - 爬取速率: {stats.get('urls_per_second', 0):.2f} URL/秒")
        print(f"  - 总耗时: {stats.get('elapsed_time', 0):.2f} 秒")
        
        # 获取并输出优化器统计信息
        optimizer_stats = crawler.get_optimizer_stats()
        
        print("\n优化器统计信息:")
        for site, site_stats in optimizer_stats.items():
            print(f"  - {site}:")
            print(f"      请求总数: {site_stats['total_requests']}")
            print(f"      成功数: {site_stats['success']}")
            print(f"      失败数: {site_stats['failure']}")
            print(f"      成功率: {site_stats['success_rate']:.2f}")
        
    except Exception as e:
        print(f"测试优化的网易财经爬虫时出错: {str(e)}")
        traceback.print_exc()
    finally:
        # 删除测试数据库
        if os.path.exists(test_db_path):
            try:
                os.remove(test_db_path)
                print(f"已删除测试数据库: {test_db_path}")
            except:
                print(f"警告: 无法删除测试数据库: {test_db_path}")

def main():
    """主函数"""
    try:
        print("===== 开始测试优化爬虫 =====")
        print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Python版本: {sys.version}")
        print(f"工作目录: {os.getcwd()}")
        
        # 测试网络状态
        test_network_status()
        
        # 测试优化的网易财经爬虫
        test_optimized_netease()
        
        print("\n===== 优化爬虫测试完成 =====")
        return 0
    except Exception as e:
        print(f"测试过程中出现未捕获的异常: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 