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
from newslook.utils.database import NewsDatabase
from newslook.utils.logger import get_logger
from newslook.config import get_settings
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
        
        logger.info(f"首页请求: 关键词={keyword}, 来源={source}, 天数={days}, 页码={page}")
        
        # 查询数据库 - 始终使用所有可用的数据库
        db = NewsDatabase(use_all_dbs=True)
        
        try:
            # 获取新闻列表
            news_list = db.query_news(
                keyword=keyword if keyword else None,
                days=days,
                source=source if source else None,
                limit=per_page,
                offset=(page - 1) * per_page
            )
            
            logger.info(f"查询到 {len(news_list)} 条新闻")
            
            # 获取总数
            total_count = db.get_news_count(
                keyword=keyword if keyword else None,
                days=days,
                source=source if source else None
            )
            
            logger.info(f"符合条件的新闻总数: {total_count}")
            
            # 获取新闻来源列表
            sources = db.get_sources()
            logger.info(f"获取到 {len(sources)} 个新闻来源")
            
            # 获取统计数据
            today = datetime.now().date()
            today_count = db.get_news_count(days=1)
            source_count = len(sources)
            categories = db.get_categories()
            
            # 获取热门关键词
            top_keywords = db.get_popular_keywords(limit=10)
            
            # 计算总页数
            total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
            
            return render_template('index.html',
                                news_list=news_list,
                                keyword=keyword,
                                source=source,
                                days=days,
                                page=page,
                                total_pages=total_pages,
                                total_count=total_count,
                                sources=sources,
                                today_count=today_count,
                                source_count=source_count,
                                categories=categories,
                                top_keywords=top_keywords,
                                view_mode=view_mode)
        except Exception as e:
            logger.error(f"首页处理出错: {str(e)}")
            return render_template('index.html',
                                news_list=[],
                                keyword=keyword,
                                source=source,
                                days=days,
                                page=page,
                                total_pages=1,
                                total_count=0,
                                sources=[],
                                today_count=0,
                                source_count=0,
                                categories=[],
                                top_keywords=[],
                                view_mode=view_mode)
    
    @app.route('/crawler_status')
    def crawler_status():
        """爬虫状态页面"""
        # 始终使用所有可用的数据库
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
    
    @app.route('/dashboard')
    def dashboard():
        """数据统计页面"""
        # 获取时间范围参数
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()
        
        # 查询数据库
        db = NewsDatabase(use_all_dbs=True)
        
        # 获取总统计数据
        total_news = db.get_news_count()
        today_news = db.get_news_count(days=1)
        week_news = db.get_news_count(days=7)
        month_news = db.get_news_count(days=30)
        
        # 获取来源统计
        sources = db.get_sources()
        source_counts = []
        for source in sources:
            count = db.get_news_count(source=source)
            source_counts.append({'name': source, 'count': count})
        
        # 按新闻数量排序
        source_counts.sort(key=lambda x: x['count'], reverse=True)
        
        # 获取日期趋势数据
        trend_data = db.get_daily_counts(start_date, end_date)
        trend_dates = [item['date'] for item in trend_data]
        trend_counts = [item['count'] for item in trend_data]
        
        # 获取热门关键词
        keywords = db.get_popular_keywords(limit=20)
        
        # 获取分类统计
        categories = db.get_categories()
        category_counts = []
        for category in categories:
            count = db.get_news_count(category=category)
            category_counts.append({'name': category, 'count': count})
        
        # 按新闻数量排序
        category_counts.sort(key=lambda x: x['count'], reverse=True)
        
        # 准备图表数据
        source_data = {
            'labels': [item['name'] for item in source_counts[:10]],
            'counts': [item['count'] for item in source_counts[:10]]
        }
        
        keyword_data = {
            'labels': [item['keyword'] for item in keywords[:10]],
            'counts': [item['count'] for item in keywords[:10]]
        }
        
        # 准备源数据标签和数据
        source_labels = [item['name'] for item in source_counts[:10]]
        source_data_values = [item['count'] for item in source_counts[:10]]
        
        # 准备趋势图数据标签
        trend_labels = trend_dates
        trend_data_values = trend_counts
        
        # 添加情感分析数据（临时数据，实际应从数据库获取）
        positive_count = int(total_news * 0.3)  # 假设30%为积极
        neutral_count = int(total_news * 0.5)   # 假设50%为中性
        negative_count = total_news - positive_count - neutral_count  # 剩余为消极
        
        return render_template('dashboard.html',
                             total_news=total_news,
                             today_news=today_news,
                             week_news=week_news,
                             month_news=month_news,
                             sources=sources,
                             source_counts=source_counts,
                             start_date=start_date.strftime('%Y-%m-%d'),
                             end_date=end_date.strftime('%Y-%m-%d'),
                             trend_dates=trend_dates,
                             trend_counts=trend_counts,
                             trend_labels=trend_labels,
                             trend_data=trend_data_values,
                             source_data=source_data,
                             keyword_data=keyword_data,
                             source_labels=source_labels,
                             source_data_values=source_data_values,
                             positive_count=positive_count,
                             neutral_count=neutral_count,
                             negative_count=negative_count,
                             categories=categories)
    
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
        
        # 始终使用所有可用的数据库
        db = NewsDatabase(use_all_dbs=True)
        
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
    
    @app.route('/test')
    def test_page():
        """测试页面（仅用于测试编码）"""
        return render_template('test.html')
    
    @app.route('/api/test')
    def test_api():
        """测试API（仅用于测试编码）"""
        from flask import jsonify
        return jsonify({
            'status': 'success',
            'message': '这是中文测试',
            'data': {
                'chinese': '中文',
                'number': 123,
                'english': 'abc',
                'sources': ['新浪财经', '腾讯财经', '东方财富']
            }
        })
    
    @app.route('/test_direct')
    def test_direct():
        """直接返回HTML（测试编码）"""
        html_content = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <title>直接测试页面</title>
        </head>
        <body>
            <h1>这是一个测试页面</h1>
            <p>测试中文显示</p>
            <p>测试数字: 1234567890</p>
            <p>测试英文: abcdefg</p>
        </body>
        </html>
        """
        from flask import Response
        return Response(html_content, mimetype='text/html; charset=utf-8')
    
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
        """新闻详情页面"""
        logger.info(f"访问新闻详情，ID: {news_id}")
        
        try:
            # 始终使用所有可用的数据库
            db = NewsDatabase(use_all_dbs=True)
            
            # 尝试查询前记录一下检查所有数据库路径
            db_paths = db.all_db_paths if hasattr(db, 'all_db_paths') else []
            logger.info(f"将在以下数据库中查询新闻ID {news_id}: {', '.join(db_paths)}")
            
            # 获取新闻详情
            news = db.get_news_by_id(news_id)
            
            # 检查是否是"新闻不存在"提示对象
            if news and news.get('title') == '新闻不存在':
                flash('新闻不存在或已被删除', 'danger')
                logger.warning(f"返回新闻不存在对象，重定向到首页")
                return redirect(url_for('index'))
                
            # 如果news为None，也显示不存在提示
            if not news:
                logger.warning(f"新闻不存在，ID: {news_id}，重定向到首页")
                flash('新闻不存在或已被删除', 'danger')
                return redirect(url_for('index'))
                
            logger.info(f"成功获取新闻详情: {news.get('title', '无标题')}, 来源: {news.get('source', '未知')}")
            
            # 检查必要的字段是否存在
            required_fields = ['title', 'content', 'pub_time']
            for field in required_fields:
                if field not in news or not news[field]:
                    if field == 'content':
                        # 如果内容为空，添加一个提示信息
                        news['content'] = "该新闻暂无详细内容，请点击查看原文获取更多信息。"
                    else:
                        # 其他必要字段为空，添加默认值
                        news[field] = f"未知{field}" if field != 'pub_time' else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.warning(f"新闻缺少{field}字段，已添加默认值")
            
            # 查询相关新闻
            related_news = []
            source_to_use = news.get('source')
            
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
                    
                    logger.info(f"新闻关键词: {keywords}")
                    
                    if keywords:
                        # 使用第一个关键词查询
                        keyword = keywords[0] if isinstance(keywords, list) else keywords
                        # 确保查询相关新闻时只获取同一来源的新闻，避免混淆
                        logger.info(f"查询相关新闻，使用关键词: {keyword}, 来源: {source_to_use}")
                        related_news = db.query_news(
                            keyword=keyword,
                            limit=5,
                            source=source_to_use
                        )
                        logger.info(f"获取到 {len(related_news)} 条相关新闻")
                        for i, rel_news in enumerate(related_news):
                            logger.info(f"相关新闻 {i+1}: {rel_news.get('title', '无标题')}")
                except Exception as e:
                    logger.error(f"查询相关新闻失败: {str(e)}")
                    logger.exception(e)
            
            # 确保图片字段正确处理
            if 'images' in news and news['images']:
                if isinstance(news['images'], str):
                    try:
                        news['images'] = json.loads(news['images'])
                    except:
                        news['images'] = [img.strip() for img in news['images'].split(',') if img.strip()]
                    logger.info(f"处理新闻图片: {news['images']}")
            
            return render_template('news_detail.html', news=news, related_news=related_news)
        except Exception as e:
            logger.error(f"处理新闻详情页面出错: {str(e)}")
            logger.exception(e)
            flash(f'查看新闻详情时发生错误: {str(e)}', 'danger')
            return redirect(url_for('index'))
    
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
    
    @app.route('/admin/update-sources', methods=['GET', 'POST'])
    def admin_update_sources():
        """管理界面：更新未知来源的新闻"""
        message = None
        updated_count = 0
        
        if request.method == 'POST':
            try:
                # 创建数据库连接
                db = NewsDatabase(use_all_dbs=True)
                
                # 更新未知来源
                updated_count = db.update_unknown_sources()
                
                if updated_count > 0:
                    message = f"成功更新 {updated_count} 条未知来源的新闻数据"
                    flash(message, 'success')
                else:
                    message = "没有需要更新的未知来源新闻数据"
                    flash(message, 'info')
                
            except Exception as e:
                message = f"更新失败: {str(e)}"
                flash(message, 'danger')
                logger.error(f"更新未知来源失败: {str(e)}")
        
        # 获取未知来源的新闻数量
        try:
            db = NewsDatabase(use_all_dbs=True)
            unknown_count = db.get_news_count(source='未知来源') + db.get_news_count(source='')
        except Exception as e:
            unknown_count = 0
            logger.error(f"获取未知来源新闻数量失败: {str(e)}")
        
        return render_template(
            'admin/update_sources.html',
            message=message,
            updated_count=updated_count,
            unknown_count=unknown_count
        )
    
    @app.errorhandler(404)
    def page_not_found(e):
        """404页面"""
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        """500页面"""
        return render_template('500.html'), 500 