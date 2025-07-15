#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库架构修复脚本
解决数据库冗余、路径分散、备份混乱等问题
"""

import os
import shutil
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional
import hashlib
import json

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_fix.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseArchitectureFixer:
    """数据库架构修复器"""
    
    def __init__(self, project_root: str = None):
        """初始化修复器"""
        if project_root is None:
            project_root = Path(__file__).parent.parent
        
        self.project_root = Path(project_root)
        
        # 定义统一的目录结构
        self.unified_db_dir = self.project_root / 'data' / 'db'
        self.backup_dir = self.unified_db_dir / 'backups'
        self.archive_dir = self.unified_db_dir / 'archives'
        self.temp_dir = self.unified_db_dir / 'temp'
        
        # 创建目录结构
        self._create_directories()
        
        # 数据源标准化映射
        self.source_mapping = {
            'eastmoney': 'eastmoney_finance.db',
            'sina': 'sina_finance.db',
            'netease': 'netease_finance.db',
            'ifeng': 'ifeng_finance.db',
            'tencent': 'tencent_finance.db',
            '东方财富': 'eastmoney_finance.db',
            '新浪财经': 'sina_finance.db',
            '网易财经': 'netease_finance.db',
            '凤凰财经': 'ifeng_finance.db',
            '腾讯财经': 'tencent_finance.db',
        }
        
        # 主数据库
        self.main_db = self.unified_db_dir / 'finance_news.db'
        
        # 修复报告
        self.report = {
            'start_time': datetime.now().isoformat(),
            'actions': [],
            'errors': [],
            'summary': {}
        }
    
    def _create_directories(self):
        """创建统一目录结构"""
        directories = [
            self.unified_db_dir,
            self.backup_dir,
            self.archive_dir,
            self.temp_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建目录: {directory}")
    
    def scan_database_files(self) -> Dict[str, List[Path]]:
        """扫描所有数据库文件"""
        logger.info("开始扫描数据库文件...")
        
        # 搜索路径
        search_paths = [
            self.project_root / 'data',
            self.project_root / 'backup',
            self.project_root / 'db',
            self.project_root
        ]
        
        db_files = {}
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for db_file in search_path.rglob('*.db'):
                # 跳过已经在目标目录的文件
                if str(db_file.parent) == str(self.unified_db_dir):
                    continue
                    
                file_type = self._classify_db_file(db_file)
                if file_type not in db_files:
                    db_files[file_type] = []
                db_files[file_type].append(db_file)
        
        logger.info(f"扫描完成，发现数据库文件: {sum(len(files) for files in db_files.values())} 个")
        return db_files
    
    def _classify_db_file(self, db_file: Path) -> str:
        """分类数据库文件"""
        filename = db_file.name.lower()
        
        # 测试文件
        if any(word in filename for word in ['test', 'debug', 'temp', 'tmp']):
            return 'test'
        
        # 备份文件
        if any(word in filename for word in ['backup', 'bak', '.bak']):
            return 'backup'
        
        # 时间戳文件
        if any(char.isdigit() for char in filename) and len(filename) > 20:
            return 'timestamped'
        
        # 主要数据源
        for source in self.source_mapping.keys():
            if source in filename:
                return 'source'
        
        # 主数据库
        if 'finance_news' in filename:
            return 'main'
        
        # 其他
        return 'other'
    
    def analyze_data_duplicates(self) -> Dict[str, any]:
        """分析数据重复情况"""
        logger.info("开始分析数据重复...")
        
        db_files = self.scan_database_files()
        duplicate_analysis = {
            'identical_files': [],
            'similar_content': [],
            'empty_files': [],
            'large_files': []
        }
        
        # 分析每个数据库文件
        for file_type, files in db_files.items():
            for db_file in files:
                try:
                    # 检查文件大小
                    file_size = db_file.stat().st_size
                    
                    if file_size == 0:
                        duplicate_analysis['empty_files'].append(str(db_file))
                        continue
                    
                    if file_size > 1024 * 1024:  # 1MB
                        duplicate_analysis['large_files'].append({
                            'file': str(db_file),
                            'size': file_size
                        })
                    
                    # 检查数据库内容
                    with sqlite3.connect(str(db_file)) as conn:
                        cursor = conn.cursor()
                        
                        # 检查是否有news表
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                        if cursor.fetchone():
                            cursor.execute("SELECT COUNT(*) FROM news")
                            count = cursor.fetchone()[0]
                            
                            if count == 0:
                                duplicate_analysis['empty_files'].append(str(db_file))
                            else:
                                # 检查数据内容重复
                                cursor.execute("SELECT COUNT(*), title FROM news GROUP BY title HAVING COUNT(*) > 1")
                                duplicates = cursor.fetchall()
                                
                                if duplicates:
                                    duplicate_analysis['similar_content'].append({
                                        'file': str(db_file),
                                        'duplicates': len(duplicates)
                                    })
                
                except Exception as e:
                    logger.error(f"分析文件 {db_file} 时出错: {e}")
        
        return duplicate_analysis
    
    def consolidate_databases(self) -> Dict[str, any]:
        """整合数据库文件"""
        logger.info("开始整合数据库文件...")
        
        db_files = self.scan_database_files()
        consolidation_report = {
            'moved_files': [],
            'merged_files': [],
            'archived_files': [],
            'deleted_files': []
        }
        
        # 处理源数据库
        if 'source' in db_files:
            for db_file in db_files['source']:
                target_file = self._get_target_file(db_file)
                
                if target_file.exists():
                    # 合并数据
                    self._merge_databases(db_file, target_file)
                    consolidation_report['merged_files'].append({
                        'source': str(db_file),
                        'target': str(target_file)
                    })
                else:
                    # 移动文件
                    shutil.move(str(db_file), str(target_file))
                    consolidation_report['moved_files'].append({
                        'source': str(db_file),
                        'target': str(target_file)
                    })
        
        # 处理备份文件
        if 'backup' in db_files:
            for db_file in db_files['backup']:
                target_file = self.backup_dir / f"{db_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.move(str(db_file), str(target_file))
                consolidation_report['archived_files'].append({
                    'source': str(db_file),
                    'target': str(target_file)
                })
        
        # 处理测试文件
        if 'test' in db_files:
            for db_file in db_files['test']:
                target_file = self.archive_dir / db_file.name
                shutil.move(str(db_file), str(target_file))
                consolidation_report['archived_files'].append({
                    'source': str(db_file),
                    'target': str(target_file)
                })
        
        # 处理时间戳文件
        if 'timestamped' in db_files:
            for db_file in db_files['timestamped']:
                # 删除空的时间戳文件
                if db_file.stat().st_size < 1024:  # 小于1KB
                    db_file.unlink()
                    consolidation_report['deleted_files'].append(str(db_file))
                else:
                    target_file = self.archive_dir / db_file.name
                    shutil.move(str(db_file), str(target_file))
                    consolidation_report['archived_files'].append({
                        'source': str(db_file),
                        'target': str(target_file)
                    })
        
        return consolidation_report
    
    def _get_target_file(self, db_file: Path) -> Path:
        """获取目标文件路径"""
        filename = db_file.name.lower()
        
        # 检查是否匹配已知的数据源
        for source, target_name in self.source_mapping.items():
            if source in filename:
                return self.unified_db_dir / target_name
        
        # 默认返回原文件名
        return self.unified_db_dir / db_file.name
    
    def _merge_databases(self, source_db: Path, target_db: Path):
        """合并数据库"""
        try:
            with sqlite3.connect(str(target_db)) as target_conn:
                target_conn.execute("ATTACH DATABASE ? AS source_db", (str(source_db),))
                
                # 检查源数据库是否有news表
                cursor = target_conn.cursor()
                cursor.execute("SELECT name FROM source_db.sqlite_master WHERE type='table' AND name='news'")
                
                if cursor.fetchone():
                    # 合并数据，避免重复
                    target_conn.execute("""
                        INSERT OR IGNORE INTO news 
                        SELECT * FROM source_db.news 
                        WHERE url NOT IN (SELECT url FROM news)
                    """)
                    
                    logger.info(f"合并数据库 {source_db} -> {target_db}")
                
                target_conn.execute("DETACH DATABASE source_db")
        
        except Exception as e:
            logger.error(f"合并数据库时出错: {e}")
    
    def optimize_databases(self):
        """优化数据库性能"""
        logger.info("开始优化数据库...")
        
        # 获取所有数据库文件
        db_files = list(self.unified_db_dir.glob('*.db'))
        
        for db_file in db_files:
            try:
                with sqlite3.connect(str(db_file)) as conn:
                    # 启用WAL模式
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=NORMAL")
                    conn.execute("PRAGMA cache_size=10000")
                    conn.execute("PRAGMA busy_timeout=5000")
                    
                    # 创建索引
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_url ON news(url)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_source ON news(source)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_pub_time ON news(pub_time)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_title ON news(title)")
                    
                    # 分析和优化
                    conn.execute("ANALYZE")
                    conn.execute("VACUUM")
                    
                    logger.info(f"优化数据库: {db_file.name}")
            
            except Exception as e:
                logger.error(f"优化数据库 {db_file} 时出错: {e}")
    
    def create_backup_strategy(self):
        """创建备份策略"""
        logger.info("创建备份策略...")
        
        backup_script = self.project_root / 'scripts' / 'backup_databases.py'
        
        backup_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库自动备份脚本
"""

