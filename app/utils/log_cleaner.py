#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志清理模块，用于定期清理旧的日志文件
"""

import os
import re
import time
import logging
import shutil
from datetime import date

# 设置日志记录器
logger = logging.getLogger(__name__)

class LogCleaner:
    """日志清理器，用于定期清理旧的日志文件"""
    
    def __init__(self, log_dir=None, max_days=30, min_free_space_mb=500):
        """
        初始化日志清理器
        
        Args:
            log_dir: 日志目录，默认为项目根目录下的logs目录
            max_days: 日志保留的最大天数，默认为30天
            min_free_space_mb: 最小可用空间(MB)，如果可用空间小于此值，将强制清理更多日志
        """
        # 如果未指定日志目录，使用默认目录
        if not log_dir:
            try:
                from app.config import BASE_DIR
                log_dir = os.path.join(BASE_DIR, 'logs')
            except ImportError:
                # 如果无法导入配置，使用相对路径
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                log_dir = os.path.join(base_dir, 'logs')
        
        self.log_dir = log_dir
        self.max_days = max_days
        self.min_free_space_mb = min_free_space_mb
        
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        
        logger.info("日志清理器初始化完成，日志目录: %s, 最大保留天数: %d, 最小可用空间: %dMB", 
                   self.log_dir, self.max_days, self.min_free_space_mb)
    
    def get_log_files(self):
        """
        获取所有日志文件及其修改时间
        
        Returns:
            list: 包含(文件路径, 修改时间)元组的列表
        """
        log_files = []
        
        # 查找所有.log文件和.log.数字文件（轮转日志）
        patterns = [
            os.path.join(self.log_dir, "*.log"),
            os.path.join(self.log_dir, "*.log.*")
        ]
        
        for pattern in patterns:
            for file_path in glob.glob(pattern):
                if os.path.isfile(file_path):
                    mtime = os.path.getmtime(file_path)
                    log_files.append((file_path, mtime))
        
        # 按修改时间排序，最旧的在前面
        log_files.sort(key=lambda x: x[1])
        
        return log_files
    
    def get_disk_free_space(self):
        """
        获取日志目录所在磁盘的可用空间（MB）
        
        Returns:
            float: 可用空间（MB）
        """
        if not os.path.exists(self.log_dir):
            return float('inf')  # 如果目录不存在，返回无限大
        
        try:
            # 获取磁盘可用空间
            free_bytes = shutil.disk_usage(self.log_dir).free
            return free_bytes / (1024 * 1024)  # 转换为MB
        except OSError as e:
            logger.error("获取磁盘可用空间失败: %s", str(e))
            return float('inf')  # 出错时返回无限大
    
    def clean_old_logs(self):
        """
        清理超过最大保留天数的旧日志文件
        
        Returns:
            int: 清理的文件数量
        """
        cleaned_count = 0
        cutoff_time = time.time() - (self.max_days * 24 * 60 * 60)
        
        log_files = self.get_log_files()
        
        for file_path, mtime in log_files:
            if mtime < cutoff_time:
                try:
                    os.remove(file_path)
                    logger.info("已删除旧日志文件: %s", file_path)
                    cleaned_count += 1
                except OSError as e:
                    logger.error("删除日志文件失败: %s, 错误: %s", file_path, str(e))
        
        return cleaned_count
    
    def clean_by_space(self, target_free_mb=None):
        """
        根据可用空间清理日志文件
        如果可用空间小于最小可用空间，则清理最旧的日志文件
        
        Args:
            target_free_mb: 目标可用空间（MB），默认为min_free_space_mb的两倍
            
        Returns:
            int: 清理的文件数量
        """
        if target_free_mb is None:
            target_free_mb = self.min_free_space_mb * 2
        
        cleaned_count = 0
        free_mb = self.get_disk_free_space()
        
        if free_mb < self.min_free_space_mb:
            logger.warning("磁盘可用空间不足: %.2fMB, 低于最小要求: %dMB", free_mb, self.min_free_space_mb)
            
            log_files = self.get_log_files()
            
            # 从最旧的文件开始删除，直到达到目标可用空间
            for file_path, _ in log_files:
                try:
                    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    os.remove(file_path)
                    logger.info("已删除日志文件以释放空间: %s (%.2fMB)", file_path, file_size_mb)
                    cleaned_count += 1
                    
                    # 重新检查可用空间
                    free_mb = self.get_disk_free_space()
                    if free_mb >= target_free_mb:
                        logger.info("已达到目标可用空间: %.2fMB", free_mb)
                        break
                except OSError as e:
                    logger.error("删除日志文件失败: %s, 错误: %s", file_path, str(e))
        
        return cleaned_count
    
    def run_cleanup(self):
        """
        运行日志清理，先按时间清理，再按空间清理
        
        Returns:
            tuple: (按时间清理的文件数, 按空间清理的文件数)
        """
        logger.info("开始清理日志文件...")
        
        # 按时间清理
        time_cleaned_count = self.clean_old_logs()
        logger.info("按时间清理完成，共删除 %d 个过期日志文件", time_cleaned_count)
        
        # 按空间清理
        space_cleaned_count = self.clean_by_space()
        if space_cleaned_count > 0:
            logger.info("按空间清理完成，共删除 %d 个日志文件以释放空间", space_cleaned_count)
        
        return (time_cleaned_count, space_cleaned_count)


def clean_logs(log_dir=None, max_days=30, min_free_space_mb=500):
    """
    清理日志的便捷函数
    
    Args:
        log_dir: 日志目录
        max_days: 最大保留天数
        min_free_space_mb: 最小可用空间(MB)
        
    Returns:
        tuple: (按时间清理的文件数, 按空间清理的文件数)
    """
    cleaner = LogCleaner(log_dir, max_days, min_free_space_mb)
    return cleaner.run_cleanup()


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
    )
    
    # 运行清理
    time_cleaned, space_cleaned = clean_logs()
    print(f"日志清理完成，按时间清理: {time_cleaned}个文件，按空间清理: {space_cleaned}个文件")
