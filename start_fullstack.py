#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 全栈启动脚本
同时启动前端和后端服务器的便捷脚本
"""

import os
import sys
import subprocess
import time
import signal
import platform

def print_logo():
    """打印Logo"""
    logo = r"""
================================================================
    _   _                     _                 _    
   | \ | |                   | |               | |   
   |  \| | _____      _____  | |     ___   ___ | | __
   | . ` |/ _ \ \ /\ / / __| | |    / _ \ / _ \| |/ /
   | |\  |  __/\ V  V /\__ \ | |___| (_) | (_) |   < 
   |_| \_|\___| \_/\_/ |___/ |______\___/ \___/|_|\_\

              财经新闻爬虫系统 - 全栈开发环境
================================================================
    """
    print(logo)

def check_requirements():
    """检查系统要求"""
    print("🔍 检查系统要求...")
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version < (3, 8):
        print("❌ Python 版本过低！需要 Python 3.8 或更高版本")
        return False
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查Node.js
    try:
        # Windows系统需要shell=True
        shell_needed = platform.system() == 'Windows'
        result = subprocess.run(['node', '--version'], 
                              capture_output=True, text=True, shell=shell_needed)
        if result.returncode == 0:
            node_version = result.stdout.strip()
            print(f"✅ Node.js {node_version}")
        else:
            print("❌ Node.js 未安装或不在PATH中")
            print(f"   错误信息: {result.stderr.strip()}")
            return False
    except FileNotFoundError:
        print("❌ Node.js 未安装")
        return False
    except Exception as e:
        print(f"❌ 检查Node.js时出错: {e}")
        return False
    
    # 检查npm
    try:
        shell_needed = platform.system() == 'Windows'
        # Windows中可能需要使用npm.cmd
        npm_cmd = 'npm.cmd' if platform.system() == 'Windows' else 'npm'
        
        # 先尝试npm.cmd (Windows)
        try:
            result = subprocess.run([npm_cmd, '--version'], 
                                  capture_output=True, text=True, shell=shell_needed, timeout=10)
        except FileNotFoundError:
            # 如果npm.cmd不存在，尝试npm
            npm_cmd = 'npm'
            result = subprocess.run([npm_cmd, '--version'], 
                                  capture_output=True, text=True, shell=shell_needed, timeout=10)
        
        if result.returncode == 0:
            npm_version = result.stdout.strip()
            print(f"✅ npm {npm_version}")
        else:
            print("❌ npm 未安装或不在PATH中")
            print(f"   错误信息: {result.stderr.strip()}")
            print(f"   尝试的命令: {npm_cmd}")
            return False
    except FileNotFoundError:
        print("❌ npm 未安装")
        print("   请确保Node.js已正确安装并包含npm")
        return False
    except subprocess.TimeoutExpired:
        print("❌ npm 命令执行超时")
        return False
    except Exception as e:
        print(f"❌ 检查npm时出错: {e}")
        return False
    
    return True

def install_dependencies():
    """安装依赖"""
    print("\n📦 安装依赖...")
    
    # 安装Python依赖
    print("🐍 安装Python依赖...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        print("✅ Python依赖安装成功")
    except subprocess.CalledProcessError:
        print("❌ Python依赖安装失败")
        return False
    
    # 安装Node.js依赖
    frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend')
    if os.path.exists(frontend_path):
        print("📦 安装前端依赖...")
        try:
            # Windows兼容性处理
            shell_needed = platform.system() == 'Windows'
            npm_cmd = 'npm.cmd' if platform.system() == 'Windows' else 'npm'
            
            # 先尝试npm.cmd，如果失败再尝试npm
            try:
                subprocess.run([npm_cmd, 'install'], check=True, cwd=frontend_path, shell=shell_needed)
            except FileNotFoundError:
                npm_cmd = 'npm'
                subprocess.run([npm_cmd, 'install'], check=True, cwd=frontend_path, shell=shell_needed)
            
            print("✅ 前端依赖安装成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ 前端依赖安装失败: {e}")
            print(f"   使用的命令: {npm_cmd} install")
            print("   请尝试手动执行: cd frontend && npm install")
            return False
        except Exception as e:
            print(f"❌ 安装前端依赖时出错: {e}")
            return False
    else:
        print("⚠️  前端目录不存在")
        return False
    
    return True

def start_servers():
    """启动服务器"""
    print("\n🚀 启动服务器...")
    
    # 启动后端服务器
    print("🔧 启动后端服务器...")
    try:
        backend_process = subprocess.Popen(
            [sys.executable, 'app.py', '--with-frontend', '--debug', '--quiet'],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            shell=True if platform.system() == 'Windows' else False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # 等待一小段时间让后端启动
        time.sleep(3)
        
        # 检查进程是否还在运行
        if backend_process.poll() is None:
            print("✅ 服务器启动成功！")
            print("\n" + "="*60)
            print("🌐 访问地址:")
            print("   前端界面: http://localhost:3000")
            print("   后端API:  http://localhost:5000")
            print("   健康检查: http://localhost:5000/api/health")
            print("="*60)
            print("\n💡 提示:")
            print("   - 如果前端未自动启动，请手动运行: cd frontend && npm run dev")
            print("   - 按 Ctrl+C 停止服务器")
        else:
            print("❌ 后端启动失败")
            return False
        
        # 等待用户中断
        try:
            backend_process.wait()
        except KeyboardInterrupt:
            print("\n\n👋 正在停止服务器...")
            backend_process.terminate()
            
            # 等待进程结束
            try:
                backend_process.wait(timeout=10)
                print("✅ 服务器已停止")
            except subprocess.TimeoutExpired:
                print("⚠️  强制停止服务器...")
                backend_process.kill()
                print("✅ 服务器已强制停止")
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("\n💡 手动启动方法:")
        print("   后端: python app.py")
        print("   前端: cd frontend && npm run dev")
        return False
    
    return True

def main():
    """主函数"""
    try:
        print_logo()
        
        # 检查系统要求
        if not check_requirements():
            print("\n❌ 系统要求检查失败，请安装所需软件后重试")
            input("按回车键退出...")
            sys.exit(1)
        
        # 询问是否安装依赖
        print("\n" + "="*60)
        install_deps = input("是否需要安装/更新依赖？(y/N): ").lower().strip()
        
        if install_deps in ['y', 'yes', '是']:
            if not install_dependencies():
                print("\n❌ 依赖安装失败")
                input("按回车键退出...")
                sys.exit(1)
        
        # 启动服务器
        print("\n" + "="*60)
        start_servers()
        
    except KeyboardInterrupt:
        print("\n\n👋 用户取消操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        input("按回车键退出...")
        sys.exit(1)

if __name__ == '__main__':
    main()