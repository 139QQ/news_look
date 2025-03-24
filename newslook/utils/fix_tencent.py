#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复腾讯爬虫文件(tencent.py)中的缩进错误
"""

import os
import re
import sys

def fix_indentation_in_file(file_path):
    """修复文件中的缩进错误"""
    print(f"开始修复文件: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复817行的缩进错误
    content = re.sub(
        r'logger\.debug\(f"检测到APP下载页URL: \{url\}"\)\n(\s+)return True',
        r'logger.debug(f"检测到APP下载页URL: {url}")\n            return True',
        content
    )
    
    # 修复874行的缩进错误
    content = re.sub(
        r'logger\.info\(f"URL已被识别为广告，跳过: \{url\}"\)\n(\s+)return None',
        r'logger.info(f"URL已被识别为广告，跳过: {url}")\n            return None',
        content
    )
    
    # 修复try-except块的错误
    content = re.sub(
        r'(\s+)# 尝试多次获取页面内容\n(\s+)for retry in range\(max_retries\):\n(\s+)try:',
        r'\g<1># 尝试多次获取页面内容\n\g<2>for retry in range(max_retries):\n\g<3>try:',
        content
    )
    
    # 修复953-958行的意外缩进
    content = re.sub(
        r'(\s+)return news_data\n(\s+)\n(\s+)except Exception as e:',
        r'\g<1>return news_data\n\n            except Exception as e:',
        content
    )
    
    # 修复1304-1306行的意外缩进
    content = re.sub(
        r'(\s+)self.random_sleep\(3, 5\)\n(\s+)except Exception as e:\n(\s+)logger\.error',
        r'\g<1>self.random_sleep(3, 5)\n            except Exception as e:\n                logger.error',
        content
    )
    
    # 保存修改后的内容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"文件修复完成: {file_path}")

def main():
    # 获取当前脚本的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建tencent.py文件的路径
    tencent_file_path = os.path.join(current_dir, '..', 'crawlers', 'tencent.py')
    
    # 检查文件是否存在
    if not os.path.exists(tencent_file_path):
        print(f"错误: 文件不存在: {tencent_file_path}")
        sys.exit(1)
    
    # 修复文件中的缩进错误
    fix_indentation_in_file(tencent_file_path)

if __name__ == '__main__':
    main() 