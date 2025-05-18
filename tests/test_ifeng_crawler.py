import unittest
from unittest.mock import patch, MagicMock, call
import os
import sys
from datetime import datetime, timedelta
import json # For testing image string parsing

# Ensure the app path is in sys.path to import IfengCrawler
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # tests/ 的父目录就是项目根目录
sys.path.insert(0, project_root)

from app.crawlers.ifeng import IfengCrawler
from app.db.SQLiteManager import SQLiteManager # For type hinting and mock spec

class TestIfengCrawler(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        # 创建模拟对象
        self.mock_db_manager = MagicMock(spec=SQLiteManager)
        self.mock_db_manager.db_path = ":memory:"
        
        # 使用patch修饰器全局模拟依赖的类和方法
        self.ad_filter_patcher = patch('app.crawlers.ifeng.AdFilter')
        self.image_detector_patcher = patch('app.crawlers.ifeng.ImageDetector')
        self.requests_patcher = patch('app.crawlers.ifeng.requests')
        
        # 启动patch
        self.mock_ad_filter_class = self.ad_filter_patcher.start()
        self.mock_image_detector_class = self.image_detector_patcher.start()
        self.mock_requests = self.requests_patcher.start()
        
        # 设置模拟对象的返回值
        self.mock_ad_filter_instance = MagicMock()
        self.mock_image_detector_instance = MagicMock()
        self.mock_session = MagicMock()
        
        self.mock_ad_filter_class.return_value = self.mock_ad_filter_instance
        self.mock_image_detector_class.return_value = self.mock_image_detector_instance
        self.mock_requests.Session.return_value = self.mock_session
        self.mock_session.headers = {}
        
        # 创建爬虫实例
        self.crawler = IfengCrawler(db_manager=self.mock_db_manager, use_source_db=True)
        
    def tearDown(self):
        """清理测试环境"""
        # 停止所有patch
        self.ad_filter_patcher.stop()
        self.image_detector_patcher.stop()
        self.requests_patcher.stop()
        
    def test_initialization(self):
        """Test crawler initialization"""
        self.assertEqual(self.crawler.source, "凤凰财经")
        self.assertIsNotNone(self.crawler.db_manager)
        self.assertIsNotNone(self.crawler.session)
        # 检查ad_filter和image_detector是否为正确的模拟实例
        self.assertEqual(self.crawler.ad_filter, self.mock_ad_filter_instance)
        self.assertEqual(self.crawler.image_detector, self.mock_image_detector_instance)
        # 验证encoding_fix_enabled设置
        self.assertTrue(self.crawler.encoding_fix_enabled)
        
        # 验证日志调用
        expected_log_calls = [
            call.info('已启用编码修复功能，自动处理中文乱码问题'),
            call.info('凤凰财经爬虫 凤凰财经 初始化完成，将使用数据库: :memory:')
        ]
        self.crawler.logger.assert_has_calls(expected_log_calls, any_order=True)
        
    def test_is_valid_url(self):
        """Test URL validation logic"""
        # 有效URL测试
        valid_urls = [
            "https://finance.ifeng.com/c/8valid1",
            "https://finance.ifeng.com/a/20230101/valid2_0.shtml",
            "https://finance.ifeng.com/a/20230102/valid3_0.html",
            "https://news.ifeng.com/c/validnews1",
        ]
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(self.crawler.is_valid_url(url))
        
        # 无效URL测试
        invalid_urls = [
            None,
            "",
            "https://example.com/news.html",
            "https://finance.ifeng.com/photo/123.html",  # 图片URL
            "https://finance.ifeng.com/special/topic.html",  # 特殊主题页面
            "https://finance.ifeng.com/video/",  # 视频URL
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(self.crawler.is_valid_url(url))
                
    @patch('app.crawlers.ifeng.clean_html')
    def test_extract_news_detail_success(self, mock_clean_html):
        """Test news detail extraction with success case"""
        # 准备测试数据
        mock_html = """
        <html><body>
            <h1 class="topic-title">Test Article Title</h1>
            <div class="timeBref">
                <span class="time">2025-05-11 11:17:48</span>
                <span class="source">凤凰财经</span>
            </div>
            <div class="main_content">
                <p>This is the first paragraph. Example text.</p>
                <p>Second paragraph with <span>more text</span>.</p>
                <div class="ad-banner">AD CONTENT HERE</div>
            </div>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_response.apparent_encoding = "utf-8"
        self.mock_session.get.return_value = mock_response
        
        # 模拟clean_html函数
        mock_clean_html.return_value = "<p>This is the first paragraph. Example text.</p><p>Second paragraph with <span>more text</span>.</p>"
        
        # 执行测试
        url = "https://finance.ifeng.com/c/test123success"
        result = self.crawler.extract_news_detail(url)
        
        # 打印实际结果以便调试
        print("\nActual news_data:")
        print(result)
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Test Article Title _凤凰财经")
        self.assertEqual(result["pub_time"], "2025-05-11 11:17:48")
        self.assertEqual(result["author"], "凤凰财经")
        self.assertEqual(result["content"], "<p>This is the first paragraph. Example text.</p><p>Second paragraph with <span>more text</span>.</p>")
        self.assertEqual(result["category"], "财经")
        self.assertEqual(result["source"], "凤凰财经")
        self.assertEqual(result["url"], url)
        
        # 验证调用
        self.mock_session.get.assert_called_once()
        mock_clean_html.assert_called_once()
    
    def test_extract_news_links(self):
        """Test extraction of news links from HTML"""
        # 准备测试数据
        mock_html = """
        <html><body>
            <div class="news-list">
                <a href="https://news.ifeng.com/c/validnews1">Valid News 1</a>
                <a href="https://finance.ifeng.com/a/20230101/valid2_0.shtml">Valid News 2</a>
                <a href="https://finance.ifeng.com/a/20230102/valid3_0.html">Valid News 3</a>
                <a href="https://finance.ifeng.com/c/8valid1">Valid News 4</a>
                <a href="https://example.com/invalid.html">Invalid News</a>
                <a href="https://finance.ifeng.com/photo/1234.html">Invalid Photo</a>
            </div>
        </body></html>
        """
        
        # 模拟is_valid_url方法
        with patch.object(self.crawler, 'is_valid_url', side_effect=lambda url: "valid" in url.lower()):
            # 执行测试
            links = self.crawler.extract_news_links(mock_html)
            
            # 打印实际结果以便调试
            print("\nActual links returned:")
            print(links)
            
            # 验证结果
            expected_links = [
                "https://news.ifeng.com/c/validnews1",
                "https://finance.ifeng.com/a/20230101/valid2_0.shtml",
                "https://finance.ifeng.com/a/20230102/valid3_0.html",
                "https://finance.ifeng.com/c/8valid1"
            ]
            self.assertEqual(sorted(links), sorted(expected_links))
            
    def test_logger_setup(self):
        """Test logger setup and initialization messages"""
        # 创建带mock logger的爬虫实例
        with patch('app.crawlers.ifeng.get_crawler_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            crawler = IfengCrawler(db_manager=self.mock_db_manager)
            
            # 打印实际日志调用
            print("\nActual logger calls:")
            print(mock_logger.mock_calls)
            
            # 验证日志调用
            expected_log_calls = [
                call.info('已启用编码修复功能，自动处理中文乱码问题'),
                call.info('凤凰财经爬虫 凤凰财经 初始化完成，将使用数据库: :memory:')
            ]
            mock_logger.assert_has_calls(expected_log_calls, any_order=True)
            
    @patch('app.crawlers.ifeng.BaseCrawler.save_news_to_db')
    @patch('app.crawlers.ifeng.IfengCrawler.extract_news_detail')
    @patch('app.crawlers.ifeng.IfengCrawler.extract_news_links')
    def test_crawl_flow(self, mock_extract_links, mock_extract_detail, mock_save_db):
        """Test the basic crawl flow"""
        # 准备测试数据
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test HTML</body></html>"
        self.mock_session.get.return_value = mock_response
        
        # 模拟extract_news_links返回一个链接列表
        mock_extract_links.return_value = ["https://finance.ifeng.com/a/testlink1", "https://finance.ifeng.com/a/testlink2"]
        
        # 模拟extract_news_detail返回一个新闻数据字典
        mock_news_data = {
            'url': 'https://finance.ifeng.com/a/testlink1',
            'title': 'Test News',
            'content': 'Test content',
            'pub_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'author': '凤凰财经',
            'source': '凤凰财经',
            'category': '财经'
        }
        mock_extract_detail.return_value = mock_news_data
        
        # 模拟save_news_to_db返回True表示保存成功
        mock_save_db.return_value = True
        
        # 执行测试
        result = self.crawler.crawl(max_count=1)
        
        # 验证结果
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'Test News')
        
        # 验证调用
        self.mock_session.get.assert_called()
        mock_extract_links.assert_called()
        mock_extract_detail.assert_called_once_with("https://finance.ifeng.com/a/testlink1")
        mock_save_db.assert_called_once()
        
    def test_encoding_fix(self):
        """Test encoding fix functionality"""
        # 准备测试数据
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>乱码测试</body></html>"
        mock_response.encoding = "ISO-8859-1"  # 设置为不正确的编码
        mock_response.apparent_encoding = "utf-8"  # 模拟apparent_encoding返回正确的编码
        self.mock_session.get.return_value = mock_response
        
        # 执行测试 - 使用patch装饰器为_detect_encoding方法返回"utf-8"
        with patch.object(self.crawler, '_detect_encoding', return_value="utf-8"):
            html = self.crawler.fetch_page("https://finance.ifeng.com/test_encoding")
            
            # 验证结果
            self.assertIsNotNone(html)
            self.assertIn("乱码测试", html)
            
            # 验证encoding被设置为返回的编码
            self.assertEqual(mock_response.encoding, "utf-8")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False) 