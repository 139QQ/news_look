#!/usr/bin/env node

/**
 * CORS跨域问题诊断工具
 * 检查前后端配置和实际网络连接
 */

const axios = require('axios')
const fs = require('fs')
const path = require('path')

console.log('🔍 开始CORS跨域问题诊断...\n')

class CORSValidator {
  constructor() {
    this.frontendConfig = null
    this.backendConfig = null
    this.results = {
      configIssues: [],
      networkIssues: [],
      corsIssues: [],
      recommendations: []
    }
  }

  // 检查前端配置
  checkFrontendConfig() {
    console.log('📋 检查前端配置...')
    
    try {
      // 检查vite.config.js
      const viteConfigPath = path.join(__dirname, '..', 'vite.config.js')
      const viteConfig = fs.readFileSync(viteConfigPath, 'utf-8')
      
      // 检查代理配置
      const proxyMatch = viteConfig.match(/proxy:\s*{[\s\S]*?}/m)
      if (!proxyMatch) {
        this.results.configIssues.push('❌ Vite配置中缺少proxy代理配置')
        return
      }
      
      const proxyConfig = proxyMatch[0]
      console.log('✅ 前端代理配置:', proxyConfig)
      
      // 检查目标地址
      if (proxyConfig.includes('localhost:5000') || proxyConfig.includes('127.0.0.1:5000')) {
        console.log('✅ 代理目标地址配置正确')
      } else {
        this.results.configIssues.push('⚠️ 代理目标地址可能不正确')
      }
      
      // 检查changeOrigin
      if (proxyConfig.includes('changeOrigin: true')) {
        console.log('✅ changeOrigin配置正确')
      } else {
        this.results.configIssues.push('⚠️ 建议添加changeOrigin: true')
      }
      
    } catch (error) {
      this.results.configIssues.push(`❌ 读取前端配置失败: ${error.message}`)
    }
  }

  // 检查后端配置
  checkBackendConfig() {
    console.log('\n📋 检查后端配置...')
    
    try {
      // 检查app.yaml
      const configPath = path.join(__dirname, '..', '..', 'configs', 'app.yaml')
      if (fs.existsSync(configPath)) {
        const yamlContent = fs.readFileSync(configPath, 'utf-8')
        
        if (yamlContent.includes('cors:')) {
          console.log('✅ 后端CORS配置存在')
          
          if (yamlContent.includes('enabled: true')) {
            console.log('✅ CORS已启用')
          } else {
            this.results.configIssues.push('❌ CORS未启用')
          }
          
          if (yamlContent.includes('localhost:3000') || yamlContent.includes('127.0.0.1:3000')) {
            console.log('✅ CORS允许的源地址配置正确')
          } else {
            this.results.configIssues.push('⚠️ CORS允许的源地址可能不正确')
          }
        } else {
          this.results.configIssues.push('❌ 后端配置中缺少CORS设置')
        }
      } else {
        this.results.configIssues.push('❌ 找不到后端配置文件')
      }
      
    } catch (error) {
      this.results.configIssues.push(`❌ 读取后端配置失败: ${error.message}`)
    }
  }

  // 检测CORS实际情况
  async checkCORSHeaders() {
    console.log('\n🌐 检查CORS实际响应头...')
    
    const testUrls = [
      'http://localhost:5000/api/health',
      'http://127.0.0.1:5000/api/health',
    ]
    
    for (const url of testUrls) {
      try {
        console.log(`🔗 测试: ${url}`)
        
        // 发送OPTIONS预检请求
        const optionsResponse = await axios.options(url, {
          headers: {
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'content-type'
          },
          timeout: 5000,
          validateStatus: () => true
        })
        
        console.log(`  OPTIONS状态码: ${optionsResponse.status}`)
        
        const corsHeaders = {
          'access-control-allow-origin': optionsResponse.headers['access-control-allow-origin'],
          'access-control-allow-methods': optionsResponse.headers['access-control-allow-methods'],
          'access-control-allow-headers': optionsResponse.headers['access-control-allow-headers'],
          'access-control-allow-credentials': optionsResponse.headers['access-control-allow-credentials']
        }
        
        console.log('  CORS响应头:', corsHeaders)
        
        // 检查CORS头
        if (corsHeaders['access-control-allow-origin']) {
          console.log('  ✅ Access-Control-Allow-Origin存在')
        } else {
          this.results.corsIssues.push(`❌ ${url} 缺少Access-Control-Allow-Origin头`)
        }
        
        // 发送实际GET请求
        const getResponse = await axios.get(url, {
          headers: {
            'Origin': 'http://localhost:3000'
          },
          timeout: 5000,
          validateStatus: () => true
        })
        
        console.log(`  GET状态码: ${getResponse.status}`)
        if (getResponse.status === 200) {
          console.log('  ✅ 服务正常响应')
        }
        
      } catch (error) {
        console.log(`  ❌ 请求失败: ${error.message}`)
        this.results.networkIssues.push(`${url}: ${error.message}`)
      }
    }
  }