import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

class DatabaseBackupManager:
    """数据库备份管理器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.db_dir = self.project_root / 'data' / 'db'
        self.backup_dir = self.db_dir / 'backups'
        
        # 备份配置
        self.backup_config = {
            'daily': 7,     # 保留7天的日备份
            'weekly': 4,    # 保留4周的周备份
            'monthly': 12   # 保留12个月的月备份
        }
    
    def create_backup(self, db_file: Path, backup_type: str = 'daily'):
        """创建数据库备份"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{db_file.stem}_{backup_type}_{timestamp}.db"
        backup_path = self.backup_dir / backup_name
        
        try:
            shutil.copy2(str(db_file), str(backup_path))
            print(f"创建备份: {backup_name}")
            return backup_path
        except Exception as e:
            print(f"创建备份失败: {e}")
            return None
    
    def cleanup_old_backups(self):
        """清理旧备份"""
        now = datetime.now()
        
        for backup_file in self.backup_dir.glob('*.db'):
            try:
                # 解析备份文件名中的时间戳
                parts = backup_file.stem.split('_')
                if len(parts) >= 3:
                    date_str = parts[-2]
                    time_str = parts[-1]
                    
                    backup_time = datetime.strptime(f"{date_str}_{time_str}", '%Y%m%d_%H%M%S')
                    age_days = (now - backup_time).days
                    
                    # 根据备份类型决定是否删除
                    backup_type = 'daily'  # 默认类型
                    for bt in ['daily', 'weekly', 'monthly']:
                        if bt in backup_file.name:
                            backup_type = bt
                            break
                    
                    max_age = self.backup_config.get(backup_type, 7)
                    
                    if age_days > max_age:
                        backup_file.unlink()
                        print(f"删除过期备份: {backup_file.name}")
            
            except Exception as e:
                print(f"处理备份文件 {backup_file} 时出错: {e}")
    
    def auto_backup(self):
        """自动备份所有数据库"""
        print("开始自动备份...")
        
        # 备份所有数据库文件
        for db_file in self.db_dir.glob('*.db'):
            if db_file.name.endswith('_finance.db') or db_file.name == 'finance_news.db':
                self.create_backup(db_file)
        
        # 清理旧备份
        self.cleanup_old_backups()
        
        print("自动备份完成")

