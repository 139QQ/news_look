from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
import os
import sys

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.logger import setup_logger
from config import SELENIUM

logger = setup_logger()

def fetch_with_selenium(url, wait_time=None):
    """使用Selenium获取动态加载的页面内容"""
    if not SELENIUM['enabled']:
        logger.warning("Selenium未启用，无法获取动态内容")
        return None
        
    wait_time = wait_time or SELENIUM['wait_time']
    
    options = Options()
    if SELENIUM['headless']:
        options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    try:
        logger.info(f"使用Selenium获取页面: {url}")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        
        # 等待页面加载
        logger.info(f"等待页面加载 {wait_time} 秒")
        time.sleep(wait_time)
        
        # 获取页面源码
        html = driver.page_source
        
        # 关闭浏览器
        driver.quit()
        
        return html
    except Exception as e:
        logger.error(f"Selenium获取页面失败: {str(e)}")
        return None 