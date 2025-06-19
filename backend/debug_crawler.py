#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试东方财富爬虫的测试脚本
"""

import os
import sys
import logging

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def test_eastmoney_crawler():
    """测试东方财富爬虫"""
    try:
        # 1. 测试爬虫导入
        logger.info("=== 测试爬虫导入 ===")
        from backend.app.crawlers.eastmoney import EastMoneyCrawler
        logger.info("✅ 东方财富爬虫导入成功")
        
        # 2. 测试爬虫实例化
        logger.info("=== 测试爬虫实例化 ===")
        db_path = os.path.join('data', 'eastmoney.db')
        crawler = EastMoneyCrawler(db_path=db_path)
        logger.info(f"✅ 东方财富爬虫实例化成功，数据库路径: {db_path}")
        
        # 3. 测试基金分类URL获取
        logger.info("=== 测试基金分类URL获取 ===")
        fund_urls = crawler.get_category_url('基金')
        logger.info(f"基金分类URLs: {fund_urls}")
        
        # 4. 测试网页链接提取
        logger.info("=== 测试网页链接提取 ===")
        if fund_urls:
            test_url = fund_urls[0]
            logger.info(f"测试URL: {test_url}")
            
            # 测试页面获取
            html = crawler.fetch_page_with_requests(test_url)
            if html:
                logger.info(f"✅ 成功获取页面内容，长度: {len(html)} 字符")
                
                # 测试链接提取
                links = crawler.extract_news_links(test_url)
                logger.info(f"提取到 {len(links)} 个新闻链接")
                if links:
                    logger.info("前5个链接:")
                    for i, link in enumerate(links[:5]):
                        logger.info(f"  {i+1}. {link}")
                else:
                    logger.warning("⚠️ 没有提取到新闻链接")
            else:
                logger.error("❌ 无法获取页面内容")
        
        # 5. 测试新闻详情爬取
        logger.info("=== 测试新闻详情爬取 ===")
        if fund_urls and hasattr(crawler, 'extract_news_links'):
            html = crawler.fetch_page_with_requests(fund_urls[0])
            if html:
                links = crawler.extract_news_links(fund_urls[0])
                if links:
                    test_detail_url = links[0]
                    logger.info(f"测试详情URL: {test_detail_url}")
                    
                    detail = crawler.crawl_news_detail(test_detail_url, '基金')
                    if detail:
                        logger.info(f"✅ 成功爬取新闻详情:")
                        logger.info(f"  标题: {detail.get('title', 'N/A')}")
                        logger.info(f"  发布时间: {detail.get('pub_time', 'N/A')}")
                        logger.info(f"  作者: {detail.get('author', 'N/A')}")
                        logger.info(f"  内容长度: {len(detail.get('content', '') or '')}")
                    else:
                        logger.error("❌ 无法爬取新闻详情")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_url_access():
    """测试URL访问能力"""
    logger.info("=== 测试URL访问能力 ===")
    import requests
    
    test_urls = [
        "https://fund.eastmoney.com/",
        "https://fund.eastmoney.com/news/cjjj.html",
        "https://finance.eastmoney.com/",
        "https://www.eastmoney.com/"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    for url in test_urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                logger.info(f"✅ {url} - 状态码: {response.status_code}, 内容长度: {len(response.text)}")
            else:
                logger.warning(f"⚠️ {url} - 状态码: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ {url} - 访问失败: {e}")

if __name__ == "__main__":
    logger.info("开始调试东方财富爬虫")
    
    # 确保数据目录存在
    os.makedirs('data', exist_ok=True)
    
    # 测试URL访问
    test_url_access()
    
    # 测试爬虫
    success = test_eastmoney_crawler()
    
    if success:
        logger.info("🎉 调试测试完成！")
    else:
        logger.error("💥 调试测试失败！")
