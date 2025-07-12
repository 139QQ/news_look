#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试新架构爬虫的单元测试
"""

import os
import sys
import unittest
import tempfile
import asyncio
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.crawlers.eastmoney_new import EastMoneyCrawler


class TestEnhancedCrawler(unittest.TestCase):
    """测试新架构爬虫"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录用于测试
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, 'test.db')
        
    def tearDown(self):
        """测试后清理"""
        # 清理临时目录
        self.temp_dir.cleanup()
    
    @patch('app.crawlers.core.http_client.SyncHttpClient.fetch')
    @patch('app.crawlers.strategies.eastmoney_strategy.EastMoneyStrategy.parse_list_page')
    @patch('app.crawlers.strategies.eastmoney_strategy.EastMoneyStrategy.parse_detail_page')
    def test_eastmoney_crawler_sync(self, mock_parse_detail, mock_parse_list, mock_fetch):
        """测试东方财富爬虫同步模式"""
        # 设置模拟数据
        mock_fetch.return_value = "<html><body>Mock HTML</body></html>"
        mock_parse_list.return_value = [
            {'url': 'http://example.com/article1', 'title': '测试文章1'},
            {'url': 'http://example.com/article2', 'title': '测试文章2'}
        ]
        mock_parse_detail.return_value = {
            'id': 'test_id',
            'url': 'http://example.com/article1',
            'title': '测试文章1',
            'content': '这是测试内容',
            'pub_time': '2023-01-01 12:00:00',
            'source': '东方财富'
        }
        
        # 创建爬虫实例
        crawler = EastMoneyCrawler(db_path=self.db_path, async_mode=False)
        
        # 执行爬取
        result = crawler.crawl(days=1, max_news=2, category='财经')
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['title'], '测试文章1')
        self.assertEqual(result[0]['source'], '东方财富')
        
        # 验证Mock函数被调用
        mock_fetch.assert_called()
        mock_parse_list.assert_called()
        mock_parse_detail.assert_called()
    
    @patch('app.crawlers.core.http_client.AsyncHttpClient.fetch')
    @patch('app.crawlers.strategies.eastmoney_strategy.EastMoneyStrategy.parse_list_page')
    @patch('app.crawlers.strategies.eastmoney_strategy.EastMoneyStrategy.parse_detail_page')
    @unittest.skipIf(sys.version_info < (3, 8), "asyncio测试需要Python 3.8+")
    async def test_eastmoney_crawler_async(self, mock_parse_detail, mock_parse_list, mock_fetch):
        """测试东方财富爬虫异步模式"""
        # 设置模拟数据
        mock_fetch.return_value = "<html><body>Mock HTML</body></html>"
        mock_parse_list.return_value = [
            {'url': 'http://example.com/article1', 'title': '测试文章1'},
            {'url': 'http://example.com/article2', 'title': '测试文章2'}
        ]
        mock_parse_detail.return_value = {
            'id': 'test_id',
            'url': 'http://example.com/article1',
            'title': '测试文章1',
            'content': '这是测试内容',
            'pub_time': '2023-01-01 12:00:00',
            'source': '东方财富'
        }
        
        # 创建爬虫实例
        crawler = EastMoneyCrawler(db_path=self.db_path, async_mode=True)
        
        # 执行爬取
        # 注意：由于crawl是异步方法，我们需要在异步上下文中调用它
        result = await crawler.crawl(days=1, max_news=2, category='财经')
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['title'], '测试文章1')
        self.assertEqual(result[0]['source'], '东方财富')
        
        # 验证Mock函数被调用
        mock_fetch.assert_called()
        mock_parse_list.assert_called()
        mock_parse_detail.assert_called()
    
    def test_preprocess_article(self):
        """测试文章预处理"""
        # 创建爬虫实例
        crawler = EastMoneyCrawler(db_path=self.db_path)
        
        # 测试数据
        article = {
            'title': ' 测试文章标题 ',  # 有空格，应被去除
            'content': '这是测试内容',
            'url': 'http://example.com/article',
            'images': [
                {'url': 'http://example.com/img1.jpg'},
                'http://example.com/img2.jpg',
                '/img3.jpg'  # 相对路径，应被转换为绝对路径
            ]
        }
        
        # 执行预处理
        processed = crawler.preprocess_article(article)
        
        # 验证结果
        self.assertEqual(processed['title'], ' 测试文章标题 ')  # 原始标题应保持不变
        self.assertEqual(processed['source'], '东方财富')  # 应设置来源
        
        # 验证ID生成
        self.assertIn('id', processed)
        
        # 验证图片处理
        self.assertIsInstance(processed['images'], list)
        self.assertEqual(len(processed['images']), 3)
        self.assertTrue(isinstance(processed['images'][0], str) and processed['images'][0].startswith('http://'))
        self.assertTrue(isinstance(processed['images'][2], str) and processed['images'][2].startswith('http://'))  # 相对路径应被转换为绝对路径
    
    @patch('app.crawlers.manager_new.EnhancedCrawlerManager._load_new_crawlers')
    def test_manager_integration(self, mock_load):
        """测试爬虫管理器集成"""
        # 导入管理器
        from backend.app.crawlers.manager_new import EnhancedCrawlerManager
        
        # 模拟爬虫加载
        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = [{'title': '测试文章', 'content': '测试内容'}]
        
        manager = EnhancedCrawlerManager()
        manager.crawlers = {'东方财富': mock_crawler}
        
        # 测试获取爬虫列表
        self.assertEqual(manager.get_crawlers(), ['东方财富'])
        
        # 测试获取爬虫实例
        self.assertEqual(manager.get_crawler('东方财富'), mock_crawler)
        
        # 测试运行爬虫
        result = manager.run_crawler_once('东方财富', days=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], '测试文章')
        
        # 验证Mock函数被调用
        mock_crawler.crawl.assert_called_with(days=1, max_news=None)


# 这个函数允许我们作为脚本运行测试
def run_tests():
    unittest.main()


if __name__ == '__main__':
    run_tests()