#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - Web应用路由
"""

import os
import json
import uuid
import psutil
import platform
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, send_from_directory, send_file, current_app
from app.db.SQLiteManager import SQLiteManager
from app.db.user_preferences_db import UserPreferencesDB
from app.utils.database import NewsDatabase
from app.utils.logger import get_logger
from app.config import get_settings
import sqlite3
import traceback
from bs4 import BeautifulSoup
from app.utils.text_cleaner import TextCleaner, format_for_display
import re
import hashlib
from importlib import reload

logger = get_logger(__name__)

def get_db_path(db_name='finance_news.db'):
    """获取一致的数据库路径
    
    Args:
        db_name: 数据库文件名，默认为finance_news.db
        
    Returns:
        str: 数据库文件的完整路径
    """
    settings = get_settings()
    db_dir = settings.get('DB_DIR', os.path.join(os.getcwd(), 'data', 'db'))
    
    # 确保数据库目录存在
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"创建数据库目录: {db_dir}")
        
    return os.path.join(db_dir, db_name)

def register_routes(app):
    """注册路由"""
    
    # 蓝图已在app/__init__.py中注册，此处不再重复注册
    # from app.routes.monitor import monitor_bp
    # app.register_blueprint(monitor_bp)
    
    # 导入并注册API蓝图
    try:
        from api.stats_api import stats_api
        app.register_blueprint(stats_api)
        logger.info("成功注册来源统计API蓝图")
    except ImportError as e:
        logger.error(f"导入来源统计API蓝图失败: {str(e)}")
    
    # 注册404错误处理器
    @app.errorhandler(404)
    def page_not_found(error):
        logger.warning(f"404错误: {request.path} - {error}")
        try:
            return render_template('404.html'), 404
        except Exception as e:
            logger.error(f"渲染404页面失败: {str(e)}")
            return "404 - 页面未找到", 404
    
    # 每个render_template调用时都传递datetime以便在模板中使用
    @app.context_processor
    def inject_datetime():
        return {'datetime': datetime}
    
    @app.route('/')
    @app.route('/index')
    def index():
        """
        首页
        
        显示新闻列表和简要信息
        """
        try:
            # 获取查询参数
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            category = request.args.get('category', None)
            source = request.args.get('source', None)
            keyword = request.args.get('keyword', None)
            sort_by = request.args.get('sort_by', 'pub_time')
            order = request.args.get('order', 'desc')
            days = request.args.get('days', 7, type=int)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            view_mode = request.args.get('view', 'list')  # 添加视图模式参数
            
            # 验证并处理日期参数
            valid_date_range = False
            if start_date and end_date:
                try:
                    # 验证日期格式
                    datetime.strptime(start_date, '%Y-%m-%d')
                    datetime.strptime(end_date, '%Y-%m-%d')
                    valid_date_range = True
                except ValueError:
                    # 日期格式无效，回退到使用days参数
                    start_date = None
                    end_date = None
                    flash('日期格式无效，已使用默认时间范围', 'warning')
            
            # 日志记录请求参数
            logger.info(
                f"访问首页: page={page}, per_page={per_page}, category={category}, "
                f"source={source}, keyword={keyword}, sort_by={sort_by}, order={order}, days={days}, view={view_mode}"
            )
            
            # 获取数据库路径
            db_path = get_db_path('finance_news.db')
            
            # 查询新闻列表 - 使用with语句确保线程安全
            with SQLiteManager(db_path=db_path) as db:
                if valid_date_range:
                    # 添加兼容层以适配不同的数据库API
                    if hasattr(db, 'get_news_paginated'):
                        news_list, total = db.get_news_paginated(
                            page=page, 
                            per_page=per_page,
                            category=category,
                            source=source,
                            keyword=keyword,
                            sort_by=sort_by,
                            order=order,
                            start_date=start_date,
                            end_date=end_date
                        )
                    else:
                        # 如果没有get_news_paginated方法，使用query_news方法
                        news_list = db.query_news(
                            page=page, 
                            per_page=per_page,
                            category=category,
                            source=source,
                            keyword=keyword,
                            sort_by=sort_by,
                            order=order,
                            start_date=start_date,
                            end_date=end_date
                        )
                        total = len(news_list)
                else:
                    # 添加兼容层以适配不同的数据库API
                    if hasattr(db, 'get_news_paginated'):
                        news_list, total = db.get_news_paginated(
                            page=page, 
                            per_page=per_page,
                            category=category,
                            source=source,
                            keyword=keyword,
                            sort_by=sort_by,
                            order=order,
                            days=days
                        )
                    else:
                        # 如果没有get_news_paginated方法，使用query_news方法
                        news_list = db.query_news(
                            page=page, 
                            per_page=per_page,
                            category=category,
                            source=source,
                            keyword=keyword,
                            sort_by=sort_by,
                            order=order,
                            days=days
                        )
                        total = len(news_list)
                
                # 添加日志输出，检查数据是否为空
                logger.info(f"获取到新闻列表: {len(news_list)} 条记录")
                
                # 如果查询结果为空，添加测试数据
                if not news_list:
                    logger.warning("未查询到新闻数据，添加测试数据用于验证模板渲染")
                    news_list = [
                        {
                            "id": "test1", 
                            "title": "测试新闻1 - 验证模板渲染", 
                            "source": "测试来源", 
                            "category": "测试分类", 
                            "pub_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "url": "#",
                            "content": "这是一条测试新闻，用于验证模板能否正确渲染"
                        },
                        {
                            "id": "test2", 
                            "title": "测试新闻2 - 验证模板渲染", 
                            "source": "测试来源2", 
                            "category": "测试分类2", 
                            "pub_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "url": "#",
                            "content": "这是另一条测试新闻，用于验证模板能否正确渲染"
                        }
                    ]
                    # 设置总记录数为测试数据的长度
                    total = len(news_list)
            
                # 确保每个新闻项都有id字段
                for news_item in news_list:
                    if 'id' not in news_item or not news_item['id']:
                        # 如果没有id字段，使用唯一标识符（例如根据URL或其他字段生成）
                        if 'url' in news_item and news_item['url']:
                            # 使用URL的哈希作为ID
                            news_id = hashlib.md5(news_item['url'].encode('utf-8')).hexdigest()
                        else:
                            # 如果没有URL，使用标题和来源生成ID
                            title_source = f"{news_item.get('title', '')}_{news_item.get('source', '')}"
                            news_id = hashlib.md5(title_source.encode('utf-8')).hexdigest()
                        
                        news_item['id'] = news_id
                        logger.warning(f"为新闻项添加了ID: {news_id}")
                        
                        # 尝试更新数据库中的记录，添加ID
                        try:
                            if 'url' in news_item and news_item['url']:
                                # 添加兼容层以适配不同的数据库API
                                if hasattr(db, 'execute_query'):
                                    db.execute_query(
                                        "UPDATE news SET id = ? WHERE url = ?", 
                                        (news_id, news_item['url'])
                                    )
                                    logger.info(f"更新了数据库中的记录，为URL {news_item['url']} 添加了ID: {news_id}")
                                else:
                                    logger.warning(f"数据库对象不支持execute_query方法，无法更新记录ID")
                        except Exception as e:
                            logger.error(f"更新数据库记录失败: {str(e)}")
            
                # 计算总页数
                total_pages = (total + per_page - 1) // per_page if total > 0 else 1
                
                # 获取分类和来源列表用于筛选
                if hasattr(db, 'get_categories'):
                    categories = db.get_categories()
                else:
                    # 如果没有get_categories方法，创建一个空列表
                    categories = []
                    logger.warning("数据库对象不支持get_categories方法")
                
                if hasattr(db, 'get_sources'):
                    sources = db.get_sources()
                else:
                    # 如果没有get_sources方法，创建一个空列表
                    sources = []
                    logger.warning("数据库对象不支持get_sources方法")
            
            # 为分页创建请求参数副本，移除可能导致冲突的参数
            pagination_args = request.args.copy()
            # 移除所有会在URL模板中显式传递的参数
            for param in ['page', 'per_page', 'keyword', 'days', 'source', 'view', 'sort_by', 'order']:
                if param in pagination_args:
                    del pagination_args[param]
                    
            logger.debug(f"分页参数: {pagination_args}")
            
            # 尝试获取用户偏好设置
            user_preferences = {}
            try:
                with UserPreferencesDB() as preference_db:
                    # 提取已经保存的新闻ID列表
                    saved_news_ids = preference_db.get_saved_news_ids('default_user')
                    
                    # 提取已读新闻ID列表
                    read_news_ids = preference_db.get_read_news_ids('default_user')
                    
                    user_preferences = {
                        'saved_news_ids': saved_news_ids,
                        'read_news_ids': read_news_ids
                    }
            except Exception as e:
                # 将错误级别从error降低为warning，因为这不是关键错误
                logger.warning(f"获取用户偏好设置失败: {str(e)}")
                user_preferences = {
                    'saved_news_ids': [],
                    'read_news_ids': []
                }
            
            # 渲染模板 - 使用news而不是news_list以匹配模板
            try:
                return render_template(
                    'index.html',
                    news=news_list,
                    page=page,
                    per_page=per_page,
                    total=total,
                    total_pages=total_pages,
                    category=category,
                    source=source,
                    keyword=keyword,
                    sort_by=sort_by,
                    order=order,
                    days=days,
                    view_mode=view_mode,
                    categories=categories,
                    sources=sources,
                    user_preferences=user_preferences,
                    pagination_args=pagination_args,
                    current_start_date=start_date if valid_date_range else '',
                    current_end_date=end_date if valid_date_range else ''
                )
            except Exception as e:
                # 记录具体的模板渲染错误
                logger.error(f"渲染首页模板失败: {str(e)}")
                # 返回简化的错误页面
                try:
                    return render_template(
                        'error.html', 
                        error=f"首页加载失败: {str(e)}",
                        error_details=str(e)
                    ), 500
                except Exception as e2:
                    # 如果error.html模板也渲染失败，返回最简单的错误响应
                    logger.error(f"渲染错误页面也失败: {str(e2)}")
                    return f"严重错误: 首页加载失败 ({str(e)}), 错误页面也无法加载 ({str(e2)})", 500
                
        except Exception as e:
            logger.error(f"首页加载异常: {str(e)}")
            return render_template(
                'error.html', 
                error="首页加载失败",
                error_details=str(e)
            ), 500
    
    @app.route('/crawler_status')
    def crawler_status():
        """爬虫状态页面"""
        # 始终使用所有可用的数据库
        db = NewsDatabase(use_all_dbs=True)
        
        # 获取统计数据
        today = datetime.now().date()
        # 添加兼容层，检查方法是否存在
        if hasattr(db, 'get_news_count'):
            today_count = db.get_news_count(days=1)
            week_count = db.get_news_count(days=7)
            month_count = db.get_news_count(days=30)
            total_count = db.get_news_count()
        else:
            # 如果方法不存在，使用默认值
            logger.warning("数据库对象不支持get_news_count方法，使用默认值")
            today_count = 0
            week_count = 0
            month_count = 0
            total_count = 0
        
        # 获取爬虫状态
        crawlers = []
        if hasattr(app, 'crawler_manager'):
            crawler_manager = app.crawler_manager
            if crawler_manager and hasattr(crawler_manager, 'get_status'):
                crawlers = crawler_manager.get_status()
                
        # 获取系统信息
        system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory': {
                'total': psutil.virtual_memory().total / (1024 * 1024 * 1024),  # GB
                'used': psutil.virtual_memory().used / (1024 * 1024 * 1024),  # GB
                'percent': psutil.virtual_memory().percent
            },
            'disk': {
                'total': psutil.disk_usage('/').total / (1024 * 1024 * 1024),  # GB
                'used': psutil.disk_usage('/').used / (1024 * 1024 * 1024),  # GB
                'percent': psutil.disk_usage('/').percent
            }
        }
        
        # 获取源列表
        sources = db.get_sources()
        
        return render_template('crawler_status.html',
                             today_count=today_count,
                             week_count=week_count,
                             month_count=month_count,
                             total_count=total_count,
                             crawlers=crawlers,
                             system_info=system_info,
                             sources=sources)
    
    @app.route('/crawler')
    def crawler():
        """爬虫管理页面"""
        try:
            # 获取选中的数据源
            selected_source = None
            if hasattr(app, 'session') and 'selected_source' in app.session:
                selected_source = app.session['selected_source']
                if selected_source == 'all':
                    selected_source = None
                    use_all_dbs = True
                else:
                    use_all_dbs = False
            else:
                use_all_dbs = True  # 默认使用所有数据库
            
            # 使用指定的数据源初始化数据库
            db = NewsDatabase(source=selected_source, use_all_dbs=use_all_dbs)
            
            # 获取统计数据
            today = datetime.now().date()
            # 添加兼容层，检查方法是否存在
            if hasattr(db, 'get_news_count'):
                today_count = db.get_news_count(days=1)
                week_count = db.get_news_count(days=7)
                month_count = db.get_news_count(days=30)
                total_count = db.get_news_count()
            else:
                # 如果方法不存在，使用默认值
                logger.warning("数据库对象不支持get_news_count方法，使用默认值")
                today_count = 0
                week_count = 0
                month_count = 0
                total_count = 0
            
            # 获取爬虫状态
            crawlers = []
            if hasattr(app, 'crawler_manager'):
                crawler_manager = app.crawler_manager
                if crawler_manager and hasattr(crawler_manager, 'get_status'):
                    crawlers = crawler_manager.get_status()
            
            # 获取系统信息
            system_info = {
                'system': f"{platform.system()} {platform.release()}",
                'cpu_percent': int(psutil.cpu_percent()),
                'memory_percent': int(psutil.virtual_memory().percent),
                'disk_percent': int(psutil.disk_usage('/').percent)
            }
            
            # 获取可用数据源
            sources = db.get_available_sources()
            
            # 获取备份列表
            backups = db.get_backups()
            
            # 关闭数据库连接
            db.close()
            
            return render_template('crawler_status.html',
                                 today_count=today_count,
                                 week_count=week_count,
                                 month_count=month_count,
                                 total_count=total_count,
                                 crawlers=crawlers,
                                 system_info=system_info,
                                 sources=sources,
                                 backups=backups,
                                 selected_source=selected_source)
                                 
        except Exception as e:
            logger.error(f"渲染爬虫管理页面时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return render_template('error.html', error=str(e))
    
    @app.route('/dashboard')
    def dashboard():
        """数据中心页面"""
        try:
            # 重新导入确保使用最新的NewsDatabase类
            from importlib import reload
            from app.utils import database as db_module
            reload(db_module)
            from app.utils.database import NewsDatabase
            
            # 使用所有可用的数据库
            db = NewsDatabase(use_all_dbs=True)
            
            # 获取统计数据
            # 添加兼容层，检查方法是否存在
            if hasattr(db, 'get_news_count'):
                total_news = db.get_news_count()
                today_news = db.get_news_count(days=1)
            else:
                # 如果方法不存在，使用默认值
                logger.warning("数据库对象不支持get_news_count方法，使用默认值")
                total_news = 0
                today_news = 0
            
            # 获取所有来源
            if hasattr(db, 'get_sources'):
                sources = db.get_sources()
                logger.info(f"找到 {len(sources)} 个来源: {sources}")
            else:
                sources = []
                logger.error("NewsDatabase对象不支持get_sources方法，这是一个问题")
                # 手动获取来源
                try:
                    # 获取数据库目录
                    db_dir = app.config.get('DB_DIR', os.environ.get('DB_DIR', 'data/db'))
                    # 获取有效的数据库路径
                    valid_db_paths = []
                    if os.path.exists(db_dir):
                        db_files = [f for f in os.listdir(db_dir) if f.endswith('.db')]
                        for db_file in db_files:
                            valid_db_paths.append(os.path.join(db_dir, db_file))
                    
                    # 从所有数据库获取来源
                    for db_path in valid_db_paths:
                        try:
                            conn = sqlite3.connect(db_path)
                            conn.row_factory = sqlite3.Row
                            cursor = conn.cursor()
                            cursor.execute("SELECT DISTINCT source FROM news WHERE source IS NOT NULL AND source != ''")
                            rows = cursor.fetchall()
                            for row in rows:
                                if row['source'] not in sources:
                                    sources.append(row['source'])
                            conn.close()
                        except Exception as e:
                            logger.warning(f"从数据库 {db_path} 获取来源失败: {str(e)}")
                except Exception as e:
                    logger.error(f"手动获取来源失败: {str(e)}")
            
            # 为图表准备数据
            source_labels = []
            source_data = []
            source_stats = {}
            
            # 获取数据库目录
            db_dir = app.config.get('DB_DIR', os.environ.get('DB_DIR', 'data/db'))
            
            # 获取趋势数据
            now = datetime.now()
            trend_labels = []
            trend_data = []
            
            # 获取有效的数据库路径
            valid_db_paths = []
            if os.path.exists(db_dir):
                try:
                    db_files = [f for f in os.listdir(db_dir) if f.endswith('.db') and '.bak' not in f]
                    for db_file in db_files:
                        db_path = os.path.join(db_dir, db_file)
                        if os.path.exists(db_path):
                            valid_db_paths.append(db_path)
                        else:
                            logger.warning(f"数据库文件不存在，忽略: {db_path}")
                except Exception as e:
                    logger.error(f"获取数据库文件列表失败: {str(e)}")
            else:
                logger.warning(f"数据库目录不存在: {db_dir}")
            
            try:
                # 获取7天的每日新闻数量
                for i in range(6, -1, -1):
                    date = (now - timedelta(days=i)).strftime('%m-%d')
                    trend_labels.append(date)
                    
                    # 获取当天发布的新闻数量
                    date_str = (now - timedelta(days=i)).strftime('%Y-%m-%d')
                    # 根据日期过滤统计当天新闻数量
                    day_count = 0
                    try:
                        # 直接使用SQLite计算特定日期的新闻数量
                        for db_path in valid_db_paths:
                            try:
                                conn = sqlite3.connect(db_path)
                                cursor = conn.cursor()
                                cursor.execute("SELECT COUNT(*) FROM news WHERE pub_time LIKE ?", (f"{date_str}%",))
                                day_count += cursor.fetchone()[0]
                                conn.close()
                            except Exception as e:
                                logger.warning(f"统计{date_str}的新闻数量失败: {str(e)}")
                    except Exception as e:
                        logger.error(f"计算日期{date_str}的新闻数量失败: {str(e)}")
                    
                    trend_data.append(day_count)
            
                # 获取各来源的新闻数量 - 只统计有效的数据库文件
                for source in sources:
                    count = 0
                    # 先检查是否存在专用数据库
                    source_db_path = os.path.join(db_dir, f"{source}.db")
                    if os.path.exists(source_db_path):
                        try:
                            conn = sqlite3.connect(source_db_path)
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(*) FROM news")
                            count = cursor.fetchone()[0]
                            conn.close()
                        except Exception as e:
                            logger.warning(f"从专用数据库统计{source}数量失败: {str(e)}")
                    else:
                        # 从主数据库查询
                        for db_path in valid_db_paths:
                            try:
                                conn = sqlite3.connect(db_path)
                                cursor = conn.cursor()
                                cursor.execute("SELECT COUNT(*) FROM news WHERE source = ?", (source,))
                                count += cursor.fetchone()[0]
                                conn.close()
                            except Exception as e:
                                logger.warning(f"从数据库 {db_path} 统计{source}数量失败: {str(e)}")
                    
                    if count > 0:  # 只显示有新闻的来源
                        source_stats[source] = count
                        source_labels.append(source)
                        source_data.append(count)
            except Exception as e:
                logger.error(f"准备图表数据时出错: {str(e)}")
                logger.exception(e)
            
            # 记录调试信息
            logger.info(f"Dashboard图表数据: 来源({len(source_labels)}), 趋势({len(trend_labels)})")
            logger.debug(f"来源标签: {source_labels}")
            logger.debug(f"来源数据: {source_data}")
            logger.debug(f"趋势标签: {trend_labels}")
            logger.debug(f"趋势数据: {trend_data}")
            
            return render_template('dashboard.html',
                                total_news=total_news,
                                today_news=today_news,
                                sources=sources,
                                source_labels=source_labels,
                                source_data=source_data,
                                trend_labels=trend_labels,
                                trend_data=trend_data,
                                source_stats=source_stats)
        except Exception as e:
            logger.error(f"数据中心页面加载失败: {str(e)}")
            logger.exception(e)
            error_message = f"加载数据中心页面时发生错误: {str(e)}"
            try:
                return render_template('error.html', 
                                error=error_message,
                                traceback=traceback.format_exc()), 500
            except Exception as e2:
                logger.error(f"渲染错误页面失败: {str(e2)}")
                return f"严重错误: 数据中心页面加载失败 ({str(e)})", 500
    
    @app.route('/data_analysis')
    def data_analysis():
        """数据分析页面"""
        # 获取时间范围参数
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()
        
        # 重新导入确保使用最新的NewsDatabase类
        from importlib import reload
        from app.utils import database as db_module
        reload(db_module)
        from app.utils.database import NewsDatabase
        
        # 始终使用所有可用的数据库
        db = NewsDatabase(use_all_dbs=True)
        
        # 获取趋势数据
        trend_dates = []
        trend_counts = []
        current_date = start_date
        while current_date <= end_date:
            # 获取当天的新闻数量
            count = 0
            try:
                # 使用SQLite直接查询来获取特定日期的新闻数量
                date_str = current_date.strftime('%Y-%m-%d')
                for db_path in db.all_db_paths:
                    if os.path.exists(db_path):
                        try:
                            conn = sqlite3.connect(db_path)
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(*) FROM news WHERE pub_time LIKE ?", (f"{date_str}%",))
                            count += cursor.fetchone()[0]
                            conn.close()
                        except Exception as e:
                            logger.error(f"查询数据库 {db_path} 获取日期 {date_str} 的新闻数量失败: {str(e)}")
            except Exception as e:
                logger.error(f"计算日期 {date_str} 的新闻数量失败: {str(e)}")
            
            trend_dates.append(current_date.strftime('%Y-%m-%d'))
            trend_counts.append(count)
            current_date += timedelta(days=1)
        
        # 获取来源分布数据
        source_data = []
        sources = db.get_sources()
        total_count = sum(db.get_news_count(source=source) for source in sources)
        for source in sources:
            source_count = db.get_news_count(source=source)
            source_data.append({
                'name': source,
                'value': source_count,
                'percentage': round(source_count / total_count * 100, 1) if total_count > 0 else 0
            })
        
        # 获取关键词数据
        keyword_data = []
        keywords = []
        # 只有在db具有get_keywords方法时才调用
        if hasattr(db, 'get_keywords'):
            try:
                keywords = db.get_keywords(limit=50)
                if keywords:
                    max_count = max(keyword['count'] for keyword in keywords) if keywords else 1
                    for keyword in keywords:
                        keyword_data.append({
                            'name': keyword['word'],
                            'value': keyword['count'] / max_count * 100
                        })
            except Exception as e:
                logger.error(f"获取关键词数据失败: {str(e)}")
                keywords = []
                
        # 获取分类统计
        categories = []
        # 添加兼容层，检查方法是否存在
        if hasattr(db, 'get_categories'):
            for category in db.get_categories():
                # 如果category已经是字典格式，直接使用
                if isinstance(category, dict) and 'name' in category and 'count' in category:
                    categories.append({
                        'name': category['name'],
                        'count': category['count'],
                        'percentage': round(category['count'] / total_count * 100, 1) if total_count > 0 else 0,
                        'trend': '↑' if category.get('trend', 0) > 0 else '↓',
                        'trend_color': 'success' if category.get('trend', 0) > 0 else 'danger'
                    })
                # 如果category只是分类名称，需要查询计数
                else:
                    category_name = category
                    # 添加兼容层，检查方法是否存在
                    if hasattr(db, 'get_news_count'):
                        category_count = db.get_news_count(keyword=category_name)
                    else:
                        category_count = 0
                    categories.append({
                        'name': category_name,
                        'count': category_count,
                        'percentage': round(category_count / total_count * 100, 1) if total_count > 0 else 0,
                        'trend': '↑',  # 默认趋势
                        'trend_color': 'success'
                    })
        else:
            logger.warning("数据库对象不支持get_categories方法，将使用空列表")
        
        return render_template('data_analysis.html',
                             start_date=start_date.strftime('%Y-%m-%d'),
                             end_date=end_date.strftime('%Y-%m-%d'),
                             trend_dates=trend_dates,
                             trend_counts=trend_counts,
                             source_data=source_data,
                             keyword_data=keyword_data,
                             categories=categories)
    
    @app.route('/settings')
    def settings():
        """系统设置页面"""
        try:
            # 获取当前系统配置
            settings = get_settings()
            
            # 获取数据库信息
            db_dir = settings.get('DB_DIR', os.environ.get('DB_DIR', 'data/db'))
            if not os.path.isabs(db_dir):
                db_dir = os.path.join(os.getcwd(), db_dir)
            
            db_files = []
            db_size_total = 0
            
            if os.path.exists(db_dir):
                for file in os.listdir(db_dir):
                    if file.endswith('.db'):
                        file_path = os.path.join(db_dir, file)
                        size = os.path.getsize(file_path)
                        db_size_total += size
                        db_files.append({
                            'name': file,
                            'size': size / (1024 * 1024),  # MB
                            'modified': datetime.fromtimestamp(os.path.getmtime(file_path))
                        })
            
            # 系统信息
            system_info = {
                'os': platform.platform(),
                'python': platform.python_version(),
                'cpu': {
                    'count': psutil.cpu_count(),
                    'percent': psutil.cpu_percent(interval=1)
                },
                'memory': {
                    'total': psutil.virtual_memory().total / (1024 * 1024 * 1024),  # GB
                    'used': psutil.virtual_memory().used / (1024 * 1024 * 1024),  # GB
                    'percent': psutil.virtual_memory().percent
                },
                'disk': {
                    'total': psutil.disk_usage('/').total / (1024 * 1024 * 1024),  # GB
                    'used': psutil.disk_usage('/').used / (1024 * 1024 * 1024),  # GB
                    'percent': psutil.disk_usage('/').percent
                }
            }
            
            return render_template('settings.html',
                                settings=settings,
                                db_dir=db_dir,
                                db_files=db_files,
                                db_size_total=db_size_total / (1024 * 1024),  # MB
                                system_info=system_info)
        except Exception as e:
            logger.error(f"系统设置页面加载失败: {str(e)}")
            logger.exception(e)
            error_message = f"加载系统设置页面时发生错误: {str(e)}"
            return render_template('error.html', 
                                error=error_message,
                                traceback=traceback.format_exc()), 500
    
    # API路由
    @app.route('/api/crawlers/<n>/start', methods=['POST'])
    def start_crawler(n):
        """启动指定爬虫"""
        if not hasattr(app, 'crawler_manager') or app.crawler_manager is None:
            logger.error("爬虫管理器未初始化或不可用")
            return jsonify({'success': False, 'message': "爬虫管理器未初始化或不可用"})
        
        try:
            app.crawler_manager.start_crawler(n)
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"启动爬虫失败: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/api/crawlers/<n>/stop', methods=['POST'])
    def stop_crawler(n):
        """停止指定爬虫"""
        if not hasattr(app, 'crawler_manager') or app.crawler_manager is None:
            logger.error("爬虫管理器未初始化或不可用")
            return jsonify({'success': False, 'message': "爬虫管理器未初始化或不可用"})
        
        try:
            app.crawler_manager.stop_crawler(n)
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"停止爬虫失败: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/api/crawlers/start_all', methods=['POST'])
    def start_all_crawlers():
        """启动所有爬虫"""
        if not hasattr(app, 'crawler_manager') or app.crawler_manager is None:
            logger.error("爬虫管理器未初始化或不可用")
            return jsonify({'success': False, 'message': "爬虫管理器未初始化或不可用"})
        
        try:
            app.crawler_manager.start_all()
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"启动所有爬虫失败: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/api/crawlers/<crawler_name>/start_fixed', methods=['POST'])
    def start_crawler_fixed(crawler_name):
        """启动指定爬虫 (修复版)"""
        if not hasattr(app, 'crawler_manager') or app.crawler_manager is None:
            logger.error("爬虫管理器未初始化或不可用")
            return jsonify({'success': False, 'message': "爬虫管理器未初始化或不可用"})
        
        try:
            app.crawler_manager.start_crawler(crawler_name)
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"启动爬虫失败: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/api/crawlers/<crawler_name>/stop_fixed', methods=['POST'])
    def stop_crawler_fixed(crawler_name):
        """停止指定爬虫 (修复版)"""
        if not hasattr(app, 'crawler_manager') or app.crawler_manager is None:
            logger.error("爬虫管理器未初始化或不可用")
            return jsonify({'success': False, 'message': "爬虫管理器未初始化或不可用"})
        
        try:
            app.crawler_manager.stop_crawler(crawler_name)
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"停止爬虫失败: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/api/settings/crawler', methods=['POST'])
    def update_crawler_settings():
        """更新爬虫设置"""
        try:
            settings = get_settings()
            
            # 准备更新的设置
            update_data = {
                'crawler_interval': int(request.form.get('crawler_interval', 30)),
                'max_crawlers': int(request.form.get('max_crawlers', 3)),
                'request_timeout': int(request.form.get('request_timeout', 30)),
                'max_retries': int(request.form.get('max_retries', 3)),
                'proxy_mode': request.form.get('proxy_mode', 'none'),
                'proxy_url': request.form.get('proxy_url', '')
            }
            
            # 检查settings是否有save_settings方法
            if hasattr(settings, 'save_settings') and callable(settings.save_settings):
                # 有save_settings方法，更新并保存
                settings.update(update_data)
                settings.save_settings()
            else:
                # 没有save_settings方法，只更新内存中的设置
                for key, value in update_data.items():
                    settings[key] = value
                logger.info("已更新爬虫设置（仅内存）")
                
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"更新爬虫设置失败: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/api/settings/database', methods=['POST'])
    def update_database_settings():
        """更新数据库设置"""
        try:
            settings = get_settings()
            
            # 准备更新的设置
            update_data = {
                'db_type': request.form.get('db_type', 'sqlite'),
                'db_host': request.form.get('db_host', 'localhost'),
                'db_port': int(request.form.get('db_port', 3306)),
                'db_name': request.form.get('db_name', 'news'),
                'db_user': request.form.get('db_user', 'root'),
                'db_password': request.form.get('db_password', '')
            }
            
            # 检查settings是否有save_settings方法
            if hasattr(settings, 'save_settings') and callable(settings.save_settings):
                # 有save_settings方法，更新并保存
                settings.update(update_data)
                settings.save_settings()
            else:
                # 没有save_settings方法，只更新内存中的设置
                for key, value in update_data.items():
                    settings[key] = value
                logger.info("已更新数据库设置（仅内存）")
                
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"更新数据库设置失败: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/api/settings/log', methods=['POST'])
    def update_log_settings():
        """更新日志设置"""
        try:
            settings = get_settings()
            
            # 准备更新的设置
            update_data = {
                'log_level': request.form.get('log_level', 'INFO'),
                'log_max_size': int(request.form.get('log_max_size', 10)),
                'log_backup_count': int(request.form.get('log_backup_count', 5))
            }
            
            # 检查settings是否有save_settings方法
            if hasattr(settings, 'save_settings') and callable(settings.save_settings):
                # 有save_settings方法，更新并保存
                settings.update(update_data)
                settings.save_settings()
            else:
                # 没有save_settings方法，只更新内存中的设置
                for key, value in update_data.items():
                    settings[key] = value
                logger.info("已更新日志设置（仅内存）")
                
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"更新日志设置失败: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/news/<news_id>')
    def news_detail(news_id):
        """新闻详情页"""
        try:
            # 使用所有数据库进行查询 - 使用with语句确保线程安全
            with NewsDatabase(use_all_dbs=True) as db:
                # 根据ID查询新闻
                if hasattr(db, 'get_news_by_id'):
                    news = db.get_news_by_id(news_id)
                else:
                    news = None
                    logger.warning(f"数据库对象不支持get_news_by_id方法，无法直接通过ID {news_id} 查询新闻")
                
                if not news:
                    logger.warning(f"未找到ID为{news_id}的新闻")
                    # 尝试通过URL查找news_id的新闻
                    try:
                        # 查询是否有url中含有news_id的新闻
                        db_path = get_db_path('finance_news.db')
                        with SQLiteManager(db_path=db_path) as db_manager:
                            cursor = db_manager.conn.cursor()
                            cursor.execute("SELECT * FROM news WHERE url LIKE ?", (f'%{news_id}%',))
                            row = cursor.fetchone()
                            
                            if row:
                                # 找到基于URL的新闻，重定向到该新闻详情页
                                found_news = dict(row)
                                correct_id = found_news.get('id')
                                if correct_id:
                                    logger.info(f"找到基于URL的新闻，重定向到正确的ID: {correct_id}")
                                    return redirect(url_for('news_detail', news_id=correct_id))
                    except Exception as e:
                        logger.error(f"尝试通过URL查找失败: {str(e)}")
                        
                    # 如果所有尝试都失败，返回找不到页面
                    return render_template('error.html', 
                                        error=f"未找到ID为 {news_id} 的新闻", 
                                        error_details="您请求的新闻可能已被删除或移动到其他位置。",
                                        back_url=url_for('index')), 404
                
                # 确保news有id属性，如果没有，添加它
                if 'id' not in news:
                    news['id'] = news_id
                    logger.warning(f"新闻对象缺少id属性，已手动添加: {news_id}")
                
                # 适配字段名称变化：处理content/content_html和text_content/html_content的兼容
                if 'text_content' in news and not 'content' in news:
                    news['content'] = news['text_content']
                    logger.debug(f"字段适配: 从text_content复制到content")
                
                if 'html_content' in news and news['html_content']:
                    # 优先使用html_content作为显示内容
                    news['content'] = news['html_content']
                    logger.debug(f"字段适配: 使用html_content作为显示内容")
                elif 'content_html' in news and news['content_html']:
                    # 其次使用content_html作为显示内容
                    news['content'] = news['content_html']
                    logger.debug(f"字段适配: 使用content_html作为显示内容")
                
                # 格式化新闻内容，提升阅读体验
                if news.get('content'):
                    # 过滤凤凰网浏览器提示弹窗
                    if news.get('source') == '凤凰财经':
                        # 去除浏览器升级提示
                        browser_tip_pattern = r'亲爱的凤凰网用户[\s\S]*?浏览器.*?下载'
                        news['content'] = re.sub(browser_tip_pattern, '', news['content'])
                    
                    # 确保段落格式正确
                    if not '<p' in news['content'] and not '<div' in news['content']:
                        news['content'] = format_for_display(news['content'])
                
                # 获取新闻关键词，并转换为列表格式
                if news.get('keywords') and isinstance(news['keywords'], str):
                    news['keywords'] = [k.strip() for k in news['keywords'].split(',') if k.strip()]
                
                # 提取图片（如果尚未提取）
                if not news.get('images') and news.get('content'):
                    try:
                        # 创建BeautifulSoup对象处理内容中的图片
                        soup = BeautifulSoup(news['content'], 'html.parser')
                        images = []
                        
                        # 提取图片
                        for img in soup.find_all('img'):
                            img_url = img.get('src', '')
                            if img_url and img_url.startswith(('http://', 'https://')):
                                alt_text = img.get('alt', '').strip() or '新闻图片'
                                images.append({
                                    'url': img_url,
                                    'alt': alt_text,
                                    'original_url': img_url
                                })
                                
                                # 为图片添加响应式类、懒加载和错误处理
                                img['loading'] = 'lazy'
                                img_classes = img.get('class', [])
                                if isinstance(img_classes, str):
                                    img_classes = [img_classes]
                                if 'img-fluid' not in img_classes:
                                    img_classes.append('img-fluid')
                                if 'rounded' not in img_classes:
                                    img_classes.append('rounded')
                                img['class'] = img_classes
                                
                                # 添加图片加载错误处理
                                img['onerror'] = "this.onerror=null; this.src='/static/img/image-error.jpg'; this.alt='图片加载失败';"
                                
                        news['images'] = images
                        news['content'] = str(soup)
                    except Exception as e:
                        logger.error(f"提取图片失败: {str(e)}")
                
                # 获取相关新闻
                related_news = []
                if news.get('keywords'):
                    # 将关键词列表或字符串转换为查询字符串
                    keywords = news['keywords']
                    if isinstance(keywords, str):
                        keywords = keywords.split(',')[0].strip()
                    elif isinstance(keywords, list) and keywords:
                        keywords = keywords[0]  # 只用第一个关键词查询相关新闻
                    
                    if keywords:
                        # 查询相关新闻，然后手动排除当前新闻ID
                        if hasattr(db, 'query_news'):
                            results = db.query_news(
                                keyword=keywords,
                                days=30,  # 最近30天的相关新闻
                                limit=10  # 获取更多结果，以便过滤后仍有足够的内容
                            )
                        else:
                            # 如果不支持query_news方法，使用空列表
                            results = []
                            logger.warning(f"数据库对象不支持query_news方法，无法查询关键词为 {keywords} 的相关新闻")
                        
                        # 手动过滤掉当前新闻
                        related_news = [item for item in results if item.get('id') != news_id][:5]  # 只保留5条
                
                # 设置相关新闻
                news['related'] = related_news
            
            # 获取用户偏好信息
            user_id = 'default_user'  # 默认用户
            is_saved = False
            is_read = False
            
            try:
                # 创建用户偏好数据库 - 使用with语句确保线程安全
                with UserPreferencesDB() as user_prefs_db:
                    # 检查该新闻是否被保存和已读
                    is_saved = user_prefs_db.is_saved(user_id, news_id)
                    is_read = user_prefs_db.is_read(user_id, news_id)
                    
                    # 标记新闻为已读
                    user_prefs_db.mark_as_read(user_id, news_id)
                    logger.info(f"已将新闻 {news_id} 标记为用户 {user_id} 已读")
            except Exception as e:
                logger.error(f"用户偏好数据库操作失败: {str(e)}")
                logger.exception(e)
            
            # 渲染模板
            return render_template('news_detail.html',
                                news=news,
                                # 用户偏好
                                is_saved=is_saved,
                                is_read=is_read,
                                user_id=user_id)
                            
        except Exception as e:
            logger.error(f"加载新闻详情失败: {str(e)}")
            logger.exception(e)
            error_message = f"加载新闻详情时发生错误: {str(e)}"
            try:
                return render_template(
                    'error.html', 
                    error=error_message,
                    traceback=traceback.format_exc()
                ), 500
            except Exception as e2:
                logger.error(f"渲染错误页面失败: {str(e2)}")
                return f"严重错误: 新闻详情加载失败 ({str(e)}), 错误页面也无法加载 ({str(e2)})", 500
    
    @app.route('/stats')
    def stats():
        """数据统计页"""
        # 重新导入确保使用最新的NewsDatabase类
        from importlib import reload
        from app.utils import database as db_module
        reload(db_module)
        from app.utils.database import NewsDatabase
        
        db = NewsDatabase(use_all_dbs=True)
        
        # 获取新闻总数
        if hasattr(db, 'get_news_count'):
            total_count = db.get_news_count()
        else:
            total_count = 0
            logger.warning("数据库对象不支持get_news_count方法，使用默认值0")
        
        # 获取来源分布
        if hasattr(db, 'get_sources'):
            sources = db.get_sources()
            
            # 获取各来源的新闻数量
            source_stats = {}
            if hasattr(db, 'get_news_count'):
                source_stats = {source: db.get_news_count(source=source) for source in sources}
            else:
                source_stats = {source: 0 for source in sources}
                logger.warning("数据库对象不支持get_news_count方法，无法获取来源统计")
        else:
            sources = []
            source_stats = {}
            logger.warning("数据库对象不支持get_sources方法，使用空列表")
        
        # 获取情感分布
        sentiment_stats = {
            '积极': db.get_news_count_by_sentiment(0.3, 1.0) if hasattr(db, 'get_news_count_by_sentiment') else 0,
            '中性': db.get_news_count_by_sentiment(-0.3, 0.3) if hasattr(db, 'get_news_count_by_sentiment') else 0,
            '消极': db.get_news_count_by_sentiment(-1.0, -0.3) if hasattr(db, 'get_news_count_by_sentiment') else 0
        }
        
        # 获取更详细的情感分布
        sentiment_distribution = {}
        try:
            if hasattr(db, 'get_sentiment_distribution'):
                sentiment_distribution = db.get_sentiment_distribution(buckets=5)
                logger.info(f"获取情感分布: {sentiment_distribution}")
            else:
                # 手动计算情感分布
                sentiment_distribution = {
                    "-1.0~-0.6": db.get_news_count_by_sentiment(-1.0, -0.6) if hasattr(db, 'get_news_count_by_sentiment') else 0,
                    "-0.6~-0.2": db.get_news_count_by_sentiment(-0.6, -0.2) if hasattr(db, 'get_news_count_by_sentiment') else 0,
                    "-0.2~0.2": db.get_news_count_by_sentiment(-0.2, 0.2) if hasattr(db, 'get_news_count_by_sentiment') else 0,
                    "0.2~0.6": db.get_news_count_by_sentiment(0.2, 0.6) if hasattr(db, 'get_news_count_by_sentiment') else 0,
                    "0.6~1.0": db.get_news_count_by_sentiment(0.6, 1.0) if hasattr(db, 'get_news_count_by_sentiment') else 0
                }
        except Exception as e:
            logger.error(f"获取情感分布失败: {str(e)}")
            sentiment_distribution = {
                "-1.0~-0.6": 0,
                "-0.6~-0.2": 0,
                "-0.2~0.2": 0,
                "0.2~0.6": 0,
                "0.6~1.0": 0
            }
        
        return render_template(
            'stats.html',
            total_count=total_count,
            source_stats=source_stats,
            sentiment_stats=sentiment_stats,
            sentiment_distribution=sentiment_distribution
        )

    @app.route('/database/select_source')
    def select_source():
        """切换数据源"""
        source = request.args.get('source', 'all')
        
        # 保存选择到会话
        if hasattr(app, 'session'):
            app.session['selected_source'] = source
        
        # 重定向回爬虫管理页面
        flash(f'已切换到数据源: {source}', 'success')
        return redirect(url_for('crawler'))
    
    @app.route('/database/backup', methods=['POST'])
    def backup_database():
        """备份数据库"""
        source = request.form.get('source')
        
        try:
            # 根据选择的数据源进行备份
            if source == 'main':
                source = None  # 主数据库使用None表示
                
            # 获取数据库管理器
            db = None
            if hasattr(app, 'db'):
                db = app.db
            else:
                # 使用NewsDatabase获取数据库连接
                db = NewsDatabase()
            
            # 执行备份
            backup_path = db.backup_database(source)
            
            if backup_path:
                flash(f'成功创建备份: {os.path.basename(backup_path)}', 'success')
            else:
                flash('备份失败', 'error')
                
            # 关闭连接
            if db and not hasattr(app, 'db'):
                db.close()
                
        except Exception as e:
            logger.error(f"备份数据库失败: {str(e)}")
            flash(f'备份失败: {str(e)}', 'error')
            
        return redirect(url_for('crawler'))
    
    @app.route('/database/restore', methods=['GET', 'POST'])
    def restore_database():
        """恢复数据库"""
        # 处理GET和POST请求
        if request.method == 'POST':
            backup_file = request.form.get('backup_file')
            target_source = request.form.get('target_source')
        else:
            backup_file = request.args.get('backup_file')
            target_source = request.args.get('target_source')
        
        if not backup_file:
            flash('缺少备份文件', 'error')
            return redirect(url_for('crawler'))
            
        try:
            # 处理目标数据源
            if target_source == 'main':
                target_source = None  # 主数据库使用None表示
                
            # 获取数据库管理器
            db = None
            if hasattr(app, 'db'):
                db = app.db
            else:
                # 使用NewsDatabase获取数据库连接
                db = NewsDatabase()
            
            # 执行恢复
            success = db.restore_database(backup_file, target_source)
            
            if success:
                flash(f'成功恢复数据库: {os.path.basename(backup_file)}', 'success')
            else:
                flash('恢复失败', 'error')
                
            # 关闭连接
            if db and not hasattr(app, 'db'):
                db.close()
                
        except Exception as e:
            logger.error(f"恢复数据库失败: {str(e)}")
            flash(f'恢复失败: {str(e)}', 'error')
            
        return redirect(url_for('crawler'))
    
    @app.route('/database/download')
    def download_backup():
        """下载备份文件"""
        backup_file = request.args.get('backup_file')
        
        if not backup_file or not os.path.exists(backup_file):
            flash('备份文件不存在', 'error')
            return redirect(url_for('crawler'))
            
        try:
            # 获取文件名
            filename = os.path.basename(backup_file)
            
            # 发送文件
            return send_file(
                backup_file,
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )
        except Exception as e:
            logger.error(f"下载备份文件失败: {str(e)}")
            flash(f'下载失败: {str(e)}', 'error')
            return redirect(url_for('crawler'))
    
    @app.route('/database/delete_backup')
    def delete_backup():
        """删除备份文件"""
        backup_file = request.args.get('backup_file')
        
        if not backup_file or not os.path.exists(backup_file):
            flash('备份文件不存在', 'error')
            return redirect(url_for('crawler'))
            
        try:
            # 删除文件
            os.remove(backup_file)
            flash(f'成功删除备份文件: {os.path.basename(backup_file)}', 'success')
        except Exception as e:
            logger.error(f"删除备份文件失败: {str(e)}")
            flash(f'删除失败: {str(e)}', 'error')
            
        return redirect(url_for('crawler'))
    
    @app.route('/database/sync_all')
    def sync_all_sources():
        """同步所有数据源到主数据库"""
        try:
            # 获取数据库管理器
            db = None
            if hasattr(app, 'db'):
                db = app.db
            else:
                # 使用NewsDatabase获取数据库连接
                db = NewsDatabase()
            
            # 获取所有数据源
            sources = db.get_available_sources()
            
            # 执行同步
            total_synced = 0
            for source in sources:
                count = db.sync_to_main_db(source)
                total_synced += count
                
            if total_synced > 0:
                flash(f'成功同步 {total_synced} 条新闻到主数据库', 'success')
            else:
                flash('没有新的内容需要同步', 'info')
                
            # 关闭连接
            if db and not hasattr(app, 'db'):
                db.close()
                
        except Exception as e:
            logger.error(f"同步数据库失败: {str(e)}")
            flash(f'同步失败: {str(e)}', 'error')
            
        return redirect(url_for('crawler'))

    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"500错误: {str(error)}")
        try:
            return render_template('500.html', error_message=str(error)), 500
        except Exception as e:
            logger.error(f"渲染500页面失败: {str(e)}")
            return "500 - 服务器错误", 500