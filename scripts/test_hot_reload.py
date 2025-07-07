#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置热重载测试脚本
用于测试配置中心的热重载功能
"""

import sys
import os
import time
import requests
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.newslook.core.config_center import get_config_center
from backend.newslook.core.config_manager import get_config


def test_hot_reload():
    """测试热重载功能"""
    print("=" * 60)
    print("配置热重载测试")
    print("=" * 60)
    
    # 获取配置中心
    config_center = get_config_center()
    config_manager = get_config()
    
    print(f"配置文件路径: {config_center.config_path}")
    print(f"当前配置版本: {config_center.config_version}")
    print(f"热重载状态: {'启用' if config_center.hot_reload_enabled else '禁用'}")
    
    # 获取初始配置
    initial_version = config_center.config_version
    initial_app_name = config_manager.get('app', {}).get('name', 'Unknown')
    
    print(f"初始应用名称: {initial_app_name}")
    print(f"初始版本: {initial_version}")
    
    # 提示用户修改配置
    print("\n" + "=" * 60)
    print("请修改配置文件 configs/app.yaml 中的应用名称")
    print("例如：将 app.name 改为 'NewsLook-HotReload-Test'")
    print("保存后观察热重载效果...")
    print("按 Ctrl+C 退出测试")
    print("=" * 60)
    
    try:
        while True:
            time.sleep(2)
            
            # 检查配置是否发生变化
            current_version = config_center.config_version
            current_app_name = config_manager.get('app', {}).get('name', 'Unknown')
            
            if current_version != initial_version:
                print(f"\n🔄 配置已重载!")
                print(f"版本: {initial_version} -> {current_version}")
                print(f"应用名称: {initial_app_name} -> {current_app_name}")
                
                # 显示配置变更详情
                history = config_center.get_config_history()
                if history:
                    latest_change = history[-1]
                    print(f"变更时间: {latest_change['timestamp']}")
                    print(f"变更详情: {latest_change['changes']}")
                
                # 更新初始值
                initial_version = current_version
                initial_app_name = current_app_name
                
                print("继续监听配置变更...")
            else:
                print(".", end="", flush=True)
                
    except KeyboardInterrupt:
        print("\n\n测试结束")
        print("热重载测试完成")


def test_sighup_reload():
    """测试SIGHUP信号重载"""
    print("=" * 60)
    print("SIGHUP信号重载测试")
    print("=" * 60)
    
    config_center = get_config_center()
    
    print(f"当前进程ID: {os.getpid()}")
    print(f"配置版本: {config_center.config_version}")
    print("\n使用以下命令发送SIGHUP信号进行热重载:")
    print(f"kill -HUP {os.getpid()}")
    print("\n按 Ctrl+C 退出测试")
    
    initial_version = config_center.config_version
    
    try:
        while True:
            time.sleep(1)
            
            current_version = config_center.config_version
            if current_version != initial_version:
                print(f"\n🔄 收到SIGHUP信号，配置已重载!")
                print(f"版本: {initial_version} -> {current_version}")
                initial_version = current_version
            else:
                print(".", end="", flush=True)
                
    except KeyboardInterrupt:
        print("\n\nSIGHUP测试结束")


def test_config_api():
    """测试配置API"""
    print("=" * 60)
    print("配置API测试")
    print("=" * 60)
    
    base_url = "http://localhost:8080"
    
    # 测试配置重载API
    try:
        print("测试配置重载API...")
        response = requests.post(f"{base_url}/config/reload", timeout=5)
        print(f"重载API响应: {response.status_code}")
        if response.status_code == 200:
            print(f"响应内容: {response.json()}")
        else:
            print(f"错误: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"API测试失败: {e}")
        print("请确保服务器正在运行")


def test_config_validation():
    """测试配置验证"""
    print("=" * 60)
    print("配置验证测试")
    print("=" * 60)
    
    config_center = get_config_center()
    
    print("执行配置验证...")
    validation_result = config_center.validate_config()
    
    print(f"验证结果: {'✅ 通过' if validation_result['is_valid'] else '❌ 失败'}")
    
    if validation_result['errors']:
        print("\n错误:")
        for error in validation_result['errors']:
            print(f"  ❌ {error}")
            
    if validation_result['warnings']:
        print("\n警告:")
        for warning in validation_result['warnings']:
            print(f"  ⚠️  {warning}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python test_hot_reload.py hot_reload    # 测试文件监听热重载")
        print("  python test_hot_reload.py sighup        # 测试SIGHUP信号重载")
        print("  python test_hot_reload.py api           # 测试配置API")
        print("  python test_hot_reload.py validation    # 测试配置验证")
        return
        
    test_type = sys.argv[1]
    
    if test_type == "hot_reload":
        test_hot_reload()
    elif test_type == "sighup":
        test_sighup_reload()
    elif test_type == "api":
        test_config_api()
    elif test_type == "validation":
        test_config_validation()
    else:
        print(f"未知的测试类型: {test_type}")


if __name__ == '__main__':
    main() 