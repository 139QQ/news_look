#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新浪财经爬虫完整测试
包含单元测试、集成测试和数据验证
"""

import os
import sys
import unittest
import tempfile
import sqlite3
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.crawlers.sina import SinaCrawler
from backend.app.utils.logger import get_crawler_logger


class TestSinaCrawlerUnit(unittest.TestCase):
    """新浪财经爬虫单元测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, 'test_sina.db')
        
        # 创建测试爬虫实例
        self.crawler = SinaCrawler(db_path=self.test_db_path)
        
        # 测试数据
        self.sample_news_data = {
            'id': 'test123',
            'title': '测试新闻标题',
            'content': '这是一个测试新闻内容，用于验证爬虫功能是否正常工作。',
            'url': 'https://finance.sina.com.cn/test/news/123.html',
            'source': '新浪财经',
            'pub_time': '2023-01-01 12:00:00',
            'author': '测试作者',
            'category': '财经'
        }
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_crawler_initialization(self):
        """测试爬虫初始化"""
        self.assertEqual(self.crawler.source, '新浪财经')
        self.assertIsNotNone(self.crawler.db_manager)
        self.assertIsNotNone(self.crawler.category_urls)
        self.assertIn('财经', self.crawler.category_urls)
        self.assertIn('股票', self.crawler.category_urls)
    
    def test_get_random_user_agent(self):
        """测试获取随机User-Agent"""
        ua1 = self.crawler.get_random_user_agent()
        ua2 = self.crawler.get_random_user_agent()
        
        self.assertIsInstance(ua1, str)
        self.assertIsInstance(ua2, str)
        self.assertGreater(len(ua1), 50)  # User-Agent应该足够长
    
    def test_get_headers(self):
        """测试获取请求头"""
        headers = self.crawler.get_headers()
        
        required_headers = ['User-Agent', 'Accept', 'Accept-Language', 'Referer']
        for header in required_headers:
            self.assertIn(header, headers)
        
        self.assertIn('finance.sina.com.cn', headers['Referer'])
    
    def test_get_category_url(self):
        """测试获取分类URL"""
        # 测试有效分类
        finance_urls = self.crawler.get_category_url('财经')
        self.assertIsInstance(finance_urls, list)
        self.assertGreater(len(finance_urls), 0)
        
        for url in finance_urls:
            self.assertIn('finance.sina.com.cn', url)
        
        # 测试无效分类
        invalid_urls = self.crawler.get_category_url('无效分类')
        self.assertEqual(invalid_urls, [])
    
    def test_is_valid_news_url(self):
        """测试URL有效性检查"""
        # 有效URL
        valid_urls = [
            'https://finance.sina.com.cn/news/article123.html',
            'https://finance.sina.com.cn/stock/news/456.html'
        ]
        
        for url in valid_urls:
            self.assertTrue(self.crawler._is_valid_news_url(url))
        
        # 无效URL
        invalid_urls = [
            'javascript:void(0)',
            'mailto:test@sina.com',
            'https://finance.sina.com.cn/app/download',
            'https://finance.sina.com.cn/image.jpg',
            'https://other-site.com/news.html',
            None,
            ''
        ]
        
        for url in invalid_urls:
            self.assertFalse(self.crawler._is_valid_news_url(url))
    
    def test_preprocess_news_data(self):
        """测试新闻数据预处理"""
        # 测试完整数据
        processed = self.crawler.preprocess_news_data(self.sample_news_data.copy())
        self.assertIsNotNone(processed)
        
        # 检查默认值填充
        expected_fields = ['keywords', 'images', 'related_stocks', 'sentiment', 
                          'classification', 'summary', 'status', 'content_html']
        for field in expected_fields:
            self.assertIn(field, processed)
        
        # 测试缺失必要字段
        incomplete_data = self.sample_news_data.copy()
        del incomplete_data['title']
        
        processed_incomplete = self.crawler.preprocess_news_data(incomplete_data)
        self.assertIsNone(processed_incomplete)
    
    def test_extract_title_from_html(self):
        """测试从HTML提取标题"""
        html_samples = [
            '<html><head><title>页面标题</title></head><body><h1>新闻标题</h1></body></html>',
            '<html><body><h1 class="main-title">主要标题</h1></body></html>',
            '<html><body><div class="article-header"><h1>文章标题</h1></div></body></html>'
        ]
        
        for html in html_samples:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            title = self.crawler._extract_title(soup)
            self.assertIsNotNone(title)
            self.assertGreater(len(title), 0)
    
    def test_extract_content_from_html(self):
        """测试从HTML提取内容"""
        html_with_content = '''
        <html>
            <body>
                <div class="article-content">
                    <p>这是第一段内容。</p>
                    <p>这是第二段内容。</p>
                </div>
            </body>
        </html>
        '''
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_with_content, 'html.parser')
        content = self.crawler._extract_content(soup)
        
        self.assertIsNotNone(content)
        self.assertIn('第一段内容', content)
        self.assertIn('第二段内容', content)


