#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 任务调度器
"""

import time
import logging
import schedule
import os
import sys
from datetime import datetime

from app.utils.logger import setup_logger
from app.crawlers import run_crawlers

logger = setup_logger()

def run_crawler_task():
    """运行爬虫任务"""
    logger.info("开始执行定时爬虫任务...")
    
    try:
        # 运行爬虫
        news_data = run_crawlers(days=1)
        logger.info(f"爬虫任务完成，共获取 {len(news_data)} 条新闻")
        
        # 生成HTML报告
        from app.utils.report_generator import generate_html_report
        report_path = generate_html_report(news_data)
        logger.info(f"HTML报告已生成: {report_path}")
        
        # 移动报告到指定目录
        if os.path.exists(report_path):
            # 创建报告目录
            report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'reports')
            os.makedirs(report_dir, exist_ok=True)
            
            # 生成新的报告文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_report_path = os.path.join(report_dir, f'news_report_{timestamp}.html')
            
            # 移动报告
            import shutil
            shutil.copy2(report_path, new_report_path)
            logger.info(f"报告已复制到: {new_report_path}")
        
        return True
    except Exception as e:
        logger.error(f"爬虫任务执行失败: {str(e)}")
        return False

def start_scheduler(config_path=None):
    """
    启动任务调度器
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        schedule.Scheduler: 调度器对象
    """
    # 设置定时任务
    schedule.every().day.at("08:00").do(run_crawler_task)
    schedule.every().day.at("18:00").do(run_crawler_task)
    
    # 如果提供了配置文件，则从配置文件加载定时设置
    if config_path and os.path.exists(config_path):
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 清除现有任务
            schedule.clear()
            
            # 添加新任务
            if 'schedule' in config:
                for task in config['schedule']:
                    if 'time' in task and 'type' in task:
                        if task['type'] == 'daily':
                            schedule.every().day.at(task['time']).do(run_crawler_task)
                        elif task['type'] == 'weekly' and 'day' in task:
                            days = {
                                'monday': schedule.every().monday,
                                'tuesday': schedule.every().tuesday,
                                'wednesday': schedule.every().wednesday,
                                'thursday': schedule.every().thursday,
                                'friday': schedule.every().friday,
                                'saturday': schedule.every().saturday,
                                'sunday': schedule.every().sunday
                            }
                            if task['day'].lower() in days:
                                days[task['day'].lower()].at(task['time']).do(run_crawler_task)
                        elif task['type'] == 'interval' and 'minutes' in task:
                            schedule.every(int(task['minutes'])).minutes.do(run_crawler_task)
            
            logger.info(f"从配置文件加载定时设置: {config_path}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
    
    logger.info("任务调度器已启动")
    
    # 立即运行一次
    run_crawler_task()
    
    # 启动调度器
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    # 创建线程运行调度器
    import threading
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    return schedule 