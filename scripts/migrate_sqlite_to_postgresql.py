#!/usr/bin/env python3
"""
SQLite到PostgreSQL数据迁移脚本
实现多源SQLite数据库到统一PostgreSQL的迁移

使用方法:
python scripts/migrate_sqlite_to_postgresql.py

功能:
1. 扫描所有SQLite数据库文件
2. 提取和转换数据
3. 批量迁移到PostgreSQL
4. 验证数据完整性
5. 生成迁移报告
"""

import os
import sys
import sqlite3
import asyncio
import time
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone
import hashlib
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.newslook.databases.postgresql_manager import (
    PostgreSQLManager, DatabaseConfig, NewsRecord
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('data/logs/migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SQLiteExtractor:
    """SQLite数据提取器"""
    
    def __init__(self):
        self.source_mapping = {
            "eastmoney": "eastmoney",
            "sina": "sina", 
            "netease": "netease",
            "ifeng": "ifeng",
            "tencent": "tencent",
            "腾讯财经": "tencent",
            "东方财富": "eastmoney",
            "新浪财经": "sina",
            "网易财经": "netease",
            "凤凰财经": "ifeng"
        }
        
    def discover_sqlite_files(self) -> List[Tuple[str, str]]:
        """发现SQLite文件并映射到源代码"""
        data_dir = project_root / "data"
        discovered = []
        
        # 搜索模式
        patterns = ["*.db", "*.sqlite", "*.sqlite3"]
        
        for pattern in patterns:
            for db_file in data_dir.rglob(pattern):
                # 跳过备份和测试文件
                if any(skip in str(db_file).lower() for skip in ['backup', 'bak', 'temp', 'tmp', 'test']):
                    continue
                    
                # 尝试从文件名推断源代码
                file_name = db_file.stem.lower()
                source_code = None
                
                for keyword, code in self.source_mapping.items():
                    if keyword.lower() in file_name:
                        source_code = code
                        break
                
                if not source_code:
                    # 默认处理
                    if 'finance' in file_name:
                        source_code = 'unknown'
                    else:
                        source_code = file_name.replace('_', '').replace('-', '')
                
                discovered.append((str(db_file), source_code))
                
        return discovered
        
    def extract_from_sqlite(self, db_path: str, source_code: str) -> List[Dict]:
        """从SQLite数据库提取数据"""
        try:
            conn = sqlite3.connect(db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 检查表结构
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            logger.info(f"数据库 {db_path} 包含表: {tables}")
            
            # 尝试不同的表名模式
            news_table = None
            for table_name in ['news', 'finance_news', 'articles', 'data']:
                if table_name in tables:
                    news_table = table_name
                    break
                    
            if not news_table:
                logger.warning(f"在数据库 {db_path} 中未找到新闻表")
                return []
                
            # 检查表结构
            cursor.execute(f"PRAGMA table_info({news_table})")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            logger.info(f"表 {news_table} 的列: {list(columns.keys())}")
            
            # 构建查询SQL
            select_columns = []
            column_mapping = {
                'title': ['title', 'headline', 'subject'],
                'content': ['content', 'body', 'text', 'article'],
                'url': ['url', 'link', 'source_url'],
                'published_at': ['published_at', 'pub_time', 'publish_time', 'date', 'created_at'],
                'author': ['author', 'writer'],
                'category': ['category', 'type', 'section'],
                'summary': ['summary', 'abstract', 'description']
            }
            
            field_map = {}
            for target, candidates in column_mapping.items():
                for candidate in candidates:
                    if candidate in columns:
                        field_map[target] = candidate
                        break
                        
            # 确保必需字段存在
            required_fields = ['title', 'url']
            for field in required_fields:
                if field not in field_map:
                    logger.error(f"缺少必需字段 {field} 在表 {news_table}")
                    return []
                    
            # 构建查询
            query = f"SELECT * FROM {news_table} ORDER BY rowid"
            cursor.execute(query)
            
            records = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                
                # 数据转换和清理
                record = {
                    'title': str(row_dict.get(field_map.get('title', 'title'), '')).strip(),
                    'content': str(row_dict.get(field_map.get('content', 'content'), '')).strip(),
                    'url': str(row_dict.get(field_map.get('url', 'url'), '')).strip(),
                    'source_code': source_code,
                    'published_at': self._parse_datetime(row_dict.get(field_map.get('published_at'))),
                    'crawled_at': datetime.now(timezone.utc),
                    'author': str(row_dict.get(field_map.get('author', 'author'), '') or '').strip(),
                    'category': str(row_dict.get(field_map.get('category', 'category'), '财经')).strip(),
                    'summary': str(row_dict.get(field_map.get('summary', 'summary'), '') or '').strip(),
                    'raw_data': row_dict  # 保存原始数据用于调试
                }
                
                # 数据验证
                if not record['title'] or not record['url']:
                    continue
                    
                # URL清理
                if not record['url'].startswith('http'):
                    continue
                    
                records.append(record)
                
            logger.info(f"从 {db_path} 提取了 {len(records)} 条记录")
            return records
            
        except Exception as e:
            logger.error(f"提取数据失败 {db_path}: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()
                
    def _parse_datetime(self, dt_value) -> datetime:
        """解析日期时间字符串"""
        if not dt_value:
            return datetime.now(timezone.utc)
            
        if isinstance(dt_value, (int, float)):
            # Unix时间戳
            try:
                return datetime.fromtimestamp(dt_value, tz=timezone.utc)
            except (ValueError, OSError):
                return datetime.now(timezone.utc)
                
        if isinstance(dt_value, str):
            # 常见日期格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d',
                '%m/%d/%Y %H:%M:%S',
                '%m/%d/%Y'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(dt_value, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
                    
        return datetime.now(timezone.utc)

class MigrationManager:
    """迁移管理器"""
    
    def __init__(self):
        self.extractor = SQLiteExtractor()
        self.pg_manager: Optional[PostgreSQLManager] = None
        self.migration_stats = {
            'start_time': None,
            'end_time': None,
            'sqlite_files_processed': 0,
            'total_records_found': 0,
            'records_migrated': 0,
            'records_skipped': 0,
            'errors': []
        }
        
    async def initialize_postgresql(self):
        """初始化PostgreSQL连接"""
        config = DatabaseConfig(
            host=os.getenv('PG_HOST', 'localhost'),
            port=int(os.getenv('PG_PORT', 5432)),
            database=os.getenv('PG_DATABASE', 'newslook'),
            username=os.getenv('PG_USERNAME', 'newslook'),
            password=os.getenv('PG_PASSWORD', 'newslook123')
        )
        
        self.pg_manager = PostgreSQLManager(config)
        await self.pg_manager.initialize()
        logger.info("PostgreSQL连接初始化完成")
        
    async def migrate_all_data(self):
        """迁移所有数据"""
        self.migration_stats['start_time'] = time.time()
        
        try:
            # 1. 初始化PostgreSQL
            await self.initialize_postgresql()
            
            # 2. 发现SQLite文件
            print("🔍 正在发现SQLite数据库文件...")
            sqlite_files = self.extractor.discover_sqlite_files()
            
            if not sqlite_files:
                print("❌ 未发现任何SQLite数据库文件")
                return
                
            print(f"✅ 发现 {len(sqlite_files)} 个SQLite数据库:")
            for db_path, source_code in sqlite_files:
                size_mb = Path(db_path).stat().st_size / 1024 / 1024
                print(f"   - {db_path} [{source_code}] ({size_mb:.2f} MB)")
                
            # 3. 逐个迁移数据库
            print("\n🚀 开始数据迁移...")
            
            for db_path, source_code in sqlite_files:
                await self._migrate_single_database(db_path, source_code)
                self.migration_stats['sqlite_files_processed'] += 1
                
            # 4. 验证迁移结果
            await self._verify_migration()
            
            # 5. 生成报告
            await self._generate_migration_report()
            
        except Exception as e:
            logger.error(f"迁移过程中发生错误: {e}")
            self.migration_stats['errors'].append(str(e))
            
        finally:
            self.migration_stats['end_time'] = time.time()
            if self.pg_manager:
                await self.pg_manager.close()
                
    async def _migrate_single_database(self, db_path: str, source_code: str):
        """迁移单个数据库"""
        print(f"\n📦 正在迁移: {Path(db_path).name} [{source_code}]")
        
        try:
            # 提取数据
            records = self.extractor.extract_from_sqlite(db_path, source_code)
            self.migration_stats['total_records_found'] += len(records)
            
            if not records:
                print(f"   ⚠️  无有效数据")
                return
                
            # 获取源ID
            source_id = self.pg_manager.get_source_id(source_code)
            
            # 转换为NewsRecord对象
            news_records = []
            for record in records:
                try:
                    news_record = NewsRecord(
                        title=record['title'],
                        content=record['content'],
                        url=record['url'],
                        source_id=source_id,
                        published_at=record['published_at'],
                        crawled_at=record['crawled_at'],
                        category=record['category'],
                        author=record['author'] if record['author'] else None,
                        summary=record['summary'] if record['summary'] else None,
                        metadata={'migrated_from': db_path, 'original_data': record['raw_data']}
                    )
                    news_records.append(news_record)
                except Exception as e:
                    logger.warning(f"记录转换失败: {e}")
                    self.migration_stats['records_skipped'] += 1
                    
            # 批量插入
            if news_records:
                print(f"   📝 正在插入 {len(news_records)} 条记录...")
                
                # 分批处理，避免内存问题
                batch_size = 500
                for i in range(0, len(news_records), batch_size):
                    batch = news_records[i:i + batch_size]
                    await self.pg_manager.batch_insert_news(batch)
                    
                self.migration_stats['records_migrated'] += len(news_records)
                print(f"   ✅ 成功迁移 {len(news_records)} 条记录")
            else:
                print(f"   ⚠️  无有效记录可迁移")
                
        except Exception as e:
            error_msg = f"迁移数据库失败 {db_path}: {e}"
            logger.error(error_msg)
            self.migration_stats['errors'].append(error_msg)
            print(f"   ❌ 迁移失败: {e}")
            
    async def _verify_migration(self):
        """验证迁移结果"""
        print("\n🔍 正在验证迁移结果...")
        
        try:
            # 获取统计信息
            stats = await self.pg_manager.get_statistics(days=365)
            
            total_in_pg = sum(stat['total_count'] for stat in stats['daily_stats'])
            
            print(f"   📊 PostgreSQL中总记录数: {total_in_pg}")
            print(f"   📊 预期迁移记录数: {self.migration_stats['records_migrated']}")
            
            if total_in_pg >= self.migration_stats['records_migrated'] * 0.95:  # 允许5%误差
                print("   ✅ 数据验证通过")
            else:
                print("   ⚠️  数据验证发现差异，请检查")
                
        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            
    async def _generate_migration_report(self):
        """生成迁移报告"""
        duration = self.migration_stats['end_time'] - self.migration_stats['start_time']
        
        report = f"""
======================================
        SQLite到PostgreSQL迁移报告
======================================

迁移时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
总耗时: {duration:.2f} 秒

文件统计:
- 处理的SQLite文件数: {self.migration_stats['sqlite_files_processed']}
- 发现的记录总数: {self.migration_stats['total_records_found']}

数据统计:
- 成功迁移记录数: {self.migration_stats['records_migrated']}
- 跳过记录数: {self.migration_stats['records_skipped']}
- 迁移成功率: {(self.migration_stats['records_migrated'] / max(self.migration_stats['total_records_found'], 1) * 100):.1f}%

性能指标:
- 迁移速度: {(self.migration_stats['records_migrated'] / max(duration, 1)):.1f} 记录/秒

错误信息:
{chr(10).join(self.migration_stats['errors']) if self.migration_stats['errors'] else '无错误'}

======================================
"""
        
        # 保存报告
        report_file = project_root / "data/logs/migration_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
            
        print(report)
        print(f"📄 迁移报告已保存至: {report_file}")

async def main():
    """主函数"""
    print("🚀 NewsLook SQLite到PostgreSQL迁移工具")
    print("=" * 60)
    
    migration_manager = MigrationManager()
    
    # 检查PostgreSQL连接
    print("🔧 正在检查PostgreSQL连接...")
    try:
        await migration_manager.initialize_postgresql()
        print("✅ PostgreSQL连接成功")
    except Exception as e:
        print(f"❌ PostgreSQL连接失败: {e}")
        print("\n💡 请确保:")
        print("   1. PostgreSQL服务已启动")
        print("   2. 数据库配置正确")
        print("   3. 用户权限充足")
        return
        
    # 执行迁移
    await migration_manager.migrate_all_data()
    
    print("\n🎉 数据迁移完成！")
    print("💡 下一步建议:")
    print("   1. 验证应用功能")
    print("   2. 更新应用配置使用PostgreSQL")
    print("   3. 备份SQLite文件到归档目录")

if __name__ == "__main__":
    asyncio.run(main()) 