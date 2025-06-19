#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 综合爬虫测试
测试所有爬虫的爬取、保存、日志功能
"""

import os
import sys
import time
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 测试配置
TEST_CONFIG = {
    'max_news': 2,  # 每个爬虫测试爬取2条新闻
    'days': 1,      # 爬取1天内的新闻
    'timeout': 60,  # 每个爬虫最大测试时间60秒
    'db_dir': 'test_crawl/data',  # 测试数据库目录
    'log_dir': 'test_crawl/logs'   # 测试日志目录
}

# 支持的爬虫列表
CRAWLERS = {
    'sina': '新浪财经',
    'eastmoney': '东方财富', 
    'netease': '网易财经',
    'ifeng': '凤凰财经'
}

class CrawlerTester:
    """爬虫综合测试器"""
    
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        self.setup_test_environment()
        
    def setup_test_environment(self):
        """设置测试环境"""
        # 创建测试目录
        os.makedirs(TEST_CONFIG['db_dir'], exist_ok=True)
        os.makedirs(TEST_CONFIG['log_dir'], exist_ok=True)
        
        # 设置日志
        log_file = os.path.join(TEST_CONFIG['log_dir'], f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('CrawlerTester')
        self.logger.info("=" * 60)
        self.logger.info("NewsLook 综合爬虫测试开始")
        self.logger.info("=" * 60)
    
    def test_crawler(self, source):
        """测试单个爬虫"""
        crawler_name = CRAWLERS[source]
        self.logger.info(f"\n开始测试 {crawler_name} 爬虫...")
        
        test_result = {
            'source': source,
            'name': crawler_name,
            'success': False,
            'error': None,
            'crawled_count': 0,
            'db_records': 0,
            'execution_time': 0,
            'log_file_exists': False,
            'db_file_exists': False
        }
        
        start_time = time.time()
        
        try:
            # 执行爬虫命令
            import subprocess
            cmd = [
                sys.executable, 'run.py', 'crawler',
                '-s', source,
                '-m', str(TEST_CONFIG['max_news']),
                '-d', str(TEST_CONFIG['days']),
                '--db-dir', TEST_CONFIG['db_dir']
            ]
            
            self.logger.info(f"执行命令: {' '.join(cmd)}")
            
            # 运行爬虫
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TEST_CONFIG['timeout'],
                cwd=project_root
            )
            
            test_result['execution_time'] = time.time() - start_time
            
            if result.returncode == 0:
                self.logger.info(f"✅ {crawler_name} 爬虫执行成功")
                test_result['success'] = True
                
                # 检查输出
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines:
                    if '爬取完成:' in line:
                        try:
                            count = int(line.split(':')[-1].strip())
                            test_result['crawled_count'] = count
                            self.logger.info(f"📊 爬取数量: {count}")
                        except:
                            pass
                
            else:
                self.logger.error(f"❌ {crawler_name} 爬虫执行失败")
                self.logger.error(f"错误输出: {result.stderr}")
                test_result['error'] = result.stderr
                
        except subprocess.TimeoutExpired:
            test_result['error'] = f"执行超时 (>{TEST_CONFIG['timeout']}秒)"
            self.logger.error(f"⏰ {crawler_name} 爬虫执行超时")
            
        except Exception as e:
            test_result['error'] = str(e)
            self.logger.error(f"💥 {crawler_name} 爬虫测试异常: {e}")
        
        # 检查数据库文件
        db_file = os.path.join(TEST_CONFIG['db_dir'], f"{source}.db")
        if os.path.exists(db_file):
            test_result['db_file_exists'] = True
            try:
                # 检查数据库记录数
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM news")
                count = cursor.fetchone()[0]
                test_result['db_records'] = count
                conn.close()
                self.logger.info(f"💾 数据库记录数: {count}")
            except Exception as e:
                self.logger.warning(f"⚠️ 无法查询数据库记录: {e}")
        else:
            self.logger.warning(f"⚠️ 数据库文件不存在: {db_file}")
        
        # 检查日志文件
        log_files = []
        for root, dirs, files in os.walk('logs'):
            for file in files:
                if crawler_name in file and file.endswith('.log'):
                    log_files.append(os.path.join(root, file))
        
        if log_files:
            test_result['log_file_exists'] = True
            self.logger.info(f"📝 找到日志文件: {len(log_files)} 个")
        else:
            self.logger.warning(f"⚠️ 未找到 {crawler_name} 的日志文件")
        
        return test_result
    
    def test_all_crawlers(self):
        """测试所有爬虫"""
        self.logger.info(f"开始测试 {len(CRAWLERS)} 个爬虫...")
        
        for source in CRAWLERS:
            try:
                result = self.test_crawler(source)
                self.results[source] = result
                
                # 等待一段时间避免请求过于频繁
                time.sleep(2)
                
            except KeyboardInterrupt:
                self.logger.warning("用户中断测试")
                break
            except Exception as e:
                self.logger.error(f"测试 {source} 时发生错误: {e}")
                self.results[source] = {
                    'source': source,
                    'name': CRAWLERS[source],
                    'success': False,
                    'error': str(e),
                    'crawled_count': 0,
                    'db_records': 0,
                    'execution_time': 0,
                    'log_file_exists': False,
                    'db_file_exists': False
                }
    
    def generate_report(self):
        """生成测试报告"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("测试报告")
        self.logger.info("=" * 60)
        
        success_count = 0
        total_crawled = 0
        total_db_records = 0
        
        for source, result in self.results.items():
            status = "✅ 成功" if result['success'] else "❌ 失败"
            
            self.logger.info(f"\n【{result['name']}】")
            self.logger.info(f"  状态: {status}")
            self.logger.info(f"  执行时间: {result['execution_time']:.2f}秒")
            self.logger.info(f"  爬取数量: {result['crawled_count']}")
            self.logger.info(f"  数据库记录: {result['db_records']}")
            self.logger.info(f"  数据库文件: {'存在' if result['db_file_exists'] else '不存在'}")
            self.logger.info(f"  日志文件: {'存在' if result['log_file_exists'] else '不存在'}")
            
            if result['error']:
                self.logger.info(f"  错误信息: {result['error']}")
            
            if result['success']:
                success_count += 1
            total_crawled += result['crawled_count']
            total_db_records += result['db_records']
        
        self.logger.info("\n" + "-" * 40)
        self.logger.info("总体统计")
        self.logger.info("-" * 40)
        self.logger.info(f"总执行时间: {total_time:.2f}秒")
        self.logger.info(f"成功率: {success_count}/{len(CRAWLERS)} ({success_count/len(CRAWLERS)*100:.1f}%)")
        self.logger.info(f"总爬取数量: {total_crawled}")
        self.logger.info(f"总数据库记录: {total_db_records}")
        
        # 检查关键功能
        self.logger.info("\n" + "-" * 40)
        self.logger.info("功能检查")
        self.logger.info("-" * 40)
        
        # 检查爬取功能
        crawl_success = total_crawled > 0
        self.logger.info(f"爬取功能: {'✅ 正常' if crawl_success else '❌ 异常'}")
        
        # 检查保存功能
        save_success = total_db_records > 0
        self.logger.info(f"保存功能: {'✅ 正常' if save_success else '❌ 异常'}")
        
        # 检查日志功能
        log_success = any(result['log_file_exists'] for result in self.results.values())
        self.logger.info(f"日志功能: {'✅ 正常' if log_success else '❌ 异常'}")
        
        # 总体评估
        all_functions_ok = crawl_success and save_success and log_success
        overall_status = "✅ 所有功能正常" if all_functions_ok else "⚠️ 部分功能异常"
        self.logger.info(f"\n总体评估: {overall_status}")
        
        return {
            'success_rate': success_count / len(CRAWLERS),
            'total_crawled': total_crawled,
            'total_db_records': total_db_records,
            'crawl_success': crawl_success,
            'save_success': save_success,
            'log_success': log_success,
            'all_functions_ok': all_functions_ok
        }
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        try:
            self.test_all_crawlers()
            report = self.generate_report()
            
            self.logger.info("\n" + "=" * 60)
            self.logger.info("综合测试完成")
            self.logger.info("=" * 60)
            
            return report
            
        except Exception as e:
            self.logger.error(f"综合测试失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None

def main():
    """主函数"""
    print("=" * 60)
    print("NewsLook 综合爬虫测试")
    print("=" * 60)
    print(f"测试配置:")
    print(f"  每个爬虫爬取数量: {TEST_CONFIG['max_news']}")
    print(f"  测试天数范围: {TEST_CONFIG['days']}")
    print(f"  超时时间: {TEST_CONFIG['timeout']}秒")
    print(f"  数据库目录: {TEST_CONFIG['db_dir']}")
    print(f"  日志目录: {TEST_CONFIG['log_dir']}")
    print("")
    
    # 确认开始测试
    try:
        input("按 Enter 开始测试，Ctrl+C 取消...")
    except KeyboardInterrupt:
        print("\n测试已取消")
        return
    
    # 运行测试
    tester = CrawlerTester()
    report = tester.run_comprehensive_test()
    
    if report:
        # 根据测试结果决定退出码
        if report['all_functions_ok'] and report['success_rate'] >= 0.75:
            print("\n🎉 测试通过！所有核心功能正常。")
            sys.exit(0)
        else:
            print("\n⚠️ 测试未完全通过，请检查错误信息。")
            sys.exit(1)
    else:
        print("\n💥 测试失败！")
        sys.exit(2)

if __name__ == "__main__":
    main() 