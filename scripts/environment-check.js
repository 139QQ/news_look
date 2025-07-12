#!/usr/bin/env node

/**
 * NewsLook 环境一致性检查脚本
 * 验证前后端配置、数据库连接、API端点等
 */

const fs = require('fs').promises
const path = require('path')
const axios = require('axios')
const { exec } = require('child_process')
const util = require('util')

const execAsync = util.promisify(exec)

// 颜色输出工具
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m'
}

function colorLog(color, message) {
  console.log(`${colors[color]}${message}${colors.reset}`)
}

// 检查结果收集器
const checkResults = {
  passed: 0,
  failed: 0,
  warnings: 0,
  results: []
}

function addResult(category, item, status, message, details = null) {
  const result = { category, item, status, message, details, timestamp: new Date() }
  checkResults.results.push(result)
  
  if (status === 'PASS') {
    checkResults.passed++
    colorLog('green', `✅ [${category}] ${item}: ${message}`)
  } else if (status === 'FAIL') {
    checkResults.failed++
    colorLog('red', `❌ [${category}] ${item}: ${message}`)
  } else if (status === 'WARN') {
    checkResults.warnings++
    colorLog('yellow', `⚠️  [${category}] ${item}: ${message}`)
  }
  
  if (details) {
    console.log(`   详情: ${JSON.stringify(details, null, 2)}`)
  }
}

// 1. 前端环境变量检查
async function checkFrontendEnvironment() {
  colorLog('cyan', '\n🔍 检查前端环境配置...')
  
  try {
    // 检查前端包配置
    const packagePath = path.join(process.cwd(), 'frontend', 'package.json')
    const packageContent = await fs.readFile(packagePath, 'utf8')
    const packageJson = JSON.parse(packageContent)
    
    addResult('前端', 'package.json', 'PASS', `项目版本: ${packageJson.version}`)
    
    // 检查关键依赖
    const criticalDeps = ['vue', 'axios', 'element-plus']
    for (const dep of criticalDeps) {
      if (packageJson.dependencies[dep]) {
        addResult('前端', `依赖-${dep}`, 'PASS', `版本: ${packageJson.dependencies[dep]}`)
      } else {
        addResult('前端', `依赖-${dep}`, 'FAIL', '关键依赖缺失')
      }
    }
    
    // 检查Vite配置
    const viteConfigPath = path.join(process.cwd(), 'frontend', 'vite.config.js')
    try {
      await fs.access(viteConfigPath)
      addResult('前端', 'vite.config.js', 'PASS', '配置文件存在')
    } catch {
      addResult('前端', 'vite.config.js', 'FAIL', '配置文件缺失')
    }
    
  } catch (error) {
    addResult('前端', '环境检查', 'FAIL', `检查失败: ${error.message}`)
  }
}

// 2. 后端环境检查
async function checkBackendEnvironment() {
  colorLog('cyan', '\n🔍 检查后端环境配置...')
  
  try {
    // 检查后端配置文件
    const configPath = path.join(process.cwd(), 'configs', 'app.yaml')
    const configContent = await fs.readFile(configPath, 'utf8')
    
    addResult('后端', 'app.yaml', 'PASS', '配置文件存在且可读取')
    
    // 检查Python环境
    try {
      const { stdout } = await execAsync('python --version')
      const pythonVersion = stdout.trim()
      addResult('后端', 'Python版本', 'PASS', pythonVersion)
    } catch {
      try {
        const { stdout } = await execAsync('python3 --version')
        const pythonVersion = stdout.trim()
        addResult('后端', 'Python版本', 'PASS', pythonVersion)
      } catch {
        addResult('后端', 'Python环境', 'FAIL', 'Python未安装或不在PATH中')
      }
    }
    
    // 检查requirements.txt
    const reqPath = path.join(process.cwd(), 'requirements.txt')
    try {
      await fs.access(reqPath)
      addResult('后端', 'requirements.txt', 'PASS', '依赖文件存在')
    } catch {
      addResult('后端', 'requirements.txt', 'WARN', '依赖文件不存在')
    }
    
  } catch (error) {
    addResult('后端', '环境检查', 'FAIL', `检查失败: ${error.message}`)
  }
}

