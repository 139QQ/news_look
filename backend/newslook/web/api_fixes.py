#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API修复和数据结构标准化
确保新闻详情API返回正确的数据结构
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def standardize_news_data(news_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化新闻数据结构
    
    Args:
        news_data: 原始新闻数据
        
    Returns:
        Dict: 标准化后的新闻数据
    """
    if not news_data:
        return create_empty_news_data()
    
    # 创建标准化的新闻数据结构
    standardized = {
        'id': news_data.get('id', ''),
        'title': news_data.get('title', ''),
        'content': news_data.get('content', ''),
        'summary': news_data.get('summary', ''),
        'source': news_data.get('source', ''),
        'category': news_data.get('category', ''),
        'url': news_data.get('url', ''),
        'keywords': parse_keywords(news_data.get('keywords')),
        'images': parse_images(news_data.get('images')),
        'related_stocks': parse_related_stocks(news_data.get('related_stocks')),
        'publish_time': standardize_time(news_data.get('publish_time') or news_data.get('pub_time')),
        'crawl_time': standardize_time(news_data.get('crawl_time')),
        'sentiment': news_data.get('sentiment', ''),
        'classification': news_data.get('classification', ''),
        'author': news_data.get('author', '')
    }
    
    # 验证和清理数据
    standardized = validate_and_clean_data(standardized)
    
    return standardized


def create_empty_news_data() -> Dict[str, Any]:
    """创建空的新闻数据结构"""
    return {
        'id': '',
        'title': '新闻数据不存在',
        'content': '请求的新闻数据不存在或已被删除。',
        'summary': '',
        'source': '系统提示',
        'category': '',
        'url': '',
        'keywords': [],
        'images': [],
        'related_stocks': [],
        'publish_time': datetime.now().isoformat(),
        'crawl_time': datetime.now().isoformat(),
        'sentiment': '',
        'classification': '',
        'author': ''
    }


def parse_keywords(keywords_data) -> list:
    """解析关键词数据"""
    if not keywords_data:
        return []
    
    if isinstance(keywords_data, list):
        return [str(k).strip() for k in keywords_data if k]
    
    if isinstance(keywords_data, str):
        try:
            # 尝试解析JSON
            parsed = json.loads(keywords_data)
            if isinstance(parsed, list):
                return [str(k).strip() for k in parsed if k]
            else:
                return [str(parsed).strip()] if parsed else []
        except json.JSONDecodeError:
            # 按逗号分割
            return [k.strip() for k in keywords_data.split(',') if k.strip()]
    
    return []


def parse_images(images_data) -> list:
    """解析图片数据"""
    if not images_data:
        return []
    
    if isinstance(images_data, list):
        return [str(img).strip() for img in images_data if img]
    
    if isinstance(images_data, str):
        try:
            # 尝试解析JSON
            parsed = json.loads(images_data)
            if isinstance(parsed, list):
                return [str(img).strip() for img in parsed if img]
            else:
                return [str(parsed).strip()] if parsed else []
        except json.JSONDecodeError:
            # 按逗号分割
            return [img.strip() for img in images_data.split(',') if img.strip()]
    
    return []


def parse_related_stocks(stocks_data) -> list:
    """解析相关股票数据"""
    if not stocks_data:
        return []
    
    if isinstance(stocks_data, list):
        return [str(stock).strip() for stock in stocks_data if stock]
    
    if isinstance(stocks_data, str):
        try:
            # 尝试解析JSON
            parsed = json.loads(stocks_data)
            if isinstance(parsed, list):
                return [str(stock).strip() for stock in parsed if stock]
            else:
                return [str(parsed).strip()] if parsed else []
        except json.JSONDecodeError:
            # 按逗号分割
            return [stock.strip() for stock in stocks_data.split(',') if stock.strip()]
    
    return []


def standardize_time(time_data) -> str:
    """标准化时间格式"""
    if not time_data:
        return ''
    
    if isinstance(time_data, datetime):
        return time_data.isoformat()
    
    if isinstance(time_data, str):
        # 尝试解析各种时间格式
        time_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%d',
        ]
        
        for fmt in time_formats:
            try:
                dt = datetime.strptime(time_data, fmt)
                return dt.isoformat()
            except ValueError:
                continue
        
        # 如果都解析失败，返回原字符串
        return time_data
    
    return str(time_data)


def validate_and_clean_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """验证和清理数据"""
    # 确保ID不为空
    if not data.get('id'):
        data['id'] = f"generated_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 确保标题不为空
    if not data.get('title'):
        data['title'] = '标题信息缺失'
    
    # 清理HTML标签（如果需要）
    if data.get('content'):
        # 基本的HTML清理（保留常用标签）
        content = data['content']
        # 这里可以添加更复杂的HTML清理逻辑
        data['content'] = content
    
    # 确保来源信息
    if not data.get('source'):
        data['source'] = '未知来源'
    
    # 确保分类信息
    if not data.get('category'):
        data['category'] = '未分类'
    
    # 验证URL格式
    url = data.get('url', '')
    if url and not url.startswith(('http://', 'https://', '#')):
        data['url'] = f"http://{url}"
    
    return data


def format_api_response(news_data: Dict[str, Any], success: bool = True, message: str = 'success') -> Dict[str, Any]:
    """
    格式化API响应
    
    Args:
        news_data: 新闻数据
        success: 是否成功
        message: 响应消息
        
    Returns:
        Dict: 格式化的API响应
    """
    if success:
        return {
            'code': 0,
            'message': message,
            'data': news_data,
            'timestamp': datetime.now().isoformat()
        }
    else:
        return {
            'code': 1,
            'message': message,
            'data': None,
            'timestamp': datetime.now().isoformat()
        }


def diagnose_data_issues(news_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    诊断数据质量问题
    
    Args:
        news_data: 新闻数据
        
    Returns:
        Dict: 诊断报告
    """
    issues = []
    warnings = []
    
    # 检查必要字段
    required_fields = ['id', 'title', 'content', 'source']
    for field in required_fields:
        if not news_data.get(field):
            issues.append(f"缺少必要字段: {field}")
    
    # 检查可选但重要的字段
    optional_fields = ['category', 'publish_time', 'url']
    for field in optional_fields:
        if not news_data.get(field):
            warnings.append(f"缺少字段: {field}")
    
    # 检查数据质量
    if news_data.get('title') and len(news_data['title']) < 5:
        warnings.append("标题过短")
    
    if news_data.get('content') and len(news_data['content']) < 50:
        warnings.append("内容过短")
    
    if news_data.get('source') == '未知来源':
        warnings.append("来源信息缺失")
    
    # 计算数据质量分数
    total_fields = 8  # 总共8个重要字段
    present_fields = sum(1 for field in ['id', 'title', 'content', 'source', 'category', 'publish_time', 'url', 'keywords'] 
                        if news_data.get(field))
    
    quality_score = present_fields / total_fields
    
    return {
        'quality_score': quality_score,
        'issues': issues,
        'warnings': warnings,
        'present_fields': present_fields,
        'total_fields': total_fields
    }


def create_diagnostic_news_detail(news_id: str, error_message: str = '') -> Dict[str, Any]:
    """
    创建诊断用的新闻详情数据
    
    Args:
        news_id: 新闻ID
        error_message: 错误消息
        
    Returns:
        Dict: 诊断用的新闻数据
    """
    return {
        'id': news_id,
        'title': f'新闻数据诊断 (ID: {news_id})',
        'content': f'''
        <div class="diagnostic-info">
            <h3>数据诊断信息</h3>
            <p><strong>新闻ID:</strong> {news_id}</p>
            <p><strong>状态:</strong> 数据获取失败</p>
            <p><strong>错误信息:</strong> {error_message or "未知错误"}</p>
            <hr>
            <h4>可能的原因：</h4>
            <ul>
                <li>新闻ID不存在</li>
                <li>数据库连接问题</li>
                <li>数据结构不匹配</li>
                <li>字段名称映射错误</li>
            </ul>
            <h4>建议操作：</h4>
            <ul>
                <li>检查新闻ID是否正确</li>
                <li>刷新页面重试</li>
                <li>联系系统管理员</li>
            </ul>
        </div>
        ''',
        'summary': f'新闻ID {news_id} 的数据获取失败，请查看详细信息了解问题原因。',
        'source': '系统诊断',
        'category': '错误诊断',
        'url': '#',
        'keywords': ['诊断', '错误', '数据获取失败'],
        'images': [],
        'related_stocks': [],
        'publish_time': datetime.now().isoformat(),
        'crawl_time': datetime.now().isoformat(),
        'sentiment': 'neutral',
        'classification': 'diagnostic',
        'author': '系统'
    } 