#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
创建测试用的来源专用数据库
"""

import os
import sys
import sqlite3
import json
from datetime import datetime, timedelta
import random

# 将项目根目录添加到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.config import get_settings

def create_table(conn):
    """创建数据库表"""
    cursor = conn.cursor()
    
    # 创建新闻表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            content_html TEXT,
            pub_time TEXT,
            author TEXT,
            source TEXT,
            url TEXT UNIQUE,
            keywords TEXT,
            images TEXT,
            related_stocks TEXT,
            sentiment TEXT,
            classification TEXT,
            category TEXT,
            crawl_time TEXT
        )
    ''')
    
    # 创建关键词表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE,
            count INTEGER DEFAULT 1,
            last_updated TEXT
        )
    ''')
    
    # 创建新闻-关键词关系表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_keywords (
            news_id TEXT,
            keyword_id INTEGER,
            PRIMARY KEY (news_id, keyword_id),
            FOREIGN KEY (news_id) REFERENCES news(id) ON DELETE CASCADE,
            FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    
def insert_test_news(conn, source_name, num_news=10):
    """插入测试新闻"""
    cursor = conn.cursor()
    
    # 定义测试数据
    categories = ["财经", "股票", "基金", "科技", "消费", "房产", "汽车"]
    keywords_list = [["经济", "市场", "股票"], ["投资", "收益", "风险"], ["科技", "创新", "AI"], ["房产", "地产", "楼市"]]
    
    # 获取当前时间
    now = datetime.now()
    
    # 插入测试新闻
    for i in range(num_news):
        # 生成ID
        news_id = f"{source_name.lower().replace(' ', '_')}_{i+1}"
        
        # 生成标题和内容
        title = f"{source_name}测试新闻标题 {i+1}: 关于{'市场' if i % 2 == 0 else '财经'}的重要信息"
        content = f"""这是{source_name}的测试新闻内容 {i+1}。
        本文提供了关于{'市场' if i % 2 == 0 else '财经'}的重要信息，希望对读者有所帮助。
        这只是一个测试数据，没有实际的新闻价值。"""
        
        # 生成URL
        url = f"http://www.{source_name.lower().replace(' ', '')}.com/news/{news_id}"
        
        # 生成发布时间（从当前时间起向前随机1-30天）
        random_days = random.randint(1, 30)
        pub_time = (now - timedelta(days=random_days)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 选择分类和关键词
        category = random.choice(categories)
        keywords = random.choice(keywords_list)
        
        # 插入新闻
        cursor.execute('''
            INSERT OR IGNORE INTO news (
                id, title, content, pub_time, author, source, url, keywords, category, crawl_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            news_id, 
            title, 
            content,
            pub_time,
            f"{source_name}作者",
            source_name,
            url,
            json.dumps(keywords),
            category,
            now.strftime('%Y-%m-%d %H:%M:%S')
        ))
    
    conn.commit()
    print(f"已在 {source_name}.db 中插入 {num_news} 条测试新闻")

def main():
    """主函数"""
    settings = get_settings()
    
    # 获取数据库目录
    db_dir = settings.get('DB_DIR')
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        print(f"已创建数据库目录: {db_dir}")
    
    # 要创建的测试数据库列表
    sources = ["腾讯财经", "新浪财经", "东方财富", "网易财经", "凤凰财经"]
    
    # 为每个来源创建数据库
    for source in sources:
        try:
            # 数据库路径
            db_path = os.path.join(db_dir, f"{source}.db")
            
            # 删除已存在的数据库文件（重新创建）
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                    print(f"已删除已存在的数据库文件: {db_path}")
                except Exception as e:
                    print(f"删除数据库文件失败: {db_path}, 错误: {str(e)}")
                    continue
            
            # 连接数据库
            conn = sqlite3.connect(db_path)
            
            # 创建表
            create_table(conn)
            
            # 插入测试新闻（固定数量，避免随机失败）
            insert_test_news(conn, source, num_news=10)
            
            # 关闭连接
            conn.close()
            
            print(f"已创建测试数据库: {db_path}")
        except Exception as e:
            print(f"创建数据库 {source}.db 失败: {str(e)}")
    
    print("\n所有测试数据库创建完成！")
    
    # 列出所有创建的数据库文件
    print("\n数据库目录内容:")
    try:
        for filename in os.listdir(db_dir):
            if filename.endswith('.db'):
                file_path = os.path.join(db_dir, filename)
                file_size = os.path.getsize(file_path) / 1024  # KB
                print(f"  - {filename} ({file_size:.1f} KB)")
    except Exception as e:
        print(f"列出数据库文件失败: {str(e)}")

if __name__ == "__main__":
    main() 