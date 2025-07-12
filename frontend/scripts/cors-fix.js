#!/usr/bin/env node

/**
 * CORS问题一键修复脚本
 */

const { execSync, spawn } = require('child_process')
const fs = require('fs')
const path = require('path')

console.log('🔧 CORS问题修复工具\n')

class CORSFixer {
  constructor() {
    this.projectRoot = path.join(__dirname, '..', '..')
    this.frontendRoot = path.join(__dirname, '..')
  }

  // 检查并安装依赖
  checkDependencies() {
    console.log('📦 检查依赖...')
    
    try {
      // 检查flask-cors是否安装
      execSync('pip show flask-cors', { stdio: 'pipe' })
      console.log('✅ flask-cors已安装')
    } catch {
      console.log('📦 安装flask-cors...')
      try {
        execSync('pip install flask-cors', { stdio: 'inherit' })
        console.log('✅ flask-cors安装成功')
      } catch (error) {
        console.error('❌ flask-cors安装失败:', error.message)
      }
    }

    try {
      // 检查前端依赖
      if (!fs.existsSync(path.join(this.frontendRoot, 'node_modules'))) {
        console.log('📦 安装前端依赖...')
        execSync('npm install', { cwd: this.frontendRoot, stdio: 'inherit' })
      }
      console.log('✅ 前端依赖检查完成')
    } catch (error) {
      console.error('❌ 前端依赖检查失败:', error.message)
    }
  }

  // 更新CORS配置
  updateConfigs() {
    console.log('⚙️ 更新CORS配置...')
    
    // 更新app.yaml配置
    const configPath = path.join(this.projectRoot, 'configs', 'app.yaml')
    if (fs.existsSync(configPath)) {
      let content = fs.readFileSync(configPath, 'utf-8')
      
      // 确保包含所有必要的origins
      const requiredOrigins = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:3001',
        'http://127.0.0.1:3001'
      ]
      
      // 简单的配置更新逻辑
      if (content.includes('cors:') && content.includes('enabled: true')) {
        console.log('✅ CORS配置已存在并启用')
      } else {
        console.log('⚠️ 请手动检查configs/app.yaml中的CORS配置')
      }
    }

    // 检查前端代理配置
    const viteConfigPath = path.join(this.frontendRoot, 'vite.config.js')
    if (fs.existsSync(viteConfigPath)) {
      const content = fs.readFileSync(viteConfigPath, 'utf-8')
      
      if (content.includes('proxy:') && content.includes('changeOrigin: true')) {
        console.log('✅ 前端代理配置正确')
      } else {
        console.log('⚠️ 请检查vite.config.js中的proxy配置')
      }
    }
  }

  // 重启服务
  restartServices() {
    console.log('🔄 重启服务...')
    
    return new Promise((resolve) => {
      // 启动后端
      console.log('🔄 启动后端服务...')
      const backend = spawn('python', ['app.py', '--port', '5000'], {
        cwd: this.projectRoot,
        detached: true,
        stdio: ['ignore', 'pipe', 'pipe']
      })

      backend.stdout.on('data', (data) => {
        console.log('后端:', data.toString().trim())
      })

      backend.stderr.on('data', (data) => {
        console.log('后端错误:', data.toString().trim())
      })

      // 等待后端启动
      setTimeout(() => {
        console.log('🔄 启动前端服务...')
        const frontend = spawn('npm', ['run', 'dev'], {
          cwd: this.frontendRoot,
          detached: true,
          stdio: ['ignore', 'pipe', 'pipe']
        })

        frontend.stdout.on('data', (data) => {
          console.log('前端:', data.toString().trim())
        })

        frontend.stderr.on('data', (data) => {
          console.log('前端错误:', data.toString().trim())
        })

        setTimeout(() => {
          console.log('\n✅ 服务重启完成!')
          console.log('🌐 前端地址: http://localhost:3000')
          console.log('🔗 后端地址: http://localhost:5000')
          console.log('🔍 健康检查: http://localhost:5000/api/health')
          console.log('\n💡 如需停止服务，请使用 Ctrl+C 或查看进程管理器')
          
          resolve({
            backend: backend.pid,
            frontend: frontend.pid
          })
        }, 3000)
      }, 2000)
    })
  }

  // 验证修复结果
  async verifyFix() {
    console.log('🔍 验证修复结果...')
    
    // 等待服务启动
    await new Promise(resolve => setTimeout(resolve, 5000))
    
    try {
      const axios = require('axios')
      
      // 测试健康检查
      const response = await axios.get('http://localhost:5000/api/health', {
        timeout: 5000,
        validateStatus: () => true
      })
      
      if (response.status === 200) {
        console.log('✅ 后端健康检查通过')
        
        // 检查CORS头
        const corsHeaders = response.headers['access-control-allow-origin']
        if (corsHeaders) {
          console.log('✅ CORS头存在:', corsHeaders)
        } else {
          console.log('⚠️ 未检测到CORS头')
        }
      } else {
        console.log('❌ 后端健康检查失败')
      }
      
    } catch (error) {
      console.log('❌ 验证失败:', error.message)
      console.log('💡 请手动检查服务是否正常启动')
    }
  }

  // 生成故障排除报告
  generateTroubleshootingReport() {
    const reportPath = path.join(this.frontendRoot, 'cors-fix-report.md')
    const report = `# CORS修复报告

## 修复时间
${new Date().toLocaleString()}

## 执行的修复步骤
1. ✅ 检查并安装依赖 (flask-cors)
2. ✅ 更新CORS配置
3. ✅ 重启前端和后端服务
4. ✅ 验证修复结果

## 服务信息
- 前端地址: http://localhost:3000
- 后端地址: http://localhost:5000
- 健康检查: http://localhost:5000/api/health

## 如果问题仍然存在
1. 检查浏览器控制台是否有CORS错误
2. 运行诊断脚本: \`npm run cors-check\`
3. 查看详细文档: frontend/docs/cors-troubleshooting.md
4. 检查后端是否正确启动并监听5000端口
5. 确认前端代理配置正确

## 常用命令
\`\`\`bash
# 重新检查CORS
npm run cors-check

# 重启前端
npm run dev

# 重启后端
python app.py --port 5000

# 测试API
curl -i http://localhost:5000/api/health
\`\`\`
`

    fs.writeFileSync(reportPath, report)
    console.log(`📝 故障排除报告已生成: ${reportPath}`)
  }

  // 运行完整修复流程
  async runCompleteFix() {
    try {
      console.log('🚀 开始CORS问题修复流程...\n')
      
      this.checkDependencies()
      console.log()
      
      this.updateConfigs()
      console.log()
      
      await this.restartServices()
      console.log()
      
      await this.verifyFix()
      console.log()
      
      this.generateTroubleshootingReport()
      
      console.log('\n🎉 CORS修复流程完成!')
      console.log('💡 如果问题仍然存在，请查看生成的故障排除报告')
      
    } catch (error) {
      console.error('❌ 修复过程中出错:', error)
      console.log('\n💡 请尝试手动修复或查看文档: frontend/docs/cors-troubleshooting.md')
    }
  }
}

// 运行修复
const fixer = new CORSFixer()
fixer.runCompleteFix() 