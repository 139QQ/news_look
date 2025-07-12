#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil

def fix_database_filenames():
    """修复数据库文件名编码问题"""
    db_dir = 'data/db'
    
    # 确保db_dir存在
    if not os.path.exists(db_dir):
        print(f"数据库目录不存在: {db_dir}")
        return
    
    # 文件名映射
    filename_mapping = {
        '腾讯财经.db': '腾讯财经.db',
        '新浪财经.db': '新浪财经.db',
        '东方财富.db': '东方财富.db',
        '网易财经.db': '网易财经.db',
        '凤凰财经.db': '凤凰财经.db',
        'finance_news.db': 'finance_news.db'
    }
    
    # 保存现有文件名
    existing_files = os.listdir(db_dir)
    print(f"目录中的文件数量: {len(existing_files)}")
    
    # 修复乱码文件名
    for file in existing_files:
        if file.endswith('.db') and not file.endswith('.bak'):
            # 检查是否是乱码文件
            if any(ord(c) > 127 for c in file) or '��' in file:
                print(f"发现可能乱码的文件名: {file}")
                
                # 推测原始文件名
                if '��Ѷ�ƾ�' in file:
                    new_name = '腾讯财经.db'
                    try:
                        # 备份原文件
                        backup_path = os.path.join(db_dir, f"{file}.backup")
                        print(f"备份文件 {file} 到 {backup_path}")
                        shutil.copy2(os.path.join(db_dir, file), backup_path)
                        
                        # 复制到正确名称
                        target_path = os.path.join(db_dir, new_name)
                        print(f"复制文件到正确名称: {target_path}")
                        shutil.copy2(os.path.join(db_dir, file), target_path)
                        
                        print(f"成功修复文件名 {file} -> {new_name}")
                    except Exception as e:
                        print(f"修复文件名 {file} 时出错: {str(e)}")
            else:
                print(f"正常文件名: {file}")
    
    # 验证结果
    print("\n--- 修复后的文件列表 ---")
    updated_files = os.listdir(db_dir)
    for file in updated_files:
        if file.endswith('.db') and not file.endswith('.bak') and not file.endswith('.backup'):
            print(f"  - {file}")

if __name__ == "__main__":
    fix_database_filenames() 