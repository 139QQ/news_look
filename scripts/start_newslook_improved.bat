@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo   NewsLook 财经新闻爬虫系统 (改进版)
echo ========================================
echo.

:: 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未检测到Python，请先安装Python 3.9+
    echo 📥 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python环境检查通过
python --version
echo.

:: 创建数据目录
if not exist data\db (
    echo 📁 创建数据库目录...
    mkdir data\db
    echo ✅ 数据库目录创建完成
    echo.
)

:: 显示启动选项
echo 🚀 请选择启动模式:
echo.
echo [1] 完整模式 - 启动后端API + Python前端服务器 (推荐)
echo [2] 完整模式 - 启动后端API + Vue开发服务器 (需要Node.js)
echo [3] 仅后端API (Flask服务器)
echo [4] 仅Python前端服务器
echo [5] 爬虫模式 - 运行新闻爬虫
echo [6] 查看系统状态
echo [0] 退出
echo.
set /p choice="请输入选择 (1-6, 0退出): "

if "%choice%"=="1" goto :full_mode_python
if "%choice%"=="2" goto :full_mode_node
if "%choice%"=="3" goto :backend_only
if "%choice%"=="4" goto :frontend_python_only
if "%choice%"=="5" goto :crawler_mode
if "%choice%"=="6" goto :status_check
if "%choice%"=="0" goto :exit
goto :invalid_choice

:full_mode_python
echo.
echo 🌟 启动完整模式 (Python前端)...
echo ⚡ 正在启动后端API服务器...
start "NewsLook Backend" cmd /k "python run.py web --host 0.0.0.0 --port 5000 && pause"
timeout /t 3 >nul

echo ⚡ 正在启动Python前端服务器...
start "NewsLook Frontend" cmd /k "python start_frontend_simple.py && pause"
timeout /t 2 >nul

echo.
echo ✅ 系统启动完成！
echo 🌐 后端API: http://localhost:5000
echo 🎨 前端界面: http://localhost:3000
echo.
echo 📝 注意: 请等待几秒钟让服务完全启动
echo 💡 使用Python内置服务器，无需Node.js环境
goto :end

:full_mode_node
echo.
echo 🌟 启动完整模式 (Vue开发服务器)...

:: 检查Node.js环境
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未检测到Node.js，请先安装Node.js或选择模式1
    echo 📥 下载地址: https://nodejs.org/
    echo 💡 建议: 选择模式1使用Python前端服务器
    pause
    goto :start
)

echo ✅ Node.js环境检查通过
node --version
echo.

:: 检查前端依赖
if exist package.json (
    echo 📦 检查前端依赖...
    if not exist node_modules (
        echo 正在安装前端依赖...
        npm install
        if %errorlevel% neq 0 (
            echo ❌ 错误: 前端依赖安装失败，切换到Python前端模式
            goto :full_mode_python
        )
    )
    echo ✅ 前端依赖检查完成
    echo.
)

echo ⚡ 正在启动后端API服务器...
start "NewsLook Backend" cmd /k "python run.py web --host 0.0.0.0 --port 5000 && pause"
timeout /t 3 >nul

echo ⚡ 正在启动Vue前端开发服务器...
start "NewsLook Frontend" cmd /k "npm run dev && pause"
timeout /t 2 >nul

echo.
echo ✅ 系统启动完成！
echo 🌐 后端API: http://localhost:5000
echo 🎨 前端界面: http://localhost:3000 (Vite开发服务器)
goto :end

:backend_only
echo.
echo 🔧 启动后端API服务器...
echo 🌐 服务器地址: http://localhost:5000
echo 📋 API文档: http://localhost:5000/health (健康检查)
echo.
python run.py web --host 0.0.0.0 --port 5000
goto :end

:frontend_python_only
echo.
echo 🎨 启动Python前端服务器...
echo 🌐 前端地址: http://localhost:3000
echo 💡 请确保后端API服务器已在 http://localhost:5000 启动
echo.
python start_frontend_simple.py
goto :end

:crawler_mode
echo.
echo 🕷️ 爬虫模式选项:
echo.
echo [1] 爬取所有来源
echo [2] 爬取新浪财经
echo [3] 爬取东方财富
echo [4] 爬取腾讯财经
echo [5] 爬取网易财经
echo [6] 爬取凤凰财经
echo [0] 返回主菜单
echo.
set /p crawler_choice="请选择爬虫来源: "

if "%crawler_choice%"=="1" (
    echo 🕷️ 启动所有爬虫...
    python run.py crawler --all --max 50
) else if "%crawler_choice%"=="2" (
    echo 🕷️ 启动新浪财经爬虫...
    python run.py crawler --source sina --max 50
) else if "%crawler_choice%"=="3" (
    echo 🕷️ 启动东方财富爬虫...
    python run.py crawler --source eastmoney --max 50
) else if "%crawler_choice%"=="4" (
    echo 🕷️ 启动腾讯财经爬虫...
    python run.py crawler --source tencent --max 50
) else if "%crawler_choice%"=="5" (
    echo 🕷️ 启动网易财经爬虫...
    python run.py crawler --source netease --max 50
) else if "%crawler_choice%"=="6" (
    echo 🕷️ 启动凤凰财经爬虫...
    python run.py crawler --source ifeng --max 50
) else if "%crawler_choice%"=="0" (
    goto :start
) else (
    echo ❌ 无效选择
    pause
    goto :crawler_mode
)
goto :end

:status_check
echo.
echo 📊 系统状态检查...
echo.
echo 📁 数据库统计:
python run.py db stats --format table
echo.
echo 🌐 如需查看详细信息，请访问Web界面
echo 💡 推荐启动完整模式查看数据
pause
goto :start

:invalid_choice
echo ❌ 无效选择，请重新输入
pause
goto :start

:end
echo.
echo 📋 系统信息:
echo 📁 项目路径: %CD%
echo 📚 使用说明: 查看 WEB界面使用指南.md
echo 🔧 技术支持: 查看 README.md
echo.
echo 💡 提示: 
echo    - 如果Node.js环境有问题，建议使用模式1 (Python前端)
echo    - 前端界面使用Vue 3 + 简化UI，功能完整
echo    - 可通过API端点直接访问数据
echo.
pause
goto :start

:exit
echo 👋 感谢使用NewsLook财经新闻爬虫系统！
echo.
pause
exit 