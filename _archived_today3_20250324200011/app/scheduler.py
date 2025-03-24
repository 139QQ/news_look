#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 调度器
"""

import os
import time
import logging
from datetime import datetime, timedelta
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class Scheduler:
    """调度器，用于定期执行爬虫任务"""
    
    def __init__(self, daemon=False):
        """
        初始化调度器
        
        Args:
            daemon: 是否以守护进程方式运行
        """
        self.daemon = daemon
        self.settings = get_settings()
        self.running = False
        self.tasks = {
            'daily_crawl': {
                'description': '每日爬取财经新闻',
                'interval': 24 * 60 * 60,  # 24小时
                'last_run': None,
                'next_run': datetime.now()
            },
            'hourly_crawl': {
                'description': '每小时爬取最新财经新闻',
                'interval': 60 * 60,  # 1小时
                'last_run': None,
                'next_run': datetime.now()
            }
        }
    
    def start(self):
        """启动调度器"""
        logger.info("调度器启动...")
        self.running = True
        
        try:
            if self.daemon:
                self._start_daemon()
            else:
                self._start_foreground()
        except KeyboardInterrupt:
            logger.info("接收到中断信号，调度器停止")
            self.running = False
    
    def _start_foreground(self):
        """在前台运行调度器"""
        logger.info("调度器在前台运行")
        while self.running:
            self._check_tasks()
            time.sleep(1)
    
    def _start_daemon(self):
        """以守护进程方式运行调度器"""
        logger.info("调度器以守护进程方式运行")
        # 具体实现省略，需要使用守护进程库
        pass
    
    def _check_tasks(self):
        """检查是否有任务需要执行"""
        now = datetime.now()
        for task_name, task in self.tasks.items():
            if now >= task['next_run']:
                self._run_task(task_name)
    
    def _run_task(self, task_name):
        """运行指定任务"""
        task = self.tasks[task_name]
        logger.info(f"执行任务: {task_name} - {task['description']}")
        
        try:
            # 根据任务名执行不同的操作
            if task_name == 'daily_crawl':
                self._run_daily_crawl()
            elif task_name == 'hourly_crawl':
                self._run_hourly_crawl()
            
            # 更新任务状态
            task['last_run'] = datetime.now()
            task['next_run'] = task['last_run'] + timedelta(seconds=task['interval'])
            logger.info(f"任务 {task_name} 执行完成，下次执行时间: {task['next_run']}")
            
        except Exception as e:
            logger.error(f"任务 {task_name} 执行失败: {e}")
    
    def _run_daily_crawl(self):
        """执行每日爬取任务"""
        from app.crawlers.manager import CrawlerManager
        manager = CrawlerManager()
        
        try:
            # 获取所有爬虫
            crawlers = manager.get_available_crawlers()
            logger.info(f"开始每日爬取，爬虫数量: {len(crawlers)}")
            
            # 运行每个爬虫
            for crawler_name in crawlers:
                try:
                    result = manager.run_crawler(crawler_name, days=1)
                    logger.info(f"爬虫 {crawler_name} 爬取完成，获取 {result} 条数据")
                except Exception as e:
                    logger.error(f"爬虫 {crawler_name} 运行失败: {e}")
            
            logger.info("每日爬取任务完成")
        finally:
            manager.close()
    
    def _run_hourly_crawl(self):
        """执行每小时爬取任务"""
        from app.crawlers.manager import CrawlerManager
        manager = CrawlerManager()
        
        try:
            # 获取所有爬虫
            crawlers = manager.get_available_crawlers()
            logger.info(f"开始每小时爬取，爬虫数量: {len(crawlers)}")
            
            # 运行每个爬虫
            for crawler_name in crawlers:
                try:
                    # 每小时爬取只获取最近0.1天的数据
                    result = manager.run_crawler(crawler_name, days=0.1)
                    logger.info(f"爬虫 {crawler_name} 爬取完成，获取 {result} 条数据")
                except Exception as e:
                    logger.error(f"爬虫 {crawler_name} 运行失败: {e}")
            
            logger.info("每小时爬取任务完成")
        finally:
            manager.close()
    
    def stop(self):
        """停止调度器"""
        logger.info("调度器停止")
        self.running = False
    
    def list_tasks(self):
        """列出所有可用的调度任务"""
        logger.info("可用的调度任务:")
        for task_name, task in self.tasks.items():
            next_run = task['next_run'].strftime('%Y-%m-%d %H:%M:%S') if task['next_run'] else '未设置'
            last_run = task['last_run'].strftime('%Y-%m-%d %H:%M:%S') if task['last_run'] else '从未运行'
            interval = timedelta(seconds=task['interval'])
            
            print(f"- {task_name}: {task['description']}")
            print(f"  间隔: {interval}")
            print(f"  上次运行: {last_run}")
            print(f"  下次运行: {next_run}")
            print("") 