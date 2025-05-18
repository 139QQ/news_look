#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试运行器 - 用于运行包含异步测试的单元测试
"""

import os
import sys
import unittest
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class AsyncioTestRunner:
    """异步测试运行器"""
    
    @staticmethod
    def run_tests():
        """运行所有测试，包括异步测试"""
        from tests.test_enhanced_crawler import TestEnhancedCrawler
        
        # 收集所有测试用例
        suite = unittest.TestLoader().loadTestsFromTestCase(TestEnhancedCrawler)
        
        # 运行测试
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)

if __name__ == '__main__':
    AsyncioTestRunner.run_tests() 