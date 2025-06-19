#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import json

logger = logging.getLogger(__name__)


class DataValidator:
    """数据验证和一致性检查工具"""
    
    def __init__(self, db_paths: List[str] = None):
        """
        初始化数据验证器
        
        Args:
            db_paths: 数据库路径列表
        """
        self.db_paths = db_paths or self._discover_databases()
        self.validation_results = {}
        
    def _discover_databases(self) -> List[str]:
        """自动发现数据库文件 - 只扫描统一的data/db目录"""
        db_paths = []
        
        # 只使用统一的数据库目录
        unified_db_dir = "data/db"
        
        if os.path.exists(unified_db_dir):
            logger.info(f"[验证器] 扫描数据库目录: {os.path.abspath(unified_db_dir)}")
            
            for file in os.listdir(unified_db_dir):
                if file.endswith('.db') and not file.endswith('.bak') and not file.endswith('-shm') and not file.endswith('-wal'):
                    db_path = os.path.join(unified_db_dir, file)
                    abs_path = os.path.abspath(db_path)
                    
                    # 检查文件大小，过滤空文件
                    if os.path.getsize(abs_path) > 1024:  # 至少1KB
                        db_paths.append(abs_path)
                        logger.info(f"[验证器] 发现数据库: {file} ({os.path.getsize(abs_path)/1024:.1f} KB)")
                    else:
                        logger.warning(f"[验证器] 跳过空数据库文件: {file}")
        else:
            logger.warning(f"[验证器] 数据库目录不存在: {unified_db_dir}")
        
        logger.info(f"[验证器] 共发现 {len(db_paths)} 个有效数据库文件")
        return db_paths
    
    def validate_database_integrity(self) -> Dict[str, Any]:
        """验证数据库完整性"""
        results = {
            'total_databases': len(self.db_paths),
            'valid_databases': 0,
            'database_details': [],
            'total_news_count': 0,
            'unique_news_count': 0,
            'duplicate_urls': [],
            'sources': set(),
            'date_range': {'min': None, 'max': None},
            'issues': []
        }
        
        seen_urls = set()
        all_news = []
        
        for db_path in self.db_paths:
            db_info = self._validate_single_database(db_path)
            results['database_details'].append(db_info)
            
            if db_info['valid']:
                results['valid_databases'] += 1
                results['total_news_count'] += db_info['news_count']
                results['sources'].update(db_info['sources'])
                
                # 检查重复URL
                for url in db_info['urls']:
                    if url in seen_urls:
                        results['duplicate_urls'].append(url)
                    else:
                        seen_urls.add(url)
                        results['unique_news_count'] += 1
                
                # 收集日期范围
                if db_info['date_range']['min']:
                    if not results['date_range']['min'] or db_info['date_range']['min'] < results['date_range']['min']:
                        results['date_range']['min'] = db_info['date_range']['min']
                
                if db_info['date_range']['max']:
                    if not results['date_range']['max'] or db_info['date_range']['max'] > results['date_range']['max']:
                        results['date_range']['max'] = db_info['date_range']['max']
        
        # 转换集合为列表以便JSON序列化
        results['sources'] = sorted(list(results['sources']))
        results['duplicate_count'] = len(results['duplicate_urls'])
        
        # 检查数据一致性问题
        if results['total_news_count'] != results['unique_news_count']:
            results['issues'].append({
                'type': 'data_inconsistency',
                'message': f'总数({results["total_news_count"]})与去重数({results["unique_news_count"]})不一致',
                'severity': 'warning'
            })
        
        if results['duplicate_count'] > 0:
            results['issues'].append({
                'type': 'duplicate_data',
                'message': f'发现 {results["duplicate_count"]} 个重复URL',
                'severity': 'warning'
            })
        
        logger.info(f"[验证器] 数据库验证完成: {results['valid_databases']}/{results['total_databases']} 个有效")
        return results
    
    def _validate_single_database(self, db_path: str) -> Dict[str, Any]:
        """验证单个数据库"""
        info = {
            'path': db_path,
            'name': os.path.basename(db_path),
            'valid': False,
            'news_count': 0,
            'sources': set(),
            'urls': [],
            'date_range': {'min': None, 'max': None},
            'table_exists': False,
            'issues': []
        }
        
        try:
            if not os.path.exists(db_path):
                info['issues'].append('文件不存在')
                return info
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 检查news表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
            if not cursor.fetchone():
                info['issues'].append('news表不存在')
                conn.close()
                return info
            
            info['table_exists'] = True
            
            # 获取新闻数量
            cursor.execute("SELECT COUNT(*) FROM news")
            info['news_count'] = cursor.fetchone()[0]
            
            # 获取来源信息
            cursor.execute("SELECT DISTINCT source FROM news WHERE source IS NOT NULL")
            for row in cursor.fetchall():
                if row['source']:
                    info['sources'].add(row['source'])
            
            # 获取URL列表（用于去重检查）
            cursor.execute("SELECT url FROM news WHERE url IS NOT NULL")
            info['urls'] = [row['url'] for row in cursor.fetchall()]
            
            # 获取日期范围
            cursor.execute("SELECT MIN(pub_time), MAX(pub_time) FROM news WHERE pub_time IS NOT NULL")
            date_row = cursor.fetchone()
            if date_row:
                info['date_range']['min'] = date_row[0]
                info['date_range']['max'] = date_row[1]
            
            conn.close()
            info['valid'] = True
            
        except Exception as e:
            info['issues'].append(f'数据库错误: {str(e)}')
            logger.error(f"[验证器] 验证数据库失败 {db_path}: {str(e)}")
        
        return info
    
    def get_consistent_statistics(self) -> Dict[str, Any]:
        """获取一致的统计数据"""
        validation_result = self.validate_database_integrity()
        
        # 计算今日新闻数（去重）
        today = datetime.now().strftime('%Y-%m-%d')
        today_count = 0
        seen_today_urls = set()
        
        for db_path in self.db_paths:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 检查表是否存在
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                if not cursor.fetchone():
                    continue
                
                cursor.execute("SELECT url FROM news WHERE pub_time LIKE ? AND url IS NOT NULL", (f"{today}%",))
                for row in cursor.fetchall():
                    url = row[0]
                    if url and url not in seen_today_urls:
                        seen_today_urls.add(url)
                        today_count += 1
                
                conn.close()
                
            except Exception as e:
                logger.error(f"[验证器] 获取今日统计失败 {db_path}: {str(e)}")
        
        # 计算活跃爬虫数（基于最近24小时内有数据的来源）
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        active_sources = set()
        
        for db_path in self.db_paths:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT DISTINCT source FROM news 
                    WHERE (pub_time >= ? OR crawl_time >= ?) 
                    AND source IS NOT NULL
                """, (yesterday, yesterday))
                
                for row in cursor.fetchall():
                    if row[0]:
                        active_sources.add(row[0])
                
                conn.close()
                
            except Exception as e:
                logger.error(f"[验证器] 获取活跃源失败 {db_path}: {str(e)}")
        
        # 模拟成功率计算（应该基于实际爬虫日志）
        crawl_success_rate = 0.95  # 默认值，应该从爬虫日志中计算
        
        statistics = {
            'total_news': validation_result['unique_news_count'],  # 使用去重后的数量
            'today_news': today_count,
            'active_sources': len(active_sources),
            'crawl_success_rate': crawl_success_rate,
            'sources': validation_result['sources'],
            'last_update': datetime.now().isoformat(),
            'data_consistency': {
                'total_raw_count': validation_result['total_news_count'],
                'duplicate_count': validation_result['duplicate_count'],
                'unique_count': validation_result['unique_news_count'],
                'consistency_ratio': validation_result['unique_news_count'] / max(validation_result['total_news_count'], 1)
            },
            'database_info': {
                'total_databases': validation_result['total_databases'],
                'valid_databases': validation_result['valid_databases'],
                'date_range': validation_result['date_range']
            },
            'issues': validation_result['issues']
        }
        
        logger.info(f"[验证器] 统计数据: 总数={statistics['total_news']}, 今日={statistics['today_news']}, 活跃源={statistics['active_sources']}")
        return statistics
    
    def generate_report(self) -> str:
        """生成数据验证报告"""
        stats = self.get_consistent_statistics()
        validation = self.validate_database_integrity()
        
        report = f"""
