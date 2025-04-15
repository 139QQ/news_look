#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能监控Web路由
提供实时性能监控和历史数据查询API
"""

import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template

from app.utils.performance_monitor import (
    get_active_crawlers, get_global_stats, get_performance_summary,
    get_performance_history, get_daily_stats, reset_stats
)

# 创建蓝图
monitor_bp = Blueprint('monitor', __name__, url_prefix='/monitor')

@monitor_bp.route('/')
def monitor_dashboard():
    """性能监控仪表板页面"""
    return render_template('monitor/dashboard.html')

@monitor_bp.route('/api/active_crawlers')
def api_active_crawlers():
    """获取活动爬虫API"""
    return jsonify(get_active_crawlers())

@monitor_bp.route('/api/global_stats')
def api_global_stats():
    """获取全局统计API"""
    return jsonify(get_global_stats())

@monitor_bp.route('/api/performance_summary')
def api_performance_summary():
    """获取性能摘要API"""
    days = request.args.get('days', 7, type=int)
    return jsonify(get_performance_summary(days))

@monitor_bp.route('/api/performance_history')
def api_performance_history():
    """获取性能历史API"""
    days = request.args.get('days', 7, type=int)
    crawler_type = request.args.get('crawler_type')
    source = request.args.get('source')
    
    history = get_performance_history(days=days, crawler_type=crawler_type, source=source)
    return jsonify(history)

@monitor_bp.route('/api/daily_stats')
def api_daily_stats():
    """获取每日统计API"""
    days = request.args.get('days', 30, type=int)
    return jsonify(get_daily_stats(days))

@monitor_bp.route('/api/stats/reset', methods=['POST'])
def api_reset_stats():
    """重置统计API"""
    reset_stats()
    return jsonify({'success': True, 'message': '统计数据已重置'})

@monitor_bp.route('/api/charts/requests')
def api_charts_requests():
    """请求统计图表数据API"""
    days = request.args.get('days', 7, type=int)
    daily_stats = get_daily_stats(days)
    
    # 准备图表数据
    dates = []
    success = []
    failure = []
    
    for day in daily_stats:
        dates.append(day['date'])
        success.append(day['success_requests'])
        failure.append(day['failure_requests'])
    
    return jsonify({
        'labels': dates,
        'datasets': [
            {
                'label': '成功请求',
                'data': success,
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'borderColor': 'rgba(75, 192, 192, 1)',
                'borderWidth': 1
            },
            {
                'label': '失败请求',
                'data': failure,
                'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                'borderColor': 'rgba(255, 99, 132, 1)',
                'borderWidth': 1
            }
        ]
    })

@monitor_bp.route('/api/charts/news')
def api_charts_news():
    """新闻统计图表数据API"""
    days = request.args.get('days', 7, type=int)
    daily_stats = get_daily_stats(days)
    
    # 准备图表数据
    dates = []
    news_counts = []
    
    for day in daily_stats:
        dates.append(day['date'])
        news_counts.append(day['news_count'])
    
    return jsonify({
        'labels': dates,
        'datasets': [
            {
                'label': '新闻数量',
                'data': news_counts,
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'borderColor': 'rgba(54, 162, 235, 1)',
                'borderWidth': 1
            }
        ]
    })

@monitor_bp.route('/api/charts/response_time')
def api_charts_response_time():
    """响应时间统计图表数据API"""
    days = request.args.get('days', 7, type=int)
    daily_stats = get_daily_stats(days)
    
    # 准备图表数据
    dates = []
    response_times = []
    
    for day in daily_stats:
        dates.append(day['date'])
        response_times.append(day['avg_response_time'])
    
    return jsonify({
        'labels': dates,
        'datasets': [
            {
                'label': '平均响应时间(秒)',
                'data': response_times,
                'backgroundColor': 'rgba(153, 102, 255, 0.2)',
                'borderColor': 'rgba(153, 102, 255, 1)',
                'borderWidth': 1
            }
        ]
    })

@monitor_bp.route('/api/charts/crawler_stats')
def api_charts_crawler_stats():
    """爬虫统计图表数据API"""
    days = request.args.get('days', 7, type=int)
    summary = get_performance_summary(days)
    crawler_stats = summary.get('crawler_stats', [])
    
    # 准备图表数据
    labels = []
    news_counts = []
    durations = []
    
    for stat in crawler_stats:
        labels.append(stat['crawler_type'] or '未知')
        news_counts.append(stat['news_count'])
        durations.append(stat['avg_duration'])
    
    return jsonify({
        'labels': labels,
        'datasets': [
            {
                'label': '新闻数量',
                'data': news_counts,
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)',
                    'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)'
                ],
                'borderColor': [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)'
                ],
                'borderWidth': 1
            }
        ],
        'durations': durations
    })

@monitor_bp.route('/api/charts/source_stats')
def api_charts_source_stats():
    """来源统计图表数据API"""
    days = request.args.get('days', 7, type=int)
    summary = get_performance_summary(days)
    source_stats = summary.get('source_stats', [])
    
    # 准备图表数据
    labels = []
    news_counts = []
    
    for stat in source_stats:
        labels.append(stat['source'] or '未知')
        news_counts.append(stat['news_count'])
    
    return jsonify({
        'labels': labels,
        'datasets': [
            {
                'label': '新闻数量',
                'data': news_counts,
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)',
                    'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)',
                    'rgba(255, 159, 64, 0.2)',
                    'rgba(201, 203, 207, 0.2)'
                ],
                'borderColor': [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(201, 203, 207, 1)'
                ],
                'borderWidth': 1
            }
        ]
    }) 