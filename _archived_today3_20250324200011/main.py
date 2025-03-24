import argparse
import os
import sys
import logging
from datetime import datetime
import pandas as pd
import json
import schedule
import time
import threading

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.logger import setup_logger, setup_daily_logger, log_exception, get_crawler_logger
from utils.database import NewsDatabase
from crawlers.sina_crawler import SinaCrawler
from crawlers.eastmoney_crawler import EastmoneyCrawler
from crawlers.tencent_crawler import TencentCrawler
from crawlers.netease_crawler import NeteaseCrawler
from crawlers.ifeng_crawler import IfengCrawler
# from api.rss_reader import get_rss_news
from api.news_api import get_api_news
from utils.crawler_manager import run_crawlers
from web.app import create_app

# 设置日志
logger = setup_daily_logger(name="main", module="main")

def get_crawler(source, db_path, use_proxy=False, use_selenium=False):
    """获取指定来源的爬虫实例"""
    crawlers = {
        'sina': SinaCrawler(db_path, use_proxy, use_selenium),
        'eastmoney': EastmoneyCrawler(db_path, use_proxy, use_selenium),
        'tencent': TencentCrawler(db_path, use_proxy, use_selenium),
        'netease': NeteaseCrawler(db_path, use_proxy, use_selenium),
        'ifeng': IfengCrawler(db_path, use_proxy, use_selenium)
    }
    return crawlers.get(source)

