#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
爬虫修复工具 - 解决爬虫相关问题
1. 合并东方财富原版和简化版爬虫
2. 修复腾讯爬虫的数据保存问题
3. 清理重复的数据库文件
"""

import os
import sys
import sqlite3
import shutil
from datetime import datetime
import logging

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('crawler_fix')

class CrawlerFixer:
    """爬虫修复工具类"""
    
    def __init__(self, db_dir=None):
        """
        初始化爬虫修复工具
        
        Args:
            db_dir: 数据库目录路径，如果为None则使用默认路径
        """
        if db_dir is None:
            self.db_dir = os.path.join(os.getcwd(), 'data', 'db')
        else:
            self.db_dir = db_dir
        
        # 确保数据库目录存在
        if not os.path.exists(self.db_dir):
            logger.error(f"数据库目录不存在: {self.db_dir}")
            raise FileNotFoundError(f"数据库目录不存在: {self.db_dir}")
        
        logger.info(f"初始化爬虫修复工具，数据库目录: {self.db_dir}")
    
    def merge_eastmoney_databases(self):
        """
        合并东方财富网的两个数据库
        
        将 "东方财富网.db" 中的数据合并到 "东方财富.db" 中，然后删除 "东方财富网.db"
        """
        source_db_path = os.path.join(self.db_dir, '东方财富网.db')
        target_db_path = os.path.join(self.db_dir, '东方财富.db')
        
        # 检查源数据库和目标数据库是否存在
        if not os.path.exists(source_db_path):
            logger.warning(f"源数据库不存在: {source_db_path}")
            return False
        
        if not os.path.exists(target_db_path):
            logger.warning(f"目标数据库不存在: {target_db_path}")
            return False
        
        logger.info(f"开始合并数据库: {source_db_path} -> {target_db_path}")
        
        try:
            # 连接源数据库
            source_conn = sqlite3.connect(source_db_path)
            source_cursor = source_conn.cursor()
            
            # 连接目标数据库
            target_conn = sqlite3.connect(target_db_path)
            target_cursor = target_conn.cursor()
            
            # 获取源数据库中的所有新闻
            source_cursor.execute("SELECT * FROM news")
            news_data = source_cursor.fetchall()
            
            # 获取目标数据库中新闻表的列名
            target_cursor.execute("PRAGMA table_info(news)")
            columns_info = target_cursor.fetchall()
            column_names = [column[1] for column in columns_info]
            
            # 构建INSERT语句
            columns_str = ', '.join(column_names)
            placeholders = ', '.join(['?' for _ in column_names])
            insert_sql = f"INSERT OR IGNORE INTO news ({columns_str}) VALUES ({placeholders})"
            
            # 插入数据前获取目标数据库中的新闻数量
            target_cursor.execute("SELECT COUNT(*) FROM news")
            before_count = target_cursor.fetchone()[0]
            
            # 遍历源数据库中的新闻并插入到目标数据库
            merged_count = 0
            for news in news_data:
                try:
                    # 确保数据长度与列数相同
                    if len(news) != len(column_names):
                        # 如果列数不匹配，尝试创建一个适当长度的元组
                        news_dict = {}
                        for i, column in enumerate(column_names):
                            if i < len(news):
                                news_dict[column] = news[i]
                            else:
                                news_dict[column] = None
                        
                        # 使用新的字典构建值元组
                        values = tuple(news_dict.get(column) for column in column_names)
                    else:
                        values = news
                    
                    # 插入数据
                    target_cursor.execute(insert_sql, values)
                    merged_count += 1
                except Exception as e:
                    logger.error(f"插入新闻失败: {str(e)}")
            
            # 提交事务
            target_conn.commit()
            
            # 获取合并后的新闻数量
            target_cursor.execute("SELECT COUNT(*) FROM news")
            after_count = target_cursor.fetchone()[0]
            
            # 关闭数据库连接
            source_conn.close()
            target_conn.close()
            
            logger.info(f"数据库合并完成，共处理 {merged_count} 条新闻，目标数据库新增 {after_count - before_count} 条")
            
            # 创建源数据库的备份
            backup_path = os.path.join(self.db_dir, 'backup', f'东方财富网_backup_{datetime.now().strftime("%Y%m%d%H%M%S")}.db')
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copy2(source_db_path, backup_path)
            logger.info(f"已创建源数据库备份: {backup_path}")
            
            # 删除源数据库
            os.remove(source_db_path)
            logger.info(f"已删除源数据库: {source_db_path}")
            
            return True
        
        except Exception as e:
            logger.error(f"合并数据库失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def fix_tencent_crawler(self):
        """
        修复腾讯爬虫数据保存问题
        
        检查腾讯爬虫的数据库表结构，确保news表有正确的字段
        """
        db_path = os.path.join(self.db_dir, '腾讯财经.db')
        
        if not os.path.exists(db_path):
            logger.warning(f"腾讯财经数据库不存在: {db_path}")
            return False
        
        logger.info(f"开始修复腾讯财经爬虫数据库: {db_path}")
        
        try:
            # 连接数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查news表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
            if not cursor.fetchone():
                logger.info("腾讯财经数据库中不存在news表，创建表...")
                # 创建news表
                cursor.execute('''
                CREATE TABLE news (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    content TEXT,
                    pub_time TEXT,
                    author TEXT,
                    source TEXT,
                    url TEXT UNIQUE,
                    keywords TEXT,
                    sentiment REAL,
                    crawl_time TEXT,
                    category TEXT,
                    images TEXT,
                    related_stocks TEXT,
                    content_html TEXT,
                    classification TEXT
                )
                ''')
                conn.commit()
                logger.info("成功创建news表")
            else:
                # 检查表结构
                cursor.execute("PRAGMA table_info(news)")
                columns = {column[1] for column in cursor.fetchall()}
                
                # 缺失的列
                missing_columns = []
                for column in ['id', 'title', 'content', 'pub_time', 'author', 'source', 'url', 
                              'keywords', 'sentiment', 'crawl_time', 'category', 'images', 
                              'related_stocks', 'content_html', 'classification']:
                    if column not in columns:
                        missing_columns.append(column)
                
                # 添加缺失的列
                if missing_columns:
                    logger.info(f"发现缺失的列: {missing_columns}")
                    for column in missing_columns:
                        # 为不同类型的列设置不同的类型
                        if column in ['sentiment']:
                            column_type = 'REAL'
                        else:
                            column_type = 'TEXT'
                        
                        try:
                            cursor.execute(f"ALTER TABLE news ADD COLUMN {column} {column_type}")
                        except sqlite3.OperationalError as e:
                            if 'duplicate column name' in str(e).lower():
                                logger.warning(f"列已存在: {column}")
                            else:
                                raise
                    
                    conn.commit()
                    logger.info("已添加缺失的列")
                else:
                    logger.info("表结构正确，无需修复")
            
            # 关闭数据库连接
            conn.close()
            logger.info("腾讯财经爬虫数据库修复完成")
            
            return True
        
        except Exception as e:
            logger.error(f"修复腾讯财经爬虫数据库失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def merge_eastmoney_crawlers(self):
        """
        合并东方财富原版和简化版爬虫
        
        修改东方财富简化版爬虫，让它使用与原版爬虫相同的数据库
        """
        logger.info("开始修复东方财富爬虫代码...")
        
        # 路径
        eastmoney_simple_path = os.path.join(os.getcwd(), 'app', 'crawlers', 'eastmoney_simple.py')
        
        if not os.path.exists(eastmoney_simple_path):
            logger.warning(f"东方财富简化版爬虫文件不存在: {eastmoney_simple_path}")
            return False
        
        try:
            # 读取文件内容
            with open(eastmoney_simple_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换source属性
            if 'self.source = "东方财富网"' in content:
                content = content.replace('self.source = "东方财富网"', 'self.source = "东方财富"')
                logger.info("已将source属性从'东方财富网'修改为'东方财富'")
            
            # 保存修改后的文件
            with open(eastmoney_simple_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.info("东方财富简化版爬虫修复完成")
            return True
        
        except Exception as e:
            logger.error(f"修复东方财富简化版爬虫失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def run_all_fixes(self):
        """
        运行所有修复任务
        
        Returns:
            dict: 修复结果
        """
        results = {}
        
        # 1. 修复东方财富简化版爬虫
        logger.info("1. 开始修复东方财富简化版爬虫...")
        results['fix_eastmoney_crawler'] = self.merge_eastmoney_crawlers()
        
        # 2. 合并东方财富数据库
        logger.info("2. 开始合并东方财富数据库...")
        results['merge_eastmoney_db'] = self.merge_eastmoney_databases()
        
        # 3. 修复腾讯爬虫
        logger.info("3. 开始修复腾讯爬虫数据库...")
        results['fix_tencent_crawler'] = self.fix_tencent_crawler()
        
        # 输出总结
        logger.info("\n===== 修复任务执行完成 =====")
        for task, result in results.items():
            logger.info(f"{task}: {'成功' if result else '失败'}")
        
        return results

# 主函数
def main():
    """主函数"""
    print("=" * 60)
    print(" 爬虫修复工具 ".center(60, '='))
    print("=" * 60)
    print("本工具用于修复以下问题:")
    print("1. 合并东方财富原版和简化版爬虫")
    print("2. 修复腾讯爬虫数据保存问题")
    print("3. 清理重复的数据库文件")
    print("=" * 60)
    
    try:
        # 获取数据库目录
        db_dir = os.path.join(os.getcwd(), 'data', 'db')
        
        # 初始化修复工具
        fixer = CrawlerFixer(db_dir)
        
        # 运行所有修复任务
        results = fixer.run_all_fixes()
        
        # 总结
        print("\n" + "=" * 60)
        print(" 修复任务执行结果 ".center(60, '='))
        print("=" * 60)
        
        for task, result in results.items():
            status = "成功" if result else "失败"
            print(f"{task}: {status}")
        
        print("=" * 60)
        print("修复完成！请重启应用程序以应用更改。")
        
    except Exception as e:
        logger.error(f"修复过程发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"\n错误: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 