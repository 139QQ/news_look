#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 配置组件
实现配置与代码分离
"""

import os
import yaml
import json
import logging
from typing import Dict, Any, Optional, List

from app.utils.logger import get_crawler_logger

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('config')

class ConfigLoader:
    """配置加载器，负责加载爬虫配置"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            config_dir: 配置文件目录
        """
        if config_dir:
            self.config_dir = config_dir
        else:
            # 默认配置目录
            self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config')
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 缓存配置
        self.config_cache = {}
        
        logger.info(f"配置加载器初始化成功: {self.config_dir}")
    
    def get_config(self, name: str, force_reload: bool = False) -> Dict[str, Any]:
        """
        获取指定名称的配置
        
        Args:
            name: 配置名称
            force_reload: 是否强制重新加载
            
        Returns:
            Dict: 配置字典
        """
        # 如果缓存中有且不需要强制重新加载，直接返回
        if name in self.config_cache and not force_reload:
            return self.config_cache[name]
        
        # 查找配置文件
        config_path = self._find_config_file(name)
        
        if not config_path:
            logger.warning(f"找不到配置文件: {name}")
            return {}
        
        # 加载配置
        config = self._load_config_file(config_path)
        
        # 缓存配置
        self.config_cache[name] = config
        
        return config
    
    def get_crawler_config(self, crawler_name: str) -> Dict[str, Any]:
        """
        获取爬虫配置，先查找专用配置，再查找通用配置
        
        Args:
            crawler_name: 爬虫名称
            
        Returns:
            Dict: 爬虫配置
        """
        # 加载通用配置
        common_config = self.get_config('common')
        
        # 加载专用配置
        crawler_config = self.get_config(crawler_name)
        
        # 合并配置
        merged_config = {}
        merged_config.update(common_config)
        merged_config.update(crawler_config)
        
        return merged_config
    
    def save_config(self, name: str, config: Dict[str, Any], format: str = 'yaml') -> bool:
        """
        保存配置
        
        Args:
            name: 配置名称
            config: 配置字典
            format: 配置文件格式，'yaml'或'json'
            
        Returns:
            bool: 保存是否成功
        """
        # 确定文件路径
        if format.lower() == 'json':
            file_path = os.path.join(self.config_dir, f"{name}.json")
        else:
            file_path = os.path.join(self.config_dir, f"{name}.yaml")
        
        try:
            # 保存配置
            if format.lower() == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # 更新缓存
            self.config_cache[name] = config
            
            logger.info(f"配置已保存: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            return False
    
    def _find_config_file(self, name: str) -> Optional[str]:
        """
        查找配置文件
        
        Args:
            name: 配置名称
            
        Returns:
            Optional[str]: 配置文件路径或None
        """
        # 优先查找YAML文件
        yaml_path = os.path.join(self.config_dir, f"{name}.yaml")
        if os.path.exists(yaml_path):
            return yaml_path
        
        # 查找YML文件
        yml_path = os.path.join(self.config_dir, f"{name}.yml")
        if os.path.exists(yml_path):
            return yml_path
        
        # 查找JSON文件
        json_path = os.path.join(self.config_dir, f"{name}.json")
        if os.path.exists(json_path):
            return json_path
        
        return None
    
    def _load_config_file(self, file_path: str) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            Dict: 配置字典
        """
        try:
            # 根据文件扩展名选择加载方式
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in ['.yaml', '.yml']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            elif ext == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                logger.error(f"不支持的配置文件格式: {ext}")
                return {}
            
            # 如果配置是None，返回空字典
            if config is None:
                return {}
                
            logger.info(f"配置已加载: {file_path}")
            return config
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            return {}
    
    def list_available_configs(self) -> List[str]:
        """
        列出所有可用的配置
        
        Returns:
            List[str]: 配置名称列表
        """
        configs = []
        
        # 遍历配置目录中的文件
        for file_name in os.listdir(self.config_dir):
            if file_name.endswith(('.yaml', '.yml', '.json')):
                # 去除扩展名
                config_name = os.path.splitext(file_name)[0]
                configs.append(config_name)
        
        return configs
    
    def create_crawler_config_template(self, crawler_name: str) -> bool:
        """
        创建爬虫配置模板
        
        Args:
            crawler_name: 爬虫名称
            
        Returns:
            bool: 创建是否成功
        """
        # 如果配置已存在，不覆盖
        if self._find_config_file(crawler_name):
            logger.warning(f"配置已存在: {crawler_name}")
            return False
        
        # 创建配置模板
        template = {
            "crawler": {
                "name": crawler_name,
                "description": f"{crawler_name}爬虫配置",
                "version": "1.0.0",
                "enabled": True
            },
            "request": {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 2,
                "use_proxy": False,
                "proxy": "",
                "rate_limit": 1.0,  # 每秒请求数
            },
            "parser": {
                "selectors": {
                    "list": {
                        "container": "div.news-list, ul.news-list",
                        "item": "div.news-item, li.news-item",
                        "title": "h2, h3, a.title",
                        "link": "a",
                        "date": "span.date, time.date",
                        "summary": "div.summary, p.summary"
                    },
                    "detail": {
                        "title": "h1.title, h1.article-title",
                        "content": "div.article-content, div.content",
                        "date": "span.date, time.date",
                        "author": "span.author, div.author",
                        "source": "span.source, div.source",
                        "category": "span.category, div.category"
                    }
                },
                "date_format": "%Y-%m-%d %H:%M:%S"
            },
            "storage": {
                "type": "sqlite",
                "db_path": f"data/db/{crawler_name}.db",
                "table_name": "news"
            },
            "urls": {
                "entry": f"https://example.com/{crawler_name}",
                "category": {
                    "财经": "https://example.com/finance",
                    "股票": "https://example.com/stock",
                    "基金": "https://example.com/fund"
                },
                "api": {
                    "list": "https://example.com/api/list",
                    "detail": "https://example.com/api/detail"
                }
            },
            "middlewares": {
                "request": ["ua_rotation", "referer", "rate_limiting", "request_logging"],
                "response": ["response_logging", "error_retry", "content_type"],
                "item": ["ads_filter", "duplicate_filter", "sentiment_analysis", "keyword_extraction", "summary"]
            },
            "monitor": {
                "enabled": True,
                "performance": {
                    "enabled": True,
                    "interval": 60
                },
                "status": {
                    "enabled": True
                },
                "resource": {
                    "enabled": True,
                    "interval": 60,
                    "alert_threshold": {
                        "cpu": 90,
                        "memory": 85,
                        "disk": 90
                    }
                }
            }
        }
        
        # 保存配置
        return self.save_config(crawler_name, template)


