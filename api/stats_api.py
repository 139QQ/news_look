import os
import sys
import json
from flask import Blueprint, jsonify, request
import sqlite3
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

logger = setup_logger()
stats_api = Blueprint('stats_api', __name__)

@stats_api.route('/api/source_stats', methods=['GET'])
def get_source_stats():
    """获取新闻来源统计数据"""
    try:
        # 获取数据库目录
        db_dir = os.environ.get('DB_DIR', 'data/db')
        if not os.path.exists(db_dir):
            db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data/db')
        
        source_stats = {}
        total_news = 0
        
        # 查找所有数据库文件
        db_files = [f for f in os.listdir(db_dir) if f.endswith('.db')]
        
        for db_file in db_files:
            try:
                source_name = os.path.splitext(db_file)[0]
                db_path = os.path.join(db_dir, db_file)
                
                # 排除备份文件
                if '.bak' in db_file:
                    continue
                    
                # 连接数据库
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 查询新闻数量
                cursor.execute("SELECT COUNT(*) FROM news")
                count = cursor.fetchone()[0]
                
                if count > 0:
                    if source_name == 'finance_news':
                        # 主数据库，按来源分组查询
                        cursor.execute("SELECT source, COUNT(*) FROM news GROUP BY source")
                        for row in cursor.fetchall():
                            src, src_count = row
                            source_stats[src] = source_stats.get(src, 0) + src_count
                            total_news += src_count
                    else:
                        # 来源数据库
                        source_stats[source_name] = source_stats.get(source_name, 0) + count
                        total_news += count
                
                conn.close()
            except Exception as e:
                logger.error(f"处理数据库文件 {db_file} 失败: {str(e)}")
        
        return jsonify({
            'stats': source_stats,
            'total': total_news,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    except Exception as e:
        logger.error(f"获取来源统计数据失败: {str(e)}")
        return jsonify({
            'error': str(e),
            'stats': {},
            'total': 0
        }), 500 