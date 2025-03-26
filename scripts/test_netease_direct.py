#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网易财经直接测试脚本
这个脚本直接使用requests获取网易财经文章并解析，不依赖爬虫类
用于确定当前的网页结构和选择器
"""

import os
import sys
import random
import time
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin
import datetime
import logging
import json

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 用户代理列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def get_latest_news_urls(count=5):
    """从网易财经首页获取最新的新闻链接"""
    try:
        # 随机选择一个User-Agent
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0"
        }
        
        # 访问网易财经首页
        homepage_url = "https://money.163.com/"
        print(f"正在获取网易财经首页: {homepage_url}")
        response = requests.get(homepage_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"获取首页失败，状态码: {response.status_code}")
            return []
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有新闻链接
        news_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'money.163.com' in href or ('163.com' in href and '/money/' in href):
                # 确保是完整URL
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(homepage_url, href)
                
                # 检查是否是新闻文章URL，使用正则表达式匹配常见的网易财经文章URL格式
                if re.search(r'163\.com/\d+/\d+/\d+/\w+\.html', href) or \
                   re.search(r'163\.com/money/article/\w+\.html', href):
                    news_links.append(href)
        
        # 去重
        news_links = list(set(news_links))
        print(f"从首页找到 {len(news_links)} 个新闻链接")
        
        # 返回指定数量的链接
        return news_links[:count]
    except Exception as e:
        print(f"获取最新新闻链接时出错: {str(e)}")
        return []

def clean_html_text(html_text):
    """简单清理HTML文本"""
    # 创建BeautifulSoup对象
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # 删除脚本和样式
    for script in soup(["script", "style"]):
        script.extract()
    
    # 获取文本
    text = soup.get_text()
    
    # 打破成行，然后合并成段落
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text

def test_article(url=None):
    """测试获取并解析网易财经文章"""
    # 如果未提供URL，获取最新的新闻链接
    if not url:
        latest_urls = get_latest_news_urls(count=5)
        if latest_urls:
            url = latest_urls[0]  # 使用第一个链接
            print(f"使用最新链接: {url}")
        else:
            url = "https://money.163.com/special/00259BVP/yaowu.html"
            print(f"使用备用链接: {url}")
    
    # 随机选择一个User-Agent
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.163.com/",
        "Upgrade-Insecure-Requests": "1"
    }
    
    try:
        # 添加随机延迟
        time.sleep(random.uniform(1, 3))
        
        # 发送请求
        print(f"正在获取页面: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"获取页面失败，状态码: {response.status_code}")
            return
        
        # 保存原始HTML以便调试
        with open("data/debug_page.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("已保存原始HTML到 data/debug_page.html")
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找标题
        print("\n--- 查找标题 ---")
        title_selectors = [
            "h1.post_title",  # 常见网易文章标题选择器
            "h1.title",       # 另一个常见选择器
            ".article-header h1",  # 另一种布局
            "h1"              # 通用h1标签
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                print(f"找到标题 使用选择器 '{selector}': {title_elem.text.strip()}")
                break
        else:
            print("未找到标题")
        
        # 查找发布时间
        print("\n--- 查找发布时间 ---")
        time_selectors = [
            ".post_info time",
            ".post_time_source",
            ".date",
            ".time"
        ]
        
        for selector in time_selectors:
            time_elem = soup.select_one(selector)
            if time_elem:
                print(f"找到发布时间 使用选择器 '{selector}': {time_elem.text.strip()}")
                break
        else:
            print("未找到发布时间")
        
        # 查找作者/来源
        print("\n--- 查找作者/来源 ---")
        author_selectors = [
            ".post_author",
            ".author",
            ".source",
            ".pb-source-wrap"
        ]
        
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                print(f"找到作者/来源 使用选择器 '{selector}': {author_elem.text.strip()}")
                break
        else:
            print("未找到作者/来源")
        
        # 查找正文内容
        print("\n--- 查找正文内容 ---")
        content_selectors = [
            "#content",      # 常见的主要内容选择器
            ".post_body",    # 另一个常见的内容选择器
            ".post_text",    # 第三种常见选择器
            ".article-content", # 其他可能的选择器
            "article"        # 通用HTML5文章标签
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 清理内容，删除脚本和样式
                for script in content_elem.find_all('script'):
                    script.decompose()
                for style in content_elem.find_all('style'):
                    style.decompose()
                
                content_text = clean_html_text(str(content_elem))
                content_length = len(content_text)
                
                print(f"找到内容 使用选择器 '{selector}'")
                print(f"内容长度: {content_length} 字符")
                
                # 显示内容预览
                if content_length > 0:
                    preview = content_text[:200] + "..." if content_length > 200 else content_text
                    print(f"内容预览: {preview}")
                    
                    # 保存内容到文件
                    with open("data/article_content.txt", "w", encoding="utf-8") as f:
                        f.write(content_text)
                    print("已保存文章内容到 data/article_content.txt")
                break
        else:
            print("未找到正文内容")
        
        # 查找图片
        print("\n--- 查找图片 ---")
        if content_elem:
            images = content_elem.find_all('img', src=True)
            if images:
                print(f"找到 {len(images)} 张图片:")
                for i, img in enumerate(images[:3]):  # 只显示前3张
                    print(f"  图片 {i+1}: {img['src']}")
                if len(images) > 3:
                    print(f"  ...还有 {len(images)-3} 张图片")
            else:
                print("未找到图片")
        
        # 生成页面结构的简要描述
        print("\n--- 页面结构简要描述 ---")
        main_tags = ['header', 'nav', 'main', 'article', 'section', 'aside', 'footer']
        for tag in main_tags:
            elements = soup.find_all(tag)
            if elements:
                print(f"找到 {len(elements)} 个 <{tag}> 元素")
        
        # 查找主要的div(有明确id或class的)
        main_divs = []
        for div in soup.find_all('div', id=True):
            main_divs.append(f"div#{div['id']}")
        
        for div in soup.find_all('div', class_=True):
            if len(div['class']) > 0 and not any(c.startswith(('js-', 'JS_')) for c in div['class']):
                main_divs.append(f"div.{'.'.join(div['class'])}")
        
        if main_divs:
            print(f"主要的div元素: {', '.join(main_divs[:5])}...")
        
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("===== 网易财经直接测试 =====")
    print(f"当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 40)
    
    # 测试获取并解析网易财经文章
    url = None
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    test_article(url)
    
    # 如果成功获取了链接，也用爬虫类测试一下
    if url and requests.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}).status_code == 200:
        print("\n\n===== 使用爬虫类测试同一URL =====")
        try:
            # 导入爬虫类
            from app.crawlers.optimized_netease import OptimizedNeteaseCrawler
            
            # 创建爬虫实例
            crawler = OptimizedNeteaseCrawler(db_path="data/test_crawler.db", max_workers=1, timeout=30)
            
            # 爬取新闻
            print(f"使用爬虫类爬取URL: {url}")
            news_data = crawler.crawl_news_detail(url)
            
            if news_data:
                print("\n爬虫类爬取结果:")
                print(f"标题: {news_data.get('title', '未提取')}")
                print(f"发布时间: {news_data.get('pub_time', '未提取')}")
                print(f"作者: {news_data.get('author', '未提取')}")
                print(f"关键词: {news_data.get('keywords', '未提取')}")
                print(f"图片数量: {len(json.loads(news_data.get('images', '[]')))}")
                
                content_text = news_data.get('content_text', '')
                content_len = len(content_text) if content_text else 0
                print(f"内容长度: {content_len} 字符")
                
                if content_text:
                    preview = content_text[:200] + "..." if len(content_text) > 200 else content_text
                    print(f"内容预览: {preview}")
                
                # 保存爬取的内容进行对比
                with open("data/crawler_content.txt", "w", encoding="utf-8") as f:
                    f.write(content_text)
                print("已保存爬虫爬取的内容到 data/crawler_content.txt")
                
                print("\n爬虫类爬取成功!")
            else:
                print("爬虫类爬取失败!")
                
            # 释放资源
            crawler.optimizer.close()
            
        except Exception as e:
            print(f"使用爬虫类测试时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n===== 测试完成 =====") 