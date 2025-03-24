#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志系统修复脚本

该脚本用于修复NewsLook项目的日志系统重复输出问题，通过：
1. 修改logger.py中的configure_logger函数
2. 确保日志只初始化一次
3. 防止多个处理器重复添加到同一个日志器
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

def backup_logger_file(logger_file):
    """
    备份日志配置文件
    
    Args:
        logger_file: 日志配置文件路径
    
    Returns:
        备份文件路径
    """
    if not os.path.exists(logger_file):
        logger.error(f"日志配置文件不存在: {logger_file}")
        return None
    
    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    backup_path = f"{logger_file}.{timestamp}"
    
    # 复制文件
    try:
        shutil.copy2(logger_file, backup_path)
        logger.info(f"已备份日志配置文件: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"备份日志配置文件失败: {str(e)}")
        return None

def fix_logger_configuration(logger_file):
    """
    修复日志配置
    
    Args:
        logger_file: 日志配置文件路径
    
    Returns:
        是否成功修复
    """
    if not os.path.exists(logger_file):
        logger.error(f"日志配置文件不存在: {logger_file}")
        return False
    
    # 读取文件内容
    try:
        with open(logger_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"读取日志配置文件失败: {str(e)}")
        return False
    
    # 检查是否存在logger缓存和configure_logger函数
    has_logger_cache = '_logger_cache = {}' in content
    has_configure_logger = 'def configure_logger(' in content
    
    # 新的logger缓存代码
    logger_cache_code = '''
# 全局日志器缓存，用于防止重复配置
_logger_cache = {}
'''
    
    # 修改后的configure_logger函数代码
    configure_logger_code = '''
def configure_logger(name, level=None, log_file=None, module=None, 
                    max_bytes=10*1024*1024, backup_count=5, propagate=True):
    """
    配置日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径
        module: 模块名
        max_bytes: 日志文件最大字节数
        backup_count: 备份文件数量
        propagate: 是否传播日志事件
    
    Returns:
        logger: 配置好的日志器
    """
    global _logger_cache
    
    # 生成唯一的logger_id
    logger_id = f"{name}_{module or ''}"
    
    # 如果已经配置过该日志器，直接返回
    if logger_id in _logger_cache:
        return _logger_cache[logger_id]
    
    # 获取日志级别
    if level is None:
        level = logging.INFO if LOG_LEVEL is None else getattr(logging, LOG_LEVEL)
    
    # 获取日志文件路径
    if log_file is None:
        log_file = LOG_FILE
    
    # 创建日志目录
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 获取或创建日志器
    logger = logging.getLogger(name)
    
    # 如果已有处理器，说明已经配置过，直接返回
    if logger.handlers:
        _logger_cache[logger_id] = logger
        return logger
    
    # 设置日志级别
    logger.setLevel(level)
    
    # 设置日志传播
    logger.propagate = propagate
    
    # 创建处理器
    # 添加文件处理器
    if log_file:
        # 根据模块名修改日志文件名
        if module:
            log_basename = os.path.basename(log_file)
            log_dirname = os.path.dirname(log_file)
            module_log_file = os.path.join(log_dirname, f"{module}_{log_basename}")
        else:
            module_log_file = log_file
        
        file_handler = logging.handlers.RotatingFileHandler(
            module_log_file, 
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
        logger.addHandler(file_handler)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(colorlog.ColoredFormatter(
        COLOR_LOG_FORMAT,
        log_colors=COLOR_DICT
    ))
    logger.addHandler(console_handler)
    
    # 缓存已配置的日志器
    _logger_cache[logger_id] = logger
    
    return logger
'''
    
    # 修改文件内容
    new_content = content
    
    # 添加全局logger缓存
    if not has_logger_cache:
        import_match = re.search(r'import\s+traceback', new_content)
        if import_match:
            pos = import_match.end()
            new_content = new_content[:pos] + logger_cache_code + new_content[pos:]
            logger.info("已添加全局日志器缓存")
    
    # 替换configure_logger函数
    if has_configure_logger:
        # 查找函数定义
        pattern = r'def configure_logger\([^)]*\):.*?(?=\n\n|\n\w|\n$|$)'
        match = re.search(pattern, new_content, re.DOTALL)
        if match:
            # 替换函数定义
            new_content = new_content[:match.start()] + configure_logger_code.strip() + new_content[match.end():]
            logger.info("已修改configure_logger函数")
    else:
        logger.warning("未找到configure_logger函数，无法修复")
        return False
    
    # 保存修改后的文件
    try:
        with open(logger_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        logger.info("已成功保存修改后的日志配置文件")
        return True
    except Exception as e:
        logger.error(f"保存修改后的日志配置文件失败: {str(e)}")
        return False

def main():
    """主函数"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    # 日志配置文件路径
    logger_file = os.path.join(project_root, "app", "utils", "logger.py")
    
    logger.info("开始修复日志系统")
    
    # 备份日志配置文件
    backup_logger_file(logger_file)
    
    # 修复日志配置
    if fix_logger_configuration(logger_file):
        logger.info("日志系统修复完成")
    else:
        logger.error("日志系统修复失败")

if __name__ == "__main__":
    main() 