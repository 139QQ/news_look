@echo off
echo 启动财经新闻爬虫系统...

REM 检查Python环境
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误：未找到Python。请安装Python 3并添加到PATH。
    pause
    exit /b 1
)

REM 创建必要的目录
mkdir logs 2>nul
mkdir data 2>nul
mkdir data\db 2>nul
mkdir data\output 2>nul

REM 设置环境变量
set "LOG_LEVEL=INFO"
set "LOG_DIR=%cd%\logs"
set "DB_DIR=%cd%\data\db"

REM 运行Web应用
echo 启动Web应用...
python run.py web --debug --host=0.0.0.0 --port=5000 --with-crawler

if %ERRORLEVEL% neq 0 (
    echo 启动失败，请检查logs目录下的日志文件。
    pause
) else (
    echo Web应用已启动，正在运行中...
)

pause 