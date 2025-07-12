#!/usr/bin/env node

/**
 * 系统指标API测试脚本
 * 用于验证后端系统指标API是否正常工作
 */

import axios from 'axios'
import fs from 'fs'
import path from 'path'

// API配置
const API_BASE_URL = 'http://localhost:5000'
const ENDPOINTS = {
  health: '/api/health',
  systemMetrics: '/api/v1/system/metrics',
  systemHealth: '/api/v1/system/health'
}

// 测试结果
const results = {
  tests: [],
  passed: 0,
  failed: 0
}

function addResult(name, success, data = null, error = null) {
  const result = {
    name,
    success,
    timestamp: new Date().toISOString(),
    data,
    error: error?.message || error
  }
  
  results.tests.push(result)
  if (success) {
    results.passed++
    console.log(`✅ ${name}`)
    if (data) {
      console.log(`   数据: ${JSON.stringify(data, null, 2).slice(0, 200)}...`)
    }
  } else {
    results.failed++
    console.log(`❌ ${name}`)
    console.log(`   错误: ${error}`)
  }
}

async function testBasicHealth() {
  try {
    const response = await axios.get(`${API_BASE_URL}${ENDPOINTS.health}`)
    addResult('基础健康检查', true, response.data)
  } catch (error) {
    addResult('基础健康检查', false, null, error.message)
  }
}

async function testSystemHealth() {
  try {
    const response = await axios.get(`${API_BASE_URL}${ENDPOINTS.systemHealth}`)
    addResult('系统健康检查', true, response.data)
  } catch (error) {
    addResult('系统健康检查', false, null, error.message)
  }
}

async function testSystemMetrics() {
  try {
    const response = await axios.get(`${API_BASE_URL}${ENDPOINTS.systemMetrics}`)
    const data = response.data
    
    // 验证数据结构
    const hasCurrentMetrics = data.current && typeof data.current.cpu_percent === 'number'
    const hasValidCpu = data.current.cpu_percent >= 0 && data.current.cpu_percent <= 100
    const hasValidMemory = data.current.memory_percent >= 0 && data.current.memory_percent <= 100
    
    if (hasCurrentMetrics && hasValidCpu && hasValidMemory) {
      addResult('系统指标API', true, {
        cpu: `${data.current.cpu_percent.toFixed(2)}%`,
        memory: `${data.current.memory_percent.toFixed(2)}%`,
        disk: `${data.current.disk_percent?.toFixed(2) || 'N/A'}%`,
        uptime: `${(data.current.uptime_seconds / 3600).toFixed(1)}h`
      })
    } else {
      addResult('系统指标API', false, null, '数据格式不正确或值超出范围')
    }
  } catch (error) {
    addResult('系统指标API', false, null, error.message)
  }
}

async function testMultipleMetricsCalls() {
  try {
    console.log('\n📊 测试连续多次调用系统指标API...')
    const calls = []
    
    for (let i = 0; i < 3; i++) {
      calls.push(axios.get(`${API_BASE_URL}${ENDPOINTS.systemMetrics}`))
    }
    
    const responses = await Promise.all(calls)
    const cpuValues = responses.map(r => r.data.current?.cpu_percent)
    
    const allValid = cpuValues.every(cpu => typeof cpu === 'number' && cpu >= 0 && cpu <= 100)
    
    if (allValid) {
      addResult('连续调用系统指标', true, {
        calls: cpuValues.length,
        cpuValues: cpuValues.map(cpu => `${cpu.toFixed(2)}%`)
      })
    } else {
      addResult('连续调用系统指标', false, null, '某些调用返回无效数据')
    }
  } catch (error) {
    addResult('连续调用系统指标', false, null, error.message)
  }
}

async function runAllTests() {
  console.log('🚀 开始测试系统指标API...\n')
  
  await testBasicHealth()
  await testSystemHealth() 
  await testSystemMetrics()
  await testMultipleMetricsCalls()
  
  console.log('\n📈 测试结果汇总:')
  console.log(`✅ 通过: ${results.passed}`)
  console.log(`❌ 失败: ${results.failed}`)
  console.log(`📊 总计: ${results.tests.length}`)
  
  if (results.failed === 0) {
    console.log('\n🎉 所有测试通过！系统指标API工作正常')
  } else {
    console.log('\n⚠️ 部分测试失败，请检查后端服务')
    
    // 显示失败的测试详情
    const failedTests = results.tests.filter(t => !t.success)
    failedTests.forEach(test => {
      console.log(`\n❌ ${test.name}:`)
      console.log(`   错误: ${test.error}`)
    })
  }
  
  // 生成测试报告
  const report = {
    summary: {
      passed: results.passed,
      failed: results.failed,
      total: results.tests.length,
      timestamp: new Date().toISOString()
    },
    details: results.tests
  }
  
  const reportPath = 'logs/system-metrics-test-report.json'
  
  // 确保目录存在
  const dir = path.dirname(reportPath)
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true })
  }
  
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2))
  console.log(`\n📄 详细报告已保存到: ${reportPath}`)
  
  return results.failed === 0
}

// 运行测试
runAllTests()
  .then(success => {
    process.exit(success ? 0 : 1)
  })
  .catch(error => {
    console.error('❌ 测试运行失败:', error)
    process.exit(1)
  })

export { runAllTests } 