  // 检查网络连接
  async checkNetworkConnectivity() {
    console.log('\n🔌 检查网络连接...')
    
    const testPorts = [3000, 3001, 5000]
    
    for (const port of testPorts) {
      try {
        const response = await axios.get(`http://localhost:${port}`, {
          timeout: 3000,
          validateStatus: () => true
        })
        
        console.log(`  端口${port}: ${response.status === 200 ? '✅ 可访问' : `⚠️ 状态码${response.status}`}`)
        
      } catch (error) {
        if (error.code === 'ECONNREFUSED') {
          console.log(`  端口${port}: ❌ 连接被拒绝（服务未启动）`)
          this.results.networkIssues.push(`端口${port}无法连接`)
        } else {
          console.log(`  端口${port}: ❌ ${error.message}`)
          this.results.networkIssues.push(`端口${port}: ${error.message}`)
        }
      }
    }
  }

  // 生成诊断报告
  generateReport() {
    console.log('\n📊 诊断报告生成中...\n')
    
    console.log('='*60)
    console.log('📋 配置问题:')
    if (this.results.configIssues.length === 0) {
      console.log('  ✅ 未发现配置问题')
    } else {
      this.results.configIssues.forEach(issue => console.log(`  ${issue}`))
    }
    
    console.log('\n🌐 网络连接问题:')
    if (this.results.networkIssues.length === 0) {
      console.log('  ✅ 网络连接正常')
    } else {
      this.results.networkIssues.forEach(issue => console.log(`  ${issue}`))
    }
    
    console.log('\n🔀 CORS问题:')
    if (this.results.corsIssues.length === 0) {
      console.log('  ✅ 未发现CORS问题')
    } else {
      this.results.corsIssues.forEach(issue => console.log(`  ${issue}`))
    }
    
    console.log('\n💡 修复建议:')
    this.generateRecommendations()
    this.results.recommendations.forEach(rec => console.log(`  ${rec}`))
    
    console.log('='*60)
  }

  // 生成修复建议
  generateRecommendations() {
    if (this.results.networkIssues.some(issue => issue.includes('5000'))) {
      this.results.recommendations.push('🔧 启动后端服务: python app.py --port 5000')
    }
    
    if (this.results.networkIssues.some(issue => issue.includes('3000'))) {
      this.results.recommendations.push('🔧 启动前端服务: cd frontend && npm run dev')
    }
    
    if (this.results.corsIssues.length > 0) {
      this.results.recommendations.push('🔧 检查后端CORS配置是否包含前端地址')
      this.results.recommendations.push('🔧 确保后端安装了flask-cors包: pip install flask-cors')
    }
    
    if (this.results.configIssues.some(issue => issue.includes('proxy'))) {
      this.results.recommendations.push('🔧 检查前端vite.config.js中的proxy配置')
    }
    
    // 通用建议
    this.results.recommendations.push('📚 查看完整CORS配置文档: frontend/docs/cors-troubleshooting.md')
  }

  // 运行完整诊断
  async runFullDiagnostic() {
    try {
      this.checkFrontendConfig()
      this.checkBackendConfig()
      await this.checkNetworkConnectivity()
      await this.checkCORSHeaders()
      this.generateReport()
      
      // 生成修复脚本
      this.generateFixScript()
      
    } catch (error) {
      console.error('❌ 诊断过程中出错:', error)
    }
  }

  // 生成修复脚本
  generateFixScript() {
    const fixScript = `#!/bin/bash

# CORS问题修复脚本
echo "🔧 开始修复CORS问题..."

# 1. 检查后端依赖
echo "📦 检查后端依赖..."
pip install flask-cors

# 2. 重启后端服务
echo "🔄 重启后端服务..."
cd "$(dirname "$0")/../.."
python app.py --port 5000 &
BACKEND_PID=$!
echo "后端PID: $BACKEND_PID"

# 3. 重启前端服务
echo "🔄 重启前端服务..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo "前端PID: $FRONTEND_PID"

echo "✅ 服务重启完成"
echo "🌐 前端地址: http://localhost:3000"
echo "🔗 后端地址: http://localhost:5000"
echo "❌ 停止服务: kill $BACKEND_PID $FRONTEND_PID"
`

    const scriptPath = path.join(__dirname, 'fix-cors.sh')
    fs.writeFileSync(scriptPath, fixScript)
    console.log(`\n📝 已生成修复脚本: ${scriptPath}`)
  }
}

// 运行诊断
const validator = new CORSValidator()
validator.runFullDiagnostic() 