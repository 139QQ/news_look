import schedule
import time
import subprocess
import os
from datetime import datetime
import sys

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.utils.logger import setup_daily_logger, log_exception

# 设置日志
logger = setup_daily_logger(name="scheduler", module="scheduler")

def run_crawler():
    """运行爬虫任务"""
    try:
        logger.info("开始执行定时爬虫任务")
        
        # 运行爬虫
        result = subprocess.run(
            ["python", "main.py", "--sources", "eastmoney", "--days", "1", "--html"],
            capture_output=True,
            text=True
        )
        
        # 记录输出
        logger.info(f"爬虫执行完成，退出码: {result.returncode}")
        if result.stdout:
            logger.info(f"标准输出: {result.stdout}")
        if result.stderr:
            logger.error(f"错误输出: {result.stderr}")
            
        # 如果成功，移动HTML文件到指定目录
        if result.returncode == 0:
            html_files = [f for f in os.listdir('.') if f.startswith('finance_news_') and f.endswith('.html')]
            if html_files:
                latest_html = max(html_files, key=os.path.getctime)
                # 确保目录存在
                os.makedirs('reports', exist_ok=True)
                # 移动文件
                new_path = os.path.join('reports', f"daily_report_{datetime.now().strftime('%Y%m%d')}.html")
                os.rename(latest_html, new_path)
                logger.info(f"报告已保存到: {new_path}")
                
    except Exception as e:
        log_exception(logger, e, "执行爬虫任务失败")

# 设置定时任务
schedule.every().day.at("08:00").do(run_crawler)  # 每天早上8点运行
schedule.every().day.at("18:00").do(run_crawler)  # 每天晚上6点运行

# 运行调度器
logger.info("定时任务调度器已启动")
logger.info(f"已设置定时任务: 每天 08:00 和 18:00 运行爬虫")

if __name__ == "__main__":
    # 启动时先运行一次爬虫
    logger.info("启动时执行一次爬虫任务")
    run_crawler()
    
    # 进入定时任务循环
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
        except Exception as e:
            log_exception(logger, e, "定时任务执行失败")
            time.sleep(300)  # 出错后等待5分钟再继续 