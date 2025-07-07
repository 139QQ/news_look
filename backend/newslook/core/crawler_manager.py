#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强化爬虫管理器
实现线程安全、连接池、配置重试机制
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager
from backend.newslook.core.config_manager import get_config, get_connection_pool
from backend.newslook.core.error_handler import get_error_handler, auto_retry

logger = logging.getLogger(__name__)

class CrawlerManager:
    """强化爬虫管理器"""
    
    def __init__(self):
        """初始化爬虫管理器"""
        self.lock = threading.Lock()  # 🔧 线程安全锁
        self.crawlers: Dict[str, Any] = {}
        self.crawler_threads: Dict[str, threading.Thread] = {}
        self.stop_flags: Dict[str, threading.Event] = {}
        self.connection_pool = get_connection_pool()  # 🔧 连接池
        self.error_handler = get_error_handler()
        self.config = None
        
        # 🔧 配置重试机制
        self._load_config_with_retry()
        
        logger.info("🔧 强化爬虫管理器初始化完成")
    
    @auto_retry(max_attempts=3, backoff_factor=1.0)
    def _load_config_with_retry(self):
        """配置重试机制"""
        try:
            self.config = get_config()
            logger.info("🔧 配置加载成功")
        except Exception as e:
            logger.error(f"🔧 配置加载失败: {e}")
            raise
    
    def register_crawler(self, name: str, crawler_class: Any, config: Dict[str, Any] = None):
        """注册爬虫"""
        with self.lock:
            try:
                # 🔧 线程安全的爬虫注册
                if name not in self.crawlers:
                    self.crawlers[name] = crawler_class(config or {})
                    self.stop_flags[name] = threading.Event()
                    logger.info(f"🔧 爬虫注册成功: {name}")
                else:
                    logger.warning(f"🔧 爬虫已存在: {name}")
            except Exception as e:
                error_response = self.error_handler.handle_crawler_error(e, name)
                logger.error(f"🔧 爬虫注册失败: {name}, 错误: {error_response.message}")
                raise
    
    def start_crawler(self, name: str) -> bool:
        """启动爬虫"""
        with self.lock:
            try:
                if name not in self.crawlers:
                    raise ValueError(f"爬虫不存在: {name}")
                
                # 检查是否已在运行
                if name in self.crawler_threads and self.crawler_threads[name].is_alive():
                    logger.warning(f"🔧 爬虫已在运行: {name}")
                    return False
                
                # 清除停止标志
                self.stop_flags[name].clear()
                
                # 创建爬虫线程
                crawler_thread = threading.Thread(
                    target=self._run_crawler_safely,
                    args=(name,),
                    name=f"Crawler-{name}",
                    daemon=True
                )
                
                self.crawler_threads[name] = crawler_thread
                crawler_thread.start()
                
                logger.info(f"🔧 爬虫启动成功: {name}")
                return True
                
            except Exception as e:
                error_response = self.error_handler.handle_crawler_error(e, name)
                logger.error(f"🔧 爬虫启动失败: {name}, 错误: {error_response.message}")
                return False
    
    def stop_crawler(self, name: str) -> bool:
        """停止爬虫"""
        with self.lock:
            try:
                if name not in self.stop_flags:
                    raise ValueError(f"爬虫不存在: {name}")
                
                # 设置停止标志
                self.stop_flags[name].set()
                
                # 等待线程结束
                if name in self.crawler_threads:
                    thread = self.crawler_threads[name]
                    if thread.is_alive():
                        thread.join(timeout=10)  # 等待最多10秒
                        if thread.is_alive():
                            logger.warning(f"🔧 爬虫未能正常停止: {name}")
                            return False
                    
                    # 清理线程
                    del self.crawler_threads[name]
                
                logger.info(f"🔧 爬虫停止成功: {name}")
                return True
                
            except Exception as e:
                error_response = self.error_handler.handle_crawler_error(e, name)
                logger.error(f"🔧 爬虫停止失败: {name}, 错误: {error_response.message}")
                return False
    
    def _run_crawler_safely(self, name: str):
        """安全运行爬虫"""
        try:
            crawler = self.crawlers[name]
            stop_flag = self.stop_flags[name]
            
            # 🔧 使用连接池获取数据库连接
            db_path = self.config.database.main_db
            
            with self.connection_pool.get_connection(db_path) as conn:
                # 运行爬虫
                while not stop_flag.is_set():
                    try:
                        # 执行爬虫任务
                        if hasattr(crawler, 'run'):
                            crawler.run()
                        else:
                            logger.warning(f"🔧 爬虫没有run方法: {name}")
                            break
                        
                        # 检查停止标志
                        if stop_flag.wait(timeout=self.config.crawler.delay):
                            break
                            
                    except Exception as e:
                        error_response = self.error_handler.handle_crawler_error(e, name)
                        logger.error(f"🔧 爬虫运行错误: {name}, 错误: {error_response.message}")
                        
                        # 短暂休眠后继续
                        if not stop_flag.wait(timeout=5):
                            continue
                        else:
                            break
                            
        except Exception as e:
            error_response = self.error_handler.handle_crawler_error(e, name)
            logger.error(f"🔧 爬虫运行异常: {name}, 错误: {error_response.message}")
        
        finally:
            logger.info(f"🔧 爬虫运行结束: {name}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取爬虫状态"""
        with self.lock:
            status = {
                'total_crawlers': len(self.crawlers),
                'running_crawlers': 0,
                'stopped_crawlers': 0,
                'crawlers': {}
            }
            
            for name in self.crawlers:
                is_running = (name in self.crawler_threads and 
                            self.crawler_threads[name].is_alive())
                is_stopping = self.stop_flags[name].is_set()
                
                if is_running:
                    status['running_crawlers'] += 1
                    crawler_status = 'running'
                elif is_stopping:
                    crawler_status = 'stopping'
                else:
                    status['stopped_crawlers'] += 1
                    crawler_status = 'stopped'
                
                status['crawlers'][name] = {
                    'status': crawler_status,
                    'is_running': is_running,
                    'is_stopping': is_stopping,
                    'thread_alive': name in self.crawler_threads and self.crawler_threads[name].is_alive()
                }
            
            return status
    
    def shutdown(self):
        """关闭爬虫管理器"""
        logger.info("🔧 开始关闭爬虫管理器")
        
        # 停止所有爬虫
        for name in list(self.crawlers.keys()):
            self.stop_crawler(name)
        
        # 关闭连接池
        self.connection_pool.close_all()
        
        logger.info("🔧 爬虫管理器关闭完成")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown()

# 全局爬虫管理器实例
_crawler_manager = None

def get_crawler_manager() -> CrawlerManager:
    """获取全局爬虫管理器实例"""
    global _crawler_manager
    if _crawler_manager is None:
        _crawler_manager = CrawlerManager()
    return _crawler_manager 