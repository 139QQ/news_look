#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库管理器
负责统一管理数据库文件位置、命名规范和备份策略
"""

import os
import shutil
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

class DatabaseManager:
    """统一数据库管理器"""
    
    # 数据库文件命名规范
    DB_NAME_MAP = {
        'sina': 'sina_finance.db',
        'eastmoney': 'eastmoney_finance.db', 
        'netease': 'netease_finance.db',
        'ifeng': 'ifeng_finance.db',
        '新浪财经': 'sina_finance.db',
        '东方财富': 'eastmoney_finance.db',
        '网易财经': 'netease_finance.db',
        '凤凰财经': 'ifeng_finance.db'
    }
    
    def __init__(self, base_dir: str = None):
        """
        初始化数据库管理器
        
        Args:
            base_dir: 基础目录，默认为项目根目录
        """
        if base_dir is None:
            # 获取项目根目录
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            base_dir = str(project_root)
        
        self.base_dir = Path(base_dir)
        
        # 设置标准目录结构
        self.db_dir = self.base_dir / 'databases'
        self.backup_dir = self.base_dir / 'databases' / 'backups'
        self.archive_dir = self.base_dir / 'databases' / 'archives'
        self.temp_dir = self.base_dir / 'databases' / 'temp'
        
        # 创建目录
        self._create_directories()
        
        # 设置日志
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _create_directories(self):
        """创建标准目录结构"""
        directories = [
            self.db_dir,
            self.backup_dir,
            self.archive_dir,
            self.temp_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_db_path(self, source: str) -> Path:
        """
        获取标准化的数据库文件路径
        
        Args:
            source: 数据源名称
            
        Returns:
            Path: 标准化的数据库文件路径
        """
        db_name = self.DB_NAME_MAP.get(source, f"{source}.db")
        return self.db_dir / db_name
    
    def normalize_database_files(self) -> Dict[str, str]:
        """
        整理和规范化数据库文件
        
        Returns:
            Dict: 操作结果报告
        """
        results = {
            'moved_files': [],
            'renamed_files': [],
            'backup_files': [],
            'deleted_files': [],
            'errors': []
        }
        
        # 查找所有可能的数据库文件位置
        search_paths = [
            self.base_dir / 'data',
            self.base_dir / 'test_crawl' / 'data',
            self.base_dir / 'backup',
            self.base_dir / 'db',
            self.base_dir,  # 根目录下的文件
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            try:
                self._process_directory(search_path, results)
            except Exception as e:
                results['errors'].append(f"处理目录 {search_path} 时出错: {e}")
        
        # 生成报告
        self._generate_cleanup_report(results)
        return results
    
    def _process_directory(self, directory: Path, results: Dict):
        """
        处理单个目录中的数据库文件
        
        Args:
            directory: 要处理的目录
            results: 结果字典
        """
        for file_path in directory.rglob('*.db'):
            try:
                # 跳过已经在标准位置的文件
                if file_path.parent == self.db_dir:
                    continue
                
                # 跳过备份和临时文件
                if any(x in str(file_path) for x in ['backup', 'temp', 'cache', '.bak']):
                    # 移动到备份目录
                    self._move_to_backup(file_path, results)
                    continue
                
                # 识别数据库类型
                source_type = self._identify_database_source(file_path)
                
                if source_type:
                    # 移动到标准位置
                    target_path = self.get_db_path(source_type)
                    self._move_database_file(file_path, target_path, results)
                else:
                    # 无法识别的文件移动到归档目录
                    self._move_to_archive(file_path, results)
                    
            except Exception as e:
                results['errors'].append(f"处理文件 {file_path} 时出错: {e}")
    
    def _identify_database_source(self, file_path: Path) -> Optional[str]:
        """
        识别数据库文件的来源
        
        Args:
            file_path: 数据库文件路径
            
        Returns:
            Optional[str]: 识别的来源类型
        """
        file_name = file_path.name.lower()
        
        # 直接文件名匹配
        for source, standard_name in self.DB_NAME_MAP.items():
            if file_name == standard_name.lower():
                return source
        
        # 模糊匹配
        if 'sina' in file_name or '新浪' in file_name:
            return 'sina'
        elif 'eastmoney' in file_name or '东方财富' in file_name:
            return 'eastmoney'
        elif 'netease' in file_name or '网易' in file_name:
            return 'netease'
        elif 'ifeng' in file_name or '凤凰' in file_name:
            return 'ifeng'
        
        # 检查数据库内容
        try:
            return self._identify_by_content(file_path)
        except:
            return None
    
    def _identify_by_content(self, file_path: Path) -> Optional[str]:
        """
        通过数据库内容识别来源
        
        Args:
            file_path: 数据库文件路径
            
        Returns:
            Optional[str]: 识别的来源类型
        """
        try:
            conn = sqlite3.connect(str(file_path))
            cursor = conn.cursor()
            
            # 检查是否有news表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
            if not cursor.fetchone():
                conn.close()
                return None
            
            # 查看source字段的值
            cursor.execute("SELECT DISTINCT source FROM news LIMIT 5")
            sources = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            for source in sources:
                if source:
                    source_lower = source.lower()
                    if '新浪' in source or 'sina' in source_lower:
                        return 'sina'
                    elif '东方财富' in source or 'eastmoney' in source_lower:
                        return 'eastmoney'
                    elif '网易' in source or 'netease' in source_lower:
                        return 'netease'
                    elif '凤凰' in source or 'ifeng' in source_lower:
                        return 'ifeng'
            
            return None
            
        except Exception:
            return None
    
    def _move_database_file(self, source_path: Path, target_path: Path, results: Dict):
        """
        移动数据库文件到标准位置
        
        Args:
            source_path: 源文件路径
            target_path: 目标文件路径
            results: 结果字典
        """
        try:
            # 如果目标文件已存在，先备份
            if target_path.exists():
                backup_path = self._create_backup(target_path)
                results['backup_files'].append(f"{target_path} -> {backup_path}")
            
            # 移动文件
            shutil.move(str(source_path), str(target_path))
            results['moved_files'].append(f"{source_path} -> {target_path}")
            
            self.logger.info(f"移动数据库文件: {source_path} -> {target_path}")
            
        except Exception as e:
            results['errors'].append(f"移动文件失败 {source_path} -> {target_path}: {e}")
    
    def _move_to_backup(self, file_path: Path, results: Dict):
        """
        移动文件到备份目录
        
        Args:
            file_path: 文件路径
            results: 结果字典
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            backup_path = self.backup_dir / backup_name
            
            shutil.move(str(file_path), str(backup_path))
            results['backup_files'].append(f"{file_path} -> {backup_path}")
            
            self.logger.info(f"移动到备份目录: {file_path} -> {backup_path}")
            
        except Exception as e:
            results['errors'].append(f"移动到备份目录失败 {file_path}: {e}")
    
    def _move_to_archive(self, file_path: Path, results: Dict):
        """
        移动文件到归档目录
        
        Args:
            file_path: 文件路径
            results: 结果字典
        """
        try:
            archive_path = self.archive_dir / file_path.name
            
            # 如果归档文件已存在，添加时间戳
            if archive_path.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                archive_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
                archive_path = self.archive_dir / archive_name
            
            shutil.move(str(file_path), str(archive_path))
            results['moved_files'].append(f"{file_path} -> {archive_path}")
            
            self.logger.info(f"移动到归档目录: {file_path} -> {archive_path}")
            
        except Exception as e:
            results['errors'].append(f"移动到归档目录失败 {file_path}: {e}")
    
    def _create_backup(self, file_path: Path) -> Path:
        """
        创建文件备份
        
        Args:
            file_path: 要备份的文件路径
            
        Returns:
            Path: 备份文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(str(file_path), str(backup_path))
        return backup_path
    
    def _generate_cleanup_report(self, results: Dict):
        """
        生成清理报告
        
        Args:
            results: 操作结果
        """
        report_path = self.base_dir / 'DATABASE_CLEANUP_REPORT.md'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 数据库文件整理报告\n\n")
            f.write(f"整理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## 新的数据库目录结构\n\n")
            f.write("```\n")
            f.write("databases/\n")
            f.write("├── sina_finance.db          # 新浪财经数据库\n")
            f.write("├── eastmoney_finance.db     # 东方财富数据库\n")
            f.write("├── netease_finance.db       # 网易财经数据库\n")
            f.write("├── ifeng_finance.db         # 凤凰财经数据库\n")
            f.write("├── backups/                 # 备份文件\n")
            f.write("├── archives/                # 归档文件\n")
            f.write("└── temp/                    # 临时文件\n")
            f.write("```\n\n")
            
            if results['moved_files']:
                f.write("## 移动的文件\n\n")
                for item in results['moved_files']:
                    f.write(f"- {item}\n")
                f.write("\n")
            
            if results['backup_files']:
                f.write("## 备份的文件\n\n")
                for item in results['backup_files']:
                    f.write(f"- {item}\n")
                f.write("\n")
            
            if results['deleted_files']:
                f.write("## 删除的文件\n\n")
                for item in results['deleted_files']:
                    f.write(f"- {item}\n")
                f.write("\n")
            
            if results['errors']:
                f.write("## 错误信息\n\n")
                for item in results['errors']:
                    f.write(f"- {item}\n")
                f.write("\n")
            
            f.write("## 数据库文件统计\n\n")
            f.write("| 数据源 | 标准文件名 | 状态 |\n")
            f.write("|--------|------------|------|\n")
            
            for source, db_name in self.DB_NAME_MAP.items():
                if source in ['sina', 'eastmoney', 'netease', 'ifeng']:
                    db_path = self.get_db_path(source)
                    status = "✅ 存在" if db_path.exists() else "❌ 不存在"
                    f.write(f"| {source} | {db_name} | {status} |\n")
        
        self.logger.info(f"生成清理报告: {report_path}")
    
    def create_backup(self, source: str = None) -> List[str]:
        """
        创建数据库备份
        
        Args:
            source: 指定要备份的数据源，None表示备份所有
            
        Returns:
            List[str]: 备份文件路径列表
        """
        backup_files = []
        
        if source:
            # 备份指定数据源
            db_path = self.get_db_path(source)
            if db_path.exists():
                backup_path = self._create_backup(db_path)
                backup_files.append(str(backup_path))
        else:
            # 备份所有数据源
            for source in ['sina', 'eastmoney', 'netease', 'ifeng']:
                db_path = self.get_db_path(source)
                if db_path.exists():
                    backup_path = self._create_backup(db_path)
                    backup_files.append(str(backup_path))
        
        return backup_files
    
    def get_database_stats(self) -> Dict:
        """
        获取数据库统计信息
        
        Returns:
            Dict: 数据库统计信息
        """
        stats = {}
        
        for source in ['sina', 'eastmoney', 'netease', 'ifeng']:
            db_path = self.get_db_path(source)
            
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    # 获取记录数
                    cursor.execute("SELECT COUNT(*) FROM news")
                    count = cursor.fetchone()[0]
                    
                    # 获取文件大小
                    size = db_path.stat().st_size
                    
                    # 获取最新记录时间
                    cursor.execute("SELECT MAX(crawl_time) FROM news")
                    latest = cursor.fetchone()[0]
                    
                    conn.close()
                    
                    stats[source] = {
                        'path': str(db_path),
                        'records': count,
                        'size_bytes': size,
                        'size_mb': round(size / 1024 / 1024, 2),
                        'latest_crawl': latest,
                        'exists': True
                    }
                    
                except Exception as e:
                    stats[source] = {
                        'path': str(db_path),
                        'error': str(e),
                        'exists': True
                    }
            else:
                stats[source] = {
                    'path': str(db_path),
                    'exists': False
                }
        
        return stats

if __name__ == "__main__":
    # 测试数据库管理器
    manager = DatabaseManager()
    
    print("开始整理数据库文件...")
    results = manager.normalize_database_files()
    
    print("\n整理结果:")
    print(f"移动文件: {len(results['moved_files'])}")
    print(f"备份文件: {len(results['backup_files'])}")
    print(f"错误: {len(results['errors'])}")
    
    print("\n数据库统计:")
    stats = manager.get_database_stats()
    for source, info in stats.items():
        if info['exists'] and 'records' in info:
            print(f"{source}: {info['records']} 条记录, {info['size_mb']} MB")
        else:
            print(f"{source}: 不存在或无法访问") 