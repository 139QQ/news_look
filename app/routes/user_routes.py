#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 用户偏好API路由
"""

from flask import Blueprint, request, jsonify, g, session
from app.db.user_preferences_db import UserPreferencesDB
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 创建蓝图
user_bp = Blueprint('user', __name__, url_prefix='/api/user')
user_prefs_db = UserPreferencesDB()

@user_bp.before_request
def before_request():
    """请求前处理 - 获取当前用户ID"""
    # 获取当前用户ID，如果没有则使用默认值
    g.user_id = session.get('user_id', 'default_user')

@user_bp.route('/toggle_saved', methods=['POST'])
def toggle_saved():
    """切换文章的收藏状态"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无效的请求数据"}), 400
            
        user_id = data.get('user_id', g.user_id)
        news_id = data.get('news_id')
        saved = data.get('saved', True)
        
        # 验证必要参数
        if not news_id:
            return jsonify({"success": False, "message": "新闻ID不能为空"}), 400
            
        # 更新收藏状态
        if saved:
            result = user_prefs_db.save_news(user_id, news_id)
        else:
            result = user_prefs_db.unsave_news(user_id, news_id)
        
        # 获取更新后的状态
        is_saved = user_prefs_db.is_saved(user_id, news_id)
        
        return jsonify({
            "success": True,
            "is_saved": is_saved,
            "message": "收藏状态已更新"
        })
    except Exception as e:
        logger.error(f"更新收藏状态时出错: {str(e)}")
        return jsonify({"success": False, "message": f"服务器错误: {str(e)}"}), 500

@user_bp.route('/toggle_read', methods=['POST'])
def toggle_read():
    """切换文章的已读状态"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无效的请求数据"}), 400
            
        user_id = data.get('user_id', g.user_id)
        news_id = data.get('news_id')
        read = data.get('read', True)
        
        # 验证必要参数
        if not news_id:
            return jsonify({"success": False, "message": "新闻ID不能为空"}), 400
            
        # 更新已读状态
        if read:
            result = user_prefs_db.mark_as_read(user_id, news_id)
        else:
            result = user_prefs_db.mark_as_unread(user_id, news_id)
        
        # 获取更新后的状态
        is_read = user_prefs_db.is_read(user_id, news_id)
        
        return jsonify({
            "success": True,
            "is_read": is_read,
            "message": "阅读状态已更新"
        })
    except Exception as e:
        logger.error(f"更新阅读状态时出错: {str(e)}")
        return jsonify({"success": False, "message": f"服务器错误: {str(e)}"}), 500

@user_bp.route('/saved_news', methods=['GET'])
def get_saved_news():
    """获取用户收藏的新闻ID列表"""
    try:
        user_id = request.args.get('user_id', g.user_id)
        
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

@user_bp.route('/read_news', methods=['GET'])
def get_read_news():
    """获取用户已读的新闻ID列表"""
    try:
        user_id = request.args.get('user_id', g.user_id)
        
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

@user_bp.route('/news/status', methods=['GET'])
def get_news_status():
    """获取新闻的收藏和已读状态"""
    try:
        news_id = request.args.get('news_id')
        user_id = request.args.get('user_id', g.user_id)
        
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