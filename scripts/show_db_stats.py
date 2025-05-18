#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库统计脚本 - 显示各个数据库中的新闻计数和来源分布情况
"""

import os
import sys
import glob
import sqlite3
import argparse
from datetime import datetime, timedelta

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 获取数据库目录
def get_db_dir():
    """获取数据库目录"""
    try:
        from app.config import get_settings
        settings = get_settings()
        db_dir = settings.get('DB_DIR', os.path.join(os.getcwd(), 'data', 'db'))
    except ImportError:
        db_dir = os.path.join(os.getcwd(), 'data', 'db')
    
    if not os.path.exists(db_dir):
        print(f"数据库目录不存在: {db_dir}")
        sys.exit(1)
    
    return db_dir

def get_db_count(db_path):
    """获取数据库中的新闻数量"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM news")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"查询数据库失败: {db_path} - {str(e)}")
        return 0

def get_source_distribution(db_path):
    """获取数据库中的来源分布"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT source, COUNT(*) FROM news GROUP BY source ORDER BY COUNT(*) DESC")
        sources = cursor.fetchall()
        conn.close()
        return sources
    except Exception as e:
        print(f"查询数据库来源分布失败: {db_path} - {str(e)}")
        return []

def get_date_distribution(db_path):
    """获取数据库中的日期分布 (最近7天)"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取当前日期
        today = datetime.now().date()
        
        # 创建日期范围
        date_counts = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            cursor.execute("SELECT COUNT(*) FROM news WHERE pub_time LIKE ?", (f"{date_str}%",))
            count = cursor.fetchone()[0]
            date_counts.append((date.strftime('%m-%d'), count))
        
        conn.close()
        return date_counts
    except Exception as e:
        print(f"查询数据库日期分布失败: {db_path} - {str(e)}")
        return []

def set_console_width():
    """设置控制台宽度"""
    try:
        # 尝试设置控制台宽度为120个字符
        os.system('mode con: cols=120 lines=50')
        print("已设置控制台宽度为120字符")
    except Exception:
        # 忽略错误，不影响主要功能
        pass

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库统计工具 - 显示各个数据库中的新闻计数和来源分布情况")
    parser.add_argument("-o", "--output", help="输出结果到文件")
    args = parser.parse_args()
    
    # 如果指定了输出文件，同时将输出重定向到文件
    if args.output:
        # 保存原始的标准输出
        original_stdout = sys.stdout
        # 打开输出文件
        f = open(args.output, 'w', encoding='utf-8')
        # 重定向标准输出到文件
        sys.stdout = f
    
    # 尝试设置控制台宽度
    set_console_width()
    
    print("\n" + "=" * 80)
    print("数据库统计信息查看工具".center(80))
    print("=" * 80 + "\n")
    
    db_dir = get_db_dir()
    print(f"数据库目录: {db_dir}\n")
    
    # 获取所有数据库文件路径
    db_files = glob.glob(os.path.join(db_dir, "*.db"))
    db_files = [f for f in db_files if os.path.basename(f) != "user_preferences.db"]
    
    print(f"找到 {len(db_files)} 个数据库文件:")
    for db_file in db_files:
        print(f"  - {os.path.basename(db_file)}")
    print()
    
    # 主数据库路径
    main_db_path = os.path.join(db_dir, "finance_news.db")
    
    # 首先输出主数据库信息
    if main_db_path in db_files:
        print("=" * 80)
        print(f"主数据库: {os.path.basename(main_db_path)}")
        print(f"新闻数量: {get_db_count(main_db_path)}")
        
        # 来源分布
        print("\n来源分布:")
        sources = get_source_distribution(main_db_path)
        for source, count in sources:
            print(f"  {source or '未知'}: {count}")
        
        # 日期分布
        print("\n最近7天日期分布:")
        date_counts = get_date_distribution(main_db_path)
        for date, count in date_counts:
            print(f"  {date}: {count}")
        
        # 从列表中移除主数据库
        db_files.remove(main_db_path)
    
    # 输出其他数据库信息
    total_source_news = 0
    for db_path in db_files:
        db_name = os.path.basename(db_path)
        print("\n" + "=" * 80)
        print(f"数据库: {db_name}")
        news_count = get_db_count(db_path)
        total_source_news += news_count
        print(f"新闻数量: {news_count}")
        
        # 日期分布
        print("\n最近7天日期分布:")
        date_counts = get_date_distribution(db_path)
        for date, count in date_counts:
            print(f"  {date}: {count}")
    
    # 显示总结信息
    print("\n" + "=" * 80)
    print("数据统计总结".center(80))
    print("=" * 80)
    main_db_count = get_db_count(main_db_path) if os.path.exists(main_db_path) else 0
    print(f"主数据库新闻总数: {main_db_count}")
    print(f"所有源数据库新闻总数: {total_source_news}")
    
    # 检查同步状态
    print("\n数据同步状态:")
    if main_db_count >= total_source_news:
        print("✓ 主数据库包含了所有源数据库的新闻")
    else:
        print("✗ 主数据库未包含所有源数据库的新闻，请运行同步脚本")
    
    print("\n" + "=" * 80)
    
    # 如果重定向了输出，恢复原来的标准输出并关闭文件
    if args.output:
        sys.stdout = original_stdout
        f.close()
        print(f"统计结果已保存到文件: {args.output}")

if __name__ == "__main__":
    main() 