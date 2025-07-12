#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 财经网站爬虫测试脚本
用于测试网易财经、新浪财经和凤凰财经爬虫的功能
"""

import os
import sys
import time
import unittest
from datetime import datetime, timedelta
import json
import logging
from unittest.mock import patch, MagicMock

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.crawlers import get_crawler
from backend.app.utils.logger import configure_logger, get_logger
from backend.app.crawlers.netease import NeteaseCrawler
from backend.app.crawlers.sina import SinaCrawler
from backend.app.crawlers.ifeng import IfengCrawler
from backend.app.utils.ad_filter import AdFilter

# 配置日志
logger = configure_logger(name='test_finance_crawlers', module='test')


class TestFinanceCrawlers(unittest.TestCase):
    """财经网站爬虫测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试前的准备工作"""
        cls.temp_db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'test_finance.db')
        os.makedirs(os.path.dirname(cls.temp_db_path), exist_ok=True)
        
        # 初始化测试用的爬虫实例
        cls.netease_crawler = NeteaseCrawler(db_path=cls.temp_db_path, use_proxy=False)
        cls.sina_crawler = SinaCrawler(db_path=cls.temp_db_path, use_proxy=False)
        cls.ifeng_crawler = IfengCrawler(db_path=cls.temp_db_path, use_proxy=False)
        
        # 测试URL
        cls.test_urls = {
            'netease': {
                'home': 'https://money.163.com/',
                'article': 'https://money.163.com/25/0325/13/ISQH9B1900259DLP.html',
                'category': 'https://money.163.com/stock/'
            },
            'sina': {
                'home': 'https://finance.sina.com.cn/',
                'article': 'https://finance.sina.com.cn/money/bank/bank_hydt/2025-03-25/doc-inafeipr8760421.shtml',
                'category': 'https://finance.sina.com.cn/stock/'
            },
            'ifeng': {
                'home': 'https://finance.ifeng.com/',
                'article': 'https://finance.ifeng.com/c/8WRsbdqGsMr',
                'category': 'https://finance.ifeng.com/stock/'
            }
        }
        
        print(f"\n{'='*50}")
        print(f"开始财经网站爬虫测试")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")
    
    def setUp(self):
        """每个测试用例执行前的准备工作"""
        print(f"\n{'-'*20} 开始测试: {self._testMethodName} {'-'*20}")
    
    def tearDown(self):
        """每个测试用例执行后的清理工作"""
        print(f"{'-'*20} 测试结束: {self._testMethodName} {'-'*20}")
    
    @classmethod
    def tearDownClass(cls):
        """测试后的清理工作"""
        # 清理临时数据库文件
        if os.path.exists(cls.temp_db_path):
            try:
                os.remove(cls.temp_db_path)
                print(f"已删除临时测试数据库: {cls.temp_db_path}")
            except:
                print(f"警告: 无法删除临时测试数据库: {cls.temp_db_path}")
        
        print(f"\n{'='*50}")
        print(f"财经网站爬虫测试结束")
        print(f"测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")
    
    # 基本功能测试
    def test_crawler_initialization(self):
        """测试爬虫初始化"""
        print("测试爬虫初始化...")
        
        # 网易财经
        self.assertEqual(self.netease_crawler.source, "网易财经")
        self.assertEqual(self.netease_crawler.db_path, self.temp_db_path)
        
        # 新浪财经
        self.assertEqual(self.sina_crawler.source, "新浪财经")
        self.assertEqual(self.sina_crawler.db_path, self.temp_db_path)
        
        # 凤凰财经
        self.assertEqual(self.ifeng_crawler.source, "凤凰财经")
        self.assertEqual(self.ifeng_crawler.db_path, self.temp_db_path)
        
        print("爬虫初始化测试通过")
    
    # 页面获取测试
    def test_fetch_page(self):
        """测试页面获取功能"""
        print("测试页面获取功能...")
        
        # 网易财经
        html = self.netease_crawler.fetch_page(self.test_urls['netease']['home'])
        self.assertIsNotNone(html)
        self.assertTrue(len(html) > 1000)
        self.assertTrue('网易财经' in html)
        print(f"网易财经首页获取成功，内容长度: {len(html)}")
        
        # 新浪财经
        html = self.sina_crawler.fetch_page(self.test_urls['sina']['home'])
        self.assertIsNotNone(html)
        self.assertTrue(len(html) > 1000)
        self.assertTrue('新浪财经' in html)
        print(f"新浪财经首页获取成功，内容长度: {len(html)}")
        
        # 凤凰财经
        html = self.ifeng_crawler.fetch_page(self.test_urls['ifeng']['home'])
        self.assertIsNotNone(html)
        self.assertTrue(len(html) > 1000)
        self.assertTrue('凤凰财经' in html or '凤凰网财经' in html)
        print(f"凤凰财经首页获取成功，内容长度: {len(html)}")
    
    # URL提取测试
    def test_extract_links(self):
        """测试新闻链接提取功能"""
        print("测试新闻链接提取功能...")
        
        # 网易财经
        html = self.netease_crawler.fetch_page(self.test_urls['netease']['home'])
        links = self.netease_crawler.extract_news_links_from_home(html, "财经")
        self.assertTrue(len(links) > 0)
        print(f"网易财经提取到 {len(links)} 个新闻链接")
        
        # 新浪财经
        html = self.sina_crawler.fetch_page(self.test_urls['sina']['home'])
        links = self.sina_crawler.extract_news_links_from_home(html, "财经")
        self.assertTrue(len(links) > 0)
        print(f"新浪财经提取到 {len(links)} 个新闻链接")
        
        # 凤凰财经
        html = self.ifeng_crawler.fetch_page(self.test_urls['ifeng']['home'])
        links = self.ifeng_crawler.extract_news_links_from_home(html, "财经")
        self.assertTrue(len(links) > 0)
        print(f"凤凰财经提取到 {len(links)} 个新闻链接")
    
    # 新闻详情爬取测试
    def test_crawl_news_detail(self):
        """测试新闻详情爬取功能"""
        print("测试新闻详情爬取功能...")
        
        # 网易财经
        news = self.netease_crawler.crawl_news_detail(self.test_urls['netease']['article'], "股票")
        if news:
            self.assertIsNotNone(news.get('title'))
            self.assertIsNotNone(news.get('content'))
            self.assertIsNotNone(news.get('pub_time'))
            print(f"网易财经文章爬取成功: {news.get('title')}")
        else:
            print("注意: 网易财经文章爬取失败，可能是测试链接已失效")
        
        # 新浪财经
        news = self.sina_crawler.crawl_news_detail(self.test_urls['sina']['article'], "理财")
        if news:
            self.assertIsNotNone(news.get('title'))
            self.assertIsNotNone(news.get('content'))
            self.assertIsNotNone(news.get('pub_time'))
            print(f"新浪财经文章爬取成功: {news.get('title')}")
        else:
            print("注意: 新浪财经文章爬取失败，可能是测试链接已失效")
        
        # 凤凰财经
        news = self.ifeng_crawler.crawl_news_detail(self.test_urls['ifeng']['article'], "财经")
        if news:
            self.assertIsNotNone(news.get('title'))
            self.assertIsNotNone(news.get('content'))
            self.assertIsNotNone(news.get('pub_time'))
            print(f"凤凰财经文章爬取成功: {news.get('title')}")
        else:
            print("注意: 凤凰财经文章爬取失败，可能是测试链接已失效")
    
    # 编码处理测试
    def test_encoding_handling(self):
        """测试编码处理功能"""
        print("测试编码处理功能...")
        
        # 模拟包含中文和特殊字符的HTML
        test_html = """
        <html>
        <body>
            <div>测试中文</div>
            <div>Unicode编码：\u4e2d\u56fd</div>
            <div>HTML实体：&quot;引号&quot;, &amp;符号</div>
            <div>URL编码：%E6%B5%8B%E8%AF%95</div>
        </body>
        </html>
        """
        
        # 新浪财经的编码处理（新浪财经有特殊的编码处理方法）
        with patch('requests.Response') as mock_response:
            mock_response.text = test_html
            mock_response.content = test_html.encode('utf-8')
            mock_response.encoding = 'ISO-8859-1'
            
            result = self.sina_crawler.fetch_page("https://example.com/")
            
            # 验证编码是否正确处理
            self.assertIn("测试中文", result)
            self.assertIn("中国", result)  # Unicode解码后
            self.assertIn('"引号"', result)  # HTML实体解码后
            self.assertIn("测试", result)  # URL编码解码后
            
            print("编码处理测试通过")
    
    # 广告过滤测试
    def test_ad_filter(self):
        """测试广告过滤功能"""
        print("测试广告过滤功能...")
        
        # 测试广告URL
        ad_urls = [
            "https://money.163.com/special/app/download.html",
            "https://finance.sina.com.cn/app/sfa_download/index.shtml",
            "https://finance.ifeng.com/app/download/index.shtml"
        ]
        
        # 测试广告内容
        ad_content = """
        点击立即下载APP，享受专属福利！
        新人专享，注册即送优惠券！
        扫码下载网易财经客户端，随时随地查看行情。
        """
        
        # 初始化广告过滤器
        netease_ad_filter = AdFilter(source_name="网易财经")
        sina_ad_filter = AdFilter(source_name="新浪财经")
        ifeng_ad_filter = AdFilter(source_name="凤凰财经")
        
        # 测试URL过滤
        self.assertTrue(netease_ad_filter.is_ad_url(ad_urls[0]))
        self.assertTrue(sina_ad_filter.is_ad_url(ad_urls[1]))
        self.assertTrue(ifeng_ad_filter.is_ad_url(ad_urls[2]))
        
        # 测试内容过滤
        self.assertTrue(netease_ad_filter.is_ad_content(ad_content))
        self.assertTrue(sina_ad_filter.is_ad_content(ad_content))
        self.assertTrue(ifeng_ad_filter.is_ad_content(ad_content))
        
        print("广告过滤测试通过")
    
    # 反爬虫机制测试
    def test_anti_crawling(self):
        """测试反爬虫机制"""
        print("测试反爬虫机制...")
        
        # 测试随机休眠
        start_time = time.time()
        self.netease_crawler.random_sleep(0.1, 0.2)
        elapsed = time.time() - start_time
        self.assertTrue(0.1 <= elapsed <= 0.3)
        
        # 测试随机User-Agent
        ua1 = self.sina_crawler.get_random_user_agent()
        ua2 = self.sina_crawler.get_random_user_agent()
        # 多次获取可能会相同，所以只测试它们不为空
        self.assertTrue(ua1)
        self.assertTrue(ua2)
        
        print("反爬虫机制测试通过")
    
    # 小规模爬取测试
    def test_mini_crawl(self):
        """测试小规模爬取"""
        print("测试小规模爬取...")
        
        # 使用小参数进行爬取测试
        try:
            # 网易财经，爬取1天内的1条新闻
            result = self.netease_crawler.crawl(days=1, max_news=1)
            print(f"网易财经爬取结果: {len(result)} 条新闻")
            
            # 新浪财经，爬取1天内第1页的新闻
            result = self.sina_crawler.crawl(days=1, max_pages=1)
            print(f"新浪财经爬取结果: {len(result)} 条新闻")
            
            # 凤凰财经，爬取1天内的1条新闻
            result = self.ifeng_crawler.crawl(days=1, max_news=1)
            print(f"凤凰财经爬取结果: {len(result)} 条新闻")
            
        except Exception as e:
            self.fail(f"小规模爬取测试失败: {str(e)}")
            
        print("小规模爬取测试通过")
    
    # 异常处理测试
    def test_exception_handling(self):
        """测试异常处理机制"""
        print("测试异常处理机制...")
        
        # 无效URL测试
        invalid_url = "https://nonexistent.example.com/"
        
        # 网易财经
        result = self.netease_crawler.fetch_page(invalid_url)
        self.assertIsNone(result)
        
        # 新浪财经
        result = self.sina_crawler.fetch_page(invalid_url)
        self.assertIsNone(result)
        
        # 凤凰财经
        result = self.ifeng_crawler.fetch_page(invalid_url)
        self.assertIsNone(result)
        
        print("异常处理测试通过")


def main():
    """主函数"""
    unittest.main(verbosity=2)

if __name__ == "__main__":
    main() 