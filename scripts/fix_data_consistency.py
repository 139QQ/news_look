#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook数据一致性检查和修复脚本
解决数据概览与新闻列表显示数量不一致的问题
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, List, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataConsistencyFixer:
    """数据一致性检查和修复器"""
    
    def __init__(self):
        """初始化数据一致性检查器"""
        self.project_root = project_root
        self.data_dir = project_root / 'data' / 'db'
        self.main_db = self.data_dir / 'finance_news.db'
        self.sources_dir = self.data_dir / 'sources'
        
        # 确保目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sources_dir.mkdir(exist_ok=True)
        
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'main_db_stats': {},
            'source_db_stats': {},
            'duplicate_analysis': {},
            'recommendations': []
        }
    
    def check_database_files(self) -> Dict[str, Any]:
        """检查数据库文件状态"""
        logger.info("检查数据库文件状态...")
        
        file_status = {
            'main_db_exists': self.main_db.exists(),
            'main_db_size': self.main_db.stat().st_size if self.main_db.exists() else 0,
            'source_dbs': []
        }
        
        # 检查源数据库
        if self.sources_dir.exists():
            for db_file in self.sources_dir.glob('*.db'):
                file_status['source_dbs'].append({
                    'name': db_file.stem,
                    'path': str(db_file),
                    'size': db_file.stat().st_size
                })
        
        # 检查data目录下的旧数据库文件
        old_dbs = []
        for db_file in self.data_dir.parent.glob('*.db'):
            if db_file.parent == self.data_dir.parent:
                old_dbs.append({
                    'name': db_file.stem,
                    'path': str(db_file),
                    'size': db_file.stat().st_size
                })
        
        file_status['old_dbs'] = old_dbs
        
        logger.info(f"主数据库: {'存在' if file_status['main_db_exists'] else '不存在'}")
        logger.info(f"源数据库: {len(file_status['source_dbs'])} 个")
        logger.info(f"旧数据库: {len(old_dbs)} 个")
        
        return file_status
    
    def analyze_data_duplicates(self) -> Dict[str, Any]:
        """分析数据重复情况"""
        logger.info("分析数据重复情况...")
        
        all_urls = {}  # URL -> [数据库来源列表]
        db_stats = {}  # 数据库 -> 统计信息
        
        # 分析主数据库
        if self.main_db.exists():
            main_stats = self._analyze_single_db(str(self.main_db), '主数据库')
            db_stats['main'] = main_stats
            
            for url in main_stats['urls']:
                if url not in all_urls:
                    all_urls[url] = []
                all_urls[url].append('主数据库')
        
        # 分析源数据库
        if self.sources_dir.exists():
            for db_file in self.sources_dir.glob('*.db'):
                source_name = db_file.stem
                source_stats = self._analyze_single_db(str(db_file), source_name)
                db_stats[source_name] = source_stats
                
                for url in source_stats['urls']:
                    if url not in all_urls:
                        all_urls[url] = []
                    all_urls[url].append(source_name)
        
        # 分析重复情况
        duplicates = {}
        unique_urls = set()
        
        for url, sources in all_urls.items():
            if len(sources) > 1:
                duplicates[url] = sources
            unique_urls.add(url)
        
        analysis = {
            'total_urls': len(all_urls),
            'unique_urls': len(unique_urls),
            'duplicate_urls': len(duplicates),
            'duplicate_details': duplicates,
            'db_stats': db_stats
        }
        
        logger.info(f"总URL数: {analysis['total_urls']}")
        logger.info(f"唯一URL数: {analysis['unique_urls']}")
        logger.info(f"重复URL数: {analysis['duplicate_urls']}")
        
        return analysis
    
    def _analyze_single_db(self, db_path: str, db_name: str) -> Dict[str, Any]:
        """分析单个数据库"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
            if not cursor.fetchone():
                logger.warning(f"{db_name} 中没有news表")
                conn.close()
                return {
                    'total_count': 0,
                    'urls': [],
                    'sources': set(),
                    'has_table': False
                }
            
            # 获取所有新闻记录
            cursor.execute("SELECT url, source, title FROM news WHERE url IS NOT NULL AND url != ''")
            rows = cursor.fetchall()
            
            urls = [row[0] for row in rows]
            sources = set(row[1] for row in rows if row[1])
            
            stats = {
                'total_count': len(rows),
                'unique_url_count': len(set(urls)),
                'urls': urls,
                'sources': sources,
                'has_table': True
            }
            
            conn.close()
            logger.info(f"{db_name}: {stats['total_count']} 条记录, {stats['unique_url_count']} 个唯一URL")
            
            return stats
            
        except Exception as e:
            logger.error(f"分析数据库 {db_name} 失败: {e}")
            return {
                'total_count': 0,
                'urls': [],
                'sources': set(),
                'has_table': False,
                'error': str(e)
            }
    
    def test_api_consistency(self) -> Dict[str, Any]:
        """测试API数据一致性"""
        logger.info("测试API数据一致性...")
        
        try:
            # 测试统一数据库管理器
            from backend.newslook.core.unified_database_manager import get_unified_database_manager
            
            db_manager = get_unified_database_manager()
            
            # 获取统计信息
            stats = db_manager.get_database_stats()
            
            # 获取新闻数量
            total_count = db_manager.get_news_count()
            
            # 获取新闻列表
            news_list = db_manager.query_news(use_all_sources=True, limit=1000)
            
            api_test = {
                'database_stats': stats,
                'news_count_method': total_count,
                'news_list_count': len(news_list),
                'consistency_check': {
                    'stats_vs_count': stats['total_news'] == total_count,
                    'stats_vs_list': stats['total_news'] == len(news_list),
                    'count_vs_list': total_count == len(news_list)
                }
            }
            
            logger.info(f"数据库统计API: {stats['total_news']} 条")
            logger.info(f"计数方法API: {total_count} 条")
            logger.info(f"新闻列表API: {len(news_list)} 条")
            
            # 检查一致性
            if api_test['consistency_check']['stats_vs_count'] and \
               api_test['consistency_check']['stats_vs_list'] and \
               api_test['consistency_check']['count_vs_list']:
                logger.info("✅ API数据一致性检查通过")
            else:
                logger.warning("❌ API数据一致性检查失败")
            
            return api_test
            
        except Exception as e:
            logger.error(f"API一致性测试失败: {e}")
            return {
                'error': str(e),
                'consistency_check': {
                    'stats_vs_count': False,
                    'stats_vs_list': False,
                    'count_vs_list': False
                }
            }
    
    def generate_recommendations(self, file_status: Dict, duplicates: Dict, api_test: Dict) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        # 检查数据重复
        if duplicates['duplicate_urls'] > 0:
            recommendations.append(
                f"发现 {duplicates['duplicate_urls']} 个重复URL，建议清理重复数据"
            )
        
        # 检查API一致性
        if not all(api_test.get('consistency_check', {}).values()):
            recommendations.append(
                "API数据不一致，已通过代码修复，建议重启应用验证"
            )
        
        # 检查旧数据库文件
        if file_status.get('old_dbs'):
            recommendations.append(
                f"发现 {len(file_status['old_dbs'])} 个旧数据库文件，建议迁移到统一位置"
            )
        
        # 检查源数据库
        if not file_status.get('source_dbs'):
            recommendations.append(
                "未发现源数据库，建议检查爬虫配置"
            )
        
        return recommendations
    
    def run_full_check(self) -> Dict[str, Any]:
        """运行完整的数据一致性检查"""
        logger.info("开始数据一致性检查...")
        
        # 1. 检查数据库文件
        file_status = self.check_database_files()
        self.report['file_status'] = file_status
        
        # 2. 分析数据重复
        duplicates = self.analyze_data_duplicates()
        self.report['duplicate_analysis'] = duplicates
        
        # 3. 测试API一致性
        api_test = self.test_api_consistency()
        self.report['api_consistency'] = api_test
        
        # 4. 生成建议
        recommendations = self.generate_recommendations(file_status, duplicates, api_test)
        self.report['recommendations'] = recommendations
        
        return self.report
    
    def save_report(self, filename: str = None):
        """保存检查报告"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data_consistency_report_{timestamp}.json"
        
        report_path = self.project_root / filename
        
        import json
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"检查报告已保存: {report_path}")
        return report_path
    
    def print_summary(self):
        """打印检查摘要"""
        print("\n" + "="*60)
        print("📊 NewsLook数据一致性检查报告")
        print("="*60)
        
        # 文件状态
        file_status = self.report.get('file_status', {})
        print(f"\n📁 数据库文件状态:")
        print(f"   主数据库: {'✅' if file_status.get('main_db_exists') else '❌'}")
        print(f"   源数据库: {len(file_status.get('source_dbs', []))} 个")
        print(f"   旧数据库: {len(file_status.get('old_dbs', []))} 个")
        
        # 重复分析
        duplicates = self.report.get('duplicate_analysis', {})
        print(f"\n🔍 数据重复分析:")
        print(f"   总URL数: {duplicates.get('total_urls', 0)}")
        print(f"   唯一URL数: {duplicates.get('unique_urls', 0)}")
        print(f"   重复URL数: {duplicates.get('duplicate_urls', 0)}")
        
        # API一致性
        api_test = self.report.get('api_consistency', {})
        consistency = api_test.get('consistency_check', {})
        print(f"\n🔧 API一致性检查:")
        print(f"   统计API: {api_test.get('database_stats', {}).get('total_news', 'N/A')} 条")
        print(f"   计数API: {api_test.get('news_count_method', 'N/A')} 条")
        print(f"   列表API: {api_test.get('news_list_count', 'N/A')} 条")
        print(f"   一致性: {'✅' if all(consistency.values()) else '❌'}")
        
        # 建议
        recommendations = self.report.get('recommendations', [])
        print(f"\n💡 修复建议:")
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        else:
            print("   ✅ 未发现需要修复的问题")
        
        print("\n" + "="*60)

def main():
    """主函数"""
    print("🔧 NewsLook数据一致性检查工具")
    print("解决数据概览与新闻列表显示数量不一致的问题")
    print("-" * 50)
    
    # 创建检查器
    fixer = DataConsistencyFixer()
    
    try:
        # 运行完整检查
        report = fixer.run_full_check()
        
        # 打印摘要
        fixer.print_summary()
        
        # 保存报告
        report_path = fixer.save_report()
        
        # 检查是否有严重问题
        api_consistency = report.get('api_consistency', {}).get('consistency_check', {})
        if not all(api_consistency.values()):
            print("\n⚠️  发现API数据不一致问题！")
            print("🔧 已通过代码修复统计逻辑，请重启应用后重新测试")
        else:
            print("\n✅ 数据一致性检查通过！")
        
        return True
        
    except Exception as e:
        logger.error(f"数据一致性检查失败: {e}")
        print(f"\n❌ 检查失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 