// 3. 数据库连接检查
async function checkDatabaseConnection() {
  colorLog('cyan', '\n🔍 检查数据库连接...')
  
  try {
    // 检查数据库目录
    const dbDir = path.join(process.cwd(), 'data', 'db')
    try {
      const files = await fs.readdir(dbDir)
      const dbFiles = files.filter(file => file.endsWith('.db'))
      
      if (dbFiles.length > 0) {
        addResult('数据库', 'SQLite文件', 'PASS', `发现 ${dbFiles.length} 个数据库文件`, dbFiles)
      } else {
        addResult('数据库', 'SQLite文件', 'WARN', '未发现数据库文件')
      }
    } catch {
      addResult('数据库', '数据库目录', 'FAIL', 'data/db 目录不存在')
    }
    
  } catch (error) {
    addResult('数据库', '连接检查', 'FAIL', `检查失败: ${error.message}`)
  }
}

// 4. API端点验证
async function checkApiEndpoints() {
  colorLog('cyan', '\n🔍 检查API端点...')
  
  const baseUrls = [
    'http://127.0.0.1:5000',
    'http://localhost:5000',
    'http://127.0.0.1:8000',
    'http://localhost:8000'
  ]
  
  const endpoints = [
    '/api/health',
    '/api/news',
    '/api/sources',
    '/api/v1/crawlers/status'
  ]
  
  let activeBaseUrl = null
  
  // 首先找到活跃的后端服务
  for (const baseUrl of baseUrls) {
    try {
      const response = await axios.get(`${baseUrl}/api/health`, { 
        timeout: 3000,
        validateStatus: status => status < 500 
      })
      
      if (response.status === 200) {
        activeBaseUrl = baseUrl
        addResult('API', '后端服务', 'PASS', `服务运行在: ${baseUrl}`)
        break
      }
    } catch (error) {
      // 继续尝试下一个URL
    }
  }
  
  if (!activeBaseUrl) {
    addResult('API', '后端服务', 'FAIL', '无法连接到后端服务')
    return
  }
  
  // 测试各个端点
  for (const endpoint of endpoints) {
    try {
      const response = await axios.get(`${activeBaseUrl}${endpoint}`, {
        timeout: 5000,
        validateStatus: status => status < 500
      })
      
      if (response.status === 200) {
        addResult('API', endpoint, 'PASS', `响应状态: ${response.status}`)
      } else if (response.status === 404) {
        addResult('API', endpoint, 'WARN', `端点不存在: ${response.status}`)
      } else {
        addResult('API', endpoint, 'FAIL', `异常状态: ${response.status}`)
      }
    } catch (error) {
      if (error.code === 'ECONNREFUSED') {
        addResult('API', endpoint, 'FAIL', '连接被拒绝')
      } else if (error.code === 'ETIMEDOUT') {
        addResult('API', endpoint, 'FAIL', '请求超时')
      } else {
        addResult('API', endpoint, 'FAIL', error.message)
      }
    }
  }
}

// 5. 跨域配置检查
async function checkCorsConfiguration() {
  colorLog('cyan', '\n🔍 检查跨域配置...')
  
  try {
    // 模拟前端请求检查CORS
    const testUrls = [
      'http://127.0.0.1:5000',
      'http://localhost:5000'
    ]
    
    for (const baseUrl of testUrls) {
      try {
        const response = await axios.get(`${baseUrl}/api/health`, {
          timeout: 3000,
          headers: {
            'Origin': 'http://localhost:3000'
          }
        })
        
        const corsHeaders = {
          'Access-Control-Allow-Origin': response.headers['access-control-allow-origin'],
          'Access-Control-Allow-Methods': response.headers['access-control-allow-methods'],
          'Access-Control-Allow-Headers': response.headers['access-control-allow-headers']
        }
        
        if (corsHeaders['Access-Control-Allow-Origin']) {
          addResult('CORS', baseUrl, 'PASS', 'CORS头部存在', corsHeaders)
        } else {
          addResult('CORS', baseUrl, 'WARN', 'CORS头部缺失')
        }
        
        break
      } catch (error) {
        continue
      }
    }
  } catch (error) {
    addResult('CORS', '配置检查', 'FAIL', `检查失败: ${error.message}`)
  }
}

