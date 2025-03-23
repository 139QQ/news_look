#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志记录修复脚本

该脚本用于修复NewsLook项目中的日志记录重复输出问题，包括：
1. 修改logger.py中的configure_logger函数，防止重复配置
2. 添加全局日志缓存管理
3. 确保日志初始化只进行一次
"""

import os
import re
import logging
import shutil
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def backup_file(file_path):
    """
    备份文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        备份文件路径
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    backup_path = f"{file_path}.{timestamp}.bak"
    shutil.copy2(file_path, backup_path)
    logger.info(f"已备份文件: {backup_path}")
    return backup_path

def fix_logger_module():
    """修复logger.py模块"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    # logger.py的路径
    logger_path = os.path.join(project_root, "app", "utils", "logger.py")
    
    if not os.path.exists(logger_path):
        logger.error(f"未找到日志模块文件: {logger_path}")
        return False
    
    # 备份文件
    backup_file(logger_path)
    
    # 读取文件内容
    with open(logger_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修改configure_logger函数
    pattern = r'def configure_logger\([^)]*\):[^@]*?(?=def|\Z)'
    
    replacement = '''def configure_logger(name, level=None, log_file=None, module=None, max_bytes=10*1024*1024, backup_count=5, propagate=False):
    """
    配置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
        module: 模块名
        max_bytes: 日志文件最大大小
        backup_count: 备份文件数量
        propagate: 是否传播日志事件
        
    Returns:
        logging.Logger: 已配置的日志记录器
    """
    global _logger_cache
    
    # 检查日志记录器是否已存在于缓存中
    if name in _logger_cache:
        return _logger_cache[name]
    
    # 获取日志记录器
    log = logging.getLogger(name)
    
    # 防止重复配置
    if hasattr(log, '_configured') and log._configured:
        return log
    
    # 设置日志级别
    if level is None:
        level = LOG_CONFIG.get('level', logging.INFO)
    log.setLevel(level)
    
    # 如果已有处理器，不再添加新处理器
    if log.handlers:
        log._configured = True
        _logger_cache[name] = log
        return log
    
    # 确定日志文件路径
    if log_file is None:
        log_file = LOG_CONFIG.get('file', 'logs/finance_news_crawler.log')
    
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    if importlib.util.find_spec("colorlog"):
        formatter = colorlog.ColoredFormatter(
            COLOR_LOG_FORMAT,
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors=COLOR_DICT
        )
    else:
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
    
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)
    
    # 添加文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S'))
    log.addHandler(file_handler)
    
    # 设置propagate属性
    log.propagate = propagate
    
    # 标记为已配置
    log._configured = True
    
    # 缓存日志记录器
    _logger_cache[name] = log
    
    return log
'''
    
    # 替换configure_logger函数
    modified_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # 确保有_logger_cache全局变量声明
    if "_logger_cache = {}" not in modified_content:
        modified_content = modified_content.replace(
            "# 创建日志记录器缓存，防止重复创建\n_logger_cache = {}",
            "# 创建日志记录器缓存，防止重复创建\n_logger_cache = {}"
        )
    
    # 写入修改后的内容
    with open(logger_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    logger.info(f"已修复日志模块: {logger_path}")
    return True

def main():
    """主函数"""
    logger.info("开始修复日志记录模块")
    
    if fix_logger_module():
        logger.info("日志记录模块修复完成")
    else:
        logger.error("日志记录模块修复失败")

if __name__ == "__main__":
    main() 