# 创建通用配置模板
def create_common_config(config_dir: Optional[str] = None) -> bool:
    """
    创建通用配置模板
    
    Args:
        config_dir: 配置目录
        
    Returns:
        bool: 创建是否成功
    """
    loader = ConfigLoader(config_dir)
    
    # 创建通用配置
    common_config = {
        "common": {
            "timeout": 30,
            "max_retries": 3,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            },
            "date_format": "%Y-%m-%d %H:%M:%S",
            "storage": {
                "type": "sqlite",
                "db_dir": "data/db",
                "table_name": "news"
            },
            "middlewares": {
                "enabled": True,
                "default_request_middlewares": ["ua_rotation", "referer", "rate_limiting", "request_logging"],
                "default_response_middlewares": ["response_logging", "error_retry", "content_type"],
                "default_item_middlewares": ["ads_filter", "duplicate_filter", "sentiment_analysis", "keyword_extraction", "summary"]
            },
            "monitor": {
                "enabled": True,
                "log_dir": "logs/performance",
                "performance_interval": 60,
                "resource_interval": 60
            }
        }
    }
    
    # 保存通用配置
    return loader.save_config("common", common_config)


# 创建网易财经配置示例
def create_netease_config(config_dir: Optional[str] = None) -> bool:
    """
    创建网易财经配置示例
    
    Args:
        config_dir: 配置目录
        
    Returns:
        bool: 创建是否成功
    """
    loader = ConfigLoader(config_dir)
    
    # 创建网易财经配置
    netease_config = {
        "crawler": {
            "name": "网易财经",
            "description": "网易财经爬虫配置",
            "version": "1.0.0",
            "enabled": True
        },
        "request": {
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 2,
            "use_proxy": False,
            "rate_limit": 1.0  # 每秒请求数
        },
        "parser": {
            "selectors": {
                "list": {
                    "container": "div.news-list, ul.news-list",
                    "item": "div.news-item, li.news-item, div.data-item",
                    "title": "h2, h3, a.title, div.news_title",
                    "link": "a",
                    "date": "span.date, time.date, span.time",
                    "summary": "div.summary, p.summary, div.news_short"
                },
                "detail": {
                    "title": "h1.title, h1.post_title, div.post_content h1",
                    "content": "div.post_body, div#endText, div.post_text, div.article-content",
                    "date": "div.post_time_source, div.post_info, span.time",
                    "author": "span.author, span.ep-editor, span.ep-source",
                    "source": "div.post_time_source, a.source",
                    "category": "div.post_crumb, div.breadcrumb"
                }
            },
            "date_format": "%Y-%m-%d %H:%M:%S"
        },
        "storage": {
            "type": "sqlite",
            "db_path": "data/db/网易财经.db",
            "table_name": "news"
        },
        "urls": {
            "entry": "https://money.163.com/",
            "category": {
                "财经": "https://money.163.com/",
                "股票": "https://money.163.com/stock/",
                "理财": "https://money.163.com/licai/",
                "基金": "https://money.163.com/fund/",
                "热点": "https://money.163.com/special/00252G50/macro.html",
                "商业": "https://biz.163.com/"
            },
            "api": {
                "股票": "https://money.163.com/special/00259BVP/news_json.js",
                "理财": "https://money.163.com/special/00259BVP/licai_json.js",
                "基金": "https://money.163.com/special/00259BVP/fund_json.js"
            }
        },
        "middlewares": {
            "request": ["ua_rotation", "referer", "rate_limiting", "request_logging"],
            "response": ["response_logging", "error_retry", "content_type"],
            "item": ["ads_filter", "duplicate_filter", "sentiment_analysis", "keyword_extraction", "summary"]
        },
        "monitor": {
            "enabled": True,
            "performance": {
                "enabled": True,
                "interval": 60
            },
            "status": {
                "enabled": True
            },
            "resource": {
                "enabled": True,
                "interval": 60
            }
        }
    }
    
    # 保存网易财经配置
    return loader.save_config("网易财经", netease_config)


# 创建配置单例
_config_loader = None

def get_config_loader(config_dir: Optional[str] = None) -> ConfigLoader:
    """
    获取配置加载器单例
    
    Args:
        config_dir: 配置目录
        
    Returns:
        ConfigLoader: 配置加载器实例
    """
    global _config_loader
    
    if _config_loader is None:
        _config_loader = ConfigLoader(config_dir)
    
    return _config_loader


def init_default_configs(config_dir: Optional[str] = None) -> None:
    """
    初始化默认配置
    
    Args:
        config_dir: 配置目录
    """
    loader = get_config_loader(config_dir)
    
    # 如果没有通用配置，创建
    if not loader._find_config_file("common"):
        create_common_config(config_dir)
        logger.info("已创建通用配置")
    
    # 如果没有网易财经配置，创建
    if not loader._find_config_file("网易财经"):
        create_netease_config(config_dir)
        logger.info("已创建网易财经配置示例")
    
    logger.info("默认配置初始化完成") 