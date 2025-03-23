#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 配置文件
"""

import os
import json
from datetime import datetime

# 获取项目根目录的绝对路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 统一使用绝对路径的data/db目录作为默认数据库目录
DEFAULT_DB_DIR = os.path.join(ROOT_DIR, 'data', 'db')

class Settings:
    """配置类"""
    
    def __init__(self):
        """初始化配置"""
        # 基础目录
        self.BASE_DIR = ROOT_DIR
        self.DATA_DIR = os.path.join(self.BASE_DIR, 'data')
        self.LOG_DIR = os.path.join(self.BASE_DIR, 'logs')
        self.DB_DIR = DEFAULT_DB_DIR
        
        # 创建必要的目录
        for directory in [self.DATA_DIR, self.LOG_DIR, self.DB_DIR]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"创建目录: {directory}")
        
        # 配置文件路径
        self.CONFIG_FILE = os.path.join(self.DATA_DIR, 'config.json')
        
        # 默认配置
        self.default_settings = {
            # 目录配置
            'BASE_DIR': self.BASE_DIR,
            'DATA_DIR': self.DATA_DIR,
            'LOG_DIR': self.LOG_DIR,
            'DB_DIR': self.DB_DIR,
            
            # 爬虫设置
            'crawler_interval': 30,  # 爬虫间隔（分钟）
            'max_crawlers': 3,  # 最大并发爬虫数
            'request_timeout': 30,  # 请求超时时间（秒）
            'max_retries': 3,  # 最大重试次数
            'proxy_mode': 'none',  # 代理模式：none/http/socks5
            'proxy_url': '',  # 代理地址
            
            # 数据库设置
            'db_type': 'sqlite',  # 数据库类型：sqlite/mysql/postgresql
            'db_host': 'localhost',  # 数据库主机
            'db_port': 3306,  # 数据库端口
            'db_name': 'news',  # 数据库名称
            'db_user': 'root',  # 数据库用户名
            'db_password': '',  # 数据库密码
            
            # 日志设置
            'log_level': 'INFO',  # 日志级别：DEBUG/INFO/WARNING/ERROR/CRITICAL
            'log_max_size': 10,  # 日志文件大小限制（MB）
            'log_backup_count': 5,  # 日志文件备份数
            
            # 系统设置
            'debug': False,  # 调试模式
            'secret_key': os.urandom(24).hex(),  # 密钥
            'timezone': 'Asia/Shanghai',  # 时区
            'language': 'zh-CN',  # 语言
            'theme': 'light',  # 主题：light/dark
        }
        
        # 从环境变量更新配置
        self.update_from_env()
        
        # 加载配置
        self.settings = self.load_settings()
    
    def update_from_env(self):
        """从环境变量更新配置"""
        if 'DB_DIR' in os.environ:
            # 确保DB_DIR是绝对路径
            db_dir = os.environ['DB_DIR']
            if not os.path.isabs(db_dir):
                db_dir = os.path.join(ROOT_DIR, db_dir)
            self.DB_DIR = db_dir
            self.default_settings['DB_DIR'] = self.DB_DIR
            print(f"设置环境变量DB_DIR: {self.DB_DIR}")
            
        if 'LOG_DIR' in os.environ:
            self.LOG_DIR = os.environ['LOG_DIR']
            self.default_settings['LOG_DIR'] = self.LOG_DIR
            
        if 'LOG_LEVEL' in os.environ:
            self.default_settings['log_level'] = os.environ['LOG_LEVEL']
    
    def load_settings(self):
        """加载配置"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            except:
                settings = {}
        else:
            settings = {}
        
        # 合并默认配置
        merged_settings = self.default_settings.copy()
        merged_settings.update(settings)
        return merged_settings
    
    def save_settings(self):
        """保存配置"""
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self.settings[key] = value
        self.save_settings()
    
    def update(self, settings_dict):
        """更新多个配置项"""
        self.settings.update(settings_dict)
        self.save_settings()
    
    def __getitem__(self, key):
        """获取配置项（字典方式）"""
        return self.settings[key]
    
    def __setitem__(self, key, value):
        """设置配置项（字典方式）"""
        self.settings[key] = value
        self.save_settings()

