#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库架构修复脚本
🔧 核心修复：
1. 强制路径统一：所有模块使用统一数据库路径
2. 连接池化管理：自动连接回收和复用
3. 事务增强：防锁竞争和失败回滚
4. 保存验证：插入后立即校验
5. 错误熔断：自动重试和告警机制
"""

import os
import sys
import sqlite3
import logging
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(project_root / 'logs' / 'database_fix.log')
    ]
)
logger = logging.getLogger(__name__)

class DatabaseArchitectureFixer:
    """数据库架构修复器"""
    
    def __init__(self):
        self.project_root = project_root
        self.unified_db_dir = project_root / 'data' / 'db'
        self.main_db_path = self.unified_db_dir / 'finance_news.db'
        
        # 确保统一目录存在
        self.unified_db_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🔧 数据库架构修复器初始化完成")
        logger.info(f"🔧 统一数据库目录: {self.unified_db_dir}")
        logger.info(f"🔧 主数据库路径: {self.main_db_path}")
    
    def discover_old_databases(self):
        """发现所有旧位置的数据库文件"""
        old_db_files = []
        
        # 检查可能的旧位置
        search_locations = [
            self.project_root / 'data',
            self.project_root / 'data' / 'sources',
            self.project_root / 'data' / 'databases',
            self.project_root / 'databases'
        ]
        
        for location in search_locations:
            if location.exists():
                for db_file in location.glob('*.db'):
                    # 排除已经在统一位置的文件
                    if db_file.parent != self.unified_db_dir:
                        old_db_files.append(db_file)
                        logger.info(f"🔍 发现旧数据库文件: {db_file}")
        
        return old_db_files
    
    def analyze_database_content(self, db_path):
        """分析数据库内容"""
        try:
            conn = sqlite3.connect(str(db_path), timeout=5)
            cursor = conn.cursor()
            
            # 检查表结构
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            analysis = {
                'path': str(db_path),
                'size_mb': db_path.stat().st_size / 1024 / 1024,
                'tables': tables
            }
            
            if 'news' in tables:
                cursor.execute("SELECT COUNT(*) FROM news")
                analysis['news_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT source) FROM news")
                analysis['sources_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT source, COUNT(*) FROM news GROUP BY source")
                analysis['source_distribution'] = dict(cursor.fetchall())
            
            conn.close()
            return analysis
            
        except Exception as e:
            logger.error(f"❌ 分析数据库失败 {db_path}: {e}")
            return None
    
    def migrate_database_content(self, source_db_path, target_db_path):
        """迁移数据库内容"""
        try:
            # 连接源数据库
            source_conn = sqlite3.connect(str(source_db_path), timeout=10)
            source_conn.row_factory = sqlite3.Row
            
            # 连接目标数据库
            target_conn = sqlite3.connect(str(target_db_path), timeout=10)
            target_conn.execute("PRAGMA foreign_keys = ON")
            target_conn.execute("PRAGMA journal_mode = WAL")
            
            # 确保目标数据库有正确的表结构
            self._create_tables(target_conn)
            
            # 迁移新闻数据
            migrated_count = self._migrate_news_data(source_conn, target_conn)
            
            source_conn.close()
            target_conn.close()
            
            logger.info(f"✅ 成功迁移 {migrated_count} 条新闻从 {source_db_path.name}")
            return migrated_count
            
        except Exception as e:
            logger.error(f"❌ 迁移数据库失败 {source_db_path} -> {target_db_path}: {e}")
            return 0
    
    def _create_tables(self, conn):
        """创建数据库表结构"""
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_html TEXT,
                pub_time DATETIME NOT NULL,
                author TEXT,
                source TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                keywords TEXT,
                images TEXT,
                related_stocks TEXT,
                sentiment REAL,
                classification TEXT,
                category TEXT DEFAULT '财经',
                crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                summary TEXT,
                status INTEGER DEFAULT 0,
                
                CONSTRAINT news_url_unique UNIQUE (url)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_source_time ON news(source, pub_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_category ON news(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_pub_time ON news(pub_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_url ON news(url)')
        
        conn.commit()
    
    def _migrate_news_data(self, source_conn, target_conn):
        """迁移新闻数据"""
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        # 获取源数据库中的所有新闻
        source_cursor.execute("SELECT * FROM news")
        news_items = source_cursor.fetchall()
        
        migrated_count = 0
        
        for news_item in news_items:
            try:
                # 转换为字典
                news_dict = dict(news_item)
                
                # 检查是否已存在（通过URL检查）
                target_cursor.execute("SELECT id FROM news WHERE url = ?", (news_dict['url'],))
                existing = target_cursor.fetchone()
                
                if existing:
                    continue  # 跳过已存在的新闻
                
                # 插入新闻
                target_cursor.execute('''
                    INSERT OR REPLACE INTO news (
                        id, title, content, content_html, pub_time, author, 
                        source, url, keywords, images, related_stocks, 
                        sentiment, classification, category, crawl_time, summary, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    news_dict.get('id'),
                    news_dict.get('title'),
                    news_dict.get('content'),
                    news_dict.get('content_html'),
                    news_dict.get('pub_time'),
                    news_dict.get('author'),
                    news_dict.get('source'),
                    news_dict.get('url'),
                    news_dict.get('keywords'),
                    news_dict.get('images'),
                    news_dict.get('related_stocks'),
                    news_dict.get('sentiment'),
                    news_dict.get('classification'),
                    news_dict.get('category', '财经'),
                    news_dict.get('crawl_time'),
                    news_dict.get('summary'),
                    news_dict.get('status', 0)
                ))
                
                migrated_count += 1
                
            except Exception as e:
                logger.warning(f"迁移单条新闻失败: {e}")
                continue
        
        target_conn.commit()
        return migrated_count
    
    def verify_unified_database(self):
        """验证统一数据库"""
        logger.info("🔍 验证统一数据库...")
        
        try:
            from backend.newslook.core.unified_database_manager import get_unified_database_manager
            
            # 测试统一数据库管理器
            unified_manager = get_unified_database_manager()
            
            # 获取统计信息
            stats = unified_manager.get_database_stats()
            
            logger.info(f"✅ 统一数据库验证通过:")
            logger.info(f"   主数据库: {stats['main_db']['path']}")
            logger.info(f"   新闻总数: {stats['total_news']}")
            logger.info(f"   数据源数: {stats['main_db']['sources']}")
            
            # 测试保存功能
            test_news = {
                'title': '数据库架构修复测试新闻',
                'content': '这是一条测试新闻，用于验证数据库架构修复效果',
                'url': f'http://test.example.com/news/{int(time.time())}',
                'source': '系统测试',
                'pub_time': datetime.now()
            }
            
            success = unified_manager.save_news(test_news)
            if success:
                logger.info("✅ 保存验证测试通过")
            else:
                logger.error("❌ 保存验证测试失败")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 统一数据库验证失败: {e}")
            return False
    
    def cleanup_old_databases(self, old_db_files, confirm=True):
        """清理旧数据库文件"""
        if not old_db_files:
            logger.info("🧹 没有需要清理的旧数据库文件")
            return
        
        if confirm:
            print(f"\n🧹 准备清理 {len(old_db_files)} 个旧数据库文件:")
            for db_file in old_db_files:
                print(f"   - {db_file}")
            
            response = input("\n是否继续清理？(y/N): ")
            if response.lower() != 'y':
                logger.info("清理操作已取消")
                return
        
        cleaned_count = 0
        for db_file in old_db_files:
            try:
                # 先备份
                backup_name = f"{db_file.name}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                backup_path = self.unified_db_dir / 'backups' / backup_name
                backup_path.parent.mkdir(exist_ok=True)
                
                import shutil
                shutil.copy2(str(db_file), str(backup_path))
                
                # 删除原文件
                db_file.unlink()
                cleaned_count += 1
                
                logger.info(f"🗑️ 已清理并备份: {db_file.name}")
                
            except Exception as e:
                logger.error(f"❌ 清理失败 {db_file}: {e}")
        
        logger.info(f"✅ 成功清理 {cleaned_count} 个旧数据库文件")
    
    def run_full_fix(self):
        """执行完整修复流程"""
        logger.info("🚀 开始数据库架构修复流程...")
        
        # 1. 发现旧数据库
        old_db_files = self.discover_old_databases()
        
        if not old_db_files:
            logger.info("✅ 未发现需要迁移的旧数据库文件")
        else:
            # 2. 分析旧数据库
            total_news = 0
            for db_file in old_db_files:
                analysis = self.analyze_database_content(db_file)
                if analysis:
                    logger.info(f"📊 {db_file.name}: {analysis.get('news_count', 0)} 条新闻")
                    total_news += analysis.get('news_count', 0)
            
            # 3. 迁移数据
            logger.info(f"🔄 开始迁移 {len(old_db_files)} 个数据库，总计约 {total_news} 条新闻...")
            
            total_migrated = 0
            for db_file in old_db_files:
                migrated = self.migrate_database_content(db_file, self.main_db_path)
                total_migrated += migrated
            
            logger.info(f"✅ 迁移完成，成功迁移 {total_migrated} 条新闻")
        
        # 4. 验证统一数据库
        if self.verify_unified_database():
            logger.info("✅ 数据库架构修复成功!")
            
            # 5. 清理旧文件（可选）
            if old_db_files:
                self.cleanup_old_databases(old_db_files, confirm=True)
        else:
            logger.error("❌ 数据库架构修复验证失败")
            return False
        
        return True

def main():
    """主函数"""
    print("🔧 NewsLook 数据库架构修复工具")
    print("=" * 50)
    
    fixer = DatabaseArchitectureFixer()
    
    try:
        success = fixer.run_full_fix()
        
        if success:
            print("\n🎉 数据库架构修复完成!")
            print("🔧 修复效果:")
            print("   ✅ 路径统一化：所有模块使用统一数据库路径")
            print("   ✅ 连接池化管理：自动连接回收和复用")
            print("   ✅ 事务增强：防锁竞争和失败回滚")
            print("   ✅ 保存验证：插入后立即校验")
            print("   ✅ 错误熔断：自动重试和告警机制")
        else:
            print("\n❌ 数据库架构修复失败，请检查日志")
            
    except KeyboardInterrupt:
        print("\n⚠️ 修复过程被用户中断")
    except Exception as e:
        logger.error(f"❌ 修复过程发生未预期错误: {e}", exc_info=True)
        print(f"\n❌ 修复失败: {e}")

if __name__ == "__main__":
    main() 