class TestSinaCrawlerIntegration(unittest.TestCase):
    """新浪财经爬虫集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, 'test_sina_integration.db')
        self.crawler = SinaCrawler(db_path=self.test_db_path)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_database_operations(self):
        """测试数据库操作"""
        # 创建测试新闻数据
        test_news = {
            'id': 'integration_test_123',
            'title': '集成测试新闻',
            'content': '这是集成测试的新闻内容。' * 10,  # 确保内容足够长
            'url': 'https://finance.sina.com.cn/integration/test/123.html',
            'source': '新浪财经',
            'pub_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'author': '集成测试',
            'category': '财经'
        }
        
        # 预处理数据
        processed_news = self.crawler.preprocess_news_data(test_news)
        self.assertIsNotNone(processed_news)
        
        # 保存到数据库
        result = self.crawler.save_news_to_db(processed_news)
        self.assertTrue(result)
        
        # 验证数据库中的数据
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM news WHERE id = ?", (test_news['id'],))
        saved_news = cursor.fetchone()
        
        self.assertIsNotNone(saved_news)
        conn.close()
        
        # 测试重复插入
        duplicate_result = self.crawler.save_news_to_db(processed_news)
        self.assertTrue(duplicate_result)  # 重复插入应该被忽略但返回True
    
    @patch('requests.get')
    def test_extract_news_links_with_mock(self, mock_get):
        """测试使用Mock的新闻链接提取"""
        # 模拟网页响应
        mock_html = '''
        <html>
            <body>
                <div class="news-list">
                    <a href="https://finance.sina.com.cn/news/article1.html">新闻1</a>
                    <a href="https://finance.sina.com.cn/news/article2.html">新闻2</a>
                    <a href="https://finance.sina.com.cn/news/article3.html">新闻3</a>
                </div>
            </body>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.content = mock_html.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # 测试链接提取
        links = self.crawler.extract_news_links('https://finance.sina.com.cn/')
        
        self.assertIsInstance(links, list)
        self.assertGreater(len(links), 0)
        
        for link in links:
            self.assertIn('finance.sina.com.cn', link)
            self.assertTrue(self.crawler._is_valid_news_url(link))
    
    @patch('requests.get')
    def test_extract_news_content_with_mock(self, mock_get):
        """测试使用Mock的新闻内容提取"""
        # 模拟新闻页面
        mock_html = '''
        <html>
            <head><title>测试新闻标题 - 新浪财经</title></head>
            <body>
                <h1 class="main-title">测试新闻标题</h1>
                <div class="article-time">2023-12-01 10:30:00</div>
                <div class="author">测试记者</div>
                <div class="article-content">
                    <p>这是新闻的第一段内容。</p>
                    <p>这是新闻的第二段内容。</p>
                    <p>这是新闻的第三段内容。</p>
                </div>
            </body>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.content = mock_html.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # 测试内容提取
        news_data = self.crawler.extract_news_content('https://finance.sina.com.cn/test.html')
        
        self.assertIsNotNone(news_data)
        self.assertEqual(news_data['title'], '测试新闻标题')
        self.assertIn('第一段内容', news_data['content'])
        self.assertIn('第二段内容', news_data['content'])
        self.assertEqual(news_data['source'], '新浪财经')
        self.assertEqual(news_data['author'], '测试记者')


class TestSinaCrawlerPerformance(unittest.TestCase):
    """新浪财经爬虫性能测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, 'test_sina_performance.db')
        self.crawler = SinaCrawler(db_path=self.test_db_path)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_batch_save_performance(self):
        """测试批量保存性能"""
        # 生成测试数据
        test_news_list = []
        for i in range(100):
            news_data = {
                'id': f'perf_test_{i}',
                'title': f'性能测试新闻 {i}',
                'content': f'这是第{i}条性能测试新闻的内容。' * 10,
                'url': f'https://finance.sina.com.cn/perf/test/{i}.html',
                'source': '新浪财经',
                'pub_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'author': '性能测试',
                'category': '财经'
            }
            test_news_list.append(news_data)
        
        # 测试保存时间
        start_time = time.time()
        
        saved_count = 0
        for news_data in test_news_list:
            processed = self.crawler.preprocess_news_data(news_data)
            if processed and self.crawler.save_news_to_db(processed):
                saved_count += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 验证结果
        self.assertEqual(saved_count, 100)
        self.assertLess(duration, 10)  # 100条记录应在10秒内完成
        
        print(f"批量保存100条记录耗时: {duration:.2f}秒")
        print(f"平均每条记录: {duration/100*1000:.2f}毫秒")


class TestSinaCrawlerRealWorld(unittest.TestCase):
    """新浪财经爬虫真实环境测试（需要网络连接）"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, 'test_sina_real.db')
        self.crawler = SinaCrawler(db_path=self.test_db_path)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @unittest.skipIf(not os.getenv('ENABLE_NETWORK_TESTS'), 
                     "跳过网络测试（设置ENABLE_NETWORK_TESTS=1来启用）")
    def test_real_crawling(self):
        """测试真实爬取（需要网络连接）"""
        try:
            # 尝试爬取少量真实数据
            result = self.crawler.crawl(max_news=2, days=1)
            
            self.assertIsInstance(result, int)
            self.assertGreaterEqual(result, 0)
            
            # 检查数据库中是否有数据
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM news")
            count = cursor.fetchone()[0]
            conn.close()
            
            print(f"真实爬取测试完成，获取到 {count} 条新闻")
            
        except Exception as e:
            self.skipTest(f"网络测试失败: {str(e)}")


def create_test_report():
    """创建测试报告"""
    import unittest
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestSinaCrawlerUnit,
        TestSinaCrawlerIntegration,
        TestSinaCrawlerPerformance,
        TestSinaCrawlerRealWorld
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 生成测试报告
    report = {
        'total_tests': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100,
        'timestamp': datetime.now().isoformat()
    }
    
    # 保存测试报告
    report_path = 'test_report_sina_crawler.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n测试报告已保存到: {report_path}")
    print(f"测试总数: {report['total_tests']}")
    print(f"失败数: {report['failures']}")
    print(f"错误数: {report['errors']}")
    print(f"成功率: {report['success_rate']:.1f}%")
    
    return result


if __name__ == '__main__':
    # 设置日志级别
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 运行测试并生成报告
    result = create_test_report()
    
    # 退出码
    sys.exit(0 if result.wasSuccessful() else 1) 