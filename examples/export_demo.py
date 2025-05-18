#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新闻数据导出示例脚本
演示如何从爬虫数据库中导出数据到CSV、Excel、JSON等格式
"""

import os
import argparse
import pandas as pd
import sqlite3
import json
from datetime import datetime

from app.utils.logger import get_logger

# 初始化日志记录器
logger = get_logger('export_demo')

class NewsExporter:
    """新闻数据导出器"""
    
    def __init__(self, db_path, output_dir='data/exports'):
        """
        初始化导出器
        
        Args:
            db_path: 数据库路径
            output_dir: 输出目录
        """
        self.db_path = db_path
        self.output_dir = output_dir
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建文件名前缀（基于数据库名称）
        self.prefix = os.path.splitext(os.path.basename(db_path))[0]
        
    def _get_connection(self):
        """获取数据库连接"""
        try:
            conn = sqlite3.connect(self.db_path)
            # 设置行工厂，返回字典而不是元组
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"连接数据库 {self.db_path} 失败: {str(e)}")
            raise
    
    def get_all_articles(self):
        """从数据库获取所有文章"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM articles")
            articles = [dict(row) for row in cursor.fetchall()]
            logger.info(f"从数据库 {self.db_path} 中获取了 {len(articles)} 篇文章")
            return articles
        except sqlite3.Error as e:
            logger.error(f"查询数据库 {self.db_path} 失败: {str(e)}")
            raise
        finally:
            conn.close()
    
    def get_articles_by_date(self, start_date=None, end_date=None):
        """
        按日期范围获取文章
        
        Args:
            start_date: 开始日期字符串 (YYYY-MM-DD)
            end_date: 结束日期字符串 (YYYY-MM-DD)
            
        Returns:
            符合条件的文章列表
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM articles WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND publish_date >= ?"
                params.append(start_date)
                
            if end_date:
                query += " AND publish_date <= ?"
                params.append(end_date)
                
            query += " ORDER BY publish_date DESC"
            
            cursor.execute(query, params)
            articles = [dict(row) for row in cursor.fetchall()]
            
            date_range = ""
            if start_date and end_date:
                date_range = f"在 {start_date} 到 {end_date} 之间"
            elif start_date:
                date_range = f"在 {start_date} 之后"
            elif end_date:
                date_range = f"在 {end_date} 之前"
                
            logger.info(f"从数据库 {self.db_path} 中获取了 {len(articles)} 篇{date_range}的文章")
            return articles
        except sqlite3.Error as e:
            logger.error(f"按日期查询数据库 {self.db_path} 失败: {str(e)}")
            raise
        finally:
            conn.close()
    
    def export_to_csv(self, articles=None, filename=None):
        """
        导出文章到CSV文件
        
        Args:
            articles: 要导出的文章列表，如果为None则导出所有文章
            filename: 输出文件名，如果为None则自动生成
            
        Returns:
            导出文件的路径
        """
        if articles is None:
            articles = self.get_all_articles()
            
        if not articles:
            logger.warning("没有找到要导出的文章")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.prefix}_{timestamp}.csv"
            
        output_path = os.path.join(self.output_dir, filename)
        
        try:
            df = pd.DataFrame(articles)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"成功导出 {len(articles)} 篇文章到 {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"导出到CSV失败: {str(e)}")
            raise
    
    def export_to_excel(self, articles=None, filename=None):
        """
        导出文章到Excel文件
        
        Args:
            articles: 要导出的文章列表，如果为None则导出所有文章
            filename: 输出文件名，如果为None则自动生成
            
        Returns:
            导出文件的路径
        """
        if articles is None:
            articles = self.get_all_articles()
            
        if not articles:
            logger.warning("没有找到要导出的文章")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.prefix}_{timestamp}.xlsx"
            
        output_path = os.path.join(self.output_dir, filename)
        
        try:
            df = pd.DataFrame(articles)
            df.to_excel(output_path, index=False, engine='openpyxl')
            logger.info(f"成功导出 {len(articles)} 篇文章到 {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"导出到Excel失败: {str(e)}")
            raise
    
    def export_to_json(self, articles=None, filename=None, pretty=True):
        """
        导出文章到JSON文件
        
        Args:
            articles: 要导出的文章列表，如果为None则导出所有文章
            filename: 输出文件名，如果为None则自动生成
            pretty: 是否美化JSON输出
            
        Returns:
            导出文件的路径
        """
        if articles is None:
            articles = self.get_all_articles()
            
        if not articles:
            logger.warning("没有找到要导出的文章")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.prefix}_{timestamp}.json"
            
        output_path = os.path.join(self.output_dir, filename)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(articles, f, ensure_ascii=False, indent=2)
                else:
                    json.dump(articles, f, ensure_ascii=False)
                    
            logger.info(f"成功导出 {len(articles)} 篇文章到 {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"导出到JSON失败: {str(e)}")
            raise
    
    def export_all_formats(self, articles=None, base_filename=None):
        """
        将文章导出为所有支持的格式
        
        Args:
            articles: 要导出的文章列表，如果为None则导出所有文章
            base_filename: 基础文件名，如果为None则自动生成
            
        Returns:
            导出文件路径的字典
        """
        if articles is None:
            articles = self.get_all_articles()
            
        if not articles:
            logger.warning("没有找到要导出的文章")
            return {}
        
        if base_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"{self.prefix}_{timestamp}"
        
        results = {}
        
        # 导出CSV
        csv_filename = f"{base_filename}.csv"
        results['csv'] = self.export_to_csv(articles, csv_filename)
        
        # 导出Excel
        excel_filename = f"{base_filename}.xlsx"
        results['excel'] = self.export_to_excel(articles, excel_filename)
        
        # 导出JSON
        json_filename = f"{base_filename}.json"
        results['json'] = self.export_to_json(articles, json_filename)
        
        return results


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description="财经新闻数据导出工具")
    parser.add_argument("db_path", help="SQLite数据库文件路径")
    parser.add_argument("--format", choices=['csv', 'excel', 'json', 'all'], default='all',
                      help="导出格式 (默认: all)")
    parser.add_argument("--output-dir", default='data/exports',
                      help="导出目录 (默认: data/exports)")
    parser.add_argument("--start-date", help="开始日期 (YYYY-MM-DD格式)")
    parser.add_argument("--end-date", help="结束日期 (YYYY-MM-DD格式)")
    
    args = parser.parse_args()
    
    try:
        # 初始化导出器
        exporter = NewsExporter(args.db_path, args.output_dir)
        
        # 按日期范围获取文章
        articles = exporter.get_articles_by_date(args.start_date, args.end_date)
        
        if not articles:
            print("没有找到符合条件的文章")
            return
        
        print(f"\n找到 {len(articles)} 篇符合条件的文章")
        
        # 根据指定格式导出
        if args.format == 'csv':
            output_path = exporter.export_to_csv(articles)
            print(f"已导出到CSV: {output_path}")
        elif args.format == 'excel':
            output_path = exporter.export_to_excel(articles)
            print(f"已导出到Excel: {output_path}")
        elif args.format == 'json':
            output_path = exporter.export_to_json(articles)
            print(f"已导出到JSON: {output_path}")
        else:  # 'all'
            results = exporter.export_all_formats(articles)
            print("\n导出完成:")
            for fmt, path in results.items():
                print(f"- {fmt.upper()}: {path}")
                
    except Exception as e:
        print(f"导出过程中发生错误: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    main() 