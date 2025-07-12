#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试Web接口和数据库连接
"""

import os
import sys
import requests
import sqlite3
import logging
import time
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def test_database_connection():
    """测试数据库连接和数据"""
    logger.info("=== 测试数据库连接 ===")
    
    db_dir = 'data'
    db_files = [f for f in os.listdir(db_dir) if f.endswith('.db')]
    
    logger.info(f"发现数据库文件: {db_files}")
    
    for db_file in db_files:
        db_path = os.path.join(db_dir, db_file)
        source_name = db_file.replace('.db', '')
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查表结构
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"数据库 {db_file} 中的表: {tables}")
            
            if 'news' in tables:
                # 检查新闻数量
                cursor.execute("SELECT COUNT(*) FROM news")
                count = cursor.fetchone()[0]
                logger.info(f"数据库 {db_file} 中的新闻数量: {count}")
                
                if count > 0:
                    # 显示最新的几条新闻
                    cursor.execute("""
                        SELECT id, title, pub_time, crawl_time 
                        FROM news 
                        ORDER BY crawl_time DESC 
                        LIMIT 3
                    """)
                    recent_news = cursor.fetchall()
                    logger.info(f"最近的3条新闻:")
                    for i, (news_id, title, pub_time, crawl_time) in enumerate(recent_news, 1):
                        logger.info(f"  {i}. {title[:50]}... (发布: {pub_time}, 爬取: {crawl_time})")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"连接数据库 {db_file} 失败: {e}")

def test_web_api(base_url="http://localhost:5000"):
    """测试Web API接口"""
    logger.info("=== 测试Web API接口 ===")
    
    # 测试接口列表
    test_apis = [
        ('/api/stats', 'GET', '统计数据'),
        ('/api/news', 'GET', '新闻列表'),
        ('/api/news/sources', 'GET', '新闻源列表'),
        ('/api/trends', 'GET', '趋势数据'),
        ('/api/crawler/status', 'GET', '爬虫状态'),
    ]
    
    for endpoint, method, description in test_apis:
        try:
            url = f"{base_url}{endpoint}"
            logger.info(f"测试 {description}: {method} {url}")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info(f"✅ {description} - 成功")
                    # 打印部分响应数据
                    if 'data' in data:
                        if isinstance(data['data'], dict):
                            logger.info(f"   响应数据键: {list(data['data'].keys())}")
                        elif isinstance(data['data'], list):
                            logger.info(f"   响应数据长度: {len(data['data'])}")
                else:
                    logger.warning(f"⚠️ {description} - API返回失败: {data.get('message', '未知错误')}")
            else:
                logger.error(f"❌ {description} - HTTP状态码: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ {description} - 连接失败，Web服务器可能未启动")
        except Exception as e:
            logger.error(f"❌ {description} - 请求失败: {e}")

def start_web_server():
    """启动Web服务器"""
    logger.info("=== 启动Web服务器 ===")
    
    import subprocess
    
    try:
        # 启动Web服务器
        cmd = [sys.executable, 'run.py', 'web', '--host', '127.0.0.1', '--port', '5000', '--debug']
        logger.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 等待几秒让服务器启动
        logger.info("等待Web服务器启动...")
        time.sleep(3)
        
        # 检查进程是否还在运行
        if process.poll() is None:
            logger.info("✅ Web服务器启动成功，正在运行中")
            return process
        else:
            stdout, stderr = process.communicate()
            logger.error(f"❌ Web服务器启动失败")
            logger.error(f"stdout: {stdout.decode()}")
            logger.error(f"stderr: {stderr.decode()}")
            return None
            
    except Exception as e:
        logger.error(f"启动Web服务器失败: {e}")
        return None

def main():
    """主测试函数"""
    logger.info("开始测试NewsLook Web界面和数据库连接")
    
    # 1. 测试数据库连接
    test_database_connection()
    
    # 2. 尝试启动Web服务器（在后台）
    logger.info("\n" + "="*50)
    web_process = start_web_server()
    
    if web_process:
        try:
            # 3. 测试Web API
            logger.info("\n" + "="*50)
            time.sleep(2)  # 再等待一点时间确保服务器完全启动
            test_web_api()
            
            # 提示用户
            logger.info("\n" + "="*50)
            logger.info("🌐 Web服务器已启动，请在浏览器中访问:")
            logger.info("   主页面: http://localhost:5000")
            logger.info("   前端页面: http://localhost:3000")
            logger.info("\n按 Ctrl+C 停止服务器...")
            
            # 保持服务器运行
            web_process.wait()
            
        except KeyboardInterrupt:
            logger.info("用户中断，正在停止Web服务器...")
            web_process.terminate()
            web_process.wait()
        except Exception as e:
            logger.error(f"测试过程中出错: {e}")
            web_process.terminate()
            web_process.wait()
    else:
        logger.error("无法启动Web服务器，请手动检查问题")

if __name__ == "__main__":
    main() 