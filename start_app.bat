@echo off
echo ====================================
echo     NewsLook 财经新闻爬虫系统
echo ====================================
echo.

REM 检查虚拟环境是否存在
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ 虚拟环境不存在，正在创建...
    D:\python\python.exe -m venv .venv
    if errorlevel 1 (
        echo ❌ 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo ✅ 虚拟环境创建成功
    echo.
)

REM 激活虚拟环境
echo 🔧 激活虚拟环境...
call .venv\Scripts\activate.bat

REM 检查是否需要安装依赖
if not exist ".venv\Lib\site-packages\flask" (
    echo 📦 检测到缺少依赖，正在安装...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ 安装依赖失败
        pause
        exit /b 1
    )
    echo ✅ 依赖安装成功
    echo.
)

REM 启动应用
echo 🚀 启动应用...
echo.
echo 📍 后端地址: http://127.0.0.1:5000
echo 🎨 前端地址: http://localhost:3000
echo.
echo 按 Ctrl+C 停止服务器
echo ====================================
echo.

python app.py --with-frontend

echo.
echo 👋 服务器已停止
pause 