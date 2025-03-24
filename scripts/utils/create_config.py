#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置文件生成工具

用法：
python scripts/create_config.py
"""

import os
import configparser

def create_config(config_path="config.ini"):
    """创建默认配置文件"""
    if os.path.exists(config_path):
        print(f"配置文件已存在: {config_path}")
        overwrite = input("是否覆盖? (y/n): ").lower() == 'y'
        if not overwrite:
            print("取消操作")
            return False
    
    config = configparser.ConfigParser()
    
    # 数据库配置
    config["Database"] = {
        "DB_DIR": "data/db",
        "BACKUP_DIR": "data/db/backup"
    }
    
    # 爬虫配置
    config["Crawler"] = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "REQUEST_TIMEOUT": "30",
        "MAX_RETRIES": "3",
        "DEFAULT_ENCODING": "utf-8"
    }
    
    # 爬虫来源配置
    config["Sources"] = {
        "ENABLED_SOURCES": "新浪财经,腾讯财经,东方财富,网易财经,凤凰财经",
        "DEFAULT_DAYS": "3"
    }
    
    # Web应用配置
    config["Web"] = {
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "DEBUG": "False",
        "SECRET_KEY": "newslook_secret_key_change_this_in_production",
        "ITEMS_PER_PAGE": "20"
    }
    
    # 日志配置
    config["Logging"] = {
        "LOG_LEVEL": "INFO",
        "LOG_FILE": "logs/newslook.log",
        "ROTATE_LOGS": "True",
        "MAX_LOG_SIZE": "10485760",  # 10MB
        "BACKUP_COUNT": "5"
    }
    
    # 调度器配置
    config["Scheduler"] = {
        "INTERVAL": "3600",
        "START_ON_BOOT": "True",
        "CRAWL_TIMES": "06:00,12:00,18:00,00:00"
    }
    
    # 创建目录（如果不存在）
    os.makedirs(os.path.dirname(os.path.abspath(config_path)) or ".", exist_ok=True)
    
    # 写入配置文件
    with open(config_path, 'w', encoding='utf-8') as f:
        config.write(f)
    
    print(f"配置文件已创建: {config_path}")
    return True

if __name__ == "__main__":
    create_config() 