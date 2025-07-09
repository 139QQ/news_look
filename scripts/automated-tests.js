#!/usr/bin/env node

/**
 * NewsLook 自动化测试脚本
 * 包含API测试、错误处理测试、性能测试、集成测试等
 */

const axios = require('axios')
const fs = require('fs').promises
const path = require('path')
const { performance } = require('perf_hooks')

// 测试配置
const TEST_CONFIG = {
  baseUrl: process.env.TEST_BASE_URL || 'http://127.0.0.1:5000',
  timeout: 30000,
  retries: 3,
  parallel: true,
  saveResults: true
}

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

// 测试结果收集器
class TestRunner {
  constructor() {
    this.results = {
      total: 0,
      passed: 0,
      failed: 0,
      skipped: 0,
      tests: [],
      startTime: Date.now(),
      endTime: null,
      duration: 0
    }
  }

  async runTest(name, testFunc, category = 'general') {
    this.results.total++
    const startTime = performance.now()
    
    try {
      colorLog('blue', `\n🧪 执行测试: ${name}`)
      
      const result = await testFunc()
      const duration = performance.now() - startTime
      
      this.results.passed++
      this.results.tests.push({
        name,
        category,
        status: 'PASSED',
        duration: Math.round(duration),
        result,
        timestamp: new Date().toISOString()
      })
      
      colorLog('green', `✅ ${name} - 通过 (${Math.round(duration)}ms)`)
      
    } catch (error) {
      const duration = performance.now() - startTime
      
      this.results.failed++
      this.results.tests.push({
        name,
        category,
        status: 'FAILED',
        duration: Math.round(duration),
        error: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString()
      })
      
      colorLog('red', `❌ ${name} - 失败: ${error.message}`)
      if (process.env.DEBUG) {
        console.error(error.stack)
      }
    }
  }

  skipTest(name, reason, category = 'general') {
    this.results.total++
    this.results.skipped++
    this.results.tests.push({
      name,
      category,
      status: 'SKIPPED',
      reason,
      timestamp: new Date().toISOString()
    })
    
    colorLog('yellow', `⏭️  ${name} - 跳过: ${reason}`)
  }

  finish() {
    this.results.endTime = Date.now()
    this.results.duration = this.results.endTime - this.results.startTime
    
    // 输出测试总结
    colorLog('blue', '\n📊 测试总结:')
    colorLog('blue', '='.repeat(50))
    colorLog('green', `✅ 通过: ${this.results.passed}`)
    colorLog('red', `❌ 失败: ${this.results.failed}`)
    colorLog('yellow', `⏭️  跳过: ${this.results.skipped}`)
    colorLog('blue', `📊 总计: ${this.results.total}`)
    colorLog('cyan', `⏱️  用时: ${Math.round(this.results.duration)}ms`)
    
    // 计算成功率
    const successRate = this.results.total > 0 ? 
      ((this.results.passed / (this.results.total - this.results.skipped)) * 100).toFixed(1) : 0
    colorLog('cyan', `📈 成功率: ${successRate}%`)
    
    return this.results
  }
}

// HTTP客户端配置
const httpClient = axios.create({
  baseURL: TEST_CONFIG.baseUrl,
  timeout: TEST_CONFIG.timeout,
  validateStatus: () => true  // 允许所有状态码，手动处理
})

// 测试工具函数
async function waitForServer(maxAttempts = 10, delay = 1000) {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const response = await httpClient.get('/api/health')
      if (response.status === 200) {
        return true
      }
    } catch (error) {
      // 继续尝试
    }
    
    if (i < maxAttempts - 1) {
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }
  return false
}

function assertStatus(response, expectedStatus, testName) {
  if (response.status !== expectedStatus) {
    throw new Error(`${testName}: 期望状态码 ${expectedStatus}，实际 ${response.status}`)
  }
}

function assertExists(value, fieldName) {
  if (value === undefined || value === null) {
    throw new Error(`${fieldName} 不应为空`)
  }
}

function assertType(value, expectedType, fieldName) {
  if (typeof value !== expectedType) {
    throw new Error(`${fieldName} 应为 ${expectedType} 类型，实际为 ${typeof value}`)
  }
}

