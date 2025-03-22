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
from flask import render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from app.utils.database import NewsDatabase
from app.utils.logger import get_logger
from app.config import get_settings
import sqlite3

logger = get_logger(__name__)

def register_routes(app):
    """注册路由"""
    
    @app.route('/')
    def index():
        """首页"""
        # 获取查询参数
        keyword = request.args.get('keyword', '')
        source = request.args.get('source', '')
        days = request.args.get('days', '7')
        page = request.args.get('page', '1')
        view_mode = request.args.get('view', 'list')
        
        try:
            days = int(days)
            page = int(page)
        except ValueError:
            days = 7
            page = 1
        
        # 每页显示的新闻数量
        per_page = 10
        
        # 查询数据库 - 使用优化后的数据库类，并搜索所有数据库
        db = NewsDatabase(use_all_dbs=True)
        news_list = db.query_news(
            keyword=keyword if keyword else None,
            days=days,
            source=source if source else None,
            limit=per_page,
            offset=(page - 1) * per_page
        )
        
        # 获取总数
        total_count = db.get_news_count(
            keyword=keyword if keyword else None,
            days=days,
            source=source if source else None
        )
        
        # 获取新闻来源列表
        sources = db.get_sources()
        
        # 获取统计数据
        today = datetime.now().date()
        today_count = db.get_news_count(days=1)
        source_count = len(sources)
        categories = db.get_categories()
        category_count = len(categories)
        
        # 计算总页数
        total_pages = (total_count + per_page - 1) // per_page
        
        return render_template('index.html',
                             news_list=news_list,
                             total_news=total_count,
                             today_news=today_count,
                             source_count=source_count,
                             category_count=category_count,
                             total_pages=total_pages,
                             current_page=page,
                             keyword=keyword,
                             source=source,
                             days=days,
                             view_mode=view_mode,
                             sources=sources)
    
    @app.route('/crawler_status')
    def crawler_status():
        """爬虫状态页面"""
        db = NewsDatabase(use_all_dbs=True)
        
        # 获取统计数据
        today = datetime.now().date()
        today_count = db.get_news_count(days=1)
        week_count = db.get_news_count(days=7)
        month_count = db.get_news_count(days=30)
        total_count = db.get_news_count()
        
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
        
        db = NewsDatabase()
        
        # 获取趋势数据
        trend_dates = []
        trend_counts = []
        current_date = start_date
        while current_date <= end_date:
            count = db.get_news_count(start_date=current_date, end_date=current_date + timedelta(days=1))
            trend_dates.append(current_date.strftime('%Y-%m-%d'))
            trend_counts.append(count)
            current_date += timedelta(days=1)
        
        # 获取来源分布数据
        source_data = []
        sources = db.get_sources()
        total_count = sum(source['count'] for source in sources)
        for source in sources:
            source_data.append({
                'name': source['name'],
                'value': source['count'],
                'percentage': round(source['count'] / total_count * 100, 1)
            })
        
        # 获取关键词数据
        keyword_data = []
        keywords = db.get_keywords(limit=50)
        max_count = max(keyword['count'] for keyword in keywords) if keywords else 1
        for keyword in keywords:
            keyword_data.append({
                'name': keyword['word'],
                'value': keyword['count'] / max_count * 100
            })
        
        # 获取分类统计
        categories = []
        for category in db.get_categories():
            categories.append({
                'name': category['name'],
                'count': category['count'],
                'percentage': round(category['count'] / total_count * 100, 1),
                'trend': '↑' if category['trend'] > 0 else '↓',
                'trend_color': 'success' if category['trend'] > 0 else 'danger'
            })
        
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
        settings = get_settings()
        
        # 获取系统信息
        system_info = {
            'version': '1.0.0',
            'python_version': platform.python_version(),
            'os': f"{platform.system()} {platform.release()}",
            'cpu_count': psutil.cpu_count(),
            'memory_usage': f"{psutil.virtual_memory().percent}%",
            'db_size': '计算中...',  # TODO: 实现数据库大小计算
            'log_size': '计算中...',  # TODO: 实现日志大小计算
            'uptime': str(datetime.now() - datetime.fromtimestamp(psutil.boot_time())).split('.')[0],
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return render_template('settings.html',
                             settings=settings,
                             system_info=system_info)
    
    # API路由
    @app.route('/api/crawlers/<name>/start', methods=['POST'])
    def start_crawler(name):
        """启动指定爬虫"""
        if not hasattr(app, 'crawler_manager') or app.crawler_manager is None:
            logger.error("爬虫管理器未初始化或不可用")
            return jsonify({'success': False, 'message': "爬虫管理器未初始化或不可用"})
        
        try:
            app.crawler_manager.start_crawler(name)
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"启动爬虫失败: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/api/crawlers/<name>/stop', methods=['POST'])
    def stop_crawler(name):
        """停止指定爬虫"""
        if not hasattr(app, 'crawler_manager') or app.crawler_manager is None:
            logger.error("爬虫管理器未初始化或不可用")
            return jsonify({'success': False, 'message': "爬虫管理器未初始化或不可用"})
        
        try:
            app.crawler_manager.stop_crawler(name)
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
    
    @app.route('/api/settings/crawler', methods=['POST'])
    def update_crawler_settings():
        """更新爬虫设置"""
        try:
            settings = get_settings()
            settings.update({
                'crawler_interval': int(request.form.get('crawler_interval', 30)),
                'max_crawlers': int(request.form.get('max_crawlers', 3)),
                'request_timeout': int(request.form.get('request_timeout', 30)),
                'max_retries': int(request.form.get('max_retries', 3)),
                'proxy_mode': request.form.get('proxy_mode', 'none'),
                'proxy_url': request.form.get('proxy_url', '')
            })
            settings.save()
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"更新爬虫设置失败: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/api/settings/database', methods=['POST'])
    def update_database_settings():
        """更新数据库设置"""
        try:
            settings = get_settings()
            settings.update({
                'db_type': request.form.get('db_type', 'sqlite'),
                'db_host': request.form.get('db_host', 'localhost'),
                'db_port': int(request.form.get('db_port', 3306)),
                'db_name': request.form.get('db_name', 'news'),
                'db_user': request.form.get('db_user', 'root'),
                'db_password': request.form.get('db_password', '')
            })
            settings.save()
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"更新数据库设置失败: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/api/settings/log', methods=['POST'])
    def update_log_settings():
        """更新日志设置"""
        try:
            settings = get_settings()
            settings.update({
                'log_level': request.form.get('log_level', 'INFO'),
                'log_max_size': int(request.form.get('log_max_size', 10)),
                'log_backup_count': int(request.form.get('log_backup_count', 5))
            })
            settings.save()
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"更新日志设置失败: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/news/<news_id>')
    def news_detail(news_id):
        """新闻详情页"""
        # 查询数据库
        db = NewsDatabase(use_all_dbs=True)
        
        # 获取新闻数据
        news = None
        
        # 尝试直接使用sqlite3连接查询所有数据库
        for db_path in db.all_db_paths:
            try:
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 查询指定ID的新闻
                cursor.execute("SELECT * FROM news WHERE id = ?", (news_id,))
                row = cursor.fetchone()
                
                if row:
                    # 转换为字典
                    news = {}
                    for i, column in enumerate(cursor.description):
                        news[column[0]] = row[i]
                    break  # 找到后跳出循环
                    
                conn.close()
            except Exception as e:
                logger.error(f"查询新闻详情失败: {str(e)}")
        
        if not news:
            flash('新闻不存在或已被删除', 'danger')
            return redirect(url_for('index'))
            
        # 查询相关新闻
        related_news = []
        if 'keywords' in news and news['keywords']:
            try:
                # 从关键词中提取查询条件
                if isinstance(news['keywords'], str):
                    try:
                        keywords = json.loads(news['keywords'])
                    except:
                        keywords = news['keywords'].split(',')
                else:
                    keywords = news['keywords']
                
                if keywords:
                    # 使用第一个关键词查询
                    keyword = keywords[0] if isinstance(keywords, list) else keywords
                    related_news = db.query_news(
                        keyword=keyword,
                        limit=5,
                        source=news.get('source')
                    )
            except Exception as e:
                logger.error(f"查询相关新闻失败: {str(e)}")
        
        return render_template('news_detail.html', news=news, related_news=related_news)
    
    @app.route('/stats')
    def stats():
        """数据统计页"""
        db = NewsDatabase()
        
        # 获取新闻总数
        total_count = db.count_news()
        
        # 获取来源分布
        sources = db.get_sources()
        source_stats = {source: db.count_news(source=source) for source in sources}
        
        # 获取情感分布
        sentiment_stats = {
            '积极': db.count_news_by_sentiment(0.5, 1.0),
            '中性': db.count_news_by_sentiment(0.3, 0.7),
            '消极': db.count_news_by_sentiment(0.0, 0.3)
        }
        
        return render_template(
            'stats.html',
            total_count=total_count,
            source_stats=source_stats,
            sentiment_stats=sentiment_stats
        )
    
    @app.route('/search')
    def search():
        """搜索页面"""
        return redirect(url_for('index', 
                               keyword=request.args.get('keyword', ''),
                               source=request.args.get('source', ''),
                               days=request.args.get('days', '7')))
    
    @app.route('/feedback', methods=['GET', 'POST'])
    def feedback():
        """反馈页面"""
        if request.method == 'POST':
            # 接收反馈信息
            feedback_data = {
                'id': str(uuid.uuid4()),
                'feedback_type': request.form.get('feedback_type'),
                'title': request.form.get('title'),
                'content': request.form.get('content'),
                'email': request.form.get('email'),
                'urgent': request.form.get('urgent') == 'on',
                'status': 'pending',
                'submit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 保存反馈
            try:
                db = NewsDatabase(use_all_dbs=True)
                
                # 尝试直接使用sqlite3连接插入数据
                conn = sqlite3.connect(db.db_path)
                cursor = conn.cursor()
                
                # 插入反馈
                cursor.execute('''
                INSERT INTO feedback (id, feedback_type, title, content, email, urgent, status, submit_time, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    feedback_data['id'],
                    feedback_data['feedback_type'],
                    feedback_data['title'],
                    feedback_data['content'],
                    feedback_data['email'],
                    1 if feedback_data['urgent'] else 0,
                    feedback_data['status'],
                    feedback_data['submit_time'],
                    feedback_data['update_time']
                ))
                
                conn.commit()
                conn.close()
                
                flash('感谢您的反馈！我们会尽快处理。', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                logger.error(f"保存反馈失败: {str(e)}")
                flash('反馈提交失败，请稍后再试。', 'danger')
        
        return render_template('feedback.html')
    
    @app.route('/about')
    def about():
        """关于页面"""
        return render_template('about.html')
    
    @app.route('/api/news')
    def api_news():
        """API: 获取新闻列表"""
        # 获取查询参数
        keyword = request.args.get('keyword', '')
        source = request.args.get('source', '')
        days = request.args.get('days', '7')
        page = request.args.get('page', '1')
        limit = request.args.get('limit', '10')
        
        try:
            days = int(days)
            page = int(page)
            limit = int(limit)
        except ValueError:
            days = 7
            page = 1
            limit = 10
            
        # 查询数据库
        db = NewsDatabase(use_all_dbs=True)
        news_list = db.query_news(
            keyword=keyword if keyword else None,
            days=days,
            source=source if source else None,
            limit=limit,
            offset=(page - 1) * limit
        )
        
        # 获取总数
        total_count = db.get_news_count(
            keyword=keyword if keyword else None,
            days=days,
            source=source if source else None
        )
        
        # 计算总页数
        total_pages = (total_count + limit - 1) // limit
        
        return jsonify({
            'news': news_list,
            'total': total_count,
            'page': page,
            'limit': limit,
            'total_pages': total_pages
        })
    
    @app.route('/api/news/<news_id>')
    def api_news_detail(news_id):
        """新闻详情API"""
        db = NewsDatabase()
        news = db.get_news_by_id(news_id)
        
        if not news:
            return jsonify({
                'code': 404,
                'msg': 'news not found',
                'data': None
            })
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': news
        })
    
    @app.route('/api/sources')
    def api_sources():
        """新闻源API"""
        db = NewsDatabase()
        sources = db.get_sources()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': sources
        })
    
    @app.route('/api/stats')
    def api_stats():
        """统计数据API"""
        db = NewsDatabase()
        
        # 获取新闻总数
        total_count = db.count_news()
        
        # 获取来源分布
        sources = db.get_sources()
        source_stats = {source: db.count_news(source=source) for source in sources}
        
        # 获取情感分布
        sentiment_stats = {
            'positive': db.count_news_by_sentiment(0.5, 1.0),
            'neutral': db.count_news_by_sentiment(0.3, 0.7),
            'negative': db.count_news_by_sentiment(0.0, 0.3)
        }
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'total': total_count,
                'sources': source_stats,
                'sentiment': sentiment_stats
            }
        })
    
    @app.route('/api/stats/sources')
    def api_stats_sources():
        """API: 获取来源统计"""
        db = NewsDatabase(use_all_dbs=True)
        sources = db.get_sources()
        
        # 计算每个来源的新闻数
        result = []
        for source in sources:
            count = db.get_news_count(source=source)
            result.append({'name': source, 'count': count})
        
        # 按数量排序
        result.sort(key=lambda x: x['count'], reverse=True)
        
        return jsonify(result)
    
    @app.route('/api/stats/daily')
    def api_stats_daily():
        """API: 获取每日新闻数统计"""
        days = request.args.get('days', '30')
        try:
            days = int(days)
        except ValueError:
            days = 30
            
        db = NewsDatabase(use_all_dbs=True)
        
        # 生成日期范围
        today = datetime.now().date()
        date_range = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
        date_range.reverse()  # 从早到晚排序
        
        # 统计每天的新闻数
        news_counts = []
        for date in date_range:
            # 尝试直接使用sqlite3连接查询所有数据库
            total_count = 0
            for db_path in db.all_db_paths:
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # 查询当天的新闻数
                    cursor.execute("SELECT COUNT(*) FROM news WHERE pub_time LIKE ?", (f"{date}%",))
                    count = cursor.fetchone()[0]
                    total_count += count
                    
                    conn.close()
                except Exception as e:
                    logger.error(f"查询日期统计失败: {str(e)}")
            
            news_counts.append(total_count)
            
        return jsonify({
            'dates': date_range,
            'counts': news_counts
        })
    
    @app.errorhandler(404)
    def page_not_found(e):
        """404页面"""
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        """500页面"""
        return render_template('500.html'), 500 