#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网易财经单页测试 - 测试脚本
用于测试爬取单个网易财经页面
"""

import os
import sys
import json
import time
import datetime
import logging
from urllib.parse import urlparse
import random

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.crawlers.optimized_netease import OptimizedNeteaseCrawler, USER_AGENTS
from app.utils.text_cleaner import clean_html

# 设置日志格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def test_single_page(url=None):
    """测试爬取单个网易财经页面"""
    
    # 测试URL
    if not url:
        # 使用一些已知的网易财经文章作为测试
        test_urls = [
            "https://money.163.com/25/0225/17/IOQC0K0700259MJD.html",  # 一支药涨价21倍...
            "https://money.163.com/25/0324/07/IP96KNN900259DLP.html",  # 重庆啤酒陷于"山城往事"
            "https://money.163.com/25/0325/06/IPB1UBLP00259DLP.html",  # 爱美客的13亿赌局
            "https://money.163.com/25/0324/06/IP94LO1D00259DLP.html",  # 王老吉突然遇冷
            "https://www.163.com/money/article/I7HR77ST002581PP.html"  # 备用URL
        ]
        url = random.choice(test_urls)
    
    print(f"URL: {url}")
    
    # 检查URL是否为网易财经
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    if not ('163.com' in domain or 'netease.com' in domain):
        print(f"错误: 不是网易财经URL: {url}")
        return
    
    # 创建临时数据库
    db_path = "data/test_single.db"
    
    try:
        # 初始化爬虫
        crawler = OptimizedNeteaseCrawler(db_path=db_path, max_workers=1, timeout=30)
        
        # 正在测试的URL
        print("链接有效性检查:", "通过" if crawler.is_valid_news_url(url) else "失败")
        
        # 爬取页面
        print("开始爬取页面...")
        
        # 设置随机用户代理
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Referer": "https://www.163.com/"
        }
        
        # 直接使用requests库进行请求，不使用优化器
        import requests
        
        try:
            # 随机延迟
            time.sleep(random.uniform(1, 3))
            
            # 直接请求
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                html_content = response.text
                print(f"页面获取成功，长度: {len(html_content)} 字节")
                
                # 爬取详情
                news_data = crawler.crawl_news_detail(url)
                
                if news_data:
                    print("\n===== 爬取结果 =====")
                    print(f"标题: {news_data.get('title', '未提取')}")
                    print(f"发布时间: {news_data.get('pub_time', '未提取')}")
                    print(f"作者: {news_data.get('author', '未提取')}")
                    print(f"关键词: {news_data.get('keywords', '未提取')}")
                    
                    content_text = news_data.get('content_text', '')
                    content_len = len(content_text) if content_text else 0
                    print(f"内容长度: {content_len} 字符")
                    
                    if content_text:
                        preview = content_text[:200] + "..." if len(content_text) > 200 else content_text
                        print(f"内容预览: {preview}")
                    
                    # 保存到数据库
                    try:
                        crawler.save_news(news_data)
                        print("保存到数据库成功")
                    except Exception as e:
                        print(f"保存到数据库失败: {str(e)}")
                    
                    print("\n爬取成功!")
                else:
                    print("抓取失败!")
            else:
                print(f"页面获取失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"页面请求异常: {str(e)}")
        
    except Exception as e:
        print(f"测试异常: {str(e)}")
    finally:
        # 尝试删除测试数据库
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception as e:
            print(f"警告: 无法删除测试数据库: {db_path}")
        
        # 释放资源
        if 'crawler' in locals():
            crawler.optimizer.close()

if __name__ == "__main__":
    print("===== 网易财经单页测试 =====")
    print(f"当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print("===== 测试抓取单个网易财经页面 =====")
    test_single_page()
    
    print("\n===== 测试完成 =====") 