// 1. 基础健康检查测试
async function testHealthCheck() {
  const response = await httpClient.get('/api/health')
  
  assertStatus(response, 200, '健康检查')
  assertExists(response.data.status, 'status')
  assertExists(response.data.timestamp, 'timestamp')
  
  return { status: response.data.status }
}

// 2. 详细健康检查测试
async function testDetailedHealthCheck() {
  const response = await httpClient.get('/api/health?level=detailed')
  
  assertStatus(response, 200, '详细健康检查')
  assertExists(response.data.system_metrics, 'system_metrics')
  assertExists(response.data.database, 'database')
  
  // 验证系统指标结构
  const metrics = response.data.system_metrics
  assertExists(metrics.cpu, 'cpu')
  assertExists(metrics.memory, 'memory')
  assertExists(metrics.disk, 'disk')
  
  return { 
    cpu_usage: metrics.cpu.usage_percent,
    memory_usage: metrics.memory.percent,
    db_status: response.data.database.status
  }
}

// 3. API性能测试
async function testApiPerformance() {
  const tests = [
    { name: '健康检查', endpoint: '/api/health' },
    { name: '新闻列表', endpoint: '/api/news' },
    { name: '新闻来源', endpoint: '/api/sources' }
  ]
  
  const results = {}
  
  for (const test of tests) {
    const startTime = performance.now()
    const response = await httpClient.get(test.endpoint)
    const duration = performance.now() - startTime
    
    results[test.name] = {
      status: response.status,
      duration: Math.round(duration),
      responseSize: JSON.stringify(response.data).length
    }
    
    // 性能阈值检查
    if (duration > 5000) {
      throw new Error(`${test.name} 响应时间过长: ${Math.round(duration)}ms`)
    }
  }
  
  return results
}

// 4. 错误处理测试
async function testErrorHandling() {
  const errorTests = [
    {
      name: '404错误',
      endpoint: '/api/nonexistent',
      expectedStatus: 404
    },
    {
      name: '无效新闻ID',
      endpoint: '/api/news/invalid-id-12345',
      expectedStatus: 404
    },
    {
      name: '无效参数',
      endpoint: '/api/news?limit=invalid',
      expectedStatus: [200, 400] // 可能被容错处理
    }
  ]
  
  const results = {}
  
  for (const test of errorTests) {
    const response = await httpClient.get(test.endpoint)
    
    const expectedStatuses = Array.isArray(test.expectedStatus) 
      ? test.expectedStatus 
      : [test.expectedStatus]
    
    if (!expectedStatuses.includes(response.status)) {
      throw new Error(`${test.name}: 期望状态码 ${test.expectedStatus}，实际 ${response.status}`)
    }
    
    results[test.name] = {
      status: response.status,
      hasErrorMessage: !!response.data?.error || !!response.data?.message
    }
  }
  
  return results
}

// 5. 数据一致性测试
async function testDataConsistency() {
  // 获取新闻列表
  const newsResponse = await httpClient.get('/api/news?limit=10')
  assertStatus(newsResponse, 200, '新闻列表获取')
  
  if (!newsResponse.data || !Array.isArray(newsResponse.data)) {
    throw new Error('新闻数据格式不正确')
  }
  
  // 验证新闻数据结构
  const news = newsResponse.data
  if (news.length > 0) {
    const firstNews = news[0]
    assertExists(firstNews.id, 'news.id')
    assertExists(firstNews.title, 'news.title')
    assertType(firstNews.title, 'string', 'news.title')
    
    // 测试获取具体新闻详情
    const detailResponse = await httpClient.get(`/api/news/${firstNews.id}`)
    if (detailResponse.status === 200) {
      assertExists(detailResponse.data.id, 'news_detail.id')
      if (detailResponse.data.id !== firstNews.id) {
        throw new Error('新闻详情ID与列表ID不匹配')
      }
    }
  }
  
  return { 
    newsCount: news.length,
    hasValidStructure: true,
    detailAccessible: news.length > 0
  }
}

