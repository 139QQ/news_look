@echo off
title NewsLook 开发环境启动
color 0a

echo.
echo ========================================
echo      NewsLook 财经新闻爬虫系统  
echo         开发环境一键启动
echo ========================================
echo.

echo [1/3] 检查环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.9+
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Node.js，请先安装Node.js 16+
    pause
    exit /b 1
)

echo ✅ Python 和 Node.js 环境检查通过

echo.
echo [2/3] 启动后端服务器 (端口 5000)...
start "NewsLook 后端" cmd /k "python app.py --port 5000"

echo 等待后端启动...
timeout /t 3 /nobreak >nul

echo.
echo [3/3] 启动前端服务器 (端口 3000)...
cd frontend
start "NewsLook 前端" cmd /k "npm run dev"

echo.
echo ========================================
echo 🚀 NewsLook 开发环境启动完成!
echo ========================================
echo.
echo 📱 前端界面: http://localhost:3000
echo 🔗 后端API:  http://localhost:5000
echo 📊 健康检查: http://localhost:5000/api/health
echo.
echo 💡 提示: 
echo   - 前端支持热重载，修改代码会自动刷新
echo   - 后端修改需要手动重启
echo   - 关闭此窗口不会停止服务器
echo.
echo 按任意键返回...
pause >nul 