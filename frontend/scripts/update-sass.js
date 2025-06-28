#!/usr/bin/env node

/**
 * 更新Sass到现代API版本并清理缓存
 */

const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')

console.log('🔄 开始更新Sass到现代API版本...')

try {
  // 1. 清理现有的node_modules和缓存
  console.log('🧹 清理现有的node_modules和缓存...')
  
  const nodeModulesPath = path.join(__dirname, '..', 'node_modules')
  const viteCachePath = path.join(__dirname, '..', 'node_modules', '.vite')
  
  if (fs.existsSync(nodeModulesPath)) {
    execSync('rm -rf node_modules', { cwd: path.join(__dirname, '..'), stdio: 'inherit' })
  }
  
  // 2. 清理package-lock.json
  const packageLockPath = path.join(__dirname, '..', 'package-lock.json')
  if (fs.existsSync(packageLockPath)) {
    fs.unlinkSync(packageLockPath)
    console.log('✅ 已删除 package-lock.json')
  }
  
  // 3. 重新安装依赖
  console.log('📦 重新安装依赖...')
  execSync('npm install', { cwd: path.join(__dirname, '..'), stdio: 'inherit' })
  
  // 4. 验证Sass版本
  console.log('🔍 验证Sass版本...')
  const sassVersion = execSync('npm list sass --depth=0', { 
    cwd: path.join(__dirname, '..'), 
    encoding: 'utf-8' 
  })
  console.log('✅ Sass版本信息:', sassVersion.trim())
  
  console.log('🎉 Sass更新完成！现在应该使用现代API，避免弃用警告。')
  console.log('💡 建议运行 npm run dev 来测试更新效果。')
  
} catch (error) {
  console.error('❌ 更新过程中出错:', error.message)
  process.exit(1)
} 