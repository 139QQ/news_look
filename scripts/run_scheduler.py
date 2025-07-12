#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 调度器运行入口
"""

import os
import sys
import time
import logging
import argparse
import importlib
from pathlib import Path

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from backend.app.tasks.scheduler import start_scheduler
from backend.app.utils.logger import configure_logger, get_logger

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="财经新闻爬虫调度器")
    parser.add_argument("--daemon", action="store_true", help="以守护进程方式运行")
    parser.add_argument("--config", help="指定配置文件路径")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
                        help="日志级别，默认为INFO")
    parser.add_argument("--log-dir", type=str, default='./logs', help="日志存储目录")
    parser.add_argument("--task", help="指定要执行的任务名称，如不指定则执行配置文件中的所有任务")
    parser.add_argument("--list-tasks", action="store_true", help="列出所有可用的调度任务")
    return parser.parse_args()

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 设置环境变量，供日志模块使用
    if args.log_level:
        os.environ['LOG_LEVEL'] = args.log_level
    if args.log_dir:
        os.environ['LOG_DIR'] = args.log_dir
    
    # 获取调度器日志记录器
    logger = configure_logger(name="scheduler", module="scheduler")
    
    # 列出所有可用的调度任务
    if args.list_tasks:
        try:
            # 导入任务模块
            from backend.app.tasks import get_all_tasks
            tasks = get_all_tasks()
            
            logger.info("可用的调度任务:")
            for task_name, task_info in tasks.items():
                logger.info(f"  - {task_name}: {task_info['description']}")
            
            return
        except ImportError as e:
            logger.error(f"无法导入任务模块: {e}")
            return
    
    # 启动调度器
    logger.info("启动调度器...")
    try:
        scheduler = start_scheduler(config_path=args.config)
        
        # 如果是守护进程模式，则一直运行
        if args.daemon:
            try:
                logger.info("调度器已启动，以守护进程方式运行...")
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止调度器...")
                scheduler.shutdown()
        else:
            # 非守护进程模式，等待所有任务完成
            logger.info("调度器已启动，等待所有任务完成...")
            scheduler.shutdown(wait=True)
            logger.info("调度器已停止")
    except Exception as e:
        logger.error(f"启动调度器失败: {e}")
        logger.exception(e)

if __name__ == "__main__":
    main() 