# 创建全局配置对象
_settings = None

def get_settings():
    """获取配置对象"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

# 获取项目根目录
BASE_DIR = get_settings().BASE_DIR

# 数据库配置
DB_CONFIG = {
    'main_db': os.path.join(BASE_DIR, 'db', 'finance_news.db'),
    'source_db_dir': os.path.join(BASE_DIR, 'db')
}

# 日志配置
LOG_CONFIG = {
    'level': get_settings().get('log_level'),
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'file': os.path.join(BASE_DIR, 'logs', 'finance_news_crawler.log'),
    'max_size': get_settings().get('log_max_size') * 1024 * 1024,  # MB to bytes
    'backup_count': get_settings().get('log_backup_count')
}

# 爬虫配置
CRAWLER_CONFIG = {
    'user_agents': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
    ],
    'timeout': get_settings().get('request_timeout'),
    'retry': get_settings().get('max_retries'),
    'sleep_min': 1,
    'sleep_max': 3,
    'use_source_db': True
}

# 代理配置
PROXY_CONFIG = {
    'enabled': get_settings().get('proxy_mode') != 'none',
    'api': get_settings().get('proxy_url'),
    'username': '',
    'password': '',
    'proxy': {
        'http': get_settings().get('proxy_mode') == 'http' and get_settings().get('proxy_url') or None,
        'https': get_settings().get('proxy_mode') == 'http' and get_settings().get('proxy_url') or None
    }
}

# 新闻源配置
NEWS_SOURCES = {
    'eastmoney': {
        'enabled': True,
        'url': 'https://finance.eastmoney.com/',
        'categories': ['财经', '股票', '基金', '科技', '消费', '房产', '汽车', '公司', '期货', '外汇', '黄金']
    },
    'sina': {
        'enabled': True,
        'url': 'https://finance.sina.com.cn/',
        'categories': ['财经', '股票', '基金', '科技', '消费'],
        'rss': 'https://rss.sina.com.cn/finance/stock/cjdt.xml'
    },
    'tencent': {
        'enabled': True,
        'url': 'https://finance.qq.com/',
        'categories': ['财经', '股票', '基金', '科技', '消费']
    },
    'netease': {
        'enabled': True,
        'url': 'https://money.163.com/',
        'categories': ['财经', '股票', '基金', '科技', '消费']
    },
    'ifeng': {
        'enabled': True,
        'url': 'https://finance.ifeng.com/',
        'categories': ['财经', '股票', '基金', '科技', '消费']
    }
}

# API配置
API_CONFIG = {
    'sentiment': {
        'enabled': True,
        'api_key': '',
        'api_secret': ''
    },
    'newsapi': {
        'enabled': False,
        'key': '',
        'url': 'https://newsapi.org/v2/top-headlines',
        'params': {
            'country': 'cn',
            'category': 'business'
        }
    }
}

# Selenium配置
SELENIUM_CONFIG = {
    'enabled': False,
    'headless': True,
    'driver_path': '',
    'page_load_timeout': 30,
    'wait_timeout': 10
}

# Web应用配置
WEB_CONFIG = {
    'host': '0.0.0.0',
    'port': 5000,
    'debug': get_settings().get('debug'),
    'secret_key': get_settings().get('secret_key'),
    'per_page': 10
}

# 报告配置
REPORT_CONFIG = {
    'enabled': True,
    'template': os.path.join(BASE_DIR, 'app', 'utils', 'templates', 'report_template.html'),
    'output_dir': os.path.join(BASE_DIR, 'data', 'reports')
}

# 任务调度配置
SCHEDULE_CONFIG = {
    'enabled': True,
    'tasks': [
        {
            'type': 'daily',
            'time': '08:00'
        },
        {
            'type': 'daily',
            'time': '18:00'
        }
    ]
} 