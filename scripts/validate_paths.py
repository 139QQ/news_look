#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 部署前路径验证脚本

验证数据库路径统一配置的正确性，确保所有组件都使用统一的数据库路径。
"""

import os
import sys
import glob
import sqlite3
import yaml
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from backend.newslook.config import get_db_path_manager, get_unified_db_path, get_unified_db_dir
    from backend.newslook.crawlers.manager import CrawlerManager
    from backend.newslook.utils.database import NewsDatabase
except ImportError as e:
    print(f"[ERROR] 导入模块失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)

class PathValidator:
    """路径验证器"""
    
    def __init__(self):
        self.project_root = project_root
        self.db_path_manager = get_db_path_manager()
        self.unified_db_dir = get_unified_db_dir()
        self.unified_db_path = get_unified_db_path()
        self.errors = []
        self.warnings = []
        self.info = []
        
    def validate_all(self):
        """执行所有验证"""
        print("=" * 60)
        print("NewsLook 部署前路径验证")
        print("=" * 60)
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"项目根目录: {self.project_root}")
        print(f"统一数据库目录: {self.unified_db_dir}")
        print(f"统一主数据库路径: {self.unified_db_path}")
        print()
        
        # 执行各项验证
        self.validate_config_consistency()
        self.validate_database_paths()
        self.validate_crawler_paths()
        self.validate_web_service_paths()
        self.validate_database_structure()
        self.check_old_databases()
        
        # 输出结果
        self.print_results()
        
        # 返回验证结果
        return len(self.errors) == 0
        
    def validate_config_consistency(self):
        """验证配置一致性"""
        print("[1/6] 验证配置一致性...")
        
        # 检查 configs/app.yaml
        config_file = self.project_root / 'configs' / 'app.yaml'
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    
                config_db_dir = config.get('database', {}).get('db_dir', '')
                if config_db_dir:
                    if not os.path.isabs(config_db_dir):
                        config_db_path = str(self.project_root / config_db_dir)
                    else:
                        config_db_path = config_db_dir
                    
                    # 标准化路径分隔符进行比较
                    config_db_path_normalized = os.path.normpath(config_db_path)
                    unified_db_dir_normalized = os.path.normpath(self.unified_db_dir)
                        
                    if config_db_path_normalized == unified_db_dir_normalized:
                        self.info.append("✓ configs/app.yaml 中的数据库目录配置正确")
                    else:
                        self.errors.append(f"✗ configs/app.yaml 中的数据库目录不一致: {config_db_path_normalized} != {unified_db_dir_normalized}")
                else:
                    self.warnings.append("⚠ configs/app.yaml 中未找到数据库目录配置")
                    
            except Exception as e:
                self.errors.append(f"✗ 读取 configs/app.yaml 失败: {e}")
        else:
            self.warnings.append("⚠ configs/app.yaml 文件不存在")
            
        # 检查环境变量
        env_db_dir = os.environ.get('NEWSLOOK_DB_DIR')
        if env_db_dir:
            self.info.append(f"✓ 检测到环境变量 NEWSLOOK_DB_DIR: {env_db_dir}")
        
    def validate_database_paths(self):
        """验证数据库路径"""
        print("[2/6] 验证数据库路径...")
        
        # 检查统一数据库目录是否存在
        if os.path.exists(self.unified_db_dir):
            self.info.append(f"✓ 统一数据库目录存在: {self.unified_db_dir}")
        else:
            self.warnings.append(f"⚠ 统一数据库目录不存在，将自动创建: {self.unified_db_dir}")
            
        # 检查主数据库文件
        if os.path.exists(self.unified_db_path):
            file_size = os.path.getsize(self.unified_db_path) / 1024
            self.info.append(f"✓ 统一主数据库存在: {self.unified_db_path} ({file_size:.1f} KB)")
        else:
            self.warnings.append(f"⚠ 统一主数据库不存在，将在首次运行时创建: {self.unified_db_path}")
            
        # 检查数据库目录权限
        try:
            os.makedirs(self.unified_db_dir, exist_ok=True)
            test_file = os.path.join(self.unified_db_dir, '.test_write')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            self.info.append("✓ 数据库目录写入权限正常")
        except Exception as e:
            self.errors.append(f"✗ 数据库目录权限检查失败: {e}")
            
    def validate_crawler_paths(self):
        """验证爬虫路径配置"""
        print("[3/6] 验证爬虫路径配置...")
        
        try:
            # 初始化爬虫管理器
            crawler_manager = CrawlerManager()
            crawlers = crawler_manager.get_all_crawlers()
            
            for name, crawler_class in crawlers.items():
                try:
                    # 创建爬虫实例（使用统一数据库路径）
                    crawler = crawler_class(db_path=self.unified_db_path, use_source_db=False)
                    
                    if hasattr(crawler, 'db_path'):
                        if crawler.db_path == self.unified_db_path:
                            self.info.append(f"✓ 爬虫 {name} 使用统一数据库路径")
                        else:
                            self.errors.append(f"✗ 爬虫 {name} 数据库路径不统一: {crawler.db_path}")
                    else:
                        self.errors.append(f"✗ 爬虫 {name} 缺少 db_path 属性")
                        
                except Exception as e:
                    self.errors.append(f"✗ 初始化爬虫 {name} 失败: {e}")
                    
        except Exception as e:
            self.errors.append(f"✗ 初始化爬虫管理器失败: {e}")
            
    def validate_web_service_paths(self):
        """验证Web服务路径配置"""
        print("[4/6] 验证Web服务路径配置...")
        
        # 检查主要的Web服务文件
        web_files = [
            'app.py',
            'backend/app/routes.py',
            'backend/main.py'
        ]
        
        for web_file in web_files:
            web_path = self.project_root / web_file
            if web_path.exists():
                try:
                    with open(web_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # 检查是否使用了统一的数据库配置导入
                    if 'get_unified_db_path' in content or 'get_db_path_manager' in content:
                        self.info.append(f"✓ {web_file} 使用统一数据库配置")
                    else:
                        self.warnings.append(f"⚠ {web_file} 可能未使用统一数据库配置")
                        
                except Exception as e:
                    self.warnings.append(f"⚠ 检查 {web_file} 失败: {e}")
            else:
                self.warnings.append(f"⚠ Web服务文件不存在: {web_file}")
                
    def validate_database_structure(self):
        """验证数据库结构"""
        print("[5/6] 验证数据库结构...")
        
        try:
            # 创建NewsDatabase实例来验证数据库结构
            news_db = NewsDatabase(db_path=self.unified_db_path)
            
            # 检查数据库连接
            if hasattr(news_db, 'session') and news_db.session:
                self.info.append("✓ 数据库连接正常")
                
                # 检查表结构
                try:
                    count = news_db.get_news_count()
                    self.info.append(f"✓ 数据库表结构正常，当前新闻数量: {count}")
                except Exception as e:
                    self.errors.append(f"✗ 数据库表结构异常: {e}")
                    
            else:
                self.errors.append("✗ 数据库连接失败")
                
        except Exception as e:
            self.errors.append(f"✗ 数据库结构验证失败: {e}")
            
    def check_old_databases(self):
        """检查旧的分散数据库文件"""
        print("[6/6] 检查旧的分散数据库文件...")
        
        # 搜索可能的旧数据库文件位置
        search_dirs = [
            self.project_root / 'data',
            self.project_root / 'data' / 'databases',
            self.project_root / 'backend' / 'data',
            self.project_root / 'backend' / 'newslook' / 'crawlers' / 'data'
        ]
        
        old_dbs = []
        for search_dir in search_dirs:
            if search_dir.exists():
                db_files = list(search_dir.glob('*.db'))
                for db_file in db_files:
                    # 排除统一的主数据库
                    if str(db_file) != self.unified_db_path:
                        old_dbs.append(str(db_file))
                        
        if old_dbs:
            self.warnings.append("⚠ 发现旧的分散数据库文件:")
            for old_db in old_dbs:
                file_size = os.path.getsize(old_db) / 1024
                self.warnings.append(f"  - {old_db} ({file_size:.1f} KB)")
            self.warnings.append("  建议在确认数据迁移完成后删除这些文件")
        else:
            self.info.append("✓ 未发现旧的分散数据库文件")
            
    def print_results(self):
        """打印验证结果"""
        print("\n" + "=" * 60)
        print("验证结果汇总")
        print("=" * 60)
        
        if self.info:
            print(f"\n✓ 成功信息 ({len(self.info)} 项):")
            for msg in self.info:
                print(f"  {msg}")
                
        if self.warnings:
            print(f"\n⚠ 警告信息 ({len(self.warnings)} 项):")
            for msg in self.warnings:
                print(f"  {msg}")
                
        if self.errors:
            print(f"\n✗ 错误信息 ({len(self.errors)} 项):")
            for msg in self.errors:
                print(f"  {msg}")
        else:
            print("\n✓ 所有验证项目通过!")
            
        print("\n" + "=" * 60)
        
        if self.errors:
            print("❌ 部署前验证失败，请解决上述错误后重新验证")
            return False
        elif self.warnings:
            print("⚠️  部署前验证通过，但有警告信息需要注意")
            return True
        else:
            print("✅ 部署前验证完全通过，系统配置正确")
            return True

def main():
    """主函数"""
    validator = PathValidator()
    success = validator.validate_all()
    
    if success:
        print(f"\n数据库配置信息:")
        print(f"  统一数据库目录: {validator.unified_db_dir}")
        print(f"  统一主数据库: {validator.unified_db_path}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 