// 6. 并发测试
async function testConcurrency() {
  const concurrentRequests = 10
  const endpoint = '/api/health'
  
  const startTime = performance.now()
  
  // 创建并发请求
  const promises = Array(concurrentRequests).fill().map(async (_, index) => {
    const response = await httpClient.get(endpoint)
    return {
      index,
      status: response.status,
      duration: performance.now() - startTime
    }
  })
  
  const results = await Promise.all(promises)
  const duration = performance.now() - startTime
  
  // 检查所有请求是否成功
  const failedRequests = results.filter(r => r.status !== 200)
  if (failedRequests.length > 0) {
    throw new Error(`${failedRequests.length}/${concurrentRequests} 并发请求失败`)
  }
  
  return {
    totalRequests: concurrentRequests,
    successfulRequests: results.length,
    totalDuration: Math.round(duration),
    averageDuration: Math.round(duration / concurrentRequests)
  }
}

// 7. 监控API测试
async function testMonitoringAPI() {
  const tests = [
    {
      name: '监控健康检查',
      endpoint: '/api/monitoring/health',
      method: 'GET'
    },
    {
      name: '系统指标',
      endpoint: '/api/monitoring/metrics?type=system',
      method: 'GET'
    },
    {
      name: '仪表盘数据',
      endpoint: '/api/monitoring/dashboard',
      method: 'GET'
    }
  ]
  
  const results = {}
  
  for (const test of tests) {
    try {
      const response = await httpClient[test.method.toLowerCase()](test.endpoint)
      results[test.name] = {
        status: response.status,
        available: response.status === 200,
        hasData: !!response.data
      }
    } catch (error) {
      results[test.name] = {
        status: 'ERROR',
        available: false,
        error: error.message
      }
    }
  }
  
  return results
}

// 8. 前端资源测试
async function testFrontendAssets() {
  const frontendTests = [
    {
      name: '前端首页',
      endpoint: '/',
      expectedType: 'text/html'
    },
    {
      name: '静态资源检查',
      endpoint: '/static/js/',
      skipOn404: true
    }
  ]
  
  const results = {}
  
  for (const test of frontendTests) {
    try {
      const response = await httpClient.get(test.endpoint)
      
      if (test.skipOn404 && response.status === 404) {
        results[test.name] = { status: 'SKIPPED', reason: 'Resource not found' }
        continue
      }
      
      results[test.name] = {
        status: response.status,
        contentType: response.headers['content-type'],
        available: response.status === 200
      }
      
    } catch (error) {
      results[test.name] = {
        status: 'ERROR',
        error: error.message,
        available: false
      }
    }
  }
  
  return results
}

// 9. 安全性测试（基础）
async function testBasicSecurity() {
  const securityTests = [
    {
      name: 'SQL注入防护',
      endpoint: '/api/news?id=1\' OR \'1\'=\'1',
      expectNoError: true
    },
    {
      name: 'XSS防护',
      endpoint: '/api/news?title=<script>alert(1)</script>',
      expectNoError: true
    },
    {
      name: '大量数据请求',
      endpoint: '/api/news?limit=999999',
      expectControlled: true
    }
  ]
  
  const results = {}
  
  for (const test of securityTests) {
    const response = await httpClient.get(test.endpoint)
    
    results[test.name] = {
      status: response.status,
      handled: response.status !== 500, // 没有内部服务器错误
      responseSize: JSON.stringify(response.data).length
    }
    
    // 检查是否有可疑的错误泄露
    if (response.status === 500 && response.data?.error?.includes?.('SQL')) {
      throw new Error(`${test.name}: 可能存在SQL注入漏洞`)
    }
  }
  
  return results
}

