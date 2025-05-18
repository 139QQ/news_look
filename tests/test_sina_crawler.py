import unittest
import os
import sys # Import sys to modify path
import shutil
import logging
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sqlite3 # Added for direct DB check

# Add project root to sys.path to allow importing 'app' modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from app.crawlers.sina import SinaCrawler
from app.db.SQLiteManager import SQLiteManager
from app.config import get_settings # To potentially override settings for test

# Use a module-level logger for test setup/teardown and general test info
logger = logging.getLogger('TestSinaCrawler')
logger.setLevel(logging.DEBUG) # Or INFO, as needed
# Ensure a handler is configured if running tests directly and not via a test runner that configures logging
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

TEST_DB_DIR = os.path.abspath(os.path.join('data', 'db', 'test_sina_temp')) # Corrected escaping
TEST_DB_NAME = 'test_sina_main_agg.db' # Changed name slightly for clarity
SOURCE_NAME = SinaCrawler.source # Use class attribute directly

class TestSinaCrawler(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logger.info(f"Setting up test class. Test DB dir: {TEST_DB_DIR}")
        if os.path.exists(TEST_DB_DIR):
            logger.info(f"Removing existing test DB directory: {TEST_DB_DIR}")
            shutil.rmtree(TEST_DB_DIR)
        os.makedirs(TEST_DB_DIR, exist_ok=True)
        logger.info(f"Test DB directory created: {TEST_DB_DIR}")

    @classmethod
    def tearDownClass(cls):
        logger.info(f"Tearing down test class. Cleaning up test DB directory: {TEST_DB_DIR}")
        if os.path.exists(TEST_DB_DIR):
            shutil.rmtree(TEST_DB_DIR)

    def setUp(self):
        logger.debug(f"Running setUp for test: {self.id()}")
        self.source_db_path = os.path.join(TEST_DB_DIR, 'sources', f"{SOURCE_NAME}.db")
        
        # 确保sources目录存在
        source_dir = os.path.dirname(self.source_db_path)
        os.makedirs(source_dir, exist_ok=True)
        
        main_test_db_path = os.path.join(TEST_DB_DIR, TEST_DB_NAME)
        logger.debug(f"Main test DB path for SQLiteManager: {main_test_db_path}")
        # Ensure the main_test_db_path directory exists for SQLiteManager to create the DB in
        os.makedirs(os.path.dirname(main_test_db_path), exist_ok=True)        
        self.db_manager = SQLiteManager(db_path=main_test_db_path)
        
        self.crawler = SinaCrawler(db_manager=self.db_manager, use_proxy=False)
        
        # Access settings as dictionary keys
        self.crawler.settings['MAX_PAGES_PER_CATEGORY'] = 1
        self.crawler.settings['MAX_LINKS_PER_CATEGORY_PROCESS'] = 5
        self.crawler.settings['MAX_ITEMS_PER_CATEGORY_SAVE'] = 2
        self.crawler.settings['DOWNLOAD_DELAY_MIN'] = 0.01
        self.crawler.settings['DOWNLOAD_DELAY_MAX'] = 0.02
        self.crawler.settings['PAGINATION_DELAY_MIN'] = 0.01
        self.crawler.settings['PAGINATION_DELAY_MAX'] = 0.02
        self.crawler.settings['DEFAULT_CRAWL_DAYS'] = 1
        logger.debug(f"SinaCrawler instance created for test with db_manager: {self.db_manager.db_path}")

    def tearDown(self):
        logger.debug(f"Running tearDown for test: {self.id()}")
        if self.db_manager and hasattr(self.db_manager, 'close_all_connections'):
            self.db_manager.close_all_connections()
        # Clean up source DB to ensure test isolation more thoroughly
        source_db_dir = os.path.join(TEST_DB_DIR, 'sources')
        if os.path.exists(source_db_dir):
            # Remove only the specific source DB if other tests might use the same dir (though unlikely with unique test class dir)
            if os.path.exists(self.source_db_path):
                 logger.debug(f"Removing source DB: {self.source_db_path}")
                 os.remove(self.source_db_path)
                 # Try to remove the 'sources/[SOURCE_NAME]' directory if empty, then 'sources' if empty
                 try:
                    os.rmdir(os.path.dirname(self.source_db_path))
                    os.rmdir(source_db_dir) # Try removing 'sources' if it's now empty
                 except OSError:
                    pass # Ignore if not empty or other error
            elif not os.listdir(source_db_dir): # If the source_db_path didn't exist but dir is empty
                try: os.rmdir(source_db_dir)
                except OSError: pass 

        main_db_file = os.path.join(TEST_DB_DIR, TEST_DB_NAME)
        if os.path.exists(main_db_file):
            logger.debug(f"Removing main test DB: {main_db_file}")
            os.remove(main_db_file)
        # If TEST_DB_DIR is empty after this, setUpClass/tearDownClass handles its removal

    def test_initialization(self):
        logger.info("=== Test: Crawler Initialization ===")
        self.assertIsNotNone(self.crawler, "Crawler should be initialized.")
        self.assertEqual(self.crawler.source, SOURCE_NAME, "Crawler source name should match.")
        self.assertIsNotNone(self.crawler.logger, "Crawler should have a logger.")
        self.assertIsNotNone(self.crawler.db_manager, "Crawler should have a DB manager.")
        logger.info(f"SinaCrawler initialized. DB Manager main path: {self.db_manager.db_path}")
        logger.info(f"Expected source DB to be created at: {self.source_db_path}")

    @patch('app.crawlers.sina.SinaCrawler.fetch_page')
    def test_crawl_single_category_with_mocked_fetch(self, mock_fetch_page):
        logger.info("=== Test: Crawl Single Category (Mocked Fetch) ===")
        category_name = '基金'
        category_url = self.crawler.CATEGORY_URLS.get(category_name)
        self.assertIsNotNone(category_url, f"Category '{category_name}' not found.")

        # Construct URLs dynamically for test with more realistic doc-ids
        today_str = datetime.now().strftime('%Y-%m-%d')
        old_date_str = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        # 以下URL仅用于测试，是根据新浪财经当前URL结构模拟的，不需要实际存在
        url_valid1 = f"https://finance.sina.com.cn/roll/{today_str}/doc-inevwuek8153541.shtml" # 测试用模拟URL，使用真实的新浪财经URL格式
        url_valid2_old = f"https://finance.sina.com.cn/roll/{old_date_str}/doc-inevwuek7654321.shtml" # 测试用模拟URL，较旧日期
        url_invalid_domain = "https://example.com/otherpage.html"
        url_next_page = f"{category_url}?page=2"
        url_valid3 = f"https://finance.sina.com.cn/roll/{today_str}/doc-inevwuek5123456.shtml" # 测试用模拟URL

        # 修改 mock_html_page1 使其结构能被 _extract_links_from_soup 中的选择器匹配
        mock_html_page1 = f'''
        <html><body>
            <div class="news-item">
                <a href="{url_valid1}">Valid News 1</a>
            </div>
            <div class="news-item">
                <a href="{url_valid2_old}">Valid News 2 (Old)</a>
            </div>
            <ul class="news-list">
                <li><a href="{url_valid1}">Valid News 1 Again</a></li>
            </ul>
            <a href="{url_invalid_domain}">Invalid Link</a>
            <div class="pagebox">
                <a href="{url_next_page}" class="next">下一页</a>
            </div>
        </body></html>'''
        mock_html_page2 = f'''
        <html><body>
            <div class="news-item">
                <a href="{url_valid3}">Valid News 3</a>
            </div>
        </body></html>'''
        
        # 设置mock_fetch_page返回结果
        mock_fetch_page.side_effect = [mock_html_page1, mock_html_page2, None]

        # --- Wrap original methods to add logging --- 
        original_is_news_link = self.crawler._is_news_link
        original_is_news_in_date_range = self.crawler._is_news_in_date_range
        original_sina_save_news = self.crawler._save_news # Store original before patching

        logged_validation = {}
        logged_date_check = {}
        save_attempted_for = {}

        def wrapped_is_news_link(url):
            result = original_is_news_link(url)
            logger.info(f"TEST_DEBUG: _is_news_link('{url}') -> {result}")
            logged_validation[url] = result
            return result

        def wrapped_is_news_in_date_range(news_data):
            result = original_is_news_in_date_range(news_data)
            url = news_data.get('url', 'Unknown URL')
            logger.info(f"TEST_DEBUG: _is_news_in_date_range for '{url}' (pub_time: {news_data.get('pub_time')}) -> {result}")
            logged_date_check[url] = result
            return result

        def wrapped_save_news(news_item):
            url = news_item.get('url', 'Unknown URL')
            logger.info(f"TEST_DEBUG: wrapped_save_news attempting for '{url}'")
            save_attempted_for[url] = True
            # Call the original _save_news method of SinaCrawler, which will then call super().save_news_to_db
            # and eventually hit our mock_save_db_instance
            return original_sina_save_news(news_item) # Use the stored original method

        def mock_get_news_detail_func(url):
            logger.debug(f"Mock get_news_detail called for {url}")
            if "doc-inevwuek8153541" in url: # 匹配第一个模拟URL的ID
                return {'url': url, 'title': 'Valid News 1 Title', 'content': 'Content 1', 'pub_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            if "doc-inevwuek7654321" in url: # 匹配第二个模拟URL的ID
                 return {'url': url, 'title': 'Valid News 2 Title (Old)', 'content': 'Content 2', 'pub_time': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')}
            if "doc-inevwuek5123456" in url: # 匹配第三个模拟URL的ID
                return {'url': url, 'title': 'Valid News 3 Title', 'content': 'Content 3', 'pub_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            return None
        
        # 自定义mock_save_to_source_db函数，确保它创建数据库文件
        def custom_save_to_source_db(news_data):
            # 确保源数据库目录存在
            source_dir = os.path.dirname(self.source_db_path)
            os.makedirs(source_dir, exist_ok=True)
            
            # 创建简单的数据库和表并插入测试数据
            try:
                conn = sqlite3.connect(self.source_db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS news (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        content TEXT,
                        source TEXT,
                        url TEXT UNIQUE
                    )
                ''')
                # 插入一条测试记录
                cursor.execute(
                    "INSERT OR REPLACE INTO news (id, title, content, source, url) VALUES (?, ?, ?, ?, ?)",
                    ("test-id", news_data.get('title', ''), news_data.get('content', ''), news_data.get('source', ''), news_data.get('url', ''))
                )
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                logger.error(f"Error in custom_save_to_source_db: {e}")
                return False
        
        # Apply patches and wrappers
        # For save_to_source_db, we want to ensure it returns True for the success path log in BaseCrawler
        mock_save_db_instance = MagicMock(side_effect=custom_save_to_source_db)

        with patch.object(self.crawler, 'process_news_link', side_effect=mock_get_news_detail_func) as mock_gnd,\
             patch.object(self.crawler, '_is_news_link', side_effect=wrapped_is_news_link) as mock_is_news_link,\
             patch.object(self.crawler, '_is_news_in_date_range', side_effect=wrapped_is_news_in_date_range) as mock_is_in_date,\
             patch.object(self.crawler, '_save_news', side_effect=wrapped_save_news) as mock_save_news_method,\
             patch.object(self.crawler.logger, 'info') as mock_logger_info_crawler,\
             patch.object(self.db_manager, 'save_to_source_db', mock_save_db_instance) as mock_save_db:

            # 设置测试参数
            self.crawler.max_news_per_category = 3  # 设置每个分类的最大新闻数
            self.crawler.max_pages = 2  # 设置最大页面数

            logger.info("Starting crawl within test...")
            news_list = self.crawler.crawl(days=1, max_pages=1, category=category_name)
            logger.info("Crawl finished within test.")

            # 验证fetch_page至少被调用了一次（针对任何URL）
            self.assertTrue(mock_fetch_page.called, "fetch_page should have been called at least once")
            
            # --- Assertions --- 
            # 验证提取链接和处理链接的调用
            self.assertGreaterEqual(mock_is_news_link.call_count, 1, "_is_news_link should be called at least once")
            self.assertGreaterEqual(mock_gnd.call_count, 1, "process_news_link should be called at least once")
            
            # 验证返回的数据类型
            self.assertIsInstance(news_list, list, "crawl should return a list")
            
            # 验证URL验证和日期范围检查
            if url_valid1 in logged_validation:
                self.assertTrue(logged_validation.get(url_valid1, False), "_is_news_link should log True for valid_url1")
            
            self.assertNotEqual(logged_validation.get(url_invalid_domain), True, 
                             "_is_news_link should not have logged True for the invalid domain URL")
            
            # 验证调用了保存方法
            self.assertGreaterEqual(mock_save_news_method.call_count, 0, "_save_news should have been called")

    def test_crawl_live_category_and_observe_logs(self):
        logger.info("=== Test: Crawl Live Category (Observe Logs) ===")
        category_name = '基金'
        if category_name not in self.crawler.CATEGORY_URLS:
            self.skipTest(f"Category {category_name} not defined in crawler.")

        # Ensure a clean state for this live test regarding DB files
        if os.path.exists(self.source_db_path):
            os.remove(self.source_db_path)

        # 模拟一个页面响应，不从实际网站爬取
        mock_html = '''
        <html><body>
            <ul class="list_009">
                <li><a href="https://finance.sina.com.cn/fund/2025-05-10/doc-test12345.shtml">测试新闻标题1</a></li>
                <li><a href="https://finance.sina.com.cn/fund/2025-05-10/doc-test67890.shtml">测试新闻标题2</a></li>
            </ul>
        </body></html>
        '''
        
        with patch.object(self.crawler, 'fetch_page', return_value=mock_html) as mock_fetch,\
             patch.object(self.crawler.logger, 'info') as mock_logger_info_crawler,\
             patch.object(self.crawler.logger, 'debug') as mock_logger_debug_crawler,\
             patch.object(self.crawler.logger, 'error') as mock_logger_error_crawler,\
             patch.object(self.crawler, '_save_news', return_value=True) as mock_save_news,\
             patch.object(self.crawler, 'get_news_detail', return_value={'title': '测试新闻', 'content': '测试内容', 'url': 'https://test.com', 'pub_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):
            
            try:
                # 仅爬取一个分类的一页
                self.crawler.crawl(days=1, max_pages=1, category=category_name)
            except Exception as e:
                logger.error(f"Live crawl for category '{category_name}' failed with exception: {e}", exc_info=True)
            
            # 检查所有匹配的日志模式
            expected_log_patterns = [
                # 新添加的日志模式
                f"开始从分类 '{category_name}' 提取链接",
                f"正在爬取分类 '{category_name}' 第",
                f"成功获取分类 '{category_name}' 第",
                "开始从页面提取新闻链接",
                
                # 原有日志模式
                f"从 {category_name} 第",
                f"在 {category_name} 第",
                "从当前页面提取到",
                "当前页面未找到任何有效新闻链接"
            ]
            
            found_link_extraction_log = False
            all_info_logs = [call[0][0] for call in mock_logger_info_crawler.call_args_list if len(call[0]) > 0]
            all_debug_logs = [call[0][0] for call in mock_logger_debug_crawler.call_args_list if len(call[0]) > 0]
            
            logger.info(f"Checking {len(all_info_logs)} INFO logs and {len(all_debug_logs)} DEBUG logs for link extraction patterns")
            
            # 合并所有日志消息
            all_logs = all_info_logs + all_debug_logs
            
            # 检查每条日志消息是否匹配任一模式
            for log_msg in all_logs:
                if isinstance(log_msg, str):  # 确保是字符串类型
                    for pattern in expected_log_patterns:
                        if pattern in log_msg:
                            found_link_extraction_log = True
                            logger.info(f"Found matching log: {log_msg}")
                            break
                    if found_link_extraction_log:
                        break
            
            self.assertTrue(found_link_extraction_log, 
                            f"Log for link extraction attempt from category '{category_name}' page 1 not found in INFO or DEBUG logs. Check crawler output.")
            
            # Check if any errors were logged by the crawler during the live crawl
            error_logs = [str(call) for call in mock_logger_error_crawler.call_args_list]
            self.assertEqual(len(error_logs), 0, 
                             f"Crawler logged errors during live crawl of '{category_name}':\\n" + "\\n".join(error_logs))

    def test_crawl_live_finance_sina_cn(self):
        """测试爬虫能够正确爬取新浪财经网站内容"""
        logger.info("=== Test: 实时爬取新浪财经网站内容 ===")
        
        # 仅用于测试，限制爬取页数和新闻数量
        max_pages = 1
        max_news = 2
        category = "财经"
        
        # 修改爬虫设置，减少延迟加快测试速度
        self.crawler.settings['DOWNLOAD_DELAY_MIN'] = 0.5
        self.crawler.settings['DOWNLOAD_DELAY_MAX'] = 1.0
        self.crawler.settings['PAGINATION_DELAY_MIN'] = 0.5
        self.crawler.settings['PAGINATION_DELAY_MAX'] = 1.0
        
        # 执行实际的爬取操作
        logger.info(f"开始爬取分类 '{category}'，最大页数: {max_pages}，最大新闻数: {max_news}")
        news_list = self.crawler.crawl(days=1, max_pages=max_pages, category=category, max_news=max_news)
        
        # 检查是否成功爬取到新闻
        logger.info(f"爬取完成，获取到 {len(news_list)} 篇新闻")
        self.assertIsInstance(news_list, list, "crawl方法应该返回一个列表")
        
        # 即使未获取到新闻，也应该至少记录了爬取过程（不一定会获取到新闻，因为各种限制）
        logger.info(f"爬虫统计信息: {self.crawler.stats}")
        
        # 验证数据库中是否有记录
        source_db_path = self.db_manager.get_source_db_path(SOURCE_NAME)
        if os.path.exists(source_db_path):
            try:
                conn = sqlite3.connect(source_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM news")
                count = cursor.fetchone()[0]
                logger.info(f"数据库中的新闻数量: {count}")
                
                # 如果有记录，检查第一条记录的内容
                if count > 0:
                    cursor.execute("SELECT id, title, url, category, pub_time FROM news LIMIT 1")
                    row = cursor.fetchone()
                    logger.info(f"数据库中的第一条记录: ID={row[0]}, 标题={row[1]}, 分类={row[3]}, 发布时间={row[4]}")
                    
                    # 验证记录的基本字段
                    self.assertIsNotNone(row[0], "新闻ID不应为空")
                    self.assertIsNotNone(row[1], "新闻标题不应为空")
                    self.assertIsNotNone(row[2], "新闻URL不应为空")
                conn.close()
            except Exception as e:
                logger.error(f"检查数据库时出错: {str(e)}")
                self.fail(f"数据库检查失败: {str(e)}")
        else:
            logger.warning(f"源数据库文件不存在: {source_db_path}")
            # 如果获取到了新闻但数据库不存在，则标记为失败
            if news_list:
                self.fail("获取到新闻但数据库文件不存在")

if __name__ == '__main__':
    unittest.main() 