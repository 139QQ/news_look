#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
爬虫初始化修复工具 - 统一所有爬虫类的初始化方法
"""

import os
import sys
import re
import logging
from datetime import datetime

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('crawler_init_fix')

class CrawlerInitFixer:
    """爬虫初始化方法修复工具类"""
    
    def __init__(self, crawlers_dir=None):
        """
        初始化爬虫初始化方法修复工具
        
        Args:
            crawlers_dir: 爬虫目录路径，如果为None则使用默认路径
        """
        if crawlers_dir is None:
            self.crawlers_dir = os.path.join(os.getcwd(), 'app', 'crawlers')
        else:
            self.crawlers_dir = crawlers_dir
        
        # 确保爬虫目录存在
        if not os.path.exists(self.crawlers_dir):
            logger.error(f"爬虫目录不存在: {self.crawlers_dir}")
            raise FileNotFoundError(f"爬虫目录不存在: {self.crawlers_dir}")
        
        logger.info(f"初始化爬虫初始化方法修复工具，爬虫目录: {self.crawlers_dir}")
        
        # 爬虫文件列表
        self.crawler_files = [
            'eastmoney.py',
            'eastmoney_simple.py',
            'sina.py',
            'tencent.py',
            'netease.py',
            'ifeng.py'
        ]
    
    def fix_all_crawlers(self):
        """修复所有爬虫类的初始化方法"""
        results = {}
        
        for file_name in self.crawler_files:
            file_path = os.path.join(self.crawlers_dir, file_name)
            if not os.path.exists(file_path):
                logger.warning(f"爬虫文件不存在: {file_path}")
                results[file_name] = False
                continue
            
            logger.info(f"修复爬虫文件: {file_name}")
            try:
                result = self.fix_crawler_init(file_path)
                results[file_name] = result
            except Exception as e:
                logger.error(f"修复爬虫文件失败: {file_path}, 错误: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                results[file_name] = False
        
        # 输出总结
        logger.info("\n===== 修复任务执行完成 =====")
        for file_name, result in results.items():
            logger.info(f"{file_name}: {'成功' if result else '失败'}")
        
        return results
    
    def fix_crawler_init(self, file_path):
        """
        修复爬虫类的初始化方法
        
        Args:
            file_path: 爬虫文件路径
        
        Returns:
            bool: 是否修复成功
        """
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找初始化方法
            init_pattern = r'def __init__\s*\(\s*self,\s*(?:db_manager=None,\s*)?db_path=None,\s*use_proxy=False,\s*use_source_db=False.*?\):'
            init_match = re.search(init_pattern, content, re.DOTALL)
            
            if not init_match:
                logger.warning(f"未找到初始化方法: {file_path}")
                return False
            
            # 获取初始化方法的参数和主体
            init_method = init_match.group(0)
            
            # 如果已经是正确的初始化方法签名，不需要修改
            if init_method == 'def __init__(self, db_path=None, use_proxy=False, use_source_db=False):' or \
               init_method == 'def __init__(self, db_path=None, use_proxy=False, use_source_db=False, **kwargs):':
                logger.info(f"初始化方法已符合要求，无需修改: {file_path}")
                return True
            
            # 修改为统一的初始化方法签名
            if 'db_manager' in init_method:
                # 保留db_manager参数，添加**kwargs
                if '**kwargs' not in init_method:
                    new_init_method = init_method.replace('use_source_db=False)', 'use_source_db=False, **kwargs)')
                else:
                    new_init_method = init_method
            else:
                # 添加db_manager参数和**kwargs
                new_init_method = init_method.replace('def __init__(self,', 'def __init__(self, db_manager=None,')
                if '**kwargs' not in new_init_method:
                    new_init_method = new_init_method.replace('use_source_db=False)', 'use_source_db=False, **kwargs)')
            
            # 修改super().__init__调用
            super_pattern = r'super\(\)\.__init__\s*\(.*?\)'
            super_match = re.search(super_pattern, content, re.DOTALL)
            
            if not super_match:
                logger.warning(f"未找到super().__init__调用: {file_path}")
                return False
            
            super_call = super_match.group(0)
            
            # 如果已经包含了db_manager参数，保留它
            if 'db_manager' in super_call:
                # 确保包含**kwargs
                if '**kwargs' not in super_call:
                    if super_call.endswith(')'):
                        new_super_call = super_call[:-1] + ', **kwargs)'
                    else:
                        new_super_call = super_call + ', **kwargs'
                else:
                    new_super_call = super_call
            else:
                # 添加db_manager=db_manager
                if '(' in super_call:
                    new_super_call = super_call.replace('(', '(db_manager=db_manager, ')
                    # 确保包含**kwargs
                    if '**kwargs' not in new_super_call:
                        if new_super_call.endswith(')'):
                            new_super_call = new_super_call[:-1] + ', **kwargs)'
                        else:
                            new_super_call = new_super_call + ', **kwargs'
                else:
                    logger.warning(f"无法修改super().__init__调用: {file_path}")
                    return False
            
            # 更新文件内容
            new_content = content.replace(init_method, new_init_method)
            new_content = new_content.replace(super_call, new_super_call)
            
            # 保存修改后的文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"成功修复爬虫初始化方法: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"修复爬虫初始化方法失败: {file_path}, 错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

# 主函数
def main():
    """主函数"""
    print("=" * 60)
    print(" 爬虫初始化方法修复工具 ".center(60, '='))
    print("=" * 60)
    print("本工具用于修复所有爬虫类的初始化方法，统一接口")
    print("=" * 60)
    
    try:
        # 获取爬虫目录
        crawlers_dir = os.path.join(os.getcwd(), 'app', 'crawlers')
        
        # 初始化修复工具
        fixer = CrawlerInitFixer(crawlers_dir)
        
        # 修复所有爬虫
        results = fixer.fix_all_crawlers()
        
        # 输出总结
        print("\n" + "=" * 60)
        print(" 修复任务执行结果 ".center(60, '='))
        print("=" * 60)
        
        success_count = sum(1 for result in results.values() if result)
        print(f"共修复 {success_count}/{len(results)} 个爬虫类")
        
        for file_name, result in results.items():
            status = "成功" if result else "失败"
            print(f"{file_name}: {status}")
        
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