#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复Python文件中的缩进错误
"""

import os
import re
import sys

def fix_indentation(filename):
    """修复文件中的缩进错误
    
    Args:
        filename: 文件路径
    """
    print(f"正在修复文件 {filename} 中的缩进错误...")
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 创建备份文件
    backup_file = f"{filename}.bak"
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"已创建备份文件: {backup_file}")
    
    # 检查并修复 if 语句后没有缩进的行
    fixed_lines = []
    for i, line in enumerate(lines):
        fixed_lines.append(line)
        
        # 检查 if 语句
        if re.match(r'^\s*if\s+.*:\s*$', line):
            # 如果下一行的缩进不正确
            if i+1 < len(lines) and not re.match(r'^\s+', lines[i+1]) and lines[i+1].strip():
                # 获取当前行的缩进
                indent = len(line) - len(line.lstrip())
                # 添加4个空格的缩进
                lines[i+1] = ' ' * (indent + 4) + lines[i+1].lstrip()
                print(f"在第 {i+2} 行增加缩进")
    
    # 保存修复后的文件
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"文件 {filename} 修复完成")

if __name__ == '__main__':
    module_path = os.path.dirname(os.path.abspath(__file__))
    # 修复 __init__.py 文件
    init_py = os.path.join(module_path, '__init__.py')
    if os.path.exists(init_py):
        fix_indentation(init_py)
    # 如果需要修复其他文件，可以在这里添加
    for file in sys.argv[1:]:
        if os.path.exists(file):
            fix_indentation(file) 