#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 用户API
"""

from flask import Blueprint, request, jsonify
from app.db.user_preferences_db import UserPreferencesDB
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 创建蓝图
user_api = Blueprint('user_api', __name__)

# 初始化用户偏好数据库
user_prefs_db = UserPreferencesDB()

@user_api.route('/api/news/<news_id>/save', methods=['POST'])
def save_news(news_id):
    """
    收藏/取消收藏新闻
    
    Args:
        news_id: 新闻ID
        
    Returns:
        JSON响应
    """
    try:
        data = request.json
        saved = data.get('saved', True)  # 默认为收藏操作
        user_id = data.get('user_id', 'default_user')  # 默认用户
        
        logger.info(f"用户{user_id}{'收藏' if saved else '取消收藏'}新闻: {news_id}")
        
        if saved:
            result = user_prefs_db.save_news(user_id, news_id)
        else:
            result = user_prefs_db.unsave_news(user_id, news_id)
        
        return jsonify({
            'success': result,
            'news_id': news_id,
            'saved': saved,
            'message': f"{'收藏' if saved else '取消收藏'}{'成功' if result else '失败'}"
        })
        
    except Exception as e:
        logger.error(f"收藏/取消收藏新闻失败: {str(e)}")
        return jsonify({
            'success': False,
            'news_id': news_id,
            'message': f"操作失败: {str(e)}"
        }), 500

@user_api.route('/api/news/<news_id>/read', methods=['POST'])
def mark_read(news_id):
    """
    标记新闻为已读/未读
    
    Args:
        news_id: 新闻ID
        
    Returns:
        JSON响应
    """
    try:
        data = request.json
        read = data.get('read', True)  # 默认为标记已读操作
        user_id = data.get('user_id', 'default_user')  # 默认用户
        
        logger.info(f"用户{user_id}将新闻{news_id}标记为{'已读' if read else '未读'}")
        
        if read:
            result = user_prefs_db.mark_as_read(user_id, news_id)
        else:
            result = user_prefs_db.mark_as_unread(user_id, news_id)
        
        return jsonify({
            'success': result,
            'news_id': news_id,
            'read': read,
            'message': f"标记{'已读' if read else '未读'}{'成功' if result else '失败'}"
        })
        
    except Exception as e:
        logger.error(f"标记新闻已读/未读失败: {str(e)}")
        return jsonify({
            'success': False,
            'news_id': news_id,
            'message': f"操作失败: {str(e)}"
        }), 500

@user_api.route('/api/user/saved_news', methods=['GET'])
def get_saved_news():
    """
    获取用户收藏的新闻ID列表
    
    Returns:
        JSON响应
    """
    try:
        user_id = request.args.get('user_id', 'default_user')  # 默认用户
        
        saved_news = user_prefs_db.get_saved_news_ids(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'saved_news': saved_news,
            'count': len(saved_news)
        })
        
    except Exception as e:
        logger.error(f"获取收藏新闻列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"获取失败: {str(e)}"
        }), 500

@user_api.route('/api/user/read_news', methods=['GET'])
def get_read_news():
    """
    获取用户已读的新闻ID列表
    
    Returns:
        JSON响应
    """
    try:
        user_id = request.args.get('user_id', 'default_user')  # 默认用户
        
        read_news = user_prefs_db.get_read_news_ids(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'read_news': read_news,
            'count': len(read_news)
        })
        
    except Exception as e:
        logger.error(f"获取已读新闻列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"获取失败: {str(e)}"
        }), 500

@user_api.route('/api/news/status', methods=['GET'])
def get_news_status():
    """
    获取新闻的收藏和已读状态
    
    Returns:
        JSON响应
    """
    try:
        news_id = request.args.get('news_id')
        user_id = request.args.get('user_id', 'default_user')  # 默认用户
        
        if not news_id:
            return jsonify({
                'success': False,
                'message': "未提供news_id参数"
            }), 400
        
        is_saved = user_prefs_db.is_saved(user_id, news_id)
        is_read = user_prefs_db.is_read(user_id, news_id)
        
        return jsonify({
            'success': True,
            'news_id': news_id,
            'user_id': user_id,
            'saved': is_saved,
            'read': is_read
        })
        
    except Exception as e:
        logger.error(f"获取新闻状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"获取失败: {str(e)}"
        }), 500 