import feedparser
import hashlib
from datetime import datetime
import logging
import os
import sys

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.logger import setup_logger
from backend.utils.sentiment import SentimentAnalyzer

logger = setup_logger()
sentiment_analyzer = SentimentAnalyzer()

def get_rss_news():
    """获取RSS新闻源的新闻"""
    rss_sources = {
        '新浪财经': 'https://rss.sina.com.cn/finance/stock/cjdt.xml',
        '东方财富': 'https://feed43.com/eastmoney.xml',  # 这是一个示例，可能需要替换为实际的RSS地址
    }
    
    all_news = []
    
    for source_name, rss_url in rss_sources.items():
        try:
            logger.info(f"正在获取 {source_name} RSS源: {rss_url}")
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries:
                try:
                    # 生成唯一ID
                    news_id = hashlib.md5(f"{entry.title}_{entry.link}".encode('utf-8')).hexdigest()
                    
                    # 提取内容
                    content = entry.summary if hasattr(entry, 'summary') else ""
                    
                    # 提取发布时间
                    if hasattr(entry, 'published'):
                        pub_time = entry.published
                    elif hasattr(entry, 'pubDate'):
                        pub_time = entry.pubDate
                    else:
                        pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                    # 提取作者
                    author = entry.author if hasattr(entry, 'author') else "未知作者"
                    
                    # 提取关键词和情感分析
                    keywords = sentiment_analyzer.extract_keywords(entry.title + " " + content)
                    sentiment = sentiment_analyzer.analyze(entry.title + " " + content)
                    
                    # 构建新闻数据
                    news_item = {
                        'id': news_id,
                        'title': entry.title,
                        'content': content,
                        'pub_time': pub_time,
                        'author': author,
                        'source': f"{source_name}RSS",
                        'url': entry.link,
                        'keywords': keywords,
                        'sentiment': sentiment,
                        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    all_news.append(news_item)
                    logger.info(f"成功获取RSS新闻: {entry.title}")
                    
                except Exception as e:
                    logger.error(f"处理RSS条目失败: {str(e)}")
                    
        except Exception as e:
            logger.error(f"获取 {source_name} RSS源失败: {str(e)}")
            
    logger.info(f"RSS源获取完成，共获取 {len(all_news)} 条新闻")
    return all_news 