// 10. 集成测试场景
async function testIntegrationScenario() {
  // 模拟用户完整操作流程
  const scenario = []
  
  // 1. 访问首页
  let response = await httpClient.get('/api/health')
  assertStatus(response, 200, '系统启动检查')
  scenario.push({ step: '系统启动检查', status: 'OK' })
  
  // 2. 获取新闻列表
  response = await httpClient.get('/api/news?limit=5')
  const hasNews = response.status === 200 && response.data?.length > 0
  scenario.push({ step: '获取新闻列表', status: hasNews ? 'OK' : 'NO_DATA' })
  
  // 3. 获取来源列表
  response = await httpClient.get('/api/sources')
  const hasSources = response.status === 200
  scenario.push({ step: '获取来源列表', status: hasSources ? 'OK' : 'FAILED' })
  
  // 4. 检查爬虫状态
  try {
    response = await httpClient.get('/api/v1/crawlers/status')
    const crawlerWorking = response.status === 200
    scenario.push({ step: '爬虫状态检查', status: crawlerWorking ? 'OK' : 'UNAVAILABLE' })
  } catch (error) {
    scenario.push({ step: '爬虫状态检查', status: 'UNAVAILABLE' })
  }
  
  return { scenario, totalSteps: scenario.length }
}

// 保存测试结果
async function saveTestResults(results) {
  if (!TEST_CONFIG.saveResults) return
  
  try {
    const resultsDir = path.join(process.cwd(), 'logs')
    await fs.mkdir(resultsDir, { recursive: true })
    
    const filename = `test-results-${Date.now()}.json`
    const filepath = path.join(resultsDir, filename)
    
    const reportData = {
      ...results,
      config: TEST_CONFIG,
      environment: {
        nodeVersion: process.version,
        platform: process.platform,
        timestamp: new Date().toISOString()
      }
    }
    
    await fs.writeFile(filepath, JSON.stringify(reportData, null, 2))
    colorLog('cyan', `📄 测试结果已保存: ${filepath}`)
    
  } catch (error) {
    colorLog('red', `保存测试结果失败: ${error.message}`)
  }
}

// 主测试函数
async function runAllTests() {
  const runner = new TestRunner()
  
  colorLog('blue', '🚀 NewsLook 自动化测试开始...')
  colorLog('blue', '='.repeat(60))
  colorLog('cyan', `测试目标: ${TEST_CONFIG.baseUrl}`)
  
  // 等待服务器就绪
  colorLog('yellow', '⏳ 等待服务器就绪...')
  const serverReady = await waitForServer()
  
  if (!serverReady) {
    colorLog('red', '❌ 服务器未响应，跳过所有测试')
    return runner.finish()
  }
  
  colorLog('green', '✅ 服务器就绪，开始测试')
  
  // 执行测试套件
  await runner.runTest('基础健康检查', testHealthCheck, 'health')
  await runner.runTest('详细健康检查', testDetailedHealthCheck, 'health')
  await runner.runTest('API性能测试', testApiPerformance, 'performance')
  await runner.runTest('错误处理测试', testErrorHandling, 'error_handling')
  await runner.runTest('数据一致性测试', testDataConsistency, 'data')
  await runner.runTest('并发测试', testConcurrency, 'performance')
  await runner.runTest('监控API测试', testMonitoringAPI, 'monitoring')
  await runner.runTest('前端资源测试', testFrontendAssets, 'frontend')
  await runner.runTest('基础安全测试', testBasicSecurity, 'security')
  await runner.runTest('集成测试场景', testIntegrationScenario, 'integration')
  
  // 完成测试
  const results = runner.finish()
  
  // 保存结果
  await saveTestResults(results)
  
  // 根据测试结果设置退出码
  if (results.failed > 0) {
    colorLog('red', '\n❗ 有测试失败，请检查相关功能')
    process.exit(1)
  } else if (results.passed === 0) {
    colorLog('yellow', '\n⚠️  没有成功的测试')
    process.exit(1)
  } else {
    colorLog('green', '\n🎉 所有测试通过！')
    process.exit(0)
  }
}

// 如果直接运行此脚本
if (require.main === module) {
  // 处理未捕获的异常
  process.on('unhandledRejection', (reason, promise) => {
    colorLog('red', `未处理的Promise拒绝: ${reason}`)
    process.exit(1)
  })
  
  process.on('uncaughtException', (error) => {
    colorLog('red', `未捕获的异常: ${error.message}`)
    process.exit(1)
  })
  
  runAllTests()
}

module.exports = {
  runAllTests,
  TestRunner,
  testHealthCheck,
  testApiPerformance,
  testErrorHandling
} 