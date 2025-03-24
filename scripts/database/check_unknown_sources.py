#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
未知来源检查工具 - 检查所有数据库中未知来源的数量

用法:
python scripts/check_unknown_sources.py
"""

import sqlite3
import os

# 数据库路径
db_dir = 'data/db'

def main():
    """检查所有数据库中未知来源的数量"""
    print("===== 未知来源检查工具 =====")
    
    # 确保数据库目录存在
    if not os.path.exists(db_dir):
        print(f"数据库目录不存在: {db_dir}")
        return
    
    # 统计总数
    total_unknown = 0
    
    # 检查所有数据库
    for db_file in os.listdir(db_dir):
        if db_file.endswith('.db') and not db_file.endswith('.bak'):
            db_path = os.path.join(db_dir, db_file)
            try:
                # 连接数据库
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 查询未知来源的数量
                cursor.execute("SELECT COUNT(*) FROM news WHERE source IS NULL OR source = '' OR source = '未知来源'")
                count = cursor.fetchone()[0]
                
                print(f"{db_file}: {count} 条未知来源新闻")
                total_unknown += count
                
                # 关闭连接
                conn.close()
            except Exception as e:
                print(f"检查 {db_file} 时出错: {e}")
    
    print(f"\n总计: {total_unknown} 条未知来源新闻")

if __name__ == "__main__":
    main() 