if __name__ == "__main__":
    backup_manager = DatabaseBackupManager()
    backup_manager.auto_backup()
'''
        
        with open(backup_script, 'w', encoding='utf-8') as f:
            f.write(backup_code)
        
        # 使脚本可执行
        backup_script.chmod(0o755)
        
        logger.info(f"创建备份脚本: {backup_script}")
    
    def generate_report(self):
        """生成修复报告"""
        self.report['end_time'] = datetime.now().isoformat()
        self.report['summary'] = {
            'total_actions': len(self.report['actions']),
            'total_errors': len(self.report['errors']),
            'unified_db_dir': str(self.unified_db_dir),
            'main_db': str(self.main_db)
        }
        
        # 保存报告
        report_file = self.project_root / f"database_architecture_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"生成修复报告: {report_file}")
        return report_file
    
    def run_full_fix(self):
        """运行完整修复"""
        logger.info("开始数据库架构修复...")
        
        try:
            # 1. 分析重复数据
            duplicate_analysis = self.analyze_data_duplicates()
            self.report['actions'].append({
                'action': 'analyze_duplicates',
                'result': duplicate_analysis
            })
            
            # 2. 整合数据库
            consolidation_report = self.consolidate_databases()
            self.report['actions'].append({
                'action': 'consolidate_databases',
                'result': consolidation_report
            })
            
            # 3. 优化数据库
            self.optimize_databases()
            self.report['actions'].append({
                'action': 'optimize_databases',
                'result': 'completed'
            })
            
            # 4. 创建备份策略
            self.create_backup_strategy()
            self.report['actions'].append({
                'action': 'create_backup_strategy',
                'result': 'completed'
            })
            
            # 5. 生成报告
            report_file = self.generate_report()
            
            logger.info("数据库架构修复完成!")
            return report_file
            
        except Exception as e:
            logger.error(f"修复过程中出错: {e}")
            self.report['errors'].append(str(e))
            return None

def main():
    """主函数"""
    fixer = DatabaseArchitectureFixer()
    report_file = fixer.run_full_fix()
    
    if report_file:
        print(f"\n修复完成! 报告文件: {report_file}")
        print(f"统一数据库目录: {fixer.unified_db_dir}")
        print(f"主数据库: {fixer.main_db}")
    else:
        print("修复过程中出现错误，请检查日志")

if __name__ == "__main__":
    main() 