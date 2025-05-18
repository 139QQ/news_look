from flask import Blueprint, jsonify, request
from app.database.news import NewsDB
from app.database.user_preferences import UserPreferencesDB
import logging

api = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

# ... existing code ...

@api.route('/user/toggle_saved', methods=['POST'])
def toggle_saved():
    """切换文章的收藏状态"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无效的请求数据"}), 400
            
        user_id = data.get('user_id')
        news_id = data.get('news_id')
        saved = data.get('saved', True)
        
        # 验证必要参数
        if not user_id or not news_id:
            return jsonify({"success": False, "message": "用户ID和新闻ID不能为空"}), 400
            
        # 使用用户偏好数据库实例
        user_prefs_db = UserPreferencesDB()
        
        # 更新收藏状态
        if saved:
            user_prefs_db.save_news(user_id, news_id)
        else:
            user_prefs_db.unsave_news(user_id, news_id)
        
        # 获取更新后的状态
        is_saved = user_prefs_db.is_news_saved(user_id, news_id)
        
        return jsonify({
            "success": True,
            "is_saved": is_saved,
            "message": "收藏状态已更新"
        })
    except Exception as e:
        logger.error(f"更新收藏状态时出错: {str(e)}")
        return jsonify({"success": False, "message": f"服务器错误: {str(e)}"}), 500

@api.route('/user/toggle_read', methods=['POST'])
def toggle_read():
    """切换文章的已读状态"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无效的请求数据"}), 400
            
        user_id = data.get('user_id')
        news_id = data.get('news_id')
        read = data.get('read', True)
        
        # 验证必要参数
        if not user_id or not news_id:
            return jsonify({"success": False, "message": "用户ID和新闻ID不能为空"}), 400
            
        # 使用用户偏好数据库实例
        user_prefs_db = UserPreferencesDB()
        
        # 更新已读状态
        if read:
            user_prefs_db.mark_as_read(user_id, news_id)
        else:
            user_prefs_db.mark_as_unread(user_id, news_id)
        
        # 获取更新后的状态
        is_read = user_prefs_db.is_news_read(user_id, news_id)
        
        return jsonify({
            "success": True,
            "is_read": is_read,
            "message": "阅读状态已更新"
        })
    except Exception as e:
        logger.error(f"更新阅读状态时出错: {str(e)}")
        return jsonify({"success": False, "message": f"服务器错误: {str(e)}"}), 500 