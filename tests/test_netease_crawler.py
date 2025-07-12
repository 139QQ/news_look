import unittest
from unittest.mock import patch, MagicMock, call
import os
import sys
from datetime import datetime, timedelta

# Ensure the app path is in sys.path to import NeteaseCrawler
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # 直接获取当前目录的父目录
sys.path.insert(0, project_root)

from backend.app.crawlers.netease import NeteaseCrawler
from backend.app.db.SQLiteManager import SQLiteManager

class TestNeteaseCrawler(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        # 创建模拟对象
        self.mock_db_manager = MagicMock(spec=SQLiteManager)
        self.mock_db_manager.db_path = ":memory:"
        
        # 使用patch修饰器全局模拟依赖的类和方法
        self.ad_filter_patcher = patch('app.crawlers.netease.AdFilter')
        self.image_detector_patcher = patch('app.crawlers.netease.ImageDetector')
        self.requests_patcher = patch('app.crawlers.netease.requests')
        
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
        self.crawler = NeteaseCrawler(db_manager=self.mock_db_manager, use_source_db=True)

    def tearDown(self):
        """清理测试环境"""
        # 停止所有patch
        self.ad_filter_patcher.stop()
        self.image_detector_patcher.stop()
        self.requests_patcher.stop()

    def test_initialization(self):
        """Test crawler initialization."""
        self.assertEqual(self.crawler.source, "网易财经")
        self.assertIsNotNone(self.crawler.db_manager)
        self.assertIsNotNone(self.crawler.session)
        # 检查ad_filter和image_detector是否为正确的模拟实例
        self.assertEqual(self.crawler.ad_filter, self.mock_ad_filter_instance)
        self.assertEqual(self.crawler.image_detector, self.mock_image_detector_instance)
        # 验证proxy_manager正确初始化
        self.assertIsNone(self.crawler.proxy_manager)  # 默认不使用代理

    def test_is_valid_url_valid_cases(self):
        """Test URL validation with valid URLs."""
        valid_urls = [
            "https://money.163.com/23/0801/12/ABCDEFG.html",
            "http://money.163.com/23/0801/12/HIJKLMN.html",
            "https://money.163.com/article/ABCDEFG/12345.html",
            "https://www.163.com/money/article/ABCDEFG/12345.html",
            "https://funds.163.com/article/ABCDEFG/12345.html",
        ]
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(self.crawler.is_valid_url(url))

    def test_is_valid_url_invalid_cases(self):
        """Test URL validation with invalid URLs."""
        invalid_urls = [
            None,
            "",
            "https://example.com/news.html",
            "https://money.163.com/special/topic.html",  # 特殊主题页面，不是新闻
            "https://money.163.com/api/getnews",  # API接口
            "https://money.163.com/ent/index.html",  # 被过滤的娱乐栏目
            "https://money.163.com/news.html?id=123",  # 带有动态参数
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(self.crawler.is_valid_url(url))

    @patch('app.crawlers.netease.clean_html')
    def test_extract_news_detail_success(self, mock_clean_html):
        """Test news detail extraction."""
        # 准备测试数据
        mock_html = """
        <html><body>
            <h1 class="post_title">Test News Title</h1>
            <div class="post_time_source">2023-08-01 10:00:00 来源：网易财经</div>
            <div class="post_body">
                <p>This is the first paragraph.</p>
                <p>This is the second paragraph.</p>
                <div class="gg200x300">AD CONTENT HERE</div>
            </div>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        self.mock_session.get.return_value = mock_response
        
        # 模拟clean_html函数
        mock_clean_html.return_value = "This is the first paragraph. This is the second paragraph."
        
        # 执行测试
        result = self.crawler.extract_news_detail("https://money.163.com/23/0801/01/TESTARTICLE.html", "财经")
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Test News Title")
        self.assertEqual(result["pub_time"], "2023-08-01 10:00:00")
        self.assertEqual(result["author"], "网易财经")
        self.assertEqual(result["source"], "网易财经")
        self.assertEqual(result["content"], "This is the first paragraph. This is the second paragraph.")
        self.assertEqual(result["category"], "财经")
        self.assertEqual(result["url"], "https://money.163.com/23/0801/01/TESTARTICLE.html")
        
        # 验证调用
        self.mock_session.get.assert_called_once()
        mock_clean_html.assert_called_once()

    def test_extract_news_detail_missing_title(self):
        """Test news detail extraction when title is missing."""
        # 准备测试数据
        mock_html = """
        <html><body>
            <div class="post_body">
                <p>Content without title</p>
            </div>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        self.mock_session.get.return_value = mock_response
        
        # 执行测试
        result = self.crawler.extract_news_detail("https://money.163.com/23/0801/01/MISSING.html", "财经")
        
        # 验证结果
        self.assertIsNone(result)
        self.mock_session.get.assert_called_once()

    def test_extract_news_detail_http_error(self):
        """Test news detail extraction with HTTP error."""
        # 准备测试数据
        mock_response = MagicMock()
        mock_response.status_code = 404
        self.mock_session.get.return_value = mock_response
        
        # 执行测试
        result = self.crawler.extract_news_detail("https://money.163.com/23/0801/01/ERROR.html", "财经")
        
        # 验证结果
        self.assertIsNone(result)
        self.mock_session.get.assert_called_once()

    def test_extract_news_links_from_home(self):
        """Test link extraction from homepage."""
        # 准备测试数据
        mock_html = """
        <html><body>
            <a href="https://money.163.com/23/0801/01/VALID01.html">Valid Link 1</a>
            <a href="//money.163.com/23/0801/02/VALID02.html">Valid Link 2</a>
            <a href="/23/0801/03/VALID03.html">Valid Link 3</a>
            <a href="https://example.com/invalid.html">Invalid Link</a>
            <a href="https://money.163.com/special/topic.html">Invalid Special Link</a>
        </body></html>
        """
        
        # 模拟is_valid_url方法
        with patch.object(self.crawler, 'is_valid_url') as mock_is_valid:
            mock_is_valid.side_effect = lambda url: "VALID" in url
            
            # 执行测试
            links = self.crawler.extract_news_links_from_home(mock_html, "财经")
            
            # 验证结果
            expected_links = [
                "https://money.163.com/23/0801/01/VALID01.html",
                "https://money.163.com/23/0801/02/VALID02.html",
                "https://money.163.com/23/0801/03/VALID03.html"
            ]
            self.assertEqual(sorted(links), sorted(expected_links))
            
            # 验证调用次数
            self.assertEqual(mock_is_valid.call_count, 5)

    @patch('app.crawlers.netease.BaseCrawler.save_news_to_db')
    @patch('app.crawlers.netease.NeteaseCrawler.extract_news_detail')
    @patch('app.crawlers.netease.NeteaseCrawler.extract_news_links')
    @patch('app.crawlers.netease.NeteaseCrawler.extract_news_links_from_home')
    @patch('app.crawlers.netease.NeteaseCrawler.fetch_page')
    def test_crawl_flow(self, mock_fetch_page, mock_extract_home, mock_extract_cat, mock_extract_detail, mock_save_db):
        """Test the full crawl flow."""
        # 准备测试数据
        mock_fetch_page.return_value = "<html><body>Test HTML</body></html>"
        
        mock_extract_home.return_value = ["https://money.163.com/home_news_1.html"]
        mock_extract_cat.return_value = ["https://money.163.com/cat_news_1.html"]
        
        mock_news_item = {
            'url': 'https://money.163.com/home_news_1.html',
            'title': 'Test Home News',
            'pub_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'content': 'Content',
            'source': '网易财经',
            'category': '财经'
        }
        mock_extract_detail.return_value = mock_news_item
        mock_save_db.return_value = True
        
        # 执行测试
        result = self.crawler.crawl(days=1, max_news=1)
        
        # 验证结果
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'Test Home News')
        
        # 验证调用
        mock_fetch_page.assert_called()
        mock_extract_home.assert_called_once()
        mock_extract_detail.assert_called()
        mock_save_db.assert_called_once()

    def test_proxy_integration(self):
        """Test proxy integration when proxy is enabled."""
        with patch('app.crawlers.netease.ProxyManager') as mock_proxy_manager_class:
            mock_proxy_manager = MagicMock()
            mock_proxy_manager_class.return_value = mock_proxy_manager
            
            # Create crawler with proxy enabled
            crawler = NeteaseCrawler(db_manager=self.mock_db_manager, use_proxy=True)
            
            # Verify proxy manager initialization
            self.assertIsNotNone(crawler.proxy_manager)
            self.assertEqual(crawler.proxy_manager, mock_proxy_manager)
            
            # Mock proxy data
            mock_proxy = {'http': 'http://1.2.3.4:8080', 'https': 'https://1.2.3.4:8080'}
            mock_proxy_manager.get_proxy.return_value = mock_proxy
            
            # Test get_proxy method
            proxy = crawler.proxy_manager.get_proxy()
            self.assertEqual(proxy, mock_proxy)
            mock_proxy_manager.get_proxy.assert_called_once()

if __name__ == '__main__':
    unittest.main() 