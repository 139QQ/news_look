import sqlite3
import os
import json

# 连接到数据库
db_path = os.path.join('data', 'db', '网易财经.db')
print(f"正在检查数据库: {db_path}")
print(f"数据库文件是否存在: {os.path.exists(db_path)}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"数据库中的表: {tables}")
    
    # 检查每个表的结构和内容
    for table in tables:
        table_name = table[0]
        print(f"\n表 '{table_name}' 的结构:")
        
        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col}")
        
        # 获取记录数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        print(f"\n表 '{table_name}' 中有 {count} 条记录")
        
        # 显示部分数据
        if count > 0:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
            rows = cursor.fetchall()
            print(f"\n表 '{table_name}' 的前3条数据:")
            for row in rows:
                print(f"  {row}")
    
    conn.close()
    print("\n数据库检查完成")
    
except Exception as e:
    print(f"检查数据库时出错: {str(e)}")
