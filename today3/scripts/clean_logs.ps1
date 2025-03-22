# 日志清理脚本
# 用于清理30天以前的日志文件

# 脚本配置
$LOG_ROOT = Join-Path $PSScriptRoot "..\logs"  # 日志根目录
$DAYS = 30                                     # 保留天数
$VERBOSE = $true                               # 是否显示详细信息

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
    # 计算截止日期
    $cutoffDate = (Get-Date).AddDays(-$DAYS)
    $logRoot = Resolve-Path $LOG_ROOT
    
    Write-LogMessage "开始清理日志文件，保留 $DAYS 天内的日志" "INFO"
    Write-LogMessage "日志根目录: $logRoot" "INFO"
    Write-LogMessage "截止日期: $cutoffDate" "INFO"
    
    try {
        # 获取所有日志文件
        $logFiles = Get-ChildItem -Path $logRoot -Filter "*.log" -Recurse
        
        Write-LogMessage "找到 $($logFiles.Count) 个日志文件" "INFO"
        
        # 按日期筛选和清理
        $oldLogFiles = $logFiles | Where-Object { $_.LastWriteTime -lt $cutoffDate }
        $removedCount = 0
        
        foreach ($logFile in $oldLogFiles) {
            if ($VERBOSE) {
                Write-LogMessage "删除文件: $($logFile.FullName) (最后修改时间: $($logFile.LastWriteTime))" "INFO"
            }
            
            try {
                Remove-Item $logFile.FullName -Force
                $removedCount++
            } catch {
                Write-LogMessage "删除文件失败: $($logFile.FullName)" "ERROR"
                Write-LogMessage $_.Exception.Message "ERROR"
            }
        }
        
        Write-LogMessage "清理完成，共删除 $removedCount 个过期日志文件" "INFO"
    } catch {
        Write-LogMessage "清理过程中发生错误" "ERROR"
        Write-LogMessage $_.Exception.Message "ERROR"
    }
}

# 执行主函数
Main 