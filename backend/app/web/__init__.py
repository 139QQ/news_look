#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 财经新闻爬虫系统 - Web API模块
提供RESTful API接口，配合Vue前端界面使用
"""

import os
import glob
from flask import Flask
from flask_cors import CORS
from datetime import datetime
from app.config import get_settings

try:
    from app.crawlers.manager import CrawlerManager
except ImportError:
    CrawlerManager = None

def create_app(config=None):
    """创建Flask应用
    
    Args:
        config: 配置对象或字典
    
    Returns:
        Flask应用实例
    """
    # 获取全局设置
    settings = get_settings()
    
    # 创建Flask应用
    app = Flask(__name__)
    
    # 启用CORS支持，允许前端访问API
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # 加载配置
    app.secret_key = settings.get('secret_key', os.urandom(24).hex())
    app.config['DEBUG'] = settings.get('debug', False)
    app.config['JSON_AS_ASCII'] = False  # 支持中文JSON输出
    
    # 确保日志目录存在
    log_dir = settings.get('LOG_DIR', os.path.join(os.getcwd(), 'logs'))
    app.config['LOG_DIR'] = log_dir
    os.makedirs(log_dir, exist_ok=True)
    
    # 确定数据库目录
    if config and 'DB_DIR' in config and config['DB_DIR']:
        # 使用传入的DB_DIR配置
        db_dir = config['DB_DIR']
    else:
        # 尝试从环境变量获取
        db_dir = os.environ.get('DB_DIR')
        
        # 如果环境变量中没有，则尝试自动查找
        if not db_dir:
            # 尝试查找数据库目录 - 修复路径优先级，优先查找 databases 目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            possible_dirs = [
                os.path.join(project_root, 'databases'),  # 优先查找 databases 目录
                os.path.join(os.getcwd(), 'databases'),   # 当前目录下的 databases
                os.path.join(os.getcwd(), 'data'),        # 当前目录下的 data
                os.path.join(os.getcwd(), 'data', 'db'),  # data/db 目录
                os.path.join(os.getcwd(), 'db'),          # db 目录
                os.path.join(project_root, 'data'),       # 项目根目录下的 data
                os.path.join(project_root, 'data', 'db'), # 项目根目录下的 data/db
                os.path.join(project_root, 'db')          # 项目根目录下的 db
            ]
            
            # 查找包含数据库文件的目录
            for possible_dir in possible_dirs:
                if os.path.exists(possible_dir):
                    db_files = glob.glob(os.path.join(possible_dir, '*.db'))
                    if db_files:
                        db_dir = possible_dir
                        print(f"自动发现数据库目录: {db_dir} (包含{len(db_files)}个数据库文件)")
                        break
            
            # 如果没找到含数据库文件的目录，使用默认目录
            if not db_dir:
                db_dir = os.path.join(project_root, 'databases')  # 修复默认路径为 databases
    
    # 确保数据库目录存在
    app.config['DB_DIR'] = db_dir
    os.makedirs(db_dir, exist_ok=True)
    
    # 查找并输出数据库文件情况
    db_files = glob.glob(os.path.join(db_dir, '*.db'))
    print(f"API服务使用数据库目录: {db_dir}")
    print(f"找到 {len(db_files)} 个数据库文件:")
    for db_file in sorted(db_files, key=os.path.getmtime, reverse=True)[:5]:  # 只显示最新的5个
        file_size = os.path.getsize(db_file) / 1024  # KB
        print(f"  - {os.path.basename(db_file)} ({file_size:.1f} KB)")
    if len(db_files) > 5:
        print(f"  - ... 以及其他 {len(db_files) - 5} 个数据库文件")
    
    # 设置环境变量，以便其他模块访问
    os.environ['DB_DIR'] = db_dir
    
    # 如果提供了额外配置，则更新
    if config:
        if isinstance(config, dict):
            app.config.update(config)
        else:
            app.config.from_object(config)
    
    # 初始化爬虫管理器（如果可用）
    if 'CRAWLER_MANAGER' in app.config:
        app.crawler_manager = app.config['CRAWLER_MANAGER']
    elif CrawlerManager is not None:
        try:
            app.crawler_manager = CrawlerManager()
        except Exception as e:
            import traceback
            print(f"初始化爬虫管理器失败: {e}")
            traceback.print_exc()
            app.crawler_manager = None
    
    # 注册API路由
    from app.api.routes import register_api_routes
    register_api_routes(app)
    
    # 添加健康检查端点
    @app.route('/health')
    def health_check():
        """健康检查端点"""
        return {
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'database_files': len(glob.glob(os.path.join(app.config['DB_DIR'], '*.db')))
        }
    
    return app
