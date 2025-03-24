#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库合并工具 - 将未知来源数据库中的数据合并到对应的专用数据库

用法:
python scripts/merge_unknown_source.py

功能:
1. 检查是否存在未知来源.db文件
2. 如果存在，分析其中的新闻内容，尝试匹配到正确的来源
3. 将数据转移到对应的来源数据库或主数据库
4. 完成后可选择是否删除未知来源数据库
"""

import sqlite3
import os
import re
import time
import shutil
from datetime import datetime

# 数据库路径
db_dir = 'data/db'
unknown_db_path = os.path.join(db_dir, '未知来源.db')
main_db_path = os.path.join(db_dir, 'finance_news.db')

# 来源专用数据库列表
source_dbs = {
    '腾讯财经': os.path.join(db_dir, '腾讯财经.db'),
    '新浪财经': os.path.join(db_dir, '新浪财经.db'),
    '东方财富': os.path.join(db_dir, '东方财富.db'),
    '网易财经': os.path.join(db_dir, '网易财经.db'),
    '凤凰财经': os.path.join(db_dir, '凤凰财经.db')
}

# URL模式匹配规则
url_patterns = {
    'finance.sina.com.cn': '新浪财经',
    'sina.com.cn/finance': '新浪财经',
    'money.163.com': '网易财经',
    'finance.qq.com': '腾讯财经',
    'finance.ifeng.com': '凤凰财经',
    'eastmoney.com': '东方财富',
    'em.com.cn': '东方财富'
}

def identify_source_by_url(url):
    """通过URL识别新闻来源"""
    if not url:
        return None
    
    for pattern, source in url_patterns.items():
        if pattern in url:
            return source
    
    return None

def identify_source_by_content(title, content):
    """通过内容识别新闻来源"""
    # 简单的关键词匹配逻辑
    keywords = {
        '新浪财经': ['新浪财经', '新浪网'],
        '腾讯财经': ['腾讯财经', '财经腾讯网'],
        '东方财富': ['东方财富', '东财'],
        '网易财经': ['网易财经', '网易财报'],
        '凤凰财经': ['凤凰财经', '凤凰网财经']
    }
    
    # 合并标题和内容以增加匹配机会
    full_text = f"{title} {content if content else ''}"
    
    for source, source_keywords in keywords.items():
        for keyword in source_keywords:
            if keyword in full_text:
                return source
    
    return None

def backup_database(db_path):
    """创建数据库备份"""
    if not os.path.exists(db_path):
        return False
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    backup_path = f"{db_path}.{timestamp}.bak"
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"已创建数据库备份: {backup_path}")
        return True
    except Exception as e:
        print(f"创建备份失败: {e}")
        return False

def merge_to_source_db(news_data, columns, source):
    """将新闻数据合并到指定来源的数据库"""
    if source not in source_dbs:
        print(f"错误: 未知来源 {source}")
        return 0
    
    target_db_path = source_dbs[source]
    if not os.path.exists(target_db_path):
        print(f"错误: 目标数据库不存在 {target_db_path}")
        return 0
    
    # 连接目标数据库
    try:
        target_conn = sqlite3.connect(target_db_path)
        target_cursor = target_conn.cursor()
        
        # 准备插入语句
        placeholders = ', '.join(['?' for _ in columns])
        column_names = ', '.join(columns)
        insert_sql = f"INSERT OR IGNORE INTO news ({column_names}) VALUES ({placeholders})"
        
        # 更新来源
        modified_data = []
        for news in news_data:
            news_list = list(news)
            # 查找来源字段索引
            source_index = columns.index('source') if 'source' in columns else -1
            if source_index >= 0:
                news_list[source_index] = source
            modified_data.append(tuple(news_list))
        
        # 执行插入
        target_cursor.executemany(insert_sql, modified_data)
        inserted_count = target_cursor.rowcount
        target_conn.commit()
        target_conn.close()
        
        return inserted_count
    except Exception as e:
        print(f"合并到 {source} 数据库时出错: {e}")
        return 0

def main():
    """主函数"""
    print("===== 未知来源数据库合并工具 =====")
    
    # 检查未知来源数据库是否存在
    if not os.path.exists(unknown_db_path):
        print(f"未找到未知来源数据库: {unknown_db_path}")
        print("检查其他可能包含未知来源的数据库...")
        
        # 查找其他可能的未知来源数据
        for db_file in os.listdir(db_dir):
            if db_file.endswith('.db') and db_file != 'finance_news.db':
                db_path = os.path.join(db_dir, db_file)
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM news WHERE source IS NULL OR source = '' OR source = '未知来源'")
                    count = cursor.fetchone()[0]
                    conn.close()
                    
                    if count > 0:
                        print(f"在 {db_file} 中发现 {count} 条未知来源新闻")
                except Exception as e:
                    print(f"检查 {db_file} 时出错: {e}")
        
        print("\n如需更新特定数据库中的未知来源，请运行更新未知来源脚本")
        return
    
    # 备份未知来源数据库
    print("正在备份未知来源数据库...")
    if not backup_database(unknown_db_path):
        print("备份失败，操作中止")
        return
    
    # 连接未知来源数据库
    try:
        unknown_conn = sqlite3.connect(unknown_db_path)
        unknown_cursor = unknown_conn.cursor()
        
        # 获取数据表结构
        unknown_cursor.execute("PRAGMA table_info(news)")
        columns_info = unknown_cursor.fetchall()
        columns = [col[1] for col in columns_info]
        
        # 获取所有新闻数据
        unknown_cursor.execute("SELECT * FROM news")
        all_news = unknown_cursor.fetchall()
        total_news = len(all_news)
        
        print(f"共找到 {total_news} 条新闻数据")
        
        # 按来源分类新闻
        news_by_source = {source: [] for source in source_dbs.keys()}
        news_by_source['其他'] = []
        
        for news in all_news:
            # 获取URL和标题
            url_index = columns.index('url') if 'url' in columns else -1
            title_index = columns.index('title') if 'title' in columns else -1
            content_index = columns.index('content') if 'content' in columns else -1
            
            url = news[url_index] if url_index >= 0 else None
            title = news[title_index] if title_index >= 0 else None
            content = news[content_index] if content_index >= 0 else None
            
            # 尝试识别来源
            source = identify_source_by_url(url)
            if not source:
                source = identify_source_by_content(title, content)
            
            # 归类新闻
            if source and source in news_by_source:
                news_by_source[source].append(news)
            else:
                news_by_source['其他'].append(news)
        
        # 显示分类结果
        print("\n按来源分类结果:")
        for source, news_list in news_by_source.items():
            print(f"{source}: {len(news_list)} 条")
        
        # 开始合并数据
        print("\n开始合并数据...")
        total_merged = 0
        
        for source, news_list in news_by_source.items():
            if not news_list:
                continue
                
            if source != '其他':
                merged = merge_to_source_db(news_list, columns, source)
                print(f"成功将 {merged}/{len(news_list)} 条新闻合并到 {source} 数据库")
                total_merged += merged
            else:
                # 合并到主数据库
                main_conn = sqlite3.connect(main_db_path)
                main_cursor = main_conn.cursor()
                
                # 准备插入语句
                placeholders = ', '.join(['?' for _ in columns])
                column_names = ', '.join(columns)
                insert_sql = f"INSERT OR IGNORE INTO news ({column_names}) VALUES ({placeholders})"
                
                # 设置默认来源为"其他来源"
                modified_data = []
                for news in news_list:
                    news_list = list(news)
                    source_index = columns.index('source') if 'source' in columns else -1
                    if source_index >= 0:
                        news_list[source_index] = "其他来源"
                    modified_data.append(tuple(news_list))
                
                # 执行插入
                main_cursor.executemany(insert_sql, modified_data)
                merged = main_cursor.rowcount
                main_conn.commit()
                main_conn.close()
                
                print(f"成功将 {merged}/{len(news_list)} 条未识别来源的新闻合并到主数据库")
                total_merged += merged
        
        # 关闭连接
        unknown_conn.close()
        
        # 总结
        print(f"\n合并完成! 共合并 {total_merged}/{total_news} 条新闻")
        
        # 询问是否删除原数据库
        if total_merged > 0:
            answer = input("是否删除原未知来源数据库? (y/n): ").lower()
            if answer == 'y':
                try:
                    os.remove(unknown_db_path)
                    print(f"已删除 {unknown_db_path}")
                except Exception as e:
                    print(f"删除失败: {e}")
    
    except Exception as e:
        print(f"处理未知来源数据库时出错: {e}")

if __name__ == "__main__":
    main() 