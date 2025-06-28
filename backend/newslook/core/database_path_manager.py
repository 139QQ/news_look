#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库路径管理器 - 统一管理所有数据库文件路径
"""

import os
import glob
import logging
from pathlib import Path
from typing import List, Dict, Optional
from backend.newslook.config import get_settings

logger = logging.getLogger(__name__)


class DatabasePathManager:
    """数据库路径统一管理器"""
    
    def __init__(self):
        """初始化数据库路径管理器"""
        self.settings = get_settings()
        self._setup_standard_paths()
    
    def _setup_standard_paths(self):
        """设置标准数据库路径 - 强制路径统一化"""
        # 获取项目根目录
        self.project_root = Path(__file__).parent.parent.parent.parent
        
        # 🔧 修复：强制统一路径，移除sources分离
        self.db_dir = self.project_root / 'data' / 'db'
        self.backup_dir = self.db_dir / 'backups' 
        # 注意：不再创建独立的sources目录，统一存储
        
        # 确保目录存在
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        # 主数据库路径 - 强制使用此路径
        self.main_db_path = self.db_dir / 'finance_news.db'
        
        logger.info(f"🔧 数据库路径统一化完成: {self.db_dir}")
        logger.info(f"🔧 主数据库强制路径: {self.main_db_path}")
    
    def get_main_db_path(self) -> str:
        """获取主数据库路径 - 统一入口"""
        return str(self.main_db_path)
    
    def get_source_db_path(self, source_name: str) -> str:
        """
        获取特定数据源的数据库路径 - 修复：统一存储在db目录
        
        Args:
            source_name: 数据源名称
            
        Returns:
            str: 数据库文件路径（统一在data/db目录下）
        """
        # 标准化数据源名称
        normalized_name = self._normalize_source_name(source_name)
        # 🔧 修复：不再使用sources子目录，统一存储
        return str(self.db_dir / f"{normalized_name}.db")
    
    def _normalize_source_name(self, source_name: str) -> str:
        """标准化数据源名称"""
        name_map = {
            '新浪财经': 'sina',
            '东方财富': 'eastmoney', 
            '网易财经': 'netease',
            '凤凰财经': 'ifeng',
            'sina': 'sina',
            'eastmoney': 'eastmoney',
            'netease': 'netease',
            'ifeng': 'ifeng'
        }
        return name_map.get(source_name, source_name.lower())
    
    def discover_all_db_files(self) -> List[str]:
        """发现所有数据库文件 - 修复：只在统一目录中查找"""
        db_files = []
        
        # 🔧 修复：只在统一数据库目录中查找
        for db_file in self.db_dir.glob('*.db'):
            db_files.append(str(db_file))
        
        # 检查旧位置的数据库文件并迁移
        old_locations = [
            self.project_root / 'data',
            self.project_root / 'data' / 'sources',  # 旧的sources目录
            self.project_root / 'data' / 'databases'
        ]
        
        for location in old_locations:
            if location.exists():
                for db_file in location.glob('*.db'):
                    abs_path = str(db_file)
                    if abs_path not in db_files:
                        db_files.append(abs_path)
                        logger.warning(f"🔧 发现旧位置数据库文件: {abs_path}")
        
        return db_files
    
    def migrate_old_databases(self):
        """迁移旧位置的数据库文件到统一位置"""
        migrated_files = []
        
        # 🔧 修复：迁移data根目录和sources目录下的数据库文件
        migration_sources = [
            self.project_root / 'data',
            self.project_root / 'data' / 'sources'  # 旧的分离目录
        ]
        
        for source_dir in migration_sources:
            if source_dir.exists():
                for db_file in source_dir.glob('*.db'):
                    # 只处理直接在目录下的文件或sources目录下的文件
                    if (db_file.parent == source_dir and 
                        db_file.parent != self.db_dir):  # 避免重复迁移
                        
                        target_path = self.db_dir / db_file.name
                        
                        try:
                            # 如果目标文件不存在或者源文件更新，则复制
                            if not target_path.exists() or db_file.stat().st_mtime > target_path.stat().st_mtime:
                                import shutil
                                shutil.copy2(str(db_file), str(target_path))
                                migrated_files.append(f"{db_file} -> {target_path}")
                                logger.info(f"🔧 迁移数据库文件: {db_file.name}")
                            
                        except Exception as e:
                            logger.error(f"迁移数据库文件失败 {db_file}: {e}")
        
        if migrated_files:
            logger.info(f"🔧 成功迁移 {len(migrated_files)} 个数据库文件到统一位置")
        
        return migrated_files
    
    def get_database_info(self) -> Dict[str, Dict]:
        """获取所有数据库文件信息"""
        db_info = {}
        
        all_db_files = self.discover_all_db_files()
        
        for db_path in all_db_files:
            path_obj = Path(db_path)
            if path_obj.exists():
                try:
                    stat = path_obj.stat()
                    db_info[db_path] = {
                        'name': path_obj.name,
                        'size': stat.st_size,
                        'size_mb': round(stat.st_size / 1024 / 1024, 2),
                        'modified': stat.st_mtime,
                        'location': 'standard' if path_obj.parent == self.db_dir else 'old',
                        'is_main': path_obj.name == 'finance_news.db'
                    }
                except Exception as e:
                    logger.error(f"获取数据库信息失败 {db_path}: {e}")
        
        return db_info
    
    def cleanup_old_databases(self, dry_run: bool = True) -> List[str]:
        """
        清理旧位置的数据库文件
        
        Args:
            dry_run: 是否只是模拟运行
            
        Returns:
            List[str]: 需要/已经清理的文件列表
        """
        cleanup_candidates = []
        
        # 查找data根目录下的数据库文件
        data_root = self.project_root / 'data'
        if data_root.exists():
            for db_file in data_root.glob('*.db'):
                if db_file.parent == data_root:  # 只处理直接在data目录下的文件
                    standard_path = self.db_dir / db_file.name
                    
                    # 如果标准位置已存在相同文件，可以清理旧文件
                    if standard_path.exists():
                        cleanup_candidates.append(str(db_file))
                        
                        if not dry_run:
                            try:
                                db_file.unlink()
                                logger.info(f"已删除旧数据库文件: {db_file}")
                            except Exception as e:
                                logger.error(f"删除旧数据库文件失败 {db_file}: {e}")
        
        if cleanup_candidates:
            action = "将清理" if dry_run else "已清理"
            logger.info(f"{action} {len(cleanup_candidates)} 个旧数据库文件")
        
        return cleanup_candidates


# 全局实例
_db_path_manager = None


def get_database_path_manager() -> DatabasePathManager:
    """获取数据库路径管理器实例（单例）"""
    global _db_path_manager
    if _db_path_manager is None:
        _db_path_manager = DatabasePathManager()
    return _db_path_manager


def get_main_db_path() -> str:
    """快捷方法：获取主数据库路径"""
    return get_database_path_manager().get_main_db_path()


def get_source_db_path(source_name: str) -> str:
    """快捷方法：获取数据源数据库路径"""
    return get_database_path_manager().get_source_db_path(source_name)


def discover_all_databases() -> List[str]:
    """快捷方法：发现所有数据库文件"""
    return get_database_path_manager().discover_all_db_files() 