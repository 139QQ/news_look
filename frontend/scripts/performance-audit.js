#!/usr/bin/env node

/**
 * NewsLook 性能审计脚本
 * 分析构建产物和运行时性能
 */

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.join(__dirname, '..');
const distDir = path.join(projectRoot, 'dist');

// 性能指标阈值
const PERFORMANCE_THRESHOLDS = {
  // 文件大小限制 (KB)
  maxJsFileSize: 500,
  maxCssFileSize: 100,
  maxImageSize: 200,
  maxFontSize: 100,
  
  // 总体大小限制 (MB)
  maxTotalSize: 5,
  maxJsSize: 2,
  maxCssSize: 0.5,
  
  // 文件数量限制
  maxJsFiles: 10,
  maxCssFiles: 5,
  maxImageFiles: 20,
  
  // Gzip压缩比例 (期望压缩到原始大小的百分比)
  expectedGzipRatio: 0.3
};

// 性能建议
const PERFORMANCE_SUGGESTIONS = {
  largeJs: '建议拆分大型JS文件，使用动态导入',
  largeCss: '建议移除未使用的CSS，使用CSS压缩',
  largeImage: '建议压缩图片或使用WebP格式',
  largeFont: '建议只加载必要的字体子集',
  tooManyFiles: '建议合并小文件，减少HTTP请求',
  poorCompression: '建议启用更好的压缩算法'
};

class PerformanceAuditor {
  constructor() {
    this.results = {
      files: [],
      summary: {},
      issues: [],
      suggestions: []
    };
  }

  async analyzeDistDirectory() {
    console.log('🔍 开始分析构建产物...\n');
    
    try {
      await this.scanDirectory(distDir);
      this.calculateSummary();
      this.checkPerformanceIssues();
      this.generateReport();
    } catch (error) {
      console.error('❌ 分析失败:', error.message);
      process.exit(1);
    }
  }

