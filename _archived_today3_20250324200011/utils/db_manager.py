import os
import sys
import logging
import sqlite3
import shutil
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import NewsDatabase
from utils.logger import setup_logger

logger = setup_logger()

class DatabaseManager:
    """数据库管理工具，用于管理和合并各个来源的数据库"""
    
    def __init__(self):
        """初始化数据库管理器"""
        # 获取项目根目录
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 数据库目录
        self.db_dir = os.path.join(self.base_dir, 'db')
        os.makedirs(self.db_dir, exist_ok=True)
        
        # 备份目录
        self.backup_dir = os.path.join(self.base_dir, 'backup')
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 主数据库
        self.main_db = NewsDatabase(os.path.join(self.db_dir, 'finance_news.db'))
    
    def list_databases(self):
        """
        列出所有数据库文件
        
        Returns:
            list: 数据库文件列表
        """
        db_files = [f for f in os.listdir(self.db_dir) if f.endswith('.db')]
        return db_files
    
    def get_database_stats(self, db_file=None):
        """
        获取数据库统计信息
        
        Args:
            db_file: 数据库文件名，如果为None则获取所有数据库的统计信息
            
        Returns:
            dict: 数据库统计信息
        """
        stats = {}
        
        if db_file:
            # 获取指定数据库的统计信息
            db_path = os.path.join(self.db_dir, db_file)
            stats[db_file] = self._get_single_db_stats(db_path)
        else:
            # 获取所有数据库的统计信息
            for db_file in self.list_databases():
                db_path = os.path.join(self.db_dir, db_file)
                stats[db_file] = self._get_single_db_stats(db_path)
        
        return stats
    
    def _get_single_db_stats(self, db_path):
        """
        获取单个数据库的统计信息
        
        Args:
            db_path: 数据库路径
            
        Returns:
            dict: 数据库统计信息
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 获取新闻总数
            cursor.execute("SELECT COUNT(*) FROM news")
            total_news = cursor.fetchone()[0]
            
            # 获取来源统计
            cursor.execute("SELECT source, COUNT(*) FROM news GROUP BY source")
            sources = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 获取分类统计
            cursor.execute("SELECT category, COUNT(*) FROM news WHERE category IS NOT NULL GROUP BY category")
            categories = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 获取日期范围
            cursor.execute("SELECT MIN(pub_time), MAX(pub_time) FROM news")
            date_range = cursor.fetchone()
            
            # 获取数据库文件大小
            file_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
            
            conn.close()
            
            return {
                'total_news': total_news,
                'sources': sources,
                'categories': categories,
                'date_range': date_range,
                'file_size': f"{file_size:.2f} MB"
            }
        except Exception as e:
            logger.error(f"获取数据库统计信息失败: {str(e)}")
            return {
                'error': str(e)
            }
    
    def merge_all_databases(self):
        """
        合并所有来源数据库到主数据库
        
        Returns:
            bool: 是否成功
        """
        try:
            # 备份主数据库
            self.backup_database('finance_news.db')
            
            # 获取所有来源数据库
            source_dbs = [f for f in self.list_databases() if f != 'finance_news.db']
            
            if not source_dbs:
                logger.info("没有找到需要合并的数据库")
                return True
            
            # 合并数据库
            return self.main_db.merge_databases()
            
        except Exception as e:
            logger.error(f"合并数据库失败: {str(e)}")
            return False
    
    def backup_database(self, db_file):
        """
        备份数据库
        
        Args:
            db_file: 数据库文件名
            
        Returns:
            str: 备份文件路径，失败返回None
        """
        try:
            db_path = os.path.join(self.db_dir, db_file)
            
            if not os.path.exists(db_path):
                logger.error(f"数据库文件不存在: {db_path}")
                return None
            
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(self.backup_dir, f"{db_file}_{timestamp}.bak")
            
            # 复制数据库文件
            shutil.copy2(db_path, backup_file)
            
            logger.info(f"数据库备份成功: {backup_file}")
            return backup_file
            
        except Exception as e:
            logger.error(f"数据库备份失败: {str(e)}")
            return None
    
    def restore_database(self, backup_file, db_file):
        """
        从备份恢复数据库
        
        Args:
            backup_file: 备份文件名
            db_file: 目标数据库文件名
            
        Returns:
            bool: 是否成功
        """
        try:
            backup_path = os.path.join(self.backup_dir, backup_file)
            db_path = os.path.join(self.db_dir, db_file)
            
            if not os.path.exists(backup_path):
                logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            # 如果目标数据库存在，先备份
            if os.path.exists(db_path):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                temp_backup = os.path.join(self.backup_dir, f"{db_file}_before_restore_{timestamp}.bak")
                shutil.copy2(db_path, temp_backup)
                logger.info(f"目标数据库已备份: {temp_backup}")
            
            # 复制备份文件到目标数据库
            shutil.copy2(backup_path, db_path)
            
            logger.info(f"数据库恢复成功: {db_file}")
            return True
            
        except Exception as e:
            logger.error(f"数据库恢复失败: {str(e)}")
            return False
    
    def delete_database(self, db_file):
        """
        删除数据库
        
        Args:
            db_file: 数据库文件名
            
        Returns:
            bool: 是否成功
        """
        try:
            db_path = os.path.join(self.db_dir, db_file)
            
            if not os.path.exists(db_path):
                logger.error(f"数据库文件不存在: {db_path}")
                return False
            
            # 先备份
            self.backup_database(db_file)
            
            # 删除文件
            os.remove(db_path)
            
            logger.info(f"数据库删除成功: {db_file}")
            return True
            
        except Exception as e:
            logger.error(f"数据库删除失败: {str(e)}")
            return False
    
    def optimize_database(self, db_file=None):
        """
        优化数据库
        
        Args:
            db_file: 数据库文件名，如果为None则优化所有数据库
            
        Returns:
            bool: 是否成功
        """
        try:
            if db_file:
                # 优化指定数据库
                db_path = os.path.join(self.db_dir, db_file)
                return self._optimize_single_db(db_path)
            else:
                # 优化所有数据库
                success = True
                for db_file in self.list_databases():
                    db_path = os.path.join(self.db_dir, db_file)
                    if not self._optimize_single_db(db_path):
                        success = False
                return success
            
        except Exception as e:
            logger.error(f"优化数据库失败: {str(e)}")
            return False
    
    def _optimize_single_db(self, db_path):
        """
        优化单个数据库
        
        Args:
            db_path: 数据库路径
            
        Returns:
            bool: 是否成功
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 执行VACUUM操作
            cursor.execute("VACUUM")
            
            # 执行ANALYZE操作
            cursor.execute("ANALYZE")
            
            conn.commit()
            conn.close()
            
            logger.info(f"数据库优化成功: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"优化数据库失败: {db_path}, 错误: {str(e)}")
            return False
    
    def export_data(self, db_file, output_file, format='json'):
        """
        导出数据库数据
        
        Args:
            db_file: 数据库文件名
            output_file: 输出文件路径
            format: 导出格式，支持json和csv
            
        Returns:
            bool: 是否成功
        """
        try:
            db_path = os.path.join(self.db_dir, db_file)
            
            if not os.path.exists(db_path):
                logger.error(f"数据库文件不存在: {db_path}")
                return False
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 查询所有新闻数据
            cursor.execute("SELECT * FROM news")
            columns = [col[0] for col in cursor.description]
            news_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            
            # 导出数据
            if format.lower() == 'json':
                import json
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(news_data, f, ensure_ascii=False, indent=2)
            elif format.lower() == 'csv':
                import csv
                with open(output_file, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=columns)
                    writer.writeheader()
                    writer.writerows(news_data)
            else:
                logger.error(f"不支持的导出格式: {format}")
                return False
            
            logger.info(f"数据导出成功: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"导出数据失败: {str(e)}")
            return False
    
    def import_data(self, db_file, input_file, format='json'):
        """
        导入数据到数据库
        
        Args:
            db_file: 数据库文件名
            input_file: 输入文件路径
            format: 导入格式，支持json和csv
            
        Returns:
            bool: 是否成功
        """
        try:
            db_path = os.path.join(self.db_dir, db_file)
            
            # 读取数据
            if format.lower() == 'json':
                import json
                with open(input_file, 'r', encoding='utf-8') as f:
                    news_data = json.load(f)
            elif format.lower() == 'csv':
                import csv
                news_data = []
                with open(input_file, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        news_data.append(row)
            else:
                logger.error(f"不支持的导入格式: {format}")
                return False
            
            # 连接数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 获取已存在的新闻ID
            cursor.execute("SELECT id FROM news")
            existing_ids = {row[0] for row in cursor.fetchall()}
            
            # 导入数据
            imported_count = 0
            for news_item in news_data:
                if news_item['id'] not in existing_ids:
                    # 构建插入语句
                    fields = list(news_item.keys())
                    placeholders = ', '.join(['?'] * len(fields))
                    fields_str = ', '.join(fields)
                    values = list(news_item.values())
                    
                    sql = f"INSERT INTO news ({fields_str}) VALUES ({placeholders})"
                    cursor.execute(sql, values)
                    
                    existing_ids.add(news_item['id'])
                    imported_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"数据导入成功，共导入 {imported_count} 条新闻")
            return True
            
        except Exception as e:
            logger.error(f"导入数据失败: {str(e)}")
            return False

# 命令行工具
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库管理工具")
    
    # 添加子命令
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 列出数据库
    list_parser = subparsers.add_parser("list", help="列出所有数据库")
    
    # 获取数据库统计信息
    stats_parser = subparsers.add_parser("stats", help="获取数据库统计信息")
    stats_parser.add_argument("--db", help="数据库文件名")
    
    # 合并数据库
    merge_parser = subparsers.add_parser("merge", help="合并所有来源数据库到主数据库")
    
    # 备份数据库
    backup_parser = subparsers.add_parser("backup", help="备份数据库")
    backup_parser.add_argument("db", help="数据库文件名")
    
    # 恢复数据库
    restore_parser = subparsers.add_parser("restore", help="从备份恢复数据库")
    restore_parser.add_argument("backup", help="备份文件名")
    restore_parser.add_argument("db", help="目标数据库文件名")
    
    # 删除数据库
    delete_parser = subparsers.add_parser("delete", help="删除数据库")
    delete_parser.add_argument("db", help="数据库文件名")
    
    # 优化数据库
    optimize_parser = subparsers.add_parser("optimize", help="优化数据库")
    optimize_parser.add_argument("--db", help="数据库文件名")
    
    # 导出数据
    export_parser = subparsers.add_parser("export", help="导出数据库数据")
    export_parser.add_argument("db", help="数据库文件名")
    export_parser.add_argument("output", help="输出文件路径")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json", help="导出格式")
    
    # 导入数据
    import_parser = subparsers.add_parser("import", help="导入数据到数据库")
    import_parser.add_argument("db", help="数据库文件名")
    import_parser.add_argument("input", help="输入文件路径")
    import_parser.add_argument("--format", choices=["json", "csv"], default="json", help="导入格式")
    
    # 解析参数
    args = parser.parse_args()
    
    # 创建数据库管理器
    db_manager = DatabaseManager()
    
    # 执行命令
    if args.command == "list":
        db_files = db_manager.list_databases()
        print(f"找到 {len(db_files)} 个数据库文件:")
        for db_file in db_files:
            print(f"- {db_file}")
    
    elif args.command == "stats":
        stats = db_manager.get_database_stats(args.db)
        import json
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    elif args.command == "merge":
        success = db_manager.merge_all_databases()
        print(f"合并数据库{'成功' if success else '失败'}")
    
    elif args.command == "backup":
        backup_file = db_manager.backup_database(args.db)
        if backup_file:
            print(f"数据库备份成功: {backup_file}")
        else:
            print("数据库备份失败")
    
    elif args.command == "restore":
        success = db_manager.restore_database(args.backup, args.db)
        print(f"数据库恢复{'成功' if success else '失败'}")
    
    elif args.command == "delete":
        success = db_manager.delete_database(args.db)
        print(f"数据库删除{'成功' if success else '失败'}")
    
    elif args.command == "optimize":
        success = db_manager.optimize_database(args.db)
        print(f"数据库优化{'成功' if success else '失败'}")
    
    elif args.command == "export":
        success = db_manager.export_data(args.db, args.output, args.format)
        print(f"数据导出{'成功' if success else '失败'}")
    
    elif args.command == "import":
        success = db_manager.import_data(args.db, args.input, args.format)
        print(f"数据导入{'成功' if success else '失败'}")
    
    else:
        parser.print_help() 