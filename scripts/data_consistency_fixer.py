#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据一致性修复类
解决重复数据、数据不一致、API数据不匹配等问题
"""

import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import hashlib
import json
import difflib

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataConsistencyFixer:
    """数据一致性修复器"""
    
    def __init__(self, project_root: str = None):
        """初始化数据一致性修复器"""
        if project_root is None:
            project_root = Path(__file__).parent.parent
        
        self.project_root = Path(project_root)
        self.db_dir = self.project_root / 'data' / 'db'
        self.main_db = self.db_dir / 'finance_news.db'
        
        # 修复报告
        self.report = {
            'start_time': datetime.now().isoformat(),
            'duplicate_analysis': {},
            'consistency_fixes': [],
            'errors': []
        }
    
    def analyze_data_duplicates(self) -> Dict[str, any]:
        """分析重复数据"""
        logger.info("开始分析重复数据...")
        
        duplicate_analysis = {
            'url_duplicates': [],
            'title_duplicates': [],
            'content_duplicates': [],
            'exact_duplicates': [],
            'near_duplicates': [],
            'statistics': {}
        }
        
        try:
            with sqlite3.connect(str(self.main_db)) as conn:
                cursor = conn.cursor()
                
                # 1. 分析URL重复
                cursor.execute("""
                    SELECT url, COUNT(*) as count, GROUP_CONCAT(id) as ids
                    FROM news 
                    GROUP BY url 
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                """)
                
                url_duplicates = cursor.fetchall()
                duplicate_analysis['url_duplicates'] = [
                    {
                        'url': url,
                        'count': count,
                        'ids': ids.split(',')
                    }
                    for url, count, ids in url_duplicates
                ]
                
                # 2. 分析标题重复
                cursor.execute("""
                    SELECT title, COUNT(*) as count, GROUP_CONCAT(id) as ids
                    FROM news 
                    GROUP BY title 
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                    LIMIT 100
                """)
                
                title_duplicates = cursor.fetchall()
                duplicate_analysis['title_duplicates'] = [
                    {
                        'title': title,
                        'count': count,
                        'ids': ids.split(',')
                    }
                    for title, count, ids in title_duplicates
                ]
                
                # 3. 分析内容重复（基于内容hash）
                cursor.execute("""
                    SELECT content, COUNT(*) as count, GROUP_CONCAT(id) as ids
                    FROM news 
                    WHERE content IS NOT NULL AND content != ''
                    GROUP BY content 
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                    LIMIT 50
                """)
                
                content_duplicates = cursor.fetchall()
                duplicate_analysis['content_duplicates'] = [
                    {
                        'content_hash': hashlib.md5(content.encode()).hexdigest()[:16],
                        'count': count,
                        'ids': ids.split(',')
                    }
                    for content, count, ids in content_duplicates
                ]
                
                # 4. 统计信息
                cursor.execute("SELECT COUNT(*) FROM news")
                total_news = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT url) FROM news")
                unique_urls = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT title) FROM news")
                unique_titles = cursor.fetchone()[0]
                
                duplicate_analysis['statistics'] = {
                    'total_news': total_news,
                    'unique_urls': unique_urls,
                    'unique_titles': unique_titles,
                    'url_duplicate_groups': len(duplicate_analysis['url_duplicates']),
                    'title_duplicate_groups': len(duplicate_analysis['title_duplicates']),
                    'content_duplicate_groups': len(duplicate_analysis['content_duplicates'])
                }
                
                logger.info(f"重复数据分析完成: {duplicate_analysis['statistics']}")
                
        except Exception as e:
            logger.error(f"分析重复数据时出错: {e}")
            self.report['errors'].append(str(e))
        
        self.report['duplicate_analysis'] = duplicate_analysis
        return duplicate_analysis
    
    def find_near_duplicates(self, similarity_threshold: float = 0.85) -> List[Dict]:
        """查找近似重复的新闻"""
        logger.info("开始查找近似重复新闻...")
        
        near_duplicates = []
        
        try:
            with sqlite3.connect(str(self.main_db)) as conn:
                cursor = conn.cursor()
                
                # 获取所有新闻的标题和内容
                cursor.execute("""
                    SELECT id, title, content, url, pub_time
                    FROM news 
                    WHERE title IS NOT NULL AND content IS NOT NULL
                    ORDER BY pub_time DESC
                    LIMIT 1000
                """)
                
                news_items = cursor.fetchall()
                
                # 比较新闻相似度
                for i, news1 in enumerate(news_items):
                    for j, news2 in enumerate(news_items[i+1:], i+1):
                        
                        # 计算标题相似度
                        title_similarity = difflib.SequenceMatcher(
                            None, news1[1], news2[1]
                        ).ratio()
                        
                        # 计算内容相似度
                        content_similarity = difflib.SequenceMatcher(
                            None, news1[2][:500], news2[2][:500]
                        ).ratio()
                        
                        # 综合相似度
                        overall_similarity = (title_similarity * 0.6 + content_similarity * 0.4)
                        
                        if overall_similarity >= similarity_threshold:
                            near_duplicates.append({
                                'id1': news1[0],
                                'id2': news2[0],
                                'title1': news1[1],
                                'title2': news2[1],
                                'url1': news1[3],
                                'url2': news2[3],
                                'pub_time1': news1[4],
                                'pub_time2': news2[4],
                                'title_similarity': title_similarity,
                                'content_similarity': content_similarity,
                                'overall_similarity': overall_similarity
                            })
                
                logger.info(f"发现 {len(near_duplicates)} 对近似重复新闻")
                
        except Exception as e:
            logger.error(f"查找近似重复时出错: {e}")
            self.report['errors'].append(str(e))
        
        return near_duplicates
    
    def remove_exact_duplicates(self) -> int:
        """移除完全重复的新闻"""
        logger.info("开始移除完全重复的新闻...")
        
        removed_count = 0
        
        try:
            with sqlite3.connect(str(self.main_db)) as conn:
                cursor = conn.cursor()
                
                # 查找完全重复的新闻（基于URL）
                cursor.execute("""
                    SELECT url, MIN(id) as keep_id, GROUP_CONCAT(id) as all_ids
                    FROM news 
                    GROUP BY url 
                    HAVING COUNT(*) > 1
                """)
                
                duplicates = cursor.fetchall()
                
                for url, keep_id, all_ids in duplicates:
                    ids_to_remove = [id for id in all_ids.split(',') if id != keep_id]
                    
                    if ids_to_remove:
                        # 删除重复记录
                        cursor.execute(f"""
                            DELETE FROM news 
                            WHERE id IN ({','.join(['?' for _ in ids_to_remove])})
                        """, ids_to_remove)
                        
                        removed_count += len(ids_to_remove)
                        logger.info(f"移除URL重复: {url} (保留 {keep_id}, 移除 {len(ids_to_remove)} 个)")
                
                conn.commit()
                logger.info(f"移除完全重复新闻完成，共移除 {removed_count} 条")
                
        except Exception as e:
            logger.error(f"移除重复新闻时出错: {e}")
            self.report['errors'].append(str(e))
        
        return removed_count
    
    def fix_data_inconsistencies(self) -> Dict[str, int]:
        """修复数据不一致问题"""
        logger.info("开始修复数据不一致问题...")
        
        fix_counts = {
            'empty_titles': 0,
            'empty_contents': 0,
            'invalid_dates': 0,
            'invalid_urls': 0,
            'missing_sources': 0,
            'encoding_fixes': 0
        }
        
        try:
            with sqlite3.connect(str(self.main_db)) as conn:
                cursor = conn.cursor()
                
                # 1. 修复空标题
                cursor.execute("""
                    UPDATE news 
                    SET title = '无标题' 
                    WHERE title IS NULL OR title = ''
                """)
                fix_counts['empty_titles'] = cursor.rowcount
                
                # 2. 修复空内容
                cursor.execute("""
                    UPDATE news 
                    SET content = '无内容' 
                    WHERE content IS NULL OR content = ''
                """)
                fix_counts['empty_contents'] = cursor.rowcount
                
                # 3. 修复无效日期
                cursor.execute("""
                    UPDATE news 
                    SET pub_time = datetime('now') 
                    WHERE pub_time IS NULL OR pub_time = ''
                """)
                fix_counts['invalid_dates'] = cursor.rowcount
                
                # 4. 修复无效URL
                cursor.execute("""
                    UPDATE news 
                    SET url = 'http://unknown.com/news/' || id 
                    WHERE url IS NULL OR url = ''
                """)
                fix_counts['invalid_urls'] = cursor.rowcount
                
                # 5. 修复缺失来源
                cursor.execute("""
                    UPDATE news 
                    SET source = '未知来源' 
                    WHERE source IS NULL OR source = ''
                """)
                fix_counts['missing_sources'] = cursor.rowcount
                
                # 6. 修复编码问题
                cursor.execute("""
                    SELECT id, title, content FROM news 
                    WHERE title LIKE '%�%' OR content LIKE '%�%'
                """)
                
                encoding_issues = cursor.fetchall()
                for news_id, title, content in encoding_issues:
                    # 尝试修复编码问题
                    fixed_title = title.replace('�', '')
                    fixed_content = content.replace('�', '')
                    
                    cursor.execute("""
                        UPDATE news 
                        SET title = ?, content = ?
                        WHERE id = ?
                    """, (fixed_title, fixed_content, news_id))
                
                fix_counts['encoding_fixes'] = len(encoding_issues)
                
                conn.commit()
                logger.info(f"数据不一致修复完成: {fix_counts}")
                
        except Exception as e:
            logger.error(f"修复数据不一致时出错: {e}")
            self.report['errors'].append(str(e))
        
        return fix_counts
    
    def standardize_data_formats(self) -> Dict[str, int]:
        """标准化数据格式"""
        logger.info("开始标准化数据格式...")
        
        standardize_counts = {
            'date_formats': 0,
            'source_names': 0,
            'categories': 0,
            'urls': 0
        }
        
        try:
            with sqlite3.connect(str(self.main_db)) as conn:
                cursor = conn.cursor()
                
                # 1. 标准化来源名称
                source_mapping = {
                    '东方财富网': '东方财富',
                    '新浪财经网': '新浪财经',
                    '网易财经网': '网易财经',
                    '凤凰财经网': '凤凰财经',
                    '腾讯财经网': '腾讯财经'
                }
                
                for old_name, new_name in source_mapping.items():
                    cursor.execute("""
                        UPDATE news 
                        SET source = ? 
                        WHERE source = ?
                    """, (new_name, old_name))
                    standardize_counts['source_names'] += cursor.rowcount
                
                # 2. 标准化分类
                cursor.execute("""
                    UPDATE news 
                    SET category = '财经' 
                    WHERE category IS NULL OR category = '' OR category = '其他'
                """)
                standardize_counts['categories'] = cursor.rowcount
                
                # 3. 标准化URL格式
                cursor.execute("""
                    UPDATE news 
                    SET url = LOWER(url) 
                    WHERE url != LOWER(url)
                """)
                standardize_counts['urls'] = cursor.rowcount
                
                conn.commit()
                logger.info(f"数据格式标准化完成: {standardize_counts}")
                
        except Exception as e:
            logger.error(f"标准化数据格式时出错: {e}")
            self.report['errors'].append(str(e))
        
        return standardize_counts
    
    def optimize_database_structure(self) -> Dict[str, any]:
        """优化数据库结构"""
        logger.info("开始优化数据库结构...")
        
        optimization_results = {
            'indexes_created': [],
            'tables_analyzed': [],
            'vacuum_completed': False,
            'pragma_settings': {}
        }
        
        try:
            with sqlite3.connect(str(self.main_db)) as conn:
                cursor = conn.cursor()
                
                # 1. 创建优化索引
                indexes = [
                    ("idx_news_url", "CREATE INDEX IF NOT EXISTS idx_news_url ON news(url)"),
                    ("idx_news_source", "CREATE INDEX IF NOT EXISTS idx_news_source ON news(source)"),
                    ("idx_news_pub_time", "CREATE INDEX IF NOT EXISTS idx_news_pub_time ON news(pub_time)"),
                    ("idx_news_title", "CREATE INDEX IF NOT EXISTS idx_news_title ON news(title)"),
                    ("idx_news_category", "CREATE INDEX IF NOT EXISTS idx_news_category ON news(category)"),
                    ("idx_news_source_time", "CREATE INDEX IF NOT EXISTS idx_news_source_time ON news(source, pub_time)"),
                ]
                
                for index_name, sql in indexes:
                    cursor.execute(sql)
                    optimization_results['indexes_created'].append(index_name)
                
                # 2. 分析表
                cursor.execute("ANALYZE news")
                optimization_results['tables_analyzed'].append('news')
                
                # 3. 清理数据库
                cursor.execute("VACUUM")
                optimization_results['vacuum_completed'] = True
                
                # 4. 设置优化参数
                pragma_settings = {
                    'journal_mode': 'WAL',
                    'synchronous': 'NORMAL',
                    'cache_size': 10000,
                    'temp_store': 'MEMORY',
                    'mmap_size': 268435456  # 256MB
                }
                
                for pragma, value in pragma_settings.items():
                    cursor.execute(f"PRAGMA {pragma} = {value}")
                    optimization_results['pragma_settings'][pragma] = value
                
                conn.commit()
                logger.info(f"数据库结构优化完成: {optimization_results}")
                
        except Exception as e:
            logger.error(f"优化数据库结构时出错: {e}")
            self.report['errors'].append(str(e))
        
        return optimization_results
    
    def verify_data_integrity(self) -> Dict[str, any]:
        """验证数据完整性"""
        logger.info("开始验证数据完整性...")
        
        integrity_check = {
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'missing_fields': {},
            'data_quality_score': 0.0
        }
        
        try:
            with sqlite3.connect(str(self.main_db)) as conn:
                cursor = conn.cursor()
                
                # 1. 总记录数
                cursor.execute("SELECT COUNT(*) FROM news")
                integrity_check['total_records'] = cursor.fetchone()[0]
                
                # 2. 验证必需字段
                required_fields = ['title', 'content', 'url', 'source', 'pub_time']
                missing_counts = {}
                
                for field in required_fields:
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM news 
                        WHERE {field} IS NULL OR {field} = ''
                    """)
                    missing_counts[field] = cursor.fetchone()[0]
                
                integrity_check['missing_fields'] = missing_counts
                
                # 3. 有效记录数
                cursor.execute("""
                    SELECT COUNT(*) FROM news 
                    WHERE title IS NOT NULL AND title != ''
                    AND content IS NOT NULL AND content != ''
                    AND url IS NOT NULL AND url != ''
                    AND source IS NOT NULL AND source != ''
                    AND pub_time IS NOT NULL AND pub_time != ''
                """)
                integrity_check['valid_records'] = cursor.fetchone()[0]
                
                integrity_check['invalid_records'] = (
                    integrity_check['total_records'] - integrity_check['valid_records']
                )
                
                # 4. 计算数据质量分数
                if integrity_check['total_records'] > 0:
                    integrity_check['data_quality_score'] = (
                        integrity_check['valid_records'] / integrity_check['total_records']
                    )
                
                logger.info(f"数据完整性验证完成: {integrity_check}")
                
        except Exception as e:
            logger.error(f"验证数据完整性时出错: {e}")
            self.report['errors'].append(str(e))
        
        return integrity_check
    
    def generate_consistency_report(self) -> Path:
        """生成数据一致性报告"""
        self.report['end_time'] = datetime.now().isoformat()
        
        report_file = self.project_root / f"data_consistency_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"生成数据一致性报告: {report_file}")
        return report_file
    
    def run_full_consistency_check(self) -> Path:
        """运行完整的数据一致性检查和修复"""
        logger.info("开始完整数据一致性检查和修复...")
        
        try:
            # 1. 分析重复数据
            self.analyze_data_duplicates()
            
            # 2. 查找近似重复
            near_duplicates = self.find_near_duplicates()
            self.report['near_duplicates'] = near_duplicates
            
            # 3. 移除完全重复
            removed_count = self.remove_exact_duplicates()
            self.report['consistency_fixes'].append({
                'action': 'remove_exact_duplicates',
                'count': removed_count
            })
            
            # 4. 修复数据不一致
            fix_counts = self.fix_data_inconsistencies()
            self.report['consistency_fixes'].append({
                'action': 'fix_data_inconsistencies',
                'counts': fix_counts
            })
            
            # 5. 标准化数据格式
            standardize_counts = self.standardize_data_formats()
            self.report['consistency_fixes'].append({
                'action': 'standardize_data_formats',
                'counts': standardize_counts
            })
            
            # 6. 优化数据库结构
            optimization_results = self.optimize_database_structure()
            self.report['consistency_fixes'].append({
                'action': 'optimize_database_structure',
                'results': optimization_results
            })
            
            # 7. 验证数据完整性
            integrity_check = self.verify_data_integrity()
            self.report['integrity_check'] = integrity_check
            
            # 8. 生成报告
            report_file = self.generate_consistency_report()
            
            logger.info("数据一致性检查和修复完成!")
            return report_file
            
        except Exception as e:
            logger.error(f"数据一致性检查过程中出错: {e}")
            self.report['errors'].append(str(e))
            return self.generate_consistency_report()

def main():
    """主函数"""
    fixer = DataConsistencyFixer()
    report_file = fixer.run_full_consistency_check()
    
    print(f"\n数据一致性检查完成! 报告文件: {report_file}")
    print(f"主数据库: {fixer.main_db}")

if __name__ == "__main__":
    main() 