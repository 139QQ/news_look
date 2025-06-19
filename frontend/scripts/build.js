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

// 清理dist目录
const cleanDist = () => {
  const distPath = path.join(__dirname, '../dist')
  
  if (fs.existsSync(distPath)) {
    log('🧹 清理旧的构建文件...', 'yellow')
    fs.rmSync(distPath, { recursive: true, force: true })
  }
}

// 检查环境
const checkEnvironment = () => {
  log('🔍 检查构建环境...', 'cyan')
  
  // 检查Node.js版本
  const nodeVersion = process.version
  const majorVersion = parseInt(nodeVersion.split('.')[0].slice(1))
  
  if (majorVersion < 16) {
    log('❌ Node.js 版本过低！需要 Node.js 16 或更高版本', 'red')
    process.exit(1)
  }
  
  // 检查package.json
  const packageJsonPath = path.join(__dirname, '../package.json')
  if (!fs.existsSync(packageJsonPath)) {
    log('❌ 未找到 package.json 文件', 'red')
    process.exit(1)
  }
  
  // 检查依赖
  const nodeModulesPath = path.join(__dirname, '../node_modules')
  if (!fs.existsSync(nodeModulesPath)) {
    log('❌ 依赖未安装，请先运行 npm install', 'red')
    process.exit(1)
  }
  
  log('✅ 环境检查通过', 'green')
}

// 运行构建
const runBuild = () => {
  return new Promise((resolve, reject) => {
    log('\n📦 开始构建生产版本...', 'cyan')
    
    const buildProcess = spawn('npm', ['run', 'build'], {
      stdio: 'inherit',
      shell: true,
      cwd: path.join(__dirname, '..')
    })
    
    buildProcess.on('error', (error) => {
      reject(error)
    })
    
    buildProcess.on('close', (code) => {
      if (code === 0) {
        resolve()
      } else {
        reject(new Error(`构建失败，退出码: ${code}`))
      }
    })
  })
}

// 分析构建结果
const analyzeBuild = () => {
  log('\n📊 分析构建结果...', 'cyan')
  
  const distPath = path.join(__dirname, '../dist')
  
  if (!fs.existsSync(distPath)) {
    log('❌ 构建目录不存在', 'red')
    return
  }
  
  // 计算文件大小
  const getFileSize = (filePath) => {
    const stats = fs.statSync(filePath)
    const size = stats.size
    if (size < 1024) return `${size} B`
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
    return `${(size / (1024 * 1024)).toFixed(1)} MB`
  }
  
  // 递归获取所有文件
  const getAllFiles = (dir, files = []) => {
    const fileList = fs.readdirSync(dir)
    
    fileList.forEach(file => {
      const filePath = path.join(dir, file)
      const stat = fs.statSync(filePath)
      
      if (stat.isDirectory()) {
        getAllFiles(filePath, files)
      } else {
        files.push({
          path: filePath,
          relativePath: path.relative(distPath, filePath),
          size: stat.size
        })
      }
    })
    
    return files
  }
  
  const files = getAllFiles(distPath)
  const totalSize = files.reduce((sum, file) => sum + file.size, 0)
  
  log(`\n📁 构建文件分析:`, 'green')
  log(`   总文件数: ${files.length}`, 'blue')
  log(`   总大小: ${getFileSize(totalSize)}`, 'blue')
  
  // 按文件类型分类
  const fileTypes = {}
  files.forEach(file => {
    const ext = path.extname(file.relativePath).toLowerCase()
    if (!fileTypes[ext]) {
      fileTypes[ext] = { count: 0, size: 0 }
    }
    fileTypes[ext].count++
    fileTypes[ext].size += file.size
  })
  
  log('\n📂 文件类型分布:', 'green')
  Object.entries(fileTypes)
    .sort((a, b) => b[1].size - a[1].size)
    .forEach(([ext, info]) => {
      log(`   ${ext || '无扩展名'}: ${info.count} 个文件, ${getFileSize(info.size)}`, 'blue')
    })
  
  // 显示最大的文件
  const largestFiles = files
    .sort((a, b) => b.size - a.size)
    .slice(0, 5)
  
  if (largestFiles.length > 0) {
    log('\n📄 最大的文件:', 'green')
    largestFiles.forEach((file, index) => {
      log(`   ${index + 1}. ${file.relativePath} (${getFileSize(file.size)})`, 'blue')
    })
  }
  
  // 检查构建质量
  log('\n✨ 构建质量检查:', 'green')
  
  const jsFiles = files.filter(f => f.relativePath.endsWith('.js'))
  const cssFiles = files.filter(f => f.relativePath.endsWith('.css'))
  const imageFiles = files.filter(f => /\.(png|jpg|jpeg|gif|svg|webp)$/i.test(f.relativePath))
  
  const totalJsSize = jsFiles.reduce((sum, f) => sum + f.size, 0)
  const totalCssSize = cssFiles.reduce((sum, f) => sum + f.size, 0)
  const totalImageSize = imageFiles.reduce((sum, f) => sum + f.size, 0)
  
  log(`   JS 文件: ${jsFiles.length} 个, ${getFileSize(totalJsSize)}`, 'blue')
  log(`   CSS 文件: ${cssFiles.length} 个, ${getFileSize(totalCssSize)}`, 'blue')
  log(`   图片文件: ${imageFiles.length} 个, ${getFileSize(totalImageSize)}`, 'blue')
  
  // 性能建议
  if (totalJsSize > 2 * 1024 * 1024) {
    log('⚠️  JS 文件总大小超过 2MB，建议进一步优化', 'yellow')
  }
  
  if (totalCssSize > 500 * 1024) {
    log('⚠️  CSS 文件总大小超过 500KB，建议检查是否有未使用的样式', 'yellow')
  }
  
  const hasSourceMaps = files.some(f => f.relativePath.endsWith('.map'))
  if (hasSourceMaps) {
    log('ℹ️  检测到 source map 文件，生产环境建议关闭', 'blue')
  }
}

// 主函数
const main = async () => {
  try {
    log('🏗️  NewsLook 前端生产构建', 'magenta')
    log('=====================================', 'magenta')
    
    checkEnvironment()
    cleanDist()
    
    await runBuild()
    
    log('\n✅ 构建完成！', 'green')
    
    analyzeBuild()
    
    log('\n🎉 构建成功完成！', 'green')
    log('📁 构建文件位于 dist/ 目录', 'blue')
    
  } catch (error) {
    log(`\n❌ 构建失败: ${error.message}`, 'red')
    process.exit(1)
  }
}

// 运行
main() 