// 6. 系统资源检查
async function checkSystemResources() {
  colorLog('cyan', '\n🔍 检查系统资源...')
  
  try {
    // 检查内存使用
    if (process.platform !== 'win32') {
      try {
        const { stdout } = await execAsync('free -m')
        const memInfo = stdout.split('\n')[1].split(/\s+/)
        const total = parseInt(memInfo[1])
        const used = parseInt(memInfo[2])
        const usage = ((used / total) * 100).toFixed(1)
        
        if (usage < 80) {
          addResult('系统', '内存使用', 'PASS', `${usage}% (${used}MB/${total}MB)`)
        } else {
          addResult('系统', '内存使用', 'WARN', `内存使用率较高: ${usage}%`)
        }
      } catch {
        addResult('系统', '内存检查', 'WARN', '无法获取内存信息')
      }
    } else {
      addResult('系统', '内存检查', 'WARN', 'Windows系统跳过内存检查')
    }
    
    // 检查磁盘空间
    try {
      const { stdout } = await execAsync(process.platform === 'win32' ? 'dir /-c' : 'df -h .')
      addResult('系统', '磁盘空间', 'PASS', '磁盘空间检查完成')
    } catch {
      addResult('系统', '磁盘空间', 'WARN', '无法检查磁盘空间')
    }
    
  } catch (error) {
    addResult('系统', '资源检查', 'FAIL', `检查失败: ${error.message}`)
  }
}

// 7. 网络连通性检查
async function checkNetworkConnectivity() {
  colorLog('cyan', '\n🔍 检查网络连通性...')
  
  const testUrls = [
    'https://www.baidu.com',
    'https://api.github.com',
    'https://httpbin.org/get'
  ]
  
  for (const url of testUrls) {
    try {
      const response = await axios.get(url, { timeout: 5000 })
      if (response.status === 200) {
        addResult('网络', url, 'PASS', '连接正常')
      } else {
        addResult('网络', url, 'WARN', `状态码: ${response.status}`)
      }
    } catch (error) {
      addResult('网络', url, 'FAIL', error.message)
    }
  }
}

// 生成检查报告
async function generateReport() {
  colorLog('cyan', '\n📊 生成检查报告...')
  
  const report = {
    timestamp: new Date().toISOString(),
    summary: {
      total: checkResults.results.length,
      passed: checkResults.passed,
      failed: checkResults.failed,
      warnings: checkResults.warnings
    },
    results: checkResults.results,
    environment: {
      nodeVersion: process.version,
      platform: process.platform,
      arch: process.arch,
      cwd: process.cwd()
    }
  }
  
  // 保存报告
  const reportPath = path.join(process.cwd(), 'logs', `environment-check-${Date.now()}.json`)
  
  try {
    // 确保logs目录存在
    await fs.mkdir(path.dirname(reportPath), { recursive: true })
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2))
    addResult('报告', '生成', 'PASS', `报告已保存: ${reportPath}`)
  } catch (error) {
    addResult('报告', '生成', 'FAIL', `保存失败: ${error.message}`)
  }
  
  return report
}

// 主函数
async function main() {
  colorLog('blue', '🚀 NewsLook 环境一致性检查开始...')
  colorLog('blue', '='.repeat(60))
  
  try {
    await checkFrontendEnvironment()
    await checkBackendEnvironment()
    await checkDatabaseConnection()
    await checkApiEndpoints()
    await checkCorsConfiguration()
    await checkSystemResources()
    await checkNetworkConnectivity()
    
    const report = await generateReport()
    
    // 输出总结
    colorLog('blue', '\n📋 检查总结:')
    colorLog('blue', '='.repeat(40))
    colorLog('green', `✅ 通过: ${report.summary.passed}`)
    colorLog('yellow', `⚠️  警告: ${report.summary.warnings}`)
    colorLog('red', `❌ 失败: ${report.summary.failed}`)
    colorLog('blue', `📊 总计: ${report.summary.total}`)
    
    if (report.summary.failed > 0) {
      colorLog('red', '\n❗ 发现严重问题，请检查失败项目')
      process.exit(1)
    } else if (report.summary.warnings > 0) {
      colorLog('yellow', '\n⚠️  发现警告，建议检查相关配置')
      process.exit(0)
    } else {
      colorLog('green', '\n🎉 所有检查通过！环境配置正常')
      process.exit(0)
    }
    
  } catch (error) {
    colorLog('red', `\n💥 检查过程中发生错误: ${error.message}`)
    console.error(error)
    process.exit(1)
  }
}

// 如果直接运行此脚本
if (require.main === module) {
  main()
}

module.exports = {
  main,
  checkFrontendEnvironment,
  checkBackendEnvironment,
  checkApiEndpoints,
  checkDatabaseConnection
} 