def export_to_excel(db_path, filename=None):
    """导出数据到Excel"""
    if not filename:
        filename = f"finance_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
    try:
        # 初始化数据库
        db = NewsDatabase(db_path)
        
        # 查询所有新闻
        news_data = db.query_news(limit=10000)
        if not news_data:
            logger.warning("没有新闻数据可导出")
            return False
            
        # 创建DataFrame
        df = pd.DataFrame(news_data)
        
        # 创建Excel写入器
        writer = pd.ExcelWriter(filename, engine='openpyxl')
        
        # 写入新闻数据
        df.to_excel(writer, sheet_name='新闻数据', index=False)
        
        # 保存Excel文件
        writer.close()
        
        logger.info(f"数据已导出到Excel文件: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"导出到Excel失败: {str(e)}")
        return False

def export_to_html(db_path, filename=None):
    """导出数据到HTML文件"""
    if not filename:
        filename = f"finance_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
    try:
        # 初始化数据库
        db = NewsDatabase(db_path)
        
        # 查询所有新闻
        news_data = db.query_news(limit=100)  # 限制导出数量
        if not news_data:
            logger.warning("没有新闻数据可导出")
            return False
            
        # 创建HTML内容
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>财经新闻</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .news-item { margin-bottom: 30px; border-bottom: 1px solid #eee; padding-bottom: 20px; }
                .news-title { font-size: 20px; font-weight: bold; color: #333; }
                .news-meta { font-size: 14px; color: #666; margin: 5px 0; }
                .news-content { font-size: 16px; line-height: 1.6; }
                img { max-width: 100%; height: auto; margin: 10px 0; }
                .sentiment-positive { color: green; }
                .sentiment-negative { color: red; }
                .sentiment-neutral { color: gray; }
            </style>
        </head>
        <body>
            <h1>财经新闻 - 导出时间: {}</h1>
        """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # 添加新闻内容
        for news in news_data:
            # 处理情感分析颜色
            sentiment_class = "sentiment-neutral"
            if news['sentiment'] > 0.2:
                sentiment_class = "sentiment-positive"
            elif news['sentiment'] < -0.2:
                sentiment_class = "sentiment-negative"
                
            # 处理内容中的图片链接
            content = news['content']
            if "图片链接:" in content:
                text_part, img_part = content.split("图片链接:", 1)
                img_links = img_part.strip().split("\n")
                img_html = ""
                for link in img_links:
                    if link.strip():
                        img_html += f'<img src="{link.strip()}" alt="新闻图片"><br>'
                content = text_part + img_html
            
            html_content += """
            <div class="news-item">
                <div class="news-title">{title}</div>
                <div class="news-meta">
                    来源: {source} | 作者: {author} | 发布时间: {pub_time} | 
                    <span class="{sentiment_class}">情感值: {sentiment:.2f}</span>
                </div>
                <div class="news-meta">关键词: {keywords}</div>
                <div class="news-content">{content}</div>
                <div class="news-meta">
                    <a href="{url}" target="_blank">原文链接</a>
                </div>
            </div>
            """.format(
                title=news['title'],
                source=news['source'],
                author=news['author'],
                pub_time=news['pub_time'],
                sentiment_class=sentiment_class,
                sentiment=news['sentiment'],
                keywords=news['keywords'],
                content=content.replace("\n", "<br>"),
                url=news['url']
            )
            
        html_content += """
        </body>
        </html>
        """
        
        # 写入HTML文件
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        logger.info(f"数据已导出到HTML文件: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"导出到HTML失败: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='财经新闻爬虫系统')
    parser.add_argument('--sources', type=str, help='新闻来源，用逗号分隔，如sina,eastmoney')
    parser.add_argument('--days', type=int, default=3, help='爬取最近几天的新闻，默认3天')
    parser.add_argument('--db', type=str, help='数据库文件路径')
    parser.add_argument('--export', action='store_true', help='是否导出数据到Excel')
    parser.add_argument('--query', type=str, help='查询关键词')
    parser.add_argument('--proxy', action='store_true', help='是否使用代理')
    parser.add_argument('--selenium', action='store_true', help='是否使用Selenium')
    parser.add_argument('--rss', action='store_true', help='是否使用RSS源')
    parser.add_argument('--api', action='store_true', help='是否使用新闻API')
    parser.add_argument('--html', action='store_true', help='导出为HTML格式')
    
    args = parser.parse_args()
    
    # 设置数据库路径
    if args.db:
        db_path = args.db
    else:
        # 使用绝对路径
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'finance_news.db'))
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 处理来源参数
    all_sources = ['eastmoney']  # 只使用东方财富
    sources = args.sources.split(',') if args.sources else all_sources
    
    # 增加爬取天数，获取更多历史内容
    if not args.days:
        args.days = 7  # 默认爬取7天的内容
    
    # 如果指定了查询参数，则执行查询
    if args.query:
        db = NewsDatabase(db_path)
        results = db.query_news(keyword=args.query, days=args.days)
        print(f"查询到 {len(results)} 条包含 '{args.query}' 的新闻:")
        for i, news in enumerate(results[:10], 1):
            print(f"{i}. {news['title']} ({news['source']} {news['pub_time']})")
        
        if args.export:
            if args.html:
                export_to_html(db_path)
            else:
                export_to_excel(db_path)
    else:
        # 执行爬虫
        all_news = []
        
        # 使用RSS源
        # if args.rss:
        #     rss_news = get_rss_news()
        #     db = NewsDatabase(db_path)
        #     for news in rss_news:
        #         db.save_news(news)
        #     all_news.extend(rss_news)
        #     logger.info(f"从RSS源获取了 {len(rss_news)} 条新闻")
            
        # 使用新闻API
        if args.api:
            api_news = get_api_news()
            db = NewsDatabase(db_path)
            for news in api_news:
                db.save_news(news)
            all_news.extend(api_news)
            logger.info(f"从API获取了 {len(api_news)} 条新闻")
            
        # 使用爬虫
        for source in sources:
            crawler = get_crawler(source, db_path, args.proxy, args.selenium)
            if crawler:
                news = crawler.run(args.days)
                all_news.extend(news)
                logger.info(f"{source} 爬取完成，获取 {len(news)} 条新闻")
            else:
                logger.warning(f"未找到 {source} 对应的爬虫")
                
        logger.info(f"所有爬虫运行完成，共获取 {len(all_news)} 条新闻")
        
        # 如果指定了导出参数，则导出到Excel
        if args.export:
            if args.html:
                export_to_html(db_path)
            else:
                export_to_excel(db_path)

def run_scheduled_crawlers():
    """运行定时爬虫任务"""
    logger.info("开始执行定时爬虫任务")
    run_crawlers(crawler_name='all', days=1)
    logger.info("定时爬虫任务执行完成")

def start_scheduler():
    """启动定时任务调度器"""
    # 每天凌晨2点运行爬虫
    schedule.every().day.at("02:00").do(run_scheduled_crawlers)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

if __name__ == "__main__":
    # 启动定时任务线程
    scheduler_thread = threading.Thread(target=start_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # 创建并启动Web服务器
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True) 