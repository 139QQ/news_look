#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化配置中心
支持热重载、配置变更监听和SIGHUP信号处理
"""

import os
import signal
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable, Set
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import yaml

from .config_manager import ConfigManager, get_config_manager

logger = logging.getLogger(__name__)


class ConfigChangeHandler(FileSystemEventHandler):
    """配置文件变更监听器"""
    
    def __init__(self, config_center: 'ConfigCenter'):
        self.config_center = config_center
        self.last_modified = {}
        
    def on_modified(self, event):
        """文件修改事件处理"""
        if event.is_directory:
            return
            
        file_path = event.src_path
        
        # 只处理YAML配置文件
        if not file_path.endswith(('.yaml', '.yml')):
            return
            
        # 防止重复触发
        now = time.time()
        if file_path in self.last_modified:
            if now - self.last_modified[file_path] < 1.0:  # 1秒内重复修改忽略
                return
                
        self.last_modified[file_path] = now
        
        logger.info(f"配置文件变更: {file_path}")
        
        # 延迟处理，避免文件正在写入时读取
        threading.Timer(0.5, self.config_center.reload_config).start()


class ConfigCenter:
    """现代化配置中心"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_manager = get_config_manager()
        self.config_path = config_path or self.config_manager.config_path
        
        # 配置变更回调
        self.change_callbacks: Set[Callable] = set()
        
        # 文件监听器
        self.observer = None
        self.file_handler = None
        
        # 热重载状态
        self.hot_reload_enabled = False
        self.reload_lock = threading.Lock()
        
        # 配置版本管理
        self.config_version = 1
        self.config_history = []
        
        # 注册信号处理器
        self._setup_signal_handlers()
        
        # 启动监听
        self.start_monitoring()
        
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        try:
            # SIGHUP信号用于热重载
            signal.signal(signal.SIGHUP, self._handle_sighup)
            # SIGUSR1信号用于配置验证
            signal.signal(signal.SIGUSR1, self._handle_sigusr1)
            logger.info("信号处理器已设置 (SIGHUP: 热重载, SIGUSR1: 配置验证)")
        except (AttributeError, ValueError) as e:
            logger.warning(f"信号处理器设置失败: {e}")
            
    def _handle_sighup(self, signum, frame):
        """处理SIGHUP信号 - 热重载"""
        logger.info("收到SIGHUP信号，开始热重载配置")
        self.reload_config()
        
    def _handle_sigusr1(self, signum, frame):
        """处理SIGUSR1信号 - 配置验证"""
        logger.info("收到SIGUSR1信号，开始配置验证")
        self.validate_config()
        
    def start_monitoring(self):
        """启动配置文件监听"""
        try:
            if self.observer:
                self.stop_monitoring()
                
            self.observer = Observer()
            self.file_handler = ConfigChangeHandler(self)
            
            # 监听配置文件目录
            config_dir = Path(self.config_path).parent
            self.observer.schedule(self.file_handler, str(config_dir), recursive=True)
            
            self.observer.start()
            self.hot_reload_enabled = True
            
            logger.info(f"配置文件监听已启动: {config_dir}")
            
        except Exception as e:
            logger.error(f"配置文件监听启动失败: {e}")
            
    def stop_monitoring(self):
        """停止配置文件监听"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.hot_reload_enabled = False
            logger.info("配置文件监听已停止")
            
    def reload_config(self) -> bool:
        """重新加载配置"""
        with self.reload_lock:
            try:
                start_time = time.time()
                
                # 备份当前配置
                old_config = self.config_manager._config.copy()
                
                # 重新加载配置
                self.config_manager._config = self.config_manager._load_config()
                
                # 更新版本号
                self.config_version += 1
                
                # 记录配置历史
                self.config_history.append({
                    'version': self.config_version,
                    'timestamp': datetime.now().isoformat(),
                    'changes': self._detect_config_changes(old_config, self.config_manager._config)
                })
                
                # 限制历史记录数量
                if len(self.config_history) > 10:
                    self.config_history.pop(0)
                
                # 执行变更回调
                self._execute_change_callbacks()
                
                reload_time = (time.time() - start_time) * 1000
                logger.info(f"配置重载完成，版本: {self.config_version}, 耗时: {reload_time:.2f}ms")
                
                return True
                
            except Exception as e:
                logger.error(f"配置重载失败: {e}")
                return False
                
    def _detect_config_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> Dict[str, Any]:
        """检测配置变更"""
        changes = {
            'added': [],
            'removed': [],
            'modified': []
        }
        
        def _compare_dict(old_dict, new_dict, path=""):
            for key, value in new_dict.items():
                current_path = f"{path}.{key}" if path else key
                
                if key not in old_dict:
                    changes['added'].append(current_path)
                elif isinstance(value, dict) and isinstance(old_dict[key], dict):
                    _compare_dict(old_dict[key], value, current_path)
                elif old_dict[key] != value:
                    changes['modified'].append({
                        'path': current_path,
                        'old_value': old_dict[key],
                        'new_value': value
                    })
                    
            for key in old_dict:
                current_path = f"{path}.{key}" if path else key
                if key not in new_dict:
                    changes['removed'].append(current_path)
                    
        _compare_dict(old_config, new_config)
        return changes
        
    def _execute_change_callbacks(self):
        """执行配置变更回调"""
        for callback in self.change_callbacks:
            try:
                callback(self.config_manager._config)
            except Exception as e:
                logger.error(f"配置变更回调执行失败: {e}")
                
    def register_change_callback(self, callback: Callable):
        """注册配置变更回调"""
        self.change_callbacks.add(callback)
        logger.info(f"配置变更回调已注册: {callback.__name__}")
        
    def unregister_change_callback(self, callback: Callable):
        """取消配置变更回调"""
        self.change_callbacks.discard(callback)
        logger.info(f"配置变更回调已取消: {callback.__name__}")
        
    def validate_config(self) -> Dict[str, Any]:
        """验证配置"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            config = self.config_manager._config
            
            # 验证必需的配置项
            required_keys = ['app', 'database', 'web', 'logging']
            for key in required_keys:
                if key not in config:
                    validation_result['errors'].append(f"缺少必需的配置项: {key}")
                    validation_result['is_valid'] = False
                    
            # 验证数据库配置
            if 'database' in config:
                db_config = config['database']
                if 'db_dir' in db_config:
                    db_dir = Path(db_config['db_dir'])
                    if not db_dir.exists():
                        try:
                            db_dir.mkdir(parents=True, exist_ok=True)
                            validation_result['warnings'].append(f"数据库目录不存在，已创建: {db_dir}")
                        except Exception as e:
                            validation_result['errors'].append(f"无法创建数据库目录: {e}")
                            validation_result['is_valid'] = False
                            
            # 验证Web配置
            if 'web' in config:
                web_config = config['web']
                port = web_config.get('port', 5000)
                if not isinstance(port, int) or port < 1 or port > 65535:
                    validation_result['errors'].append(f"Web端口配置无效: {port}")
                    validation_result['is_valid'] = False
                    
            # 验证日志配置
            if 'logging' in config:
                log_config = config['logging']
                if 'handlers' in log_config and 'file' in log_config['handlers']:
                    file_config = log_config['handlers']['file']
                    if 'path' in file_config:
                        log_dir = Path(file_config['path'])
                        if not log_dir.exists():
                            try:
                                log_dir.mkdir(parents=True, exist_ok=True)
                                validation_result['warnings'].append(f"日志目录不存在，已创建: {log_dir}")
                            except Exception as e:
                                validation_result['errors'].append(f"无法创建日志目录: {e}")
                                validation_result['is_valid'] = False
                                
            logger.info(f"配置验证完成: {'通过' if validation_result['is_valid'] else '失败'}")
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"配置验证异常: {e}")
            logger.error(f"配置验证异常: {e}")
            
        return validation_result
        
    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            'config_path': str(self.config_path),
            'config_version': self.config_version,
            'hot_reload_enabled': self.hot_reload_enabled,
            'last_reload': self.config_history[-1]['timestamp'] if self.config_history else None,
            'change_callbacks_count': len(self.change_callbacks),
            'config_size': len(str(self.config_manager._config))
        }
        
    def get_config_history(self) -> list:
        """获取配置变更历史"""
        return self.config_history.copy()
        
    def export_config(self, file_path: str):
        """导出配置到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config_manager._config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"配置已导出到: {file_path}")
        except Exception as e:
            logger.error(f"配置导出失败: {e}")
            raise
            
    def import_config(self, file_path: str):
        """从文件导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                new_config = yaml.safe_load(f)
                
            # 验证新配置
            old_config = self.config_manager._config
            self.config_manager._config = new_config
            
            validation_result = self.validate_config()
            if not validation_result['is_valid']:
                # 回滚配置
                self.config_manager._config = old_config
                raise ValueError(f"配置验证失败: {validation_result['errors']}")
                
            # 更新版本号
            self.config_version += 1
            
            # 记录配置历史
            self.config_history.append({
                'version': self.config_version,
                'timestamp': datetime.now().isoformat(),
                'changes': self._detect_config_changes(old_config, new_config),
                'imported_from': file_path
            })
            
            # 执行变更回调
            self._execute_change_callbacks()
            
            logger.info(f"配置已从文件导入: {file_path}")
            
        except Exception as e:
            logger.error(f"配置导入失败: {e}")
            raise
            
    def reset_config(self):
        """重置配置为默认值"""
        try:
            old_config = self.config_manager._config.copy()
            self.config_manager._config = self.config_manager._get_default_config()
            
            # 更新版本号
            self.config_version += 1
            
            # 记录配置历史
            self.config_history.append({
                'version': self.config_version,
                'timestamp': datetime.now().isoformat(),
                'changes': self._detect_config_changes(old_config, self.config_manager._config),
                'action': 'reset_to_default'
            })
            
            # 执行变更回调
            self._execute_change_callbacks()
            
            logger.info("配置已重置为默认值")
            
        except Exception as e:
            logger.error(f"配置重置失败: {e}")
            raise
            
    def __del__(self):
        """析构函数"""
        self.stop_monitoring()


# 全局配置中心实例
_config_center: Optional[ConfigCenter] = None


def get_config_center() -> ConfigCenter:
    """获取配置中心实例"""
    global _config_center
    if _config_center is None:
        _config_center = ConfigCenter()
    return _config_center


def initialize_config_center(config_path: Optional[str] = None) -> ConfigCenter:
    """初始化配置中心"""
    global _config_center
    _config_center = ConfigCenter(config_path)
    return _config_center 