#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强型爬虫批处理示例脚本
演示如何使用增强型爬虫的批处理功能爬取多个新闻源
"""

import os
import time
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.crawlers.factory import CrawlerFactory
from app.utils.logger import get_logger

# 初始化日志记录器
logger = get_logger('batch_demo')

# 支持的新闻源列表
SUPPORTED_SOURCES = ['东方财富', '新浪财经', '网易财经', '凤凰财经']

class BatchCrawlerDemo:
    """增强型爬虫批处理示例类"""
    
    def __init__(self, output_dir='data/batch_demo', max_workers=2):
        """
        初始化批处理示例
        
        Args:
            output_dir: 输出目录
            max_workers: 最大工作线程数
        """
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.factory = CrawlerFactory()
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 记录开始时间
        self.start_time = datetime.now()
        self.crawl_results = {}
    
    def crawl_source(self, source, days=1, max_news=20, config=None):
        """
        爬取单个新闻源
        
        Args:
            source: 新闻源名称
            days: 爬取天数
            max_news: 最大爬取数量
            config: 爬虫配置
            
        Returns:
            爬取结果字典
        """
        logger.info(f"开始爬取 {source}，天数: {days}，最大新闻数: {max_news}")
        
        try:
            # 默认配置
            default_config = {
                'concurrency_per_domain': 3,
                'domain_delay': 0.5,
                'chunk_size': 10,
                'timeout': 30
            }
            
            # 合并配置
            if config:
                default_config.update(config)
            
            # 创建数据库路径
            db_path = os.path.join(self.output_dir, f"{source}_{self.start_time.strftime('%Y%m%d_%H%M')}.db")
            
            # 创建爬虫
            crawler = self.factory.create_enhanced_crawler(source, db_path, default_config)
            
            # 记录开始时间
            start = time.time()
            
            # 执行爬取
            articles = crawler.crawl(days=days, max_news=max_news)
            
            # 计算耗时
            elapsed = time.time() - start
            
            # 获取统计信息
            stats = crawler.get_stats()
            
            # 准备结果
            result = {
                'source': source,
                'success': True,
                'article_count': len(articles),
                'time': elapsed,
                'database': db_path,
                'stats': stats
            }
            
            logger.info(f"{source} 爬取完成: {len(articles)} 篇文章, 耗时: {elapsed:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"{source} 爬取失败: {str(e)}")
            return {
                'source': source,
                'success': False,
                'error': str(e),
                'time': 0,
                'article_count': 0
            }
    
    def run_batch(self, sources=None, days=1, max_news=20, configs=None):
        """
        运行批处理爬取
        
        Args:
            sources: 要爬取的新闻源列表，默认为所有支持的源
            days: 爬取天数
            max_news: 最大爬取数量
            configs: 每个源的配置字典
            
        Returns:
            所有爬取结果的字典
        """
        if sources is None:
            sources = SUPPORTED_SOURCES
            
        if configs is None:
            configs = {}
            
        logger.info(f"开始批处理爬取，源: {sources}，最大工作线程: {self.max_workers}")
        print(f"\n===== 开始批处理爬取 =====")
        print(f"爬取源: {', '.join(sources)}")
        print(f"爬取天数: {days}, 最大新闻数: {max_news}")
        print(f"最大并行爬取数: {self.max_workers}")
        
        batch_start = time.time()
        results = {}
        
        # 使用线程池执行并行爬取
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_source = {
                executor.submit(
                    self.crawl_source, 
                    source, 
                    days, 
                    max_news, 
                    configs.get(source)
                ): source for source in sources
            }
            
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    result = future.result()
                    results[source] = result
                except Exception as e:
                    logger.error(f"处理 {source} 结果时出错: {str(e)}")
                    results[source] = {
                        'source': source,
                        'success': False,
                        'error': str(e)
                    }
        
        # 计算总体结果
        total_time = time.time() - batch_start
        total_articles = sum(r.get('article_count', 0) for r in results.values())
        success_count = sum(1 for r in results.values() if r.get('success', False))
        
        print(f"\n===== 批处理完成 =====")
        print(f"总耗时: {total_time:.2f}秒")
        print(f"成功源数: {success_count}/{len(sources)}")
        print(f"总文章数: {total_articles}")
        
        # 打印详细结果
        print("\n详细结果:")
        for source, result in results.items():
            status = "成功" if result.get('success', False) else "失败"
            article_count = result.get('article_count', 0)
            time_cost = result.get('time', 0)
            error = result.get('error', '')
            
            print(f"- {source}: {status}, 文章数: {article_count}, 耗时: {time_cost:.2f}秒")
            if error:
                print(f"  错误: {error}")
        
        return results


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description="增强型爬虫批处理演示")
    parser.add_argument("--sources", type=str, nargs="+", 
                      help=f"要爬取的数据源列表 (支持: {', '.join(SUPPORTED_SOURCES)})")
    parser.add_argument("--days", type=int, default=1,
                      help="爬取天数")
    parser.add_argument("--max-news", type=int, default=20,
                      help="每个源最大爬取数量")
    parser.add_argument("--workers", type=int, default=2,
                      help="最大并行爬取数")
    parser.add_argument("--output-dir", type=str, default="data/batch_demo",
                      help="输出目录")
    
    args = parser.parse_args()
    
    # 初始化批处理演示
    demo = BatchCrawlerDemo(args.output_dir, args.workers)
    
    # 运行批处理
    demo.run_batch(
        sources=args.sources,
        days=args.days,
        max_news=args.max_news
    )


if __name__ == "__main__":
    main() 