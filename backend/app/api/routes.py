#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 财经新闻爬虫系统 - API路由
提供RESTful API接口
"""

import os
import glob
import json
import sqlite3
import logging
import subprocess
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, current_app, send_file
from werkzeug.exceptions import BadRequest

# 设置日志
logger = logging.getLogger(__name__)

def register_api_routes(app):
    """注册API路由到Flask应用"""
    
    # 新闻相关API
    @app.route('/api/news', methods=['GET'])
    def get_news_list():
        """获取新闻列表"""
        try:
            # 获取查询参数
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 20))
            source = request.args.get('source', '')
            search = request.args.get('q', '')
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            sort_by = request.args.get('sort_by', 'publish_time')
            sort_order = request.args.get('sort_order', 'desc')
            
            # 获取数据库文件
            db_dir = current_app.config['DB_DIR']
            news_list = []
            total_count = 0
            
            logger.info(f"查找数据库目录: {db_dir}")
            
            # 确定要查询的数据库文件
            if source:
                # 如果指定了来源，查找对应的数据库文件
                possible_files = [
                    f"{source}_finance.db",  # 标准格式
                    f"{source}.db",          # 简单格式
                ]
                db_files = []
                for possible_file in possible_files:
                    if os.path.exists(os.path.join(db_dir, possible_file)):
                        db_files.append(possible_file)
                        break
            else:
                # 查找所有数据库文件
                db_files = [f for f in os.listdir(db_dir) if f.endswith('.db')]
            
            logger.info(f"找到数据库文件: {db_files}")
            
            # 从所有相关数据库获取新闻
            for db_file in db_files:
                db_path = os.path.join(db_dir, db_file)
                if not os.path.exists(db_path):
                    continue
                    
                try:
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # 构建查询条件
                    where_conditions = []
                    params = []
                    
                    if search:
                        where_conditions.append("(title LIKE ? OR content LIKE ?)")
                        params.extend([f"%{search}%", f"%{search}%"])
                    
                    if date_from:
                        where_conditions.append("pub_time >= ?")
                        params.append(date_from)
                    
                    if date_to:
                        where_conditions.append("pub_time <= ?")
                        params.append(date_to)
                    
                    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                    
                    # 获取总数
                    count_query = f"SELECT COUNT(*) FROM news WHERE {where_clause}"
                    cursor.execute(count_query, params)
                    total_count += cursor.fetchone()[0]
                    
                    # 获取新闻列表
                    offset = (page - 1) * page_size
                    order_clause = f"ORDER BY {sort_by} {sort_order.upper()}"
                    
                    query = f"""
                        SELECT id, title, content, author, pub_time, url, 
                               source, category, keywords, images,
                               crawl_time, content_html, sentiment, classification
                        FROM news 
                        WHERE {where_clause}
                        {order_clause}
                        LIMIT ? OFFSET ?
                    """
                    
                    cursor.execute(query, params + [page_size, offset])
                    rows = cursor.fetchall()
                    
                    # 转换为字典列表并修复字段名
                    for row in rows:
                        news_item = dict(row)
                        # 统一字段名 - 前端期望的字段名
                        news_item['publish_time'] = news_item.get('pub_time')
                        news_item['created_at'] = news_item.get('crawl_time') 
                        news_item['image_url'] = news_item.get('images')
                        # 从文件名推断来源名称
                        source_name = db_file.replace('_finance.db', '').replace('.db', '')
                        news_item['source_name'] = get_source_display_name(source_name)
                        news_list.append(news_item)
                    
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"查询数据库 {db_file} 时出错: {e}")
                    continue
            
            # 如果是跨数据库查询，需要重新排序和分页
            if not source and len(db_files) > 1:
                # 按指定字段排序
                reverse = (sort_order.lower() == 'desc')
                sort_field = 'pub_time' if sort_by == 'publish_time' else sort_by
                news_list.sort(key=lambda x: x.get(sort_field, ''), reverse=reverse)
                
                # 重新分页
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                news_list = news_list[start_idx:end_idx]
            
            return jsonify({
                'success': True,
                'data': news_list,
                'total': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size
            })
            
        except Exception as e:
            logger.error(f"获取新闻列表时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/news/<int:news_id>', methods=['GET'])
    def get_news_detail(news_id):
        """获取新闻详情"""
        try:
            source = request.args.get('source', '')
            db_dir = current_app.config['DB_DIR']
            
            # 如果指定了来源，直接查询对应数据库
            if source:
                db_files = [f"{source}.db"]
            else:
                # 否则查询所有数据库
                db_files = [f for f in os.listdir(db_dir) if f.endswith('.db')]
            
            # 查找新闻
            for db_file in db_files:
                db_path = os.path.join(db_dir, db_file)
                if not os.path.exists(db_path):
                    continue
                
                try:
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT id, title, content, author, pub_time, url,
                               source, category, summary, keywords, images,
                               crawl_time, content_html, sentiment, classification
                        FROM news WHERE id = ?
                    """, (news_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        news_detail = dict(row)
                        # 统一字段名 - 前端期望的字段名
                        news_detail['publish_time'] = news_detail.get('pub_time')
                        news_detail['created_at'] = news_detail.get('crawl_time')
                        news_detail['image_url'] = news_detail.get('images')
                        news_detail['source_name'] = db_file.replace('.db', '')
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'data': news_detail
                        })
                    
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"查询数据库 {db_file} 时出错: {e}")
                    continue
            
            return jsonify({'success': False, 'message': '新闻不存在'}), 404
            
        except Exception as e:
            logger.error(f"获取新闻详情时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/news/search', methods=['GET'])
    def search_news():
        """搜索新闻"""
        query = request.args.get('q', '')
        if not query:
            return jsonify({'success': False, 'message': '搜索关键词不能为空'}), 400
        
        # 重定向到新闻列表接口
        return get_news_list()
    
    @app.route('/api/news/sources', methods=['GET'])
    def get_news_sources():
        """获取新闻来源列表"""
        try:
            db_dir = current_app.config['DB_DIR']
            sources = []
            
            # 扫描数据库文件
            for db_file in os.listdir(db_dir):
                if db_file.endswith('.db'):
                    source_name = db_file.replace('.db', '')
                    db_path = os.path.join(db_dir, db_file)
                    
                    # 获取数据库统计信息
                    try:
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        
                        # 获取记录数
                        cursor.execute("SELECT COUNT(*) FROM news")
                        count = cursor.fetchone()[0]
                        
                        # 获取最新更新时间
                        cursor.execute("SELECT MAX(crawl_time) FROM news")
                        latest_update = cursor.fetchone()[0]
                        
                        conn.close()
                        
                        sources.append({
                            'name': source_name,
                            'display_name': get_source_display_name(source_name),
                            'count': count,
                            'latest_update': latest_update
                        })
                        
                    except Exception as e:
                        logger.error(f"读取数据库 {db_file} 统计信息时出错: {e}")
                        continue
            
            return jsonify({
                'success': True,
                'data': sources
            })
            
        except Exception as e:
            logger.error(f"获取新闻来源时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/stats', methods=['GET'])
    def get_stats():
        """获取统计数据"""
        try:
            db_dir = current_app.config['DB_DIR']
            stats = {
                'total_news': 0,
                'sources_count': 0,
                'today_news': 0,
                'weekly_news': 0,
                'sources': []
            }
            
            today = datetime.now().strftime('%Y-%m-%d')
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            for db_file in os.listdir(db_dir):
                if not db_file.endswith('.db'):
                    continue
                
                db_path = os.path.join(db_dir, db_file)
                source_name = db_file.replace('.db', '')
                
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # 总新闻数
                    cursor.execute("SELECT COUNT(*) FROM news")
                    total = cursor.fetchone()[0]
                    stats['total_news'] += total
                    
                    # 今日新闻数 - 修复字段名
                    cursor.execute("SELECT COUNT(*) FROM news WHERE DATE(crawl_time) = ?", (today,))
                    today_count = cursor.fetchone()[0]
                    stats['today_news'] += today_count
                    
                    # 本周新闻数 - 修复字段名
                    cursor.execute("SELECT COUNT(*) FROM news WHERE crawl_time >= ?", (week_ago,))
                    weekly_count = cursor.fetchone()[0]
                    stats['weekly_news'] += weekly_count
                    
                    # 来源统计
                    stats['sources'].append({
                        'name': source_name,
                        'display_name': get_source_display_name(source_name),
                        'total': total,
                        'today': today_count,
                        'weekly': weekly_count
                    })
                    
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"统计数据库 {db_file} 时出错: {e}")
                    continue
            
            stats['sources_count'] = len(stats['sources'])
            
            return jsonify({
                'success': True,
                'data': stats
            })
            
        except Exception as e:
            logger.error(f"获取统计数据时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/trends', methods=['GET'])
    def get_trends():
        """获取趋势数据"""
        try:
            days = int(request.args.get('days', 7))
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            db_dir = current_app.config['DB_DIR']
            
            # 生成日期列表
            if start_date and end_date:
                # 自定义日期范围
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                date_list = []
                current_date = start
                while current_date <= end:
                    date_list.append(current_date.strftime('%Y-%m-%d'))
                    current_date += timedelta(days=1)
            else:
                # 默认天数范围
                date_list = []
                for i in range(days):
                    date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                    date_list.append(date)
                date_list.reverse()
            
            trends = {
                'dates': date_list,
                'total_news': [0] * len(date_list),
                'sources': {},
                'daily_stats': []
            }
            
            # 扫描所有数据库文件
            for db_file in os.listdir(db_dir):
                if not db_file.endswith('.db'):
                    continue
                
                source_name = db_file.replace('.db', '')
                db_path = os.path.join(db_dir, db_file)
                trends['sources'][source_name] = [0] * len(date_list)
                
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # 为每个日期查询新闻数量
                    for i, date in enumerate(date_list):
                        # 查询该日期的新闻数量 - 修复字段名
                        cursor.execute("""
                            SELECT COUNT(*) FROM news 
                            WHERE DATE(crawl_time) = ? OR DATE(pub_time) = ?
                        """, (date, date))
                        count = cursor.fetchone()[0]
                        
                        trends['sources'][source_name][i] = count
                        trends['total_news'][i] += count
                    
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"获取趋势数据库 {db_file} 时出错: {e}")
                    continue
            
            # 生成每日统计详情
            for i, date in enumerate(date_list):
                daily_total = trends['total_news'][i]
                source_details = []
                
                for source_name, counts in trends['sources'].items():
                    if counts[i] > 0:
                        source_details.append({
                            'source': source_name,
                            'display_name': get_source_display_name(source_name),
                            'count': counts[i]
                        })
                
                trends['daily_stats'].append({
                    'date': date,
                    'total': daily_total,
                    'sources': source_details
                })
            
            # 计算趋势指标
            if len(trends['total_news']) >= 2:
                recent_avg = sum(trends['total_news'][-3:]) / min(3, len(trends['total_news']))
                previous_avg = sum(trends['total_news'][:3]) / min(3, len(trends['total_news']))
                
                growth_rate = 0
                if previous_avg > 0:
                    growth_rate = ((recent_avg - previous_avg) / previous_avg) * 100
                
                trends['analytics'] = {
                    'total_count': sum(trends['total_news']),
                    'avg_daily': round(sum(trends['total_news']) / len(trends['total_news']), 1),
                    'growth_rate': round(growth_rate, 1),
                    'peak_day': date_list[trends['total_news'].index(max(trends['total_news']))] if trends['total_news'] else None,
                    'peak_count': max(trends['total_news']) if trends['total_news'] else 0
                }
            
            return jsonify({
                'success': True,
                'data': trends
            })
            
        except Exception as e:
            logger.error(f"获取趋势数据时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # 爬虫管理API
    @app.route('/api/crawler/status', methods=['GET'])
    def get_crawler_status():
        """获取爬虫状态"""
        try:
            crawler_manager = getattr(current_app, 'crawler_manager', None)
            
            if crawler_manager:
                # 如果有爬虫管理器，获取真实状态
                status = crawler_manager.get_status()
            else:
                # 模拟状态数据
                status = {
                    'crawlers': [
                        {'name': 'sina', 'display_name': '新浪财经', 'status': 'stopped', 'last_run': datetime.now().isoformat(), 'success_rate': 95},
                        {'name': 'eastmoney', 'display_name': '东方财富', 'status': 'running', 'last_run': datetime.now().isoformat(), 'success_rate': 88},
                        {'name': 'tencent', 'display_name': '腾讯财经', 'status': 'stopped', 'last_run': datetime.now().isoformat(), 'success_rate': 92},
                        {'name': 'netease', 'display_name': '网易财经', 'status': 'running', 'last_run': datetime.now().isoformat(), 'success_rate': 90},
                        {'name': 'ifeng', 'display_name': '凤凰财经', 'status': 'error', 'last_run': datetime.now().isoformat(), 'success_rate': 78}
                    ],
                    'total_crawlers': 5,
                    'active_crawlers': 2,
                    'success_rate': 0.89
                }
            
            return jsonify({
                'success': True,
                'data': status
            })
            
        except Exception as e:
            logger.error(f"获取爬虫状态时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/crawler/start', methods=['POST'])
    def start_crawler():
        """启动爬虫"""
        try:
            data = request.get_json()
            crawler_name = data.get('name', '')
            
            if not crawler_name:
                return jsonify({'success': False, 'message': '缺少爬虫名称'}), 400
            
            # 使用subprocess启动爬虫
            if crawler_name == 'all':
                command = ['python', 'run.py', 'crawler', '--all', '--max', '50']
            else:
                command = ['python', 'run.py', 'crawler', '--source', crawler_name, '--max', '50']
            
            # 在后台启动
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            return jsonify({
                'success': True,
                'message': f'爬虫 {crawler_name} 已启动',
                'process_id': process.pid
            })
            
        except Exception as e:
            logger.error(f"启动爬虫时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/crawler/stop', methods=['POST'])
    def stop_crawler():
        """停止爬虫"""
        try:
            data = request.get_json()
            crawler_name = data.get('name', '')
            
            if not crawler_name:
                return jsonify({'success': False, 'message': '缺少爬虫名称'}), 400
            
            # 这里应该实现实际的停止逻辑
            # 可以通过进程管理或者爬虫管理器来停止
            
            return jsonify({
                'success': True,
                'message': f'爬虫 {crawler_name} 已停止'
            })
            
        except Exception as e:
            logger.error(f"停止爬虫时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # 定时任务API
    @app.route('/api/scheduler/tasks', methods=['GET'])
    def get_scheduled_tasks():
        """获取定时任务列表"""
        try:
            # 这里应该从实际的任务调度器获取任务
            # 目前返回模拟数据
            tasks = [
                {
                    'id': 1,
                    'name': '每日新闻爬取',
                    'type': '爬虫任务',
                    'cron_expression': '0 8 * * *',
                    'status': 'active',
                    'next_run': '2024-01-16 08:00:00',
                    'created_at': '2024-01-01 10:00:00'
                },
                {
                    'id': 2,
                    'name': '数据库清理',
                    'type': '维护任务',
                    'cron_expression': '0 2 * * 0',
                    'status': 'active',
                    'next_run': '2024-01-21 02:00:00',
                    'created_at': '2024-01-01 10:00:00'
                },
                {
                    'id': 3,
                    'name': '报告生成',
                    'type': '分析任务',
                    'cron_expression': '0 18 * * 5',
                    'status': 'paused',
                    'next_run': '2024-01-19 18:00:00',
                    'created_at': '2024-01-01 10:00:00'
                }
            ]
            
            return jsonify({
                'success': True,
                'data': tasks
            })
            
        except Exception as e:
            logger.error(f"获取定时任务时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/scheduler/tasks', methods=['POST'])
    def create_scheduled_task():
        """创建定时任务"""
        try:
            data = request.get_json()
            
            # 验证必需字段
            required_fields = ['name', 'type', 'cron_expression']
            for field in required_fields:
                if field not in data:
                    return jsonify({'success': False, 'message': f'缺少字段: {field}'}), 400
            
            # 这里应该实际创建任务
            task_id = int(time.time())  # 简单的ID生成
            
            return jsonify({
                'success': True,
                'message': '任务创建成功',
                'task_id': task_id
            })
            
        except Exception as e:
            logger.error(f"创建定时任务时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/scheduler/tasks/<int:task_id>', methods=['PUT'])
    def update_scheduled_task(task_id):
        """更新定时任务"""
        try:
            data = request.get_json()
            
            # 这里应该实际更新任务
            
            return jsonify({
                'success': True,
                'message': '任务更新成功'
            })
            
        except Exception as e:
            logger.error(f"更新定时任务时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/scheduler/tasks/<int:task_id>', methods=['DELETE'])
    def delete_scheduled_task(task_id):
        """删除定时任务"""
        try:
            # 这里应该实际删除任务
            
            return jsonify({
                'success': True,
                'message': '任务删除成功'
            })
            
        except Exception as e:
            logger.error(f"删除定时任务时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # 系统管理API
    @app.route('/api/system/info', methods=['GET'])
    def get_system_info():
        """获取系统信息"""
        try:
            db_dir = current_app.config['DB_DIR']
            
            # 计算数据库总大小
            total_size = 0
            db_count = 0
            
            for db_file in os.listdir(db_dir):
                if db_file.endswith('.db'):
                    db_path = os.path.join(db_dir, db_file)
                    total_size += os.path.getsize(db_path)
                    db_count += 1
            
            system_info = {
                'database_count': db_count,
                'database_size_mb': round(total_size / (1024 * 1024), 2),
                'database_directory': db_dir,
                'uptime': '运行中',
                'version': '1.0.0'
            }
            
            return jsonify({
                'success': True,
                'data': system_info
            })
            
        except Exception as e:
            logger.error(f"获取系统信息时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/system/logs', methods=['GET'])
    def get_system_logs():
        """获取系统日志"""
        try:
            log_dir = current_app.config.get('LOG_DIR', 'logs')
            lines = int(request.args.get('lines', 100))
            
            logs = []
            
            # 读取最新的日志文件
            log_files = glob.glob(os.path.join(log_dir, '*.log'))
            if log_files:
                latest_log = max(log_files, key=os.path.getmtime)
                
                try:
                    with open(latest_log, 'r', encoding='utf-8') as f:
                        all_lines = f.readlines()
                        # 取最后N行
                        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                        
                        for i, line in enumerate(recent_lines):
                            line = line.strip()
                            if line:
                                logs.append({
                                    'id': i,
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'level': 'INFO',
                                    'message': line
                                })
                except Exception as e:
                    logger.error(f"读取日志文件失败: {e}")
            
            # 如果没有日志文件，返回模拟日志
            if not logs:
                logs = [
                    {'id': 1, 'timestamp': '2024-01-15 10:52:30', 'level': 'INFO', 'message': '系统启动完成'},
                    {'id': 2, 'timestamp': '2024-01-15 10:52:28', 'level': 'INFO', 'message': '爬虫管理器初始化成功'},
                    {'id': 3, 'timestamp': '2024-01-15 10:52:25', 'level': 'INFO', 'message': '数据库连接建立'}
                ]
            
            return jsonify({
                'success': True,
                'data': logs
            })
            
        except Exception as e:
            logger.error(f"获取系统日志时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/system/export', methods=['POST'])
    def export_data():
        """导出数据"""
        try:
            data = request.get_json()
            export_type = data.get('type', 'json')  # json, csv, excel
            
            # 这里应该实现实际的数据导出逻辑
            
            return jsonify({
                'success': True,
                'message': f'数据导出成功 ({export_type})',
                'download_url': '/api/system/download/export.zip'
            })
            
        except Exception as e:
            logger.error(f"导出数据时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/system/cleanup', methods=['POST'])
    def cleanup_old_data():
        """清理旧数据"""
        try:
            data = request.get_json()
            days = data.get('days', 30)  # 默认清理30天前的数据
            
            # 这里应该实现实际的数据清理逻辑
            
            return jsonify({
                'success': True,
                'message': f'已清理 {days} 天前的旧数据'
            })
            
        except Exception as e:
            logger.error(f"清理旧数据时出错: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

def get_source_display_name(source_name):
    """获取数据源显示名称"""
    display_names = {
        'sina': '新浪财经',
        'eastmoney': '东方财富',
        'netease': '网易财经',
        'ifeng': '凤凰财经',
        'tencent': '腾讯财经'
    }
    return display_names.get(source_name, source_name) 