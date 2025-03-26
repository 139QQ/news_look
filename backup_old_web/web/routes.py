#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - Web路由
"""

import os
import sys
from flask import render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import math

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import NewsDatabase
from utils.article_processor import ArticleProcessor
from utils.text_cleaner import clean_text, format_news_content, format_datetime

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'finance_news.db')

def register_routes(app):
    """注册路由"""
    
    @app.route('/')
    def index():
        """首页，显示最新新闻列表"""
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        keyword = request.args.get('keyword', '')
        days = request.args.get('days', 7, type=int)
        source = request.args.get('source', '')
        sentiment = request.args.get('sentiment', '')
        view_mode = request.args.get('view', 'list')  # 新增：视图模式参数
        
        # 查询数据库
        db = NewsDatabase(DB_PATH)
        
        # 处理情感过滤
        sentiment_value = None
        if sentiment == 'positive':
            sentiment_value = 1
        elif sentiment == 'negative':
            sentiment_value = -1
        elif sentiment == 'neutral':
            sentiment_value = 0
        
        # 查询新闻数据
        news_data = db.query_news(keyword=keyword, days=days, source=source, 
                               limit=per_page, offset=(page-1)*per_page)
        
        # 过滤情感
        if sentiment_value is not None:
            if sentiment_value > 0:
                news_data = [news for news in news_data if news['sentiment'] > 0.2]
            elif sentiment_value < 0:
                news_data = [news for news in news_data if news['sentiment'] < -0.2]
            else:
                news_data = [news for news in news_data if -0.2 <= news['sentiment'] <= 0.2]
        
        # 全面清理新闻数据中的乱码
        for item in news_data:
            # 标题处理
            if 'title' in item and item['title']:
                item['title'] = clean_text(item['title'])
                
            # 内容处理 
            if 'content' in item and item['content']:
                item['content'] = format_news_content(item['content'], 200)
                
            # 作者处理
            if 'author' in item and item['author']:
                item['author'] = clean_text(item['author'])
                
            # 时间处理
            if 'pub_time' in item and item['pub_time']:
                item['pub_time'] = format_datetime(item['pub_time'])
                
            # 来源处理
            if 'source' in item:
                if not item['source'] or item['source'] == '未知来源':
                    # 尝试从URL推断来源
                    if 'url' in item and item['url']:
                        url = item['url'].lower()
                        if 'eastmoney.com' in url:
                            item['source'] = '东方财富网'
                        elif 'sina.com' in url or 'sina.cn' in url:
                            item['source'] = '新浪财经'
                        elif 'qq.com' in url:
                            item['source'] = '腾讯财经'
                        elif '163.com' in url:
                            item['source'] = '网易财经'
                        elif 'ifeng.com' in url:
                            item['source'] = '凤凰财经'
                
            # 关键词处理
            if 'keywords' in item and item['keywords']:
                try:
                    if isinstance(item['keywords'], str):
                        if item['keywords'].startswith('[') and item['keywords'].endswith(']'):
                            import json
                            kw_list = json.loads(item['keywords'])
                            item['keywords'] = ','.join(kw_list)
                        elif ',' in item['keywords']:
                            kws = item['keywords'].split(',')
                            item['keywords'] = ','.join([clean_text(kw) for kw in kws])
                        else:
                            item['keywords'] = clean_text(item['keywords'])
                except:
                    pass
        
        # 获取总数
        total = db.count_news(keyword=keyword, days=days, source=source)
        
        # 计算分页
        total_pages = math.ceil(total / per_page)
        has_prev = page > 1
        has_next = page < total_pages
        
        # 获取所有来源
        sources = db.get_sources()
        
        # 获取热门关键词
        hot_keywords = get_hot_keywords(db)
        
        # 获取更多统计数据
        today = datetime.now().strftime('%Y-%m-%d')
        today_count = db.count_news_by_date(today)
        total_count = db.count_news()
        
        # 获取情感分布
        positive_count = db.count_news_by_sentiment(0.2, float('inf'))
        negative_count = db.count_news_by_sentiment(float('-inf'), -0.2)
        neutral_count = db.count_news_by_sentiment(-0.2, 0.2)
        
        # 获取日期统计数据
        date_counts = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            count = db.count_news_by_date(date)
            date_counts.append({'date': date, 'count': count})
        date_counts.reverse()  # 按时间顺序排列
        
        # 按类别分组热门关键词
        categorized_keywords = categorize_keywords(hot_keywords)
        
        # 按来源分类的新闻数据
        categorized_news = {}
        if view_mode == 'card':
            for src in sources:
                src_news = db.query_news(days=days, source=src, limit=5)
                # 清理数据
                for item in src_news:
                    if 'title' in item and item['title']:
                        item['title'] = clean_text(item['title'])
                    if 'content' in item and item['content']:
                        item['content'] = format_news_content(item['content'], 100)
                    if 'author' in item and item['author']:
                        item['author'] = clean_text(item['author'])
                    if 'pub_time' in item and item['pub_time']:
                        item['pub_time'] = format_datetime(item['pub_time'])
                
                if src_news:
                    categorized_news[src] = src_news
        
        return render_template('index.html',
                            news=news_data,
                            page=page,
                            per_page=per_page,
                            total=total,
                            total_pages=total_pages,
                            has_prev=has_prev,
                            has_next=has_next,
                            keyword=keyword,
                            days=days,
                            source=source,
                            sentiment=sentiment,
                            sources=sources,
                            hot_keywords=hot_keywords,
                            categorized_keywords=categorized_keywords,
                            today_count=today_count,
                            total_count=total_count,
                            positive_count=positive_count,
                            negative_count=negative_count,
                            neutral_count=neutral_count,
                            date_counts=date_counts,
                            view_mode=view_mode,
                            categorized_news=categorized_news)
    
    @app.route('/news/<news_id>')
    def news_detail(news_id):
        """新闻详情页"""
        db = NewsDatabase(DB_PATH)
        news = db.get_news_by_id(news_id)
        
        if not news:
            flash('新闻不存在', 'danger')
            return redirect(url_for('index'))
        
        # 清理新闻数据中的乱码
        if news:
            news['title'] = clean_text(news['title'])
            news['content'] = clean_text(news['content'])
            if news['author']:
                news['author'] = clean_text(news['author'])
        
        # 获取相关新闻
        related_news = get_related_news(db, news)
        
        # 清理相关新闻数据
        for item in related_news:
            item['title'] = clean_text(item['title'])
            item['content'] = format_news_content(item['content'], 100)
        
        return render_template('news_detail.html', news=news, related_news=related_news)
    
    @app.route('/search')
    def search():
        """搜索页面，重定向到首页并带上搜索参数"""
        keyword = request.args.get('keyword', '')
        return redirect(url_for('index', keyword=keyword))
    
    @app.route('/dashboard')
    def dashboard():
        """数据统计页面"""
        db = NewsDatabase(DB_PATH)
        
        # 获取总新闻数
        total_news = db.count_news()
        
        # 获取来源统计
        sources = db.get_sources()
        source_counts = []
        for source in sources:
            count = db.count_news(source=source)
            source_counts.append({'name': source, 'count': count})
        
        # 获取日期统计
        date_counts = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            count = db.count_news_by_date(date)
            date_counts.append({'date': date, 'count': count})
        
        # 获取情感分析统计
        positive_count = db.count_news_by_sentiment(0.2, float('inf'))
        negative_count = db.count_news_by_sentiment(float('-inf'), -0.2)
        neutral_count = db.count_news_by_sentiment(-0.2, 0.2)
        
        return render_template('dashboard.html',
                            total_news=total_news,
                            source_counts=source_counts,
                            date_counts=date_counts,
                            positive_count=positive_count,
                            negative_count=negative_count,
                            neutral_count=neutral_count)
    
    @app.route('/crawler')
    def crawler():
        """爬虫管理页面"""
        return render_template('crawler.html')
    
    @app.route('/api/news')
    def api_news():
        """API: 获取新闻列表"""
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        keyword = request.args.get('keyword', '')
        days = request.args.get('days', 7, type=int)
        source = request.args.get('source', '')
        
        # 查询数据库
        db = NewsDatabase(DB_PATH)
        news_data = db.query_news(keyword=keyword, days=days, source=source, 
                                limit=per_page, offset=(page-1)*per_page)
        
        # 获取总数
        total = db.count_news(keyword=keyword, days=days, source=source)
        
        # 计算分页
        total_pages = math.ceil(total / per_page)
        
        return jsonify({
            'news': news_data,
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages
        })

    @app.route('/feedback', methods=['GET', 'POST'])
    def feedback():
        """用户反馈页面"""
        success_message = None
        error_message = None
        
        if request.method == 'POST':
            try:
                # 获取表单数据
                feedback_type = request.form.get('feedback_type')
                title = request.form.get('title')
                content = request.form.get('content')
                email = request.form.get('email')
                urgent = 'urgent' in request.form
                
                # 验证必填字段
                if not all([feedback_type, title, content]):
                    error_message = "请填写所有必填字段"
                elif len(content) > 500:
                    error_message = "反馈内容不能超过500个字符"
                else:
                    # 生成跟踪ID
                    tracking_id = f"FB-{datetime.now().strftime('%Y%m%d')}-{hash(title + content) % 10000:04d}"
                    
                    # 准备反馈数据
                    feedback_data = {
                        'id': tracking_id,
                        'feedback_type': feedback_type,
                        'title': title,
                        'content': content,
                        'email': email,
                        'urgent': urgent,
                        'submit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # 保存到数据库
                    db = NewsDatabase(DB_PATH)
                    if db.save_feedback(feedback_data):
                        success_message = f"感谢您的反馈！我们已收到您的信息，跟踪ID: {tracking_id}"
                        
                        # 如果提供了邮箱，可以发送确认邮件
                        if email:
                            # 这里可以添加发送确认邮件的代码
                            # 例如：send_confirmation_email(email, tracking_id)
                            pass
                    else:
                        error_message = "保存反馈时出错，请稍后再试"
            
            except Exception as e:
                error_message = f"提交反馈时出错: {str(e)}"
        
        # 获取当前时间，用于模板渲染
        now = datetime.now()
        
        return render_template('feedback.html', 
                              success_message=success_message, 
                              error_message=error_message,
                              now=now)
    
    @app.route('/feedback/status', methods=['GET'])
    def feedback_status():
        """反馈状态查询页面"""
        feedback_id = request.args.get('id')
        feedback_data = None
        error_message = None
        
        if feedback_id:
            try:
                db = NewsDatabase(DB_PATH)
                feedback_data = db.get_feedback(feedback_id)
                
                if not feedback_data:
                    error_message = f"未找到ID为 {feedback_id} 的反馈记录"
            except Exception as e:
                error_message = f"查询反馈状态时出错: {str(e)}"
        
        # 获取当前时间，用于模板渲染
        now = datetime.now()
        
        return render_template('feedback_status.html',
                              feedback_id=feedback_id,
                              feedback_data=feedback_data,
                              error_message=error_message,
                              now=now)

def get_hot_keywords(db, limit=10):
    """获取热门关键词"""
    news_data = db.query_news(days=3, limit=100)  # 获取最近3天的100条新闻
    
    # 统计关键词频率
    keyword_freq = {}
    for news in news_data:
        if news['keywords']:
            for keyword in news['keywords'].split(','):
                keyword = keyword.strip()
                if len(keyword) > 1:  # 忽略单字符关键词
                    keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
    
    # 排序并返回前N个
    sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
    return [{'keyword': k, 'count': v} for k, v in sorted_keywords[:limit]]

def categorize_keywords(keywords):
    """将关键词按类别分组
    
    Args:
        keywords (list): 关键词列表，每项包含 keyword 和 count
        
    Returns:
        dict: 按类别分组的关键词
    """
    # 预定义的类别和对应的关键词
    categories = {
        '市场': ['股市', '大盘', '指数', '涨停', '跌停', '牛市', '熊市', '震荡', '反弹', '回调', 
                '成交量', '市值', '交易', '股价', '股票', '基金', '债券', '期货', '外汇'],
        '行业': ['科技', '金融', '医药', '房地产', '能源', '消费', '制造', '互联网', '通信', '教育', 
                '农业', '物流', '零售', '餐饮', '旅游', '娱乐', '汽车', '航空', '银行', '保险'],
        '公司': ['公司', '企业', '集团', '上市', '融资', '并购', '重组', '盈利', '亏损', '业绩', 
                '财报', '营收', '利润', '股东', '董事', '高管', '战略', '转型', '创新'],
        '政策': ['政策', '监管', '法规', '央行', '证监会', '银保监会', '利率', '税收', '补贴', '改革', 
                '开放', '宏观', '调控', '财政', '货币', '外资', '国资', '民营']
    }
    
    # 初始化结果
    result = {category: [] for category in categories}
    result['其他'] = []  # 未分类的关键词
    
    # 分类关键词
    for item in keywords:
        keyword = item['keyword']
        categorized = False
        
        # 检查关键词是否属于某个类别
        for category, keywords_list in categories.items():
            for cat_keyword in keywords_list:
                if cat_keyword in keyword or keyword in cat_keyword:
                    result[category].append(item)
                    categorized = True
                    break
            if categorized:
                break
        
        # 如果未分类，则归入"其他"
        if not categorized:
            result['其他'].append(item)
    
    # 移除空类别
    result = {k: v for k, v in result.items() if v}
    
    return result

def get_related_news(db, news, limit=5):
    """获取相关新闻"""
    if not news or not news['keywords']:
        return []
    
    # 使用关键词查找相关新闻
    keywords = news['keywords'].split(',')
    related = []
    
    for keyword in keywords:
        keyword = keyword.strip()
        if keyword:
            results = db.query_news(keyword=keyword, limit=10)
            for result in results:
                if result['id'] != news['id'] and result not in related:
                    related.append(result)
                    if len(related) >= limit:
                        return related
    
    return related

# 在处理新闻数据时添加编码修复
def clean_text(text):
    """清理文本中的乱码"""
    if not text:
        return ""
    
    # 导入正式的文本清理模块
    from utils.text_cleaner import clean_text as cleaner
    return cleaner(text)

# 格式化日期时间
def format_datetime(date_str):
    """格式化日期时间字符串"""
    if not date_str:
        return "未知时间"
    
    # 导入正式的日期格式化模块
    from utils.text_cleaner import format_datetime as formatter
    return formatter(date_str) 