  async scanDirectory(dir, basePath = '') {
    try {
      const entries = await fs.readdir(dir, { withFileTypes: true });
      
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        const relativePath = path.join(basePath, entry.name);
        
        if (entry.isDirectory()) {
          await this.scanDirectory(fullPath, relativePath);
        } else {
          await this.analyzeFile(fullPath, relativePath);
        }
      }
    } catch (error) {
      console.warn(`⚠️  无法扫描目录 ${dir}: ${error.message}`);
    }
  }

  async analyzeFile(filePath, relativePath) {
    try {
      const stats = await fs.stat(filePath);
      const ext = path.extname(relativePath).toLowerCase();
      const size = stats.size;
      
      const fileInfo = {
        path: relativePath,
        size: size,
        sizeKB: Math.round(size / 1024 * 100) / 100,
        type: this.getFileType(ext),
        ext: ext,
        gzipEstimate: Math.round(size * 0.3) // 估算Gzip压缩后大小
      };
      
      this.results.files.push(fileInfo);
    } catch (error) {
      console.warn(`⚠️  无法分析文件 ${filePath}: ${error.message}`);
    }
  }

  getFileType(ext) {
    const typeMap = {
      '.js': 'javascript',
      '.mjs': 'javascript',
      '.css': 'stylesheet',
      '.png': 'image',
      '.jpg': 'image',
      '.jpeg': 'image',
      '.gif': 'image',
      '.svg': 'image',
      '.webp': 'image',
      '.woff': 'font',
      '.woff2': 'font',
      '.ttf': 'font',
      '.eot': 'font',
      '.html': 'html',
      '.json': 'data',
      '.ico': 'icon'
    };
    
    return typeMap[ext] || 'other';
  }

  calculateSummary() {
    const summary = {
      totalFiles: this.results.files.length,
      totalSize: 0,
      totalSizeKB: 0,
      totalSizeMB: 0,
      types: {}
    };
    
    for (const file of this.results.files) {
      summary.totalSize += file.size;
      
      if (!summary.types[file.type]) {
        summary.types[file.type] = {
          count: 0,
          size: 0,
          sizeKB: 0,
          files: []
        };
      }
      
      summary.types[file.type].count++;
      summary.types[file.type].size += file.size;
      summary.types[file.type].sizeKB += file.sizeKB;
      summary.types[file.type].files.push(file);
    }
    
    summary.totalSizeKB = Math.round(summary.totalSize / 1024 * 100) / 100;
    summary.totalSizeMB = Math.round(summary.totalSize / (1024 * 1024) * 100) / 100;
    
    this.results.summary = summary;
  }

  checkPerformanceIssues() {
    const { files, summary } = this.results;
    const issues = [];
    const suggestions = [];
    
    // 检查总体大小
    if (summary.totalSizeMB > PERFORMANCE_THRESHOLDS.maxTotalSize) {
      issues.push({
        type: 'warning',
        category: 'size',
        message: `总构建大小过大: ${summary.totalSizeMB}MB (建议 < ${PERFORMANCE_THRESHOLDS.maxTotalSize}MB)`
      });
    }
    
    // 检查JavaScript文件
    const jsFiles = files.filter(f => f.type === 'javascript');
    const totalJsSize = jsFiles.reduce((sum, f) => sum + f.sizeKB, 0) / 1024;
    
    if (totalJsSize > PERFORMANCE_THRESHOLDS.maxJsSize) {
      issues.push({
        type: 'warning',
        category: 'javascript',
        message: `JavaScript总大小过大: ${totalJsSize.toFixed(2)}MB (建议 < ${PERFORMANCE_THRESHOLDS.maxJsSize}MB)`
      });
      suggestions.push(PERFORMANCE_SUGGESTIONS.largeJs);
    }
    
    if (jsFiles.length > PERFORMANCE_THRESHOLDS.maxJsFiles) {
      issues.push({
        type: 'info',
        category: 'javascript',
        message: `JavaScript文件数量较多: ${jsFiles.length} (建议 < ${PERFORMANCE_THRESHOLDS.maxJsFiles})`
      });
    }
    
    // 检查单个大文件
    for (const file of files) {
      const threshold = PERFORMANCE_THRESHOLDS[`max${file.type.charAt(0).toUpperCase() + file.type.slice(1)}FileSize`];
      
      if (threshold && file.sizeKB > threshold) {
        issues.push({
          type: 'warning',
          category: file.type,
          message: `文件过大: ${file.path} (${file.sizeKB}KB > ${threshold}KB)`
        });
      }
    }
    
    // 检查CSS文件
    const cssFiles = files.filter(f => f.type === 'stylesheet');
    const totalCssSize = cssFiles.reduce((sum, f) => sum + f.sizeKB, 0) / 1024;
    
    if (totalCssSize > PERFORMANCE_THRESHOLDS.maxCssSize) {
      issues.push({
        type: 'warning',
        category: 'stylesheet',
        message: `CSS总大小过大: ${totalCssSize.toFixed(2)}MB (建议 < ${PERFORMANCE_THRESHOLDS.maxCssSize}MB)`
      });
      suggestions.push(PERFORMANCE_SUGGESTIONS.largeCss);
    }
    
    this.results.issues = issues;
    this.results.suggestions = [...new Set(suggestions)];
  }

  generateReport() {
    const { summary, issues, suggestions } = this.results;
    
    console.log('📊 构建产物分析报告');
    console.log('='.repeat(50));
    
    // 总体概况
    console.log('\n📋 总体概况:');
    console.log(`   总文件数: ${summary.totalFiles}`);
    console.log(`   总大小: ${summary.totalSizeMB}MB (${summary.totalSizeKB}KB)`);
    console.log(`   估算Gzip后: ${Math.round(summary.totalSizeMB * 0.3 * 100) / 100}MB`);
    
    // 文件类型分布
    console.log('\n📁 文件类型分布:');
    for (const [type, data] of Object.entries(summary.types)) {
      console.log(`   ${type.padEnd(12)}: ${data.count.toString().padStart(3)} 文件, ${data.sizeKB.toString().padStart(8)}KB`);
    }
    
    // 最大文件
    console.log('\n📈 最大文件 (前10):');
    const largestFiles = this.results.files
      .sort((a, b) => b.sizeKB - a.sizeKB)
      .slice(0, 10);
    
    for (const file of largestFiles) {
      console.log(`   ${file.sizeKB.toString().padStart(6)}KB  ${file.path}`);
    }
    
    // 性能问题
    if (issues.length > 0) {
      console.log('\n⚠️  性能问题:');
      for (const issue of issues) {
        const icon = issue.type === 'warning' ? '⚠️ ' : 'ℹ️ ';
        console.log(`   ${icon} ${issue.message}`);
      }
    } else {
      console.log('\n✅ 未发现性能问题');
    }
    
    // 优化建议
    if (suggestions.length > 0) {
      console.log('\n💡 优化建议:');
      for (const suggestion of suggestions) {
        console.log(`   • ${suggestion}`);
      }
    }
    
    // 性能评分
    const score = this.calculatePerformanceScore();
    console.log('\n⭐ 性能评分:');
    console.log(`   ${score}/100 ${this.getScoreEmoji(score)}`);
    
    console.log('\n' + '='.repeat(50));
    
    // 保存详细报告
    this.saveDetailedReport();
  }

  calculatePerformanceScore() {
    let score = 100;
    const { issues } = this.results;
    
    for (const issue of issues) {
      if (issue.type === 'warning') {
        score -= 15;
      } else if (issue.type === 'info') {
        score -= 5;
      }
    }
    
    return Math.max(0, score);
  }

  getScoreEmoji(score) {
    if (score >= 90) return '🟢 优秀';
    if (score >= 70) return '🟡 良好';
    if (score >= 50) return '🟠 一般';
    return '🔴 需要优化';
  }

  async saveDetailedReport() {
    const reportPath = path.join(distDir, 'performance-report.json');
    
    try {
      await fs.writeFile(
        reportPath,
        JSON.stringify(this.results, null, 2),
        'utf8'
      );
      console.log(`📄 详细报告已保存: ${reportPath}`);
    } catch (error) {
      console.warn(`⚠️  无法保存详细报告: ${error.message}`);
    }
  }
}

// 运行性能审计
async function main() {
  console.log('🚀 NewsLook 性能审计工具\n');
  
  const auditor = new PerformanceAuditor();
  await auditor.analyzeDistDirectory();
}

// 执行主函数
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

export default PerformanceAuditor; 