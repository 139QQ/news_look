# 日志整理脚本
# 用于将logs目录下的日志文件按爬虫名称分类存储

# 脚本配置
$LOG_ROOT = Join-Path $PSScriptRoot "..\logs"  # 日志根目录
$VERBOSE = $true                               # 是否显示详细信息

# 爬虫名称映射表
$CRAWLER_NAMES = @{
    "eastmoney" = "eastmoney"
    "eastmoney_simple" = "eastmoney_simple"
    "sina" = "sina"
    "tencent" = "tencent"
    "netease" = "netease"
    "ifeng" = "ifeng"
    "东方财富" = "东方财富"
    "新浪财经" = "新浪财经"
    "腾讯财经" = "腾讯财经"
    "网易财经" = "网易财经"
    "凤凰财经" = "凤凰财经"
}

# 输出信息函数
function Write-LogMessage {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Message,
        
        [Parameter(Mandatory = $false)]
        [string]$Type = "INFO"
    )
    
    $timeStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timeStamp] [$Type] $Message"
}

# 主函数
function Main {
    $logRoot = Resolve-Path $LOG_ROOT
    
    Write-LogMessage "开始整理日志文件，按爬虫名称分类存储" "INFO"
    Write-LogMessage "日志根目录: $logRoot" "INFO"
    
    try {
        # 获取根目录下的所有日志文件
        $logFiles = Get-ChildItem -Path $logRoot -Filter "*.log" -File
        
        Write-LogMessage "找到 $($logFiles.Count) 个待整理的日志文件" "INFO"
        
        $movedCount = 0
        
        foreach ($logFile in $logFiles) {
            $fileName = $logFile.Name
            $matched = $false
            
            # 根据文件名前缀确定爬虫类型
            foreach ($crawlerPrefix in $CRAWLER_NAMES.Keys) {
                if ($fileName -like "$crawlerPrefix*") {
                    $crawlerDir = Join-Path $logRoot $CRAWLER_NAMES[$crawlerPrefix]
                    
                    # 确保目标目录存在
                    if (-not (Test-Path $crawlerDir)) {
                        New-Item -Path $crawlerDir -ItemType Directory -Force | Out-Null
                        Write-LogMessage "创建目录: $crawlerDir" "INFO"
                    }
                    
                    $targetPath = Join-Path $crawlerDir $fileName
                    
                    # 检查目标文件是否已存在
                    if (Test-Path $targetPath) {
                        Write-LogMessage "目标文件已存在，将覆盖: $targetPath" "WARNING"
                        Remove-Item $targetPath -Force
                    }
                    
                    if ($VERBOSE) {
                        Write-LogMessage "移动文件: $($logFile.FullName) -> $targetPath" "INFO"
                    }
                    
                    try {
                        Move-Item -Path $logFile.FullName -Destination $targetPath -Force
                        $movedCount++
                        $matched = $true
                        break
                    } catch {
                        Write-LogMessage "移动文件失败: $($logFile.FullName)" "ERROR"
                        Write-LogMessage $_.Exception.Message "ERROR"
                    }
                }
            }
            
            if (-not $matched) {
                Write-LogMessage "无法确定文件 $fileName 所属的爬虫，保留在原位置" "WARNING"
            }
        }
        
        Write-LogMessage "整理完成，共移动 $movedCount 个日志文件" "INFO"
    } catch {
        Write-LogMessage "整理过程中发生错误" "ERROR"
        Write-LogMessage $_.Exception.Message "ERROR"
    }
}

# 执行主函数
Main 