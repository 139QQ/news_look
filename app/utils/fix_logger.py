#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志修复工具 - 用于修复日志输出问题
"""

import os
import sys
import logging
import shutil
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.utils.logger import get_crawler_logger, get_logger

# 初始化日志
logger = get_logger('log_fixer')

class LogFixer:
    """日志修复工具类"""
    
    def __init__(self):
        """初始化日志修复工具"""
        # 获取项目根目录
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        
        # 确保日志目录存在
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir, exist_ok=True)
            logger.info(f"创建日志目录: {self.logs_dir}")
            
        logger.info("日志修复工具初始化完成")
        
    def check_log_directories(self):
        """检查日志目录结构"""
        # 爬虫源列表
        sources = ['东方财富', '新浪财经', '网易财经', '腾讯财经', '凤凰财经']
        
        # 检查并创建每个爬虫源的日志目录
        for source in sources:
            source_log_dir = os.path.join(self.logs_dir, source)
            if not os.path.exists(source_log_dir):
                os.makedirs(source_log_dir, exist_ok=True)
                logger.info(f"创建爬虫日志目录: {source_log_dir}")
        
        logger.info("日志目录结构检查完成")
        
    def fix_eastmoney_logger(self):
        """修复东方财富日志记录器"""
        # 获取东方财富日志记录器
        eastmoney_logger = get_crawler_logger('东方财富')
        
        # 测试日志输出
        eastmoney_logger.info("====== 日志修复工具测试 ======")
        eastmoney_logger.info("这是一条测试日志信息")
        eastmoney_logger.warning("这是一条测试警告信息")
        eastmoney_logger.error("这是一条测试错误信息")
        eastmoney_logger.info("====== 测试完成 ======")
        
        # 获取日志文件路径
        today = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(self.logs_dir, '东方财富', f"东方财富_{today}.log")
        
        # 检查日志文件是否存在且有内容
        if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
            logger.info(f"东方财富日志文件存在并有内容: {log_file}")
            logger.info("东方财富日志修复成功")
            return True
        else:
            logger.error(f"东方财富日志文件不存在或为空: {log_file}")
            logger.error("东方财富日志修复失败")
            return False
            
    def reset_logger_cache(self):
        """重置日志记录器缓存"""
        # 导入日志模块以访问缓存
        from app.utils.logger import _logger_cache
        
        # 检查并清除东方财富日志记录器的缓存
        cache_key = 'crawler.东方财富'
        if cache_key in _logger_cache:
            logger.info(f"从缓存中移除日志记录器: {cache_key}")
            del _logger_cache[cache_key]
            
        # 重新初始化东方财富日志记录器
        self.fix_eastmoney_logger()
        
        logger.info("日志记录器缓存重置完成")


def main():
    """主函数"""
    print("=== 日志修复工具 ===")
    
    # 创建日志修复工具实例
    fixer = LogFixer()
    
    # 检查日志目录结构
    fixer.check_log_directories()
    
    # 修复东方财富日志记录器
    if fixer.fix_eastmoney_logger():
        print("东方财富日志修复成功，请检查日志文件")
    else:
        print("东方财富日志修复失败，尝试重置日志缓存...")
        fixer.reset_logger_cache()
    
    print("修复过程完成")


if __name__ == "__main__":
    main() 