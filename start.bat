@echo off
echo ========================================
echo    NewsLook 财经新闻爬虫系统启动器
echo ========================================
echo.

cd /d "%~dp0"

echo 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或未添加到PATH
    echo 请安装Python 3.9+并添加到系统PATH
    pause
    exit /b 1
)

echo 检查依赖...
if not exist requirements.txt (
    echo ❌ requirements.txt文件不存在
    pause
    exit /b 1
)

echo 安装/更新依赖...
pip install -r requirements.txt

echo.
echo 启动后端服务...
echo 后端地址: http://localhost:5000
echo.

start "NewsLook Backend" python main.py

echo.
echo 检查前端环境...
cd frontend

if not exist node_modules (
    echo 安装前端依赖...
    npm install
)

echo 启动前端开发服务器...
echo 前端地址: http://localhost:3000
echo.

start "NewsLook Frontend" npm run dev

cd ..

echo.
echo ✅ NewsLook 启动完成!
echo 请在浏览器中访问: http://localhost:3000
echo.
pause
