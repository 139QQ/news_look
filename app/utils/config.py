#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置管理模块
"""

import os
import configparser
import logging

logger = logging.getLogger(__name__)

class Config:
    """配置类，用于读取和管理配置"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.config_file = './config.ini'
        self.config = configparser.ConfigParser()
        self.settings = {}
        
        # 默认配置
        self.default_settings = {
            'general': {
                'db_dir': './data/db',
                'log_dir': './logs',
                'log_level': 'INFO',
            },
            'crawler': {
                'interval': '3600',
                'max_pages': '10',
                'timeout': '30',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            },
            'web': {
                'host': '0.0.0.0',
                'port': '8000',
                'debug': 'False',
            }
        }
        
        # 尝试加载配置文件
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                logger.info("找到配置文件: %s", self.config_file)
                self.config.read(self.config_file, encoding='utf-8')
                logger.info("成功加载配置文件: %s", self.config_file)
                
                # 将配置转换为字典
                for section in self.config.sections():
                    if section not in self.settings:
                        self.settings[section] = {}
                    for key, value in self.config[section].items():
                        self.settings[section][key] = value
            else:
                logger.warning("配置文件不存在: %s", self.config_file)
                self.create_default_config()
        except Exception as e:
            logger.error("加载配置文件出错: %s", str(e))
            logger.info("未找到配置文件，使用默认配置")
            self.settings = self.default_settings
    
    def create_default_config(self):
        """创建默认配置文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(self.config_file)), exist_ok=True)
            
            # 创建配置对象
            config = configparser.ConfigParser()
            
            # 添加默认配置
            for section, options in self.default_settings.items():
                config[section] = options
            
            # 写入配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            
            logger.info("已创建默认配置文件: %s", self.config_file)
            self.settings = self.default_settings
        except Exception as e:
            logger.error("创建默认配置文件失败: %s", str(e))
            self.settings = self.default_settings
    
    def get(self, section, key, default=None):
        """获取配置项"""
        try:
            return self.settings.get(section, {}).get(key, default)
        except KeyError:
            logger.error("获取配置项出错: 找不到键 %s 在 %s 中", key, section)
            return default
    
    def set(self, section, key, value):
        """设置配置项"""
        try:
            if section not in self.settings:
                self.settings[section] = {}
            self.settings[section][key] = value
            
            # 更新配置对象
            if section not in self.config:
                self.config[section] = {}
            self.config[section][key] = str(value)
            
            # 写入配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            
            return True
        except Exception as e:
            logger.error("设置配置项出错: %s", str(e))
            return False
    
    def get_all(self):
        """获取所有配置"""
        return self.settings
