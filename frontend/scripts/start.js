import { spawn } from 'child_process'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m'
}

const log = (message, color = 'reset') => {
  console.log(`${colors[color]}${message}${colors.reset}`)
}

// 检查Node.js版本
const checkNodeVersion = () => {
  const nodeVersion = process.version
  const majorVersion = parseInt(nodeVersion.split('.')[0].slice(1))
  
  if (majorVersion < 16) {
    log('❌ Node.js 版本过低！需要 Node.js 16 或更高版本', 'red')
    log(`当前版本: ${nodeVersion}`, 'yellow')
    process.exit(1)
  }
  
  log(`✅ Node.js 版本检查通过: ${nodeVersion}`, 'green')
}

// 检查依赖是否安装
const checkDependencies = () => {
  const packageJsonPath = path.join(__dirname, '../package.json')
  const nodeModulesPath = path.join(__dirname, '../node_modules')
  
  if (!fs.existsSync(packageJsonPath)) {
    log('❌ 未找到 package.json 文件', 'red')
    process.exit(1)
  }
  
  if (!fs.existsSync(nodeModulesPath)) {
    log('❌ 依赖未安装，请先运行 npm install', 'red')
    process.exit(1)
  }
  
  log('✅ 依赖检查通过', 'green')
}

// 检查端口是否可用
const checkPortAvailable = (port) => {
  return new Promise((resolve) => {
    import('net').then(({ default: net }) => {
      const server = net.createServer()
      
      server.listen(port, () => {
        server.once('close', () => {
          resolve(true)
        })
        server.close()
      })
      
      server.on('error', () => {
        resolve(false)
      })
    })
  })
}

// 启动开发服务器
const startDevServer = async () => {
  log('\n🚀 启动 NewsLook 前端开发服务器...', 'cyan')
  
  // 检查端口
  const port = 3000
  const isPortAvailable = await checkPortAvailable(port)
  
  if (!isPortAvailable) {
    log(`⚠️  端口 ${port} 被占用，将尝试使用其他端口`, 'yellow')
  }
  
  // 启动Vite开发服务器
  const viteProcess = spawn('npm', ['run', 'dev'], {
    stdio: 'inherit',
    shell: true,
    cwd: path.join(__dirname, '..')
  })
  
  viteProcess.on('error', (error) => {
    log(`❌ 启动失败: ${error.message}`, 'red')
    process.exit(1)
  })
  
  viteProcess.on('close', (code) => {
    if (code !== 0) {
      log(`❌ 开发服务器退出，退出码: ${code}`, 'red')
    } else {
      log('👋 开发服务器已停止', 'blue')
    }
  })
  
  // 处理进程退出
  process.on('SIGINT', () => {
    log('\n📴 正在停止开发服务器...', 'yellow')
    viteProcess.kill('SIGINT')
  })
  
  process.on('SIGTERM', () => {
    log('\n📴 正在停止开发服务器...', 'yellow')
    viteProcess.kill('SIGTERM')
  })
}

// 主函数
const main = async () => {
  try {
    log('🔍 NewsLook 前端启动检查...', 'magenta')
    log('=====================================', 'magenta')
    
    checkNodeVersion()
    checkDependencies()
    
    log('=====================================', 'magenta')
    
    await startDevServer()
  } catch (error) {
    log(`❌ 启动失败: ${error.message}`, 'red')
    process.exit(1)
  }
}

// 运行
main() 