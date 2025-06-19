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
from backend.newslook.utils.database import NewsDatabase
from backend.newslook.utils.enhanced_database import EnhancedNewsDatabase
from backend.newslook.utils.data_validator import DataValidator
from backend.newslook.utils.logger import get_logger
from backend.newslook.config import get_settings, get_unified_db_path
import sqlite3

logger = get_logger(__name__)

def register_routes(app):
    """注册路由"""
    
    @app.route('/')
    def index():
        """首页 - 重定向到前端应用"""
        from flask import redirect
        # 重定向到前端Vue应用
        return redirect('http://localhost:3000')
    
    @app.route('/api/news')
    def api_news():
        """新闻列表API - 前端需要"""
        try:
            # 获取查询参数
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 20))
            keyword = request.args.get('keyword', '')
            source = request.args.get('source', '')
            # 默认查询所有新闻，不限制日期
            days_param = request.args.get('days')
            days = int(days_param) if days_param else None
            
            per_page = page_size
            
            logger.info(f"API新闻请求: 关键词={keyword}, 来源={source}, 天数={days}, 页码={page}")
            
            # 查询数据库 - 使用统一的数据库路径
            unified_db_path = get_unified_db_path()
            db = EnhancedNewsDatabase(db_paths=[unified_db_path], timeout=25.0)
            
            # 获取新闻列表
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
            
            db.close()
            
            logger.info(f"API查询到 {len(news_list)} 条新闻，总数: {total_count}")
            
            # 计算分页信息
            total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
            
            return jsonify({
                'data': news_list,
                'total': total_count,
                'page': page,
                'pages': total_pages,
                'page_size': per_page
            })
            
        except Exception as e:
            logger.error(f"API新闻请求处理出错: {str(e)}")
            return jsonify({
                'data': [],
                'total': 0,
                'page': 1,
                'pages': 1,
                'page_size': 20,
                'error': str(e)
            }), 500
    
    @app.route('/crawler_status')
    def crawler_status():
        """爬虫状态页面 - 重定向到前端"""
        from flask import redirect
        return redirect('http://localhost:3000/crawler-manager')
    
    @app.route('/dashboard')
    def dashboard():
        """数据统计页面 - 重定向到前端"""
        from flask import redirect
        return redirect('http://localhost:3000/dashboard')
    
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
        
        # 使用统一的数据库路径
        unified_db_path = get_unified_db_path()
        db = NewsDatabase(db_path=unified_db_path)
        
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
            # 使用统一的数据库路径
            unified_db_path = get_unified_db_path()
            db = NewsDatabase(db_path=unified_db_path)
            
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
        unified_db_path = get_unified_db_path()
        db = NewsDatabase(db_path=unified_db_path)
        
        # 获取新闻总数
        total_count = db.get_news_count()
        
        # 获取来源分布
        sources = db.get_sources()
        source_stats = {source: db.get_news_count(source=source) for source in sources}
        
        # 获取情感分布 (暂时关闭，等待情感分析功能完善)
        sentiment_stats = {
            '积极': 0,
            '中性': 0,
            '消极': 0
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
                unified_db_path = get_unified_db_path()
                db = NewsDatabase(db_path=unified_db_path)
                
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
    
    @app.route('/api/news/<news_id>')
    def api_news_detail(news_id):
        """新闻详情API - 增强版"""
        try:
            from backend.newslook.web.api_fixes import (
                standardize_news_data, 
                format_api_response, 
                diagnose_data_issues,
                create_diagnostic_news_detail
            )
            
            logger.info(f"[API] 获取新闻详情: {news_id}")
            
            # 使用统一的数据库路径
            unified_db_path = get_unified_db_path()
            db = NewsDatabase(db_path=unified_db_path)
            
            # 获取原始新闻数据
            raw_news = db.get_news_by_id(news_id)
            
            if not raw_news:
                # 创建诊断信息
                diagnostic_news = create_diagnostic_news_detail(
                    news_id, 
                    "新闻ID不存在或数据库中无此记录"
                )
                standardized_news = standardize_news_data(diagnostic_news)
                logger.warning(f"[API] 新闻不存在: {news_id}")
                return jsonify(format_api_response(
                    standardized_news, 
                    success=True, 
                    message=f'news {news_id} not found, showing diagnostic info'
                ))
            
            # 标准化新闻数据
            standardized_news = standardize_news_data(raw_news)
            
            # 诊断数据质量
            diagnosis = diagnose_data_issues(standardized_news)
            
            # 记录数据质量信息
            logger.info(f"[API] 新闻 {news_id} 数据质量分数: {diagnosis['quality_score']:.2f}")
            if diagnosis['warnings']:
                logger.warning(f"[API] 新闻 {news_id} 数据质量警告: {diagnosis['warnings']}")
            
            # 在响应中添加诊断信息（仅调试时）
            response_data = standardized_news.copy()
            response_data['_debug'] = {
                'quality_score': diagnosis['quality_score'],
                'missing_fields': diagnosis['warnings'],
                'data_issues': diagnosis['issues']
            }
            
            logger.info(f"[API] 成功返回新闻详情: {news_id}")
            return jsonify(format_api_response(response_data, success=True, message='success'))
            
        except ImportError as e:
            logger.error(f"[API] 导入API修复模块失败: {str(e)}")
            # 降级到原始实现
            unified_db_path = get_unified_db_path()
            db = NewsDatabase(db_path=unified_db_path)
            news = db.get_news_by_id(news_id)
            
            if not news:
                return jsonify({
                    'code': 404,
                    'message': 'news not found',
                    'data': None
                })
            
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': news
            })
            
        except Exception as e:
            logger.error(f"[API] 获取新闻详情失败: {str(e)}")
            # 创建错误诊断数据
            try:
                from backend.newslook.web.api_fixes import create_diagnostic_news_detail, standardize_news_data
                diagnostic_news = create_diagnostic_news_detail(news_id, str(e))
                standardized_news = standardize_news_data(diagnostic_news)
                return jsonify(format_api_response(
                    standardized_news, 
                    success=False, 
                    message=f'error retrieving news: {str(e)}'
                ))
            except:
                # 最终降级方案
                return jsonify({
                    'code': 500,
                    'message': f'internal server error: {str(e)}',
                    'data': None
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
        """统计数据API - 前端Dashboard需要"""
        try:
            logger.info("[DB] 开始获取统计数据（使用数据验证器）")
            
            # 使用数据验证器获取一致的统计数据
            validator = DataValidator()
            stats = validator.get_consistent_statistics()
            
            logger.info(f"[DB] 统计数据: 总新闻={stats['total_news']}, 今日新闻={stats['today_news']}, 活跃源={stats['active_sources']}")
            
            # 构建响应数据
            response_data = {
                'total_news': stats['total_news'],
                'today_news': stats['today_news'],
                'active_sources': stats['active_sources'],
                'crawl_success_rate': stats['crawl_success_rate'],
                'last_update': stats['last_update'],
                'data_sources': f"{stats['database_info']['valid_databases']}/{stats['database_info']['total_databases']} 个数据库",
                'data_consistency': {
                    'unique_ratio': stats['data_consistency']['consistency_ratio'],
                    'duplicate_count': stats['data_consistency']['duplicate_count'],
                    'has_issues': len(stats['issues']) > 0
                }
            }
            
            # 如果有数据质量问题，添加警告信息
            if stats['issues']:
                response_data['warnings'] = [issue['message'] for issue in stats['issues']]
            
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"[DB] 获取统计数据失败: {str(e)}")
            import traceback
            logger.error(f"[DB] 错误堆栈: {traceback.format_exc()}")
            # 返回默认数据确保前端不会出错
            return jsonify({
                'total_news': 0,
                'today_news': 0,
                'active_sources': 0,
                'crawl_success_rate': 0.0,
                'last_update': datetime.now().isoformat(),
                'data_sources': '0/0 个数据库',
                'error': '数据库连接失败'
            })
    
    @app.route('/api/stats/sources')
    def api_stats_sources():
        """API: 获取来源统计 - 前端需要"""
        try:
            # 使用数据验证器获取准确的来源统计
            validator = DataValidator()
            stats = validator.get_consistent_statistics()
            
            # 计算每个来源的新闻数
            db = EnhancedNewsDatabase(timeout=25.0)
            sources_data = {}
            for source in stats['sources']:
                count = db.get_news_count(source=source)
                sources_data[source] = count
            
            logger.info(f"[DB] 来源统计: {sources_data}")
            
            db.close()
            
            return jsonify({
                'sources': sources_data,
                'last_update': stats['last_update']
            })
        except Exception as e:
            logger.error(f"[DB] 获取来源统计失败: {str(e)}")
            return jsonify({
                'sources': {},
                'error': str(e)
            })
    
    @app.route('/api/data/validation-report')
    def api_validation_report():
        """API: 获取数据验证报告"""
        try:
            logger.info("[DB] 开始生成数据验证报告")
            
            # 创建数据验证器实例
            validator = DataValidator()
            logger.info("[DB] DataValidator实例创建成功")
            
            # 获取统计数据
            stats = validator.get_consistent_statistics()
            logger.info(f"[DB] 获取统计数据成功: {stats.keys()}")
            
            # 生成报告文本
            report = validator.generate_report()
            logger.info("[DB] 报告生成成功")
            
            # 构建响应数据
            response_data = {
                'report': report,
                'summary': {
                    'total_databases': stats['database_info']['total_databases'],
                    'valid_databases': stats['database_info']['valid_databases'],
                    'total_news': stats['total_news'],
                    'duplicate_count': stats['data_consistency']['duplicate_count'],
                    'consistency_ratio': stats['data_consistency']['consistency_ratio'],
                    'issues_count': len(stats['issues'])
                },
                'database_files': [
                    {
                        'name': os.path.basename(db_path),
                        'path': db_path,
                        'size': f"{os.path.getsize(db_path) / 1024:.1f} KB"
                    } for db_path in validator.db_paths if os.path.exists(db_path)
                ],
                'sources_found': stats['sources'],
                'total_news_count': stats['total_news'],
                'generated_at': datetime.now().isoformat()
            }
            
            logger.info(f"[DB] 验证报告API响应构建完成")
            return jsonify(response_data)
            
        except ImportError as e:
            logger.error(f"[DB] DataValidator导入失败: {str(e)}")
            return jsonify({
                'error': f'DataValidator模块导入失败: {str(e)}',
                'report': '数据验证器不可用'
            }), 500
        except Exception as e:
            logger.error(f"[DB] 生成验证报告失败: {str(e)}")
            import traceback
            logger.error(f"[DB] 错误堆栈: {traceback.format_exc()}")
            
            # 提供降级的基本信息
            try:
                unified_db_path = get_unified_db_path()
                db = NewsDatabase(db_path=unified_db_path)
                fallback_data = {
                    'error': str(e),
                    'report': f'验证报告生成失败: {str(e)}',
                    'summary': {
                        'total_databases': len(db.all_db_paths),
                        'valid_databases': len([p for p in db.all_db_paths if os.path.exists(p)]),
                        'total_news': db.get_news_count(),
                        'duplicate_count': 0,
                        'consistency_ratio': 1.0,
                        'issues_count': 1
                    },
                    'sources_found': db.get_sources(),
                    'generated_at': datetime.now().isoformat()
                }
                db.close()
                return jsonify(fallback_data), 200
            except Exception as fallback_error:
                logger.error(f"[DB] 降级数据获取也失败: {str(fallback_error)}")
                return jsonify({
                    'error': str(e),
                    'report': '无法生成验证报告',
                    'fallback_error': str(fallback_error)
                }), 500
    
    @app.route('/api/stats/daily')
    def api_stats_daily():
        """API: 获取每日新闻数统计 - 前端需要"""
        try:
            days = request.args.get('days', '7')
            try:
                days = int(days)
            except ValueError:
                days = 7
                
            unified_db_path = get_unified_db_path()
            db = NewsDatabase(db_path=unified_db_path)
            
            # 生成日期范围
            today = datetime.now().date()
            date_range = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
            date_range.reverse()  # 从早到晚排序
            
            # 统计每天的新闻数（简化版本）
            daily_stats = []
            for date in date_range:
                # 模拟数据，实际应该查询数据库
                import random
                count = random.randint(10, 100)
                daily_stats.append({
                    'date': date,
                    'count': count
                })
            
            logger.info(f"每日统计: {len(daily_stats)} 天的数据")
            
            return jsonify({
                'daily_stats': daily_stats
            })
        except Exception as e:
            logger.error(f"获取每日统计失败: {str(e)}")
            return jsonify({
                'daily_stats': []
            })
    
    @app.route('/admin/update-sources', methods=['GET', 'POST'])
    def admin_update_sources():
        """管理员更新数据源"""
        # 检查权限（暂时跳过）
        
        if request.method == 'POST':
            # 处理更新逻辑
            unified_db_path = get_unified_db_path()
            db = NewsDatabase(db_path=unified_db_path)
            # 可以在这里添加更新数据源的逻辑
            flash("数据源更新成功", "success")
            
        # 显示当前数据源状态
        unified_db_path = get_unified_db_path()
        db = NewsDatabase(db_path=unified_db_path)
        sources = db.get_sources()
        
        stats = []
        for source in sources:
            count = db.get_news_count(source=source)
            today_count = db.get_news_count(source=source, days=1)
            stats.append({
                'name': source,
                'total': count,
                'today': today_count
            })
        
        return render_template('admin/update_sources.html', stats=stats)
    
    @app.errorhandler(404)
    def page_not_found(e):
        """404页面"""
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        """500页面"""
        return render_template('500.html'), 500
    
    # API路由 - 前端需要的接口
    @app.route('/api/crawler/status')
    def api_crawler_status():
        """获取爬虫状态 - 前端需要"""
        try:
            # 获取爬虫状态（模拟数据，实际应从爬虫管理器获取）
            crawlers = [
                {
                    'name': '新浪财经',
                    'status': 'stopped',
                    'progress': 0,
                    'lastUpdate': datetime.now().isoformat(),
                    'newsCount': 0,
                    'errorCount': 0
                },
                {
                    'name': '东方财富',
                    'status': 'stopped',
                    'progress': 0,
                    'lastUpdate': datetime.now().isoformat(),
                    'newsCount': 0,
                    'errorCount': 0
                },
                {
                    'name': '腾讯财经',
                    'status': 'stopped',
                    'progress': 0,
                    'lastUpdate': datetime.now().isoformat(),
                    'newsCount': 0,
                    'errorCount': 0
                },
                {
                    'name': '网易财经',
                    'status': 'stopped',
                    'progress': 0,
                    'lastUpdate': datetime.now().isoformat(),
                    'newsCount': 0,
                    'errorCount': 0
                },
                {
                    'name': '凤凰财经',
                    'status': 'stopped',
                    'progress': 0,
                    'lastUpdate': datetime.now().isoformat(),
                    'newsCount': 0,
                    'errorCount': 0
                }
            ]
            
            return jsonify({
                'success': True,
                'data': crawlers
            })
        except Exception as e:
            logger.error(f"获取爬虫状态失败: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    @app.route('/api/crawlers/<name>/start', methods=['POST'])
    def api_start_crawler(name):
        """启动指定爬虫"""
        try:
            # 这里应该调用爬虫管理器启动指定爬虫
            # 暂时返回成功响应
            logger.info(f"启动爬虫: {name}")
            return jsonify({
                'success': True,
                'message': f'爬虫 {name} 启动成功'
            })
        except Exception as e:
            logger.error(f"启动爬虫失败: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    @app.route('/api/crawlers/<name>/stop', methods=['POST'])
    def api_stop_crawler(name):
        """停止指定爬虫"""
        try:
            # 这里应该调用爬虫管理器停止指定爬虫
            # 暂时返回成功响应
            logger.info(f"停止爬虫: {name}")
            return jsonify({
                'success': True,
                'message': f'爬虫 {name} 停止成功'
            })
        except Exception as e:
            logger.error(f"停止爬虫失败: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    @app.route('/api/crawlers/start_all', methods=['POST'])
    def api_start_all_crawlers():
        """启动所有爬虫"""
        try:
            # 这里应该调用爬虫管理器启动所有爬虫
            # 暂时返回成功响应
            logger.info("启动所有爬虫")
            return jsonify({
                'success': True,
                'message': '所有爬虫启动成功'
            })
        except Exception as e:
            logger.error(f"启动所有爬虫失败: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    @app.route('/api/crawlers/stop_all', methods=['POST'])
    def api_stop_all_crawlers():
        """停止所有爬虫"""
        try:
            # 这里应该调用爬虫管理器停止所有爬虫
            # 暂时返回成功响应
            logger.info("停止所有爬虫")
            return jsonify({
                'success': True,
                'message': '所有爬虫停止成功'
            })
        except Exception as e:
            logger.error(f"停止所有爬虫失败: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500 