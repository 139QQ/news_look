#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单测试新浪财经爬虫
"""

import traceback
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("SinaCrawlerTest")

try:
    logger.info("正在导入SinaCrawler...")
    from app.crawlers.sina import SinaCrawler
    logger.info("导入成功")
    
    logger.info("正在初始化爬虫...")
    crawler = SinaCrawler()
    logger.info("初始化成功")
    
    # 测试URL验证
    test_url = "https://finance.sina.com.cn/stock/2023-03-29/doc-test.shtml"
    logger.info("测试URL验证: %s", test_url)
    is_valid = crawler.is_valid_news_url(test_url)
    logger.info("URL验证结果: %s", '有效' if is_valid else '无效')
    
    # 测试提取链接
    test_html = """
    <html>
    <body>
        <a href="https://finance.sina.com.cn/stock/2023-03-29/doc-test.shtml">测试新闻</a>
    </body>
    </html>
    """
    logger.info("测试提取链接...")
    links = crawler.extract_news_links_from_home(test_html, "测试")
    logger.info("提取到 %s 个链接", len(links))
    
    # 测试爬取股票页面
    logger.info("测试爬取股票页面...")
    stock_url = crawler.CATEGORY_URLS.get('股票')
    if stock_url:
        logger.info("股票页面URL: %s", stock_url)
        html = crawler.fetch_page(stock_url)
        if html:
            logger.info("成功获取股票页面内容")
            # 提取链接
            links = crawler.extract_news_links(html, "股票")
            logger.info("从股票页面提取到 %s 个链接", len(links))
            
            # 测试爬取第一个新闻
            if links:
                first_link = links[0]
                logger.info("测试爬取新闻: %s", first_link)
                news_data = crawler.crawl_news_detail(first_link, "股票")
                if news_data:
                    logger.info("成功爬取新闻: %s", news_data['title'])
                    logger.info("新闻发布时间: %s", news_data['pub_time'])
                    logger.info("新闻内容长度: %s 字符", len(news_data['content']))
                    logger.info("新闻关键词: %s", news_data['keywords'])
                else:
                    logger.warning("爬取新闻失败")
        else:
            logger.warning("获取股票页面失败")
    else:
        logger.warning("股票页面URL不存在")
    
    logger.info("测试完成")
except Exception as e:
    logger.error("错误: %s", str(e))
    traceback.print_exc()
