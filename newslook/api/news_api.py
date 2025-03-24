import requests
import hashlib
from datetime import datetime
import logging
import os
import sys

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger
from utils.sentiment import SentimentAnalyzer
from config import API

logger = setup_logger()
sentiment_analyzer = SentimentAnalyzer()

def get_api_news():
    """使用第三方API获取新闻"""
    all_news = []
    
    # 检查NewsAPI是否启用
    if not API['newsapi']['enabled']:
        logger.info("NewsAPI未启用，跳过")
        return all_news
        
    try:
        logger.info(f"正在从NewsAPI获取新闻: {API['newsapi']['url']}")
        
        # 构建请求参数
        params = API['newsapi']['params'].copy()
        params['apiKey'] = API['newsapi']['key']
        
        # 发送请求
        response = requests.get(API['newsapi']['url'], params=params)
        response.raise_for_status()
        data = response.json()
        
        # 处理响应
        if data.get('status') != 'ok':
            logger.error(f"NewsAPI返回错误: {data.get('message', '未知错误')}")
            return all_news
            
        # 处理文章
        for article in data.get('articles', []):
            try:
                # 生成唯一ID
                news_id = hashlib.md5(f"{article.get('title')}_{article.get('url')}".encode('utf-8')).hexdigest()
                
                # 提取内容
                title = article.get('title', '')
                content = article.get('description', '')
                
                # 提取关键词和情感分析
                keywords = sentiment_analyzer.extract_keywords(title + " " + content)
                sentiment = sentiment_analyzer.analyze(title + " " + content)
                
                # 构建新闻数据
                news_item = {
                    'id': news_id,
                    'title': title,
                    'content': content,
                    'pub_time': article.get('publishedAt', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                    'author': article.get('author', '未知作者'),
                    'source': article.get('source', {}).get('name', 'NewsAPI'),
                    'url': article.get('url', ''),
                    'keywords': keywords,
                    'sentiment': sentiment,
                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                all_news.append(news_item)
                logger.info(f"成功获取API新闻: {title}")
                
            except Exception as e:
                logger.error(f"处理API文章失败: {str(e)}")
                
        logger.info(f"NewsAPI获取完成，共获取 {len(all_news)} 条新闻")
        return all_news
        
    except Exception as e:
        logger.error(f"从NewsAPI获取新闻失败: {str(e)}")
        return all_news 