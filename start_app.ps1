# NewsLook 财经新闻爬虫系统启动脚本
# PowerShell 版本

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "     NewsLook 财经新闻爬虫系统" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# 检查虚拟环境是否存在
if (-not (Test-Path ".venv\Scripts\activate.ps1")) {
    Write-Host "❌ 虚拟环境不存在，正在创建..." -ForegroundColor Red
    & D:\python\python.exe -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 创建虚拟环境失败" -ForegroundColor Red
        Read-Host "按任意键继续..."
        exit 1
    }
    Write-Host "✅ 虚拟环境创建成功" -ForegroundColor Green
    Write-Host ""
}

# 激活虚拟环境
Write-Host "🔧 激活虚拟环境..." -ForegroundColor Blue
& .venv\Scripts\activate.ps1

# 检查是否需要安装依赖
if (-not (Test-Path ".venv\Lib\site-packages\flask")) {
    Write-Host "📦 检测到缺少依赖，正在安装..." -ForegroundColor Yellow
    & python -m pip install --upgrade pip
    & pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 安装依赖失败" -ForegroundColor Red
        Read-Host "按任意键继续..."
        exit 1
    }
    Write-Host "✅ 依赖安装成功" -ForegroundColor Green
    Write-Host ""
}

# 启动应用
Write-Host "🚀 启动应用..." -ForegroundColor Green
Write-Host ""
Write-Host "📍 后端地址: http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "🎨 前端地址: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# 启动应用
try {
    & python app.py --with-frontend
}
catch {
    Write-Host "❌ 启动失败: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    Write-Host ""
    Write-Host "👋 服务器已停止" -ForegroundColor Yellow
    Read-Host "按任意键继续..."
} 