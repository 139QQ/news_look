#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志测试工具 - 用于测试日志输出功能
"""

import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.utils.logger import get_crawler_logger, get_logger

def test_logger():
    """测试日志记录器"""
    # 测试普通日志记录器
    logger = get_logger('test')
    logger.info("这是一个测试信息")
    logger.warning("这是一个警告信息")
    logger.error("这是一个错误信息")
    
    # 测试爬虫专用日志记录器
    crawler_logger = get_crawler_logger('test')
    crawler_logger.info("这是爬虫的测试信息")
    crawler_logger.warning("这是爬虫的警告信息")
    crawler_logger.error("这是爬虫的错误信息")
    
    # 测试东方财富日志记录器
    eastmoney_logger = get_crawler_logger('东方财富')
    eastmoney_logger.info("东方财富爬虫测试信息")
    eastmoney_logger.warning("东方财富爬虫警告信息")
    eastmoney_logger.error("东方财富爬虫错误信息")
    
    print("日志测试完成，请检查logs目录下的日志文件")

if __name__ == "__main__":
    test_logger() 