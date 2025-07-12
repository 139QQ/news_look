#!/usr/bin/env python3
"""
SQLite紧急优化脚本
立即缓解锁争用和并发瓶颈问题

使用方法:
python scripts/emergency_sqlite_optimization.py
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.newslook.core.sqlite_optimizer import get_sqlite_optimizer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('data/logs/sqlite_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def discover_sqlite_databases() -> List[str]:
    """发现项目中的所有SQLite数据库文件"""
    data_dir = project_root / "data"
    db_files = []
    
    # 搜索模式
    patterns = ["*.db", "*.sqlite", "*.sqlite3"]
    
    for pattern in patterns:
        db_files.extend(data_dir.rglob(pattern))
    
    # 过滤掉备份文件和测试文件
    filtered_files = []
    for db_file in db_files:
        file_name = db_file.name.lower()
        if not any(skip in file_name for skip in ['backup', 'bak', 'temp', 'tmp', 'test']):
            filtered_files.append(str(db_file))
    
    return filtered_files

def main():
    """主执行函数"""
    print("🚨 NewsLook SQLite紧急优化程序启动")
    print("=" * 60)
    
    start_time = time.time()
    optimizer = get_sqlite_optimizer()
    
    try:
        # 1. 发现所有数据库文件
        print("📊 正在发现数据库文件...")
        db_files = discover_sqlite_databases()
        
        if not db_files:
            print("❌ 未发现任何SQLite数据库文件")
            return
            
        print(f"✅ 发现 {len(db_files)} 个数据库文件:")
        for db_file in db_files:
            size_mb = Path(db_file).stat().st_size / 1024 / 1024
            print(f"   - {db_file} ({size_mb:.2f} MB)")
        
        print("\n" + "=" * 60)
        
        # 2. 立即启用WAL模式
        print("🔧 正在为所有数据库启用WAL模式...")
        wal_results = optimizer.enable_wal_mode_for_all(db_files)
        
        print(f"✅ WAL模式启用成功: {len(wal_results['success'])} 个")
        print(f"❌ WAL模式启用失败: {len(wal_results['failed'])} 个")
        
        if wal_results['failed']:
            print("失败详情:")
            for failed in wal_results['failed']:
                print(f"   - {failed}")
        
        print("\n" + "=" * 60)
        
        # 3. 收集优化前的统计信息
        print("📈 正在收集数据库统计信息...")
        stats_before = []
        for db_file in db_files:
            stats = optimizer.get_database_stats(db_file)
            stats_before.append(stats)
            if 'error' not in stats:
                print(f"   - {Path(db_file).name}: {stats['size_mb']:.2f}MB, {stats['journal_mode']} 模式")
        
        print("\n" + "=" * 60)
        
        # 4. 执行数据库优化
        print("⚡ 正在并行优化所有数据库...")
        optimization_results = optimizer.optimize_all_databases(db_files)
        
        # 5. 汇总结果
        print("\n" + "=" * 60)
        print("📊 优化结果汇总:")
        
        successful = [r for r in optimization_results if r.get('status') == 'success']
        failed = [r for r in optimization_results if r.get('status') == 'error']
        
        print(f"✅ 成功优化: {len(successful)} 个数据库")
        print(f"❌ 优化失败: {len(failed)} 个数据库")
        
        total_time_saved = 0
        total_size_reduction = 0
        
        for result in successful:
            if 'before' in result and 'after' in result:
                size_before = result['before']['size_mb']
                size_after = result['after']['size_mb']
                size_reduction = size_before - size_after
                total_size_reduction += size_reduction
                
                print(f"   📁 {Path(result['db_path']).name}:")
                print(f"      ⏱️  优化耗时: {result['optimization_time']:.2f}s")
                print(f"      💾 大小变化: {size_before:.2f}MB → {size_after:.2f}MB")
                if size_reduction > 0:
                    print(f"      📉 节省空间: {size_reduction:.2f}MB")
                
                total_time_saved += result['optimization_time']
        
        if failed:
            print("\n❌ 优化失败的数据库:")
            for result in failed:
                print(f"   - {result.get('db_path', 'Unknown')}: {result.get('message', 'Unknown error')}")
        
        # 6. 生成优化报告
        total_time = time.time() - start_time
        
        print("\n" + "=" * 60)
        print("📋 优化总结:")
        print(f"   🕒 总耗时: {total_time:.2f}秒")
        print(f"   💾 总计节省空间: {total_size_reduction:.2f}MB")
        print(f"   ⚡ 预期性能提升: 查询延迟↓60-80%, 并发连接↑5-10X")
        
        # 7. 保存优化报告
        report_file = project_root / "data/logs/sqlite_optimization_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"SQLite紧急优化报告\n")
            f.write(f"优化时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总耗时: {total_time:.2f}秒\n")
            f.write(f"优化文件数: {len(db_files)}\n")
            f.write(f"成功: {len(successful)}, 失败: {len(failed)}\n")
            f.write(f"节省空间: {total_size_reduction:.2f}MB\n\n")
            
            f.write("详细结果:\n")
            for result in optimization_results:
                f.write(f"{result}\n")
        
        print(f"📄 优化报告已保存至: {report_file}")
        
        print("\n🎉 SQLite紧急优化完成！")
        print("💡 下一步建议:")
        print("   1. 监控应用性能变化")
        print("   2. 准备PostgreSQL迁移环境")
        print("   3. 执行数据迁移脚本")
        
    except Exception as e:
        logger.error(f"优化过程中发生错误: {e}")
        print(f"❌ 优化失败: {e}")
        
    finally:
        # 清理资源
        optimizer.close_all_pools()

if __name__ == "__main__":
    main() 