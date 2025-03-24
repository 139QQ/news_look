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
        
        # 查询数据库
        db = NewsDatabase()
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
        db = NewsDatabase()
        
        # 获取统计数据
        today = datetime.now().date()
        today_count = db.get_news_count(days=1)
        week_count = db.get_news_count(days=7)
        month_count = db.get_news_count(days=30)
        total_count = db.get_news_count()
        
        # 获取爬虫状态
        crawlers = []
        # 检查crawler_manager是否存在且可用
        if hasattr(app, 'crawler_manager') and app.crawler_manager is not None:
            try:
                for crawler in app.crawler_manager.get_crawlers():
                    crawlers.append({
                        'name': crawler.name,
                        'status': crawler.status,
                        'status_color': 'success' if crawler.status == 'running' else 'warning',
                        'last_run': crawler.last_run.strftime('%Y-%m-%d %H:%M:%S') if crawler.last_run else '从未运行',
                        'next_run': crawler.next_run.strftime('%Y-%m-%d %H:%M:%S') if crawler.next_run else '未设置'
                    })
            except Exception as e:
                logger.error(f"获取爬虫状态失败: {str(e)}")
                flash(f"获取爬虫状态失败: {str(e)}", 'danger')
        else:
            logger.warning("爬虫管理器未初始化或不可用")
            flash("爬虫管理器未初始化或不可用", 'warning')
        
        # 获取最近日志
        recent_logs = []
        log_file = os.path.join(app.config['LOG_DIR'], f'crawler_{today.strftime("%Y%m%d")}.log')
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f.readlines()[-100:]:  # 只读取最后100行
                    try:
                        log_data = json.loads(line)
                        recent_logs.append({
                            'timestamp': log_data['timestamp'],
                            'crawler': log_data.get('crawler', 'system'),
                            'level': log_data['level'],
                            'level_color': {
                                'DEBUG': 'secondary',
                                'INFO': 'info',
                                'WARNING': 'warning',
                                'ERROR': 'danger',
                                'CRITICAL': 'danger'
                            }.get(log_data['level'], 'info'),
                            'message': log_data['message']
                        })
                    except:
                        continue
        
        return render_template('crawler_status.html',
                             today_count=today_count,
                             week_count=week_count,
                             month_count=month_count,
                             total_count=total_count,
                             crawlers=crawlers,
                             recent_logs=recent_logs)
    
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
        db = NewsDatabase()
        news = db.get_news_by_id(news_id)
        
        if not news:
            flash('新闻不存在', 'error')
            return redirect(url_for('index'))
        
        # 获取相关新闻
        related_news = []
        if 'keywords' in news and news['keywords']:
            keywords = news['keywords'].split(',')[:3]
            for keyword in keywords:
                related = db.query_news(keyword=keyword, limit=3)
                for item in related:
                    if item['id'] != news_id and item not in related_news:
                        related_news.append(item)
                        if len(related_news) >= 5:
                            break
                if len(related_news) >= 5:
                    break
        
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
    
    @app.route('/feedback', methods=['GET', 'POST'])
    def feedback():
        """反馈页面"""
        if request.method == 'POST':
            # 获取表单数据
            feedback_type = request.form.get('type')
            title = request.form.get('title')
            content = request.form.get('content')
            email = request.form.get('email')
            urgent = request.form.get('urgent') == 'on'
            
            # 验证数据
            if not all([feedback_type, title, content]):
                flash('请填写所有必填字段', 'error')
                return redirect(url_for('feedback'))
            
            # 生成反馈ID
            feedback_id = str(uuid.uuid4())
            
            # 构建反馈数据
            feedback_data = {
                'id': feedback_id,
                'feedback_type': feedback_type,
                'title': title,
                'content': content,
                'email': email,
                'urgent': urgent,
                'submit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 保存到数据库
            db = NewsDatabase()
            if db.save_feedback(feedback_data):
                flash('反馈提交成功，感谢您的反馈！', 'success')
                return redirect(url_for('feedback_status', feedback_id=feedback_id))
            else:
                flash('反馈提交失败，请稍后重试', 'error')
                return redirect(url_for('feedback'))
        
        return render_template('feedback.html')
    
    @app.route('/feedback/status/<feedback_id>')
    def feedback_status(feedback_id):
        """反馈状态页面"""
        db = NewsDatabase()
        feedback = db.get_feedback(feedback_id)
        
        if not feedback:
            flash('反馈不存在', 'error')
            return redirect(url_for('feedback'))
        
        return render_template('feedback_status.html', feedback=feedback)
    
    @app.route('/api/news')
    def api_news():
        """新闻API"""
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
        db = NewsDatabase()
        news_list = db.query_news(
            keyword=keyword if keyword else None,
            days=days,
            source=source if source else None,
            limit=limit,
            offset=(page - 1) * limit
        )
        
        # 获取总数
        total_count = db.count_news(
            keyword=keyword if keyword else None,
            days=days,
            source=source if source else None
        )
        
        # 计算总页数
        total_pages = (total_count + limit - 1) // limit
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'news': news_list,
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': total_pages
            }
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
    
    @app.errorhandler(404)
    def page_not_found(e):
        """404页面"""
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        """500页面"""
        return render_template('500.html'), 500 