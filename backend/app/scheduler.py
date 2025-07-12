#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 调度器
"""

import os
import time
import logging
from datetime import datetime, timedelta
from backend.app.config import get_settings
from backend.app.utils.logger import get_logger
from backend.app.utils.database import NewsDatabase

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
            },
            'daily_backup': {
                'description': '每日备份数据库',
                'interval': 24 * 60 * 60,  # 24小时
                'last_run': None,
                'next_run': datetime.now() + timedelta(hours=1)  # 启动1小时后进行第一次备份
            },
            'weekly_backup': {
                'description': '每周备份数据库',
                'interval': 7 * 24 * 60 * 60,  # 7天
                'last_run': None,
                'next_run': datetime.now() + timedelta(days=1)  # 启动1天后进行第一次备份
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
            elif task_name == 'daily_backup':
                self._run_daily_backup()
            elif task_name == 'weekly_backup':
                self._run_weekly_backup()
            
            # 更新任务状态
            task['last_run'] = datetime.now()
            task['next_run'] = task['last_run'] + timedelta(seconds=task['interval'])
            logger.info(f"任务 {task_name} 执行完成，下次执行时间: {task['next_run']}")
            
        except Exception as e:
            logger.error(f"任务 {task_name} 执行失败: {e}")
    
    def _run_daily_crawl(self):
        """执行每日爬取任务"""
        from backend.app.crawlers.manager import CrawlerManager
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
        from backend.app.crawlers.manager import CrawlerManager
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
    
    def _run_daily_backup(self):
        """执行每日备份任务"""
        try:
            # 创建数据库连接
            db = NewsDatabase()
            
            # 备份主数据库
            main_backup_path = db.backup_database()
            if main_backup_path:
                logger.info(f"主数据库备份成功: {main_backup_path}")
            
            # 获取所有数据源
            sources = db.get_available_sources()
            logger.info(f"开始每日备份数据源，数量: {len(sources)}")
            
            # 备份每个数据源
            for source in sources:
                try:
                    backup_path = db.backup_database(source)
                    if backup_path:
                        logger.info(f"数据源 {source} 备份成功: {backup_path}")
                except Exception as e:
                    logger.error(f"数据源 {source} 备份失败: {e}")
            
            # 清理过期备份（保留最近10个）
            self._clean_old_backups(db, max_keep=10)
            
            # 关闭数据库连接
            db.close()
            
            logger.info("每日备份任务完成")
        except Exception as e:
            logger.error(f"执行每日备份任务失败: {e}")
    
    def _run_weekly_backup(self):
        """执行每周备份任务"""
        try:
            # 创建数据库连接
            db = NewsDatabase()
            
            # 备份主数据库
            main_backup_path = db.backup_database()
            if main_backup_path:
                logger.info(f"主数据库周备份成功: {main_backup_path}")
                
                # 为周备份文件添加标记，确保不会被每日备份清理策略删除
                weekly_mark_path = main_backup_path + ".weekly"
                with open(weekly_mark_path, 'w') as f:
                    f.write(f"周备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 获取所有数据源
            sources = db.get_available_sources()
            logger.info(f"开始每周备份数据源，数量: {len(sources)}")
            
            # 备份每个数据源
            for source in sources:
                try:
                    backup_path = db.backup_database(source)
                    if backup_path:
                        logger.info(f"数据源 {source} 周备份成功: {backup_path}")
                        
                        # 为周备份文件添加标记
                        weekly_mark_path = backup_path + ".weekly"
                        with open(weekly_mark_path, 'w') as f:
                            f.write(f"周备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                except Exception as e:
                    logger.error(f"数据源 {source} 周备份失败: {e}")
            
            # 关闭数据库连接
            db.close()
            
            logger.info("每周备份任务完成")
        except Exception as e:
            logger.error(f"执行每周备份任务失败: {e}")
    
    def _clean_old_backups(self, db, max_keep=10):
        """
        清理过期备份，每个数据源只保留最新的几个备份
        
        Args:
            db: 数据库对象
            max_keep: 每个数据源要保留的最大备份数量
        """
        try:
            # 获取所有备份
            all_backups = db.get_backups()
            
            # 按数据源分组
            backups_by_source = {}
            for backup in all_backups:
                source = backup['source']
                if source not in backups_by_source:
                    backups_by_source[source] = []
                backups_by_source[source].append(backup)
            
            # 对每个数据源，只保留最新的几个备份
            for source, backups in backups_by_source.items():
                # 按时间降序排序
                backups.sort(key=lambda x: x['timestamp'], reverse=True)
                
                # 删除旧备份
                if len(backups) > max_keep:
                    for old_backup in backups[max_keep:]:
                        backup_path = old_backup['path']
                        
                        # 检查是否是周备份（有.weekly标记）
                        weekly_mark_path = backup_path + ".weekly"
                        if os.path.exists(weekly_mark_path):
                            logger.info(f"保留周备份: {backup_path}")
                            continue
                            
                        try:
                            os.remove(backup_path)
                            logger.info(f"删除旧备份: {backup_path}")
                        except Exception as e:
                            logger.error(f"删除旧备份失败 {backup_path}: {e}")
            
            logger.info("清理旧备份完成")
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
    
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