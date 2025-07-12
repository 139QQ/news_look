#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - Web应用程序主入口
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import os
import json
from datetime import datetime, timedelta

# 修改导入语句，适应当前项目结构
from backend.app.utils.logger import get_logger, configure_logger
from backend.app.web.routes import register_routes
from backend.api.stats_api import stats_api
from backend.api.user_api import user_api
from backend.app.routes.user_routes import user_bp

logger = get_logger(__name__)

def create_app():
    """创建Flask应用"""
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
    
    # 设置密钥，使用环境变量或默认值
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'news_look_secret_key')
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 禁用缓存
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    
    # 注册蓝图
    register_routes(app)  # 注册web路由
    
    # 注册API蓝图
    app.register_blueprint(stats_api, url_prefix='/api/stats')
    app.register_blueprint(user_api)
    app.register_blueprint(user_bp)
    
    @app.context_processor
    def inject_global_vars():
        """注入全局变量到模板"""
        now = datetime.now()
        return {
            'app_name': os.environ.get('APP_NAME', '财经新闻爬虫系统'),
            'current_year': now.year,
            'version': os.environ.get('APP_VERSION', '1.0.0'),
        }
    
    return app 