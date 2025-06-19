#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 爬虫性能基准测试
用于比较不同爬虫实现的性能差异
"""

import os
import time
import json
import asyncio
import argparse
from typing import Dict, List, Any
from datetime import datetime

from backend.app.utils.logger import get_logger
from backend.app.crawlers.core import BaseCrawler
from backend.app.crawlers.enhanced_crawler import EnhancedCrawler
from backend.app.crawlers.factory import CrawlerFactory

# 初始化日志记录器
logger = get_logger('benchmark')

class CrawlerBenchmark:
    """爬虫性能基准测试类"""
    
    def __init__(self, db_dir: str = 'data/benchmark', config_dir: str = 'configs/crawlers'):
        """
        初始化基准测试
        
        Args:
            db_dir: 数据库目录
            config_dir: 配置文件目录
        """
        self.db_dir = db_dir
        self.config_dir = config_dir
        
        # 创建目录
        os.makedirs(db_dir, exist_ok=True)
        
        # 初始化工厂
        self.factory = CrawlerFactory(config_dir=config_dir)
        
        # 测试结果
        self.results = {}
        
        logger.info(f"基准测试初始化完成，使用数据库目录: {db_dir}")
    
    def run_benchmark(self, sources: List[str] = None, days: int = 1, max_news: int = 10,
                     standard_options: Dict[str, Any] = None, 
                     enhanced_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        运行基准测试
        
        Args:
            sources: 要测试的数据源列表，为None则测试所有源
            days: 爬取天数
            max_news: 最大爬取数量
            standard_options: 标准爬虫选项
            enhanced_options: 增强型爬虫选项
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        # 确保选项字典存在
        if standard_options is None:
            standard_options = {
                'async_mode': True,
                'max_concurrency': 5,
                'timeout': 30
            }
            
        if enhanced_options is None:
            enhanced_options = {
                'concurrency_per_domain': 5,
                'chunk_size': 10,
                'domain_delay': 0
            }
        
        # 获取要测试的源
        if not sources:
            sources = self.factory.get_supported_sources()
            
        # 测试每个源
        results = {}
        
        for source in sources:
            logger.info(f"开始测试源: {source}")
            
            # 测试标准爬虫
            standard_db = os.path.join(self.db_dir, f"{source}_standard.db")
            standard_start = time.time()
            standard_crawler = self.factory.create_crawler(source, standard_db, standard_options)
            standard_articles = standard_crawler.crawl(days=days, max_news=max_news)
            standard_time = time.time() - standard_start
            
            logger.info(f"标准爬虫 {source} 完成，耗时: {standard_time:.2f}秒，获取 {len(standard_articles)} 篇文章")
            
            # 测试增强型爬虫
            enhanced_db = os.path.join(self.db_dir, f"{source}_enhanced.db")
            enhanced_start = time.time()
            enhanced_crawler = self.factory.create_enhanced_crawler(source, enhanced_db, enhanced_options)
            enhanced_articles = enhanced_crawler.crawl(days=days, max_news=max_news)
            enhanced_time = time.time() - enhanced_start
            
            logger.info(f"增强型爬虫 {source} 完成，耗时: {enhanced_time:.2f}秒，获取 {len(enhanced_articles)} 篇文章")
            
            # 记录结果
            source_result = {
                'standard': {
                    'time': standard_time,
                    'articles': len(standard_articles),
                    'articles_per_second': len(standard_articles) / standard_time if standard_time > 0 else 0
                },
                'enhanced': {
                    'time': enhanced_time,
                    'articles': len(enhanced_articles),
                    'articles_per_second': len(enhanced_articles) / enhanced_time if enhanced_time > 0 else 0
                },
                'improvement': (standard_time - enhanced_time) / standard_time * 100 if standard_time > 0 else 0
            }
            
            results[source] = source_result
            
            logger.info(f"源 {source} 测试结果: 标准爬虫 {standard_time:.2f}秒, 增强型爬虫 {enhanced_time:.2f}秒, "
                       f"性能提升: {source_result['improvement']:.2f}%")
        
        # 计算总体结果
        total_standard_time = sum(r['standard']['time'] for r in results.values())
        total_enhanced_time = sum(r['enhanced']['time'] for r in results.values())
        total_standard_articles = sum(r['standard']['articles'] for r in results.values())
        total_enhanced_articles = sum(r['enhanced']['articles'] for r in results.values())
        
        overall_result = {
            'sources': results,
            'summary': {
                'total_sources': len(sources),
                'standard': {
                    'total_time': total_standard_time,
                    'total_articles': total_standard_articles,
                    'articles_per_second': total_standard_articles / total_standard_time if total_standard_time > 0 else 0
                },
                'enhanced': {
                    'total_time': total_enhanced_time,
                    'total_articles': total_enhanced_articles,
                    'articles_per_second': total_enhanced_articles / total_enhanced_time if total_enhanced_time > 0 else 0
                },
                'overall_improvement': (total_standard_time - total_enhanced_time) / total_standard_time * 100 if total_standard_time > 0 else 0,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        
        # 保存结果
        self.results = overall_result
        self._save_results()
        
        logger.info(f"基准测试完成，总体性能提升: {overall_result['summary']['overall_improvement']:.2f}%")
        
        return overall_result
    
    def _save_results(self, filename: str = None) -> None:
        """
        保存测试结果到文件
        
        Args:
            filename: 文件名，默认为基于时间戳的文件名
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"benchmark_results_{timestamp}.json"
            
        filepath = os.path.join(self.db_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=4)
            
        logger.info(f"测试结果已保存到: {filepath}")
    
    def print_results(self) -> None:
        """打印测试结果摘要"""
        if not self.results:
            logger.warning("没有可用的测试结果")
            return
            
        summary = self.results['summary']
        sources = self.results['sources']
        
        print("\n===== 爬虫性能基准测试结果 =====")
        print(f"测试时间: {summary['timestamp']}")
        print(f"测试源数量: {summary['total_sources']}")
        print("\n----- 总体性能 -----")
        print(f"标准爬虫总时间: {summary['standard']['total_time']:.2f}秒")
        print(f"增强型爬虫总时间: {summary['enhanced']['total_time']:.2f}秒")
        print(f"标准爬虫总文章数: {summary['standard']['total_articles']}")
        print(f"增强型爬虫总文章数: {summary['enhanced']['total_articles']}")
        print(f"标准爬虫吞吐量: {summary['standard']['articles_per_second']:.2f} 文章/秒")
        print(f"增强型爬虫吞吐量: {summary['enhanced']['articles_per_second']:.2f} 文章/秒")
        print(f"总体性能提升: {summary['overall_improvement']:.2f}%")
        
        print("\n----- 各源性能对比 -----")
        for source, result in sorted(sources.items(), key=lambda x: x[1]['improvement'], reverse=True):
            print(f"\n{source}:")
            print(f"  标准爬虫: {result['standard']['time']:.2f}秒, {result['standard']['articles']} 篇文章")
            print(f"  增强型爬虫: {result['enhanced']['time']:.2f}秒, {result['enhanced']['articles']} 篇文章")
            print(f"  性能提升: {result['improvement']:.2f}%")
        
        print("\n===============================")


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description="财经新闻爬虫性能基准测试")
    parser.add_argument("--sources", type=str, help="要测试的数据源，逗号分隔")
    parser.add_argument("--days", type=int, default=1, help="爬取天数")
    parser.add_argument("--max", type=int, default=10, help="最大爬取数量")
    parser.add_argument("--db-dir", type=str, default="data/benchmark", help="数据库目录")
    parser.add_argument("--config-dir", type=str, default="configs/crawlers", help="配置文件目录")
    
    args = parser.parse_args()
    
    # 解析数据源
    sources = None
    if args.sources:
        sources = [s.strip() for s in args.sources.split(',')]
    
    # 运行基准测试
    benchmark = CrawlerBenchmark(db_dir=args.db_dir, config_dir=args.config_dir)
    benchmark.run_benchmark(sources=sources, days=args.days, max_news=args.max)
    benchmark.print_results()


if __name__ == "__main__":
    main() 