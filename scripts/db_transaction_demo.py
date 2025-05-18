#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库事务和并发控制功能演示脚本
用于演示如何使用数据库事务功能，以及事务在高并发情况下的性能和可靠性
"""

import os
import sys
import time
import random
import logging
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入事务数据库管理器和日志工具
from app.utils.db_transaction import TransactionalDBManager, create_db_manager, DEFAULT_TABLE_SCHEMAS
from app.utils.logger import configure_logger

# 设置日志
logger = configure_logger('db_transaction_demo', level=logging.INFO)

# 测试数据库路径
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'test_transaction.db')

def generate_test_news(count=100):
    """
    生成测试新闻数据
    
    Args:
        count: 生成的新闻数量
        
    Returns:
        list: 新闻数据列表
    """
    news_list = []
    for i in range(count):
        timestamp = int(time.time() * 1000) + i
        news_data = {
            'id': f"test_{timestamp}",
            'title': f"测试新闻标题 {i+1}",
            'content': f"这是测试新闻内容 {i+1}，用于演示数据库事务功能。" * 3,
            'pub_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'author': '测试作者',
            'source': '测试来源',
            'url': f"https://example.com/news/{timestamp}",
            'keywords': f"测试,事务,数据库,新闻,{i+1}",
            'images': f"https://example.com/images/{timestamp}_1.jpg,https://example.com/images/{timestamp}_2.jpg",
            'related_stocks': f"000001,600001,300001",
            'sentiment': random.choice(['积极', '中性', '消极']),
            'category': random.choice(['财经', '股票', '基金', '外汇']),
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        news_list.append(news_data)
    return news_list

def basic_transaction_demo():
    """基本事务功能演示"""
    logger.info("=== 基本事务功能演示 ===")
    
    # 创建数据库管理器
    db_manager = create_db_manager(TEST_DB_PATH)
    
    # 生成测试数据
    news_list = generate_test_news(10)
    
    # 使用事务保存单条新闻
    for i, news in enumerate(news_list[:3], 1):
        try:
            start_time = time.time()
            result = db_manager.save_news(news)
            end_time = time.time()
            status = "成功" if result else "失败"
            logger.info(f"保存新闻 {i} {status}，耗时: {(end_time - start_time)*1000:.2f} ms")
        except Exception as e:
            logger.error(f"保存新闻 {i} 出错: {str(e)}")
    
    # 使用批量事务保存多条新闻
    try:
        start_time = time.time()
        saved_count = db_manager.batch_save_news(news_list[3:])
        end_time = time.time()
        logger.info(f"批量保存 {saved_count}/{len(news_list[3:])} 条新闻成功，耗时: {(end_time - start_time)*1000:.2f} ms")
    except Exception as e:
        logger.error(f"批量保存新闻出错: {str(e)}")

def concurrent_transaction_demo(worker_count=5, news_per_worker=10):
    """
    并发事务功能演示
    
    Args:
        worker_count: 并发工作线程数
        news_per_worker: 每个工作线程处理的新闻数量
    """
    logger.info(f"=== 并发事务功能演示 (工作线程: {worker_count}, 每线程新闻: {news_per_worker}) ===")
    
    # 创建数据库管理器 (所有线程共享同一个数据库)
    db_manager = create_db_manager(TEST_DB_PATH)
    
    # 生成测试数据
    all_news = generate_test_news(worker_count * news_per_worker)
    
    # 工作线程函数
    def worker(worker_id, news_list):
        logger.info(f"工作线程 {worker_id} 启动，需处理 {len(news_list)} 条新闻")
        
        try:
            # 保存新闻到数据库
            start_time = time.time()
            saved_count = db_manager.batch_save_news(news_list)
            end_time = time.time()
            
            # 统计结果
            logger.info(f"工作线程 {worker_id} 完成，成功保存 {saved_count}/{len(news_list)} 条新闻，"
                      f"耗时: {(end_time - start_time)*1000:.2f} ms")
            return saved_count
        except Exception as e:
            logger.error(f"工作线程 {worker_id} 出错: {str(e)}")
            return 0
    
    # 启动多个工作线程
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = []
        for i in range(worker_count):
            start_idx = i * news_per_worker
            end_idx = start_idx + news_per_worker
            worker_news = all_news[start_idx:end_idx]
            futures.append(executor.submit(worker, i+1, worker_news))
        
        # 收集结果
        total_saved = 0
        for future in futures:
            total_saved += future.result()
        
        logger.info(f"所有工作线程完成，总共成功保存 {total_saved}/{len(all_news)} 条新闻")

def retry_mechanism_demo():
    """重试机制演示"""
    logger.info("=== 数据库重试机制演示 ===")
    
    # 创建数据库管理器
    db_manager = create_db_manager(TEST_DB_PATH)
    
    # 添加锁模拟
    db_lock = threading.RLock()
    
    # 生成测试数据
    news = generate_test_news(1)[0]
    
    def lock_db_worker():
        """模拟锁定数据库一段时间"""
        logger.info("开始锁定数据库 (将持续3秒)...")
        with db_lock:
            # 锁定数据库3秒
            time.sleep(3)
        logger.info("数据库锁定结束")
    
    def save_news_worker():
        """
        尝试保存新闻，但会遇到数据库锁
        这里我们使用自己的锁来模拟SQLite锁
        """
        # 延迟2秒，确保数据库已被锁定
        time.sleep(1)
        logger.info("尝试保存新闻 (数据库被锁定时)")
        
        try:
            with db_lock:
                # 现在我们能够获取锁，模拟数据库操作
                start_time = time.time()
                result = db_manager.save_news(news)
                end_time = time.time()
                
                status = "成功" if result else "失败"
                logger.info(f"保存新闻{status}，耗时: {(end_time - start_time)*1000:.2f} ms")
        except Exception as e:
            logger.error(f"保存新闻出错: {str(e)}")
    
    # 创建并启动线程
    lock_thread = threading.Thread(target=lock_db_worker)
    save_thread = threading.Thread(target=save_news_worker)
    
    lock_thread.start()
    save_thread.start()
    
    # 等待线程完成
    lock_thread.join()
    save_thread.join()
    
    logger.info("重试机制演示完成")

def performance_test(news_count=1000, batch_size=100):
    """
    性能测试
    
    Args:
        news_count: 测试新闻总数
        batch_size: 批量保存的大小
    """
    logger.info(f"=== 性能测试 (总数: {news_count}, 批量大小: {batch_size}) ===")
    
    # 创建数据库管理器
    db_path = os.path.join(os.path.dirname(TEST_DB_PATH), 'test_performance.db')
    db_manager = create_db_manager(db_path)
    
    # 生成测试数据
    all_news = generate_test_news(news_count)
    
    # 单条保存性能测试
    sample_size = min(100, news_count)
    logger.info(f"1. 单条保存性能测试 (样本: {sample_size} 条)")
    
    start_time = time.time()
    for news in all_news[:sample_size]:
        db_manager.save_news(news)
    end_time = time.time()
    
    single_time = (end_time - start_time)
    logger.info(f"   单条保存耗时: {single_time:.2f} 秒, 平均: {(single_time*1000/sample_size):.2f} ms/条")
    
    # 批量保存性能测试
    logger.info(f"2. 批量保存性能测试 (总数: {news_count}, 批量大小: {batch_size})")
    
    # 分批处理
    batches = [all_news[i:i+batch_size] for i in range(0, news_count, batch_size)]
    
    start_time = time.time()
    total_saved = 0
    for i, batch in enumerate(batches, 1):
        saved = db_manager.batch_save_news(batch)
        total_saved += saved
        if i % 5 == 0 or i == len(batches):
            logger.info(f"   已处理 {i}/{len(batches)} 批, 保存: {total_saved}/{news_count} 条")
    end_time = time.time()
    
    batch_time = (end_time - start_time)
    logger.info(f"   批量保存耗时: {batch_time:.2f} 秒, 平均: {(batch_time*1000/news_count):.2f} ms/条")
    
    # 对比结果
    speedup = (single_time / sample_size) / (batch_time / news_count)
    logger.info(f"   批量保存性能提升: {speedup:.2f}x")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库事务和并发控制功能演示")
    parser.add_argument("--mode", type=str, choices=["basic", "concurrent", "retry", "performance", "all"], 
                       default="all", help="演示模式")
    parser.add_argument("--workers", type=int, default=5, help="并发工作线程数")
    parser.add_argument("--news", type=int, default=10, help="每个线程处理的新闻数量")
    parser.add_argument("--count", type=int, default=1000, help="性能测试的新闻总数")
    parser.add_argument("--batch", type=int, default=100, help="批量保存的大小")
    
    args = parser.parse_args()
    
    # 确保测试数据目录存在
    os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)
    
    # 运行演示
    if args.mode == "basic" or args.mode == "all":
        basic_transaction_demo()
        
    if args.mode == "concurrent" or args.mode == "all":
        concurrent_transaction_demo(args.workers, args.news)
        
    if args.mode == "retry" or args.mode == "all":
        retry_mechanism_demo()
        
    if args.mode == "performance" or args.mode == "all":
        performance_test(args.count, args.batch) 