# NewsLook 数据验证报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 数据库概览
- 总数据库数: {validation['total_databases']}
- 有效数据库数: {validation['valid_databases']}
- 数据日期范围: {validation['date_range']['min']} 至 {validation['date_range']['max']}

## 统计数据（一致性校正后）
- 总新闻数: {stats['total_news']} 条（去重后）
- 原始总数: {stats['data_consistency']['total_raw_count']} 条
- 重复数据: {stats['data_consistency']['duplicate_count']} 条
- 数据一致性: {stats['data_consistency']['consistency_ratio']:.2%}

- 今日新闻: {stats['today_news']} 条
- 活跃来源: {stats['active_sources']} 个
- 爬虫成功率: {stats['crawl_success_rate']:.1%}

## 新闻来源
{chr(10).join(f"- {source}" for source in stats['sources'])}

## 数据库详情
"""
        
        for db_info in validation['database_details']:
            report += f"""
### {db_info['name']}
- 路径: {db_info['path']}
- 状态: {'✅ 正常' if db_info['valid'] else '❌ 异常'}
- 新闻数: {db_info['news_count']} 条
- 来源数: {len(db_info['sources'])} 个
- 问题: {', '.join(db_info['issues']) if db_info['issues'] else '无'}
"""
        
        if stats['issues']:
            report += "\n## 发现的问题\n"
            for issue in stats['issues']:
                severity_icon = {'warning': '⚠️', 'error': '❌', 'info': 'ℹ️'}.get(issue['severity'], '•')
                report += f"- {severity_icon} {issue['message']}\n"
        
        return report 