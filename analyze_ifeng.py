#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
凤凰财经网页结构分析工具
用于分析凤凰财经网页的HTML结构，帮助调整爬虫选择器
"""

import requests
from bs4 import BeautifulSoup
import sys
import time
import random

# 测试URL列表
TEST_URLS = [
    "https://finance.ifeng.com/c/8eYGOiALsrj",
    "https://finance.ifeng.com/c/8e9gpxVG3LS",
    "http://finance.ifeng.com/c/8NTGyMSRgoK",
    "https://finance.ifeng.com/c/8iEGpltD0tx",
    "http://finance.ifeng.com/c/8NVsU0iBjzs",
    "https://finance.ifeng.com/c/8cRcXnB0Mw7",
    "https://finance.ifeng.com/c/8NTGyMSRgoK"
]

# 最新的User-Agent列表
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
]

# 可能的内容选择器
CONTENT_SELECTORS = [
    'div.main_content',
    'div.text_area',
    'div.article-main',
    'div.text-3w2e3DBc',
    'div.main-content-section',
    'div.js-video-content',
    'div.content',
    'div.article_content',
    'article.article-main-content',
    'div.detailArticle-content',
    'div#artical_real',
    'div.yc-artical',
    'div.art_content',
    'div.article-cont',
    'div.news-content',
    'div.news_txt',
    'div.c-article-content'
]

# 可能的标题选择器
TITLE_SELECTORS = [
    'h1.title',
    'h1.headline-title',
    'div.headline-title',
    'h1.news-title-h1',
    'h1.yc-title',
    'h1.c-article-title',
    'h1.news_title'
]

def analyze_page(url):
    """分析页面结构，查找匹配的选择器"""
    print(f"\n分析URL: {url}")
    
    # 随机选择一个User-Agent
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    try:
        # 请求页面
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 解析HTML
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 检查标题选择器
        print("检查标题选择器:")
        for selector in TITLE_SELECTORS:
            title_elem = soup.select_one(selector)
            if title_elem:
                print(f"  ✓ {selector}: {title_elem.text.strip()[:50]}...")
            else:
                print(f"  ✗ {selector}: 未找到")
        
        # 检查内容选择器
        print("\n检查内容选择器:")
        for selector in CONTENT_SELECTORS:
            content_elem = soup.select_one(selector)
            if content_elem:
                content_text = content_elem.get_text('\n').strip()
                content_preview = content_text[:100] + "..." if len(content_text) > 100 else content_text
                print(f"  ✓ {selector}: {content_preview}")
            else:
                print(f"  ✗ {selector}: 未找到")
        
        # 查找所有可能的内容容器
        print("\n查找其他可能的内容容器:")
        potential_content_divs = soup.find_all(['div', 'article'], class_=True)
        for div in potential_content_divs:
            # 检查是否可能是内容容器
            text_length = len(div.get_text().strip())
            if text_length > 500 and not any(div.select_one(selector) for selector in CONTENT_SELECTORS):
                class_name = ' '.join(div.get('class', []))
                tag_name = div.name
                selector = f"{tag_name}.{class_name.replace(' ', '.')}" if class_name else tag_name
                print(f"  可能的内容容器: {selector} (文本长度: {text_length})")
                
        # 查找页面中的所有iframe
        print("\n检查iframe:")
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            print(f"  发现iframe: {iframe.get('src', 'No src')} (id: {iframe.get('id', 'No id')})")
        
    except Exception as e:
        print(f"分析页面出错: {str(e)}")

def main():
    """主函数"""
    print("凤凰财经网页结构分析工具")
    print("=" * 50)
    
    # 如果提供了URL参数，则只分析该URL
    if len(sys.argv) > 1:
        analyze_page(sys.argv[1])
    else:
        # 否则分析测试URL列表
        for url in TEST_URLS:
            analyze_page(url)
            # 随机休眠，避免请求过快
            time.sleep(random.uniform(1, 3))

if __name__ == "__main__":
    main()
